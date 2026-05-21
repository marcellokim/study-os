from __future__ import annotations

import unittest

from study_os.core.packet_html import render_packet_html
from study_os.core.packet_models import PacketEntry, PacketPage, PacketSection, PacketVisual


class PacketHtmlTest(unittest.TestCase):
    def test_html_contains_nav_checkbox_and_data_attributes(self) -> None:
        packet = PacketPage(
            packet_type="learning",
            page_title="Day 01 학습 패킷",
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            day_index=1,
            generated_date="2026-05-18",
            summary_text="summary",
            sections=[
                PacketSection(
                    section_id="items",
                    title="문항별 학습 카드",
                    entries=[
                        PacketEntry(
                            item_id="paging",
                            block_id="memory",
                            prompt="Explain paging.",
                            checked=True,
                            draft_answer="Paging maps pages to frames.",
                            result="partial",
                            confidence_score=2,
                            blocker_type="concept",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={"learning": "/packets/learning/day/1"})
        self.assertIn('data-packet-type="learning"', html)
        self.assertIn('input type="checkbox"', html)
        self.assertIn('data-item-id="paging"', html)
        self.assertIn('href="/packets/learning/day/1"', html)
        self.assertIn("fetch('/api/progress'", html)
        self.assertIn('packet_type: "learning"', html)
        self.assertIn("day_index: 1", html)
        self.assertIn('data-action="attempt"', html)
        self.assertIn('name="result-paging"', html)
        self.assertIn('value="partial" checked', html)
        self.assertIn('name="confidence_score-paging"', html)
        self.assertIn('data-field="confidence_score"', html)
        self.assertIn('value="2" checked', html)
        self.assertIn('name="blocker_type-paging"', html)
        self.assertIn('value="concept" checked', html)
        self.assertIn("막힌 이유", html)
        self.assertIn("<style>", html)
        self.assertIn("loadSavedProgress", html)
        self.assertIn("fetch('/api/progress')", html)

    def test_html_renders_answer_textarea_and_restores_draft_answer(self) -> None:
        packet = PacketPage(
            packet_type="learning",
            page_title="Day 01 학습 패킷",
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            day_index=1,
            generated_date="2026-05-18",
            summary_text="summary",
            sections=[
                PacketSection(
                    section_id="items",
                    title="문항별 학습 카드",
                    entries=[
                        PacketEntry(
                            item_id="paging",
                            block_id="memory",
                            prompt="Explain paging.",
                            draft_answer='Paging keeps "pages" & frames aligned.',
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn('class="packet-answer-box"', html)
        self.assertIn("내 답안", html)
        self.assertIn('textarea data-action="draft-answer"', html)
        self.assertIn('data-item-id="paging"', html)
        self.assertIn('rows="5"', html)
        self.assertIn('Paging keeps &quot;pages&quot; &amp; frames aligned.', html)
        self.assertIn("progress.draft_answer", html)

    def test_html_renders_close_session_draft_button_and_loader(self) -> None:
        packet = PacketPage(
            packet_type="recall",
            page_title="Day 01 회상 패킷",
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            day_index=1,
            generated_date="2026-05-18",
            summary_text="summary",
            sections=[],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn('data-action="close-session-draft"', html)
        self.assertIn('data-close-session-draft', html)
        self.assertIn("function loadCloseSessionDraft", html)
        self.assertIn("/api/close-session-draft", html)
        self.assertIn('session_date: "2026-05-18"', html)

    def test_html_renders_available_visual_as_asset_figure(self) -> None:
        packet = PacketPage(
            packet_type="learning",
            page_title="Day 01 학습 패킷",
            course_slug="software-engineering-midterm-testflight",
            course_name="Software Engineering Midterm",
            day_index=1,
            generated_date="2026-05-18",
            summary_text="summary",
            sections=[
                PacketSection(
                    section_id="visuals",
                    title="시각 자료",
                    visual_requirements=[
                        PacketVisual(
                            item_id="class_diagram",
                            required_image="/diagrams/class diagram & relation.png",
                            description='Class "association" diagram',
                            status="available",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn('class="packet-visual packet-visual-available"', html)
        self.assertIn(
            'src="/assets/diagrams/class%20diagram%20%26%20relation.png"',
            html,
        )
        self.assertIn('alt="Class &quot;association&quot; diagram"', html)
        self.assertIn('loading="lazy"', html)
        self.assertIn("Class &quot;association&quot; diagram", html)
        self.assertIn("/diagrams/class diagram &amp; relation.png", html)
