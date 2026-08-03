# KAN-67 receipt-recovery correction exact-subject review

Date: 2026-08-02 (Europe/London)

Verdict: `rework_required`

Severity counts: 0 Critical, 1 Major, 0 Minor.

This is a fresh independent exact-subject review of the candidate at
`4f87fc00dd4807a32978906b9f6d12ff63c2b405`. The producer history and producer
validation report were not used as evidence for this verdict.

## Exact review identity

- Review cwd: `C:\Users\steph\.codex\worktrees\faf9\TDL`
- Review branch: `codex/kan67-receipt-recovery-r8-review`
- Required parent: `bda4ed908c027d87aa3c809e743fe5d8dd4ba2ff`
- Reviewed candidate: `4f87fc00dd4807a32978906b9f6d12ff63c2b405`
- Candidate tree: `56d879d4db499658d43a5e4d2d4079945a15cc60`
- At review start, `HEAD`, the named local branch, the named remote-tracking
  branch, and `git ls-remote origin` all resolved to the candidate. The
  worktree started detached and one deterministic `git switch
  codex/kan67-receipt-recovery-r8-review` attached it to the named branch.
- Required-parent ancestry: pass (`git merge-base --is-ancestor` exited zero).
- Post-switch upstream equality: `origin/codex/kan67-receipt-recovery-r8-review`,
  `+0 -0`; status was clean before this report write.

## Governing authority and scope

I read the preceding exact-subject review at
`docs/plans/agentic-research-system/reviews/kan-67-receipt-recovery-f7cbc84-review-2026-08-02.md`,
Handoffs 31 and 32, P-046 at
`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:942-1005`,
and the WP6.3 control-store acceptance mechanics review. These sources require
exact owner, project, store, decision, and schema bindings; replay-derived
authority; fail-closed recovery; and preservation of the accepted WP6.3 bytes.
They do not authorize implementation, owner acceptance, merge, Jira closure,
Gate A A7, WP6.4, or Gate 6.

The candidate delta is exactly these two paths:

```text
research_system/command/service.py
tests/research_system/integration/test_external_assurance_record_publication.py
```

No other candidate path is in the parent-to-candidate diff. No protected
WP6.3 contract or schema was edited.

## Executive disposition

The candidate closes the previously observed ordinary receipt-present failure
for both `ActivateAuthorityGrant` and
`ActivateExternalAssuranceRecordGrant`:

- malformed orphan bytes now raise `IntegrityError` and remain at the same path
  byte-identically for final-marker-present and final-marker-absent retries;
- a submitted envelope with a foreign `project_id` now raises
  `ConflictError` in both marker states when the ordinary accepted receipt is
  present;
- valid matching residue is cleaned only after command, event, object, schema,
  and replay-backed authority checks;
- valid foreign residue conflicts without deletion, and mixed residue is
  classified atomically;
- the exact stored receipt is returned, with no new event, object, authority, or
  receipt bytes in the tested ordinary state.

The exact subject is nevertheless not accepted. A crash-shaped accepted-index
state remains outside the candidate controls: if the accepted idempotency index
exists but the ordinary receipt file is missing, receipt reconciliation
recreates that receipt before recovery residue validation. A malformed orphan
therefore fails closed only after a new receipt write, and an absent-marker
foreign-project retry also writes the receipt before rejecting the project.
This violates the required zero-new-receipt and fail-closed atomicity boundary.

## Findings by severity

### Major — M-01: receipt rehydration precedes recovery validation

**Claim tested:** An accepted scoped-activation retry must validate the current
submitted project and all marker or temporary residue before any mutation. A
malformed or foreign orphan must fail closed with its path and bytes preserved;
the retry must not create a new event, object, authority record, or receipt.

**Direct code evidence:**

- `research_system/command/service.py:829-832` calls
  `_scoped_authority_receipt` before `_reconcile_scoped_activation_receipt`.
- `research_system/command/service.py:1305-1307` sends an accepted receipt from
  the idempotency index into `_reconcile_scoped_authority_receipt`.
- `research_system/command/service.py:1316-1365` replays the canonical ledger
  and checks the exact accepted event, but at `:1361-1364` writes the receipt
  whenever the ordinary receipt file is absent.
- The recovery checks that should precede that write are later in
  `research_system/command/service.py:1112-1148`: the submitted project is
  checked at `:1112-1113`, and malformed temporary bytes fail at `:1121-1124`.

**Independent reproduction:** In a fresh control store for each activation
sibling, I created an accepted command with its recovery marker retained,
deleted only the ordinary `receipts/<command_id>.json` file, and retained the
accepted idempotency index. I then tested both final-marker states with
malformed temporary bytes `b'{"partial":'`:

```text
authority present: IntegrityError; receipt_recreated=True; durable_equal=False; temp_same=True; marker_same=True
authority absent:  IntegrityError; receipt_recreated=True; durable_equal=False; temp_same=True
external present:  IntegrityError; receipt_recreated=True; durable_equal=False; temp_same=True; marker_same=True
external absent:   IntegrityError; receipt_recreated=True; durable_equal=False; temp_same=True
```

For the same four sibling/state combinations, changing only the submitted
envelope `project_id` to `FOREIGN_PROJECT_ID` produced:

```text
present: preloaded-marker ConflictError; no receipt write
absent:  ConflictError; receipt_recreated=True; durable_equal=False
```

The ordinary receipt was re-derived from the already accepted canonical event,
so these probes did not create an event, object, or authority record. That does
not cure the boundary failure: the failed retry changed the canonical receipt
store before the malformed-residue or project check completed.

**Impact:** The mutation is bounded to deterministic receipt re-materialisation
and does not provide a new authority grant or append a new event in the probe.
It is nevertheless a material write on a retry that must fail closed, leaves a
new receipt alongside untouched invalid recovery evidence, and makes the
marker-absent path non-atomic relative to the marker-present path. The missing
receipt is a realistic index-before-receipt crash window, not a producer-history
assumption.

**Disposition:** Keep M-01 open. Before allowing receipt materialisation,
validate the submitted project and complete the activation recovery state
(final marker or every temporary, exact command/schema/event/object identity,
foreign/malformed/competing classification). The service should expose a
read-only receipt-reconciliation/validation phase and a separate final
materialisation phase, or otherwise guarantee that
`_reconcile_scoped_authority_receipt` cannot write until
`_reconcile_scoped_activation_receipt` succeeds. All failure paths must
preserve the existing receipt/index, marker, temporary bytes, objects, events,
and authority state. Add the missing-ordinary-receipt matrix for both
siblings, both marker states, malformed residue, foreign residue, and foreign
submitted project. Do not broaden the subject or edit protected WP6.3 bytes.

## Control matrix

| Control | Independent evidence | Result |
|---|---|---|
| Invalid/malformed orphan bytes | The added integration test at `tests/research_system/integration/test_external_assurance_record_publication.py:1017-1043`, plus the four ordinary-receipt direct probes | Pass when the accepted receipt file exists: `IntegrityError`, same path, byte-identical temporary, no durable-file change, both siblings and marker states. Fail in the index-only crash window described by M-01 because the receipt is recreated first. |
| Submitted envelope project revalidation | Added test at `:1048-1072`, plus four ordinary-receipt direct probes | Pass when the accepted receipt file exists for both marker states and both siblings. Fail in the absent-marker index-only crash window because receipt rehydration precedes the project conflict. |
| Same authority/project/store/schema boundary | `service.py:1317-1358` replays and checks the exact canonical event; `:1126-1142` validates the marker command, event status, and exact object; the resolver replay validator supplies the owner/store/bootstrap/project/schema cross-bindings | Pass for the ordinary accepted-receipt path and named shared cohort. The ordering residual remains a recovery atomicity defect, not a new authority-admission bypass. |
| Matching cleanup | Existing tests at `:840-873` and `:923-960`; direct 16-state matrix | Pass for authority and external activation, marker present/absent; only valid matching residue is removed. |
| Foreign conflict and mixed-residue atomicity | Existing tests at `:876-919` and `:963-1012`; direct 16-state matrix | Pass with foreign bytes preserved and mixed residue left untouched. |
| Exact receipt identity and zero writes | Ordinary receipt-present tests and direct matrix | Pass for an existing ordinary receipt: exact receipt, no event/object/authority/receipt mutation. Fail for a missing ordinary receipt: receipt is newly written before a later failure. |
| Protected WP6.3 identities | Parent blob, candidate blob, and physical checkout comparisons | Pass: `16/16` exact identities. |
| Candidate range | Parent-to-candidate name-status and diff check | Pass: only `service.py` and the publication integration test are changed; `git diff --check` is clean. |

## Validation evidence

All validation used the direct project interpreter
`C:\Users\steph\TDL\.venv\Scripts\python.exe`, with bytecode, plugin
autoload, pytest cache, and coverage side effects disabled where applicable.

- Exact changed publication integration file: `35 passed in 591.72s`.
- Named shared authority/replay cohort in
  `tests/research_system/integration/test_scoped_authority_grant_activation.py`:
  `17 passed, 35 deselected in 132.83s`.
- Independent direct matrix: both activation siblings x both marker states x
  `none`, matching, foreign, and malformed residue (`16` ordinary-state
  combinations), plus four ordinary-state project mutations. Matching cleanup,
  foreign conflict, mixed-residue atomicity, exact receipt identity, and
  no-new event/object/authority/receipt bytes passed in the ordinary receipt
  state. The separate four-case index-only malformed probe and four-case
  index-only project probe are the M-01 failures above.
- Ruff check: passed for the two candidate paths.
- Ruff format check: `2 files already formatted`.
- `git diff --check`: passed.
- Exact protected identity check: `16/16` parent blob = candidate blob = physical
  checkout bytes.
- Candidate tree: `56d879d4db499658d43a5e4d2d4079945a15cc60`.
- No full repository suite was run; no narrower failure or cross-cutting scope
  justified expanding beyond the changed integration file and named cohort.

## Protected WP6.3 identities

The following 16 paths were compared as parent Git blob, candidate Git blob,
and physical checkout bytes; every comparison was exact:

1. `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
2. `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`
3. `.research-system/schemas/wp6-3-authority/accept-r3-assurance-requirement-policy-action.schema.json`
4. `.research-system/schemas/wp6-3-authority/activate-authority-grant-command.schema.json`
5. `.research-system/schemas/wp6-3-authority/activate-external-assurance-record-grant-command.schema.json`
6. `.research-system/schemas/wp6-3-authority/external-assurance-record-grant-activated-event.schema.json`
7. `.research-system/schemas/wp6-3-authority/external-assurance-record-grant-revoked-event.schema.json`
8. `.research-system/schemas/wp6-3-authority/external-assurance-record-owner-authority-administration-decision.schema.json`
9. `.research-system/schemas/wp6-3-authority/external-assurance-record-scoped-authority-grant.schema.json`
10. `.research-system/schemas/wp6-3-authority/issued-authority-grant-revoked-event.schema.json`
11. `.research-system/schemas/wp6-3-authority/owner-authority-administration-decision.schema.json`
12. `.research-system/schemas/wp6-3-authority/publish-external-assurance-record-policy-action.schema.json`
13. `.research-system/schemas/wp6-3-authority/revoke-external-assurance-record-grant-command.schema.json`
14. `.research-system/schemas/wp6-3-authority/revoke-issued-authority-grant-command.schema.json`
15. `.research-system/schemas/wp6-3-authority/scoped-authority-grant.schema.json`
16. `.research-system/schemas/wp6-3-authority/scoped-authority-grant-activated-event.schema.json`

## Boundary and next action

The exact subject is not accepted. The next action is a narrowly scoped
`service.py` ordering correction plus publication integration controls for the
index-only crash window, followed by a fresh exact-subject review. This review
does not authorize merge, Jira Done, CodeRabbit, Gate A A7, WP6.4, Gate 6,
owner acceptance, dispatch, or any external-party/live-governance operation.

## Change log

This review wrote only this report. It did not remediate production or test
code, stage candidate changes, trigger or poll CodeRabbit, touch Jira, create a
PR, merge, or alter the control store.
