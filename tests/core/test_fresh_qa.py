from collections import UserDict
import re
import unittest

from study_os.core.fresh_qa import (
    FRESH_QA_AXES,
    normalize_fresh_qa_result,
    render_daily_fresh_qa_report,
    select_global_fix_priority,
)


def complete_pass_result() -> dict:
    return {
        "course_slug": "software-engineering-midterm-testflight",
        "packet_type": "recall",
        "day_index": 3,
        "next_action": {"type": "keep_current_packet"},
        "failure_type": "pass",
        "phase1_attempts": [
            {
                "item_id": "sequence_diagram_trace",
                "answerable_from_packet": True,
                "draft_answer": "List the valid message order and guard condition.",
                "confidence_score": 4,
                "visible_blockers": [],
                "answer_first_supported": True,
            }
        ],
        "phase2_grading": [
            {
                "item_id": "sequence_diagram_trace",
                "result": "correct",
                "grading_rationale": "The answer includes order, guard, and trace condition.",
                "self_grading_supported": True,
                "source_connection_supported": True,
                "exam_plausibility": "high",
                "failure_source": "none",
            }
        ],
        "axis_scorecard": {axis: "OK" for axis in FRESH_QA_AXES},
        "highest_answer_rate_blocker": "none",
        "fix_priority": {},
        "gate": "pass",
        "evidence": {"summary": "packet day 3 recall item sequence_diagram_trace"},
    }


def add_fix_priority(payload: dict, axis: str = "outcome_measurement") -> None:
    payload["fix_priority"] = {
        "summary": "Repair the failed fresh QA axis.",
        "axis": axis,
        "recommended_action": "Make the next daily evolution fix specific and testable.",
    }


class FreshQAResultTest(unittest.TestCase):
    def test_accepts_complete_pass_result(self) -> None:
        result = normalize_fresh_qa_result(complete_pass_result())

        self.assertEqual("pass", result["computed_gate"])
        self.assertEqual("positive", result["predicted_answer_rate_effect"])
        self.assertEqual({axis: "OK" for axis in FRESH_QA_AXES}, result["axis_scorecard"])

    def test_stricter_submitted_gate_controls_predicted_effect(self) -> None:
        payload = complete_pass_result()
        payload["gate"] = "block"
        add_fix_priority(payload)

        result = normalize_fresh_qa_result(payload)

        self.assertEqual("block", result["gate"])
        self.assertEqual("pass", result["computed_gate"])
        self.assertEqual("negative", result["predicted_answer_rate_effect"])

    def test_accepts_mapping_axis_scorecard(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"] = UserDict({axis: "OK" for axis in FRESH_QA_AXES})

        result = normalize_fresh_qa_result(payload)

        self.assertEqual("pass", result["computed_gate"])
        self.assertEqual("positive", result["predicted_answer_rate_effect"])

    def test_normalizes_top_level_mapping_payload_to_plain_dict(self) -> None:
        result = normalize_fresh_qa_result(UserDict(complete_pass_result()))

        self.assertIs(type(result), dict)

    def test_normalizes_mapping_axis_scorecard_to_plain_dict(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"] = UserDict({axis: "OK" for axis in FRESH_QA_AXES})

        result = normalize_fresh_qa_result(payload)

        self.assertIs(type(result["axis_scorecard"]), dict)

    def test_failure_type_requires_minimum_gate(self) -> None:
        cases = [
            ("packet_blocked", "pass", "block"),
            ("learning_weak", "pass", "warn"),
            ("grading_blocked", "pass", "warn"),
            ("subagent_failed", "pass", "warn"),
        ]
        for failure_type, submitted_gate, computed_gate in cases:
            with self.subTest(failure_type=failure_type):
                payload = complete_pass_result()
                payload["failure_type"] = failure_type
                payload["gate"] = submitted_gate
                add_fix_priority(payload)

                with self.assertRaisesRegex(ValueError, "weaker gate"):
                    normalize_fresh_qa_result(payload)

                payload["gate"] = computed_gate
                result = normalize_fresh_qa_result(payload)
                self.assertEqual(computed_gate, result["computed_gate"])

    def test_blocked_axis_overrides_warn_failure_type_minimum_gate(self) -> None:
        payload = complete_pass_result()
        payload["failure_type"] = "grading_blocked"
        payload["axis_scorecard"]["visual_source_connection"] = "BLOCKED"
        payload["gate"] = "warn"
        add_fix_priority(payload, "visual_source_connection")

        with self.assertRaisesRegex(ValueError, "weaker gate"):
            normalize_fresh_qa_result(payload)

        payload["gate"] = "block"
        result = normalize_fresh_qa_result(payload)
        self.assertEqual("block", result["computed_gate"])

    def test_grading_blocked_requires_block_when_self_grading_impossible(self) -> None:
        payload = complete_pass_result()
        payload["failure_type"] = "grading_blocked"
        payload["phase2_grading"][0]["result"] = "uncertain"
        payload["phase2_grading"][0]["self_grading_supported"] = False
        payload["phase2_grading"][0]["failure_source"] = "rubric"
        payload["gate"] = "warn"
        add_fix_priority(payload)

        with self.assertRaisesRegex(ValueError, "weaker gate"):
            normalize_fresh_qa_result(payload)

        payload["gate"] = "block"
        result = normalize_fresh_qa_result(payload)
        self.assertEqual("block", result["computed_gate"])

    def test_grading_blocked_accepts_warn_when_self_grading_supported(self) -> None:
        payload = complete_pass_result()
        payload["failure_type"] = "grading_blocked"
        payload["phase2_grading"][0]["self_grading_supported"] = True
        payload["gate"] = "warn"
        add_fix_priority(payload)

        result = normalize_fresh_qa_result(payload)

        self.assertEqual("warn", result["computed_gate"])

    def test_normalizes_nested_mappings_to_plain_dicts(self) -> None:
        payload = complete_pass_result()
        payload["next_action"] = UserDict({"type": "keep_current_packet"})
        payload["fix_priority"] = UserDict({"first": "source_connection"})
        payload["evidence"] = UserDict({"summary": "packet evidence"})
        payload["phase1_attempts"][0] = UserDict(payload["phase1_attempts"][0])
        payload["phase2_grading"][0] = UserDict(payload["phase2_grading"][0])

        result = normalize_fresh_qa_result(payload)

        self.assertIs(type(result["next_action"]), dict)
        self.assertIs(type(result["fix_priority"]), dict)
        self.assertIs(type(result["evidence"]), dict)
        self.assertIs(type(result["phase1_attempts"][0]), dict)
        self.assertIs(type(result["phase2_grading"][0]), dict)

    def test_recursively_normalizes_nested_mappings_to_plain_dicts(self) -> None:
        payload = complete_pass_result()
        payload["next_action"] = UserDict({"nested": UserDict({"mode": "repair"})})
        payload["fix_priority"] = UserDict({"nested": UserDict({"axis": "exam_transfer"})})
        payload["evidence"] = UserDict({"nested": UserDict({"source": "packet"})})
        payload["phase1_attempts"][0]["extra"] = UserDict({"nested": UserDict({"tag": "p1"})})
        payload["phase2_grading"][0]["extra"] = UserDict({"nested": UserDict({"tag": "p2"})})

        result = normalize_fresh_qa_result(payload)

        self.assertIs(type(result["next_action"]["nested"]), dict)
        self.assertIs(type(result["fix_priority"]["nested"]), dict)
        self.assertIs(type(result["evidence"]["nested"]), dict)
        self.assertIs(type(result["phase1_attempts"][0]["extra"]), dict)
        self.assertIs(type(result["phase1_attempts"][0]["extra"]["nested"]), dict)
        self.assertIs(type(result["phase2_grading"][0]["extra"]), dict)
        self.assertIs(type(result["phase2_grading"][0]["extra"]["nested"]), dict)

    def test_rejects_missing_phase2_grading(self) -> None:
        payload = complete_pass_result()
        del payload["phase2_grading"]

        with self.assertRaisesRegex(ValueError, "missing required field: phase2_grading"):
            normalize_fresh_qa_result(payload)

    def test_rejects_non_mapping_top_level_payload(self) -> None:
        for payload in (None, 3):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "bad payload: expected mapping"):
                    normalize_fresh_qa_result(payload)

    def test_rejects_invalid_top_level_field_types_and_values(self) -> None:
        invalid_cases = [
            ("course_slug", None, "bad course_slug"),
            ("packet_type", 3, "bad packet_type"),
            ("packet_type", "quiz", "bad packet_type"),
            ("day_index", True, "bad day_index"),
            ("day_index", 0, "bad day_index"),
            ("next_action", [], "bad next_action"),
            ("highest_answer_rate_blocker", "", "bad highest_answer_rate_blocker"),
            ("fix_priority", [3], "bad fix_priority"),
            ("gate", "hold", "bad gate"),
            ("evidence", None, "bad evidence"),
        ]
        for field, value, message in invalid_cases:
            with self.subTest(field=field, value=value):
                payload = complete_pass_result()
                payload[field] = value

                with self.assertRaisesRegex(ValueError, message):
                    normalize_fresh_qa_result(payload)

    def test_rejects_invalid_fix_priority_axis(self) -> None:
        payload = complete_pass_result()
        payload["fix_priority"] = {
            "summary": "Repair the packet.",
            "axis": "visuals",
            "recommended_action": "Use a valid 9-axis key.",
        }

        with self.assertRaisesRegex(ValueError, "bad fix_priority.axis"):
            normalize_fresh_qa_result(payload)

    def test_rejects_invalid_axis_value(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"]["exam_transfer"] = "MAYBE"

        with self.assertRaisesRegex(ValueError, "bad axis value"):
            normalize_fresh_qa_result(payload)

    def test_rejects_non_string_axis_scorecard_keys(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"] = {
            **{axis: "OK" for axis in FRESH_QA_AXES},
            1: "OK",
            None: "OK",
        }

        with self.assertRaisesRegex(ValueError, "bad axis key"):
            normalize_fresh_qa_result(payload)

    def test_requires_block_gate_when_any_axis_is_blocked(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"]["visual_source_connection"] = "BLOCKED"
        payload["gate"] = "warn"
        add_fix_priority(payload, "visual_source_connection")

        with self.assertRaisesRegex(ValueError, "weaker gate"):
            normalize_fresh_qa_result(payload)

    def test_rejects_confidence_score_outside_1_to_5(self) -> None:
        payload = complete_pass_result()
        payload["phase1_attempts"][0]["confidence_score"] = 6

        with self.assertRaisesRegex(ValueError, "bad confidence score"):
            normalize_fresh_qa_result(payload)

    def test_rejects_bool_confidence_score(self) -> None:
        payload = complete_pass_result()
        payload["phase1_attempts"][0]["confidence_score"] = True

        with self.assertRaisesRegex(ValueError, "bad confidence score"):
            normalize_fresh_qa_result(payload)

    def test_rejects_malformed_phase1_attempt_row(self) -> None:
        payload = complete_pass_result()
        payload["phase1_attempts"] = [None]

        with self.assertRaisesRegex(ValueError, r"bad phase1_attempts\[0\]"):
            normalize_fresh_qa_result(payload)

    def test_rejects_malformed_phase2_grading_row(self) -> None:
        payload = complete_pass_result()
        payload["phase2_grading"] = [3]

        with self.assertRaisesRegex(ValueError, r"bad phase2_grading\[0\]"):
            normalize_fresh_qa_result(payload)

    def test_rejects_invalid_phase1_field_types_and_values(self) -> None:
        invalid_cases = [
            ("item_id", "", "bad phase1_attempts[0].item_id"),
            ("answerable_from_packet", "yes", "bad phase1_attempts[0].answerable_from_packet"),
            ("draft_answer", None, "bad phase1_attempts[0].draft_answer"),
            ("visible_blockers", "none", "bad phase1_attempts[0].visible_blockers"),
            ("visible_blockers", [3], "bad phase1_attempts[0].visible_blockers[0]"),
            ("answer_first_supported", "yes", "bad phase1_attempts[0].answer_first_supported"),
        ]
        for field, value, message in invalid_cases:
            with self.subTest(field=field, value=value):
                payload = complete_pass_result()
                payload["phase1_attempts"][0][field] = value

                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    normalize_fresh_qa_result(payload)

    def test_rejects_invalid_phase2_field_types_and_values(self) -> None:
        invalid_cases = [
            ("item_id", "", "bad phase2_grading[0].item_id"),
            ("result", "mostly", "bad grading result"),
            ("grading_rationale", "", "bad phase2_grading[0].grading_rationale"),
            ("self_grading_supported", "yes", "bad phase2_grading[0].self_grading_supported"),
            (
                "source_connection_supported",
                "yes",
                "bad phase2_grading[0].source_connection_supported",
            ),
            ("exam_plausibility", "", "bad phase2_grading[0].exam_plausibility"),
            ("failure_source", "notes", "bad failure_source"),
        ]
        for field, value, message in invalid_cases:
            with self.subTest(field=field, value=value):
                payload = complete_pass_result()
                payload["phase2_grading"][0][field] = value

                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    normalize_fresh_qa_result(payload)

    def test_rejects_phase2_item_without_matching_phase1_attempt(self) -> None:
        payload = complete_pass_result()
        payload["phase2_grading"][0]["item_id"] = "not_attempted"

        with self.assertRaisesRegex(ValueError, "phase2 item without phase1 attempt"):
            normalize_fresh_qa_result(payload)

    def test_rejects_phase1_attempt_without_phase2_grading(self) -> None:
        payload = complete_pass_result()
        payload["phase1_attempts"].append(
            {
                "item_id": "ungraded_attempt",
                "answerable_from_packet": True,
                "draft_answer": "Second answer.",
                "confidence_score": 3,
                "visible_blockers": [],
                "answer_first_supported": True,
            }
        )

        with self.assertRaisesRegex(ValueError, "phase1 attempt without phase2 grading"):
            normalize_fresh_qa_result(payload)

    def test_rejects_duplicate_phase2_grading_item_id(self) -> None:
        payload = complete_pass_result()
        payload["phase2_grading"].append(dict(payload["phase2_grading"][0]))

        with self.assertRaisesRegex(ValueError, "duplicate phase2 grading item_id"):
            normalize_fresh_qa_result(payload)

    def test_rejects_pass_gate_when_any_grading_result_is_not_correct(self) -> None:
        payload = complete_pass_result()
        payload["phase2_grading"][0]["result"] = "wrong"
        payload["phase2_grading"][0]["failure_source"] = "learner_difficulty"
        payload["gate"] = "pass"

        with self.assertRaisesRegex(ValueError, "weaker gate"):
            normalize_fresh_qa_result(payload)

    def test_rejects_correct_result_when_packet_or_grading_support_is_missing(self) -> None:
        payload = complete_pass_result()
        payload["phase1_attempts"][0]["answerable_from_packet"] = False
        payload["phase1_attempts"][0]["answer_first_supported"] = False
        payload["phase1_attempts"][0]["visible_blockers"] = ["required diagram was not visible"]
        payload["phase2_grading"][0]["result"] = "correct"
        payload["phase2_grading"][0]["self_grading_supported"] = False
        payload["phase2_grading"][0]["source_connection_supported"] = False
        payload["phase2_grading"][0]["failure_source"] = "none"

        with self.assertRaisesRegex(ValueError, "inconsistent phase2_grading"):
            normalize_fresh_qa_result(payload)

    def test_accepts_visual_asset_failure_when_self_grading_and_source_are_blocked(self) -> None:
        payload = complete_pass_result()
        payload["failure_type"] = "grading_blocked"
        payload["phase1_attempts"][0]["answerable_from_packet"] = False
        payload["phase1_attempts"][0]["answer_first_supported"] = False
        payload["phase1_attempts"][0]["visible_blockers"] = ["required visual was missing"]
        payload["phase2_grading"][0]["result"] = "uncertain"
        payload["phase2_grading"][0]["self_grading_supported"] = False
        payload["phase2_grading"][0]["source_connection_supported"] = False
        payload["phase2_grading"][0]["failure_source"] = "visual_asset"
        payload["axis_scorecard"]["visual_source_connection"] = "BLOCKED"
        payload["axis_scorecard"]["pdf_visual_intake"] = "BLOCKED"
        payload["gate"] = "block"
        add_fix_priority(payload, "visual_source_connection")

        result = normalize_fresh_qa_result(payload)

        self.assertEqual("block", result["computed_gate"])

    def test_rejects_non_pass_result_without_actionable_fix_priority(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"]["visual_source_connection"] = "BLOCKED"
        payload["gate"] = "block"
        payload["fix_priority"] = {}

        with self.assertRaisesRegex(ValueError, "missing fix_priority.axis"):
            normalize_fresh_qa_result(payload)

    def test_rejects_non_pass_fix_priority_axis_that_is_not_a_failed_axis(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"]["visual_source_connection"] = "BLOCKED"
        payload["gate"] = "block"
        add_fix_priority(payload, "outcome_measurement")

        with self.assertRaisesRegex(ValueError, "fix_priority.axis must match"):
            normalize_fresh_qa_result(payload)

    def test_select_global_fix_priority_prefers_block_over_warn(self) -> None:
        warn_result = complete_pass_result()
        warn_result["course_slug"] = "course-warn"
        warn_result["axis_scorecard"]["exam_transfer"] = "WEAK"
        warn_result["gate"] = "warn"
        warn_result["highest_answer_rate_blocker"] = "Prompt is too generic."
        warn_result["fix_priority"] = {
            "summary": "Rewrite generic prompt.",
            "axis": "exam_transfer",
            "recommended_action": "Use exam-style question wording.",
        }
        block_result = complete_pass_result()
        block_result["course_slug"] = "course-block"
        block_result["axis_scorecard"]["grading_quality"] = "BLOCKED"
        block_result["gate"] = "block"
        block_result["highest_answer_rate_blocker"] = "Missing answer key."
        block_result["fix_priority"] = {
            "summary": "Add answer key.",
            "axis": "grading_quality",
            "recommended_action": "Attach answer key and rubric before next study session.",
        }

        priority = select_global_fix_priority([warn_result, block_result])

        self.assertEqual("course-block", priority["course_slug"])
        self.assertEqual("block", priority["gate"])
        self.assertEqual("Add answer key.", priority["summary"])

    def test_select_global_fix_priority_tie_breaks_to_lexicographically_later_course(self) -> None:
        earlier_result = complete_pass_result()
        earlier_result["course_slug"] = "alpha-course"
        earlier_result["axis_scorecard"]["exam_transfer"] = "WEAK"
        earlier_result["gate"] = "warn"
        earlier_result["highest_answer_rate_blocker"] = "Alpha blocker."
        earlier_result["fix_priority"] = {
            "summary": "Fix alpha.",
            "axis": "exam_transfer",
            "recommended_action": "Rewrite alpha prompt.",
        }
        later_result = complete_pass_result()
        later_result["course_slug"] = "zeta-course"
        later_result["axis_scorecard"]["exam_transfer"] = "WEAK"
        later_result["gate"] = "warn"
        later_result["highest_answer_rate_blocker"] = "Zeta blocker."
        later_result["fix_priority"] = {
            "summary": "Fix zeta.",
            "axis": "exam_transfer",
            "recommended_action": "Rewrite zeta prompt.",
        }

        priority = select_global_fix_priority([earlier_result, later_result])

        self.assertEqual("zeta-course", priority["course_slug"])
        self.assertEqual("Fix zeta.", priority["summary"])

    def test_select_global_fix_priority_empty_results_returns_stable_no_result_priority(self) -> None:
        priority = select_global_fix_priority([])

        self.assertEqual("", priority["course_slug"])
        self.assertEqual("pass", priority["gate"])
        self.assertIn("fresh QA", priority["summary"])
        self.assertEqual("outcome_measurement", priority["axis"])
        self.assertIn("fresh QA", priority["recommended_action"])
        self.assertEqual("No fresh QA result.", priority["highest_answer_rate_blocker"])

    def test_render_daily_fresh_qa_report_includes_priority_axes_blocker_and_packet_path(self) -> None:
        result = complete_pass_result()
        result["axis_scorecard"]["visual_source_connection"] = "WEAK"
        result["gate"] = "warn"
        result["highest_answer_rate_blocker"] = (
            "Diagram reference is visible but hard to inspect."
        )
        result["fix_priority"] = {
            "summary": "Expose the diagram crop beside the prompt.",
            "axis": "visual_source_connection",
            "recommended_action": "Render the required visual near the item.",
        }
        result["evidence"]["packet_path"] = "outputs/daily/day_03_recall.html"

        report = render_daily_fresh_qa_report([result], today="2026-05-22")

        self.assertIn("# Daily Fresh QA - 2026-05-22", report)
        self.assertIn("## Global Fix Priority", report)
        self.assertIn("정답률 영향", report)
        self.assertIn("visual_source_connection: WEAK", report)
        self.assertIn("Diagram reference is visible but hard to inspect.", report)
        self.assertIn("outputs/daily/day_03_recall.html", report)

    def test_render_daily_fresh_qa_report_normalizes_raw_results_internally(self) -> None:
        result = complete_pass_result()
        result["course_slug"] = "raw-mapping-course"
        result["axis_scorecard"] = UserDict(
            {**{axis: "OK" for axis in FRESH_QA_AXES}, "visual_source_connection": "WEAK"}
        )
        result["gate"] = "warn"
        result["highest_answer_rate_blocker"] = "Raw mapping blocker."
        result["fix_priority"] = UserDict(
            {
                "summary": "Normalize raw mapping.",
                "axis": "visual_source_connection",
                "recommended_action": "Render after normalization.",
            }
        )
        result["evidence"] = UserDict({"packet_path": "raw/day_03_recall.html"})

        report = render_daily_fresh_qa_report([UserDict(result)], today="2026-05-22")

        self.assertIn("## raw-mapping-course", report)
        self.assertIn("visual_source_connection: WEAK", report)
        self.assertIn("raw/day_03_recall.html", report)

    def test_render_daily_fresh_qa_report_rejects_missing_expected_course(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing fresh QA result"):
            render_daily_fresh_qa_report(
                [complete_pass_result()],
                today="2026-05-22",
                expected_course_slugs=["software-engineering-midterm-testflight", "basic-computer-programming-final"],
            )

    def test_render_daily_fresh_qa_report_sorts_mixed_type_evidence_keys_safely(self) -> None:
        result = complete_pass_result()
        result["evidence"] = {1: "one", "2": "two"}

        report = render_daily_fresh_qa_report([result], today="2026-05-22")

        self.assertIn("- 1: one", report)
        self.assertIn("- 2: two", report)

    def test_render_daily_fresh_qa_report_serializes_nested_mixed_type_mapping_keys_safely(
        self,
    ) -> None:
        result = complete_pass_result()
        result["fix_priority"] = {
            "summary": {1: "one", "b": 2},
            "axis": "outcome_measurement",
            "recommended_action": "Inspect nested evidence.",
        }
        result["evidence"] = {
            "nested": {1: "one", "b": 2},
            "packet_path": "mixed/day_03_recall.html",
        }

        report = render_daily_fresh_qa_report([result], today="2026-05-22")

        self.assertIn('"1": "one"', report)
        self.assertIn('"b": 2', report)
        self.assertIn("mixed/day_03_recall.html", report)


if __name__ == "__main__":
    unittest.main()
