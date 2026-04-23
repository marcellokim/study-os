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

    def test_init_request_rejects_non_string_course_slug(self) -> None:
        payload = {
            "course": {
                "course_slug": ["operating-systems-midterm"],
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
        }

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_bad_exam_date(self) -> None:
        payload = {
            "course": {
                "course_slug": "operating-systems-midterm",
                "course_name": "Operating Systems Midterm",
                "exam_date": "2026/05/20",
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
        }

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_unknown_source_manifest_block_id(self) -> None:
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
            "source_manifest": [
                {
                    "block_id": "unknown_block",
                    "source_type": "pdf",
                    "path": "docs/source.pdf",
                }
            ],
        }

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_non_string_block_id_in_item(self) -> None:
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
                    "block_id": ["use_case_diagram"],
                    "prompt": "Explain include vs extend.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_visuals": True,
                }
            ],
        }

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

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

    def test_close_session_rejects_non_hashable_confidence_and_error_code(self) -> None:
        confidence_payload = {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "reviewed_items": [
                {
                    "item_id": "include_vs_extend",
                    "phase": "review",
                    "result": "wrong",
                    "confidence": ["high"],
                }
            ],
        }
        error_code_payload = {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "reviewed_items": [
                {
                    "item_id": "include_vs_extend",
                    "phase": "review",
                    "result": "wrong",
                    "error_code": {"code": "C2"},
                }
            ],
        }

        with self.assertRaises(ValidationError):
            validate_close_session_request(confidence_payload, {"include_vs_extend"})
        with self.assertRaises(ValidationError):
            validate_close_session_request(error_code_payload, {"include_vs_extend"})

    def test_close_session_rejects_non_string_item_id(self) -> None:
        payload = {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "reviewed_items": [
                {"item_id": ["include_vs_extend"], "phase": "review", "result": "wrong"}
            ],
        }

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_boolean_day_index(self) -> None:
        payload = {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "reviewed_items": [
                {"item_id": "include_vs_extend", "phase": "review", "result": "wrong"}
            ],
            "day_index": True,
        }

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})
