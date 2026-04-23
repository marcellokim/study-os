import unittest

from study_os.core.validation import ValidationError, validate_close_session_request, validate_init_course_request


class ValidationTest(unittest.TestCase):
    def _valid_init_payload(self) -> dict:
        return {
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

    def _valid_close_payload(self) -> dict:
        return {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "reviewed_items": [
                {"item_id": "include_vs_extend", "phase": "review", "result": "wrong"}
            ],
        }

    def test_init_request_builds_typed_models(self) -> None:
        payload = self._valid_init_payload()

        request = validate_init_course_request(payload)
        self.assertEqual(request.course.course_slug, "operating-systems-midterm")
        self.assertEqual(request.blocks[0].block_id, "use_case_diagram")

    def test_init_request_rejects_non_string_course_slug(self) -> None:
        payload = self._valid_init_payload()
        payload["course"]["course_slug"] = ["operating-systems-midterm"]

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_bad_exam_date(self) -> None:
        payload = self._valid_init_payload()
        payload["course"]["exam_date"] = "2026/05/20"

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_non_object_rows(self) -> None:
        course_payload = self._valid_init_payload()
        course_payload["course"] = ["not-an-object"]
        blocks_payload = self._valid_init_payload()
        blocks_payload["blocks"] = ["not-an-object"]
        source_payload = self._valid_init_payload()
        source_payload["source_manifest"] = ["not-an-object"]

        with self.assertRaisesRegex(ValidationError, "course must be an object"):
            validate_init_course_request(course_payload)
        with self.assertRaisesRegex(ValidationError, "block must be an object"):
            validate_init_course_request(blocks_payload)
        with self.assertRaisesRegex(ValidationError, "source manifest row must be an object"):
            validate_init_course_request(source_payload)

    def test_init_request_rejects_unknown_source_manifest_block_id(self) -> None:
        payload = self._valid_init_payload()
        payload["source_manifest"] = [
            {
                "block_id": "unknown_block",
                "source_type": "pdf",
                "path": "docs/source.pdf",
            }
        ]

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_malformed_block_fields(self) -> None:
        string_payload = self._valid_init_payload()
        string_payload["blocks"][0]["block_name"] = 7
        bool_payload = self._valid_init_payload()
        bool_payload["blocks"][0]["needs_visuals"] = "yes"

        with self.assertRaises(ValidationError):
            validate_init_course_request(string_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(bool_payload)

    def test_init_request_rejects_non_string_block_id_in_item(self) -> None:
        payload = self._valid_init_payload()
        payload["items"][0]["block_id"] = ["use_case_diagram"]

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_malformed_item_fields(self) -> None:
        string_payload = self._valid_init_payload()
        string_payload["items"][0]["prompt"] = ["Explain include vs extend."]
        bool_payload = self._valid_init_payload()
        bool_payload["items"][0]["needs_visuals"] = "yes"

        with self.assertRaises(ValidationError):
            validate_init_course_request(string_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(bool_payload)

    def test_init_request_rejects_malformed_source_manifest_fields(self) -> None:
        string_payload = self._valid_init_payload()
        string_payload["source_manifest"] = [
            {
                "block_id": "use_case_diagram",
                "source_type": 1,
                "path": "docs/source.pdf",
            }
        ]
        note_payload = self._valid_init_payload()
        note_payload["source_manifest"] = [
            {
                "block_id": "use_case_diagram",
                "source_type": "pdf",
                "path": "docs/source.pdf",
                "note": ["lecture note"],
            }
        ]

        with self.assertRaises(ValidationError):
            validate_init_course_request(string_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(note_payload)

    def test_init_request_rejects_malformed_visual_requirement_fields(self) -> None:
        description_payload = self._valid_init_payload()
        description_payload["visual_requirements"] = [
            {
                "item_id": "include_vs_extend",
                "block_id": "use_case_diagram",
                "description": False,
                "required_image": "diagram.png",
            }
        ]
        image_payload = self._valid_init_payload()
        image_payload["visual_requirements"] = [
            {
                "item_id": "include_vs_extend",
                "block_id": "use_case_diagram",
                "description": "Need a UML diagram.",
                "required_image": {"path": "diagram.png"},
            }
        ]

        with self.assertRaises(ValidationError):
            validate_init_course_request(description_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(image_payload)

    def test_close_session_rejects_unknown_result(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"][0]["result"] = "great"

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_non_object_reviewed_item(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"] = ["not-an-object"]

        with self.assertRaisesRegex(ValidationError, "reviewed item must be an object"):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_non_hashable_confidence_and_error_code(self) -> None:
        confidence_payload = self._valid_close_payload()
        confidence_payload["reviewed_items"][0]["confidence"] = ["high"]
        error_code_payload = self._valid_close_payload()
        error_code_payload["reviewed_items"][0]["error_code"] = {"code": "C2"}

        with self.assertRaises(ValidationError):
            validate_close_session_request(confidence_payload, {"include_vs_extend"})
        with self.assertRaises(ValidationError):
            validate_close_session_request(error_code_payload, {"include_vs_extend"})

    def test_close_session_rejects_non_string_item_id(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"][0]["item_id"] = ["include_vs_extend"]

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_boolean_day_index(self) -> None:
        payload = self._valid_close_payload()
        payload["day_index"] = True

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})
