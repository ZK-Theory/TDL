---
name: tda-domain-modeling
description: Use when a TDL term is ambiguous or drifting — a paper section uses stale notation, a contract introduces a new concept, a code name conflicts with project vocabulary, a result field names a quantity unclearly, or a new method decision should become a convention.
---

# TDA Domain Modeling

Keep one precise research vocabulary across code, contracts, vault notes,
papers, and agent prompts. This skill is for *sharpening or changing* the
vocabulary, not for merely reading conventions. Symbol-level drift in a draft
is `notation-check`; this skill owns the concept behind the symbol.

## Canonical Terms to Guard

- **Markov order k** — never bare "Markov null"; the memory ladder tests
  k = 1, 2, 3, …
- **W2 (Wasserstein-2)** — the primary diagram metric; W1 is never cited for
  P01 trajectory null-battery results.
- **Persistence landscape L2** — the mandatory complement to W2, not an
  alternative.
- **`pvalue_null_draws` vs `effect_null_pairs`** — the p-value denominator
  versus the diagnostic effect-size pair count; conflating them is the T1.36
  defect class.
- **Fitted vs eligible vs complete-case sample** — always name the stage;
  counts cite `sample_provenance.fitted` by reference.
- **Observed diagram vs null diagram** — and which coordinate frame each
  lives in.
- **Frozen loadings vs re-fit PCA** — a null that re-fits the scaler/PCA per
  draw is testing basis rotation as well as generative difference.
- **External-indexing dedup** (greedy permutation, `ripser(X[I])`) vs ripser
  internal `n_perm` — not interchangeable.
- **L = 5000** — the canonical landmark count; L = 2000 is retired.
- **P01-A applied findings vs P01-B hypothesis-testing framework** — never
  blur; P01-B §4 has a strict scope rule.

## Procedure

1. State the ambiguous or conflicting term and every place it appears
   (code identifier, contract field, prose, result key).
2. Check existing usage: `CONVENTIONS.md`, `papers/shared/notation.md`, the
   relevant contracts, and the code names.
3. Propose ONE canonical term. Record rejected alternatives when the
   distinction they mark matters.
4. Stress-test the term against 2–4 concrete edge cases (a length-matched
   cell, a BHPS-vs-USoc coding difference, a superseded result file).
5. Decide the level: local code comment · glossary entry · paper-notation
   entry · contract term · `CONVENTIONS.md` lock. A pure glossary entry gets
   no implementation detail.
6. Update the right file or draft the patch plan. Notational locks go in
   `papers/shared/notation.md` — never let two papers diverge on the same
   object.

## Completion Checklist

- [ ] Existing usage checked across code, contracts, and prose.
- [ ] One canonical term proposed; rejected alternatives recorded if the
      distinction matters.
- [ ] Edge cases tested.
- [ ] Paper-specific scope checked (does the term mean the same in P01-A,
      P01-B, and P04?).
- [ ] Target documentation level selected and updated (or patch plan drafted).
- [ ] Code / contract / prose renaming implications listed.

## Escalate Or Stop When

- The sharpening would amend a locked convention — that is a User decision
  plus a `[DECISION]` vault entry, never a silent edit.
- Two papers already diverge on the same object — surface before either
  draft advances.

## Related Skills

`notation-check` (symbol drift in drafts) · `wasserstein-audit` ·
`schema-contract-design` (contract terms) · `tda-codebase-design`
(seam naming) · `commit-log` / `vault-sync` (recording the lock) ·
`tda-representation-diagnostics` (when the drifting term is a
representation: frozen vs re-fit, inference vs visualization).
