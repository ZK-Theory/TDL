# Adversarial WP6.5 W11 remediation R5 review — 2026-07-19

## 1. Review identity

- **Reviewed PR:** #121
- **Exact reviewed subject:** `892d1d1650cdcf71d2a886318e174a18e11d5de0`
- **Branch:** `pipe/ars-wp6-5-w11-spec`
- **Base:** `main`
- **W11 SHA-256:** `3011de88b6826b27bbc105dbf2ce0e2f3fa095666dec082aa0e460be9cca0799`
- **W11 Git blob:** `f90729d0c42a0de98d064fac0824d1969c871c82`
- **Decision-register SHA-256:** `bb57bef4acd2e051873b146389e42aae69f5715884684c4f69b575cd0cb7e922`
- **Decision-register Git blob:** `9eecbb7084fb2c9c840c4f233201d964fe08808b`
- **R4 report commit:** `e68d60f4e9d41fd86495c4259cbc5bc84b77d018`
- **R4 report SHA-256:** `5860ee1c68234411d75270afa698f8e5675b66d7bb5672deab0c67588c4468d9`
- **R4 report Git blob:** `f6c2d1e4d104f0a95bc4bd99e4f01f7bd7a38748`
- **Review boundary:** fresh independent, read-only, exact-head adversarial review. Author reconciliation was treated only as a claim to re-test.

At both entry and exit, local `HEAD`, the local origin-tracking ref, `git ls-remote` for the branch, `git ls-remote` for `refs/pull/121/head`, and GitHub PR #121’s `headRefOid` all equalled the exact reviewed subject. The worktree was clean.

## Additive erratum to immutable R4 evidence

**Appended 2026-07-19 after CodeRabbit exact-head review comment
`PRRC_kwDOQn1MU87XI78K` / `discussion_r3609444106`.** This erratum is outside the
original R5 review epoch and does not broaden or alter the R5 verdict.

The immutable R4 report is identified by commit
`e68d60f4e9d41fd86495c4259cbc5bc84b77d018`, SHA-256
`5860ee1c68234411d75270afa698f8e5675b66d7bb5672deab0c67588c4468d9`, and Git blob
`f6c2d1e4d104f0a95bc4bd99e4f01f7bd7a38748`. R4 line 126’s `OR-034–OR-040`
catalogue-summary shorthand is a typo. The exact six request rows are **OR-034–OR-038
and OR-040**, excluding verdict row OR-039. The R4 report remains unchanged; this
additive erratum does not alter its `rework_required` verdict or either R4 finding.

## 2. Verdict

**`approved`**

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 0 |
| Minor | 0 |

Revision 0.5 closes both R4 findings at specification level without regressing the earlier R1–R3 closures. This review verdict does not accept W11 on Stephen’s behalf, authorize implementation, approve a transition batch, or close either D-G6-4 limb.

## 3. R4 finding disposition

### R4-M1 — Negative or unverifiable review cleared the outcome gate

**Disposition: Closed at specification level.**

Section 4.2.3 now defines one closed policy for exactly six outcome discriminants:

```text
assay_scored
assay_partial
assay_cancelled
spike_verdict
spike_partial
spike_cancelled
```

The independent reconstruction covered all six W2 verdicts, with both conditional-approval branches, across all six subjects: 42 subject/branch combinations.

| W2 verdict/branch | Review projection | Aggregate/Candidate effect | Permitted replacement |
|---|---|---|---|
| `approve` | `satisfied` | Exact row-specific `*Reviewed` events | No unchanged-subject re-review |
| `approve_with_conditions`, all conditions explicitly non-blocking, owned, dated, evidence-bound, and subject-preserving | `satisfied` | Exact `*Reviewed` events; conditions remain audit obligations only | No unchanged-subject re-review |
| `approve_with_conditions` with any blocking, unknown, unowned, undated, or subject-changing condition | `changes_requested` | No aggregate/Candidate event | Superseding subject or bounded delta |
| `changes_requested` | `changes_requested` | No aggregate/Candidate event | Superseding subject or bounded delta |
| `reject` | `verdict_recorded`, unsatisfied | No aggregate/Candidate event | New subject required; same-subject retry forbidden |
| `unable_to_verify` | `verdict_recorded`, unsatisfied | No aggregate/Candidate event | Added evidence/capability in a superseding subject or explicit bounded delta |
| `withdrawn` | `withdrawn` | No aggregate/Candidate event | Same-subject replacement only with exact withdrawn refs/reason and a different eligible reviewer relation |

Every verdict is immutable and updates the W2 Review projection. Only `satisfied` emits the subject-specific Assay, Spike, or Candidate outcome events.

The replacement relation binds the prior request/verdict, prior and new subject hashes, changed evidence or condition-resolution references, reason, reviewer relation, and either `superseding_subject` or `bounded_delta`. A bounded delta also binds the unchanged base and exact accepted delta scope. It is invalid after `reject` without a new subject. Equal old/new subject hashes fail except for the explicit withdrawn-review replacement.

Negative-review progression is closed:

- A negative complete Assay or Spike review creates no `AssayReviewed` or `SpikeReviewed`, so OR-012/OR-026 cannot supply their exact reviewed evidence subject.
- A negative Partial or cancellation review creates no `*_partial_reviewed` or `*_cancelled_reviewed` aggregate/Candidate state, so OR-009/OR-023 cannot satisfy their revisit preconditions.
- A recorded negative verdict changes only Review state. It cannot resolve promotion, propose revisit, open an attempt, or create a replacement aggregate.
- Human authority cannot compensate for the missing policy-satisfied review.

Tests 4, 7, and 11 now explicitly require all verdict branches, conditional-approval ownership, negative/withdrawn replacement, policy-satisfied event production, and promotion/revisit denial.

### R4-m1 — Inconsistent Review projection targets

**Disposition: Closed.**

All six verdict owner rows now have the same projection rule:

| Owner row | Subject | Review effect |
|---|---|---|
| OR-006 | `assay_scored` | Always `U:review → P:review`; Assay effect conditional |
| OR-007 | `assay_partial` | Always `U:review → P:review`; Assay/Candidate effects conditional |
| OR-020 | `spike_verdict` | Always `U:review → P:review`; Spike effect conditional |
| OR-021 | `spike_partial` | Always `U:review → P:review`; Spike/Candidate effects conditional |
| OR-039 | `assay_cancelled` | Always `U:review → P:review`; Assay/Candidate effects conditional |
| OR-041 | `spike_cancelled` | Always `U:review → P:review`; Spike/Candidate effects conditional |

Tests 1, 3, and 11 now include conditional event producers, `P:review`, and every section 4.2.3 verdict branch.

## 4. Earlier finding disposition

| Finding | R5 disposition |
|---|---|
| R3-M1 — cyclic/undefined derived hashes | **Closed.** Relation preimages remain separately enumerated and acyclic; `catalogue_content_hash` remains forbidden. |
| R3-M2 — catalogue bootstrap required prohibited runtime | **Closed.** External exact-byte observation/review/acceptance precedes runtime; OR-140 is only the later verified genesis import. |
| R3-M3 — owner catalogue disagreed with allowlist/projections/tests | **Closed.** Exact W4 joins, Candidate effects, Review effects, receipts, and three per-row test identities reconcile. |
| R3-M4 — cancellation lacked review producers | **Closed.** OR-038–OR-041 provide exact request/verdict producers, and only policy satisfaction clears the route. |
| R3-M5 — Partial/cancel left overlays live | **Closed.** OR-019 closes attempt/lease; OR-022 closes attempt/lease and supersedes a pending OR-015 proposal atomically. |
| R3-M6 — late annotation staled cutover | **Closed.** Accepted epoch re-observation, atomic fence, and successor routing remain intact. |
| R2-M1 — dossier self-addressing | **Closed.** |
| R2-M2 — inventory/mapping cycle | **Closed.** |
| R2-M3 — abstract Assay bar | **Closed.** |
| R2-M4 — incomplete owner catalogue | **Closed.** |
| R2-M5 — cancellation/Partial dead ends | **Closed.** |
| R1 C-1/C-2, M-1–M-6, m-1/m-2 | **Closed at specification level.** No regression found. |

## 5. Owner-catalogue reconstruction

The independent parser found:

- exactly **81** owner rows;
- exact ranges **OR-001–OR-041** and **OR-101–OR-140**;
- no gaps, duplicates, or extra IDs;
- five non-empty normative cells per row;
- 81 command/schema bindings;
- 81 reducer bindings;
- 81 projection target sets;
- **81 unique receipts**;
- **81 unique expanded positive test IDs**;
- **81 unique expanded negative/mutation test IDs**;
- **81 unique expanded retry test IDs**.

The exact expanded conventions remain:

```text
W11-T01-OR-nnn
W11-T03-OR-nnn-owner-row-mutation
W11-T11-OR-nnn
```

The explicit W4 joins remain consistent:

- Scout: OR-001 and OR-029.
- Portfolio Steward: OR-001/002/003/008/009/011/012/014/015/023/025/026/030/034–038/040 and OR-105/107/110/112/114/128.
- Operator/auditor: OR-017/022/028/032/033/116/118/140.
- All other rows retain the exact named profile and grant subject from the owner annex.

The exact six request rows OR-034–OR-038 and OR-040 include exact prior-review
supersession or null. OR-006/007/020/021/039/041 include unconditional Review effects
and policy-conditional aggregate/Candidate effects. No implicit producer, wildcard
subject, blank reducer, missing projection, or aliased test identity was found.

## 6. Review/recovery reachability

### Complete outcomes

```text
score/verdict recorded
  -> exact review request
  -> ReviewVerdictRecorded
     -> satisfied: aggregate Reviewed event -> promotion proposal may be considered
     -> non-satisfying: aggregate unchanged -> only exact replacement review
```

A non-satisfying complete review cannot reach OR-012 or OR-026 because the exact reviewed aggregate event/evidence relation is absent.

### Partial outcomes

```text
Partial + closed attempt/lease where applicable
  -> exact Partial review request
  -> ReviewVerdictRecorded
     -> satisfied: partial_reviewed -> revisit proposal
     -> non-satisfying: Partial unchanged -> replacement review only
```

No branch promotes a Partial outcome or reuses the same aggregate for retry.

### Cancelled outcomes

```text
cancelled + resource/proposal cleanup
  -> exact cancellation review request
  -> ReviewVerdictRecorded
     -> satisfied: cancelled_reviewed -> revisit proposal
     -> non-satisfying: cancelled unchanged -> replacement review only
```

The cancellation/proposal races remain closed:

- OR-015 first, then OR-022: pending proposal is superseded atomically.
- OR-022 first, then OR-015: proposal fails the cancelled state/version.
- OR-016 first, then OR-022: resolved proposal leaves no pending overlay; cancellation from authorized remains valid.
- OR-022 first, then OR-016: stale/superseded resolution fails.
- OR-019 PARTIAL closes its exact attempt and releases its lease before review.
- Retry creates a fresh aggregate and supersedes the old one atomically.

## 7. Hash-DAG and bootstrap re-test

The independent authority oracle retained 40 named nodes and 35 dependencies. It produced a complete topological order with no self-edge, back edge, cycle, or strongly connected component.

The following chains remain constructible:

```text
owner requirement
  -> content
  -> independent file observation
  -> independent review
  -> external Decision/acceptance
  -> later runtime consumer
```

and:

```text
source observation
  -> source-only inventory acceptance
  -> transition-mapping acceptance
  -> transition event
  -> later cutover closure acceptance
  -> cutover
```

The catalogue bootstrap remains external and acyclic:

```text
accepted specification
  -> materialized schemas/catalogue
  -> independent byte observation
  -> independent review
  -> Stephen’s external acceptance envelope
  -> runtime implementation
  -> one-time OR-140 genesis import
```

OR-140 cannot create, amend, review, or accept its own prerequisite. No W11 acceptance was inferred from the previously approved bounded bootstrap policy.

## 8. Annotation and path controls

The annotation-epoch remediation remains intact:

1. The closure binds the exact legacy epoch, directory identity, writer-grant position, members, ingestion/rejection references, and empty pending-set hash.
2. Cutover re-enumerates the epoch under the registered directory and registry locks.
3. A pre-fence delta rejects before publication.
4. The atomic transaction revokes old grants, fences the old epoch, activates the successor epoch, completes cutover, and revises path registration.
5. Locks remain held through commit.
6. Post-fence annotations resolve only to the successor epoch.

Physical writer separation, handle/file-identity checks, no-follow traversal, hardlink/reparse detection, parent locking, atomic replace, and race-injection requirements were not weakened.

## 9. Decision and gate audit

| Decision/gate | R5 disposition |
|---|---|
| P-004/P-021 | Keep. Exclusive ownership and disjoint physical writers remain exact. |
| P-005/P-022 | Keep. Review satisfaction is now distinct from verdict recording, and human authority remains non-compensable. |
| P-026 | Keep. The reviewed subject is specification-only. |
| P-032 | Keep. The exact revision is now independently reviewable with no open finding. |
| P-034 | Keep. Transition and cutover remain acyclic, one-way, and epoch-fenced. |
| P-036 | Keep unchanged. It accepts the WP6 launch basis, not W11. |
| D-G6-4 bounded bootstrap/epoch policies | Previously recorded as accepted; no broader authority inferred. |
| D-G6-4 limb 1 | **Open pending Stephen’s exact-revision decision.** R5 supplies the required no-finding independent review but does not exercise acceptance authority. |
| D-G6-4 limb 2 | **Open.** No first ownership-transition batch is approved or inferred. |
| W11-A1 | Open/optional; omission remains conforming. |

## 10. Complete invariant disposition

| Invariant | R5 disposition |
|---|---|
| W11-I01 | Pass at specification level |
| W11-I02 | Pass |
| W11-I03 | Pass |
| W11-I04 | Pass; R4-M1 closed |
| W11-I05 | Pass |
| W11-I06 | Pass; R4-M1 and resource-cleanup paths closed |
| W11-I07 | Pass; policy-satisfied review is required before promotion/revisit |
| W11-I08 | Pass |
| W11-I09 | Pass |
| W11-I10 | Pass |
| W11-I11 | Pass |
| W11-I12 | Pass; all 81 rows and Review projections reconcile |
| W11-I13 | Pass |
| W11-I14 | Pass at design level; unavailable future Windows coverage remains Partial |
| W11-I15 | Pass |
| W11-I16 | Pass |
| W11-I17 | Pass |
| W11-I18 | Pass |
| W11-I19 | Pass |
| W11-I20 | Pass |
| W11-I21 | Pass |
| W11-I22 | Pass |

## 11. Complete pre-implementation test-family disposition

| Test | R5 disposition |
|---:|---|
| 1 | Pass as specified |
| 2 | Pass as specified |
| 3 | Pass as specified |
| 4 | Pass; all outcome verdict and replacement branches are explicit |
| 5 | Pass |
| 6 | Pass |
| 7 | Pass; satisfaction, negative review, cleanup, and reachability are explicit |
| 8 | Pass |
| 9 | Pass |
| 10 | Pass |
| 11 | Pass; all owner rows, `P:review`, and conditional effects are joined |
| 12 | Pass |
| 13 | Pass at design level |
| 14 | Pass at design level; unavailable required Windows coverage remains Partial |
| 15 | Pass |
| 16 | Pass |
| 17 | Pass |
| 18 | Pass |
| 19 | Pass |
| 20 | Pass |

## 12. Mechanical validation evidence

- `python -B .claude/hooks/contract_binding_check.py --validate-only`
  - Passed all gates against **101 contracts**.
- `python -B .claude/hooks/contract_binding_check.py --no-pytest`
  - Passed all gates against **101 contracts**.
- `git diff --check`: passed.
- Owner rows: 81, exact ranges and unique.
- Invariants: 22, exact `W11-I01`–`W11-I22`.
- Test families: 20, exact sequence 1–20.
- Review-verdict subject/branch combinations: 42, all explicitly dispositioned.
- Review verdict rows: all six contain unconditional `U:review → P:review` and conditional aggregate/Candidate effects.
- Markdown tables: no width mismatches.
- Code fences: 22 delimiters, balanced.
- Local Markdown links: no missing targets.
- R4 and earlier historical review evidence remains unchanged.
- Remediation commit changed only W11 and the W11 status entry in the decision register.
- Worktree remained clean.

## 13. External check evidence

At the R5 review epoch, at the exact reviewed head:

- PR #121 was open, draft, and mergeable.
- Codacy Static Code Analysis completed successfully.
- CodeRabbit’s successful status then observed represented “Review skipped: draft pull request”; it was not treated as substantive review evidence and was not retriggered.
- The later substantive CodeRabbit review is outside the R5 review epoch and is the
  source of the additive erratum above.

## 14. Residual risks

- Future reducers must implement the owner rows’ conditional event batches exactly; a generated handler must not flatten “always Review, conditional aggregate” into unconditional outcome events.
- Materialized tests must exercise all 42 outcome subject/verdict branches, including condition ownership and replacement-mode mutations.
- Future schema/catalogue construction must preserve independent expected/observed producers and the external genesis envelope.
- Required Windows race coverage that cannot execute on the target platform remains Partial rather than pass.
- The living legacy backlog remains mutable and requires fresh exact-byte observation for migration.
- W9/W10 and implementation specifications remain downstream and cannot narrow ownership, path, review, or gate controls.
- Interface conformance does not establish scientific adequacy, result acceptance, or claim authority.

## 15. Review action boundary

This review made no file changes, commits, branch changes, pushes, PR comments, thread resolutions, CodeRabbit triggers, merges, acceptance decisions, schema/runtime mutations, admissions, ownership transitions, cutovers, PR #124 actions, or claim actions.
