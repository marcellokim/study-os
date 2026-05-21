from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

from study_os.core.packet_server import PacketServer
from study_os.core.paths import build_course_paths
from study_os.core.storage import CourseStore


class PacketServerTest(unittest.TestCase):
    def _start_server(self, workspace: Path) -> tuple[PacketServer, threading.Thread]:
        server = PacketServer(workspace_root=workspace, course_slug="operating-systems-midterm", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)
        return server, thread

    def test_progress_post_persists_checked_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_packet_progress({})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "POST",
                "/api/progress",
                body=json.dumps(
                    {
                        "packet_type": "learning",
                        "day_index": 1,
                        "item_id": "paging",
                        "checked": True,
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertTrue(payload["saved"])
            self.assertTrue(store.load_packet_progress()["learning:day:1"]["paging"]["checked"])

    def test_progress_post_persists_attempt_result_confidence_and_blocker_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_packet_progress({"learning:day:1": {"paging": {"checked": True}}})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "POST",
                "/api/progress",
                body=json.dumps(
                    {
                        "action": "attempt",
                        "packet_type": "learning",
                        "day_index": 1,
                        "item_id": "paging",
                        "result": "partial",
                        "confidence": "low",
                        "blocker_type": "concept_connection_gap",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertTrue(payload["saved"])
            saved = store.load_packet_progress()["learning:day:1"]["paging"]
            self.assertEqual(saved["checked"], True)
            self.assertEqual(saved["result"], "partial")
            self.assertEqual(saved["confidence"], "low")
            self.assertEqual(saved["blocker_type"], "concept_connection_gap")
            self.assertIn("checked_at", saved)

    def test_progress_post_persists_draft_answer_confidence_score_blocker_and_checked_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_packet_progress({"learning:day:1": {"paging": {"checked": True}}})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "POST",
                "/api/progress",
                body=json.dumps(
                    {
                        "action": "attempt",
                        "packet_type": "learning",
                        "day_index": 1,
                        "item_id": "paging",
                        "draft_answer": "Paging maps pages.",
                        "result": "partial",
                        "confidence_score": 4,
                        "blocker_type": "careless",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            saved = store.load_packet_progress()["learning:day:1"]["paging"]
            self.assertEqual(response.status, 200)
            self.assertTrue(payload["saved"])
            self.assertEqual(saved["draft_answer"], "Paging maps pages.")
            self.assertEqual(saved["result"], "partial")
            self.assertEqual(saved["confidence_score"], 4)
            self.assertEqual(saved["confidence"], "high")
            self.assertEqual(saved["blocker_type"], "careless")
            self.assertIn("checked_at", saved)
            self.assertTrue(str(saved["checked_at"]).endswith("Z"))

    def test_get_serves_existing_learning_html_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            paths.learning_packet_html_file(day_index=1).write_text("<html>Learning packet</html>", encoding="utf-8")

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/packets/learning/day/1")
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertIn("Learning packet", body)

    def test_get_serves_workspace_asset_under_assets_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            image_path = workspace / "courses" / "operating-systems-midterm" / "sources" / "images" / "diagram.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"\x89PNG\r\n\x1a\nimage")

            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            CourseStore(paths).save_packet_progress({})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/assets/courses/operating-systems-midterm/sources/images/diagram.png")
            response = connection.getresponse()
            body = response.read()
            content_type = response.getheader("Content-Type")
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertEqual(body, b"\x89PNG\r\n\x1a\nimage")
            self.assertEqual(content_type, "image/png")

    def test_get_assets_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            CourseStore(paths).save_packet_progress({})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/assets/../secret.png")
            response = connection.getresponse()
            response.read()
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 404)

    def test_get_progress_returns_saved_packet_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_packet_progress(
                {
                    "learning:day:1": {
                        "paging": {
                            "checked": True,
                            "result": "partial",
                            "confidence": "low",
                            "blocker_type": "concept_connection_gap",
                        }
                    }
                }
            )

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/api/progress")
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertEqual(
                payload["learning:day:1"]["paging"],
                {
                    "checked": True,
                    "result": "partial",
                    "confidence": "low",
                    "blocker_type": "concept_connection_gap",
                },
            )

    def test_get_serves_existing_final_recall_html_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            paths.final_recall_html_file.write_text("<html>Final recall packet</html>", encoding="utf-8")

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request("GET", "/packets/final-recall")
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertIn("Final recall packet", body)

    def test_get_close_session_draft_returns_packet_progress_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_items(
                [
                    {
                        "item_id": "paging",
                        "block_id": "memory",
                        "prompt": "Explain paging.",
                        "answer_mode": "short-answer",
                        "difficulty": "medium",
                        "exam_relevance": "high",
                        "needs_visuals": False,
                    }
                ]
            )
            store.save_packet_progress(
                {
                    "learning:day:1": {
                        "paging": {
                            "checked": True,
                            "draft_answer": "Maps pages.",
                            "result": "partial",
                            "confidence_score": 3,
                            "confidence": "medium",
                            "blocker_type": "concept",
                        }
                    }
                }
            )

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "GET",
                "/api/close-session-draft?packet_type=learning&day_index=1&session_date=2026-05-21",
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 200)
            self.assertEqual(payload["course_slug"], "operating-systems-midterm")
            self.assertEqual(payload["session_date"], "2026-05-21")
            self.assertEqual(payload["day_index"], 1)
            self.assertEqual(payload["reviewed_items"][0]["item_id"], "paging")
            self.assertEqual(payload["reviewed_items"][0]["phase"], "learning")
            self.assertEqual(payload["reviewed_items"][0]["result"], "partial")
            self.assertEqual(payload["reviewed_items"][0]["confidence"], "medium")
            self.assertEqual(payload["reviewed_items"][0]["error_code"], "C1")

    def test_progress_post_rejects_invalid_payload_without_persisting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = build_course_paths(workspace, "operating-systems-midterm")
            paths.ensure_directories()
            store = CourseStore(paths)
            store.save_packet_progress({})

            server, thread = self._start_server(workspace)

            connection = HTTPConnection("127.0.0.1", server.port)
            connection.request(
                "POST",
                "/api/progress",
                body=json.dumps(
                    {
                        "packet_type": "learning",
                        "day_index": 1,
                        "item_id": "paging",
                        "checked": "yes",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            connection.close()

            server.shutdown()
            thread.join(timeout=1)

            self.assertEqual(response.status, 400)
            self.assertFalse(payload["saved"])
            self.assertEqual(store.load_packet_progress(), {})
