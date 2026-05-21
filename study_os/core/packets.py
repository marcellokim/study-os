from __future__ import annotations

from collections import Counter

from study_os.core.models import Block, CourseConfig, Item, QueueEntry, VisualRequirement
from study_os.core.risk_ranking import queue_entry_exam_risk_key


_FALLBACK_ORDER = 10**9


def _block_sort_key(block: Block) -> tuple[bool, int, str, str]:
    return (block.study_order is None, block.study_order or _FALLBACK_ORDER, block.block_name, block.block_id)


def _item_sort_key(item: Item) -> tuple[str, str]:
    return (item.item_id, item.prompt)


def _visual_sort_key(visual: VisualRequirement) -> tuple[str, str, str, str]:
    return (visual.block_id, visual.item_id, visual.required_image, visual.description)


def _has_learning_support(item: Item) -> bool:
    return bool(
        item.learning_note
        or item.answer_key
        or item.rubric
        or item.common_mistakes
        or item.model_answer
        or item.worked_example
        or item.correction_ladder
        or item.retrieval_cues
        or item.source_refs
    )


def _append_learning_execution_loop(lines: list[str]) -> None:
    lines.extend(
        [
            "## 학습 실행 루프",
            "1. 노트와 정답을 가리고 먼저 답한다.",
            "2. 답안을 소리 내어 설명하고, 왜 그런지 한 문장으로 자기설명한다.",
            "3. 대표 예제나 최종 암기 답안과 대조해 빠진 조건을 표시한다.",
            "4. 오답이면 correction ladder를 따라 같은 문항을 즉시 다시 푼다.",
            "5. 세션 끝에는 결과, 자신감, error_code, note를 `close-session` 입력으로 남긴다.",
            "",
        ]
    )


def _append_recall_verification(lines: list[str]) -> None:
    lines.extend(
        [
            "## 검증 방식",
            "- 채팅으로 설명하지 말고 먼저 별도 답안을 작성한다.",
            "- 정답 기준과 rubric으로 채점한 뒤 `correct`, `partial`, `wrong`, `uncertain` 중 하나를 고른다.",
            "- 자신감이 높았는데 틀리면 error_code를 남기고 다음 `close-session request`에 포함한다.",
            "- 부족한 문항은 같은 날 다시 풀어 R0 교정을 끝낸다.",
            "",
        ]
    )


def _append_item_support(lines: list[str], item: Item) -> None:
    lines.append(f"### `{item.item_id}`")
    lines.append(f"- 문제: {item.prompt}")
    if item.retrieval_cues:
        lines.append("- 회상 큐:")
        lines.extend(f"  - {cue}" for cue in item.retrieval_cues)
    if item.learning_note:
        lines.append(f"- 핵심 개념: {item.learning_note}")
    if item.worked_example:
        lines.append("- 대표 예제:")
        lines.extend(f"  {line}" if line else "  " for line in item.worked_example.splitlines())
    if item.answer_key:
        lines.append(f"- 정답 기준: {item.answer_key}")
    if item.model_answer:
        lines.append(f"- 최종 암기 답안: {item.model_answer}")
    if item.rubric:
        lines.append(f"- 채점 기준: {item.rubric}")
    if item.common_mistakes:
        lines.append("- 흔한 오답:")
        lines.extend(f"  - {mistake}" for mistake in item.common_mistakes)
    if item.correction_ladder:
        lines.append("- 오답 교정 ladder:")
        lines.extend(f"  {index}. {step}" for index, step in enumerate(item.correction_ladder, start=1))
    if item.source_refs:
        lines.append("- 근거:")
        lines.extend(f"  - {source_ref}" for source_ref in item.source_refs)
    lines.append("")


def build_master_plan(course: CourseConfig, blocks: list[Block], items: list[Item]) -> str:
    item_counts = Counter(item.block_id for item in items)
    supported_items = sum(1 for item in items if item.answer_key and item.rubric and item.source_refs)
    lines = [
        f"# {course.course_name} 학습 마스터 플랜",
        "",
        f"- 시험일: {course.exam_date}",
        f"- 총 블록: {len(blocks)}",
        f"- 총 문항: {len(items)}",
        f"- 정답/채점/근거 포함 문항: {supported_items}/{len(items)}",
        "",
        "## 블록 지도",
    ]
    for block in sorted(blocks, key=lambda block: (
        block.study_order is None,
        block.study_order or _FALLBACK_ORDER,
        block.importance != "high",
        block.block_name,
    )):
        lines.extend(
            [
                f"### {block.block_name} (`{block.block_id}`)",
                f"- 학습 순서: {block.study_order if block.study_order is not None else '미지정'}",
                f"- 유형: {block.block_type}",
                f"- 중요도: {block.importance}",
                f"- 난이도: {block.difficulty}",
                f"- 시험 관련도: {block.exam_relevance}",
                f"- 문항 수: {item_counts[block.block_id]}",
                "",
            ]
        )
    for item in sorted(items, key=lambda item: (item.block_id, item.item_id)):
        support = "정답/근거 있음" if item.answer_key and item.source_refs else "정답/근거 보강 필요"
        lines.append(f"- `{item.item_id}` ({support}): {item.prompt}")
    return "\n".join(lines) + "\n"


def build_learning_packet(
    course: CourseConfig,
    day_index: int,
    blocks: list[Block],
    items_by_block: dict[str, list[Item]],
    visuals: list[VisualRequirement],
    today: str | None = None,
) -> str:
    sorted_blocks = sorted(blocks, key=_block_sort_key)
    sorted_visuals = sorted(visuals, key=_visual_sort_key)
    sorted_items_by_block = {
        block.block_id: sorted(items_by_block.get(block.block_id, []), key=_item_sort_key) for block in sorted_blocks
    }

    lines = [
        f"# Day {day_index:02d} 학습 패킷 — {course.course_name}",
        "",
    ]
    if today is not None:
        lines.extend([f"- 날짜: {today}", ""])
    lines.append("## 첫 행동")
    if not sorted_blocks:
        lines.extend(
            [
                "- 오늘 새로 배울 블록이 없습니다.",
                "",
                "## 신규 블록",
                "- 없음",
                "",
                "## 필요한 시각자료",
                "- 없음",
                "",
                "## 완료 기준",
                "- 세션을 끝내기 전에 예정된 신규 블록이 없는지 확인한다.",
            ]
        )
        return "\n".join(lines) + "\n"

    first_item = next(
        (items[0] for block_id, items in sorted_items_by_block.items() if items),
        None,
    )
    if first_item is None:
        lines.append("- 오늘 예정된 문항 프롬프트가 없습니다.")
    else:
        lines.append(f"- 먼저 `{first_item.item_id}`에 답하세요: {first_item.prompt}")
    lines.append("")
    _append_learning_execution_loop(lines)
    lines.append("## 신규 블록")

    for block in sorted_blocks:
        lines.extend(
            [
                f"### {block.block_name}",
                f"- 블록 유형: {block.block_type}",
                f"- 중요도: {block.importance}",
                "- 학습 방식: 노트를 보기 전에 설명, 비교, 재구성한다.",
            ]
        )
        for item in sorted_items_by_block[block.block_id]:
            lines.append(f"- `{item.item_id}` — {item.prompt}")
        lines.append("")
    supported_items = [
        item
        for block in sorted_blocks
        for item in sorted_items_by_block[block.block_id]
        if _has_learning_support(item)
    ]
    if supported_items:
        lines.append("## 문항별 학습 카드")
        for item in supported_items:
            _append_item_support(lines, item)
    lines.append("## 필요한 시각자료")
    if sorted_visuals:
        for visual in sorted_visuals:
            lines.append(
                f"- `{visual.item_id}`: `{visual.required_image}` 필요 — {visual.description} "
                f"(status: {visual.status})"
            )
    else:
        lines.append("- 없음")
    lines.extend(["", "## 완료 기준", "- 각 신규 문항을 최소 1회 능동 회상하고, 당일 R0 복습 준비 상태로 만든다."])
    return "\n".join(lines) + "\n"


def build_recall_packet(
    course: CourseConfig,
    day_index: int,
    queue_entries: list[QueueEntry],
    items_by_id: dict[str, Item],
    visuals: list[VisualRequirement],
    today: str | None = None,
    new_items: list[Item] | None = None,
) -> str:
    sorted_queue_entries = sorted(queue_entries, key=queue_entry_exam_risk_key)
    sorted_visuals = sorted(visuals, key=_visual_sort_key)
    lines = [
        f"# Day {day_index:02d} 복습 패킷 — {course.course_name}",
        "",
    ]
    if today is not None:
        lines.extend([f"- 날짜: {today}", ""])
    lines.append("## 즉시 회상")
    if not sorted_queue_entries:
        lines.append("- 아직 마감된 복습 문항이 없습니다. 신규 학습 후 당일 회상을 실행하세요.")
    for entry in sorted_queue_entries:
        item = items_by_id[entry.item_id]
        lines.extend(
            [
                f"- `{entry.item_id}` ({entry.priority}) — {item.prompt}",
                f"  - 직전 결과: {entry.last_result}; 자신감: {entry.confidence}; 이유: {entry.reason}",
            ]
        )
        if item.retrieval_cues:
            lines.append(f"  - 회상 큐: {'; '.join(item.retrieval_cues)}")
    lines.append("")
    _append_recall_verification(lines)
    sorted_new_items = sorted(new_items or [], key=_item_sort_key)
    if sorted_new_items:
        lines.extend(
            [
                "## 당일 R0 회상",
                "- 먼저 답한 뒤 기준으로 채점하고, 부족하면 학습 패킷의 문항별 학습 카드를 다시 확인하세요.",
            ]
        )
        for item in sorted_new_items:
            lines.append(f"- `{item.item_id}` — {item.prompt}")
            if item.retrieval_cues:
                lines.append(f"  - 회상 큐: {'; '.join(item.retrieval_cues)}")
            if item.answer_key:
                lines.append(f"  - 정답 기준: {item.answer_key}")
            if item.rubric:
                lines.append(f"  - 채점 기준: {item.rubric}")
    lines.extend(["", "## 시각자료 게이트 확인"])
    if sorted_visuals:
        for visual in sorted_visuals:
            lines.append(f"- `{visual.item_id}`은/는 `{visual.required_image}` 확인 필요. status: {visual.status}")
    else:
        lines.append("- 없음")
    return "\n".join(lines) + "\n"


def build_final_recall_pack(
    course: CourseConfig,
    queue_entries: list[QueueEntry],
    items_by_id: dict[str, Item],
    blocks_by_id: dict[str, Block],
    visuals: list[VisualRequirement],
    today: str | None = None,
) -> str:
    sorted_queue_entries = sorted(queue_entries, key=queue_entry_exam_risk_key)
    sorted_visuals = sorted(visuals, key=_visual_sort_key)
    lines = [
        f"# 최종 회상 팩 — {course.course_name}",
        "",
        f"- 시험일: {course.exam_date}",
    ]
    if today is not None:
        lines.append(f"- 생성일: {today}")
    lines.extend(
        [
            "- 규칙: 범위를 넓히지 말고 회상 안정화만 수행한다.",
        "",
        "## 최고 위험 문항",
        ]
    )
    for entry in sorted_queue_entries:
        item = items_by_id[entry.item_id]
        block = blocks_by_id[entry.block_id]
        lines.append(f"- `{entry.item_id}` ({block.block_name}): {item.prompt} ({entry.reason})")
        if item.answer_key:
            lines.append(f"  - 정답 기준: {item.answer_key}")
        if item.common_mistakes:
            lines.append(f"  - 주의: {'; '.join(item.common_mistakes)}")
    lines.extend(
        [
            "",
            "## 실수 방지 체크리스트",
            "- 노트를 확인하기 전에 기억만으로 먼저 답한다.",
            "- 헷갈리는 쌍은 소리 내어 비교한다.",
            "- 이미지 의존 문항은 참조 이미지를 확보하기 전 승급하지 않는다.",
        ]
    )
    if sorted_visuals:
        lines.extend(["", "## 필요한 시각자료"])
        for visual in sorted_visuals:
            lines.append(f"- `{visual.item_id}`: `{visual.required_image}` (status: {visual.status})")
    return "\n".join(lines) + "\n"
