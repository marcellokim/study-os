from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.models import QueueEntry
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class EngineFreshQAContextTest(unittest.TestCase):
    def _payload(self, *, course_slug: str = "software-engineering-midterm") -> dict:
        return {
            "course": {
                "course_slug": course_slug,
                "course_name": "Software Engineering Midterm",
                "exam_date": "2026-05-30",
                "timezone": "Asia/Seoul",
            },
            "blocks": [
                {
                    "block_id": "uml",
                    "block_name": "UML",
                    "block_type": "diagram",
                    "importance": "high",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_prereq": False,
                    "needs_visuals": True,
                    "study_order": 1,
                },
                {
                    "block_id": "testing",
                    "block_name": "Testing",
                    "block_type": "concept",
                    "importance": "medium",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_prereq": False,
                    "needs_visuals": False,
                    "study_order": 2,
                },
                {
                    "block_id": "architecture",
                    "block_name": "Architecture",
                    "block_type": "concept",
                    "importance": "low",
                    "difficulty": "medium",
                    "exam_relevance": "medium",
                    "needs_prereq": False,
                    "needs_visuals": False,
                    "study_order": 3,
                },
            ],
            "items": [
                {
                    "item_id": "sequence_diagram_trace",
                    "block_id": "uml",
                    "prompt": "Trace the sequence diagram message order.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_visuals": True,
                    "learning_note": "Focus on message order and guard conditions.",
                    "answer_key": "Order messages and include the guard condition.",
                    "rubric": "Full credit requires order, guard, and actor responsibility.",
                    "common_mistakes": ["Skipping the guard condition."],
                    "model_answer": "The actor calls service A, which conditionally calls service B.",
                    "worked_example": "Read lifelines from top to bottom.",
                    "correction_ladder": ["Find actors.", "Follow messages.", "Check guards."],
                    "retrieval_cues": ["lifeline", "guard"],
                    "source_refs": ["slides/week05.pdf#p=12"],
                },
                {
                    "item_id": "white_box_branch",
                    "block_id": "testing",
                    "prompt": "Explain branch coverage.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "high",
                    "needs_visuals": False,
                    "answer_key": "Every branch outcome is executed at least once.",
                    "rubric": "Must distinguish branch from statement coverage.",
                    "source_refs": ["slides/week09.pdf#p=4"],
                },
                {
                    "item_id": "mvc_boundary",
                    "block_id": "architecture",
                    "prompt": "Explain MVC boundary placement.",
                    "answer_mode": "short-answer",
                    "difficulty": "medium",
                    "exam_relevance": "medium",
                    "needs_visuals": False,
                    "answer_key": "Keep domain rules outside view code.",
                    "rubric": "Must identify model and controller responsibilities.",
                    "source_refs": ["slides/week07.pdf#p=9"],
                },
            ],
            "visual_requirements": [
                {
                    "item_id": "sequence_diagram_trace",
                    "block_id": "uml",
                    "description": "Sequence diagram with guard condition.",
                    "required_image": "sequence-diagram.png",
                    "status": "available",
                }
            ],
        }

    def _initialized_day_one(self, tmp: str) -> tuple[StudyEngine, CourseStore]:
        engine = StudyEngine(Path(tmp))
        engine.initialize_course(self._payload())
        engine.start_day("software-engineering-midterm", day_index=1, today="2026-05-22")
        paths = build_course_paths(Path(tmp), "software-engineering-midterm")
        return engine, CourseStore(paths)

    def test_selects_learning_when_no_due_review_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertEqual(context["selected_packet"]["packet_type"], "learning")
            self.assertEqual(context["next_action"]["kind"], "open_packet")
            self.assertTrue(context["selected_packet"]["exists"])
            self.assertTrue(context["selected_packet"]["openable"])
            self.assertEqual(context["phase1_context"]["packet_item_ids"], ["sequence_diagram_trace", "white_box_branch"])
            self.assertEqual(context["inspection_budget"]["max_items"], 5)

    def test_structurally_corrupt_learning_html_blocks_packet_without_phase2_items(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)
            paths = build_course_paths(Path(tmp), "software-engineering-midterm")
            paths.learning_packet_html_file(day_index=1).write_text(
                "<html><body>No packet entries</body></html>",
                encoding="utf-8",
            )

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertTrue(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["next_action"]["kind"], "packet_blocked")
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])
            self.assertEqual(context["phase2_context"]["items"], [])

    def test_stale_learning_html_with_unknown_items_blocks_packet_without_phase2_items(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)
            paths = build_course_paths(Path(tmp), "software-engineering-midterm")
            paths.learning_packet_html_file(day_index=1).write_text(
                '<html><body><article class="packet-entry" data-item-id="stale_item">'
                "Stale prompt"
                "</article></body></html>",
                encoding="utf-8",
            )

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertTrue(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["next_action"]["kind"], "packet_blocked")
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])
            self.assertEqual(context["phase2_context"]["items"], [])

    def test_stale_learning_html_with_tampered_known_prompt_blocks_packet(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)
            paths = build_course_paths(Path(tmp), "software-engineering-midterm")
            paths.learning_packet_html_file(day_index=1).write_text(
                """
                <html><body>
                  <article class="packet-entry" data-item-id="sequence_diagram_trace">
                    <div class="packet-entry-header">
                      <label class="packet-check">
                        <input type="checkbox" data-action="checked" data-item-id="sequence_diagram_trace">
                        <span>Tampered prompt that the current course item does not contain.</span>
                      </label>
                    </div>
                  </article>
                </body></html>
                """,
                encoding="utf-8",
            )

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertTrue(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["next_action"]["kind"], "packet_blocked")
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])
            self.assertEqual(context["phase2_context"]["items"], [])

    def test_learning_html_with_duplicate_packet_item_id_blocks_packet(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)
            paths = build_course_paths(Path(tmp), "software-engineering-midterm")
            paths.learning_packet_html_file(day_index=1).write_text(
                """
                <html><body>
                  <article class="packet-entry" data-item-id="sequence_diagram_trace">
                    <div class="packet-entry-header"><span>Trace the sequence diagram message order.</span></div>
                  </article>
                  <article class="packet-entry" data-item-id="sequence_diagram_trace">
                    <div class="packet-entry-header"><span>Trace the sequence diagram message order.</span></div>
                  </article>
                </body></html>
                """,
                encoding="utf-8",
            )

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertTrue(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["next_action"]["kind"], "packet_blocked")
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])

    def test_unreadable_learning_html_blocks_packet_without_deriving_phase2_items(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)
            paths = build_course_paths(Path(tmp), "software-engineering-midterm")
            paths.learning_packet_html_file(day_index=1).write_bytes(b"\xff\xfe\xfa")

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertTrue(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["next_action"]["kind"], "packet_blocked")
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])
            self.assertEqual(context["phase2_context"]["items"], [])
            self.assertNotIn("Order messages", repr(context["phase2_context"]))

    def test_selects_due_recall_and_does_not_fallback_when_recall_packet_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, store = self._initialized_day_one(tmp)
            paths = build_course_paths(Path(tmp), "software-engineering-midterm")
            store.save_review_queue(
                [
                    asdict(
                        QueueEntry(
                            item_id="sequence_diagram_trace",
                            block_id="uml",
                            status="R1",
                            priority="urgent",
                            last_result="wrong",
                            confidence="high",
                            next_review_day=1,
                            next_review_date="2026-05-22",
                            reason="diagram trace failed",
                        )
                    )
                ]
            )
            paths.recall_packet_html_file(day_index=1).unlink()
            paths.daily_dir.joinpath("day_01_recall.md").unlink()

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertEqual(context["selected_packet"]["packet_type"], "recall")
            self.assertFalse(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["next_action"]["kind"], "packet_blocked")
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])
            self.assertEqual(context["phase2_context"]["items"], [])
            self.assertNotIn("Order messages", repr(context["phase2_context"]))

    def test_phase1_excludes_answer_key_and_rubric_phase2_includes_answer_key_and_visuals(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            phase1_item = context["phase1_context"]["items"][0]
            phase2_item = context["phase2_context"]["items"][0]
            forbidden = {
                "answer_key",
                "rubric",
                "common_mistakes",
                "model_answer",
                "worked_example",
                "correction_ladder",
                "source_refs",
            }
            self.assertTrue(forbidden.isdisjoint(phase1_item))
            self.assertEqual(phase2_item["answer_key"], "Order messages and include the guard condition.")
            self.assertEqual(phase2_item["rubric"], "Full credit requires order, guard, and actor responsibility.")
            self.assertEqual(
                phase2_item["visual_requirements"][0]["required_image"],
                "sequence-diagram.png",
            )

    def test_phase1_context_can_be_passed_without_full_paths_or_answer_support(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            phase1_text = repr(context["phase1_context"])
            self.assertNotIn("html_path", phase1_text)
            self.assertNotIn("markdown_path", phase1_text)
            self.assertNotIn("url_path", phase1_text)
            self.assertNotIn("/packets/learning/day/1", phase1_text)
            self.assertNotIn("day_01_learning", phase1_text)
            self.assertNotIn("answer_key", phase1_text)
            self.assertNotIn("rubric", phase1_text)
            self.assertNotIn("common_mistakes", phase1_text)
            self.assertNotIn("model_answer", phase1_text)
            self.assertNotIn("worked_example", phase1_text)
            self.assertNotIn("correction_ladder", phase1_text)
            self.assertNotIn("source_refs", phase1_text)
            self.assertNotIn("Order messages and include the guard condition.", phase1_text)
            self.assertNotIn("Full credit requires order, guard, and actor responsibility.", phase1_text)
            self.assertEqual(
                context["phase1_context"]["visual_requirements"][0]["description"],
                "Sequence diagram with guard condition.",
            )

    def test_phase2_context_is_limited_to_selected_packet_items_not_whole_course(self) -> None:
        with TemporaryDirectory() as tmp:
            engine, _store = self._initialized_day_one(tmp)

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            phase2_ids = [item["item_id"] for item in context["phase2_context"]["items"]]
            self.assertEqual(phase2_ids, ["sequence_diagram_trace", "white_box_branch"])
            self.assertNotIn("mvc_boundary", phase2_ids)

    def test_list_active_course_slugs_returns_sorted_initialized_courses(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(self._payload(course_slug="zeta-course"))
            engine.initialize_course(self._payload(course_slug="alpha-course"))
            (Path(tmp) / "courses" / "not-initialized").mkdir(parents=True)

            self.assertEqual(engine.list_active_course_slugs(), ["alpha-course", "zeta-course"])

    def test_missing_current_day_returns_generate_day_context(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(self._payload())

            context = engine.build_fresh_qa_context("software-engineering-midterm", today="2026-05-22")

            self.assertEqual(context["next_action"]["kind"], "generate_day")
            self.assertIsNone(context["selected_packet"]["packet_type"])
            self.assertFalse(context["selected_packet"]["exists"])
            self.assertFalse(context["selected_packet"]["openable"])
            self.assertEqual(context["phase1_context"]["packet_item_ids"], [])
