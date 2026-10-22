# 06v — W9 implementation plan (Gate 7)

| Field | Value |
|---|---|
| Date | 2026-10-22 |
| Status | **Draft, revision 1, `review_pending`.** Needs independent adversarial review, reconciliation and Stephen's exact-revision acceptance (P-063). |
| Authority to write | P-063 (Gate 7 opening): "authoring, independent adversarial review and Stephen's exact-revision acceptance of the W9 implementation plan", including a proposal for the W9-D10 store |
| Implementation authority | **None.** P-063 does not authorize implementing this plan. Implementation starts only on Stephen's separate decision after the plan is accepted, and each live operation in §7 needs its own decision on top of that. |
| Specification | W9, `design/09-migration-compatibility-and-pilot.md`, draft 0.5, blob `ea3a8e4a`, accepted 2026-10-22 (W9-D1 to W9-D14) |
| Code base read | origin/main `e82f9630`. Every `path:line` below was read at that commit. |
| Jira | KAN-22 (parent). No implementation issues are created until Stephen authorizes implementation. |

All document paths are under `docs/plans/agentic-research-system/` unless they start with a repository root directory
(`research_system/`, `tests/`, `tools/`, `.github/`, `.research-system/`).

## 1. What this plan delivers

This plan builds the machinery W9 specifies, in eight work packages (§5). Each package lands as one reviewed PR.

**The machinery:**
- the closed `ars://legacy/` schema family;
- the W9 catalogue, its bootstrap contract and its one-time genesis;
- the legacy runtime (commands, routes, reducers, CLI);
- the handle-bound observation reader with its selectors;
- adoption, discharge and citation status;
- the four W9-D5 detectors;
- rollback and recovery;
- the read-only legacy projection;
- the dispatch guards W9's tests need.

**Not in this plan:** opening a store, running a genesis, or observing, importing, adopting or transitioning any item. Those are live operations, and §7 sequences them behind their own owner decisions.

**Measure of done:** the W9 acceptance tests W9-T1 to W9-T23 (W9 §17) all pass against negative controls, and every obligation in §3 has a disposition.

## 2. Interface map (verified at `e82f9630`)

### 2.1 What W11 already provides, and what W9 copies

| Seam | Fact | Citation |
|---|---|---|
| Accepted-catalogue identity | A frozen `ACCEPTED` mapping holds commit, tree, catalogue blob, bytes and SHA-256, the bootstrap contract identity and the owner decision. The row set is OR-001 to OR-041 plus OR-101 to OR-140 (81 rows), and the catalogue stream ID is a constant. | `research_system/discovery/accepted_w11.py:16-52` |
| Catalogue bytes | `.research-system/evals/expected/w11-portfolio-discovery-v1.json` (blob `8d588185`) | `git ls-tree` at `e82f9630` |
| W11 schemas | 62 files under `.research-system/schemas/contracts/w11/`, every `$id` `ars://portfolio/...`, frozen to accepted commit `09be63a9` | `tests/research_system/contracts/test_w11_expected_catalogue.py:209-251` |
| Genesis guard | `_prepare_genesis` refuses with "W11 genesis already exists" when the store's projection already holds a catalogue (`:2628`). It also requires the catalogue stream at `expected_stream_version == 0` (`:2630`), requires the payload to equal `ACCEPTED`, re-hashes the catalogue and bootstrap bytes (`:2638-2656`), and checks the 81-row set (`:2659`). | `research_system/discovery/runtime.py:2622-2662` |
| Second-genesis replay guard | The replay reducer refuses a second genesis or a payload mismatch | `research_system/discovery/replay/genesis.py:17-31` |
| Genesis operator entry | `ars discovery spec advance --action bootstrap_genesis` | `research_system/discovery/spec_assay.py:105,196`; `implementation/06s-phase5-runbook.md:211` |
| W11 legacy rows | Not implemented. OR-031, OR-032, OR-033 and OR-122 to OR-139 are `DISCOVERY_EXCLUDED_ROWS`, and OR-030 is deferred. The route registry must partition exactly 59 / 21 / 1. | `research_system/discovery/routes.py:65-68,344-355`; `tests/research_system/unit/test_wp6_6_discovery_activation.py:113-125` |
| W11 not runtime-activated | No `ars://portfolio/` schema ID may appear in `_RUNTIME_BINDINGS` | `tests/research_system/contracts/test_w11_contract_materialization.py:1589-1592` |

**Consequence (W9 §5.3 item 4, confirmed).** W11 genesis is one-time **per store**. The guard reads the target store's
own projection (`runtime.py:2628`), so a new store needs its own W11 genesis before any W11-referencing record exists.
W9 does not touch W11's route partition, its excluded rows or its schema tree. Under this plan all three stay exactly
as accepted.

### 2.2 Command, authority, store and CLI seams

| Seam | Fact | Citation |
|---|---|---|
| Discovery-style command path (the model for W9) | Commands bind the generic `ars://core/command` 1.0.0. The touchpoints are: a command-type set; a route row; subject kinds in the runtime and in `authority.py`; a family preparer; a transaction contract; a replay reducer. Events with no producer binding fall back to `ars://core/event` 1.0.0, and receipts are scoped. | `research_system/schema_registry.py:210-265`; `research_system/discovery/commands.py:14-44`; `routes.py`; `runtime.py:209-237,464-472,551-577,588-613`; `research_system/authority.py:171-234`; `research_system/discovery/replay/transactions.py:146`; `replay/registry.py:83` |
| Generic command path (the alternative) | Schema files under `core/commands` and `core/events`, `_RUNTIME_BINDINGS` rows, the lifecycle triple, service tables, a reducer and a receipt. Example: `CancelTask` → `TaskCancelled`. | `schema_registry.py:764-770,1344-1427`; `research_system/command/lifecycle.py:186`; `research_system/command/service.py:137-139,251-261,287,1552-1619,3829-3860`; `research_system/command/reducers.py:527-535` |
| Store creation | `ars store reserve`, then `ars store init` with an approved `authority-bootstrap-input`, then the first binding through `ars store repair-binding --owner-action bind-initialized-store`. Control roots must be disjoint from code roots. | `research_system/cli.py:239-285`; `research_system/authority.py:1591-1660`; `research_system/store/identity.py:767-854`; `research_system/store/layout.py:9-16`; `06s-phase5-runbook.md:191-195` |
| Scoped grants | `ars authority activate-grant`: owner only. Each allowed command is pinned to its runtime binding's schema ID, version and SHA-256, and a command with no active binding is refused. | `cli.py:1159-1218` |
| Store binding to code | Binding records `git_head`, `git_tree` and a `schema_catalogue_sha256` over every committed `*.schema.json` | `research_system/store/current_binding.py:53-79,201-253` |
| CLI | `_parser()` groups: discovery, store, command, brief, context-packet, authority, assurance-record, assurance-pack, replay, projection, eval. A new group needs `groups.add_parser`, handlers, and an entry in `main`'s error set. | `cli.py:2184-2457` |
| Projections | `ars projection rebuild` requires only that the output path sit under `<code_root>/.research-system/projections`. There is no namespace registry, and the directory is gitignored. | `cli.py:1507-1547` (check at `:1521-1525`); `research_system/projection/replay.py:1385-1404`; `.gitignore:219-220` |

### 2.3 Protected identities (P-059)

| Pin | Fact | Citation |
|---|---|---|
| Runtime-binding census | Exactly 261 rows, with SHA-256 `f359855b…` over the canonical row format | `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py:97-101,139-149` |
| Append-site classification | Every ledger-append site must be classified, so a new legacy runtime's append site is a new entry | `test_wp6_1_06h_append_path_closure.py:33-75` |
| Protected schema trees | Git tree IDs of `core/commands` (`8a86a0c4`) and `core/events` (`058c1d5d`) | `tests/research_system/contracts/wp6_2_t2_expectations.py:406-409`; enforced at `wp6_2_t2_authority_validation.py:244-249` |
| P-059 record | Re-accepted at exact bytes; census 218 → 261 | `03-decisions-and-open-questions.md` P-059 |

### 2.4 Detection and admission tooling

The existing tooling is the workflows `ci.yml`, `merge-admission.yml`, `merge-admission-sweep.yml`, `ars-artefact-currency*.yml` and
`research-system-suite.yml`, plus the tools `tools/check_merge_admission.py` (thread finality, platform order, queue, sweep)
and `tools/check_retired_imperatives.py`.

None of the following exists:
- a first-parent post-merge detector;
- a `results/` prefix rule;
- any read of rulesets or rule-suites.

A grep for `rule-suites|rulesets|first-parent` over `tools/` and `.github/` finds nothing. The P-049 ruleset appears only in
comments: `tools/check_merge_admission.py:705-707` and `.github/CODEOWNERS:11`.

### 2.5 Dispatch guard for model-family coverage

`r3_family_coverage_insufficient` appears only in an eval fixture executor
(`research_system/evals/executors/context_routing.py:210`). No dispatch path enforces P-029's two-family rule. W9-D3 and
W9-T12 therefore need a new guard (WP9.7).

### 2.6 Interface-unverified items (dispatch blockers for the named package)

| ID | Unverified | Package | How it is resolved |
|---|---|---|---|
| U-1 | Whether the W9 runtime can bind its command envelopes to `ars://core/command` 1.0.0 and its events to `ars://core/event` 1.0.0 without new `_RUNTIME_BINDINGS` rows. If it can, the census count may stay at 261, but the append-site classification still changes. | WP9.2 | The package's first step reads `runtime.py:588-613` and `schema_registry.py:210-265` end to end and records the answer in the PR before writing code |
| U-2 | Where in the dispatch path a family-coverage check belongs (ClaimDispatch preparation or an earlier admission step) | WP9.7 | Read the ClaimDispatch preparer in `research_system/command/service.py` and record `path:line` before writing code |
| U-3 | Whether the CI token can read `GET /repos/{owner}/{repo}/rulesets/20822054` and the rule-suites history | WP9.5 | A read-only probe from a workflow run, recorded in the PR. If the token cannot, the check runs locally under the owner's `gh` and the batch checklist records the run |
| U-4 | How the operator machine reaches the vault (path and junction behaviour) for the Computational-Log detector. CI cannot see the vault. | WP9.5 | Recorded from a dry run on the operator machine |

## 3. Obligation register

Every forward obligation found in W9 and its acceptance trail, with its disposition. Scan sources:
- W9 §§2–17;
- the W9 acceptance record and its "Carried" list;
- the reconciliation, review and re-check records for W9;
- P-062 and P-063.

| # | Obligation | Source | Disposition |
|---|---|---|---|
| O-1 | Implementation plan for the W9 family; no W9 operation before it | W9 §2.1 W9-A1; §2.3 | This plan |
| O-2 | Name the store for the W9 catalogue; Stephen decides; never the Gate 6 store | W9 §5.3 item 1; W9-D10; W9-T20 | §6 D-1 (proposal); WP9.2 test W9-T20 |
| O-3 | A separately accepted, minimal W9 bootstrap contract; one independently verified genesis transaction | W9 §5.3 item 2 | WP9.1 (contract), WP9.2 (genesis code), §7 L-3 (live genesis) |
| O-4 | Genesis under an owner grant scoped to the W9 catalogue stream | W9 §5.3 item 3 | WP9.2 (grant scope); §7 L-3 |
| O-5 | W11 genesis first in a new store; confirm the one-time-per-store reading against `accepted_w11.py` | W9 §5.3 item 4 | Confirmed in §2.1; §7 L-2 |
| O-6 | P-059 protected-identity re-acceptance for the new commands | W9 §5.3 item 5; W9-D10 | §6 D-4; WP9.2 acceptance gate |
| O-7 | Exact JSON shapes of the record family (W9 gives field level only) | W9 reconciliation §8 note | WP9.1 |
| O-8 | Separate W9 catalogue with exact Git/blob/SHA-256 identities, independently reviewed and accepted by Stephen | W9 §5.3 | WP9.1, with its own owner acceptance |
| O-9 | Post-merge first-parent detector, the `results/` prefix rule, and rule-suite reads | W9 §4.4; W9-D5 | WP9.5 |
| O-10 | Ruleset 20822054 bypass list read before each batch | W9 §4.4; W9-D5 | WP9.5 (tool); §7 batch checklist |
| O-11 | Vault Computational-Log detector against the baseline export | W9 §4.4, §7.3 | WP9.5 |
| O-12 | `CONVENTIONS.md` check against `4b143c92` under the insertion-only rule | W9 §4.4, §7.3 | WP9.5 |
| O-13 | Each detector watched to fail before the first registration | W9 §4.4; W9-D5 | WP9.5 negative controls; §7 L-1 |
| O-14 | Mechanical citation extractor or second derivation for W9-T17 (re-check Info I-c) | W9 acceptance record "Carried"; reconciliation §7 | §6 D-3; WP9.4 |
| O-15 | Dated W6 addendum re-specifying S-016 under P-042 | W9 §12.3; W9-D12b | WP9.0 (document); its own review and acceptance |
| O-16 | Read-only projection under `.research-system/projections/legacy/`, registered under the W9 family | W9 §7.2; W9-D8b | WP9.6 |
| O-17 | Each item's tested rollback handle: the pre-commit abort path and the post-commit supersession or recovery route, each exercised once on a scratch store before the item's batch | W9 §13.1; P-062 E9 | WP9.6 (code and tests); §7 batch checklist |
| O-18 | Manual-operation mode attribution: signed commits or recorded pusher identity, verified at import | W9 §13.1; W9-T23 | WP9.6 |
| O-19 | `.apm/bus/` closure inventory (names, sizes, SHA-256) | W9 §13.3 item 2 | WP9.3 (tool); §7 L-5 |
| O-20 | Light inventories with blocker rows, and duplicate anchors as blockers | W9 §5.5; W9-T18, W9-T22 | WP9.3 |
| O-21 | Shared-writer exception baselines: the classified legacy-entry list, accepted by Stephen; the Git-anchored export | W9 §7.3 item 1–2; W9-D9 | WP9.3 (export tool); §7 L-1 |
| O-22 | Restricted bytes never enter the store | W9 §5.4; W9-T11 | WP9.3 (reader); WP9.2 (artefact refusal) |
| O-23 | Successor compute writes nothing legacy | W9 §10; W9-T10 | WP9.7 |
| O-24 | Family coverage at dispatch for P-005's R3 set | W9 §11.2; W9-D3; W9-T12 | WP9.7 |
| O-25 | Integration-pilot thresholds anchored before the first acceptance | W9 §14.3; W9-T16 | WP9.7 (anchor check); §7 L-4 |
| O-26 | Recall metric in the versioned W3 reference tokenizer | W9 §14.2–14.3; P-028 | WP9.7 (metric helper) |
| O-27 | Stephen's W0-D1 signature on all eight §14 items, before any closed-reference observation; the signing record cites P-062 C1 | W9 §4.5; §8.5 item 2; G7C-D1 | §7 L-0 (owner action; not code) |
| O-28 | Every W9 acceptance test W9-T1 to W9-T23 | W9 §17 | §4 map |
| O-29 | `legacy-paper-root` acyclicity; citation status as a separate relation | W9 §5.2; W9-T17, W9-T21 | WP9.1, WP9.4 |
| O-30 | W11 dossier admission referencing a `legacy-paper-root` | W9 §8.2 | **Out of scope.** A later W11 step, not W9 (W9 §8.2) |
| O-31 | Paper-root transitions, wider adoption, prose | W9 §§12, 14.2; W9-D7, W9-D12a | **Out of scope** for this plan's code. Later owner decisions, under §7 |

No obligation is dropped. O-30 and O-31 are out of scope by W9's own text.

## 4. Acceptance tests (W9 §17) → packages

| Test | Package | Kind |
|---|---|---|
| W9-T1 status word never yields acceptance | WP9.3 | unit |
| W9-T2 families survive import | WP9.3 | integration (fixture copies of the T1.37 headline) |
| W9-T3 every key in exactly one family | WP9.3 | unit |
| W9-T4 precedence resolves lines 69–71 | WP9.3 | integration (fixture copy of `SUPERSEDED.md` lines) |
| W9-T5 no return to `legacy_owned` | WP9.2 | unit (reducer) |
| W9-T6 change in a window aborts | WP9.3 | integration |
| W9-T7 detectors fire | WP9.5 | integration (replays of `5df0c001` and `811d5a2b` in a scratch clone) |
| W9-T8 no successor use without adoption | WP9.4 | integration |
| W9-T9 adoption revalidates | WP9.4 | integration |
| W9-T10 parked compute writes nothing legacy | WP9.7 | integration |
| W9-T11 restricted bytes stay out of the store | WP9.3, WP9.2 | integration |
| W9-T12 family coverage at dispatch | WP9.7 | integration |
| W9-T13 corrections bind generally | WP9.3 | unit |
| W9-T14 supersession acyclic, history kept | WP9.6 | unit |
| W9-T15 paper recovery changes no accepted artefact | WP9.6 | integration (scratch store) |
| W9-T16 thresholds precede the batch | WP9.7 | unit |
| W9-T17 paper transition cannot bypass adoption | WP9.4 | integration, with the D-3 extractor |
| W9-T18 closure is a bijection | WP9.3 | unit |
| W9-T19 legacy entries and locks match baselines | WP9.5 | unit (fixture log and `CONVENTIONS.md`) |
| W9-T20 Gate 6 store never a W9 target | WP9.2 | integration |
| W9-T21 paper-root records acyclic | WP9.1, WP9.4 | unit (schema and reducer) |
| W9-T22 duplicate anchors block | WP9.3 | unit |
| W9-T23 manual-mode edits attributable | WP9.6 | unit |

**Fixtures rule.** No test reads a live legacy file, the vault or a restricted byte. Tests use committed fixture copies
or synthetic files, with the exception of W9-T7's replay of two known commits in a scratch clone. A test that would
need restricted data uses a synthetic stand-in with the same shape (CLAUDE.md: no mocks of external data sources in
integration tests. These fixtures are copies of committed repository text, not mocks of data sources).

## 5. Work packages

Each package is one PR on a `pipe/` branch. It gets an independent adversarial review by a distinct session and
CodeRabbit review before merge, and Stephen merges. Order: WP9.0 and WP9.1 first. WP9.2 needs WP9.1's accepted catalogue
identity. WP9.3 to WP9.7 can follow WP9.2 in any order that respects the stated dependencies.

### WP9.0 — Documents that gate the code

- **W6 addendum for S-016** (O-15): `design/06d-w9-s016-operator-mediated-addendum-<date>.md`. It re-specifies S-016 under
  P-042: an unavailable second-family session yields `r3_family_coverage_insufficient`, and the `unable_to_grade` H row
  stays. It gets its own independent review and Stephen's acceptance.
- **Membership-table template and authoring guide** (W9 §6.2). This is a template only. Real tables are authored per
  file by a non-author session under §7.
- **Done:** the addendum is accepted and the template is merged.

### WP9.1 — Schema family, catalogue and bootstrap contract (data, no runtime)

- **Schemas:** `.research-system/schemas/contracts/w9/` holds one strict, closed JSON Schema per W9 §5.2 record, with
  `$id` `ars://legacy/<record>` and `additionalProperties: false`. The records are:
  - `legacy-path-registration`
  - `legacy-field-family-membership`
  - `legacy-light-inventory`
  - `legacy-observation`
  - `legacy-closed-reference-acceptance`
  - `legacy-adoption-decision`
  - `legacy-discharge-relation`
  - `legacy-paper-root`
  - `legacy-paper-citation-status`
  - `legacy-source-inventory`
  - `legacy-transition-mapping`
  - `legacy-ownership-transitioned`
  - `legacy-record-supersession`
  - the events each command emits
  
  Enumerations take W9's exact sets: the §5.2 roles, the §5.4 identity kinds, the §5.5 selector kinds, the §6.1
  classes, the §6.4 qualifiers, and the §8.2 transitions (`successor_owned → legacy_owned` is absent). `legacy-paper-root`
  carries no transition ref and no citation status. A recovery root carries its predecessor and its recovery Decision.
  This is W9-T21's structural half.
- **Catalogue:** `.research-system/evals/expected/w9-legacy-integration-v1.json`. It has one row per W9 command, with IDs
  `LR-001` onward, distinct from W11's `OR-` namespace. Each row gives the command, actor class, preconditions, events,
  touched streams and the W9 tests that bind it.
- **Acceptance envelope and bootstrap contract:** `.research-system/schemas/contracts/w9/w9-catalogue-acceptance-envelope`
  and `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml`, modelled on W11's. The contract states
  that the W9 runtime cannot produce or accept its own prerequisite.
- **Tests:**
  - **Schema validity:** a contract test validates every W9 schema against the metaschema.
  - **Namespace separation:** a test asserts that no `ars://legacy/` ID collides with `ars://portfolio/` and that the
    W11 tree is unchanged. This mirrors `test_w11_expected_catalogue.py:209-251`.
  - **Acyclicity:** a test asserts the reference graph between record kinds is acyclic, including the W9-T21 shapes.
- **Gate:**
  1. The independent review of the schemas and catalogue.
  2. **Stephen accepts the catalogue at an exact Git/blob/SHA-256 identity** (O-8).
  3. Only then does a follow-up commit add `research_system/legacy/accepted_w9.py`, holding the accepted identity as a
     frozen mapping, like `accepted_w11.py:16-52`.

### WP9.2 — Legacy runtime, genesis and CLI

- **Resolve U-1 first.**
- **Package:** `research_system/legacy/` with `commands.py`, `routes.py`, `runtime.py`, `replay/` (reducers and
  transaction contracts) and `accepted_w9.py`. It follows the Discovery-style path (§2.2). Each command is admitted only
  through the W2 command service. No module writes the store outside it.
- **Genesis.** `ImportAcceptedW9CatalogueGenesis` emits `W9CatalogueGenesisImported`. It copies `_prepare_genesis`'s
  guards (`runtime.py:2622-2662`): it refuses a second genesis per store, requires stream version 0, requires the
  payload to equal the accepted identity, re-hashes the catalogue and bootstrap bytes, and checks the row set. It also
  **refuses a store with no W11 genesis** (O-5).
- **Gate 6 store refusal.** The runtime refuses any store whose identity manifest
  (`research_system/store/identity.py:767-854`) matches the Gate 6 store's recorded identity (O-2; W9-T20). This is a
  refusal by identity, not by path, so a moved or copied store is still refused.
- **Authority.** Subject kinds and scoped-grant command types for the W9 commands are added in `research_system/authority.py:171-253`.
  Resolver rows are Stephen-only (P-005). The observer, reviewer and analyst roles follow W9 §8.6. A command whose
  actor is also the item's producer is refused for observer and reviewer roles.
- **Reducer invariants:**
  - only the W9 §8.2 transitions;
  - `successor_owned → legacy_owned` is refused (W9-T5);
  - supersession is acyclic;
  - restricted-kind sources never carry a frozen-copy ref (W9-T11, store half).
- **CLI.** A new `ars legacy` group (`cli.py:2184-2457` pattern) with read-only subcommands first (`status`, `show`) and
  command submission through the existing service.
- **P-059.**
  - Update the append-site classification, the runtime-binding census if U-1 requires it, and the protected-tree IDs
    only if `core/commands` or `core/events` change.
  - **Stephen re-accepts the changed identities at exact bytes at PR review** (O-6; P-059 precedent).
  - W11's partition test (59/21/1) and the not-runtime-activated test must still pass unchanged.
- **Tests:** W9-T5, W9-T20, the W9-T11 store half, the W9-T21 reducer half, and a genesis negative set (second
  genesis, wrong stream version, tampered bytes, missing W11 genesis).

### WP9.3 — Observation reader, selectors and inventories

- **Handle-bound reader** for the four W9 §5.4 identity kinds:
  - `git_tracked`: commit, blob and SHA-256 of the bytes read.
  - `untracked_file`: handle-bound SHA-256, size and path, with a frozen copy.
  - `restricted_untracked_file`: hash, size and path only. It **refuses** to create a frozen copy in the store; any
    copy stays under `PROJ_ROOT` (W9-T11, reader half).
  - `vault_file`: handle-bound read of the vault path. The `CONVENTIONS.md` vault alias is refused (W9 §7.3).
  
  Reads use the W11 §7.3 protocol: open, hash, re-check identity, close. A change between observation and acceptance
  aborts with no event (W9-T6).
- **Selectors** (W9 §5.5):
  - JSON-pointer family sets from an accepted membership table;
  - the tracker task-ID row;
  - the Working Note date-heading entry;
  - log frontmatter;
  - Computational-Log heading entry (from the export only);
  - `CONVENTIONS.md` bullet or paragraph (from blob `4b143c92` only);
  - heading-anchored sections.
  
  An unaddressed region or a duplicate anchor is a blocker row, never resolved by position (W9-T18, W9-T22).
- **Class and qualifier assignment:**
  - Per-family W0 class comes only from a signed W0 record. An unsigned class refuses the observation (W9 §1 item 6;
    O-27).
  - Qualifiers are typed (§6.4), and `corrected_by` takes values from the canonical source by precedence (W9-T13).
  - Precedence follows W0 manifest §8.4, so the lines 69–71 conflict resolves to `unverified` (W9-T4).
  - A status word never yields acceptance (W9-T1).
  - An unassigned JSON key blocks import (W9-T3).
- **Tools:**
  - a light-inventory builder with an independent-reproduction mode;
  - the Computational-Log baseline exporter, which writes the export into the repository's W9 evidence area so its hash
    is Git-anchored (O-21);
  - the `.apm/bus/` closure inventory (O-19).
- **Tests:** W9-T1, W9-T2, W9-T3, W9-T4, W9-T6, the W9-T11 reader half, W9-T13, W9-T18 and W9-T22.

### WP9.4 — Adoption, discharge and citation status

- `AdoptLegacyAuthority` (W9 §9):
  - Stephen-only and use-scoped.
  - Its subject is one accepted observation by family, or a whole binary file under §9 item 1.
  - It records the W5 admissibility consequence.
  - **Revalidation:** a re-observation with a new blob, a new qualifier or a supersession suspends the adoption
    (W9-T9).
  - A successor Task that references an unadopted closed-reference family is refused (W9-T8).
- `legacy-discharge-relation`: successor result → legacy open item, with reviewer and Stephen's Decision.
- `legacy-paper-citation-status`:
  - It points at the root and binds the hash of the frozen cited-family set.
  - A later status supersedes an earlier one.
  - A transition is refused if the set omits a family, or if the drafts cite a family missing from the set (W9-T17).
- **The extractor (D-3).** `research_system/legacy/citations.py` is a deterministic extractor of result-file citations
  from draft Markdown: paths and filenames under `results/`, and table references the audit's artifact map lists. Its
  output is compared with the reviewer's independent derivation, and any difference blocks the transition until
  resolved. Both are hashed and filed before the transition (O-14).
- **Tests:** W9-T8, W9-T9, W9-T17 and the W9-T21 graph half.

### WP9.5 — Detectors (W9-D5)

- **Post-merge first-parent detector:** `tools/check_legacy_writes.py` with the workflow `.github/workflows/legacy-write-detector.yml`,
  run on push to main and on a schedule.
  - It walks `origin/main`'s first-parent history from a recorded baseline commit.
  - It flags (1) any commit touching a registered legacy file without a W9 §4.2 record, and (2) any change under
    `results/` outside `results/ars/` without a §4.2 record. Unregistered legacy families are still guarded (W9-D13).
  - §4.2 records are files in the W9 evidence area, matched by commit and blob.
  - It reads the ruleset 20822054 configuration and the rule-suites history for bypass use, subject to U-3.
- **`CONVENTIONS.md` check:** `tools/check_conventions_legacy_locks.py`, as a CI job. It compares every legacy bullet and
  paragraph against blob `4b143c92` under the insertion-only rule (W9 §7.3 item 4).
- **Vault detector:** `tools/check_legacy_log_baseline.py`.
  - It compares every live legacy Computational-Log entry with the accepted export.
  - It flags a missing, renamed or duplicated legacy anchor, and any unparseable heading.
  - **It runs on the operator machine,** because CI cannot see the vault (U-4). It runs before each batch and on a
    cadence Stephen sets (§6 D-5).
- **Negative controls (O-13), each watched to fail before the first registration:**
  - replays of `5df0c001` and `811d5a2b` in a scratch clone;
  - a fixture change to an unregistered file under `results/`;
  - a fixture edit inside a legacy entry, and a renamed legacy heading;
  - a modified legacy bullet. An inserted successor bullet must **not** fire.
- **Tests:** W9-T7 and W9-T19.

### WP9.6 — Rollback, recovery and projection

- `legacy-record-supersession`:
  - It requires a reason, a reviewer and Stephen's Decision.
  - Current use re-points to the new record, and dependent adoptions suspend (W9 §13.2).
  - Cycles are refused (W9-T14).
- **Paper recovery** (W9 §13.1):
  - Stephen's recovery Decision names only the predecessor root and the recovery intent.
  - The recovery root is created after the Decision and names both the Decision and the predecessor.
  - Neither names a transition event.
- **Manual-operation mode:** the importer verifies a commit's signature against a key Stephen registered for the named
  writer, or a recorded GitHub pusher identity. It rejects any commit it cannot attribute (W9-T23).
- **Rollback-handle harness (O-17):** a scratch-store script exercises an item's pre-commit abort path and its
  post-commit supersession or recovery route. The batch checklist requires one recorded run per item before its batch.
- **Read-only legacy projection** under `.research-system/projections/legacy/` (W9-D8b; O-16). It carries source
  position, projector version, content hash and rebuild identity. The `legacy_read_only_projection` registration names
  the namespace. It is never an authority input, and a test asserts that no command reads it.
- **Tests:** W9-T14, W9-T15 (scratch store: every legacy blob unchanged after recovery) and W9-T23.

### WP9.7 — Successor-work guards and pilot support

- **Dispatch guard for model-family coverage (O-24).** Resolve U-2 first. For a Task in P-005's R3 set, dispatch requires
  a record naming a second-family session that meets W9 §11.2's three-part eligibility test, checked by someone other
  than both the producer and that second-family session. Otherwise it records `r3_family_coverage_insufficient` and the
  dispatch is refused before compute (W9-T12).
- **Legacy-write refusal (O-23).** A successor Task's declared outputs and pre-registration paths may not resolve to a
  registered legacy path or the legacy pre-registration record. Outputs must sit under `results/ars/` (W9-T10).
- **Threshold anchoring (O-25).** A batch's first acceptance is refused unless its threshold pre-registration hash is
  anchored in a Git commit or ARS event that precedes it (W9-T16).
- **Recall and context metric helper (O-26).** It uses the versioned W3 reference tokenizer only, and never combines
  counts from different tokenizers.
- **Tests:** W9-T10, W9-T12 and W9-T16.

## 6. Owner decisions this plan asks for

| ID | Decision | Recommendation |
|---|---|---|
| D-1 | **The W9 store (W9-D10).** Which store receives W11's and then W9's genesis | A **new control store, `C:/Users/steph/TDL-ARS-G7-Control`**, created by the existing public procedure, runbook steps L1 to L7 (`06s-phase5-runbook.md:189-195`), with Gate 7 names. In order: a durable checkout clone and an empty origin-authority root; `ars store reserve`; a foundation re-pin PR (`.research-system/config/foundation.yaml` and its contract test) that Stephen merges, with its delta assurance; `ars store init` with a newly approved bootstrap input; then `ars store repair-binding` with `owner_action: bind-initialized-store`. The Gate 6 store stays frozen at 91 events, and the runtime refuses it by identity (WP9.2). One store for Gate 7 keeps W11 and W9 genesis, observations and successor compute on one ledger. |
| D-2 | **Command path.** Discovery-style package (`research_system/legacy/`) or the generic command service tables | **Discovery-style.** It already carries one-time genesis, scoped receipts, route partitioning and replay contracts, and it keeps W9 out of the `core/commands` and `core/events` protected trees unless U-1 says otherwise. |
| D-3 | **W9-T17's second clause (Info I-c).** Mechanical extractor, second derivation, or both | **Both:** the deterministic extractor (WP9.4) and the reviewer's independent derivation, compared, with any difference blocking. The extractor alone can miss prose citations; the derivation alone can miss mechanical ones. |
| D-4 | **P-059 re-acceptance procedure** | Stephen re-accepts the changed protected identities (append-site classification, and the census and trees if they change) **at exact bytes at WP9.2's PR review**, as P-059 did. The re-acceptance is recorded in the register. |
| D-5 | **Vault-detector cadence** | Before every batch, plus a weekly local scheduled run, with results recorded in the batch checklist. A hosted run is impossible because CI cannot read the vault. |
| D-6 | **Package granularity** | One PR per package as listed. WP9.3 may split into reader and selectors if review asks. |

## 7. Live operations (not authorized by this plan or P-063)

These follow implementation. **Each needs its own recorded owner decision** and runs under W9 §4.5 and the Gate 7
per-item conditions (04-plan §4, Gate 7).

| Step | Operation | Owner gate before it |
|---|---|---|
| L-0 | Stephen signs the eight W0 manifest §14 items after the independent check W0-D1 names; the signing record cites P-062 C1 | Not code. A prerequisite of any closed-reference observation (O-27) |
| L-1 | Detectors live and each watched to fail (WP9.5 controls run on real `main` and the real vault). Then: the non-author Computational-Log baseline export, the classified legacy-entry list accepted by Stephen, and the `CONVENTIONS.md` baseline recorded | Stephen's decision to take the baseline (W9 §7.3 item 6: as early as he authorizes) |
| L-2 | Create the D-1 store; W11 genesis (`bootstrap_genesis`) | Stephen's store decision and a scoped grant |
| L-3 | W9 genesis under a grant scoped to the W9 catalogue stream | Accepted catalogue (WP9.1) and bootstrap contract |
| L-4 | Integration-pilot thresholds pre-registered and anchored; first closed-reference batch (at most 20 items, W9 §14.2) | Stephen's batch decision; the §12.3 fixture set fixed per item |
| L-5 | Later batches; adoption; successor compute; paper roots | Each under its own W9 §4.5 row and owner decision |

**Batch checklist** (every batch):
- re-read the ruleset bypass list;
- run all four detectors;
- record one rollback-handle run per item (O-17);
- confirm the W0 currency (G7-A §17).

## 8. Stop rules

Stop and return the package as Partial when any of these holds. Never work around one.

- An interface in §2.6 resolves differently from the plan's assumption.
- A W11 pin would have to change: the route partition, the schema tree, or the not-runtime-activated test.
- A test needs live legacy, vault or restricted bytes.
- A command would write a legacy file or the Gate 6 store.
- A protected identity changes without Stephen's exact-bytes re-acceptance.
- Any W9 §13.4 criterion applies.

## 9. Review and acceptance of this plan

- [ ] Independent adversarial review of revision 1 by a distinct session (`adversarial-design-review`).
- [ ] Author reconciliation.
- [ ] Stephen's exact-revision acceptance of the plan and of D-1 to D-6.
- [ ] Stephen's separate decision authorizing implementation, which this plan does not contain.

**Known limit (P-058):** reviews so far run on one model family.
