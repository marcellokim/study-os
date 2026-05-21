from collections.abc import Mapping
from copy import deepcopy
import json


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
PACKET_TYPES = ("learning", "recall", "final_recall")
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
FAILURE_TYPE_MINIMUM_GATES = {
    "subagent_failed": "warn",
    "packet_blocked": "block",
    "grading_blocked": "warn",
    "learning_weak": "warn",
    "pass": "pass",
}


def computed_gate_for(
    axis_scorecard: dict,
    *,
    failure_type: str,
    self_grading_blocked: bool = False,
    non_correct_grading: bool = False,
) -> str:
    axis_gate = _axis_driven_gate_for(axis_scorecard)
    failure_gate = _failure_type_gate_for(
        failure_type,
        self_grading_blocked=self_grading_blocked,
    )
    grading_gate = "warn" if non_correct_grading else "pass"
    return max((axis_gate, failure_gate, grading_gate), key=lambda gate: GATE_STRENGTH[gate])


def predicted_effect_for(gate: str, axis_scorecard: dict) -> str:
    if gate == "block":
        return "negative"
    if gate == "warn":
        return "neutral"
    if gate == "pass" and all(value == "OK" for value in axis_scorecard.values()):
        return "positive"
    return "unknown"


def normalize_fresh_qa_result(payload: dict) -> dict:
    _require_mapping(payload, "payload")
    normalized = _normalize_container(deepcopy(payload))

    for field in REQUIRED_FIELDS:
        if field not in normalized:
            raise ValueError(f"missing required field: {field}")

    _validate_top_level_fields(normalized)
    _validate_phase1_attempts(normalized["phase1_attempts"])
    _validate_phase2_grading(normalized["phase2_grading"])
    _validate_phase_contract(normalized["phase1_attempts"], normalized["phase2_grading"])
    _validate_axis_scorecard(normalized["axis_scorecard"])
    _validate_fix_priority(
        normalized["fix_priority"],
        gate=normalized["gate"],
        axis_scorecard=normalized["axis_scorecard"],
    )
    normalized["next_action"] = _normalize_container(normalized["next_action"])
    normalized["fix_priority"] = _normalize_container(normalized["fix_priority"])
    normalized["evidence"] = _normalize_container(normalized["evidence"])
    normalized["phase1_attempts"] = _normalize_container(normalized["phase1_attempts"])
    normalized["phase2_grading"] = _normalize_container(normalized["phase2_grading"])
    normalized["axis_scorecard"] = _normalize_container(normalized["axis_scorecard"])

    gate = normalized["gate"]

    failure_type = normalized.get("failure_type", "pass")
    if failure_type not in FAILURE_TYPES:
        raise ValueError(f"bad failure_type: {failure_type}")
    normalized["failure_type"] = failure_type

    computed_gate = computed_gate_for(
        normalized["axis_scorecard"],
        failure_type=failure_type,
        self_grading_blocked=any(
            entry["self_grading_supported"] is False for entry in normalized["phase2_grading"]
        ),
        non_correct_grading=any(
            entry["result"] != "correct" for entry in normalized["phase2_grading"]
        ),
    )
    if GATE_STRENGTH[gate] < GATE_STRENGTH[computed_gate]:
        raise ValueError(f"weaker gate: gate {gate} is weaker than computed gate {computed_gate}")

    normalized["computed_gate"] = computed_gate
    normalized["predicted_answer_rate_effect"] = predicted_effect_for(
        gate,
        normalized["axis_scorecard"],
    )
    return normalized


def _failure_type_gate_for(failure_type: str, *, self_grading_blocked: bool) -> str:
    if failure_type == "grading_blocked" and self_grading_blocked:
        return "block"
    return FAILURE_TYPE_MINIMUM_GATES[failure_type]


def _normalize_container(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _normalize_container(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_container(item) for item in value]
    return value


def _axis_driven_gate_for(axis_scorecard: dict) -> str:
    if any(value == "BLOCKED" for value in axis_scorecard.values()):
        return "block"
    if any(value in {"WEAK", "NOT_CHECKED"} for value in axis_scorecard.values()):
        return "warn"
    return "pass"


def _validate_top_level_fields(payload: Mapping) -> None:
    _require_non_empty_string(payload["course_slug"], "course_slug")
    _require_non_empty_string(payload["packet_type"], "packet_type")
    if payload["packet_type"] not in PACKET_TYPES:
        raise ValueError(f"bad packet_type: {payload['packet_type']}")
    _require_positive_int_or_none(payload["day_index"], "day_index")
    _require_mapping(payload["next_action"], "next_action")
    _require_non_empty_string(
        payload["highest_answer_rate_blocker"],
        "highest_answer_rate_blocker",
    )
    _require_mapping(payload["fix_priority"], "fix_priority")
    gate = payload["gate"]
    if gate not in GATES:
        raise ValueError(f"bad gate: {gate}")
    _require_mapping(payload["evidence"], "evidence")


def _validate_phase1_attempts(attempts: list) -> None:
    if not isinstance(attempts, list):
        raise ValueError("bad phase1_attempts: expected list")
    for index, attempt in enumerate(attempts):
        field_name = f"phase1_attempts[{index}]"
        attempt = _require_mapping(attempt, field_name)
        for field in PHASE1_ATTEMPT_FIELDS:
            if field not in attempt:
                raise ValueError(f"missing phase1_attempts field: {field}")
        _require_non_empty_string(attempt["item_id"], f"{field_name}.item_id")
        _require_bool(attempt["answerable_from_packet"], f"{field_name}.answerable_from_packet")
        _require_string(attempt["draft_answer"], f"{field_name}.draft_answer")
        confidence_score = attempt["confidence_score"]
        if (
            isinstance(confidence_score, bool)
            or not isinstance(confidence_score, int)
            or not 1 <= confidence_score <= 5
        ):
            raise ValueError(f"bad confidence score: {confidence_score}")
        _require_string_list(attempt["visible_blockers"], f"{field_name}.visible_blockers")
        _require_bool(attempt["answer_first_supported"], f"{field_name}.answer_first_supported")


def _validate_phase2_grading(entries: list) -> None:
    if not isinstance(entries, list):
        raise ValueError("bad phase2_grading: expected list")
    for index, entry in enumerate(entries):
        field_name = f"phase2_grading[{index}]"
        entry = _require_mapping(entry, field_name)
        for field in PHASE2_GRADING_FIELDS:
            if field not in entry:
                raise ValueError(f"missing phase2_grading field: {field}")
        _require_non_empty_string(entry["item_id"], f"{field_name}.item_id")
        result = entry["result"]
        if result not in GRADING_RESULTS:
            raise ValueError(f"bad grading result: {result}")
        _require_non_empty_string(entry["grading_rationale"], f"{field_name}.grading_rationale")
        _require_bool(entry["self_grading_supported"], f"{field_name}.self_grading_supported")
        _require_bool(
            entry["source_connection_supported"],
            f"{field_name}.source_connection_supported",
        )
        _require_non_empty_string(entry["exam_plausibility"], f"{field_name}.exam_plausibility")
        failure_source = entry["failure_source"]
        if failure_source not in FAILURE_SOURCES:
            raise ValueError(f"bad failure_source: {failure_source}")


def _validate_phase_contract(attempts: list[dict], entries: list[dict]) -> None:
    attempts_by_id: dict[str, dict] = {}
    for index, attempt in enumerate(attempts):
        item_id = attempt["item_id"]
        if item_id in attempts_by_id:
            raise ValueError(f"duplicate phase1 attempt item_id: {item_id}")
        attempts_by_id[item_id] = attempt

    entries_by_id: dict[str, dict] = {}
    for index, entry in enumerate(entries):
        item_id = entry["item_id"]
        if item_id in entries_by_id:
            raise ValueError(f"duplicate phase2 grading item_id: {item_id}")
        entries_by_id[item_id] = entry
        attempt = attempts_by_id.get(item_id)
        if attempt is None:
            raise ValueError(f"phase2 item without phase1 attempt: {item_id}")

        if entry["result"] == "correct":
            if (
                not attempt["answerable_from_packet"]
                or not attempt["answer_first_supported"]
                or not entry["self_grading_supported"]
                or not entry["source_connection_supported"]
                or entry["failure_source"] != "none"
            ):
                raise ValueError(
                    f"inconsistent phase2_grading[{index}]: correct requires packet, "
                    "answer-first, self-grading, source support, and failure_source=none"
                )
            continue

        if entry["failure_source"] == "none":
            raise ValueError(
                f"inconsistent phase2_grading[{index}]: non-correct result requires failure_source"
            )

        if not attempt["answerable_from_packet"] and entry["failure_source"] not in {
            "packet",
            "visual_asset",
            "source_connection",
        }:
            raise ValueError(
                f"inconsistent phase2_grading[{index}]: unanswerable packet needs packet-linked failure_source"
            )

        if not entry["self_grading_supported"] and entry["failure_source"] not in {
            "rubric",
            "source_connection",
            "visual_asset",
        }:
            raise ValueError(
                f"inconsistent phase2_grading[{index}]: unsupported self-grading needs grading-linked failure_source"
            )

        if not entry["source_connection_supported"] and entry["failure_source"] not in {
            "source_connection",
            "visual_asset",
        }:
            raise ValueError(
                f"inconsistent phase2_grading[{index}]: unsupported source connection needs source-linked failure_source"
            )

    for item_id in attempts_by_id:
        if item_id not in entries_by_id:
            raise ValueError(f"phase1 attempt without phase2 grading: {item_id}")


def _require_mapping(value: object, field_name: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f"bad {field_name}: expected mapping")
    return value


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"bad {field_name}: expected bool")


def _require_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"bad {field_name}: expected string")


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"bad {field_name}: expected non-empty string")


def _require_positive_int_or_none(value: object, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"bad {field_name}: expected positive int or None")


def _require_string_list(value: object, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"bad {field_name}: expected list of strings")
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"bad {field_name}[{index}]: expected string")


def _validate_axis_scorecard(axis_scorecard: dict) -> None:
    if not isinstance(axis_scorecard, Mapping):
        raise ValueError("bad axis_scorecard: expected mapping")
    for axis in axis_scorecard:
        if not isinstance(axis, str):
            raise ValueError(f"bad axis key: {axis}")
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


def _validate_fix_priority(fix_priority: Mapping, *, gate: str, axis_scorecard: Mapping) -> None:
    axis = fix_priority.get("axis")
    if gate != "pass":
        for field in ("axis", "summary", "recommended_action"):
            if field not in fix_priority:
                raise ValueError(f"missing fix_priority.{field}")
            _require_non_empty_string(fix_priority[field], f"fix_priority.{field}")

    if axis is None:
        return
    if not isinstance(axis, str) or axis not in FRESH_QA_AXES:
        raise ValueError(f"bad fix_priority.axis: {axis}")
    failed_axes = {
        axis_name
        for axis_name, value in axis_scorecard.items()
        if value in {"BLOCKED", "WEAK", "NOT_CHECKED"}
    }
    if gate != "pass" and failed_axes and axis not in failed_axes:
        raise ValueError(f"fix_priority.axis must match a failed axis: {axis}")


def select_global_fix_priority(results: list[dict]) -> dict:
    if not results:
        return {
            "course_slug": "",
            "gate": "pass",
            "summary": "검사된 fresh QA 결과가 없습니다.",
            "axis": "outcome_measurement",
            "recommended_action": "먼저 fresh QA 결과를 생성하거나 수집하세요.",
            "highest_answer_rate_blocker": "No fresh QA result.",
        }

    normalized_results = [normalize_fresh_qa_result(result) for result in results]
    selected = max(normalized_results, key=_global_fix_priority_sort_key)
    fix_priority = selected["fix_priority"]
    return {
        "course_slug": selected["course_slug"],
        "gate": selected["gate"],
        "summary": str(fix_priority.get("summary", selected["highest_answer_rate_blocker"])),
        "axis": str(fix_priority.get("axis", "outcome_measurement")),
        "recommended_action": str(
            fix_priority.get("recommended_action", "Inspect the blocked QA evidence.")
        ),
        "highest_answer_rate_blocker": selected["highest_answer_rate_blocker"],
    }


def render_daily_fresh_qa_report(
    results: list[dict],
    *,
    today: str,
    expected_course_slugs: list[str] | None = None,
) -> str:
    normalized_results = [normalize_fresh_qa_result(result) for result in results]
    _validate_expected_course_results(normalized_results, expected_course_slugs)
    global_priority = select_global_fix_priority(normalized_results)
    lines = [
        f"# Daily Fresh QA - {today}",
        "",
        "## Global Fix Priority",
        f"- course_slug: {global_priority['course_slug'] or 'none'}",
        f"- gate: {global_priority['gate']}",
        f"- axis: {global_priority['axis']}",
        f"- highest_answer_rate_blocker: {global_priority['highest_answer_rate_blocker']}",
        f"- fix_priority: {global_priority['summary']}",
        f"- next_action: {global_priority['recommended_action']}",
        "",
    ]

    for result in sorted(normalized_results, key=lambda row: row["course_slug"]):
        lines.extend(
            [
                f"## {result['course_slug']}",
                f"- next_action: {_format_report_value(result['next_action'])}",
                f"- packet_checked: {_format_packet_checked(result)}",
                f"- gate: {result['gate']} (computed: {result['computed_gate']})",
                f"- 정답률 영향: {result['predicted_answer_rate_effect']}",
                f"- highest_answer_rate_blocker: {result['highest_answer_rate_blocker']}",
                f"- fix_priority: {_format_report_value(result['fix_priority'])}",
                "",
                "### 9-axis scorecard",
            ]
        )
        for axis in FRESH_QA_AXES:
            lines.append(f"- {axis}: {result['axis_scorecard'][axis]}")
        lines.extend(["", "### evidence"])
        evidence = result["evidence"]
        if evidence:
            for key in sorted(evidence, key=str):
                lines.append(f"- {key}: {_format_report_value(evidence[key])}")
        else:
            lines.append("- none")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _validate_expected_course_results(
    results: list[dict],
    expected_course_slugs: list[str] | None,
) -> None:
    if expected_course_slugs is None:
        return

    expected = set(expected_course_slugs)
    actual = [result["course_slug"] for result in results]
    actual_set = set(actual)
    if len(actual) != len(actual_set):
        raise ValueError("duplicate fresh QA result course_slug")

    missing = sorted(expected - actual_set)
    if missing:
        raise ValueError(f"missing fresh QA result for course: {missing[0]}")

    unexpected = sorted(actual_set - expected)
    if unexpected:
        raise ValueError(f"unexpected fresh QA result for course: {unexpected[0]}")


def _global_fix_priority_sort_key(result: dict) -> tuple:
    blocked, weak, not_checked = _axis_counts(result["axis_scorecard"])
    return (
        GATE_STRENGTH[result["gate"]],
        blocked,
        weak,
        not_checked,
        result["course_slug"],
    )


def _axis_counts(axis_scorecard: dict) -> tuple[int, int, int]:
    blocked = sum(1 for value in axis_scorecard.values() if value == "BLOCKED")
    weak = sum(1 for value in axis_scorecard.values() if value == "WEAK")
    not_checked = sum(1 for value in axis_scorecard.values() if value == "NOT_CHECKED")
    return blocked, weak, not_checked


def _format_packet_checked(result: dict) -> str:
    packet_type = result["packet_type"]
    day_index = result["day_index"]
    if day_index is None:
        label = packet_type
    else:
        label = f"{packet_type}:day:{day_index}"

    packet_path = result["evidence"].get("packet_path")
    if isinstance(packet_path, str) and packet_path:
        return f"{label} ({packet_path})"
    return label


def _format_report_value(value: object) -> str:
    if isinstance(value, Mapping) or isinstance(value, list):
        return json.dumps(_json_safe_value(value), ensure_ascii=False, sort_keys=True)
    return str(value)


def _json_safe_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    return value
