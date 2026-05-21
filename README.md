# Study OS

Study OS is a filesystem-first study planning CLI that turns course scope, source references, and recall results into deterministic learning packets, review queues, and final-recall plans.

It is designed for exam preparation workflows where private course material should stay in a local runtime workspace while the engine code remains clean, testable, and publishable.

## What It Does

- Initializes a course from a structured JSON request.
- Writes canonical course state under `courses/<course_slug>/state/`.
- Generates daily learning and recall packets.
- Tracks mastery states from session results.
- Saves per-item draft answers, self-check results, 1-5 confidence scores, blocker types, and checkbox progress immediately without changing mastery state.
- Builds priority review queues using difficulty, importance, mistakes, confidence, exam proximity, and visual-material blockers.
- Produces a final recall pack near the exam.
- Serves local packet visuals from the course source tree without copying private assets into the engine repository.
- Builds close-session request drafts from saved in-packet progress.
- Validates local source files without copying private PDFs, transcripts, notes, or images into this repository.

## Tech Stack

- Python 3.10+
- Standard library only
- `unittest` test suite
- JSON-backed state files with `.yaml` filenames for YAML 1.2 compatibility

No database, web server, background service, package manager, or cloud account is required.

## Repository Layout

```text
study_os/
  cli.py                  # argparse command surface
  core/
    engine.py             # course initialization, day start, session close, final recall
    packets.py            # markdown packet rendering
    scheduler.py          # review queue priority and spacing policy
    transitions.py        # mastery state transitions
    validation.py         # request validation and defensive input checks
scripts/
  check.sh                # compile + full unittest verification
  prepare_real_course.py  # creates runtime source buckets and starter init requests
examples/
  sample_init_request.json
  sample_close_request.json
workspace_template/
  courses/sample-course/sources/
tests/
  core/ and integration tests
```

## Prerequisites

- Python 3.10 or newer.

The verification script auto-selects `python3.13`, `python3.12`, `python3.11`, `python3.10`, then `python3` if compatible. You can override it:

```bash
PYTHON=/path/to/python3.10 bash scripts/check.sh
```

## Quick Start

From a fresh clone:

```bash
git clone <repo-url>
cd study-os
bash scripts/check.sh
python3 -m study_os --help
```

Run the built-in sample flow in a temporary workspace:

```bash
tmp_workspace="$(mktemp -d)"
cp examples/sample_init_request.json "$tmp_workspace/init_request.json"
cp examples/sample_close_request.json "$tmp_workspace/close_request.json"

python3 -m study_os --workspace "$tmp_workspace" init-course \
  --request-file "$tmp_workspace/init_request.json"

python3 -m study_os --workspace "$tmp_workspace" start-day \
  --course sample-course \
  --day 1 \
  --today 2026-04-23

python3 -m study_os --workspace "$tmp_workspace" close-session \
  --request-file "$tmp_workspace/close_request.json"

python3 -m study_os --workspace "$tmp_workspace" start-final-recall \
  --course sample-course \
  --today 2026-04-23

python3 -m study_os --workspace "$tmp_workspace" status \
  --course sample-course
```

Generated files will be under:

```text
$tmp_workspace/courses/sample-course/
```

## CLI Commands

```bash
python3 -m study_os --help
```

Available commands:

- `init-course` - validate a course request and write canonical course state.
- `start-day` - create daily learning and recall markdown packets.
- `close-session` - apply reviewed item results and rebuild the review queue.
- `draft-close-session` - print a JSON close-session request draft from saved packet progress.
- `start-final-recall` - create the final recall pack.
- `status` - print tracked item and queue counts.


## HTML Packet Workflow

When using generated HTML packets through the local packet server, work inside each item before closing the session:

- Write the draft answer.
- Mark the self-check result as `correct`, `partial`, `wrong`, or `uncertain`.
- Set confidence from 1 to 5.
- Mark a blocker type when the miss has a clear cause.

Packet progress is stored in `state/packet_progress.yaml` as execution progress only. Local visual assets are served from the course `sources/` tree, so diagrams can be checked in the browser without copying private source assets into this repository. Mastery state still changes only through `close-session`.

After packet work, draft a close-session request from saved in-packet progress:

```bash
python3 -m study_os \
  --workspace /Users/<you>/Documents/study-workspace \
  draft-close-session \
  --course operating-systems-midterm \
  --packet-type learning \
  --day 1 \
  --session-date 2026-05-21
```

Review the JSON, then pass the edited request to `close-session`. The draft command itself does not change mastery, queues, or session history.

## Working With Real Course Sources

Private course material should live outside this engine repository. A typical runtime workspace is:

```text
/Users/<you>/Documents/study-workspace
```

Create source buckets and a starter source inventory:

```bash
python3 scripts/prepare_real_course.py \
  --workspace /Users/<you>/Documents/study-workspace \
  --course-slug operating-systems-midterm \
  --course-name "Operating Systems Midterm" \
  --exam-date 2026-05-20
```

Put files under:

```text
/Users/<you>/Documents/study-workspace/courses/operating-systems-midterm/sources/
  syllabus/      # syllabus, exam scope, rubrics
  slides/        # PDFs, slide decks, exported slide text
  transcripts/   # lecture transcripts or OCR text
  images/        # extracted diagrams, charts, tables, formulas
  notes/         # user notes and annotations
```

Refresh the generated request after adding files:

```bash
python3 scripts/prepare_real_course.py \
  --workspace /Users/<you>/Documents/study-workspace \
  --course-slug operating-systems-midterm \
  --course-name "Operating Systems Midterm" \
  --exam-date 2026-05-20 \
  --overwrite
```

Then initialize the course:

```bash
python3 -m study_os \
  --workspace /Users/<you>/Documents/study-workspace \
  init-course \
  --request-file /Users/<you>/Documents/study-workspace/courses/operating-systems-midterm/init_request.json \
  --validate-sources
```

`--validate-sources` checks that manifest paths stay inside the workspace, files exist and are non-empty, PDFs start with a PDF header, and text-like files are UTF-8.

The generated request is a starter inventory. For a real study run, decompose indexed sources into exam-scope blocks, recallable items, source references, and visual requirements before starting daily study.

## Course Request Shape

An init request contains:

- `course` - slug, name, exam date, timezone
- `blocks` - exam-scope topics with importance, difficulty, prerequisites, and visual needs
- `items` - recall prompts tied to blocks
- `source_manifest` - local source files that support each block
- `visual_requirements` - required diagrams/images that must exist before visual-dependent items can be promoted

See [examples/sample_init_request.json](examples/sample_init_request.json).

Session close requests record reviewed items:

```json
{
  "item_id": "scope_keywords",
  "phase": "learning",
  "result": "correct",
  "confidence": "medium",
  "note": "Recovered the scope keywords without checking notes."
}
```

Allowed `result` values are `correct`, `wrong`, `partial`, and `uncertain`. Allowed `confidence` values are `low`, `medium`, `high`, and `unknown`.

## Testing

Run the full local verification:

```bash
bash scripts/check.sh
```

This performs:

- `python -m compileall study_os tests`
- `python -m unittest discover -s tests -v`

## Environment Variables

Study OS does not require environment variables for normal use.

Optional:

- `PYTHON` - override the Python interpreter used by `scripts/check.sh`.

No `.env` file is needed. Keep private course files in a runtime workspace, not in this repository.

## Docker

Docker is not included. The project has no external services and runs directly with Python, so Docker would add more setup than it removes for normal local use.

## Deployment

Study OS is a local CLI engine rather than a hosted service. The realistic portfolio/review path is to run the CLI locally against sample or private runtime workspaces. If this becomes a web app or API later, deployment should be documented for that new interface.

## Security And Privacy

- Private course materials are intentionally kept outside the engine repository.
- Root-level `/courses/` and `/workspace.md` are ignored by Git.
- `.env` and local secret files are ignored.
- Source validation rejects paths that escape the workspace.
- Do not commit private PDFs, transcripts, notes, images, generated course state, or runtime logs.

## Troubleshooting

- `TypeError` from modern type syntax usually means the selected Python is too old. Use Python 3.10+.
- `unknown course_slug` means the course has not been initialized in the selected `--workspace`.
- `request file not found` means the `--request-file` path is wrong relative to your current shell.
- `--validate-sources` failures usually mean a manifest path is missing, empty, outside the workspace, not UTF-8, or not a valid PDF header.

## Current Limitations

- This repository is an engine and CLI, not a packaged PyPI distribution.
- The source inventory script does not automatically summarize PDFs or transcripts; decomposition is a separate workflow.
- No screenshots are included because the project currently has no GUI.
- No deployment target is included because the project is designed for local CLI use.
