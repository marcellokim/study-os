# Source Workspace Template Design

## Goal

Make the source-material drop zone obvious before real-use testing, while keeping private course materials out of the public repository by default.

## Approved approach

Use the existing course layout as the source of truth: runtime workspaces store real course data under `courses/<course_slug>/sources/`. Track only a template copy under `workspace_template/` so GitHub users can see the intended folder shape without committing their own PDFs, transcripts, or notes.

## Components

- `README.md` documents where source files go and how to run the sample flow.
- `.gitignore` ignores root-level runtime `courses/` and generated `workspace.md`.
- `workspace_template/courses/sample-course/sources/` shows the five source buckets: syllabus, slides, transcripts, images, and notes.
- `examples/sample_init_request.json` and `examples/sample_close_request.json` provide valid request payloads that reference the template paths.
- An integration test runs the sample files through the CLI so docs and examples do not drift from the implementation.

## Data flow

A user copies or creates files under `courses/<course_slug>/sources/`, runs `init-course` with an init request that references those paths, then uses `start-day`, `close-session`, and `start-final-recall` to generate and update derived artifacts under the same course folder.

## Error handling

The template does not change runtime validation. Invalid course slugs, malformed JSON, missing courses, or invalid visual requirement references still fail through the existing CLI validation path.

## Testing

Run `bash scripts/check.sh`. The new example integration test proves the sample init request, source directories, day packet generation, close-session payload, and final recall command remain executable.
