import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class RealSourcePrepareIntegrationTest(unittest.TestCase):
    def test_prepares_request_from_user_supplied_pdf_and_text_files(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            script = REPO_ROOT / "scripts" / "prepare_real_course.py"
            base_command = [
                sys.executable,
                str(script),
                "--workspace",
                str(workspace),
                "--course-slug",
                "os-midterm",
                "--course-name",
                "OS Midterm",
                "--exam-date",
                "2026-05-20",
            ]

            first = subprocess.run(base_command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)

            syllabus = workspace / "courses/os-midterm/sources/syllabus/syllabus.pdf"
            transcript = workspace / "courses/os-midterm/sources/transcripts/week01.txt"
            syllabus.write_bytes(b"%PDF-1.4\n% real user pdf placeholder for tests\n")
            transcript.write_text("process scheduling lecture notes\n", encoding="utf-8")

            second = subprocess.run(base_command + ["--overwrite"], capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr)

            request_file = workspace / "courses/os-midterm/init_request.json"
            payload = json.loads(request_file.read_text(encoding="utf-8"))
            manifest_paths = {row["path"] for row in payload["source_manifest"]}
            self.assertIn("courses/os-midterm/sources/syllabus/syllabus.pdf", manifest_paths)
            self.assertIn("courses/os-midterm/sources/transcripts/week01.txt", manifest_paths)

            init = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(request_file),
                    "--validate-sources",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertTrue((workspace / "courses/os-midterm/outputs/master_plan.md").exists())
