# KAN-67 receipt-recovery ordering correction exact-subject review

Date: 2026-08-02 (Europe/London)

Verdict: `accept_exact_subject`

Severity counts: 0 Critical, 0 Major, 0 Minor.

This is a fresh independent exact-subject review of candidate
`1e0b04b69365b62ac28a6f8933faa9e41f44b4e9`. Producer history and producer
validation summaries were not used as acceptance evidence. The review was
bounded to the receipt-recovery ordering correction and the exact controls
listed below.

## Exact review identity

- Review cwd: `C:\Users\steph\.codex\worktrees\3123\TDL`
- Review branch: `codex/kan67-receipt-recovery-r10-review`
- Required parent: `34cec82be61639f8216e4f01ecab910acc88222a`
- Candidate/start: `1e0b04b69365b62ac28a6f8933faa9e41f44b4e9`
- Candidate tree: `6e2636ca5f003c7b6eb41d17d56f6c8f49b9e787`
- The worktree started detached at the candidate. The detached `HEAD`, local
  review ref, and `origin/codex/kan67-receipt-recovery-r10-review` all resolved
  to the candidate before one deterministic `git switch` to the named branch.
- After the switch, `HEAD`, the named local branch, and the live remote branch
  remained equal to the candidate; `git merge-base --is-ancestor` confirmed the
  required parent; status was clean before this report write.
- Parent-to-candidate delta: exactly
  `research_system/command/service.py` and
  `tests/research_system/integration/test_external_assurance_record_publication.py`.
- No protected WP6.3 contract or schema path is in the candidate delta.

## Governing authority and review boundary

The review read the supplied preceding review at
`docs/plans/agentic-research-system/reviews/kan-67-receipt-recovery-4f87fc0-review-2026-08-02.md`,
its cited KAN-67 predecessor at
`docs/plans/agentic-research-system/reviews/kan-67-receipt-recovery-f7cbc84-review-2026-08-02.md`,
Handoffs 31 and 32, P-046 at
`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:942-1005`,
and `docs/plans/agentic-research-system/reviews/wp6-3-control-store-acceptance-mechanics-2026-07-30.md`.
These sources require exact owner/project/store/schema bindings, replay-derived
authority, fail-closed recovery, and preservation of accepted WP6.3 bytes.

They do not authorize implementation beyond this candidate, owner acceptance,
merge, Jira closure, Gate A A7, WP6.4, Gate 6, provider calls, external-party
records, or live-governance actions.

## Executive disposition

The exact M-01 finding, "receipt rehydration precedes recovery validation," is
closed. The candidate now validates the recovery boundary before it can
materialize a missing ordinary receipt:

1. `CommandService.submit` passes the resolved command schema into
   `_scoped_authority_receipt` and returns only after that reconciliation path
   completes (`research_system/command/service.py:829-834`).
2. `load_scoped` is a read of the accepted idempotency index. For an accepted
   scoped activation, `_scoped_authority_receipt` calls
   `_reconcile_scoped_activation_receipt` before the common authority-receipt
   reconciliation (`service.py:1288-1315`).
3. Recovery checks the submitted project before touching residue
   (`service.py:1113-1115`). It then validates the final marker or every
   temporary, exact command/schema identity, replay-derived event status, and
   exact object bytes. Malformed, foreign, competing, or mismatched evidence
   raises before cleanup or receipt materialization (`service.py:1116-1155`).
4. Only after those checks does the common path replay the ledger, validate the
   exact accepted event, and write a missing ordinary receipt
   (`service.py:1324-1373`). Valid missing-receipt recovery therefore remains
   available, while failed recovery remains byte-preserving and mutation-free.

## Finding disposition

### M-01 - closed: receipt rehydration precedes recovery validation

**Required invariant:** With an accepted idempotency index and no ordinary
receipt, malformed or invalid activation residue must fail before any receipt
repair/materialization or other store mutation, preserving the residue bytes at
the same path. A submitted foreign project must fail at the same boundary. The
boundary must hold for both activation siblings and both final-marker states.

**Direct candidate controls:**

- `test_index_only_retry_rejects_invalid_marker_temp_without_mutation` at
  `tests/research_system/integration/test_external_assurance_record_publication.py:1077-1106`
  deletes the ordinary receipt while retaining the accepted index, injects
  `b'{"partial":'`, and checks unchanged durable files, unchanged residue
  bytes, marker-state preservation, and absence of a repaired receipt.
- `test_index_only_retry_revalidates_envelope_project_without_mutation` at
  `.../test_external_assurance_record_publication.py:1111-1137` deletes the
  ordinary receipt, changes only `project_id`, and checks unchanged durable
  files, marker-state preservation, and absence of a repaired receipt.
- The two parametrized controls cover `ActivateAuthorityGrant` and
  `ActivateExternalAssuranceRecordGrant`, with marker present and absent: four
  malformed-residue cases plus four foreign-project cases.

**Decisive result:** the new index-only matrix passed `8 passed in 59.31s`.
Every invalid-residue case raised `IntegrityError` before receipt repair, and
every foreign-project case raised `ConflictError` before receipt repair. The
same ordering is visible in the executable call graph above, including
marker-present paths through `_remove_scoped_activation_marker` and
marker-absent paths through temporary-residue classification.

**Disposition:** closed. No Critical, Major, or Minor finding remains within
the exact subject.

## Ordinary receipt-present matrix

I also ran a separate direct temporary-control-store probe, independent of the
candidate test assertions. It covered both activation siblings, both marker
states, and all four residue states (`none`, matching, foreign, mixed):
`2 x 2 x 4 = 16` cases.

| Residue state | Marker present | Marker absent |
|---|---|---|
| None | Exact receipt returned; marker removed | Exact receipt returned; no new recovery file |
| Matching | Exact receipt returned; marker and matching temporary removed | Exact receipt returned; matching temporary removed |
| Foreign | `ConflictError`; marker and foreign bytes preserved | `ConflictError`; foreign bytes preserved |
| Mixed | `ConflictError`; marker and both temporary files preserved | `ConflictError`; both temporary files preserved |

All `16` cases passed. Before and after snapshots showed no new event, no
changed event history, no changed authority-grant object bytes, no changed
ordinary receipt bytes, and no durable-file delta other than the expected
successful recovery-file removals. The exact receipt object was returned on
every successful retry.

The full changed publication file passed `43 passed in 268.80s`. This includes
the ordinary receipt-present controls at
`tests/research_system/integration/test_external_assurance_record_publication.py:840-1012`
and the index-only controls cited above.

## Authority, replay, and sibling controls

The named bounded authority/replay cohort passed:

```text
tests/research_system/integration/test_scoped_authority_grant_activation.py
17 passed, 35 deselected in 116.88s
```

The selection covered owner-bound activation and retry, projection and risk
checks, admission-version enforcement, inert unactivated objects, failed-append
rollback and exact retry, producer downgrade rejection, direct activation and
revocation admission gates, legacy-v2 separation, replay rejection, legacy
revocation retry, typed-v2 revocation, and the three immutable activation
decision restart cases. This supports the current replay/authority validation
used by the recovery ordering; it is not a claim that the full repository suite
was run.

## Validation evidence

All pytest runs used
`C:\Users\steph\TDL\.venv\Scripts\python.exe` with
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONDONTWRITEBYTECODE=1`,
`-o addopts=`, `-p no:cacheprovider`, and `-p no:cov`.

- Decisive index-only matrix: `8 passed in 59.31s`.
- Full changed publication file: `43 passed in 268.80s`.
- Named authority/replay cohort: `17 passed, 35 deselected in 116.88s`.
- Independent ordinary receipt-present matrix: `16` cases passed.
- Ruff check on both candidate paths: passed (`All checks passed!`).
- Ruff format check on both candidate paths: passed (`2 files already formatted`).
- `git diff --check`: passed.
- No full repository suite was run, as required by the bounded review scope.

## Protected WP6.3 identities

For each path below, the parent Git blob, candidate Git blob, and physical
checkout `git hash-object` were compared. All `16/16` comparisons were exact.

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

## Residual risk and authority limits

- This is an exact-subject review, not a full repository or concurrent
  filesystem review. Unrelated KAN-67 control-store concerns, other command
  families, provider integrations, and live external stores are not certified
  here.
- The review does not authorize merge, owner acceptance, Jira transition, Gate
  A A7, WP6.4, Gate 6, CodeRabbit, provider invocation, external-party record
  creation, or any live-governance action.
- The bounded tests and direct probes used temporary control stores only. No
  production control store or restricted data was touched.

## Change log

- Wrote only this review record.
- Did not remediate production or test code, stage candidate changes, alter
  protected WP6.3 bytes, create a PR, merge, update Jira, invoke providers, or
  trigger/poll CodeRabbit.
