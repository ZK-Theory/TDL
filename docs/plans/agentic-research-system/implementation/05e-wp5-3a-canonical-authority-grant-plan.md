# ARS WP5.3-A: Canonical W2 Authority-Grant Source and Resolver Plan

> **Status:** prerequisite direction approved; implementation plan blocked on
> owner decision G5.3-B. The Owner approved the canonical-source/resolver
> prerequisite on 2026-07-12, but has not yet selected the actor-authentication
> threat model exposed by adversarial review. WP5.3 runtime remains blocked.
>
> **Outcome:** a release-publication command can resolve one immutable,
> canonically activated W2 authority grant and prove, at write time, that it is
> store-provenanced, current, unrevoked, unexpired, attributed-actor-bound, command-bound,
> project-bound, and release-decision-bound.

## 1. Decision and scope

Owner decision G5.3-A is:

~~~text
Approved G5.3-A prerequisite: implement a canonical W2 authority-grant
source/resolver before WP5.3 runtime implementation.
~~~

This package closes only the authority-source prerequisite opened by
`05d-wp5-3-release-event-publication-plan.md` section 4.2. It does not publish
a release decision and does not close O12.

### In scope

- define a one-time, fail-closed authority root at new control-store creation;
- write immutable AuthorityGrant objects into the registered control store;
- activate the root and one release-publication grant as canonical W2 facts;
- derive current grant state from the verified ledger and immutable object;
- revoke the publication grant through the ordinary command/ledger path;
- expose a narrow resolver result that WP5.3 can consume later; and
- recheck current authority while holding the same W2 writer lock that protects
  the governed append.

### Out of scope

- WP5.3 release-event publication, sentinel retirement, or O12 closure;
- a general user, role, group, delegation, key-management, or policy service;
- grant renewal, mutation, reactivation, wildcard scope, grant delegation, or
  grant-to-grant equivalence;
- retrofitting or silently migrating an existing control store;
- live providers, network access, credentials, secret managers, `.env`, raw
  transcripts, restricted data, Gate 5 acceptance, Gate 6, or paper claims; and
- changes to W6 decision policy, W7/W8 parity, P0 coverage, fixtures,
  deletion/retention, or capability restrictions.

No path, filename, environment variable, CLI boolean, caller assertion,
neighbouring AuthorityGrant-shaped object, test fixture, or unreferenced object
is authority.

### Owner decision G5.3-B - principal-authentication boundary

The current local CLI and store identity provide integrity and canonical
provenance inside a registered control store. They do not authenticate that a
process presenting a public `act_...` ID is the human/role named by that ID.
Hash chains cannot create that missing principal-authentication fact.

The Owner must select one option before implementation dispatch:

- **(a) trusted-local-operator foundation (recommended):** accept the existing
  P0 local-operator trust boundary. The exact bootstrap-manifest hash is recorded
  in an Owner decision before the integrated publication run; the registered
  expected store identity binds it. Runtime claims canonical provenance,
  current scope, and revocation/expiry, but not cryptographic principal
  authentication. Release evidence records this capability restriction.
- **(b) authenticated principal first:** add an independently authenticated
  principal and signed Owner bootstrap record. This introduces key/signature
  lifecycle, credential handling, and a wider security package before G5.3-A.

This plan is written for option (a) but does not authorize its implementation
until the Owner accepts it. Option (b) requires a replacement plan. A high-level
approval to create a canonical resolver does not silently decide this boundary.

## 2. Authoritative sources and obligation register

| Source | Obligation | Disposition |
| --- | --- | --- |
| `design/02-task-event-and-artifact-schema.md` sections 7-9 and 13 | Immutable objects are inert until referenced by a committed event; CommandService order, one writer, canonical hashes, atomic batches, receipts, and replay are binding. | Tasks 1-4 and invariants A-01 to A-14. |
| `.research-system/schemas/core/authority-grant.schema.json` | Use the registered `agr_` identity and typed grant fields; do not treat document shape as activation. | Task 1 adds activation/revocation schemas and constrains the existing grant at activation. |
| `research_system/command/service.py` | Current integrity validation explicitly leaves authorization downstream. | Task 3 adds a narrow resolver seam; it does not silently authorize every command. |
| `05d-wp5-3-release-event-publication-plan.md` section 4.2 | Name source/schema, resolver, actor source, exact scope, immutable hash, and locked revocation/expiry validation. | Section 3 records all six under the G5.3-B threat model; Tasks 1-4 make them load-bearing. |
| `05d` hard boundary | A grant store/lifecycle is forbidden without a separately approved prerequisite. | This owner-approved package is that prerequisite and remains narrowly scoped. |
| W2 idempotency rule | Historical accepted/rejected outcomes are stable; new submissions validate current authority. | Task 3 and A-10. |
| Gate 5 owner record | `gate5_authorized=false`, `candidate_status=blocked`, D-G5-1 restriction, D-G5-2 deferral, and O15 open must remain unchanged. | Regression gate and stop conditions. |

Forward obligations not listed above remain with their owning WP. This plan
does not absorb WP5.2, WP5.3, WP5.6, O12, or O15.

## 3. Accepted G5.3-A authority record

This section is the exact record required by `05d` section 4.2.

### 3.1 Typed source and schema version

The source is the combination of:

1. an immutable `ars://core/authority-grant` version `1.1.0` object whose
   canonical SHA-256 is stored in the control store;
2. one canonical `AuthorityGrantActivated` W2 event that binds the exact object
   reference and SHA-256 to an `agr_...` stream; and
3. the verified current projection of that stream, including any later
   `AuthorityGrantRevoked` event.

Version 1.1.0 retains the registered grant/actor/command/risk/time fields but
replaces the unconstrained string-array `subject_scope` with a strict typed
object containing one `project_id` and one exact subject `{kind, id}`. Version
1.0.0 remains readable for existing evidence but is not accepted by this
resolver. An activation rejects a grant with `revoked != false`,
`delegable != false`, an empty or duplicate field, an unsupported subject kind,
a wildcard, or a grant whose identity differs from its stream. The immutable
object is never rewritten to represent revocation.

### 3.2 Root of trust and canonical provenance

A new control store is initialized once from a strict
`ars://core/authority-bootstrap-manifest` version `1.0.0`. The manifest is
canonical JSON and contains the project identity, owner actor identity, one
administrative root grant, one release-publication grant, their immutable
object hashes, and the exact `rgd_...` target. A new-store-only
`ars://core/store-identity` version `1.1.0` binds the bootstrap-manifest hash.
Its externally retained `store_identity` is SHA-256 over the canonical stable
identity fields: schema/version, generated nonce, project, and bootstrap-
manifest hash. Physical control root, code roots, and endpoint binding remain
verified manifest fields but do not define stable store identity, preserving
the registered backup/restore machine-move model. Changing any authority bootstrap field
therefore changes the expected store identity and fails the existing registered-
writer identity check; a self-recomputed manifest hash is not sufficient.

Initialization must:

1. prove the final target does not exist and create a same-volume sibling
   staging directory with no ledger events or authority objects;
2. bind the manifest hash into the version 1.1.0 control-store identity and
   derive the externally retained expected store identity;
3. write both grant objects and the complete initialization event batch through
   a private staging writer; competing initializers remain invisible and the
   absent-target atomic rename arbitrates the winner;
4. validate and flush the complete staged identity, objects, event batch, and
   ledger metadata before publication, using the platform's supported durable-
   file primitives and replaying the staged store before rename;
5. atomically rename the complete staging directory to the absent final control
   root, making the directory rename the genesis commit point; and
6. become unavailable for any new or changed bootstrap after the final store
   becomes visible. An exact retry after a lost response verifies the complete
   final store and bootstrap hash, then returns the original store identity
   without writing; a changed manifest or foreign store conflicts.

The typed unpublished release decision, including its exact `rgd_...` ID, must
exist before this initialization input is finalized. Initialization does not
interpret W6 evidence or publish the decision; it binds only the already-
allocated target ID into the publication grant.

Under G5.3-B(a), the final bootstrap-manifest SHA-256 must be recorded in an
Owner decision before the integrated publication run. Store initialization
requires exact equality with that approved hash. This is a human governance
anchor inside the trusted-local-operator threat model, not cryptographic
principal authentication; synthetic tests use explicitly test-classified
approval records and cannot publish the production P0 decision.

The initializer persists one strict internal command envelope:

~~~text
command_type: InitializeAuthorityRoot
actor_id: <bootstrap owner act_...>
authority_grant_id: <administrative root agr_...>
target_stream_id: <administrative root agr_...>
idempotency_key: authority-bootstrap:<bootstrap-manifest sha256>
payload: exact bootstrap hash plus both grant IDs and object hashes
~~~

It is created only inside the staged initializer, never accepted by
`CommandService`, and is reused byte-for-byte on resume. Its transaction has
exactly two ordered events with one command ID and transaction ID:

1. index 0/2: `AuthorityRootInitialized` on the root `agr_...` stream; this is
   the root grant's activating event; and
2. index 1/2: `AuthorityGrantActivated` on the publication `agr_...` stream,
   authorized by the root established at index 0 in the same genesis batch.

Both generic event envelopes are complete. Their event-specific typed payloads
record `authorizing_grant_sha256`; the publication activation also records the
target grant ID and `activated_grant_sha256`. Same-batch authority is valid only
for index 1 after index 0 and complete-batch validation; it cannot authorize a
third event. Missing, reversed, duplicated, extra, non-genesis, or split events
reject the complete batch. The root event is the single explicit
W2 bootstrap exception: its envelope references the root grant created in the
same atomic initialization transaction. Replay rejects the same event at any
later position or in a store whose identity lacks the exact bootstrap hash.

Ordinary post-genesis W2 batches retain the event-file rename commit point. The
atomic directory publish is a narrowly specified genesis rule because no
registered store exists before it. A crash before rename leaves only an inert
sibling staging directory; readers never discover it, and retry may resume only
after proving the complete staged transaction matches the same bootstrap hash.
A crash after rename leaves one complete store. Copying selected staged files
into a final store is forbidden.

Staging directories carry a strict bootstrap transaction marker and hash. An
exact retry may resume only a fully validated matching stage, preserving its
nonce, command, objects, and event bytes. A partial matching stage is rebuilt
inside a new private stage; a foreign-hash stage is inert and never adopted.
Legacy identity-only stores and current version 1.0.0 stores are classified
`authority_bootstrap_required` and remain read-only for this capability; they
are never repaired by deleting objects, rewriting identity, or appending a
late genesis batch.

This makes the externally retained expected store identity and genesis hash the
local P0 trust anchor. A directory path merely locates that store and cannot
replace identity/hash verification. Existing stores without this binding fail
closed; this package performs no in-place bootstrap or migration.

### 3.3 Resolver

Add a narrow `LedgerAuthorityGrantResolver`. Given a verified registered
control store, `authority_grant_id`, actor, command type, project, target, and
trusted UTC instant, it:

1. verifies store identity and the complete ledger/hash chain;
2. resolves exactly one activating event and its immutable grant object:
   `AuthorityRootInitialized` for the administrative root or
   `AuthorityGrantActivated` for the publication grant;
3. validates schema, canonical bytes, object reference, SHA-256, and stream ID;
4. derives current state through replay rather than reading a mutable status
   file;
5. rejects missing, duplicate, revoked, not-yet-effective, expired, malformed,
   foreign-project, wrong-actor, wrong-command, wrong-target, wildcard, or
   unsupported-scope grants; and
6. returns a frozen typed result containing the exact grant ID, object hash,
   actor, normalized scope, effective interval, activation event ID/position,
   current status, and revocation event identity when present.

The resolver does not create grants, mutate state, consult cwd, read provider or
network state, or accept a caller-provided `authorized` value.

### 3.4 Actor identity source

Under G5.3-B(a), the attributed owner actor is the exact `act_...` identity bound into the immutable
control-store authority bootstrap record. The release-publication grant repeats
that actor identity. Later WP5.3 commands must carry the same actor ID in the W2
envelope. Equality is checked against the verified root binding and the grant;
a role name, username, environment value, process identity, or adjacent profile
does not establish even that attribution. This proves canonical identifier
binding inside the trusted-local-operator boundary; it does not authenticate the
human or process presenting that public identifier.

### 3.5 Exact command and subject scope

The administrative root grant is non-delegable, has risk ceiling `R2`, permits
only `RevokeAuthorityGrant`, and has exactly:

~~~json
{
  "project_id": "prj_...",
  "subject": {
    "kind": "authority_grant",
    "id": "agr_<exact publication grant>"
  }
}
~~~

It cannot publish a release decision, revoke an unrelated grant, activate
another grant, delegate, or use a wildcard.

The publication grant is non-delegable, has risk ceiling `R2`, requires a
non-null `expires_at` strictly after `effective_at`, and is active on the exact
half-open interval `[effective_at, expires_at)`. It has exactly:

~~~json
{
  "allowed_command_types": ["PublishReleaseGateDecision"],
  "subject_scope": {
    "project_id": "prj_...",
    "subject": {
      "kind": "release_gate_decision",
      "id": "rgd_..."
    }
  }
}
~~~

Scope fields are ASCII, canonical, and validated against registered ID kinds.
Extra, missing, wildcard, prefix-only, candidate-only, or path-like scope is
rejected. The later WP5.3 authorizer must require exact typed-object equality,
not subset or string-prefix matching.

### 3.6 Immutable identity and current-state recheck

Every new governed command-specific payload binds `authority_grant_id` and
`authority_grant_sha256`; the existing generic W2 envelope continues to carry
the ID. Activation payload, immutable object path/bytes, resolver result,
idempotency index/receipt scope, and governed event-specific authority evidence
must carry the same hash. For revocation, the command/event additionally bind
the target grant ID and target object hash. Later WP5.3 request and event
evidence record `publication_authority_grant_id` and
`publication_authority_sha256` exactly.

For every new governed submission, CommandService first performs a cheap
fail-closed availability/shape check. After acquiring `WriterLock`, it samples
the process-composition-root UTC clock once (injectable only at construction for
deterministic tests, never from a command, CLI flag, or grant), reruns the full
resolver against the current ledger tail, and validates effective time, expiry,
and revocation before any governed write. Historical idempotent outcomes are
returned before evaluating a newly changed grant state; a new attempt after
remediation uses a new idempotency key.

Revocation is a canonical `RevokeAuthorityGrant` command producing exactly one
`AuthorityGrantRevoked` event on the target `agr_...` stream. It is idempotent,
cannot reactivate or alter the immutable grant, and is authorized only by the
administrative root from the same bootstrap batch. Concurrent revoke/publish
operations serialize on the same writer lock; whichever validates and commits
first determines the other command's current-state result.

The revocation command uses the current accepted W2 proxy tuple exactly:

~~~text
(actor_id, authority_grant_id, command_type, idempotency_key)
~~~

Target grant ID, project, expected version, and canonical payload hash are part
of semantic equality. An exact retry returns the original receipt; the same
tuple with changed target, reason, project, or payload conflicts without a new
event.

This is W2 section 13.1's explicit pre-WP2 stricter proxy, not a redefinition of
the later normalized `authority_scope` tuple. This prerequisite must add an
atomic ReceiptStore index keyed by the proxy tuple plus canonical payload hash
and authority-grant hash. Accepted, rejected, and conflict outcomes persist
with that index under `WriterLock`; an exact retry with a new submission command
ID returns the original receipt, while reusing a command ID outside its original
logical submission still rejects. Restart rebuilds/verifies the index from
events and operational receipt records before accepting new commands.

## 4. Contract and module map

| Surface | Planned change |
| --- | --- |
| Core schemas | Add strict store-identity 1.1.0, bootstrap-manifest, authority activation/root/revocation event payloads, and revoke-command payload schemas; retain generic W2 envelope validation. |
| Authority models | Add frozen bootstrap, canonical scope, projection, and resolver-result models; reject floats, paths, secrets, wildcards, and additional fields. |
| Control-store initialization | Extend the existing `ars store init` operator seam with a required strict non-secret authority-bootstrap document; implement same-volume staged genesis with absent-target, exact derived store-identity, flush/replay, and atomic-directory-publish preconditions; no public re-bootstrap operation. |
| Immutable object store | Write and resolve authority-grant objects by registered ID and canonical SHA-256; unreferenced objects remain inert. |
| Ledger/finalizer | Allocate protected event fields and atomically commit the root/activation initialization batch and later revocation event. |
| Replay/projection | Validate genesis position, event/object/hash bindings, stream order, and revocation monotonicity; produce a pure authority projection. |
| Resolver | Add `LedgerAuthorityGrantResolver` over verified store + replay projection, with injected trusted time. |
| Command service | Register only `RevokeAuthorityGrant` in this package and add the reusable locked resolver hook; do not register `PublishReleaseGateDecision` yet. |
| Receipt persistence | Add the W2 pre-WP2 proxy-tuple + payload-hash + grant-hash index atomically for accepted/rejected/conflict outcomes, including restart verification and new-command-ID exact retry. |
| Tests/factories | Synthetic, non-secret bootstrap/grant/store builders plus unit, integration, concurrency, tamper, and restart controls. |
| Documentation | Mark G5.3-A `implemented` only after merge evidence; do not close O12. |

If current module locations differ, the Worker traces the existing public seam
and records the equivalent path in the PR. The conceptual boundaries above do
not move with filenames.

## 5. Execution tasks

### Task 0 - baseline and seam trace

1. Verify the exact branch starts from merged `origin/main` containing PRs
   #78, #80, #82, #83, and #84.
2. Confirm the current AuthorityGrant schema, CommandService downstream-
   authorization statement, store identity, writer lock, object store, ledger,
   replay, receipt, and schema-registry seams.
3. Run the focused W2 command/ledger/replay tests before editing and record any
   pre-existing failure separately.

Stop if the branch or exact writable root is wrong, a source is absent, or the
baseline requires `.env`, credentials, provider/network access, or restricted
data.

### Task 1 - red contracts and genesis controls

Write public-seam tests first for:

- valid-shaped grant objects being inert without activation;
- bootstrap rejected on non-empty, already initialized, mismatched-store, or
  mismatched-project state;
- fully atomic staged-directory publication of store identity, root/publication
  activation, and ledger metadata with ledger-owned identities and a pure
  replay-derived projection;
- missing, reversed, duplicated, extra, split, or non-genesis root/activation
  events rejecting the complete transaction;
- wrong object hash, actor, stream, event position, transaction shape, or store
  identity failing replay;
- schema rejection of floats, additional fields, secrets, paths, wildcard
  scope, malformed IDs, `revoked=true`, or `delegable=true`; and
- crash recovery after staged identity, each object, batch flush, replay, and
  pre/post directory rename yielding either no visible store or one complete
  verified initialization, never a half state; and
- exact stage/final retry resuming or returning the original identity while a
  foreign/changed hash and a legacy identity-only store fail closed.

The first red failure must be the missing public contract, not an import or
fixture error.

### Task 2 - green immutable source and projection

1. Implement the frozen models and strict schemas.
2. Implement canonical object writing and the internal one-time same-volume
   staged-directory initializer.
3. Add ledger-owned root/activation finalizers and complete validation before
   atomic publication.
4. Add pure replay and projection with exact genesis/object/hash checks.
5. Prove restart and tamper behavior at the public store seam.

The public initialization shape is:

~~~powershell
uv run --no-sync python -m research_system.cli store init --code-root C:/tmp/ars-wp53a-code --control-root C:/tmp/ars-wp53a-control --project-id prj_01978abc-1000-7000-8000-000000001000 --authority-bootstrap C:/tmp/ars-wp53a-authority-bootstrap.json
~~~

The path locates a strict, non-secret genesis input only at owner/operator store
creation; it is never accepted by a governed release command or resolver. The
Worker must verify `--help`, success evidence, exact retry, changed retry,
non-empty target, and crash recovery through this literal process seam. No
ordinary command or CLI may invoke genesis initialization after store creation.

### Task 3 - resolver, revocation, and lock ordering

1. Implement `LedgerAuthorityGrantResolver` with injected UTC time.
2. Register `RevokeAuthorityGrant` through CommandService and the normal receipt
   path, implementing the missing atomic proxy-tuple idempotency index before
   the command is enabled.
3. Revalidate current grant state under `WriterLock` before revocation and
   expose the same reusable hook for WP5.3.
4. Add concurrency tests for publish-shaped authorization versus revocation;
   use a synthetic governed callback only to test the hook, not to claim WP5.3
   publication exists.
5. Prove exact retries return their original receipt and new submissions see
   current revocation/expiry state.

Negative controls cover missing activation, duplicate activation, wrong actor,
wrong command, wrong project, wrong `rgd`, not-yet-effective, expired, revoked,
changed immutable object, stale tail, and concurrent revocation.

### Task 4 - regression and prerequisite closeout

Run focused unit/integration tests, full ARS Ruff, full ARS pytest, schema
materializers/checkers, tamper controls, and a twice-built canonical bootstrap
fixture equality check. Inspect tracked diff and generated bytes for restricted
material.

Update `05d` from `approved prerequisite` to `prerequisite implemented` only
after immutable evidence passes independent Manager review and the code PR
merges. O12, O15, Gate 5, and Gate 6 remain open/unchanged.

## 6. Invariants and machine checks

| ID | Invariant | Required evidence |
| --- | --- | --- |
| A-01 | An AuthorityGrant-shaped object is inert without its one valid activating event: root-initialized for the root or grant-activated for publication. | Object-only, wrong-event-kind, and duplicate-activation integration tests. |
| A-02 | Bootstrap commits exactly once and only for a new empty target; exact lost-response retry returns the verified original identity and changed retry conflicts. | Empty/non-empty/restart/concurrent initializer and retry tests. |
| A-03 | Derived expected store identity binds the exact bootstrap manifest hash; self-rehashing a modified manifest cannot preserve identity. | Bootstrap-field mutation, expected-identity mismatch, and foreign-path/store-swap tests. |
| A-04 | Root plus publication activation, identity, and ledger metadata become visible only through one atomic staged-directory publish; projection is purely replay-derived. | Batch indexes/counts, pre/post-rename crash recovery, replay, and no-half-state test. |
| A-05 | Ledger owns event ID, positions, hashes, timestamps, and transaction fields; command/event-specific authority snapshots bind the authorizing grant hash. | Caller override, missing/wrong grant-hash, and finalizer tests. |
| A-06 | Governed command payload, grant object, `agr_` stream, activating payload, receipt index/scope, projection, resolver, and governed event evidence share one ID/hash. | Canonical equality plus one mutation control at every boundary. |
| A-07 | Publication authority is exact attributed actor + command + typed project/`rgd` scope; no wildcard/subset/prefix match. | One negative test per dimension, v1.0 rejection, and extra-scope test. |
| A-08 | Resolver status is active iff activation is valid, trusted time is in `[effective_at, expires_at)`, and no valid revocation exists. | Null/equal/inverted timestamps plus before/at/inside/at-expiry/after and revocation tests. |
| A-09 | Current-state validation repeats under the same writer lock before governed writes. | Deterministic revoke-versus-governed-operation race. |
| A-10 | Atomic pre-WP2 proxy-tuple receipt indexing returns the original accepted/rejected/conflict outcome for an exact retry, including a new command ID and restart; new keys evaluate current authority. | Same/new command ID, changed payload/hash, restart, and retry-before/after-revocation tests. |
| A-11 | Revocation is monotonic, idempotent, and never mutates or reactivates the grant object. | Duplicate/changed revoke and immutable-byte checks. |
| A-12 | Replay is pure and rejects tampered genesis, ledger chain, schema, object, or authority snapshot; no stored projection is trusted. | Restart/tamper suite with injected schemas and time. |
| A-13 | No `.env`, secret, credential, provider, network, transcript, or restricted data crosses the seam. | Transport spies, schema negatives, diff/output inspection. |
| A-14 | Gate 5 evaluation state is unchanged. | Applicable baseline remains 40/15/132/false/blocked before WP5.2 or 40/15/302/calibrated/false/blocked after WP5.2; this package contains no count constant. |

Software tests alone are insufficient: the implementation PR must map every
invariant to the exact test and code path that enforces it.

## 7. Validation commands

The Worker first traces current filenames, then runs the literal applicable
commands from the repository root using `--no-sync`:

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_command_service.py tests/research_system/unit/test_replay.py -q --no-cov
uv run --no-sync pytest tests/research_system/unit/test_authority_grants.py tests/research_system/integration/test_authority_grant_source.py -q --no-cov
uv run --no-sync python -m research_system.cli store init --help
uv run --no-sync ruff check research_system tools/ars tests/research_system
uv run --no-sync pytest tests/research_system -q --no-cov
~~~

New test paths are exact planned homes. If the repository's existing test
layout requires an equivalent path, the Worker records the mapping rather than
silently dropping a command. Exit zero without the declared state transition,
canonical object/event evidence, or negative no-mutation evidence is failure.

## 8. Research assurance requirements

- **Assurance lanes touched:** Output/Provenance and Authority.
- **Governing contracts:** W2 design sections 7-9 and 13; AuthorityGrant 1.1.0;
  Gate 5 owner record; `05d` section 4.2.
- **Machine-checkable claims:** A-01 through A-14.
- **Human-review-only claims:** whether the one-time control-store genesis trust
  root is proportionate for local P0 and whether the package remains narrow
  enough not to become a general identity/policy service.
- **Output provenance:** canonical object/event/projection hashes and exact code
  ancestry; synthetic non-secret temporary outputs only, outside `results/`.
- **Partial criteria:** report Partial rather than weakening bootstrap,
  canonical provenance, exact scope, lock ordering, revocation, expiry, replay, or
  privacy controls.

## 9. Stop conditions

Stop and return evidence when:

1. implementation needs path/config/caller/test assertions as authority;
2. bootstrap can run on an existing/non-empty store or after genesis;
3. an existing store would require silent migration or history rewriting;
4. exact actor, command, project, `rgd`, object hash, or current status cannot be
   derived from typed canonical state;
5. revocation/expiry cannot be rechecked under the same writer lock;
6. a general identity, delegation, renewal, key-management, provider, network,
   credential, or secret service becomes necessary;
7. a governed write can race revocation against a pre-lock snapshot;
8. replay accepts an inert object, partial batch, tampered chain, or mutable
   status file;
9. any Gate 5 invariant, coverage/fixture policy, deletion/O15 state, W6/W7
   policy, or capability restriction changes; or
10. diff exceeds 150 files or exposes sensitive/restricted material.

The Worker must not work around a stop. A new material authority or migration
decision returns to the Owner.

## 10. Delivery and review

Implementation is one bounded branch, `pipe/ars-gate5-authority-grant-source`,
with `[PIPELINE] P00:` commits. The Worker creates the branch before any edit,
works only from its exact declared writable root, commits and pushes, opens one
ready PR, and never merges. Do not provoke CodeRabbit mid-task; normal PR review
begins after the package is complete unless the diff approaches 150 files.

Independent Manager review must attack bootstrap circularity, store-identity
binding, exact scope closure, object/event/projection equality, lock ordering,
idempotency after revocation, replay purity, migration behavior, and restricted
material before merge. Only then may WP5.3 runtime implementation begin.
