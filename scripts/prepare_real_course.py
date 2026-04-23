#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from study_os.core.models import Block, CourseConfig, Item, SourceLink  # noqa: E402
from study_os.core.source_files import validate_source_files  # noqa: E402
from study_os.core.validation import (  # noqa: E402
    ValidationError,
    validate_course_slug_text,
    validate_iso_date_text,
)


SOURCE_BUCKETS = (
    "syllabus",
    "slides",
    "transcripts",
    "images",
    "notes",
)
SOURCE_TYPE_BY_BUCKET = {
    "syllabus": "syllabus",
    "slides": "slides",
    "transcripts": "transcript",
    "images": "image",
    "notes": "notes",
}
IGNORED_SOURCE_FILENAMES = {".DS_Store", ".gitkeep"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a real-use Study OS course folder and init request from user-supplied source files.",
    )
    parser.add_argument("--workspace", default=".", help="Workspace root that contains courses/.")
    parser.add_argument("--course-slug", required=True, help="Lowercase course slug, e.g. os-midterm.")
    parser.add_argument("--course-name", required=True, help="Human-readable course name.")
    parser.add_argument("--exam-date", required=True, help="Exam date as YYYY-MM-DD.")
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rewrite courses/<course_slug>/init_request.json after adding or changing source files.",
    )
    return parser


def _relative_to_workspace(workspace_root: Path, path: Path) -> str:
    return path.relative_to(workspace_root).as_posix()


def _ensure_source_dirs(course_root: Path) -> None:
    for bucket in SOURCE_BUCKETS:
        course_root.joinpath("sources", bucket).mkdir(parents=True, exist_ok=True)


def _iter_user_source_files(course_root: Path) -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    for bucket in SOURCE_BUCKETS:
        bucket_dir = course_root / "sources" / bucket
        for path in sorted(bucket_dir.rglob("*")):
            is_hidden = any(part.startswith(".") for part in path.relative_to(bucket_dir).parts)
            if path.is_file() and path.name not in IGNORED_SOURCE_FILENAMES and not is_hidden:
                rows.append((bucket, path))
    return rows


def _build_payload(
    *,
    workspace_root: Path,
    course_slug: str,
    course_name: str,
    exam_date: str,
    timezone: str,
    source_files: list[tuple[str, Path]],
) -> dict:
    source_manifest = [
        SourceLink(
            block_id="source_inventory",
            source_type=SOURCE_TYPE_BY_BUCKET[bucket],
            path=_relative_to_workspace(workspace_root, path),
            note=f"User-supplied {bucket} source file.",
        )
        for bucket, path in source_files
    ]
    validate_source_files(workspace_root, source_manifest, [])

    course = CourseConfig(
        course_slug=course_slug,
        course_name=course_name,
        exam_date=exam_date,
        timezone=timezone,
    )
    blocks = [
        Block(
            block_id="source_inventory",
            block_name="Source Inventory",
            block_type="concept-definition",
            importance="high",
            difficulty="medium",
            exam_relevance="high",
            needs_prereq=False,
            needs_visuals=False,
        )
    ]
    items = [
        Item(
            item_id="source_inventory_recall",
            block_id="source_inventory",
            prompt="Review the supplied PDF/text sources and list the exam-scope concepts to decompose next.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=False,
        )
    ]

    return {
        "course": asdict(course),
        "blocks": [asdict(block) for block in blocks],
        "items": [asdict(item) for item in items],
        "source_manifest": [asdict(source) for source in source_manifest],
        "visual_requirements": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        course_slug = validate_course_slug_text(args.course_slug)
        exam_date = validate_iso_date_text(args.exam_date, "exam_date")
        workspace_root = Path(args.workspace)
        course_root = workspace_root / "courses" / course_slug
        request_file = course_root / "init_request.json"

        _ensure_source_dirs(course_root)
        if request_file.exists() and not args.overwrite:
            print(f"source folders ready: {course_root / 'sources'}")
            print(f"request already exists: {request_file}")
            print("add or replace files under sources/, then rerun with --overwrite to refresh the manifest")
            return 0

        source_files = _iter_user_source_files(course_root)
        payload = _build_payload(
            workspace_root=workspace_root,
            course_slug=course_slug,
            course_name=args.course_name,
            exam_date=exam_date,
            timezone=args.timezone,
            source_files=source_files,
        )
        request_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"source folders ready: {course_root / 'sources'}")
    print(f"source files indexed: {len(source_files)}")
    print(f"request written: {request_file}")
    print("next:")
    print(
        f"  {sys.executable} -m study_os --workspace {workspace_root} init-course "
        f"--request-file {request_file} --validate-sources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
