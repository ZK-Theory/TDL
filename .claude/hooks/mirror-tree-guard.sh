#!/bin/bash
# mirror-tree-guard: block an agent Write/Edit/MultiEdit into the Claude-side
# MIRROR skill tree (.claude/skills/...).
#
# Why: .agents/skills/ is the single authoring source of truth; .claude/skills/
# is a byte-mirror produced by tools/sync_agent_skills.py (pre-commit Gate 0).
# An edit applied to the mirror is silently overwritten — or worse, REVERSES a
# newer authoring-tree fix — at the next sync. Skill prose (tda-skill-authoring-
# workbench, tda-agent-safety-guardrails) states this as a rule; a rule that only
# lives in prose is the anti-pattern SKL-4 exists to close, so it is a hook.
#
# Scope: a Write/Edit/MultiEdit whose target path resolves inside a `.claude/skills/`
# directory, matching both `/` and `\` separators and worktree paths (the segment
# appears regardless of the prefix, so `.apm/worktrees/<wt>/.claude/skills/...` and
# absolute `C:\...\.claude\skills\...` are both caught). The sync tool itself writes
# via Python (shutil.copy2), not an agent tool, so it never reaches this hook and is
# unaffected. Everything else is allowed. Fails open (loudly) on any error.

INPUT=$(cat)

printf '%s' "$INPUT" | python -c "
import sys, json, re

d = json.load(sys.stdin)
ti = d.get('tool_input', {})
fp = ti.get('file_path', ti.get('path', '')) or ''

def emit(decision, reason=None):
    out = {'hookEventName': 'PreToolUse', 'permissionDecision': decision}
    if reason:
        out['permissionDecisionReason'] = reason
    print(json.dumps({'hookSpecificOutput': out}))
    sys.exit(0)

# Normalise Windows separators so the path segment match is separator-agnostic.
norm = fp.replace('\\\\', '/')

# Target inside the Claude-side mirror skill tree (any prefix, incl. worktrees)?
if re.search(r'(^|/)\.claude/skills/', norm):
    emit('deny',
         'Blocked: %s is inside the Claude-side MIRROR skill tree (.claude/skills/). '
         'Skills are authored ONLY in the .agents/skills/ tree, then mirrored with '
         '\`uv run python tools/sync_agent_skills.py\`. A direct edit to the mirror is '
         'overwritten (or reverses a newer authoring-tree fix) at the next sync. '
         'Edit the matching file under .agents/skills/ and run the sync tool instead.'
         % fp)

emit('allow')
" 2>/dev/null || {
  # Fail open so a broken hook never blocks all writes — but make it LOUD, because
  # silent absence is the failure mode this project treats as cardinal. A bypass
  # here only risks a mirror edit being lost at the next sync (Gate 0 still catches
  # divergence at commit); it cannot corrupt a result.
  printf 'mirror-tree-guard: hook errored or timed out — FAILING OPEN (write allowed). Do not edit .claude/skills/ directly; author under .agents/skills/ and run tools/sync_agent_skills.py.\n' >&2
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
}
