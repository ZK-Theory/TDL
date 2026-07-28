# WP6.3 semantic review result — handback to Manager

**Created:** 2026-07-27
**Predecessor packet:** `20-wp6-3-post-pr170-semantic-review-handoff.md`
**Workflow system:** `standalone` (not APM; `.apm` not initialized or used)
**Reviewer authority exercised:** review only — no acceptance, implementation,
Jira transition, provider, migration, pilot, result, or claim authority
**Verdict:** `rework_required`

## 1. Precondition — passed

| Check | Result |
|---|---|
| PR #170 state | `MERGED` 2026-07-27T21:19:49Z |
| Merge commit | `6bfc8dd9dfd919ec67e55dd0ab111f37557bd0d2` |
| `origin/main` after fetch | `6bfc8dd9dfd919ec67e55dd0ab111f37557bd0d2` — equals the merge commit, no drift, no drift accounting needed |
| CodeRabbit | Concluded 2026-07-27T21:17:56Z against head `0d87c12c222c5165017aee3b086f3fc55b53f8fc` ("No actionable comments were generated"), ~2 minutes before merge. `GET /repos/stephendor/TDL/pulls/170/comments` returned 0 inline findings. Merge gate cleared. |
| Review checkout | Fresh worktree detached at `6bfc8dd`: `C:\Users\steph\TDL\.apm\worktrees\wp63-review-170`. The main working directory was not used as a starting state. |

## 2. Exact subject identities (computed at the subject commit)

| Artifact | `git rev-parse HEAD:<path>` | SHA-256 of blob bytes |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `967a0d9532e6871d8487084855a5680972544def` | `e500b448feb964e4c738ef52d74a2683f99157be0b793f04911d5f6ce4675330` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `a80ac7c37541b9ff3ba38fdb4e618970865d7146` | `35907e75adf84cffb45d3b9e929be4d6bcd23e384c6be21fdf378ecb10b2b533` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `a3f5e5d951c823863b58c6299fddc03d20006835` | `0f5560682bf3297b5584788a60eec04da3808bc4de5cd51a2f1e497280db0508` |

The contract identity matches the handoff's cross-check exactly (independently
computed, not assumed). No divergence to report.

## 3. Blocker re-resolution at the subject commit

| # | Blocker as filed | State at `6bfc8dd` |
|---|---|---|
| 1 | Fresh independent review + owner acceptance | OPEN → now answered by this review with `rework_required`. Contract `status: pending_independent_re_review` (contract:5). |
| 2 | 6 skill pins stale | CLOSED. All 12 reference rows resolve to the blob and canonical SHA-256 actually present at the subject commit, including the two PR #170 repins. |
| 3 | Two contract references `pending: true` | CLOSED. `null-operation-changes-ph-input` (contract:447) and `markov-order-provenance` (contract:449) are `activation_state: active`, `pack_acceptance_eligible: true`; `current_pending_reference_ids: []` (contract:467). |
| 4 | `assurance_pack` id-kind absent from registry | Unchanged — `.research-system/config/id-kind-registry.yaml` still carries only `assurance_requirement: asr`. Correctly sequenced after owner acceptance; not a bar to contract acceptance. |

## 4. Verdict and blocking findings

Verdict: **`rework_required`**, on two blocking findings. Both are invisible to
the passing test suite: they are gaps in what the schema *requires* and what the
fixtures *instantiate*, not defects the existing negatives probe.

### F-1 (blocking) — provenance typing was remediated on only one of three review records

*Scope items 1 and 5.*

`review_provenance_binding: typed_operators_distinct_task_and_session_stable_handoff_and_fresh_context`
sits under `external_acceptance_evidence` (contract:240), which governs all
eleven `required_record_types` — including `independent_contract_review` and
`independent_schema_review`.

`operator_provenance` is required on **only** `independentPackReviewRecord`
(schema:699). `independentContractReviewRecord` (schema:520) and
`independentSchemaReviewRecord` (schema:542) require only `reviewer_actor_id`,
`author_actor_id`, `relationship_record_id`, and `minimum_independence_grade` —
exactly the "distinct actor UUID plus asserted I2" configuration that prior
finding M-1 declared insufficient, and that the contract itself declares
insufficient (`role_labels_or_candidate_attestations_are_evidence: false`,
contract:259).

`operator_provenance` appears exactly once in the test fixtures (test:1325) and
has exactly one validation site (test:1753), both on the pack review. The two
records left unremediated are the ones that gate Stephen's acceptance of these
very bytes.

**Pattern:** partial remediation — a finding fixed on the artifact it was raised
against, while structurally identical siblings were left unfixed and the
governing clause stayed written at the level that covers all of them.

### F-2 (blocking) — schema and validator narrow the provenance model to Codex, against provider-neutral P-042/06g

*Scope item 6.*

06g §1 is provider-symmetric ("Stephen uses Claude and Codex…", "the operator
selects the external application/session"); §6 requires ARS to record "the
**operator-selected** session family".

The schema hard-codes `session_family: {"const": "codex_standalone"}` and
`operator_type: {"enum": ["codex_task_agent", "human_owner"]}` (schema:647,
schema:662). The validation logic goes further and requires *both* producer and
reviewer to be `codex_task_agent` (test:1755–1757), rejecting even the
`human_owner` value the schema admits.

Three consequences:

1. An owner-operated Claude review — explicitly authorized by 06g — cannot
   produce a schema-valid record, so the acceptance path is silently
   provider-exclusive.
2. The contract's own binding term (contract:240) is provider-neutral and the
   613-line file mentions Codex nowhere. The narrowing exists only in the schema
   and validator, undocumented and unjustified.
3. Schema and validator disagree with each other on `human_owner`.

**Pattern:** specificity leak — an environment-specific constraint baked into a
schema whose governing contract and accepted amendment are both
provider-neutral, with no test that would notice because every fixture is Codex.

## 5. Non-blocking findings (fix alongside, or record and defer)

- **N-1 (scope 3/7).** The `representation` lane declares fixture
  `apf_degenerate_fallback` (contract:390), but that catalogue row is
  `lane_id: stochastic_null` with
  `target_invariant: invariant.stochastic.degenerate_fallback` (contract:520).
  It is the only fixture cross-listed into a foreign lane without being modelled
  `cross_lane`. The representation obligation it would serve
  (`representation.prohibited_refit_and_fallback`) is governed by a different
  invariant.
- **N-2.** Cross-reference id patterns are prefix-only (`^act_`, `^rel_`,
  `^cau_`, `^crv_`) while the defining records use fully-anchored UUIDv7
  patterns.
- **N-3.** `handoff_id` is schema-required but bound by nothing in the
  validation logic, so 06g §6's "stable handoff identifier **shared by the brief
  and returned evidence**" is presence-checked, not linked.

## 6. Scope items that passed

| # | Scope item | Result |
|---|---|---|
| 1 | External authority resolution | Pass. `self_embedded_contract_hash: prohibited`; `candidate_review_or_acceptance_fields: prohibited`; `candidate_may_supply_record_bodies: false`; `caller_may_supply_record_hash_oracle: false`; `hash_validity_alone_is_sufficient: false`; `observed_side_may_supply_expected_authority: false`. `test_c1_…` (test:3128) asserts by signature inspection that the validator has no `record_store`/`hash_manifest` parameters. (F-1 is a provenance-typing gap within an otherwise sound authority separation.) |
| 2 | Exact-reference currency | Pass. All 12 rows verified independently against `git rev-parse HEAD:<path>` plus SHA-256 of blob bytes — 0 mismatches. `authority_resolution_phases: [load, acceptance, consumption]` (contract:232); `test_m2_…` (test:3251) proves a coordinated stale pin fails current-snapshot revalidation, including mid-flight authority change. |
| 3 | Two-key obligation closure | Pass (see N-1). Computed 69 obligations (11 / 11 / 12 / 10 / 11 / 14), 69 unique `(lane_id, obligation_id)` pairs, no duplicates, no prefix or lane mismatches, no dangling lane references, `allowed_lane_ids` bidirectionally consistent with each lane's governing set. Schema pins `minItems: 69, maxItems: 69` (schema:711). Cross-lane compensation prohibited on every lane. |
| 4 | Lifecycle ordering | Pass. The nine-step `required_sequence` is enforced temporally at test:1842–1857 as a strict chain (authored < both reviews < contract acceptance < requirement acceptance < candidate authored < pack review < owner decision <= as_of), with relationship-window bounds per action. `accepted_state_may_be_inferred_from_candidate: false`; `supersession_is_immutable: true`; `stale_identity_behavior: block_and_require_superseding_revision`. |
| 6 | Semantic compatibility (references) | The six contract and six skill references all resolve to live, active, correctly lane-scoped artifacts. The failure is confined to the provenance model (F-2). |
| 7 | Intended negative cases | Pass. All four PR #169 correction points present and discriminating: per-case `match=` strings rather than bare exception classes; tuple-key lane swap (test:3202) as well as the set-level swap (test:2460); independent Git subject comparison (test:2605) plus a distinct dirty-bytes check; canonical byte reuse (test:2208); prohibited semantic variants via `test_hash_valid_external_record_semantic_mutations_are_rejected`. Fixture catalogue: 52 rows, all unique, every `expected_outcome: blocked`; the three boundary fixtures are consistently declared across `required_executed_boundary_fixture_ids`, `fixture_execution_boundary`, and the schema's `boundaryFixtureExecutionRow` enum, with `upstream_may_claim_downstream_execution: false`. |

## 7. Validation performed

```
"C:/Users/steph/TDL/.venv/Scripts/python.exe" -m pytest -q tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -o addopts='' -p no:cacheprovider -p no:cov
```

Result: `31 passed in 105.21s` — matches the expected result at the PR #170
merge. The primary interpreter was used per the handoff's environment note;
`uv run` was not invoked.

Additionally, read-only Python was run over the contract YAML in the review
worktree to recompute the twelve reference identities, the 69-row two-key
closure and lane-relation consistency, and the fixture-set consistency. No broad
suites were rerun; no evidence already established by PR #169 or PR #170 was
recreated.

## 8. Boundary statement

No file was edited, staged, committed, or pushed during the review; no PR was
opened. No WP6 lifecycle gate was advanced, no Gate A / A7 action taken, no
WP6.4 dispatch, no KAN-56 reassessment. No Jira transition or comment. No
CodeRabbit run triggered, polled, or waited on. No provider, API, OAuth, or
session-credential work. `.research-system/packs/tdl-private-assurance.yaml` was
not created and no `assurance_pack` object or id-kind was registered. PR merge,
CodeRabbit completion, passing tests, and Jira status were not treated as
semantic or owner acceptance.

This document is the sole file authored, at Stephen's explicit request after the
review concluded. It is uncommitted and untracked.

The review worktree at `C:\Users\steph\TDL\.apm\worktrees\wp63-review-170`
remains in place — worktree removal is manual by convention. Sweep it at the
next Manager-session sweep.

## 9. Recommended Manager action

1. **Do not seek owner acceptance of these bytes.** The verdict is
   `rework_required`; step 1 of the handoff's "what happens after this review"
   is not satisfied.
2. **Author one bounded remediation brief** covering F-1 and F-2 together —
   they are both provenance-model defects in the same schema region and splitting
   them risks a second partial remediation of exactly the kind F-1 documents.
   Fold in N-1 to N-3 unless there is a reason to defer.
   - F-1: extend `operator_provenance` (or an equivalent typed-provenance
     `$def`) to `independentContractReviewRecord` and
     `independentSchemaReviewRecord`, with negative tests mirroring
     `test_m1_…` for each — a review record that reuses the author's task or
     session id must fail for each of the three record types, not one.
   - F-2: either make `session_family` and `operator_type` operator-selected and
     provider-neutral per 06g §6 (preferred — it matches the accepted
     amendment), or state the Codex-only restriction explicitly in the contract
     with its rationale and reconcile the validator's rejection of `human_owner`
     with the schema enum that admits it. Add at least one non-Codex provenance
     fixture so the constraint has a watched negative either way.
3. **The remediation lands on a branch, is reviewed by CodeRabbit before merge,
   and then requires a further fresh independent review** bound to the new exact
   contract and schema identities. The identities in §2 will not survive
   remediation; do not carry them forward.
4. **Downstream sequencing is unchanged and still gated** — W1 `assurance_pack`
   id-kind registration, KAN-56 re-run (needs a new issue or a reopen, Stephen's
   call), WP6.3 pack implementation brief, Gate A A7, WP6.1 currency
   re-verification, KAN-57 / WP6.4.

## 10. System observations (for the observation log, not yet written)

Both blocking findings generalize beyond this contract and are worth carrying
into the record:

- **Partial remediation is a distinct failure mode.** A finding raised against
  one artifact was fixed there and nowhere else, while the governing clause
  remained written at the level covering all siblings. Countermeasure: when a
  finding is closed, enumerate every artifact the governing clause covers and
  require the fix or an explicit exemption for each.
- **Specificity leak.** An environment-specific constant (`codex_standalone`)
  was frozen into a schema whose governing contract and accepted amendment are
  both provider-neutral, and no test would ever notice because every fixture
  used that same environment. Countermeasure: a constraint narrower than its
  governing document needs either a stated rationale in the contract or a
  negative fixture from outside the constraint.

## 11. Sensitive information

None. No credentials, OAuth material, provider session data, tokens, private
research data, or account details appear in this handback.
