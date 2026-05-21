from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PacketVisual:
    item_id: str
    required_image: str
    description: str
    status: str = "missing"


@dataclass(frozen=True)
class PacketEntry:
    item_id: str
    block_id: str
    prompt: str
    checked: bool = False
    draft_answer: str | None = None
    result: str | None = None
    confidence: str | None = None
    confidence_score: int | None = None
    blocker_type: str | None = None
    priority: str | None = None
    reason: str | None = None
    learning_note: str | None = None
    retrieval_cues: list[str] = field(default_factory=list)
    answer_key: str | None = None
    rubric: str | None = None
    common_mistakes: list[str] = field(default_factory=list)
    model_answer: str | None = None
    worked_example: str | None = None
    correction_ladder: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PacketSection:
    section_id: str
    title: str
    helper_text: str | None = None
    empty_state_text: str | None = None
    checklist_items: list[str] = field(default_factory=list)
    entries: list[PacketEntry] = field(default_factory=list)
    visual_requirements: list[PacketVisual] = field(default_factory=list)


@dataclass(frozen=True)
class PacketPage:
    packet_type: str
    page_title: str
    course_slug: str
    course_name: str
    day_index: int | None
    generated_date: str | None
    summary_text: str
    sections: list[PacketSection]
