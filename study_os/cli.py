from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from study_os.core.engine import StudyEngine
from study_os.core.fresh_qa import render_daily_fresh_qa_report
from study_os.core.packet_server import PacketServer, validate_close_session_draft_params
from study_os.core.paths import build_course_paths
from study_os.core.validation import ValidationError, validate_course_slug_text


COMMAND_HELP = {
    "init-course": "Write a validated course snapshot from a request file.",
    "start-day": "Generate daily learning and recall packets for a course.",
    "close-session": "Apply a validated session update request.",
    "draft-close-session": "Build a close-session request draft from saved packet progress.",
    "start-final-recall": "Generate the exam-near final recall pack.",
    "status": "Show a compact course status summary.",
    "serve-packets": "Serve HTML packets and immediate packet-progress writes for a course.",
    "fresh-qa-context": "Print next-packet context for daily fresh black-box QA.",
    "fresh-qa-report": "Validate fresh QA result JSON and render a Korean daily report.",
}


def _load_request_file(path: str) -> dict[str, Any]:
    request_path = Path(path)
    try:
        raw_text = request_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"request file not found: {request_path}") from exc
    except OSError as exc:
        raise ValidationError(f"request file could not be read: {request_path}") from exc

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"request file is not valid JSON: {request_path}") from exc


def _load_fresh_qa_results(path: str) -> list[dict[str, Any]]:
    result_path = Path(path)
    try:
        raw_text = result_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"fresh QA result file not found: {result_path}") from exc
    except OSError as exc:
        raise ValidationError(f"fresh QA result file could not be read: {result_path}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"fresh QA result file is not valid JSON: {result_path}") from exc

    if isinstance(payload, list):
        results = payload
    elif isinstance(payload, dict) and "results" in payload:
        results = payload["results"]
    elif isinstance(payload, dict):
        results = [payload]
    else:
        raise ValidationError("fresh QA result file must contain an object, a list, or {'results': [...]}")

    if not isinstance(results, list):
        raise ValidationError("fresh QA result file 'results' must be a list")
    if not all(isinstance(result, dict) for result in results):
        raise ValidationError("fresh QA result entries must be objects")
    return results


def _fresh_qa_context_for_phase(context: dict[str, Any], phase: str) -> dict[str, Any]:
    if phase == "all":
        return context
    filtered = dict(context)
    if phase == "phase1":
        filtered.pop("phase2_context", None)
    else:
        raise ValidationError(f"unknown fresh QA phase: {phase}")
    filtered["context_phase"] = phase
    return filtered


def _print_receipt(receipt: Any, *, include_close_session_holds: bool = False) -> None:
    print(receipt.status)
    if include_close_session_holds:
        for warning in receipt.warnings:
            print(f"warning: {warning}")
        for item_id in receipt.held_items:
            print(f"held-item: {item_id}")
    for path in receipt.generated_files:
        print(path)


def _validate_existing_course(workspace_root: Path, course_slug: str) -> None:
    validate_course_slug_text(course_slug)
    paths = build_course_paths(workspace_root, course_slug)
    if not paths.course_file.exists():
        raise ValidationError(f"unknown course_slug: {course_slug}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="study_os")
    parser.add_argument("--workspace", default=".")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init-course", help=COMMAND_HELP["init-course"])
    init_parser.add_argument("--request-file", required=True)
    init_parser.add_argument(
        "--validate-sources",
        action="store_true",
        help="Require source_manifest files and available visual files to exist under the workspace.",
    )

    start_day_parser = subparsers.add_parser("start-day", help=COMMAND_HELP["start-day"])
    start_day_parser.add_argument("--course", required=True)
    start_day_parser.add_argument("--day", required=True, type=int)
    start_day_parser.add_argument("--today", required=True)

    close_session_parser = subparsers.add_parser("close-session", help=COMMAND_HELP["close-session"])
    close_session_parser.add_argument("--request-file", required=True)

    draft_close_session_parser = subparsers.add_parser(
        "draft-close-session",
        help=COMMAND_HELP["draft-close-session"],
    )
    draft_close_session_parser.add_argument("--course", required=True)
    draft_close_session_parser.add_argument(
        "--packet-type",
        required=True,
        choices=["learning", "recall", "final_recall"],
    )
    draft_close_session_parser.add_argument("--day", type=int)
    draft_close_session_parser.add_argument("--session-date", required=True)

    final_recall_parser = subparsers.add_parser("start-final-recall", help=COMMAND_HELP["start-final-recall"])
    final_recall_parser.add_argument("--course", required=True)
    final_recall_parser.add_argument("--today", required=True)

    status_parser = subparsers.add_parser("status", help=COMMAND_HELP["status"])
    status_parser.add_argument("--course", required=True)

    serve_parser = subparsers.add_parser("serve-packets", help=COMMAND_HELP["serve-packets"])
    serve_parser.add_argument("--course", required=True)
    serve_parser.add_argument("--port", type=int, default=8765)

    fresh_qa_context_parser = subparsers.add_parser(
        "fresh-qa-context",
        help=COMMAND_HELP["fresh-qa-context"],
    )
    fresh_qa_context_parser.add_argument("--today", required=True)
    fresh_qa_context_parser.add_argument("--course")
    fresh_qa_context_parser.add_argument(
        "--phase",
        choices=["phase1", "all"],
        default="phase1",
        help="Print only the learner-visible Phase 1 context by default; use all only for trusted orchestration.",
    )

    fresh_qa_report_parser = subparsers.add_parser(
        "fresh-qa-report",
        help=COMMAND_HELP["fresh-qa-report"],
    )
    fresh_qa_report_parser.add_argument("--result-file", required=True)
    fresh_qa_report_parser.add_argument("--today", required=True)
    fresh_qa_report_parser.add_argument(
        "--expected-course",
        action="append",
        default=[],
        help="Require one fresh QA result for this course. Defaults to active courses in --workspace when present.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = sys.argv[1:] if argv is None else argv

    if not args:
        parser.print_help()
        return 1

    parsed = parser.parse_args(args)

    if parsed.command is None:
        parser.error("a command is required")

    try:
        if parsed.command == "serve-packets":
            workspace_root = Path(parsed.workspace)
            _validate_existing_course(workspace_root, parsed.course)
            try:
                server = PacketServer(workspace_root=workspace_root, course_slug=parsed.course, port=parsed.port)
            except OSError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            print(f"http://127.0.0.1:{server.port}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                return 0
            finally:
                server.shutdown()
            return 0

        engine = StudyEngine(Path(parsed.workspace))

        if parsed.command == "init-course":
            receipt = engine.initialize_course(
                _load_request_file(parsed.request_file),
                validate_sources=parsed.validate_sources,
            )
            _print_receipt(receipt)
            return 0

        if parsed.command == "start-day":
            receipt = engine.start_day(parsed.course, day_index=parsed.day, today=parsed.today)
            _print_receipt(receipt)
            return 0

        if parsed.command == "close-session":
            receipt = engine.close_session(_load_request_file(parsed.request_file))
            _print_receipt(receipt, include_close_session_holds=True)
            return 0

        if parsed.command == "draft-close-session":
            packet_type, day_index, session_date = validate_close_session_draft_params(
                packet_type=parsed.packet_type,
                day_index=parsed.day,
                session_date=parsed.session_date,
            )
            draft = engine.build_close_session_draft(
                parsed.course,
                packet_type=packet_type,
                day_index=day_index,
                session_date=session_date,
            )
            print(json.dumps(draft, ensure_ascii=False, indent=2))
            return 0

        if parsed.command == "start-final-recall":
            receipt = engine.start_final_recall(parsed.course, today=parsed.today)
            _print_receipt(receipt)
            return 0

        if parsed.command == "status":
            print(engine.status(parsed.course))
            return 0

        if parsed.command == "fresh-qa-context":
            course_slugs = [parsed.course] if parsed.course else engine.list_active_course_slugs()
            contexts = [
                _fresh_qa_context_for_phase(
                    engine.build_fresh_qa_context(course_slug, today=parsed.today),
                    parsed.phase,
                )
                for course_slug in course_slugs
            ]
            print(json.dumps({"today": parsed.today, "courses": contexts}, ensure_ascii=False, indent=2))
            return 0

        if parsed.command == "fresh-qa-report":
            results = _load_fresh_qa_results(parsed.result_file)
            expected_course_slugs = parsed.expected_course or engine.list_active_course_slugs()
            if not expected_course_slugs:
                expected_course_slugs = None
            sys.stdout.write(
                render_daily_fresh_qa_report(
                    results,
                    today=parsed.today,
                    expected_course_slugs=expected_course_slugs,
                )
            )
            return 0
    except (ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0
