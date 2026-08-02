#!/bin/bash
# notation-guard: block writes to papers/**/*.{md,tex,txt} containing W_1 Wasserstein notation.
# Project convention (CONVENTIONS.md + papers/shared/notation.md): W_2 is mandatory.
# Exception: papers/shared/ — notation.md itself documents the wrong patterns.
#
# Every python subprocess below is checked for exit status. A failure is a
# loud, attributed fail-open (stderr "FAILING OPEN (reason)") rather than a
# silent fall-through to allow — the earlier version left no way to tell "no
# violation found" apart from "the check that would have found one never ran"
# (obs 2026-08-02-notation-guard-liveness-gap). This hook is wrapped by
# _receipt-wrap.sh in settings.json so every invocation, including a fail-open,
# leaves a durable entry in hook-receipts.log.
#
# Run `bash notation-guard.sh --selftest` to exercise the negative controls.

allow() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
  exit 0
}

fail_open() {
  printf 'notation-guard: FAILING OPEN (%s)\n' "$1" >&2
  allow
}

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Notation violation: W_1 (Wasserstein-1) found in papers/ draft. Project convention mandates W_2. Replace W_1 with W_2 (LaTeX: W_2 or W_{2}). See papers/shared/notation.md, or run /wasserstein-audit for a full audit."}}'
  exit 0
}

run_hook() {
  local input="$1"

  local file_path
  file_path=$(printf '%s' "$input" | python -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ti.get('path', '')))
" 2>/dev/null)
  if [ $? -ne 0 ]; then
    fail_open "file_path extraction failed"
  fi

  # Only check prose/markup files — not Python code (handled by ruff)
  case "$file_path" in
    *.md|*.tex|*.txt) ;;
    *) allow ;;
  esac

  # Only apply inside papers/, skip papers/shared/ (the audit files themselves).
  # Matches both a bare relative path ("papers/...") and an absolute/prefixed
  # one ("C:\...\papers\..."); the original prefixed-only patterns
  # (*/papers/*, *\\papers\\*) silently never matched a bare relative path
  # starting exactly with "papers/" — no character precedes it, so "*/" can't
  # match. Found by this file's own selftest.
  case "$file_path" in
    papers/shared/*|*/papers/shared/*|papers\\shared\\*|*\\papers\\shared\\*) allow ;;
    papers/*|*/papers/*|papers\\*|*\\papers\\*) ;;
    *) allow ;;
  esac

  local content
  content=$(printf '%s' "$input" | python -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('content', '') + ti.get('new_string', ''))
" 2>/dev/null)
  if [ $? -ne 0 ]; then
    fail_open "content extraction failed"
  fi

  # Check for W_1 / W_{1} — but not W_12, W_16, etc.
  local violation
  violation=$(printf '%s' "$content" | python -c "
import sys, re
text = sys.stdin.read()
if re.search(r'W_\{?1\}?(?!\d)', text):
    print('found')
" 2>/dev/null)
  if [ $? -ne 0 ]; then
    fail_open "violation regex check failed"
  fi

  if [ "$violation" = "found" ]; then
    deny
  else
    allow
  fi
}

selftest() {
  local failures=0

  check_decision() {
    local name="$1" payload="$2" expected="$3"
    local result actual
    result=$(printf '%s' "$payload" | bash "$0" 2>/dev/null)
    actual=$(printf '%s' "$result" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('hookSpecificOutput', {}).get('permissionDecision', ''))
except Exception:
    print('PARSE_ERROR')
" 2>/dev/null)
    if [ "$actual" = "$expected" ]; then
      printf 'PASS: %s\n' "$name"
    else
      printf 'FAIL: %s (expected %s, got %s)\n' "$name" "$expected" "$actual"
      failures=$((failures + 1))
    fi
  }

  check_decision "outside-papers-allow" \
    '{"tool_input":{"file_path":"README.md","content":"uses W_1 here"}}' \
    "allow"

  check_decision "papers-w1-deny" \
    '{"tool_input":{"file_path":"papers/P01/section.md","content":"the W_1 distance is..."}}' \
    "deny"

  check_decision "papers-w12-allow-not-a-w1-match" \
    '{"tool_input":{"file_path":"papers/P01/section.md","content":"W_12 clusters"}}' \
    "allow"

  check_decision "papers-shared-exception-allow" \
    '{"tool_input":{"file_path":"papers/shared/notation.md","content":"do not use W_1"}}' \
    "allow"

  check_decision "papers-non-prose-file-allow" \
    '{"tool_input":{"file_path":"papers/P01/script.py","content":"w1 = compute()"}}' \
    "allow"

  check_decision "edit-new-string-w1-deny" \
    '{"tool_input":{"file_path":"papers/P01/section.md","new_string":"see W_1 above"}}' \
    "deny"

  # Malformed JSON must fail open, but LOUDLY (stderr carries the FAILING OPEN marker).
  local result stderr_content actual stderr_tmpfile
  stderr_tmpfile=$(mktemp)
  result=$(printf 'not json at all' | bash "$0" 2>"$stderr_tmpfile")
  stderr_content=$(cat "$stderr_tmpfile" 2>/dev/null)
  rm -f "$stderr_tmpfile" 2>/dev/null
  actual=$(printf '%s' "$result" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('hookSpecificOutput', {}).get('permissionDecision', ''))
except Exception:
    print('PARSE_ERROR')
" 2>/dev/null)
  if [ "$actual" = "allow" ] && printf '%s' "$stderr_content" | grep -q 'FAILING OPEN'; then
    printf 'PASS: malformed-input-fails-open-loudly\n'
  else
    printf 'FAIL: malformed-input-fails-open-loudly (decision=%s stderr=%s)\n' "$actual" "$stderr_content"
    failures=$((failures + 1))
  fi

  if [ $failures -gt 0 ]; then
    printf '%d selftest(s) FAILED\n' "$failures" >&2
    exit 1
  fi
  printf 'All notation-guard selftests passed (7/7)\n'
  exit 0
}

if [ "${1:-}" = "--selftest" ]; then
  selftest
fi

INPUT=$(cat)
run_hook "$INPUT"
