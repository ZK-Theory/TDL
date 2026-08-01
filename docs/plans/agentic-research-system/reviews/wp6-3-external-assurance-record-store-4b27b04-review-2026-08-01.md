# WP6.3 external assurance-record recovery identity/residue correction exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 0 Critical, 0 Major, 1 Minor.

This is a fresh independent exact-subject review. It is not owner acceptance,
PR or merge evidence, Jira transition, Gate A/Gate 6 acceptance, production
multi-party materialization, or authorization to remediate the subject.

## Exact review identity

- Review worktree: `C:\Users\steph\.codex\worktrees\b6d3\TDL`
- Review branch: `codex/review-kan67-record-store-4b27b04`
- Reviewed candidate: `4b27b04f7a232fbc71097ff4c82587374016fc83`
- Expected parent: `f825629887d05bc906cc9719d622bee4a7a56f0a`
- Expected tree: `d1404ce05f173f9cac86b96e5ae809aae5f9a660`
- Producer remote: `origin/codex/kan67-external-assurance-record-store-r4`
- Producer remote, review branch, and `HEAD`: all equal the candidate SHA.
- Candidate delta: exactly
  `research_system/command/service.py` and
  `tests/research_system/integration/test_external_assurance_record_publication.py`.

Before the report write, the review confirmed the expected cwd, symbolic
branch, `HEAD`, parent, tree, ancestry, producer remote, clean index/worktree,
zero missing tracked files, and 3,432 physically materialized tracked paths.
The named review record was absent from both the working tree and candidate
tree.

## Executive disposition

The candidate closes both predecessor findings that it claims to correct:

1. The recovery marker now records the event schema's independently resolved
   raw-source SHA-256, and restart, exact retry, and marker reconstruction
   reject a same-ID/version schema replacement before event/object/receipt or
   residue mutation.
2. Committed-marker cleanup classifies all candidate temporary residue before
   unlinking the final marker. A valid foreign temporary preserves the final
   marker and all residue, and the receipt-reconstruction exact retry converges
   after that foreign item is removed.

One bounded lifecycle gap remains. If the process terminates after the scoped
   receipt is written but before marker cleanup, an exact retry returns the
   stored receipt before it reaches marker-status classification or cleanup.
   The marker therefore remains, and a valid foreign temporary can remain
   unclassified on that receipt-present retry. This does not corrupt the event
   or object, so it is Minor, but it leaves recovery residue non-convergent
   through the exact retry path and prevents acceptance of this subject.

## Finding m-01 - receipt-present retry bypasses committed-marker cleanup

**Severity:** Minor

**Claim tested:** Every exact retry of a committed scoped activation must either
classify its marker residue before cleanup or return only after the committed
marker has been safely resolved. A stored scoped receipt must not bypass the
recovery-marker lifecycle.

**Direct current-code evidence:**

- `research_system/command/service.py:827-829` calls
  `_scoped_authority_receipt(command)` and returns immediately when a scoped
  receipt exists, before the marker status is read at `:840-849`.
- The normal success path writes the receipt at
  `research_system/command/service.py:1066-1075` and only then removes the
  marker. A process termination between those operations is reachable.
- Marker cleanup and foreign-residue classification occur later in
  `_remove_scoped_activation_marker` at
  `research_system/command/service.py:428-455`; that function is not reached
  on the receipt-present early return.
- The added positive test at
  `tests/research_system/integration/test_external_assurance_record_publication.py:683-716`
  deletes all receipts before retry, so it exercises receipt reconstruction,
  not this receipt-present path.

**Concrete reachable failure:** An independent production-class probe made
`_remove_scoped_activation_marker` raise `KeyboardInterrupt` after the
scoped receipt had been written. The subsequent exact retry returned the
stored accepted receipt while `marker_remains_after_exact_retry=true` and
`receipt_present=true`. With a valid foreign marker temporary present, the
same early return also returned the receipt without raising the required
temporary-data conflict; the final marker and foreign temporary remained.

**Impact:** The committed marker remains a stale recovery authority after an
exact retry, and a valid foreign temporary can remain hidden until a later
restart. The event, grant object, and receipt remain internally consistent;
the defect is recovery cleanup/liveness rather than authority corruption.

**Disposition:** Fix now in the next exact subject. For both
`ActivateAuthorityGrant` and `ActivateExternalAssuranceRecordGrant`, route a
receipt-present retry through committed-marker status and residue
classification before returning, or perform an equivalent marker cleanup
after the receipt has been reconciled. Preserve the current rule that a valid
foreign temporary raises without deleting the final marker or any residue.
Add a deterministic crash-after-receipt control with (a) no residue, (b) a
matching valid temporary, and (c) a valid foreign temporary; require exact
retry to classify residue and converge after foreign-residue handling.

**Affected paths:** `_scoped_authority_receipt`, the marker status/cleanup
branches in `CommandService.submit`, `_remove_scoped_activation_marker`, and
both activation command types in `_SCOPED_ACTIVATION_COMMAND_TYPES`.

## Predecessor finding closure

| Predecessor finding | Current evidence | Disposition |
|---|---|---|
| `f825629` M-01: event-schema ID/version did not bind raw bytes | `service.py:294-315` resolves the current registry binding and raw identity; `:346-371` records the resolved digest; `:643-651` validates the marker before event classification; the 13-test changed-surface run and independent marker/schema probes rejected same-ID/version replacement with no mutation | Closed for this subject |
| `f825629` m-01: final marker was deleted before a valid foreign temp was discovered | `service.py:428-455` scans and classifies all candidate residue before `path.unlink`; the foreign-temp test at `test_external_assurance_record_publication.py:720-784` preserved final marker and residue on conflict, then removed the foreign item and completed exact retry | Closed for the exercised receipt-reconstruction path |

## Identity and independence attack

The expected and observed sides are independently sourced:

- The expected event-schema identity is obtained from the trusted
  `SchemaRegistry.event_binding` and a fresh `resolve_identity` call at
  `service.py:294-314`; it is not taken from the marker's digest.
- The observed side is the persisted marker's `prepared_identity` at
  `service.py:306-315`, and the ledger side is independently read from
  `self.ledger.snapshot().events` at `:643-661`.
- The event-schema negative uses two separately constructed schema roots with
  the same schema ID/version and different raw bytes. A separate probe
  tampered the marker's stored event-schema digest itself; restart rejected it
  with `ConflictError`, preserved the marker and all durable bytes, and left
  the object at revision 1 with no activation event.
- A marker-reconstruction probe moved a valid old-schema marker to
  `command-id.json.tmp`, replaced the same-ID/version event schema, and retried
  with a fresh registry. It rejected with `ConflictError`, preserved the valid
  temp and all durable bytes, and emitted no event.

## Sibling and lifecycle closure

The shared marker rules were enumerated across the complete current call
surface:

| Rule | Shared enforcement | Governed sibling paths |
|---|---|---|
| Event-schema raw identity | `_write_scoped_activation_marker`, `_load_scoped_activation_marker`, `_validate_scoped_activation_marker_event_schema`, `_scoped_activation_event_status`, and startup recovery | `ActivateAuthorityGrant` → `ScopedAuthorityGrantActivated`; `ActivateExternalAssuranceRecordGrant` → `ExternalAssuranceRecordGrantActivated` |
| Marker reconstruction and exact retry | preloaded-marker validation at `submit:797-806`, marker write at `:969-1000`, and status handling at `:840-866` | Both activation commands; typed revocation commands are adjacent administration controls but do not use activation markers |
| Final-marker/residue ordering | `_remove_scoped_activation_marker` called from committed, competing, successful, and exception/recovery branches | Both activation commands and startup recovery; invalid temps are quarantined only after valid residue has been classified |
| Object rollback/ownership | `_scoped_activation_event_status` and `_recover_scoped_activation_markers:666-710` compare the exact event command and object value before cleanup/rollback | Both activation commands; distinct later activation of the same target was included in sibling controls |

The sibling scoped-authority selection covered 11 collected items and passed
11/11, including direct-admission sealing, replay family separation, failed
append rollback, later activation preservation, and immutable decision
revalidation. The external-publication file covered the new external-grant
path and passed all 13/13 tests.

## Validation evidence

All validation used the pre-existing interpreter
`C:\Users\steph\TDL\.venv\Scripts\python.exe` directly, with
`PYTHONDONTWRITEBYTECODE=1`, pytest third-party plugin autoload disabled,
pytest cache disabled, and coverage disabled. No repository file other than
this named review record was written.

```text
tests/research_system/integration/test_external_assurance_record_publication.py
13 passed in 250.12s

bounded sibling scoped-authority/recovery selection
11 passed in 441.08s

focused Ruff check: passed
focused Ruff format --check: passed
git diff --check: passed
```

Independent probe results:

```text
marker digest tamper: ConflictError; durable_unchanged=true;
  marker_preserved=true; object_revision=1; no command event
event-schema replacement during marker reconstruction: ConflictError;
  durable_unchanged=true; temp_preserved=true; no command event
crash after receipt publication: exact retry returned accepted receipt;
  marker remained (the Minor finding above)
```

## Protected identity set

The following 16 protected WP6.3 contract/schema/authority paths were compared
between the expected parent and candidate Git objects, and each candidate Git
object was compared with its physical checkout bytes. All 16 had equal parent
and candidate blobs and equal raw SHA-256 values.

| Protected path | Git blob | Raw SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7298b994ca80fb43364ec53964b735f1c7e3929a` | `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` |
| `.research-system/schemas/wp6-3-authority/accept-r3-assurance-requirement-policy-action.schema.json` | `84d30db5102ce9c052d31e74dd6c2bdafda0bf8d` | `fd93c16cafa1d0f38729c8bd3784c37f0ff47a5d361ae1c5895c17c110fa2908` |
| `.research-system/schemas/wp6-3-authority/activate-authority-grant-command.schema.json` | `3e26da4221604369a09ca2818e1f0fe179d61a3d` | `904556b5f1a8c0fa45a39ab2245d3a4fe8c14a4c0387f3ddb7e3923a51549762` |
| `.research-system/schemas/wp6-3-authority/activate-external-assurance-record-grant-command.schema.json` | `26ce9a7454ace7c759c007e508ff56277868dc7c` | `510b481a82bc1a4e8700b4b2d4eac1ba575c947e9c92eb49f1d6ca07699f69f6` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-grant-activated-event.schema.json` | `5213dfdb2c8e8046248aac185c96b30d630542f9` | `20753a39c13b97b68dce4a3028c62527e1195ca2cff6484ca792dba4eff3a9ee` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-grant-revoked-event.schema.json` | `762bcdc10fca91e313de19fb7ea6b2b8a91b313f` | `572797957b1447c0769cc08ff4c0ed5973feb5e606b30f728909920c41ed1aa6` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-owner-authority-administration-decision.schema.json` | `13f21543d0197255dc589efa730cefbef0a72622` | `0a5b209ac08db89fc40d36d01706be9577b583afac501eca0ff091acda328277` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-scoped-authority-grant.schema.json` | `94a1f7082b2bc49d7fc50aa46226444f88811cc5` | `489c8a4686c0b4911fd221417347a15223f3f4c68d19bc90c427e5bd70adce2f` |
| `.research-system/schemas/wp6-3-authority/issued-authority-grant-revoked-event.schema.json` | `6a960732ad280b3326f48d8400eb0d422ecfd615` | `a094787c5d8e4788e70b2462486622c3e26f4157932dc8ab4aa46a52c9bd14f5` |
| `.research-system/schemas/wp6-3-authority/owner-authority-administration-decision.schema.json` | `e2236c250d34807fc1ecfd14566bb116c297e4ce` | `971072c7b180b4c39125b012db323c167318db1656ba14f38839243a4f7615d3` |
| `.research-system/schemas/wp6-3-authority/publish-external-assurance-record-policy-action.schema.json` | `c8f2da51e37ac8cb0fb3e3000c46ac3eeaa129fe` | `cede809de4d2bc006f17f3ca9bfadaa655572b1e26625d89355c76eb41fcdf1e` |
| `.research-system/schemas/wp6-3-authority/revoke-external-assurance-record-grant-command.schema.json` | `1475d4d11b2a5fe875ffc01fd223fb09fe462b28` | `b3bc15151cd45af1256850266eee0a9e37f4d4bd99cfe44862b5cc7c874f0b27` |
| `.research-system/schemas/wp6-3-authority/revoke-issued-authority-grant-command.schema.json` | `3f0754b1bd1f8c329a478e736bf0dc975e7dcb47` | `b98a42c7af4d1bbd5c0e6498ac4555e91603b4a183412c753e7e2cf076cbed05` |
| `.research-system/schemas/wp6-3-authority/scoped-authority-grant.schema.json` | `e0338b83c1f03449d65ffc73ab7c6d47a2d39157` | `03ac40ea2df4d100746b10d39ae1227a7d2835c18997f701a4f85ede992105bb` |
| `.research-system/schemas/wp6-3-authority/scoped-authority-grant-activated-event.schema.json` | `926245aba3821e17d1245c3eb64cf5177c69c0cf` | `0d2d130b2b76e4d63fa6dcb92f821f7dcd3829ff817ec9f896fe7257c038e0d9` |

## Final boundary

The candidate is a clean rejected handoff point pending the one Minor
receipt-present cleanup correction and a fresh exact-subject review. No
provider, credential, live external party, real assurance record, owner
decision, merge, or CodeRabbit operation was accessed or inferred. The review
record itself is the only authorized repository write.
