# Adversarial WP6.3 scoped-authority revocation-seal exact-subject review

**Date:** 2026-08-01

**Verdict:** `accept_exact_subject`

**New findings:** 0 Critical, 0 Major, 0 Minor

**Prior findings:** prior C-2 closed; earlier C-1, M-1, and M-2 remain closed

**Review mode:** fresh independent defensive code review, exact-subject, no
implementation remediation

## 1. Exact review subject

| Field | Exact value |
|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\6f50\TDL` |
| Branch at review | `codex/wp63-scoped-grant-revocation-seal` |
| Subject commit | `10759ecaf53d865a801fe5cedaaf15412b36b91e` |
| Direct parent / review base | `2cbc0951808162323457dd742100f5c2d9520d6b` |
| Rejected predecessor | `13c479d69ab1b5690fb8f51bce43f76ebbf4553b` |
| Base ancestry | `git merge-base --is-ancestor 2cbc0951808162323457dd742100f5c2d9520d6b 10759ecaf53d865a801fe5cedaaf15412b36b91e` exited 0 |
| Predecessor ancestry | `git merge-base --is-ancestor 13c479d69ab1b5690fb8f51bce43f76ebbf4553b 10759ecaf53d865a801fe5cedaaf15412b36b91e` exited 0 |
| Entry status | only preserved setup changes: `M .claude/CLAUDE.md`, `M .repowise-workspace.yaml` |
| Review-owned path | this report only |

`git rev-list --parents -n 1 10759ec...` identifies `2cbc095...` as the
subject's direct parent. The subject commit is `[PIPELINE] P00: seal legacy
revocation from scoped grants` and changes exactly five paths, 188 insertions
and 5 deletions:

| Status | Path |
|---|---|
| M | `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` |
| M | `research_system/command/service.py` |
| M | `research_system/projection/replay.py` |
| M | `research_system/store/ledger.py` |
| M | `tests/research_system/integration/test_scoped_authority_grant_activation.py` |

No implementation, accepted contract, schema, fixture, setup, or unrelated
path was edited by this review.

## 2. Governing authority and review boundary

The review applied, in order:

1. P-046, `03-decisions-and-open-questions.md:911-974`;
2. Handoff 32, especially sections 5A and 6;
3. `06-wp6-gate6-readiness-and-integration-plan.md`;
4. `06g-wp6-owner-operated-session-amendment.md`;
5. the prior exact-subject review
   `adversarial-wp6-3-scoped-authority-13c479d-remediation-exact-subject-review-2026-08-01.md`;
6. all five subject diffs and the service, ledger, replay, resolver, receipt,
   bootstrap, and legacy-publication seams they invoke; and
7. fresh temporary-store and pytest evidence at the exact subject.

P-046 reserves typed post-genesis activation and revocation to the bootstrap
owner and one exact immutable owner decision. Its preserved legacy boundary is
narrower: valid untyped genesis history and CommandService-issued
`RevokeAuthorityGrant` remain valid, while raw append grants no authority and a
legacy revocation cannot target a typed v2 grant
(`03-decisions-and-open-questions.md:923-967`). Handoff 32 separately requires
deterministic replay/revocation and forbids direct authority-state fabrication.

The approved WP6 snapshot and P-042/06g remain authority boundaries, not
implementation acceptance. This review creates no grant or owner decision,
performs no provider call, migration, acceptance run, eligibility transition,
merge, or push, and does not infer owner acceptance.

## 3. Verdict

`accept_exact_subject`

The exact subject closes the prior Critical cross-family revocation defect.
New generic `AuthorityGrantRevoked` / `RevokeAuthorityGrant` publication is now
sealed behind the same one-shot, ledger-specific CommandService continuation as
typed scoped administration. Direct raw append fails before any event/runtime
file, canonical tail, receipt, or projection change. Replay derives the target
family from the activation projection: a record with typed schema lineage is
inadmissible to the legacy branch before the terminal `revoked` update.

Fresh independent controls also established that:

- a valid genesis plus typed v2 activation chain followed by a hash-valid
  generic legacy revocation fails replay with the prior projection unchanged;
- normal legacy CommandService revocation still returns an accepted receipt,
  preserves exact-retry behavior across restart, and remains replayable;
- that same generic command path rejects a typed v2 target, leaves it active,
  and changes no event, runtime, object, or tail bytes;
- typed `RevokeIssuedAuthorityGrant` with its exact owner decision remains
  accepted; and
- direct typed append sealing, immutable-decision revalidation, inactive and
  later-binding closure, wrong-subject closure, and the R3 bound-human-owner
  rule all remain green.

No Critical, Major, or Minor finding was established against this exact
subject.

## 4. Prior-finding dispositions

### Prior C-2 - closed

**Disposition:** `closed_exact_subject`

The rejected predecessor admitted a raw generic revocation against an active
typed v2 grant, advanced the tail, and replayed the target as revoked without a
typed owner decision. The prescribed correction required separate historical
compatibility from live publication and classify replay by activation family.

The subject implements that mechanism rather than merely removing the earlier
probe vehicle:

- `CommandService.submit` sends both legacy `RevokeAuthorityGrant` and typed
  scoped-administration events through the guarded continuation
  (`research_system/command/service.py:421-478`).
- The continuation is one-shot and ledger-specific, creates an internal
  `EventDraft`, and cannot be supplied through the public submit signature
  (`research_system/store/ledger.py:77-191,232-256`).
- `EventLedger.append` treats all three administration producer pairs as
  sealed and rejects an ordinary mapping before publication
  (`research_system/store/ledger.py:326-390`).
- Replay records typed schema lineage during `ActivateAuthorityGrant`
  (`research_system/projection/replay.py:261-328`) and rejects the generic branch
  when that lineage exists, before the shared terminal mutation
  (`research_system/projection/replay.py:331-428`).

The independent valid-chain reducer/replay probe and the changed tests both
rejected the former cross-family transition without mutation.

### Earlier C-1 - remains closed and is now complete at family level

**Disposition:** `closed_exact_subject`

The typed activation and issued-revocation raw-append vehicles remained sealed,
and missing, foreign, tampered, reused, or mismatched owner decisions remained
invalid on replay/restart. The new generic seal removes the sibling producer
gap that prevented authority-family closure at `13c479d...`.

### Earlier M-1 - remains closed

**Disposition:** `closed_exact_subject`

Activation still resolves exact active schema identity and the closed
command/action-to-subject mapping before publication. Unresolved, inactive,
wrong-hash, wrong-command-subject, and wrong-policy-subject proposals remain
rejected; later registry activation cannot wake a rejected proposal.

### Earlier M-2 - remains closed

**Disposition:** `closed_exact_subject`

The R3 policy still derives actor class from the bound human-owner policy.
Agent, service, and non-owner-human grants remain rejected without authority
publication.

## 5. Adversarial disposition matrix

| Invariant or path | Enforcement and independent result | Disposition |
|---|---|---|
| Raw generic revocation append | Generic pair added to sealed administration set; direct temporary-store append rejected; event/runtime files and tail byte-identical | Pass; prior C-2 live-admission limb closed |
| Valid-chain typed v2 activation then generic replay | Typed activation stores schema lineage; legacy reducer rejects `schema_id`-bearing target before mutation | Pass; prior C-2 replay limb closed |
| Projection immutability on failed replay | Independent `apply_event` probe compared a deep copy before/after the exact rejection | Pass |
| Legacy CommandService one-shot continuation | Service routes generic revocation through the ledger-bound continuation after normal resolver preparation | Pass |
| Legacy accepted retry semantics | Accepted exact retry with new command ID returned the original receipt across restart | Pass |
| Legacy command targeting typed v2 grant | Independent service probe returned `rejected`, reason `authority_revocation_unauthorized`; target remained active and event/runtime/object bytes did not change | Pass |
| Typed v2 owner-decision revocation | Normal `RevokeIssuedAuthorityGrant` positive accepted and projected revoked | Pass |
| Pre-existing untyped legacy revocation history | Genesis projection deliberately has no typed schema lineage; exact legacy positive nodes replayed it as revoked | Pass |
| Raw typed activation and revocation | Both require sealed scoped-administration drafts | Pass; earlier C-1 remains closed |
| Immutable typed decision replay | Missing/tampered activation or revocation decision invalidates replay/resolution | Pass; earlier C-1 remains closed |
| Inactive/unresolved/wrong identity and later binding | Rejected without grant/event; later binding does not activate it | Pass; earlier M-1 remains closed |
| Wrong subject | Closed command/action mapping remains enforced | Pass; earlier M-1 remains closed |
| R3 human-owner rule | Agent, service, and foreign human variants rejected | Pass; earlier M-2 remains closed |
| P-046 boundary statement | Narrows legacy preservation to valid history and CommandService issuance, excludes direct append and v2 targets, and repeats that implementation/owner acceptance remain outstanding | Accurate; no authority escalation |

## 6. Validation evidence

All Python validation used the verified pre-existing interpreter/environment at
`C:\Users\steph\TDL\.venv`, with `PYTHONDONTWRITEBYTECODE=1`, empty
`PYTEST_ADDOPTS`, `-p no:cacheprovider`, and `-p no:cov`. No environment manager
was allowed to bootstrap inside the review worktree.

### Decisive changed-seam tests

Command:

```text
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_direct_legacy_revocation_append_cannot_target_scoped_v2_grant
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_replay_rejects_legacy_revocation_of_scoped_v2_grant
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_legacy_v1_command_service_revocation_and_retry_remain_accepted
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_typed_v2_owner_decision_revocation_remains_accepted
  -o addopts= -p no:cacheprovider -p no:cov
```

Result: `4 passed in 48.79s`.

### Complete scoped-authority regression tier plus exact legacy positives

Command:

```text
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q
  tests/research_system/integration/test_scoped_authority_grant_activation.py
  tests/research_system/integration/test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart
  tests/research_system/unit/test_release_publication.py::test_historical_publication_retry_and_eval_survive_later_revocation
  -o addopts= -p no:cacheprovider -p no:cov
```

Result: `31 passed in 376.65s (0:06:16)`.

This broader module tier was justified by the subject's changes to the shared
CommandService, EventLedger append admission, and replay reducer. No package or
full suite was run.

### Independent external temporary-store probe

A PowerShell `$reviewCode` string was UTF-8/Base64 passed to the same Python
interpreter with `python.exe -c "import base64; exec(base64.b64decode(...))"`.
It used `TemporaryDirectory` outside the repository and production registry,
bootstrap, service, ledger, object, receipt, replay, and resolver classes. It:

1. activated one valid typed v2 grant with its exact owner decision;
2. constructed a fully positioned and hash-valid generic legacy revocation;
3. called the reducer directly and compared the input projection to a deep copy;
4. replayed the complete valid chain through the generic revocation; and
5. submitted a normal generic legacy command against the typed v2 target while
   comparing event/runtime/object bytes and the ledger snapshot.

Final result:

```text
cross_family_replay=blocked; projection_unchanged=true;
generic_command_to_v2=rejected; target_status=active;
event_runtime_object_files_unchanged=true; tail_unchanged=true
```

Two initial shell-quoting attempts failed with Python `SyntaxError` before test
code executed. The first encoded semantic run expected an exception from the
generic command but observed the service's declared rejected-receipt contract;
the final harness asserted that exact contract. No attempt wrote to the
repository; the semantic runs used disposable external directories.

### Static and diff checks

```text
C:\Users\steph\TDL\.venv\Scripts\ruff.exe check <4 changed Python files>
All checks passed!

C:\Users\steph\TDL\.venv\Scripts\ruff.exe format --check <4 changed Python files>
4 files already formatted

git diff --check 2cbc0951808162323457dd742100f5c2d9520d6b..10759ecaf53d865a801fe5cedaaf15412b36b91e
exit 0
```

## 7. Protected identities

The broader core/contract trees are unchanged from the direct review base. The
two owner-accepted WP6.3 artifacts also exactly match accepted subject
`449b0d002edea3013dcc32a115f1870c4a082974` at Git-blob and recorded raw-byte
SHA-256 identity.

| Protected artifact | Base identity | Subject identity | Result |
|---|---|---|---|
| `.research-system/schemas/core` | `831ed486736d74df7c2d3a10d1ba70c2940e18d2` | same | unchanged |
| `.research-system/contracts` | `27f1e12e8ecfb5c6fb33377981a96410555cbd56` | same | unchanged |
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | blob `7298b994ca80fb43364ec53964b735f1c7e3929a`; raw `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` | same | exact accepted bytes |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | blob `acf622b4e7ae72ab9ac58d10aac14efed04560ac`; raw `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` | same | exact accepted bytes |

## 8. Residual boundaries and final decision

- The generic CommandService-to-v2 negative is independently established here,
  but has no dedicated committed test node. This is a non-blocking regression-
  coverage boundary because the exact-subject behavior is also structurally
  closed by strict legacy-object resolution and replay family separation; a
  future hardening change may add that test without reopening this verdict.
- The production control-store writer, acceptance runner, real multi-party
  records, live grant, and live owner decision remain later Handoff-32 work.
- This review accepts only exact subject `10759ec...`. Any implementation change
  requires fresh focused review.
- Review acceptance is not owner acceptance. No merge or dispatch authority is
  inferred, and nothing was pushed.

**Final exact-subject verdict: `accept_exact_subject`.**

Owner acceptance of this exact reviewed subject remains outstanding.
