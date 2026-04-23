from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from study_os.core.engine import StudyEngine


COMMAND_HELP = {
    "init-course": "Write a validated course snapshot from a request file.",
    "start-day": "Generate daily learning and recall packets for a course.",
    "close-session": "Apply a validated session update request.",
    "start-final-recall": "Generate the exam-near final recall pack.",
    "status": "Show a compact course status summary.",
}


def _load_request_file(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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

    for name in ("start-final-recall", "status"):
        subparsers.add_parser(name, help=COMMAND_HELP[name])

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

    if parsed.command == "init-course":
        receipt = engine.initialize_course(_load_request_file(parsed.request_file))
        print(receipt.status)
        for path in receipt.generated_files:
            print(path)
        return 0

    if parsed.command == "start-day":
        receipt = engine.start_day(parsed.course, day_index=parsed.day, today=parsed.today)
        print(receipt.status)
        for path in receipt.generated_files:
            print(path)
        return 0

    if parsed.command == "close-session":
        receipt = engine.close_session(_load_request_file(parsed.request_file))
        print(receipt.status)
        for path in receipt.generated_files:
            print(path)
        return 0

    return 0
