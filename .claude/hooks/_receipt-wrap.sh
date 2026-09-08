#!/bin/bash
# _receipt-wrap.sh: transparent wrapper around a harness hook that appends a
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
# without touching the wrapped hook's own decision logic. Wraps all four
# PreToolUse hooks (results-no-overwrite, dispatch-readiness-guard,
# mirror-tree-guard, notation-guard) — each prints a "FAILING OPEN (reason)"
# line to stderr on its own internal fallback path (obs
# 2026-08-02-notation-guard-liveness-gap closed notation-guard.sh's prior gap
# here: it now shares the same unified marker as the other three).
#
# Advisory mode (obs 2026-09-08-posttooluse-hooks-lack-receipt-wrap): the two
# PostToolUse hooks (research-context-check, results-vault-reminder) were wired
# into settings.json unwrapped and so had zero receipts across the log's entire
# history — indistinguishable from never having run. They cannot be wrapped in
# the default strict mode because they emit advisory text on stdout, never a
# permissionDecision JSON, so strict parsing would stamp every single
# invocation FAILOPEN(no-decision-in-output) and the receipt would carry no
# information. `--advisory` classifies on what an advisory hook actually
# signals instead: `advise` (it ran and had something to warn about) vs
# `silent` (it ran and matched nothing). Both are positive proof of execution,
# which is the whole point of the receipt for an always-exit-0 hook.
#
# Usage (from settings.json): _receipt-wrap.sh [--advisory] <hook-script-path>
# The wrapped hook still reads the tool-call JSON from stdin as normal.
#
# Mis-wiring control: when the harness payload carries `hook_event_name`, the
# mode flag is cross-checked against it and a mismatch is recorded as
# MISWIRED(<event>) rather than a decision — the flag is static wiring, so a
# strict-wrapped PostToolUse hook (or an advisory-wrapped PreToolUse gate, the
# strictly worse direction) leaves a durable trace instead of quietly
# mis-classifying every receipt it writes. The field is treated as optional:
# absent, the flag alone selects the mode.
#
# Run `bash _receipt-wrap.sh --selftest` to exercise the sanitizer negative
# controls (obs 2026-08-02-hook-receipts-log-content-injection).

set -u

if [ "${1:-}" = "--selftest" ]; then
  TMP_LOG=$(mktemp)
  TMP_HOOK=$(mktemp)
  printf '#!/bin/bash\ncat >/dev/null\nprintf %%s '"'"'{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'"'"'\n' > "$TMP_HOOK"
  chmod +x "$TMP_HOOK"
  FAILURES=0

  # 1. Confusable payload (no real newline) must not appear verbatim in the log.
  # The wrapper resolves LOG from CLAUDE_PROJECT_DIR, so redirect by pointing
  # CLAUDE_PROJECT_DIR at a scratch dir containing .claude/hooks/.
  CONFUSABLE='C:\Users\steph\.claude\skills\research-observer\SKILL.md2099-01-01T00:00:00Z hook=FORGED decision=deny file=nothing'
  SCRATCH_ROOT=$(mktemp -d)
  mkdir -p "$SCRATCH_ROOT/.claude/hooks"
  python -c "
import json, sys
sys.stdout.write(json.dumps({'tool_input': {'file_path': sys.argv[1]}}))
" "$CONFUSABLE" \
    | CLAUDE_PROJECT_DIR="$SCRATCH_ROOT" bash "$0" "$TMP_HOOK" > /dev/null 2>&1
  LOGGED=$(cat "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log" 2>/dev/null)
  LINE_COUNT=$(printf '%s\n' "$LOGGED" | grep -c '^')
  if [ "$LINE_COUNT" -eq 1 ] && printf '%s' "$LOGGED" | grep -q 'CONFUSABLE-RECEIPT-FIELD-REDACTED' \
     && ! printf '%s' "$LOGGED" | grep -q 'hook=FORGED'; then
    printf 'PASS: confusable-payload-defused-single-line\n'
  else
    printf 'FAIL: confusable-payload-defused-single-line (lines=%s content=%s)\n' "$LINE_COUNT" "$LOGGED"
    FAILURES=$((FAILURES + 1))
  fi

  # 2. Embedded real newline must still be stripped (pre-existing guarantee).
  : > "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log"
  printf '{"tool_input":{"file_path":"a/b\\nhook=X decision=Y file=Z"}}' \
    | CLAUDE_PROJECT_DIR="$SCRATCH_ROOT" bash "$0" "$TMP_HOOK" > /dev/null 2>&1
  LOGGED2=$(cat "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log" 2>/dev/null)
  LINE_COUNT2=$(printf '%s\n' "$LOGGED2" | grep -c '^')
  if [ "$LINE_COUNT2" -eq 1 ]; then
    printf 'PASS: embedded-real-newline-still-one-line\n'
  else
    printf 'FAIL: embedded-real-newline-still-one-line (lines=%s)\n' "$LINE_COUNT2"
    FAILURES=$((FAILURES + 1))
  fi

  # 3. Ordinary allow decision still logs correctly through the wrapper.
  : > "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log"
  printf '{"tool_input":{"file_path":"ordinary/file.md"}}' \
    | CLAUDE_PROJECT_DIR="$SCRATCH_ROOT" bash "$0" "$TMP_HOOK" > /dev/null 2>&1
  LOGGED3=$(cat "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log" 2>/dev/null)
  if printf '%s' "$LOGGED3" | grep -q 'decision=allow file=ordinary/file.md'; then
    printf 'PASS: ordinary-decision-logs-correctly\n'
  else
    printf 'FAIL: ordinary-decision-logs-correctly (content=%s)\n' "$LOGGED3"
    FAILURES=$((FAILURES + 1))
  fi

  # 4/5. Advisory mode distinguishes "ran and warned" from "ran and matched
  # nothing" — an always-exit-0 hook has no other observable trace, so a mode
  # that collapsed both into one value would defeat the receipt's purpose.
  TMP_ADVISORY=$(mktemp)
  printf '#!/bin/bash\ncat >/dev/null\n[ -n "${ADVISE:-}" ] && echo "Warning: something"\nexit 0\n' > "$TMP_ADVISORY"
  chmod +x "$TMP_ADVISORY"
  for CASE in advise silent; do
    : > "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log"
    if [ "$CASE" = "advise" ]; then export ADVISE=1; else unset ADVISE; fi
    printf '{"hook_event_name":"PostToolUse","tool_input":{"file_path":"a/results/x.json"}}' \
      | CLAUDE_PROJECT_DIR="$SCRATCH_ROOT" bash "$0" --advisory "$TMP_ADVISORY" > /dev/null 2>&1
    LOGGED4=$(cat "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log" 2>/dev/null)
    if printf '%s' "$LOGGED4" | grep -q "decision=$CASE file=a/results/x.json"; then
      printf 'PASS: advisory-mode-records-%s\n' "$CASE"
    else
      printf 'FAIL: advisory-mode-records-%s (content=%s)\n' "$CASE" "$LOGGED4"
      FAILURES=$((FAILURES + 1))
    fi
  done
  unset ADVISE

  # 6. A PreToolUse gate wrapped in advisory mode (the dangerous direction —
  # a real deny would be recorded as mere advice) must be caught, not classified.
  : > "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log"
  printf '{"hook_event_name":"PreToolUse","tool_input":{"file_path":"a/b.md"}}' \
    | CLAUDE_PROJECT_DIR="$SCRATCH_ROOT" bash "$0" --advisory "$TMP_HOOK" > /dev/null 2>&1
  LOGGED6=$(cat "$SCRATCH_ROOT/.claude/hooks/hook-receipts.log" 2>/dev/null)
  if printf '%s' "$LOGGED6" | grep -q 'decision=MISWIRED(PreToolUse)'; then
    printf 'PASS: mode-event-mismatch-recorded-as-miswired\n'
  else
    printf 'FAIL: mode-event-mismatch-recorded-as-miswired (content=%s)\n' "$LOGGED6"
    FAILURES=$((FAILURES + 1))
  fi

  rm -rf "$SCRATCH_ROOT" "$TMP_HOOK" "$TMP_ADVISORY" "$TMP_LOG" 2>/dev/null

  if [ "$FAILURES" -gt 0 ]; then
    printf '%d selftest(s) FAILED\n' "$FAILURES" >&2
    exit 1
  fi
  printf 'All _receipt-wrap selftests passed (6/6)\n'
  exit 0
fi

MODE="strict"
if [ "${1:-}" = "--advisory" ]; then
  MODE="advisory"
  shift
fi

HOOK_SCRIPT="$1"
HOOK_NAME="$(basename "$HOOK_SCRIPT" .sh)"
LOG="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/hook-receipts.log"

INPUT=$(cat)

# One python spawn extracts both fields (obs 125: cold-start subprocess spawns
# race the hook's own timeout, so don't add a second one). Emitted as
# "<event>\t<file_path>" with the event first — it is a fixed harness enum, so
# a tab or newline embedded in the *path* can only corrupt the trailing field,
# which the sanitizer below already handles.
EXTRACTED=$(printf '%s' "$INPUT" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    event = str(d.get('hook_event_name', ''))
    for bad in ('\t', '\r', '\n'):
        event = event.replace(bad, '')
    sys.stdout.write(event + '\t' + str(ti.get('file_path', ti.get('path', ''))))
except Exception:
    sys.stdout.write('\t')
" 2>/dev/null)
HOOK_EVENT=$(printf '%s' "$EXTRACTED" | head -1 | cut -f1)
FILE_PATH=$(printf '%s' "$EXTRACTED" | cut -f2-)

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

# The mode flag is static wiring; hook_event_name comes from the harness. When
# both are present and disagree, the receipt records the mis-wiring rather than
# a decision derived from the wrong parser — a receipt that silently
# mis-classifies is worse than no receipt, because it reads as evidence.
EXPECTED_EVENT="PreToolUse"
[ "$MODE" = "advisory" ] && EXPECTED_EVENT="PostToolUse"

# A hook that hit its own internal fallback prints "FAILING OPEN" to stderr
# even though it still exits 0 and emits a well-formed allow JSON — that text
# is the only signal distinguishing a checked "allow" from an unchecked one.
if [ -n "$HOOK_EVENT" ] && [ "$HOOK_EVENT" != "$EXPECTED_EVENT" ]; then
  DECISION="MISWIRED($HOOK_EVENT)"
elif [ $STATUS -ne 0 ] || printf '%s' "$STDERR_CONTENT" | grep -q 'FAILING OPEN'; then
  DECISION="FAILOPEN(exit=$STATUS)"
elif [ "$STDERR_CAPTURED" -eq 0 ]; then
  DECISION="FAILOPEN(stderr-unavailable)"
elif [ "$MODE" = "advisory" ]; then
  # An advisory PostToolUse hook never emits a permissionDecision — it exits 0
  # either way and its only observable output is the reminder text it prints on
  # a match. Both outcomes are positive proof of execution; the receipt exists
  # precisely because nothing else about this hook is observable downstream.
  if [ -n "$OUTPUT" ]; then
    DECISION="advise"
  else
    DECISION="silent"
  fi
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
# invocation per line. That alone is not enough (obs
# 2026-08-02-hook-receipts-log-content-injection): a file_path value can
# contain no real newline at all and still visually forge a second entry by
# merely containing a substring shaped like this file's own record format
# ("hook=X decision=Y file=Z"), which a real-newline-only strip does nothing
# to defuse and which any substring/grep-based liveness check (rather than a
# strict per-line, anchored-timestamp parse) would misread as genuine. Defuse
# any such confusable substring in addition to stripping CR/LF.
FILE_PATH_SAFE=$(printf '%s' "$FILE_PATH" | python -c "
import sys, re
text = sys.stdin.read()
text = text.replace('\r', '').replace('\n', '')
text = re.sub(r'hook=\S+\s+decision=\S+\s+file=', '[CONFUSABLE-RECEIPT-FIELD-REDACTED]', text)
sys.stdout.write(text)
" 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$FILE_PATH_SAFE" ]; then
  # Sanitizer itself failed (or the path was empty to begin with) — don't
  # silently fall through to the raw, unexamined value on the failure branch.
  if [ -n "$FILE_PATH" ]; then
    FILE_PATH_SAFE="[SANITIZE_FAILED]"
  else
    FILE_PATH_SAFE=""
  fi
fi

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
