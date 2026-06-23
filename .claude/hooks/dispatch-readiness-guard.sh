#!/bin/bash
# dispatch-readiness-guard: block a Manager dispatch (Task Prompt written to a
# Worker bus) that has not been through the dispatch-readiness gate.
#
# Why this is a hook and not just a guide rule: the dispatch procedure
# (.claude/apm-guides/task-assignment.md §2.5/§3.3 — worktree, .env, contracts,
# input-provenance) is lazy-loaded and does NOT survive context compaction. The
# compaction summary is task-state-focused; the role discipline drops out. This
# hook fires at the moment of the bus write, independent of what is in context,
# so "I described the workspace in the envelope" can no longer pass for "I did
# the setup". The forcing function lives on disk, not in the model's memory.
#
# Scope: a Write to .apm/bus/<agent>/task.md that is a Task Prompt (has a
# "## Workspace" section or a frontmatter log_path/tasks key). Such an envelope
# MUST carry a "## Dispatch Readiness" block (the pasted output of
# shared/manager_dispatch_check.py) showing PASS. Relays / plain status messages
# (no Workspace section) are allowed. Fails open on any error.

INPUT=$(cat)

printf '%s' "$INPUT" | python -c "
import sys, json, re

d = json.load(sys.stdin)
tool = d.get('tool_name', '')
ti = d.get('tool_input', {})
fp = (ti.get('file_path') or ti.get('path') or '').replace('\\\\', '/')
content = ti.get('content', '') or ''

def emit(decision, reason=None):
    out = {'hookEventName': 'PreToolUse', 'permissionDecision': decision}
    if reason:
        out['permissionDecisionReason'] = reason
    print(json.dumps({'hookSpecificOutput': out}))
    sys.exit(0)

# Scope: a bus Task Prompt write only.
if not re.search(r'(^|/)\.apm/bus/[^/]+/task\.md\$', fp):
    emit('allow')
if tool != 'Write':
    # Envelopes are written whole via Write; an incremental Edit cannot be judged
    # from a partial diff — allow and rely on the eventual Write.
    emit('allow')

# Is this a Task Prompt (a dispatch), versus a relay / plain status message?
is_dispatch = (
    '## Workspace' in content
    or re.search(r'(?m)^\\s*(log_path|tasks)\\s*:', content) is not None
)
if not is_dispatch:
    emit('allow')

# A dispatch must carry the Dispatch Readiness block, and it must show PASS.
if '## Dispatch Readiness' not in content:
    emit('deny',
         'This Task Prompt has no \"## Dispatch Readiness\" section. Run the '
         'dispatch-readiness gate and paste its output before writing the bus '
         'envelope:  uv run python -m shared.manager_dispatch_check --agent '
         '<slug> --branch <branch> --mode <parallel|sequential> '
         '[--provenance-manifest <yaml>]. It verifies the worktree+.env, the '
         'contracts (validate-only), the input-provenance ledger, and a cleared '
         'report bus actually exist on disk — not just that the envelope '
         'describes them (task-assignment.md §3.3).')

if re.search(r'Dispatch Readiness[\\s\\S]*\\*\\*FAIL\\*\\*', content):
    emit('deny',
         'The Dispatch Readiness block reports FAIL — a dispatch prerequisite '
         '(worktree/.env, contracts, input-provenance, or report bus) is not '
         'satisfied. Resolve the failing item (or surface a User decision, e.g. '
         'an unresolved data-vintage choice) before issuing the Task. Do not '
         'dispatch on a failed readiness gate.')

emit('allow')
" 2>/dev/null || {
  printf 'dispatch-readiness-guard: hook errored or timed out — FAILING OPEN (write allowed). Verify dispatch readiness manually (worktree+.env, contracts, input-provenance, cleared report bus) before issuing the Task.\n' >&2
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
}
