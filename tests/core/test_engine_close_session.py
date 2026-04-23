from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.engine import StudyEngine
from study_os.core.models import MasteryRecord
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore
from study_os.core.validation import ValidationError


class CloseSessionWorkflowTest(unittest.TestCase):
    def test_close_session_validates_before_accessing_course_slug(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))

            with self.assertRaises(ValidationError):
                engine.close_session(
                    {
                        "session_date": "2026-04-23",
                        "reviewed_items": [],
                    }
                )

    def test_close_session_rejects_malformed_request_without_creating_course_directories(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            engine = StudyEngine(workspace)

            with self.assertRaises(ValidationError):
                engine.close_session(
                    {
                        "course_slug": "operating-systems-midterm",
                        "reviewed_items": [],
                    }
                )

            self.assertFalse(workspace.joinpath("courses", "operating-systems-midterm").exists())

    def test_close_session_rejects_nonexistent_course_cleanly(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))

            with self.assertRaisesRegex(ValidationError, "unknown course_slug: ghost-course"):
                engine.close_session(
                    {
                        "course_slug": "ghost-course",
                        "session_date": "2026-04-23",
                        "reviewed_items": [],
                    }
                )

    def test_close_session_updates_mastery_queue_and_logs_errors(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
                {
                    "course": {
                        "course_slug": "operating-systems-midterm",
                        "course_name": "Operating Systems Midterm",
                        "exam_date": "2026-04-25",
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
            )

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            store = CourseStore(paths)
            store.save_mastery(
                {
                    "include_vs_extend": asdict(
                        MasteryRecord(
                            item_id="include_vs_extend",
                            block_id="use_case_diagram",
                            status="R2",
                            last_result="correct",
                            last_confidence="high",
                        )
                    )
                }
            )

            receipt = engine.close_session(
                {
                    "course_slug": "operating-systems-midterm",
                    "session_date": "2026-04-23",
                    "day_index": 1,
                    "reviewed_items": [
                        {
                            "item_id": "include_vs_extend",
                            "phase": "review",
                            "result": "wrong",
                            "confidence": "high",
                            "error_code": "C2",
                            "note": "Arrow direction reversed.",
                        }
                    ],
                }
            )

            mastery = store.load_mastery()
            queue = store.load_review_queue()
            errors = store.load_errors()
            sessions = store.load_session_history()

            self.assertEqual(receipt.status, "applied")
            self.assertEqual(mastery["include_vs_extend"]["status"], "R0")
            self.assertEqual(queue[0]["item_id"], "include_vs_extend")
            self.assertEqual(errors[0]["error_code"], "C2")
            self.assertEqual(sessions[0]["status"], "applied")

    def test_close_session_all_correct_receipt_does_not_claim_error_log(self) -> None:
        with TemporaryDirectory() as tmp:
            engine = StudyEngine(Path(tmp))
            engine.initialize_course(
                {
                    "course": {
                        "course_slug": "operating-systems-midterm",
                        "course_name": "Operating Systems Midterm",
                        "exam_date": "2026-04-25",
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
            )

            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            store = CourseStore(paths)
            store.save_mastery(
                {
                    "include_vs_extend": asdict(
                        MasteryRecord(
                            item_id="include_vs_extend",
                            block_id="use_case_diagram",
                            status="R1",
                            last_result="correct",
                            last_confidence="medium",
                        )
                    )
                }
            )

            receipt = engine.close_session(
                {
                    "course_slug": "operating-systems-midterm",
                    "session_date": "2026-04-23",
                    "day_index": 1,
                    "reviewed_items": [
                        {
                            "item_id": "include_vs_extend",
                            "phase": "review",
                            "result": "correct",
                            "confidence": "high",
                            "note": "Solid recall.",
                        }
                    ],
                }
            )

            self.assertNotIn(str(paths.error_log_file), receipt.generated_files)
            self.assertFalse(paths.error_log_file.exists())
