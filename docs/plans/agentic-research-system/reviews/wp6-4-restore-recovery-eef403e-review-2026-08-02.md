# WP6.4 restore-recovery state-machine correction — exact-subject review

**Date:** 2026-08-02 (Europe/London)

**Verdict:** `rework_required`

**Findings:** 4 Critical, 2 Major, 0 Minor

This is a fresh independent review of the exact implementation subject. It is
not producer self-report, owner acceptance, PR or merge evidence, CodeRabbit
evidence, Gate 6 acceptance, or authority to remediate or dispatch. Passing
tests are supporting evidence only; they do not override the independently
reproduced durability and admission failures below.

## 1. Exact review identity

| Identity | Exact value |
|---|---|
| Review worktree | `C:\Users\steph\.codex\worktrees\6570\TDL` |
| Review branch | `codex/wp64-restore-recovery-r7-review` |
| Candidate | `eef403e88b997a01168553174114aebb8b05b62a` |
| Required parent | `1bd4a4c671aa62abdfbafb0e1aea1e11155f963c` |
| Candidate tree | `bf2980fff39f68269202965a6737ff98d0c6c240` |
| Live remote before review-record write | `origin/codex/wp64-restore-recovery-r7-review` = exact candidate |
| Candidate delta | exactly 9 paths; 1,776 insertions and 1,780 deletions |

The worktree started detached. Detached `HEAD`, the named local review ref,
the remote-tracking ref, and the live fully qualified remote ref all resolved
to the exact candidate before one deterministic switch to the existing review
branch. The candidate has the required sole parent, the required tree, and a
clean worktree; the parent is an ancestor. No fallback branch, rename,
detached commit, force push, producer-history acceptance, or foreign-worktree
write was used.

## 2. Authorities and protected identities

| Authority | Candidate blob | Review use |
|---|---:|---|
| Decision register, including P-020/P-031/P-036/P-042 | `552183b39e70cf4b105346bdd7f747496a792e85` | Single external canonical writer; separate planning, owner, and Gate 6 authority |
| Original Gate 6/pilot plan | `3e823d14cd61a02506663ba44730c95cfa8cf7ba` | Deterministic recovery and rollback without rewriting accepted evidence |
| WP6 Gate 6 master plan | `3d0b24bb003d856ccf477c2cb910df3d885fc0b2` | WP6.4 binding and separate preflight acceptance boundary |
| Owner-operated-session amendment | `49696e5b737f59ab8bd58d18c6e9231b0a61a599` | Exact-subject/operator boundary; no provider automation |
| Owner acceptance of 06g | `6c9d64cf04f00819f0b4c81b9e248b31ca1940c2` | Planning authority only |
| Adjudicated restore state-machine design 06n | `bacb3325d0f232098627301e05ade1f1663441f8` | Normative Option B plus necessary C contract |
| Prior exact-subject review of `3d5a1a7` | `38e4f5a8679e818ec24ffabbebf95d17983a2ca0` | Findings were independently re-tested, not inherited |
| Prior `ebc4259` review at its durable review commit | `31f04348d892992aa730b5648f748769206dd824` | M-01/M-02 and the original finalization defect |

The parent and candidate have identical protected trees:

- `.research-system/schemas`: `9748096b435951acbc8d36d58d500dc89907fc80`;
- `.research-system/contracts`: `27f1e12e8ecfb5c6fb33377981a96410555cbd56`;
- ARS implementation/design documents: `cfbbab500ba11a089a78c7fcb0436db0502d0f06`;
- pre-existing ARS review records: `e89f70c449806fa5082d7cb9226a63db533bafb7`.

The protected catalogue blobs are also identical parent-to-candidate:

- `.research-system/evals/catalogue.yaml` — `98f6413d49606e7553e74cd2fb24f914b087f133`;
- WP6.1 owner-source catalogue — `1adc66921ee9c90d8786ff173748150922f1035e`;
- WP6.2 T2 authority catalogue — `ddc142344278d4628b8e70d5de1c5924896600d1`;
- WP6.2 T3/T4 live-issue catalogue — `7e0cd065b8522fbebe3b8e85f5ec7f201e587175`;
- 06d owner-source catalogue plan — `eab2eca016583841bc620690a1b29fa7266bf239`.

No schema, contract, catalogue, design, prior review, `foundation.yaml`, Jira,
provider, credential, Gate 6, or external-assurance semantic source changed.

## 3. Complete candidate scope

The complete parent-to-candidate path set is:

1. `research_system/cli.py`
2. `research_system/command/service.py`
3. `research_system/config.py`
4. `research_system/operations/backups.py`
5. `research_system/store/identity.py`
6. `tests/research_system/integration/test_external_assurance_record_cli.py`
7. `tests/research_system/integration/test_gate5_release_tranche.py`
8. `tests/research_system/unit/test_replay.py`
9. `tests/research_system/unit/test_store.py`

The complete diff and real CLI, `CommandService`, preflight, finalization,
binding-load, retry, and cleanup call graph were inspected. `git diff --check`
passed.

## 4. Executive disposition

The candidate replaces the journal/marker pair with one canonical record,
publishes a store-owned content-addressed output, routes the CLI and
`CommandService` through the shared transaction, retains a durable `cleared`
record, and makes normal loaders reject visible non-`cleared` records. The
focused controls for the four prior Critical vehicles pass: post-validation
canonical-output mutation is detected, foreign bytes present before cleanup
are preserved, transition replacement creates no sibling authority, and a
CommandService crash during manifest publication is rejected by the loader.

Those changes do not establish the adjudicated invariant. On this native
Windows host, directory fsync is unsupported by the implementation, but each
failed attempt mutates visible state before reporting the durability failure.
Eighteen repeated retries ratcheted the record through every labelled state
and the eighteenth returned success although `_fsync_directory` was false on
every attempt. This is a false durability claim, not a supported fail-closed
platform limitation.

Loader admission also remains provenance-incomplete: it can classify a
target-bound manifest with no restore proof as never restored, and its cleared
join takes expected values from the same mutable transaction being checked.
Two additional crash/ownership controls fail: a crash before `prepared`
publication strands an unowned generation that later conflicts with admission,
and cleanup can delete a foreign replacement between its byte comparison and
unlink. A nested output-ancestor reparse can be carried through `cleared`.

The exact candidate therefore remains quarantined. It must not be integrated,
represented as WP6.4 closure, or used to support A8, SCALE-01, or Gate 6.

## 5. Findings

### C-01 — Critical — Repeated Windows retries convert unsupported directory durability into success

**Claim.** Every labelled transition, especially `cleared`, must be recorded
only after its directory entry is known durable. If the platform cannot prove
that property, every attempt must remain fail-closed; retry must not treat the
visible but non-durable mutation as completed.

**Direct evidence.** `_fsync_directory` uses `os.open(directory, O_RDONLY)` and
`os.fsync` at `research_system/store/identity.py:180-201`. On this Windows host
the direct OS-temporary probe returned `False`. The implementation nevertheless
hard-links the initial record before checking the directory result at
`identity.py:615-631`, replaces every later generation before checking it at
`:635-672`, and unlinks temporaries before checking cleanup durability at
`:594-603`. The next invocation trusts the visible `state`, `generation`, and
`last_completed_durability_step` at `:444-476`. A visible `cleared` record
returns through `:1133-1139` without any new directory-durability operation.

**Concrete failure scenario.** A bounded OS-temporary probe used the real
candidate and the host's real `_fsync_directory` result. Attempts 1–17 each
raised a durability error while the record advanced through
`prepared-record-durable`, output, manifest, evidence, `published`,
`final_validated`, `committed`, and finally `cleared`. Attempt 18 returned the
target-bound manifest successfully. A subsequent admission check also passed.
Directory fsync returned `False` throughout.

**Impact.** The transaction can report complete recoverable success without
establishing any of the directory-entry durability on which the monotone state
machine depends. A crash may therefore lose a supposedly committed record or
publication while evidence says `durable` and recovery authority says
`cleared`. This crosses the authority/evidence boundary and makes deterministic
recovery unprovable.

**Disposition.** Fix now; reject this exact subject.

**Required interface/lifecycle change.** A durability failure must not become a
trusted completed step on retry. Implement a Windows-capable directory-entry
durability primitive or keep the platform permanently non-successful. Recovery
must distinguish an observed-but-unconfirmed generation and re-establish its
durability before using it. Add a repeated-failure negative that holds directory
durability false across every retry and proves success is impossible.

**Affected decisions/work packages.** 06n C-01 and sections 5.1/6/7/10/11;
P-020; WP6.4 deterministic recovery; CLI and CommandService restore paths; Gate
6 recovery evidence.

### C-02 — Critical — Missing restore proof downgrades a rebound store to ordinary initialized state

**Claim.** A target-bound manifest produced by restore cannot be admitted as a
never-restored store merely because the transaction, evidence, and output are
absent. The loader must distinguish initialization identity from a partially
rebound or stripped restore.

**Direct evidence.** The rebound manifest changes `control_root` to the target
at `identity.py:1058-1061`. With no transaction, admission checks only evidence,
matching output objects, and transition temporaries before returning ordinary
state at `identity.py:1255-1267`; it does not test whether the manifest is a
record-less rebound. `ControlBinding.load` accepts that result at
`research_system/config.py:203-210`.

**Concrete failure scenario.** In an OS-temporary copied store, the review
rewrote only the manifest's `control_root` and canonical hash to the target,
leaving no transaction, restore evidence, or output object. `ControlBinding.load`
accepted the target-bound store. This recreates the authority outcome of the
prior journal-less manifest-publication crash without using the now-removed
optional finalizer.

**Impact.** Removing or losing the durable restore proof changes a restored
store's authority class from restored to ordinary and permits normal command
use without canonical restore evidence. The `cleared` tombstone is therefore
not durable admission authority.

**Disposition.** Fix now; reject this exact subject.

**Required interface/lifecycle change.** Give initialized and restored stores
independently verifiable, non-ambiguous origins. Loader admission must reject a
target-bound/rebound manifest when the required restore tombstone and tuple are
absent; deleting the proof must never broaden admission.

**Affected decisions/work packages.** 06n C-01/C-02 and sections 8/9/11; prior
C-03; P-020; `ControlBinding` and `ApprovedProjectBinding`; CommandService
restart; WP6.4/Gate 6 provenance.

### C-03 — Critical — Cleared admission certifies evidence against a mutable self-attested record

**Claim.** The expected side of the cleared tuple must be re-derived from the
approved foundation, receipt, source replay/snapshot, and preflight evidence;
it cannot come solely from the transaction record whose integrity is being
decided.

**Direct evidence.** `_validate_restore_join` compares live manifest, evidence,
and output to bytes and identities embedded in the same transaction at
`identity.py:920-953`. Admission at `:1255-1273` supplies no independent
approved inputs and does not re-derive `canonical_restore_binding_output`.
`prior_record_sha256` is only shape-checked at `:474-476`; no surviving or
external predecessor anchors it.

**Concrete failure scenario.** After a valid cleared restore, a bounded
OS-temporary probe coordinated changes to the record and evidence, including
actor/grant identity and the record's intended-evidence bytes/digests. The
manifest remained unchanged. `verify_restore_binding_admission` accepted the
rewritten tuple. The same construction can coordinate output bytes/path/digest
because those expected values also come from the rewritten record.

**Impact.** A writer capable of replacing the proof files can mint a new
internally consistent cleared tuple without the independently approved source,
receipt, grant, or output derivation. Strict comparisons then certify the
producer against itself and allow invalid restore authority.

**Disposition.** Fix now; reject this exact subject.

**Required interface/lifecycle change.** Anchor cleared admission to an
independent immutable approval identity or re-derive every expected field from
approved sources supplied to the loader. Add coordinated record/evidence/output
mutations, including actor, grant, receipt, source snapshot, and canonical
output, with the manifest both unchanged and coordinated.

**Affected decisions/work packages.** 06n E-01/C-01 and sections 5.3/7/9/11;
P-020; binding loaders; restore evidence; WP6.4/Gate 6 authority.

### C-04 — Critical — Crash before `prepared` publication strands an unowned generation and splits finalization from admission

**Claim.** A crash before `prepared` durability must leave no canonical mutation
and must be safely retryable. A later finalizer must not return success for a
state that the ordinary loader rejects.

**Direct evidence.** `_write_initial_transaction` fsyncs a generation temporary
before linking the canonical record at `identity.py:615-631`. A failure between
those operations leaves no canonical record. The next attempt observes no
record at `:1028-1033`, creates a new transaction ID at `:1062`, and ignores the
orphan. The immediate committed-to-cleared path at `:1240-1251` does not call
the temporary-closure check used later by admission at `:957-962` and `:1270`.

**Concrete failure scenario.** A bounded probe failed only the initial hard
link after the generation temporary was fsynced. The manifest remained
unchanged, the canonical record was absent, and one
`.restore-binding-transaction.<old-id>.0.tmp` remained. The next unmodified
retry returned a target-bound result and recorded a new transaction as
`cleared`; the old temporary remained. `verify_restore_binding_admission` then
rejected the store with `cleared restore binding retains a transaction
temporary`.

**Impact.** The shared finalizer can report completion while the normal loader
rejects the same store, and there is no deterministic authority to adopt or
remove the pre-record orphan. In the CommandService seam this can occur before
ordinary command append and leave restart-invalid canonical state.

**Disposition.** Fix now; reject this exact subject.

**Required interface/lifecycle change.** Define recoverable ownership for the
initial generation before any orphan can exist, or make pre-record temporaries
uniquely discoverable and safely adoptable without deleting foreign state.
Require the same no-temporary closure before the first success return and on
all loaders. Add a process-exit control between initial temporary fsync and
canonical publication.

**Affected decisions/work packages.** 06n sections 5.1/7/8/11; C-01; CLI and
CommandService crash recovery; WP6.4 deterministic recovery.

### M-01 — Major — Temporary cleanup has no physical ownership seal and retains a compare/unlink race

**Claim.** Cleanup may unlink only the exact transaction-owned file identity at
the mutation seam, not merely a path whose bytes matched moments earlier.

**Direct evidence.** Transaction temporaries record only relative path and
SHA-256 at `identity.py:525-540` and `:867-879`. `_cleanup_owned_temporary`
reads bytes and then separately calls `unlink` at `:594-603`; no file identity,
open-handle deletion, or atomic ownership primitive seals the interval.

**Concrete failure scenarios.** First, replacing a recorded temporary with a
new same-byte inode was accepted and the foreign inode was deleted. Second, a
bounded compare/use probe replaced the name with different foreign bytes after
`_file_bytes` returned the expected bytes but before `unlink`; cleanup returned
without error and deleted the foreign replacement. The candidate regression at
`tests/research_system/integration/test_external_assurance_record_cli.py:892-920`
substitutes different bytes before the comparison, so it does not exercise
either surviving seam.

**Impact.** Recovery can delete state it does not own. The same mechanism is
used for transaction and output temporaries, so a crash/retry path can convert
an ownership conflict into silent destructive cleanup.

**Disposition.** Fix now; reject the cleanup mechanism.

**Required interface/lifecycle change.** Record and verify a stable physical
identity as well as bytes, and make comparison plus deletion one ownership-
sealed operation. If the platform cannot seal them, preserve the path and keep
the record live.

**Affected decisions/work packages.** 06n C-03 and sections 5.1/7/8/11; restore
rollback/retry; P-020 store ownership.

### M-02 — Major — A reparse ancestor can relocate the canonical output inside the store

**Claim.** Every canonical-output ancestor must be physical; containment within
the target root is insufficient when the accepted design explicitly rejects
symlink/junction/reparse substitution.

**Direct evidence.** `_record_path` resolves only for target containment at
`identity.py:247-255`. Output publication at `:702-726` and final joins at
`:920-953` then follow the accepted alias without an `lstat`/reparse walk.

**Concrete failure scenario.** In an OS-temporary target, the review made
`manifests/restore-bindings` a directory symlink to
`target/objects/binding-output-alias-target`. The unmodified restore returned a
target-bound result, reached `cleared`, passed
`verify_restore_binding_admission`, and placed the canonical output physically
under the symlink target. A stable outside-target alias is rejected; this
in-target reparse is the uncovered case.

**Impact.** The canonical output's physical namespace is not the namespace
recorded by the evidence. It can collide with a different store subsystem and
violates the Windows/output-ancestor identity rule, even though the lexical
path and digest remain internally consistent.

**Disposition.** Fix now; reject this output-layout implementation.

**Required interface/lifecycle change.** Validate every ancestor from the
physical target root to the final output with Windows reparse metadata and
physical-parent identity, both before publication and at final admission. Add
inside-target and outside-target symlink/junction controls.

**Affected decisions/work packages.** 06n sections 5.2/7/10/11; content-
addressed output ownership; WP6.4 Windows recovery.

## 6. Prior Critical re-review

| Prior defect | Exact-subject disposition |
|---|---|
| Mutable caller-selected output could change after final validation and still determine success | **Vehicle closed.** Canonical success now cites the store-owned digest path; the caller path is a best-effort projection. Focused four-state mutation control passed. C-01 and M-02 show the replacement mechanism is not yet acceptable. |
| Recovery could delete foreign final-output bytes | **Final-output vehicle closed; ownership invariant still open.** The final content-addressed object is not rollback-deleted, but M-01 reproduces foreign deletion at the transaction-temporary seam. |
| Journal-to-marker failure created two authorities | **Closed at this subject.** There is one canonical record; the focused replace-failure control passed and created no sibling marker. |
| CommandService could finalize without a journal and a partial manifest was loadable | **Journal-less caller closed; loader invariant still open.** The focused CommandService crash control passed for the new prepared-record path, but C-02 reproduces record-less target-manifest admission one level down. |

Closed M-01/M-02 physical layout behavior from the prior review is preserved:
`require_existing_control_root` remains read-only, all six direct children are
checked with `lstat` and reparse metadata, and a parent alias canonicalizes to
the physical root. The changed CLI loads/validates the target before constructing
normal consumers, and the changed CommandService retry rechecks the existing
layout before mutation. This disposition does not extend to the new nested
output namespace (M-02).

## 7. Invariant-to-enforcement matrix

| Design invariant | Candidate enforcement | Independent result | Disposition |
|---|---|---|---|
| Durable monotone `prepared → published → final_validated → committed → cleared` | Same-path link/replace plus `_fsync_directory` | Native false durability ratcheted to success; pre-`prepared` orphan split finalizer from loader | Failed: C-01, C-04 |
| `cleared` is durable revocation, never proof deletion/downgrade | Retained transaction record; admission checks visible state | Missing proof admitted a rebound manifest as ordinary state | Failed: C-02 |
| Store-owned content-addressed canonical output | Digest path plus no-replace hard link | Exact reuse/wrong-byte collision controls pass; nested reparse accepted | Partial: M-02 |
| Ownership-limited cleanup | Recorded path/digest plus byte check | Same-byte identity replacement and compare/unlink race deleted foreign state | Failed: M-01 |
| Evidence/manifest/output join has independent expected side | `_validate_restore_join` against record bytes | Coordinated record/evidence rewrite admitted | Failed: C-03 |
| All callers use one transaction | Required finalization inputs; CLI and CommandService shared call | Prior CommandService crash control passed | Satisfied for the corrected caller graph; C-02 remains a loader bypass |
| Normal loaders reject non-`cleared` and partial restored state | `verify_restore_binding_admission` | Visible non-cleared states reject; record-less rebound and self-attested cleared tuple admit | Failed: C-02, C-03 |
| M-01 read-only validation | Existing-root validator before changed-path consumption | Direct-child behavior preserved | Satisfied for the six required direct children |
| M-02 physical direct children and parent alias | `lstat`, reparse bit, physical-parent/same-file checks | Prior exact controls and unchanged layout implementation preserved | Satisfied for direct children; M-02 is a new nested-output gap |

## 8. Negative and coverage disposition

| Design negative group | Disposition at this subject |
|---|---|
| Crashes after each successfully labelled durable state | Candidate controls exist and the focused four-state output-mutation selector passed; they hook only after a successful fsync and do not cover C-01 |
| Crash before `prepared` durability/publication | Failed independently: C-04 |
| Persistent state-record/directory-fsync failure across retries | Failed independently on native Windows: C-01 |
| Existing exact/wrong content-addressed output | Candidate controls support exact reuse and preserve wrong bytes |
| Foreign output at cleanup mutation seam | Pre-comparison different-byte control passes; same-byte identity and post-comparison replacement fail: M-01 |
| Journal/marker ambiguity and second authority | Candidate controls pass; no sibling authority created |
| Missing/file/reparse each required direct child; parent alias | Preserved from the accepted prior subject and unchanged physical-child implementation |
| Output-ancestor reparse | Missing and independently failed: M-02 |
| Source/target physical drift and second writer | Candidate controls exist; no contrary evidence found |
| CommandService crash during restore and after clear/before append | New controls exist; the prior journal-less crash control passed |
| Missing/stale/revoked/wrong-scope grant | Real CLI/CommandService rederive authority on retry; governed revoked-retry control exists |
| Missing record plus partial rebound state | Failed independently: C-02 |
| Coordinated/self-attested evidence construction | Existing test changes manifest/evidence while leaving the record fixed; coordinated record/evidence expected-side control failed: C-03 |

## 9. Validation evidence

The direct interpreter was Python 3.13.5 at
`C:\Users\steph\TDL\.venv\Scripts\python.exe`. Repository bytecode, pytest
cache, addopts, coverage, and plugin autoload writes were disabled. All custom
stores and probes used OS temporary directories outside the repository.

| Check | Result |
|---|---|
| Cwd/branch/HEAD/parent/tree/ancestry/local ref/remote-tracking ref/live remote/clean status | Exact before review write |
| Complete `parent..candidate` inventory and diff | 9 paths; inspected |
| `git diff --check` | Passed |
| Native `_fsync_directory` probe | `False` on this Windows host |
| Persistent native durability retry probe | Attempts 1–17 failed while advancing; attempt 18 returned success; admission accepted — candidate invariant failed |
| Pre-`prepared` hard-link failure and retry | No record plus orphan after first failure; retry returned `cleared`; later admission rejected — candidate invariant failed |
| Cleanup compare/unlink race | Foreign replacement deleted without error — candidate invariant failed |
| Same-byte temporary identity replacement | Foreign inode deleted — candidate invariant failed |
| In-target output-ancestor symlink | Restore reached `cleared` and admission accepted physical output under the alias — candidate invariant failed |
| Record-less target-bound manifest | `ControlBinding.load` accepted — candidate invariant failed |
| Coordinated record/evidence expected-side rewrite | Admission accepted — candidate invariant failed |
| Prior-Critical focused selectors | 7 passed in four isolated runs: 4 state-mutation cases plus cleanup, transition-replace, and CommandService-crash controls |
| Larger named changed-behavior selection | Timed out after 604 seconds without a completed summary; not counted as passing evidence and not rerun after the decisive direct failure |

No package or full suite was run. The native Windows failure independently
decides the verdict, and broader green output cannot establish missing
durability or authority controls.

## 10. Decision audit and residual risk

| Mechanism/decision | Disposition |
|---|---|
| One canonical monotone transaction record | Keep the design; reject this durability/retry implementation (C-01/C-04). |
| Durable `cleared` audit tombstone | Keep the design; reject downgrade and self-attested admission (C-02/C-03). |
| Store-owned content-addressed output | Keep the design; add physical ancestor identity and independent expected-side derivation (C-03/M-02). |
| Ownership-limited cleanup | Reject current path+digest compare/unlink mechanism (M-01). |
| Read-only six-child physical validation | Keep; preserved at this subject. |
| Shared CLI/CommandService finalization | Keep the direction; do not accept until every crash/admission seam shares the same invariant. |
| Exact candidate accepted for integration | Reject/quarantine. |

The principal residual platform risk is native Windows directory-entry
durability. This candidate has no Windows-capable success primitive and, worse,
its retry behavior converts that unsupported capability into a success claim.
A correction must either implement and directly validate the platform primitive
or remain permanently fail-closed without ratcheting state. Filesystem reparse
and name-replacement races also remain live until physical identity is checked
at the output and deletion seams.

## 11. Exact verdict and authority boundary

**Verdict: `rework_required`.** The exact candidate
`eef403e88b997a01168553174114aebb8b05b62a` does not establish 06n's durable
monotone transaction, durable cleared authority, independent evidence join,
ownership-limited cleanup, or physical content-addressed output namespace.

This verdict does **not** bind or edit `foundation.yaml`, close A8, authorize
SCALE-01, accept Gate 6, authorize remediation, authorize merge, or perform an
owner decision. Any correction requires a new exact candidate and a fresh
independent exact-subject review.

No production or test remediation was performed. The only repository write by
this review is this record.
