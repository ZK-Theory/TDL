---
paths:
  - "results/**"
  - ".apm/**"
  - "**/scripts/**"
---

# APM Output-File Mechanics

## Two-path rule — mandatory for all scripts running in worktrees

Every script defines two root paths and uses them strictly:

- `WORKTREE` — the worktree checkout the script runs from (committed deliverables, e.g. result JSONs, live here on the Task branch).
- `PROJ_ROOT` — `c:\Users\steph\TDL` (gitignored intermediates consumed across tasks are written here, not to the worktree).

## Downstream data guarantee

Every task **producing** a gitignored intermediate consumed downstream must:

1. List the file with its full `PROJ_ROOT`-based absolute path in its Output section.
2. Write it to that `PROJ_ROOT` path (not the worktree path).
3. Note the regeneration command in the Task Log.

Every task **consuming** a gitignored intermediate must:

1. Verify the file exists at its expected `PROJ_ROOT` path before any computation.
2. If missing: run the committed producing script to regenerate it. Escalate only if the script is missing or regeneration fails.

The Manager verifies all cross-task gitignored dependencies are present in `PROJ_ROOT` before dispatching any consuming task and before removing any worktree.

## Input-provenance gate (pre-dispatch data-coherence)

Presence is necessary but **not sufficient** — co-consumed inputs must also share a coherent data vintage. (B9, 2026-06-22: the OM input `01_trajectories_sequences.json` was present but regenerated 2026-05-02, three weeks after the GMM labels it was matched against (2026-04-08); the dispatched ARI recompute returned 0.2062 instead of the committed 0.2611807.) Every Task that consumes input data carries an **input-provenance manifest** and an **Input Provenance Ledger**, enforced at two points:

1. **Manifest** — a YAML data file under `contracts/manifests/input-provenance/<task>-inputs.yaml` (not a contract; it lives under `manifests/` so the contract gate does not validate it as one). Each input declares its `path`, `role`, `root`, and an `expected` signature:
   - `root: worktree` (default) — a committed file, resolved under the running checkout. **Git does not preserve mtimes** (a fresh worktree resets them to checkout time), so the git-stable signature is the content `sha256`. Do not pin `vintage_date` for these.
   - `root: proj_root` — a gitignored intermediate, which lives only at `PROJ_ROOT` (absent from worktrees). Its mtime there is meaningful, so pin `vintage_date` (and/or `sha256` if recorded). Vintage-spread coherence (`coherence.max_vintage_spread_days`) is computed only across `proj_root` inputs.
   - `enforced: false` documents an expected-coherent state not yet satisfied (e.g. an open data-vintage decision): R-B still reports it, the commit gate skips it. Flip to `enforced: true` once coherent.

2. **R-B — Manager pre-dispatch (mandatory before issuing the Task):** run `uv run --env-file .env python -m shared.manager_predispatch_check contracts/manifests/input-provenance/<task>-inputs.yaml`. It exits non-zero on any missing/mismatched/incoherent input. **Paste its output into the Task Prompt's Input Provenance Ledger section** — that pasted block, generated from a fresh on-disk check, is the ledger. Do not author the ledger from memory.

3. **R-C — Worker commit-time:** the `input-provenance-manifest-coherence` invariant contract's binding test re-runs the same check over every `enforced: true` manifest, so an input that drifts between dispatch and the Worker's commit fails the Worker's own pre-commit gate. (Implemented on the existing four contract kinds — no meta-schema change.)

## General output rules

- Numerical results use date-suffixed filenames (`<basename>_<YYYY-MM-DD>.json`). Never overwrite an existing results file — new date suffix; old file preserved as historical record.
- **All deliverable JSON files are committed on the Task branch** — explicitly `git add` every result JSON listed in the Task Output section before committing.
- **`*.csv` and `*.pkl` are globally gitignored** (UKDA T&C compliance and size). Write them to `PROJ_ROOT` per the two-path rule; commit the producing script so they are regenerable; never attempt to commit these types.
- **GMM and model checkpoints (pkl/joblib)** — deliverable set: (1) producing script committed on the Task branch; (2) timestamped metrics JSON committed at `WORKTREE/results/...`; (3) pkl checkpoint written to `PROJ_ROOT/results/...` — not committed, regenerable. Log both paths in the Task Log.
- **Gitignored ≠ inaccessible.** Any file written to `PROJ_ROOT` is on disk regardless of gitignore status — verify at the absolute path before concluding it is missing.

## UKDA user guides (plain-text conversions, gitignored, on disk — use `Read` at absolute paths; PDF Viewer MCP cannot access local files)

- `c:\Users\steph\TDL\data\guides\6614\` — four curated guides: `6614_main_survey_bhps_harmonised_user_guide.md`, `6614_main_survey_user_guide_family_matrix_xhhrel.md`, `6614_Understanding_Society_and_its_income_data.md`, `6614_main_survey_user_guide_weighting_variables.md`
- `c:\Users\steph\TDL\data\UKDA-6614-tab\mrdoc\pdf\` — all 86 UKDA documentation PDFs converted to `.md`. Main methodological guides: `6614_bhps_harmonised_user_guide.md`, `6614_main_survey_user_guide.md`, `6614_bhps_user_manual_volume_a.md`, plus wave-specific technical reports.
