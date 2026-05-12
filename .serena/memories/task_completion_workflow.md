# Task Completion Workflow

## When a Task is Complete

### 1. Code Quality Checks (Mandatory)
Always run these commands before considering a task complete:

```bash
# Lint and auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Run tests (skip slow unless specifically testing slow features)
uv run pytest -m "not slow"
```

### 2. Domain-Specific Testing
Run appropriate tests for the domain you worked in:
```bash
# If working in financial_tda
uv run pytest tests/financial_tda/

# If working in poverty_tda  
uv run pytest tests/poverty_tda/

# If working in trajectory_tda
uv run pytest tests/trajectory/

# If working in shared utilities
uv run pytest tests/shared/
```

### 3. Mathematical Validation (TDA Work)
For any TDA-related changes, run validation tests:
```bash
uv run pytest -m validation
```

### 4. Commit Message Format
Use the TDL-specific commit format with research prefixes:
```bash
git commit -m "[PREFIX] PXX: description"
```

Where PREFIX is one of:
- `[RESULT]` - Quantitative result worth logging
- `[DECISION]` - Parameter or method locked  
- `[NEGATIVE]` - Informative negative result
- `[PIPELINE]` - Pipeline change
- `[DATA]` - Data processing change
- `[EXPLORE]` - Exploratory, no vault action needed

### 5. Vault Synchronization
For computational results or decisions, update the Obsidian vault:
- Update `04-Methods/Computational-Log.md` 
- Add entries to `CONVENTIONS.md` for locked decisions
- Create permanent notes for significant findings

### 6. Pre-Commit Hook Verification
Pre-commit hooks automatically run on every commit:
- Ruff linting with auto-fix
- Code formatting
- Import organization
- **Never use `--no-verify`** to skip hooks

### 7. Coverage Maintenance
If adding new public functions, ensure test coverage:
```bash
uv run pytest --cov=<domain> --cov-report=term-missing
```

## Research Context Requirements

### New Scripts
Every new script must include:
```python
# Research context: TDA-Research/03-Papers/PXX/_project.md
# Purpose: [what this script does in the research context]
```

### Random Seeds
For any stochastic processes:
- Specify seeds explicitly: `np.random.seed(42)`
- Document in script comments
- Log in vault computational entry

### Paper Updates
If working on paper-related code:
- Update `papers/PXX/_project.md` status and open items
- Version new drafts as `vN-YYYY-MM.md`
- Never overwrite previous drafts