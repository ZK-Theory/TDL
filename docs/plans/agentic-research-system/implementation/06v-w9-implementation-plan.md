# 06v — W9 implementation plan (Gate 7)

| Field | Value |
|---|---|
| Date | 2026-10-23 (revision 2); revision 1 of 2026-10-22 |
| Status | **Draft, revision 2, `review_pending`.** Revision 1 (`2a3940e2`) was reviewed: REWORK REQUIRED, 0 Blocking, 8 Major, 13 Minor, 6 Info (`reviews/06v-w9-plan-review-2a3940e2-2026-10-23.md`, `b3fe778c`). This revision is reconciled in `reviews/06v-w9-plan-reconciliation-2026-10-23.md`. Next: a narrow re-review, then Stephen's exact-revision acceptance (P-063). |
| Authority to write | P-063 (Gate 7 opening): "authoring, independent adversarial review and Stephen's exact-revision acceptance of the W9 implementation plan", including a proposal for the W9-D10 store |
| Implementation authority | **None.** P-063 does not authorize implementing this plan. Implementation starts only on Stephen's separate decision after the plan is accepted. Each live operation in §7 needs its own decision on top of that. |
| Specification | W9, `design/09-migration-compatibility-and-pilot.md`, draft 0.5, blob `ea3a8e4a`, accepted 2026-10-22 (W9-D1 to W9-D14) |
| Code base read | origin/main `e82f9630`. Every `path:line` below was read at that commit. |
| Jira | KAN-22 (parent). No implementation issues are created until Stephen authorizes implementation. |

All document paths are under `docs/plans/agentic-research-system/` unless they start with a repository root directory
(`research_system/`, `tests/`, `tools/`, `.github/`, `.research-system/`).

## 1. What this plan delivers

This plan delivers the machinery W9 specifies, built in eight work packages (§5), each landing as one reviewed PR:
- the closed `ars://legacy/` schema family;
- the W9 catalogue, its bootstrap contract and its one-time genesis;
- the legacy runtime (commands, routes, reducers, shared-ledger replay, CLI);
- the handle-bound observation reader and its selectors;
- adoption, discharge and citation status;
- the four W9-D5 detectors;
- rollback and recovery;
- the read-only legacy projection;
- the successor-side guards W9's tests need, which sit in the generic command service (§2.7).

It does not open a store, run a genesis, or observe, import, adopt or transition any item. Those are live operations,
sequenced in §7 behind their own owner decisions.

**Measure of done:** the W9 acceptance tests W9-T1 to W9-T23 (W9 §17) all pass against negative controls, and every
obligation in §3 has a disposition.

## 2. Interface map (verified at `e82f9630`)

### 2.1 What W11 already provides, and what W9 copies

| Seam | Fact | Citation |
|---|---|---|
| Accepted-catalogue identity | A frozen `ACCEPTED` mapping holds the commit, tree, catalogue blob, bytes and SHA-256, the bootstrap contract identity and the owner decision. `ROW_IDS` covers OR-001 to OR-041 plus OR-101 to OR-140 (81 rows). The catalogue stream ID is a constant. | `research_system/discovery/accepted_w11.py:16-52` |
| Catalogue bytes | `.research-system/evals/expected/w11-portfolio-discovery-v1.json` (blob `8d588185`) | `git ls-tree` at `e82f9630` |
| W11 schemas | 62 files under `.research-system/schemas/contracts/w11/`, every `$id` `ars://portfolio/...`, frozen to accepted commit `09be63a9` | `tests/research_system/contracts/test_w11_expected_catalogue.py:209-251` |
| Genesis guard | `submit` checks the payload before taking the lock (`runtime.py:192`). `_prepare_genesis` then runs these checks in order: refuses with "W11 genesis already exists" when the store's replayed projection already holds a catalogue (`:2628`); requires the catalogue stream at `expected_stream_version == 0` (`:2630`); requires the payload to equal `ACCEPTED` (`:2632`); re-hashes the catalogue and bootstrap bytes (`:2638-2656`); checks the 81-row set (`:2659-2660`); proves the route registry partitions the accepted catalogue (`:2661`; `routes.py:337-353`). | `research_system/discovery/runtime.py:192,2622-2662` |
| Second-genesis replay guard | The replay reducer refuses a second genesis or a payload mismatch | `research_system/discovery/replay/genesis.py:17-31` |
| Genesis operator entry | `ars discovery spec advance --action bootstrap_genesis` | `research_system/discovery/spec_assay.py:105,196`; `implementation/06s-phase5-runbook.md:211` |
| W11 legacy rows | Not implemented. OR-031, OR-032, OR-033 and OR-122 to OR-139 are `DISCOVERY_EXCLUDED_ROWS`, and OR-030 is deferred. The route registry must partition exactly 59 / 21 / 1. | `research_system/discovery/routes.py:65-68,344-355`; `tests/research_system/unit/test_wp6_6_discovery_activation.py:113-125` |
| W11 not runtime-activated | No `ars://portfolio/` schema ID may appear in `_RUNTIME_BINDINGS`. Discovery validates portfolio content directly through the registry instead. | `tests/research_system/contracts/test_w11_contract_materialization.py:1589-1592`; `runtime.py:2610` |

**Consequence (W9 §5.3 item 4, confirmed).** W11 genesis is one-time **per store**. The guard reads the projection
replayed from the bound store's own ledger (`runtime.py:474-479,2628`). A new store therefore needs its own W11
genesis before any W11-referencing record exists. W9 does not touch W11's route partition, its excluded rows or its
schema tree; under this plan all three stay exactly as accepted.

### 2.2 Command, authority, store, replay and CLI seams

| Seam | Fact | Citation |
|---|---|---|
| Discovery-style command path (the model for W9) | Its own append site: `DiscoveryRuntime._submit_authorized` appends directly, separately from `CommandService.submit`. Touchpoints: a command-type set; a route row; subject kinds in the runtime and in `authority.py`; a family preparer; a transaction contract; a replay reducer. Events with no producer binding fall back to `ars://core/event` 1.0.0. Receipts are scoped. | `research_system/discovery/runtime.py:209-237,363,464-472,551-577,588-613`; `research_system/discovery/commands.py:14-44`; `research_system/authority.py:171-234`; `research_system/discovery/replay/transactions.py:146`; `replay/registry.py:83` |
| One runtime-binding row per command | Every Discovery command has its own `SchemaBinding("ars://core/command", "1.0.0", command_type=…)` row. `command_binding` is keyed by command type. A command with no row is refused at authority resolution and again before append, and cannot be granted ("no active command binding"). Events need no row. | `research_system/schema_registry.py:209-265,1547-1549`; `runtime.py:205-207,578-581`; `research_system/cli.py:1206-1208` |
| Writer lock | Discovery appends under a three-root `CompositeWriterLock`: the control root, the authority root and the operational ledger root | `runtime.py:194-198` |
| **Shared-ledger replay** | Every whole-ledger replay in a store must recognise every event type in it. `rebuild_projection` treats an event as Discovery's only when `is_discovery_projection_event` holds, which is closed over `DISCOVERY_COMMAND_TYPES`. Every other event goes to `apply_event`, which raises "unsupported event type" for any event type it does not know. `shared_event_partition` sends unknown events to `"operational"`, which `replay_discovery` hands to `replay_control_plane`. `DiscoveryRuntime` replays the whole ledger before every Discovery command. `rebuild_projection` lazily calls `replay_discovery` when Discovery events are present. | `research_system/projection/replay.py:1125,1319-1324,1369-1381`; `research_system/discovery/routes.py:301-319`; `research_system/discovery/commands.py:84`; `research_system/discovery/replay/driver.py:66-75,396-400`; `runtime.py:474-483` |
| Generic command path (successor objects) | Schema files under `core/commands` and `core/events`; `_RUNTIME_BINDINGS` rows; the lifecycle triple; service tables; a reducer; a receipt. Example: `CancelTask` → `TaskCancelled`. | `schema_registry.py:764-770,1344-1427`; `research_system/command/lifecycle.py:186`; `research_system/command/service.py:137-139,251-261,287,1552-1619,3829-3860`; `research_system/command/reducers.py:527-535` |
| Store creation | The public procedure is runbook L1 to L7: a durable checkout; an empty origin-authority root; `ars store reserve`; a foundation re-pin PR; `ars store init` with an approved `authority-bootstrap-input`; and the first binding through `ars store repair-binding` with `owner_action: bind-initialized-store`. Control roots must be disjoint from and external to the code roots. | `06s-phase5-runbook.md:189-195`; `research_system/cli.py:239-285`; `research_system/authority.py:1591-1660`; `research_system/store/layout.py:19,56`; `research_system/store/identity.py:767-854` |
| Store identity | `store_identity` is a random 32-byte token written into the manifest at initialization, so it survives a copy or move. It is read through `load_store_manifest`. | `identity.py:824,857` |
| Store binding to code | The binding records `git_head`, `git_tree` and a `schema_catalogue_sha256` over every committed schema-registry input. Later code is bound by `ars store advance-binding`. | `research_system/store/current_binding.py:53-79,201-253`; `cli.py:2232-2234` |
| Scoped grants | `ars authority activate-grant` is owner-only. Each allowed command is pinned to its runtime binding's schema ID, version and SHA-256, and a command with no binding is refused. Subject kinds are a closed enum in the authority schemas. Discovery reuses existing kinds. | `cli.py:1159-1218`; `.research-system/schemas/wp6-3-authority/activate-authority-grant-command-v1.1.0.schema.json`, `scoped-authority-grant-v2.1.0.schema.json`; `runtime.py:209-236` |
| CLI | `_parser()` has 11 groups. A new group needs `groups.add_parser`, handlers, and an entry in `main`'s error set. | `cli.py:2184-2457` |
| Projections | `ars projection rebuild` requires only that the output path sit under `<code_root>/.research-system/projections`. There is no namespace registry. The directory is gitignored. | `cli.py:1507-1547` (check at `:1521-1522`); `research_system/projection/replay.py:1385-1404`; `.gitignore:219-220` |

### 2.3 Protected identities (P-059)

| Pin | Fact | Citation |
|---|---|---|
| Runtime-binding census | Exactly 261 rows, SHA-256 `f359855b…`, over the canonical row format. The same values are in the 06h manifest, which the test reads. | `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py:97-101,139-149,342-357`; `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml` |
| Append-site classification | Every ledger-append site must be classified. Discovery is `discovery_command_producer`. | `test_wp6_1_06h_append_path_closure.py:33-75` (Discovery at `:52-58`) |
| Protected schema trees | Git tree IDs: `core/commands` `8a86a0c4`, `core/events` `058c1d5d` | `tests/research_system/contracts/wp6_2_t2_expectations.py:406-409`; enforced at `wp6_2_t2_authority_validation.py:244-245`, with the pathspec diff at `:252-268` |
| P-059 record | Re-accepted at exact bytes; census went from 218 to 261 | `03-decisions-and-open-questions.md` P-059 |

**Consequence.** Every W9 command needs its own runtime-binding row (§2.2), so **every package that adds a command
changes the census and its digest**. A successor-side guard (§2.7) changes a protected tree only if a core command or
event schema must change. D-4 sets the re-acceptance procedure for both.

### 2.4 Detection and admission tooling

- **Existing workflows:** `ci.yml`, `merge-admission.yml`, `merge-admission-sweep.yml`, `ars-artefact-currency*.yml` and
  `research-system-suite.yml`.
- **Existing tools:** `tools/check_merge_admission.py` (thread finality, platform order, queue, sweep) and
  `tools/check_retired_imperatives.py`.
- **Squash merges:** main is squash-merged one entry at a time through the merge queue
  (`tools/check_merge_admission.py:703-709`). A commit SHA created by the queue cannot be named inside the PR that
  creates it.
- **What does not exist:** there is no first-parent post-merge detector, no `results/` prefix rule, and no ruleset or
  rule-suites read. A grep over `tools/`, `.github/`, `research_system/`, `.githooks/` and `.claude/hooks/` finds
  nothing. The P-049 ruleset appears only in comments (`check_merge_admission.py:705-707`; `.github/CODEOWNERS:11`).
  `.claude/hooks/admin-bypass-guard.sh` allows `gh api` GETs of rulesets and blocks mutations.

### 2.5 Model-family coverage

`r3_family_coverage_insufficient` appears only eval-side:
- `research_system/evals/executors/context_routing.py:210`;
- `tools/ars/materialize_context_routing_fixtures.py:215`;
- the F-031 oracle.

No dispatch path enforces P-029's two-family rule.

### 2.6 Gate 6 store identity (frozen)

The Gate 6 store's identity, from `.research-system/config/foundation.yaml` at M2 `4d867d85`, unchanged on main at
`e82f9630` (P-058):

| Field | Value |
|---|---|
| `store_identity` | `5e3b95a956a8a416accd697f250088b5c8723924eb68544f01064ede6eb18d69` |
| `project_id` | `prj_01978abc-1000-7000-8000-000000001000` |
| `origin_witness_sha256` | `1a7aa957917f20d537fbc99e23e23fc094f60e94906d80e4a2250577d7ffe7c4` |

D-1's foundation re-pin replaces the live foundation. After it merges, the CLI binds the new store through
`ApprovedProjectBinding.load(canonical_foundation_path())` (`cli.py:1513-1518`; `research_system/config.py:534-536`), and
the Gate 6 store is readable only from the M2 checkout. W9's refusal of the Gate 6 store (WP9.2) therefore keys on this
frozen `store_identity`, not on the live foundation.

### 2.7 Successor-side seams (the guards W9's tests need outside the legacy package)

| Test | Owning module and line | Field read | Core schema change? |
|---|---|---|---|
| W9-T8: unadopted family used by a successor Task | CreateTask preparer, `research_system/command/service.py:6019` | `definition.source_import_refs` (`.research-system/schemas/core/commands/create_task.schema.json:264`) | **U-5**: whether those refs can carry a legacy-observation family reference without a schema change |
| W9-T10: successor work writes a legacy path | RegisterArtefact preparer, `service.py:4382`. The Task definition has no output-path field. | `manifest.relative_path` (`.research-system/schemas/core/commands/register_artefact.schema.json:119`) | No. The path field exists. The guard refuses a `relative_path` that is a registered legacy file, or that falls under `results/` outside `results/ars/`. |
| W9-T11: restricted bytes registered as an artefact | RegisterArtefact preparer, `service.py:4382` | `manifest.relative_path`; any `restricted_untracked_file` registration in the store's W9 projection | No |
| W9-T12: family coverage at dispatch | ClaimDispatch preparer in `service.py` | The dispatch record | **U-2**: the exact preparer and whether the coverage record needs a new field |
| W9-T16: thresholds precede the batch | W9 legacy runtime, closed-reference acceptance preparer (WP9.3) | The threshold anchor | No |
| W9-T17, W5 clause: an unadopted family blocks its claims | W5 assurance engine under `research_system/assurance/` (likely `resolver.py`) | The citation-status relation | **U-6**: the exact hook and whether W5's claim inputs need a new field |

Each guard reads the store's W9 projection through the legacy package's read interface, not by importing its
internals. If any of U-2, U-5 or U-6 requires a change to a `core/commands` or `core/events` schema, that is a
protected-tree change under D-4.

### 2.8 Interface-unverified items (dispatch blockers for the named package)

| ID | Unverified | Package | How it is resolved |
|---|---|---|---|
| U-2 | The ClaimDispatch preparer and the family-coverage record's field | WP9.7 | Read the preparer and record `path:line` in the PR before writing code |
| U-3 | Whether the CI token can read ruleset 20822054 and its rule-suites history | WP9.5 | A read-only probe from a workflow run. If the token cannot, the limit goes to Stephen as D-8. It is not a package-level fallback. |
| U-4 | The operator machine's path to the vault (junction behaviour) for the Computational-Log detector; CI cannot see the vault | WP9.5 | Recorded from a dry run on the operator machine |
| U-5 | Whether `source_import_refs` can reference a legacy-observation family without a schema change | WP9.4 | Read the CreateTask preparer and schema; record the answer before writing code |
| U-6 | The W5 hook for "an unadopted family blocks its claims" | WP9.4 | Read `research_system/assurance/`; record `path:line` before writing code |
| U-7 | Whether the shared-replay edits (WP9.2) can be confined to a predicate that `projection/replay.py` and `shared_event_partition` consult before their defaults, leaving the 59/21/1 partition and every W11 pin unchanged | WP9.2 | Read and prototype on a scratch store. If the edit cannot be confined, stop and return Partial (§8). |

## 3. Obligation register

Every forward obligation in W9 and its acceptance trail has a disposition here.

**Sources scanned.**
- W9 §§2–17.
- The W9 acceptance record and its "Carried" list.
- The W9 reconciliation.
- The five G7-B review rounds.
- The G7-A, G7-C and D8c acceptance records.
- P-062 and P-063.

| # | Obligation | Source | Disposition |
|---|---|---|---|
| O-1 | Implementation plan for the W9 family; no W9 operation before it | W9 §2.1 W9-A1; §2.3 | This plan |
| O-2 | Name the store; Stephen decides; never the Gate 6 store | W9 §5.3 item 1; W9-D10; W9-T20 | D-1; §2.6 frozen identity; WP9.2 refusal and W9-T20 |
| O-3 | Separately accepted minimal bootstrap contract; one independently verified genesis transaction | W9 §5.3 item 2 | WP9.1 (contract); WP9.2 (genesis code, including the partition and pre-lock checks); §7 L-3 |
| O-4 | Genesis under an owner grant scoped to the W9 catalogue stream | W9 §5.3 item 3 | WP9.2 (grant scope); §7 L-3 |
| O-5 | W11 genesis first in a new store; confirm the one-time-per-store reading | W9 §5.3 item 4 | Confirmed in §2.1; WP9.2 checks the replayed Discovery projection; §7 L-2 |
| O-6 | P-059 protected-identity re-acceptance for the new commands | W9 §5.3 item 5; W9-D10 | D-4: at every package PR that changes a protected identity |
| O-7 | Exact JSON shapes of the record family | W9 reconciliation | WP9.1 |
| O-8 | Separate W9 catalogue with exact identities, independently reviewed and accepted by Stephen | W9 §5.3 | WP9.1 owner gate |
| O-9 | Post-merge first-parent detector, the `results/` prefix rule and rule-suite reads | W9 §4.4; W9-D5 | WP9.5, reading a committed registration manifest; records keyed by PR |
| O-10 | Ruleset 20822054 bypass list read before each batch | W9 §4.4; W9-D5 | WP9.5; §7 batch checklist; D-8 if U-3 fails |
| O-11 | Vault Computational-Log detector against the baseline export | W9 §4.4, §7.3 | WP9.5; D-5 |
| O-12 | `CONVENTIONS.md` check against `4b143c92`, insertion-only | W9 §4.4, §7.3 | WP9.5 |
| O-13 | Each detector watched to fail before the first registration | W9 §4.4; W9-D5 | WP9.5 controls on a scratch clone or a byte copy, with a fixture registry; §7 L-1, never writing `main` or the vault |
| O-14 | Citation extractor or second derivation for W9-T17 (Info I-c) | W9 acceptance "Carried" | D-3 (both); WP9.4 with m-6's scope |
| O-15 | Dated W6 addendum re-specifying S-016 under P-042 | W9 §12.3; W9-D12b | WP9.0 |
| O-16 | Read-only projection under `.research-system/projections/legacy/`, registered under the W9 family | W9 §7.2; W9-D8b | WP9.6, built on WP9.2's shared replay |
| O-17 | Each item's rollback handle exercised once on a scratch store before its batch | W9 §13.1; P-062 E9 | WP9.6 harness; §7 batch checklist |
| O-18 | Manual-mode attribution: signed commits or recorded pusher identity | W9 §13.1; W9-T23 | WP9.6, with O-35's key registry |
| O-19 | `.apm/bus/` closure inventory | W9 §13.3 item 2 | WP9.3 tool; §7 L-5 |
| O-20 | Light inventories with blocker rows; duplicate anchors block | W9 §5.5; W9-T18, W9-T22 | WP9.3, under the versioned segmentation contract (m-7) |
| O-21 | Shared-writer baselines: the classified legacy-entry list accepted by Stephen; the Git-anchored export | W9 §7.3 items 1, 2 and 6 | D-7 and §7 L-0b, as early as authorized; WP9.3 exporter |
| O-22 | Restricted bytes never enter the store, on every path | W9 §5.4; W9-T11 | WP9.3 reader; WP9.7 RegisterArtefact guard (§2.7) |
| O-23 | Successor compute writes nothing legacy | W9 §10; W9-T10 | WP9.7 RegisterArtefact guard (§2.7) |
| O-24 | Family coverage at dispatch for P-005's R3 set | W9 §11.2; W9-D3; W9-T12 | WP9.7, after U-2 |
| O-25 | Integration-pilot thresholds, and the governing-record set, hashed and anchored before the batch's first acceptance | W9 §14.3; W9-T16 | WP9.3 acceptance preparer; m-9's anchor definition; §7 L-4 |
| O-26 | Recall metric in the versioned W3 reference tokenizer | W9 §14.2–14.3; P-028 | WP9.7 |
| O-27 | Stephen's W0-D1 signature on all eight §14 items before any closed-reference observation; the signing record cites P-062 C1 | W9 §4.5; §8.5 item 2; G7C-D1 | §7 L-0 |
| O-28 | Every W9 acceptance test | W9 §17 | §4 |
| O-29 | `legacy-paper-root` acyclic; citation status as a separate relation | W9 §5.2; W9-T17, W9-T21 | WP9.1, WP9.2, WP9.4 |
| O-30 | W11 dossier admission referencing a `legacy-paper-root` | W9 §8.2 | **Out of scope:** a later W11 step |
| O-31 | Paper-root transitions, wider adoption, prose | W9 §§12, 14.2; W9-D7, W9-D12a | **Out of scope** for this plan's code; later owner decisions under §7 |
| O-32 | A change to a `shared_enforcement_surface` contract re-triggers observation of the affected results' enforcement state; the reviewer derives the affected set from binding tests | W9 §4.3; W9-D14 | WP9.5: the detector flags such a change. WP9.3: re-observation is marked required. Test: a fixture contract change marks its bound results for re-observation. |
| O-33 | Any blob change to a registered file blocks every open observation, adoption or transition that binds the old blob | W9 §4.2 item 3 | WP9.3 (observation and acceptance preparers re-hash at commit); WP9.4 (adoption suspends); test with W9-T6 and W9-T9 |
| O-34 | Whole-file adoption of a binary or restricted input; the successor Task re-hashes it at use, and a mismatch suspends the adoption | W9 §9 item 1 | WP9.4 (adoption subject); WP9.7 (use-time re-hash in the successor Task path) |
| O-35 | In-store manual-operation mode: each human edit enters as an attributed ARS event registering the new bytes; a registry of the keys Stephen registers for named writers | W9 §13.1 | WP9.6 |
| O-36 | `.apm/` file-level inventory: 34 tracked files, stage logs and the bus, each mapped to exactly one closure or non-import record | W9 §13.3 item 5 | WP9.3 tool; closure is a bijection test (W9-T18) |
| O-37 | Per-item `pilot_promotion` evidence or waiver, with fixture IDs, before acceptance | W9 §8.5 item 4; P-062 A8 | WP9.1 adds evidence or waiver refs to `legacy-closed-reference-acceptance`; WP9.3 refuses acceptance without them |
| O-38 | D8c carried m-3: a positional-free backlog selector with byte offsets, at the next re-observation | D8c acceptance record, "Carried" | **Out of scope:** W11 machinery (W9 §15). Noted for W11's next re-observation. |

## 4. Acceptance tests (W9 §17) → packages

| Test | Package | Kind |
|---|---|---|
| W9-T1 status word never yields acceptance | WP9.3 | unit |
| W9-T2 families survive import | WP9.3 | integration (fixture copy of the T1.37 headline) |
| W9-T3 every key in exactly one family | WP9.3 | unit |
| W9-T4 precedence resolves lines 69–71 | WP9.3 | integration (fixture copy of the `SUPERSEDED.md` lines) |
| W9-T5 no return to `legacy_owned` | WP9.2 | unit (reducer) |
| W9-T6 change in a window aborts | WP9.3 | integration (with O-33) |
| W9-T7 detectors fire | WP9.5 | integration, `slow`: scratch clone from the local object store, fixture registry listing the files `5df0c001` and `811d5a2b` touched |
| W9-T8 no successor use without adoption | WP9.4 (legacy side), WP9.7 (CreateTask guard) | integration |
| W9-T9 adoption revalidates | WP9.4 | integration |
| W9-T10 successor work writes nothing legacy | WP9.7 | integration (RegisterArtefact guard) |
| W9-T11 restricted bytes stay out of the store | WP9.3 (reader), WP9.7 (RegisterArtefact) | integration |
| W9-T12 family coverage at dispatch | WP9.7 | integration |
| W9-T13 corrections bind generally | WP9.3 | unit |
| W9-T14 supersession acyclic, history kept | WP9.6 | unit |
| W9-T15 paper recovery changes no accepted artefact | WP9.6 | integration (scratch store) |
| W9-T16 thresholds precede the batch | WP9.3 (acceptance preparer) | unit |
| W9-T17 paper transition cannot bypass adoption | WP9.4 (legacy side and W5 clause) | integration, with D-3 |
| W9-T18 closure is a bijection | WP9.3 | unit |
| W9-T19 legacy entries and locks match baselines | WP9.5 | unit (fixture log and `CONVENTIONS.md`) |
| W9-T20 Gate 6 store never a W9 target | WP9.2 | integration: a scratch store whose manifest carries the frozen §2.6 `store_identity` under a valid test foundation, plus a copy at a second path. The test asserts the W9 guard's own reason code. |
| W9-T21 paper-root records acyclic | WP9.1 (schema), WP9.2 (reducer), WP9.4 (graph) | unit |
| W9-T22 duplicate anchors block | WP9.3 | unit |
| W9-T23 manual-mode edits attributable | WP9.6 | unit, with synthetic keys |

**Fixtures rule.**
- **No live sources.** No test reads a live legacy file, the vault or a restricted byte. Tests use committed fixture
  copies or synthetic files. The one exception is W9-T7's replay of two known commits, which runs in a scratch clone.
- **Fixture manifest.** Each fixture copy carries a manifest naming its source path and blob at a pinned commit. A
  test re-derives the blob, so "copy" is verified rather than asserted.
- **Restricted data.** A test that would need restricted data uses a synthetic stand-in with the same shape.
- **Mocking rule.** The fixtures are byte copies of committed repository text, not mocks of external data sources.
  This keeps to the CLAUDE.md rule.

## 5. Work packages

Each package is one PR on a `pipe/` branch. It gets independent adversarial review by a distinct session and
CodeRabbit review before merge, and Stephen merges.

**Order.** WP9.0 and WP9.1 come first. WP9.2 needs WP9.1's accepted catalogue identity. WP9.3 to WP9.7 follow WP9.2,
in any order that respects the stated dependencies.

**Recurring owner gate (D-4).** Every package PR that adds a W9 command or changes a protected identity carries the
changed census row set and digest, the 06h manifest YAML, the append-site classification and any changed tree ID.
Stephen re-accepts them at exact bytes at that PR's review, and the re-acceptance gets a register entry. Expected:
WP9.2, WP9.3, WP9.4 and WP9.6 add commands. WP9.7 changes a protected tree only if U-2, U-5 or U-6 requires it.

### WP9.0 — Documents that gate the code

- **W6 addendum for S-016** (O-15): `design/06d-w9-s016-operator-mediated-addendum-<date>.md`. It re-specifies S-016
  under P-042: an unavailable second-family session yields `r3_family_coverage_insufficient`, and the `unable_to_grade`
  H row stays. It gets its own independent review and Stephen's acceptance.
- **Membership-table template and authoring guide** (W9 §6.2). This is a template only. The real tables are authored,
  reviewed and accepted per file under §7 L-4a.
- **Segmentation contract** (m-7): a versioned contract for item boundaries in Markdown selectors, covering:
  - heading to the last non-blank line;
  - trailing blank lines;
  - LF handling;
  - the hash input;
  - a required UTC timestamp on every observation.
  
  It is reviewed with WP9.3, and the Computational-Log export (D-7) uses it.
- **Done:** the addendum is accepted; the template and the contract are merged.

### WP9.1 — Schema family, catalogue and bootstrap contract (data, no runtime)

- **Schemas.** `.research-system/schemas/contracts/w9/` holds one strict, closed JSON Schema per W9 §5.2 record and per
  emitted event, each with `$id` `ars://legacy/<record>` and `additionalProperties: false`.
  - Enumerations take W9's exact sets: the §5.2 roles, the §5.4 identity kinds, the §5.5 selector kinds, the §6.1
    classes, the §6.4 qualifiers and the §8.2 transitions. `successor_owned → legacy_owned` is absent.
  - `legacy-paper-root` carries no transition ref and no citation status. A recovery root carries its predecessor and
    its recovery Decision. This is the structural half of W9-T21.
  - `legacy-closed-reference-acceptance` carries per-item `pilot_promotion` evidence or waiver refs with fixture IDs
    (O-37), and the hashes of the threshold pre-registration and of the governing-record set (O-25).
- **Runtime activation (m-13).** The `ars://legacy/` schemas are validated by the W9 runtime directly through the
  registry, as Discovery validates `ars://portfolio/` content (`runtime.py:2610`). They are not runtime bindings. A test
  asserts that no `ars://legacy/` ID appears in `_RUNTIME_BINDINGS`, mirroring
  `test_w11_contract_materialization.py:1589-1592`. W9 command envelopes do get `ars://core/command` rows (§2.2).
- **Catalogue.** `.research-system/evals/expected/w9-legacy-integration-v1.json` has one row per W9 command, with IDs
  `LR-001` onward, distinct from W11's `OR-` namespace. Each row lists the command, actor class, preconditions, events,
  touched streams and binding tests.
- **Acceptance envelope and bootstrap contract.** These are
  `.research-system/schemas/contracts/w9/w9-catalogue-acceptance-envelope` and
  `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml`, modelled on W11's. The contract states
  that the W9 runtime cannot produce or accept its own prerequisite.
- **Tests.**
  - Every schema validates against the metaschema.
  - No `ars://legacy/` ID collides with `ars://portfolio/`, and the W11 tree is unchanged
    (`test_w11_expected_catalogue.py:209-251`).
  - The reference graph between record kinds is acyclic.
  - The `ars://legacy/` IDs are not runtime-activated.
- **Gate.**
  1. Independent review.
  2. **Stephen accepts the catalogue at an exact Git/blob/SHA-256 identity** (O-8).
  3. A follow-up commit adds `research_system/legacy/accepted_w9.py`, holding that identity and the frozen Gate 6
     identity (§2.6) as frozen mappings, like `accepted_w11.py:16-52`.

### WP9.2 — Legacy runtime, genesis, shared replay and CLI

- **Package.** `research_system/legacy/` with `commands.py`, `routes.py`, `runtime.py`, `replay/` (reducers and
  transaction contracts) and `accepted_w9.py`. It follows the Discovery-style path (§2.2), with its own single append
  site. Each command is admitted only through that append site, under scoped authority and the same three-root
  `CompositeWriterLock` as Discovery (`runtime.py:194-198`). No other module appends.
- **Runtime-binding rows.** Each W9 command added in this package gets its `ars://core/command` 1.0.0 row
  (`schema_registry.py:209-265`). Events fall back to `ars://core/event`. Census, manifest and append-site changes go
  to D-4.
- **Shared-ledger replay (M-1; resolve U-7 first).**
  - A `legacy` command-type predicate, owned by `research_system/legacy/`, that `projection/replay.py` (`:1319-1324`)
    and `shared_event_partition` (`discovery/routes.py:301-319`) consult before their defaults.
  - A lazy `replay_legacy` call at the generic boundary, next to the `replay_discovery` call (`replay.py:1369-1381`).
  - The Discovery replay must accept W9 events in the same ledger without treating them as operational.
  - Editing `shared_event_partition` is in scope **only as the predicate consultation**. The 59/21/1 partition, the
    excluded rows and every W11 pin stay unchanged. If the edit cannot be confined to that, the package stops and
    returns Partial.
  - **Test.** A scratch store holding W11 genesis, W9 genesis, one W9 observation and one generic command must replay
    through `rebuild_projection`, `replay_discovery` and the verify-restore path. **Negative control:** the same ledger
    with the predicate removed must fail.
- **Genesis.** `ImportAcceptedW9CatalogueGenesis` emits `W9CatalogueGenesisImported`. It copies every W11 guard
  (§2.1):
  - the pre-lock payload check;
  - refusal of a second genesis per store, from the replayed projection;
  - stream version 0;
  - payload equal to the accepted identity;
  - re-hashed catalogue and bootstrap bytes;
  - the row-set check;
  - a route-registry partition check over the W9 catalogue.
  
  It also refuses a store whose **replayed Discovery projection** holds no W11 catalogue (O-5; Info I-3).
- **Gate 6 store refusal (M-4).**
  - The runtime reads the bound store's manifest through `load_store_manifest` (`identity.py:857`).
  - It refuses with a dedicated W9 reason code when `store_identity` equals the frozen §2.6 value. This refuses by
    identity, so a moved or copied store is still refused.
  - It does not depend on the live foundation (W9-T20).
- **Authority.**
  - W9 commands reuse existing scoped-grant subject kinds (`scope_definition`, `review`, `decision`), as Discovery
    does (`runtime.py:209-236`). A new kind would need an authority schema version, which is out of this package's
    scope.
  - Resolver rows are Stephen-only (P-005).
  - Observer, reviewer and analyst roles follow W9 §8.6. A command whose actor is the item's producer is refused for
    the observer and reviewer roles.
- **Reducer invariants.**
  - Only the W9 §8.2 transitions.
  - `successor_owned → legacy_owned` is refused (W9-T5).
  - Supersession is acyclic.
  - Restricted-kind sources never carry a frozen-copy ref (W9-T11, store half).
- **CLI.** A new `ars legacy` group (the `cli.py:2184-2457` pattern), with read-only `status` and `show` first.
- **Tests.**
  - W9-T5, W9-T20 and the store half of W9-T11.
  - The reducer half of W9-T21.
  - The shared-replay test and its negative control.
  - **Genesis negatives:**
    - a second genesis;
    - the wrong stream version;
    - tampered bytes;
    - a missing W11 genesis;
    - a catalogue row with no route and no recorded exclusion.

### WP9.3 — Observation reader, selectors, inventories and acceptance

- **Handle-bound reader** for the four W9 §5.4 identity kinds, using the W11 §7.3 protocol: open, hash, re-check
  identity, close. Every observation records UTC time.
  - **`git_tracked`:** commit, blob and SHA-256 of the bytes read.
  - **`untracked_file`:** hash, size and path, with a frozen copy.
  - **`restricted_untracked_file`:** hash, size and path only. The reader **refuses** a frozen copy in the store.
  - **`vault_file`:** a handle-bound read. The `CONVENTIONS.md` vault alias is refused.
- **Windows (O-33).** The observation and acceptance preparers re-hash at commit. A change aborts with no event
  (W9-T6), and every open observation, adoption or transition that binds the old blob is blocked.
- **Selectors** (W9 §5.5) under the WP9.0 segmentation contract:
  - JSON-pointer family sets from an accepted membership table;
  - the tracker task-ID row;
  - the Working Note date-heading entry;
  - log frontmatter;
  - the Computational-Log heading entry, from the export only;
  - the `CONVENTIONS.md` bullet or paragraph, from blob `4b143c92` only;
  - heading-anchored sections.
  
  An unaddressed region or a duplicate anchor is a blocker row, never resolved by position (W9-T18, W9-T22).
- **Class and qualifiers.**
  - W0 classes come only from a signed W0 record; an unsigned class refuses the observation (O-27).
  - Qualifiers are typed. `corrected_by` takes values from the canonical source (W9-T13).
  - Precedence follows W0 manifest §8.4 (W9-T4).
  - A status word never yields acceptance (W9-T1).
  - An unassigned key blocks import (W9-T3).
  - A `shared_enforcement_surface` change marks the bound results for re-observation (O-32).
- **Closed-reference acceptance.** The preparer refuses a batch unless each item carries its `pilot_promotion` evidence
  or waiver refs with fixture IDs (O-37). It also requires the threshold pre-registration and the governing-record set
  to be hashed and anchored before the batch's first acceptance (O-25; W9-T16). An anchor is either a Git commit that is
  an ancestor of the store binding's `git_head` at that acceptance, or an ARS event at a lower global position (m-9).
- **Tools.**
  - A light-inventory builder with an independent-reproduction mode.
  - The Computational-Log baseline exporter. It writes the export into the repository's W9 evidence area, so the
    export's hash is Git-anchored (O-21; D-7).
  - The `.apm/bus/` closure inventory (O-19).
  - The `.apm/` file-level inventory (O-36).
- **Tests:** W9-T1, W9-T2, W9-T3, W9-T4, W9-T6, the reader half of W9-T11, W9-T13, W9-T16, W9-T18 and W9-T22, plus
  O-32 and O-33.

### WP9.4 — Adoption, discharge and citation status

- **`AdoptLegacyAuthority`** (W9 §9).
  - Stephen-only and use-scoped.
  - Its subject is one accepted observation by family, or a whole binary or restricted file whose use-time re-hash is
    required (O-34).
  - It records the W5 admissibility consequence.
  - Revalidation: a re-observation, a new qualifier or a supersession suspends it (W9-T9).
- **`legacy-discharge-relation`.** A successor result paired with a legacy open item, carrying a reviewer and Stephen's
  Decision.
- **`legacy-paper-citation-status`.** It points at the root and binds the frozen cited-family set's hash. A later
  status supersedes an earlier one.
- **The citation check (D-3).** `research_system/legacy/citations.py` is a deterministic extractor.
  - **Input:** the observed, handle-bound bytes of the paper root's files, read by a non-author, never the live tree.
  - **Scope:** every file in the root's inventory: Markdown, LaTeX and scripts such as
    `papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py`.
  - **Output:** cited result files, projected to families through the accepted membership tables and the audit's
    artifact map.
  - **Comparison:** the result is compared with the reviewer's independent derivation. A difference blocks the
    transition. Both are hashed and filed before it (O-14).
- **Legacy-side refusals.** A transition is refused if the set omits a family, or if the drafts cite a family missing
  from the set (W9-T17).
- **Successor-side refusals** (resolve U-5 and U-6 first):
  - The CreateTask guard (§2.7) refuses a Task whose `source_import_refs` reference an unadopted family (W9-T8).
  - The W5 hook blocks claims resting on a family marked unadopted (W9-T17, W5 clause).
- **Tests:** W9-T8, W9-T9 and W9-T17, plus the graph half of W9-T21.

### WP9.5 — Detectors (W9-D5)

- **Registration manifest (M-6).** Each registration batch exports the store's registered set to a committed,
  Git-anchored file in the W9 evidence area. The export is reviewed with the batch. A test checks that the manifest
  equals the store's registered set at the bound head. The detectors read this manifest, because CI cannot read the
  store.
- **Post-merge first-parent detector.** `tools/check_legacy_writes.py`, run by
  `.github/workflows/legacy-write-detector.yml` on push to main and on a schedule. It walks `origin/main` first-parent
  from a recorded baseline commit and flags:
  1. a commit touching a manifest-registered legacy file without a §4.2 record;
  2. any change under `results/` outside `results/ars/` without a §4.2 record;
  3. a change to a `shared_enforcement_surface` contract (O-32).
  
  §4.2 records are keyed by **PR number plus each registered file's old and new blob**, not by commit SHA. The
  detector maps each squash commit to its PR through the merge-queue derivation that `tools/check_merge_admission.py`
  already performs.

  It also reads the configuration of ruleset 20822054 and its rule-suites history, subject to U-3 and D-8.
- **`CONVENTIONS.md` check.** `tools/check_conventions_legacy_locks.py`, as a CI job. It applies the insertion-only rule
  against blob `4b143c92`.
- **Vault detector.** `tools/check_legacy_log_baseline.py` compares every live legacy Computational-Log entry with the
  accepted export. It flags a missing, renamed or duplicated legacy anchor and any unparseable heading. It runs on the
  operator machine (U-4) before each batch and weekly (D-5). Each run files an output hash in the W9 evidence area, and
  a missed run blocks the next batch.
- **Negative controls (O-13).** Each control is watched to fail **on a scratch clone or a byte copy, never by writing
  `main` or the vault**:
  - replays of `5df0c001` and `811d5a2b` against a fixture registry that lists the files they touched;
  - a fixture change to an unregistered file under `results/`;
  - a fixture edit inside a legacy log entry, and a renamed legacy heading, on a byte copy of the export;
  - a modified legacy bullet. An inserted successor bullet must **not** fire.
- **Tests:** W9-T7 (slow, integration) and W9-T19.

### WP9.6 — Rollback, recovery, manual mode and projection

- **`legacy-record-supersession`.** It needs a reason, a reviewer and Stephen's Decision. Current use re-points to the
  new record, and dependent adoptions suspend. Cycles are refused (W9-T14).
- **Paper recovery** (W9 §13.1). The Decision comes first and names only the predecessor root and the intent. The
  recovery root is created after it and names both. Neither names a transition event.
- **Manual-operation mode** (O-18, O-35).
  - **In-store mode:** each human edit enters as an attributed ARS event that registers the new bytes under the human
    actor.
  - **Store-failure mode:** the importer verifies each commit's signature against a writer-key registry that Stephen
    maintains, or verifies a recorded GitHub pusher identity. It rejects any commit it cannot attribute (W9-T23).
- **Rollback-handle harness (O-17).** A scratch-store script exercises an item's pre-commit abort path and its
  post-commit supersession or recovery route. The batch checklist records one run per item.
- **Read-only legacy projection** (O-16; W9-D8b). It is written under `.research-system/projections/legacy/`, built on
  WP9.2's `replay_legacy`, and carries source position, projector version, content hash and rebuild identity. A test
  asserts that no command reads it.
- **Tests:** W9-T14, W9-T15 (scratch store; every legacy blob unchanged after recovery) and W9-T23.

### WP9.7 — Successor-side guards and pilot support

This package edits the generic command service (§2.7). Its review may split it along those seams (D-6).

- **Family-coverage dispatch guard** (O-24; resolve U-2 first). For a Task in P-005's R3 set, dispatch requires a
  record naming a second-family session that meets W9 §11.2's three-part eligibility test. Someone other than the
  producer and that session must check it. Otherwise the dispatch records `r3_family_coverage_insufficient` and is
  refused before compute (W9-T12).
- **RegisterArtefact guard** (O-22, O-23). A `manifest.relative_path` is refused if it:
  - is a manifest-registered legacy file;
  - falls under `results/` outside `results/ars/`;
  - matches a registered `restricted_untracked_file`, or a restricted pattern (`*.pkl`, `*.csv`, null caches).
  
  This covers W9-T10 and the artefact half of W9-T11.
- **Use-time re-hash** (O-34). A successor Task that uses an adopted whole-file input re-hashes it at use. A mismatch
  suspends the adoption.
- **Recall and context metric helper** (O-26). It uses the versioned W3 reference tokenizer only.
- **Tests:** W9-T10, the artefact half of W9-T11, W9-T12, and O-34.

## 6. Owner decisions this plan asks for

| ID | Decision | Recommendation |
|---|---|---|
| D-1 | **The W9 store (W9-D10)** | A **new control store, `C:/Users/steph/TDL-ARS-G7-Control`**, created by runbook L1 to L7 (`06s-phase5-runbook.md:189-195`) with Gate 7 names. Specifics below the table. |
| D-2 | **Command path** | **Discovery-style** (`research_system/legacy/`). It keeps the **legacy commands** out of the protected `core/commands` and `core/events` trees. The successor guards are mapped in §2.7. The conditions are M-1's shared replay and writer lock, one runtime-binding row per command, and §2.7. |
| D-3 | **W9-T17's second clause (Info I-c)** | **Both.** The deterministic extractor runs over every file type in the root, on observed bytes, projected to families. The reviewer's independent derivation is compared with it, and any difference blocks. |
| D-4 | **P-059 re-acceptance procedure** | At **every** package PR that adds a command or changes a protected identity, Stephen re-accepts at exact bytes: the census row set and digest, the 06h manifest YAML, the append-site classification, and any changed tree ID. Each re-acceptance gets a register entry, as P-059 did. Expected at WP9.2, WP9.3, WP9.4 and WP9.6, and at WP9.7 if a core schema changes. |
| D-5 | **Vault-detector cadence** | Before every batch, plus a weekly local scheduled run. Each run files an output hash in the W9 evidence area, and a missed run blocks the next batch. CI cannot read the vault. |
| D-6 | **Package granularity** | One PR per package. WP9.3 may split into reader and selectors, and WP9.7 along its §2.7 seams, if their reviews ask. |
| D-7 | **Computational-Log baseline timing** (W9 §7.3 item 6) | Take the non-author baseline export as preparation under W9 §4.5 row 1, **as soon as Stephen authorizes it**. That can be before any package lands: a reviewed byte copy with per-entry hashes under the WP9.0 segmentation contract. Otherwise, as soon as WP9.3's exporter merges. The classified legacy-entry list follows, for his acceptance. This is §7 L-0b. |
| D-8 | **U-3 fallback**, decided only if U-3 shows the CI token cannot read rule-suites | Record as a known limit that bypass use between batches is seen only at the next pre-batch local read, under the owner's `gh`. The alternative is a token with ruleset read access. |

**D-1 specifics.**
- **Project ID:** reuse `prj_01978abc-1000-7000-8000-000000001000`. It is the same TDL project. The new store gets its
  own random `store_identity`, and the Gate 6 refusal keys on that, not on the project ID.
- **Consequence of the re-pin:** after the foundation re-pin merges, the Gate 6 store is readable only from the M2
  checkout `4d867d85`. Its identity is frozen in §2.6 for the W9 refusal.
- **Binding advance:** every later code change the store uses needs `ars store advance-binding` (`cli.py:2232-2234`),
  each by Stephen's authorization. 06s L7's "nothing is pulled into the checkout" does not hold for a gate this long.
- **Separate authorizations:** creation needs runbook A1 to A7, each authorized separately, plus a delta assurance on
  the re-pin, as in Gate 6.

## 7. Live operations (not authorized by this plan or P-063)

These follow implementation, except L-0 and L-0b. **Each needs its own recorded owner decision.**

**Operative preconditions.** W9 §4.5, W9 §8.5 and the 04-plan §4 Gate 7 per-item conditions apply to every step. The
gate column below adds only what those texts do not already state.

| Step | Operation | Added gate |
|---|---|---|
| L-0 | Stephen signs the eight W0 manifest §14 items after the independent check W0-D1 names. The signing record cites P-062 C1. | Not code; it precedes any closed-reference observation (O-27) |
| L-0b | Non-author Computational-Log baseline export; then the classified legacy-entry list, accepted by Stephen; the `CONVENTIONS.md` baseline recorded | Stephen's authorization (D-7) |
| L-1 | Detectors live on real `main` and on the operator machine's vault. Each negative control is watched to fail **on a scratch clone or a byte copy, never by writing `main` or the vault**. | The WP9.5 package merged |
| L-2 | Create the D-1 store (runbook A1 to A7), then run W11 genesis (`bootstrap_genesis`) | Stephen's store decision; each A-step authorization; a scoped grant |
| L-3 | W9 genesis, under a grant scoped to the W9 catalogue stream | The catalogue and bootstrap contract accepted (WP9.1) |
| L-4a | Per file: a membership table authored by a non-author, independently reviewed, accepted by Stephen | Before that file's first observation (W9 §8.5 item 3) |
| L-4 | First closed-reference batch (the integration pilot, at most 20 items) | Before acceptance: the thresholds and the governing-record set hashed and anchored (W9 §14.3); per-item `pilot_promotion` evidence or waiver refs, with fixture IDs |
| L-5 | Later batches, adoption, successor compute, paper roots | Any project-use acceptance also needs a public writer for the governing scientific-review record, or another option-A placement (04-plan §4 Gate 7) |

**Batch checklist.**
- **Before every batch:**
  - re-read the ruleset bypass list;
  - run all four detectors;
  - check the registration manifest against the store;
  - record one rollback-handle run per item;
  - confirm W0 currency (G7-A §17).
- **After every batch:** replay and restore, as in S-014 (W9 §12.3 and §14.3).

## 8. Stop rules

Stop and return the package as Partial when any of these holds:
- an interface in §2.8 resolves differently from the plan's assumption;
- a W11 pin would change: the route partition, the schema tree, or the not-runtime-activated test;
- the shared-replay edit cannot be confined to a predicate (U-7);
- a test needs live legacy, vault or restricted bytes;
- a command would write a legacy file or the Gate 6 store;
- a protected identity changes without Stephen's exact-bytes re-acceptance (D-4);
- a successor guard needs a core schema change that the package did not carry to D-4;
- any W9 §13.4 criterion applies.

## 9. Review and acceptance of this plan

- [x] Independent adversarial review of revision 1: REWORK REQUIRED (`b3fe778c`).
- [x] Author reconciliation (this revision 2).
- [ ] Narrow re-review of revision 2.
- [ ] Stephen's exact-revision acceptance of the plan and of D-1 to D-8, recorded as a register entry, as P-062 and
  P-063 were.
- [ ] Stephen's separate decision authorizing implementation, which this plan does not contain.

**Known limit (P-058):** all reviews so far have run on one model family.
