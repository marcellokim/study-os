from collections import UserDict
import re
import unittest

from study_os.core.fresh_qa import FRESH_QA_AXES, normalize_fresh_qa_result


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


class FreshQAResultTest(unittest.TestCase):
    def test_accepts_complete_pass_result(self) -> None:
        result = normalize_fresh_qa_result(complete_pass_result())

        self.assertEqual("pass", result["computed_gate"])
        self.assertEqual("positive", result["predicted_answer_rate_effect"])
        self.assertEqual({axis: "OK" for axis in FRESH_QA_AXES}, result["axis_scorecard"])

    def test_stricter_submitted_gate_controls_predicted_effect(self) -> None:
        payload = complete_pass_result()
        payload["gate"] = "block"

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

        with self.assertRaisesRegex(ValueError, "weaker gate"):
            normalize_fresh_qa_result(payload)

        payload["gate"] = "block"
        result = normalize_fresh_qa_result(payload)
        self.assertEqual("block", result["computed_gate"])

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

    def test_rejects_invalid_axis_value(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"]["exam_transfer"] = "MAYBE"

        with self.assertRaisesRegex(ValueError, "bad axis value"):
            normalize_fresh_qa_result(payload)

    def test_requires_block_gate_when_any_axis_is_blocked(self) -> None:
        payload = complete_pass_result()
        payload["axis_scorecard"]["visual_source_connection"] = "BLOCKED"
        payload["gate"] = "warn"

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


if __name__ == "__main__":
    unittest.main()
