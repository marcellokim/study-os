from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.paths import build_course_paths


class InitCourseWorkflowTest(unittest.TestCase):
    def test_initialize_course_writes_state_and_master_plan(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            receipt = engine.initialize_course(
                {
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
            )

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
