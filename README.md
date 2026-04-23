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

## File-format rule

State files ending in `.yaml` are written as pretty-printed JSON so they remain valid YAML 1.2 without adding dependencies.
