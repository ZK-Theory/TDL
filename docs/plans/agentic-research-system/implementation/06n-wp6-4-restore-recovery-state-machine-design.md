# 06n — WP6.4 restore recovery state-machine design

**Date:** 2026-08-02

**Status:** `design_adjudicated_implementation_not_authorized`

**Exact implementation subject reviewed:** `3d5a1a7bdf6af80f47e6be3aa68c4d32708fd1ab`

**Parent:** `ebc42596fc4bc7b95fb380e6bbece5efde0f742d`

**Candidate tree:** `930ae9401849c965111893ccd32a5af096825a46`

**Companion review:**
`reviews/wp6-4-restore-recovery-3d5a1a7-review-2026-08-02.md`

**Implementation authority:** none

## 1. Design ruling

The selected recovery design is:

> **Option B plus the minimum necessary part of option C:** one durable
> transaction record with monotone `prepared`, `published`,
> `final_validated`, `committed`, and `cleared` states, together with a
> store-owned, content-addressed final binding output.

The transaction record stays at one canonical path. `cleared` is a durable
state of that record, not deletion of the only recovery proof. The transition
to `cleared` revokes rollback/completion authority while retaining an audit
record. No sibling recovery marker is created.

The final binding output is an immutable content-addressed object in a
single-writer store namespace. A caller-selected mutable path may be a
rebuildable projection, but it is not canonical restore output, is not cited
by canonical restore evidence, and cannot determine restore success.

This is the least complex design that meets the requirements. A state record
alone cannot seal a mutable output between its last validation and transaction
clear. Content-addressed output alone cannot recover partial manifest/evidence
publication. The combination closes both seams without introducing a database,
distributed transaction coordinator, or new service.

## 2. Governing authority and forward obligations

| Source | Binding obligation | Design disposition |
|---|---|---|
| `03-decisions-and-open-questions.md` P-020 | One project-wide command service owns one external canonical store and protected linear history. | The target store writer owns the transaction record, output object, manifest, and evidence namespace. Task worktrees do not publish them. |
| `04-parallel-specification-and-foundation-pilot-plan.md` §§4–7 | Gate 6 requires recovery evidence and rollback that does not change accepted research evidence; stop if recovery cannot prove canonical state. | Success is impossible until the exact tuple is durable and recovery authority is durably cleared. Conflicts fail closed without rewriting foreign output. |
| `implementation/06-wp6-gate6-readiness-and-integration-plan.md` §3 WP6.4 and §9 | Bind the approved external store, prove restore/recovery, and obtain separate Gate 6 preflight acceptance. | This design governs binding/recovery only. It creates no Gate 6, pilot, dispatch, or owner acceptance. |
| `implementation/06g-wp6-owner-operated-session-amendment.md` §§3, 6–7 | WP6.4 must preserve exact-subject evidence and the operator-mediated boundary without provider automation. | Transaction/evidence identities include exact store, source, target, receipt, and output identities. No provider or credential surface is added. |
| `reviews/wp6-owner-operated-session-amendment-owner-acceptance-2026-07-26.md` | The owner-operated amendment is planning authority only. | This design record authorizes no runtime implementation or Gate 6 transition. |
| Prior exact-subject review of `ebc4259` | Close final output/journal atomicity, read-only restore validation, and physical child identity across all callers. | M-01 and M-02 are preserved. C-01 is replaced by the state machine and output-ownership contract below. |

## 3. Option comparison

| Option | Strength | Decisive weakness | Disposition |
|---|---|---|---|
| A. Journal → durable recovery marker → final validation → clear | Small delta from the existing journal and can preserve authority after some unlink failures. | Moving one record between two names can create duplicate authorities on a failed move. More importantly, a mutable output can change after the last validation and before marker removal. Repeating the validation only moves the race. | Rejected as a complete design. Its useful property—authority survives a failed cleanup—is retained through a durable `committed`/`cleared` record state instead. |
| B. One record with `prepared`/`published`/`final_validated`/`committed`/`cleared` | Gives one recovery authority, explicit crash semantics, monotone retry, and no journal/marker split. | By itself, it still cannot prevent a separately mutable output from changing between validation and the state transition. | Selected as the recovery state machine, conditional on C. |
| C. Owned or content-addressed output publication | Removes overwrite/delete authority over foreign output and gives output bytes an independently checkable identity. | By itself, it does not recover partial manifest/evidence publication or distinguish rollback from completion. | Selected narrowly for the final output; combined with B. |

## 4. Normative invariants

### C-01 — Complete, recoverable success

Success requires all of the following at one transaction identity:

1. the immutable final output bytes hash to the output digest encoded by their
   content-addressed path;
2. the target manifest is canonical and its raw-byte digest and semantic
   identity match the intended rebound manifest;
3. canonical restore evidence binds the exact output digest/path, target
   manifest raw-byte digest and semantic hash, source snapshot, receipt,
   project, store, source root, and target root;
4. the transaction record is durably `cleared`; and
5. no live `prepared`, `published`, `final_validated`, or `committed` recovery
   authority remains.

Any mismatch before `cleared`, any state-record durability failure, or any
failure to prove final output ownership retains the single transaction record
and fails closed. Rollback never overwrites or deletes a foreign final output.

### M-01 — Validation is read-only

Restore validation and retry never create or repair a control-store directory.
Missing required directories are rejected with the complete filesystem state
unchanged. Store initialization remains an explicit operation through the
existing initialization path.

### M-02 — Physical child layout

`objects`, `events`, `manifests`, `receipts`, `snapshots`, and `runtime` must
each be a physical directory directly under the approved resolved root. A
regular file, symlink, junction, mount/reparse escape, or unavailable identity
is rejected. A parent alias is accepted only when it resolves to the approved
root and all six children themselves are physical.

### C-02 — One recovery authority for every caller

Every path that can rebind a restored manifest uses the same transaction
record. `CommandService._recheck_moved_restore`, CLI `store restore-bind`, and
direct finalization helpers may not select a journal-less mode.

### C-03 — Ownership-limited cleanup

Cleanup may remove a temporary only when the record identifies it as created by
the transaction and its current file identity and bytes match the recorded
transaction-owned object. Final content-addressed output is never deleted by
rollback. A foreign collision is preserved and reported.

### E-01 — Acyclic evidence identity

The hash dependency graph is one-way:

`approved inputs/source snapshot → output object + rebound manifest → canonical evidence → transaction state record`

Evidence never hashes a record that in turn hashes the same evidence. Expected
values come from the approved foundation, receipt, independently replayed
source state, and preflight result—not from the producer fields being checked.

## 5. Durable objects

### 5.1 Transaction record

Use one canonical target-store path, for example:

`manifests/.restore-binding-transaction.json`

The record is canonical JSON and has at least:

- `schema_id`, `schema_version`, `transaction_id`, `state`, and a monotone
  `generation`;
- the prior record digest for a monotone transition chain;
- resolved source and target paths plus stable physical root identity where the
  platform exposes it;
- project, store, restore receipt, actor, grant, source snapshot, code-root,
  schema-root, and target pre-state identities;
- exact original and intended target-manifest bytes/digests;
- exact original and intended canonical-evidence bytes/digests;
- the content-addressed output relative path, byte digest, and bytes or a
  separately verified immutable source for those bytes;
- transaction-owned temporary identities and digests; and
- the last completed durability step.

Each transition is written to a temporary file, file-fsynced, atomically
replaced at the same canonical path, and directory-fsynced. A failed transition
does not create a second authority at another name. Recovery accepts whichever
complete generation is durably present and re-derives the next action from the
record plus live bytes.

### 5.2 Final binding output

The canonical output lives under a target-store-owned content-addressed
namespace, for example:

`manifests/restore-bindings/sha256-<digest>.json`

Publication is no-replace. An existing exact object is an idempotent reuse; an
existing object whose bytes do not hash to its name is a conflict and is never
overwritten. The object is immutable after publication and all canonical
consumers verify its name/content digest before loading it.

The CLI prints this exact canonical path. If compatibility needs a mutable
caller-selected path, that path is a projection created after restore success.
Its failure cannot alter the restore verdict, and normal consumers must resolve
back to the content-addressed canonical object.

### 5.3 Canonical evidence

Restore evidence adds `transaction_id`, `output_object_path`, and
`output_object_sha256` and continues to bind the target manifest raw-byte hash,
manifest semantic hash, source snapshot, receipt, project, store, source, and
target. A non-`cleared` transaction record makes the evidence ineligible for
normal binding load even if the manifest and evidence bytes look complete.

## 6. State machine

| State | Durable facts | Permitted next action | Recovery authority |
|---|---|---|---|
| absent | No transaction mutation has started. | Validate approved inputs and acquire all locks; publish `prepared` before the first mutation. | None. |
| `prepared` | Original tuple, intended identities, and output ownership are durable; canonical paths are unchanged. | Publish the immutable output object and prepared manifest/evidence temporaries. Roll back transaction-owned temporaries if publication cannot start. | May roll back transaction-owned work or continue. |
| `published` | Output object, rebound manifest, and canonical evidence are each durable at their intended paths; the record binds their exact bytes. | Revalidate source snapshot, physical roots, output digest, manifest, evidence, grant, receipt, and target identity under locks. | May complete; may roll back store-owned manifest/evidence only when current bytes equal an allowed recorded state. Never remove final output. |
| `final_validated` | The complete intended tuple was checked while the store/output ownership boundary remained held. | Atomically advance the same record to `committed`. Any mismatch retains this state and fails. | Completion/rollback authority remains; foreign output conflicts prohibit rollback of that output. |
| `committed` | The intended tuple is the only accepted transaction outcome. Rollback is no longer authorized. | Revalidate the exact tuple and advance to `cleared`. | Completion/repair authority only; never rollback. |
| `cleared` | Recovery authority is durably revoked. The record is an audit tombstone, not a live journal. | Return success; optionally archive by a separately safe maintenance operation. | None. |

Success is emitted only after the `cleared` generation and its containing
directory are durable. No fallible transaction cleanup follows the transition
to `cleared`; later projection or console failures do not reinterpret the
already committed restore.

## 7. Transition protocol

1. Resolve and validate the approved source, target, code roots, schema root,
   and all six physical children without mutation.
2. Acquire source, target, and canonical-output ownership in deterministic path
   order. A second writer fails before any mutation.
3. Recompute the preflight result, current grant, source replay/snapshot, target
   manifest raw bytes, and intended output bytes under those locks.
4. Create `prepared` with exclusive creation and make it durable.
5. Create and fsync the content-addressed output without replacing any existing
   path. Prepare manifest/evidence temporaries and record their exact bytes.
6. Publish output, manifest, and evidence; fsync each containing directory; then
   durably record `published`.
7. Re-read every intended object independently, confirm the evidence joins, and
   durably record `final_validated` while output ownership remains held.
8. Durably record `committed`. From this point recovery may only complete or
   report a conflict; it may not restore original manifest/evidence.
9. Recheck the owned immutable output object and exact manifest/evidence tuple,
   then durably record `cleared` before releasing locks.
10. Return success with the canonical content-addressed output path and hashes.

## 8. Recovery and idempotency

- `prepared`: remove only exact transaction-owned temporaries; leave any
  content-addressed final object as an unreferenced immutable object; restore
  manifest/evidence only if their current bytes are a recorded allowed state.
- `published`: if every intended byte matches, continue. If manifest/evidence
  are still original, roll them back/clear using compare-before-write. A
  foreign output is preserved and the record remains.
- `final_validated`: re-run the complete final validation. Continue only if it
  still matches; otherwise retain the record and fail.
- `committed`: never rollback. Revalidate and advance to `cleared`; if any byte
  is foreign, retain the record and fail with the exact conflicting path.
- `cleared`: verify the canonical tuple on retry, re-run fresh authority and
  source evidence checks required by policy, and return the same result. Retry
  is read-only.
- missing record plus a partially rebound manifest/evidence combination is a
  hard integrity error. It is never interpreted as a fresh initialized store.

Every compare-before-write must be performed at the actual mutation seam, not
only in an earlier inventory pass. If the comparison and mutation cannot be
sealed by the store/output ownership primitive, the mutation is prohibited.

## 9. Caller integration

### CLI restore-bind

The CLI supplies approved identities and policy evidence but does not own the
state machine through callbacks. One restore transaction component owns output,
manifest, evidence, state transitions, and recovery. Callback ordering is not
an acceptance mechanism.

### CommandService moved restore

The command service must not call finalization with `journal_path=None`.
The least-complex integration is to separate restore commitment from the first
domain command:

1. validate the proposed command without mutation;
2. under the existing source/target locks, recheck restore preflight and run the
   shared restore transaction through `cleared`;
3. append the command through the ordinary idempotent command path.

A crash after restore clear but before command append leaves a valid bound store
and no command mutation; the command retry appends once by its existing command
ID/receipt rules. This is simpler and safer than adding ledger batches and
receipts to the restore transaction record.

### Binding loaders

`ApprovedProjectBinding.load` and `ControlBinding.load` remain read-only. When a
restore transaction record exists, they reject every state except `cleared` and
verify the cleared record, evidence, manifest, and canonical output join before
returning a restored binding. Stores that have never been restored continue to
use their ordinary initialization identity.

## 10. Windows, roots, and concurrent writers

- Canonicalize a parent alias to the approved physical root, then inspect each
  child with `lstat`/reparse metadata. Reject `FILE_ATTRIBUTE_REPARSE_POINT`,
  symbolic links, junctions, and a child whose resolved physical parent is not
  the approved root.
- Keep source, target, and output acquisition in deterministic path order.
  Recheck source/target physical identity after lock acquisition and again
  before `final_validated`.
- Directory durability remains fail-closed. A platform that cannot establish
  required directory-entry durability cannot report restore success.
- The output object is inside the same single-writer target-store namespace.
  No arbitrary mutable path is held out as canonical output.
- Temporary and final publication use Windows-safe no-replace semantics and
  long absolute paths. A reparse substitution at any checked child or output
  ancestor is a conflict.

## 11. Decisive negative matrix

| Negative | Required result |
|---|---|
| Crash before `prepared` durability | No canonical mutation and no transaction record. |
| Crash in `prepared` before output publication | Retry removes only exact temporaries or continues; original state remains authoritative. |
| Crash after output publication | Record survives; exact object may remain orphaned; no foreign output is deleted. |
| Crash after manifest publication | Normal binding load rejects non-`cleared`; retry completes or safely rolls back. |
| Crash after evidence publication | Record survives; retry verifies the exact three-way join before continuing. |
| Crash after `final_validated` | Revalidate; mismatch retains the record. |
| Crash after `committed` | Never rollback; retry completes to `cleared` only after exact validation. |
| State-record replace or directory-fsync failure | One canonical record path remains the only authority; no sibling marker is created. |
| Attempted transition with a second record/marker present | Fail closed as corruption; do not guess precedence. |
| Output changes immediately before or after final validation | Ownership/no-replace control blocks it, or the mismatch retains the record; success is impossible. |
| Foreign output appears during rollback | Preserve it byte-for-byte; retain the record; do not unlink or overwrite it. |
| Existing exact content-addressed output | Idempotent reuse after digest verification. |
| Existing wrong bytes under the content-addressed name | Conflict; preserve bytes; no canonical publication. |
| Missing each required child | Read-only rejection; inventory remains unchanged. |
| File at each required child | Read-only rejection. |
| Symlink/junction/reparse at each required child | Read-only rejection on Windows and portable equivalents. |
| Parent alias with six physical children | Accept and canonicalize to the approved resolved root. |
| Source or target physical identity changes under lock | Reject before publication; retain `prepared` if already created. |
| Second restore writer | Reject before mutation. |
| CommandService crash after restore clear and before command append | Bound store remains valid; retry appends the command once. |
| CommandService crash during restore publication | Same transaction-record recovery as CLI; ordinary binding load rejects. |
| Missing, stale, revoked, forged, or wrong-scope grant | Reject before publication and on policy-required retry recheck. |
| Coordinated manifest/evidence rewrite | Independent approved inputs and raw-byte joins reject it. |
| Evidence produced from the values it validates | Contract test rejects self-attested expected-side construction. |

## 12. Preserved candidate work

The following directions in `3d5a1a7` are retained:

- `ControlBinding.load` uses read-only existing-root validation;
- all six required children are checked;
- child symlink/reparse rejection and parent-alias acceptance are required;
- source and target layout are rechecked in finalization;
- canonical evidence, raw target-manifest bytes, and output identity are checked
  together; and
- restore locks remain deterministic and include the output authority boundary.

The following candidate mechanisms are superseded:

- `.restore-binding-journal.json` → `.restore-binding-recovery.json` renaming;
- deletion of recovery authority as the commit/clear protocol;
- callback-counted final validation over a mutable output path;
- rollback through `_restore_exact_path` without mutation-seam ownership; and
- any journal-less `rebind_restored_store` caller.

## 13. Implementation boundary and exit

A remediation may change only the restore state machine, its CLI/CommandService
integration, binding/evidence fields required by this design, and decisive
tests. It must preserve the accepted M-01/M-02 behavior and unrelated store,
replay, provider, research, Jira, PR, and Gate 6 state.

Implementation is complete only when:

1. the complete negative matrix has direct controls at the exact corrected
   subject;
2. the real CLI and CommandService callers share the same record;
3. no normal loader accepts a non-`cleared` restored state;
4. an independent exact-subject review returns `accept_exact_subject`; and
5. any later owner/Gate 6 decision is recorded separately.

This document does not authorize remediation, integration, merge, dispatch,
pilot initialization, or Gate 6 acceptance.
