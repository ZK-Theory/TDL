# 06q — Gate 6 SPEC Real-Run Integration and Follow-Up

**Date:** 2026-08-16

**Status:** `PROVEN / integration_pending`

**Repository subject:** draft PR
[#258](https://github.com/ZK-Theory/TDL/pull/258), branch
`codex/gate6-spec01-spec02-real-run`, head
`c51b96d1db34e46e4798d3589c7e2cf62015db40` at creation.

**Jira:** KAN-103 under KAN-12.

**Current integration note (2026-08-21):** PR #258 reached exact head
`bb9ab7a0f679ba71d2a364410f69ec53673c2ae2` after repeated review remediation,
but review has not converged. The bounded subordinate execution plan is
[06r — Gate 6 PR #258 review convergence](06r-gate6-pr258-review-convergence-plan.md).
06q remains the master integration and follow-up authority.

## 1. Purpose

This plan replaces stale construction-era “missing dossier”, “SPEC-02 unrun”,
and SCALE-only status as the current Gate 6 execution control. It does not
rewrite the accepted historical plans or reviews that led here.

The observable capability is now real: the public ARS route admitted the SPEC
authority, carried a genuine research subject through SPEC-01, ran an
owner-approved SPEC-02 methods spike, recorded independent reviews and owner
decisions, corrected a source error append-only, and released its attempt,
lease, and resources.

The immediate objective is to integrate that assembled candidate without
mixing unrelated follow-on work into PR #258.

## 2. Current evidence

The live public status is:

```text
PROVEN / spec_02_owner_decided / next_action=null
```

The live ledger closes the run at position 444, `ResourcesReleased`, event
hash `ff738e0e548eb556faf520e72cce56c8acb1599ffab6a584ecea5ea6deb349da`.
The candidate, assay, spike, and completed attempt are:

- `obj_01a00620-0f74-7613-a7b0-dffbb50d9663`;
- `asy_01a00620-0f74-74e6-b440-f760f4eb6731`;
- `spk_9fc9324c-8f28-7066-89bb-d4f708ef7d44`;
- `att_c7cf1966-93a1-7114-9b00-61df0d7b94ca`.

SPEC-02 executed 126 frozen configurations and 42 deterministic reruns. All
six spectral configurations passed and the repeated whole-run output was
byte-identical. The complete human-readable evidence register is
[the result handoff](../handoffs/01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md).

## 3. Research disposition

The run was a suitability assessment for an ongoing research project, not an
attempt to create a scientific claim. Its terminal `PARK` decision means:

- retain the spectral persistent-homology method as an experimental or
  benchmark candidate;
- do not yet adopt it as the default empirical method;
- do not infer empirical validity from a synthetic-only spike; and
- do not publish a scientific claim from this run.

The paper's `neurips2024` source is a valid lightweight Git tag at commit
`145efcde673f1a1897eff250b77221d26c34c479`. The correction is durable. The
generic locator still needs to understand branches, tags, and direct commits
before declaring a source absent.

## 4. Integration job — KAN-103 / PR #258

### Observable outcome

The exact reviewed PR head merges into `main`; the merged tree retains the
public SPEC route and result record; merged-state status and required currency
controls pass; Jira no longer describes Gate 6 as lacking a real dossier or
run.

### Required evidence

1. exact PR head and base identities;
2. review conclusions for that exact head;
3. remediation only for findings still valid at the current head;
4. passing required GitHub checks;
5. merged commit/tree read-back;
6. post-merge public status and replay read-back; and
7. KAN-103/KAN-12 descriptions, labels, links, and status read back after the
   merge decision.

### Stop conditions

- Do not merge on a stale review subject.
- Do not describe a draft or passing candidate as `INTEGRATED`.
- Do not amend live evidence to make a PR easier to merge.
- Do not add the residual jobs below to PR #258 unless review finds a direct
  regression in the changed capability.
- Do not continue specimen-by-specimen remediation after a repeated finding
  identifies an unclosed action or transaction family. Apply the 06r
  convergence contract and stop-loss rule before another external review.

## 5. Bounded follow-on jobs

| Job | Why it remains | Closure evidence |
| --- | --- | --- |
| Evidence archive and restoration | The live control store is durable, but no independent backup/archive of the final result set has been verified. | Hash-complete archive, restore into an isolated root, and byte/replay equality. |
| Semantic Git source locator | The run initially misclassified a valid tag-backed paper link as an absent branch. | Resolver accepts branch, tag, and direct-commit locators; absence requires an exhaustive bounded check; regression covers the `neurips2024` tag. |
| Upstream-wrapper equivalence | The bounded spike used a stable-index local kNN wrapper because upstream `vis_utils` packaging was unavailable. | Owner decision to retain or replace; if replaced, frozen comparison against the upstream construction. |
| Empirical design freeze | Synthetic success is not an estimand or representation choice for the real project. | Frozen estimand, representation, data-access route, non-redundant question, and review authority. |
| Auxiliary task projection | Task `tsk_60c5549e-d11f-7d17-8145-d80e144aa537` remains `in_progress` after attempt completion and lease/resource release. | Replay/projection repair with no history rewrite and a live regression. |
| Human-readable result view | The operator had to reconstruct the judgement from technical records. | Public command or generated view stating question, work, evidence, decision, limitations, and next use in plain language. |

Each row becomes a named Jira job with one owner and next action after PR #258
is integrated. The empirical-design row may remain parked until there is a
real research question; it is not forced merely to close infrastructure work.

## 6. Gate 7 consequence

The real run supplies Gate 6 evidence. It does not automatically open Gate 7.
PARK is not pilot promotion, claim promotion, migration authority, writer
cutover, or retirement authority. After PR #258 integrates, the Gate-7
sequencing document may proceed through its authoring/review path, but opening
still requires its separate recorded decision and current prerequisite
read-back.

## 7. Completion rule

The Gate 6 implementation capability becomes `INTEGRATED` only after PR #258
is merged and the merged public path is reverified. KAN-103 may then close if
the follow-on jobs are explicitly created or assigned outside its scope.
KAN-12 remains open until the programme-level downstream work is visibly owned
and its own closure contract is met.
