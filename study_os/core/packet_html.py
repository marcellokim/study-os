from __future__ import annotations

from html import escape
import json
from urllib.parse import quote

from study_os.core.packet_models import PacketPage


_RESULT_OPTIONS = (
    ("correct", "정답"),
    ("partial", "부분"),
    ("wrong", "오답"),
    ("uncertain", "모름"),
)
_BLOCKER_OPTIONS = (
    ("concept", "개념"),
    ("memory", "기억"),
    ("application", "응용"),
    ("visual", "시각자료"),
    ("wording", "표현"),
    ("careless", "실수"),
    ("unknown", "불명"),
)


def _json_for_script(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _asset_url(relative_path: str) -> str:
    return "/assets/" + quote(relative_path.lstrip("/"), safe="/._-~")


def _style_block() -> str:
    return """
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f7f9;
        --surface: #ffffff;
        --surface-strong: #eef5f2;
        --text: #17211b;
        --muted: #5e6b63;
        --line: #d9e0dc;
        --accent: #1c6b51;
        --accent-soft: #dceee7;
        --warn-soft: #fff0d7;
        --shadow: 0 1px 2px rgba(23, 33, 27, 0.08);
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        letter-spacing: 0;
      }

      header {
        border-bottom: 1px solid var(--line);
        background: var(--surface);
      }

      .packet-shell {
        width: min(1120px, calc(100vw - 32px));
        margin: 0 auto;
      }

      .packet-header {
        display: grid;
        gap: 12px;
        padding: 28px 0 22px;
      }

      h1 {
        margin: 0;
        font-size: clamp(1.6rem, 2.1vw, 2.4rem);
        line-height: 1.18;
        letter-spacing: 0;
      }

      h2 {
        margin: 34px 0 12px;
        font-size: 1.12rem;
        letter-spacing: 0;
      }

      p { margin: 0; }

      nav {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      nav a {
        color: var(--accent);
        border: 1px solid var(--line);
        background: var(--surface);
        padding: 6px 10px;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 650;
      }

      main {
        padding: 8px 0 40px;
      }

      section > p {
        color: var(--muted);
        max-width: 76ch;
      }

      .packet-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 14px;
        color: var(--muted);
      }

      .packet-summary {
        max-width: 76ch;
        color: var(--muted);
      }

      .packet-checklist {
        margin: 14px 0 0;
        padding: 14px 18px 14px 34px;
        background: var(--surface-strong);
        border: 1px solid #c9ddd4;
        border-radius: 8px;
      }

      .packet-entry {
        display: grid;
        gap: 14px;
        margin: 14px 0;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: var(--shadow);
      }

      .packet-entry-header {
        display: grid;
        gap: 10px;
      }

      .packet-check {
        display: grid;
        grid-template-columns: 22px 1fr;
        gap: 10px;
        align-items: start;
        font-weight: 700;
      }

      .packet-check input {
        margin-top: 4px;
        inline-size: 18px;
        block-size: 18px;
      }

      .packet-entry-body {
        display: grid;
        gap: 10px;
      }

      .packet-answer-key,
      .packet-detail {
        padding: 12px 14px;
        border-left: 4px solid var(--accent);
        background: #f8fbf9;
        color: #26352d;
      }

      .packet-detail strong {
        display: block;
        margin-bottom: 4px;
      }

      .packet-answer-box {
        display: grid;
        gap: 8px;
      }

      .packet-answer-box > span {
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 700;
      }

      .packet-answer-box textarea {
        width: 100%;
        min-height: 132px;
        resize: vertical;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        color: var(--text);
        font: inherit;
      }

      .packet-answer-box textarea:focus {
        outline: 2px solid var(--accent-soft);
        border-color: var(--accent);
      }

      .packet-attempt {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.4fr);
        gap: 12px;
        padding: 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfcfd;
      }

      .packet-choice-group {
        min-width: 0;
      }

      .packet-choice-group > span {
        display: block;
        margin-bottom: 8px;
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 700;
      }

      .packet-choice-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .packet-choice {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        min-height: 34px;
        padding: 6px 9px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: var(--surface);
        cursor: pointer;
        font-weight: 650;
      }

      .packet-choice:has(input:checked) {
        border-color: var(--accent);
        background: var(--accent-soft);
        color: #0d4634;
      }

      .packet-save-state {
        grid-column: 1 / -1;
        min-height: 20px;
        color: var(--muted);
        font-size: 0.9rem;
      }

      .packet-empty-state {
        padding: 16px;
        border: 1px dashed var(--line);
        border-radius: 8px;
        background: var(--warn-soft);
      }

      .packet-draft-panel {
        display: grid;
        gap: 10px;
        padding: 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfcfd;
      }

      .packet-draft-panel button {
        justify-self: start;
        min-height: 36px;
        padding: 7px 12px;
        border: 1px solid var(--accent);
        border-radius: 6px;
        background: var(--accent);
        color: #fff;
        cursor: pointer;
        font: inherit;
        font-weight: 700;
      }

      .packet-draft-panel pre {
        overflow: auto;
        max-height: 280px;
        margin: 0;
        padding: 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        white-space: pre-wrap;
      }

      .packet-visuals {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
        margin: 12px 0 0;
      }

      .packet-visual {
        display: grid;
        gap: 8px;
        margin: 0;
        padding: 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }

      .packet-visual-available {
        border-color: #c9ddd4;
        background: #f8fbf9;
      }

      .packet-visual-missing {
        border-style: dashed;
        background: var(--warn-soft);
      }

      .packet-visual img {
        width: 100%;
        max-height: 420px;
        object-fit: contain;
        border-radius: 6px;
        background: #fff;
      }

      .packet-visual figcaption {
        display: grid;
        gap: 2px;
        color: var(--muted);
        font-size: 0.9rem;
      }

      code {
        overflow-wrap: anywhere;
      }

      @media (max-width: 720px) {
        .packet-shell {
          width: min(100vw - 20px, 1120px);
        }

        .packet-header {
          padding-top: 20px;
        }

        .packet-entry {
          padding: 14px;
        }

        .packet-attempt {
          grid-template-columns: 1fr;
        }
      }
    </style>
    """


def _choice_group(
    *,
    item_id: str,
    group: str,
    label: str,
    selected: str | None,
    options: tuple[tuple[str, str], ...],
) -> str:
    choices = []
    for value, text in options:
        checked = " checked" if selected == value else ""
        choices.append(
            f"""
            <label class="packet-choice">
              <input type="radio" data-action="attempt" data-item-id="{escape(item_id)}"
                     data-field="{escape(group)}" name="{escape(group)}-{escape(item_id)}"
                     value="{escape(value)}"{checked}>
              <span>{escape(text)}</span>
            </label>
            """
        )
    return (
        f'<div class="packet-choice-group"><span>{escape(label)}</span>'
        f'<div class="packet-choice-row">{"".join(choices)}</div></div>'
    )


def _confidence_score_group(*, item_id: str, selected: int | None) -> str:
    choices = []
    for score in range(1, 6):
        value = str(score)
        checked = " checked" if selected == score else ""
        choices.append(
            f"""
            <label class="packet-choice">
              <input type="radio" data-action="attempt" data-item-id="{escape(item_id)}"
                     data-field="confidence_score" name="confidence_score-{escape(item_id)}"
                     value="{value}"{checked}>
              <span>{value}</span>
            </label>
            """
        )
    return (
        '<div class="packet-choice-group"><span>자신감 1-5</span>'
        f'<div class="packet-choice-row">{"".join(choices)}</div></div>'
    )


def render_packet_html(packet: PacketPage, *, packet_links: dict[str, str]) -> str:
    nav = "".join(
        f'<a href="{escape(url)}" data-nav="{escape(name)}">{escape(name)}</a>'
        for name, url in packet_links.items()
    )

    body_sections: list[str] = []
    for section in packet.sections:
        checklist_html = ""
        if section.checklist_items:
            checklist_items = "".join(f"<li>{escape(item)}</li>" for item in section.checklist_items)
            checklist_html = f'<ul class="packet-checklist">{checklist_items}</ul>'

        entry_html: list[str] = []
        for entry in section.entries:
            checked = " checked" if entry.checked else ""
            answer_key_html = (
                f'<p class="packet-answer-key"><strong>정답 기준</strong>{escape(entry.answer_key)}</p>'
                if entry.answer_key
                else ""
            )
            learning_note_html = (
                f'<p class="packet-detail"><strong>핵심 개념</strong>{escape(entry.learning_note)}</p>'
                if entry.learning_note
                else ""
            )
            rubric_html = (
                f'<p class="packet-detail"><strong>채점 기준</strong>{escape(entry.rubric)}</p>'
                if entry.rubric
                else ""
            )
            answer_html = f"""
                <label class="packet-answer-box">
                  <span>내 답안</span>
                  <textarea data-action="draft-answer" data-item-id="{escape(entry.item_id)}"
                            rows="5" placeholder="정답을 보기 전에 먼저 내 답안을 적어라.">{escape(entry.draft_answer or "")}</textarea>
                </label>
            """
            attempt_html = (
                '<div class="packet-attempt">'
                + _choice_group(
                    item_id=entry.item_id,
                    group="result",
                    label="정답도",
                    selected=entry.result,
                    options=_RESULT_OPTIONS,
                )
                + _confidence_score_group(item_id=entry.item_id, selected=entry.confidence_score)
                + _choice_group(
                    item_id=entry.item_id,
                    group="blocker_type",
                    label="막힌 이유",
                    selected=entry.blocker_type,
                    options=_BLOCKER_OPTIONS,
                )
                + '<p class="packet-save-state" aria-live="polite"></p>'
                + "</div>"
            )
            entry_html.append(
                f"""
                <article class="packet-entry" data-item-id="{escape(entry.item_id)}">
                  <div class="packet-entry-header">
                    <label class="packet-check">
                      <input type="checkbox" data-action="checked" data-item-id="{escape(entry.item_id)}"{checked}>
                      <span>{escape(entry.prompt)}</span>
                    </label>
                  </div>
                  <div class="packet-entry-body">
                    {answer_html}
                    {attempt_html}
                    {learning_note_html}
                    {answer_key_html}
                    {rubric_html}
                  </div>
                </article>
                """
            )

        if not entry_html and section.empty_state_text:
            entry_html.append(f'<p class="packet-empty-state">{escape(section.empty_state_text)}</p>')

        visual_figures = []
        for visual in section.visual_requirements:
            visual_class = (
                "packet-visual packet-visual-available"
                if visual.status == "available"
                else "packet-visual packet-visual-missing"
            )
            image_html = ""
            if visual.status == "available":
                image_html = (
                    f'<img src="{escape(_asset_url(visual.required_image))}" '
                    f'alt="{escape(visual.description)}" loading="lazy">'
                )
            visual_figures.append(
                f"""
                <figure class="{visual_class}" data-item-id="{escape(visual.item_id)}">
                  {image_html}
                  <figcaption>
                    <span>{escape(visual.item_id)}</span>
                    <span>{escape(visual.description)}</span>
                    <code>{escape(visual.required_image)}</code>
                  </figcaption>
                </figure>
                """
            )
        visuals_block = f'<div class="packet-visuals">{"".join(visual_figures)}</div>' if visual_figures else ""
        helper_html = f"<p>{escape(section.helper_text)}</p>" if section.helper_text else ""

        body_sections.append(
            f"""
            <section data-section-id="{escape(section.section_id)}">
              <h2>{escape(section.title)}</h2>
              {helper_html}
              {checklist_html}
              {''.join(entry_html)}
              {visuals_block}
            </section>
            """
        )

    generated_date = f"<p>{escape(packet.generated_date)}</p>" if packet.generated_date else ""
    packet_type_json = _json_for_script(packet.packet_type)
    day_index_json = _json_for_script(packet.day_index)
    generated_date_json = _json_for_script(packet.generated_date or "")

    style_block = _style_block()

    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(packet.page_title)}</title>
    {style_block}
  </head>
  <body data-packet-type="{escape(packet.packet_type)}">
    <header>
      <div class="packet-shell packet-header">
        <h1>{escape(packet.page_title)}</h1>
        <div class="packet-meta">
          <p>{escape(packet.course_name)}</p>
          {generated_date}
        </div>
        <nav>{nav}</nav>
        <p class="packet-summary">{escape(packet.summary_text)}</p>
        <div class="packet-draft-panel">
          <button type="button" data-action="close-session-draft">마감 초안 생성</button>
          <pre data-close-session-draft aria-live="polite"></pre>
        </div>
      </div>
    </header>
    <main class="packet-shell">{''.join(body_sections)}</main>
    <script>
      const packetProgressContext = {{
        packet_type: {packet_type_json},
        day_index: {day_index_json},
        session_date: {generated_date_json}
      }};

      function progressKey() {{
        if (packetProgressContext.day_index === null || packetProgressContext.day_index === undefined) {{
          return packetProgressContext.packet_type;
        }}
        return `${{packetProgressContext.packet_type}}:day:${{packetProgressContext.day_index}}`;
      }}

      function rememberAttemptState(container) {{
        container.querySelectorAll('input[data-field]').forEach((input) => {{
          input.dataset.wasChecked = input.checked ? 'true' : 'false';
        }});
      }}

      function applyEntryProgress(itemId, progress) {{
        const container = document.querySelector(`.packet-entry[data-item-id="${{CSS.escape(itemId)}}"]`);
        if (!container || !progress) {{
          return;
        }}
        const checkbox = container.querySelector('input[data-action="checked"]');
        if (checkbox && typeof progress.checked === 'boolean') {{
          checkbox.checked = progress.checked;
        }}
        const draftAnswer = container.querySelector('textarea[data-action="draft-answer"]');
        if (draftAnswer && typeof progress.draft_answer === 'string') {{
          draftAnswer.value = progress.draft_answer;
        }}
        if (progress.result) {{
          const resultInput = container.querySelector(`input[data-field="result"][value="${{CSS.escape(progress.result)}}"]`);
          if (resultInput) {{
            resultInput.checked = true;
          }}
        }}
        if (progress.confidence_score) {{
          const confidenceInput = container.querySelector(`input[data-field="confidence_score"][value="${{CSS.escape(String(progress.confidence_score))}}"]`);
          if (confidenceInput) {{
            confidenceInput.checked = true;
          }}
        }}
        if (progress.blocker_type) {{
          const blockerInput = container.querySelector(`input[data-field="blocker_type"][value="${{CSS.escape(progress.blocker_type)}}"]`);
          if (blockerInput) {{
            blockerInput.checked = true;
          }}
        }}
        rememberAttemptState(container);
      }}

      async function loadSavedProgress() {{
        const response = await fetch('/api/progress');
        if (!response.ok) {{
          return;
        }}
        const allProgress = await response.json();
        const packetProgress = allProgress[progressKey()] || {{}};
        Object.entries(packetProgress).forEach(([itemId, progress]) => {{
          applyEntryProgress(itemId, progress);
        }});
      }}

      async function saveProgress(payload, container) {{
        const status = container ? container.querySelector('.packet-save-state') : null;
        if (status) {{
          status.textContent = '저장 중';
        }}
        const response = await fetch('/api/progress', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{
            packet_type: packetProgressContext.packet_type,
            day_index: packetProgressContext.day_index,
            ...payload
          }})
        }});
        if (!response.ok) {{
          throw new Error('progress save failed');
        }}
        if (status) {{
          status.textContent = '저장됨';
        }}
      }}

      document.querySelectorAll('input[type="checkbox"][data-action="checked"]').forEach((checkbox) => {{
        checkbox.addEventListener('change', async () => {{
          const previous = !checkbox.checked;
          const container = checkbox.closest('.packet-entry');
          checkbox.disabled = true;
          try {{
            await saveProgress({{
              item_id: checkbox.dataset.itemId,
              checked: checkbox.checked
            }}, container);
          }} catch (error) {{
            checkbox.checked = previous;
          }} finally {{
            checkbox.disabled = false;
          }}
        }});
      }});

      document.querySelectorAll('input[type="radio"][data-action="attempt"]').forEach((radio) => {{
        radio.addEventListener('change', async () => {{
          const container = radio.closest('.packet-entry');
          const field = radio.dataset.field;
          const selectedResult = container.querySelector('input[data-field="result"]:checked');
          const selectedConfidenceScore = container.querySelector('input[data-field="confidence_score"]:checked');
          const selectedBlocker = container.querySelector('input[data-field="blocker_type"]:checked');
          container.querySelectorAll('input[data-action="attempt"]').forEach((input) => {{
            input.disabled = true;
          }});
          try {{
            await saveProgress({{
              action: 'attempt',
              item_id: radio.dataset.itemId,
              result: selectedResult ? selectedResult.value : undefined,
              confidence_score: selectedConfidenceScore ? Number(selectedConfidenceScore.value) : undefined,
              blocker_type: selectedBlocker ? selectedBlocker.value : undefined
            }}, container);
          }} catch (error) {{
            radio.checked = false;
            const previous = container.querySelector(`input[data-field="${{field}}"][data-was-checked="true"]`);
            if (previous) {{
              previous.checked = true;
            }}
          }} finally {{
            container.querySelectorAll('input[data-action="attempt"]').forEach((input) => {{
              input.disabled = false;
            }});
            rememberAttemptState(container);
          }}
        }});
      }});

      document.querySelectorAll('textarea[data-action="draft-answer"]').forEach((textarea) => {{
        textarea.addEventListener('blur', async () => {{
          const container = textarea.closest('.packet-entry');
          textarea.disabled = true;
          try {{
            await saveProgress({{
              action: 'attempt',
              item_id: textarea.dataset.itemId,
              draft_answer: textarea.value
            }}, container);
          }} catch (error) {{
            const status = container ? container.querySelector('.packet-save-state') : null;
            if (status) {{
              status.textContent = '저장 실패';
            }}
          }} finally {{
            textarea.disabled = false;
          }}
        }});
      }});

      async function loadCloseSessionDraft() {{
        const output = document.querySelector('[data-close-session-draft]');
        if (!output) {{
          return;
        }}
        output.textContent = '마감 초안을 불러오는 중';
        const params = new URLSearchParams({{
          packet_type: packetProgressContext.packet_type,
          session_date: packetProgressContext.session_date
        }});
        if (packetProgressContext.day_index !== null && packetProgressContext.day_index !== undefined) {{
          params.set('day_index', String(packetProgressContext.day_index));
        }}
        try {{
          const response = await fetch(`/api/close-session-draft?${{params.toString()}}`);
          if (!response.ok) {{
            throw new Error('close-session draft failed');
          }}
          const draft = await response.json();
          output.textContent = JSON.stringify(draft, null, 2);
        }} catch (error) {{
          output.textContent = '마감 초안을 불러오지 못했습니다.';
        }}
      }}

      const closeSessionDraftButton = document.querySelector('[data-action="close-session-draft"]');
      if (closeSessionDraftButton) {{
        closeSessionDraftButton.addEventListener('click', loadCloseSessionDraft);
      }}
      document.querySelectorAll('.packet-entry').forEach((container) => {{
        rememberAttemptState(container);
      }});
      loadSavedProgress();
    </script>
  </body>
</html>
"""
