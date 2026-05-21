from __future__ import annotations

import unittest

from study_os.core.models import Block, CourseConfig, Item, QueueEntry, VisualRequirement
from study_os.core.packet_builder import (
    build_final_recall_packet_model,
    build_learning_packet_model,
    build_recall_packet_model,
)


class PacketModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.course = CourseConfig(
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            exam_date="2026-05-20",
            timezone="Asia/Seoul",
            current_day=1,
        )
        self.memory_block = Block(
            block_id="memory",
            block_name="Memory",
            block_type="concept",
            importance="high",
            difficulty="medium",
            exam_relevance="direct",
            needs_prereq=False,
            needs_visuals=False,
            study_order=1,
        )
        self.cpu_block = Block(
            block_id="cpu",
            block_name="CPU",
            block_type="concept",
            importance="medium",
            difficulty="medium",
            exam_relevance="direct",
            needs_prereq=False,
            needs_visuals=False,
            study_order=2,
        )
        self.paging_item = Item(
            item_id="paging",
            block_id="memory",
            prompt="Explain paging.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=False,
            retrieval_cues=["Define page and frame."],
            answer_key="Maps virtual pages to physical frames.",
            rubric="Must mention indirection and fixed-size units.",
            model_answer="Paging maps fixed-size pages to physical frames via a page table.",
            worked_example="Virtual page 3 can point at physical frame 12.",
            correction_ladder=["Define page.", "Define frame.", "Explain the mapping table."],
            source_refs=["slides/memory.pdf#page=12"],
        )
        self.context_switch_item = Item(
            item_id="context_switch",
            block_id="cpu",
            prompt="Explain context-switch overhead.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=False,
        )

    def test_learning_packet_model_is_html_ready(self) -> None:
        packet = build_learning_packet_model(
            self.course,
            day_index=1,
            blocks=[self.memory_block],
            items_by_block={"memory": [self.paging_item]},
            visuals=[],
            today="2026-05-18",
            progress_by_item={"paging": True},
        )

        self.assertEqual(packet.packet_type, "learning")
        self.assertEqual(packet.page_title, "Day 01 학습 패킷")
        self.assertEqual(len(packet.sections), 3)
        self.assertEqual(
            packet.sections[0].checklist_items[0],
            "노트와 정답을 가리고 먼저 답한다.",
        )
        self.assertEqual(packet.sections[1].section_id, "items")
        self.assertTrue(packet.sections[1].entries[0].checked)
        self.assertEqual(packet.sections[1].entries[0].item_id, "paging")
        self.assertEqual(packet.sections[1].entries[0].source_refs, ["slides/memory.pdf#page=12"])

    def test_learning_packet_model_sorts_blocks_items_and_visuals(self) -> None:
        later_visual = VisualRequirement(
            block_id="memory",
            item_id="paging",
            required_image="paging-diagram.png",
            description="page/frame mapping",
            status="missing",
        )
        earlier_visual = VisualRequirement(
            block_id="cpu",
            item_id="context_switch",
            required_image="context-switch.png",
            description="register save and restore",
            status="missing",
        )

        packet = build_learning_packet_model(
            self.course,
            day_index=1,
            blocks=[self.cpu_block, self.memory_block],
            items_by_block={
                "memory": [self.paging_item],
                "cpu": [self.context_switch_item],
            },
            visuals=[later_visual, earlier_visual],
            today="2026-05-18",
            progress_by_item={},
        )

        self.assertEqual(
            [entry.item_id for entry in packet.sections[1].entries],
            ["paging", "context_switch"],
        )
        self.assertEqual(
            [visual.item_id for visual in packet.sections[2].visual_requirements],
            ["context_switch", "paging"],
        )

    def test_recall_packet_model_keeps_queue_reason(self) -> None:
        entry = QueueEntry(
            item_id="paging",
            block_id="memory",
            status="R1",
            priority="high",
            reason="wrong answer yesterday",
            next_review_date="2026-05-18",
            next_review_day=1,
            last_result="wrong",
            confidence="low",
        )
        new_item = Item(
            item_id="day0_followup",
            block_id="cpu",
            prompt="Explain same-day R0 follow-up.",
            answer_mode="short-answer",
            difficulty="medium",
            exam_relevance="high",
            needs_visuals=False,
            retrieval_cues=["Answer before checking the card."],
            answer_key="Must restate the new concept from memory.",
            rubric="Includes the concept and the key distinction.",
        )

        packet = build_recall_packet_model(
            self.course,
            day_index=1,
            queue_entries=[entry],
            items_by_id={"paging": self.paging_item, "day0_followup": new_item},
            visuals=[],
            today="2026-05-18",
            progress_by_item={},
            new_items=[new_item],
        )

        recall_entry = packet.sections[1].entries[0]
        self.assertEqual(packet.packet_type, "recall")
        self.assertEqual(
            packet.sections[0].checklist_items[0],
            "별도 답안을 먼저 작성하고 채팅으로 설명하지 않는다.",
        )
        self.assertEqual(recall_entry.priority, "high")
        self.assertEqual(recall_entry.reason, "wrong answer yesterday")
        self.assertEqual(packet.sections[2].section_id, "same_day_r0")
        self.assertEqual(packet.sections[2].entries[0].item_id, "day0_followup")
        self.assertEqual(
            packet.sections[2].entries[0].answer_key,
            "Must restate the new concept from memory.",
        )

    def test_recall_packet_model_carries_empty_state_for_queue_and_same_day_r0(self) -> None:
        packet = build_recall_packet_model(
            self.course,
            day_index=1,
            queue_entries=[],
            items_by_id={},
            visuals=[],
            today="2026-05-18",
            progress_by_item={},
            new_items=[],
        )

        self.assertEqual(packet.sections[1].section_id, "queue")
        self.assertEqual(packet.sections[1].entries, [])
        self.assertEqual(
            packet.sections[1].empty_state_text,
            "아직 마감된 복습 문항이 없습니다. 신규 학습 후 당일 회상을 실행하세요.",
        )
        self.assertEqual(packet.sections[2].section_id, "same_day_r0")
        self.assertEqual(packet.sections[2].entries, [])
        self.assertEqual(
            packet.sections[2].empty_state_text,
            "오늘 새로 배운 문항이 없습니다.",
        )

    def test_learning_packet_model_carries_draft_answer_confidence_score_and_empty_state(self) -> None:
        packet = build_learning_packet_model(
            self.course,
            day_index=3,
            blocks=[],
            items_by_block={},
            visuals=[],
            today="2026-05-21",
            progress_by_item={
                "paging": {
                    "checked": True,
                    "draft_answer": "My answer",
                    "confidence_score": 4,
                    "result": "correct",
                    "blocker_type": "careless",
                }
            },
        )

        self.assertEqual(packet.sections[1].entries, [])
        self.assertIn("복습 패킷", packet.sections[1].empty_state_text)

    def test_recall_packet_model_uses_exam_risk_order(self) -> None:
        generic = QueueEntry(
            item_id="context_switch",
            block_id="cpu",
            status="R1",
            priority="high",
            reason="scheduled by state policy",
            next_review_date="2026-05-21",
            next_review_day=1,
            last_result="correct",
            confidence="medium",
        )
        urgent = QueueEntry(
            item_id="paging",
            block_id="memory",
            status="R1",
            priority="urgent",
            reason="overconfidence",
            next_review_date="2026-05-22",
            next_review_day=2,
            last_result="wrong",
            confidence="high",
        )

        packet = build_recall_packet_model(
            self.course,
            day_index=1,
            queue_entries=[generic, urgent],
            items_by_id={"paging": self.paging_item, "context_switch": self.context_switch_item},
            visuals=[],
            today="2026-05-21",
            progress_by_item={"paging": {"checked": True, "draft_answer": "answer", "confidence_score": 1}},
            new_items=[],
        )

        self.assertEqual([entry.item_id for entry in packet.sections[1].entries], ["paging", "context_switch"])
        self.assertEqual(packet.sections[1].entries[0].draft_answer, "answer")
        self.assertEqual(packet.sections[1].entries[0].confidence_score, 1)

    def test_final_recall_model_keeps_visual_requirements(self) -> None:
        entry = QueueEntry(
            item_id="paging",
            block_id="memory",
            status="FINAL",
            priority="urgent",
            reason="exam near",
            next_review_date="2026-05-18",
            next_review_day=1,
            last_result="partial",
            confidence="medium",
        )
        visual = VisualRequirement(
            block_id="memory",
            item_id="paging",
            required_image="paging-diagram.png",
            description="page/frame mapping",
            status="missing",
        )

        packet = build_final_recall_packet_model(
            self.course,
            queue_entries=[entry],
            items_by_id={"paging": self.paging_item},
            blocks_by_id={"memory": self.memory_block},
            visuals=[visual],
            today="2026-05-18",
            progress_by_item={},
        )

        self.assertEqual(packet.packet_type, "final_recall")
        self.assertEqual(
            packet.sections[0].checklist_items[0],
            "기억만으로 먼저 답하고 범위를 넓히지 않는다.",
        )
        self.assertEqual(packet.sections[-1].visual_requirements[0].required_image, "paging-diagram.png")


if __name__ == "__main__":
    unittest.main()
