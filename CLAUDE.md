# CLAUDE.md — TDL (Topological Data Lab)

## Project Purpose

Research platform applying **Topological Data Analysis (TDA)**, **topological deep learning**, and **geometric deep learning** to social science datasets. Produces novel insights for academic research papers. Primary domains:

- **financial_tda** — Market regime detection and crisis identification via persistent homology on time series

> Active Claude Code policy is anchored in `.claude/CLAUDE.md`; this file is the broader project handbook.

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

Use the built-in `Read`, `Grep`, and `Glob` tools for code navigation. There is no symbol-level MCP server in use.

**Tool routing:**
- read a file with a known path → `Read`
- search file contents (symbol names, strings, regex) across the repo → `Grep` (with `type: "py"` filter and `output_mode: "content"` for code context)
- list files by name pattern (e.g. `**/*.py`) or do a filesystem inventory → `Glob`
- edit an existing file → `Edit` (must be preceded by `Read` of that file)
- create or fully overwrite a file → `Write`

`Read` is permitted only after the target file has been identified — typically just before `Edit`/`Write`. The agent harness requires a prior `Read` for `Edit`/`Write` to succeed.

Do not use `Bash` (`grep` / `rg` / `find`) for code search — `Grep` is faster, sandboxed, and integrates with the agent harness.

For large multi-step searches (more than a few rounds of grep/read), spawn an `Explore` subagent rather than burning the main context.

---

APM_RULES {

## Empiricism-first ordering

- Data analysis precedes prose for the same section. Do not draft prose against expected, predicted, or partial results — wait for the result to land in `results/...` and a vault `[RESULT]` entry to be filed before any prose work for the dependent section begins.
- Outcome-contingent prose direction is locked by a vault `[DECISION]` entry recording the outcome (e.g., A/B/C, a/b/c) against the pre-registered decision rule. Do not draft prose for an outcome-contingent section until the lock is on file.
- When a Task relies on an inferred property of an external resource — a harmonised dataset's coding rule, a library's behaviour, a checkpoint's expected schema — verify the property before relying on it. Do not assume.

## No speculative paths

This project's history includes large costs from work pursued on speculative or assumptive foundations. Do not pursue analyses, prose, or implementation directions whose foundation is "this is probably true" or "this should hold" without verification. When uncertain, surface the uncertainty as a User-decision point or as a verification step in the same Task; do not proceed past it.

## Research assurance before dispatch and acceptance

- Before dispatching or accepting any Task that touches mathematical, statistical, topological, representation, output-provenance, or paper-claim logic, run research assurance triage. Classify the touched assurance lanes, identify governing pre-registrations / decision rules / contracts / vault locks, and decide which claims are machine-checkable versus human-review-only.
- Machine-checkable research claims need an enforcement artifact where practical: contract, binding test, output schema, validation command, smoke/canary, or provenance check. If a claim is not mechanized, the Manager records why in the Task Prompt or review notes.
- Passing software tests is not sufficient for research Tasks. A Task can pass lint, unit tests, and smoke runs while failing mathematical validity, null-model validity, output provenance, or paper-claim traceability.

## Vault discipline

- Every Task ends with the appropriate vault entry appended to the relevant vault file via `Write` / `Edit` against its absolute path under `C:\Users\steph\Documents\TDA-Research\`. **Insert new entries at the top of the page, just below the `---` header, in reverse-chronological order** (per the 2026-05-25 vault-discipline `[DECISION]` at the top of `04-Methods/Computational-Log.md`). Computational Tasks write `[RESULT]` → `04-Methods/Computational-Log.md`; parameter or method locks write `[DECISION]` → `04-Methods/Computational-Log.md` and (where they lock a rule) `CONVENTIONS.md`; informative null findings write `[NEGATIVE]` → `04-Methods/Computational-Log.md` plus a permanent note in `02-Notes/Permanent/`; pipeline changes write `[PIPELINE]` → `04-Methods/Pipeline-Overview.md`; data-processing changes write `[DATA]` → relevant `04-Methods/Datasets/` note. `vault_observe` is NOT the write path — it attaches a short observation to a page for cross-session retrieval and does not append to the page. Use it optionally *in addition* when an entry should be discoverable from queries against a related page that does not yet wikilink to it. See "Commit Message Conventions" and "After-Session Sync (Repo → Vault)" above for entry format and prefix mapping.
- Pre-registration entries are written *before* outcome-contingent runs, not after. Each pre-registration records: parameter values, decision rule, prose-direction rule per outcome, and a timestamp. The post-run `[RESULT]` entry references the pre-registration.
- Vault **reads** go through the `vault-engine` MCP server (`vault_get`, `vault_query`, `vault_skeleton`, `vault_status`, `vault_graph`, `cross_vault`) — these provide wikilink-graph context that raw filesystem reads do not. Vault **writes** use `Write` / `Edit` against absolute paths under `C:\Users\steph\Documents\TDA-Research\`; there is no MCP `vault_write` tool.

## Output file management

### Two-path rule — mandatory for all scripts running in worktrees

Every script defines two root paths and uses them strictly:

### Downstream data guarantee

Every task that produces a gitignored intermediate consumed by a downstream task must:

1. List the file with its full `PROJ_ROOT`-based absolute path in its Output section.
2. Write it to that `PROJ_ROOT` path (not the worktree path).
3. Note the regeneration command in the Task Log so the file can be reproduced from scratch.

Every task that consumes a gitignored intermediate must:

1. Verify the file exists at its expected `PROJ_ROOT` path before doing any computation.
2. If missing: run the committed producing script to regenerate it. Escalate only if the script is missing or regeneration fails.

The Manager verifies all cross-task gitignored file dependencies are present in `PROJ_ROOT` before dispatching any consuming task, and before removing any worktree.

### General output rules

- Numerical results use date-suffixed filenames (`<basename>_<YYYY-MM-DD>.json`). Never overwrite an existing results file — new date suffix, old file preserved as historical record.
- **All deliverable JSON files must be committed on the Task branch.** Before committing, explicitly `git add` every result JSON listed in the Task Output section.
- **`*.csv` and `*.pkl` files are globally gitignored** (UKDA T&C compliance and size). Write them to `PROJ_ROOT` per the two-path rule. Commit the producing script so they are regenerable. Do not attempt to commit these file types.
- **GMM and model checkpoints (pkl/joblib):** deliverable set is: (1) producing script committed on Task branch; (2) timestamped metrics JSON committed at `WORKTREE/results/...`; (3) pkl checkpoint written to `PROJ_ROOT/results/...` — not committed, regenerable. Log both paths in the Task Log.
- **Gitignored ≠ inaccessible.** Any file written to `PROJ_ROOT` is on disk regardless of gitignore status. Never assume a file is missing because it is gitignored — verify by checking the filesystem at the absolute path.
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
- If a producing Task's committed JSON output is missing or malformed, surface the issue rather than fabricating a substitute. Do not proceed past the inconsistency.
- If a producing Task's gitignored intermediate (pkl, rds, csv) is missing: first check whether the committed producing script exists, then regenerate the file by re-running that script. Escalate only if the script is absent or regeneration fails. Do not treat a missing gitignored file as a hard blocker without attempting regeneration.

## Surfacing User-decision points

When a Task encounters a question requiring User input — a journal-formatting decision, a methodological judgement call, a data-availability constraint, a contradiction between an inferred property and observed behaviour — surface it as an explicit User-facing prompt within the Task. Tasks are designed to embed such prompts; do not guess and do not block.

## Version control

- Repository at `c:\Users\steph\TDL`; base branch `main`. Each dispatched Task gets its own feature branch off `main`. Branch types: `pipe/<desc>` for topology pipeline code-side fixes (Stage 0 TDA/Reproducibility infrastructure), `run/<desc>` for computational Tasks (Stage 1, Stage 4 numerical work), `paper/<desc>` for prose Tasks (Stage 2, Stage 4 prose), `repo/<desc>` for repo-extraction Tasks (Stage 3, Stage 4.10). Branch names describe the work, not Task IDs.
- Commit messages use the `[PREFIX] PXX: <description>` pattern with `PREFIX ∈ {RESULT, DECISION, NEGATIVE, PIPELINE, DATA, EXPLORE}` per the vault-action mapping in "Commit Message Conventions" above. Workers append the Co-Authored-By trailer per Claude Code defaults. Never use `--no-verify` — pre-commit hooks (Ruff lint/format) must run.
- Workers commit on their own feature branches and do not merge. The Manager performs all merges to `main` after Task Review per the APM merge protocol.
- Parallel dispatch uses worktrees under `.apm/worktrees/` (concurrency cap 3–4); the main working directory remains on `main` for merge operations. With User-confirmed multi-terminal compute, parallel TDA + Panel-Statistics dispatch in Stage 1 is the expected pattern.
- **Worktree `.env` setup (mandatory):** After `git worktree add`, immediately copy `.env` from the main working tree: `Copy-Item "c:\Users\steph\TDL\.env" "<worktree-path>\.env"`. The `.env` file is gitignored and never copied automatically; without it, `uv run --env-file .env` calls fail silently or hunt for the file. Workers should not need to locate `.env` — it must already be present when the worktree is created.
- **Worktree pre-removal checklist (mandatory):** Before `git worktree remove`, the Manager must verify: (1) all committed result files on the branch have been merged to `main`; (2) all gitignored intermediate files needed by downstream tasks are present at their `PROJ_ROOT` paths. If any downstream-needed gitignored file is missing from `PROJ_ROOT`, regenerate it before removing the worktree.
- `.apm/` git-tracking policy is Option B: planning artefacts (`plan.md`, `spec.md`, `tracker.md`, `memory/index.md`, `metadata.json`) are tracked; runtime artefacts (`bus/`, Worker Task Logs in `memory/stage-NN/`, `worktrees/`) are gitignored to keep `main` free of coordination churn.

## Code exploration

See "Code Exploration Policy" above. Use the built-in `Read`/`Grep`/`Glob` tools; `Read` is reserved for files about to be edited; `Grep` is the canonical content-search tool; `Glob` is for filesystem inventory. Do not rely on `Bash` for code search.

## Methodological mandates

See "Code Conventions" and "What NOT to Do" above, and `.claude/CLAUDE.md` § "Methodological Mandates (enforced in all Python code)". These define locked rules — Python 3.13, W₂ for persistence-diagram comparison with persistence landscape L² as mandatory complement, Markov-order *k* always specified explicitly, never raw-trajectory persistent homology (always embed first), BHPS/USoc variable coding never assumed shared without verification, type hints with `numpy.typing.NDArray`, Google-style docstrings, research-context comment header on every new script, random seeds specified and recorded for every stochastic process. They apply to every Task touching the relevant material; reference, do not re-derive.

} //APM_RULES
