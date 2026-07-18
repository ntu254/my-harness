#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Repository root: $ROOT_DIR"

required=(
  "AGENTS.md"
  "README.md"
  "harness.yaml"
  "harness/features.json"
  "harness/progress.md"
  "docs/INTAKE.md"
  "docs/WORKFLOWS.md"
  "docs/VERIFICATION.md"
  "docs/HUMAN_GATE.md"
)

missing=()
for path in "${required[@]}"; do
  if [ ! -e "$path" ]; then
    missing+=("$path")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  printf 'Missing required files:\n' >&2
  printf '  %s\n' "${missing[@]}" >&2
  exit 1
fi

python -m json.tool harness/features.json >/dev/null

echo "==> Required files present"
echo "==> features.json parses"
echo "==> Next: read harness/progress.md and classify the requested work"
