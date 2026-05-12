# TDL Essential Commands

## Development Setup
```bash
# Install dependencies (development)
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

## Testing Commands
```bash
# Run all tests
uv run pytest

# Skip slow tests (recommended for development)
uv run pytest -m "not slow"

# Run specific test categories
uv run pytest -m validation              # Mathematical validation
uv run pytest -m integration            # Integration tests
uv run pytest -m "integration and slow" # Slow integration tests

# Domain-specific testing
uv run pytest tests/financial_tda/      # Financial TDA tests
uv run pytest tests/poverty_tda/        # Poverty TDA tests
uv run pytest tests/trajectory/         # Trajectory TDA tests

# With coverage reporting
uv run pytest --cov=financial_tda --cov=poverty_tda --cov=shared --cov=trajectory_tda
```

## Code Quality Commands
```bash
# Lint code (check for issues)
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Combined lint and format
uv run ruff check . --fix && uv run ruff format .
```

## Domain Pipeline Commands
```bash
# Trajectory TDA pipeline (BHPS data)
uv run python trajectory_tda/scripts/bhps_pipeline.py

# Financial TDA experiments
uv run python financial_tda/experiments/six_market_analysis.py

# Poverty TDA validation
uv run python poverty_tda/validation/comparison_runner.py
```

## Windows-Specific Commands
```bash
# List directory contents
Get-ChildItem               # PowerShell equivalent to ls
dir                        # Command Prompt

# Find files
Get-ChildItem -Recurse -Name "*.py"  # Find all Python files
findstr "pattern" *.py              # Search within files

# Git operations (standard)
git status
git add .
git commit -m "message"
git push origin branch-name
```

## Project Management
```bash
# Check git status
git status

# Create feature branch
git checkout -b feature/description

# View project structure
Get-ChildItem -Directory     # List directories only
```

## Code Navigation (jCodemunch/Serena)
- Use Serena symbol tools for code exploration rather than manual file reading
- jcodemunch-MCP tools provide advanced code search and navigation
- See `.claude/CLAUDE.md` for detailed code exploration policies