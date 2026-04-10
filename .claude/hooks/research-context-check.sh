#!/bin/bash
# research-context-check: warn when a newly created .py file lacks the mandatory
# "# Research context:" header (project convention from CLAUDE.md).
# Only triggers on Write (new file creation), not Edit (partial edits won't have full content).

INPUT=$(cat)

# Extract file path
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
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

# Get content — only Write tool has 'content'; Edit tools have old_string/new_string (skip)
CONTENT=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('content', ''))
" 2>/dev/null)

# Empty string means this was an Edit tool call — not a new file, skip
[ -z "$CONTENT" ] && exit 0

# Check first 10 lines for the mandatory header
FOUND=$(printf '%s' "$CONTENT" | head -10 | grep -c '# Research context:' 2>/dev/null || echo 0)

if [ "$FOUND" -eq 0 ]; then
  echo "Warning: $(basename "$FILE_PATH") is missing the mandatory research context header."
  echo "Add near the top of the file:"
  echo "  # Research context: TDA-Research/03-Papers/PXX/_project.md"
  echo "  # Purpose: [what this script does in the research context]"
fi
exit 0
