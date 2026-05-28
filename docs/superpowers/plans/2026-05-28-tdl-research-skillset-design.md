# TDL Research Skillset Design Strategy

> **For agentic workers:** This is a strategic skillset reference, not an implementation checklist. Use it to decide which TDL-specific skills to create next and which checks should instead become hooks, contracts, schemas, or scripts.

**Goal:** Preserve the independent plan for TDL research skills that support mathematical, statistical, topological, representation, provenance, and paper-claim work.

**Architecture:** `research-assurance-triage` is the routing skill. Lane-specific skills provide judgment. Hooks/contracts/schemas enforce repeated deterministic checks. Manager and Worker workflows decide when to invoke skills; this plan decides what skills should exist.

**Tech Stack:** Project-local Codex skills in `.agents/skills`, Superpowers skill-writing guidance, YAML contracts, JSON schemas, Python hooks, result files, cache metadata, vault logs, and paper project notes.

---

## Recovery Note

`docs/` is ignored in this repository. The durable recovery copy is:

`.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`

## Existing Skill Inventory

Coordination and logging:

- `apm-*`
- `apm-communication`
- `commit-log`
- `vault-sync`

TDA and null models:

- `tda-experiment`
- `markov-null-design`
- `validate-topology`
- `wasserstein-audit`
- `tda-figure-spec`

Data and panel work:

- `bhps-wave-crosswalk`
- `new-analysis`
- `phase0-status`

Paper and notation:

- `paper-draft`
- `humanizer`
- `notation-check`
- `paper-repo-extract`

Research assurance core:

- `research-assurance-triage`

## Design Principles

Use skills for judgment-heavy procedures: triage, interpretation, design audits,
claim tracing, and cross-artifact reasoning. Use hooks/contracts/schemas/scripts
for deterministic checks that should produce stable pass/fail results.

Do not duplicate rules across many skills. Keep broad routing in
`research-assurance-triage`, lane judgment in lane skills, and mechanical checks
in tooling.

## Proposed Skill Layers

Layer 0 routing:

- `research-assurance-triage`

Layer 1 high-priority lane skills:

1. `result-provenance-review`
2. `statistical-design-audit`
3. `pre-reg-to-dispatch`
4. `representation-freeze-audit`
5. `paper-claim-trace`

Layer 2 later domain skills:

- `null-operation-invariance-audit`
- `panel-estimand-audit`
- `schema-contract-design`
- `topology-benchmark-review`
- `sensitivity-comparison-review`
- `reproducibility-package-review`

Layer 3 deterministic enforcement:

- `apm_task_prompt_check.py`
- p-value denominator hook
- Markov-order/provenance hook
- result no-overwrite hook
- JSON schema completeness validators
- frozen/provisional representation comparability contracts
- null-operation topology-invariance contracts

## Priority Skill Specs

### `result-provenance-review`

Use when reviewing computational result files, caches, seeds, output paths, date
suffixes, no-overwrite behavior, or vault traceability.

Pressure scenarios: T1.36 invalid p-values from preserved caches; T1.37
frozen/provisional output path distinctions; superseded smoke outputs.

### `statistical-design-audit`

Use when tasks involve p-values, denominators, null-null comparisons, FDR,
bootstrap, confidence intervals, estimands, eligibility rules, GLMM/Firth/svyglm,
MICE, IPW, or bounds.

Pressure scenarios: T1.36 denominator error; future panel tasks changing the
estimand while passing software tests.

### `pre-reg-to-dispatch`

Use when converting pre-registration decisions, amendments, or decision rules
into APM Task Prompt requirements.

Pressure scenarios: T1.2g first13 asymmetric-L rerun requiring amendment before
dispatch; methodology changes disguised as routine reruns.

### `representation-freeze-audit`

Use when tasks touch PCA/UMAP/scaler fitting, frozen loadings, provisional vs
frozen embeddings, GMM labels, state recoding, windows, or comparability across
surrogates/cohorts/eras.

Pressure scenarios: label/cohort shuffles after embedding; T1.37 frozen-loadings
rerun and frozen/provisional comparisons.

### `paper-claim-trace`

Use when turning results into manuscript claims, table entries, figure captions,
discussion prose, limitations, or disclosure text.

Pressure scenarios: T1.2 cascade disclosure; claims awaiting computation;
negative or weaker-than-expected results needing honest prose.

## Creation Sequence

After T1.37 review:

1. `result-provenance-review`
2. `representation-freeze-audit`

Before p-value/statistical follow-up work:

1. `statistical-design-audit`
2. `pre-reg-to-dispatch`

Before manuscript integration:

1. `paper-claim-trace`

After repeated use:

- promote stable checks into hooks/contracts/schemas
- keep skills as the judgment layer around those tools
- update `research-assurance-triage` routing

## Skill Authoring Rules

Follow `skill-creator` and `writing-skills`: concise `SKILL.md`, frontmatter with
trigger-only `description`, pressure scenarios for validation, no extra
README/INSTALL/CHANGELOG files, and project-local placement under
`.agents/skills/<skill-name>/SKILL.md`.
