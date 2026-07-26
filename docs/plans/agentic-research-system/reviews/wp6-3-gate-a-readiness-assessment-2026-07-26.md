# WP6.3 Gate A readiness assessment

**Assessment date:** 2026-07-26

**Jira scope:** KAN-56

**Assessment subject:** `origin/main` at
`3be791fbf28c50f61347d8acd326dc7a39e5e208`

**Verdict:** `blocked_not_ready_for_wp6_3_implementation`

**Gate consequence:** Gate A A7 remains open

## 1. Authority and scope

The accepted P-042/06g amendment makes WP6.3 the next first-release preparation
package and permits this separate readiness assessment. It does not itself
authorize WP6.3 implementation. This assessment therefore verifies the current
upstream contract, exact references, acceptance state, and required registry
surface. It does not create the future `TDL_private` pack, implement its semantic
validator, make a provider or model call, handle OAuth or credentials, run
research, or make a Gate 6 decision.

The historical master plan defines A7 as the absence of an accepted TDA/panel
assurance pack. A7 closes only after the WP6.3 pack is accepted with
distinct-authority review. The absence of the future pack is therefore expected
at this readiness stage; it is not permission to bypass the upstream contract
gate.

## 2. Readiness verdict

WP6.3 pack implementation is **not ready to dispatch**. The merged upstream
contract is useful design input, but it remains a pending candidate and does not
bind the current authority surface:

| Readiness condition | Current evidence | Result |
|---|---|---|
| P-042/06g governing-planning amendment accepted | External owner-acceptance record permits KAN-56 | Pass |
| Upstream WP6.3 contract accepted for implementation | Contract says `pending_independent_re_review`; fresh reviewer and owner decisions are pending | Blocked |
| Exact governing references match current base | All six contract blobs match; all six skill blobs differ from `HEAD` | Blocked |
| Every required contract reference is acceptance-eligible | Two exact references remain `pending: true` and pack-ineligible | Blocked |
| `assurance_pack` identity kind is available | `.research-system/config/id-kind-registry.yaml` has no `assurance_pack` kind | Blocked |
| Future pack already exists | `.research-system/packs/tdl-private-assurance.yaml` is absent, as the contract requires before acceptance | Expected |
| Gate A A7 closed | No accepted `TDL_private` pack exists | No |

PR #123 merged the contract candidate at head
`4fa8a70bf1b061e5ddc83a7a1af202350536e976` through merge commit
`9f42655d3e23a8f4bb3753f67be427093886c4d9`. Merge is repository history,
not the missing independent-review and owner-acceptance evidence. The latest
durable independent report reviewed the earlier subject
`1550a57c389da00b7c25299e579d27e4916e4383`, returned
`rework_required`, and required a fresh R4 review. No later R4 acceptance record
or exact-subject owner-acceptance record is present.

## 3. Exact-reference audit

The contract freezes 12 required references. Mechanical comparison with
`HEAD:<repository_path>` produced:

| Reference class | Match count | Current disposition |
|---|---:|---|
| Contract references | 6/6 | Exact blobs still match |
| Skill references | 0/6 | Every pinned blob is stale |

The stale skill identities are:

| Reference | Contract pin | Current `HEAD` blob |
|---|---|---|
| `skill/validate-topology` | `fb1d000f96b31a69f9f4c0adc53e0115f89e6d18` | `487d883f1df718b1d61139434dfce70ef5fbe05d` |
| `skill/statistical-design-audit` | `273d85d134cd10400237624ffd65c48cd9edfb02` | `950ce28f1bb1cedd16c18ea4d77e782d24aafed7` |
| `skill/representation-freeze-audit` | `a15eebe6d3367bbae95566867c45e29668e0ccaa` | `efe61fd9a0b77993aa2edb1eaa59bdb1bcaeff4d` |
| `skill/result-provenance-review` | `91130d3d1e3c145ca3b2b63cfaab987d39f3b589` | `9c82784470c5b867a8c06c6ec0c42b6ef0c5a328` |
| `skill/paper-claim-trace` | `63be5441a82dc2b82b820597e7791fb5fbf43d90` | `99f68cd42649f5845d1c8fb42a601ee8ef4fd50d` |
| `skill/research-assurance-triage` | `b16c683f02684db8144b6f1fc5cefa3768b220a5` | `16895a663d7705ad19eeebf7c19a516d5ad58657` |

The two pack-ineligible contract references are:

- `contract/topology-invariants/null-operation-changes-ph-input`
- `contract/stochastic-tests/markov-order-provenance`

Both referenced files still declare `pending: true`. The WP6.3 contract itself
states that these rows block owner acceptance and require a superseding upstream
contract revision.

## 4. Validation evidence

The complete focused module did not produce a result within the bounded
64-second command window, so it is not reported as a suite pass or failure. A
three-test slice covering the readiness-relevant contract state and reference
relations completed in 14 seconds:

```text
1 failed, 2 passed
```

The failing test was
`test_upstream_contract_is_strict_pending_and_identity_separated`; it stopped at
the first stale `validate-topology` blob. The exact-reference-set and
lane-reference-relation tests passed. A separate direct 12-row Git-object audit
then established the complete 6/6 contract and 0/6 skill result above.

Command:

```powershell
python -m pytest -q `
  tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py::test_upstream_contract_is_strict_pending_and_identity_separated `
  tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py::test_exact_reference_set_rejects_missing_extra_duplicate_alias_swap_and_foreign_rows `
  tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py::test_lane_reference_relations_reject_dangling_swapped_and_pending_rows `
  -o addopts='' -p no:cacheprovider -p no:cov
```

## 5. Required prerequisite sequence

No WP6.3 pack implementation brief is issued from this assessment. Readiness
requires this ordered closure:

1. Resolve and independently accept the two pending scientific contract
   references under their own upstream authority. WP6.3 must consume their
   accepted versions; its producer must not invent or self-approve them.
2. Produce a bounded superseding WP6.3 upstream contract candidate that binds
   the then-current six skill versions and the accepted six contract versions,
   and resolves the missing `assurance_pack` registry authority without creating
   the future pack.
3. Run the complete focused contract suite and required repository contract
   gates at the exact candidate head.
4. Obtain a fresh, context-independent review of the exact final contract and
   schema subject, followed by Stephen's explicit exact-subject acceptance.
5. Re-run KAN-56 readiness against the accepted identities. Only a passing
   assessment may issue a vertical WP6.3 pack implementation brief.

Each prerequisite preserves the owner-operated-session boundary: no ARS routing
to Claude or Codex, no direct provider API, no OAuth or credential handling, and
no model-generated receipt requirement.

## 6. Hard stops

- Do not create `.research-system/packs/tdl-private-assurance.yaml`.
- Do not materialize an `assurance_pack` object before its registry authority is
  accepted.
- Do not treat PR #123's merge as independent review or owner acceptance.
- Do not update stale pins without reviewing the changed skill content.
- Do not dispatch WP6.4 or claim Gate A/Gate 6 readiness.
- Do not execute research, produce assurance results, or promote paper claims.
