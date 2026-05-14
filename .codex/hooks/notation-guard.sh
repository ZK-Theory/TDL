#!/bin/bash
# notation-guard: block writes to papers/**/*.{md,tex,txt} containing W_1 Wasserstein notation.
# Project convention (CONVENTIONS.md + papers/shared/notation.md): W_2 is mandatory.
# Exception: papers/shared/ — notation.md itself documents the wrong patterns.

INPUT=$(cat)

# Extract file path (works for Write and all Edit variants)
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ti.get('path', '')))
" 2>/dev/null)

# Only check prose/markup files — not Python code (handled by ruff)
case "$FILE_PATH" in
  *.md|*.tex|*.txt) ;;
  *) printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'; exit 0 ;;
esac

# Only apply inside papers/, skip papers/shared/ (the audit files themselves)
case "$FILE_PATH" in
  */papers/shared/*|*\\papers\\shared\\*)
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'; exit 0 ;;
  */papers/*|*\\papers\\*) ;;
  *)
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'; exit 0 ;;
esac

# Extract content being written (Write => 'content', Edit => 'new_string')
CONTENT=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('content', '') + ti.get('new_string', ''))
" 2>/dev/null)

# Check for W_1 / W_{1} — but not W_12, W_16, etc.
VIOLATION=$(printf '%s' "$CONTENT" | python3 -c "
import sys, re
text = sys.stdin.read()
if re.search(r'W_\{?1\}?(?!\d)', text):
    print('found')
" 2>/dev/null)

if [ "$VIOLATION" = "found" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Notation violation: W_1 (Wasserstein-1) found in papers/ draft. Project convention mandates W_2. Replace W_1 with W_2 (LaTeX: W_2 or W_{2}). See papers/shared/notation.md, or run /wasserstein-audit for a full audit."}}'
else
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
fi
exit 0
