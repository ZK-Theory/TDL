#!/bin/bash
# commit-state-guard: refuse a git commit whose outcome the session would misread.
#
# PreToolUse (Bash, PowerShell): denies `git commit ... | tail` without pipefail,
# because a pipeline reports its last command's status and a commit blocked by
# pre-commit then reads as exit 0 (obs 2026-09-08-blocked-commit-reported-exit-zero);
# and denies a commit when HEAD is not the branch this session last saw in that
# repository (obs 2026-09-08-concurrent-session-branch-switch); and denies setting
# TDL_ALLOW_MAIN_COMMIT, the owner's exception to the pre-commit main refusal.
# PostToolUse (Bash, PowerShell): records the branch of every repository a git
# command touched, one file per session, under <absolute-git-dir>/tdl-session-branches/.
#
# Logic lives in commit_state_guard.py. Fails OPEN with the FAILING OPEN marker that
# _receipt-wrap.sh records: the pre-commit branch gate (.githooks/pre-commit, gate -1)
# still refuses commits on main when this hook cannot run.

INPUT=$(cat)
HERE=$(cd "$(dirname "$0")" && pwd)

OUTPUT=$(printf '%s' "$INPUT" | python "$HERE/commit_state_guard.py" 2>/dev/null)
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
  printf 'commit-state-guard: hook errored or timed out -- FAILING OPEN (command allowed).\n' >&2
  if printf '%s' "$INPUT" | grep -q '"PostToolUse"'; then
    exit 0
  fi
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
  exit 0
fi

printf '%s' "$OUTPUT"
exit 0
