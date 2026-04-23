from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from study_os.core.models import ExecutionReceipt, MasteryRecord
from study_os.core.packets import build_master_plan
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore
from study_os.core.validation import validate_init_course_request


class StudyEngine:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def initialize_course(self, payload: dict[str, Any]) -> ExecutionReceipt:
        request = validate_init_course_request(payload)
        paths = build_course_paths(self.workspace_root, request.course.course_slug)
        paths.ensure_directories()
        store = CourseStore(paths)

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
