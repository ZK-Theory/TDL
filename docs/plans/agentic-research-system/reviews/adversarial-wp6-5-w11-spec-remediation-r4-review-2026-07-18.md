# Adversarial WP6.5 W11 remediation R4 review — 2026-07-18

## 1. Review identity

- **Reviewed PR:** #121
- **Exact reviewed subject:** `4b941326e290582db7be07113d5d7bb78d8b97a3`
- **Branch:** `pipe/ars-wp6-5-w11-spec`
- **Base:** `main`
- **W11 SHA-256:** `4a91f53ff102131a9580a0730ad423eec31249ee4bd04b715f5aeee95995712c`
- **W11 Git blob:** `db781ee046be07ffabfc0553a00bec62bf2a7917`
- **Decision-register SHA-256:** `3248288254c3029ac4a6cfb1b5a5668962d6363529470735e2aa62e152735d8f`
- **Decision-register Git blob:** `ec83ffac6f3ae48d006849f8450ed5b099a3803b`
- **Review boundary:** independent, read-only, exact-head reconstruction. No author conclusion was treated as acceptance.

Four-ref currency was checked at the end of the review. Local `HEAD`, the local origin-tracking ref, `git ls-remote` for the branch, and GitHub PR #121’s `headRefOid` all equalled the exact subject above. The worktree remained clean.

## 2. Verdict

**`rework_required`**

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 1 |
| Minor | 1 |

Revision 0.4 closes five of the six R3 findings at specification level. The newly added cancellation-review route does not yet distinguish a recorded negative verdict from a review that satisfies the gate, so R3-M4 is not fully closed.

## 3. Findings

### R4-M1 — A rejected or unverifiable outcome review clears the reviewed-outcome gate

**Severity:** Major

**Claim.** `ReviewDiscoveryOutcome` unconditionally emits the aggregate/Candidate `*Reviewed` events after any W2 `ReviewVerdictRecorded`. The specification does not require a satisfying verdict before it moves a cancelled or Partial outcome to `*_reviewed` and enables the revisit path.

**Direct evidence.**

1. Accepted W2 distinguishes a merely recorded verdict from a satisfied review gate:

   - W2 §17.2, line 754: `verdict_recorded` means a verdict exists, while `satisfied` means the governing policy accepted it for the gate.
   - W2 §17.3, lines 758–769: allowed verdicts include `changes_requested`, `reject`, `unable_to_verify`, and `withdrawn`; `approve_with_conditions` is satisfying only under an explicit policy.

2. W11’s cancellation transitions do not make that distinction:

   - W11 lines 424–425 and 432–433 say OR-039/OR-041 “satisfy” the overlay, but the transitions list `ReviewVerdictRecorded`, `*CancellationReviewed`, and Candidate `*CancellationReviewed` without a verdict predicate.
   - OR-039 at line 521 requires only an exact unresolved request, exact cancellation evidence, and independence.
   - OR-041 at line 523 similarly requires exact evidence/cleanup and independence.
   - Both rows unconditionally list the `*CancellationReviewed` events and `cancelled_reviewed` projections.

3. The same ambiguity exists in the complete and Partial outcome rows OR-006, OR-007, OR-020, and OR-021: exactness and independence are checked, but no satisfying-verdict predicate controls the `AssayReviewed`, `AssayPartialReviewed`, `SpikeReviewed`, or `SpikePartialReviewed` events.

4. The acceptance-test families require review traversal but do not define expected effects for each W2 verdict. In particular, tests 4 and 7 do not say that negative or unverifiable verdicts must leave the outcome gate unsatisfied.

**Concrete failure scenario.**

1. A running Spike is cancelled through OR-022; its attempt, lease, and pending OR-015 proposal are correctly retired.
2. OR-040 creates the exact cancellation review request.
3. The independent verifier records `reject` or `unable_to_verify` because the stop evidence or cleanup proof is insufficient.
4. OR-041 nevertheless emits `SpikeCancellationReviewed` and `CandidateSpikeCancellationReviewed`.
5. The projections become `cancelled_reviewed` / `spike_cancelled_reviewed`.
6. OR-023 can now propose RETRY, PARK, or KILL as if the review gate had been satisfied.

The same path exists for Assay cancellation and for Partial or complete outcome review.

**Impact.** A negative independent review becomes equivalent to a satisfying review for Discovery lifecycle progression. This violates the W2 review lifecycle, weakens P-022, and leaves the R3-M4 recovery route authority-incomplete even though the missing producer rows now exist.

**Required disposition.**

- Define an explicit verdict-to-effect table for all six `ReviewDiscoveryOutcome` discriminants.
- Emit `*Reviewed` and Candidate `*Reviewed` only when the W2 review reaches `satisfied` under a named policy.
- `changes_requested`, `reject`, `unable_to_verify`, and `withdrawn` must not clear the overlay or enable promotion/revisit. They should retain the underlying outcome, project the exact negative review state, and provide an explicit new-request or supersession route where appropriate.
- Define the treatment of `approve_with_conditions`, including condition ownership and whether conditions are blocking.
- Add each W2 verdict to tests 4, 7, and 11 for complete, Partial, and cancelled Assay/Spike subjects.

**Affected controls:** P-022/P-032; D-G6-4 limb 1; W11-I04/I06/I07/I12; tests 4, 7, and 11; R3-M4.

### R4-m1 — Discovery review-verdict rows have inconsistent Review projection targets

**Severity:** Minor

**Claim.** Rows in the same `ReviewDiscoveryOutcome` family inconsistently update the W2 Review projection.

**Evidence.**

- Every request row OR-034–OR-040 includes `U:review → P:review`.
- Verdict rows OR-020, OR-039, and OR-041 include `P:review`.
- Verdict rows OR-006, OR-007, and OR-021 name `U:review` but omit `P:review`.
- W2 §17.2 defines explicit Review projection states, and W11-I12 requires effect-equivalent projection targets for every owner row.

**Impact.** Canonical review events still exist, so this does not by itself create an authority bypass. It does, however, make rebuild and query behaviour discriminator-dependent without a stated reason and weakens the claimed reducer/projection join.

**Required disposition.** Add `P:review` to OR-006, OR-007, and OR-021, or state and test a consistent alternative projection rule across the entire Discovery outcome-review family.

## 4. R3 finding disposition

| R3 finding | R4 disposition |
|---|---|
| R3-M1 — cyclic/undefined derived hashes | **Closed at specification level.** Relation preimages are separately enumerated and exclude themselves, enclosing hashes, and later authorities. `catalogue_content_hash` is forbidden. The reconstructed authority graph was acyclic. |
| R3-M2 — prohibited-runtime catalogue bootstrap | **Closed at specification level.** Schema/catalogue bytes, independent observation/review, and Stephen’s external acceptance envelope precede runtime; OR-140 is a later one-time verified import and cannot create acceptance. |
| R3-M3 — owner catalogue/allowlist/projection/test disagreement | **Closed for the stated R3 defects.** The six Portfolio Steward review discriminants are allowed; OR-004/005/007 now project Candidate; all 81 rows receive exact expanded positive, negative/mutation, and retry identities. R4-m1 records a narrower remaining projection inconsistency. |
| R3-M4 — cancelled outcomes lack review producers | **Not fully closed; R4-M1.** OR-038–OR-041 supply exact producers, but negative W2 verdicts still clear the reviewed-outcome gate. |
| R3-M5 — Spike Partial/cancel leaves overlays live | **Closed at specification level.** OR-019 closes the attempt and lease; OR-022 atomically closes resources and supersedes a pending OR-015 proposal. Both cancellation/proposal race orders fail closed. |
| R3-M6 — late annotation stales cutover | **Closed at specification level.** The accepted epoch is re-enumerated under lock, a pre-fence delta rejects, and fence/successor activation/cutover occur atomically. |

## 5. Owner-catalogue reconstruction

The independent parser found:

- exactly **81** owner rows;
- exact ranges **OR-001–OR-041** and **OR-101–OR-140**;
- no gaps, duplicates, or extra IDs;
- five non-empty normative cells in every row;
- one command/schema, reducer, projection target set, and receipt in every row;
- **81 unique receipts**;
- **81 unique expanded positive IDs** of the form `W11-T01-OR-nnn`;
- **81 unique expanded negative IDs** of the form `W11-T03-OR-nnn-owner-row-mutation`;
- **81 unique expanded retry IDs** of the form `W11-T11-OR-nnn`.

The closed W4 joins passed for the explicitly enumerated additions:

- Scout: OR-001 and OR-029.
- Portfolio Steward: OR-001/002/003/008/009/011/012/014/015/023/025/026/030/034–038/040 and the explicitly named authority-content/proposal rows OR-105/107/110/112/114/128.
- Operator/auditor: OR-017/022/028/032/033/116/118/140.

OR-034–OR-040 now match the six exact Portfolio Steward `RequestDiscoveryOutcomeReview` discriminants. OR-004, OR-005, and OR-007 now include Candidate projection effects. The only remaining catalogue issue found is R4-m1.

## 6. Hash-DAG and bootstrap reconstruction

The normative ordering is constructible:

```text
owner requirement/specification
  -> content candidate
  -> independent file observation
  -> independent review
  -> external Decision/acceptance
  -> runtime consumer or later closure
```

The independent DAG oracle covered the dossier, Assay bar, source inventory, transition mapping, cutover closure, schema catalogue, runtime, and genesis chains. It contained 40 named nodes and 35 dependencies and produced a complete topological order with no self-edge or strongly connected component.

Specific R3 repairs passed:

- `assay_relation_hash` has an exact `AssayRequestRelation` preimage and excludes itself and enclosing/later hashes.
- `transition_relation_hash` has an exact `LegacyTransitionRelation` preimage and excludes itself, `content_hash`, and later authority/event hashes.
- `W11SchemaCatalogueContent` uses only the common `content_hash`; `catalogue_content_hash` is forbidden.
- The external `W11CatalogueAcceptanceEnvelope` is accepted before runtime and contains exact specification/schema/catalogue/observation/review/owner-multiset/bootstrap identities.
- OR-140 imports only that accepted envelope. It cannot propose, review, accept, amend, or regenerate it, and a conflicting or second genesis fails closed.

No W11 revision acceptance was inferred from Stephen’s approval of the bounded bootstrap policy.

## 7. Cancellation and resource-race reconstruction

The resource cleanup itself is now closed:

- **OR-015 first, OR-022 second:** cancellation binds the unresolved proposal and atomically emits its supersession alongside Spike cancellation and any attempt/lease closure.
- **OR-022 first, OR-015 second:** the Spike is no longer `approval_pending`, so a later proposal fails its state/version precondition.
- **OR-016 wins before cancellation:** the proposal is resolved; cancellation from `authorized` remains valid and has no unresolved proposal to retire.
- **OR-022 wins before OR-016:** the proposal is superseded and stream versions change, so the resolution fails stale.
- **Spike PARTIAL:** OR-019 closes the exact attempt and releases the lease before Partial review/revisit.
- **Retry:** OR-025 creates a fresh `spk_` and supersedes the old aggregate atomically.

The remaining defect is review authority after cleanup, not resource cleanup itself.

## 8. Annotation-epoch reconstruction

The R3-M6 policy is now coherent at specification level:

1. The accepted cutover closure binds the exact legacy annotation epoch, directory identity, writer-grant/event position, complete member list, ingestion/rejection references, and empty pending-set hash.
2. `CutOverDiscoveryPath` reloads the full closure and re-enumerates the epoch using raw directory handles while holding the path and epoch locks.
3. Any new pre-fence member or identity change rejects before publication.
4. On exact equality, one atomic registry/event transaction revokes the old writer grants, fences the old epoch, activates a successor epoch and grants, completes cutover, and revises path registration.
5. Locks remain held through the commit point.
6. Post-fence writers resolve the new registry epoch; the old epoch is read-only and cannot receive a stranded late annotation.

Stephen’s policy approval is not treated as approval of revision 0.4, implementation, migration, or a transition batch.

## 9. Decision and gate audit

| Decision/gate | R4 disposition |
|---|---|
| P-004/P-021 | Keep. Exclusive ownership and disjoint physical writers remain correct. |
| P-005/P-022 | Keep. R4-M1 must be repaired so negative review is not treated as gate satisfaction. |
| P-026 | Keep. The subject remains specification-only. |
| P-032 | Keep direction; rework this exact revision. |
| P-034 | Keep. The source-inventory → mapping → transition → closure → cutover ordering is now acyclic and epoch-fenced. |
| P-036 | Keep unchanged. It accepts the WP6 launch-basis revision, not W11. |
| D-G6-4 bounded bootstrap/epoch policies | Recorded as accepted on 2026-07-18; this accepts only those two policies. |
| D-G6-4 limb 1 | **Open.** Do not accept `4b941326...`; it has one open Major. |
| D-G6-4 limb 2 | **Open.** No first ownership-transition batch is approved or inferred. |
| W11-A1 | Open/optional; default omission remains conforming. |

## 10. Complete invariant disposition

| Invariant | R4 disposition |
|---|---|
| W11-I01 | Pass |
| W11-I02 | Pass; R3 hash defects closed |
| W11-I03 | Pass |
| W11-I04 | **Fail — R4-M1** |
| W11-I05 | Pass |
| W11-I06 | **Fail — R4-M1** |
| W11-I07 | Partial pending R4-M1 |
| W11-I08 | Pass |
| W11-I09 | Pass |
| W11-I10 | Pass |
| W11-I11 | Pass |
| W11-I12 | Partial — R4-M1 and R4-m1 |
| W11-I13 | Pass |
| W11-I14 | Pass at design level; unavailable future Windows coverage remains Partial |
| W11-I15 | Pass |
| W11-I16 | Pass; transition relation is constructible |
| W11-I17 | Pass |
| W11-I18 | Pass; annotation epoch/fence closes the prior race |
| W11-I19 | Pass |
| W11-I20 | Pass |
| W11-I21 | Pass |
| W11-I22 | Pass; external-envelope genesis is constructible |

## 11. Complete pre-implementation test-family disposition

| Test | R4 disposition |
|---:|---|
| 1 | Partial pending projection consistency in R4-m1 |
| 2 | Pass as a required pattern |
| 3 | Partial: complete-row equality alone does not detect R4-M1/R4-m1 |
| 4 | **Blocked by R4-M1** |
| 5 | Pass |
| 6 | Pass |
| 7 | **Blocked by R4-M1** |
| 8 | Pass |
| 9 | Pass |
| 10 | Pass |
| 11 | **Blocked by R4-M1; partial under R4-m1** |
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
- Markdown tables: no width mismatches.
- Code fences: 22 delimiters, balanced.
- Local Markdown links: no missing targets.
- `git diff --check`: passed.
- R1, R2, and R3 historical review files are unchanged from their review commits.
- PR #121: open, draft, mergeable.
- Codacy: passed.
- CodeRabbit: status “success” only because review was skipped for the draft PR; it is not substantive review evidence and was not retriggered.

## 13. Historical evidence hashes

| Evidence | SHA-256 | Git blob |
|---|---|---|
| R1 report | `478dfc2b4c2e5dfa3deb57ab2fb577ef3f1551a9aa1e04789141e23dc5b98617` | `8af8add2bd1853b4aaf6b0178279013256dfb044` |
| R2 report | `49d964f9931b37e76ca9223864c06f32d12bee5fc80611b9f5d0860a0d8c3cb7` | `3d15046c937672f3a7a1519f65e739a586374248` |
| R3 report | `b9112e42c2d677aeb0425c1e59e08fd553ff05f3cdefcfcfdfed24634735080b` | `b0b33c75b00b6318a1deaf50846640d33bd5030c` |

## 14. Residual risks after remediation

- Future materialization must reconstruct expected owner and schema rows independently rather than derive both sides from runtime.
- Every W2 outcome-review verdict must receive an explicit lifecycle effect; “review recorded” must never silently become “gate satisfied.”
- Future Windows identity/race tests must report unavailable coverage as Partial.
- The living legacy backlog remains mutable and must be freshly re-observed for any migration authority.
- W9/W10 and implementation review remain downstream and cannot narrow W11’s ownership or writer controls.
- Passing interface tests does not establish scientific adequacy, result acceptance, or claim authority.

## 15. Review action boundary

This review made no file changes, commits, branch changes, pushes, PR comments, thread resolutions, CodeRabbit triggers, merges, acceptance decisions, schema/runtime mutations, admissions, ownership transitions, cutovers, or claim actions.
