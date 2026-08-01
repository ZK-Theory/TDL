# WP6.4 owner-binding evidence inventory - 2026-08-01

## Record identity

| Field | Value |
|---|---|
| Disposition | `owner_binding_not_materialized` |
| Review mode | Independent evidence inventory; read-only except for this record |
| Repository CWD | `C:\Users\steph\.codex\worktrees\6f50\TDL` |
| Management branch | `codex/wp6-gate6-completion` |
| Inventory base | `6684ca517866174204a61eb89d85251d12f521ed` |
| Rejected implementation subject examined | `f18ece7c0bd181e2e8ca07c61d57eb868b45d1db` |
| Jira evidence | KAN-57 comments `10422` and `10424`; KAN-57 remains In Progress |
| Active bounded correction | task `019fbe40-3022-70e2-b734-8c2b688b11b6` |

This is an evidence inventory. It is not an owner approval request, an
implementation acceptance, A8 evidence, a Gate 6 closure, or dispatch
authority.

## Conclusion

No single tracked, materialized, owner-approved WP6.4 foundation binding exists
at the inventory base. The only tracked foundation configuration is a null
template. The repository contains schemas, runtime constructors and validators,
test-created examples, and a historical Gate 5 acceptance record, but none is a
current operational WP6.4 binding.

The historical Gate 5 record must not be erased or mischaracterized. It records
exact values that Stephen accepted for that Gate 5 initialization, including a
project identifier, control-root path, schema-root path, store identity, code-root
topology, and then-observed ledger events. It does **not** supply a materialized
current WP6.4 foundation:

1. the corresponding manifest instances are not tracked;
2. the recorded control root and schema root are absent at this review;
3. its ledger tail is a past observation, not an approved expected current tail;
4. it contains no concrete WP6.4 endpoint binding or foundation digest; and
5. no owner decision extends those historical values into one current WP6.4
   bundle.

Accordingly, historical values cannot be copied, reconstructed, or combined
with caller, restored-manifest, runtime-generated, test, or invented values to
materialize the foundation.

## Evidence-class boundary

| Evidence class | Exact evidence | Authority consequence |
|---|---|---|
| Null template | `.research-system/config/foundation.yaml:1-7` names template alias `ars-foundation-p0`, with `project_id: null` and `control_root: null`. | Declares required shape/defaults; supplies no operational identity. |
| Scheme or algorithm selector | `.research-system/config/foundation.yaml:6-7` contains `endpoint_scheme: local-cli` and `canonical_hash: sha256`. | `local-cli` selects a transport class and `sha256` selects an algorithm. Neither is a concrete endpoint nor a digest value. |
| Runtime/store initialization | `research_system/store/identity.py:63-83` accepts project/control/code roots, generates `store_identity` with `secrets.token_hex(32)`, sets the scheme, and computes a manifest self-hash. | These are caller-supplied or runtime-derived store values, not independent owner approval. |
| Runtime observation | `research_system/store/ledger.py:258-272` derives the current tail from events; exact subject `f18ece7...:research_system/operations/backups.py:305-313,627-630` captures and compares live ledger tails. | Observation and verification do not create an owner-approved expected tail. |
| Schemas/contracts | Tracked schemas include `.research-system/schemas/core/authority-bootstrap-input.schema.json`, `authority-bootstrap-manifest.schema.json`, and `store-identity-1.1.schema.json`. | They prove document shape only. No tracked instance was found. |
| Tests/examples | Exact subject `f18ece7...:tests/research_system/integration/test_external_assurance_record_cli.py:114-124` writes a temporary foundation from the test case's receipt/code root/schema root. | Synthetic values prove mechanics and negative controls only; they are not production authority. |
| Historical owner-approved evidence | `docs/plans/agentic-research-system/reviews/adversarial-gate5-foundation-review-reconciliation-2026-07-16.md:32-63,65-119` records the accepted Gate 5 bootstrap and its then-current runtime topology/state. | Durable provenance for Gate 5 only. It is not a current materialized WP6.4 binding and cannot silently be promoted into one. |
| Current owner-approved WP6.4 values | No complete tracked bundle or owner decision was found. | Absent. Operational materialization is prohibited pending the exact bundle and live external-store evidence described below. |

## Required-field inventory

| Required binding field | Repository/runtime evidence | Inventory result |
|---|---|---|
| `project_id` | The canonical template is null (`foundation.yaml:3`). P-020 specifies one project-wide store architecture (`03-decisions-and-open-questions.md:254-260`) but no identifier. The Gate 5 reconciliation records an historically approved project at lines 32-39; the candidate test instead derives a temporary value from its case at `f18ece7...:test_external_assurance_record_cli.py:114-124`. | No value is bound in a current owner-approved WP6.4 foundation. The historical Gate 5 identifier is provenance, not authority to rematerialize it. |
| Dedicated external `control_root` canonical path/URI | The template is null and marks the field required (`foundation.yaml:4-5`). P-020 requires a dedicated root outside task-worktree branches (`03-decisions-and-open-questions.md:259-260`). Runtime initialization accepts a path (`identity.py:63-80`). The Gate 5 record names `C:\Users\steph\TDL-ARS-Gate5-Control` at lines 59-63, but the exact path returned `False` to `Test-Path` on 2026-08-01. | No current live path/URI is bound by a WP6.4 owner bundle. |
| Store identity | The template has no store-identity field. The current initializer generates it at `identity.py:74-83`. The Gate 5 record reports a historical persisted identity and hashes at lines 101-106, but no tracked `store-identity.json` exists and its recorded external root is absent. | No current owner-bound store identity is materialized. Runtime generation and a historical review value are inadmissible substitutes. |
| Concrete endpoint binding | `foundation.yaml:6` supplies only the `local-cli` scheme. Exact subject `f18ece7...:research_system/operations/backups.py:688-696` reads and checks a runtime endpoint-ownership document containing target root, scheme, actor, grant, and observation time. No tracked endpoint-ownership instance was found. | Concrete canonical endpoint binding is absent. A scheme selector or runtime file supplied to a command is insufficient. |
| Expected canonical tail position/hash | Empty-ledger and non-empty tail values are computed by `EventLedger.snapshot()` (`ledger.py:258-272`). Exact subject `f18ece7...:backups.py:305-313` reads source/target live tails and lines 627-630 compare a receipt to a current snapshot. The Gate 5 events at reconciliation lines 110-119 are historical observations only. | No owner-approved expected current tail pair is materialized. In particular, `(0, "0" * 64)` is runtime empty-ledger semantics, not owner approval. |
| Exact code roots | The template has no `code_roots`. The rejected subject's `ApprovedProjectBinding` accepts them from a supplied file (`f18ece7...:research_system/config.py:20-65`); the store initializer accepts and persists supplied roots (`identity.py:63-83`). The Gate 5 record lists a historical 30-root runtime topology at lines 65-99, including transient worktrees. | No exact current list is bound in a non-template WP6.4 configuration. Historical topology, caller input, restored manifests, and test roots cannot establish current authority. |
| Exact schema root | The template has no `schema_root`. The rejected binding loads one from a supplied file (`f18ece7...:config.py:20-65`). The Gate 5 record names `C:\Users\steph\.codex\worktrees\4b98\TDL\.research-system\schemas` at lines 59-63; that exact path returned `False` to `Test-Path` on 2026-08-01. | No available current schema root is bound by a WP6.4 owner bundle. |
| Foundation digest | `foundation.yaml:7` names only the `sha256` algorithm. `identity.py:23-25,83` computes the store manifest's self-integrity hash, while the Gate 5 reconciliation lines 32-53 and 101-106 records hashes of other specific artifacts. A tracked search found no `foundation_digest` or `foundation-digest` field. | The digest of the complete owner-approved WP6.4 foundation is absent. Algorithm selectors, bootstrap hashes, and self-hashes are not that digest. |

## Tracked-instance inventory

`git ls-files .research-system/config` returned exactly:

- `.research-system/config/assurance-pack-object-allocations.yaml`
- `.research-system/config/assurance-producer-and-requirement-allocations.yaml`
- `.research-system/config/foundation.yaml`
- `.research-system/config/id-kind-registry.yaml`

Targeted tracked-path searches found schemas for store identity and authority
bootstrap, but found none of the following instances:

- `store-identity.json`;
- `authority-bootstrap.json` or an authority-bootstrap YAML instance;
- an endpoint-ownership instance;
- a non-template foundation/binding configuration; or
- a `foundation_digest` / `foundation-digest` field.

The exact historical Gate 5 paths were also checked read-only. Both
`C:\Users\steph\TDL-ARS-Gate5-Control` and
`C:\Users\steph\.codex\worktrees\4b98\TDL\.research-system\schemas` were
absent. This path check is deliberately bounded to the paths named by the
durable accepted record; it is not a claim about every possible local or remote
filesystem location.

## Decision and Jira reconciliation

- P-020 authorizes the single-writer/dedicated-external-ledger architecture and
  the separation of tracked definitions from dynamic canonical state
  (`03-decisions-and-open-questions.md:254-260`). It does not choose the
  concrete WP6.4 values in the inventory table.
- P-042 authorizes an operator-mediated external-session workflow and prohibits
  ARS provider invocation or credential handling
  (`03-decisions-and-open-questions.md:731-757`). It does not choose a project,
  store, endpoint, tail, root set, or foundation digest.
- KAN-57 comment `10422` records the `f18ece7...` `rework_required` verdict and
  directs active task `019fbe40-3022-70e2-b734-8c2b688b11b6` to use durable
  owner-approved identities, never caller/restored/invented values.
- KAN-57 comment `10424` records the targeted absence finding and directs the
  active task to finish truthful fail-closed mechanics without fabricating a
  foundation. This inventory narrows that statement by preserving the
  historical Gate 5 values as non-operative provenance rather than claiming
  that no historical exact values exist anywhere.

## Implementation boundary

The active implementation may complete and ship fail-closed mechanics: a
binding loader that refuses null/incomplete authority, deterministic
`config_output` lock/CAS handling, a small durable journal and recovery path,
and their negative controls. Synthetic fixtures may exercise those mechanics.

It must not populate `foundation.yaml`, publish another operational binding, or
select values from source/target manifests, command arguments, test fixtures,
historical paths, or generated identifiers. Operational foundation
materialization remains blocked until both of these are available together:

1. one owner-supplied exact bundle covering every required field in the table,
   sealed by its foundation digest; and
2. a real external store at the approved endpoint with its actual store-identity
   and authority-bootstrap manifests plus an observed canonical tail
   position/hash that matches the approved binding policy.

That later bundle must be recorded as its own owner decision and independently
checked. This inventory neither requests that decision now nor closes any gate.
