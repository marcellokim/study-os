from __future__ import annotations

from dataclasses import asdict, replace
from html.parser import HTMLParser
from pathlib import Path
import shutil
from typing import Any

from study_os.core.close_session_draft import build_close_session_draft
from study_os.core.constants import STATUS_ORDER
from study_os.core.fresh_qa import AXIS_VALUES, FRESH_QA_AXES, GATES, REQUIRED_FIELDS
from study_os.core.models import Block, CourseConfig, ExecutionReceipt, Item, MasteryRecord, QueueEntry, VisualRequirement
from study_os.core.packet_builder import (
    build_final_recall_packet_model,
    build_learning_packet_model,
    build_recall_packet_model,
)
from study_os.core.packet_html import render_packet_html
from study_os.core.packet_progress import build_progress_key
from study_os.core.packets import build_final_recall_pack, build_learning_packet, build_master_plan, build_recall_packet
from study_os.core.paths import CoursePaths, build_course_paths
from study_os.core.scheduler import build_queue_entry
from study_os.core.source_files import validate_source_files
from study_os.core.storage import CourseStore
from study_os.core.transitions import apply_review_update
from study_os.core.validation import (
    ValidationError,
    validate_close_session_request,
    validate_close_session_request_shape,
    validate_course_slug_text,
    validate_init_course_request,
    validate_iso_date_text,
    validate_positive_day_index,
)

_IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}
_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
_NEW_BLOCKS_PER_DAY = 2
_FALLBACK_STUDY_ORDER = 10**9


class _PacketItemIdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.item_ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "article":
            return
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        item_id = attr_map.get("data-item-id")
        if "packet-entry" in classes and item_id:
            self.item_ids.append(item_id)


def _pending_visual_requirements(visuals: list[VisualRequirement]) -> list[VisualRequirement]:
    return [visual for visual in visuals if visual.status != "available"]


def _block_schedule_key(block: Block) -> tuple[bool, int, int, str, str]:
    return (
        block.study_order is None,
        block.study_order or _FALLBACK_STUDY_ORDER,
        _IMPORTANCE_ORDER.get(block.importance, len(_IMPORTANCE_ORDER)),
        block.block_name,
        block.block_id,
    )


def _checked_progress_for(
    packet_progress: dict[str, Any],
    *,
    packet_type: str,
    day_index: int | None,
) -> dict[str, dict[str, Any]]:
    progress_key = build_progress_key(packet_type=packet_type, day_index=day_index)
    return {
        item_id: dict(item_progress)
        for item_id, item_progress in packet_progress.get(progress_key, {}).items()
    }


def _daily_packet_links(day_index: int) -> dict[str, str]:
    return {
        "learning": f"/packets/learning/day/{day_index}",
        "recall": f"/packets/recall/day/{day_index}",
    }


def _review_entry_is_due(entry: QueueEntry, *, day_index: int, today: str) -> bool:
    if entry.next_review_day is None or entry.next_review_day <= day_index:
        return True
    if entry.next_review_date is not None and entry.next_review_date <= today:
        return True
    return False


def _packet_item_ids_from_html(html_path: Path) -> list[str] | None:
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError:
        return None
    parser = _PacketItemIdParser()
    try:
        parser.feed(html)
    except Exception:
        return None
    return list(dict.fromkeys(parser.item_ids))


def _fresh_qa_packet_paths(paths: CoursePaths, *, packet_type: str, day_index: int) -> tuple[Path, Path, str]:
    if packet_type == "recall":
        return (
            paths.recall_packet_html_file(day_index=day_index),
            paths.daily_dir / f"day_{day_index:02d}_recall.md",
            f"/packets/recall/day/{day_index}",
        )
    return (
        paths.learning_packet_html_file(day_index=day_index),
        paths.daily_dir / f"day_{day_index:02d}_learning.md",
        f"/packets/learning/day/{day_index}",
    )


def _item_phase1_context(item: Item) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "block_id": item.block_id,
        "prompt": item.prompt,
        "answer_mode": item.answer_mode,
        "difficulty": item.difficulty,
        "exam_relevance": item.exam_relevance,
        "needs_visuals": item.needs_visuals,
        "learning_note": item.learning_note,
        "retrieval_cues": list(item.retrieval_cues),
    }


def _visual_payload(visual: VisualRequirement) -> dict[str, Any]:
    return {
        "item_id": visual.item_id,
        "block_id": visual.block_id,
        "description": visual.description,
        "required_image": visual.required_image,
        "status": visual.status,
    }


def _item_phase2_context(item: Item, visuals: list[VisualRequirement]) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "block_id": item.block_id,
        "prompt": item.prompt,
        "answer_mode": item.answer_mode,
        "difficulty": item.difficulty,
        "exam_relevance": item.exam_relevance,
        "needs_visuals": item.needs_visuals,
        "answer_key": item.answer_key,
        "rubric": item.rubric,
        "common_mistakes": list(item.common_mistakes),
        "model_answer": item.model_answer,
        "worked_example": item.worked_example,
        "correction_ladder": list(item.correction_ladder),
        "source_refs": list(item.source_refs),
        "visual_requirements": [
            _visual_payload(visual)
            for visual in visuals
            if visual.item_id == item.item_id
        ],
    }


class StudyEngine:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def list_active_course_slugs(self) -> list[str]:
        courses_root = self.workspace_root / "courses"
        if not courses_root.exists():
            return []
        return sorted(
            path.name
            for path in courses_root.iterdir()
            if path.is_dir() and (path / "course.yaml").exists()
        )

    def initialize_course(self, payload: dict[str, Any], *, validate_sources: bool = False) -> ExecutionReceipt:
        request = validate_init_course_request(payload)
        if validate_sources:
            validate_source_files(self.workspace_root, request.source_manifest, request.visual_requirements)
        paths = build_course_paths(self.workspace_root, request.course.course_slug)
        if paths.outputs_dir.exists():
            shutil.rmtree(paths.outputs_dir)
        paths.ensure_directories()
        store = CourseStore(paths)

        for log_file in (paths.error_log_file, paths.session_history_file):
            if log_file.exists():
                log_file.unlink()

        store.save_course(request.course)
        store.save_blocks(request.blocks)
        store.save_items(request.items)
        store.save_source_manifest(request.source_manifest)
        store.save_visual_requirements(request.visual_requirements)
        store.save_mastery(
            {
                item.item_id: asdict(MasteryRecord(item_id=item.item_id, block_id=item.block_id))
                for item in request.items
            }
        )
        store.save_review_queue([])

        paths.master_plan_file.write_text(
            build_master_plan(request.course, request.blocks, request.items),
            encoding="utf-8",
        )
        self._refresh_workspace_md()

        return ExecutionReceipt(
            status="applied",
            applied_items=[item.item_id for item in request.items],
            held_items=[],
            generated_files=[
                str(paths.course_file),
                str(paths.blocks_file),
                str(paths.items_file),
                str(paths.source_manifest_file),
                str(paths.visual_requirements_file),
                str(paths.mastery_file),
                str(paths.review_queue_file),
                str(paths.master_plan_file),
                str(paths.workspace_file),
            ],
            warnings=[],
        )

    def start_day(self, course_slug: str, *, day_index: int, today: str) -> ExecutionReceipt:
        validate_positive_day_index(day_index)
        validate_iso_date_text(today, "today")
        validate_course_slug_text(course_slug)

        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")
        paths.ensure_directories()
        store = CourseStore(paths)

        course = CourseConfig(**store.load_course())
        blocks = [Block(**payload) for payload in store.load_blocks()]
        items = [Item(**payload) for payload in store.load_items()]
        visuals = [VisualRequirement(**payload) for payload in store.load_visual_requirements()]
        review_queue = [QueueEntry(**payload) for payload in store.load_review_queue()]

        items_by_block: dict[str, list[Item]] = {}
        for item in items:
            items_by_block.setdefault(item.block_id, []).append(item)
        items_by_id = {item.item_id: item for item in items}

        sorted_blocks = sorted(blocks, key=_block_schedule_key)
        start_index = max(day_index - 1, 0) * _NEW_BLOCKS_PER_DAY
        selected_blocks = sorted_blocks[start_index:start_index + _NEW_BLOCKS_PER_DAY]
        due_review_entries = [
            entry for entry in review_queue if _review_entry_is_due(entry, day_index=day_index, today=today)
        ]

        selected_block_ids = {block.block_id for block in selected_blocks}
        due_review_item_ids = {entry.item_id for entry in due_review_entries}
        selected_visuals = [
            visual
            for visual in visuals
            if visual.block_id in selected_block_ids or visual.item_id in due_review_item_ids
        ]

        learning_file = paths.daily_dir / f"day_{day_index:02d}_learning.md"
        recall_file = paths.daily_dir / f"day_{day_index:02d}_recall.md"
        packet_progress = store.load_packet_progress()
        learning_model = build_learning_packet_model(
            course,
            day_index,
            selected_blocks,
            items_by_block,
            selected_visuals,
            today=today,
            progress_by_item=_checked_progress_for(packet_progress, packet_type="learning", day_index=day_index),
        )
        recall_model = build_recall_packet_model(
            course,
            day_index,
            due_review_entries,
            items_by_id,
            selected_visuals,
            today=today,
            progress_by_item=_checked_progress_for(packet_progress, packet_type="recall", day_index=day_index),
            new_items=[item for block in selected_blocks for item in items_by_block.get(block.block_id, [])],
        )
        packet_links = _daily_packet_links(day_index)
        learning_html_file = paths.learning_packet_html_file(day_index=day_index)
        recall_html_file = paths.recall_packet_html_file(day_index=day_index)
        learning_html_file.write_text(
            render_packet_html(learning_model, packet_links=packet_links),
            encoding="utf-8",
        )
        recall_html_file.write_text(
            render_packet_html(recall_model, packet_links=packet_links),
            encoding="utf-8",
        )
        learning_file.write_text(
            build_learning_packet(course, day_index, selected_blocks, items_by_block, selected_visuals, today=today),
            encoding="utf-8",
        )
        recall_file.write_text(
            build_recall_packet(
                course,
                day_index,
                due_review_entries,
                items_by_id,
                selected_visuals,
                today=today,
                new_items=[item for block in selected_blocks for item in items_by_block.get(block.block_id, [])],
            ),
            encoding="utf-8",
        )

        updated_course = asdict(course)
        updated_course["current_day"] = day_index
        store.save_course(updated_course)

        applied_items = list(dict.fromkeys(
            [item.item_id for item in items if item.block_id in selected_block_ids]
            + [entry.item_id for entry in due_review_entries]
        ))

        return ExecutionReceipt(
            status="applied",
            applied_items=applied_items,
            held_items=[],
            generated_files=[
                str(paths.course_file),
                str(learning_html_file),
                str(recall_html_file),
                str(learning_file),
                str(recall_file),
            ],
            warnings=[],
        )

    def build_fresh_qa_context(self, course_slug: str, *, today: str) -> dict[str, Any]:
        validate_course_slug_text(course_slug)
        validate_iso_date_text(today, "today")

        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")

        store = CourseStore(paths)
        course = CourseConfig(**store.load_course())
        items = [Item(**payload) for payload in store.load_items()]
        visuals = [VisualRequirement(**payload) for payload in store.load_visual_requirements()]
        review_queue = [QueueEntry(**payload) for payload in store.load_review_queue()]

        day_index = course.current_day
        due_entries = [
            entry
            for entry in review_queue
            if day_index > 0 and _review_entry_is_due(entry, day_index=day_index, today=today)
        ]
        due_entries.sort(
            key=lambda entry: (
                _PRIORITY_ORDER.get(entry.priority, len(_PRIORITY_ORDER)),
                entry.next_review_date or "",
                entry.item_id,
            )
        )
        review_pressure = {
            "due_count": len(due_entries),
            "urgent_count": sum(1 for entry in due_entries if entry.priority == "urgent"),
            "top_due_item_ids": [entry.item_id for entry in due_entries[:5]],
        }
        inspection_budget = {
            "max_items": 5,
            "selection_rules": [
                "Inspect at most five visible packet items.",
                "Phase 1 uses only selected packet content before grading materials are revealed.",
                "Phase 2 grades only items visible in the selected packet.",
                "Do not inspect unrelated course items to fill gaps.",
            ],
        }

        if day_index <= 0:
            return {
                "course_slug": course_slug,
                "today": today,
                "current_day": day_index,
                "next_action": {
                    "kind": "generate_day",
                    "label": "Generate today's study day",
                    "reason": "course.current_day is not initialized yet",
                },
                "selected_packet": {
                    "packet_type": None,
                    "day_index": None,
                    "html_path": None,
                    "markdown_path": None,
                    "url_path": None,
                    "exists": False,
                    "openable": False,
                },
                "review_pressure": review_pressure,
                "inspection_budget": inspection_budget,
                "phase1_context": self._fresh_qa_phase1_context(
                    packet_item_ids=[],
                    selected_packet={},
                ),
                "phase2_context": {"items": []},
                "result_contract": self._fresh_qa_result_contract(),
            }

        packet_type = "recall" if due_entries else "learning"
        html_path, markdown_path, url_path = _fresh_qa_packet_paths(
            paths,
            packet_type=packet_type,
            day_index=day_index,
        )
        packet_exists = html_path.exists() or markdown_path.exists()
        packet_openable = html_path.is_file()
        selected_packet = {
            "packet_type": packet_type,
            "day_index": day_index,
            "html_path": str(html_path),
            "markdown_path": str(markdown_path),
            "url_path": url_path,
            "exists": packet_exists,
            "openable": packet_openable,
        }

        packet_item_ids = _packet_item_ids_from_html(html_path)
        if packet_item_ids is None:
            packet_item_ids = [entry.item_id for entry in due_entries] if packet_type == "recall" else []
        packet_item_ids = packet_item_ids[: inspection_budget["max_items"]]

        items_by_id = {item.item_id: item for item in items}
        selected_items = [
            items_by_id[item_id]
            for item_id in packet_item_ids
            if item_id in items_by_id
        ]

        if packet_openable:
            next_action = {
                "kind": "open_packet",
                "label": f"Open day {day_index} {packet_type} packet",
                "reason": (
                    "due review items are ready for recall"
                    if packet_type == "recall"
                    else "no due review items; continue current-day learning"
                ),
            }
        else:
            next_action = {
                "kind": "packet_blocked",
                "label": f"Regenerate missing day {day_index} {packet_type} packet",
                "reason": "selected packet is missing or not openable; do not fall back to another packet type",
            }

        return {
            "course_slug": course_slug,
            "today": today,
            "current_day": day_index,
            "next_action": next_action,
            "selected_packet": selected_packet,
            "review_pressure": review_pressure,
            "inspection_budget": inspection_budget,
            "phase1_context": self._fresh_qa_phase1_context(
                packet_item_ids=packet_item_ids,
                selected_packet=selected_packet,
                items=selected_items,
            ),
            "phase2_context": {
                "items": [_item_phase2_context(item, visuals) for item in selected_items],
            },
            "result_contract": self._fresh_qa_result_contract(),
        }

    def build_close_session_draft(
        self,
        course_slug: str,
        *,
        packet_type: str,
        day_index: int | None,
        session_date: str,
    ) -> dict[str, Any]:
        validate_course_slug_text(course_slug)
        validate_iso_date_text(session_date, "session_date")

        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")

        store = CourseStore(paths)
        items_by_id = {row["item_id"]: Item(**row) for row in store.load_items()}
        packet_progress = store.load_packet_progress()
        return build_close_session_draft(
            course_slug=course_slug,
            session_date=session_date,
            packet_type=packet_type,
            day_index=day_index,
            packet_progress=packet_progress,
            items_by_id=items_by_id,
        )

    def close_session(self, payload: dict[str, Any]) -> ExecutionReceipt:
        request_shape = validate_close_session_request_shape(payload)
        paths = build_course_paths(self.workspace_root, request_shape.course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {request_shape.course_slug}")
        store = CourseStore(paths)

        items = [Item(**row) for row in store.load_items()]
        blocks = [Block(**row) for row in store.load_blocks()]
        visuals = [VisualRequirement(**row) for row in store.load_visual_requirements()]
        pending_visuals = _pending_visual_requirements(visuals)
        request = validate_close_session_request(payload, {item.item_id for item in items})

        course = CourseConfig(**store.load_course())
        mastery = store.load_mastery()
        item_by_id = {item.item_id: item for item in items}
        block_by_id = {block.block_id: block for block in blocks}

        recent_error_codes: dict[str, list[str]] = {}
        for error in store.load_errors():
            item_id = error.get("item_id")
            error_code = error.get("error_code")
            if isinstance(item_id, str) and isinstance(error_code, str):
                recent_error_codes.setdefault(item_id, []).append(error_code)

        applied_items: list[str] = []
        held_items: list[str] = []
        warnings: list[str] = []
        wrote_error_row = False
        for reviewed in request.reviewed_items:
            item = item_by_id[reviewed.item_id]
            unresolved_visual = item.needs_visuals and any(
                visual.item_id == reviewed.item_id
                for visual in pending_visuals
            )
            current = MasteryRecord(
                **mastery.get(
                    reviewed.item_id,
                    asdict(MasteryRecord(item_id=item.item_id, block_id=item.block_id)),
                )
            )
            updated = apply_review_update(current, reviewed, request.session_date)
            if self._should_hold_visual_gated_promotion(current, updated, reviewed.phase, unresolved_visual):
                updated = replace(updated, status=current.status)
                held_items.append(reviewed.item_id)
                warnings.append(
                    f"Held promotion for {reviewed.item_id} because required visual is still missing."
                )
            mastery[reviewed.item_id] = asdict(updated)
            applied_items.append(reviewed.item_id)

            if reviewed.result == "wrong" or reviewed.error_code is not None:
                error_code = reviewed.error_code or "C1"
                store.append_error(
                    {
                        "date": request.session_date,
                        "block_id": updated.block_id,
                        "item_id": reviewed.item_id,
                        "error_code": error_code,
                        "confidence": reviewed.confidence,
                        "note": reviewed.note,
                    }
                )
                recent_error_codes.setdefault(reviewed.item_id, []).append(error_code)
                wrote_error_row = True

        current_day = request.day_index if request.day_index is not None else course.current_day
        rebuilt_queue: list[dict[str, Any]] = []
        for item_id in sorted(mastery):
            record = MasteryRecord(**mastery[item_id])
            item = item_by_id[item_id]
            block = block_by_id[item.block_id]
            unresolved_visual = any(
                visual.item_id == item_id
                for visual in pending_visuals
            )
            queue_entry = build_queue_entry(
                record,
                item,
                block,
                course.exam_date,
                request.session_date,
                current_day=current_day,
                recent_error_codes=recent_error_codes.get(item_id, [])[-3:],
                unresolved_visual=unresolved_visual,
            )
            if queue_entry is not None:
                rebuilt_queue.append(asdict(queue_entry))

        rebuilt_queue.sort(
            key=lambda row: (
                _PRIORITY_ORDER.get(row["priority"], len(_PRIORITY_ORDER)),
                row["next_review_date"] or "",
                row["item_id"],
            )
        )

        store.save_mastery(mastery)
        store.save_review_queue(rebuilt_queue)
        store.append_session_history(
            {
                "course_slug": request.course_slug,
                "session_date": request.session_date,
                "day_index": request.day_index,
                "status": "applied",
                "applied_items": applied_items,
                "held_items": held_items,
                "warnings": warnings,
            }
        )

        generated_files = [
            str(paths.mastery_file),
            str(paths.review_queue_file),
            str(paths.session_history_file),
        ]
        if wrote_error_row:
            generated_files.append(str(paths.error_log_file))

        return ExecutionReceipt(
            status="applied",
            applied_items=applied_items,
            held_items=held_items,
            generated_files=generated_files,
            warnings=warnings,
        )

    def start_final_recall(self, course_slug: str, *, today: str) -> ExecutionReceipt:
        validate_iso_date_text(today, "today")
        validate_course_slug_text(course_slug)

        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")

        store = CourseStore(paths)
        course = CourseConfig(**store.load_course())
        blocks = {row["block_id"]: Block(**row) for row in store.load_blocks()}
        items = {row["item_id"]: Item(**row) for row in store.load_items()}
        visuals = [VisualRequirement(**row) for row in store.load_visual_requirements()]
        queue = [QueueEntry(**row) for row in store.load_review_queue()]

        ranked_queue = sorted(
            queue,
            key=lambda entry: (
                _PRIORITY_ORDER.get(entry.priority, len(_PRIORITY_ORDER)),
                entry.next_review_date or "",
                entry.item_id,
            ),
        )
        relevant_item_ids = {entry.item_id for entry in ranked_queue}
        ranked_visuals = [visual for visual in visuals if visual.item_id in relevant_item_ids]
        packet_progress = store.load_packet_progress()
        final_model = build_final_recall_packet_model(
            course,
            ranked_queue,
            items,
            blocks,
            ranked_visuals,
            today=today,
            progress_by_item=_checked_progress_for(packet_progress, packet_type="final_recall", day_index=None),
        )

        paths.final_recall_html_file.write_text(
            render_packet_html(final_model, packet_links={"final_recall": "/packets/final-recall"}),
            encoding="utf-8",
        )
        paths.final_recall_file.write_text(
            build_final_recall_pack(course, ranked_queue, items, blocks, ranked_visuals, today=today),
            encoding="utf-8",
        )

        return ExecutionReceipt(
            status="applied",
            applied_items=[entry.item_id for entry in ranked_queue],
            held_items=[],
            generated_files=[str(paths.final_recall_html_file), str(paths.final_recall_file)],
            warnings=[],
        )

    def status(self, course_slug: str) -> str:
        validate_course_slug_text(course_slug)
        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")

        store = CourseStore(paths)
        mastery = store.load_mastery()
        packet_progress = store.load_packet_progress()
        checked_packet_entries = sum(
            1
            for packet_items in packet_progress.values()
            for item_progress in packet_items.values()
            if item_progress["checked"]
        )
        queue = [
            QueueEntry(**row)
            for row in sorted(
                store.load_review_queue(),
                key=lambda row: (
                    _PRIORITY_ORDER.get(row["priority"], len(_PRIORITY_ORDER)),
                    row["next_review_date"] or "",
                    row["item_id"],
                ),
            )
        ]

        lines = [
            f"Course: {course_slug}",
            f"Tracked items: {len(mastery)}",
            f"Queued items: {len(queue)}",
            f"Checked packet entries: {checked_packet_entries}",
            "Top queue entries:",
        ]
        if not queue:
            lines.append("- None")
        else:
            for entry in queue[:5]:
                lines.append(
                    f"- {entry.item_id} [{entry.status}] {entry.priority} -> {entry.next_review_date} ({entry.reason})"
                )
        return "\n".join(lines)

    def _refresh_workspace_md(self) -> None:
        courses_root = self.workspace_root / "courses"
        course_slugs: list[str] = []
        if courses_root.exists():
            course_slugs = sorted(
                path.name
                for path in courses_root.iterdir()
                if path.is_dir() and (path / "course.yaml").exists()
            )

        lines = ["# Study OS Workspace", "", "## Courses"]
        if course_slugs:
            lines.extend(f"- `{course_slug}`" for course_slug in course_slugs)
        else:
            lines.append("- None")

        (self.workspace_root / "workspace.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _fresh_qa_phase1_context(
        self,
        *,
        packet_item_ids: list[str],
        selected_packet: dict[str, Any],
        items: list[Item] | None = None,
    ) -> dict[str, Any]:
        return {
            "packet": {
                "html_path": selected_packet.get("html_path"),
                "markdown_path": selected_packet.get("markdown_path"),
                "url_path": selected_packet.get("url_path"),
            },
            "instructions": [
                "Attempt answers from the selected packet only.",
                "Do not inspect answer keys, rubrics, common mistakes, model answers, worked examples, or source references.",
                "Record blockers that prevent answering from visible packet content.",
            ],
            "packet_item_ids": list(packet_item_ids),
            "items": [_item_phase1_context(item) for item in (items or [])],
        }

    def _fresh_qa_result_contract(self) -> dict[str, Any]:
        return {
            "required_fields": list(REQUIRED_FIELDS),
            "axes": list(FRESH_QA_AXES),
            "axis_values": list(AXIS_VALUES),
            "gate_values": list(GATES),
        }

    def _should_hold_visual_gated_promotion(
        self,
        current: MasteryRecord,
        updated: MasteryRecord,
        phase: str,
        unresolved_visual: bool,
    ) -> bool:
        if phase != "review" or not unresolved_visual:
            return False
        return STATUS_ORDER.index(updated.status) > STATUS_ORDER.index(current.status)
