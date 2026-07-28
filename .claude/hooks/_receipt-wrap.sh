#!/bin/bash
# _receipt-wrap.sh: transparent wrapper around a PreToolUse hook that appends a
# durable one-line execution receipt (timestamp, hook name, decision, target
# file) to .claude/hooks/hook-receipts.log on every invocation, then re-emits
# the wrapped hook's stdout unchanged. Never alters the wrapped hook's decision
# and never blocks on a logging failure.
#
# Why (obs 121, 122, 125): PreToolUse hooks had no durable execution signal, so
# a silent fail-open (e.g. a cold-start subprocess-spawn racing the hook's own
# timeout — obs 125, empirically observed on dispatch-readiness-guard.sh's
# first invocation of a fresh session) left no trace distinguishing "nothing to
# deny" from "the check never ran." This wrapper makes every invocation —
# including a fail-open — visible after the fact via one grep-able log line,
# without touching the wrapped hook's own decision logic. Only wraps the three
# hooks that share the "... 2>/dev/null || { printf '...FAILING OPEN...' >&2;
# ...allow... }" pattern (results-no-overwrite, dispatch-readiness-guard,
# mirror-tree-guard); notation-guard.sh has a different structure with no
# unified fail-open signal and is not wrapped here (see obs 125 follow-up).
#
# Usage (from settings.json): _receipt-wrap.sh <hook-script-path>
# The wrapped hook still reads the tool-call JSON from stdin as normal.

set -u

HOOK_SCRIPT="$1"
HOOK_NAME="$(basename "$HOOK_SCRIPT" .sh)"
LOG="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/hook-receipts.log"

INPUT=$(cat)

FILE_PATH=$(printf '%s' "$INPUT" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('file_path', ti.get('path', '')))
except Exception:
    print('')
" 2>/dev/null)

STDERR_FILE=$(mktemp 2>/dev/null) || STDERR_FILE=""
STDERR_CAPTURED=1
if [ -n "$STDERR_FILE" ]; then
  OUTPUT=$(printf '%s' "$INPUT" | "$HOOK_SCRIPT" 2>"$STDERR_FILE")
  STATUS=$?
  STDERR_CONTENT=$(cat "$STDERR_FILE" 2>/dev/null)
  rm -f "$STDERR_FILE" 2>/dev/null
else
  # mktemp unavailable — we can still run the hook, but with stderr discarded
  # we lose the only signal ("FAILING OPEN") that distinguishes a checked
  # decision from the wrapped hook's own fail-open. Don't silently trust an
  # unexamined allow in that case — flag it as failed-open below instead.
  OUTPUT=$(printf '%s' "$INPUT" | "$HOOK_SCRIPT" 2>/dev/null)
  STATUS=$?
  STDERR_CONTENT=""
  STDERR_CAPTURED=0
fi

# A hook that hit its own internal fallback prints "FAILING OPEN" to stderr
# even though it still exits 0 and emits a well-formed allow JSON — that text
# is the only signal distinguishing a checked "allow" from an unchecked one.
if [ $STATUS -ne 0 ] || printf '%s' "$STDERR_CONTENT" | grep -q 'FAILING OPEN'; then
  DECISION="FAILOPEN(exit=$STATUS)"
elif [ "$STDERR_CAPTURED" -eq 0 ]; then
  DECISION="FAILOPEN(stderr-unavailable)"
else
  # Parse as JSON rather than grep/sed — json.dumps() inserts a space after
  # each colon ("permissionDecision": "deny"), which a naive no-space grep
  # pattern misses entirely, silently mis-tagging every real decision as
  # FAILOPEN(no-decision-in-output). Caught by this wrapper's own dry run.
  DECISION=$(printf '%s' "$OUTPUT" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('hookSpecificOutput', {}).get('permissionDecision', ''))
except Exception:
    print('')
" 2>/dev/null)
  [ -z "$DECISION" ] && DECISION="FAILOPEN(no-decision-in-output)"
fi

# Strip embedded CR/LF from the file path before it goes into a one-line
# receipt record — an unsanitised newline would split the record across
# lines (or forge a fake-looking second entry) in a log meant to be one
# invocation per line.
FILE_PATH_SAFE=$(printf '%s' "$FILE_PATH" | tr -d '\r\n')

{
  printf '%s hook=%s decision=%s file=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$HOOK_NAME" "$DECISION" "$FILE_PATH_SAFE" \
    >> "$LOG"
} 2>/dev/null || true

# Re-emit the wrapped hook's own stderr (e.g. the loud FAILING OPEN message)
# and stdout (the JSON decision the harness actually consumes) unchanged.
printf '%s' "$STDERR_CONTENT" >&2
printf '%s' "$OUTPUT"
exit "$STATUS"
