# 06i: WP6.1 Artefact Authority and Consumer Firewall Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> schema-contract-design, research-assurance-triage, and
> executing-plans-extras. Read W2 sections 8, 16-18, W5 sections 14.6 and 19,
> P-005, P-043, and RR-C1/RR-C2 from the 2026-07-30 rereview.

**Status:** PROPOSED 2026-07-30. This plan replaces the rejected authority and
test-only consumer portions of 06h/RM-03 revision 2. Dispatch is blocked on an
accepted 06h exact subject, fresh G-RM-3 review, and G-RM-10 approval of the
exact policy/command interfaces below.

**Goal:** make `RegisterArtefact`, `SetArtefactUseAuthority`,
`RecordScientificReview`, and the P-005 decision path authoritative in
production; provide one fail-closed artefact-use resolver that every result,
review, manuscript, claim, and sensitive-sidecar consumer must call.

The exact-subject runtime has no production claim/manuscript consumer. This
plan does not relabel a test helper as one. It creates the canonical production
port first, blocks direct object-store consumption structurally, and makes
RM-03/RM-04 wire their concrete CLI/use call sites through that port.

## Verified existing foundations

- `LedgerAuthorityGrantResolver.resolve` already checks current replay-derived
  grant status, actor, exact command, project/kind/id scope, effectivity, and
  expiry.
- `CommandService.submit` already orders lock, idempotency, expected version,
  preparation, event append, projection update, and receipt for implemented
  commands.
- `CommandService.with_locked_authority` demonstrates same-lock authority
  revalidation, but it is not by itself an event writer.
- `ControlStoreAuthorityResolver` is a content-addressed external read channel;
  it is not an owner-decision writer.
- The owner catalogue specifies `none -> candidate` for registration and the
  NA/NI controls at artefact register/use-authority rows. Generated schema
  shape alone does not enforce them.

## G-RM-10 exact decision subject

Before dispatch Stephen reviews and pins:

1. the four accepted command types and event/reducer mapping;
2. exact grants/actors/scopes usable for each command;
3. version 1 of the six-dimension consumer-policy registry;
4. the review-set resolver and P-005 decision binding;
5. the public `ArtefactUseResolver` request/result types; and
6. the atomic no-side-effect failure contract.

The decision record binds Git blobs and canonical SHA-256 values for the policy
registry and public interface specification. A Worker-authored policy file
without that accepted subject is not authority.

## File map

**Create:**

~~~text
.research-system/policies/artefact-consumer-predicates.v1.yaml
.research-system/schemas/policy/artefact-consumer-predicates.schema.json
research_system/artefacts/__init__.py
research_system/artefacts/authority.py
research_system/artefacts/use_resolver.py
research_system/evidence/__init__.py
research_system/evidence/consumers.py
tests/research_system/integration/test_artefact_authority_commands.py
tests/research_system/integration/test_artefact_use_resolver.py
tests/research_system/unit/test_artefact_consumer_boundary.py
~~~

**Modify:**

~~~text
research_system/command/service.py
research_system/projection/replay.py
research_system/cli.py
tests/research_system/unit/test_command_service.py
tests/research_system/unit/test_replay.py
~~~

Generated command/event schemas remain fixed. If an accepted schema cannot
express the catalogue semantics, stop Partial and request a separately reviewed
schema decision; do not weaken authority in Python to fit it.

## Authoritative interfaces

### Registration

`RegisterArtefact` ignores/rejects any caller attempt to choose initial use
authority. The authoritative transition is `none -> candidate`. The service
validates the manifest, recomputes exact content identity, resolves the current
grant for actor/project/`artefact`/new ID, verifies expected version and
idempotency, writes the immutable object, appends one event, and publishes the
accepted receipt under one writer lock.

### Use-authority transition

`SetArtefactUseAuthority` resolves:

- current artefact state from replay;
- exact artefact bytes/content hash;
- current command grant and exact subject scope;
- accepted consumer-policy registry identity;
- the named predicate's version and six-dimension rule;
- complete governing review set, reviewer eligibility/relatedness/independence,
  and satisfied-gate state; and
- Stephen's current P-005 decision for any claim/manuscript-promotion scope.

Caller-supplied `consumer_predicate` is an ID/version/hash reference, never
free-string policy. The event binds the accepted predicate identity, resolved
review IDs/hashes, decision ID/hash when applicable, and exact subject hash.

### Canonical consumption

`ArtefactUseResolver.resolve(request)` takes:

~~~text
artefact_id, exact_content_sha256, consumer_id, consumer_kind,
project_id, task/scope identity, predicate_id/version/hash,
evaluation_time, required_decision_kind
~~~

`consumer_kind` is closed:
`result_evidence | review_evidence | manuscript_evidence | claim_evidence |
sensitive_sidecar`. The resolver rebuilds current state from verified replay
and returns immutable resolved evidence only when all six dimensions and the
accepted predicate pass. Candidate, rejected, superseded, restricted, stale,
hash-mismatched, wrong-scope, wrong-consumer, incomplete-review, and missing
P-005 cases fail closed.

`research_system/evidence/consumers.py` exposes exactly these production
methods and no generic status-based fallback:

| Method | Fixed kind | Concrete first caller |
|---|---|---|
| `resolve_for_result` | `result_evidence` | RM-03 `brief.py::build_brief` for the closed result-assessment purpose |
| `resolve_for_review` | `review_evidence` | RM-03 `brief.py::build_brief` and RM-04 follow-up review export |
| `resolve_for_manuscript` | `manuscript_evidence` | RM-03 `brief.py::build_brief` and RM-04 manuscript pilot |
| `resolve_for_claim` | `claim_evidence` | RM-03 `brief.py::build_brief` for the closed claim-assessment purpose, with P-005 required |
| `resolve_sensitive_sidecar` | `sensitive_sidecar` | RM-03 `brief.py`/`importer.py` de-identification join |

Each method constructs the complete `ArtefactUseResolver` request itself; a
caller cannot downgrade the kind. Direct `ObjectStore.read` is not a
consumption decision. A structural test rejects new artefact reads in
`research_system/methods/**`, `research_system/evidence/**`, and the exact CLI
handlers unless the call is inside `ArtefactUseResolver`.

Sensitive sidecars contain no self-authorizing consumer list. Their access
policy is the replay-derived `SetArtefactUseAuthority` state for the sidecar
artefact, independently written from the sidecar bytes.

## Tasks

1. **Accepted policy registry.** Schema the six dimensions from W2 section
   16.2, define closed consumer kinds, canonicalize/hash the registry, and
   require the G-RM-10 accepted subject on load. Add wrong-but-valid registry,
   rule mutation, and self-pinned policy negatives.
2. **Registration authority.** Implement `RegisterArtefact` with forced
   candidate state, exact grant/scope checks, immutable object write, event,
   reducer, retry semantics, and atomic rollback.
3. **Review and decision evidence.** Wire the minimum accepted
   `RecordScientificReview` and P-005 `ResolveDecision` paths required to create
   replay-derived governing evidence. No review verdict alone promotes an
   artefact.
4. **Use-authority transition.** Implement the full resolver and
   `SetArtefactUseAuthority`; import every owner-catalogue NA/NI control rather
   than selecting examples.
5. **Production consumer port.** Implement the five fail-closed methods and the
   direct-read/call-graph boundary. RM-03/RM-04 may consume only this accepted
   interface.
6. **CLI writer.** Add bounded operator commands for registration, scientific
   review, P-005 decision reference, and use-authority transition. They submit
   through `CommandService`; they never call `ObjectStore.write` or
   `ledger.append` directly. This is the production writer missing from
   revision 2.

## Required negative controls

Every owner-catalogue NA/NI case is required, including importer actor,
missing/wrong/expired/not-yet-effective grant, wrong project/kind/id, wrong
subject hash, caller-selected accepted initial state, invalid transition,
policy mutation, free-string predicate, reviewer ineligibility/relatedness/
insufficient independence, incomplete review set, wrong-but-valid P-005
decision, direct object read, local status parse, projection reclassification,
separately valid authority-record substitution, superseded object, and
unauthorized sidecar consumer.

For every rejection assert **no event, no accepted receipt, no object revision,
and no projection mutation**. Same logical retry returns the original receipt;
conflicting retry is rejected.

## Validation and close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/integration/test_artefact_authority_commands.py tests/research_system/integration/test_artefact_use_resolver.py tests/research_system/unit/test_artefact_consumer_boundary.py tests/research_system/unit/test_command_service.py tests/research_system/unit/test_replay.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

Run the full `tests/research_system` tree once at final exact head because this
changes the shared command service and replay. Record the accepted policy
subject, grants, review-set evidence, P-005 fixtures, atomicity results, and
remaining unwired command families. If RM-01's append-path smoke gate already
exists, add the 06i command/event families before 06i close-out; otherwise
publish their exact smoke cases as blocking input to RM-01. Independent
exact-subject review and Stephen's G-RM-10 acceptance are distinct from test
success.
