---
review: Reconciliation of the adversarial first-pass review
date: 2026-06-29
review_commit: 33ab053e30fa5e564ac7cc999544dec2225e9ccb
reviewed_design_commit: bcc3c0739e17869315f8744a50eac32e995dda13
status: approved_for_specification_integration
authority: Stephen
implementation_authority: none
---

# Adversarial Review Reconciliation — 2026-06-29

## 1. Purpose

This record preserves the submitted adversarial review unchanged while stating which findings are accepted, amended, deferred, or corrected before they enter the Agentic Research System specifications. It is the authority bridge between the review and the revised W1, W2, and W6 drafts; it does not authorize runtime implementation or migration.

The overall verdict remains **`accept_with_required_changes`**. The review supports the accepted system direction and identifies bounded changes to concurrency, compatibility, independence, evidence grading, fixture provenance, and transition currency.

## 2. Observation-log reconciliation

The review and the integration pass observed different temporal states of the Task Observer log because observations were actioned between them. Bare observation numbers are therefore not durable evidence identities.

At integration time, the canonical log records Observation 7 as **“Bus writes need explicit ownership, not only read-before-write”**, actioned on 2026-06-28. The P-009, W2, and W6 references to that title remain correct and EF-2 is not applied. References in the review to Observations 12–20 are retained as part of the submitted review's evidence snapshot but are not carried into revised specifications by number. Their underlying lessons must instead cite stable repository evidence, an exact observation title/date, or a commit-anchored source.

Future ARS evidence records must identify Task Observer material by canonical path, exact title, date, and status; a bare ordinal is insufficient.

## 3. Dispositions

| Finding | Disposition | Integration rule |
|---|---|---|
| M-1 / M-2 | Accept; gating | One project-wide command service owns one dedicated linear ledger repository/root outside task-worktree branches. Worktrees submit commands and never allocate canonical positions. |
| M-3 | Accept; strengthen | Successor-owned compatibility files use non-shared namespaced paths. An unmodified legacy Worker implies `legacy_owned`; hooks are defence-in-depth only. |
| M-4 | Accept with clarification | R0/R1 may use delegated Manager acceptance; R2 requires independent verification plus Manager acceptance; R3 and reserved P-005 transitions require Stephen. Solo operation provides graded contextual/model independence, not independent human authorities. |
| M-5 | Accept with amendment | Independence is checked from actor, role, session, model-family, context-manifest, subject-hash, and trace-visibility evidence. The verifier must inspect the subject artefact but must not inherit the implementer's conclusions or hidden reasoning. |
| M-6 | Accept narrowly | Preserve mechanical `RuleEvaluation` versus authorized `Decision`. Add typed referent/estimand/metric/denominator and subject hashes; require a Decision when policy promotes the output into interpretation, prose, amendment, migration, or a claim. W5 owns the broader result-versus-decision policy. |
| M-7 | Accept; immediate | Add the dated W0 currency addendum. A-001 remains pending until T1.28 review and closeout; A-002 remains unresolved. |
| M-8 | Accept | Scientific model graders declare producer and grader family/context relationship. Required cross-family grading fails closed when unavailable. |
| M-9 | Accept | D/T graders may not certify a scientific property from a producer-emitted pass flag. They independently recompute or bound it and exercise the relevant degenerate mutation. |
| M-10 | Accept with clearer taxonomy | F-001 and the overwrite portion of F-002 have a historical incident basis but reconstructed fixture inputs. Fixture provenance records both dimensions. |
| EF-2 | Do not apply | Current Observation 7 title supports the existing citation. Use stable title/date/path references going forward. |
| EF-3 / m-A5 | Accept | Name the practitioner whitepapers and generalize the core portfolio wording. |
| m-B6 / m-B8 / m-B9 | Accept | Add regenerability metadata, verified-snapshot replay, and W8 lease/heartbeat requirements. |
| m-C2/C6 / m-B12 | Accept | Add operational anti-gaming evidence, a non-aggregated P0 gate, and exception-bypass coverage. |
| F-021–F-024 / S-011–S-016 | Reserve | Add IDs and priorities now; materialization follows the named W3–W8 dependencies. |

## 4. Resolved canonical-store architecture

The first release uses a **single project-wide writer**, not a distributed or per-worktree ledger:

1. One local command service owns canonical mutation for one `project_id`.
2. Canonical events, immutable objects, receipts, and accepted manifests live in a dedicated control-store root with a protected linear history. The default durable implementation is a dedicated Git repository or equivalently versioned linear store; it is not a branch or directory independently advanced by task worktrees.
3. The code repository's `.research-system/` directory holds tracked schemas, policies, pack declarations, adapter definitions, eval definitions, and the stable control-store binding. It does not contain independently writable per-worktree event ledgers.
4. Worktrees and provider sessions submit commands through the service endpoint/CLI. They receive receipts and projections; they do not write the control store directly.
5. `global_position` and the global hash chain are retained because allocation occurs under one writer. Ledger history is append-only: no rebase, reset, history rewrite, or event-file revert. Corrections use compensating events.
6. Root binding includes `project_id`, control-store identity, endpoint, canonical path/URI, and expected tail hash/position. Resolution from current working directory is prohibited.
7. Periodic verified snapshots and audit exports support recovery and inspection. A snapshot may become a replay anchor only after its state hash, source position, reducer version, and preceding chain are verified.

This resolution amends P-001, P-002, P-003, and P-006 without adopting per-stream distributed reconciliation.

## 5. Compatibility and authority resolution

- A successor-owned Task never shares a mutable legacy `task.md` or `report.md` slot.
- Namespaced compatibility projections are read-only views for humans or ARS-aware adapters. Legacy tools do not gain successor authority by reading or clearing them.
- If an unmodified APM Worker must receive or return work through legacy bus files, that Task remains `legacy_owned` until explicit cutover.
- R0 uses a minimal command/event/receipt envelope with deterministic checks and no independent review.
- R1 uses delegated operational acceptance where policy permits.
- R2 requires a verifier distinct from the implementer context and Manager acceptance; Stephen is required only when a reserved transition is also involved.
- R3 requires cross-family/cross-context review and Stephen's attributed approval. This reduces correlated error but is not represented as independent human review in a solo programme.

## 6. Evaluation resolution

- Fixture provenance separates `incident_basis` from `input_fidelity`.
- A deterministic grader must establish its assertion from fixture inputs and independent computation, not from the producer's declared result.
- Scientific M-graders record family diversity and context provenance; producer-correlated error examples are mandatory calibration cases.
- P0 failures remain visible as a separate release gate and cannot be obscured by aggregate acceptance percentages.
- Qualitative/non-computational support is scoped honestly: ARS supplies provenance, lifecycle, authority, review, and claim controls, but deterministic scientific validation may be `not_applicable` and human/independent review carries more weight.

## 7. Integration and review boundary

The approved integration sequence is:

1. this reconciliation record and the W0 dated addendum;
2. dated amendments in the decision register;
3. W1 architecture revision;
4. W2 schema/lifecycle revision;
5. W6 catalogue and grader revision;
6. editorial/source-provenance corrections;
7. deterministic cross-document verification and a bounded delta review.

No runtime, schema implementation, migration, pilot, or active APM modification is authorized by this reconciliation.
