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

The separation proof is therefore only as strong as the external record
substrate that resolves these ids to real Task objects, and that substrate does
not exist yet. Treat this allocation as necessary, not sufficient, and do not
report the separation as evidenced on the strength of it.

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
while the accepted relationship has materially changed. Neither this decision nor
the accepted-requirement record currently captures a prospective
profile/session tuple to compare against, so the staleness rule is not
implemented anywhere today. Do not present the two equal actor fields as
satisfying it. Capturing and comparing the full tuple is outstanding work, and it
belongs with the substrate question in Decision 5.

## Decision 5 — step 3 is paused: the acceptance record needs a substrate, not more UUIDs

Added 2026-07-29 after Codex review. **Do not start step 3 until this is settled.**

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

So the honest position is that steps 3 and 4 cannot produce a sound artifact on
the current base, and the blocker is not identity allocation. It is that
**no external record substrate exists to resolve these records against**, which
is the same root cause behind `acceptance_record_sha256` in Decision 3 and the
unbound task id in Decision 4. Three separate blockers, one cause.

This needs an owner decision before any further work. Do not improvise a fourth
patch.

## Hard stops

- Do not edit `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
  or `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`.
  Owner-accepted at exact bytes at `449b0d00`.
- Do not mint any identity. Six are allocated above (five in Decision 2, the task
  id in Decision 4). The rest are **not** allocated by design — see Decision 5;
  stop rather than filling them in.
- Do not set the risk floor, lane scope, or any `not_applicable` rationale on
  your own authority — draft, then surface.
- Do not write Stephen's acceptance statement. Surface it and stop.
- Do not self-review, close Gate A A7, dispatch WP6.4, or move Gate 6.
- Do not transition Jira or comment on it.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
