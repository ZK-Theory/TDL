# KAN-67 receipt-present recovery correction exact-subject review

Date: 2026-08-02 (Europe/London)

Verdict: `rework_required`

Severity counts: 0 Critical, 0 Major, 1 Minor.

This is a fresh independent exact-subject review. It is not owner acceptance,
PR or merge evidence, Jira transition, Gate A/Gate 6 acceptance, production
multi-party materialization, or authorization to remediate the subject.

## Exact review identity

- Review worktree: `C:\Users\steph\.codex\worktrees\94f5\TDL`
- Review branch: `codex/kan67-receipt-recovery-263b304-review`
- Reviewed candidate: `263b304733afb2bb34037566ad7884ea2dd47612`
- Git-proven parent: `4b27b04f7a232fbc71097ff4c82587374016fc83`
- Candidate tree: `93413037afca4fa2cf0055a6334aec8b848385df`
- Candidate branch remote: `origin/codex/kan67-receipt-recovery-263b304-review`
- Remote head at review: `263b304733afb2bb34037566ad7884ea2dd47612`
- Candidate delta: exactly `research_system/command/service.py` and
  `tests/research_system/integration/test_external_assurance_record_publication.py`.
- The worktree was detached initially; the named branch ref equalled the
  candidate, so exactly one deterministic `git switch` attached it. After the
  switch, cwd, branch, HEAD, parent, tree, ancestry, remote head, and clean
  status were verified. The producer's stale parent label was not used.

## Authority and review basis

The accepted WP6.3 authority/acceptance boundary was read from Handoffs 31 and
32, the accepted P-046 scoped-authority decision, and the WP6.3 control-store
acceptance mechanics review. The preceding exact review for `4b27b04` was read
from its reachable review commit `159b780b237fdbb50399530439fd1ca0009449f0`.
Those sources preserve the owner-reserved authority boundary and the frozen
WP6.3 contract/schema bytes; they do not authorize implementation or imply
owner acceptance.

The prior review's live defect was confirmed in source: a stored accepted
scoped receipt returned before committed-marker status and residue
classification. The candidate correctly adds receipt-present reconciliation
for both `ActivateAuthorityGrant` and
`ActivateExternalAssuranceRecordGrant` when the final marker remains present.

## Executive disposition

The candidate closes the prior final-marker-present bypass for the exercised
state. At `research_system/command/service.py:825-829`, an accepted scoped
receipt now routes activation commands through
`_reconcile_scoped_activation_receipt`. That method validates the marker's
command identity and active command schema, requires a committed event, and
delegates to the shared object/residue reconciliation at `:1103-1116` and
`:663-690`. The existing cleanup classifies valid temporary residue before
unlinking the final marker at `:428-454`.

The candidate does not close the adjacent crash state in which the final marker
has already been unlinked but a valid temporary remains. In that state the new
receipt-present method returns at `:1109-1110` without enumerating temporary
paths. A foreign valid temporary is therefore silently bypassed, and a
matching valid temporary is left behind. This is a recovery-liveness and
authority-residue defect, not event/object corruption, so it is Minor but
blocks exact-subject acceptance.

## Finding M-01 - receipt-present retry bypasses orphan temporary residue

**Severity:** Minor

**Claim tested:** Every accepted receipt retry must classify all scoped
activation recovery residue, even when the final marker is absent. Matching
residue may be removed only after the committed command/event/object identity is
revalidated; foreign valid residue must raise an integrity conflict and remain
untouched.

**Direct evidence:**

- `_remove_scoped_activation_marker` scans residue at
  `research_system/command/service.py:428-444`, then unlinks the final marker
  at `:446` before unlinking valid temporary files at `:447-453`. A process
  termination between those operations can leave a valid temporary with no
  final marker.
- `_reconcile_scoped_activation_receipt` returns immediately when the final
  marker is absent at `research_system/command/service.py:1103-1110`; it never
  calls `_scoped_activation_marker_temporary_paths` or performs a residue
  classification in that state.
- The candidate's new tests at
  `tests/research_system/integration/test_external_assurance_record_publication.py:818-898`
  all retain a final marker before exercising no-residue, matching-temp, and
  foreign-temp behavior. They do not instantiate a valid temporary after the
  final marker has disappeared.
- A fresh direct production-seam probe reproduced the state for both command
  siblings. After creating an accepted receipt, leaving a valid matching or
  foreign temporary, and removing only the final marker, exact retry returned
  the accepted receipt and left the temporary in place:

  ```text
  authority matching orphan temp: returned True, temp remains True
  authority foreign orphan temp: returned True, temp remains True, marker remains False
  external matching orphan temp: returned True, temp remains True
  external foreign orphan temp: returned True, temp remains True, marker remains False
  ```

**Concrete failure scenario:** A process dies after the final-marker unlink in
`_remove_scoped_activation_marker` but before the temporary unlink. On restart
or exact retry, the accepted receipt is found, the final marker is absent, and
the new early return leaves a valid matching or foreign temporary. A foreign
temporary therefore does not produce the required conflict, and residue does
not converge without an unrelated later cleanup.

**Impact:** A valid foreign recovery object can remain unclassified after an
accepted command, weakening recovery isolation and leaving stale authority
residue. The committed event, grant object, and accepted receipt remain
consistent in this scenario; the impact is bounded to cleanup liveness and
foreign-residue detection.

**Disposition:** Fix now in the next exact subject. When an accepted receipt is
present, enumerate temporary paths even if the final marker is absent. Validate
each valid temporary against the submitted command/schema and the committed
event/object identity; remove only matching residue, raise `ConflictError` for
foreign valid residue while preserving it, and retain the existing no-marker
semantics for genuinely absent residue. Add deterministic controls for both
activation siblings covering matching and foreign valid residue after final
marker removal, then rerun the current final-marker-present controls.

**Affected paths:**
`_reconcile_scoped_activation_receipt`,
`_remove_scoped_activation_marker`,
`_scoped_activation_marker_temporary_paths`, and both members of
`_SCOPED_ACTIVATION_COMMAND_TYPES`.

## Control matrix

| Invariant / requirement | Enforcement and evidence | Disposition |
|---|---|---|
| Accepted receipt + no residue converges for both siblings | `service.py:825-829`, `:1103-1116`; new tests `:818-834`; direct probe passed authority and external siblings | Pass for final-marker-present state |
| Accepted receipt + matching valid temp reconciles | Shared cleanup `:428-454`; new tests `:836-851`; direct probe passed both siblings | Pass for final-marker-present state; M-01 remains for orphan state |
| Foreign valid temp conflicts without deleting marker/residue, then converges after explicit removal | Cleanup scans/classifies before unlink; new tests `:855-898`; direct probe passed both siblings with final marker present | Pass for final-marker-present state; M-01 remains for orphan state |
| Marker, command, command-schema, event-schema, authority, and identity binding | Marker command/schema validation before reconciliation; changed publication tests for schema-byte replacement, event identity, and marker integrity; direct changed-command probe rejected with `ConflictError` and preserved marker | Pass on exercised surfaces |
| Replay, rollback, idempotency, immutable decision revalidation, and sibling separation | Bounded authority selection: 17 passed, 35 deselected, including failed-append rollback, exact retry, direct-admission/replay separation, immutable activation-decision restart, inactive/wrong-subject rejection, and closed subject mapping; changed publication file: 19 passed | Pass on bounded sibling surface |
| Protected WP6.3 contract/schema/authority bytes | 16 protected paths compared parent Git blob, candidate Git blob, and physical checkout bytes | Pass: 16/16 exact |

The only unresolved item in the matrix is M-01's marker-absent residue state.

## Validation evidence

All tests used the pre-existing interpreter
`C:\Users\steph\TDL\.venv\Scripts\python.exe` directly, with
`PYTHONDONTWRITEBYTECODE=1`, pytest plugin autoload disabled, cache disabled,
and coverage disabled. No repository file other than this review record was
written.

```text
tests/research_system/integration/test_external_assurance_record_publication.py
19 passed in 584.51s

bounded authority sibling selection
17 passed, 35 deselected in 503.31s

fresh direct production-seam probes
authority and external siblings passed no/matching/foreign residue plus
changed-command mismatch; orphan-residue probe reproduced M-01 for both
siblings

focused Ruff check
All checks passed

focused Ruff format --check
2 files already formatted

git diff --check
passed
```

No full suite was run: the candidate delta is bounded to the shared activation
reconciliation path and its integration coverage, and the targeted tests plus
direct probes were decisive for the requested surface.

## Residual risk and boundary

Until M-01 is corrected, an orphan valid temporary can survive an accepted
receipt retry and a foreign orphan temporary can bypass the conflict guard.
This review does not assess unmodified WP6.1 runtime slices, production
multi-party WP6.3 materialization, owner decisions, Gate A/Gate 6, merges,
providers, credentials, Jira, or CodeRabbit.

## One next action

Implement the marker-absent temporary-residue reconciliation and its two-sibling
negative/positive controls as one narrowly scoped follow-up, then obtain a fresh
exact-subject review of the resulting commit. Do not change the protected
WP6.3 contract/schema bytes or broaden this subject into general runtime
activation work.

## Change log

- Reviewed only the exact candidate's two-file delta.
- Added only this durable review record; production code and tests were not
  edited.
- No PR, merge, provider, credential, Jira, CodeRabbit, or external-party
  operation was performed.
