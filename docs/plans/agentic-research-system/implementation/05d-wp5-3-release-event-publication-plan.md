# ARS WP5.3: Canonical Release-Event Publication Plan

> **Status:** implementation remediation complete; O12 remains pending independent
> Manager acceptance and merge. G5.3-A was implemented,
> independently remediated/reviewed, and merged in PR #90. WP5.2 was likewise
> independently remediated/reviewed and merged in PR #89.
>
> **Outcome:** publish an already verified, blocked P0 ReleaseGateDecision as exactly one canonical W2 event. Publication records a decision; it does not authorize Gate 5.

## 1. Scope, objective, and non-goals

WP5.3 owns O12: replace the temporary unpublished release-decision reference with a resolvable canonical W2 event, and require release verification to resolve that event.

The exact unpublished input is the complete typed ReleaseGateDecision emitted by the existing fake P0 evaluation path:

~~~text
research_system.evals.models.ReleaseGateDecision
canonical_event_ref == "unpublished:p0"
gate5_authorized == false
candidate_status == "blocked"
~~~

The exact output is one canonical W2 event:

~~~text
event_type: ReleaseGateDecisionPublished
schema_id: ars://core/event/ReleaseGateDecisionPublished
stream_id: <release_decision_id exactly; already an rgd_... ID>
payload.release_decision.canonical_event_ref: <ledger-allocated evt_... ID>
~~~

The full typed decision, its evidence identities, the event hash-chain entry, the accepted/duplicate receipt, and the deterministic replay projection are the publication record. A filename, path, header, candidate ID, status flag, output directory, or caller-selected event ID is never a substitute for the full decision evidence.

### Hard boundaries

- Do not implement WP5.2 variant parity, WP5.6 deletion/O15, live-provider enablement, Gate 5 acceptance, Gate 6, research computation, or paper claims.
- Do not alter W6 decision policy, W7/W8 parity policy, P0 coverage, fixture membership, deletion/retention behavior, or the blocked P0 disposition.
- Do not introduce a grant store, authority lifecycle, provider adapter, network client, direct ledger writer, generic permission bypass, or path-based trust rule outside the exact owner-approved prerequisite in `05e-wp5-3a-canonical-authority-grant-plan.md`. Until that implementation merges, this boundary keeps WP5.3 runtime blocked rather than licensing a fake authority source.
- Do not copy or read .env files; use credentials; invoke live providers or the network; serialize raw transcripts; or use restricted data.
- Configuration must be explicitly injected, non-secret, and schema-validated. An approved secret manager, if ever required, is a separate owner-gated follow-on, never a .env workaround.
- Do not request or provoke CodeRabbit during drafting. The Manager owns any normal repository review workflow after the plan PR.

## 2. Authoritative sources and precedence

| Source | Binding use |
| --- | --- |
| docs/plans/agentic-research-system/handoffs/05-gate5-orchestration-handover-prompt.md | Defines WP5.3 as canonical W2 publication, sentinel retirement, and release-time rejection of unresolvable references. |
| docs/plans/agentic-research-system/implementation/05-wp5-gate5-foundation-acceptance-plan.md | Master scope, Owner Record decisions D-G5-1 through D-G5-3, O12 ownership, and Gate 5 boundary. |
| docs/plans/agentic-research-system/implementation/05a-wp5-1-grading-integrity-plan.md and merged implementation | Accepted release-coordination/authority boundary; no widening of release semantics. |
| docs/plans/agentic-research-system/implementation/05b-wp5-4-release-tranche-plan.md and merged implementation | Pre-WP5.2 P0 evidence: 40 foundation cases, 15 blocked, zero live calls, 132 results, gate5_authorized=false, candidate_status=blocked. |
| docs/plans/agentic-research-system/implementation/05c-wp5-2-variant-parity-plan.md and PR #82 amendment | Approved post-WP5.2 re-baseline: 40 foundation cases, 15 blocked, zero uncalibrated mutations, 302 results, calibrated, gate5_authorized=false, candidate_status=blocked, with typed W7 parity evidence. |
| docs/plans/agentic-research-system/implementation/05e-wp5-3a-canonical-authority-grant-plan.md | Owner-approved G5.3-A prerequisite and the exact typed source, resolver, actor/scope, immutable-hash, bootstrap, revocation, expiry, and writer-lock contract. |
| docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md | O12 wording and the temporary P0 sentinel. |
| docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md | W2 identities, canonical JSON/hash, command validation, receipts, locking, idempotency, and replay. |
| docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md | W6 decision evidence, non-aggregation, blocked precedence, and privacy requirements. |
| docs/plans/agentic-research-system/design/07-runtime-adapters-and-policy-parity.md | W7 adapter/policy boundary and prohibited credential/provider handling. |
| docs/plans/agentic-research-system/05-p0-materialization-and-foundation-implementation-plan.md | Accepted P0 W6/W7 operating boundaries, explicit control root, fake/offline execution, retention, and release-tranche constraints. |

The accepted W2 typed contract and recorded Owner Record override this plan if any wording drifts. Later implementation must trace current module locations from these sources before editing; this plan does not resolve a conflict by inventing adjacent metadata, a caller assertion, or a new authority source.

## 3. Accepted state that must not change

| Invariant | WP5.3 treatment |
| --- | --- |
| gate5_authorized=false | Preserve exactly in verified source, event payload, replay projection, CLI output, duplicate path, and release verification. |
| candidate_status=blocked | Preserve exactly. Publication cannot promote, authorize, or unblock a candidate. |
| Approved source baseline | The PR #83 baseline is 40/15/zero-live/132. After the reviewed WP5.2 merge, the approved source is 40/15/zero-uncalibrated/302/calibrated with typed parity evidence. Record source ancestry and re-derive the applicable baseline; never hard-code 132 or 302 in the publisher and never publish a stale pre-WP5.2 decision after WP5.2 merges. |
| W6 owns decision evidence | Publisher consumes and compares W6 output; it does not recompute, reweight, or aggregate verdicts. |
| W7/W8 own parity evidence | Publisher records existing typed status only; it does not execute adapters or infer parity. |
| O15 is deferred | No deletion action, evidence deletion, retention change, or O15 closure. |

## 4. Publication contract

### 4.1 Source request and evidence

The command accepts a typed ReleasePublicationRequest:

~~~json
{
  "schema": "ars://evals/release-publication-request",
  "project_id": "prj_...",
  "release_decision_id": "rgd_...",
  "evaluation_runs_manifest_ref": "art_...",
  "control_binding_ref": "art_...",
  "publication_authority_grant_id": "agr_...",
  "publication_authority_sha256": "lowercase-hex-sha256",
  "idempotency_key": "release-publication:..."
}
~~~

It does not accept an arbitrary decision JSON object as authority. The request binds the command to stored typed evidence. Before locking, the service validates schema, registered references, project ownership, static request shape, and authorizer availability. While holding the W2 writer lock, it resolves and verifies each item again:

| Evidence | Required verification |
| --- | --- |
| Evaluation-runs manifest | Resolve through the accepted artifact/reference resolver; validate typed schema and canonical hash. |
| Candidate decision | Re-derive from the exact manifest and explicit control binding using the existing fake, offline evaluator; compare the complete canonical document and SHA-256. |
| Unpublished precondition | The source has canonical_event_ref exactly equal to unpublished:p0. Any other unresolved, malformed, or canonical value rejects. |
| Release identity | Project, release decision, baseline/candidate identity, coverage snapshot hash, all W6/W7/W8 evidence, decision, and restrictions equal the re-derived document. |
| Current P0 state | Supplied and re-derived input both retain gate5_authorized=false and candidate_status=blocked. |
| Control binding | Valid schema/hash and explicit injected control root; no cwd inference, credential, provider endpoint, or secret. |
| Authority evidence | Accepted resolver returns a current, unrevoked W2 grant covering actor, PublishReleaseGateDecision, project, and exact release decision. |

Use W2 canonical JSON and SHA-256. Do not use Python object equality, timestamps, paths, a reduced projection, or an adjacent status field. Canonical JSON uses the W2 subset: ASCII keys, allowed scalars/containers, no floats, deterministic keys, and no unsupported values.

### 4.2 Owner gate G5.3-A: accepted authority source

The present CommandService integrity checks and AuthorityGrant schema do not independently establish a trusted release-publication grant resolver or authority event source. `CommandService.submit` explicitly leaves authorization downstream, and W2 makes an unreferenced object inert. The Manager must obtain and record the Owner's accepted source before runtime implementation begins.

The record must name:

1. the W2 typed grant/reference source and schema version;
2. the resolver that proves authenticity and current/revoked status;
3. the actor identity source;
4. exact scope for PublishReleaseGateDecision, the project, and the rgd target;
5. immutable content identity/hash binding the command to the grant; and
6. expiry/revocation validation repeated under the writer lock.

**Current disposition: G5.3-A SATISFIED; G5.3-B(a) PRESERVED; WP5.3
IMPLEMENTED.** The approved W2 authority-source prerequisite was implemented in
PR #87, independently remediated/reviewed in PR #90, and merged. Actor IDs
remain attribution inside the trusted-local-operator boundary; cryptographic
principal authentication and its key/credential lifecycle remain out of scope.
Production publication uses the merged `LedgerAuthorityGrantResolver`. A
test-injected resolver remains limited to fail-closed interface controls and
does not satisfy the production authority path.

After an accepted decision, implementation may add a narrow injected
ReleasePublicationAuthorizer protocol. It verifies authority; it never creates
it. A CLI flag, path, environment variable, caller boolean, fixture, or
AuthorityGrant-shaped neighbouring document is not authority.

Before the gate is satisfied, the public command must fail closed:

~~~text
status: rejected
reason_code: release_publication_authorizer_unavailable
~~~

It appends no lifecycle event, allocates no event position, and changes no projection. This is a stop condition, not permission to add a permissive fallback.

### 4.3 Canonical W2 event

An authorized, verified request appends exactly one event:

~~~json
{
  "event_id": "evt_...",
  "event_type": "ReleaseGateDecisionPublished",
  "schema_id": "ars://core/event/ReleaseGateDecisionPublished",
  "project_id": "prj_...",
  "stream_id": "rgd_...",
  "payload": {
    "release_decision": {
      "release_gate_decision_id": "rgd_...",
      "canonical_event_ref": "evt_..."
    },
    "source_decision_sha256": "lowercase-hex-sha256",
    "evaluation_runs_manifest_ref": "art_...",
    "evaluation_runs_manifest_sha256": "lowercase-hex-sha256",
    "control_binding_ref": "art_...",
    "control_binding_sha256": "lowercase-hex-sha256",
    "publication_authority_grant_id": "agr_...",
    "publication_authority_sha256": "lowercase-hex-sha256"
  }
}
~~~

The event `stream_id` equals
`payload.release_decision.release_gate_decision_id` exactly; the existing
`rgd_` prefix is not added twice. There is no top-level `payload_schema`
field because the accepted generic event schema forbids it. The finalized event
must validate both `ars://core/event` and the strict full-event schema
`ars://core/event/ReleaseGateDecisionPublished` before hashing or persistence.
The latter schema constrains the complete payload with
`additionalProperties: false`.

The nested release_decision is the complete canonical typed decision, not the abbreviated example shown above. The event payload allows only typed identifiers, hashes, and approved decision fields. It excludes filesystem paths, raw outputs, transcripts, exception dumps, secrets, environment values, credentials, provider names/URLs, and unrestricted diagnostics.

The nested canonical_event_ref must equal the W2 ledger-allocated event ID. This needs a narrow typed internal EventDraft/finalizer seam:

1. CommandService passes a typed draft builder rather than an event ID.
2. Under the one-writer lock, the ledger allocates the next position and evt ID.
3. The finalizer receives only allocated identity/position context and creates the schema-valid payload.
4. The ledger canonicalizes and hashes with the previous hash, atomically appends, then stores/returns the receipt.

This must not weaken existing protection against caller-provided event_id, position, prev_hash, event_hash, or timestamps. The only new path is the internal finalizer for this command; no caller can preselect event identity.

### 4.4 Command, receipt, conflict, and idempotency

Register W2 command type PublishReleaseGateDecision, constrained to an rgd target and accessible only through CommandService. The command ID remains cmd. W2 idempotency uses the accepted caller-scoped tuple exactly:

~~~text
(actor_id, authority_grant_id, command_type, idempotency_key)
~~~

The canonical request payload hash, target stream, and project are part of
semantic equality. `command_id` identifies a submission but is not an
alternate idempotency scope.

| Condition | Result |
| --- | --- |
| Same tuple and same canonical request | Return the original accepted or rejected receipt; never append/reject again. |
| Same tuple, changed payload | Stable conflict receipt; no append. |
| Distinct valid command after decision is published | Stable rejected receipt with release_decision_already_published; no append. |
| Missing, untrusted, expired, revoked, or out-of-scope authority | Stable rejected receipt with release_publication_authorizer_unavailable or release_publication_unauthorized; no append. |
| Manifest/decision/hash/control/sentinel/P0 mismatch | Stable rejected receipt with release_publication_evidence_mismatch; no append. |
| Stale expected version | W2 conflict receipt with observed version; no automatic retry. |
| Schema/reference/project/stream violation | Deterministic W2 rejected receipt; no append. |

Rejected receipts retain W2 fields: status, reason code, bounded explanation,
observed version when relevant, and unmet preconditions. They are canonical
operational records, not lifecycle events. No raw exception, stack trace, path,
transcript, secret, or volatile timestamp enters their semantic identity.

The current receipt store is keyed only by `command_id`, so WP5.3 must add an
atomic typed index for the exact idempotency tuple plus payload hash. Under the
same writer lock, an exact retry returns the original receipt even with a new
submission ID; a changed payload conflicts. The index and receipt are published
as one recoverable operational transaction. A previously accepted or rejected
historical outcome is returned before evaluating a new authority state; a retry
after remediation uses a new idempotency key. New submissions validate current
authority before any append.

### 4.5 Replay, projection, and release verification

Add a pure reducer for ReleaseGateDecisionPublished that returns a
release-decision projection keyed by the exact `rgd_...`
`release_decision_id`, containing the canonical decision and evidence hashes.
Replay receives a deterministic injected schema validator/registry; it reads no
configuration, filesystem, network, clock, provider state, or resolver. A
release event fails closed when that validator is absent.

Replay must:

1. validate every event schema, contiguous position, previous hash, event hash, allowed stream, and event type before applying a reducer;
2. reject a release event if nested canonical_event_ref differs from event_id, canonical JSON/hash is wrong, a required evidence hash is absent, stream is not rgd, or P0 false/blocked state is changed;
3. expose a new materialized projection only after full validation succeeds;
4. recover from simulated append/projection interruption as old state or exactly one complete event/projection, never a half state; and
5. replay identical ledger bytes deterministically and idempotently.

Update eval release to resolve canonical_event_ref through the replayed ledger/projection and compare it to the re-derived decision. It must reject unpublished:p0, unknown event, wrong event type, wrong project/stream, event/payload self-reference mismatch, source hash mismatch, and projection mismatch. A resolved event never substitutes for W6 evidence re-derivation.

## 5. File map

| Change | Files | Purpose |
| --- | --- | --- |
| New contracts | .research-system/schemas/evals/release-publication-request.schema.json; .research-system/schemas/core/release-gate-decision-published.schema.json | Strict request schema plus a full event schema with ID `ars://core/event/ReleaseGateDecisionPublished`; ID patterns, evidence refs/hashes, `additionalProperties: false`, non-secret surface. |
| Publication domain | research_system/evals/release_publication.py | Frozen request/verified-publication/payload models, canonical comparison, authorizer protocol, reject mapping, pure builder. |
| Command schema | .research-system/schemas/core/command.schema.json | Register PublishReleaseGateDecision and rgd target constraint. |
| W2 ledger seam | research_system/store/ledger.py | Typed internal draft/finalizer under existing locking/atomic append; validate the fully allocated event against generic and release-specific schemas before hash/publish; protected fields retained. |
| Command boundary | research_system/command/service.py; research_system/command/models.py; .research-system/schemas/core/receipt.schema.json | New command validation, authority/evidence recheck, exact W2 idempotency, typed receipt scope, and finalizer routing. |
| Receipt persistence | research_system/store/receipts.py | Atomic idempotency-scope index for accepted/rejected/conflict receipts, payload-hash conflict detection, and crash recovery under WriterLock. |
| Replay/projection | research_system/projection/replay.py and current projection-model home | Injected deterministic schema validation, release reducer, and pure projection; absent release schema validation fails closed. |
| Evaluation public seam | research_system/evals/harness.py; research_system/cli.py | Verified source building, offline eval publish-release command, canonical resolution in eval release. |
| Synthetic fixtures | tests/research_system/factories.py | Synthetic request/grant-resolver/manifest/decision/event builders. |
| Unit tests | tests/research_system/unit/test_release_publication.py; tests/research_system/unit/test_command_service.py; tests/research_system/unit/test_replay.py | Models, hashes, authority, receipts, finalizer, replay. |
| Public-seam tests | tests/research_system/integration/test_release_event_publication.py; tests/research_system/integration/test_eval_cli.py; tests/research_system/integration/test_release_coordinator.py | Command-service/ledger/replay/CLI and negative controls. |
| Closeout only after proof | Gate 5 master plan; WP4.8 obligation register; required vault/decision record | Link immutable evidence and close O12 only after criteria pass. |

Do not change P0 coverage YAML, fixture corpus, W6/W7 specs, provider/adapter packages, deletion/retention modules, .env files, secret settings, or unrelated tests. If a listed module moved, trace the existing public seam and record the equivalent in the implementation PR.

## 6. Execution tasks

### Task 0 — manager authority gate and baseline

**Owner:** Manager for G5.3-A; implementation Worker for read-only baseline.

1. Record the authority decision required in section 4.2.
2. Confirm fake offline evaluation still emits the required blocked source decision.
3. Confirm the current service, ledger, replay, schema registry, and receipt seams.

~~~powershell
uv run --no-sync pytest tests/research_system/integration/test_eval_cli.py tests/research_system/integration/test_release_coordinator.py -q --no-cov
uv run --no-sync python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake --output C:/tmp/ars-wp53-evaluation-runs.json
~~~

Stop for absent/ambiguous authority source, non-fake transport,
network/provider activity, credential prompt, or a baseline that does not match
the approved value for its proven source ancestry. The read-only pre-WP5.2
baseline is 40/15/132/false/blocked; after WP5.2 merges it is
40/15/302/calibrated/false/blocked with typed parity evidence. Report evidence;
do not modify matrix or policy.

### Task 1 — red tests and typed contracts

**Owner:** implementation Worker after G5.3-A is recorded.

Write public-seam tests first. They prove:

- a valid-shaped request cannot succeed without injected accepted authority;
- request, generic event, and `ars://core/event/ReleaseGateDecisionPublished` schemas reject additional fields, a top-level `payload_schema`, paths, floats, malformed IDs/hashes, doubled/mismatched `rgd_` stream identity, `unpublished:p0` in an event, secret-like keys, and caller-supplied authorization booleans;
- equal typed evidence produces stable canonical JSON/hash despite key ordering;
- a payload cannot assert an event ID before ledger allocation; and
- false/blocked are exact values rather than truthy/falsy substitutes.

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_release_publication.py -q
uv run --no-sync pytest tests/research_system/integration/test_release_event_publication.py -q
~~~

The first red failure must describe the missing public contract, not an incidental import/fixture fault. Record the test and invariant in the implementation PR.

### Task 2 — green command-service and writer path

**Owner:** implementation Worker.

1. Register strict schemas.
2. Implement frozen models and canonical evidence comparison.
3. Add the narrow authorizer protocol and wire the implemented
   `LedgerAuthorityGrantResolver` from the G5.3-A prerequisite. Test-injected
   resolvers are permitted only for fail-closed interface controls and cannot
   satisfy the production path.
4. Add PublishReleaseGateDecision to the existing W2 validation order, including rechecks under lock.
5. Add the typed ledger draft/finalizer without exposing protected ledger fields.
6. Extend the canonical receipt model/store with the exact W2 idempotency-scope index; atomically persist accepted, duplicate, rejected, and conflict outcomes so exact retries return the original receipt and changed payloads conflict.

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_release_publication.py tests/research_system/unit/test_command_service.py -q
uv run --no-sync pytest tests/research_system/integration/test_release_event_publication.py -q
~~~

Negative controls: missing/unaccepted authority; wrong actor; expired/revoked/out-of-scope grant; manifest/document/hash mismatch; wrong project/stream; stale version; repeat changed payload; already published decision; concurrent submissions. Each failed control proves no event position or projection mutation.

### Task 3 — replay and offline CLI public seams

**Owner:** implementation Worker.

1. Add pure replay reducer/full validation.
2. Add explicit offline-only public command:

~~~text
research-system eval publish-release
~~~

It takes only schema-valid injected non-secret control/authority bindings and typed evaluation evidence. It must not expose provider options, credentials, raw decision blobs, or direct ledger paths.

3. Update eval release to resolve and compare canonical event evidence.

Post-implementation invocation contract. The Worker first verifies each parser
with `--help`, then materializes only synthetic, non-secret files under
`C:/tmp`. After the typed unpublished decision allocates its exact `rgd_...`
ID, the Worker builds the strict G5.3-A bootstrap input for that target,
initializes the absent control store, records its returned expected store
identity in the control binding, and runs these exact shapes:

~~~powershell
uv run --no-sync python -m research_system.cli store init --code-root C:/tmp/ars-wp53-code --control-root C:/tmp/ars-wp53-control --project-id prj_01978abc-1000-7000-8000-000000001000 --authority-bootstrap C:/tmp/ars-wp53-authority-bootstrap.json
uv run --no-sync python -m research_system.cli eval publish-release --config C:/tmp/ars-wp53-control-binding.yaml --actor-id act_01978abc-1002-7000-8000-000000001002 --authority-grant-id agr_01978abc-1001-7000-8000-000000001001 --evaluation-runs C:/tmp/ars-wp53-evaluation-runs.json --output C:/tmp/ars-wp53-publish-receipt.json
uv run --no-sync python -m research_system.cli replay verify --control-root C:/tmp/ars-wp53-control
uv run --no-sync python -m research_system.cli eval release --config C:/tmp/ars-wp53-control-binding.yaml --evaluation-runs C:/tmp/ars-wp53-evaluation-runs.json
~~~

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_replay.py -q
uv run --no-sync pytest tests/research_system/integration/test_release_event_publication.py tests/research_system/integration/test_eval_cli.py tests/research_system/integration/test_release_coordinator.py -q
~~~

Negative controls must reject: sentinel; unknown event; non-release event; foreign project/stream; self-reference mismatch; source hash mismatch; malformed event hash/position; missing evidence hash; true authorization; non-blocked candidate; and simulated append/projection interruption.

### Task 4 — regression, provenance, and closeout

**Owner:** implementation Worker, then independent Manager review.

1. Run focused and Gate 5 regression tests.
2. Re-run fake P0 evidence and verify the ancestry-applicable approved baseline: 40/15/zero-live/132 plus false/blocked before WP5.2, or 40/15/zero-uncalibrated/302/calibrated plus false/blocked after WP5.2. The publisher itself contains no count constant.
3. Inspect event/receipt canonical bytes, ledger hashes, projection, and absence of restricted material.
4. Run repository lint/type commands plus diff/scope checks.
5. Only then close O12 in the master/register/vault record. Never close O15 or claim Gate 5 accepted.

~~~powershell
uv run --no-sync ruff check research_system tests
uv run --no-sync pytest tests/research_system/unit/test_release_publication.py tests/research_system/unit/test_command_service.py tests/research_system/unit/test_replay.py tests/research_system/integration/test_release_event_publication.py tests/research_system/integration/test_eval_cli.py tests/research_system/integration/test_release_coordinator.py -q
uv run --no-sync pytest tests/research_system -q
git diff --check
git diff --name-only origin/main...HEAD
~~~

Run a documented narrower repository type/lint command in addition to these checks if it exists at implementation time.

## 7. Exact modelled invariants and test matrix

| ID | Invariant | Public evidence |
| --- | --- | --- |
| I-5.3-01 | Only PublishReleaseGateDecision through CommandService appends a release event. | Direct ledger/caller identity path is inaccessible or rejected. |
| I-5.3-02 | One writer per project serializes allocation, finalization, hashing, append, and receipt. | Concurrent valid calls give one event and original/duplicate receipt relationship. |
| I-5.3-03 | Event ID, position, prior hash, event hash, and timestamp remain ledger-owned. | Caller override attempts fail before append. |
| I-5.3-04 | Nested canonical_event_ref equals its own allocated event ID. | Event, canonical payload, and replay equality test. |
| I-5.3-05 | Full source decision and evidence identities compare through W2 canonical SHA-256. | Key reordering passes; semantic/evidence mismatch rejects. |
| I-5.3-06 | Authority fails closed and is checked while locked. | Missing, expired, revoked, wrong actor/command/project/decision reject. |
| I-5.3-07 | Success, duplicate, projection, and release verification preserve false/blocked. | Mutation negative tests across all public seams. |
| I-5.3-08 | W2 idempotency is exactly actor_id, authority_grant_id, command_type, and idempotency_key, with identical target/project/payload semantics. | Accepted or rejected exact retry, including a new submission ID, returns original; altered request conflicts; no second event or rejection. |
| I-5.3-09 | Rejected/conflict receipts are stable bounded operations, never lifecycle events. | Repeat failure returns same semantic receipt; ledger count unchanged. |
| I-5.3-10 | Replay is pure, validates complete ledger, and atomically projects. | Tamper and crash/restart controls. |
| I-5.3-11 | eval release accepts only a resolvable matching canonical release event and re-derived evidence. | Sentinel, unknown, foreign, tampered, partial reference controls reject. |
| I-5.3-12 | No .env, secret, provider, network, transcript, or restricted data crosses the seam. | Transport spies, schema negatives, source/output inspection. |

### Required red/green sequence

| Stage | Red test | Green evidence |
| --- | --- | --- |
| Request boundary | Valid-shaped request cannot be accepted because schema/model/authorizer binding is absent. | Only exact schema-valid, accepted-authority request reaches evidence verification. |
| Event identity | Caller cannot create arbitrary evt payload and no finalizer exists. | Ledger allocation produces one self-referential canonical payload without caller control. |
| Authority | Failed authority lacks release-specific stable behavior. | All authority controls return mapped stable receipts with no append. |
| Idempotency | Repetition behavior is undefined. | Same request returns original; changed one conflicts; distinct command cannot republish. |
| Replay | Event unrecognized or eval release accepts sentinel. | Replay projects valid event; release resolves and compares it. |
| Recovery | Interrupted append/projection is untested. | Recovery gives zero or one complete publication, never partial state. |

## 8. Obligation mapping

| Obligation/decision | WP5.3 action | Evidence for satisfaction | Owner/boundary |
| --- | --- | --- | --- |
| O12 canonical publication | Implement the exact path in this plan. | Event/receipt, replay, eval release resolution, negative suite, provenance review. | WP5.3 Worker; Manager closes after independent review. |
| W2 contract | Use narrow command/finalizer/reducer. | Schema, protected fields, hash-chain, receipt, idempotency, replay tests. | W2 is authoritative; no ad hoc storage write. |
| W6 evidence | Consume and compare complete decision; no recomputation. | Re-derivation/hash mismatch controls. | W6 owner. |
| W7/W8 policy parity | Record current statuses only; no adapter action. | Payload equality; no-provider/network controls. | W7/W8 owners; WP5.2 owns parity. |
| D-G5-1 | Preserve capability restriction. | No generic grant/permission scope expansion. | Owner Record. |
| D-G5-2/O15 | Keep deletion verification deferred. | No deletion diff or O15 closure. | WP5.6. |
| D-G5-3 | Preserve the ancestry-applicable approved P0 state. | WP5.4 baseline 40/15/132 and the approved WP5.2 re-baseline 40/15/302/calibrated; both retain exact false/blocked. No publisher count constant and no stale decision after WP5.2 merge. | WP5.4 implementation plus approved WP5.2 plan/amendment. |
| G5.3-A | Require accepted source before code. | Manager record names source/resolver/scope/revocation binding. | Manager; Worker stops if absent. |

## 9. Research-assurance triage

This is a software-assurance change, not a research computation. Relevant lanes are Output, Provenance, and Authority.

| Lane | Machine-checkable claim | Human review question | Partial/stop rule |
| --- | --- | --- | --- |
| Output | One typed event appears at most once and matches replay projection. | Does it record the existing decision without implying approval? | Any mismatch fails publication; do not close O12. |
| Provenance | Full canonical decision and evidence hashes are bound and rechecked. | Are all W6/W7/W8 fields present without restricted material? | Path/header/summary-only match is insufficient. |
| Authority | Accepted source proves current scoped authority at write time. | Is source truly accepted, typed, and independently resolvable? | No resolver/source means fail closed and Manager escalation. |
| Privacy/safety | Fixtures/outputs have no environment, secret, provider, network, transcript, or restricted content. | Do diagnostics expose sensitive material? | Exposure stops work and requires appropriate incident handling. |

No numerical assurance or paper-claim lane opens. Passing publication does not establish scientific validity, production readiness, or Gate 5 acceptance.

## 10. Acceptance criteria

WP5.3 is complete only when:

1. G5.3-A records an accepted typed source, resolver, actor/scope, immutable identity/hash, and revocation/expiry semantics.
2. The only success source is a re-derived full decision with exact unpublished:p0, false, and blocked state.
3. One authorized CommandService invocation writes exactly one ReleaseGateDecisionPublished W2 event whose nested ref equals allocated evt ID.
4. Schema, identity, canonical JSON, SHA-256, lock, expected-version, receipt, and idempotency behavior satisfy every invariant.
5. Authority/evidence/identity/replay negative controls are fail closed, stable, and append/projection free.
6. Replay is deterministic, pure, and cannot reveal a partial append/projection.
7. eval release rejects every sentinel/unresolvable/tampered reference and accepts only the matching canonical event plus re-derived evidence.
8. Focused/relevant regression tests pass and fake P0 matches its proven ancestry: 40/15/zero-live/132/false/blocked before WP5.2, or 40/15/zero-uncalibrated/302/calibrated/false/blocked after WP5.2. Integrated publication uses the latter after WP5.2 merges.
9. Tests and inspection prove no .env, credential, live provider, network, raw transcript, or restricted data; configuration is injected and non-secret.
10. Diff remains under 150 files and within section 5; it does not broaden into WP5.2, WP5.6/O15, live providers, Gate 5/Gate 6, research, or paper work.
11. O12 is closed only with immutable validation evidence; O15 remains open and Gate 5 remains unauthorized.

### O12 implementation closeout evidence (2026-07-13)

- Source ancestry is `080c54091efaa9120e5432e84f04efaa8f5f51db`, containing
  the PR #89 merge `a7866c3422a51a3a3b3dc8ff812504959e215c1b` and PR #90
  merge `080c54091efaa9120e5432e84f04efaa8f5f51db`.
- The fake-only source re-derived `40` fixtures, `15` blocked fixtures, zero
  uncalibrated mutations, `302` unique results, calibrated typed W7 parity,
  `gate5_authorized=false`, and `candidate_status=blocked`.
- The synthetic `C:/tmp` public flow appended exactly one event at position 3:
  `evt_019f5d87-4478-791e-9f23-2fc135cf6a27`, event SHA-256
  `9526a0a0a86bd47ad330a4d99f73378b1492f1e0ef2397a7885362b0a7318993`.
  Recomputed event hash matched; original and exact-retry receipt SHA-256 both
  equal `6e8d834b908aece4c4c6343844a7723ac13d13307dd1a23f49e3463acf92f019`;
  changed payload returned `idempotency_conflict`; replay projection SHA-256 is
  `4de38cf27abd48b687c32057d036a4f00b6b04260923d6eba72ec3e8aa57e592`;
  and `eval release` resolved the same event while retaining false/blocked.
- Focused publication tests include 39 strict authority, idempotency, recovery,
  concurrency, source/chain, sentinel, unknown, foreign, self-reference, and
  projection-tamper controls. The final research-system suite is `554 passed in
  629.18s`; Ruff passes; four semantic materializers pass. The P0 matrix checker
  reports only inherited `i/lf w/crlf` checkout bytes: LF-normalized worktree and
  index SHA-256 both equal
  `e7d61c32c817ca95d21f17d6d8557656b0c99bb3a823a85ee7704d245b0de94f`
  with no Git diff.
- This bounded WP5.3 implementation supplied initial O12 evidence. O12 remains
  pending independent Manager acceptance/merge; O15 remains open and Gate 5
  remains unauthorized.

### PR #92 review-remediation evidence (2026-07-14)

- The release verifier now rejects `unpublished:p0` and resolves only the exact
  published `evt_` reference. It compares the full decision plus manifest,
  control, authority, project, stream, event, source-hash, and false/blocked
  bindings. Manifest and control documents are immutable revision-1 canonical
  objects, and restart, byte/schema tamper, foreign-store, nested callback
  mutation, and producer-seam tests fail closed.
- `EventLedger` owns trusted generic and event-specific schema validation;
  release drafts cannot supply validators. Replay binds the payload authority
  ID/hash to the event and replayed active grant. Exact concurrent retries wait
  beyond the former five-second cutoff, while output preflight, durable
  same-directory temporary writes, and exclusive atomic publication cover
  pre-existing, interrupted, and racing receipt paths.
- The final focused command is `92 passed in 405.16s`; the full research-system
  suite is `568 passed in 733.86s`; Ruff passes; four semantic materializers
  pass. The inherited matrix CRLF variance remains LF-normalized byte-identical
  at SHA-256 `e7d61c32c817ca95d21f17d6d8557656b0c99bb3a823a85ee7704d245b0de94f`.
- The fake-only source again derived 40 fixtures, 15 blocked fixtures, zero
  uncalibrated mutations, 302 results, calibrated typed parity, and blocked.
  The real unmocked offline release path retained `gate5_authorized=false`.
- The final `C:/tmp` flow emitted event
  `evt_019f5e0e-dcc2-75ad-a656-629bc576a590` with event SHA-256
  `f7b5b20da0594461c866a32571e61ab110c14bf3bb58f3223cfc36c9dc65ab2f`;
  recomputation matched. Original/retry receipt SHA-256 is
  `d69d6873e716deabe27741150f14246ce43538065ca04dd3e4851c40d54514c0`,
  projection SHA-256 is
  `4887c39bc29bdbcd1601e5f0cb6ef0095def98b56e3b26c00d7cfbf2536e369c`,
  changed payload returned `idempotency_conflict`, and the ledger retained one
  release event. O12 remains pending independent Manager acceptance; O15
  remains open; Gate 5 remains unauthorized and unaccepted.

### PR #92 second review-remediation evidence (2026-07-14)

- Ordinary callers cannot construct or append a release draft. A module-private
  `CommandService` capability is required, remains stable across service
  restart, and `EventLedger` still owns allocation and mandatory schema
  validation.
- Historical exact retries return the original outcome after later
  expiry/revocation, while new keys revalidate current authority under the
  writer lock. Replay records activation/publication/revocation positions, so a
  later valid revocation does not retroactively invalidate publication.
- Registered strict producer/control schemas bind a complete immutable offline
  W6/W7/W8 snapshot. Re-derivation consumes stored typed evidence rather than
  current checkout discovery; restart, nested producer mutation, individual
  evidence-seam tamper, schema/hash tamper, and checkout-drift controls fail
  closed.
- Immutable object publication uses durable same-directory temporaries and
  exclusive atomic linking. Injected interruption/retry and concurrent
  identical writers retain one complete content-addressed revision. Receipt
  publication preserves the same non-clobbering discipline.
- Final-state validation passes as `412` unit plus `172` integration tests
  (`584` total); repository-wide Ruff passes. Four semantic materializers pass;
  the variant-matrix checker has only inherited CRLF variance, with normalized
  worktree/index SHA-256 both
  `e7d61c32c817ca95d21f17d6d8557656b0c99bb3a823a85ee7704d245b0de94f`.
  The fake-only source is `40/15/0/302/calibrated/false/blocked`.
- The final `C:/tmp` flow emits exactly one release event at position 3:
  `evt_019f5e97-a682-75b6-a93e-12edb773cbce`, event SHA-256
  `0a282e717390f3a673dbfc0f9e1d7f96222d56ad6b5dd548330ecf365278bd0f`.
  Recalculation matches; exact-retry receipt SHA-256 is
  `a22d4b8edf30b385d2c0561eda2b5279101d3a9d96b0aae5d437dbbf59ac7e8d`;
  changed source returns `idempotency_conflict`; projection SHA-256 is
  `32a3a73b39fc99313625e46071fdb2f003deca540fa1cde9b1a99eacd364b962`.
  Manifest/control hashes are respectively
  `ed3eee585f7013f3a94d3783fbeebe70547962685f78fe54bbe245b1b0112b32`
  and `af7c714f07823a493cf31264ac39f607ae3002f3e194e0abdd94dd0b94030869`.
- This evidence supports O12 implementation closeout, but independent Manager
  acceptance and merge remain pending. O15 remains open; Gate 5 remains
  unauthorized and unaccepted.

### PR #92 third review-remediation evidence (2026-07-14)

- Release draft issuance and consumption now occur atomically inside a narrow
  ledger-specific `CommandService` append boundary. No reusable capability is
  retained by the ledger or draft; caller mint, raw append, cross-ledger use,
  and reuse fail closed while ledger-owned event identity, position, timestamp,
  transaction identity, self-reference, and hash chain remain protected.
- `ReleaseGateDecisionPublished` requires its exact registered schema and is
  validated before and after allocation. A missing release schema leaves no
  durable event or projection mutation.
- The frozen publication-evidence schema strictly types every rehydrated nested
  boundary. Exact `GraderResult` fields round-trip without synthesized
  identities; retained-hash policy tamper is rejected using canonical
  source/preimage revalidation; D-G5-5 applicability/provider bindings use the
  canonical loaders. Actual producer perturbations and the reachable stored-
  evidence CLI restart seam are exercised rather than only post-production
  dictionary tamper.
- Immutable objects contend on one revision-scoped publication claim:
  identical concurrent content is idempotent, conflicting content yields one
  success and one conflict, and interruption/retry leaves one readable
  canonical revision. Each public authority resolution derives identity,
  scope, temporal, and revocation state from one verified projection.
- Final validation passes as `439` unit plus `172` integration tests (`611`
  total), including the `131`-test focused WP5.3 matrix. Scoped Ruff and four
  semantic materializers pass. The variant matrix has only inherited CRLF
  checkout variance; normalized worktree/index SHA-256 both equal
  `e7d61c32c817ca95d21f17d6d8557656b0c99bb3a823a85ee7704d245b0de94f`.
  The fake-only source remains `40/15/0/302/calibrated/false/blocked`.
- The final fresh `C:/tmp` offline flow publishes exactly one event at position
  3: `evt_019f62b8-2eda-7112-81a9-f0a50e2d323a`, event SHA-256
  `f3436581c548e9cd194bf416f55de3bc3dabad5a561f66594e1b29b532856fa5`.
  Recalculation matches; exact-retry receipt SHA-256 is
  `78800047ab320873b60031a575ca49059b8169565c9349c5c6089605c140ded6`;
  changed source returns `idempotency_conflict`; projection SHA-256 is
  `dd7b8d30479d85fe7efea05d0083f127e46e96c307076a94bbb8e3e15aa3b57b`.
  Manifest/control hashes are respectively
  `b96ad92a066e1241cac469786cc98b272174191146e4411736df212a208ae3c6`
  and `acd2187addd73f18c850fae644d86b1e0e6cf87684aaacb3d2cfb74bd220606c`.
- This evidence completes the Worker remediation package, but O12 remains
  pending independent Manager acceptance and merge. O15 remains open; Gate 5
  remains unauthorized and unaccepted.

## 11. Stop conditions

Stop implementation and report evidence to the Manager when:

1. G5.3-A has no precise accepted source/resolver/scope decision, or a proposed solution relies on metadata, configuration, path, .env, or caller claim as authority.
2. Work requires a new grant lifecycle/store, authority-policy redesign, provider adapter, network, credential, secret-manager integration, or live provider.
3. Full source cannot be re-derived from manifest/control binding, or canonical evidence/hash comparison fails.
4. Source decision is not exact false/blocked; its totals do not match the approved baseline for proven ancestry; or a post-WP5.2 run attempts to publish the stale 132-result decision.
5. Passing would require changing coverage/fixtures, W6/W7 policy, deletion/retention, O15, or Gate 5 acceptance.
6. The ledger cannot provide a narrow finalizer while retaining W2 protected-field and one-writer invariants.
7. Replay/recovery exposes partial publication, nondeterminism, or receipt/event inconsistency.
8. Any output, fixture, log, command, or review material exposes environment content, credentials, restricted data, raw transcripts, or provider/network traces.

The Worker must not work around a stop. The Manager records a new accepted decision/dispatch or explicitly defers.

## 12. Independent Manager review

Before merging implementation or closing O12, the Manager verifies:

1. G5.3-A relies on an accepted source, not adjacent metadata or an injected caller assertion;
2. CommandService cannot be bypassed and the ledger finalizer preserves all protected identity/hash/position fields;
3. full typed W6 evidence is compared, rather than a summary, path, header, or status flag;
4. event identity, chain hash, receipt, idempotency, locking, replay, and crash recovery have public-seam evidence;
5. false/blocked survives success, duplicate, projection, and release verification;
6. negative controls leave no event/projection mutation and diagnostics remain bounded/non-sensitive; and
7. diff/closeout do not widen into WP5.2, WP5.6/O15, providers, Gate 5/Gate 6, research, or paper claims.

Review immutable test/output hashes and source references directly; do not rely only on a narrative test summary.

## 13. Delivery shape

This document began as the reviewable planning contract. The implemented WP5.3
change remains one bounded PR well below 150 files, uses red-to-green public-seam
TDD, retains independent Manager review, and must not be merged by the
implementation Worker.
