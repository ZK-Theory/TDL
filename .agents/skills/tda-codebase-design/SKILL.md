---
name: tda-codebase-design
description: Use when adding or refactoring a TDL pipeline module — embedding, null generation, PH computation, diagram distance, permutation testing, result serialization, provenance validation, plotting, or CLI orchestration — and the module boundary or interface is in question.
---

# TDA Codebase Design

Design pipeline modules as deep modules — substantial behaviour behind a small
interface — organised around clean *scientific seams*. Not for prose editing,
literature work, or note cleanup.

## An Interface Is More Than a Signature

A seam's interface includes: parameters · invariants · ordering constraints ·
assumptions (metric space, embedding stage, frozen-loadings status) ·
randomness and seed handling · error modes (fail fast — never silently
truncate, coerce, or drop) · performance characteristics · provenance fields
emitted · output schema · contract binding point. If callers must know an
unstated assumption to use the module safely, the interface is wrong.

## Seam Vocabulary

`trajectory_loader` · `sample_manifest` · `embedding_transform` ·
`frozen_loadings` · `null_generator` · `diagram_computer` ·
`diagram_distance` · `permutation_test` · `landmark_selector` ·
`result_writer` · `provenance_validator` · `contract_binding`

Name new modules against this vocabulary. A module that spans two seams is
usually two modules.

## Procedure

1. Identify the pipeline step, its current callers, and the downstream result
   consumers (including committed result JSONs).
2. Define the scientific seam and its full interface (list above).
3. Deep or shallow? A pass-through adapter with a single implementation is
   noise — fold it in.
4. Find duplicated logic across scripts — duplication across battery scripts
   is the recurring pattern here; consolidate at the seam, not with a leaky
   helper.
5. Define the test surface: tests cross the same seam the callers cross.
6. Define the contract surface: which invariants deserve a formula / schema /
   invariant / output_validation contract.
7. State the migration plan and backward-compatibility requirements for
   existing result artifacts.
8. Flag paper-result risks: any change that could alter a committed result's
   value gets a rerun plan and a vault `[DECISION]` — never a silent change.

## Completion Checklist

- [ ] Seam named against the vocabulary.
- [ ] Interface includes invariants, error modes, seeds, and performance —
      not just the signature.
- [ ] Output schema and provenance implications identified.
- [ ] Randomness and seeds specified where relevant.
- [ ] Tests cross the caller seam.
- [ ] Contract binding location identified where needed.
- [ ] No single-implementation adapter introduced.
- [ ] Paper-result risk flagged with a rerun plan where applicable.

## Escalate Or Stop When

- A refactor would change the numbers in a committed result file.
- The proposed seam conflicts with a locked convention (metric order,
  landmark count, dedup strategy) — that is a `[DECISION]`-level question.

## Related Skills

`tda-domain-modeling` (the vocabulary the seams are named in) ·
`contract-first-tdd` (implementing across the seam) ·
`schema-contract-design` (the contract surface) ·
`tda-diagnosing-computational-defects` (when a missing seam blocks a
regression test).
