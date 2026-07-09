---
name: tda-diagnosing-computational-defects
description: Use when a TDL result changes unexpectedly, a null model gives suspicious p-values, a permutation test looks inconsistent, a result JSON is schema-valid but semantically wrong, stochastic compute behaves non-deterministically, a fitted sample drifts, performance regresses, or a reviewer/CodeRabbit comment points at a real computational defect.
---

# Diagnosing Computational Defects

Use this for defects where outputs are mathematically wrong, statistically
invalid, silently truncated, provenance-incomplete, or inconsistent with a
contract — the class of bug that passes every software test. Not for ordinary
refactoring without a bug, not for contract authoring (`schema-contract-design`,
authored upstream), and not for exploratory analysis with no current defect claim.

## Core Rule

**No defect is closed merely because a test passes.** If the defect touches a
mathematical, statistical, null-model, representation, provenance, or paper-claim
lane, closure requires either binding to an existing contract (or updating one)
or an explicit note saying why no deterministic contract applies. This is the
locked Research Assurance rule in `CONVENTIONS.md`.

## Procedure

1. State the exact symptom: the wrong value, the file it lives in, the command
   that produced it.
2. Classify the defect lane — Topology, Stochastic/Null Model, Statistical/Panel,
   Representation, Output/Provenance, Paper Claim, or ordinary software — via
   `research-assurance-triage`.
3. Build **one red-capable command** that exercises the exact defect path:
   `pytest <specific_test>`, a repro script with a pinned fixture, a contract
   validation command, or a deterministic result-diff. "A test that runs" is not
   red-capable unless it fails on the defect.
4. Minimise to the smallest dataset, fixture, contract, or JSON artifact that
   still fails.
5. Write 3–5 falsifiable hypotheses, ranked by prior probability.
6. Instrument only at discriminating seams — points where hypotheses diverge.
7. Fix only after reproduction.
8. Add or update a regression test, or document why no valid test seam exists
   (then route the seam problem to `tda-codebase-design`).
9. Re-run the original command AND the relevant contract binding check.
10. Post-mortem: cause, prevention, contract impact, provenance impact,
    paper-claim impact. Result-bearing defects get a vault entry.

## Known TDL Failure Classes (check these first)

- Monte Carlo p-value with the wrong denominator — diagnostic pair cap used
  instead of null draws; the formula is `p = (r + 1) / (n + 1)` with
  `n = min(B, total_pairs)`.
- W1/W2 order or notation drift between code, stored results, and prose.
- ripser internal `n_perm` greedy permutation used where the contract specifies
  external-indexing dedup (`compute_greedy_dedup_count` + `ripser(X[I])`).
- Row-order-invariant "label shuffle" nulls — PH is row-order invariant, so
  shuffling rows of an already-computed embedding tests nothing; shuffle labels
  BEFORE embedding.
- Re-fit PCA/scaler where frozen loadings are required — observed and null
  diagrams end up in independently-fit coordinate frames.
- Fitted-sample count drift across stages — "two deterministic scripts disagree"
  is almost always a stage-of-measurement mismatch; reconcile against
  `sample_provenance.fitted`.
- Result JSON passing key-presence checks while values/types are wrong
  (`level: {}` instead of `null`; "any positive n" instead of the pinned count).
- A self-description field naming one object while the payload was computed on
  another (`use_stability` declared vs computed) — needs a relational check.
- Silent truncation: `zip()` on unequal lengths, `.SD[1:2]` group truncation,
  a missing lookup propagating `NA` into a gate, `{}` serialised for null.
- Cross-version pickle loads silently collapsing labels — load `gmm_labels`
  from `05_analysis.json`, never from a pickle.

## Completion Checklist

- [ ] Defect lane classified.
- [ ] One red-capable command recorded and seen failing.
- [ ] Minimal failing fixture or artifact identified.
- [ ] 3–5 falsifiable hypotheses recorded before instrumenting.
- [ ] Fix implemented only after reproduction.
- [ ] Regression test added, or the missing seam documented and routed.
- [ ] Contract binding or validation command run (or explicit N/A note).
- [ ] Sample-provenance and paper-claim impact checked.
- [ ] Post-mortem / vault entry written if result-bearing.

## Escalate Or Stop When

- Reproduction needs data or a checkpoint that is absent and cannot be
  regenerated from a committed script.
- The defect implicates an archived result JSON — never silently correct it;
  record a new date-suffixed file plus a vault entry marking supersession.
- The fix would change an estimand, a null design, or a headline claim —
  surface as a User decision before proceeding.

## Related Skills

`research-assurance-triage` (lane routing) · `statistical-design-audit` ·
`null-operation-invariance-audit` · `representation-freeze-audit` ·
`result-provenance-review` · `contract-first-tdd` (the regression fix) ·
`tda-statistical-analysis-review` (if inference changed) · `tda-handoff`
(if unresolved at session end).
