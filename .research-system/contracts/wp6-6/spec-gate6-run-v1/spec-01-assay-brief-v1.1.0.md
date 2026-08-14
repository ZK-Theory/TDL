---
document_type: ars-spec-assay-brief
alias: SPEC-01
version: 1.1.0
status: proposed_inert
authority_activation: forbidden
supersedes_lineage_file: ars-spec-01-spectral-distance-ph-assay-brief-v1.0.0-2026-07-16.md
supersedes_lineage_sha256: 39ee3e5a44ec9dbe25766e7ecf89b98fbae8eedcace2ae40f9d5a0fb32f43b84
decision_basis: owner_selected_spec_route_for_gate_6
---

# SPEC-01 — Spectral-distance persistent-homology Assay

## Purpose and boundary

Assess whether spectral graph distances could support one falsifiable, non-redundant
synthetic-to-survey research contribution. This is an operator-mediated evidence and
design task. It performs no numerical experiment, reads no survey microdata, writes no
research result, and cannot start SPEC-02.

The historical file named in the lineage metadata is evidence of origin only. This
successor is the governed brief. Runtime identities, reviewer eligibility, grants, and
owner authority must be resolved from real accepted records; this document supplies no
default identity or authority.

## Required evidence questions

The returned evidence must answer or explicitly block each question:

1. What exact geometric or graph object is supplied to Vietoris–Rips persistence?
2. Which primary paper and exact reference-code commit, licence, environment, formulas,
   symmetrisation, eigenvalue handling, and heuristic guard are authoritative?
3. Is the intended contribution a method, application, robustness, or negative result,
   and what closest alternative could make it redundant?
4. What planted-truth synthetic benchmark, sphere negative control, Euclidean baseline,
   frozen configuration, and resource envelope could falsify feasibility?
5. What future survey estimand, feature block, fit population, freeze rule, missingness,
   weighting, attrition, and comparator would make a later empirical claim identifiable?

Primary-paper/code discrepancies affecting the benchmark are blocking evidence, not
permission to choose a convenient convention.

## Assay scorecard and decision

Use `ars://portfolio/assay-scorecard` version `1.0.0` and its accepted Assay-bar
authority. The exact producer relation must be frozen at request and revalidated at
score recording. A caller-built object that merely satisfies the scorecard schema is
not producer evidence.

- Axis 1: topology earns its keep, pass/fail, evaluated first.
- Axis 2: data feasibility, integer 0–3.
- Axis 3: novelty and publishability, integer 0–3.
- Mechanical PROMOTE requires Axis 1 pass, Axes 2+3 at least 4, and neither score zero.
- PARK requires exact remediable gaps and revisit predicates.
- KILL requires a directly verified decisive failure or redundancy.
- Partial cannot be relabelled PROMOTE.

PROMOTE additionally requires: one non-redundant primary claim; a planted noisy-circle
benchmark with sphere control; Euclidean PH baseline; a named future estimand and
representation freeze; disconnected graphs treated as blocked; a decision-complete
SPEC-02 design within two hours, 12 GB memory, 5 GB scratch, and four CPU slots; and no
unresolved primary-paper/code discrepancy. If the machine scorecard cannot express an
additional gate, the human-readable decision must record it and the outcome is PARK.

## Returned evidence

The operator returns an exact-byte evidence bundle bound to the issued brief subject:

- direct-source table with access dates and immutable paper/code references;
- contribution-class and closest-alternative analysis;
- one schema-valid AssayScorecard produced through the sealed producer relation;
- topology, data, novelty, resource, and representation findings;
- limitations, prohibited inferences, unresolved findings, and focused validation;
- a decision-complete SPEC-02 amendment on PROMOTE, otherwise PARK/KILL/Partial rationale.

The return is recorded through the owner-operated session evidence seam. Import or
return recording alone creates neither an accepted scientific result nor a paper claim.
An independent outcome review is required before a promotion proposal.

## Stop rules

Stop on provider API use, provider process or command-line launch by ARS, credential or
OAuth access, survey-data access, numerical outcome inspection, code implementation,
unregistered object writes, fabricated identity or grant, self-review, or automatic
promotion. A reviewed PROMOTE reaches an explicit owner decision and stops. SPEC-02
requires a later, separate, explicit live-run approval.

## Assurance routing

For this materialization package, Output and Provenance are current: exact bytes,
accepted schemas, producer relation, review relation, and restart receipts are checked.
Topology and Paper Claim assurance remain deferred to the operator return and live run.
