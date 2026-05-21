from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from html.parser import HTMLParser
from html import escape
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from study_os.core.close_session_draft import build_close_session_draft
from study_os.core.models import Item
from study_os.core.packet_progress import set_packet_attempt, set_packet_checked
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore
from study_os.core.validation import ValidationError, validate_iso_date_text, validate_positive_day_index


_CLOSE_SESSION_DRAFT_PACKET_TYPES = frozenset({"learning", "recall", "final_recall"})
_DAILY_CLOSE_SESSION_DRAFT_PACKET_TYPES = frozenset({"learning", "recall"})


class _PacketItemIdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.item_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        attributes = {name: value for name, value in attrs}
        class_names = set((attributes.get("class") or "").split())
        item_id = attributes.get("data-item-id")
        if "packet-entry" in class_names and item_id:
            self.item_ids.add(item_id)


def validate_close_session_draft_params(
    *,
    packet_type: object,
    day_index: object,
    session_date: object,
) -> tuple[str, int | None, str]:
    packet_type_text = packet_type
    if not isinstance(packet_type_text, str) or packet_type_text not in _CLOSE_SESSION_DRAFT_PACKET_TYPES:
        raise ValidationError("packet_type must be one of: final_recall, learning, recall")

    session_date_text = validate_iso_date_text(session_date, "session_date")

    if packet_type_text in _DAILY_CLOSE_SESSION_DRAFT_PACKET_TYPES:
        if day_index is None:
            raise ValidationError("day_index is required for learning and recall packets")
        day_index_value = validate_positive_day_index(day_index)
    else:
        if day_index is not None:
            raise ValidationError("day_index must be omitted for final_recall packets")
        day_index_value = None

    return packet_type_text, day_index_value, session_date_text


class PacketServer:
    def __init__(self, *, workspace_root: Path, course_slug: str, port: int) -> None:
        self.workspace_root = workspace_root
        self.course_slug = course_slug
        self.paths = build_course_paths(workspace_root, course_slug)
        self.paths.ensure_directories()
        self.store = CourseStore(self.paths)
        self._progress_lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", port), self._build_handler())

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/api/close-session-draft":
                    try:
                        self._write_json(parent._close_session_draft_from_query(parsed.query))
                    except (KeyError, TypeError, ValueError) as exc:
                        self._write_json({"error": str(exc)}, status=400)
                    return

                if parsed.path == "/api/progress":
                    self._write_json(parent.store.load_packet_progress())
                    return

                asset_file = parent._resolve_asset_file(parsed.path)
                if asset_file is not None:
                    self._write_file(asset_file)
                    return
                if parsed.path.startswith("/assets/"):
                    self.send_error(404)
                    return

                if parsed.path == "/":
                    self._write_html(parent._render_index())
                    return

                html_file = parent._resolve_packet_file(parsed.path)
                if html_file is None or not html_file.exists():
                    self.send_error(404)
                    return

                self._write_html(html_file.read_text(encoding="utf-8"))

            def do_POST(self) -> None:  # noqa: N802
                if urlparse(self.path).path != "/api/progress":
                    self.send_error(404)
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                    parent._save_progress_update(body)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    self._write_json({"saved": False, "error": str(exc)}, status=400)
                    return

                self._write_json({"saved": True})

            def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                return

            def _write_html(self, body: str, *, status: int = 200) -> None:
                encoded = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _write_file(self, path: Path, *, status: int = 200) -> None:
                body = path.read_bytes()
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _write_json(self, payload: dict[str, object], *, status: int = 200) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler

    def _utc_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def _save_progress_update(self, body: dict[str, object]) -> None:
        with self._progress_lock:
            packet_type, day_index, item_id = self._validate_progress_target(
                packet_type=body["packet_type"],
                day_index=body.get("day_index"),
                item_id=body["item_id"],
            )
            payload = self.store.load_packet_progress()
            if body.get("action") == "attempt":
                updated = set_packet_attempt(
                    payload,
                    packet_type=packet_type,
                    day_index=day_index,
                    item_id=item_id,
                    draft_answer=body.get("draft_answer"),
                    result=body.get("result"),
                    confidence=body.get("confidence"),
                    confidence_score=body.get("confidence_score"),
                    blocker_type=body.get("blocker_type"),
                    checked_at=body.get("checked_at") or self._utc_timestamp(),
                )
            else:
                updated = set_packet_checked(
                    payload,
                    packet_type=packet_type,
                    day_index=day_index,
                    item_id=item_id,
                    checked=body["checked"],
                )
            self.store.save_packet_progress(updated)

    def _validate_progress_target(
        self,
        *,
        packet_type: object,
        day_index: object,
        item_id: object,
    ) -> tuple[str, int | None, str]:
        if not isinstance(packet_type, str) or packet_type not in _CLOSE_SESSION_DRAFT_PACKET_TYPES:
            raise ValidationError("packet_type must be one of: final_recall, learning, recall")
        if not isinstance(item_id, str) or not item_id:
            raise ValidationError("item_id must be a non-empty string")

        if packet_type in _DAILY_CLOSE_SESSION_DRAFT_PACKET_TYPES:
            day_index_value = validate_positive_day_index(day_index)
            packet_file = self._daily_packet_file(packet_type=packet_type, day_index=day_index_value)
        else:
            if day_index is not None:
                raise ValidationError("day_index must be omitted for final_recall packets")
            day_index_value = None
            packet_file = self.paths.final_recall_html_file

        if packet_file is None or not packet_file.exists():
            raise ValidationError("packet file not found for progress target")
        if item_id not in self._packet_item_ids(packet_file):
            raise ValidationError("item_id must exist in the served packet")
        return packet_type, day_index_value, item_id

    def _packet_item_ids(self, packet_file: Path) -> set[str]:
        parser = _PacketItemIdParser()
        parser.feed(packet_file.read_text(encoding="utf-8"))
        return parser.item_ids

    def _resolve_asset_file(self, path: str) -> Path | None:
        prefix = "/assets/"
        if not path.startswith(prefix):
            return None

        relative_path = unquote(path[len(prefix) :])
        if not relative_path or Path(relative_path).is_absolute():
            return None

        workspace_root = self.workspace_root.resolve()
        resolved_path = (self.workspace_root / relative_path).resolve(strict=False)
        try:
            resolved_path.relative_to(workspace_root)
        except ValueError:
            return None

        if not self._is_allowed_asset_path(resolved_path):
            return None
        if not resolved_path.exists() or not resolved_path.is_file():
            return None
        return resolved_path

    def _is_allowed_asset_path(self, path: Path) -> bool:
        if not self._is_image_asset_path(path):
            return False
        return path in self._allowed_visual_asset_paths()

    def _is_image_asset_path(self, path: Path) -> bool:
        content_type = mimetypes.guess_type(path.name)[0]
        return bool(content_type and content_type.startswith("image/"))

    def _allowed_visual_asset_paths(self) -> set[Path]:
        workspace_root = self.workspace_root.resolve()
        allowed_paths: set[Path] = set()
        for visual in self.store.load_visual_requirements():
            if visual.get("status") != "available":
                continue
            required_image = visual.get("required_image")
            if not isinstance(required_image, str) or not required_image:
                continue
            visual_path = Path(required_image)
            if visual_path.is_absolute():
                continue
            resolved_path = (self.workspace_root / visual_path).resolve(strict=False)
            try:
                resolved_path.relative_to(workspace_root)
            except ValueError:
                continue
            if self._is_image_asset_path(resolved_path):
                allowed_paths.add(resolved_path)
        return allowed_paths


    def _close_session_draft_from_query(self, query: str) -> dict[str, object]:
        params = parse_qs(query)
        packet_type = params.get("packet_type", [None])[0]
        session_date = params.get("session_date", [None])[0]
        day_text = params.get("day_index", [None])[0]
        try:
            parsed_day_index = int(day_text) if day_text not in {None, ""} else None
        except ValueError as exc:
            raise ValidationError("day_index must be a positive integer when provided") from exc
        packet_type, day_index, session_date = validate_close_session_draft_params(
            packet_type=packet_type,
            day_index=parsed_day_index,
            session_date=session_date,
        )
        items_by_id = {row["item_id"]: Item(**row) for row in self.store.load_items()}
        return build_close_session_draft(
            course_slug=self.course_slug,
            session_date=session_date,
            packet_type=packet_type,
            day_index=day_index,
            packet_progress=self.store.load_packet_progress(),
            items_by_id=items_by_id,
        )

    def _render_index(self) -> str:
        links = self._packet_links()
        if links:
            items = "".join(f'<li><a href="{escape(href)}">{escape(label)}</a></li>' for label, href in links)
            body = f"<ul>{items}</ul>"
        else:
            body = "<p>No packet HTML files found yet.</p>"
        return (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{escape(self.course_slug)} packets</title></head><body>"
            f"<h1>{escape(self.course_slug)}</h1>{body}</body></html>"
        )

    def _packet_links(self) -> list[tuple[str, str]]:
        links: list[tuple[str, str]] = []
        for html_file in sorted(self.paths.daily_dir.glob("day_*_*.html")):
            stem_parts = html_file.stem.split("_")
            if len(stem_parts) < 3:
                continue
            _, day_text, *packet_type_parts = stem_parts
            packet_type = "_".join(packet_type_parts)
            try:
                day_index = int(day_text)
            except ValueError:
                continue
            route_packet_type = packet_type.replace("_", "-")
            links.append((f"{packet_type} day {day_index}", f"/packets/{route_packet_type}/day/{day_index}"))
        if self.paths.final_recall_html_file.exists():
            links.append(("final_recall", "/packets/final-recall"))
        return links

    def _resolve_packet_file(self, path: str) -> Path | None:
        segments = [segment for segment in path.split("/") if segment]
        if segments == ["packets", "final-recall"]:
            return self.paths.final_recall_html_file

        if len(segments) != 4 or segments[0] != "packets" or segments[2] != "day":
            return None

        packet_type = segments[1].replace("-", "_")
        try:
            day_index = int(segments[3])
        except ValueError:
            return None
        if day_index <= 0:
            return None

        return self._daily_packet_file(packet_type=packet_type, day_index=day_index)

    def _daily_packet_file(self, *, packet_type: str, day_index: int) -> Path | None:
        file_builders: dict[str, Callable[..., Path]] = {
            "learning": self.paths.learning_packet_html_file,
            "recall": self.paths.recall_packet_html_file,
        }
        builder = file_builders.get(packet_type)
        if builder is None:
            return None
        return builder(day_index=day_index)

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
