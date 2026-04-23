from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from study_os.core.models import Block, CourseConfig, ExecutionReceipt, Item, MasteryRecord, QueueEntry, VisualRequirement
from study_os.core.packets import build_learning_packet, build_master_plan, build_recall_packet
from study_os.core.paths import build_course_paths
from study_os.core.scheduler import build_queue_entry
from study_os.core.storage import CourseStore
from study_os.core.transitions import apply_review_update
from study_os.core.validation import ValidationError, validate_close_session_request, validate_close_session_request_shape, validate_init_course_request

_IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}
_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


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

    def start_day(self, course_slug: str, *, day_index: int, today: str) -> ExecutionReceipt:
        date.fromisoformat(today)

        paths = build_course_paths(self.workspace_root, course_slug)
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

        selected_blocks = sorted(
            blocks,
            key=lambda block: (
                _IMPORTANCE_ORDER.get(block.importance, len(_IMPORTANCE_ORDER)),
                block.block_name,
                block.block_id,
            ),
        )[:2]
        due_review_entries = [
            entry for entry in review_queue if entry.next_review_day is None or entry.next_review_day <= day_index
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
        learning_file.write_text(
            build_learning_packet(course, day_index, selected_blocks, items_by_block, selected_visuals, today=today),
            encoding="utf-8",
        )
        recall_file.write_text(
            build_recall_packet(course, day_index, due_review_entries, items_by_id, selected_visuals, today=today),
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
            generated_files=[str(paths.course_file), str(learning_file), str(recall_file)],
            warnings=[],
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
        warnings: list[str] = []
        wrote_error_row = False
        for reviewed in request.reviewed_items:
            item = item_by_id[reviewed.item_id]
            current = MasteryRecord(
                **mastery.get(
                    reviewed.item_id,
                    asdict(MasteryRecord(item_id=item.item_id, block_id=item.block_id)),
                )
            )
            updated = apply_review_update(current, reviewed, request.session_date)
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
                visual.item_id == item_id and visual.status != "available"
                for visual in visuals
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
                "held_items": [],
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
            held_items=[],
            generated_files=generated_files,
            warnings=warnings,
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
