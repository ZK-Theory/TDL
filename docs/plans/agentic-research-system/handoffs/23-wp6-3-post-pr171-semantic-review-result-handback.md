# WP6.3 fresh semantic review handback, after PR #171

**Created:** 2026-07-28
**Responds to:** `22-wp6-3-post-pr171-semantic-review-handoff.md`
**Workflow system:** `standalone` (no `.apm` initialized or used)
**Repository:** `stephendor/TDL`
**Reviewer authority:** review only. No acceptance, implementation, Jira-transition, provider, migration, pilot, result, or claim authority was exercised.

## Verdict

**`rework_required`**

Findings are presented below. No remediation cycle was begun.

## Subject and computed identities

**Subject commit:** `034fb49475ae6d8c234835b02926b271f4485a7b` (verified `origin/main` after `git fetch origin`; unmoved).

Computed independently in a fresh detached worktree at the subject commit, after the LF refresh. Working-tree bytes and blob bytes hash identically for all three, so the canonical byte surface `git_blob_utf8_lf` held throughout.

| Artifact | Blob (`git rev-parse HEAD:<path>`) | SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `36164b2b32e211a2cbc7f980af14bcf7af59bf3f` | `8f58b47ad142dc17cdea31497af9070a8c09c0562da5afb51c832ebf150f6ba5` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `b9fbd4fbd4af06f9695c4b67fe45832291f258bc` | `c1a6e34b0a42de9ac0cb9f892a7fc199c20ec4e5b13318e63b54c66af4c0257f` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `c95ceee33ce396d5be5b036abbf6be26dac8e4cb` | `2a53469e112445ba7b8fb2a3c34c7889e8891593c51c7ce5ec1d091d84bc719c` |

All three match the packet-22 cross-check exactly. No divergence. No identity from packets 20 or 21 was carried forward.

## Preconditions

1. `origin/main` = subject commit. **Pass.**
2. PR #171 `MERGED` at `034fb494…`; PR #172 `MERGED` at `7347ae95…`. **Pass.**
3. CodeRabbit concluded on both PRs before merge. **Pass as written, with a caveat (see O-1 below).**
4. Fresh worktree detached at the subject commit, not derived from `C:\Users\steph\TDL`. **Done** — `…\scratchpad\wt-review`.
5. LF refresh applied immediately after creation. **Done.** Tree clean throughout; `git status --porcelain` empty at the end.

## Validation commands and results

```
"C:/Users/steph/TDL/.venv/Scripts/python.exe" -m pytest -q tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -o addopts='' -p no:cacheprovider -p no:cov
```

→ **`36 passed in 127.52s`**, matching the expected result. The broader `tests/research_system/contracts/` suite was not rerun; no finding below depends on it.

Supplementary, run from the same worktree:

- Independent re-resolution of all twelve `exact_reference_registry_snapshot` rows against `git rev-parse HEAD:<path>` + SHA-256 of blob bytes → **12 rows checked, 0 drifted**; 6 contract + 6 skill; every row `pack_acceptance_eligible: true` and in `acceptance_active_states`.
- Obligation closure by `(lane_id, obligation_id)` → **69 rows, 69 distinct keys**, across the six declared lanes (topology 11, stochastic_null 11, statistical_panel 12, representation 10, output_provenance 11, paper_claim 14); every `obligation_id` prefix equals its lane.
- Declared-vs-actual test surface → 35 test functions defined, 25 declared durable, 1 declared task-local, **9 undeclared**.
- `.research-system/config/id-kind-registry.yaml` → no `assurance_pack` kind; `assurance_requirement: asr` present, as expected.

## Blocker state, re-resolved at the subject commit

| # | Blocker as filed | State at `034fb494` | Evidence |
|---|---|---|---|
| 1 | Fresh independent review + owner acceptance | **OPEN** | `status: pending_independent_re_review` (contract:5); `review_gate.current_disposition: stop_for_fresh_independent_re_review_and_stephen_acceptance` (:615). This review addresses the review half only. |
| 2 | 6 skill pins stale | **CLOSED** | All 12 rows re-resolved, 0 drift (above). |
| 3 | Two contract references `pending: true` | **CLOSED** | Both rows `activation_state: active`, `pack_acceptance_eligible: true`; `current_pending_reference_ids: []` (:482). |
| 4 | `assurance_pack` id-kind absent | **Still absent, correctly sequenced after acceptance** | Registry has 25 kinds, none `assurance_pack`; contract records `allocation_state: blocked_pending_w1_registry_materialization_after_contract_owner_acceptance` (:147). |

## Per-scope-item findings

**1. External authority resolution — pass.** `contract_content_addressing.self_embedded_contract_hash: prohibited` (:12), `review_and_owner_acceptance_location: external_content_addressed_lifecycle_records` (:13), `candidate_may_supply_record_bodies: false` (:228), `caller_may_supply_record_hash_oracle: false` (:229), `candidate_supplied_expected_identity: prohibited` (:180). Enforced at `_validate_external_acceptance_with_authority` and exercised by `test_c1_coordinated_full_store_forgery_cannot_supply_bodies_and_hash_oracle` (test:3240) and `test_coordinated_candidate_and_oracle_replacement_does_not_change_external_authority` (test:2641).

**2. Exact-reference currency — pass.** 12/12 resolve at the subject commit; re-resolution is wired at all three phases (`authority_resolution_phases: [load, acceptance, consumption]`, :232) via `_resolve_authority_phase` (test:517), with `test_m2_coordinated_stale_reference_pin_fails_current_snapshot_revalidation` (test:3363) as the negative control.

**3. Two-key obligation closure — pass.** 69 rows, no duplicate, missing, extra, or lane-swapped row; `cross_lane_compensation: prohibited` on every lane; `apf_cross_lane_compensation` catalogued and referenced. Controlled by `test_complete_w5_obligation_rows_reject_missing_duplicate_swap_and_free_text` (test:2555) and `test_c2_two_key_evidence_rejects_schema_valid_swapped_lane` (test:3314).

**4. Lifecycle ordering — pass.** Nine-step `required_sequence` (:200–209), `accepted_state_may_be_inferred_from_candidate: false` (:210), `supersession_is_immutable: true` (:211), `stale_identity_behavior: block_and_require_superseding_revision` (:212). Fixtures `apf_acceptance_before_review`, `apf_accepted_candidate_state`, `apf_candidate_self_acceptance` are catalogued with `expected_outcome: blocked`.

**5. Provenance typing — pass on the current governed set, fail on the partial-application prohibition.** All three review record types are checked, by one helper, at three call sites (test:1644, :1651, :1861); `handoff_id` is bound across all three (test:1870–1876). That part is genuinely enforced, not merely declared. **But `review_provenance_partial_application: prohibited` and `review_provenance_required_record_types` are themselves read by nothing** — see F-1 below.

**6. Operator model coherence — pass.** `provider_neutral: true`, `session_family_selection: operator_selected`, non-empty subsets of the governance enums with `minItems: 1` and no maximum (schema:297–310). The validator reads `allowed_session_families` and derives permitted review-operator types from `review_operator_must_be_agent_operator_type` and `human_owner_may_act_as_review_operator` rather than from the agent allowlist (test:907–918) — correct, and it stays correct if either flag is relaxed. Schema and validator now agree on `human_owner`: `agentOperatorIdentity` (schema:690–695) narrows `typedOperatorIdentity` via `allOf` and excludes it, matching `human_owner_may_act_as_review_operator: false`. Consistent with P-042/06g; no provider-specific constraint remains without contract rationale — the two literal provider names left in the schema are the governance boundary enums, which the contract selects from.

**7. Fixture/lane agreement — pass.** Every lane's `exact_fixture_ids` entry is catalogued to that lane or to `cross_lane`, checked exhaustively at test:3587–3589. `apf_representation_frozen_fallback` is catalogued `lane_id: representation` with `target_invariant: invariant.representation.prohibited_refit_and_fallback` (:537), matching obligation `representation.prohibited_refit_and_fallback` (:403); `apf_degenerate_fallback` no longer appears in the representation lane.

**8. Intended negative cases — pass, and none of the five #171 controls is vacuous.** Each was checked against the question "would this still pass with the defect reintroduced?":

- `test_review_provenance_is_required_on_every_review_record_type` (test:3422) mutates `review_task_id` and `review_session_id` on each of the three records and matches on a per-label message. Restore the pack-only check and the contract and schema iterations fail. **Not vacuous.**
- `test_review_provenance_accepts_any_contract_allowed_session_family_and_agent_operator` (test:3454) asserts its own precondition (`claude_standalone` / `claude_task_agent` currently admitted) before relying on it, rather than pinning the allowlist to a pair. Restore a Codex `const` and it fails. **Not vacuous, precondition guaranteed.**
- `test_review_operator_outside_the_contract_operator_model_is_rejected` (test:3494) exercises both layers separately — schema rejection for `human_owner` and an out-of-enum family, then a contract narrowed to `codex_standalone` so the validator branch is reachable and the allowlist is load-bearing rather than decorative. **Not vacuous.**
- `test_review_provenance_records_must_share_one_stable_handoff_id` (test:3549) diverges the pack record's `handoff_id` and matches the specific message. **Not vacuous**, with the limitation that only one of the three branches has a negative control; the docstring states the reason honestly (mutating the other two fails earlier on the acceptance record's embedded review hashes).
- `test_lane_may_not_declare_a_fixture_catalogued_to_a_foreign_lane` (test:3575) checks all lanes exhaustively, asserts the specific representation swap, and adds a pack-side negative control on a mutated contract supplied through a trusted fixture authority. **Not vacuous.**

The PR #169 correction points also hold: negative-test messages are matched specifically rather than by bare exception type, lane swaps are keyed on tuples, `test_upstream_contract_and_schema_subjects_resist_stale_foreign_and_coordinated_replacement` compares against an independent Git subject, canonical bytes are reused via `_resolve_committed_bytes`, and `test_reference_semantic_compatibility_rejects_forbidden_wording_variations` is parametrized over prohibited semantic variants.

## Findings

### F-1 — a contract-declared governed set that no check reads (the F-1 remediation clause is itself inert)

**Severity: rework.** `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml:241–245` declares:

```yaml
review_provenance_required_record_types:
  - independent_contract_review
  - independent_schema_review
  - independent_pack_review
review_provenance_partial_application: prohibited
```

Neither key is read by any executable code. A repository-wide search finds them only in the JSON schema, as `const`/shape constraints (schema:281, :288), and in two test docstrings (test:902, :3426). The three provenance checks are hardcoded literal call sites (test:1644, :1651, :1861). Adding a fourth entry to `review_provenance_required_record_types` — or adding a fourth review record type without a call site — produces no failure. That is the F-1 defect class exactly: a clause written at the level of a class, enforcement written at the level of instances, and no artifact connecting the two. The list currently *describes* the checks that happen to exist; it does not *govern* them.

The prior review's own remediation guidance was to make the declared set the thing the validator iterates. The declaration landed; the iteration did not.

**Sibling artifacts covered by the same governing clause** (a contract key naming a governed set must be consumed by the check it governs). All are in these exact bytes:

| Contract key | Line | Status |
|---|---|---|
| `review_provenance_required_record_types` / `review_provenance_partial_application` | :241–245 | Not read. Three hardcoded call sites. |
| `required_executed_boundary_fixture_ids` | :236–239 | Not read. Duplicates `upstream_executable_fixture_ids` (:542) with no agreement check; `test_no_op_degenerate_and_claim_escalation_rows_have_upstream_negatives_and_downstream_stop` (test:2527) pins the *second* list as literals, so the two copies can diverge silently. `downstream_scientific_execution_fixture_ids` (:544) is a third copy. |
| `required_distinct_pairs` (11 pairs) | :260–271 | Not read. A hardcoded 5-actor distinctness set (test:1667–1681) plus scattered pairwise checks stand in; the declared list is not their source. |
| `required_temporal_order` | :272 | Not read. Ordering checks are hardcoded. |
| `required_contract_reference_count: 6` / `required_skill_reference_count: 6` | :473–474 | Not read. (Both happen to hold — verified 6 and 6.) |

### F-2 — the contract's self-declared enforcement surface is bound by a subset assertion, so this round's five controls are unbound

**Severity: rework.** `validation_bindings.durable_test_functions` (:572–597) declares 25 functions. The binding is asserted as `bound_names <= set(globals())` (test:2107) — subset only. Measured: **35 test functions defined, 26 declared (25 durable + 1 task-local), 9 undeclared:**

```
test_review_provenance_is_required_on_every_review_record_type
test_review_provenance_accepts_any_contract_allowed_session_family_and_agent_operator
test_review_operator_outside_the_contract_operator_model_is_rejected
test_review_provenance_records_must_share_one_stable_handoff_id
test_lane_may_not_declare_a_fixture_catalogued_to_a_foreign_lane
test_c2_two_key_evidence_rejects_schema_valid_swapped_lane
test_default_contract_authority_resolves_current_subject_once
test_external_schema_artifact_reuses_current_subject_blob_bytes
test_reference_semantic_compatibility_rejects_forbidden_wording_variations
```

The first five are precisely the controls that close F-1, F-2, N-1 and N-3 this round. Any of them can be deleted with no contract-level signal. This is inconsistent with the precedent set in the same file: the previous round's remediation controls were promoted to durable (`test_m1_distinct_actor_uuid_and_asserted_i2_fail_without_fresh_task_provenance`, `test_m2_coordinated_stale_reference_pin_fails_current_snapshot_revalidation`, :596–597). The remaining four undeclared functions came from the #169/#170 corrections and were likewise never promoted, so the drift predates this PR — but `contract_revision` was bumped to 5 without closing it.

A subset assertion on a self-declared enforcement surface accepts silent shrinkage of that surface, which is the same failure shape as F-1: declared, not bound.

### Note, not a finding

**O-1 — PR #171's merged bytes were not CodeRabbit-reviewed.** CodeRabbit submitted its only review on #171 at `2026-07-27T23:06:23Z` against head `98c162a7`. Commit `0d4b11e3` ("address PR #171 nitpicks on the operator model") was pushed at `23:27:55Z`; the PR merged at `00:57:39Z` with no second review. The nitpick commit is the one that changed `minItems`/`maxItems` on the operator allowlists and moved the validator's derivation off the agent allowlist — the substance of scope item 6.

Precondition 3 as written ("CodeRabbit concluded on both PRs before they merged") is satisfied, so this review did not stop. Recording it because the precondition is an event-ordering test over a commit-level property: once a review exists on a PR, later commits inherit its appearance of coverage. PR #172 by contrast shows the full cycle before merge. I reviewed the merged bytes directly and found no defect attributable to `0d4b11e3`; the finding is about the gate's phrasing, not about those bytes. Suggested restatement: the SHA CodeRabbit reviewed must equal the PR head SHA at merge.

Per the handoff's instruction, no CodeRabbit run was triggered, polled, or waited on.

## Statements required by the packet

- **No file in the review worktree was edited.** `git status --porcelain` was empty at the end of the review; `test_upstream_contract_and_schema_subjects_resist_stale_foreign_and_coordinated_replacement` passed, which is only possible on a clean tree.
- **No WP6 lifecycle gate was advanced.** Gate A / A7 was not closed, WP6.4 was not dispatched, KAN-56 readiness was not reassessed, no Jira issue was transitioned or commented, no `assurance_pack` id-kind or object was registered, `.research-system/packs/tdl-private-assurance.yaml` was not created, and no provider, API, OAuth, or session-credential work was performed.
- **No acceptance was manufactured.** PR merges, CodeRabbit completion, the 36 passing tests, and Jira status were treated as evidence only.
- The only file written by this task is this handback, in the main working directory, uncommitted.

## Disposition

`rework_required`. Stopping here. Both findings are of one kind — a clause declared at class level whose enforcement is written at instance level, with nothing binding the two — which is the same generalising pattern flagged for F-1 and F-2 in the previous round. Neither finding is a defect in what the reviewed bytes currently do: the 69-row closure, the twelve reference pins, the three-record provenance check, the handoff binding, and the operator model are all correct and non-vacuously controlled as of `034fb494`. What is missing is the mechanism that keeps them correct.

The review worktree is left in place for inspection at:
`C:\Users\steph\AppData\Local\Temp\claude\C--Users-steph-TDL\82d3cece-e081-406c-a10c-f2c806567862\scratchpad\wt-review`

## Sensitive information

None. No credentials, OAuth material, provider session data, tokens, private research data, or account details appear in this handback.
