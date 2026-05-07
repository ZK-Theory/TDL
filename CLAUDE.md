# CLAUDE.md — TDL (Topological Data Lab)

## Project Purpose

Research platform applying **Topological Data Analysis (TDA)**, **topological deep learning**, and **geometric deep learning** to social science datasets. Produces novel insights for academic research papers. Primary domains:

- **financial_tda** — Market regime detection and crisis identification via persistent homology on time series
- **poverty_tda** — UK poverty trap detection via Morse-Smale complex analysis on socioeconomic mobility landscapes
- **trajectory_tda** — Employment/income career trajectory analysis via persistent homology on BHPS/UKHLS panel data

## Obsidian Vault Integration

The research record lives in a separate Obsidian vault at:
`C:\Users\steph\Documents\TDA-Research\`

This repo contains the code. The vault contains theory, methodology, literature, and project management. **They must stay in sync.**

| Vault location | What's there |
|---|---|
| `03-Papers/[ID]/_project.md` | Paper status, open items, draft history |
| `04-Methods/Computational-Log.md` | Logged results and decisions |
| `04-Methods/Pipeline-Overview.md` | Pipeline architecture description |
| `04-Methods/Datasets/` | Dataset processing notes |
| `02-Notes/Permanent/` | Crystallised methodological insights |
| `CONVENTIONS.md` | Always/never rules with rationale — **load at session start** |
| `VAULT-MAP.md` | Full vault navigation index |

**When working on code:** Cross-check `CONVENTIONS.md` for locked methodological decisions before implementing. Any new decision should be added there after locking.

## Key Concepts (Domain Knowledge)

**TDA fundamentals used here:**
- Persistent homology: tracks topological features (connected components H0, loops H1, voids H2) across filtration scales
- Persistence diagrams / barcodes: birth-death pairs; points far from diagonal = significant features
- Wasserstein-2 distance: **mandatory** for persistence diagram comparisons — captures both position and multiplicity of features
- Persistence landscape L² distance: **mandatory complementary metric** alongside Wasserstein-2 — captures shape-level differences single statistics miss
- Bottleneck distance: insufficient as primary metric (captures only single worst discrepancy); do not use alone
- Mapper: graph-based topological summary via cover + clustering
- Morse-Smale complex: decomposes a function's domain into ascending/descending manifolds; basins = stable regions (poverty traps)

**Key libraries:**
- `giotto-tda`: Rips/Alpha filtrations, persistence diagrams, vectorisation (landscape, image, silhouette)
- `gudhi`: Lower-level TDA; simplex trees, cubical complexes, Mapper
- `ripser`: Fast Vietoris-Rips computation
- `torch-geometric`: GNNs on graph-structured data (spatial mobility graphs, persistence graphs)
- `geopandas` / `libpysal`: Spatial analysis on UK LSOAs

**Topology conventions in this codebase:**
- Persistence thresholds are tuned per domain (financial: shorter windows; poverty: geographic scale)
- Permutation nulls are the standard for hypothesis testing on persistence features
- Bootstrap resampling (n=1000) for confidence intervals on topological summaries
- FDR correction (Benjamini-Hochberg) for multiple comparisons
- Always specify the **Markov order k** when describing null models — "Markov null model" alone is ambiguous
- Always check **BHPS wave variable documentation** before assuming variable coding is consistent across waves or between BHPS and Understanding Society

## Architecture

```
papers/                  ← ALL paper projects (see Papers Structure below)
financial_tda/    poverty_tda/    trajectory_tda/
├── data/         ├── data/        ├── data/
├── topology/     ├── topology/    ├── topology/
├── models/       ├── models/      ├── analysis/
├── analysis/     ├── analysis/    ├── scripts/
├── validation/   ├── validation/  ├── viz/
└── viz/          └── viz/
shared/           tests/           .apm/
docs/plans/strategy/     ← Meta-Research-Plan, Obsidian-Overview
```

`shared/` contains cross-domain utilities: persistence diagram I/O, common validation patterns, TTK/ParaView integration.

## Papers Structure

All paper projects live in `papers/`, **not** in domain subdirectories. The domain directories hold code only.

### Directory layout for each paper

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

### `_project.md` YAML schema (mandatory fields)

```yaml
---
paper: P01                    # paper identifier (P01–P10, FIN-01, etc.)
title: "Full paper title"
status: in-progress           # idea | in-progress | submitted | under-review | published | archived
target-journal: "Name"
submitted: null               # ISO date or null
deadline: 2026-06-01          # target submission date or null
priority: high                # high | medium | low
stage: 0                      # 0=consolidate | 1=near | 2=medium | 3=deep-learning
domain: trajectory_tda        # trajectory_tda | poverty_tda | financial_tda
data: [USoc, BHPS]
tags: [paper, tda, ...]
---
```

### Current submission track

| ID | Title | Status | Stage | Target | arXiv |
|---|---|---|---|---|---|
| P01-A | The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries | in-progress | 0 | JRSS-A | stat.AP |
| P01-B | Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data | in-progress | 0 | JRSS-B | stat.ME |
| P04 | Multi-Parameter Persistent Homology Reveals Income-Stratified Career Topology | in-progress | 2 | AoAS | stat.ME, math.AT |

### Later programme papers

| ID | Title | Status | Stage |
|---|---|---|---|
| P05 | Cross-National Welfare State Topology | idea | 2 |
| P06 | Intergenerational Topological Inheritance | idea | 2 |
| P07 | Geometric Trajectory Forecasting | idea | 3 |
| P08 | GNNs on Household Graphs | idea | 3 |
| P09 | CCNNs for Multi-Level Social Data | idea | 3 |
| P10 | Topological Fairness | idea | 3 |
| FIN-01 | Market Regime Detection (financial) | in-progress | — |

Archived source papers preserved as historical record: `papers/P01-VR-PH-Core/`,
`papers/P02-Mapper/`, and `papers/P03-Zigzag/`.

### Draft naming convention

`vN-YYYY-MM.md` — e.g., `v5-2026-03.md` for the fifth draft written in March 2026.

### Rules for agents working on papers

1. **Always** open `papers/PXX/_project.md` first to read current status and open items.
2. **Always** update `_project.md` status and open items after making changes.
3. New drafts go in `papers/PXX/drafts/` with version prefix — never overwrite a previous draft.
4. Computational results go in `results/` (domain-specific) — not in the papers/ directory.
5. Figures are placeholders in text `[Figure N]` until final production pass.
6. After completing a draft, run the `/humanizer` command to check for AI writing tells before marking the paper `submitted`.

See `papers/README.md` for full structure documentation.

## Code Conventions

- **Python 3.13**, 88-char line length, Ruff rules E/F/I/W
- **Type hints** mandatory on all public APIs; use `numpy.typing.NDArray` not bare `np.ndarray`
- **Docstrings**: Google-style on all public functions/classes
- **Imports**: standard → third-party → local; no wildcard imports
- **Pre-commit**: ruff linting/formatting runs on every commit; don't skip hooks
- **Research context comment**: add at the top of every new script:
  ```python
  # Research context: TDA-Research/03-Papers/P01/_project.md
  # Purpose: [what this script does in the research context]
  ```
- **Random seeds**: always specify and record for any stochastic process (Markov simulation, permutation tests, bootstrap); log them in the script and in the vault's Computational-Log entry

**Key libraries:** `giotto-tda`, `gudhi`, `ripser`, `persim`, `scikit-tda`, `umap-learn`, `torch-geometric`, `geopandas`, `libpysal`

```python
# Correct pattern for typed numpy arrays
from numpy.typing import NDArray
import numpy as np

def compute_persistence(point_cloud: NDArray[np.float64], max_dim: int = 2) -> list[tuple]:
    """Compute persistent homology of a point cloud.

    Args:
        point_cloud: Shape (n_points, n_dims) array.
        max_dim: Maximum homology dimension to compute.

    Returns:
        List of (dimension, (birth, death)) persistence pairs.
    """
```

## Commit Message Conventions

Use prefixes to keep the repo-vault bridge meaningful:

| Prefix | Meaning | Vault action needed |
|---|---|---|
| `[RESULT]` | Quantitative result worth logging | Update `04-Methods/Computational-Log.md` |
| `[DECISION]` | Parameter or method locked | Update `04-Methods/Computational-Log.md` + `CONVENTIONS.md` |
| `[NEGATIVE]` | Informative negative result | Create permanent note in `02-Notes/Permanent/` |
| `[PIPELINE]` | Pipeline change | Update `04-Methods/Pipeline-Overview.md` |
| `[DATA]` | Data processing change | Update relevant `04-Methods/Datasets/` note |
| `[EXPLORE]` | Exploratory, no vault action needed | No vault update required |

Examples:
```
[RESULT] P01: Wasserstein-2 permutation test p=0.002 at k=3 Markov null
[DECISION] P01: Lock n_components=50 for UMAP embedding
[NEGATIVE] FIN-01: Bottleneck distance cannot distinguish market regimes
```

## After-Session Sync (Repo → Vault)

When finishing a session that produced results, decisions, or insights:

1. **In Cowork:** Say "repo bridge" or "log results" to trigger the `tda-repo-bridge` skill, which structures session outputs and files them into the vault
2. **In Claude Code / Copilot:** Produce the vault entry text and write it directly to `04-Methods/Computational-Log.md`
3. **Manually:** Add an entry to `04-Methods/Computational-Log.md` in the vault

Format for Computational-Log entries:
```
### YYYY-MM-DD — PXX: [short description]

**Script/notebook:** `C:\Users\steph\TDL\[path]` (commit `[hash]`)
**What was done:** [summary]
**Key findings:** [table or bullets]
**Decision:** [if any parameter/method locked]
**Resolves:** [open items closed]
```

## Common Workflows

### Run the test suite
```bash
uv run pytest                           # all tests
uv run pytest -m "not slow"            # skip slow tests
uv run pytest tests/financial_tda/     # domain-specific
uv run pytest -m validation            # validation tests only
```

### Lint and format
```bash
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run ruff check --fix .              # auto-fix lint issues
```

### Add a new experiment
Follow the pattern in existing `experiments/` or `scripts/` subdirectories:
1. Data loading via domain `data/` modules
2. Topology computation via domain `topology/` modules
3. Analysis in domain `analysis/` modules
4. Output to `results/` or `outputs/` (domain-specific)

### Run a full pipeline
Each domain has scripts that chain data → topology → analysis:
- `trajectory_tda/scripts/bhps_pipeline.py` — full BHPS trajectory pipeline
- `financial_tda/experiments/` — multi-asset regime experiments
- `poverty_tda/validation/` — comparison runners

### Start work on a paper
1. Check `papers/PXX/_project.md` — read status, open items, and current draft path.
2. Read the current draft in `papers/PXX/drafts/vN-YYYY-MM.md`.
3. Run any required computation in the domain directory; save results to `results/`.
4. Write or update the draft as `papers/PXX/drafts/vN+1-YYYY-MM.md`.
5. Update `_project.md` open items and status.
6. Run `/humanizer` before marking a draft ready for submission review.
7. Branch naming: `paper/pXX-name` for paper writing; `run/pXX-name` for computation.

## Testing Conventions

- Test markers: `slow` (long-running), `integration` (external deps/data), `validation` (mathematical correctness)
- Tests live in `tests/<domain>/`
- Validation tests check against known published results (e.g., Gidea-Katz 2017 for financial TDA)
- Permutation null distributions require `--run-slow` or `-m slow` to run fully

## APM Workflow

This project uses APM (Agentic Project Management) v0.5.3. Phase plans live in `.apm/Implementation_Plan.md`. When implementing new phases:
- Check the plan before starting work
- Use the prompts in `.github/prompts/` to initiate manager/implementation agents
- Log progress in `.apm/Memory/`

## Deep Learning Integration Points

- GNNs: `torch-geometric`; spatial graphs in `poverty_tda/models/spatial_gnn.py`, persistence graphs in `financial_tda/models/rips_gnn.py`
- VAEs: `poverty_tda/models/opportunity_vae.py`
- Persistence-based DL: Perslay/PersFormer patterns for learning on persistence diagrams (partially implemented)
- TTK/ParaView: acceleration for large-scale topology; see `shared/ttk_utils.py`

## What NOT to Do

- Do not mock external data sources in integration tests — use real cached data or skip with `@pytest.mark.integration`
- Do not hardcode file paths; use `pathlib.Path` relative to the package root or a config
- Do not run `torch-geometric` imports without checking they are installed (optional dependency)
- Do not commit large data files; data lives outside the repo or in `.gitignore`d `data/` directories
- Do not skip pre-commit hooks (`--no-verify`)
- Do not amend published commits; create new commits instead
- **Do not run persistent homology on raw trajectories** without the embedding step — the Vietoris-Rips complex requires a metric space
- **Do not assume BHPS and Understanding Society use the same variable coding** even for variables that appear identical — always check wave documentation
- **Do not use bottleneck distance as the sole comparison metric** for persistence diagrams — always use Wasserstein-2 as primary

## Geometric / Topological Deep Learning (Emerging)

As the project expands into topological and geometric deep learning, the intended structure is:
- Domain-agnostic DL layers → `shared/deep_learning/` (e.g., persistence-based layers, simplicial convolutions)
- Domain-specific DL models → `<domain>/models/` (as now)
- Experiment scaffolds → `<domain>/experiments/` or `<domain>/scripts/`

Key frameworks to integrate: `torch-geometric`, `TopoModelX` (simplicial/cellular/hypergraph NNs), `Perslay`.


## Code Exploration Policy

Always use jCodemunch-MCP tools for code navigation. Never fall back to Read, Grep, Glob, or Bash for code exploration.
**Exception:** Use `Read` when you need to edit a file — the agent harness requires a `Read` before `Edit`/`Write` will succeed. Use jCodemunch tools to *find and understand* code, then `Read` only the specific file you're about to modify.

**Start any session:**
1. `resolve_repo { "path": "." }` — confirm the project is indexed. If not: `index_folder { "path": "." }`
2. `suggest_queries` — when the repo is unfamiliar

**Finding code:**
- symbol by name → `search_symbols` (add `kind=`, `language=`, `file_pattern=`, `decorator=` to narrow)
- decorator-aware queries → `search_symbols(decorator="X")` to find symbols with a specific decorator (e.g. `@property`, `@route`); combine with set-difference to find symbols *lacking* a decorator (e.g. "which endpoints lack CSRF protection?")
- string, comment, config value → `search_text` (supports regex, `context_lines`)
- database columns (dbt/SQLMesh) → `search_columns`

**Reading code:**
- before opening any file → `get_file_outline` first
- one or more symbols → `get_symbol_source` (single ID → flat object; array → batch)
- symbol + its imports → `get_context_bundle`
- specific line range only → `get_file_content` (last resort)

**Repo structure:**
- `get_repo_outline` → dirs, languages, symbol counts
- `get_file_tree` → file layout, filter with `path_prefix`

**Relationships & impact:**
- what imports this file → `find_importers`
- where is this name used → `find_references`
- is this identifier used anywhere → `check_references`
- file dependency graph → `get_dependency_graph`
- what breaks if I change X → `get_blast_radius`
- what symbols actually changed since last commit → `get_changed_symbols`
- find unreachable/dead code → `find_dead_code`
- class hierarchy → `get_class_hierarchy`

## Session-Aware Routing

**Opening move for any task:**
1. `plan_turn { "repo": "...", "query": "your task description", "model": "<your-model-id>" }` — get confidence + recommended files; the `model` parameter narrows the exposed tool list to match your capabilities at zero extra requests.
2. Obey the confidence level:
   - `high` → go directly to recommended symbols, max 2 supplementary reads
   - `medium` → explore recommended files, max 5 supplementary reads
   - `low` → the feature likely doesn't exist. Report the gap to the user. Do NOT search further hoping to find it.

**Interpreting search results:**
- If `search_symbols` returns `negative_evidence` with `verdict: "no_implementation_found"`:
  - Do NOT re-search with different terms hoping to find it
  - Do NOT assume a related file (e.g. auth middleware) implements the missing feature (e.g. CSRF)
  - DO report: "No existing implementation found for X. This would need to be created."
  - DO check `related_existing` files — they show what's nearby, not what exists
- If `verdict: "low_confidence_matches"`: examine the matches critically before assuming they implement the feature

**After editing files:**
- If PostToolUse hooks are installed (Claude Code only), edited files are auto-reindexed
- Otherwise, call `register_edit` with edited file paths to invalidate caches and keep the index fresh
- For bulk edits (5+ files), always use `register_edit` with all paths to batch-invalidate

**Token efficiency:**
- If `_meta` contains `budget_warning`: stop exploring and work with what you have
- If `auto_compacted: true` appears: results were automatically compressed due to turn budget
- Use `get_session_context` to check what you've already read — avoid re-reading the same files

## Model-Driven Tool Tiering

Your jcodemunch-mcp server narrows the exposed tool list based on the model you are running as. To avoid wasting requests on primitives when a composite would do, always include `model="<your-model-id>"` in your opening `plan_turn` call.

Replace `<your-model-id>` with your active model:
- Claude Opus variants → `claude-opus-4-7` (or any `claude-opus-*`)
- Claude Sonnet variants → `claude-sonnet-4-6`
- Claude Haiku variants → `claude-haiku-4-5`
- GPT-4o / GPT-5 / o1 / Llama → use the model id as printed by your runner

The `model=` parameter rides on the existing `plan_turn` call — it does **not** add a separate tool invocation. If `plan_turn` is not appropriate for a non-code task, call `announce_model(model="...")` once instead.

---

APM_RULES {

## Empiricism-first ordering

- Data analysis precedes prose for the same section. Do not draft prose against expected, predicted, or partial results — wait for the result to land in `results/...` and a vault `[RESULT]` entry to be filed before any prose work for the dependent section begins.
- Outcome-contingent prose direction is locked by a vault `[DECISION]` entry recording the outcome (e.g., A/B/C, a/b/c) against the pre-registered decision rule. Do not draft prose for an outcome-contingent section until the lock is on file.
- When a Task relies on an inferred property of an external resource — a harmonised dataset's coding rule, a library's behaviour, a checkpoint's expected schema — verify the property before relying on it. Do not assume.

## No speculative paths

This project's history includes large costs from work pursued on speculative or assumptive foundations. Do not pursue analyses, prose, or implementation directions whose foundation is "this is probably true" or "this should hold" without verification. When uncertain, surface the uncertainty as a User-decision point or as a verification step in the same Task; do not proceed past it.

## Vault discipline

- Every Task ends with the appropriate vault entry written via the `vault-engine` MCP server using `vault_observe`. Computational Tasks write `[RESULT]`; parameter or method locks write `[DECISION]`; informative null findings write `[NEGATIVE]`; pipeline changes write `[PIPELINE]`; data-processing changes write `[DATA]`. See "Commit Message Conventions" and "After-Session Sync (Repo → Vault)" above for entry format and prefix mapping.
- Pre-registration entries are written *before* outcome-contingent runs, not after. Each pre-registration records: parameter values, decision rule, prose-direction rule per outcome, and a timestamp. The post-run `[RESULT]` entry references the pre-registration.
- Vault access is MCP-only via the `vault-engine` server (see `.claude/CLAUDE.md` § "Vault-Engine MCP Server" for the tool list — `vault_get`, `vault_query`, `vault_observe`, `vault_skeleton`, `vault_status`, `vault_graph`, `cross_vault`). Do not attempt direct filesystem reads of the vault path.

## Output file management

- Numerical results are written under `results/...` with date-suffixed filenames (`<basename>_<YYYY-MM-DD>.json`). Never overwrite an existing results file: if a re-run is needed, the new file receives a new date-suffix and the previous file is preserved as historical record.
- **All deliverable output files must be committed on the Task branch.** Before committing, explicitly `git add` every result JSON listed in the Task Output section. Do not assume files written to absolute paths in the main working tree will be preserved across Manager merge operations — they must be tracked in the branch commit.
- **`*.csv` and `*.pkl` files are globally gitignored** (UKDA T&C compliance and size). If a Task produces a CSV or pickle deliverable, note this in the Task Log and confirm the producing script is committed so the file can be regenerated on demand. Do not attempt to commit these file types.
- **GMM and model checkpoints (pkl/joblib):** When a Task refits a model, the correct deliverable set is: (1) the refit script committed on the Task branch; (2) a timestamped results JSON at `results/<domain>/<model>/refit_<YYYY-MM-DD>.json` containing key metrics (k, silhouette score, regime counts, seed, script path) — this IS committed; (3) the pkl checkpoint written locally to the same directory for immediate use — NOT committed. Log the pkl path and reproduce-from-scratch command in the Task Log so the checkpoint can be regenerated on any machine.
- **Gitignored ≠ inaccessible.** Files in `data/`, `data/raw/`, `data/processed/`, `data/UKDA-6614-tab/`, and other gitignored directories are physically present on disk. Agents can read them with the `Read` tool using absolute paths (e.g., `c:\Users\steph\TDL\data\raw\...`) or list them with `Get-ChildItem`. Git only prevents committing these files — it does not delete or hide them. Never assume data is missing because it is gitignored; always verify by checking the filesystem first.
- **UKDA user guides** are available as plain-text conversions (via `pdftotext`) at two locations (both gitignored, on disk — use `Read` tool at absolute path; PDF Viewer MCP cannot access local files):
  - `c:\Users\steph\TDL\data\guides\6614\` — four curated guides: `6614_main_survey_bhps_harmonised_user_guide.md`, `6614_main_survey_user_guide_family_matrix_xhhrel.md`, `6614_Understanding_Society_and_its_income_data.md`, `6614_main_survey_user_guide_weighting_variables.md`
  - `c:\Users\steph\TDL\data\UKDA-6614-tab\mrdoc\pdf\` — all 86 UKDA documentation PDFs converted to `.md` (wave questionnaires, technical reports, user guides, fieldwork docs). The main methodological guides are `6614_bhps_harmonised_user_guide.md`, `6614_main_survey_user_guide.md`, `6614_bhps_user_manual_volume_a.md`, and wave-specific technical reports.
- Paper drafts are versioned `vN-YYYY-MM.md` in `papers/PXX/drafts/`. Never overwrite a previous draft; create the next version (see "Papers Structure" → "Draft naming convention" above).
- When a Task completes work referenced in a paper's `papers/PXX/_project.md` open-items list, update `_project.md` (mark items closed; append to draft history if a new draft was produced).
- Locked notational decisions go into `papers/shared/notation.md`; never let two papers use divergent notation for the same object.

## Prose work — notation, voice, completion

- After every prose change, run the `/notation-check` skill against `papers/shared/notation.md`. Do not batch notation checks across multiple section edits; check at every change to prevent compounding inconsistency.
- Before any draft is considered ready for review at v2 (or v3) completion, run the `/humanizer` skill on it. `/humanizer` is a final-pass gate, not a per-section pass.
- Writing voice across both papers and supplements is academic, professional, and mathematical. Avoid colloquialisms, hedge-stacking, contribution inflation, and the AI-tells the `/humanizer` skill targets.
- For prose Tasks, User per-section review is a validation step — surface the section to the User before marking the Task complete.

## Cross-Worker output consumption

- When a Task depends on another Worker's output (a results JSON, a vault entry, a code-side fix, a verified property), read that output directly rather than re-running the producing computation. The Task description names the producing Task and the deliverable at the boundary.
- If a producing Task's output is missing, malformed, or contradicts what the consuming Task needs, surface the issue rather than fabricating or guessing a substitute. Do not proceed past the inconsistency.

## Surfacing User-decision points

When a Task encounters a question requiring User input — a journal-formatting decision, a methodological judgement call, a data-availability constraint, a contradiction between an inferred property and observed behaviour — surface it as an explicit User-facing prompt within the Task. Tasks are designed to embed such prompts; do not guess and do not block.

## Version control

- Repository at `c:\Users\steph\TDL`; base branch `main`. Each dispatched Task gets its own feature branch off `main`. Branch types: `pipe/<desc>` for topology pipeline code-side fixes (Stage 0 TDA/Reproducibility infrastructure), `run/<desc>` for computational Tasks (Stage 1, Stage 4 numerical work), `paper/<desc>` for prose Tasks (Stage 2, Stage 4 prose), `repo/<desc>` for repo-extraction Tasks (Stage 3, Stage 4.10). Branch names describe the work, not Task IDs.
- Commit messages use the `[PREFIX] PXX: <description>` pattern with `PREFIX ∈ {RESULT, DECISION, NEGATIVE, PIPELINE, DATA, EXPLORE}` per the vault-action mapping in "Commit Message Conventions" above. Workers append the Co-Authored-By trailer per Claude Code defaults. Never use `--no-verify` — pre-commit hooks (Ruff lint/format) must run.
- Workers commit on their own feature branches and do not merge. The Manager performs all merges to `main` after Task Review per the APM merge protocol.
- Parallel dispatch uses worktrees under `.apm/worktrees/` (concurrency cap 3–4); the main working directory remains on `main` for merge operations. With User-confirmed multi-terminal compute, parallel TDA + Panel-Statistics dispatch in Stage 1 is the expected pattern.
- **Worktree `.env` setup (mandatory):** After `git worktree add`, immediately copy `.env` from the main working tree: `Copy-Item "c:\Users\steph\TDL\.env" "<worktree-path>\.env"`. The `.env` file is gitignored and never copied automatically; without it, `uv run --env-file .env` calls fail silently or hunt for the file. Workers should not need to locate `.env` — it must already be present when the worktree is created.
- `.apm/` git-tracking policy is Option B: planning artefacts (`plan.md`, `spec.md`, `tracker.md`, `memory/index.md`, `metadata.json`) are tracked; runtime artefacts (`bus/`, Worker Task Logs in `memory/stage-NN/`, `worktrees/`) are gitignored to keep `main` free of coordination churn.

## Code exploration

See "Code Exploration Policy" and "Session-Aware Routing" above, and `.claude/CLAUDE.md` § "vexp" — `jcodemunch-mcp` and `vexp` tools (especially `run_pipeline` and `get_skeleton`) are mandatory for code navigation, with `Read` reserved for files about to be edited. Do not fall back to `Grep`, `Glob`, or `Bash` for code search.

## Methodological mandates

See "Code Conventions" and "What NOT to Do" above, and `.claude/CLAUDE.md` § "Methodological Mandates (enforced in all Python code)". These define locked rules — Python 3.13, W₂ for persistence-diagram comparison with persistence landscape L² as mandatory complement, Markov-order *k* always specified explicitly, never raw-trajectory persistent homology (always embed first), BHPS/USoc variable coding never assumed shared without verification, type hints with `numpy.typing.NDArray`, Google-style docstrings, research-context comment header on every new script, random seeds specified and recorded for every stochastic process. They apply to every Task touching the relevant material; reference, do not re-derive.

} //APM_RULES
