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
        payload["blocks"][0]["study_order"] = 2
        payload["blocks"][0]["study_goal"] = "Use this after textual use-case basics."
        payload["items"][0]["learning_note"] = "Include is mandatory reuse; extend is optional behavior."
        payload["items"][0]["answer_key"] = "Mention mandatory reuse, optional extension, and dependency direction."
        payload["items"][0]["rubric"] = "Full credit requires both semantics and arrow direction."
        payload["items"][0]["common_mistakes"] = ["Treating include as sequence order."]
        payload["items"][0]["source_refs"] = ["slides/week06.pdf p.12", "transcript SE-0325"]

        request = validate_init_course_request(payload)
        self.assertEqual(request.course.course_slug, "operating-systems-midterm")
        self.assertEqual(request.blocks[0].block_id, "use_case_diagram")
        self.assertEqual(request.blocks[0].study_order, 2)
        self.assertEqual(request.items[0].answer_key, "Mention mandatory reuse, optional extension, and dependency direction.")
        self.assertEqual(request.items[0].common_mistakes, ["Treating include as sequence order."])
        self.assertEqual(request.items[0].source_refs, ["slides/week06.pdf p.12", "transcript SE-0325"])

    def test_init_request_rejects_non_string_course_slug(self) -> None:
        payload = self._valid_init_payload()
        payload["course"]["course_slug"] = ["operating-systems-midterm"]

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_path_traversal_course_slug(self) -> None:
        for invalid_slug in ('../escape', 'nested/path', 'nested\\path', '.hidden-course'):
            payload = self._valid_init_payload()
            payload['course']['course_slug'] = invalid_slug

            with self.subTest(course_slug=invalid_slug):
                with self.assertRaisesRegex(ValidationError, 'course_slug must be a lowercase slug using only letters, digits, _ or -'):
                    validate_init_course_request(payload)

    def test_init_request_rejects_bad_exam_date(self) -> None:
        payload = self._valid_init_payload()
        payload["course"]["exam_date"] = "2026/05/20"

        with self.assertRaises(ValidationError):
            validate_init_course_request(payload)

    def test_init_request_rejects_scalar_collection_fields(self) -> None:
        blocks_payload = self._valid_init_payload()
        blocks_payload["blocks"] = 1
        items_payload = self._valid_init_payload()
        items_payload["items"] = 1
        sources_payload = self._valid_init_payload()
        sources_payload["source_manifest"] = 1
        visuals_payload = self._valid_init_payload()
        visuals_payload["visual_requirements"] = 1

        with self.assertRaises(ValidationError):
            validate_init_course_request(blocks_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(items_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(sources_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(visuals_payload)

    def test_init_request_rejects_non_object_rows(self) -> None:
        course_payload = self._valid_init_payload()
        course_payload["course"] = ["not-an-object"]
        blocks_payload = self._valid_init_payload()
        blocks_payload["blocks"] = ["not-an-object"]
        items_payload = self._valid_init_payload()
        items_payload["items"] = ["not-an-object"]
        source_payload = self._valid_init_payload()
        source_payload["source_manifest"] = ["not-an-object"]
        visual_payload = self._valid_init_payload()
        visual_payload["visual_requirements"] = ["not-an-object"]

        with self.assertRaisesRegex(ValidationError, "course must be an object"):
            validate_init_course_request(course_payload)
        with self.assertRaisesRegex(ValidationError, "block must be an object"):
            validate_init_course_request(blocks_payload)
        with self.assertRaisesRegex(ValidationError, "item must be an object"):
            validate_init_course_request(items_payload)
        with self.assertRaisesRegex(ValidationError, "source manifest row must be an object"):
            validate_init_course_request(source_payload)
        with self.assertRaisesRegex(ValidationError, "visual requirement must be an object"):
            validate_init_course_request(visual_payload)

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

    def test_init_request_rejects_duplicate_block_ids(self) -> None:
        payload = self._valid_init_payload()
        payload["blocks"].append(
            {
                "block_id": "use_case_diagram",
                "block_name": "Sequence Diagram",
                "block_type": "compare-contrast",
                "importance": "medium",
                "difficulty": "medium",
                "exam_relevance": "medium",
                "needs_prereq": False,
                "needs_visuals": False,
            }
        )

        with self.assertRaisesRegex(ValidationError, "duplicate block_id: use_case_diagram"):
            validate_init_course_request(payload)

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
        mistakes_payload = self._valid_init_payload()
        mistakes_payload["items"][0]["common_mistakes"] = ["ok", 3]
        refs_payload = self._valid_init_payload()
        refs_payload["items"][0]["source_refs"] = "slides/week06.pdf"

        with self.assertRaises(ValidationError):
            validate_init_course_request(string_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(bool_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(mistakes_payload)
        with self.assertRaises(ValidationError):
            validate_init_course_request(refs_payload)

    def test_init_request_rejects_duplicate_item_ids(self) -> None:
        payload = self._valid_init_payload()
        payload["items"].append(
            {
                "item_id": "include_vs_extend",
                "block_id": "use_case_diagram",
                "prompt": "Explain actor generalization.",
                "answer_mode": "short-answer",
                "difficulty": "medium",
                "exam_relevance": "medium",
                "needs_visuals": False,
            }
        )

        with self.assertRaisesRegex(ValidationError, "duplicate item_id: include_vs_extend"):
            validate_init_course_request(payload)

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

    def test_init_request_rejects_visual_requirement_block_mismatch_for_item(self) -> None:
        payload = self._valid_init_payload()
        payload["blocks"].append(
            {
                "block_id": "sequence_diagram",
                "block_name": "Sequence Diagram",
                "block_type": "compare-contrast",
                "importance": "medium",
                "difficulty": "medium",
                "exam_relevance": "medium",
                "needs_prereq": False,
                "needs_visuals": True,
            }
        )
        payload["visual_requirements"] = [
            {
                "item_id": "include_vs_extend",
                "block_id": "sequence_diagram",
                "description": "Need the use-case relationship diagram.",
                "required_image": "diagram.png",
            }
        ]

        with self.assertRaisesRegex(
            ValidationError,
            "visual requirement item include_vs_extend must use block_id use_case_diagram, got sequence_diagram",
        ):
            validate_init_course_request(payload)

    def test_init_request_rejects_unknown_visual_requirement_status(self) -> None:
        payload = self._valid_init_payload()
        payload["visual_requirements"] = [
            {
                "item_id": "include_vs_extend",
                "block_id": "use_case_diagram",
                "description": "Need the use-case relationship diagram.",
                "required_image": "diagram.png",
                "status": "ready",
            }
        ]

        with self.assertRaisesRegex(
            ValidationError,
            "status must be one of: available, missing",
        ):
            validate_init_course_request(payload)

    def test_init_request_rejects_visual_requirement_for_non_visual_item_or_block(self) -> None:
        non_visual_item_payload = self._valid_init_payload()
        non_visual_item_payload["items"][0]["needs_visuals"] = False
        non_visual_item_payload["visual_requirements"] = [
            {
                "item_id": "include_vs_extend",
                "block_id": "use_case_diagram",
                "description": "Need the use-case relationship diagram.",
                "required_image": "diagram.png",
            }
        ]
        non_visual_block_payload = self._valid_init_payload()
        non_visual_block_payload["blocks"][0]["needs_visuals"] = False
        non_visual_block_payload["visual_requirements"] = [
            {
                "item_id": "include_vs_extend",
                "block_id": "use_case_diagram",
                "description": "Need the use-case relationship diagram.",
                "required_image": "diagram.png",
            }
        ]

        with self.assertRaisesRegex(
            ValidationError,
            "visual requirement item include_vs_extend must have needs_visuals=True",
        ):
            validate_init_course_request(non_visual_item_payload)
        with self.assertRaisesRegex(
            ValidationError,
            "visual requirement block use_case_diagram must have needs_visuals=True",
        ):
            validate_init_course_request(non_visual_block_payload)

    def test_close_session_rejects_unknown_result(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"][0]["result"] = "great"

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_path_traversal_course_slug(self) -> None:
        payload = self._valid_close_payload()
        payload['course_slug'] = '../escape'

        with self.assertRaisesRegex(ValidationError, 'course_slug must be a lowercase slug using only letters, digits, _ or -'):
            validate_close_session_request(payload, {'include_vs_extend'})

    def test_close_session_rejects_scalar_reviewed_items(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"] = 1

        with self.assertRaises(ValidationError):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_non_object_reviewed_item(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"] = ["not-an-object"]

        with self.assertRaisesRegex(ValidationError, "reviewed item must be an object"):
            validate_close_session_request(payload, {"include_vs_extend"})

    def test_close_session_rejects_duplicate_reviewed_item_ids(self) -> None:
        payload = self._valid_close_payload()
        payload["reviewed_items"].append(
            {"item_id": "include_vs_extend", "phase": "review", "result": "correct"}
        )

        with self.assertRaisesRegex(ValidationError, "duplicate reviewed_items item_id: include_vs_extend"):
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
