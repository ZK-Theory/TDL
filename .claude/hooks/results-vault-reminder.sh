#!/bin/bash
# results-vault-reminder: nudge to log to Computational-Log when a quantitative
# results file is written under results/. Fires on .json, .npy, .npz, .csv, .pkl.

INPUT=$(cat)

# Extract file path
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ti.get('path', '')))
" 2>/dev/null)

# Only trigger for files under results/
case "$FILE_PATH" in
  */results/*) ;;
  *) exit 0 ;;
esac

# Only for quantitative output formats
case "$FILE_PATH" in
  *.json|*.npy|*.npz|*.csv|*.pkl) ;;
  *) exit 0 ;;
esac

FILENAME=$(basename "$FILE_PATH")
echo "Results file written: $FILENAME"
echo "  → Run /vault-sync to log to 04-Methods/Computational-Log.md"
echo "  → Commit prefix: [RESULT] (or [EXPLORE] if intermediate / development output)"
exit 0
