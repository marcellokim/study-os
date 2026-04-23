from __future__ import annotations

from dataclasses import dataclass, field

from study_os.core.constants import Confidence, Result, StudyStatus


@dataclass(frozen=True)
class CourseConfig:
    course_slug: str
    course_name: str
    exam_date: str
    timezone: str
    current_day: int = 0


@dataclass(frozen=True)
class Block:
    block_id: str
    block_name: str
    block_type: str
    importance: str
    difficulty: str
    exam_relevance: str
    needs_prereq: bool
    needs_visuals: bool


@dataclass(frozen=True)
class Item:
    item_id: str
    block_id: str
    prompt: str
    answer_mode: str
    difficulty: str
    exam_relevance: str
    needs_visuals: bool


@dataclass(frozen=True)
class SourceLink:
    block_id: str
    source_type: str
    path: str
    note: str = ""


@dataclass(frozen=True)
class VisualRequirement:
    item_id: str
    block_id: str
    description: str
    required_image: str
    status: str = "missing"


@dataclass(frozen=True)
class MasteryRecord:
    item_id: str
    block_id: str
    status: str = StudyStatus.NEW.value
    last_result: str = Result.UNCERTAIN.value
    consecutive_successes: int = 0
    last_confidence: str = Confidence.UNKNOWN.value
    last_review_date: str | None = None
    next_review_date: str | None = None
    next_review_day: int | None = None
    reason: str = ""


@dataclass(frozen=True)
class QueueEntry:
    item_id: str
    block_id: str
    status: str
    priority: str
    last_result: str
    confidence: str
    next_review_day: int | None
    next_review_date: str | None
    reason: str


@dataclass(frozen=True)
class ReviewedItemUpdate:
    item_id: str
    phase: str
    result: str
    confidence: str = Confidence.UNKNOWN.value
    error_code: str | None = None
    note: str = ""


@dataclass(frozen=True)
class InitCourseRequest:
    course: CourseConfig
    blocks: list[Block]
    items: list[Item]
    source_manifest: list[SourceLink] = field(default_factory=list)
    visual_requirements: list[VisualRequirement] = field(default_factory=list)


@dataclass(frozen=True)
class CloseSessionRequest:
    course_slug: str
    session_date: str
    reviewed_items: list[ReviewedItemUpdate]
    day_index: int | None = None


@dataclass(frozen=True)
class ExecutionReceipt:
    status: str
    applied_items: list[str]
    held_items: list[str]
    generated_files: list[str]
    warnings: list[str]
