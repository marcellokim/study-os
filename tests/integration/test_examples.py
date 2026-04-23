import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class ExampleFilesIntegrationTest(unittest.TestCase):
    def test_sample_requests_run_against_workspace_template(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            shutil.copytree(REPO_ROOT / "workspace_template", workspace)

            init_request = REPO_ROOT / "examples" / "sample_init_request.json"
            close_request = REPO_ROOT / "examples" / "sample_close_request.json"
            course_root = workspace / "courses" / "sample-course"

            commands = [
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(init_request),
                ],
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "sample-course",
                    "--day",
                    "1",
                    "--today",
                    "2026-04-23",
                ],
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "close-session",
                    "--request-file",
                    str(close_request),
                ],
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-final-recall",
                    "--course",
                    "sample-course",
                    "--today",
                    "2026-04-23",
                ],
            ]

            outputs: list[str] = []
            for command in commands:
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                outputs.append(completed.stdout)

            for source_bucket in ("syllabus", "slides", "transcripts", "images", "notes"):
                self.assertTrue(course_root.joinpath("sources", source_bucket).is_dir())

            self.assertTrue(course_root.joinpath("outputs", "master_plan.md").exists())
            self.assertTrue(course_root.joinpath("outputs", "daily", "day_01_learning.md").exists())
            self.assertTrue(course_root.joinpath("outputs", "daily", "day_01_recall.md").exists())
            self.assertTrue(course_root.joinpath("outputs", "final_recall_pack.md").exists())
            self.assertTrue(course_root.joinpath("state", "error_log.jsonl").exists())
            self.assertIn("error_log.jsonl", outputs[2])
