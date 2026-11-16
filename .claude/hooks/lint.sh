#!/usr/bin/env bash
# PostToolUse (Edit|Write): format and lint the edited Python file with ruff.
# Unfixable lint errors go back to Claude via exit 2 so it fixes them.
set -uo pipefail

file=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[[ "$file" == *.py && -f "$file" ]] || exit 0

# Same ruff version as requirements-dev.txt; runs on the host, no container needed.
RUFF_VERSION=$(grep -E '^ruff==' "$CLAUDE_PROJECT_DIR/requirements-dev.txt" | cut -d= -f3)
ruff=(uvx --quiet "ruff@${RUFF_VERSION:-0.17.5}")

cd "$CLAUDE_PROJECT_DIR" || exit 0
"${ruff[@]}" format --quiet "$file"
if ! out=$("${ruff[@]}" check --fix --quiet "$file" 2>&1); then
  echo "ruff found problems in $file that it could not auto-fix:" >&2
  echo "$out" >&2
  exit 2
fi
exit 0
