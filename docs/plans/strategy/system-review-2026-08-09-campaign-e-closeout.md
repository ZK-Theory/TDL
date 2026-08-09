# System Review 2026-08-09 - Campaign E Closeout

## Outcome

Campaign E is actioned. The approved durable-store and recovery observations are now bound to current implementation controls, public-seam negatives, and reusable skill guidance. One missing read-path control was added: every required control-store child is removed in turn and `ApprovedProjectBinding.load` must reject without recreating or changing any remaining entry.

## Observation dispositions

| Observation | Disposition and evidence |
|---|---|
| `01KYZ84R9Y80VG8N5BJQJ0C79C` | ACTIONED - scoped activation markers bind the complete command envelope and resolved schema identity in `research_system/command/service.py`; changed command/event schema controls live in `test_external_assurance_record_publication.py`. |
| `01KYZ84RB87PZ7HCR71984FAQ4` | ACTIONED - rollback ownership is generation-bound; `test_recovery_preserves_distinct_later_activation_of_same_target` proves a later command's object survives. |
| `01KYZ84RCMT2Q5V202TMRVZQC6` | ACTIONED - stale reclamation uses an atomic recovery claim; `test_two_reclaimers_cannot_remove_a_fresh_winner` is the deterministic ABA negative. |
| `01KYZ8W4ETJ9FGVZ2PYNAC7FVF` | ACTIONED - `CompositeWriterLock` captures physical directory identity; the Windows public-seam alias matrix in `test_wp6_1_scope_task_authority.py` includes the extended-path spelling. |
| `01KYZBCCM5Y6XK8EVVTSC9ASZF` | ACTIONED - approved binding uses the read-only `require_existing_control_root`; the new six-child parameterized negative proves rejection does not repair the store. |
| `01KYZW4ZHN97PYCGYXTWE9HAF5` | ACTIONED - directory-anchor cleanup retains failed handles for retry and preserves the primary error; unit controls cover both primary-error and cleanup-only orderings. |
| `2026-08-02-validate-layout-before-mutating-constructors` | ACTIONED - existing-store layout validation precedes manifest loading and mutating construction; the new six-child negative preserves the original missing-child evidence. |
| `2026-08-02-win32-directory-durability-retry-barrier` | ACTIONED - restore identity uses native `CreateFileW` and `FlushFileBuffers`; generation/retry controls require durability before state advancement. |
| `2026-08-02-store-origin-information-loss` | ACTIONED - initialization persists an external immutable origin witness; normal loading requires it and copied-store/no-witness negatives fail closed. |
| `01KZ1P33M70RPNQW1HAVEDD9HG` | ACTIONED - composite locking and final fences use real ownership records; reusable skill guidance now requires lock-double protocol conformance and primary-domain-error controls. |
| `01KZ2K4C0E2PTX15WC1G923QV7` | ACTIONED - `configure_moved_restore` requires an explicit approved witness and joins configured source lineage before any writer lock; mismatch is tested without mutation. |
| `01KZ3MM325YW3PCPYNT8KZT1QM` | ACTIONED - public restore retry, retired-source loading, post-mutation generations, and destination durability are covered by the Gate 5 and origin-witness integration suites. |

## Simplification sweep

No new recovery framework or duplicate helper was added. Existing production mechanisms already implement eleven dispositions; the campaign adds one missing negative and consolidates the reusable rules into the two skills that own implementation and independent review.

## Validation contract

- 25 mapped lock, marker, witness, source-lineage, restore-retry, and six-child approved-binding cases passed on Windows.
- `.agents/skills` to `.claude/skills` byte-identity and guide checks passed.
- diff hygiene passed after excluding the sync tool's non-semantic state-file line-ending rewrite.
- the campaign changes 6 files, below the 100-file PR limit.
