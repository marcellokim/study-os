from __future__ import annotations

from collections import Counter

from study_os.core.models import Block, CourseConfig, Item, QueueEntry, VisualRequirement


def build_master_plan(course: CourseConfig, blocks: list[Block], items: list[Item]) -> str:
    item_counts = Counter(item.block_id for item in items)
    lines = [
        f"# {course.course_name} Master Plan",
        "",
        f"- Exam date: {course.exam_date}",
        f"- Total blocks: {len(blocks)}",
        f"- Total items: {len(items)}",
        "",
        "## Block map",
    ]
    for block in sorted(blocks, key=lambda block: (block.importance != "high", block.block_name)):
        lines.extend(
            [
                f"### {block.block_name} (`{block.block_id}`)",
                f"- Type: {block.block_type}",
                f"- Importance: {block.importance}",
                f"- Difficulty: {block.difficulty}",
                f"- Exam relevance: {block.exam_relevance}",
                f"- Item count: {item_counts[block.block_id]}",
                "",
            ]
        )
    for item in sorted(items, key=lambda item: (item.block_id, item.item_id)):
        lines.append(f"- `{item.item_id}`: {item.prompt}")
    return "\n".join(lines) + "\n"


def build_learning_packet(
    course: CourseConfig,
    day_index: int,
    blocks: list[Block],
    items_by_block: dict[str, list[Item]],
    visuals: list[VisualRequirement],
) -> str:
    first_block = blocks[0]
    first_item = items_by_block[first_block.block_id][0]
    lines = [
        f"# Day {day_index:02d} Learning Packet — {course.course_name}",
        "",
        "## First action",
        f"- Start with `{first_item.item_id}` and answer: {first_item.prompt}",
        "",
        "## New blocks",
    ]
    for block in blocks:
        lines.extend(
            [
                f"### {block.block_name}",
                f"- Block type: {block.block_type}",
                f"- Importance: {block.importance}",
                "- Required learning behavior: explain, contrast, or reconstruct without notes before checking the source.",
            ]
        )
        for item in items_by_block[block.block_id]:
            lines.append(f"- `{item.item_id}` — {item.prompt}")
        lines.append("")
    lines.append("## Required visuals")
    if visuals:
        for visual in visuals:
            lines.append(f"- `{visual.required_image}` for `{visual.item_id}`: {visual.description}")
    else:
        lines.append("- None")
    lines.extend(["", "## Done means", "- Each new item got at least one active attempt and is ready for same-day R0 recall."])
    return "\n".join(lines) + "\n"


def build_recall_packet(
    course: CourseConfig,
    day_index: int,
    queue_entries: list[QueueEntry],
    items_by_id: dict[str, Item],
    visuals: list[VisualRequirement],
) -> str:
    lines = [
        f"# Day {day_index:02d} Recall Packet — {course.course_name}",
        "",
        "## Immediate recall",
    ]
    if not queue_entries:
        lines.append("- No due review items yet. Run same-day recall after finishing new learning.")
    for entry in queue_entries:
        item = items_by_id[entry.item_id]
        lines.extend(
            [
                f"- `{entry.item_id}` ({entry.priority}) — {item.prompt}",
                f"  - Last result: {entry.last_result}; confidence: {entry.confidence}; reason: {entry.reason}",
            ]
        )
    lines.extend(["", "## Visual gate checks"])
    if visuals:
        for visual in visuals:
            lines.append(f"- `{visual.item_id}` requires `{visual.required_image}` before promotion.")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def build_final_recall_pack(
    course: CourseConfig,
    queue_entries: list[QueueEntry],
    items_by_id: dict[str, Item],
    blocks_by_id: dict[str, Block],
    visuals: list[VisualRequirement],
) -> str:
    lines = [
        f"# Final Recall Pack — {course.course_name}",
        "",
        f"- Exam date: {course.exam_date}",
        "- Rule: no scope expansion, only recall stabilization.",
        "",
        "## Highest-risk items",
    ]
    for entry in queue_entries:
        item = items_by_id[entry.item_id]
        block = blocks_by_id[entry.block_id]
        lines.append(f"- `{entry.item_id}` in {block.block_name}: {item.prompt} ({entry.reason})")
    lines.extend(
        [
            "",
            "## Mistake-prevention checklist",
            "- Say the answer from memory before checking notes.",
            "- Compare confusing pairs out loud.",
            "- Do not promote image-dependent items without the referenced image.",
        ]
    )
    if visuals:
        lines.extend(["", "## Required visuals"])
        for visual in visuals:
            lines.append(f"- `{visual.required_image}` for `{visual.item_id}`")
    return "\n".join(lines) + "\n"
