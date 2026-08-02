# WP6.4 restore recovery correction — exact-subject review

**Date:** 2026-08-02 (Europe/London)

**Verdict:** `rework_required`

**Findings:** 3 Critical, 0 Major, 0 Minor

**Design adjudication:**
`implementation/06n-wp6-4-restore-recovery-state-machine-design.md`

This is a fresh independent review of the exact implementation subject. It is
not producer self-report, owner acceptance, PR or merge evidence, Gate 6
acceptance, CodeRabbit evidence, or authorization to remediate or dispatch.
Passing tests are supporting evidence only and cannot establish the missing
transaction semantics.

## 1. Exact review identity

| Identity | Exact value |
|---|---|
| Review worktree | `C:\Users\steph\.codex\worktrees\da43\TDL` |
| Review branch | `codex/wp64-restore-state-machine-design` |
| Candidate | `3d5a1a7bdf6af80f47e6be3aa68c4d32708fd1ab` |
| Parent | `ebc42596fc4bc7b95fb380e6bbece5efde0f742d` |
| Candidate tree | `930ae9401849c965111893ccd32a5af096825a46` |
| Producer remote | `origin/codex/wp64-store-restore-binding-r6` |
| Design-branch remote before review-record commit | `origin/codex/wp64-restore-state-machine-design` |
| Fully qualified remote equality before record writes | both refs resolved to the exact candidate |
| Candidate delta | 8 paths; 504 insertions, 22 deletions |

The worktree started detached. Detached `HEAD`, the named local design branch,
the producer branch, the fully qualified design remote ref, and the candidate
tree were proved equal before one deterministic switch to the named design
branch. The parent is an ancestor. Cwd, symbolic branch, `HEAD`, remote head,
and clean status were rechecked before record writes. No foreign worktree was
edited.

## 2. Authorities read and provenance

| Authority | Blob/revision used | Disposition |
|---|---|---|
| WP6 Gate 6 master plan | `3d0b24bb003d856ccf477c2cb910df3d885fc0b2` at the candidate | Governs WP6.4 binding/recovery and preserves the separate Gate 6 acceptance boundary. |
| Original Gate 6/pilot plan | `3e823d14cd61a02506663ba44730c95cfa8cf7ba` at the candidate | Requires deterministic recovery and rollback without rewriting accepted evidence. |
| Owner-operated-session amendment | accepted blob `49696e5b737f59ab8bd58d18c6e9231b0a61a599` | Removes provider automation; does not weaken store/output provenance. |
| Owner acceptance of the amendment | `6c9d64cf04f00819f0b4c81b9e248b31ca1940c2` at the candidate | Planning authority only; no runtime or Gate 6 authority. |
| Decision register | `552183b39e70cf4b105346bdd7f747496a792e85` at the candidate | P-020 single writer/external store, P-031 pilot boundary, P-036 exact-plan authority, and P-042 owner-operated sessions. |
| Current review of parent candidate `ebc4259` | blob `31f04348d892992aa730b5648f748769206dd824` at review commit `eb73ca4957ee05576fb23203717674b16b86f4ca` | Prior findings were re-tested against current code; its verdict was not inherited. |

## 3. Executive disposition

The candidate closes the prior read-only layout defects. `ControlBinding.load`
no longer initializes missing directories; all six required children use one
physical-child validator; Windows reparse/symlink children are rejected; and a
parent alias with physical children is accepted. The CLI and CommandService
also add restore-side layout rechecks. Direct current-code probes confirmed
those properties.

The candidate does not close the recovery boundary. Its option-A protocol
still validates a mutable output and then removes the recovery marker in a
separate operation. A bounded probe changed the output after the second and
last journal-state validation; the command returned `0` and `status=bound`,
canonical evidence remained, the output was foreign, and both journal and
recovery marker were absent. A second probe showed recovery can delete foreign
output introduced after its initial inventory. A failed journal-to-marker move
can create both names, after which recovery deterministically selects the
journal and immediately rejects the already-existing marker.

The shared caller is also incomplete. `CommandService._recheck_moved_restore`
still invokes finalization without a journal. A process-exit probe at manifest
publication left a target-bound manifest, no canonical evidence, no journal or
marker, and an ordinary `ControlBinding.load` accepted the target.

The exact subject remains quarantined. It must not be integrated, represented
as WP6.4 closure, or used to support Gate 6 acceptance.

## 4. Prior-finding re-review

| Parent-review finding | Current disposition | Exact reason |
|---|---|---|
| C-01 final output/journal clear | **Open; vehicle narrowed but invariant not closed.** | Final validation now occurs inside clear and a recovery marker covers some unlink failures, but final validation is not sealed to marker removal, rollback has a compare/use gap, and one caller remains journal-less. |
| M-01 retry repairs missing target directories | **Closed at this subject.** | `ControlBinding.load` uses `require_existing_control_root`; CLI retry and CommandService paths call the read-only validator. The direct six-child matrix rejected every absence and left it absent. |
| M-02 foreign child reparse accepted | **Closed at this subject.** | `lstat`, Windows reparse metadata, directory type, resolved-parent, and same-file checks are applied to all six children. The direct reparse probe rejected a directory symlink and the parent-alias control passed. |

## 5. Findings

### C-01 — Critical — Mutable output remains unsealed and recovery can delete foreign bytes

**Claim.** Final output publication is still a mutable-path check rather than an
owned commit primitive. The candidate can report success after a foreign output
change, and its rollback helper can delete foreign output introduced after the
earlier inventory.

**Direct evidence.** `research_system/cli.py:515-532` performs the caller's
last manifest/evidence/output validation. `research_system/store/identity.py:552-587`
then validates journal state, renames the journal, validates again, unlinks the
marker, and fsyncs the directory. There is no output ownership primitive that
prevents mutation after the second check at line 575 and before/after unlink at
line 576. The adjacent output lock in
`research_system/operations/backups.py:379-395` is cooperative and does not bind
the output file identity to marker removal.

Recovery first inventories bytes at
`research_system/store/identity.py:675-690`, then later calls
`_restore_exact_path` on output at lines 738 or 744. `_restore_exact_path` at
lines 590-611 unlinks when the expected original is absent and overwrites when
an original is recorded; it does not require transaction ownership or the
earlier observed bytes to remain current at the mutation seam.

**Concrete failure scenarios.**

1. The `FINAL_GAP_PROBE` invoked the real CLI and changed the output immediately
   after the second `_validate_restore_binding_journal_state` returned. Result:
   `return_code=0`, `journal_state_validations=2`,
   `output_is_foreign=true`, `evidence_exists=true`,
   `journal_exists=false`, and `recovery_exists=false`.
2. The `ROLLBACK_RACE_PROBE` started with allowed original/expected state, then
   placed foreign bytes immediately before `_restore_exact_path` performed the
   rollback. Recovery returned without error, deleted the foreign output, and
   cleared all recovery authority:
   `foreign_preserved=false`, `output_exists=false`,
   `journal_exists=false`, `recovery_exists=false`.

**Impact.** Scenario 1 creates canonical success evidence for output bytes that
are not present and removes deterministic recovery authority. Scenario 2
deletes a path the transaction does not own. Both cross the accepted
authority/evidence and filesystem-ownership boundaries; the first can admit an
invalid binding and the second can destroy foreign state.

**Disposition.** Fix now; reject this subject. Repeated validation is not an
adequate correction.

**Required interface/lifecycle change.** Implement the companion design's
single transaction record and store-owned content-addressed output. Canonical
success must cite the immutable output object. Rollback must never delete the
final object and may clean a temporary only through an exact transaction-owned
claim checked at the mutation seam.

**Affected decisions/work packages.** P-020 storage/single-writer boundary;
WP6.4 restored-store binding; Gate 6 rollback/recovery evidence; CLI
`store restore-bind`; every consumer of canonical restore evidence.

### C-02 — Critical — Journal-to-marker failure creates two unrecoverable authorities

**Claim.** The marker fallback can leave both the original journal and recovery
marker present, while restart logic has no reconciliation rule for the pair.

**Direct evidence.** In
`research_system/store/identity.py:560-573`, a failed
`os.replace(journal_path, marker_path)` causes the exception handler to write a
new marker when no marker is visible; it does not require the original journal
to be absent. `recover_restore_binding` at lines 768-775 always selects the
journal first when both names exist. Its eventual clear reaches lines 560-562
and rejects because the marker already exists.

**Concrete failure scenario.** `RENAME_FAILURE_PROBE` failed only the primary
journal-to-marker rename while allowing the fallback marker write. The clear
raised the simulated `OSError`; both files existed. A normal recovery attempt
then failed with `ConflictError: restore binding recovery marker already
exists`, leaving both authorities present.

**Impact.** A permitted removal/publication failure makes deterministic
recovery impossible without manual deletion or an unreviewed precedence
choice. The state is fail-closed but not recoverable, directly violating C-01's
durable recovery-authority requirement.

**Disposition.** Fix now; reject this subject.

**Required interface/lifecycle change.** Use one fixed transaction-record path
with monotone durable states. `cleared` must revoke recovery authority by record
state, not by moving/deleting the only record during the command. Never create
a sibling marker as fallback.

**Affected decisions/work packages.** WP6.4 crash recovery; CLI retry;
store-identity internal record semantics; Gate 6 deterministic-recovery proof.

### C-03 — Critical — CommandService still has a journal-less crash path accepted by normal loading

**Claim.** The shared moved-restore caller can publish a rebound manifest
without durable transaction authority. A process crash then leaves a state
that normal binding load accepts even though canonical restore evidence is
absent.

**Direct evidence.** `CommandService._recheck_moved_restore` calls
`finalize_verified_restore_binding` at
`research_system/command/service.py:272-286` without a `journal_path` or output
transaction. `finalize_verified_restore_binding` passes its optional value to
`rebind_restored_store` at
`research_system/operations/backups.py:1077-1096`; the default is `None`.
`rebind_restored_store` publishes manifest and evidence in separate operations
and only marks/clears a journal when `journal_path is not None`
(`research_system/store/identity.py:1013-1093`).

After such a partial publication, `ControlBinding.load` at
`research_system/config.py:201-214` checks layout and store manifest identity
but does not require canonical restore evidence or a cleared transaction
record.

**Concrete failure scenario.** `JOURNALLESS_CRASH_PROBE` ran the shared real
rebind implementation with the same `journal_path=None` shape and exited the
process immediately after target-manifest replacement. Result:
`child_return_code=77`, `manifest_bound_to_target=true`,
`evidence_exists=false`, `journal_exists=false`, `recovery_exists=false`.
An ordinary `ControlBinding.load` returned the target root with no error.

**Impact.** A crash can convert a copied store into apparently ordinary bound
state without canonical recovery/evidence identity. Subsequent commands can
operate on a state that never reached the reviewed restore commit protocol.
This is an authority/evidence bypass, not only an unavailable retry.

**Disposition.** Fix now; reject this subject.

**Required interface/lifecycle change.** Forbid journal-less restore
finalization. Route CLI and CommandService through the same durable transaction
record. Keep restore commitment separate from the first domain-command append:
finish the restore through `cleared`, then use ordinary command idempotency for
the append. Binding loaders must reject every non-`cleared` restored state.

**Affected decisions/work packages.** P-020 single writer; WP6.4 moved-store
activation; CommandService restart/replay; restore evidence and binding loaders;
Gate 6 recovery and exact-subject evidence.

## 6. Invariant-to-enforcement matrix

| Invariant | Candidate enforcement | Direct result | Disposition |
|---|---|---|---|
| C-01 exact output/manifest/evidence plus durable removal of recovery authority | CLI final validators; journal→marker→validate→unlink | Final-gap and rollback-race probes failed | Not satisfied; C-01 |
| One deterministic recovery authority | Journal plus recovery marker | Rename-failure probe created both and recovery deadlocked | Not satisfied; C-02 |
| All restore callers use recovery state | Optional `journal_path`; CLI supplies it | CommandService omits it; process-crash probe left accepted partial state | Not satisfied; C-03 |
| M-01 validation/retry are read-only | `ControlBinding.load` and finalizers use `require_existing_control_root` | All six missing-child cases rejected; each remained missing | Satisfied at this subject |
| M-02 physical direct children; parent alias accepted | `lstat`, reparse bit, directory and physical-parent checks | Directory symlink rejected; parent alias accepted | Satisfied at this subject |
| Concurrent ARS writers excluded | Source/target/output lock ordering | Deterministic cooperative locking preserved | Satisfied for cooperating writers; it does not cure C-01 mutable output |
| Moved-root identity and fresh authority | preflight snapshot/grant/manifest rechecks | Existing exact join remains; layout recheck added | Preserved, but C-03 bypasses crash completion |
| Replay/evidence identity | Source replay/snapshot plus manifest/evidence joins | Normal loader accepts the C-03 partial state without evidence | Not satisfied across restart |

## 7. Candidate mechanism audit

| Mechanism/decision | Disposition |
|---|---|
| Read-only existing-root validation in `ControlBinding.load` | Keep. |
| Six-child physical directory validation and parent-alias behavior | Keep. |
| Source/target recheck in finalization and CommandService | Keep. |
| Canonical evidence joined to raw manifest bytes and output digest | Keep the fields; extend them with transaction/output-object identity. |
| Journal → recovery marker → validation → unlink | Reject; replace with one durable monotone record. |
| Caller-supplied mutable output as canonical result | Reject; make canonical output store-owned/content-addressed. |
| `_restore_exact_path` rollback of final output | Reject; final output is never rollback-deleted. |
| Optional/journal-less finalization | Reject for all restore callers. |
| Exact candidate accepted for integration | Reject/quarantine. |

## 8. Validation evidence

The direct interpreter was Python 3.13.5 at
`C:\Users\steph\TDL\.venv\Scripts\python.exe`, with repository bytecode and
pytest cache writes disabled. Every custom probe used an OS temporary directory
outside the repository. No provider, credential, PR, Jira, CodeRabbit, external
party, or production foundation record was touched.

| Check | Result |
|---|---|
| Candidate identity, parent, tree, ancestry, local/remote refs, clean status | Passed before review work |
| Complete `parent..candidate` path/diff inventory | 8 paths; 504 insertions, 22 deletions; complete diff inspected |
| `git diff --check` before record writes | Passed |
| `FINAL_GAP_PROBE` | Failed candidate invariant: success with foreign output and no recovery authority |
| `ROLLBACK_RACE_PROBE` | Failed candidate invariant: foreign output deleted and authority cleared |
| `RENAME_FAILURE_PROBE` | Failed candidate invariant: journal plus marker; retry conflict |
| `JOURNALLESS_CRASH_PROBE` | Failed candidate invariant: rebound manifest, no evidence/record, ordinary load accepted |
| Direct six-child/read-only/reparse/parent-alias matrix | Passed: six missing children remained absent; symlink rejected; parent alias accepted |
| Combined candidate regression selection | Timed out after 604 seconds without a completed result; not counted as passing evidence |

The timeout covered only the candidate's selected changed-behavior tests and
emitted no completed summary before termination. No package or full suite was
run: the direct negatives already decide the verdict, and broader green output
could not close absent controls.

## 9. Prompt-ready bounded remediation brief

**Recommended agent:** **Sol**. The work crosses crash linearization,
filesystem ownership, Windows reparse/durability behavior, canonical evidence,
and two live callers. Terra would be appropriate only after the state-machine
contract is implemented and the remaining work is mechanical test closure;
Luna is not recommended for this systems-critical correction.

**Starting subject:**
`3d5a1a7bdf6af80f47e6be3aa68c4d32708fd1ab` on one new remediation branch.

**Objective:** implement exactly
`implementation/06n-wp6-4-restore-recovery-state-machine-design.md`, preserving
the accepted M-01/M-02 behavior and producing one new exact candidate for
independent review.

**Allowed production scope:**

- `research_system/store/identity.py`
- `research_system/operations/backups.py`
- `research_system/cli.py`
- `research_system/command/service.py`
- `research_system/config.py` only for cleared-record/evidence admission
- `research_system/store/layout.py` only if required to preserve, not weaken,
  physical-root validation

**Allowed test scope:** the two changed integration files plus directly relevant
`tests/research_system/unit/test_replay.py` or
`tests/research_system/unit/test_store.py` controls. Do not refactor unrelated
fixtures.

**Required work:**

1. Replace the journal/recovery-marker pair with one canonical durable record
   implementing `prepared`, `published`, `final_validated`, `committed`, and
   `cleared` generations. Do not delete the record to express clear.
2. Publish canonical binding output as a no-replace, store-owned,
   content-addressed object; add its path/digest and transaction ID to canonical
   evidence. Treat caller-selected mutable paths as projections only.
3. Make compare-before-write ownership checks occur at every cleanup mutation;
   never delete final output and preserve all foreign bytes.
4. Remove the journal-less finalization mode from CLI, CommandService, and
   direct restore helpers. Complete restore before the first domain-command
   append, relying on ordinary command idempotency across the boundary.
5. Make normal binding loaders reject non-`cleared` restored state and verify
   cleared record/evidence/manifest/output identity.
6. Add the complete decisive negative matrix from the design, including the
   four failures reproduced in this review, every state crash, all six child
   types, parent alias, concurrent writer, moved-root drift, and replay/evidence
   expected-side independence.

**Validation boundary:** run the exact new negatives and the existing
changed-behavior restore/layout/replay tests with coverage and cache plugins
disabled. Expand only if a shared evidence/schema interface change creates a
named dependency trigger. Record any timeout as incomplete, never as passing.

**Hard stops:** no provider/credential work, PR/Jira/CodeRabbit action, merge,
Gate 6 claim, owner acceptance, unrelated refactor, or foreign-worktree write.
Do not weaken M-01/M-02 or reinterpret a green suite as semantic acceptance.

**Required handback:** exact cwd, branch, parent, candidate, tree, complete diff,
targeted commands/results, unresolved Windows risk, remote equality, and clean
status; then request a fresh independent exact-subject review.

## 10. Residual risk and next action

The design has not been implemented. Native Windows directory-entry durability
and no-replace content-addressed publication still require direct evidence at a
future candidate. The long selected pytest run did not complete and provides no
positive evidence. These are validation obligations, not reasons to dilute the
three reproduced Critical findings.

**One next action:** dispatch the bounded Sol remediation brief above from the
exact candidate, then independently review the resulting new exact subject.

No production or test remediation was performed. The only task writes are this
review and its companion design record.
