# WP6.3 Gate A readiness reassessment

**Created:** 2026-07-28
**Supersedes:** `wp6-3-gate-a-readiness-assessment-2026-07-26.md`
**Ticket:** KAN-56 — "WP6.3: confirm top-level Gate A closure and readiness for WP6.3 implementation"
**Base evaluated:** `origin/main` at `268d597` (PR #175 merge)
**Workflow system:** `standalone` (no `.apm` initialized or used)

## Verdict

**WP6.3 pack implementation is ready to dispatch.** One bounded vertical brief is
authorized. Every readiness condition that was blocked on 2026-07-26 is now
closed and re-resolved mechanically against the current base.

Gate A A7 remains open, and that is the expected state, not a blocker: A7 closes
when an accepted `TDL_private` pack exists, and the pack is the *output* of the
work this assessment authorizes.

## Condition table, re-resolved

| Readiness condition | 2026-07-26 | 2026-07-28 | Evidence |
|---|---|---|---|
| P-042/06g governing-planning amendment accepted | Pass | **Pass** | Unchanged |
| Upstream WP6.3 contract accepted for implementation | Blocked | **Pass** | Fresh independent review returned `accept_exact_subject`; owner accepted the exact contract and schema bytes at `449b0d00` on 2026-07-28 |
| Exact governing references match current base | Blocked (6/6 contract, 0/6 skill) | **Pass** | **12/12** resolve at `origin/main` |
| Every required contract reference is acceptance-eligible | Blocked (2 pending) | **Pass** | `pending: true` removed from both by `f523b1e`; both rows `activation_state: active`; contract's declared pending set is empty |
| `assurance_pack` identity kind is available | Blocked | **Pass** | Registry maps `assurance_pack: asp`; object `asp_019fa860-3a4b-7784-839f-60f6277e6ce9` revision 1 allocated (PR #175) |
| Future pack already exists | Expected absent | **Expected absent** | `.research-system/packs/tdl-private-assurance.yaml` absent, as the contract requires pre-acceptance |
| Gate A A7 closed | No | **No — by design** | No accepted `TDL_private` pack exists yet; closing A7 is the brief's deliverable |

## Exact-reference audit

Every row of `required_pack_contract.references.exact_reference_rows` was
resolved with `git rev-parse origin/main:<repository_path>` and compared to its
pinned `git_blob`:

| Reference class | 2026-07-26 | 2026-07-28 |
|---|---|---|
| Contract references | 6/6 | **6/6** |
| Skill references | **0/6** | **6/6** |

No stale reference remains. The six stale skill blobs that blocked the previous
assessment are all current. The contract's own
`current_pending_reference_ids` is `[]`, and the declared contract and skill
reference counts (6 and 6) match what is present.

## The two scientific contract references

The previous assessment required these be "resolved and independently accepted
under their own upstream authority", with the WP6.3 producer barred from
inventing or self-approving them.

Both are now active. `f523b1e "[PIPELINE] P01-A: activate WP6.3 prerequisite
contracts"` (stephendor, 2026-07-26) did not merely clear a flag — it added
binding tests (`tests/trajectory_tda/test_markov_order_provenance.py`,
`tests/.../test_null_operation_invariance.py`), wired enforcement into
`trajectory_tda/scripts/stage1/_battery_core.py` and `run_stage1_battery.py`,
and added the paired output-validation contract.

That acceptance took the form of owner-authored activation plus binding tests,
not a separate external acceptance record of the kind the WP6.3 contract demands
for itself. This was raised as an open owner question and has been **decided:
activation plus binding tests is sufficient for these two; no separate record
will be produced** (owner decision, 2026-07-28).

The reasoning, since the asymmetry with WP6.3's own standard is real and a future
reader will ask about it. Three things a separate record could buy:

1. **Drift detection — already provided.** WP6.3 pins both references by
   `git_blob` *and* `canonical_sha256` with `pack_acceptance_eligible: true`.
   Editing either file fails the 12/12 reference resolution and
   `test_exact_reference_set_rejects_missing_extra_duplicate_alias_swap_and_foreign_rows`.
   A record adds no protection the pins do not already give.
2. **Independent review of the scientific claim — already done, recorded
   elsewhere.** This is the one with real force: tests prove a contract is
   *enforced*, never that it is *correct*. But both claims restate mandates
   already owner-locked in `CONVENTIONS.md` — Markov order k at line 246, and
   the shuffle-before-embedding rule at lines 406–421 with its full derivation
   (shuffling already-embedded rows permutes a set the diagram is invariant to,
   so the null collapses). The contracts encode a decision already made and
   reasoned; they do not introduce one.
3. **Author/acceptor separation — absent, and empty here.** `f523b1e` is one
   commit doing both, which WP6.3 forbids itself. That rule exists to stop a
   *producer* self-approving its own dependency. The acceptor here is the owner,
   the terminal authority for these contracts, so the record would be the owner
   attesting to the owner.

**The limit of this decision.** Activation plus binding tests is sufficient
*only* where the contract restates an already-locked mandate. A future scientific
contract encoding a methodological claim not already in `CONVENTIONS.md` would
let an unreviewed research decision enter the governed set with a green suite as
cover. That case requires the separate record. Locked in `CONVENTIONS.md`.

## Validation evidence

Run at the merged head, in a worktree on `origin/main` content:

```
C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest \
  tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py \
  tests/research_system/contracts/test_assurance_pack_object_allocation.py \
  -o "addopts=" -p no:cacheprovider -p no:cov -q
```

**`45 passed in 95.89s`** — 38 from the WP6.3 contract module, 7 from the
allocation bindings.

This is a materially stronger evidence base than the previous assessment, which
could only report a three-test slice (`1 failed, 2 passed`) because the complete
module did not finish inside its 64-second window.

**Suite caveat, stated plainly.** `tests/research_system/unit` and
`tests/research_system/integration` are red on this base. Those failures are
pre-existing and unrelated: a detached worktree at `449b0d00` produces
byte-identical output. Three separate defects are documented in
`../handoffs/26-research-system-suite-red-briefing.md`, one of which is a WP6.1
currency gap (86 generated event schemas require `command_schema_*` fields no
production code emits). None of them touch the WP6.3 contract surface, and the
contract suite is green — but "the repository suite passes" is not true of this
base and should not be claimed.

## Prerequisite sequence — closure check

Against the five prerequisites the 2026-07-26 assessment set:

1. Resolve and independently accept the two pending scientific contract
   references — **done** (`f523b1e`, with the caveat recorded above).
2. Produce a bounded superseding WP6.3 contract candidate binding the
   then-current six skill versions and accepted six contract versions, resolving
   the missing `assurance_pack` registry authority without creating the pack —
   **done** (PRs #170–#173 for the contract, #175 for the registry authority;
   the pack is still absent, correctly).
3. Run the complete focused contract suite and required repository contract
   gates at the exact candidate head — **done** (45 passed; the pre-commit
   contract framework passed all gates across 103 contracts).
4. Fresh context-independent review of the exact contract and schema subject,
   then explicit owner exact-subject acceptance — **done** (2026-07-28).
5. Re-run KAN-56 readiness against the accepted identities — **this document**.

## What this authorizes, and what it does not

**Authorizes:** one bounded vertical WP6.3 pack implementation brief. The
producer must be distinct from the contract author, must carry the exact
pre-allocated `assurance_pack_id`, and must not self-attest review or
acceptance.

**Does not authorize:** WP6.4 dispatch, Gate A A7 closure, Gate 6 movement, or
any edit to the owner-accepted contract and schema bytes at `449b0d00`.

Two items carry forward into the brief from the packet-25 review handback:

- The comment claiming the schema pins `required_distinct_pairs` to eleven; the
  schema actually sets `minItems: 7` with no upper bound. Decide whether seven
  is the intended floor.
- The unreachable `key_a_status` / `key_b_status` / `forbidden_state_or_claim`
  disjuncts, dead-lettered by the external-record schema rejecting those
  mutations first.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
