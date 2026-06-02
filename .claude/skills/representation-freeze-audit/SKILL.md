---
name: representation-freeze-audit
description: Use when a TDL task touches PCA/UMAP/scaler fitting, frozen loadings, provisional vs frozen embeddings, GMM labels, state recoding, trajectory windows, or comparability of embeddings across cohorts/eras/surrogates.
---

# Representation Freeze Audit

Use this for the Representation assurance lane. The embedding is the metric space
persistent homology runs on, so an error in how it is fit, frozen, or applied
silently corrupts every downstream topological claim. The signature bug: a null
operation that permutes *already-embedded* rows, leaving the persistence diagram
invariant to the very operation the null is meant to test.

## Checklist

1. **Frozen before comparison.** The embedding (loadings, scaler, GMM, recoding)
   was frozen *before* any null draw or cross-group comparison. A representation
   re-fit per null draw or per group is not comparable.
2. **Fit on reference, transform elsewhere.** Loadings and scaler are fit on the
   designated reference data and applied transform-only (no re-fit) to all other
   cohorts/eras/surrogates.
3. **Null operates pre-embedding.** Label/cohort/order shuffles are applied to the
   raw inputs *before* embedding, so the embedding — and therefore the PH — changes
   under the null. Permuting embedded rows is the invariance bug; reject it.
4. **Frozen vs provisional paths distinct.** Frozen and provisional embeddings
   write to distinct, clearly named output paths; a provisional embedding is never
   read as the frozen reference.
5. **Cross-group comparability.** Any comparison across cohorts/eras/surrogates
   uses the *same* frozen loadings; differences must come from the data, not from
   a refit transform.
6. **Recoding/windows consistent.** State recoding and trajectory-window
   definitions are identical across the objects being compared.

## Output Format

Report **PASS / FAIL** per checklist item with the code location (fit call,
transform call, shuffle site). For any FAIL, state whether it invalidates the
downstream topological result (e.g. a pre-embedding-shuffle violation invalidates
the null) or only threatens comparability.

## Escalate Or Stop When

- A null operation acts on embedded rows (PH invariant to the null).
- A representation is re-fit per group or per draw where it should be frozen.
- A provisional embedding is being consumed as the frozen reference.

## Pressure Scenarios From This Repo

- Label/cohort shuffles permuted already-embedded rows, making persistent homology
  invariant to the null operation — the test could not reject anything.
- T1.37 frozen-loadings rerun: the frozen vs provisional distinction had to be
  preserved end-to-end or the comparison would mix incomparable embeddings.

## Related Skills & Contracts

- Pairs with `null-operation-invariance-audit` (the dedicated check that the null
  perturbs the PH input) and `tda-experiment`.
- Enforcing contracts: `frozen-loadings-null-threading`,
  `frozen-loadings-transform-only`, `null-operation-changes-ph-input`.
