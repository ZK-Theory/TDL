# WP6.4 restored-store transaction/binding correction — exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 1 Critical, 2 Major, 0 Minor.

This is a fresh, independent, read-only review of the exact candidate. It is
not owner acceptance, PR or merge evidence, Gate 6 acceptance, CodeRabbit
evidence, authorization to dispatch research, or authorization to remediate
the candidate.

## Exact review identity

- Review worktree: `C:\Users\steph\.codex\worktrees\7b17\TDL`
- Review branch: `codex/review-wp64-store-restore-ebc4259`
- Candidate: `ebc42596fc4bc7b95fb380e6bbece5efde0f742d`
- Expected parent: `87e521beee53e76fb522eeb1ba61b4173337dd54`
- Expected tree: `de59d92335c29d25a35902d1766a61ba7fff6203`
- Producer remote: `origin/codex/wp64-store-restore-binding-r5`
- Producer remote equality: exact candidate SHA
- Candidate parent/tree equality: exact expected parent/tree
- Exact delta: five paths only
  - `research_system/cli.py`
  - `research_system/config.py`
  - `research_system/store/identity.py`
  - `research_system/store/layout.py`
  - `tests/research_system/integration/test_external_assurance_record_cli.py`

The detached start was verified against the pre-created review branch ref and
the candidate before one deterministic switch to the review branch. After the
switch, cwd, branch, HEAD, parent, tree, ancestry, producer remote, complete
checkout, and clean status were rechecked. No producer or foreign worktree was
edited.

## Executive disposition

The candidate materially improves the prior subject. It makes approved-binding
loading reject absent, partial, and wrong-type store layouts without creating
or repairing them; it adds output checks at several earlier publication seams;
and its bounded crash controls recover the manifest/evidence transaction at the
tested process-exit boundaries.

It does not establish the required transaction invariant. The final output
check is not atomic with journal removal. An external replacement immediately
after the new `post_commit` check produces a successful command with a rebound
target manifest, durable success evidence, foreign configuration bytes, and no
recovery journal. A journal-durability failure after unlink likewise produces a
failed command with rebound manifest/evidence and no recovery authority. The
approved-binding layout check also accepts a foreign directory reparse/symlink
for `objects`, and the already-bound retry path still repairs a missing target
directory through the sibling `ControlBinding.load` path before preflight can
reject the damaged target.

The candidate remains quarantined. It must not be integrated or treated as a
closed WP6.4/Gate 6 handoff. Any correction requires a new exact subject and a
fresh independent review.

## Findings

### C-01 — Final output staleness and journal-clear failure can leave committed success state without recovery

**Claim.** The restore transaction must not clear its recovery authority until
the output/configuration, target manifest, and canonical evidence are all
still mutually bound; a failed or externally invalidated finalization must not
leave rebound state and success evidence with no journal.

**Direct current-code evidence.**

- `research_system/cli.py:494-511` implements the new `post_commit` check: it
  loads the published config, rechecks its bytes and identity, and checks
  canonical durable evidence.
- `research_system/store/identity.py:947-969` commits the output, validates it,
  replaces the target manifest, publishes evidence, and then invokes
  `post_commit`.
- `research_system/store/identity.py:978-985` exits the transaction cleanup and
  clears the journal after `post_commit` returns. There is no final output or
  manifest revalidation between the callback return and journal removal.
- `research_system/store/identity.py:469-474` unlinks the journal before
  confirming directory durability; a durability error can therefore be raised
  after the recovery authority has already disappeared.

**Concrete reachable failures.**

1. In a temporary restore case, the independent probe replaced the output with
   foreign canonical binding bytes immediately before calling the real
   `clear_restore_binding_journal`. The candidate returned `0` and printed
   `status=bound`, while the target manifest had `control_root=target`, the
   canonical evidence existed with `operation_status=bound-and-config-published`
   and `durability_status=durable`, the output was foreign, and the journal was
   absent. The replacement occurred after `post_commit` had already validated
   the expected output.
2. A second bounded probe made the journal-clear seam unlink the journal and
   then raise a simulated durability error. The command raised
   `ArsError`, while the target manifest was rebound, success evidence existed,
   the expected output remained present, and no journal remained.

**Impact.** The first path lets foreign configuration bytes be reported as a
successful restore with durable evidence that no longer describes the output;
the second path leaves a failed command with committed-looking target/evidence
state and no deterministic recovery authority. This violates the core
authority/evidence invariant at the irreversible journal-removal boundary.

**Disposition.** Fix now; reject this candidate for integration. Keep the
transaction recoverable through the final externally observable validation, and
do not classify a journal as cleared until durable removal has a defined
success/failure protocol that cannot report a failed committed state.

**Exact proposed interface/lifecycle change.** Define one finalization primitive
whose commit point is explicit and whose post-publication checks are included in
the recoverable state machine. It must either (a) keep the journal until a
final exact output/manifest/evidence identity check and durable journal removal
have both succeeded, with a retained conflict marker when the output changes,
or (b) record a durable committed/recovery state that remains authoritative if
journal removal itself fails. Add controls for replacement after `post_commit`,
replacement immediately before journal clear, and clear-after-unlink durability
failure; assert command outcome, manifest bytes, evidence bytes, output bytes,
journal/marker state, and retry behavior together.

**Affected decisions/work packages.** WP6.4 restored-store binding and recovery
transaction; Gate 6 preflight eligibility; the CLI restore-bind seam;
`CommandService._recheck_moved_restore` because it shares
`finalize_verified_restore_binding`; any acceptance decision that relies on
`bound-and-config-published` evidence.

### M-01 — Already-bound retry validation still mutates a damaged target store

**Claim.** Every restore read/validation path must reject a missing or partial
target store without creating its required directories.

**Direct current-code evidence.**

- `research_system/cli.py:393-399` calls `_load_restore_output` on an
  already-bound retry before the new writer preflight.
- `research_system/cli.py:277-283` makes `_load_restore_output` call
  `ControlBinding.load`.
- `research_system/config.py:202-208` makes `ControlBinding.load` call
  `require_external_control_root`.
- `research_system/store/layout.py:50-54` shows that helper creating all six
  child directories with `mkdir(..., exist_ok=True)`.

**Concrete reachable failure.** After a successful restore-bind, the probe
removed `target/objects` and retried the same command. The retry recreated the
missing `objects` directory, then failed with
`ArsError: restore preflight is not verified: source_snapshot_mismatch,
verification_authority_mismatch`. The filesystem inventory changed from 21 to
22 entries despite the command being a rejecting validation path.

**Impact.** A failed retry repairs the object it was supposed to validate and
can erase the distinction between a physically incomplete restore and an
initialized store. The mutation also occurs before the preflight failure is
reported, so the caller cannot use the rejection as exact no-mutation evidence.

**Disposition.** Fix now; reject this candidate for integration. Split
initialization from validation for the whole restore call graph, not only for
`ApprovedProjectBinding.load`.

**Exact proposed interface/lifecycle change.** Add a read-only binding/load
  seam for restore retries (or require `require_existing_control_root` in every
  restore-side `ControlBinding.load` call), and reserve
  `require_external_control_root` for explicit store initialization. Add a
  retry negative that removes each required directory in turn, proves the
  complete target inventory and bytes are unchanged after rejection, and checks
  both the CLI path and the `CommandService` moved-restore path.

**Affected decisions/work packages.** WP6.4 read-only restore/rebind boundary;
target preflight and retry semantics; the CLI `_load_restore_output` path;
`ControlBinding.load` callers that are validation-only; Gate 6 rollback
evidence.

### M-02 — Required child-directory validation accepts a foreign physical `objects` directory

**Claim.** An approved external store must bind all required store directories
to the approved physical control-root layout; a directory symlink/junction or
other foreign reparse target must not satisfy the `objects` requirement.

**Direct current-code evidence.**

- `research_system/config.py:136-146` now routes approved binding loading
  through `require_existing_control_root` before loading the manifest.
- `research_system/store/layout.py:7-14` defines `objects`, `events`,
  `manifests`, `receipts`, `snapshots`, and `runtime` as required directories.
- `research_system/store/layout.py:64-69` checks only `control.is_dir()` and
  `(control / name).is_dir()`; it does not establish that each child is a
  physical child of the approved root or reject a reparse/symlink escape.
- `research_system/store/objects.py:252-287` and
  `research_system/assurance/external_records.py:426-439` consume the
  `control_root/objects` path after the binding is accepted.

**Concrete reachable failure.** On this Windows host, the probe removed the
  approved source `objects` directory and replaced it with a directory symlink
  to a sibling foreign directory. `ApprovedProjectBinding.load` returned an
  approved binding with `accepted=true`; `objects.is_symlink()` was true and
  `objects.resolve()` pointed at the foreign directory. The inventory and
  bytes were unchanged by the loader, so the no-mutation check alone did not
  detect the authority escape. A wrong-type file was rejected and preserved,
  confirming that the missing control is physical identity rather than the
  basic type check.

**Impact.** Subsequent object and external-assurance-record reads/writes use a
  directory outside the approved store root. A foreign actor can therefore
  supply or receive object revisions while the manifest and foundation still
  appear identity-consistent. This weakens the external-store and authority
  boundary on Windows reparse-capable filesystems.

**Disposition.** Fix now; reject this candidate for integration. Preserve the
  read-only behavior while making the child-layout identity check physical and
  fail closed.

**Exact proposed interface/lifecycle change.** For every required child,
  reject reparse/symlink/junction targets and verify its final physical parent
  identity is the approved control root (using a Windows-safe final-path or
  file-identity check, with a portable equivalent). Add controls for missing,
  regular-file, directory-symlink/junction, parent alias, and valid-directory
  cases, recording the complete inventory and bytes before and after each
  rejection.

**Affected decisions/work packages.** P-020 storage externality; WP6.4
  approved foundation binding; object-store and external-assurance-record
  consumers; Windows/reparse-point acceptance criteria for Gate 6.

## Caller and sibling-path closure

The governing seam is not limited to the edited helper:

| Surface | Current callers/consumers | Review disposition |
|---|---|---|
| `ApprovedProjectBinding.load` | `cli._load_canonical_approved_binding` at `research_system/cli.py:214-219`, called before the lock at `:336` and reloaded under the lock at `:373`; direct integration negatives at `tests/.../test_external_assurance_record_cli.py:351-399` | Missing/partial/wrong-type/no-creation controls pass; foreign child physical identity remains M-02. |
| `finalize_verified_restore_binding` | CLI `restore-bind` at `research_system/cli.py:513`; `CommandService._recheck_moved_restore` at `research_system/command/service.py:269` | Both route through `rebind_restored_store`; CLI supplies journal/output callbacks. C-01 covers the shared finalization lifecycle and requires both callers to be rechecked. |
| `rebind_restored_store` | `finalize_verified_restore_binding` at `research_system/operations/backups.py:1049`, plus direct unit callers | Earlier output/manifests/evidence/crash controls are bounded; the final journal-clear seam is not atomic (C-01). |
| `ControlBinding.load` | Restore output validation at `research_system/cli.py:278` and `:496`, plus ordinary submit/assurance/evaluation loaders | Its initializer helper at `research_system/config.py:202-208` is unsafe for the restore-side read paths; target retry repair is M-01. Ordinary initialization callers were not treated as restore validation evidence. |

## Invariant-to-enforcement matrix

| Invariant | Enforcement point | Direct controls/evidence | Result |
|---|---|---|---|
| Approved foundation has an existing complete layout and does not repair absence | `config.py:136-146`; `layout.py:57-70` | Absent, partial, missing-`objects`, and wrong-type probes; inventory/bytes preserved | Partial: M-02 foreign child escape remains |
| Output bytes and identity match the approved foundation | `cli.py:287-330`, `:486-511`; `identity.py:947-969` | Publication swap, journal-phase swap, prepublication swap, and valid restore controls | Partial: C-01 final callback-to-clear interval remains |
| Target manifest/evidence/config publication is rollback-safe | `identity.py:918-985`; journal recovery `:518-648` | Manifest process-crash control passed; pending-evidence promotion passed; direct clear-failure probe failed | Failed at the irreversible journal-clear boundary (C-01) |
| Read-only validation leaves target layout unchanged | `config.py:202-208`; `cli.py:393-399` | Missing target `objects` retry probe | Failed: M-01 |
| Required store directories are physically within the approved root | `layout.py:64-69` | Windows directory-symlink probe | Failed: M-02 |

## Preserved controls and validation evidence

The direct pre-existing interpreter was used:
`C:\Users\steph\TDL\.venv\Scripts\python.exe` (Python 3.13.5), with
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, no coverage
plugin, `-p no:cacheprovider`, and repository addopts disabled. Temporary stores
and all probes were outside the repository. No provider, credential, transport,
live research record, fabricated grant, or production-foundation owner bundle
was used.

Passing bounded checks included:

- absent approved store without creation: 1 passed;
- partial and valid-manifest/missing-`objects` approved stores: 2 passed;
- foreign-output swaps at publication and already-bound retry seams: 2 passed;
- valid restore-bind after verified preflight: 1 passed;
- manifest-publication process crash/restart recovery: 1 passed;
- pending evidence promotion: 1 passed;
- wrong-type child rejection and no-byte-mutation: direct probe passed;
- foreign `objects` directory symlink acceptance: direct probe reproduced M-02;
- target retry directory repair: direct probe reproduced M-01;
- final output replacement before journal clear: direct probe reproduced C-01;
- journal unlink followed by durability failure: direct probe reproduced C-01.

`git diff --check` passed. The candidate delta contains no changes under
`.research-system`, `contracts`, or the `docs/plans/agentic-research-system`
`06*` implementation/design surfaces. The complete checkout was clean before
and after validation. The full focused test file, and the two slow selected
pre-publication controls, exceeded the bounded execution window and are not
counted as passing evidence; the direct current-code probes above are the
decisive evidence for the two unresolved mechanisms.

## Decision audit and revision disposition

| Candidate decision/mechanism | Disposition |
|---|---|
| Keep a journal-backed restore transaction | Keep the direction; amend the final commit/recovery state machine for C-01. |
| Use a read-only existing-root check for approved foundation loading | Keep the direction; amend it for physical child identity and all restore-side sibling loaders (M-01/M-02). |
| Publish config, target manifest, and evidence as one accepted restore result | Reject the current acceptance claim; it is not established across the final output/journal seam. |
| Treat this exact candidate as accepted | Reject/quarantine; no Gate 6 or owner acceptance credit. |

## Required next review boundary

1. Correct the final journal-clear/commit protocol and add the three negative
   controls named in C-01.
2. Route every restore-side read through a non-mutating complete-layout check;
   add target retry controls for every required directory.
3. Bind every required child directory to the approved physical root and add
   Windows reparse/symlink controls, including `objects`.
4. Re-run the exact changed-behavior tests plus the bounded crash/recovery
   matrix at the corrected candidate head, then provision a fresh exact-subject
   independent review. Do not amend or merge this review subject in place.

No source or test remediation was performed by this review. The only intended
write from this review is this durable review record.

