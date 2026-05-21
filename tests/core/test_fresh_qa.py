import unittest

from study_os.core.fresh_qa import FRESH_QA_AXES, normalize_fresh_qa_result


def complete_pass_result() -> dict:
    return {
        "course_slug": "software-engineering-midterm-testflight",
        "packet_type": "recall",
        "day_index": 3,
        "next_action": "keep_current_packet",
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
        "fix_priority": [],
        "gate": "pass",
        "evidence": ["packet day 3 recall item sequence_diagram_trace"],
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

    def test_rejects_missing_phase2_grading(self) -> None:
        payload = complete_pass_result()
        del payload["phase2_grading"]

        with self.assertRaisesRegex(ValueError, "missing required field: phase2_grading"):
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


if __name__ == "__main__":
    unittest.main()
