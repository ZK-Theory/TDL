# WP6.3 pack unblock — owner decisions and W1 allocations

**Created:** 2026-07-28
**For:** the agent session that executed brief 27 (holds the loader branch)
**Responds to:** the two blockers reported against brief 27
**Base:** `origin/main` at `268d597`

Both blockers were verified independently against `origin/main` before these
decisions were taken. Both reports were correct. The brief-27 error about
`research_system/assurance.py` was also correct — that path is a package
(`__init__.py`, `models.py`, `requirements.py`), the brief was wrong, and the
dotted path resolves identically.

## Decision 1 — the frozen task-local stop retires by amending closure semantics

**Do not** revise the contract, and **do not** rewrite the task-local test's body.

The contract's own declared constant is
`every_defined_test_function_is_declared_durable_or_task_local` — that is
*defined ⊆ declared*. The equality assertion added by PR #173's F-2 remediation
is **stricter than the semantics the accepted contract actually declares**.
Amending it is a correction, not a weakening.

Change `_assert_test_surface_closure` so it enforces both real guarantees
separately, instead of collapsing them into one equality:

```python
bound_names = set(bindings["durable_test_functions"])
task_local_names = set(bindings["task_local_unbound_test_functions"])

assert bound_names <= set(globals())          # durable names must all exist
assert not bound_names & task_local_names
assert bindings["binding_closure"] == "every_defined_test_function_is_declared_durable_or_task_local"

defined = {n for n, v in globals().items() if n.startswith("test_") and callable(v)}
declared = bound_names | task_local_names

assert defined <= declared, f"undeclared test functions: {sorted(defined - declared)}"
assert bound_names <= defined, f"declared durable control is missing: {sorted(bound_names - defined)}"
```

What this preserves, which is everything F-2 was actually for:

- **no undeclared test** — `defined <= declared` still fails closed
- **no silent shrinkage of a durable control** — `bound_names <= defined` still
  fails closed

What it permits, deliberately: a **task-local** declared name may be absent once
its task has ended. That is the whole meaning of task-local, and it retires
expired scope markers as a class rather than one-off.

Delete `test_scope_stop_future_pack_is_absent_in_remediation_task` when you
create the pack. Its declaration stays in the frozen contract, which is correct —
it records that the contract-authoring task was scope-stopped, which remains
true forever.

Add a control proving the new semantics: a task-local name declared-but-absent
passes; a durable name declared-but-absent fails; an undeclared defined test
fails. Write the negative controls first.

## Decision 2 — W1 allocates the producer and requirement identities

Extend `.research-system/config/assurance-pack-object-allocations.yaml`, or add a
sibling file under `.research-system/config/` following the same model. Same
rules as the `asp_` allocation: append-only, bound by tests, producer barred from
minting.

**Allocated under W1 authority, 2026-07-28 — use these exact values:**

| Field | Value |
|---|---|
| `producer_actor_id` | `act_019fa9de-c8a4-7ca5-9e03-8da0c2159a4b` |
| `prospective_producer_actor_id` | `act_019fa9de-c8a4-7ca5-9e03-8da0c2159a4b` |
| `assurance_requirement_id` | `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` |
| `revision` | `1` |
| `acceptance_record_id` | `ard_019fa9de-c8a4-7978-90b1-8c73e8f1e5ed` |
| `acceptance_record_sha256` | **not allocatable — see Decision 3** |

All four identifiers were validated against the pack schema's `actorId`,
`assuranceRequirementId` and `recordId` patterns before being written here.

**The two actor fields are deliberately the same value.** The eleven
`required_distinct_pairs` constrain *roles*, and `future_pack_producer` is one
role. Two identities for one role would make the distinctness matrix
unevaluable. Add a binding test asserting the two fields are equal.

Note the producer actor must be distinct from `contract_author`,
`requirement_author`, `requirement_scope_reviewer`, `requirement_acceptor`,
`pack_scientific_reviewer` and `owner_acceptor` — six of the eleven pairs. The
producer is the authoring agent session, not Stephen and not the contract author.

## Decision 3 — the assurance requirement is accepted via the wp6-1 record pattern

`acceptance_record_sha256` is the one field that **cannot be allocated**. It
hashes an acceptance record that has to genuinely exist; minting a hash of
nothing is exactly the self-attestation the contract forbids.

There is already an in-repo precedent, and it is the one to follow:
`.research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml` and its
stage2 sibling — `schema_id`, `schema_version`, `record_type`,
`statement_provenance: owner_supplied_task_delegation`, `recorded_date`, an
explicit `acceptance_statement` in Stephen's words, and the accepted tuple.

Sequence, and it matters because `required_temporal_order` puts
`requirement_accepted` before `candidate_authored`:

1. Author the assurance requirement against
   `.research-system/schemas/assurance/assurance-requirement.schema.json`,
   carrying `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` at revision 1.
2. Author the acceptance record following the wp6-1 shape, carrying
   `ard_019fa9de-c8a4-7978-90b1-8c73e8f1e5ed`. **Stop here and surface the
   acceptance statement to Stephen** — you do not write his acceptance for him.
3. Once accepted, compute the record's sha256 over its canonical bytes and record
   it in the allocation file.
4. Only then author the pack candidate.

This satisfies `requirement_accepted → candidate_authored` honestly rather than
by construction.

## Order of work

1. Closure amendment + its negative controls (unblocks everything else).
2. Allocation file extension + binding tests.
3. Assurance requirement authored → acceptance surfaced to Stephen → record
   hashed → allocation completed.
4. Pack candidate, replacing every placeholder. Report the new
   `pack_git_blob` / `pack_raw_sha256` — the current
   `2728b135…` / `e0cb712b…` are placeholder-derived and not a reviewable
   subject.
5. Delete `test_scope_stop_future_pack_is_absent_in_remediation_task` and
   `test_external_identity_prerequisites_are_still_unallocated` in the same
   change that makes them false, not before.

## Validation

- Contracts directory green, including the WP6.3 module and both allocation
  modules.
- Every new control's negative written first and observed to fail.
- Ruff clean; pre-commit gates across 103 contracts.

## Decision 4 — the producer task identity, and the requirement's risk classification

Added 2026-07-28 after the executing session stopped at step 3. It was right to
stop: the `task_id` is not bookkeeping, and minting one would have forged the
separation proof.

**Both claims were verified before this decision was taken.** The
assurance-requirement schema does require `task_id` matching `^tsk_` (it is in
the schema's `required` list, and Decision 2's table has no sixth row). And the
binding is load-bearing —
`tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py:1921`
reads `if canonical_requirement["task_id"] != provenance["producer_task_id"]`,
with line 954 separately requiring `producer_task_id != review_task_id`. An
invented task id would manufacture exactly the separation the reviewer is meant
to prove.

**Allocated under W1 authority, 2026-07-28:**

| Field | Value |
|---|---|
| `task_id` | `tsk_019faddf-5d6c-7629-bc3b-b20112ad041d` |
| `task_revision` | `1` |

Validated three ways: matches `^tsk_`, matches the `task: tsk` prefix in the
id-kind registry, and round-trips through `validate_id(value, "task")`.

**What this allocation does and does not buy** (corrected 2026-07-29 after Codex
review; the original text overstated it). Lines 954–955 and 1921 are **string
comparisons**. They reject `producer_task_id == review_task_id` and require
`canonical_requirement["task_id"] == provenance["producer_task_id"]`, but nothing
binds any of those strings to an immutable Task object. Allocating the producer
task id under W1 removes one degree of freedom — the producer can no longer
choose an id that conveniently differs from the reviewer's — which is why
minting it was the wrong move and stopping was right. It does **not** make the
separation real: `review_task_id` and `review_session_id` remain free strings,
so a single session supplying all three still satisfies every check.

The separation proof is therefore only as strong as the external record substrate
that resolves these ids to real Task objects. **Superseded in part by Decision 5's
2026-07-29 correction:** the sentence that stood here claimed no such substrate
exists. It does — the external control store — and what was missing was a resolver
implementing the loader's protocol over it. That resolver is written but **not yet
merged** (see Decision 5).

The conclusion this paragraph exists for is unchanged either way. Treat the
allocation as **necessary, not sufficient**, and do not report the separation as
evidenced on the strength of it: `review_task_id` and `review_session_id` remain
free strings until the ids resolve to real objects, whatever the substrate.

**Risk classification — confirmed, and it is not a free choice.** Use:

| Field | Value |
|---|---|
| `requested_risk` | `R3` |
| `w5_epistemic_risk_floor` | `R3` |
| `action_semantic_risk` | `R3` |
| `requirement_relationship_grade` | `I2` |

The proposal was correct and it is better grounded than "matches the in-module
precedent". `docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md`
line 171: *"For R3/P-005 work, an I2 cross-family/context requirement-scope
review and Stephen's attributed acceptance are required."* So **R3 forces I2** —
they are not independent knobs — and I2 is also the contract's declared
`minimum_independence_grade`. R3 is the correct floor for a private assurance
pack governing six research-assurance lanes whose output supports publishable
claims, and R3 is what compels the attributed owner acceptance Decision 3 already
sequences.

Line 307 of the same document is why this had to come from the owner rather than
the executing session: *"A prospective producing actor may contribute a
requirement draft but cannot be the sole authority for its R2/R3 floor, lane
scope, or `not_applicable` decisions."* Drafting the requirement is in scope;
setting its floor is not. Stopping to ask was correct behaviour, not a delay.

**Consequence for lane scope.** The same clause covers `lanes` and any
`not_applicable` rationale. Draft them from the contract's six lanes and their
declared obligations, but surface the lane scope and every `not_applicable`
rationale to Stephen **in the same stop** as the acceptance statement. Do not
treat lane scope as a mechanical projection.

**Watch for staleness — and note actor equality does not implement the rule**
(corrected 2026-07-29 after Codex review). Line 171 stales requirement acceptance
if the actual producer **or its relationship** differs materially from the
accepted prospective relationship. Line 307 says that relationship is the
`actor / session / context / model-family / trace` tuple, not the actor alone.

Keeping `producer_actor_id` equal to `prospective_producer_actor_id` is therefore
**necessary but not sufficient**: work could resume under a different session,
context or model family with the same actor id and the equality would still pass
while the accepted relationship has materially changed.

**Current status, corrected** — the sentence that stood here said the rule "is not
implemented anywhere today", which was wrong twice over. `pack_loader` implements
the actor-equality half, and `routing/independence.py::independence_grade` grades
the full `same_actor / same_session / same_context_hash / same_model_family /
producer_conclusions_visible` tuple. What is true is that the grading function is
**not called from the assurance path**.

PR #194 narrows the gap without closing it: it resolves the relationship record the
requirement pins and rejects a lapsed validity window or a grade below the accepted
floor. But the accepted `producerRelationshipEvidenceRecord` schema carries an
*attested* `grade` plus two actor ids — **not** the five booleans — so no code path
recomputes the grade from evidence, and a stale tuple behind an unchanged attested
grade still passes. **Do not present either the equal actor fields or PR #194 as
satisfying the rule.** Recomputing the grade from a captured tuple needs a record
schema that carries the tuple, which is a superseding-revision question, not a code
change. Outstanding.

## Decision 5 — the records need a substrate, and it already exists

Added 2026-07-29 after Codex review; **corrected the same day** — see the
correction below before acting on anything in this section. The escalation that
opened it was wrong: step 3 is not blocked on an owner decision. It **is** still
blocked on implementation that is not in this branch — see "Steps 3 and 4 remain
PENDING on this branch" at the end of this section.

Codex found that `acceptedAssuranceRequirementRecord` requires
`scope_relationship_record_id`, and `producerRelationshipEvidenceRecord` requires
`relationship_record_id`, with no `rel_` identity allocated anywhere. Verified —
correct. Enumerating the whole record set rather than that one field shows the
scale: **23 required identity fields across the record definitions; Decisions 2
and 4 allocate five of them.**

The acceptance record alone requires four actor identities —
`requirement_author_actor_id`, `scope_reviewer_actor_id`, `acceptor_actor_id`,
`prospective_producer_actor_id` — plus `scope_relationship_record_id`. The
producer-relationship record requires `relationship_record_id`,
`subject_actor_id`, `object_actor_id`, a `grade`, and an
`effective_at`/`expires_at` validity window. And three of the eleven
`required_distinct_pairs` demand that `requirement_author`,
`requirement_scope_reviewer` and `requirement_acceptor` each differ from
`future_pack_producer`.

**Allocating five more UUIDs would unblock authoring and produce an unsound
record.** That is the wrong response, and it is worth naming why rather than
quietly doing it.

**Decision 3's precedent does not fit.** The wp6-1 records it points at are
*single-party* owner attestations — `statement_provenance:
owner_supplied_task_delegation`, one acceptor, one statement. The
assurance-requirement acceptance record encodes a *multi-party independence
structure*: a distinct author, a distinct scope reviewer, a distinct acceptor,
and a relationship record carrying an independence grade and a validity window.
Authoring that in-repo means one session writes both sides of every separation
claim it asserts — precisely the self-attestation the contract exists to prevent,
and the same failure Decision 4's correction above already identifies for task
ids.

### Correction, 2026-07-29: the substrate exists — this is not an owner decision

The paragraph that stood here concluded that **no external record substrate
exists** and that steps 3 and 4 were blocked pending an owner decision. That was
wrong, and it was wrong because the conclusion was reasoned from contract and
schema text rather than traced through the code.

`research_system/store/layout.py::require_external_control_root` refuses a
control root that is, contains, or is contained by any registered code root.
Under that root, `research_system/store/objects.py::ObjectStore` stores immutable
revisions whose filename is the SHA-256 of their canonical bytes,
re-canonicalises on read, and gates identity through `validate_id(object_id,
kind)` against the same id-kind registry Decision 2 extends. `cli.py` and
`evals/executors/release_tranche.py` use it: it is live, not a fixture.

That store supplies, structurally, every property the escalation claimed was
missing. Records live outside every code root, so a repository commit *cannot*
author them — which is what makes a multi-party independence record meaningful
rather than a producer writing both sides of its own claim. The store's own
digest is the referent `acceptance_record_sha256` lacked.

The consumer side was already built for it:
`pack_loader.py::_resolve_records` resolves each record through
`ContentAddressedAuthorityResolver` at three phases and rejects one that is
unstable across them, self-identifies wrongly, or is not active. The protocol was
specified and enforced; only test doubles implemented it. **The gap was a missing
adapter, not a missing design.**

Two further claims made during that escalation were also wrong. The staleness
rule *is* partly implemented (`pack_loader.py`, "prospective producer
relationship is stale"), and `routing/independence.py` grades the full
actor/session/context/model-family tuple — neither was wired to the assurance
path. And `GrantBackedAuthorityPolicy` was "grant-backed" in name only: a
dataclass wrapping a caller-supplied mapping, with no production caller, while
`authority.py` held real replay-resolved grants carrying actor, allowed commands,
risk ceiling, and a validity window.

### What tracing it through the code actually found

Reconciling the loader against the accepted record schemas surfaced a defect no
test could have caught, because every test supplied its own doubles: **the loader
required `record_id`, `authority_root`, and `lifecycle_state`, and no record
schema defines any of them.** Every record schema sets
`additionalProperties: false`, so those three checks were not lax — they were
unsatisfiable by any schema-valid record. The loader could never have accepted a
real record. Each record class carries its own identity field and its own
lifecycle field and active value (`status: active`, `review_state: completed`,
`grant_state: active`, …).

That single mismatch is the common cause behind all three "blockers". It is
resolved on the loader side, leaving the owner-accepted contract and schema bytes
untouched, by `pipe/assurance-control-store-resolver`:

1. `assurance_record` and `relationship_record` id kinds registered.
2. `ControlStoreAuthorityResolver` implements the protocol over the control store.
3. `_RECORD_ENVELOPE` reconciles the loader with the schemas, bound by a test that
   fails if the map and the schemas ever diverge.
4. Authority-root binding moves from the record body to the resolution channel —
   a record body asserting its own authority root is self-attestation anyway.
5. The staleness check resolves the pinned relationship record and rejects a lapsed
   validity window or a grade below the accepted independence floor. This narrows
   the gap the Decision 2 note describes; it does not close it, because the record
   schema carries an attested grade rather than the tuple needed to recompute one.
6. `LedgerBackedAuthorityPolicy` resolves R3 acceptance authority from replayed
   grants; the caller-supplied variant is renamed `DeclaredActionsAuthorityPolicy`
   so its name stops claiming a backing it never had.

### Steps 3 and 4 remain PENDING on this branch

**No owner decision is required** — that is what the correction above establishes,
and it is the only thing it establishes. **It does not make steps 3 and 4
actionable yet.**

This branch carries documentation only. Nothing in the six items above exists in
this branch's tree: they are on `pipe/assurance-control-store-resolver`
([PR #194](https://github.com/stephendor/TDL/pull/194)), and until that merges to
`main` the loader still requires `record_id`, `authority_root`, and
`lifecycle_state`, so it still cannot accept any schema-valid record. Reading this
document alone, on this branch, an agent would find no resolver and no envelope
map.

**Do not start step 3 or step 4 until all of the following hold on `main`:**

1. PR #194 is merged.
2. `_RECORD_ENVELOPE` covers exactly the record classes the accepted schema
   catalogue defines, and each entry's identity field, lifecycle field, and active
   value match that record's own schema — verified by its binding test, not by
   reading this list.
3. The lifecycle check reads each record's own state field, and no generic
   `lifecycle_state` check remains.
4. Authority-root binding is enforced at the resolution channel, and a foreign root
   is refused.
5. The producer-relationship staleness check resolves the relationship record the
   requirement pins, and rejects a lapsed window or a grade below the accepted
   independence floor.

If any of these is not true on `main`, steps 3 and 4 are still blocked — on
implementation, not on a decision. Verify against the tree, not against this
paragraph.

## Hard stops

- Do not edit `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
  or `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`.
  Owner-accepted at exact bytes at `449b0d00`.
- Do not mint any identity. Six are allocated above (five in Decision 2, the task
  id in Decision 4). The remaining record identities are allocated by writing the
  records into the external control store, not by minting UUIDs into repository
  YAML — but that path is not open until PR #194 is on `main`. Until then, stop
  rather than filling them in, exactly as before. See Decision 5.
- Do not set the risk floor, lane scope, or any `not_applicable` rationale on
  your own authority — draft, then surface.
- Do not write Stephen's acceptance statement. Surface it and stop.
- Do not self-review, close Gate A A7, dispatch WP6.4, or move Gate 6.
- Do not transition Jira or comment on it.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
