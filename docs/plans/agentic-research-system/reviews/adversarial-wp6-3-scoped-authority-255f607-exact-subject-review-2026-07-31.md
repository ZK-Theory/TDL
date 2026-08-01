# Adversarial WP6.3 scoped-authority exact-subject review

**Date:** 2026-07-31
**Verdict:** `rework_required`
**Findings:** 1 Critical, 2 Major, 0 Minor
**Review mode:** independent, adversarial, exact-subject, no remediation

## 1. Exact review subject

| Field | Exact value |
|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\6f50\TDL` |
| Branch at review | `codex/wp63-scoped-grant-foundation` |
| Subject commit | `255f607084e9b847f4d3ed15ef8b383d5530c253` |
| Required base | `6dcdbe85bdbadbbc5c66d0e3cdedd1080d8411b6` |
| Base ancestry | `git merge-base --is-ancestor 6dcdbe85bdbadbbc5c66d0e3cdedd1080d8411b6 255f607084e9b847f4d3ed15ef8b383d5530c253` exited 0 |
| Independent-review entry status | only pre-existing setup dirt: `M .claude/CLAUDE.md`, `M .repowise-workspace.yaml` |
| Durable-record handoff status | the same setup dirt plus this inherited untracked review draft; no other path was adopted or changed |
| Review-owned path | this report only |

The subject contains 17 changed files, with 3,063 insertions and 87
deletions. Review scope covered the new scoped-grant schemas, grant model,
command admission, ledger append, replay/projection, runtime resolution,
assurance-requirement policy boundary, and the changed tests.

The accepted A0 schema-binding foundation is already present in the required
base ancestry. This review therefore does not treat the subject as an
out-of-order combination of A0 and the scoped-grant semantic delivery.

## 2. Governing authority and decision boundary

The review applied these sources in order:

1. the current owner instruction authorising handoff 32's recommended
   least-privilege issuer/scope direction and permitting the technical design
   choice within that standing authority;
2. `handoffs/32-wp6-3-management-handoff-authority-model-and-acceptance-tooling.md`;
3. `reviews/wp6-3-control-store-acceptance-mechanics-2026-07-30.md`;
4. `implementation/06g-wp6-owner-operated-session-amendment.md`;
5. `implementation/06d-wp6-1-owner-source-catalogue.md`;
6. `implementation/05e-wp5-3a-canonical-authority-grant-plan.md`;
7. `design/02-task-event-and-artifact-schema.md`; and
8. `design/05-research-assurance-and-independent-review.md`.

Permission to make the design choice exists in the current owner instruction.
There is, however, no durable repository decision that records the selected
bootstrap-owner/one-time-owner-decision design and its rejected alternatives.
That is a traceability gap, not a claim that the implementation was
unauthorised. This review does not infer owner acceptance, merge approval, or
activation of any live grant.

The decisive question is whether a caller can obtain durable authority without
the exact typed owner decision and whether later runtime changes can silently
expand an already active grant. The exact subject does not close those
boundaries.

## 3. Verdict

`rework_required`

The subject cannot be accepted because a reachable `EventLedger.append(...)`
path can publish a correctly labelled `AuthorityGrantActivated` event without
any owner-decision object. Replay then projects the grant as active and the
runtime resolver returns it as active. The strings identifying the expected
producer, owner, decision ID, and decision hash are caller-controlled event
data; they are not proof that the command service verified a decision.

Two further major defects make active authority depend on future runtime
configuration and permit an `agent`-class caller to satisfy the R3 human
acceptance path. These are not schema-shape observations: each was exercised
against the subject's production classes using isolated temporary stores.

## 4. Findings

### C-1 - Correctly labelled direct append bypasses the owner-decision authority boundary

**Severity:** Critical
**Disposition:** blocking

**Governing requirement**

- A scoped authority grant object is inert without the accepted lifecycle
  event.
- The post-genesis activation authority is a typed, immutable owner decision,
  not a caller assertion or an unreferenced identifier.
- Commands never mutate durable state without accepted authority.
- An authority event may be historical evidence only if its admission is
  structurally bound to the verified authority evidence it claims.

**Exact implementation seam**

- `research_system/command/service.py:1927-1941` performs the real
  owner-decision load and verification on the normal service path.
- `research_system/store/ledger.py:384-448` chooses a producer binding from
  event-supplied `event_type` and `command_type`, validates the declared schema,
  and appends; it does not verify the owner-decision object or require an
  unforgeable continuation from the command-service check.
- `research_system/projection/replay.py:260-324` checks copied root, owner,
  schema, and grant fields, then records the copied decision ID/hash and marks
  the grant active. It never loads or hashes the owner-decision object.
- `research_system/projection/replay.py:357-410` uses the same copied-evidence
  structure for revocation.
- `research_system/authority.py:1514-1575` contains the decision verifier, but
  the append/replay path does not invoke it.
- `research_system/authority.py:1577-1646` resolves the grant object against
  the projection without loading the decision projected as its authority.

**Attack**

In an isolated temporary store, the review:

1. initialised the real authority store and wrote a valid
   `ScopedAuthorityGrant` v2 object;
2. created no administration/owner-decision record;
3. constructed an `AuthorityGrantActivated` event with the exact active event
   schema, the exact active `ActivateAuthorityGrant` command schema identity,
   correct project/bootstrap/root/owner/grant fields, and a syntactically valid
   but nonexistent `administration_decision_id` plus arbitrary hash;
4. called the public `EventLedger.append([event])` path directly; and
5. resolved the grant through `LedgerAuthorityGrantResolver`.

**Observed result**

```text
append_event_batch_id=<published batch id>
resolved_status=active
decision_record_exists=False
decision_id_projected=<nonexistent decision id>
```

The event was durable, the projection treated it as authoritative, and the
resolver returned the grant as active even though the claimed owner decision
did not exist.

**Why the existing negative case is insufficient**

The subject correctly rejects a legacy/wrong-producer downgrade. That test
does not exercise the stronger attack: a raw append carrying all expected
producer labels and schema identities. Producer names in a payload are
self-attestation unless the append capability is sealed to the verifier that
established them.

**Impact**

Any in-process caller reaching the ledger can fabricate owner activation using
public data and arbitrary decision references. The normal revocation command
does call the same owner-decision verifier, but a correctly labelled direct
revocation append reaches `replay.py:357-403`, where the decision ID/hash are
again copied without loading or hashing the decision object. The review
executed the activation exploit and confirmed the revocation bypass by source
trace; it does not claim a separately executed revocation exploit. This defeats
the central least-privilege control and makes replay preserve fabricated
authority.

**Closure requirement**

Implement the bounded remediation contract in section 8. At minimum, a direct
correct-producer activation or revocation append with a missing, foreign,
mismatched, or wrong-hash owner decision must fail before any stream advance,
receipt, projection change, or grant-state change.

### M-1 - An active grant can pre-authorise unresolved identities that wake under later runtime bindings

**Severity:** Major
**Disposition:** blocking

**Governing requirement**

The accepted authority model requires exact active command identity and an
exact command/policy-action-to-subject mapping. An owner decision must decide
the authority being activated now; later registry/configuration changes must
not silently enlarge it.

**Exact implementation seam**

- `research_system/authority.py:395-445` validates grant syntax, duplicates,
  finite lifetime, and wildcard exclusions but does not resolve each allowed
  command/policy identity or enforce its semantic subject mapping.
- `research_system/command/service.py:1911-1926` resolves the scoped-grant
  schema itself but not every identity and semantic mapping embedded in the
  grant.
- `research_system/authority.py:1723-1748` and `1764-1791` defer active
  command/policy identity checks until the grant is used.

**Attack**

The review activated a grant through the normal command-service and real
owner-decision path. The grant contained the exact schema identity of an
existing but inactive `CreateAttempt` command and paired it with an
`assurance_requirement` subject scope. The current resolver denied use because
that command schema was not active. A separate temporary registry was then
constructed with the same runtime bindings plus `CreateAttempt` activated,
without changing the persisted grant or owner decision.

**Observed result**

```text
activation_status=accepted
before_binding=ArsError: authority command schema is not active
after_binding=active
after_binding_scope=assurance_requirement
```

**Impact**

An already active grant can acquire new operational force merely because code
or runtime bindings change. No fresh owner decision is required at the moment
the latent capability becomes usable. Activation also accepts a
command/subject combination outside the accepted closed mapping.

**Closure requirement**

Activation must reject every unresolved or inactive allowed identity and every
command/policy-action-to-subject mismatch. If future preauthorisation is a
desired feature, it needs a distinct inert/proposed lifecycle and a second
owner activation after all bindings resolve; it cannot be represented as an
active grant that wakes later.

### M-2 - The R3 assurance path accepts an `agent` actor class as human authority

**Severity:** Major
**Disposition:** blocking

**Governing requirement**

R3/P-005 acceptance is an attributed human-owner decision after evidence
review. Trusted-local actor attribution may be an accepted deployment
constraint, but it does not permit an actor explicitly classified as `agent`
to satisfy a human-only decision.

**Exact implementation seam**

- `research_system/assurance/requirements.py:45-72` accepts caller-supplied
  actor-class mappings for the production policy boundary.
- `research_system/assurance/requirements.py:102-124` forwards that mapping to
  the authority resolver for an R3 action.
- `research_system/assurance/requirements.py:170-174` describes attributed
  human authority but relies on the generic policy result.
- `research_system/authority.py:407-414` permits `human`, `agent`, and
  `service` in scoped grants without an R3-specific class restriction.
- `design/05-research-assurance-and-independent-review.md:478-483` assigns the
  R3/P-005 decision to Stephen after evidence review.

**Attack and observed result**

A grant limited to `allowed_actor_classes=["agent"]` was activated through the
normal owner-decision path. `LedgerBackedAuthorityPolicy` was supplied a caller
mapping classifying the caller as `agent`. `validate_requirement` then accepted
the R3/I2 authority check:

```text
activation_status=accepted
caller_actor_class=agent
r3_validation=accepted
```

**Impact**

The implemented assurance boundary does not enforce the human-only semantic
contract it advertises. There is not yet a production control-store acceptance
runner that could repair this upstream, so the present class must fail closed
until a canonical actor-class source and human-owner check are wired.

**Closure requirement**

`accept_r3_assurance_requirement` must require the exact human class and the
authorised accepting-owner relation. The runtime must derive the actor class
from a bound actor/profile authority source, not an unconstrained caller map.
Agent and service classes must be negative cases.

## 5. Adversarial disposition matrix

| Attack or invariant | Result | Disposition |
|---|---|---|
| Correct-producer direct activation append with nonexistent owner decision | Event appended; grant resolved active | **Critical fail, C-1** |
| Correct-producer direct revocation append with a fabricated/tampered decision reference | Normal command path verifies it; direct append reaches the copied-evidence replay seam; source-confirmed, not separately executed | Must be a direct negative in remediation |
| Inactive command identity embedded at activation | Activation accepted; use initially denied | **Major fail, M-1** |
| Same persisted grant after later command binding | Grant resolved active without new owner decision | **Major fail, M-1** |
| R3 check with actor explicitly classed as `agent` | Accepted | **Major fail, M-2** |
| Normal service activation before `effective_at` | Rejected as `scoped_authority_administration_unauthorized`; stream version remained 0 | Pass on the command path |
| Direct append carrying a future `effective_at` | Replay records it active, but resolution denies before `effective_at` and would wake at that time | Timing check does not close C-1 |
| Resolution before `effective_at` or at/after `expires_at` | Rejected by the closed timing checks | Pass |
| Grant object without activation event | Resolver rejects; object remains inert | Pass |
| Failed append followed by exact retry | Object remains inert until valid event; exact retry succeeds | Pass |
| Wrong-producer legacy downgrade | Rejected durably | Pass, but does not cover C-1 |
| Exact retry, restart/replay, changed-payload conflict | Covered by passing focused tests | Pass |
| Normal authorised revocation | Covered by passing focused tests | Pass |
| No wildcard, no delegation, finite expiry, importer prohibited | Schema/model/tests align | Pass |
| Closed subject-kind and prefix unions | Schema/model/tests align | Pass |

The legacy root grant's exact bytes and old command allowlist are unchanged.
The ordinary resolver does not grant it `ActivateAuthorityGrant`. C-1 instead
shows that the raw event path treats copied root/owner metadata as sufficient
to project activation.

## 6. Protected-byte and exact-state checks

The review compared the required base and exact subject:

| Protected artifact | Base tree/blob | Subject tree/blob | Result |
|---|---|---|---|
| `.research-system/schemas/core` | `831ed486736d74df7c2d3a10d1ba70c2940e18d2` | same | unchanged |
| `.research-system/contracts` | `27f1e12e8ecfb5c6fb33377981a96410555cbd56` | same | unchanged |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | same | unchanged |

The protected-path diff was empty. For additional context, the command schema
subtree remained `9ea0aec...` and the event schema subtree remained
`154ffc4...`; the decisive defects are runtime authority-admission defects, not
changes to those protected bytes.

## 7. Validation evidence

No test result is promoted beyond what actually completed.
The recorder did not rerun tests. The results and semantic-probe observations
below are the completed independent-review evidence carried into this durable
record; the code seams were re-read at the exact subject before recording them.

### Completed focused changed-surface tier

```text
tests/research_system/unit/test_scoped_authority_grants.py
tests/research_system/integration/test_scoped_authority_grant_activation.py
tests/research_system/unit/test_assurance_requirements.py
tests/research_system/unit/test_schema_registry.py

96 passed in 295.08s
```

The run used the repository environment with repository-level `addopts`,
coverage, and cache disabled for a focused semantic run, and bytecode writes
disabled.

### Completed propagation nodes

```text
tests/research_system/integration/test_authority_grant_source.py::
  test_genesis_is_atomic_replay_derived_and_exact_retry_is_read_only
tests/research_system/integration/test_authority_grant_source.py::
  test_authority_store_exact_retry_replays_activated_lifecycle_history
tests/research_system/unit/test_release_publication.py::
  test_authorized_verified_command_publishes_one_self_referential_event

3 passed in 72.70s
```

These nodes establish that the existing genesis/replay and guarded publication
paths still propagate at the exact subject. They do not negate C-1.

### Non-terminal tier

A four-module expansion covering authority-grant source, release publication,
and release-event publication remained non-terminal and emitted no result
under quiet output after approximately eight minutes. The process was
terminated. It is **not counted as pass or fail** and supplies no acceptance
evidence.

### Executed semantic probes

All attack probes used production classes and isolated external temporary
stores; they did not alter repository state:

- correct-producer direct append with a missing owner decision: reproduced
  C-1;
- inactive identity followed by a later runtime binding: reproduced M-1;
- agent-class R3 acceptance: reproduced M-2; and
- activation before effective time: rejected without stream advancement.

## 8. One bounded remediation contract

Deliver one vertical slice named **owner-bound scoped-authority admission**.
Keep it limited to scoped-grant activation/revocation admission, replay,
resolution, and the R3 consumer seam.

The slice must:

1. make scoped-grant administration events publishable only through a sealed
   ledger finalisation path that consumes a successfully verified typed owner
   decision, or equivalently re-load and cryptographically cross-bind that
   immutable decision at append and replay; caller-supplied producer strings,
   decision IDs, and hashes alone are never authority;
2. apply the same invariant to activation and revocation, with no raw
   correct-producer bypass;
3. resolve every allowed command and policy-action identity at activation and
   reject inactive/unresolved identities, wrong SHA/version, and every
   command/action-to-subject mapping outside the closed accepted catalogue;
4. keep future preauthorisation inert unless a separate owner activation occurs
   after binding;
5. require an exact human accepting-owner relation for
   `accept_r3_assurance_requirement` and fail closed for agent/service or
   unbound caller-class data; and
6. preserve protected bytes, legacy-root semantics, no delegation, finite
   lifetime, exact retry/read-only replay, changed-payload conflict,
   writer-lock, restart, timing, and inert-object behaviour.

Required decisive negatives:

- direct correctly labelled activation and revocation appends with missing,
  foreign-project, foreign-owner, wrong-type, wrong-target, mismatched-hash, or
  stale decisions reject before publication and leave the stream/projection
  unchanged;
- inactive/unresolved command or policy identities reject activation;
- semantically wrong command/action subject kinds reject activation;
- later runtime binding cannot wake an already persisted active grant;
- R3 rejects `agent` and `service` classes and accepts only the exact authorised
  human-owner relation; and
- pre-effective and expired grants remain rejected.

Out of scope for this slice:

- fabrication of live production grants or decisions;
- provider or cryptographic-principal redesign;
- expansion of the legacy root grant;
- delegation;
- unrelated schema, control-store, or release-publication changes; and
- modification of owner-accepted protected artifacts.

Before dispatch, add a short durable design decision recording the owner-ruling
provenance, the selected bootstrap-owner/one-time-decision model, the historical
event authority rule, and the rejected self-attestation alternatives. This
closes traceability; it is not a substitute for the runtime remediation.

## 9. Residual risks and final decision

- Revocation shares C-1's copied-decision replay structure but was not
  separately exploited in this review; remediation must make it an explicit
  direct-append negative.
- The administration receipt's special idempotency scope does not currently
  include command schema ID/version/SHA. Only one active administration version
  exists now, so this is latent; include exact identity before multiple versions
  can coexist.
- The production control-store writer/acceptance runner remains a later
  handoff-32 stage. Passing this foundation cannot fabricate live records or
  imply that stage is complete.
- The non-terminal four-module tier remains uncounted.
- Owner acceptance remains outstanding after remediation and independent
  exact-subject re-review.

**Final exact-subject verdict: `rework_required`.**

The subject's schema and normal command-service path are not sufficient to
establish authority while the reachable append/replay seam accepts fabricated
owner-decision evidence. No merge or owner-acceptance conclusion follows from
this review.
