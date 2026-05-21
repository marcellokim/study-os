from __future__ import annotations

from study_os.core.models import Block, CourseConfig, Item, QueueEntry, VisualRequirement
from study_os.core.packet_models import PacketEntry, PacketPage, PacketSection, PacketVisual
from study_os.core.risk_ranking import queue_entry_exam_risk_key


_FALLBACK_ORDER = 10**9
_EMPTY_PROGRESS: dict[str, object] = {}


def _block_sort_key(block: Block) -> tuple[bool, int, str, str]:
    return (block.study_order is None, block.study_order or _FALLBACK_ORDER, block.block_name, block.block_id)


def _item_sort_key(item: Item) -> tuple[str, str]:
    return (item.item_id, item.prompt)


def _visual_sort_key(visual: VisualRequirement) -> tuple[str, str, str, str]:
    return (visual.block_id, visual.item_id, visual.required_image, visual.description)


def _queue_entry_sort_key(entry: QueueEntry) -> tuple[bool, int, str, str, str, str, str, str]:
    return (
        entry.next_review_day is None,
        entry.next_review_day if entry.next_review_day is not None else _FALLBACK_ORDER,
        entry.next_review_date or "",
        entry.block_id,
        entry.item_id,
        entry.status,
        entry.priority,
        entry.reason,
    )


def _visuals_for(visuals: list[VisualRequirement]) -> list[PacketVisual]:
    return [
        PacketVisual(
            item_id=visual.item_id,
            required_image=visual.required_image,
            description=visual.description,
            status=visual.status,
        )
        for visual in sorted(visuals, key=_visual_sort_key)
    ]


def _entry_from_item(
    item: Item,
    *,
    progress: bool | dict[str, object] | None,
    priority: str | None = None,
    reason: str | None = None,
) -> PacketEntry:
    if isinstance(progress, dict):
        checked = bool(progress.get("checked", False))
        draft_answer = progress.get("draft_answer")
        result = progress.get("result")
        confidence = progress.get("confidence")
        confidence_score = progress.get("confidence_score")
        blocker_type = progress.get("blocker_type")
    else:
        checked = bool(progress)
        draft_answer = None
        result = None
        confidence = None
        confidence_score = None
        blocker_type = None
    return PacketEntry(
        item_id=item.item_id,
        block_id=item.block_id,
        prompt=item.prompt,
        checked=checked,
        draft_answer=draft_answer if isinstance(draft_answer, str) else None,
        result=result if isinstance(result, str) else None,
        confidence=confidence if isinstance(confidence, str) else None,
        confidence_score=confidence_score if isinstance(confidence_score, int) else None,
        blocker_type=blocker_type if isinstance(blocker_type, str) else None,
        priority=priority,
        reason=reason,
        learning_note=item.learning_note or None,
        retrieval_cues=list(item.retrieval_cues),
        answer_key=item.answer_key or None,
        rubric=item.rubric or None,
        common_mistakes=list(item.common_mistakes),
        model_answer=item.model_answer or None,
        worked_example=item.worked_example or None,
        correction_ladder=list(item.correction_ladder),
        source_refs=list(item.source_refs),
    )


def _actions_section(section_id: str, title: str, helper_text: str | None, checklist_items: list[str]) -> PacketSection:
    return PacketSection(
        section_id=section_id,
        title=title,
        helper_text=helper_text,
        checklist_items=checklist_items,
    )


def build_learning_packet_model(
    course: CourseConfig,
    day_index: int,
    blocks: list[Block],
    items_by_block: dict[str, list[Item]],
    visuals: list[VisualRequirement],
    today: str | None,
    progress_by_item: dict[str, bool | dict[str, object]],
) -> PacketPage:
    entries = [
        _entry_from_item(item, progress=progress_by_item.get(item.item_id, _EMPTY_PROGRESS))
        for block in sorted(blocks, key=_block_sort_key)
        for item in sorted(items_by_block.get(block.block_id, []), key=_item_sort_key)
    ]
    return PacketPage(
        packet_type="learning",
        page_title=f"Day {day_index:02d} 학습 패킷",
        course_slug=course.course_slug,
        course_name=course.course_name,
        day_index=day_index,
        generated_date=today,
        summary_text="노트를 보기 전에 먼저 답하고 체크 상태는 실행 흔적만 기록한다.",
        sections=[
            _actions_section(
                section_id="actions",
                title="첫 행동",
                helper_text="학습 카드를 보기 전에 먼저 회상하고 실행 흔적만 남긴다.",
                checklist_items=[
                    "노트와 정답을 가리고 먼저 답한다.",
                    "답안을 소리 내어 설명하고 자기설명 한 문장을 남긴다.",
                    "빠진 조건을 표시하고 correction ladder로 즉시 교정한다.",
                ],
            ),
            PacketSection(
                section_id="items",
                title="문항별 학습 카드",
                empty_state_text=(
                    "오늘 새 학습 문항이 없습니다. 복습 패킷으로 이동해 위험 문항을 먼저 처리하세요."
                    if not entries
                    else None
                ),
                entries=entries,
            ),
            PacketSection(section_id="visuals", title="필요한 시각자료", visual_requirements=_visuals_for(visuals)),
        ],
    )


def build_recall_packet_model(
    course: CourseConfig,
    day_index: int,
    queue_entries: list[QueueEntry],
    items_by_id: dict[str, Item],
    visuals: list[VisualRequirement],
    today: str | None,
    progress_by_item: dict[str, bool | dict[str, object]],
    new_items: list[Item],
) -> PacketPage:
    entries = [
        _entry_from_item(
            items_by_id[queue_entry.item_id],
            progress=progress_by_item.get(queue_entry.item_id, _EMPTY_PROGRESS),
            priority=queue_entry.priority,
            reason=queue_entry.reason,
        )
        for queue_entry in sorted(queue_entries, key=queue_entry_exam_risk_key)
    ]
    same_day_r0_entries = [
        _entry_from_item(item, progress=progress_by_item.get(item.item_id, _EMPTY_PROGRESS))
        for item in sorted(new_items, key=_item_sort_key)
    ]
    return PacketPage(
        packet_type="recall",
        page_title=f"Day {day_index:02d} 복습 패킷",
        course_slug=course.course_slug,
        course_name=course.course_name,
        day_index=day_index,
        generated_date=today,
        summary_text="복습 체크는 실행 흔적이며 판정은 close-session에서 확정한다.",
        sections=[
            _actions_section(
                section_id="actions",
                title="즉시 회상",
                helper_text="직접 답한 뒤 채점하고 최종 판정은 close-session에서 확정한다.",
                checklist_items=[
                    "별도 답안을 먼저 작성하고 채팅으로 설명하지 않는다.",
                    "정답 기준과 rubric으로 채점한다.",
                    "같은 날 새 문항은 R0 교정을 끝낼 때까지 다시 푼다.",
                ],
            ),
            PacketSection(
                section_id="queue",
                title="복습 문항",
                empty_state_text=(
                    "아직 마감된 복습 문항이 없습니다. 신규 학습 후 당일 회상을 실행하세요."
                    if not entries
                    else None
                ),
                entries=entries,
            ),
            PacketSection(
                section_id="same_day_r0",
                title="당일 R0 회상",
                helper_text="새로 배운 문항은 같은 날 한 번 더 회상해 교정한다.",
                empty_state_text="오늘 새로 배운 문항이 없습니다." if not same_day_r0_entries else None,
                entries=same_day_r0_entries,
            ),
            PacketSection(section_id="visuals", title="시각자료 게이트", visual_requirements=_visuals_for(visuals)),
        ],
    )


def build_final_recall_packet_model(
    course: CourseConfig,
    queue_entries: list[QueueEntry],
    items_by_id: dict[str, Item],
    blocks_by_id: dict[str, Block],
    visuals: list[VisualRequirement],
    today: str | None,
    progress_by_item: dict[str, bool | dict[str, object]],
) -> PacketPage:
    del blocks_by_id
    entries = [
        _entry_from_item(
            items_by_id[queue_entry.item_id],
            progress=progress_by_item.get(queue_entry.item_id, _EMPTY_PROGRESS),
            priority=queue_entry.priority,
            reason=queue_entry.reason,
        )
        for queue_entry in sorted(queue_entries, key=queue_entry_exam_risk_key)
    ]
    return PacketPage(
        packet_type="final_recall",
        page_title="최종 회상 팩",
        course_slug=course.course_slug,
        course_name=course.course_name,
        day_index=None,
        generated_date=today,
        summary_text="범위를 넓히지 말고 위험 문항 안정화에만 집중한다.",
        sections=[
            _actions_section(
                section_id="actions",
                title="실수 방지 체크리스트",
                helper_text="시험 전에는 범위를 넓히지 않고 기억 안정화에만 집중한다.",
                checklist_items=[
                    "기억만으로 먼저 답하고 범위를 넓히지 않는다.",
                    "헷갈리는 쌍은 소리 내어 비교한다.",
                    "이미지 의존 문항은 참조 이미지를 확보하기 전 승급하지 않는다.",
                ],
            ),
            PacketSection(section_id="risks", title="최고 위험 문항", entries=entries),
            PacketSection(section_id="visuals", title="필요한 시각자료", visual_requirements=_visuals_for(visuals)),
        ],
    )
