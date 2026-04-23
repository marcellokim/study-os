# Study OS v1

Filesystem-first study operating system with a deterministic core.

## Requirements

- Python 3.10 or newer. `scripts/check.sh` auto-selects a compatible `python3.x` when available.

## Run the checks

```bash
bash scripts/check.sh
```

## CLI entrypoint

```bash
python3 -m study_os --help
```

## Example flow

```bash
python3 -m study_os --workspace . init-course --request-file init_request.json
python3 -m study_os --workspace . start-day --course operating-systems-midterm --day 1 --today 2026-04-23
python3 -m study_os --workspace . close-session --request-file close_request.json
python3 -m study_os --workspace . start-final-recall --course operating-systems-midterm --today 2026-04-23
python3 -m study_os --workspace . status --course operating-systems-midterm
```

## Real source smoke test

Use this when you want to drop your own PDFs and text files into a private local workspace before building the real course decomposition.

```bash
python3 scripts/prepare_real_course.py \
  --workspace . \
  --course-slug operating-systems-midterm \
  --course-name "Operating Systems Midterm" \
  --exam-date 2026-05-20
```

Put files under the generated source buckets:

```text
courses/operating-systems-midterm/sources/
  syllabus/      # .pdf, .txt, .md
  slides/        # .pdf, .txt, .md
  transcripts/   # .txt, .md
  images/        # extracted diagrams/images
  notes/         # .txt, .md
```

Refresh the generated request so it indexes the files you added:

```bash
python3 scripts/prepare_real_course.py \
  --workspace . \
  --course-slug operating-systems-midterm \
  --course-name "Operating Systems Midterm" \
  --exam-date 2026-05-20 \
  --overwrite
```

Then validate the referenced source files and initialize the course:

```bash
python3 -m study_os --workspace . init-course \
  --request-file courses/operating-systems-midterm/init_request.json \
  --validate-sources
```

`--validate-sources` checks that manifest paths stay inside the workspace, files exist and are non-empty, PDFs start with a PDF header, and text-like files are UTF-8. The generated request is only a starter source inventory; after this smoke test, Codex should read the indexed sources and replace the inventory placeholder with exam-scope blocks/items before the real study run.


## Where to put source files

Runtime course workspaces live under `courses/<course_slug>/`. The source-material drop zone is:

```text
courses/<course_slug>/sources/
  syllabus/      # syllabus, exam scope, rubrics
  slides/        # original PDFs, slide decks, exported slide text
  transcripts/   # lecture transcripts or OCR text
  images/        # extracted diagrams, charts, tables, handwriting, formulas
  notes/         # user notes and annotations
```

`init-course` creates this folder structure automatically and preserves existing files in `sources/` when you reinitialize a course. Root-level `courses/` is ignored by Git so private PDFs, transcripts, and notes do not get published accidentally.

A tracked template is available at `workspace_template/courses/sample-course/sources/`. To start from it:

```bash
cp -R workspace_template/courses .
python3 -m study_os --workspace . init-course --request-file examples/sample_init_request.json
```

Then replace the placeholder source paths in `examples/sample_init_request.json` with your real files, or create a new request file for your course slug.

## File-format rule

State files ending in `.yaml` are written as pretty-printed JSON so they remain valid YAML 1.2 without adding dependencies.
