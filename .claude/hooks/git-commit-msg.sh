#!/bin/bash
# Enforce commit message prefixes for the TDL repository.
# Install this script as .git/hooks/commit-msg or integrate it with your git hook manager.

commit_msg_file="$1"
if [ -z "$commit_msg_file" ]; then
  echo "ERROR: commit-msg hook requires a commit message file path." >&2
  exit 1
fi

first_line=$(sed -n '1p' "$commit_msg_file" | tr -d '\r')
prefix=$(printf '%s' "$first_line" | awk '{print $1}')

case "$prefix" in
  '[RESULT]'|'[DECISION]'|'[NEGATIVE]'|'[PIPELINE]'|'[DATA]'|'[EXPLORE]')
    exit 0
    ;;
  *)
    echo "ERROR: Commit message must start with one of: [RESULT], [DECISION], [NEGATIVE], [PIPELINE], [DATA], [EXPLORE]" >&2
    echo "Example: [PIPELINE] P01: Stage-1 phase-script PROJ_ROOT defaults" >&2
    exit 1
    ;;
esac
