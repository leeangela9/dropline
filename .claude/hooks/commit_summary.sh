#!/usr/bin/env bash
# PreToolUse (Bash, git commit): summarize what is about to be committed.
# Shows the summary to the user and to Claude. Never blocks the commit.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // empty')
[[ "$cmd" =~ (^|[;&|[:space:]])git[[:space:]]+commit ]] || exit 0

cd "$CLAUDE_PROJECT_DIR" || exit 0

# `git commit -a` / `--all` also commits tracked, unstaged changes.
if [[ "$cmd" =~ [[:space:]](-a|--all|-[a-zA-Z]*a[a-zA-Z]*)([[:space:]]|$) ]]; then
  diff_args=(HEAD)
  scope="staged + tracked unstaged (commit -a)"
else
  diff_args=(--cached)
  scope="staged"
fi

files=$(git diff "${diff_args[@]}" --name-status)
if [[ -z "$files" ]]; then
  summary="Pre-commit summary: nothing $scope to commit on $(git branch --show-current)."
else
  stat=$(git diff "${diff_args[@]}" --shortstat | sed 's/^ *//')
  summary="Pre-commit summary ($scope) on branch $(git branch --show-current): $stat
$files"
  # Flag files that should never be committed.
  risky=$(echo "$files" | awk '{print $NF}' | grep -E '(^|/)\.env$|dropline-practice-project\.md' || true)
  if [[ -n "$risky" ]]; then
    summary="$summary
WARNING: these files should not be committed: $risky"
  fi
fi

jq -n --arg s "$summary" '{
  systemMessage: $s,
  hookSpecificOutput: { hookEventName: "PreToolUse", additionalContext: $s }
}'
exit 0
