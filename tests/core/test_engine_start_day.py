from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.models import MasteryRecord
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore
from study_os.core.validation import ValidationError


class StartDayWorkflowTest(unittest.TestCase):
    def _course_payload(
        self,
        *,
        blocks: list[dict] | None = None,
        items: list[dict] | None = None,
        visual_requirements: list[dict] | None = None,
    ) -> dict:
        return {
            "course": {
                "course_slug": "operating-systems-midterm",
                "course_name": "Operating Systems Midterm",
                "exam_date": "2026-05-20",
                "timezone": "Asia/Seoul",
            },
            "blocks": blocks
            or [
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
            "items": items
            or [
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
            "visual_requirements": visual_requirements
            if visual_requirements is not None
            else [
                {
                    "item_id": "include_vs_extend",
                    "block_id": "use_case_diagram",
                    "description": "Need the UML arrow direction diagram.",
                    "required_image": "uml-use-case-arrow.png",
                }
            ],
        }

    def test_start_day_writes_learning_and_recall_packets(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(self._course_payload())

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            store = CourseStore(paths)
            store.save_mastery(
                {
                    "include_vs_extend": asdict(
                        MasteryRecord(
                            item_id="include_vs_extend",
                            block_id="use_case_diagram",
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
                        "item_id": "include_vs_extend",
                        "block_id": "use_case_diagram",
                        "status": "R0",
                        "priority": "urgent",
                        "last_result": "wrong",
                        "confidence": "high",
                        "next_review_day": 1,
                        "next_review_date": "2026-04-23",
                        "reason": "comparison confusion",
                    }
                ]
            )
            store.save_packet_progress({"learning:day:1": {"include_vs_extend": {"checked": True}}})

            receipt = engine.start_day("operating-systems-midterm", day_index=1, today="2026-04-23")
            self.assertEqual(receipt.status, "applied")
            self.assertIn(str(paths.course_file), receipt.generated_files)
            self.assertIn(str(paths.learning_packet_html_file(day_index=1)), receipt.generated_files)
            self.assertIn(str(paths.recall_packet_html_file(day_index=1)), receipt.generated_files)
            self.assertTrue(paths.daily_dir.joinpath("day_01_learning.md").exists())
            self.assertTrue(paths.daily_dir.joinpath("day_01_recall.md").exists())
            self.assertTrue(paths.learning_packet_html_file(day_index=1).exists())
            self.assertTrue(paths.recall_packet_html_file(day_index=1).exists())
            self.assertEqual(store.load_course()["current_day"], 1)
            self.assertIn("2026-04-23", paths.daily_dir.joinpath("day_01_learning.md").read_text(encoding="utf-8"))
            self.assertIn("2026-04-23", paths.daily_dir.joinpath("day_01_recall.md").read_text(encoding="utf-8"))
            self.assertIn("첫 행동", paths.daily_dir.joinpath("day_01_learning.md").read_text(encoding="utf-8"))
            self.assertIn("즉시 회상", paths.daily_dir.joinpath("day_01_recall.md").read_text(encoding="utf-8"))
            learning_html = paths.learning_packet_html_file(day_index=1).read_text(encoding="utf-8")
            recall_html = paths.recall_packet_html_file(day_index=1).read_text(encoding="utf-8")
            self.assertIn('body data-packet-type="learning"', learning_html)
            self.assertIn('data-item-id="include_vs_extend" checked', learning_html)
            self.assertIn('body data-packet-type="recall"', recall_html)

    def test_failed_learning_item_reappears_in_next_day_recall(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(self._course_payload(visual_requirements=[]))

            day_one = engine.start_day("operating-systems-midterm", day_index=1, today="2026-04-23")
            self.assertEqual(day_one.applied_items, ["include_vs_extend"])

            engine.close_session(
                {
                    "course_slug": "operating-systems-midterm",
                    "session_date": "2026-04-23",
                    "day_index": 1,
                    "reviewed_items": [
                        {
                            "item_id": "include_vs_extend",
                            "phase": "learning",
                            "result": "wrong",
                            "confidence": "medium",
                            "note": "Still mixing up the terms.",
                        }
                    ],
                }
            )

            day_two = engine.start_day("operating-systems-midterm", day_index=2, today="2026-04-24")

            recall_file = Path(tmp) / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_02_recall.md"
            self.assertIn("include_vs_extend", day_two.applied_items)
            self.assertIn("Explain include vs extend.", recall_file.read_text(encoding="utf-8"))

    def test_start_day_includes_review_due_by_calendar_date_even_when_day_index_is_future(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(self._course_payload(visual_requirements=[]))

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            store = CourseStore(paths)
            store.save_review_queue(
                [
                    {
                        "item_id": "include_vs_extend",
                        "block_id": "use_case_diagram",
                        "status": "R0",
                        "priority": "urgent",
                        "last_result": "wrong",
                        "confidence": "high",
                        "next_review_day": 13,
                        "next_review_date": "2026-05-21",
                        "reason": "exam near",
                    }
                ]
            )

            receipt = engine.start_day("operating-systems-midterm", day_index=12, today="2026-05-21")

            recall_file = paths.daily_dir / "day_12_recall.md"
            self.assertIn("include_vs_extend", receipt.applied_items)
            self.assertIn("Explain include vs extend.", recall_file.read_text(encoding="utf-8"))

    def test_start_day_advances_new_block_selection_across_days(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
                self._course_payload(
                    blocks=[
                        {
                            "block_id": "block_a",
                            "block_name": "Alpha",
                            "block_type": "concept",
                            "importance": "high",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_prereq": False,
                            "needs_visuals": False,
                        },
                        {
                            "block_id": "block_b",
                            "block_name": "Beta",
                            "block_type": "concept",
                            "importance": "high",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_prereq": False,
                            "needs_visuals": False,
                        },
                        {
                            "block_id": "block_c",
                            "block_name": "Gamma",
                            "block_type": "concept",
                            "importance": "medium",
                            "difficulty": "medium",
                            "exam_relevance": "medium",
                            "needs_prereq": False,
                            "needs_visuals": False,
                        },
                    ],
                    items=[
                        {
                            "item_id": "item_a",
                            "block_id": "block_a",
                            "prompt": "Explain alpha.",
                            "answer_mode": "short-answer",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_visuals": False,
                        },
                        {
                            "item_id": "item_b",
                            "block_id": "block_b",
                            "prompt": "Explain beta.",
                            "answer_mode": "short-answer",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_visuals": False,
                        },
                        {
                            "item_id": "item_c",
                            "block_id": "block_c",
                            "prompt": "Explain gamma.",
                            "answer_mode": "short-answer",
                            "difficulty": "medium",
                            "exam_relevance": "medium",
                            "needs_visuals": False,
                        },
                    ],
                    visual_requirements=[],
                )
            )
            day_one = engine.start_day("operating-systems-midterm", day_index=1, today="2026-04-23")
            day_two = engine.start_day("operating-systems-midterm", day_index=2, today="2026-04-24")

            self.assertEqual(day_one.applied_items, ["item_a", "item_b"])
            self.assertEqual(day_two.applied_items, ["item_c"])

    def test_start_day_uses_explicit_study_order_before_localized_block_name(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
                self._course_payload(
                    blocks=[
                        {
                            "block_id": "late_korean_sort",
                            "block_name": "가나다 선행처럼 보이는 블록",
                            "block_type": "concept",
                            "importance": "high",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_prereq": False,
                            "needs_visuals": False,
                            "study_order": 3,
                        },
                        {
                            "block_id": "first_by_order",
                            "block_name": "중간고사 전략",
                            "block_type": "exam-strategy",
                            "importance": "high",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_prereq": False,
                            "needs_visuals": False,
                            "study_order": 1,
                        },
                        {
                            "block_id": "second_by_order",
                            "block_name": "소프트웨어 프로세스",
                            "block_type": "concept",
                            "importance": "medium",
                            "difficulty": "medium",
                            "exam_relevance": "medium",
                            "needs_prereq": False,
                            "needs_visuals": False,
                            "study_order": 2,
                        },
                    ],
                    items=[
                        {
                            "item_id": "late_item",
                            "block_id": "late_korean_sort",
                            "prompt": "Explain late item.",
                            "answer_mode": "short-answer",
                            "difficulty": "medium",
                            "exam_relevance": "high",
                            "needs_visuals": False,
                        },
                        {
                            "item_id": "first_item",
                            "block_id": "first_by_order",
                            "prompt": "Explain first item.",
                            "answer_mode": "short-answer",
                            "difficulty": "low",
                            "exam_relevance": "high",
                            "needs_visuals": False,
                        },
                        {
                            "item_id": "second_item",
                            "block_id": "second_by_order",
                            "prompt": "Explain second item.",
                            "answer_mode": "short-answer",
                            "difficulty": "medium",
                            "exam_relevance": "medium",
                            "needs_visuals": False,
                        },
                    ],
                    visual_requirements=[],
                )
            )

            day_one = engine.start_day("operating-systems-midterm", day_index=1, today="2026-04-23")

            self.assertEqual(day_one.applied_items, ["first_item", "second_item"])
            learning_text = Path(tmp).joinpath(
                "courses", "operating-systems-midterm", "outputs", "daily", "day_01_learning.md"
            ).read_text(encoding="utf-8")
            self.assertLess(learning_text.index("중간고사 전략"), learning_text.index("소프트웨어 프로세스"))
            self.assertNotIn("late_item", learning_text)

    def test_start_day_rejects_unknown_course_without_creating_directories(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            missing_paths = build_course_paths(workspace, "missing-course")

            with self.assertRaisesRegex(ValidationError, "unknown course_slug: missing-course"):
                engine.start_day("missing-course", day_index=1, today="2026-04-23")

            self.assertFalse(missing_paths.course_root.exists())

    def test_start_day_includes_available_visuals_in_user_packets(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
                self._course_payload(
                    visual_requirements=[
                        {
                            "item_id": "include_vs_extend",
                            "block_id": "use_case_diagram",
                            "description": "Need the UML arrow direction diagram.",
                            "required_image": (
                                "courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png"
                            ),
                            "status": "available",
                        }
                    ]
                )
            )

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            store = CourseStore(paths)
            store.save_review_queue(
                [
                    {
                        "item_id": "include_vs_extend",
                        "block_id": "use_case_diagram",
                        "status": "R0",
                        "priority": "urgent",
                        "last_result": "wrong",
                        "confidence": "high",
                        "next_review_day": 1,
                        "next_review_date": "2026-04-23",
                        "reason": "comparison confusion",
                    }
                ]
            )

            engine.start_day("operating-systems-midterm", day_index=1, today="2026-04-23")

            learning_text = paths.daily_dir.joinpath("day_01_learning.md").read_text(encoding="utf-8")
            recall_text = paths.daily_dir.joinpath("day_01_recall.md").read_text(encoding="utf-8")
            learning_html = paths.learning_packet_html_file(day_index=1).read_text(encoding="utf-8")
            recall_html = paths.recall_packet_html_file(day_index=1).read_text(encoding="utf-8")

            self.assertIn(
                "- `include_vs_extend`: "
                "`courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png` 필요 — "
                "Need the UML arrow direction diagram. (status: available)",
                learning_text,
            )
            self.assertIn(
                "- `include_vs_extend`은/는 "
                "`courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png` 확인 필요. "
                "status: available",
                recall_text,
            )
            self.assertIn(
                'src="/assets/courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png"',
                learning_html,
            )
            self.assertIn(
                'src="/assets/courses/operating-systems-midterm/sources/images/uml-use-case-arrow.png"',
                recall_html,
            )
