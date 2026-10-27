#!/bin/bash
# research-context-check: warn when a newly created .py file lacks the mandatory
# "# Research context:" header (project convention from CLAUDE.md).
# Only triggers on Write (new file creation), not Edit (partial edits won't have full content).

INPUT=$(cat)

# Extract file path
FILE_PATH=$(printf '%s' "$INPUT" | python -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ti.get('path', '')))
" 2>/dev/null)

# Only check Python files
case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

# Only files the TDL convention governs: a relative path, or an absolute path inside
# $CLAUDE_PROJECT_DIR (its linked worktrees included), and never a scratchpad or temp file.
# 193 of the first 282 advisories were scratchpad files and 54 were other trees
# (obs 2026-10-27-research-context-advisory-fires-mostly-outside-the-repo).
IN_SCOPE=$(FILE_PATH="$FILE_PATH" python -c "
import os, re
def norm(p):
    p = p.replace('\\\\', '/').lower().rstrip('/')
    return re.sub(r'^/([a-z])/', r'\1:/', p)  # Git Bash /c/... and Windows c:/... name one path
path, project = norm(os.environ['FILE_PATH']), norm(os.environ.get('CLAUDE_PROJECT_DIR', ''))
if '/scratchpad/' in path:
    print('no')
elif not re.match(r'^([a-z]:/|/)', path):
    print('yes')
elif project:
    print('yes' if (path + '/').startswith(project + '/') else 'no')
else:
    print('no' if re.search(r'/(appdata/local/temp|tmp)/', path) else 'yes')
" 2>/dev/null)
[ "$IN_SCOPE" = "no" ] && exit 0

# Get content — only Write tool has 'content'; Edit tools have old_string/new_string (skip)
CONTENT=$(printf '%s' "$INPUT" | python -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('content', ''))
" 2>/dev/null)

# Empty string means this was an Edit tool call — not a new file, skip
[ -z "$CONTENT" ] && exit 0

# Check first 10 lines for the mandatory header
FOUND=$(printf '%s' "$CONTENT" | head -10 | grep -c '# Research context:' 2>/dev/null)
FOUND=${FOUND:-0}

if [ "$FOUND" -eq 0 ]; then
  echo "Warning: $(basename "$FILE_PATH") is missing the mandatory research context header."
  echo "Add near the top of the file:"
  echo "  # Research context: TDA-Research/03-Papers/PXX/_project.md"
  echo "  # Purpose: [what this script does in the research context]"
fi
exit 0
