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

## Hard stops

- Do not edit `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
  or `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`.
  Owner-accepted at exact bytes at `449b0d00`.
- Do not mint any identity. All five are allocated above; the sixth is a hash of
  a real record.
- Do not write Stephen's acceptance statement. Surface it and stop.
- Do not self-review, close Gate A A7, dispatch WP6.4, or move Gate 6.
- Do not transition Jira or comment on it.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
