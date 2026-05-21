from collections.abc import Mapping
from copy import deepcopy


FRESH_QA_AXES = (
    "exam_transfer",
    "active_recall",
    "grading_quality",
    "risk_based_priority",
    "visual_source_connection",
    "session_close_scheduling",
    "course_specific_strategy",
    "outcome_measurement",
    "pdf_visual_intake",
)

AXIS_VALUES = ("OK", "WEAK", "BLOCKED", "NOT_CHECKED")
GATES = ("pass", "warn", "block")
FAILURE_TYPES = ("subagent_failed", "packet_blocked", "grading_blocked", "learning_weak", "pass")
GRADING_RESULTS = ("correct", "partial", "wrong", "uncertain")
FAILURE_SOURCES = (
    "none",
    "packet",
    "source_connection",
    "rubric",
    "visual_asset",
    "learner_difficulty",
    "subagent",
)

REQUIRED_FIELDS = (
    "course_slug",
    "packet_type",
    "day_index",
    "next_action",
    "phase1_attempts",
    "phase2_grading",
    "axis_scorecard",
    "highest_answer_rate_blocker",
    "fix_priority",
    "gate",
    "evidence",
)
PHASE1_ATTEMPT_FIELDS = (
    "item_id",
    "answerable_from_packet",
    "draft_answer",
    "confidence_score",
    "visible_blockers",
    "answer_first_supported",
)
PHASE2_GRADING_FIELDS = (
    "item_id",
    "result",
    "grading_rationale",
    "self_grading_supported",
    "source_connection_supported",
    "exam_plausibility",
    "failure_source",
)
GATE_STRENGTH = {"pass": 0, "warn": 1, "block": 2}


def computed_gate_for(axis_scorecard: dict, *, failure_type: str) -> str:
    if failure_type == "subagent_failed":
        return "warn"
    if any(value == "BLOCKED" for value in axis_scorecard.values()):
        return "block"
    if any(value in {"WEAK", "NOT_CHECKED"} for value in axis_scorecard.values()):
        return "warn"
    return "pass"


def predicted_effect_for(gate: str, axis_scorecard: dict) -> str:
    if gate == "block":
        return "negative"
    if gate == "warn":
        return "neutral"
    if gate == "pass" and all(value == "OK" for value in axis_scorecard.values()):
        return "positive"
    return "unknown"


def normalize_fresh_qa_result(payload: dict) -> dict:
    normalized = deepcopy(payload)

    for field in REQUIRED_FIELDS:
        if field not in normalized:
            raise ValueError(f"missing required field: {field}")

    _validate_phase1_attempts(normalized["phase1_attempts"])
    _validate_phase2_grading(normalized["phase2_grading"])
    _validate_axis_scorecard(normalized["axis_scorecard"])

    gate = normalized["gate"]
    if gate not in GATES:
        raise ValueError(f"bad gate: {gate}")

    failure_type = normalized.get("failure_type", "pass")
    if failure_type not in FAILURE_TYPES:
        raise ValueError(f"bad failure_type: {failure_type}")
    normalized["failure_type"] = failure_type

    computed_gate = computed_gate_for(normalized["axis_scorecard"], failure_type=failure_type)
    if GATE_STRENGTH[gate] < GATE_STRENGTH[computed_gate]:
        raise ValueError(f"weaker gate: gate {gate} is weaker than computed gate {computed_gate}")

    normalized["computed_gate"] = computed_gate
    normalized["predicted_answer_rate_effect"] = predicted_effect_for(
        gate,
        normalized["axis_scorecard"],
    )
    return normalized


def _validate_phase1_attempts(attempts: list) -> None:
    if not isinstance(attempts, list):
        raise ValueError("bad phase1_attempts: expected list")
    for index, attempt in enumerate(attempts):
        attempt = _require_mapping(attempt, f"phase1_attempts[{index}]")
        for field in PHASE1_ATTEMPT_FIELDS:
            if field not in attempt:
                raise ValueError(f"missing phase1_attempts field: {field}")
        confidence_score = attempt["confidence_score"]
        if (
            isinstance(confidence_score, bool)
            or not isinstance(confidence_score, int)
            or not 1 <= confidence_score <= 5
        ):
            raise ValueError(f"bad confidence score: {confidence_score}")


def _validate_phase2_grading(entries: list) -> None:
    if not isinstance(entries, list):
        raise ValueError("bad phase2_grading: expected list")
    for index, entry in enumerate(entries):
        entry = _require_mapping(entry, f"phase2_grading[{index}]")
        for field in PHASE2_GRADING_FIELDS:
            if field not in entry:
                raise ValueError(f"missing phase2_grading field: {field}")
        result = entry["result"]
        if result not in GRADING_RESULTS:
            raise ValueError(f"bad grading result: {result}")
        failure_source = entry["failure_source"]
        if failure_source not in FAILURE_SOURCES:
            raise ValueError(f"bad failure_source: {failure_source}")


def _require_mapping(value: object, field_name: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f"bad {field_name}: expected mapping")
    return value


def _validate_axis_scorecard(axis_scorecard: dict) -> None:
    if not isinstance(axis_scorecard, dict):
        raise ValueError("bad axis_scorecard: expected dict")
    expected_axes = set(FRESH_QA_AXES)
    actual_axes = set(axis_scorecard)
    for axis in sorted(actual_axes - expected_axes):
        raise ValueError(f"bad axis: {axis}")
    for axis in FRESH_QA_AXES:
        if axis not in axis_scorecard:
            raise ValueError(f"missing axis: {axis}")
        value = axis_scorecard[axis]
        if value not in AXIS_VALUES:
            raise ValueError(f"bad axis value: {axis}={value}")
