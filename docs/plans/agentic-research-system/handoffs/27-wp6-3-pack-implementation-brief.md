# WP6.3 pack implementation brief

**Created:** 2026-07-28
**Authorized by:** `reviews/wp6-3-gate-a-readiness-reassessment-2026-07-28.md` (readiness passed), KAN-56
**Workflow system:** `standalone` (no `.apm` initialized or used)
**Repository:** `stephendor/TDL`
**Base:** `origin/main` at `268d597`
**Execute in:** a fresh agent session with no inherited context from the WP6.3 contract work

## Copy-paste prompt

You are implementing the WP6.3 `TDL_private` assurance pack and the semantic
seam that loads it. Work only from this brief and the repository. Do not infer
intent from any other session.

### Precondition — verify, and stop if it fails

```bash
git fetch origin && git rev-parse origin/main
```

Must be `268d597…` or a descendant. Then confirm the accepted upstream artifacts
are unmodified:

| Artifact | Blob | SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7298b994ca80fb43364ec53964b735f1c7e3929a` | `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` |

These are **owner-accepted at exact bytes** (2026-07-28). If either differs,
stop and report — do not proceed, and do not edit them to make anything pass.

### The contract's hard stops are not your hard stops — read this carefully

`hard_stops` inside the contract constrains **the upstream contract-authoring
task**, not you. It lists `future_pack_file_created: false` and
`assurance_pack_id_materialized: false`. Both were correct for that task. You
are explicitly authorized to do the first, and the second is already done:

- `assurance_pack: asp` is registered in `.research-system/config/id-kind-registry.yaml`
- the object is allocated in `.research-system/config/assurance-pack-object-allocations.yaml`

Do not read those entries as prohibitions on this task. Everything else in that
list — no live calls, no research execution, no result or claim creation, no
credential access, no self-review as approval — **does** bind you.

## Deliverable 1 — the pack candidate

Author `.research-system/packs/tdl-private-assurance.yaml`. It does not exist
yet; that absence is the correct pre-acceptance state, not an error.

It must validate against `.research-system/schemas/assurance/assurance-pack.schema.json`
(`$id: ars://assurance/packs/tdl-private/1.0`, version `1.0.0`), which pins these
as `const` — copy them exactly, do not invent variants:

```
schema_id                 ars://assurance/packs/tdl-private/1.0
schema_version            1.0.0
pack_id                   TDL_private
assurance_pack_revision   1
canonical_repository_path .research-system/packs/tdl-private-assurance.yaml
distribution_scope        TDL_private
candidate_state           proposed
```

**`assurance_pack_id` must be exactly `asp_019fa860-3a4b-7784-839f-60f6277e6ce9`.**
This was pre-allocated under W1 authority precisely so the producer cannot mint
its own. Do not generate a new UUID. `tests/research_system/contracts/test_assurance_pack_object_allocation.py`
binds the allocation; read it before authoring.

Twenty required top-level fields: `schema_id`, `schema_version`, `pack_id`,
`assurance_pack_id`, `assurance_pack_revision`, `canonical_repository_path`,
`distribution_scope`, `candidate_state`, `producer_actor_id`,
`upstream_contract_reference`, `schema_reference`,
`assurance_requirement_reference`, `source_authority`, `references`,
`task_applicability_policy`, `distribution_controls`, `currency`, `lanes`,
`required_fixtures`, `limitations`, `core_boundary`.

### Lane and obligation structure

Six lanes, **69 obligations total**, distributed exactly:

| Lane | Obligations | Governing refs |
|---|---:|---:|
| `topology` | 11 | 5 |
| `stochastic_null` | 11 | 6 |
| `statistical_panel` | 12 | 5 |
| `representation` | 10 | 3 |
| `output_provenance` | 11 | 4 |
| `paper_claim` | 14 | 3 |

Obligation keys are `(lane_id, obligation_id)` pairs and must be unique across
the whole set — 69 distinct keys, no lane compensating for another. The 12
exact references (6 contract, 6 skill) all currently resolve at the base; every
lane's `exact_governing_reference_ids` must name only references in its
`allowed_lane_ids`, or `cross_lane`.

`required_fixtures` must include the three executed boundary fixtures:
`apf_tested_object_no_op`, `apf_degenerate_fallback`, `apf_claim_escalation`.

### What the candidate must NOT contain

- any review verdict, acceptance state, or owner decision — `candidate_state` is
  `proposed` and `candidate_may_assert_review_or_acceptance: false`
- any self-referential content hash of itself — the loader computes that
- any claimed identity for the schema or upstream contract beyond references;
  exact hashes come from external acceptance records
- any downstream scientific execution, result, or claim

## Deliverable 2 — the semantic seam

Implement `research_system.assurance.validate_tdl_private_pack_for_acceptance`.
The module does not exist; `research_system/assurance.py` must be created.

This is in scope because the contract's `required_sequence` places
`loader_computes_exact_candidate_subject_identity` **between** candidate
authorship and independent review, and the callable's `invoked_by` is
`[pack_loader, pack_review_gate, owner_acceptance_gate, every_pack_consumer]`.
Without it the reviewer would have to hand-compute the subject, which is exactly
the self-attestation the contract forbids.

The contract names eight required independent inputs. Honour all of them:

```
accepted_upstream_contract_subject
accepted_schema_subject
trusted_w1_w2_content_addressed_authority_resolver
independently_supplied_authority_root
opaque_external_record_ids
current_exact_reference_snapshot
raw_candidate_pack_bytes
evaluation_time
```

Required behaviour:

- compute `pack_git_blob` and `pack_raw_sha256` **from the raw candidate bytes**,
  in the loader. A candidate-supplied expected identity is `prohibited`.
- canonical byte surface is `git_blob_utf8_lf`. `.gitattributes` already covers
  `.research-system/**`, so committed bytes are LF; do not hand-normalize.
- resolve external records through the trusted resolver only. Candidate-supplied
  record bodies and hash oracles are prohibited.
- `failure_behavior: pack_unconsumable_and_no_acceptance` — fail closed. Never
  return a partial or best-effort acceptance.
- eleven required external record types must be resolvable: `canonical_actor`,
  `accepted_assurance_requirement`, `producer_relationship_evidence`,
  `contract_schema_authorship`, `independent_contract_review`,
  `independent_schema_review`, `stephen_contract_schema_acceptance`,
  `independent_pack_review`, `stephen_owner_acceptance`, `active_authority_grant`,
  `registered_pack_object`.

## Deliverable 3 — binding tests

Every machine-checkable claim above needs an enforcement artifact. Follow the
pattern already established in
`tests/research_system/contracts/test_assurance_pack_object_allocation.py`:
read declared values **from the governing artifact** rather than hardcoding
them, so drift fails.

**Put new tests in a new module.** Do not add to
`test_wp6_3_tdl_private_assurance_pack_contract.py` — its declared test surface
is closed at 37 defined functions and `_assert_test_surface_closure` will fail.

### Before filing any "X is not enforced" finding or writing a duplicate check

There are two enforcement layers: the JSON Schema and the runtime validator.
Three times across earlier review rounds, findings were filed against the
validator for things the schema already enforced more strictly. Before adding a
runtime check, **write the negative control first and watch where it fails.** If
the schema rejects it, a runtime check is unreachable — and an unreachable check
can never be given a watched negative, which is the thing this contract's own
fixture catalogue exists to prevent.

Look for the inverse too: an existing runtime check made dead by a schema
constraint firing first. Two are already known and are yours to resolve:

1. **`required_distinct_pairs` floor.** A comment in the contract test module
   claims the schema pins the list to 11 pairs. It actually sets `minItems: 7`
   with no `maxItems`. Correct the comment, and decide whether 7 is the intended
   floor — if eleven separations are load-bearing, the schema should say so.
2. **Unreachable status disjuncts.** The `key_a_status` / `key_b_status` /
   `forbidden_state_or_claim` branches in the two-key evidence block cannot fire;
   the external-record schema rejects those mutations first. Either drop them and
   note that the schema owns status, or add a control proving they are reachable.
   Do not leave them unlabelled.

## Environment

- **`uv run` fails in a fresh worktree** building `petls` (CMake cannot find
  Boost). Use the venv interpreter directly:

```bash
C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -q tests/research_system/contracts -o "addopts=" -p no:cacheprovider -p no:cov
```

- Contracts directory is **741 tests, ~11 minutes**. `pytest -q` flushes one
  line per 72 tests, so silence for several minutes is normal, not a hang.
- Branch `pipe/<desc>` off `origin/main`. Copy `.env` into any new worktree.
- Never `--no-verify`; the pre-commit gate runs ruff plus the contract validator
  across 103 contracts.

### The suite is red on this base, and it is not you

`tests/research_system/unit` and `integration` fail at `268d597` before you
change anything — a detached worktree at `449b0d00` produces byte-identical
output. Three defects are documented in
`26-research-system-suite-red-briefing.md`, including a WP6.1 currency gap where
86 generated event schemas require `command_schema_*` fields no production code
emits. **Establish this baseline before you start** so you do not chase someone
else's bug. Your gate is the contracts directory plus your new module.

## Validation required before reporting done

1. New pack validates against the pack schema, exercised by a test, not by hand.
2. Contracts directory green, including the 38-test WP6.3 module and the 7-test
   allocation module.
3. Ruff clean; pre-commit gate passed.
4. State the exact `pack_git_blob` and `pack_raw_sha256` your loader computes for
   the candidate — the independent review will bind that subject.

## Hard stops

- Do not edit `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
  or `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`.
  Owner-accepted at exact bytes; editing forces a fresh independent review.
- Do not mint a new `assurance_pack_id`.
- Do not assert review, acceptance, or owner decisions in the candidate.
- Do not self-review. Your own passing tests are not independent review.
- Do not close Gate A A7, dispatch WP6.4, or move Gate 6.
- Do not transition Jira or comment on it.
- Do not trigger, poll, or wait for CodeRabbit — Stephen owns that.
- Do not perform provider, API, OAuth, or session-credential work.
- Do not execute research, produce results, or write to results paths.

## What happens after this brief

1. Candidate authored, loader computes its exact subject identity.
2. Fresh independent pack review binds that exact subject.
3. Stephen's owner acceptance binds the same subject and review.
4. Gate A A7 closes.
5. WP6.1 currency re-verified. The `command_schema_*` gap is **resolved in
   direction**: producer emits, schemas stay (owner decision 2026-07-28). The
   implementation is separate work and does not block this brief.
6. KAN-57 / WP6.4 binding and preflight → Gate 6.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
