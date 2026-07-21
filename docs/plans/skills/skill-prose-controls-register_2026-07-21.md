# Skill Prose-Controls Register

**Date:** 2026-07-21
**Task:** SKL-4 (docs/plans/skills/2026-07-02-skill-suite-ars-readiness-plan.md)
**Scope:** every `SYNC_SKILLS` skill's `SKILL.md` (authoring tree `.agents/skills/`), 61 skills.
**Author:** Opus (audit), against a directly-read enforcement inventory.

## Purpose

Enumerate every control-like assertion carried in skill *prose* and classify whether it is
already mechanically enforced, could be mechanized (with a one-line sketch), or is
genuinely a judgment call. Rationale (SKL-4 brief): ARS reviews cite prose-carried
controls as an anti-pattern — machine-checkable controls belong in hooks/contracts;
skills teach judgment. This register is the map of where prose is doing an enforcer's job.

A "control-like assertion" here is an imperative rule with a clear comply/violate boundary
governing research integrity, provenance, safety, scope, or a locked convention — not
general procedure narration or prose-style advice. Skills whose body is purely procedural
or advisory get an explicit **`none`** row so coverage is checkable against the full roster.

## Method — enforcement artifacts read before classifying "enforced"

Classifications of "enforced" were made only after reading the actual artifacts, not their
names. Verified this session:

| Artifact | Kind | What it actually does (verified) |
|---|---|---|
| `notation-guard.sh` | PreToolUse **deny** | Denies a `Write`/`Edit`/`MultiEdit` whose target is `papers/**/*.{md,tex,txt}` (except `papers/shared/`) and whose content contains the literal `W_1`/`W_{1}` (regex `W_\{?1\}?(?!\d)`). Does **not** check code, does **not** enforce W₂-in-computation, landscape-L² complement, or `bottleneck`. |
| `results-no-overwrite.sh` | PreToolUse **deny** | Denies an agent `Write`/`Edit`/`MultiEdit` that overwrites an **existing** `results/**/*.{json,npy,npz}` with differing bytes. Does **not** cover `.csv`/`.pkl`, does **not** see files written by Python scripts (the normal production path), does **not** check date-suffix naming — only in-place overwrite of an existing path. Fails open on error. |
| `dispatch-readiness-guard.sh` | PreToolUse **deny** | Denies a `Write` to `.apm/bus/<agent>/task.md` that is a Task Prompt (`## Workspace` or frontmatter `log_path`/`tasks`) unless it carries a `## Dispatch Readiness` block that is not `**FAIL**`. Only `Write`, not `Edit`. Fails open. |
| `research-context-check.sh` | PostToolUse **warn only** | Prints a warning when a new `.py` `Write` lacks `# Research context:` in its first 10 lines. **exit 0 — never blocks.** A control asserting this header is "required" is *not* deny-enforced. |
| `results-vault-reminder.sh` | PostToolUse **reminder only** | Prints a `/vault-sync` nudge on a `results/**` write. Non-blocking. |
| `mirror-tree-guard.sh` | PreToolUse **deny** | **NEW (this task).** Denies an agent `Write`/`Edit`/`MultiEdit` into the Claude-side mirror `.claude/skills/…` tree. Sync tool writes via Python and is unaffected. |
| `.githooks/pre-commit` | git gate | Gate 0 `sync_agent_skills.py --check` (dual-tree parity, incl. `MIRROR_EDITED`); Gate 1 ruff; Gate 2 `contract_binding_check.py` (contract meta-schema, binding-test existence via AST, pytest of bound tests, JSON-schema validation of **staged** `results/` output files against `output_validation` contracts). |
| `.githooks/commit-msg` | git gate | Rejects a subject line lacking one of `[RESULT|DECISION|NEGATIVE|PIPELINE|DATA|EXPLORE]` (merges/reverts/fixups/squashes skipped). |
| `.githooks/prepare-commit-msg` | git advisory | Suggests a prefix; never blocks. |
| `contracts/**` | contracts (via Gate 2) | 120+ YAMLs present. Every contract named as an "Enforcing contract" by a skill was confirmed to exist on disk (see below). |
| `tools/apm_task_prompt_check.py` | tool (exists, **not** auto-wired) | Present, but **not** referenced by `settings.json` or `.githooks/`. It is a manual/Manager-invoked check, not an automatic gate. The wired dispatch gate is `dispatch-readiness-guard.sh` (block-presence only). |

Named contracts confirmed present (spot of the claim-validity / result-immutability set):
`topology-invariants/null-operation-changes-ph-input.yaml`,
`topology-invariants/frozen-loadings-null-threading.yaml`,
`topology-invariants/frozen-loadings-transform-only.yaml`,
`stochastic-tests/monte-carlo-permutation-p-value.yaml`,
`stochastic-tests/markov-order-provenance.yaml`,
`stochastic-tests/icc-cluster-bootstrap.yaml`,
`regression-specs/{rubin-pooling,normalised-ipw-trimming,mice-convergence-rule,svyglm-cluster-robust-se}.yaml`,
`stage1-output-schemas/stage1-output-json-validation.yaml` (+ many `*-output-json-validation`),
`discovery-harness/{assay-scorecard,spike-pre-registration,spike-result-summary}.yaml`,
`data-provenance/input-provenance-manifest-coherence.yaml`. **No phantom contracts found.**

## Escalation determination (SKL-4 stop condition)

The brief requires immediate escalation if a control is *believed enforced* but actually
uncovered **and** it guards result immutability or claim validity. **This condition is not
met — no escalation is raised.** Reasoning:

- **Result immutability.** Many skills assert "results are date-suffixed and never
  overwritten." This is backed by `results-no-overwrite.sh`, which is **real but partial**
  (agent-tool `Write`/`Edit` of existing `.json/.npy/.npz` under `results/` only; script
  writes and `.csv`/`.pkl` are outside it). The prose does **not** over-claim this: it is
  framed as a *convention* (CLAUDE.md APM_RULES) with the hook as a backstop, and
  `result-provenance-review` explicitly calls itself "the judgment layer over … the
  no-overwrite enforcement hook." A known-partial hook honestly described is a register
  entry (extend/complement), not a false enforcement belief. Captured below, not escalated.
- **Claim validity.** `paper-claim-trace` explicitly states "Enforcing artifact:
  human-review-only — there is no contract for claim honesty; this skill *is* the check."
  That is honest, not a false "enforced" claim. `tda-statistical-analysis-review` and
  `tda-peer-review-panel` are likewise declared review passes, not gates.

The only "believed enforced but not wired" nuance found is
`pre-reg-to-dispatch`'s "Enforcing artifact: `apm_task_prompt_check.py`" — the script
exists but is not wired to any hook/CI. This guards **dispatch-prompt completeness**, not
result immutability or claim validity, so it is a register `enforceable (gap)` row (below),
below the escalation bar.

## Classification legend

- **`enforced-by:<artifact>`** — an actually-verified hook/contract/git-gate enforces it.
  `(partial: …)` when the artifact's scope is narrower than the prose assertion.
- **`enforceable:<proposed artifact>`** — machine-checkable, no artifact yet; sketch given.
- **`enforceable (gap)`** — believed/named as enforced but the artifact is absent or unwired.
- **`judgment-only`** — genuinely needs human/agent judgment; not mechanizable.
- **`none`** — the skill carries no control-like assertion (advisory/procedural only).

---

## Register

### adversarial-design-review

| Quoted assertion | Class | Sketch (enforceable only) |
|---|---|---|
| "A report written to a `reviews/` path (never overwrite the reviewed documents)" | judgment-only | — |
| "You MAY directly fix … unambiguous factual errors *after recording them in the report*. PROPOSE — never silently rewrite — any material governance … change." | judgment-only | — |
| "confirm **every** decision, invariant, and test has an explicit disposition" (Completeness Gate) | judgment-only | — |
| "A gate passes only on exact required-set closure, not merely because all supplied evidence passed." | judgment-only | — |

Note: this skill is itself a human-review procedure; its "controls" are review obligations, not mechanizable checks.

### assay
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Axis 1 gate must pass before PROMOTE is possible … PROMOTE iff Axis 1 passes and Axis2 + Axis3 >= 4 with neither score at 0." | enforced-by:`contracts/discovery-harness/assay-scorecard.yaml` (decision-rule fields validated) + in-skill `validate_assay_scorecard` | — |
| "Do not add programme_fit to the machine-readable block." | enforced-by:`assay-scorecard.yaml` (`forbidden_keys`) *if* the schema forbids it | verify `programme_fit` is a `forbidden_keys` entry; add if absent |
| "Verify any kill-justifying citation directly … before it can KILL a candidate." | judgment-only | — |
| "PROMOTE is a user-decision point, not automatic execution." | judgment-only | — |
| multi-block notes: "iterate and validate every block explicitly … the standard extractor silently under-validates the second application." | enforceable:`validate_assay_scorecard` multi-block mode | make `extract_scorecard_block` return all blocks; contract test asserts N-block validation |

### bhps-wave-crosswalk
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Never assume BHPS and USoc share variable coding. Always check before implementing." | judgment-only | — |
| "For unverified variables, add `# CODING UNVERIFIED:` …" | enforceable:lint | grep gate flagging new `extract_*` harmonisers touching known-divergent vars (income, NS-SEC, hiqual, hlstat) without a `CODING UNVERIFIED`/crosswalk citation |

### commit-log
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Produce a correctly prefixed commit message (≤72 chars)" | enforced-by:`commit-msg` (prefix); `(partial)` — 72-char limit is only advisory in `commit-msg` | make the 72-char check blocking in `commit-msg` if desired |
| "Do NOT use `Out-File -Encoding utf8` … Use `[IO.File]::WriteAllText(… UTF8Encoding($false))`" | enforceable:hook | pre-commit/commit-msg check: reject a commit-message file beginning with a UTF-8 BOM |
| "Do not use this [vault-not-updated] exception for research methods, parameters, estimands, or result interpretation." | judgment-only | — |

### contract-first-tdd
| Quoted assertion | Class | Sketch |
|---|---|---|
| "the implementing agent never authors its own contract (locked 2026-05-27 in `CONVENTIONS.md`)" | enforced-by: contract-authorship split is procedural; **partially** enforced-by:`.githooks/pre-commit` Gate 2 only insofar as `pending`/binding lifecycle is validated | enforceable: gate flagging a diff that adds a `contracts/*.yaml` AND its implementing module in one commit |
| "Result files are date-suffixed and never overwrite an existing file." | enforced-by:`results-no-overwrite.sh` (partial: agent Write/Edit of `results/**/*.{json,npy,npz}` only; script writes & `.csv`/`.pkl` uncovered; naming not checked) | extend: date-suffix filename-shape check in `output_validation`; a script-side no-overwrite guard |
| "assert the **exact value and type** — `n == 711`, `family == "quasibinomial"` … not key presence, not '> 0'. Add a negative case for each `must_assert` clause." | enforced-by:`contract_binding_check.py` (Gate 2 claim-to-assertion coverage; value/type is the contract author's duty) | — |
| "Producers emit contract-pinned fields as exact literal tokens … a literal living only in a contract description is documentation, not a guard." | enforced-by:`contract_binding_check.py` (Gate 2, when the binding test equality-checks the literal) | — |
| "Seeds specified and recorded for anything stochastic." | enforceable:`output_validation` `required_keys: metadata.seed` (already present in several stage1 schemas) | make `metadata.seed` a required key across result schemas |
| "Never proceed on 'probably fine'." (contract resolved before implementation) | judgment-only | — |

### executing-plans-extras
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Run the literal command from the specified directory … do not substitute a unit-level function call." | judgment-only | — |
| "Treat exit zero with missing output or missing state change as a failed verification …" | judgment-only | — |
| "Do not mark the task complete when only an internal function test passed …" | judgment-only | — |

### gh-address-comments-extras
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Force UTF-8 mode for the process, for example by setting PYTHONUTF8=1." | enforceable:env/wrapper | ship a thread-fetch wrapper that sets `PYTHONUTF8=1` + `encoding=utf-8, errors=strict` |
| "An annotation message alone is not a rule identity. … Do not infer an ID from a similarly named rule." | judgment-only | — |
| "Run a fresh remote analysis. Only that rerun proves the suppression matched and the finding closed." | judgment-only | — |

### humanizer
| Quoted assertion | Class | Sketch |
|---|---|---|
| (prose-quality guidance: significance-inflation, hedge-stacking, em-dash overuse, etc.) | judgment-only | — |
| "Run at v2/v3 completion, not per-section." | judgment-only | — |
Note: body is anti-AI-tell **advisory** prose editing; no hard control besides the run-timing note.

### markov-null-design
| Quoted assertion | Class | Sketch |
|---|---|---|
| "the P01-B mandate that Markov order k is always explicit … `markov_order=1, # ALWAYS explicit — never omit`" | enforced-by:`stochastic-tests/markov-order-provenance.yaml` (result-side k provenance); prose-side judgment | notation-check skill covers prose (not a gate) |
| "`n_permutations < 200` for a published result → Increase to ≥500 (Wasserstein) or ≥200" | enforced-by:`output_validation`/pre-reg `decision_coupling_invariants` (e.g. `n_permutations >= 500`) where present | add `n_permutations >= 200/500` invariant to the relevant result contract |
| "Landmarks selected once from observed data → Re-select per permutation (maxmin_landmarks)" | enforced-by:`topology-invariants/null-operation-changes-ph-input.yaml` + `frozen-loadings-*` (adjacent) | dedicated invariant asserting per-draw landmark reselection |
| "Statistic … a function of the same sufficient statistic the null is fit from … expect p≈0.5 … Add a lower rung / richer substrate / two-sample design." | judgment-only | — (centering degeneracy is a design judgment; see null-operation-invariance-audit) |

### new-analysis
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Results go to `results/…`; Code goes in `…/experiments/` or `…/scripts/`." | enforceable:convention lint | path-shape check only; low value |
Note: otherwise procedural scaffolding; no strong control.

### notation-check
| Quoted assertion | Class | Sketch |
|---|---|---|
| "`$W_1$` \| Must justify or change to `$W_2$`; `$W$` unsubscripted \| Always wrong" | enforced-by:`notation-guard.sh` (partial: literal `W_1` in `papers/**/*.{md,tex,txt}` only; unsubscripted `W` and `W_p` **not** caught) | extend `notation-guard.sh` regex to flag bare `$W$` and `W_p` without a nearby `p=` |
| "Markov order always written as $k$ explicitly" | judgment-only (prose) | — |
| "Propose fixes but do not apply without user confirmation … always ask before editing [theorems]." | judgment-only | — |
| "**Ruling-out exception:** … write it in words … never the literal order-1 subscript token" (because the notation-guard hook is a blunt literal guard) | enforced-by:`notation-guard.sh` (this row documents the hook's known blind spot) | (documents hook limitation; a context-aware guard is the enforceable improvement) |

### null-operation-invariance-audit
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Confirm the shuffle is **upstream** of the statistic, so a non-identity permutation produces a different statistic value." | enforced-by:`topology-invariants/null-operation-changes-ph-input.yaml` | — |
| "Centering check … Require a lower-order null rung, a statistic on a richer substrate, or a two-sample design." | judgment-only | — |
| "A length/shape divergence is a red finding, not a runtime detail to fix later." | enforceable:invariant | contract asserting observed & one null draw share grid length/shape before reduction |

### panel-estimand-audit
| Quoted assertion | Class | Sketch |
|---|---|---|
| "The estimand is unchanged from the prior run; if it must change, a pre-registration amendment is required." | judgment-only | — |
| "Eligibility aligns … Denominator aligns … Weighting/clustering consistent." | enforced-by:`regression-specs/{normalised-ipw-trimming,svyglm-cluster-robust-se,rubin-pooling,mice-convergence-rule}.yaml` (mechanical sub-parts); estimand alignment itself judgment | — |

### paper-claim-trace
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Every quantitative or interpretive claim … must trace to a specific result file and the pre-registered decision rule." | judgment-only | — |
| "A claim with no backing artifact is flagged 'awaiting computation' — do not draft prose for it (empiricism-first)." | judgment-only | — |
| "Enforcing artifact: human-review-only — there is no contract for claim honesty; this skill *is* the check." | judgment-only *(explicitly declared — honest)* | — |
Note: the honest self-declaration here is why the escalation rule does **not** fire for claim validity.

### paper-draft
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Banned in draft/section files:** `this working file` · `Task Prompt` · `Manager` · `ISSUE <ID>` · … · result-JSON filenames or repo paths in body text · Task/Stage numbers." | enforceable:hook | PostToolUse warn on a `papers/**/drafts/**` write containing any banned token / `results/…json` path / `ISSUE <ID>` |
| "**Never overwrite a previous draft.** … increment version number from the current highest draft." | enforceable:hook | PreToolUse deny an `Edit`/overwriting `Write` to an existing `papers/**/drafts/vN-YYYY-MM.md` (mirror of results-no-overwrite for drafts) |
| "Pre-delivery self-check (do not skip): re-read and delete anything a referee could not read." | judgment-only | — |

### paper-repo-extract
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Confirmation gate (required, human-in-the-loop).** … obtain explicit user confirmation. Do not proceed on assumption; if the target directory already exists, stop and ask rather than overwriting." | judgment-only | — |
| "No real BHPS/USoc data in the repo (data access agreement)" | enforceable:extraction check | smoke/CI assertion that the extracted `data/` contains only `synthetic/`; grep for UKDA tab prefixes |
| "`uv run pytest tests/` must pass without TDL installed" | enforced-by: the extraction's own smoke test (`tests/test_smoke.py`), run manually | wire into extraction script as a required step |

### phase0-status
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Read-only — never modifies files." | judgment-only | — |

### pre-reg-to-dispatch
| Quoted assertion | Class | Sketch |
|---|---|---|
| "If none [pre-reg] exists for an outcome-contingent run, stop — the pre-reg must be filed first." | judgment-only | — |
| "If it changes a parameter, the decision rule, the null model, or the eligibility rule … Require a pre-registration amendment, filed and locked … *before* dispatch." | judgment-only | — |
| "do NOT write contract YAMLs into `contracts/` on `main` … embed … inside the pre-registration as a `planned_contracts` array." | enforceable:hook | PreToolUse warn on a `Write` adding `contracts/*.yaml` while on `main` |
| "the **Worker** writes ONLY the binding test and clears `pending`." (authorship split) | enforced-by:`contract_binding_check.py` pending lifecycle (partial); authorship attribution itself judgment | — |
| "Forbid writing toy/synthetic/illustrative output to `results/`." | enforceable:hook | extend `results-no-overwrite`/new hook to deny writes to `results/**` containing `synthetic`/`toy` markers, or a `forbidden_keys: [synthetic]` output-contract (precedent exists) |
| "Enforcing artifact: `apm_task_prompt_check.py` (verifies the dispatched prompt carries the assurance block …)" | **enforceable (gap)** — script exists at `tools/apm_task_prompt_check.py` but is **not** wired to any hook/CI | wire `apm_task_prompt_check.py` into `dispatch-readiness-guard.sh` or a bus-write PreToolUse hook |
| "verify the referent, not just the derivation, before dispatch" (value-proposition claims a pipeline step exists) | judgment-only | — |

### representation-freeze-audit
| Quoted assertion | Class | Sketch |
|---|---|---|
| "The embedding … was frozen *before* any null draw or cross-group comparison." | enforced-by:`topology-invariants/frozen-loadings-null-threading.yaml`, `frozen-loadings-transform-only.yaml` | — |
| "Null operates pre-embedding … Permuting embedded rows is the invariance bug; reject it." | enforced-by:`topology-invariants/null-operation-changes-ph-input.yaml` | — |
| "Frozen and provisional embeddings write to distinct, clearly named output paths; a provisional embedding is never read as the frozen reference." | enforceable:`output_validation`/path check | contract asserting frozen vs provisional path prefixes are disjoint |

### reproducibility-package-review
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Every result file (including gitignored `*.csv`/`*.pkl`) has its producing script committed on the branch." | judgment-only (cross-file, whole-set) | — |
| "the **pinned pre-commit version governs** (commits must pass hooks, never `--no-verify`)" | enforced-by:`.githooks/pre-commit` Gate 1 (ruff via pinned `.pre-commit-config.yaml`) | — |
| "Enforcing: the two-path rule and downstream-data guarantee in CLAUDE.md APM_RULES." | enforced-by:`data-provenance/input-provenance-manifest-coherence.yaml` (input side) + judgment | — |

### research-assurance-triage
| Quoted assertion | Class | Sketch |
|---|---|---|
| "For machine-checkable claims, choose at least one artifact: contract, binding test, output schema, validation command, smoke/canary, provenance check." | judgment-only (the triage rule itself) | — |
| "**Expected/sanity values are inputs to falsify, not targets.** … independently re-derived, never reproduced-and-stopped." | judgment-only | — |
| "**Guard degenerate fallbacks.** … require an output-contract assertion that *excludes the degenerate constant* in the normal regime … plus a binding test against an independent oracle." | enforced-by:`contract_binding_check.py` (Gate 2, when authored); the *requirement to author it* is judgment | value-in-open-interval invariant per statistic with a degenerate fallback |
| "A machine-checkable claim has no enforcement artifact and no explicit reason → stop." | judgment-only | — |

### result-provenance-review
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Numerical results use `<basename>_<YYYY-MM-DD>.json`. … No silent overwrite." | enforced-by:`results-no-overwrite.sh` (partial: existing `results/**/*.{json,npy,npz}` overwrite via agent tools only; naming shape unchecked) | filename-shape `output_validation` gate; script-side no-overwrite guard |
| "writes deliverables to the `PROJ_ROOT` path, not the worktree path." (two-path rule) | judgment-only | — |
| "Every stochastic step … has its seed set in the script and recorded in the vault `[RESULT]` entry." | enforceable:`output_validation` `metadata.seed` (script side); vault side judgment | — |
| "A cache built under different parameters is not a valid input." | enforceable:invariant | cache metadata must record `{seed,B,L,null,k}`; consumer asserts match before reuse |
| "the superseded file is `git rm`ed — not left matching an `output_validation` dispatch glob … confirm the enforcement test *exercises* the files it guards." | enforced-by:`contract_binding_check.py` Gate 2 dispatch globs (partial — a skip pattern can still hide files) | — |
| "Reusable reference caches self-declare their generative inputs [sha256 of every generative input]." | enforceable:schema | cache-metadata contract requiring `source_input_sha256` |
| "File provenance rulings [live] under the object they rule on (e.g. `SUPERSEDED.md`)." | judgment-only | — |

### schema-contract-design
| Quoted assertion | Class | Sketch |
|---|---|---|
| "`id` is kebab-case and MUST equal the filename stem. Required keys: `id`, `kind`, `description` (>=20 chars), `spec_citation`, `binding`." | enforced-by:`contract_binding_check.py` Gate 1 meta-schema (`contracts/schema/contract.schema.yaml`) | — |
| "`binding.test_function` (unique across ALL contracts by the one-to-one rule)" | enforced-by:`contract_binding_check.py` (one-to-one rule) | — |
| "**Assert VALUE and TYPE, not key presence** … A check that only confirms a key exists … is NOT enforcement." | enforced-by:`contract_binding_check.py` coverage gate (partial — depends on the binding test's own assertions) | — |
| "Fixtures must not depend on gitignored intermediates … must be constructible from committed files alone." | enforceable:gate | Gate 2 check that a binding test's fixtures don't read `PROJ_ROOT`/gitignored paths without a `pytest.skip` guard |
| "If the binding test is not yet on the base branch, set `pending: true`." | enforced-by:`contract_binding_check.py` pending lifecycle + pending-debt gate | — |

### scout-review
| Quoted assertion | Class | Sketch |
|---|---|---|
| "This skill only ever produces `triaged` entries … It never marks `assayed`, `spiked`, `registered`, etc." | judgment-only | — |
| "`_backlog.md` is the single source of truth for state — never duplicate state tracking elsewhere." | judgment-only | — |
| "Write the triage output back into the inbox note itself (append a `## Triage` section) — do not create a separate triage file. This `## Triage` section is the completion marker." | enforceable:convention lint | check every `_inbox/YYYY-Www.md` older than N days has a `## Triage` section |

### sensitivity-comparison-review
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Confirm each [downstream field] is present in the result JSON for every arm / cell / probe — not just the headline arm." | enforced-by:`*-output-json-validation` `required_keys` (per-arm) where authored | add per-arm `required_keys` to the comparison-JSON schema |
| "A schema change that drops a field is caught — prefer a `schema` contract with explicit `required_keys` over informal review." | enforced-by:`contract_binding_check.py` Gate 2 (when the schema exists) | — |

### spike
| Quoted assertion | Class | Sketch |
|---|---|---|
| "No speculative path becomes an APM task without a locked Spike pre-registration. … do not run the Spike until Stephen has explicitly approved the PROMOTE decision." | judgment-only | — |
| "The Spike pre-registration validates with `validate_spike_preregistration`." | enforced-by:`contracts/discovery-harness/spike-pre-registration.yaml` + in-skill validator | — |
| "The probe is toy-scale only: `time_box_hours` between 1 and 4 …" | enforced-by:`spike-pre-registration.yaml` (if it bounds `time_box_hours`) | add `time_box_hours` range invariant to the contract if absent |
| "Default `decision_rule` to a **two-sided** test unless a directional argument is explicitly recorded." | judgment-only | — |
| "grep the codebase to confirm step X actually exists as described before locking the pre-registration" | judgment-only | — |
| "Approval is missing. Do not infer approval from a PROMOTE scorecard." | enforced-by:`spike-pre-registration.yaml` `approval.approved` field | — |

### statistical-design-audit
| Quoted assertion | Class | Sketch |
|---|---|---|
| "the denominator is the number of null draws used for the p-value, `n = min(B, total_pairs)` — not a diagnostic cap." | enforced-by:`stochastic-tests/monte-carlo-permutation-p-value.yaml` | — |
| "Two-sided Monte Carlo p-value uses the bias-corrected `p = (r + 1) / (n + 1)`; minimum achievable p is `1 / (n + 1)`." | enforced-by:`monte-carlo-permutation-p-value.yaml` | — |
| "FDR (Benjamini-Hochberg) is applied and the correction family is defined explicitly." | judgment-only (family definition); mechanical FDR partially in output schemas | — |
| "Repeated observations on the same unit are handled (cluster-robust SE, mixed model, or cluster bootstrap)." | enforced-by:`stochastic-tests/icc-cluster-bootstrap.yaml`, `regression-specs/svyglm-cluster-robust-se.yaml` | — |
| "Any Markov null states *k* explicitly." | enforced-by:`stochastic-tests/markov-order-provenance.yaml` (result side) | — |
| "Distinguish machine-checkable items (denominator, formula — bind to a contract) from human-review-only judgments." | judgment-only (the routing rule) | — |

### subagent-driven-development-extras
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Reviewer subagents remain mandatory for any authored or novel code … The whole-branch final review remains mandatory regardless of budget." | judgment-only | — |
| "A controller-supplied factual claim that authorizes a broad change … carries the same verification burden as the edit it licenses … State the exact scope actually checked." | judgment-only | — |
| "the requirement set for task N is the UNION of [plan, ledger roll-up, resume/handoff carve-outs]." | judgment-only | — |

### tda-acceleration-benchmarking
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Accept an acceleration only if ALL hold: … outputs match the baseline within a declared tolerance … contracts still pass … result artifacts are not silently overwritten." | judgment-only (acceptance gate); overwrite sub-part enforced-by:`results-no-overwrite.sh` | — |
| "The acceleration would change a pre-registered parameter (B, L) — never; surface instead." | judgment-only | — |
| "a single-configuration timing is not a benchmark." | judgment-only | — |

### tda-agent-safety-guardrails
| Quoted assertion | Class | Sketch |
|---|---|---|
| "`git commit --no-verify` — never, outside a documented emergency …" | enforceable:hook | git hooks cannot see `--no-verify`; a CI check on `main` comparing committed vs hook-clean state can detect a bypass after the fact |
| "Deleting or overwriting result artifacts; date-suffixed result files are immutable once written." | enforced-by:`results-no-overwrite.sh` (partial, as above) | — |
| "Editing the two skill trees manually out of step — changes go to the authoring tree and through the sync tool." | **enforced-by:`mirror-tree-guard.sh` (NEW, this task)** + `.githooks/pre-commit` Gate 0 (`sync --check`) | — |
| "Writing toy/synthetic output under `results/`." | enforceable:hook | see pre-reg-to-dispatch row (synthetic-marker deny / `forbidden_keys`) |
| "Are the write-time hooks active (notation guard, results no-overwrite, dispatch-readiness guard)?" | enforced-by: those hooks (names verified accurate) | — |
| "`git push` to a shared branch without explicit instruction; `git reset --hard`, `git clean`, force-pushes." | judgment-only (no repo-side hook blocks these) | enforceable: a pre-push hook / allowlist |

### tda-codebase-design
| Quoted assertion | Class | Sketch |
|---|---|---|
| "error modes (fail fast — never silently truncate, coerce, or drop)" | judgment-only | — |
| "any change that could alter a committed result's value gets a rerun plan and a vault `[DECISION]` — never a silent change." | judgment-only | — |
| "A refactor would change the numbers in a committed result file → [stop]" | enforceable:CI diff | result-JSON byte/value-diff check in CI when pipeline modules change |

### tda-diagnosing-computational-defects
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**No defect is closed merely because a test passes.** … closure requires either binding to an existing contract … or an explicit note saying why no deterministic contract applies. This is the locked Research Assurance rule in `CONVENTIONS.md`." | enforced-by:`contract_binding_check.py` Gate 2 (contract path) + judgment | — |
| "Build **one red-capable command** … 'A test that runs' is not red-capable unless it fails on the defect." | judgment-only | — |
| "The defect implicates an archived result JSON — never silently correct it; record a new date-suffixed file plus a vault entry marking supersession." | enforced-by:`results-no-overwrite.sh` (partial) | — |
| "The fix would change an estimand, a null design, or a headline claim — surface as a User decision." | judgment-only | — |

### tda-document-ingestion
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**converted text is not automatically a verified source** … Citation verification is `tda-literature-verification`'s job — this skill feeds it, never bypasses it." | judgment-only | — |
| "Numbers extracted from tables that will be cited or computed on are treated as **unverified** until checked against the source rendering." | judgment-only | — |

### tda-domain-modeling
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**W2 (Wasserstein-2)** — the primary diagram metric; W1 is never cited for P01 trajectory null-battery results." | enforced-by:`notation-guard.sh` (partial: prose `W_1` in `papers/` only) + `wasserstein-audit` (manual) | code-side `p=2` lint (see wasserstein-audit) |
| "**L = 5000** — the canonical landmark count; L = 2000 is retired." | enforceable:`output_validation` | assert `metadata.n_landmarks == 5000` on headline result schemas |
| "Notational locks go in `papers/shared/notation.md` — never let two papers diverge on the same object." | judgment-only | — |
| "The sharpening would amend a locked convention — that is a User decision plus a `[DECISION]` vault entry, never a silent edit." | judgment-only | — |

### tda-experiment
| Quoted assertion | Class | Sketch |
|---|---|---|
| "PCA loadings **frozen** from full-sample fit — do not refit on surrogates" | enforced-by:`topology-invariants/frozen-loadings-transform-only.yaml` | — |
| "Maxmin landmarks re-selected on each surrogate (do not couple landmark geometry to observed data)" | enforced-by:`topology-invariants/null-operation-changes-ph-input.yaml` (adjacent) | dedicated per-draw-landmark invariant |
| "Include `metadata` dict in results JSON: `{n_permutations, n_landmarks, seed, runtime_s, date}` … record `seed`" | enforced-by:`stage1-output-json-validation.yaml` + `*-output-json-validation` (`required_keys`) | ensure `metadata.seed` required across all result schemas |
| "Do not expand robustness cells or regenerate PH unless the dispatch explicitly authorizes that design change." | judgment-only | — |
| "On Windows, do not call `compute_rips_ph(timeout_seconds=…)` from inside a joblib `loky` worker." | enforceable:lint | AST/grep rule flagging `timeout_seconds=` within a `Parallel`/`delayed` call site |
| "Working figures must not be saved to `papers/PXX/figures/`." | enforceable:hook | PostToolUse warn on a `papers/**/figures/**` write with an exploratory/`YYYYMMDD_` name |

### tda-external-data-lookup
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Every external lookup becomes a **provenance artifact** … no value is free-typed into manuscript prose." | judgment-only | — |
| "Transform only in scripted form — no hand-edited spreadsheets between the source and the artifact." | judgment-only | — |
| "Inferential use pulls the full provenance path (date-suffixed artifact, seeds if resampled, schema validation)." | enforceable:`output_validation` | schema for external-data artifacts (dataset id, retrieval date, version) |

### tda-figure-spec
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Uses `PUBLICATION_RC`, `DPI`, `FIGSIZE_*`, `STATE_COLORS`, `_save_figure` … never ad-hoc sizes or colours." | enforceable:lint | grep gate on `papers/**/figures` scripts for literal `figsize=`/`color=` not sourced from `viz.constants` |
| "**Sequential/diverging:** `viridis`, `plasma`, `RdBu_r` — **never `jet`**" | enforceable:lint | grep for `jet`/`rainbow` in figure scripts |
| "p-values: write `p=0.003`, not `p<0.01`" | judgment-only | — |
| "Working figures must not be saved to `papers/PXX/figures/` — that is for production only." | enforceable:hook | (same as tda-experiment figure row) |

### tda-graph-network-analysis
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Graph summaries complement PH; they do not replace it." (equivalence claim needs topology lane) | judgment-only | — |
| "torch-geometric … it is an optional dependency: check it is installed before importing." | enforced-by:`.githooks/pre-commit` Gate 1 ruff only catches syntax; import-guard is judgment | enforceable: lint rule requiring a guarded import for `torch_geometric` |
| "If visualized, record the layout algorithm and seed (an unseeded layout is unreproducible)." | judgment-only | — |

### tda-handoff
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Do not bypass pre-commit hooks." | enforced-by:`.githooks/*` (the hooks themselves) | — |
| "Do not overwrite archived or date-suffixed result JSONs." | enforced-by:`results-no-overwrite.sh` (partial) | — |
| "Do not implement against a math contract authored by the implementing agent." | judgment-only | — |
| "Do not silently change sample counts — cite `sample_provenance.fitted`." | enforced-by:`stochastic-tests/sample-provenance-ledger*.yaml` (result side) | — |
| "Do not write toy/synthetic output into `results/`." | enforceable:hook (see pre-reg-to-dispatch row) | — |
| "The handoff would be the only record of a result or decision — that belongs in the vault first." | judgment-only | — |

### tda-learning-scaffold
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Learning artifacts … are never evidence." / "never under `results/` and never in the vault's methods/results pages" | enforceable:hook | deny/warn a `results/**` or `04-Methods/**` write from a file marked learning-material |
| "Do not cite exercise outputs as literature or as validation." | judgment-only | — |
| Tier-3 constraint: "may not create paper claims, result artifacts, canonical computations, or contract-bearing implementations unless routed through … tier 1 or tier 2." | judgment-only | — |

### tda-light-task-triage
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Escalate Immediately (this skill may not process the task) If It Touches [topology, null models, statistics, representation, output/provenance, result JSONs, sample counts, paper claims, contracts/hooks]." | judgment-only | — |
| "an untracked deferral is a discard in disguise." | judgment-only | — |

### tda-literature-verification
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Leads are not sources.** … are never cited directly. The locked pipeline is: lead → verify existence → Zotero → literature note → prose. No shortcuts, no orphan notes." | judgment-only | — |
| "The identifier must resolve to the **claimed** paper — matching title, authors, year, and venue. A DOI that resolves to a different paper is a failed verification." | judgment-only | — |
| "No search/Perplexity output cited directly anywhere in prose." | enforceable:lint | flag literature-note files with `status: usable` but `verified: false`/missing `doi` |
| "Verify kill-justifying citations hardest." | judgment-only | — |

### tda-paper-dissemination-pack
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Strictly downstream of review and verification — dissemination never runs ahead of the evidence." | judgment-only | — |
| "Do Not Use When: the result is provisional … Literature sources are unverified … Figures lack regeneration scripts." | judgment-only | — |
| "The allowed/prohibited claim lists come from the paper's claim tracing, not from memory." | judgment-only | — |

### tda-peer-review-panel
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Review and repair stay separate** … fixing happens in a later pass, never mid-review." | judgment-only | — |
| "Every finding cites a specific passage or claim — no finding without a location." | judgment-only | — |
| "applied P01-A content must not leak into P01-B methods sections and vice versa (P01-B §4 strict scope rule)." | judgment-only | — |
| "sources cited must have passed `tda-literature-verification`." | judgment-only | — |

### tda-prototype-sandbox
| Quoted assertion | Class | Sketch |
|---|---|---|
| "A prototype cannot write into canonical result directories." / "Write under `scratch/`, `prototypes/` … **never** under `results/`." | enforceable:hook | deny a `results/**` write from a file under `scratch/`/`prototypes/` or marked exploratory |
| "Do not overwrite canonical artifacts; do not import prototype modules from pipeline code." | enforceable:lint | grep pipeline modules for imports from `scratch`/`prototypes` |
| Tier-3 constraint (as above). | judgment-only | — |

### tda-representation-diagnostics
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**observed and null diagrams must not be compared after independently re-fitting PCA / scaler / loadings**" | enforced-by:`topology-invariants/frozen-loadings-null-threading.yaml`, `frozen-loadings-transform-only.yaml` | — |
| "UMAP/t-SNE output is visualization-only unless explicitly contracted otherwise." | judgment-only | — |
| "SHAP or other explanations: associational language only — never causal — unless separately justified." | judgment-only | — |

### tda-research-ideation-lab
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Everything produced here is **speculative by construction** and stays outside the claim pipeline until verified." | judgment-only | — |
| "Do not present generated ideas as findings. Do not cite unverified literature. Do not create implementation tasks directly." | judgment-only | — |
| "Every idea carries every applicable label: `speculative` · `literature-needed` · …" | enforceable:schema | validate the JSON output record's `status`/label fields |

### tda-scenario-stress-test
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Do not use it when the decision is already constrained by a locked convention or contract — locked means locked, and reopening one is a User decision." | judgment-only | — |
| Tier-3 constraint (as above). | judgment-only | — |

### tda-skill-authoring-workbench
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Author in the `.agents` tree.** Never edit the `.claude` mirror — an edit applied to the mirror is overwritten … at the next sync." | **enforced-by:`mirror-tree-guard.sh` (NEW, this task)** + `.githooks/pre-commit` Gate 0 (`sync --check`) + `sync_agent_skills.py` MIRROR_EDITED detection | — |
| "**Register every new skill in `SYNC_SKILLS`** … an unregistered skill hard-errors every sync run." | enforced-by:`sync_agent_skills.py` classify() (fatal on unclassified) → `.githooks/pre-commit` Gate 0 | — |
| "both trees must be byte-identical before commit." | enforced-by:`.githooks/pre-commit` Gate 0 | — |
| "Skill bodies must not contain tree-specific path literals (the sync tool lints for them)." | enforced-by:`sync_agent_skills.py` `lint_path_literals` (WARN) | make the lint fail (currently warn-only) if desired |
| "description is **trigger-only, third person, starts with 'Use when'**" | enforceable:`check_skill_metadata.py` (SKL-1) | add a description-shape check to the metadata checker |
| "never restate a locked convention differently — reference `CONVENTIONS.md`; never paraphrase a lock." | judgment-only | — |

### tda-statistical-analysis-review
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Both the test statistic AND the p-value are reported — never one alone." | judgment-only | — |
| "Headline diagram-comparison claims report both W2 and persistence landscape L2." | judgment-only | — |
| "Sample counts are cited by reference to `sample_provenance.fitted` … never transcribed from memory." | enforced-by:`stochastic-tests/sample-provenance-ledger*.yaml` (result side) + judgment (prose) | — |
| "PROVISIONAL flags are carried through — a result flagged pending a fix may not be reported as final." | judgment-only | — |
| "A reviewed claim depends on a result a lane audit invalidates — the claim is blocked, not softened." | judgment-only | — |

### tda-statistical-modeling-toolkit
| Quoted assertion | Class | Sketch |
|---|---|---|
| "counts come from a result JSON's `sample_provenance` block by reference, never from memory." | enforced-by:`sample-provenance-ledger*.yaml` (result side) | — |
| "Report effect sizes and uncertainty intervals — a p-value alone is an incomplete result." | judgment-only | — |
| "No causal language unless a causal design … has been explicitly specified and reviewed." | judgment-only | — |
| "If yes [result-bearing], it needs schema / provenance validation and the contract path." | enforced-by:`contract_binding_check.py` Gate 2 (when a contract exists) | — |

### tda-task-brief-from-plan
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Contract authorship stays upstream.** … a needed-but-missing contract is authored before dispatch … never delegated to the implementing agent." | judgment-only | — |
| "'Tests pass' alone is never an acceptance criterion for a lane-touching task — name the enforcement artifact or record why none applies." | judgment-only | — |
| "**Dispatch safety** (mandatory in every brief): bound scope with explicit hard stops … forbid toy/synthetic/illustrative output in `results/`." | enforceable:hook (synthetic-in-results) + judgment (scope stops) | (see pre-reg-to-dispatch synthetic row) |
| "If the brief relies on an inferred property of an external resource … includes a verification step — no speculative foundations." | judgment-only | — |
| "For every assurance lane … record an explicit disposition … do not treat aggregate coverage prose as per-lane closure." | judgment-only | — |

### tda-trajectory-baselines
| Quoted assertion | Class | Sketch |
|---|---|---|
| "**Leakage check (be severe):** does any future information enter a predictor; is a scaler/PCA fitted on the full dataset before a temporal split …?" | judgment-only | — |
| "baseline and PH results use comparable samples — reconcile against `sample_provenance`, and name the stage." | enforced-by:`sample-provenance-ledger*.yaml` (result side) + judgment | — |
| "Store outputs with provenance (date-suffixed, no overwrite, seeds in the result file)." | enforced-by:`results-no-overwrite.sh` (partial) + `output_validation` seed key | — |

### tda-visualisation-and-diagramming
| Quoted assertion | Class | Sketch |
|---|---|---|
| "A `paper_figure` MUST be bound to a script and an input artifact." | enforceable:schema | figure-metadata record with required `script_path` + `input_artifacts`; CI check paper figures regenerate |
| "the visual claim must not exceed the statistic (`W2` and landscape L2 conventions apply to captions too)." | judgment-only | — |
| "date-suffix outputs, never overwrite." | enforced-by:`results-no-overwrite.sh` only for `results/**` (figures under `papers/**/figures` are **not** covered) | extend no-overwrite to figure output paths |
| "pipeline schematics … must match the pipeline as implemented, not as remembered." | judgment-only | — |
| "A figure's input artifact carries a PROVISIONAL flag — the figure carries it too." | judgment-only | — |

### topology-benchmark-review
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Compare against a published benchmark where one exists (e.g. Gidea-Katz 2017) or the project's `validate-topology` benchmark table." | enforced-by:`topology-invariants/*` (mechanical invariants) + judgment (external anchor) | — |
| "W2/landscape distances move in the expected direction for a known perturbation." | enforced-by:`topology-invariants/null-operation-changes-ph-input.yaml` (adjacent) | — |

### using-git-worktrees-extras
| Quoted assertion | Class | Sketch |
|---|---|---|
| "A scoped pass never converts the full baseline to green; report both results." | judgment-only | — |
| "Obtain explicit user approval before adopting a scoped baseline." | judgment-only | — |
| "**Glob/Grep are ignore-blind inside a worktree** … never trust a Glob/Grep absence signal alone inside `.apm/worktrees/`." | judgment-only | — |
| "**Never run two `uv run`/`uv sync` against the same venv concurrently**." | judgment-only | — |
| "Do not bypass a split-root denial with shell/base64 writes, `git apply`, or another editor." | judgment-only | — |
| "the expected ref must resolve to the required commit and `git symbolic-ref --short HEAD` must name that branch." | judgment-only | — |

### validate-topology
| Quoted assertion | Class | Sketch |
|---|---|---|
| "All birth values ≥ 0; All death values > birth; H₀ has exactly one infinite feature; H₀ has L-1 finite features." | enforced-by:`topology-invariants/*` contracts (diagram sanity) | dedicated diagram-sanity invariant if not already bound |
| "Label/cohort shuffle p-values are non-significant (negative control); Markov-2 null generates more total persistence than Markov-1." | enforceable:`output_validation` | invariant/benchmark assertion on the null-battery result JSON |
| "Capture backend stderr/logs and fail on any VTK or topology-pipeline error, even when the process exits successfully." | judgment-only | — |
| "Known benchmarks" table (USoc order-shuffle H₀ p<0.005, GMM bootstrap ARI 0.646±0.086, …) | enforceable:benchmark test | regression test asserting headline results against the pinned table |

### vault-sync
| Quoted assertion | Class | Sketch |
|---|---|---|
| "new entries at the top of the page … reverse-chronological. Read-reconcile-place, never blind-prepend." | judgment-only | — |
| "Do not fabricate numbers — use `[TO FILL]` as placeholder." | judgment-only | — |
| "Only update CONVENTIONS.md for locked decisions, not provisional findings." | judgment-only | — |

### wasserstein-audit
| Quoted assertion | Class | Sketch |
|---|---|---|
| "project convention mandates W₂ as the primary metric." | enforced-by:`notation-guard.sh` (partial: prose `W_1` in `papers/` only) | — |
| "`bottleneck` without alongside Wasserstein \| Sole metric violation" / "`bottleneck_distance(...)` \| Must not be used as sole metric" | **enforceable** — **not** currently enforced (notation-guard ignores `bottleneck`) | extend `notation-guard.sh` (or a code lint) to flag `bottleneck` without a W₂ metric nearby |
| "`wasserstein_distance(a, b)` with no `p=` arg / `gudhi.wasserstein.wasserstein_distance` without `order=2`" | **enforceable** — code lint | ruff/grep rule flagging Wasserstein calls lacking an explicit `p=2`/`order=2` |

### writing-plans-extras
| Quoted assertion | Class | Sketch |
|---|---|---|
| "Trace every obligation to a numbered plan task or a named, justified deferral. Never silently drop a hit …" | judgment-only | — |
| "Preserve owner-review and implementation-approval gates literally." | judgment-only | — |
| "give every required semantic field a typed accepted source. … missing authority requires an owner-gated decision and fail-closed Partial." | judgment-only | — |

---

## Roll-up: highest-value `enforceable` proposals (not built here — SKL-4 builds only the mirror-tree guard)

These recur across skills and would move the most prose off the judgment floor:

1. **Synthetic/toy output in `results/` deny** — a PreToolUse hook (or `forbidden_keys: [synthetic]` output-contract; precedent exists) blocking date-stamped synthetic files in `results/`. Named by `pre-reg-to-dispatch`, `tda-handoff`, `tda-task-brief-from-plan`, `tda-prototype-sandbox`, `tda-agent-safety-guardrails`, `tda-learning-scaffold`.
2. **Extend `notation-guard.sh`** beyond literal `W_1`: flag bare `$W$`, `W_p` without a nearby `p=`, and `bottleneck` without W₂. Named by `notation-check`, `wasserstein-audit`, `tda-domain-modeling`.
3. **Wasserstein code lint** (`p=2`/`order=2` explicit). Named by `wasserstein-audit`.
4. **`metadata.seed` required key** across result `output_validation` schemas. Named by `contract-first-tdd`, `result-provenance-review`, `tda-experiment`, and others.
5. **Draft no-overwrite + banned-token warn** for `papers/**/drafts/**`. Named by `paper-draft`.
6. **Wire `apm_task_prompt_check.py`** into the dispatch gate (`enforceable (gap)`). Named by `pre-reg-to-dispatch`.
7. **Extend no-overwrite to figures** (`papers/**/figures`) and to script-written / `.csv`/`.pkl` result files. Named by `tda-visualisation-and-diagramming`, `result-provenance-review`.

## Coverage

All 61 `SYNC_SKILLS` skills are present as sections above (skills with only advisory/procedural
prose carry an explicit note in lieu of a control row). Enforcement classifications rest on the
directly-read artifacts in the Method table; no contract named by a skill was found missing.
