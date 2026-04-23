# Study OS v1

Filesystem-first study operating system with a deterministic core.

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
