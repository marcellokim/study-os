from __future__ import annotations

from html.parser import HTMLParser
import posixpath
import unittest
from urllib.parse import unquote, urlparse

from study_os.core.packet_html import render_packet_html, render_phase1_packet_html
from study_os.core.packet_models import PacketEntry, PacketPage, PacketSection, PacketVisual


class _ImageSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        attrs_by_name = dict(attrs)
        src = attrs_by_name.get("src")
        if src is not None:
            self.srcs.append(src)


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
        for value, label in (
            ("concept", "개념"),
            ("memory", "기억"),
            ("application", "응용"),
            ("visual", "시각자료"),
            ("wording", "표현"),
            ("careless", "실수"),
            ("unknown", "불명"),
        ):
            self.assertIn(f'value="{value}"', html)
            self.assertIn(f"<span>{label}</span>", html)
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
        self.assertIn('textarea.addEventListener(\'blur\'', html)
        self.assertIn("textarea.disabled = true", html)
        self.assertIn("action: 'attempt'", html)
        self.assertIn("item_id: textarea.dataset.itemId", html)
        self.assertIn("draft_answer: textarea.value", html)
        self.assertIn("textarea.disabled = false", html)

    def test_html_hides_answer_key_and_rubric_behind_reveal_boundary(self) -> None:
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
                            answer_key="Maps virtual pages to physical frames.",
                            rubric="Must mention indirection and fixed-size units.",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn('<details class="packet-answer-support"', html)
        self.assertIn("<summary>정답/채점 기준 보기</summary>", html)
        self.assertIn("Maps virtual pages to physical frames.", html)
        self.assertIn("Must mention indirection and fixed-size units.", html)
        self.assertLess(html.index("<summary>정답/채점 기준 보기</summary>"), html.index("정답 기준"))

    def test_phase1_packet_html_removes_answer_support_from_raw_html(self) -> None:
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
                            learning_note="Paging splits memory into fixed-size units.",
                            answer_key="Maps virtual pages to physical frames.",
                            rubric="Must mention indirection and fixed-size units.",
                        )
                    ],
                )
            ],
        )

        phase1_html = render_phase1_packet_html(render_packet_html(packet, packet_links={}))

        self.assertIn("Explain paging.", phase1_html)
        self.assertIn('class="packet-answer-box"', phase1_html)
        self.assertNotIn("packet-answer-support", phase1_html)
        self.assertNotIn("Paging splits memory into fixed-size units.", phase1_html)
        self.assertNotIn("Maps virtual pages to physical frames.", phase1_html)
        self.assertNotIn("Must mention indirection and fixed-size units.", phase1_html)

    def test_phase1_packet_html_removes_packet_nav_routes_previous_state_and_progress_script(self) -> None:
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
                            draft_answer="LEAKED PREVIOUS DRAFT",
                            result="correct",
                            confidence_score=4,
                            blocker_type="concept",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(
            packet,
            packet_links={
                "learning": "/packets/learning/day/1",
                "recall": "/packets/recall/day/1",
            },
        )

        phase1_html = render_phase1_packet_html(html)

        self.assertIn("Explain paging.", phase1_html)
        self.assertIn('class="packet-answer-box"', phase1_html)
        self.assertIn('value="correct"', phase1_html)
        self.assertIn('value="4"', phase1_html)
        self.assertIn('value="concept"', phase1_html)
        self.assertNotIn("/packets/learning/day/1", phase1_html)
        self.assertNotIn("/packets/recall/day/1", phase1_html)
        self.assertNotIn("LEAKED PREVIOUS DRAFT", phase1_html)
        self.assertNotIn('data-item-id="paging" checked', phase1_html)
        self.assertNotIn('value="correct" checked', phase1_html)
        self.assertNotIn('value="4" checked', phase1_html)
        self.assertNotIn('value="concept" checked', phase1_html)
        self.assertNotIn("loadSavedProgress", phase1_html)
        self.assertNotIn("/api/progress", phase1_html)

    def test_phase1_packet_html_removes_legacy_inline_answer_support(self) -> None:
        legacy_html = """
        <html><body>
          <ul class="packet-checklist">
            <li>별도 답안을 먼저 작성한다.</li>
            <li>정답 기준과 rubric으로 채점한다.</li>
            <li>model-answer grading support is available later.</li>
            <li>model answer examples are available later.</li>
            <li>model_answer field is available later.</li>
            <li>최종 암기 답안은 채점 단계에서만 본다.</li>
            <li>모범 답안은 채점 단계에서만 본다.</li>
          </ul>
          <article class="packet-entry" data-item-id="paging">
            <div class="packet-entry-header"><span>Explain paging.</span></div>
            <div class="packet-entry-body">
              <label class="packet-answer-box"><textarea></textarea></label>
              <p class="packet-detail"><strong>핵심 개념</strong>Paging splits memory.</p>
              <p class="packet-answer-key"><strong>정답 기준</strong>Map pages to frames.</p>
              <p class="packet-detail"><strong>채점 기준</strong>Mention indirection.</p>
            </div>
          </article>
        </body></html>
        """

        phase1_html = render_phase1_packet_html(legacy_html)

        self.assertIn("Explain paging.", phase1_html)
        self.assertIn("packet-answer-box", phase1_html)
        self.assertIn("별도 답안을 먼저 작성한다.", phase1_html)
        self.assertNotIn("rubric으로 채점", phase1_html)
        self.assertNotIn("정답 기준", phase1_html)
        self.assertNotIn("model-answer", phase1_html)
        self.assertNotIn("model answer", phase1_html)
        self.assertNotIn("model_answer", phase1_html)
        self.assertNotIn("최종 암기 답안", phase1_html)
        self.assertNotIn("모범 답안", phase1_html)
        self.assertNotIn("Paging splits memory.", phase1_html)
        self.assertNotIn("Map pages to frames.", phase1_html)
        self.assertNotIn("Mention indirection.", phase1_html)
        self.assertNotIn("packet-answer-key", phase1_html)

    def test_html_saves_confidence_score_in_attempt_payload(self) -> None:
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
                            confidence_score=5,
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn(
            "const selectedConfidenceScore = container.querySelector('input[data-field=\"confidence_score\"]:checked');",
            html,
        )
        self.assertIn(
            "confidence_score: selectedConfidenceScore ? Number(selectedConfidenceScore.value) : undefined",
            html,
        )

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

    def test_close_session_draft_waits_for_pending_draft_answer_saves(self) -> None:
        packet = PacketPage(
            packet_type="recall",
            page_title="Day 01 회상 패킷",
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            day_index=1,
            generated_date="2026-05-18",
            summary_text="summary",
            sections=[
                PacketSection(
                    section_id="items",
                    title="문항별 회상 카드",
                    entries=[
                        PacketEntry(
                            item_id="paging",
                            block_id="memory",
                            prompt="Explain paging.",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn("const pendingDraftAnswerSaves = new Set();", html)
        self.assertIn("async function saveDraftAnswer(textarea)", html)
        self.assertIn("pendingDraftAnswerSaves.add(savePromise)", html)
        self.assertIn("pendingDraftAnswerSaves.delete(savePromise)", html)
        self.assertIn("textarea.addEventListener('blur', async () =>", html)
        self.assertIn("await saveDraftAnswer(textarea)", html)
        self.assertIn(
            "await Promise.allSettled(Array.from(pendingDraftAnswerSaves));",
            html,
        )
        self.assertLess(
            html.index("await Promise.allSettled(Array.from(pendingDraftAnswerSaves));"),
            html.index("const response = await fetch(`/api/close-session-draft?${params.toString()}`);"),
        )

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

    def test_html_renders_missing_visual_without_image(self) -> None:
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
                            item_id="missing_diagram",
                            required_image="diagrams/missing diagram.png",
                            description="Missing class diagram",
                            status="missing",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertIn('class="packet-visual packet-visual-missing"', html)
        self.assertIn('data-item-id="missing_diagram"', html)
        self.assertIn("Missing class diagram", html)
        self.assertIn("diagrams/missing diagram.png", html)
        self.assertNotIn('src="/assets/diagrams/missing%20diagram.png"', html)

    def test_visual_asset_url_replaces_dot_segments_before_rendering(self) -> None:
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
                            item_id="secret",
                            required_image="../secret.png",
                            description="Unsafe traversal path",
                            status="available",
                        )
                    ],
                )
            ],
        )

        html = render_packet_html(packet, packet_links={})

        self.assertNotIn('src="/assets/../secret.png"', html)
        self.assertNotIn('src="/assets/%2E%2E/secret.png"', html)
        self.assertIn('src="/assets/_dotdot_/secret.png"', html)
        self.assertIn("../secret.png", html)

        parser = _ImageSrcParser()
        parser.feed(html)
        self.assertEqual(parser.srcs, ["/assets/_dotdot_/secret.png"])
        parsed_path = urlparse(parser.srcs[0]).path
        normalized_path = posixpath.normpath(unquote(parsed_path))
        self.assertTrue(
            normalized_path.startswith("/assets/"),
            f"{parser.srcs[0]} normalized outside /assets as {normalized_path}",
        )
        self.assertNotIn(".", unquote(parsed_path).split("/"))
        self.assertNotIn("..", unquote(parsed_path).split("/"))
