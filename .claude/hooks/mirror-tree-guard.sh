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
# directory THAT LIVES UNDER THIS PROJECT (the main checkout or one of its linked
# worktrees), matching both `/` and `\` separators (so `.apm/worktrees/<wt>/.claude/
# skills/...` and absolute `C:\...\.claude\skills\...` are both caught as long as
# they are still under $CLAUDE_PROJECT_DIR). The sync tool itself writes via Python
# (shutil.copy2), not an agent tool, so it never reaches this hook and is unaffected.
# Everything else is allowed. Fails open (loudly) on any error.
#
# Anchored to $CLAUDE_PROJECT_DIR (obs 127, 2026-07-27): an earlier version matched
# the bare substring `.claude/skills/` anywhere on disk, which also caught paths with
# no dual-tree sync relationship at all — e.g. the user's global, per-user skill store
# (~/.claude/skills/), which has no `.agents/skills/` source and is never touched by
# tools/sync_agent_skills.py. A path outside the project must never be denied here.

INPUT=$(cat)

printf '%s' "$INPUT" | python -c "
import sys, json, re, os

d = json.load(sys.stdin)
ti = d.get('tool_input') or {}
fp = ti.get('file_path') or ti.get('path') or ''

def emit(decision, reason=None):
    out = {'hookEventName': 'PreToolUse', 'permissionDecision': decision}
    if reason:
        out['permissionDecisionReason'] = reason
    print(json.dumps({'hookSpecificOutput': out}))
    sys.exit(0)

# Normalise Windows separators so the .claude/skills/ segment match below is
# separator-agnostic.
norm = fp.replace('\\\\', '/')

project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')

if not project_dir:
    # Can't scope the check without a project root. Raise rather than silently
    # emit('allow') here: the outer '2>/dev/null || { ... }' wrapper below would
    # swallow a stderr message printed from inside this process, so the only way
    # to make this loud is to fail the python invocation and let the EXISTING
    # fail-open fallback (which prints to stderr unconditionally) fire instead.
    raise RuntimeError('CLAUDE_PROJECT_DIR is not set — cannot scope the mirror-tree check')

# Containment via realpath+commonpath, not a string prefix: a lexical compare
# misses Windows case-insensitivity and '..'/'.'-segments, which would produce
# a FALSE NEGATIVE (a real mirror-tree edit reading as 'outside the project'
# and slipping through) — the dangerous direction, unlike obs 127's original
# false-positive bug. os.path.normcase folds case and separators on Windows.
def _canon(p):
    return os.path.normcase(os.path.realpath(p)) if p else ''

real_project = _canon(project_dir)
real_fp = _canon(fp)

in_project = False
if real_fp:
    try:
        in_project = os.path.commonpath([real_project, real_fp]) == real_project
    except ValueError:
        # Different drives (Windows) or an absolute/relative mismatch — treat
        # as outside the project rather than raising.
        in_project = False

if in_project and re.search(r'(^|/)\.claude/skills/', norm):
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
