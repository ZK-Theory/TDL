# Adversarial WP6.3 scoped-authority remediation exact-subject review

**Date:** 2026-08-01

**Verdict:** `rework_required`

**New findings:** 1 Critical, 0 Major, 0 Minor

**Prior findings:** C-1 typed path repaired but authority-family closure incomplete;
M-1 closed; M-2 closed

**Review mode:** fresh independent defensive code review, exact-subject, no
remediation

## 1. Exact review subject

| Field | Exact value |
|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\6f50\TDL` |
| Branch at review | `codex/wp63-scoped-grant-foundation` |
| Subject commit | `13c479d69ab1b5690fb8f51bce43f76ebbf4553b` |
| Prior durable review commit | `8f4eaadb29c27ef22068537096c2b798f546db4a` |
| Prior-record ancestry | `git merge-base --is-ancestor 8f4eaadb29c27ef22068537096c2b798f546db4a 13c479d69ab1b5690fb8f51bce43f76ebbf4553b` exited 0 |
| Entry status | only the preserved setup changes: `M .claude/CLAUDE.md`, `M .repowise-workspace.yaml` |
| Review-owned path | this report only |

The remediation range changes 13 files with 1,205 insertions and 83 deletions.
The review covered the three prior findings, the new scoped-administration
continuation, append admission, projection/replay, restart validation, scoped
resolution, the R3 consumer, and the legacy/typed revocation boundary. The two
pre-existing setup changes were neither edited nor staged.

## 2. Governing authority and boundary

The review applied, in order:

1. P-046, `03-decisions-and-open-questions.md:911-971`;
2. Handoff 32, especially sections 5A and 6;
3. the approved WP6 plan `06-wp6-gate6-readiness-and-integration-plan.md`;
4. the owner-operated-session amendment
   `06g-wp6-owner-operated-session-amendment.md`;
5. the prior exact-subject review at commit `8f4eaadb...`; and
6. the exact implementation and tests at `13c479d...`.

P-046 reserves post-genesis activation and revocation to the owner and requires
one exact typed `OwnerAuthorityAdministrationDecision`
(`03-decisions-and-open-questions.md:923-939`). It preserves legacy genesis and
legacy `RevokeAuthorityGrant` semantics, but does not authorize a legacy event
to administer a v2 scoped grant (`03-decisions-and-open-questions.md:960-964`).
Handoff 32 likewise requires deterministic revocation consequences and forbids
fabricating authority state outside the decided ledger mechanism (sections 5A
and 6).

This review creates no grant or live owner decision, changes no accepted
artifact, performs no provider action or migration, and claims neither owner
acceptance nor merge authority.

## 3. Verdict

`rework_required`

The remediation closes the prior inactive-identity and R3-human-owner defects
and seals correctly labelled typed scoped-administration events behind a
one-shot `CommandService.submit` continuation. It does not close the authority
family as a whole.

In a temporary store, after a valid typed activation of a v2 scoped grant, the
preserved generic `AuthorityGrantRevoked` / `RevokeAuthorityGrant` event was
accepted by the public append path. The durable tail advanced from position 3
to 4, its hash matched the ledger snapshot, replay completed with the bound
owner-decision validator, and the v2 grant became `revoked` in both projection
and resolver output. No typed revocation decision existed; the only projected
administration decision remained the activation decision.

Separate positive controls established the legitimate paths: the generic
command/service path revoked the genesis v1 publication grant, while
`RevokeIssuedAuthorityGrant` revoked a v2 grant using the exact typed owner
decision. The failure is therefore cross-family admission, not a general
revocation or replay failure.

## 4. Prior finding dispositions

### Prior C-1 - typed vehicle repaired; underlying family closure incomplete

**Disposition:** `partially_closed_new_blocker_C-2`

The remediation adds a one-shot, ledger-specific continuation
(`research_system/store/ledger.py:77-192`) and admits
`ActivateAuthorityGrant` / `RevokeIssuedAuthorityGrant` only through its scoped
draft (`research_system/store/ledger.py:375-389`). Replay records the typed
decision links (`research_system/projection/replay.py:261-328,361-425`), and the
resolver re-loads and cross-binds every consumed owner decision on replay
(`research_system/authority.py:1504-1574`). Direct correctly labelled typed
activation and revocation negatives, plus restart revalidation, passed.

That repair closes the exact typed producer vehicle from the prior probe. The
prior closure requirement was broader: revocation must have no raw
correct-producer bypass. C-2 demonstrates that the sibling generic producer can
still mutate the same v2 grant. C-1 therefore cannot be treated as complete at
the authority-family level.

### Prior M-1 - closed

**Disposition:** `closed_exact_subject`

Activation now derives the accepted command/action-to-subject mapping from a
closed catalogue and requires the exact identity to be active
(`research_system/authority.py:127-138,464-511`; invoked from
`research_system/command/service.py:1949-1969`). The five inactive,
unresolved, wrong-hash, and wrong-subject variants reject without publication;
a later registry binding cannot wake the rejected proposal. The focused tests
passed.

### Prior M-2 - closed

**Disposition:** `closed_exact_subject`

The production R3 policy no longer accepts a caller actor-class map. It invokes
the scoped resolver with the bound `human` class
(`research_system/assurance/requirements.py:100-121`), while activation
requires the R3 policy grant to bind the exact bootstrap owner as human. Agent,
service, and non-owner-human variants reject without publication. The focused
tests passed.

## 5. New finding

### C-2 - preserved generic revocation can revoke a v2 scoped grant without the typed owner decision

**Severity:** Critical

**Disposition:** blocking; fix before acceptance

**Affected decisions/packages:** P-005, P-046, W2 authority lifecycle, Handoff
32 section 5A, WP6.3 scoped-authority foundation

**Claim**

The implementation partitions typed scoped-administration events by producer,
but does not partition the preserved generic revocation event by target grant
generation or activation lineage. Consequently, a generic legacy event can
perform the v2 state transition that P-046 reserves to
`RevokeIssuedAuthorityGrant` plus one exact typed owner decision.

**Direct evidence**

- Append seals only the two typed pairs
  `AuthorityGrantActivated/ActivateAuthorityGrant` and
  `AuthorityGrantRevoked/RevokeIssuedAuthorityGrant`
  (`research_system/store/ledger.py:375-383`).
- The same append method expressly exempts
  `AuthorityGrantRevoked/RevokeAuthorityGrant/ars://core/event/1.0.0` as a
  legacy authority producer (`research_system/store/ledger.py:456-475`). It
  does not inspect the target grant's projected generation before publication.
- Generic replay checks that the current record is active and that target/root
  IDs and hashes match, but it does not require legacy activation lineage or
  reject the v2 `schema_id` / `schema_version` markers
  (`research_system/projection/replay.py:331-360`).
- The typed replay branch does require the v2 schema identity, owner actor,
  `owner-bound-v1` marker, and unconsumed administration decision
  (`research_system/projection/replay.py:361-410`). The generic branch then
  applies the same terminal `status: revoked` update without those typed fields
  (`research_system/projection/replay.py:413-425`).
- The intended legacy root is narrowly scoped to revoke only its genesis
  publication grant (`research_system/authority.py:753-756`), and the normal
  generic command path resolves that authority before building the event
  (`research_system/command/service.py:1874-1916`). A raw append never executes
  that resolver check.

**Defensive failure scenario and observed result**

A production-class temporary-store check first activated a valid v2 scoped
grant through the exact typed decision path. It then submitted one generic
legacy revocation event to `EventLedger.append` for that already-active stream.
No revocation decision record was created. Observed:

```text
append_batch=true
position_before=3
position_after=4
tail_position=4
tail_hash_matches_snapshot=true
target_schema_version=2.0.0
replay_status=revoked
resolver_status=revoked
typed_revocation_decision=null
decision_count=1  # activation only
```

The probe used an isolated external temporary directory and left repository
state unchanged. This record intentionally omits a reusable event construction
recipe; the evidence required for remediation is the crossed producer/target
family and the observed append/replay state transition.

**Impact**

An in-process ledger caller can record an unauthorized revocation of a v2
owner-issued authority grant without the owner decision P-046 makes mandatory.
The hash chain and replay then preserve the false authority history as valid.
This can deny a valid owner-granted operation, corrupt the audit meaning of the
grant lifecycle, and make typed decision evidence disagree with durable state.
Because it changes canonical authority state and survives restart/replay, this
is Critical rather than a local hardening issue.

**Required disposition and exact interface change**

Preserve historical legacy replay, but separate historical compatibility from
new live admission:

1. New generic `RevokeAuthorityGrant` publication must use a one-shot,
   ledger-specific continuation issued only after the normal legacy authority
   resolver succeeds. Raw generic authority-event append must fail before tail
   advance.
2. Replay must classify the target by activation lineage. The generic branch
   may revoke only the exact genesis v1 publication-grant family; it must reject
   a target activated by `ActivateAuthorityGrant` or carrying the scoped v2
   schema markers. The typed branch remains the only revocation transition for
   that family.
3. Do not rewrite historical events. Derive/store an activation-family marker
   during replay from the already persisted activation producer and use it for
   the revocation-family check.
4. Add decisive negatives for both live append and direct replay: generic
   revocation against an active v2 grant must leave tail, projection, receipt,
   and resolver state unchanged. Retain positive controls proving (a) the
   legitimate genesis v1 generic command path and historical replay and (b) the
   typed v2 owner-decision path.

This is a bounded authority-admission correction. It does not require changing
legacy grant bytes, migrating existing history, expanding the root grant, or
altering the accepted WP6.3 pack/schema artifacts.

## 6. Adversarial disposition matrix

| Invariant or path | Exact-subject result | Disposition |
|---|---|---|
| Raw typed activation append | Rejected before publication | Prior C-1 typed vehicle passes |
| Raw typed issued-revocation append | Rejected before publication | Prior C-1 typed vehicle passes |
| Restart with missing/tampered typed decision | Replay/resolution reject | Prior C-1 typed evidence passes |
| Inactive/unresolved/wrong identity at activation | Rejected with no grant object or event | Prior M-1 closed |
| Later binding after rejected proposal | Grant remains unactivated | Prior M-1 closed |
| R3 agent/service/non-owner-human grant | Rejected with no event | Prior M-2 closed |
| Legitimate legacy v1 generic command | Accepted; genesis publication grant revoked | Compatibility positive passes |
| Legitimate typed v2 command with exact owner decision | Accepted; decision linked; v2 grant revoked | Typed positive passes |
| Generic legacy event targeting active v2 grant | Appended, replayed, resolver reports revoked without typed revocation decision | **Critical fail, C-2** |

## 7. Protected identity and validation evidence

### Protected Git identities

Compared from prior durable review commit `8f4eaadb...` to exact subject
`13c479d...`:

| Protected artifact | Base identity | Subject identity | Result |
|---|---|---|---|
| `.research-system/schemas/core` | `831ed486736d74df7c2d3a10d1ba70c2940e18d2` | same | unchanged |
| `.research-system/contracts` | `27f1e12e8ecfb5c6fb33377981a96410555cbd56` | same | unchanged |
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7298b994ca80fb43364ec53964b735f1c7e3929a` | same | unchanged |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | same | unchanged |

### Focused prior-finding regression tier

Command:

```text
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_direct_activation_append_requires_sealed_verified_decision
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_direct_issued_revocation_append_requires_sealed_verified_decision
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_restart_revalidates_immutable_activation_decision
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_restart_revalidates_immutable_revocation_decision
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_activation_rejects_unresolved_inactive_or_wrong_subject_identity
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_later_binding_cannot_wake_rejected_inactive_identity
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_r3_policy_grant_requires_bound_human_owner
  tests/research_system/unit/test_assurance_requirements.py::test_ledger_policy_has_no_caller_asserted_actor_class_input
  -o addopts= -p no:cacheprovider -p no:cov
```

Result:

```text
16 passed in 184.48s (0:03:04)
```

`PYTHONDONTWRITEBYTECODE=1` was set. The command used the verified pre-existing
main-worktree environment, not an environment-manager bootstrap in this review
root.

### Temporary-store semantic controls

One external temporary harness exercised production registry, command service,
ledger, object store, replay, and resolver classes. It completed in 54.9
seconds. Results:

```text
legitimate_legacy: receipt=accepted, producer=RevokeAuthorityGrant,
  target=<genesis v1 publication grant>, status=revoked
legitimate_typed: receipt=accepted, producer=RevokeIssuedAuthorityGrant,
  typed decision linked, target=<v2 scoped grant>, status=revoked
cross_family_probe: append_batch=true, tail 3->4, replay_status=revoked,
  resolver_status=revoked, typed_revocation_decision=null
```

### Targeted static and diff checks

The ten changed Python files in `8f4eaadb...13c479d...` were checked:

```text
ruff check <10 changed Python files>
All checks passed!

ruff format --check <10 changed Python files>
10 files already formatted

git diff --check 8f4eaadb29c27ef22068537096c2b798f546db4a..13c479d69ab1b5690fb8f51bce43f76ebbf4553b
exit 0
```

Green tests and static checks establish the implemented typed-path behaviour;
they do not negate the independently executed cross-family authority failure.

## 8. Residual risks and final decision

- C-2 is the only new blocking finding established by this review.
- The exact typed closure should be preserved while the generic family is
  sealed and target-partitioned; broad authority redesign is not required.
- The production control-store writer and acceptance runner remain later
  Handoff-32 work. This remediation subject does not complete them.
- No live grant, live owner decision, WP6.3 acceptance, Gate 6 transition,
  merge approval, or owner acceptance follows from this report.

**Final exact-subject verdict: `rework_required`.**

Acceptance requires one bounded correction that preserves legitimate legacy
history while preventing generic live append or replay from revoking a scoped
v2 grant. After that correction, a fresh exact-subject independent review is
required. Owner acceptance remains outstanding.
