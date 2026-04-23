from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.json_yaml import append_jsonl, read_jsonl, read_yamlish, write_yamlish
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class StorageTest(unittest.TestCase):
    def test_yamlish_round_trip_uses_json_compatible_text(self) -> None:
        payload = [{"item_id": "include_vs_extend", "status": "R1"}]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "review_queue.yaml"
            write_yamlish(path, payload)
            self.assertEqual(read_yamlish(path, []), payload)
            self.assertTrue(path.read_text(encoding="utf-8").lstrip().startswith("["))

    def test_jsonl_append_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "error_log.jsonl"
            append_jsonl(path, {"item_id": "include_vs_extend", "error_code": "C2"})
            append_jsonl(path, {"item_id": "fork_vs_exec", "error_code": "C8"})
            self.assertEqual(len(read_jsonl(path)), 2)

    def test_course_store_saves_mastery_and_queue(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = build_course_paths(Path(tmp), "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_mastery({"include_vs_extend": {"item_id": "include_vs_extend", "block_id": "use_case_diagram", "status": "R1"}})
            store.save_review_queue([{"item_id": "include_vs_extend", "block_id": "use_case_diagram", "status": "R1", "priority": "high", "last_result": "wrong", "confidence": "high", "next_review_day": 2, "next_review_date": "2026-04-24", "reason": "comparison confusion"}])
            self.assertIn("include_vs_extend", store.load_mastery())
            self.assertEqual(store.load_review_queue()[0]["priority"], "high")
