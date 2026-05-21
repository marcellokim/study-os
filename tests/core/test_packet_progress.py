from __future__ import annotations

import unittest

from study_os.core.packet_progress import (
    build_progress_key,
    empty_packet_progress,
    normalize_packet_progress,
    set_packet_attempt,
    set_packet_checked,
)


class PacketProgressTest(unittest.TestCase):
    def test_progress_key_is_scoped_by_packet_type_and_day(self) -> None:
        self.assertEqual(
            build_progress_key(packet_type="learning", day_index=3),
            "learning:day:3",
        )

    def test_progress_key_uses_bare_packet_type_without_day(self) -> None:
        self.assertEqual(
            build_progress_key(packet_type="final_recall", day_index=None),
            "final_recall",
        )

    def test_progress_key_rejects_bare_daily_packet_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "day_index"):
            build_progress_key(packet_type="learning", day_index=None)

        with self.assertRaisesRegex(ValueError, "day_index"):
            build_progress_key(packet_type="recall", day_index=None)

    def test_progress_key_rejects_ambiguous_packet_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "packet_type"):
            build_progress_key(packet_type="", day_index=1)

        with self.assertRaisesRegex(ValueError, "packet_type"):
            build_progress_key(packet_type="learning:day", day_index=1)

    def test_progress_key_rejects_invalid_day_index(self) -> None:
        with self.assertRaisesRegex(ValueError, "day_index"):
            build_progress_key(packet_type="learning", day_index=0)

        with self.assertRaisesRegex(ValueError, "day_index"):
            build_progress_key(packet_type="learning", day_index=-3)

    def test_set_packet_checked_rejects_invalid_item_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "item_id"):
            set_packet_checked(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="",
                checked=True,
            )

    def test_set_packet_checked_rejects_non_boolean_checked(self) -> None:
        with self.assertRaisesRegex(ValueError, "checked"):
            set_packet_checked(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                checked="yes",
            )

    def test_set_packet_checked_only_touches_requested_item(self) -> None:
        payload = empty_packet_progress()

        updated = set_packet_checked(
            payload,
            packet_type="recall",
            day_index=2,
            item_id="paging",
            checked=True,
        )

        self.assertTrue(updated["recall:day:2"]["paging"]["checked"])
        self.assertEqual(payload, {})

    def test_set_packet_checked_preserves_unrelated_entries_and_is_copy_on_write(self) -> None:
        payload = {
            "recall:day:2": {
                "fork": {"checked": False},
            },
            "learning:day:1": {
                "paging": {"checked": False},
            },
        }

        updated = set_packet_checked(
            payload,
            packet_type="learning",
            day_index=1,
            item_id="paging",
            checked=True,
        )

        self.assertIsNot(updated, payload)
        self.assertIsNot(updated["learning:day:1"], payload["learning:day:1"])
        self.assertEqual(updated["recall:day:2"], payload["recall:day:2"])
        self.assertFalse(payload["learning:day:1"]["paging"]["checked"])
        self.assertTrue(updated["learning:day:1"]["paging"]["checked"])

    def test_set_packet_attempt_stores_result_and_confidence_without_losing_checked(self) -> None:
        payload = {
            "learning:day:1": {
                "paging": {"checked": True},
            },
        }

        updated = set_packet_attempt(
            payload,
            packet_type="learning",
            day_index=1,
            item_id="paging",
            result="partial",
            confidence="low",
            blocker_type="concept_connection_gap",
        )

        self.assertEqual(
            updated["learning:day:1"]["paging"],
            {
                "checked": True,
                "result": "partial",
                "confidence": "low",
                "blocker_type": "concept_connection_gap",
            },
        )
        self.assertEqual(payload["learning:day:1"]["paging"], {"checked": True})

    def test_set_packet_attempt_rejects_unsupported_result_confidence_and_blocker_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "result"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                result="almost",
                confidence="high",
            )

        with self.assertRaisesRegex(ValueError, "confidence"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                result="correct",
                confidence="sure",
            )

        with self.assertRaisesRegex(ValueError, "blocker_type"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                result="partial",
                confidence="low",
                blocker_type="unknown_gap",
            )

    def test_set_packet_attempt_stores_draft_answer_confidence_score_and_checked_at(self) -> None:
        payload = {
            "learning:day:1": {
                "paging": {"checked": True},
            },
        }

        updated = set_packet_attempt(
            payload,
            packet_type="learning",
            day_index=1,
            item_id="paging",
            draft_answer="Paging maps virtual pages to physical frames.",
            result="partial",
            confidence_score=2,
            blocker_type="concept",
            checked_at="2026-05-21T09:30:00Z",
        )

        self.assertEqual(
            updated["learning:day:1"]["paging"],
            {
                "checked": True,
                "draft_answer": "Paging maps virtual pages to physical frames.",
                "result": "partial",
                "confidence": "low",
                "confidence_score": 2,
                "blocker_type": "concept",
                "checked_at": "2026-05-21T09:30:00Z",
            },
        )
        self.assertEqual(payload["learning:day:1"]["paging"], {"checked": True})

    def test_set_packet_attempt_rejects_invalid_confidence_score_and_draft_answer(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence_score"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                confidence_score=0,
            )

        with self.assertRaisesRegex(ValueError, "confidence_score"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                confidence_score=6,
            )

        with self.assertRaisesRegex(ValueError, "draft_answer"):
            set_packet_attempt(
                empty_packet_progress(),
                packet_type="learning",
                day_index=1,
                item_id="paging",
                draft_answer=["not", "text"],
            )

    def test_normalize_packet_progress_accepts_legacy_and_m0_blocker_types(self) -> None:
        payload = {
            "learning:day:1": {
                "legacy": {
                    "checked": False,
                    "confidence": "medium",
                    "blocker_type": "concept_connection_gap",
                },
                "m0": {
                    "checked": True,
                    "draft_answer": "answer",
                    "confidence_score": 5,
                    "blocker_type": "careless",
                    "checked_at": "2026-05-21T09:30:00Z",
                },
            }
        }

        normalized = normalize_packet_progress(payload)

        self.assertEqual(normalized["learning:day:1"]["legacy"]["confidence"], "medium")
        self.assertEqual(normalized["learning:day:1"]["legacy"]["blocker_type"], "concept_connection_gap")
        self.assertEqual(normalized["learning:day:1"]["m0"]["confidence"], "high")
        self.assertEqual(normalized["learning:day:1"]["m0"]["confidence_score"], 5)
        self.assertEqual(normalized["learning:day:1"]["m0"]["blocker_type"], "careless")
