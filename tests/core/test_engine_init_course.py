from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class InitCourseWorkflowTest(unittest.TestCase):
    def _course_payload(self) -> dict:
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
            "visual_requirements": [
                {
                    "item_id": "include_vs_extend",
                    "block_id": "use_case_diagram",
                    "description": "Need the UML arrow direction diagram.",
                    "required_image": "uml-use-case-arrow.png",
                }
            ],
        }

    def test_initialize_course_writes_state_and_master_plan(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            receipt = engine.initialize_course(self._course_payload())

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            self.assertEqual(receipt.status, "applied")
            self.assertTrue(paths.course_file.exists())
            self.assertTrue(paths.blocks_file.exists())
            self.assertTrue(paths.items_file.exists())
            self.assertTrue(paths.mastery_file.exists())
            self.assertTrue(paths.review_queue_file.exists())
            self.assertTrue(paths.master_plan_file.exists())
            self.assertIn("Use Case Diagram", paths.master_plan_file.read_text(encoding="utf-8"))
            self.assertIn("operating-systems-midterm", paths.workspace_file.read_text(encoding="utf-8"))

    def test_initialize_course_clears_append_only_history_on_reinit(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            engine.initialize_course(self._course_payload())

            paths = build_course_paths(workspace, "operating-systems-midterm")
            store = CourseStore(paths)
            store.append_error({"item_id": "include_vs_extend", "error_code": "C1"})
            store.append_session_history({"course_slug": "operating-systems-midterm", "status": "applied"})

            engine.initialize_course(self._course_payload())

            self.assertEqual(store.load_errors(), [])
            self.assertEqual(store.load_session_history(), [])

    def test_initialize_course_reinit_clears_derived_outputs_and_preserves_sources(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)
            engine.initialize_course(self._course_payload())

            paths = build_course_paths(workspace, "operating-systems-midterm")
            source_file = paths.notes_dir / "lecture-annotated.md"
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text("keep me", encoding="utf-8")

            stale_learning = paths.daily_dir / "day_01_learning.md"
            stale_recall = paths.daily_dir / "day_01_recall.md"
            stale_learning.write_text("stale learning", encoding="utf-8")
            stale_recall.write_text("stale recall", encoding="utf-8")
            paths.final_recall_file.write_text("stale final recall", encoding="utf-8")

            engine.initialize_course(self._course_payload())

            self.assertFalse(stale_learning.exists())
            self.assertFalse(stale_recall.exists())
            self.assertFalse(paths.final_recall_file.exists())
            self.assertTrue(source_file.exists())
            self.assertEqual(source_file.read_text(encoding="utf-8"), "keep me")
