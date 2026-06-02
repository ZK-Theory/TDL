#!/bin/bash
# Pre-commit hook: invokes the math-correctness contract validator.
# Install via .claude/hooks/install-git-hooks.py as .git/hooks/pre-commit.
#
# The hook runs four gates against the contracts/ framework:
#   1. Meta-schema validation of every contract.
#   2. Binding test_file existence + function presence (AST-checked).
#   3. pytest invocation of every bound test function.
#   4. JSON schema validation of staged output files.
#
# Non-zero exit blocks the commit. See contracts/README.md.

# Find the repo root (parent of .git).
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  echo "ERROR: pre-commit hook could not locate repo root via git rev-parse." >&2
  exit 2
fi

# Gate 0: dual-tree skill sync. The Codex (.agents/skills/) and Claude Code
# (.claude/skills/) skill trees must stay in step for research-assurance skills
# to be visible in both runtimes. Fast filecmp; advisory message names the fix.
if ! uv run python "$REPO_ROOT/tools/sync_agent_skills.py" --check; then
  echo "ERROR: skill trees diverged; run tools/sync_agent_skills.py to mirror." >&2
  exit 1
fi

# Gates 1-4: math-correctness contracts. Invoke the validator under the project's
# locked Python environment. `uv run` resolves the project venv automatically.
exec uv run python "$REPO_ROOT/.claude/hooks/contract_binding_check.py" "$@"
