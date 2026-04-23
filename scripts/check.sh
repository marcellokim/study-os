#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

select_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s\n' "$PYTHON"
    return
  fi

  local candidate
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      then
        printf '%s\n' "$candidate"
        return
      fi
    fi
  done

  return 1
}

python_bin="$(select_python)" || {
  echo "error: Study OS checks require Python 3.10 or newer" >&2
  echo "hint: install Python 3.10+ or run with PYTHON=/path/to/python bash scripts/check.sh" >&2
  exit 1
}

cd "$repo_root"
echo "Using $($python_bin --version)"
"$python_bin" -m compileall study_os tests
"$python_bin" -m unittest discover -s tests -v
