---
description: Repository workflow and research process guidance.
alwaysApply: true
---

## Repository Workflow

Comprehensive workflow guidance for TDL research platform operations.

### Testing Workflow

**Run test suite:**
```bash
uv run pytest                           # all tests
uv run pytest -m "not slow"            # skip slow tests
uv run pytest tests/financial_tda/     # domain-specific
uv run pytest -m validation            # validation tests only
```

**Test markers:**
- `slow` (long-running), `integration` (external deps/data), `validation` (mathematical correctness)
- Tests live in `tests/<domain>/`
- Validation tests check against known published results

### Code Quality Workflow

**Lint and format:**
```bash
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run ruff check --fix .              # auto-fix lint issues
```

### Experiment Workflow

**Add new experiment:**
Follow pattern in existing `experiments/` or `scripts/` subdirectories:
1. Data loading via domain `data/` modules
2. Topology computation via domain `topology/` modules
3. Analysis in domain `analysis/` modules
4. Output to `results/` or `outputs/` (domain-specific)

**Run full pipeline:**
Each domain has scripts that chain data → topology → analysis:
- `trajectory_tda/scripts/bhps_pipeline.py` — full BHPS trajectory pipeline
- `financial_tda/experiments/` — multi-asset regime experiments
- `poverty_tda/validation/` — comparison runners

### Paper Workflow

**Start work on a paper:**
1. Check `papers/PXX/_project.md` — read status, open items, and current draft path
2. Read the current draft in `papers/PXX/drafts/vN-YYYY-MM.md`
3. Run any required computation in the domain directory; save results to `results/`
4. Write or update the draft as `papers/PXX/drafts/vN+1-YYYY-MM.md`
5. Update `_project.md` open items and status
6. Run `/humanizer` before marking a draft ready for submission review
7. Branch naming: `paper/pXX-name` for paper writing; `run/pXX-name` for computation

### Paper Directory Structure

**Directory layout for each paper:**
```
papers/PXX-Name/
├── _project.md          ← YAML metadata (status, journal, deadline) — source of truth
├── _outline.md          ← Current argument structure
├── _reviewer-log.md     ← Reviewer comments and response tracking
├── drafts/
│   ├── vN-YYYY-MM.md   ← Versioned full drafts (v1-2025.md, v5-2026-03.md, …)
│   └── sections/        ← Section-level working files (optional)
├── figures/             ← Exported PD diagrams, Mapper graphs, barcodes
└── notes/               ← Scratch: outlines, action plans, handoff notes
```

### Rules for Paper Work

1. **Always** open `papers/PXX/_project.md` first to read current status and open items
2. **Always** update `_project.md` status and open items after making changes
3. New drafts go in `papers/PXX/drafts/` with version prefix — never overwrite a previous draft
4. Computational results go in `results/` (domain-specific) — not in the papers/ directory
5. Figures are placeholders in text `[Figure N]` until final production pass
6. After completing a draft, run the `/humanizer` command to check for AI writing tells

### Commit Message Conventions

Use prefixes to keep repo-vault bridge meaningful:

| Prefix | Meaning | Vault action needed |
|---|---|---|
| `[RESULT]` | Quantitative result worth logging | Update `04-Methods/Computational-Log.md` |
| `[DECISION]` | Parameter or method locked | Update `04-Methods/Computational-Log.md` + `CONVENTIONS.md` |
| `[NEGATIVE]` | Informative negative result | Create permanent note in `02-Notes/Permanent/` |
| `[PIPELINE]` | Pipeline change | Update `04-Methods/Pipeline-Overview.md` |
| `[DATA]` | Data processing change | Update relevant `04-Methods/Datasets/` note |
| `[EXPLORE]` | Exploratory, no vault action needed | No vault update required |

### After-Session Sync (Repo → Vault)

When finishing a session that produced results, decisions, or insights:

1. **In Cowork:** Say "repo bridge" or "log results" to trigger the `tda-repo-bridge` skill
2. **In Claude Code / Copilot:** Produce the vault entry text and write it directly to `04-Methods/Computational-Log.md`
3. **Manually:** Add an entry to `04-Methods/Computational-Log.md` in the vault

**Format for Computational-Log entries:**
```
### YYYY-MM-DD — PXX: [short description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash]`)
**What was done:** [summary]
**Key findings:** [table or bullets]
**Decision:** [if any parameter/method locked]
**Resolves:** [open items closed]
```

### Workflow References

- `.claude/instructions/research-context.instructions.md` for new script headers and research metadata
- `.claude/instructions/hook-enforcement.instructions.md` for policy enforcement checks
- `.claude/instructions/git.instructions.md` for git workflow and branching
