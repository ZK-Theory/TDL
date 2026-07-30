# WP6.3 — assurance requirement draft, lane scope, and acceptance request

**Created:** 2026-07-29
**For:** Stephen (owner decision) — raised by the session executing handoff 29 step 3
**Branch:** `pipe/wp6-3-tdl-private-pack`
**Responds to:** handoff 29, Decision 3 step 2 and Decision 4 "Consequence for lane scope"

This is the stop handoff 29 sequences. Decision 4 forbids the executing session
from setting lane scope, the risk floor, or any `not_applicable` rationale on its
own authority, and forbids writing the acceptance statement. Everything below the
"Requires your decision" heading is a draft awaiting your ruling.

## Decision 5's five preconditions — verified against the tree

Decision 5 says to verify these against `main`, not against the paragraph. Done,
after merging `origin/main` at `8b9c583` into this branch.

| # | Precondition | Status |
|---|---|---|
| 1 | PR #194 merged | Yes — `8b9c583`, 2026-07-29T21:42:07Z |
| 2 | `_RECORD_ENVELOPE` covers the catalogue, each entry matching that record's own schema | Yes — 12 classes, `pack_loader.py:69`, bound by `test_external_record_envelope_and_resolver.py` |
| 3 | Lifecycle read from each record's own state field; no generic `lifecycle_state` | Yes — no `lifecycle_state` remains in `pack_loader.py` |
| 4 | Authority-root binding enforced at the resolution channel; foreign root refused | Yes — `resolver.py:104`, root read from the store's own verified manifest, not the caller |
| 5 | Staleness resolves the pinned relationship record; rejects lapsed window or sub-floor grade | Yes — `pack_loader.py:421-460` |

Merge validation: 95 passed across the three WP6.3 modules; the commit gate ran
clean across 103 contracts.

**Step 3 is unblocked on implementation.** It is now blocked only on the two
things below, both of which are yours.

## What is mechanically derived, and needs no decision

Read off the accepted contract; stated here so you can check the projection, not
so you have to choose it.

**Lane closure is complete and every governing reference resolves.** Six lanes,
69 required obligations, 12 exact reference rows — and every one of the 12 is
used by at least one lane, with no lane naming a reference the contract does not
carry. Nothing is dangling in either direction.

| Lane | Obligations | Governing references |
|---|---|---|
| `topology` | 11 | w2-exact-diagonal-bound, null-operation-changes-ph-input, validate-topology, research-assurance-triage, paper-claim-trace |
| `stochastic_null` | 11 | null-operation-changes-ph-input, markov-order-provenance, monte-carlo-permutation-p-value, statistical-design-audit, validate-topology, research-assurance-triage |
| `statistical_panel` | 12 | monte-carlo-permutation-p-value, stage1-output-json-validation, statistical-design-audit, research-assurance-triage, paper-claim-trace |
| `representation` | 10 | frozen-loadings-transform-only, representation-freeze-audit, research-assurance-triage |
| `output_provenance` | 11 | stage1-output-json-validation, result-provenance-review, research-assurance-triage, paper-claim-trace |
| `paper_claim` | 14 | paper-claim-trace, result-provenance-review, research-assurance-triage |

`governing_ref_hashes` per lane are the `canonical_sha256` values of those rows.
`failure_consequence` is `blocked_no_cross_lane_compensation` for all six —
`cross_lane_compensation: prohibited` on every lane. `proof_obligation_ids` are
the obligation ids listed above.

Also fixed by Decision 4 and not re-opened here: `requested_risk` R3,
`w5_epistemic_risk_floor` R3, `action_semantic_risk` R3,
`requirement_relationship_grade` I2, `task_id`
`tsk_019faddf-5d6c-7629-bc3b-b20112ad041d` at revision 1,
`assurance_requirement_id` `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` at
revision 1.

## Requires your decision

### D-1. Lane scope — the recommendation is all six `required`, zero `not_applicable`

Decision 4 says not to treat lane scope as a mechanical projection, so this is a
recommendation with its reasoning exposed, not a fait accompli.

Every one of the six lanes carries required obligations, `six_lane_closure` names
all six, and `cross_lane_compensation` is `prohibited` on each. No lane in the
contract carries a `disposition` field at all, and no obligation declares one —
so the contract offers no `not_applicable` anywhere, and marking a lane
`not_applicable` would be adding a disposition the accepted contract does not
contain rather than reading one off it.

**Recommendation: all six `required`. No `not_applicable` rationale is needed,
because there is no `not_applicable` lane.**

The reason this still needs your signature rather than my inference: the
`AssuranceRequirement` model admits `not_applicable`, so "none apply" is a
substantive claim about the pack's scope, not an absence of one.

### D-2. Reviewer capabilities per lane — drafted, not derivable

`LaneRequirement.reviewer_capabilities` has no source in the contract. Every
obligation's `reviewer_capabilities` is empty, so this cannot be projected and
must be authored. Draft, for your amendment:

| Lane | Drafted reviewer capabilities |
|---|---|
| `topology` | persistent homology construction and filtration review; Wasserstein/landscape metric validity; embedding-before-PH discipline |
| `stochastic_null` | null-model construction review; Markov-order provenance; Monte-Carlo permutation p-value validity |
| `statistical_panel` | panel/longitudinal inference; multiple-comparison control; Stage-1 output schema conformance |
| `representation` | representation-freeze audit; loadings/transform separation |
| `output_provenance` | result-artifact provenance tracing; output schema validation; date-suffixed result discipline |
| `paper_claim` | claim-to-result traceability; publishable-claim scope review |

These are drafted from each lane's governing references, which is the only
grounding available. Treat them as a starting point.

### D-3. The acceptance statement — yours to write

Handoff 29 Decision 3 step 2 forbids me from writing it. What you would be
accepting, stated so you can decide whether to:

> The assurance requirement `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` at
> revision 1, governing the `TDL_private` assurance pack across all six research
> assurance lanes and their 69 obligations, at requested risk R3 with a W5
> epistemic risk floor of R3, action-semantic risk R3, and a required
> requirement-relationship independence grade of I2.

The record follows the wp6-1 shape
(`.research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml`) and
carries `ard_019fa9de-c8a4-7978-90b1-8c73e8f1e5ed`.

## A blocker Decision 5 does not fully retire

Decision 5 establishes that the remaining record identities are allocated *by
writing records into the external control store*, and that the store now has a
working resolver. That is true. But two things follow that the sequence in
handoff 29 does not address, and I have not acted on either.

**First, the requirement itself cannot validate yet.**
`AssuranceRequirement` requires five identities that are still unallocated:
`owner_actor_id`, `author_actor_id`, `scope_reviewer_actor_id`,
`accepting_actor_id`, and `prospective_producer_profile_id`. Three of them are
constrained by `required_distinct_pairs` to differ from the producer. Until they
exist as control-store records, the requirement can be drafted but not made
valid.

**Second, and more substantially: R3 acceptance needs a real authority grant.**
`validate_requirement` at R3 calls
`authority_policy.permits(accepting_actor_id, "accept_r3_assurance_requirement")`,
and the production path is `LedgerBackedAuthorityPolicy`, which resolves the
answer from replayed authority grants in the control store — actor, allowed
command, risk ceiling, validity window. So the acceptance is not complete when
you write the statement. It is complete when a grant authorising your actor to
take `accept_r3_assurance_requirement` over this subject exists in the store and
replays cleanly.

That is a good property, not an obstacle — it is exactly what stops the
acceptance being a sentence in a YAML file. But it means step 3 has a fourth
stage handoff 29 does not list: **the grant has to be issued before the
acceptance record can be validated**, and issuing it is a W1/owner action, not a
producer action.

**I have written nothing into the control store.** Writing the multi-party
independence records would mean this session authoring both sides of every
separation claim the pack asserts — the failure Decision 5 names explicitly. The
externality of the store makes the records *capable* of being sound; it does not
make them sound when one party writes them all.

## What was done on the branch

- Merged `origin/main` (`8b9c583`) — PRs #184, #190, #194 — into
  `pipe/wp6-3-tdl-private-pack`, resolving one conflict in
  `test_tdl_private_pack_candidate.py` in favour of the W1-allocated identities
  over main's placeholder constants.
- Verified Decision 5's five preconditions against the merged tree.
- Derived the lane projection above from the accepted contract bytes.

Not done, deliberately: no identity minted, no control-store record written, no
acceptance statement authored, no lane scope set, no `not_applicable` rationale
chosen, no self-review, Gate A A7 untouched.

## Note on `uv run` in linked worktrees

The commit gate's gate 3 shells out to `uv run pytest`, which triggers a `petls`
rebuild that fails on a missing Boost. The pre-commit hook itself carefully
resolves the main checkout's interpreter for gates 0 and 2 and then gate 3
discards it. Worked around for this commit with
`UV_PROJECT_ENVIRONMENT` + `UV_NO_SYNC` pointing at the main venv — the gate ran
in full, nothing was bypassed. PR #195 (demote `petls` to optional) is the real
fix; the gate-3 inconsistency is worth closing separately so the workaround is
not needed per-session.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
