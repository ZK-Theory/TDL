# KAN-67 orphan activation-residue remediation exact-subject review

Date: 2026-08-02 (Europe/London)

Verdict: `rework_required`

Severity counts: 0 Critical, 1 Major, 0 Minor.

This is a fresh independent exact-subject review of M-01 only. It is not owner
acceptance, merge evidence, Jira Done, Gate A A7, WP6.4, Gate 6, or authority to
remediate the candidate.

## Exact review identity

- Review cwd: `C:\Users\steph\.codex\worktrees\3159\TDL`
- Review branch: `codex/kan67-receipt-recovery-r6-review`
- Required parent: `4d0ed65b36d77a23cf66829fa843af4f8960f9a5`
- Reviewed candidate: `f7cbc84874c50d727e8947b0b98255e0dc610dc1`
- Candidate tree resolved from the candidate commit: `a7b16695ace85a107ddd3115a76ef47da8d8f91c`
- The delegation supplied `a7b16695ace85a107ddd3115a76ef47da8d8f91c3`, which is
  41 characters and cannot be a Git object; the commit-derived 40-character
  tree above is the authoritative identity used here.
- At review start, the detached `HEAD`, local review ref, and
  `origin/codex/kan67-receipt-recovery-r6-review` all resolved to the candidate.
  One deterministic `git switch` attached this worktree to the review branch.
- Required-parent ancestry: pass. Status was clean before the report write.
- Candidate delta: exactly
  `research_system/command/service.py` and
  `tests/research_system/integration/test_external_assurance_record_publication.py`.

## Governing authority and scope

The review used Handoffs 31 and 32, P-046 in
`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:942-1005`,
the WP6.3 control-store acceptance mechanics review, and the preceding exact
KAN-67 review at commit `159b780b237fdbb50399530439fd1ca0009449f0`. These sources
require exact owner/project/store/decision/schema bindings, replay-derived
authority, fail-closed recovery, and preservation of the accepted WP6.3 bytes.
They do not authorize implementation, merge, or owner acceptance.

## Executive disposition

The candidate closes the prior valid-residue gap for both
`ActivateAuthorityGrant` and `ActivateExternalAssuranceRecordGrant`: a matching
valid orphan temporary is removed before the exact accepted receipt is returned,
and a foreign valid temporary raises `ConflictError` without changing it. The
same behavior holds with the final marker present and absent, and retries do not
append an event or rewrite the object or stored receipt.

M-01 remains open. Invalid orphan bytes are quarantined and the accepted receipt
is returned instead of failing closed with the residue untouched. Separately,
when the final marker is absent, the receipt-present path does not revalidate the
submitted command's envelope project identity: a command differing only in
`project_id` receives the prior accepted receipt, while the same mutation is
rejected when the marker is present. This is a marker-state authority mismatch.

## Findings by severity

### Major — M-01: accepted receipt retry still bypasses fail-closed residue and project binding

**Claim tested:** An accepted scoped-activation receipt may coexist with a valid
orphan `.tmp` after the final marker is gone, but matching residue must be
removed before returning the exact receipt; foreign or invalid residue must fail
closed without deleting or changing it; and current authority/project/store
identity must be revalidated for both marker states.

**Direct code evidence:**

- The shared cleanup helper at
  `research_system/command/service.py:428-439` quarantines every `existing is
  None` temporary. Both final-marker cleanup (`:441-463`) and the new
  receipt-present orphan branch (`:1111-1151`) use it.
- The absent-marker branch appends malformed residue at `:1123-1127`, then
  returns after cleanup at `:1149-1151`; it does not raise or preserve the
  original temporary.
- With no residue, that branch returns without invoking
  `_validate_scoped_activation_marker_command`. The preceding shared receipt
  reconciliation at `:1319-1364` checks the canonical event against the ledger
  project (`:1359`) but does not compare the submitted command envelope's
  `project_id` with that project.

**Independent failure matrix:**

- For both activation siblings and both marker states, malformed
  `{"partial":` residue produced `return:accepted:exact=True`; the original
  temporary disappeared into `.quarantine`; events, object bytes, receipt bytes,
  and the one existing accepted-event count were unchanged.
- For both siblings, changing only the command envelope `project_id` produced
  `ConflictError` with the marker present but `return:accepted:same=True` with
  the marker absent; event history remained unchanged.
- The candidate's valid-residue matrix passed: matching residue was removed;
  foreign residue raised `ConflictError` and remained byte-identical; no new
  accepted event, object, authority record, or receipt bytes appeared.

**Impact:** The candidate does not corrupt the existing event or grant object in
these probes, but it permits an accepted retry to silently relocate invalid
recovery evidence and to return an accepted receipt for a command whose current
project identity is foreign. The final-marker-present and final-marker-absent
paths therefore do not enforce the same authority boundary.

**Disposition:** Rework the exact M-01 subject. Classify malformed orphan
residue as a fail-closed integrity conflict while preserving its path and bytes;
only remove a valid matching temporary after the same event/object/schema and
authority/project/store checks used by the committed-marker path. Revalidate the
submitted command envelope's project binding even when no marker or temporary
exists. Add controls for invalid residue and the project mutation in both
marker states and both activation siblings. Do not broaden the subject or edit
the protected WP6.3 bytes.

## Passing controls and protected identities

- Focused cohort: the specified interpreter
  `C:\Users\steph\TDL\.venv\Scripts\python.exe`, with
  `PYTHONDONTWRITEBYTECODE=1`, pytest plugin autoload disabled, cache disabled,
  and coverage disabled. The 17-item receipt/identity cohort passed (`17 passed,
  10 deselected` in 268.84 seconds).
- Ruff check: passed. Ruff format check: `2 files already formatted`.
- `git diff --check`: passed. Exact candidate delta scope: passed.
- The independent valid-residue probe covered both activation siblings, final
  marker present/absent, matching/foreign residue, event count, object bytes,
  receipt bytes, and residue bytes.
- No production or test file was edited by this review.

The following 16 protected WP6.3 contract/schema/acceptance identities were
compared as parent Git blob, candidate Git blob, and physical checkout bytes.
All 16 were byte-identical:

| Path | Parent = candidate = physical Git blob |
|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7298b994ca80fb43364ec53964b735f1c7e3929a` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` |
| `.research-system/schemas/wp6-3-authority/accept-r3-assurance-requirement-policy-action.schema.json` | `84d30db5102ce9c052d31e74dd6c2bdafda0bf8d` |
| `.research-system/schemas/wp6-3-authority/activate-authority-grant-command.schema.json` | `3e26da4221604369a09ca2818e1f0fe179d61a3d` |
| `.research-system/schemas/wp6-3-authority/activate-external-assurance-record-grant-command.schema.json` | `26ce9a7454ace7c759c007e508ff56277868dc7c` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-grant-activated-event.schema.json` | `5213dfdb2c8e8046248aac185c96b30d630542f9` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-grant-revoked-event.schema.json` | `762bcdc10fca91e313de19fb7ea6b2b8a91b313f` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-owner-authority-administration-decision.schema.json` | `13f21543d0197255dc589efa730cefbef0a72622` |
| `.research-system/schemas/wp6-3-authority/external-assurance-record-scoped-authority-grant.schema.json` | `94a1f7082b2bc49d7fc50aa46226444f88811cc5` |
| `.research-system/schemas/wp6-3-authority/issued-authority-grant-revoked-event.schema.json` | `6a960732ad280b3326f48d8400eb0d422ecfd615` |
| `.research-system/schemas/wp6-3-authority/owner-authority-administration-decision.schema.json` | `e2236c250d34807fc1ecfd14566bb116c297e4ce` |
| `.research-system/schemas/wp6-3-authority/publish-external-assurance-record-policy-action.schema.json` | `c8f2da51e37ac8cb0fb3e3000c46ac3eeaa129fe` |
| `.research-system/schemas/wp6-3-authority/revoke-external-assurance-record-grant-command.schema.json` | `1475d4d11b2a5fe875ffc01fd223fb09fe462b28` |
| `.research-system/schemas/wp6-3-authority/revoke-issued-authority-grant-command.schema.json` | `3f0754b1bd1f8c329a478e736bf0dc975e7dcb47` |
| `.research-system/schemas/wp6-3-authority/scoped-authority-grant.schema.json` | `e0338b83c1f03449d65ffc73ab7c6d47a2d39157` |
| `.research-system/schemas/wp6-3-authority/scoped-authority-grant-activated-event.schema.json` | `926245aba3821e17d1245c3eb64cf5177c69c0cf` |

## Boundary and next action

The exact subject is not accepted. The next action is a narrowly scoped
correction of M-01 followed by a fresh exact-subject review. This review does
not authorize merge, Jira Done, Gate A A7, WP6.4, Gate 6, CodeRabbit, or any
external-party or live-governance operation.

## Change log

- Reviewed only `4d0ed65b36d77a23cf66829fa843af4f8960f9a5..f7cbc84874c50d727e8947b0b98255e0dc610dc1`.
- Added only this durable review record; production and test sources were not
  edited.
- No PR, merge, Jira, CodeRabbit, provider, credential, or external-store
  operation was performed.
