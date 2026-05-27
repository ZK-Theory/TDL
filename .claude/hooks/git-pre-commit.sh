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

# Invoke the validator under the project's locked Python environment.
# `uv run` resolves the project venv automatically; no need to source .venv.
exec uv run python "$REPO_ROOT/.claude/hooks/contract_binding_check.py" "$@"
