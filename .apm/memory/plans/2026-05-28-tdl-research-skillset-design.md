# TDL Research Skillset Design Strategy

Date: 2026-05-28

This file preserves the strategic plan for TDL-specific research skills,
independent of APM Manager/Worker routing. It is the skillset-design companion
to:

- `.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`
- `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`

## Purpose

The TDL skillset should make agents better at mathematical and empirical
research work, not merely better at software engineering. Skills should encode
judgment-heavy research procedures; deterministic and repeated mechanical checks
should become contracts, schemas, hooks, or scripts.

## Recovered Design Context

- Superpowers is strongly opinionated toward software design. TDL needs an
  additional research-assurance layer for mathematical, statistical,
  topological, representation, provenance, and paper-claim work.
- `research-assurance-triage` is the routing/checklist skill that connects APM
  Manager and Worker workflows to domain-specific research checks.
- Existing TDL skills already cover substantial ground: Markov null design,
  topology validation, Wasserstein notation/order audits, TDA experiment
  scaffolding, BHPS/USoc coding, notation checks, paper drafting, prose
  humanizing, vault sync, paper repo extraction, and commit/vault logging.
- Gaps surfaced earlier in this chat include T1.36 p-value denominator errors,
  T1.2g pre-reg amendment needs, label/cohort shuffle invariance after
  embedding, LM sensitivity schema truncation, and the need to preserve
  provisional/superseded result state.

## Skill Design Principles

Use a skill when:

- judgment is required
- the same research reasoning recurs across tasks
- the procedure depends on context that a regex cannot know
- the output is a review, triage, interpretation, or decision
- the task spans code, results, paper prose, and vault conventions

Use a hook, contract, schema, or script when:

- the check is deterministic
- the same field/path/formula can be validated mechanically
- failure should block commit or task acceptance
- a command can produce a stable pass/fail result

Do not duplicate the same rule in many skills. Put broad routing in
`research-assurance-triage`, lane-specific judgment in lane skills, and
deterministic checks in tooling.

## Existing Skill Inventory

### Coordination And Logging

- `apm-*` skills: APM planner, manager, worker, task/report checks, handoffs,
  recovery, summaries.
- `apm-communication`: bus and message discipline.
- `commit-log`: commit messages and matching research/vault summaries.
- `vault-sync`: routes results, decisions, negatives, pipeline changes, data
  changes, and paper updates into the Obsidian vault.

### TDA And Null Models

- `tda-experiment`: experiment scaffolding, result metadata, output JSON
  conventions.
- `markov-null-design`: Markov memory ladder, explicit `markov_order`, null
  scaffold, logging reminders.
- `validate-topology`: persistence diagram sanity, total persistence scaling,
  Wasserstein checks, known P01 benchmarks.
- `wasserstein-audit`: W1/W2 and order ambiguity across code and manuscripts.
- `tda-figure-spec`: publication-ready figure conventions.

### Data And Panel Work

- `bhps-wave-crosswalk`: BHPS/Understanding Society coding differences and
  harmonisation risk checks.
- `new-analysis`: scaffolding new TDL/trajectory TDA analyses.
- `phase0-status`: read-only project status dashboard.

### Paper And Notation Work

- `paper-draft`: paper draft creation/update workflow.
- `humanizer`: academic prose revision and AI-writing-tell removal.
- `notation-check`: manuscript notation drift and cross-paper leakage.
- `paper-repo-extract`: reproducibility repository extraction.

### Research Assurance Core

- `research-assurance-triage`: lane classification, Manager dispatch/review,
  Worker evidence expectations, and stop conditions.

## Proposed Skill Layers

### Layer 0: Routing Skill

Existing:

- `research-assurance-triage`

Role:

- classify lanes
- decide machine-checkable vs human-review-only
- decide whether pre-reg amendment, contract/schema, vault lock, or follow-up is
  needed

Do not overload this skill with detailed p-value, topology, representation, or
paper-claim procedures. It should route to those skills.

### Layer 1: High-Priority Lane Skills

Create next:

1. `result-provenance-review`
2. `statistical-design-audit`
3. `pre-reg-to-dispatch`
4. `representation-freeze-audit`
5. `paper-claim-trace`

These should be skills first because they require judgment and will help shape
which hooks/contracts are worth writing.

### Layer 2: Later Domain Skills

Create after T1.37 or when repeated need appears:

- `null-operation-invariance-audit`
- `panel-estimand-audit`
- `schema-contract-design`
- `topology-benchmark-review`
- `sensitivity-comparison-review`
- `reproducibility-package-review`

Some may collapse into Layer 1 skills after live use clarifies boundaries.

### Layer 3: Deterministic Enforcement

Build after the skill-guided review exposes repeated gaps:

- `apm_task_prompt_check.py`
- p-value denominator hook
- Markov-order/provenance hook
- result no-overwrite hook
- JSON schema completeness validators
- frozen/provisional representation comparability contracts
- null-operation topology-invariance contracts

## Priority Skill Specs

### `result-provenance-review`

Use when reviewing or reporting computational results, caches, seeds, output
paths, date suffixes, no-overwrite behavior, or vault traceability.

Core questions:

- Which result files were created or modified?
- Which caches were read or written?
- Are seed, B, L, null model, Markov order, and sample restrictions recorded?
- Were any superseded results preserved and labelled?
- Are result paths, cache paths, and schema versions explicit?
- Was the vault updated when required?

Pressure scenarios:

- T1.36 invalid p-values from preserved null caches.
- T1.37 frozen/provisional output path distinctions.
- Superseded smoke outputs that must not be merged into claims.

Likely future tooling:

- no-overwrite hook
- result metadata schema
- cache provenance validator

### `statistical-design-audit`

Use when tasks involve p-values, denominators, null-null comparisons, FDR,
bootstrap, confidence intervals, estimands, eligibility rules, GLMM/Firth/svyglm,
MICE, IPW, or bounds.

Core questions:

- What is the estimand?
- What is the denominator or reference distribution?
- Is the Monte Carlo p-value formula correct for the design?
- Are FDR families and correction methods explicit?
- Are sample restrictions and missingness rules explicit?
- Does code reality match the pre-reg decision rule?

Pressure scenarios:

- T1.36 denominator used diagnostic null-null cap instead of intended
  permutation count.
- Future panel tasks may pass code tests while changing the estimand.

Likely future tooling:

- p-value denominator check
- explicit FDR family metadata check
- sample restriction provenance check

### `pre-reg-to-dispatch`

Use when converting pre-registration decisions, amendments, or decision rules
into APM Task Prompt requirements.

Core questions:

- What existing pre-reg rule governs this task?
- Is the task routine execution or methodology-changing?
- Are parameters explicit enough to dispatch?
- Is a pre-reg amendment required before running?
- What would count as Partial, Failed, or Success?
- How should outcomes map to paper prose?

Pressure scenarios:

- T1.2g first13 asymmetric-L rerun requires an amendment before revival.
- Methodology changes that look like routine reruns.

Likely future tooling:

- prompt checklist hook for missing pre-reg/decision-rule fields

### `representation-freeze-audit`

Use when tasks touch PCA/UMAP/scaler fitting, frozen loadings, provisional vs
frozen embeddings, GMM labels, state recoding, windows, or comparability across
surrogates/cohorts/eras.

Core questions:

- Which representation was fit, frozen, or reused?
- Were surrogates embedded under the correct frozen/provisional regime?
- Are labels, cohorts, and windows comparable?
- Could the null operation be invisible after embedding?
- Are output names explicit about frozen/provisional status?

Pressure scenarios:

- Label/cohort shuffles permuting already-embedded rows, making PH invariant.
- T1.37 frozen-loadings rerun and frozen/provisional comparison JSONs.

Likely future tooling:

- frozen/provisional metadata schema
- representation comparability contract

### `paper-claim-trace`

Use when turning results into manuscript claims, table entries, figure captions,
discussion prose, limitations, or disclosure text.

Core questions:

- Which result file supports each claim?
- Which decision rule maps result to prose?
- Does the result support the strength of the claim?
- Are superseded or provisional results excluded from claims?
- Are limitations/disclosures required?
- Are vault and project notes updated?

Pressure scenarios:

- T1.2 cascade disclosure paragraph.
- Paper-facing claims awaiting computation.
- Negative or weaker-than-expected results that still need honest prose.

Likely future tooling:

- claim-to-result table template
- paper result manifest schema

## Skill Creation Sequence

### Phase 1: After T1.37 Review

Create only the skills that T1.37 proves are immediately useful.

Likely first two:

1. `result-provenance-review`
2. `representation-freeze-audit`

Reason:

- T1.37 directly stresses frozen/provisional representation and output
  provenance.
- These skills will clarify which schema/hook checks should exist.

### Phase 2: Before P-Value Or Statistical Follow-Up Work

Create:

1. `statistical-design-audit`
2. `pre-reg-to-dispatch`

Reason:

- T1.36/T1.2 risks are statistical/pre-reg failures, not generic software
  failures.
- These should precede hook work on p-value denominators.

### Phase 3: Before Manuscript Integration

Create:

1. `paper-claim-trace`

Reason:

- Claim trace is primarily judgment-heavy.
- It should integrate with `paper-draft`, `humanizer`, `notation-check`, and
  `vault-sync`.

### Phase 4: Promote Repeated Checks Into Tooling

After skills stabilize through live use:

- write hooks/contracts/schemas for repeated mechanical checks
- keep skills as the judgment layer around those tools
- update `research-assurance-triage` to route to the new skills

## Skill Authoring Rules

Follow `skill-creator` and `writing-skills`:

- Frontmatter must include `name` and `description`.
- Description starts with "Use when..." and states triggering conditions only.
- Keep SKILL.md concise; move heavy references to `references/` only if needed.
- Use pressure scenarios before or during creation to expose failure modes.
- Do not create extra README/INSTALL/CHANGELOG files.
- Prefer project-local skills in `.agents/skills/<skill-name>/SKILL.md`.

## Relationship To Manager And Worker Workflows

- Manager workflow decides when a skill should be invoked for dispatch/review.
- Worker workflow decides when a skill should be invoked for execution/evidence.
- Skillset design decides what skills exist and what should instead be tooling.
- Hooks/contracts should follow repeated gaps discovered by Manager/Worker use,
  especially during the T1.37 trial.
