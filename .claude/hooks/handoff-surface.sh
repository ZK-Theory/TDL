#!/bin/bash
# handoff-surface: list recently-modified handoff documents at session start.
#
# Handoffs are written for a future agent and name their audience in a
# "**For:**" line, but nothing made that agent read them. On 2026-07-28 a
# briefing addressed to the running session by name sat unread for two hours
# while its contents -- the working pytest invocation, the pre-existing red
# baseline, and a verified two-line fix -- were rediscovered from scratch.
#
# Filing a document in the right directory is authorship, not delivery. This
# closes the gap by making the handoff arrive at the moment of need.
#
# Advisory only: never blocks, and exits 0 on every path including error.

set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || exit 0

# Overridable so the negative controls can widen or narrow the window.
DAYS="${HANDOFF_SURFACE_DAYS:-21}"
MAX="${HANDOFF_SURFACE_MAX:-8}"

# -mtime is a poor proxy for "recent" after a fresh clone or a worktree add,
# both of which reset mtimes wholesale. Prefer git's own last-commit date and
# fall back to mtime only when git is unavailable.
listing=$(
  cd "$ROOT" 2>/dev/null || exit 0
  if git rev-parse --git-dir >/dev/null 2>&1; then
    git ls-files -z -- 'docs/*/handoffs/*.md' 'docs/*/*/handoffs/*.md' 2>/dev/null |
      while IFS= read -r -d '' f; do
        ts=$(git log -1 --format=%ct -- "$f" 2>/dev/null)
        [ -n "$ts" ] && printf '%s\t%s\n' "$ts" "$f"
      done
  else
    find docs -type f -path '*/handoffs/*.md' -printf '%T@\t%p\n' 2>/dev/null
  fi
)

[ -n "$listing" ] || exit 0

cutoff=$(( $(date +%s) - DAYS * 86400 ))
recent=$(printf '%s\n' "$listing" |
  awk -F'\t' -v c="$cutoff" '$1 + 0 >= c' |
  sort -rn -k1,1 |
  head -n "$MAX")

[ -n "$recent" ] || exit 0

echo "Recent handoff documents (last ${DAYS} days) - check before starting work:"
printf '%s\n' "$recent" | while IFS=$'\t' read -r _ts path; do
  full="$ROOT/$path"
  # The "**For:**" line is the audience declaration; surfacing it is the whole
  # point, since it is what tells a reader the document is addressed to them.
  audience=$(grep -m1 -E '^\*\*For:\*\*' "$full" 2>/dev/null |
    sed -E 's/^\*\*For:\*\* *//' | cut -c1-100)
  title=$(grep -m1 -E '^# ' "$full" 2>/dev/null | sed -E 's/^# *//' | cut -c1-90)
  [ -n "$title" ] || title=$(basename "$path")
  echo "  - ${path}"
  echo "      ${title}"
  [ -n "$audience" ] && echo "      For: ${audience}"
done
echo "  Read any whose 'For:' line matches this session before improvising."

exit 0
