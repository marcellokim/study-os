import json
from http.client import HTTPConnection
from pathlib import Path
import queue
import signal
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.parse import urlparse

from study_os.core.fresh_qa import FRESH_QA_AXES


class CliSmokeTest(unittest.TestCase):
    def _complete_fresh_qa_result(self) -> dict[str, object]:
        return {
            "course_slug": "sample-course",
            "packet_type": "learning",
            "day_index": 1,
            "next_action": {"type": "keep_current_packet"},
            "failure_type": "pass",
            "phase1_attempts": [
                {
                    "item_id": "scope_keywords",
                    "answerable_from_packet": True,
                    "draft_answer": "List the exam-scope keywords.",
                    "confidence_score": 4,
                    "visible_blockers": [],
                    "answer_first_supported": True,
                }
            ],
            "phase2_grading": [
                {
                    "item_id": "scope_keywords",
                    "result": "correct",
                    "grading_rationale": "The answer covers the packet prompt.",
                    "self_grading_supported": True,
                    "source_connection_supported": True,
                    "exam_plausibility": "high",
                    "failure_source": "none",
                }
            ],
            "axis_scorecard": {axis: "OK" for axis in FRESH_QA_AXES},
            "highest_answer_rate_blocker": "none",
            "fix_priority": {},
            "gate": "pass",
            "evidence": {"packet_path": "outputs/daily/day_01_learning.html"},
        }

    def _init_sample_course(self, workspace: Path) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "study_os",
                "--workspace",
                str(workspace),
                "init-course",
                "--request-file",
                "examples/sample_init_request.json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def _post_progress(self, server_url: str, body: dict[str, object]) -> None:
        parsed = urlparse(server_url)
        connection = HTTPConnection(parsed.hostname or "127.0.0.1", parsed.port, timeout=5)
        try:
            connection.request(
                "POST",
                "/api/progress",
                body=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

        self.assertEqual(response.status, 200, payload)
        self.assertTrue(payload["saved"])

    def _start_packet_server_process(self, workspace: Path) -> tuple[subprocess.Popen, str]:
        process = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-m",
                "study_os",
                "--workspace",
                str(workspace),
                "serve-packets",
                "--course",
                "sample-course",
                "--port",
                "0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            server_url = self._read_packet_server_url(process)
        except BaseException:
            self._stop_packet_server_process(process)
            raise
        return process, server_url

    def _read_packet_server_url(self, process: subprocess.Popen) -> str:
        if process.stdout is None:
            self.fail("serve-packets stdout was not captured")

        lines: queue.Queue[str] = queue.Queue(maxsize=1)

        def read_line() -> None:
            lines.put(process.stdout.readline())

        reader = threading.Thread(target=read_line, daemon=True)
        reader.start()
        try:
            server_url = lines.get(timeout=5).strip()
        except queue.Empty:
            self.fail("serve-packets did not print a local URL within 5 seconds")
        reader.join(timeout=1)
        self.assertIn("http://127.0.0.1:", server_url)
        return server_url

    def _stop_packet_server_process(self, process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    def _record_packet_progress_through_server(self, workspace: Path) -> None:
        completed = subprocess.run(
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
                "2026-05-21",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        process, server_url = self._start_packet_server_process(workspace)
        try:
            self._post_progress(
                server_url,
                {
                    "packet_type": "learning",
                    "day_index": 1,
                    "item_id": "scope_keywords",
                    "checked": True,
                },
            )
            self._post_progress(
                server_url,
                {
                    "action": "attempt",
                    "packet_type": "learning",
                    "day_index": 1,
                    "item_id": "scope_keywords",
                    "draft_answer": "Missed one scope keyword.",
                    "result": "partial",
                    "confidence_score": 2,
                    "blocker_type": "memory",
                },
            )
        finally:
            self._stop_packet_server_process(process)

    def test_help_lists_core_commands(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "study_os", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("init-course", completed.stdout)
        self.assertIn("start-day", completed.stdout)
        self.assertIn("close-session", completed.stdout)
        self.assertIn("start-final-recall", completed.stdout)
        self.assertIn("status", completed.stdout)
        self.assertIn("serve-packets", completed.stdout)
        self.assertIn("draft-close-session", completed.stdout)
        self.assertIn("fresh-qa-context", completed.stdout)
        self.assertIn("fresh-qa-report", completed.stdout)

    def test_empty_invocation_prints_help_and_returns_non_zero(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "study_os"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("usage:", completed.stdout)
        self.assertIn("init-course", completed.stdout)
        self.assertEqual(completed.stderr, "")

    def test_serve_packets_prints_local_url_before_blocking(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)

            process, line = self._start_packet_server_process(workspace)
            try:
                self.assertIn("http://127.0.0.1:", line)
            finally:
                self._stop_packet_server_process(process)

    def test_serve_packets_unknown_course_fails_cleanly_without_creating_directories(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "serve-packets",
                    "--course",
                    "missing-course",
                    "--port",
                    "0",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: unknown course_slug: missing-course", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((workspace / "courses" / "missing-course").exists())

    def test_serve_packets_port_conflict_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved_socket:
                reserved_socket.bind(("127.0.0.1", 0))
                reserved_socket.listen(1)
                port = reserved_socket.getsockname()[1]

                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "study_os",
                        "--workspace",
                        str(workspace),
                        "serve-packets",
                        "--course",
                        "sample-course",
                        "--port",
                        str(port),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: ", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_serve_packets_sigint_exits_without_keyboardinterrupt_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)

            process: subprocess.Popen | None = None
            try:
                process, _server_url = self._start_packet_server_process(workspace)
                process.send_signal(signal.SIGINT)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    self._stop_packet_server_process(process)
                    self.fail("serve-packets did not exit after SIGINT")
            finally:
                if process is not None:
                    self._stop_packet_server_process(process)

            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(stdout, "")
            self.assertNotIn("Traceback", stderr)
            self.assertNotIn("KeyboardInterrupt", stderr)

    def test_fresh_qa_context_outputs_all_active_course_contexts(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)
            started = subprocess.run(
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
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(started.returncode, 0, started.stderr)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "fresh-qa-context",
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["today"], "2026-05-22")
            self.assertEqual(len(payload["courses"]), 1)
            self.assertEqual(payload["courses"][0]["course_slug"], "sample-course")
            self.assertIn("phase1_context", payload["courses"][0])
            self.assertNotIn("phase2_context", payload["courses"][0])

    def test_fresh_qa_context_outputs_single_requested_course(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)
            subprocess.run(
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
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "fresh-qa-context",
                    "--today",
                    "2026-05-22",
                    "--course",
                    "sample-course",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual([course["course_slug"] for course in payload["courses"]], ["sample-course"])

    def test_fresh_qa_context_phase_all_includes_phase2_for_trusted_orchestration(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)
            subprocess.run(
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
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "fresh-qa-context",
                    "--today",
                    "2026-05-22",
                    "--phase",
                    "all",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertIn("phase1_context", payload["courses"][0])
            self.assertIn("phase2_context", payload["courses"][0])

    def test_fresh_qa_report_renders_valid_result_json(self) -> None:
        with TemporaryDirectory() as tmp:
            result_file = Path(tmp) / "fresh-qa-result.json"
            result_file.write_text(json.dumps(self._complete_fresh_qa_result()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "fresh-qa-report",
                    "--result-file",
                    str(result_file),
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("# Daily Fresh QA - 2026-05-22", completed.stdout)
            self.assertIn("## sample-course", completed.stdout)
            self.assertIn("정답률 영향: positive", completed.stdout)

    def test_fresh_qa_report_rejects_missing_active_workspace_course_result(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self._init_sample_course(workspace)
            result = self._complete_fresh_qa_result()
            result["course_slug"] = "other-course"
            result_file = Path(tmp) / "fresh-qa-result.json"
            result_file.write_text(json.dumps(result), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "fresh-qa-report",
                    "--result-file",
                    str(result_file),
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("missing fresh QA result for course: sample-course", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_fresh_qa_report_missing_file_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            missing_result = Path(tmp) / "missing.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "fresh-qa-report",
                    "--result-file",
                    str(missing_result),
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: fresh QA result file not found:", completed.stderr)
            self.assertIn(str(missing_result), completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_fresh_qa_report_invalid_json_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            result_file = Path(tmp) / "fresh-qa-result.json"
            result_file.write_text('{"results": ', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "fresh-qa-report",
                    "--result-file",
                    str(result_file),
                    "--today",
                    "2026-05-22",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: fresh QA result file is not valid JSON:", completed.stderr)
            self.assertIn(str(result_file), completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_draft_close_session_prints_reviewed_items_from_packet_progress(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            self._init_sample_course(workspace)
            self._record_packet_progress_through_server(workspace)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "draft-close-session",
                    "--course",
                    "sample-course",
                    "--packet-type",
                    "learning",
                    "--day",
                    "1",
                    "--session-date",
                    "2026-05-21",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["course_slug"], "sample-course")
            self.assertEqual(payload["session_date"], "2026-05-21")
            self.assertEqual(payload["day_index"], 1)
            self.assertEqual(payload["reviewed_items"][0]["item_id"], "scope_keywords")
            self.assertEqual(payload["reviewed_items"][0]["confidence"], "low")
            self.assertEqual(payload["reviewed_items"][0]["result"], "partial")
            self.assertEqual(payload["reviewed_items"][0]["error_code"], "C1")
            self.assertEqual(
                payload["reviewed_items"][0]["note"],
                "blocker=memory; answer=Missed one scope keyword.",
            )
            self.assertEqual(payload["next_focus"], ["scope_keywords"])

    def test_init_course_command_writes_requested_artifacts(self) -> None:
        request = {
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

        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            request_file = Path(tmp) / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("applied", completed.stdout)
            self.assertTrue((workspace / "courses" / "operating-systems-midterm" / "course.yaml").exists())
            self.assertTrue((workspace / "courses" / "operating-systems-midterm" / "outputs" / "master_plan.md").exists())
            self.assertIn("operating-systems-midterm", (workspace / "workspace.md").read_text(encoding="utf-8"))

    def test_init_course_with_missing_request_file_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / 'workspace'
            missing_request = Path(tmp) / 'missing.json'

            completed = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'study_os',
                    '--workspace',
                    str(workspace),
                    'init-course',
                    '--request-file',
                    str(missing_request),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, '')
            self.assertIn('error: request file not found:', completed.stderr)
            self.assertIn(str(missing_request), completed.stderr)
            self.assertNotIn('Traceback', completed.stderr)

    def test_init_course_with_malformed_request_file_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / 'workspace'
            request_file = Path(tmp) / 'request.json'
            request_file.write_text('{"course": ', encoding='utf-8')

            completed = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'study_os',
                    '--workspace',
                    str(workspace),
                    'init-course',
                    '--request-file',
                    str(request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, '')
            self.assertIn('error: request file is not valid JSON:', completed.stderr)
            self.assertIn(str(request_file), completed.stderr)
            self.assertNotIn('Traceback', completed.stderr)

    def test_close_session_with_missing_request_file_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / 'workspace'
            missing_request = Path(tmp) / 'missing.json'

            completed = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'study_os',
                    '--workspace',
                    str(workspace),
                    'close-session',
                    '--request-file',
                    str(missing_request),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, '')
            self.assertIn('error: request file not found:', completed.stderr)
            self.assertIn(str(missing_request), completed.stderr)
            self.assertNotIn('Traceback', completed.stderr)

    def test_close_session_with_malformed_request_file_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / 'workspace'
            request_file = Path(tmp) / 'request.json'
            request_file.write_text('{"course_slug": ', encoding='utf-8')

            completed = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'study_os',
                    '--workspace',
                    str(workspace),
                    'close-session',
                    '--request-file',
                    str(request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, '')
            self.assertIn('error: request file is not valid JSON:', completed.stderr)
            self.assertIn(str(request_file), completed.stderr)
            self.assertNotIn('Traceback', completed.stderr)

    def test_close_session_surfaces_held_visual_gated_promotions_in_stdout(self) -> None:
        init_request = {
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
                    "status": "missing",
                }
            ],
        }

        close_request = {
            "course_slug": "operating-systems-midterm",
            "session_date": "2026-04-23",
            "day_index": 1,
            "reviewed_items": [
                {
                    "item_id": "include_vs_extend",
                    "phase": "review",
                    "result": "correct",
                    "confidence": "high",
                    "note": "Verbal explanation was correct but the diagram is still missing.",
                }
            ],
        }

        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            init_request_file = Path(tmp) / "init-request.json"
            init_request_file.write_text(json.dumps(init_request), encoding="utf-8")

            init_completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(init_request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init_completed.returncode, 0, init_completed.stderr)

            mastery_file = workspace / "courses" / "operating-systems-midterm" / "state" / "mastery.json"
            review_queue_file = workspace / "courses" / "operating-systems-midterm" / "state" / "review_queue.yaml"
            session_history_file = workspace / "courses" / "operating-systems-midterm" / "state" / "session_history.jsonl"
            mastery_file.write_text(
                json.dumps(
                    {
                        "include_vs_extend": {
                            "item_id": "include_vs_extend",
                            "block_id": "use_case_diagram",
                            "status": "R1",
                            "last_result": "correct",
                            "consecutive_successes": 1,
                            "last_confidence": "medium",
                            "last_review_date": None,
                            "next_review_date": None,
                            "next_review_day": None,
                            "reason": "",
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            close_request_file = Path(tmp) / "close-request.json"
            close_request_file.write_text(json.dumps(close_request), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "close-session",
                    "--request-file",
                    str(close_request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                completed.stdout.strip().splitlines(),
                [
                    "applied",
                    "warning: Held promotion for include_vs_extend because required visual is still missing.",
                    "held-item: include_vs_extend",
                    str(mastery_file),
                    str(review_queue_file),
                    str(session_history_file),
                ],
            )
            self.assertEqual(completed.stderr, "")

    def test_start_day_command_writes_daily_packets_and_reports_success(self) -> None:
        request = {
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

        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            request_file = Path(tmp) / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")

            init_completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "init-course",
                    "--request-file",
                    str(request_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init_completed.returncode, 0, init_completed.stderr)

            review_queue_file = workspace / "courses" / "operating-systems-midterm" / "state" / "review_queue.yaml"
            review_queue_file.write_text(
                json.dumps(
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
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "operating-systems-midterm",
                    "--day",
                    "1",
                    "--today",
                    "2026-04-23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            learning_file = workspace / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_01_learning.md"
            recall_file = workspace / "courses" / "operating-systems-midterm" / "outputs" / "daily" / "day_01_recall.md"
            course_file = workspace / "courses" / "operating-systems-midterm" / "course.yaml"

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("applied", completed.stdout)
            self.assertIn(str(learning_file), completed.stdout)
            self.assertIn(str(recall_file), completed.stdout)
            self.assertIn(str(course_file), completed.stdout)
            self.assertTrue(learning_file.exists())
            self.assertTrue(recall_file.exists())
            self.assertIn("2026-04-23", learning_file.read_text(encoding="utf-8"))
            self.assertIn("2026-04-23", recall_file.read_text(encoding="utf-8"))
            self.assertIn('"current_day": 1', course_file.read_text(encoding="utf-8"))

    def test_start_day_unknown_course_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "missing-course",
                    "--day",
                    "1",
                    "--today",
                    "2026-04-23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: unknown course_slug: missing-course", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((workspace / "courses" / "missing-course").exists())

    def test_start_day_invalid_today_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "operating-systems-midterm",
                    "--day",
                    "1",
                    "--today",
                    "2026/04/23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: today must be YYYY-MM-DD", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_start_day_zero_day_fails_cleanly(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "operating-systems-midterm",
                    "--day",
                    "0",
                    "--today",
                    "2026-04-23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: day_index must be a positive integer", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_start_day_negative_day_fails_cleanly(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-day",
                    "--course",
                    "operating-systems-midterm",
                    "--day",
                    "-3",
                    "--today",
                    "2026-04-23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: day_index must be a positive integer", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_start_final_recall_invalid_today_fails_cleanly_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "study_os",
                    "--workspace",
                    str(workspace),
                    "start-final-recall",
                    "--course",
                    "operating-systems-midterm",
                    "--today",
                    "2026/04/23",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            self.assertIn("error: today must be YYYY-MM-DD", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_public_course_commands_reject_malformed_course_selectors(self) -> None:
        command_cases = (
            ("start-day", ["--day", "1", "--today", "2026-04-23"]),
            ("start-final-recall", ["--today", "2026-04-23"]),
            ("status", []),
        )

        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            for course_selector in (".", "a/..", "nested/path"):
                for command, extra_args in command_cases:
                    with self.subTest(command=command, course=course_selector):
                        completed = subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "study_os",
                                "--workspace",
                                str(workspace),
                                command,
                                "--course",
                                course_selector,
                                *extra_args,
                            ],
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        self.assertEqual(completed.returncode, 2)
                        self.assertEqual(completed.stdout, "")
                        self.assertIn(
                            "error: course_slug must be a lowercase slug using only letters, digits, _ or -",
                            completed.stderr,
                        )
                        self.assertNotIn("Traceback", completed.stderr)

    def test_workspace_without_subcommand_returns_non_zero(self) -> None:
        with TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, "-m", "study_os", "--workspace", tmp],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("command", completed.stderr.lower())
