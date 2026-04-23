from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from study_os.core.engine import StudyEngine
from study_os.core.validation import ValidationError


COMMAND_HELP = {
    "init-course": "Write a validated course snapshot from a request file.",
    "start-day": "Generate daily learning and recall packets for a course.",
    "close-session": "Apply a validated session update request.",
    "start-final-recall": "Generate the exam-near final recall pack.",
    "status": "Show a compact course status summary.",
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


def _print_receipt(receipt: Any, *, include_close_session_holds: bool = False) -> None:
    print(receipt.status)
    if include_close_session_holds:
        for warning in receipt.warnings:
            print(f"warning: {warning}")
        for item_id in receipt.held_items:
            print(f"held-item: {item_id}")
    for path in receipt.generated_files:
        print(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="study_os")
    parser.add_argument("--workspace", default=".")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init-course", help=COMMAND_HELP["init-course"])
    init_parser.add_argument("--request-file", required=True)

    start_day_parser = subparsers.add_parser("start-day", help=COMMAND_HELP["start-day"])
    start_day_parser.add_argument("--course", required=True)
    start_day_parser.add_argument("--day", required=True, type=int)
    start_day_parser.add_argument("--today", required=True)

    close_session_parser = subparsers.add_parser("close-session", help=COMMAND_HELP["close-session"])
    close_session_parser.add_argument("--request-file", required=True)

    final_recall_parser = subparsers.add_parser("start-final-recall", help=COMMAND_HELP["start-final-recall"])
    final_recall_parser.add_argument("--course", required=True)
    final_recall_parser.add_argument("--today", required=True)

    status_parser = subparsers.add_parser("status", help=COMMAND_HELP["status"])
    status_parser.add_argument("--course", required=True)

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

    engine = StudyEngine(Path(parsed.workspace))
    try:
        if parsed.command == "init-course":
            receipt = engine.initialize_course(_load_request_file(parsed.request_file))
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

        if parsed.command == "start-final-recall":
            receipt = engine.start_final_recall(parsed.course, today=parsed.today)
            _print_receipt(receipt)
            return 0

        if parsed.command == "status":
            print(engine.status(parsed.course))
            return 0
    except (ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0
