# CLAUDE.md — TDL (Topological Data Lab)

## Project Purpose

Research platform applying **Topological Data Analysis (TDA)**, **topological deep learning**, and **geometric deep learning** to social science datasets. Produces novel insights for academic research papers. Primary domains:

- **financial_tda** — Market regime detection and crisis identification via persistent homology on time series
- **poverty_tda** — UK poverty trap detection via Morse-Smale complex analysis on socioeconomic mobility landscapes
- **trajectory_tda** — Employment/income career trajectory analysis via persistent homology on BHPS/UKHLS panel data

> Active Claude Code policy is anchored in `.claude/CLAUDE.md`; this file is the broader project handbook. Conditional guidance lives in path-scoped `.claude/rules/` files that load automatically when matching files are touched.

## Obsidian Vault Integration

The research record lives in a separate Obsidian vault at `C:\Users\steph\Documents\TDA-Research\`. This repo contains the code; the vault contains theory, methodology, literature, and project management. **They must stay in sync.**

| Vault location | What's there |
|---|---|
| `03-Papers/[ID]/_project.md` | Paper status, open items, draft history |
| `04-Methods/Computational-Log.md` | Logged results and decisions |
| `04-Methods/Pipeline-Overview.md` | Pipeline architecture description |
| `04-Methods/Datasets/` | Dataset processing notes |
| `02-Notes/Permanent/` | Crystallised methodological insights |
| `VAULT-MAP.md` | Full vault navigation index |

**CONVENTIONS.md is repo-canonical (single source for all agents).** The always/never rules live in the committed **repo-root `CONVENTIONS.md`**; the vault's copy is a **hardlink** to the repo file (same inode — a hardlink, not a symlink, because symlinks need Developer Mode/admin on Windows; if git ever rewrites the file and breaks the link, re-create it). **Load `CONVENTIONS.md` at session start; read/edit it at the repo root, never via the vault path.** Newly-locked decisions are added to the repo-root file and surface in the vault through the hardlink.

**Access modes.** A gitignored Windows junction at `c:\Users\steph\TDL\vault\` mirrors the vault root — use `vault/<path>` with `Read`/`Edit`/`Write` for content work (Computational-Log appends, daily notes); edits land in the real vault file. Use the vault-engine MCP (`vault_query`, `vault_skeleton`, `vault_graph`, `vault_status`, `cross_vault`) for wikilink-graph navigation — graph context the filesystem cannot provide. Entry formats and templates: `.claude/rules/vault-templates.md`.

## Architecture

```
papers/                  ← ALL paper projects (rules: .claude/rules/papers.md)
financial_tda/    poverty_tda/    trajectory_tda/      ← code only
├── data/  topology/  models/  analysis/  validation/  scripts/  viz/
shared/           tests/           .apm/
docs/plans/strategy/     ← Meta-Research-Plan, Obsidian-Overview
```

`shared/` contains cross-domain utilities: persistence diagram I/O, common validation patterns, TTK/ParaView integration. Deep-learning integration points: `.claude/rules/deep-learning.md`.

**Active papers:** P01-A (JRSS-A), P01-B (JRSS-B), P04 (AoAS) in progress; P05–P10 and FIN-01 form the later programme. Always open `papers/PXX/_project.md` first. Full paper structure, YAML schema, and prose rules load from `.claude/rules/papers.md` when working under `papers/`.

## Methodological Mandates (locked)

- **Wasserstein-2 is the primary metric** for persistence-diagram comparison; **persistence landscape L² is the mandatory complement**. Bottleneck distance is never the sole metric.
- **Never run persistent homology on raw trajectories** — embed first; the Vietoris-Rips complex requires a metric space.
- **Always specify the Markov order k** when describing a Markov null model — "Markov null" alone is ambiguous.
- **Never assume BHPS and Understanding Society share variable coding**, even for variables that appear identical — check wave documentation (`/bhps-wave-crosswalk`).
- Permutation nulls are the standard for hypothesis testing on persistence features; bootstrap resampling (n=1000) for CIs; FDR correction (Benjamini-Hochberg) for multiple comparisons. Persistence thresholds are tuned per domain.
- Random seeds always specified and recorded for any stochastic process — in the script and in the vault's Computational-Log entry.
- Long stochastic compute (bootstraps, nulls, MICE, batteries) runs ≥4 parallel workers with checkpointing and a wall-time flag.

**Key libraries:** `giotto-tda`, `gudhi`, `ripser`, `persim`, `scikit-tda`, `umap-learn`, `torch-geometric`, `geopandas`, `libpysal`.

## Code Conventions

Python 3.13 · 120-char lines · Ruff E/F/I/W · type hints mandatory on public APIs (`numpy.typing.NDArray`, not bare `np.ndarray`) · Google-style docstrings · imports standard → third-party → local, no wildcards · pre-commit hooks run on every commit, never skipped. Per-file detail, the research-context header requirement, and the typed-array pattern: `.claude/rules/python.md`.

## Commit Message Conventions

`[PREFIX] PXX: <description>` — prefixes keep the repo-vault bridge meaningful:

| Prefix | Meaning | Vault action needed |
|---|---|---|
| `[RESULT]` | Quantitative result worth logging | `04-Methods/Computational-Log.md` |
| `[DECISION]` | Parameter or method locked | Computational-Log + `CONVENTIONS.md` |
| `[NEGATIVE]` | Informative negative result | Computational-Log + permanent note in `02-Notes/Permanent/` |
| `[PIPELINE]` | Pipeline change | `04-Methods/Pipeline-Overview.md` |
| `[DATA]` | Data processing change | relevant `04-Methods/Datasets/` note |
| `[EXPLORE]` | Exploratory | none |

Example: `[RESULT] P01: Wasserstein-2 permutation test p=0.002 at k=3 Markov null`

## After-Session Sync (Repo → Vault)

Sessions that produced results, decisions, or insights end with the matching vault entry written via `Write`/`Edit` to the vault path — **new entries at the top of the page, just below the `---` header, reverse-chronological**. Formal artifacts (`[RESULT]`, `[DECISION]`, `[NEGATIVE]`, `[PIPELINE]`, `[DATA]`) go to the Computational-Log or mapped file; the session story (judgement calls, dead-ends, surprises, CodeRabbit batches, workflow lessons) goes to a daily note `vault/05-Daily/YYYY-MM-DD.md` when there is commentary worth preserving. Entry and daily-note templates: `.claude/rules/vault-templates.md`.

## Common Workflows

```bash
uv run pytest                        # all tests; -m "not slow" to skip slow
uv run pytest tests/financial_tda/   # domain-specific; -m validation for math checks
uv run ruff check .  &&  uv run ruff format .
```

- New experiment: data via domain `data/` modules → topology via domain `topology/` → analysis in domain `analysis/` → output to `results/`.
- Full pipelines: `trajectory_tda/scripts/bhps_pipeline.py`, `financial_tda/experiments/`, `poverty_tda/validation/`.
- Paper work: `.claude/rules/papers.md`. Branch naming: `paper/pXX-name` for prose, `run/pXX-name` for computation.
- Before long compute or a context-heavy stretch: write checkpoint/handoff state (`.apm/memory/` or the bus) so a resumed session continues without re-derivation; prefer background tasks and subagents for >10-minute compute.

## Testing Conventions

Markers: `slow` (long-running), `integration` (external deps/data), `validation` (mathematical correctness against published results, e.g. Gidea-Katz 2017). Tests live in `tests/<domain>/`. Full permutation-null distributions need `--run-slow` / `-m slow`.

## APM Workflow

APM v0.5.3. Phase plans live in `.apm/Implementation_Plan.md` — check before starting work. Initiate manager/implementation agents via `.github/prompts/`; log progress in `.apm/Memory/`. Output-file mechanics (two-path rule, gitignored intermediates, checkpoints, UKDA guide locations): `.claude/rules/apm-outputs.md`.

## What NOT to Do

- Do not mock external data sources in integration tests — real cached data or `@pytest.mark.integration` skip.
- Do not hardcode file paths; use `pathlib.Path` relative to the package root or a config.
- Do not import `torch-geometric` without checking it is installed (optional dependency).
- Do not commit large data files; data lives outside the repo or gitignored.
- Do not skip pre-commit hooks (`--no-verify`); do not amend published commits.

## Code Exploration

`Read` for known paths (typically just before `Edit`/`Write`) · `Grep` for content search (`type:` filter, `output_mode: "content"`) · `Glob` for filesystem inventory · never Bash `grep`/`rg`/`find` for code search. For large multi-step searches, spawn an `Explore` subagent rather than burning main context.

---

APM_RULES {

## Empiricism-first ordering

- Data analysis precedes prose for the same section. Do not draft prose against expected, predicted, or partial results — the result lands in `results/...` with a vault `[RESULT]` entry before dependent prose begins.
- Outcome-contingent prose direction is locked by a vault `[DECISION]` entry recording the outcome against the pre-registered decision rule. No prose for that section until the lock is on file.
- When a Task relies on an inferred property of an external resource — a harmonised dataset's coding rule, a library's behaviour, a checkpoint's schema — verify before relying on it. Do not assume.

## No speculative paths

This project's history includes large costs from work pursued on speculative foundations. Do not pursue analyses, prose, or implementation whose foundation is "this is probably true" without verification. Surface uncertainty as a User-decision point or a verification step in the same Task; do not proceed past it.

## Research assurance before dispatch and acceptance

- Before dispatching or accepting any Task touching mathematical, statistical, topological, representation, output-provenance, or paper-claim logic: run research-assurance triage — classify assurance lanes, identify governing pre-registrations/decision rules/contracts/vault locks, decide which claims are machine-checkable vs human-review-only.
- Machine-checkable claims need an enforcement artifact where practical (contract, binding test, output schema, validation command, smoke/canary, provenance check); if not mechanized, record why.
- Passing software tests is not sufficient for research Tasks: lint, unit tests, and smoke runs can pass while mathematical validity, null-model validity, provenance, or claim traceability fail.

## Vault discipline

- Every Task ends with the appropriate vault entry (prefix→file mapping per Commit Message Conventions) appended **top-of-page, reverse-chronological**, via `Write`/`Edit` on absolute paths under `C:\Users\steph\Documents\TDA-Research\`. `vault_observe` is NOT a write path — it attaches an observation for retrieval, never appends to the page; use it only *in addition* when an entry should be discoverable from a related page lacking a wikilink.
- Pre-registration entries are written **before** outcome-contingent runs: parameter values, decision rule, prose-direction rule per outcome, timestamp. The post-run `[RESULT]` references the pre-registration.
- Vault reads for graph context via vault-engine MCP; vault writes via `Write`/`Edit` (there is no MCP write tool).

## Output files (core — full mechanics in .claude/rules/apm-outputs.md)

- Numerical results use date-suffixed filenames (`<basename>_<YYYY-MM-DD>.json`). Never overwrite an existing results file.
- Deliverable JSONs are committed on the Task branch; `*.csv`/`*.pkl` are globally gitignored (UKDA T&C + size) — write to `PROJ_ROOT`, commit the producing script.
- **Gitignored ≠ inaccessible:** files at `PROJ_ROOT` are on disk regardless of git status — verify at the absolute path before declaring anything missing; regenerate from the committed script before escalating.
- Locked notational decisions go in `papers/shared/notation.md`; never let two papers diverge on the same object.

## Surfacing User-decision points

Journal-formatting decisions, methodological judgement calls, data-availability constraints, inferred-vs-observed contradictions: surface as an explicit User-facing prompt within the Task. Do not guess and do not block.

## Version control

- Repository `c:\Users\steph\TDL`; base branch `main`. Each dispatched Task gets a feature branch: `pipe/<desc>` (pipeline code-side), `run/<desc>` (computational), `paper/<desc>` (prose), `repo/<desc>` (repo extraction). Branch names describe the work, not Task IDs.
- Commits use `[PREFIX] PXX:` with the Co-Authored-By trailer. Never `--no-verify` — pre-commit hooks must run.
- Workers commit on their own branches and do not merge; the Manager performs all merges to `main` after Task Review. Parallel dispatch via worktrees under `.apm/worktrees/` (concurrency cap 3–4); the main working directory stays on `main` for merges.
- **Worktree `.env` (mandatory):** after `git worktree add`, immediately `Copy-Item "c:\Users\steph\TDL\.env" "<worktree-path>\.env"` — gitignored, never auto-copied; without it `uv run --env-file .env` fails silently.
- **Worktree removal is manual** — start of a Manager session or explicit User trigger ("sweep worktrees"), never automatic post-merge: CodeRabbit reviews can continue after the merge lands and the project relies on them as a safety net. Sweep only worktrees whose PRs are closed AND whose CodeRabbit review has concluded (`gh pr view <PR#> --json comments`). Pre-removal: (1) branch result files merged to `main`; (2) downstream-needed gitignored files present at `PROJ_ROOT` (regenerate if not); (3) list swept worktrees in the Tracker notes. Hard block on timer/merge-event auto-cleanup; overrides `.claude/apm-guides/task-review.md` §2.5.
- `.apm/` tracking is Option B: planning artefacts (`plan.md`, `spec.md`, `tracker.md`, `memory/index.md`, `metadata.json`) tracked; runtime artefacts (`bus/`, Worker Task Logs in `memory/stage-NN/`, `worktrees/`) gitignored.

## Cross-Worker output consumption

- A Task depending on another Worker's output reads that deliverable directly (the Task description names the producing Task and the boundary artifact) — never re-run the producing computation.
- Missing/malformed committed JSON → surface the inconsistency, never fabricate a substitute. Missing gitignored intermediate → regenerate from the committed script; escalate only if the script is absent or regeneration fails.

## Methodological mandates

See "Methodological Mandates" and "Code Conventions" above plus `.claude/rules/python.md` — locked rules; reference, do not re-derive.

