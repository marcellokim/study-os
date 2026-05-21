# Daily Fresh Black-Box QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest Study OS daily fresh black-box QA loop that resolves each active course's next real packet, gives a fresh evaluator a two-phase contract, validates returned QA results, and renders a Korean fix-priority report focused on exam answer-rate improvement.

**Architecture:** Keep Study OS engine code deterministic and local: it does not spawn Codex agents. The engine exposes next-packet context and a strict result/report contract; Codex daily evolution or another orchestrator runs the fresh subagent and feeds the JSON result back into Study OS for validation and report rendering.

**Tech Stack:** Python standard library, `dataclasses`, existing `StudyEngine`, existing filesystem course state, existing `unittest` suite, argparse CLI.

---

## File Structure

- Create `study_os/core/fresh_qa.py`
  - Owns the nine-axis constants, inspection-budget constants, fresh QA result validation, gate/effect normalization, global fix-priority selection, and Korean report rendering.
  - Contains no filesystem access and no Codex subagent calls.
- Modify `study_os/core/engine.py`
  - Adds `list_active_course_slugs()` and `build_fresh_qa_context(course_slug, today="2026-05-22")`.
  - Resolves the actual next packet from current course state and generated packet files.
  - Splits Phase 1 packet-only context from Phase 2 grading materials.
- Modify `study_os/cli.py`
  - Adds `fresh-qa-context` for daily orchestration to fetch one course or all active courses.
  - Adds `fresh-qa-report` for validating result JSON and rendering the daily Korean report.
- Modify `tests/core/test_engine_fresh_qa.py`
  - Covers next-packet resolution, missing packet signals, all-active course discovery, and Phase 1/Phase 2 material separation.
- Create `tests/core/test_fresh_qa.py`
  - Covers result schema validation, gate/effect logic, global fix-priority selection, and Korean report content.
- Modify `tests/test_cli_smoke.py`
  - Covers CLI help, context JSON output, and report rendering from a fixture result.

## Behavioral Contracts

### Axis Names

Use these exact machine keys for the nine improvement axes:

```text
exam_transfer
active_recall
grading_quality
risk_based_priority
visual_source_connection
session_close_scheduling
course_specific_strategy
outcome_measurement
pdf_visual_intake
```

### Next-Packet Resolution

The resolver must not pick a random sample. It uses the course's current state:

1. If the course has `current_day <= 0`, return a `generate_day` next action and no open packet.
2. If any review queue entry is due by current day or date, the next packet is current-day recall.
3. If no review queue entry is due, the next packet is current-day learning.
4. If the selected packet does not exist, keep the selected packet type and mark `exists=false` and `openable=false`; do not silently fall back to another packet.
5. If the selected packet exists, include the local HTML path, Markdown path, and packet-server URL path.

This makes a bad Study OS recommendation visible as a product-quality signal.

### Phase Separation

`phase1_context` may include packet paths, packet URL, inspection budget, and user-flow instructions. It must not include item `answer_key`, `rubric`, `common_mistakes`, `model_answer`, `worked_example`, or source excerpts.

`phase2_context` may include item answer keys, rubrics, common mistakes, model answers, source refs, and visual requirements. The orchestrator passes this only after Phase 1 attempts are recorded.

### Result Gate Policy

Study OS validates the result's declared gate and also computes a recommended gate from axis states:

```text
any BLOCKED axis -> block
any WEAK axis or NOT_CHECKED axis -> warn
all OK axes -> pass
subagent_failed failure_type -> warn unless the submitted gate is block
```

If the declared gate is weaker than the computed gate, normalization raises `ValueError`. A result may be stricter than computed gate; that lets the evaluator block on evidence outside the axis summary.

### Daily Report

The report is Korean-first and compact:

```text
# Daily Fresh QA - YYYY-MM-DD

## Global Fix Priority
- course_slug: sample-course
- gate: warn
- axis: grading_quality
- highest_answer_rate_blocker: Missing answer key.
- fix_priority: Add answer key and rubric.
- next_action: Attach answer key before the next study session.

## course_slug value
- next_action: Open day 1 learning packet
- packet_checked: learning:day:1
- gate: warn
- predicted_answer_rate_effect: neutral
- highest_answer_rate_blocker: Missing answer key.
- fix_priority: Add answer key and rubric.

### 9-axis scorecard
- exam_transfer: OK
- active_recall: OK
- grading_quality: BLOCKED

### evidence
- packet_path: /tmp/workspace/courses/sample-course/outputs/daily/day_01_learning.html
```

## Task 1: Fresh QA Result Contract

**Files:**
- Create: `study_os/core/fresh_qa.py`
- Test: `tests/core/test_fresh_qa.py`

- [ ] **Step 1: Write failing tests for result normalization and gate enforcement**

Create `tests/core/test_fresh_qa.py` with this initial content:

```python
import unittest

from study_os.core.fresh_qa import (
    FRESH_QA_AXES,
    normalize_fresh_qa_result,
)


def _axis_scorecard(value: str = "OK") -> dict[str, str]:
    return {axis: value for axis in FRESH_QA_AXES}


def _valid_result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "course_slug": "sample-course",
        "packet_type": "learning",
        "day_index": 1,
        "next_action": {
            "kind": "open_packet",
            "label": "Open day 1 learning packet",
            "reason": "No due recall entries.",
        },
        "phase1_attempts": [
            {
                "item_id": "scope_keywords",
                "answerable_from_packet": True,
                "draft_answer": "State the three key scope terms.",
                "confidence_score": 4,
                "visible_blockers": [],
                "answer_first_supported": True,
            }
        ],
        "phase2_grading": [
            {
                "item_id": "scope_keywords",
                "result": "correct",
                "grading_rationale": "The attempt includes every required keyword.",
                "self_grading_supported": True,
                "source_connection_supported": True,
                "exam_plausibility": "high",
                "failure_source": "none",
            }
        ],
        "axis_scorecard": _axis_scorecard(),
        "highest_answer_rate_blocker": "None.",
        "fix_priority": {
            "summary": "No immediate fix needed.",
            "axis": "exam_transfer",
            "recommended_action": "Keep monitoring next packets.",
        },
        "gate": "pass",
        "failure_type": "pass",
        "evidence": {
            "packet_path": "/tmp/workspace/courses/sample-course/outputs/daily/day_01_learning.html",
            "source_refs": ["slides/week01.pdf#p3"],
        },
    }
    payload.update(overrides)
    return payload


class FreshQaResultContractTest(unittest.TestCase):
    def test_normalize_accepts_complete_pass_result(self) -> None:
        normalized = normalize_fresh_qa_result(_valid_result())

        self.assertEqual(normalized["course_slug"], "sample-course")
        self.assertEqual(normalized["gate"], "pass")
        self.assertEqual(normalized["predicted_answer_rate_effect"], "positive")
        self.assertEqual(normalized["axis_scorecard"]["exam_transfer"], "OK")

    def test_missing_required_field_is_rejected(self) -> None:
        payload = _valid_result()
        payload.pop("phase2_grading")

        with self.assertRaisesRegex(ValueError, "fresh QA result missing required field: phase2_grading"):
            normalize_fresh_qa_result(payload)

    def test_invalid_axis_value_is_rejected(self) -> None:
        payload = _valid_result(axis_scorecard={**_axis_scorecard(), "exam_transfer": "GOOD"})

        with self.assertRaisesRegex(ValueError, "axis exam_transfer must be one of"):
            normalize_fresh_qa_result(payload)

    def test_blocked_axis_requires_block_gate(self) -> None:
        payload = _valid_result(
            axis_scorecard={**_axis_scorecard(), "grading_quality": "BLOCKED"},
            gate="warn",
        )

        with self.assertRaisesRegex(ValueError, "gate warn is weaker than computed gate block"):
            normalize_fresh_qa_result(payload)

    def test_confidence_score_must_be_one_to_five(self) -> None:
        payload = _valid_result(
            phase1_attempts=[
                {
                    "item_id": "scope_keywords",
                    "answerable_from_packet": True,
                    "draft_answer": "State the scope terms.",
                    "confidence_score": 6,
                    "visible_blockers": [],
                    "answer_first_supported": True,
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "confidence_score must be an integer from 1 to 5"):
            normalize_fresh_qa_result(payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused failing test**

Run:

```bash
python3.13 -m unittest tests.core.test_fresh_qa
```

Expected:

```text
ModuleNotFoundError: No module named 'study_os.core.fresh_qa'
```

- [ ] **Step 3: Add the fresh QA contract implementation**

Create `study_os/core/fresh_qa.py`:

```python
from __future__ import annotations

from copy import deepcopy
from typing import Any


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
AXIS_SCORE_VALUES = frozenset({"OK", "WEAK", "BLOCKED", "NOT_CHECKED"})
GATE_VALUES = frozenset({"pass", "warn", "block"})
FAILURE_TYPE_VALUES = frozenset(
    {
        "subagent_failed",
        "packet_blocked",
        "grading_blocked",
        "learning_weak",
        "pass",
    }
)
GRADING_RESULT_VALUES = frozenset({"correct", "partial", "wrong", "uncertain"})
FAILURE_SOURCE_VALUES = frozenset(
    {
        "none",
        "packet",
        "source_connection",
        "rubric",
        "visual_asset",
        "learner_difficulty",
        "subagent",
    }
)
PREDICTED_EFFECT_VALUES = frozenset({"positive", "neutral", "negative", "unknown"})
_GATE_STRENGTH = {"pass": 0, "warn": 1, "block": 2}


def _require_mapping(payload: Any, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a mapping")
    return dict(payload)


def _require_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_optional_day_index(payload: dict[str, Any]) -> int | None:
    value = payload.get("day_index")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("day_index must be a positive integer or null")
    return value


def _require_list(payload: dict[str, Any], field_name: str) -> list[Any]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return list(value)


def _normalize_axis_scorecard(payload: Any) -> dict[str, str]:
    scorecard = _require_mapping(payload, "axis_scorecard")
    normalized: dict[str, str] = {}
    for axis in FRESH_QA_AXES:
        value = scorecard.get(axis)
        if value not in AXIS_SCORE_VALUES:
            allowed = ", ".join(sorted(AXIS_SCORE_VALUES))
            raise ValueError(f"axis {axis} must be one of: {allowed}")
        normalized[axis] = value
    extra_axes = sorted(set(scorecard) - set(FRESH_QA_AXES))
    if extra_axes:
        raise ValueError(f"axis_scorecard contains unknown axes: {', '.join(extra_axes)}")
    return normalized


def _normalize_visible_blockers(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("visible_blockers must be a list")
    normalized: list[str] = []
    for blocker in value:
        if not isinstance(blocker, str):
            raise ValueError("visible_blockers entries must be strings")
        normalized.append(blocker)
    return normalized


def _normalize_phase1_attempts(payload: Any) -> list[dict[str, Any]]:
    attempts = _require_list({"phase1_attempts": payload}, "phase1_attempts")
    normalized: list[dict[str, Any]] = []
    for index, raw_attempt in enumerate(attempts):
        attempt = _require_mapping(raw_attempt, f"phase1_attempts[{index}]")
        item_id = _require_string(attempt, "item_id")
        answerable = attempt.get("answerable_from_packet")
        if not isinstance(answerable, bool):
            raise ValueError("answerable_from_packet must be a boolean")
        draft_answer = attempt.get("draft_answer")
        if not isinstance(draft_answer, str):
            raise ValueError("draft_answer must be a string")
        confidence_score = attempt.get("confidence_score")
        if (
            isinstance(confidence_score, bool)
            or not isinstance(confidence_score, int)
            or confidence_score < 1
            or confidence_score > 5
        ):
            raise ValueError("confidence_score must be an integer from 1 to 5")
        answer_first_supported = attempt.get("answer_first_supported")
        if not isinstance(answer_first_supported, bool):
            raise ValueError("answer_first_supported must be a boolean")
        normalized.append(
            {
                "item_id": item_id,
                "answerable_from_packet": answerable,
                "draft_answer": draft_answer,
                "confidence_score": confidence_score,
                "visible_blockers": _normalize_visible_blockers(attempt.get("visible_blockers")),
                "answer_first_supported": answer_first_supported,
            }
        )
    return normalized


def _normalize_phase2_grading(payload: Any) -> list[dict[str, Any]]:
    grading_rows = _require_list({"phase2_grading": payload}, "phase2_grading")
    normalized: list[dict[str, Any]] = []
    for index, raw_row in enumerate(grading_rows):
        row = _require_mapping(raw_row, f"phase2_grading[{index}]")
        item_id = _require_string(row, "item_id")
        result = _require_string(row, "result")
        if result not in GRADING_RESULT_VALUES:
            allowed = ", ".join(sorted(GRADING_RESULT_VALUES))
            raise ValueError(f"result must be one of: {allowed}")
        failure_source = _require_string(row, "failure_source")
        if failure_source not in FAILURE_SOURCE_VALUES:
            allowed = ", ".join(sorted(FAILURE_SOURCE_VALUES))
            raise ValueError(f"failure_source must be one of: {allowed}")
        for boolean_field in ("self_grading_supported", "source_connection_supported"):
            if not isinstance(row.get(boolean_field), bool):
                raise ValueError(f"{boolean_field} must be a boolean")
        normalized.append(
            {
                "item_id": item_id,
                "result": result,
                "grading_rationale": _require_string(row, "grading_rationale"),
                "self_grading_supported": row["self_grading_supported"],
                "source_connection_supported": row["source_connection_supported"],
                "exam_plausibility": _require_string(row, "exam_plausibility"),
                "failure_source": failure_source,
            }
        )
    return normalized


def computed_gate_for(axis_scorecard: dict[str, str], *, failure_type: str) -> str:
    if failure_type == "subagent_failed":
        return "warn"
    if any(value == "BLOCKED" for value in axis_scorecard.values()):
        return "block"
    if any(value in {"WEAK", "NOT_CHECKED"} for value in axis_scorecard.values()):
        return "warn"
    return "pass"


def predicted_effect_for(gate: str, axis_scorecard: dict[str, str]) -> str:
    if gate == "block":
        return "negative"
    if gate == "warn":
        return "neutral"
    if all(value == "OK" for value in axis_scorecard.values()):
        return "positive"
    return "unknown"


def normalize_fresh_qa_result(payload: Any) -> dict[str, Any]:
    result = _require_mapping(payload, "fresh QA result")
    required_fields = (
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
    for field_name in required_fields:
        if field_name not in result:
            raise ValueError(f"fresh QA result missing required field: {field_name}")

    normalized = deepcopy(result)
    normalized["course_slug"] = _require_string(result, "course_slug")
    normalized["packet_type"] = _require_string(result, "packet_type")
    normalized["day_index"] = _require_optional_day_index(result)
    normalized["next_action"] = _require_mapping(result["next_action"], "next_action")
    normalized["phase1_attempts"] = _normalize_phase1_attempts(result["phase1_attempts"])
    normalized["phase2_grading"] = _normalize_phase2_grading(result["phase2_grading"])
    normalized["axis_scorecard"] = _normalize_axis_scorecard(result["axis_scorecard"])
    normalized["highest_answer_rate_blocker"] = _require_string(result, "highest_answer_rate_blocker")
    normalized["fix_priority"] = _require_mapping(result["fix_priority"], "fix_priority")
    normalized["evidence"] = _require_mapping(result["evidence"], "evidence")

    gate = _require_string(result, "gate")
    if gate not in GATE_VALUES:
        allowed = ", ".join(sorted(GATE_VALUES))
        raise ValueError(f"gate must be one of: {allowed}")
    failure_type = result.get("failure_type", "pass")
    if failure_type not in FAILURE_TYPE_VALUES:
        allowed = ", ".join(sorted(FAILURE_TYPE_VALUES))
        raise ValueError(f"failure_type must be one of: {allowed}")

    computed_gate = computed_gate_for(normalized["axis_scorecard"], failure_type=failure_type)
    if _GATE_STRENGTH[gate] < _GATE_STRENGTH[computed_gate]:
        raise ValueError(f"gate {gate} is weaker than computed gate {computed_gate}")

    normalized["gate"] = gate
    normalized["failure_type"] = failure_type
    normalized["computed_gate"] = computed_gate
    normalized["predicted_answer_rate_effect"] = predicted_effect_for(gate, normalized["axis_scorecard"])
    return normalized
```

- [ ] **Step 4: Run focused tests and confirm pass**

Run:

```bash
python3.13 -m unittest tests.core.test_fresh_qa
```

Expected:

```text
Ran 5 tests

OK
```

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add study_os/core/fresh_qa.py tests/core/test_fresh_qa.py
git commit -m "feat: add fresh qa result contract"
```

Expected:

```text
commit summary includes "feat: add fresh qa result contract" and the command exits 0
```

## Task 2: Gate Summary And Daily Report Rendering

**Files:**
- Modify: `study_os/core/fresh_qa.py`
- Modify: `tests/core/test_fresh_qa.py`

- [ ] **Step 1: Add failing tests for global priority and report rendering**

Append these tests inside `FreshQaResultContractTest` in `tests/core/test_fresh_qa.py`:

```python
    def test_select_global_fix_priority_prefers_block_over_warn(self) -> None:
        from study_os.core.fresh_qa import select_global_fix_priority

        warn_result = normalize_fresh_qa_result(
            _valid_result(
                course_slug="course-warn",
                axis_scorecard={**_axis_scorecard(), "exam_transfer": "WEAK"},
                gate="warn",
                highest_answer_rate_blocker="Prompt is too generic.",
                fix_priority={
                    "summary": "Rewrite generic prompt.",
                    "axis": "exam_transfer",
                    "recommended_action": "Use exam-style question wording.",
                },
            )
        )
        block_result = normalize_fresh_qa_result(
            _valid_result(
                course_slug="course-block",
                axis_scorecard={**_axis_scorecard(), "grading_quality": "BLOCKED"},
                gate="block",
                highest_answer_rate_blocker="Missing answer key.",
                fix_priority={
                    "summary": "Add answer key.",
                    "axis": "grading_quality",
                    "recommended_action": "Attach answer key and rubric before next study session.",
                },
            )
        )

        priority = select_global_fix_priority([warn_result, block_result])

        self.assertEqual(priority["course_slug"], "course-block")
        self.assertEqual(priority["gate"], "block")
        self.assertEqual(priority["summary"], "Add answer key.")

    def test_render_daily_fresh_qa_report_is_korean_and_contains_axes(self) -> None:
        from study_os.core.fresh_qa import render_daily_fresh_qa_report

        normalized = normalize_fresh_qa_result(
            _valid_result(
                axis_scorecard={**_axis_scorecard(), "visual_source_connection": "WEAK"},
                gate="warn",
                highest_answer_rate_blocker="Diagram reference is visible but hard to inspect.",
                fix_priority={
                    "summary": "Expose the diagram crop beside the prompt.",
                    "axis": "visual_source_connection",
                    "recommended_action": "Render the required visual near the item.",
                },
            )
        )

        report = render_daily_fresh_qa_report([normalized], today="2026-05-22")

        self.assertIn("# Daily Fresh QA - 2026-05-22", report)
        self.assertIn("## Global Fix Priority", report)
        self.assertIn("정답률 영향", report)
        self.assertIn("visual_source_connection: WEAK", report)
        self.assertIn("Diagram reference is visible but hard to inspect.", report)
```

- [ ] **Step 2: Run the focused failing tests**

Run:

```bash
python3.13 -m unittest tests.core.test_fresh_qa
```

Expected:

```text
ImportError: cannot import name 'select_global_fix_priority'
```

- [ ] **Step 3: Implement priority selection and report rendering**

Append this code to `study_os/core/fresh_qa.py`:

```python

def _axis_counts(result: dict[str, Any]) -> tuple[int, int, int]:
    scorecard = result["axis_scorecard"]
    blocked = sum(1 for value in scorecard.values() if value == "BLOCKED")
    weak = sum(1 for value in scorecard.values() if value == "WEAK")
    not_checked = sum(1 for value in scorecard.values() if value == "NOT_CHECKED")
    return blocked, weak, not_checked


def select_global_fix_priority(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "course_slug": "",
            "gate": "pass",
            "summary": "검사된 fresh QA 결과가 없습니다.",
            "axis": "outcome_measurement",
            "recommended_action": "먼저 fresh QA 결과 JSON을 생성하세요.",
            "highest_answer_rate_blocker": "No fresh QA result.",
        }

    normalized_results = [normalize_fresh_qa_result(result) for result in results]

    def sort_key(result: dict[str, Any]) -> tuple[int, int, int, int, str]:
        blocked, weak, not_checked = _axis_counts(result)
        return (
            _GATE_STRENGTH[result["gate"]],
            blocked,
            weak,
            not_checked,
            result["course_slug"],
        )

    selected = max(normalized_results, key=sort_key)
    fix_priority = _require_mapping(selected["fix_priority"], "fix_priority")
    return {
        "course_slug": selected["course_slug"],
        "gate": selected["gate"],
        "summary": str(fix_priority.get("summary", selected["highest_answer_rate_blocker"])),
        "axis": str(fix_priority.get("axis", "outcome_measurement")),
        "recommended_action": str(fix_priority.get("recommended_action", "Inspect the blocked QA evidence.")),
        "highest_answer_rate_blocker": selected["highest_answer_rate_blocker"],
    }


def _format_packet_checked(result: dict[str, Any]) -> str:
    evidence = result.get("evidence", {})
    packet_path = evidence.get("packet_path") if isinstance(evidence, dict) else None
    packet_type = result["packet_type"]
    day_index = result["day_index"]
    if day_index is None:
        label = packet_type
    else:
        label = f"{packet_type}:day:{day_index}"
    if isinstance(packet_path, str) and packet_path:
        return f"{label} ({packet_path})"
    return label


def render_daily_fresh_qa_report(results: list[dict[str, Any]], *, today: str) -> str:
    normalized_results = [normalize_fresh_qa_result(result) for result in results]
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
        next_action = result.get("next_action", {})
        action_label = next_action.get("label", next_action.get("kind", "unknown"))
        fix_priority = result.get("fix_priority", {})
        lines.extend(
            [
                f"## {result['course_slug']}",
                f"- next_action: {action_label}",
                f"- packet_checked: {_format_packet_checked(result)}",
                f"- gate: {result['gate']} (computed: {result['computed_gate']})",
                f"- 정답률 영향: {result['predicted_answer_rate_effect']}",
                f"- highest_answer_rate_blocker: {result['highest_answer_rate_blocker']}",
                f"- fix_priority: {fix_priority.get('summary', '')}",
                "",
                "### 9-axis scorecard",
            ]
        )
        for axis in FRESH_QA_AXES:
            lines.append(f"- {axis}: {result['axis_scorecard'][axis]}")
        evidence = result.get("evidence", {})
        lines.extend(["", "### evidence"])
        if isinstance(evidence, dict) and evidence:
            for key in sorted(evidence):
                lines.append(f"- {key}: {evidence[key]}")
        else:
            lines.append("- none")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
python3.13 -m unittest tests.core.test_fresh_qa
```

Expected:

```text
Ran 7 tests

OK
```

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add study_os/core/fresh_qa.py tests/core/test_fresh_qa.py
git commit -m "feat: render daily fresh qa report"
```

Expected:

```text
commit summary includes "feat: render daily fresh qa report" and the command exits 0
```

## Task 3: Engine Next-Packet Context

**Files:**
- Modify: `study_os/core/engine.py`
- Test: `tests/core/test_engine_fresh_qa.py`

- [ ] **Step 1: Write failing tests for next-packet resolution and phase separation**

Create `tests/core/test_engine_fresh_qa.py`:

```python
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.models import MasteryRecord
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class FreshQaContextTest(unittest.TestCase):
    def _course_payload(self, course_slug: str = "sample-course") -> dict:
        return {
            "course": {
                "course_slug": course_slug,
                "course_name": "Sample Course",
                "exam_date": "2026-06-16",
                "timezone": "Asia/Seoul",
            },
            "blocks": [
                {
                    "block_id": "scope",
                    "block_name": "Scope",
                    "block_type": "concept",
                    "importance": "high",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_prereq": False,
                    "needs_visuals": True,
                }
            ],
            "items": [
                {
                    "item_id": "scope_keywords",
                    "block_id": "scope",
                    "prompt": "List the scope control keywords.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_visuals": True,
                    "learning_note": "Focus on exam wording.",
                    "answer_key": "auto, static, register",
                    "rubric": "One point for each keyword.",
                    "common_mistakes": ["Confusing storage duration with scope."],
                    "model_answer": "The main C storage-class keywords are auto, static, and register.",
                    "source_refs": ["Week05_Ch05.pdf#p12"],
                }
            ],
            "visual_requirements": [
                {
                    "item_id": "scope_keywords",
                    "block_id": "scope",
                    "description": "Keyword summary table.",
                    "required_image": "scope-table.png",
                    "status": "available",
                }
            ],
        }

    def test_context_selects_learning_when_no_due_review_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            engine.initialize_course(self._course_payload())
            engine.start_day("sample-course", day_index=1, today="2026-05-22")

            context = engine.build_fresh_qa_context("sample-course", today="2026-05-22")

            self.assertEqual(context["course_slug"], "sample-course")
            self.assertEqual(context["packet"]["packet_type"], "learning")
            self.assertTrue(context["packet"]["exists"])
            self.assertTrue(context["packet"]["openable"])
            self.assertEqual(context["packet"]["url_path"], "/packets/learning/day/1")
            self.assertEqual(context["inspection_budget"]["max_items"], 5)

    def test_context_selects_due_recall_without_falling_back_to_learning(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            engine.initialize_course(self._course_payload())
            engine.start_day("sample-course", day_index=1, today="2026-05-22")
            paths = build_course_paths(workspace, "sample-course")
            store = CourseStore(paths)
            store.save_mastery(
                {
                    "scope_keywords": asdict(
                        MasteryRecord(
                            item_id="scope_keywords",
                            block_id="scope",
                            status="R0",
                            last_result="wrong",
                            last_confidence="high",
                        )
                    )
                }
            )
            store.save_review_queue(
                [
                    {
                        "item_id": "scope_keywords",
                        "block_id": "scope",
                        "status": "R0",
                        "priority": "urgent",
                        "last_result": "wrong",
                        "confidence": "high",
                        "next_review_day": 1,
                        "next_review_date": "2026-05-22",
                        "reason": "overconfidence error",
                    }
                ]
            )
            paths.recall_packet_html_file(day_index=1).unlink()

            context = engine.build_fresh_qa_context("sample-course", today="2026-05-22")

            self.assertEqual(context["packet"]["packet_type"], "recall")
            self.assertFalse(context["packet"]["exists"])
            self.assertFalse(context["packet"]["openable"])
            self.assertIn("missing selected recall packet", context["next_action"]["reason"])

    def test_phase1_context_excludes_answer_key_and_phase2_context_includes_it(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            engine.initialize_course(self._course_payload())
            engine.start_day("sample-course", day_index=1, today="2026-05-22")

            context = engine.build_fresh_qa_context("sample-course", today="2026-05-22")

            phase1_text = repr(context["phase1_context"])
            phase2_text = repr(context["phase2_context"])
            self.assertNotIn("auto, static, register", phase1_text)
            self.assertNotIn("One point for each keyword.", phase1_text)
            self.assertIn("auto, static, register", phase2_text)
            self.assertIn("scope-table.png", phase2_text)

    def test_phase2_context_is_limited_to_selected_packet_items(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = self._course_payload()
            payload["blocks"].extend(
                [
                    {
                        "block_id": "arrays",
                        "block_name": "Arrays",
                        "block_type": "concept",
                        "importance": "high",
                        "difficulty": "medium",
                        "exam_relevance": "high",
                        "needs_prereq": False,
                        "needs_visuals": False,
                        "study_order": 2,
                    },
                    {
                        "block_id": "late_topic",
                        "block_name": "Late Topic",
                        "block_type": "concept",
                        "importance": "high",
                        "difficulty": "medium",
                        "exam_relevance": "high",
                        "needs_prereq": False,
                        "needs_visuals": False,
                        "study_order": 3,
                    },
                ]
            )
            payload["blocks"][0]["study_order"] = 1
            payload["items"].extend(
                [
                    {
                        "item_id": "array_bounds",
                        "block_id": "arrays",
                        "prompt": "Explain array bounds.",
                        "answer_mode": "short-answer",
                        "difficulty": "medium",
                        "exam_relevance": "high",
                        "needs_visuals": False,
                        "answer_key": "Array indexes start at 0 and end at length - 1.",
                    },
                    {
                        "item_id": "late_topic_item",
                        "block_id": "late_topic",
                        "prompt": "Explain the late topic.",
                        "answer_mode": "short-answer",
                        "difficulty": "medium",
                        "exam_relevance": "high",
                        "needs_visuals": False,
                        "answer_key": "late_topic_answer",
                    },
                ]
            )
            engine = StudyEngine(workspace)
            engine.initialize_course(payload)
            engine.start_day("sample-course", day_index=1, today="2026-05-22")

            context = engine.build_fresh_qa_context("sample-course", today="2026-05-22")

            phase2_text = repr(context["phase2_context"])
            self.assertIn("Array indexes start at 0", phase2_text)
            self.assertNotIn("late_topic_answer", phase2_text)

    def test_list_active_course_slugs_returns_initialized_courses(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            engine.initialize_course(self._course_payload("course-b"))
            engine.initialize_course(self._course_payload("course-a"))

            self.assertEqual(engine.list_active_course_slugs(), ["course-a", "course-b"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused failing test**

Run:

```bash
python3.13 -m unittest tests.core.test_engine_fresh_qa
```

Expected:

```text
AttributeError: 'StudyEngine' object has no attribute 'build_fresh_qa_context'
```

- [ ] **Step 3: Add imports and packet item-id pattern to `study_os/core/engine.py`**

Modify the import block near the top of `study_os/core/engine.py`:

```python
from dataclasses import asdict, replace
from html import unescape
from pathlib import Path
import re
import shutil
from typing import Any

from study_os.core.close_session_draft import build_close_session_draft
from study_os.core.constants import STATUS_ORDER
from study_os.core.fresh_qa import FRESH_QA_AXES
from study_os.core.models import Block, CourseConfig, ExecutionReceipt, Item, MasteryRecord, QueueEntry, VisualRequirement
```

Add this module constant near `_FALLBACK_STUDY_ORDER`:

```python
_PACKET_ITEM_ID_PATTERN = re.compile(r'<article class="packet-entry" data-item-id="([^"]+)">')
```

- [ ] **Step 4: Add packet context helpers to `StudyEngine`**

Add these methods inside `StudyEngine`, before `initialize_course`:

```python
    def list_active_course_slugs(self) -> list[str]:
        courses_root = self.workspace_root / "courses"
        if not courses_root.exists():
            return []
        return sorted(
            path.name
            for path in courses_root.iterdir()
            if path.is_dir() and (path / "course.yaml").exists()
        )

    def build_fresh_qa_context(self, course_slug: str, *, today: str) -> dict[str, Any]:
        validate_course_slug_text(course_slug)
        validate_iso_date_text(today, "today")
        paths = build_course_paths(self.workspace_root, course_slug)
        if not paths.course_file.exists():
            raise ValidationError(f"unknown course_slug: {course_slug}")

        store = CourseStore(paths)
        course = CourseConfig(**store.load_course())
        items = [Item(**payload) for payload in store.load_items()]
        visuals = [VisualRequirement(**payload) for payload in store.load_visual_requirements()]
        review_queue = [QueueEntry(**payload) for payload in store.load_review_queue()]
        current_day = course.current_day
        due_review_entries = [
            entry
            for entry in review_queue
            if current_day > 0 and _review_entry_is_due(entry, day_index=current_day, today=today)
        ]
        packet_type = "recall" if due_review_entries else "learning"

        if current_day <= 0:
            return self._fresh_qa_missing_day_context(
                course=course,
                today=today,
                reason="No generated study day exists for this course.",
            )

        html_path = (
            paths.recall_packet_html_file(day_index=current_day)
            if packet_type == "recall"
            else paths.learning_packet_html_file(day_index=current_day)
        )
        markdown_path = paths.daily_dir / f"day_{current_day:02d}_{packet_type}.md"
        packet_exists = html_path.exists() and markdown_path.exists()
        packet = {
            "packet_type": packet_type,
            "day_index": current_day,
            "html_path": str(html_path),
            "markdown_path": str(markdown_path),
            "url_path": f"/packets/{packet_type}/day/{current_day}",
            "exists": packet_exists,
            "openable": packet_exists,
        }
        if packet_exists:
            next_action = {
                "kind": "open_packet",
                "label": f"Open day {current_day} {packet_type} packet",
                "reason": self._fresh_qa_next_action_reason(packet_type, due_review_entries),
            }
        else:
            next_action = {
                "kind": "packet_blocked",
                "label": f"Selected day {current_day} {packet_type} packet is missing",
                "reason": f"missing selected {packet_type} packet for current_day={current_day}",
            }

        due_item_ids = [entry.item_id for entry in due_review_entries]
        packet_item_ids = self._fresh_qa_packet_item_ids(html_path) if html_path.exists() else []
        selected_item_ids = set(packet_item_ids) or self._fresh_qa_selected_item_ids(packet_type, due_item_ids)
        phase2_items = [
            {
                "item_id": item.item_id,
                "block_id": item.block_id,
                "prompt": item.prompt,
                "answer_key": item.answer_key,
                "rubric": item.rubric,
                "common_mistakes": list(item.common_mistakes),
                "model_answer": item.model_answer,
                "worked_example": item.worked_example,
                "correction_ladder": list(item.correction_ladder),
                "source_refs": list(item.source_refs),
            }
            for item in items
            if item.item_id in selected_item_ids
        ]
        phase2_visuals = [
            {
                "item_id": visual.item_id,
                "block_id": visual.block_id,
                "description": visual.description,
                "required_image": visual.required_image,
                "status": visual.status,
            }
            for visual in visuals
            if visual.item_id in selected_item_ids or visual.block_id in {item["block_id"] for item in phase2_items}
        ]
        return {
            "course_slug": course.course_slug,
            "course_name": course.course_name,
            "today": today,
            "current_day": current_day,
            "next_action": next_action,
            "packet": packet,
            "review_pressure": {
                "due_count": len(due_review_entries),
                "urgent_count": sum(1 for entry in due_review_entries if entry.priority == "urgent"),
                "top_due_item_ids": due_item_ids[:5],
            },
            "inspection_budget": {
                "max_items": 5,
                "small_packet_limit": 5,
                "selection_rules": [
                    "include the first user-flow item",
                    "include at least one visual-dependent item when visible",
                    "include at least one urgent/high-risk/wrong/partial/uncertain/low-confidence item when visible",
                    "fill remaining slots from packet order",
                ],
            },
            "phase1_context": {
                "packet_type": packet_type,
                "day_index": current_day,
                "html_path": str(html_path),
                "markdown_path": str(markdown_path),
                "url_path": packet["url_path"],
                "packet_item_ids": packet_item_ids,
                "instructions": [
                    "Inspect the packet as a learner.",
                    "Write answers before using answer keys, rubrics, source refs, or hidden grading material.",
                    "Record confidence_score from 1 to 5 for each inspected item.",
                ],
            },
            "phase2_context": {
                "items": phase2_items,
                "visual_requirements": phase2_visuals,
                "grading_instructions": [
                    "Grade Phase 1 as correct, partial, wrong, or uncertain.",
                    "Diagnose whether failure came from packet, source_connection, rubric, visual_asset, learner_difficulty, or subagent.",
                    "Return every required fresh QA result field.",
                ],
            },
            "result_contract": {
                "required_fields": [
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
                ],
                "axes": list(FRESH_QA_AXES),
                "axis_values": ["OK", "WEAK", "BLOCKED", "NOT_CHECKED"],
                "gate_values": ["pass", "warn", "block"],
            },
        }
```

- [ ] **Step 5: Add private helper methods to `StudyEngine`**

Add these methods inside `StudyEngine`, before `_refresh_workspace_md`:

```python
    def _fresh_qa_missing_day_context(
        self,
        *,
        course: CourseConfig,
        today: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "course_slug": course.course_slug,
            "course_name": course.course_name,
            "today": today,
            "current_day": course.current_day,
            "next_action": {
                "kind": "generate_day",
                "label": "Generate the first daily packet",
                "reason": reason,
                "command": f"study_os --workspace {self.workspace_root} start-day --course {course.course_slug} --day 1 --today {today}",
            },
            "packet": {
                "packet_type": "learning",
                "day_index": None,
                "html_path": "",
                "markdown_path": "",
                "url_path": "",
                "exists": False,
                "openable": False,
            },
            "review_pressure": {
                "due_count": 0,
                "urgent_count": 0,
                "top_due_item_ids": [],
            },
            "inspection_budget": {
                "max_items": 5,
                "small_packet_limit": 5,
                "selection_rules": [
                    "create the next daily packet before black-box QA",
                ],
            },
            "phase1_context": {},
            "phase2_context": {},
            "result_contract": {
                "required_fields": [
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
                ],
                "axes": list(FRESH_QA_AXES),
                "axis_values": ["OK", "WEAK", "BLOCKED", "NOT_CHECKED"],
                "gate_values": ["pass", "warn", "block"],
            },
        }

    def _fresh_qa_next_action_reason(self, packet_type: str, due_review_entries: list[QueueEntry]) -> str:
        if packet_type == "recall":
            urgent_count = sum(1 for entry in due_review_entries if entry.priority == "urgent")
            return f"{len(due_review_entries)} review entries are due; {urgent_count} are urgent."
        return "No due review entries; continue the current learning packet."

    def _fresh_qa_selected_item_ids(
        self,
        packet_type: str,
        due_item_ids: list[str],
    ) -> set[str]:
        if packet_type == "recall":
            return set(due_item_ids)
        return set()

    def _fresh_qa_packet_item_ids(self, html_path: Path) -> list[str]:
        try:
            html_text = html_path.read_text(encoding="utf-8")
        except OSError:
            return []
        item_ids: list[str] = []
        seen: set[str] = set()
        for match in _PACKET_ITEM_ID_PATTERN.finditer(html_text):
            item_id = unescape(match.group(1))
            if item_id not in seen:
                item_ids.append(item_id)
                seen.add(item_id)
        return item_ids
```

- [ ] **Step 6: Run focused engine tests**

Run:

```bash
python3.13 -m unittest tests.core.test_engine_fresh_qa
```

Expected:

```text
Ran 5 tests

OK
```

- [ ] **Step 7: Commit Task 3**

Run:

```bash
git add study_os/core/engine.py tests/core/test_engine_fresh_qa.py
git commit -m "feat: resolve daily fresh qa packet context"
```

Expected:

```text
commit summary includes "feat: resolve daily fresh qa packet context" and the command exits 0
```

## Task 4: CLI Context And Report Commands

**Files:**
- Modify: `study_os/cli.py`
- Modify: `tests/test_cli_smoke.py`

- [ ] **Step 1: Add failing CLI smoke tests**

Append these imports near the top of `tests/test_cli_smoke.py`:

```python
from study_os.core.fresh_qa import FRESH_QA_AXES
```

Append these methods inside `CliSmokeTest`:

```python
    def _start_day_for_sample_course(self, workspace: Path) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "study_os",
                "--workspace",
                str(workspace),
                "start-day",
                "--course",
                "sample-course",
                "--day",
                "1",
                "--today",
                "2026-05-22",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_fresh_qa_context_outputs_all_active_course_contexts(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)
            self._start_day_for_sample_course(workspace)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "fresh-qa-context",
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["today"], "2026-05-22")
            self.assertEqual(len(payload["courses"]), 1)
            self.assertEqual(payload["courses"][0]["course_slug"], "sample-course")
            self.assertIn("phase1_context", payload["courses"][0])

    def test_fresh_qa_report_renders_valid_result_json(self) -> None:
        with TemporaryDirectory() as tmp:
            result_file = Path(tmp) / "fresh-qa-result.json"
            result_file.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "course_slug": "sample-course",
                                "packet_type": "learning",
                                "day_index": 1,
                                "next_action": {
                                    "kind": "open_packet",
                                    "label": "Open day 1 learning packet",
                                    "reason": "No due review entries.",
                                },
                                "phase1_attempts": [
                                    {
                                        "item_id": "scope_keywords",
                                        "answerable_from_packet": True,
                                        "draft_answer": "A concise answer.",
                                        "confidence_score": 4,
                                        "visible_blockers": [],
                                        "answer_first_supported": True,
                                    }
                                ],
                                "phase2_grading": [
                                    {
                                        "item_id": "scope_keywords",
                                        "result": "correct",
                                        "grading_rationale": "Matches answer key.",
                                        "self_grading_supported": True,
                                        "source_connection_supported": True,
                                        "exam_plausibility": "high",
                                        "failure_source": "none",
                                    }
                                ],
                                "axis_scorecard": {axis: "OK" for axis in FRESH_QA_AXES},
                                "highest_answer_rate_blocker": "None.",
                                "fix_priority": {
                                    "summary": "Keep monitoring.",
                                    "axis": "exam_transfer",
                                    "recommended_action": "Run the next daily fresh QA.",
                                },
                                "gate": "pass",
                                "failure_type": "pass",
                                "evidence": {
                                    "packet_path": "/tmp/day_01_learning.html",
                                    "source_refs": [],
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "fresh-qa-report",
                    "--result-file",
                    str(result_file),
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("# Daily Fresh QA - 2026-05-22", completed.stdout)
            self.assertIn("sample-course", completed.stdout)
            self.assertIn("정답률 영향: positive", completed.stdout)
```

Update `test_help_lists_core_commands` to assert the new commands:

```python
        self.assertIn("fresh-qa-context", completed.stdout)
        self.assertIn("fresh-qa-report", completed.stdout)
```

- [ ] **Step 2: Run failing CLI tests**

Run:

```bash
python3.13 -m unittest tests.test_cli_smoke.CliSmokeTest.test_help_lists_core_commands tests.test_cli_smoke.CliSmokeTest.test_fresh_qa_context_outputs_all_active_course_contexts tests.test_cli_smoke.CliSmokeTest.test_fresh_qa_report_renders_valid_result_json
```

Expected:

```text
AssertionError: 'fresh-qa-context' not found
```

- [ ] **Step 3: Add imports and command help to `study_os/cli.py`**

Modify the imports and `COMMAND_HELP`:

```python
import argparse
import json
from pathlib import Path
import sys
from typing import Any

from study_os.core.engine import StudyEngine
from study_os.core.fresh_qa import render_daily_fresh_qa_report
from study_os.core.packet_server import PacketServer, validate_close_session_draft_params
from study_os.core.paths import build_course_paths
from study_os.core.validation import ValidationError, validate_course_slug_text
```

```python
COMMAND_HELP = {
    "init-course": "Write a validated course snapshot from a request file.",
    "start-day": "Generate daily learning and recall packets for a course.",
    "close-session": "Apply a validated session update request.",
    "draft-close-session": "Build a close-session request draft from saved packet progress.",
    "start-final-recall": "Generate the exam-near final recall pack.",
    "status": "Show a compact course status summary.",
    "serve-packets": "Serve HTML packets and immediate packet-progress writes for a course.",
    "fresh-qa-context": "Print next-packet context for daily fresh black-box QA.",
    "fresh-qa-report": "Validate fresh QA result JSON and render a Korean daily report.",
}
```

- [ ] **Step 4: Add result file loader to `study_os/cli.py`**

Add this helper after `_load_request_file`:

```python
def _load_fresh_qa_results(path: str) -> list[dict[str, Any]]:
    request_path = Path(path)
    try:
        raw_text = request_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"fresh QA result file not found: {request_path}") from exc
    except OSError as exc:
        raise ValidationError(f"fresh QA result file could not be read: {request_path}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"fresh QA result file is not valid JSON: {request_path}") from exc

    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ValidationError("fresh QA result file must contain a result object, a result list, or a results mapping")
```

- [ ] **Step 5: Add parsers in `build_parser()`**

Add these parser definitions after the `serve-packets` parser:

```python
    fresh_context_parser = subparsers.add_parser(
        "fresh-qa-context",
        help=COMMAND_HELP["fresh-qa-context"],
    )
    fresh_context_parser.add_argument("--today", required=True)
    fresh_context_parser.add_argument("--course")

    fresh_report_parser = subparsers.add_parser(
        "fresh-qa-report",
        help=COMMAND_HELP["fresh-qa-report"],
    )
    fresh_report_parser.add_argument("--result-file", required=True)
    fresh_report_parser.add_argument("--today", required=True)
```

- [ ] **Step 6: Add command handling in `main()`**

Add these branches after `engine = StudyEngine(Path(parsed.workspace))` and before `init-course` handling:

```python
        if parsed.command == "fresh-qa-context":
            course_slugs = [parsed.course] if parsed.course else engine.list_active_course_slugs()
            contexts = [
                engine.build_fresh_qa_context(course_slug, today=parsed.today)
                for course_slug in course_slugs
            ]
            print(json.dumps({"today": parsed.today, "courses": contexts}, ensure_ascii=False, indent=2))
            return 0

        if parsed.command == "fresh-qa-report":
            results = _load_fresh_qa_results(parsed.result_file)
            print(render_daily_fresh_qa_report(results, today=parsed.today), end="")
            return 0
```

- [ ] **Step 7: Run focused CLI tests**

Run:

```bash
python3.13 -m unittest tests.test_cli_smoke.CliSmokeTest.test_help_lists_core_commands tests.test_cli_smoke.CliSmokeTest.test_fresh_qa_context_outputs_all_active_course_contexts tests.test_cli_smoke.CliSmokeTest.test_fresh_qa_report_renders_valid_result_json
```

Expected:

```text
Ran 3 tests

OK
```

- [ ] **Step 8: Commit Task 4**

Run:

```bash
git add study_os/cli.py tests/test_cli_smoke.py
git commit -m "feat: expose fresh qa cli"
```

Expected:

```text
commit summary includes "feat: expose fresh qa cli" and the command exits 0
```

## Task 5: Full Verification And Runtime QA

**Files:**
- No new files required.
- Runtime commands read `study-workspace` but do not mutate canonical state files.

- [ ] **Step 1: Run the repository verification script**

Run:

```bash
bash scripts/check.sh
```

Expected:

```text
OK
```

If the script prints individual `unittest` output instead of a single `OK`, the acceptable result is all tests passing with exit code `0`.

- [ ] **Step 2: Generate fresh QA contexts for every active runtime course**

Run:

```bash
python3.13 -m study_os --workspace study-workspace fresh-qa-context --today 2026-05-22 > /tmp/study-os-fresh-qa-contexts.json
python3.13 -m json.tool /tmp/study-os-fresh-qa-contexts.json > /tmp/study-os-fresh-qa-contexts.pretty.json
```

Expected:

```text
no output from json.tool and exit code 0
```

Then confirm both active course slugs are present:

```bash
rg '"course_slug": "basic-computer-programming-final"|"course_slug": "software-engineering-midterm-testflight"' /tmp/study-os-fresh-qa-contexts.pretty.json
```

Expected:

```text
"course_slug": "basic-computer-programming-final"
"course_slug": "software-engineering-midterm-testflight"
```

- [ ] **Step 3: Split context files and run fresh black-box QA with separate evaluator contexts**

Split the all-course context into one file per course:

```bash
python3.13 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/study-os-fresh-qa-contexts.json").read_text(encoding="utf-8"))
for course in payload["courses"]:
    path = Path(f"/tmp/study-os-fresh-qa-context-{course['course_slug']}.json")
    path.write_text(json.dumps(course, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
PY
```

Expected:

```text
/tmp/study-os-fresh-qa-context-basic-computer-programming-final.json
/tmp/study-os-fresh-qa-context-software-engineering-midterm-testflight.json
```

Use `superpowers:subagent-driven-development` and dispatch one fresh subagent per course. Give each subagent only the matching context file path.

Prompt template for each subagent:

```text
You are a fresh black-box Study OS QA evaluator. You have no prior conversation context.

Goal: determine whether the next packet can improve exam answer accuracy for the given course.

Rules:
- Phase 1: use only phase1_context and the visible packet file/path. Do not inspect phase2_context, answer keys, rubrics, source refs, model answers, or common mistakes before writing Phase 1 attempts.
- Inspect all items if the packet has 5 or fewer visible items. Inspect 5 items if the packet is larger.
- Your inspected set must include the first user-flow item, at least one visual-dependent item when visible, at least one urgent/high-risk/wrong/partial/uncertain/low-confidence item when visible, and remaining items from packet order.
- Phase 2: after Phase 1 is complete, use phase2_context to grade and diagnose.
- Return only JSON matching result_contract.required_fields.
- Use axis values only from OK, WEAK, BLOCKED, NOT_CHECKED.
- Use gate only from pass, warn, block.
- Do not mutate Study OS state files.
- Read exactly one course context file: /tmp/study-os-fresh-qa-context-basic-computer-programming-final.json or /tmp/study-os-fresh-qa-context-software-engineering-midterm-testflight.json.
- Write the result JSON to /tmp/study-os-fresh-qa-result-basic-computer-programming-final.json or /tmp/study-os-fresh-qa-result-software-engineering-midterm-testflight.json, matching the course you evaluated.
```

Expected: each subagent writes one JSON object with `course_slug`, `phase1_attempts`, `phase2_grading`, `axis_scorecard`, `highest_answer_rate_blocker`, `fix_priority`, `gate`, and `evidence`.

- [ ] **Step 4: Validate the fresh QA results and render the daily report**

Combine the two subagent result files into the result wrapper:

```bash
python3.13 - <<'PY'
import json
from pathlib import Path

paths = [
    Path("/tmp/study-os-fresh-qa-result-basic-computer-programming-final.json"),
    Path("/tmp/study-os-fresh-qa-result-software-engineering-midterm-testflight.json"),
]
results = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
Path("/tmp/study-os-fresh-qa-results.json").write_text(
    json.dumps({"results": results}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("/tmp/study-os-fresh-qa-results.json")
PY
```

Then run:

```bash
python3.13 -m study_os fresh-qa-report --result-file /tmp/study-os-fresh-qa-results.json --today 2026-05-22 > /tmp/study-os-fresh-qa-report.md
python3.13 -m json.tool /tmp/study-os-fresh-qa-results.json > /tmp/study-os-fresh-qa-results.pretty.json
rg '# Daily Fresh QA - 2026-05-22|Global Fix Priority|basic-computer-programming-final|software-engineering-midterm-testflight|정답률 영향' /tmp/study-os-fresh-qa-report.md
```

Expected:

```text
# Daily Fresh QA - 2026-05-22
## Global Fix Priority
- 정답률 영향:
```

The `rg` output must include both course slugs before this task is considered complete.

- [ ] **Step 5: Confirm no runtime canonical state was mutated by context/report commands**

Run:

```bash
git status --short -- study_os/core/fresh_qa.py study_os/core/engine.py study_os/cli.py tests/core/test_fresh_qa.py tests/core/test_engine_fresh_qa.py tests/test_cli_smoke.py study-workspace/courses
```

Expected:

```text
 M study_os/core/engine.py
 M study_os/cli.py
?? study_os/core/fresh_qa.py
?? tests/core/test_engine_fresh_qa.py
?? tests/core/test_fresh_qa.py
```

The expected output may omit files that were already committed in earlier tasks. It must not show modifications under:

```text
study-workspace/courses/*/state/mastery.json
study-workspace/courses/*/state/review_queue.yaml
study-workspace/courses/*/state/error_log.jsonl
study-workspace/courses/*/state/session_history.jsonl
```

- [ ] **Step 6: Commit Task 5 if runtime QA required small code/test fixes**

If Task 5 required code or test fixes, run:

```bash
git add study_os/core/fresh_qa.py study_os/core/engine.py study_os/cli.py tests/core/test_fresh_qa.py tests/core/test_engine_fresh_qa.py tests/test_cli_smoke.py
git commit -m "test: verify daily fresh qa workflow"
```

Expected:

```text
commit summary includes "test: verify daily fresh qa workflow" and the command exits 0
```

If Task 5 only produced `/tmp` QA artifacts and no repository files changed, skip this commit and record the verification commands in the final handoff.

## Implementation Notes

- This plan intentionally keeps Codex subagent dispatch outside `study_os` Python code. The Python package should remain reusable from shell scripts, daily automations, and human-in-the-loop Codex sessions.
- The context command is read-only. It may read private runtime source metadata but must not write course state.
- The report command validates and renders JSON. It must not treat subagent attempts as real learner performance.
- Phase 1/Phase 2 separation depends on the orchestrator passing `phase2_context` only after Phase 1 is completed. The engine makes that split explicit and testable.
- The resolver's due-review rule is conservative: recall outranks learning when due entries exist. If this exposes a weak or missing recall packet, the QA result should warn or block rather than hide the issue.

## Completion Criteria

- `python3.13 -m unittest tests.core.test_fresh_qa` passes.
- `python3.13 -m unittest tests.core.test_engine_fresh_qa` passes.
- Focused CLI smoke tests for `fresh-qa-context` and `fresh-qa-report` pass.
- `bash scripts/check.sh` exits `0`.
- Runtime context generation includes `basic-computer-programming-final` and `software-engineering-midterm-testflight`.
- Runtime fresh QA report includes both courses, one global fix priority, a 9-axis scorecard, and answer-rate effect.
- Runtime context/report commands do not mutate canonical course state.
