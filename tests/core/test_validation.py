import unittest

from study_os.core.validation import ValidationError, validate_close_session_request, validate_init_course_request


class ValidationTest(unittest.TestCase):
    def test_init_request_builds_typed_models(self) -> None:
        payload = {
            "course": {
                "course_slug": "operating-systems-midterm",
                "course_name": "Operating Systems Midterm",
                "exam_date": "2026-05-20",
                "timezone": "Asia/Seoul",
            },
            "blocks": [
                {
                    "block_id": "use_case_diagram",
                    "block_name": "Use Case Diagram",
                    "block_type": "compare-contrast",
                    "importance": "high",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_prereq": False,
                    "needs_visuals": True,
                }
            ],
            "items": [
                {
                    "item_id": "include_vs_extend",
                    "block_id": "use_case_diagram",
                    "prompt": "Explain include vs extend.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_visuals": True,
                }
            ],
            "source_manifest": [],
            "visual_requirements": [],
        }

        request = validate_init_course_request(payload)
        self.assertEqual(request.course.course_slug, "operating-systems-midterm")
        self.assertEqual(request.blocks[0].block_id, "use_case_diagram")

    def test_close_session_rejects_unknown_result(self) -> None:
        payload = {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "reviewed_items": [
                {"item_id": "include_vs_extend", "phase": "review", "result": "great"}
            ],
        }

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})
