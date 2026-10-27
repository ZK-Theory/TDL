# WP9.2 design note: the legacy runtime, genesis, shared replay and CLI

**Date:** 2026-10-27<br>
**Status:** Revision 3, confirmed. Revision 2 reconciled the review
`reviews/wp9-2-design-note-review-6b5aeee3-2026-10-27.md` (rework required, narrow) under Stephen's decisions P-077
(see `reviews/wp9-2-design-note-reconciliation-2026-10-27.md`). The reviewer's confirmation of revision 2
(`reviews/wp9-2-design-note-confirmation-0fa7eb09-2026-10-27.md`) passed with four Minor findings, n-1 to n-4, which
revision 3 folds in at Stephen's request with no further round (reconciliation §5). Nothing in it is implemented.<br>
**Package:** 06v WP9.2 ("Legacy runtime, genesis, shared replay and CLI"), in two PRs, WP9.2-1 and WP9.2-2 (P-077 item
4).<br>
**Authority:** P-076 (WP9.2, note first), with P-077 (owner points A to D, the D-6 exception and the boundary
extension). WP9.0 and WP9.1 are complete; the catalogue and annex were accepted at `7979e85a` (O-8, P-075).<br>
**Base:** `main` at `eab253f6` (tree `0962a5a4`). P-076 and P-077 are on `pipe/w9-wp9-2-legacy-runtime`; documents
that cite them by commit cite their `main` commit after merge (review i-5).<br>
**Not authorized (P-076):** WP9.3 to WP9.7; live operations L-0 to L-5; creating a real store, or running genesis or
issuing a grant on one; any legacy write. Every store in this note is a scratch store that a test creates under a
temporary directory and discards.<br>
**Probe:** the U-7 prototype in §2 was a throwaway, run in a working tree and reverted. To reproduce it, the probe test
(`test_u7_probe.py`), the diff of the three shared files and the prototype `research_system/legacy/commands.py` are
kept outside the repository, in the session notes folder `wp9-2-u7-probe/`. Apply them at `eab253f6` and run the probe
with `PYTHONPATH=.` from the repository root.

## 1. What this note settles

06v WP9.2 lists the package. This note settles what 06v leaves open or states wrongly, so that the code has nothing
left to decide:
1. U-7: the shared-replay edit is confined to four sites, under five conditions (§2).
2. The one command WP9.2 admits, its binding row and its authority entries, and the route classes (§3; P-077 item 1).
3. Event payloads (§4).
4. `accepted_w9.py`, the genesis payload and the acceptance envelope, with its out-of-store refs (§5; P-077 items 2
   and 3).
5. The bootstrap contract amendment and the two PRs (§6; P-077 items 4 to 6).
6. The runtime, the Gate 6 refusal, genesis and the reducers (§7); the CLI (§8); the tests (§9); D-4 (§10); the stop
   rules (§11).

## 2. U-7: the shared-replay edit is confined to four sites

### 2.1 The sites at `eab253f6`

06v cites the sites at `e82f9630`. They have not moved materially:

| # | Site | Location at `eab253f6` | Edit |
|---|---|---|---|
| 1 | Generic replay's per-event loop | `research_system/projection/replay.py:1319-1360` (`_replay`), where `discovery_projection_event` is computed, `_validate_active_lifecycle_binding` is called, and `apply_event` is called | Compute `legacy = is_legacy_projection_event(event)`. When it holds, skip both `_validate_active_lifecycle_binding` and `apply_event`, as Discovery events skip them. Every envelope, schema, hash-chain, stream-version and transaction check before them still runs |
| 2 | `shared_event_partition` | `research_system/discovery/routes.py:301-319` | Directly after the `discovery` branch and before the artefact, context and control branches, return a **new** value, `"legacy"`, when the predicate holds |
| 3 | `replay_discovery`'s partition dispatch | `research_system/discovery/replay/driver.py:379-408` | One branch: `if partition == "legacy": continue` |
| 4 | The generic boundary | `research_system/projection/replay.py:1369-1381`, beside the lazy `replay_discovery` call | When `validate_discovery_semantics` holds and the ledger holds a legacy event, lazily import and call `replay_legacy(ordered_events, schemas=...)` |

The predicate is `research_system/legacy/commands.py::is_legacy_projection_event`: the event's `command_type` is in
`LEGACY_COMMAND_TYPES`. That set is the 12 command types of the accepted catalogue: a literal in the leaf module, so
the replay path reads no file, and a test requires it to equal the accepted catalogue's command set. Sites 1, 2 and 4
import it lazily, inside the function, as `replay.py` already imports `replay_discovery`. That keeps
`research_system/legacy/` out of the import graph of the Discovery architecture pins.

**Why site 1 skips the lifecycle check (review B-1).** `validate_exact_lifecycle_envelope`
(`research_system/command/lifecycle.py:470-513`) falls back from its producer table to `EXACT_LIFECYCLE_BINDINGS`,
which maps each W2 event schema to its generic producer: `ReviewRequested` to `RequestReview` (`:261-265`), and the
same for `ReviewVerdictRecorded`, `DecisionProposed` and `DecisionResolved` (`:300-338`). It would therefore refuse
every W9 review and Decision event with "exact lifecycle event provenance mismatch", and those events belong to 43 of
the 61 catalogue rows. The review reproduced that refusal. Discovery events skip the check for the same reason
(`projection/replay.py:1323-1324`), which is why W11 needed no `lifecycle.py` entry, and neither does W9. What the
check would protect is covered three ways:
- `_replay` still resolves every event's command-schema identity against its recorded SHA-256
  (`projection/replay.py:1248-1258`);
- the Discovery envelope validator checks command rows and producer bindings over the whole ledger (C1, C2);
- `replay_legacy` validates every payload record (§4) and refuses a W9 event type under a non-W9 command, or the
  reverse.

### 2.2 Probe

The probe built a scratch store with W11 genesis through the Discovery test harness
(`tests/research_system/integration/test_wp6_6_discovery_runtime.py::_runtime`, `_genesis`). It then appended forged,
re-hashed W9 events under `ImportAcceptedW9CatalogueGenesis` and `ObserveLegacyRecord`, schema `ars://core/event`
1.0.0, command schema `ars://core/command` 1.0.0, with prototype binding rows for the 12 W9 commands. Its payloads were
not schema-shaped and its event-type names were not catalogue-derived (review M-1, m-10); the code's tests use
catalogue-derived names and schema-valid payloads (§4, §9).

| Case | Result |
|---|---|
| W11 genesis alone | `replay` and `replay_discovery` pass |
| W11 genesis + two W9 events, four sites + binding rows | `replay`, `replay_discovery` and `rebuild_projection` pass. Both W9 events partition as `legacy`. `replay_legacy` runs once per `replay` and once per `rebuild_projection`, and not from `replay_discovery`'s internal shared replay, which passes `validate_discovery_semantics=False` (`projection/replay.py:1199`) |
| **Negative control:** the predicate returns `False` | `replay`: "unsupported event type: W9CatalogueGenesisImported". `replay_discovery`: "invalid Discovery operational partition" |
| Site 3 alone removed (sites 1, 2 and 4 in place) | `replay_discovery`: "unsupported Discovery event: W9CatalogueGenesisImported" |
| No W9 command binding rows | Both refuse in the Discovery envelope validator: "Discovery persisted schema provenance mismatch", cause "active command binding mismatch" |
| A W2-typed event (`ReviewRequested` under `RequestW9AuthorityReview`) with no producer binding | Both refuse: cause "unbound event producer" |
| The same event with a producer binding but recorded as `ars://core/event` | Refused: "active event binding mismatch" |
| A W9 payload carrying `governing_refs: ["W11:OR-010"]` | `replay_discovery` refuses: "Discovery transaction carries conflicting W11 owner rows" |
| Review §A2: a schema-valid `ReviewRequested` under `RequestW9AuthorityReview`, with a producer binding | With the lifecycle check kept: both refuse, "exact lifecycle event provenance mismatch". With site 1 as in §2.1: both pass |

Against the prototype, these suites passed unchanged: `test_wp6_6_discovery_activation.py`,
`test_wp6_6_discovery_architecture.py`, `test_p045_envelope_decision.py`, `test_w11_expected_catalogue.py` and
`test_w11_contract_materialization.py` (339 tests; the review reproduced them), and `test_wp6_6_discovery_runtime.py`
(100 tests, 26 minutes). The 59/21/1 partition, the excluded rows and every W11 pin are untouched.

### 2.3 The conditions the confinement depends on

The edit stays at four sites only while these hold. Each is a rule for the W9 package, with a test (§9):
1. **C1, command rows.** Every W9 command that appends has its `ars://core/command` 1.0.0 runtime-binding row. The
   Discovery envelope validator (`discovery/ledger_integrity.py:38-170`) runs over the whole ledger and refuses any
   command without one.
2. **C2, W2-typed events.** A W9 command that emits a W2 event type (`ReviewRequested`, `ReviewVerdictRecorded`,
   `DecisionProposed`, `DecisionResolved`) needs a producer binding for that pair, and the event carries the W2 event
   schema with a payload valid against it. W11's `RequestW11AuthorityReview` is the pattern. This corrects 06v WP9.2
   "Events fall back to `ars://core/event`", which holds only for event types with no producer bindings. No such
   command is admitted in WP9.2 (§3), so these bindings land with their packages, under D-4, and need no
   `lifecycle.py` entry (§2.1).
3. **C3, no W11 row in a W9 payload (review M-1).** No W9 event payload carries, at its top level, an `owner_row_id`
   or `row_id` that names a W11 row, or a `W11:OR-` string in `governing_refs` or `governing_evidence_refs`.
   `_owner_row_id` (`discovery/replay/transactions.py:173-192`) collects exactly those. An `LR-` row there is inert to
   Discovery: `_matching_contract_rows` keeps only W11 rows whose command type matches (`:455-459`), and
   `validate_transaction_contract` returns for a non-Discovery command (`:513-530`). It is optional, and the closed W2
   payloads cannot carry one anyway. The W9 preparer refuses a violating payload before append, and a test shows
   replay refuses it too.
4. **C4, positive-equality consumers.** Every other partition consumer selects by equality or set membership
   (`discovery/runtime.py:2214` and `:2254`, `discovery/spec.py:284`, `discovery/spec_assay.py:1133`,
   `discovery/replay/driver.py:59,64`), so the new value is excluded from each without an edit. Without site 2, W9
   events would partition as `operational` and enter the `spec.py:284` and `runtime.py:2214` filters. The consumer
   test pins all of them. The review confirmed the list is complete (i-3).
5. **C5, no shared event type (review m-11).** Site 2 sends `PartialOutcomeRecorded` and `LeaseReleased` to
   `operational` before any other branch (`discovery/routes.py:309-310`), and site 1's predicate keys on command type
   alone. So no W9 row may emit an event type in the operational, artefact, context or control sets. The accepted
   catalogue emits none; a test checks every row's `ordered_events` against those sets.

### 2.4 Corrections to 06v's text

- 06v WP9.2 says that without the `continue` branch a legacy event "falls through to 'unsupported Discovery event'".
  With sites 1 and 2 in place but site 3 removed, that is right (§2.2). With the predicate removed altogether, the
  event never reaches the reducer table: it partitions as `operational`, and `replay_control_plane` refuses it. The
  negative controls assert the observed messages.
- "Events fall back to `ars://core/event`" (C2 above).

These are corrections to 06v's text; its accepted bytes are not edited.

### 2.5 One accepted asymmetry (review m-5)

`DiscoveryRuntime`'s pre-command replay (`discovery/runtime.py:474-479`) reaches only `_replay_shared_partitions`, with
`validate_discovery_semantics=False`, so it never runs `replay_legacy`. A Discovery command can therefore append on top
of a ledger whose legacy half `replay_legacy` would refuse. Closing that would be a fifth site, so it is accepted: the
next generic or legacy replay refuses the store, and a test shows it. `LegacyRuntime` itself replays all three halves
before every command (§7.1).

### 2.6 Verdict

U-7 resolves as the plan assumed. The package does not stop.

## 3. What WP9.2 admits, and the route classes

**Binding (P-077 item 1).** WP9.2 adds one runtime-binding row, `SchemaBinding("ars://core/command", "1.0.0",
command_type="ImportAcceptedW9CatalogueGenesis")`. The census grows by 1. `research_system/authority.py` gains the
matching entries (review M-2):
- `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` (`:171-207`), a set of command types: the genesis command, as W11's
  genesis is listed (`:180`). A command in that set, submitted by anyone other than the owner, needs a grant with
  exactly one actor class (`:2721-2726`), drawn from `{"human", "agent", "service"}` (`:170`). The genesis grant's one
  class is `human` (review confirmation n-4). The catalogue's LR-001 `eligible_actor: operator` is a W9 actor role, not
  a class: the operator is the human who runs L-3, so the role maps to `human`;
- `_SCOPED_COMMAND_SUBJECT_KINDS` (`:208-331`): `ImportAcceptedW9CatalogueGenesis` as `scope_definition`, as W11's
  genesis is.

Without them, `validate_scoped_grant_activation` (`:700-708`) refuses the grant ("inactive or has the wrong subject
kind"). The grant's subject ID must equal the W9 `CATALOGUE_STREAM_ID`, as Discovery binds `target_stream_id`
(`discovery/runtime.py:240`). That meets O-4 ("genesis under an owner grant scoped to the W9 catalogue stream") and
global precondition G4 ("a path-only, role-only or wildcard subject never satisfies a row"). These entries are not a
P-059 protected identity (review D-4 row), so §10 adds nothing for them.

**The predicate** covers all 12 command types. Membership grants nothing; it only routes replay, and fixing the set now
means later packages never touch the four shared sites again.

**Not admitted.** The inert `ImportAcceptedW9CatalogueRevision` (LR-002, "inert in v1: no accepted revision exists")
gets no row (review m-2): with no row it cannot be granted, which is the same argument that keeps the other ten
commands unbound. Its replay reducer and its guards are built and tested in WP9.2 against a test registry that adds
the row, as the probe did.

**Route classes (review m-1).** The legacy route registry partitions the 61 rows into two classes, as W11's registry
partitions its 81 (`discovery/routes.py:344-355`):
- **routed** (1): LR-001;
- **deferred** (60): every other row, each tagged with what routes it.

06v §5 predates the stage B command set, so it maps no row to a package (confirmation n-3). The tags follow from the
package scopes in 06v §5, by record kind or Decision:

| Tag | Rows (by record kind or Decision) | 06v §5 basis |
|---|---|---|
| `catalogue_revision` | LR-002, the revision import | Routed only by an accepted catalogue revision (P-071 item 4; P-072 item 5), not by a package |
| `WP9.3` | `legacy-record-observed`; `legacy-light-inventory`; `legacy-closed-reference-acceptance`; `legacy-path-registration`; `legacy-field-family-membership`; and their review and Decision rows | "Observation reader, selectors, inventories and acceptance" |
| `WP9.4` | `legacy-adoption-decision` (other than the eligibility Decision); `legacy-discharge-relation`; `legacy-paper-citation-status`; the ordinary `legacy-paper-root`; `legacy-source-inventory`; `legacy-transition-mapping`; `legacy-ownership-transitioned`; and their review and Decision rows | "Adoption, discharge and citation status", including the legacy-side transition refusals |
| `WP9.6` | `legacy-record-supersession`; the recovery `legacy-paper-root` and the paper-root recovery Decision; and their review and Decision rows | "Rollback, recovery, manual mode and projection" |
| `WP9.7` | `legacy-adoption-use-mismatch` (`RecordAdoptionUseMismatch`); the reviewer-eligibility Decision; the integration-pilot outcome Decision | "Successor-side guards and pilot support"; P-072 item 3 adds the use-mismatch row "for WP9.7's guard to request" |

The per-row list of all 60 tags lives in the legacy route table, and a test pins it. WP9.7 routing
`RecordAdoptionUseMismatch` and the two Decisions means WP9.7 adds commands, which 06v D-4's expected list ("WP9.2,
WP9.3, WP9.4 and WP9.6") did not foresee. So WP9.7 also carries a D-4 re-acceptance. Any later move of a row between
packages is a change to this table, made by the package that takes the row.

There is no "excluded" class: in W11 an exclusion means never implemented under that catalogue, which is not the case
here. A test pins the 1/60 partition. `replay_legacy` refuses any event of a deferred row with "W9 row not routed in
this version", so a store cannot hold an event that this code has no reducer route for. If L-3 runs before WP9.3, the
store holds genesis only, and every later command is refused for want of a binding row.

**Reducers** for every record kind are still built in WP9.2, as 06v lists, and tested on forged ledgers through a test
registry and a test route table that routes their rows. The production route table routes only LR-001.

## 4. Event payloads (review M-1; P-069 item 2)

| Event kind | Event type | Schema recorded | Payload | W9 row identified by |
|---|---|---|---|---|
| `E:` events (24 kinds, plus genesis and revision) | `catalogue_event_name(token)` (`discovery/routes.py:322-335`): `E:w9-catalogue-genesis-imported` gives `W9CatalogueGenesisImported`, `E:legacy-record-observed` gives `LegacyRecordObserved` | `ars://core/event` 1.0.0 (no producer binding exists for these types) | The record itself, validated against the row's `record_schema_id` and `record_schema_version` through the registry | The discriminant function below, applied to the command type and the record's content |
| `W2:ReviewRequested` | `ReviewRequested` | `ars://core/event/ReviewRequested` (C2) | The closed W2 payload | `governing_refs: ["W9:LR-nnn"]` |
| `W2:ReviewVerdictRecorded` | `ReviewVerdictRecorded` | its W2 schema (C2) | The closed W2 payload, which has no `governing_refs` | Its `review_id`, through the `ReviewRequested` it answers |
| `W2:DecisionProposed`, `W2:DecisionResolved` | as named | their W2 schemas (C2) | The closed W2 payloads | `governing_evidence_refs` holding exactly one `W9:LR-nnn` string (required by both schemas: `decision_proposed.schema.json:54-62`, `:115`) |

**Why not the Decision's proposal (confirmation n-1).** Three Decision pairs write no W9 record (catalogue G5), so no
proposal pre-assigns their `dec_`: the integration-pilot outcome (LR-021, LR-022), the reviewer-eligibility Decision
(LR-024, LR-025) and the paper-root recovery Decision (LR-036, LR-037). The `governing_evidence_refs` string works for
every Decision row, and a `W9:` string there is inert to Discovery: `_owner_row_id` reads only `W11:OR-` strings
(`discovery/replay/transactions.py:186-189`).

**The discriminant function.** No W9 record carries a `payload_discriminant`: it is a catalogue row field only. So
`replay_legacy` assigns each transaction to one row as follows:
- **A transaction with a W2 event** (the review and Decision rows, including every `ResolveW9AuthorityDecision` row
  that also writes an `E:…-recorded` event): every event in it takes the row its W2 event names, by the rules in the
  table. That separates rows that share a command and record kind, such as LR-054 and LR-055 (both
  `legacy-ownership-transitioned` under `ResolveW9AuthorityDecision`, differing only by direction) and LR-024 and
  LR-028 (`legacy-adoption-decision`).
- **A transaction of `E:` events only** (18 rows): the discriminant is computed from the command type and the record:
  - `ProposeLegacyRecord`: `propose-legacy-record/<record kind>`, with the kind's hyphens written as underscores, for
    example `propose-legacy-record/legacy_path_registration` (10 rows);
  - `CreateLegacyPaperRoot`: `recovery: null` gives `create-legacy-paper-root/ordinary` (LR-035); a non-null `recovery`
    gives `create-legacy-paper-root/recovery` (LR-038);
  - every other command: its kebab-case slug alone, for example `observe-legacy-record` (LR-001, LR-002, LR-014,
    LR-015, LR-039, LR-061).

`(command_type, payload_discriminant)` is unique over the 61 rows (confirmation i-1), so each rule selects one row. A
test shows the rules together are a bijection onto the 61 rows.

Only genesis is admitted in WP9.2. The W2 rows are fixed here so that WP9.3 and later packages add bindings and
reducers, not a layout. `replay_legacy` validates every `E:` payload through the registry, and a test shows a
schema-invalid payload is refused (P-069 item 2: "WP9.2 validates each event's payload record through the schema
registry"). Generic replay does not do this for `ars://core/event` (`projection/replay.py:219-220`), so the legacy half
must.

The genesis event's payload is the genesis record (`ars://legacy/import-accepted-w9-catalogue-genesis` 1.0.0). It is
closed and has no row field, unlike W11's genesis event, which adds `owner_row_id: OR-140` to its payload
(`discovery/accepted_w11.py:35-52`). C3 allows that absence.

## 5. `accepted_w9.py`, the genesis payload and the envelope

### 5.1 `research_system/legacy/accepted_w9.py`

A leaf module, as `discovery/accepted_w11.py` is. Its frozen `ACCEPTED` mapping:

| Key | Value |
|---|---|
| `accepted_commit`, `accepted_tree` | `7979e85a075ab6a643a7b201ac4186b0b2090d74`, `d6746b4d583f3f6e1beefd74723290ac30e5fa3f` |
| `catalogue_path`, `catalogue_blob`, `catalogue_bytes`, `catalogue_sha256`, `content_hash` | `.research-system/evals/expected/w9-legacy-integration-v1.json`, `d1916ffd…`, 128,583, `f7e2d9e2…db8c`, `fd94dc94…5e676` |
| `annex_path`, `annex_blob`, `annex_bytes`, `annex_sha256` | `…/wp9-1-catalogue-owner-annex.yaml`, `d8fbda41…`, 85,664, `36a3d1ac…36fc` |
| `owner_row_multiset_hash` | `a80788184c02b5baa9ea47cf2f1a254f4f14499188e6a0dcbef8d083072ffde7` (P-077 item 3) |
| `bootstrap_*` (path, commit, blob, bytes, SHA-256) | The contract as amended and merged by WP9.2-1 (§6) |
| `envelope_*` (path, commit, blob, bytes, SHA-256) | The envelope as merged by WP9.2-1 (§6) |
| `gate6_store_identity` | `5e3b95a956a8a416accd697f250088b5c8723924eb68544f01064ede6eb18d69` (06v §2.6; 06v WP9.1 gate step 3, re-homed by P-066 item 2) (review m-6) |
| `external_refs` | The three reserved IDs of §5.3, with the file identities they derive from |
| `owner_decision` | P-075's quoted text |

`ROW_IDS` is LR-001 to LR-061. `CATALOGUE_STREAM_ID` is a fixed `obj_` constant.

**The O-8 pin keeps its independent expected side (review m-6).** `test_w9_expected_catalogue.py` keeps its
`O8_ACCEPTED` literals and adds an assertion that `ACCEPTED` equals them, so one PR cannot change the runtime's
constants and the test's expected side together.

### 5.2 The genesis payload

`accepted_genesis_payload()` returns the complete closed record (`import-accepted-w9-catalogue-genesis` 1.0.0), field
by field (review m-3):

| Field | Value |
|---|---|
| `schema_id`, `schema_version` | `ars://legacy/import-accepted-w9-catalogue-genesis`, `1.0.0` |
| `bootstrap_contract_identity` | The amended contract at WP9.2-1's main commit: path, commit, blob, length, SHA-256 |
| `external_envelope_identity` | The envelope at WP9.2-1's main commit: path, commit, blob, length, SHA-256 |
| `requested_genesis_transaction_id` | The fixed nominal string `w9-genesis-request-v1`, which the closed schema requires (`minLength: 1`). It is not compared with the ledger's transaction, which the ledger mints itself (`store/ledger.py:447`), and it deliberately carries no `txb_` prefix, so it cannot be read as a ledger ID (confirmation n-2). Retries are handled by receipts (§7.3) |
| `required_w11_catalogue` | The contract's value: blob `8d588185…`, `7e36b39a…0b80`, 136,229 bytes |
| `refused_store_identities` | `[gate6_store_identity]` |
| `verification_requirements` | The contract's `verification_rules`, as amended, verbatim |
| `activation_status` | `not_executed` (a schema const: the record describes the request; the event records its execution) |

### 5.3 The envelope's fields and its reserved external refs (P-077 item 2; review M-3, M-4, m-12)

The envelope (`ars://legacy/w9-catalogue-acceptance-envelope` 1.0.0) requires 17 fields. Their sources:

| Field | Source |
|---|---|
| `schema_id`, `schema_version` | Consts |
| `specification_identity`, `plan_identity` | The catalogue's `owner_spec_identity` and `owner_plan_identity`, verbatim: W9 at `50371fac` (blob `ea3a8e4a`) and 06v at `4999111c` (blob `2b40fae4`). That fixes which of 06v's two accepted byte states is cited: the one the catalogue cites |
| `catalogue_identity` | `7979e85a`, `d1916ffd`, `f7e2d9e2…db8c`, 128,583 |
| `owner_annex_identity` | The catalogue's `owner_annex_identity`: `fc5f356b`, `d8fbda41`, `36a3d1ac…36fc`, 85,664 |
| `schema_identities` | The catalogue's 19 `schema_source_rows`, verbatim |
| `owner_row_multiset_hash` | `a8078818…ffde7` (P-077 item 3) |
| `bootstrap_contract_identity` | The contract as merged at `7979e85a`: blob `96a63114`, `b3352b2c…3ac1`, 3,820 bytes (P-075 carried; review M-5) |
| `schema_generator_identity`, `verifier_identity` | At `7979e85a`: `tools/w9_schema_gen.py` `5b068f9d`, `tools/verify_w9_materialization.py` `e8bb5085` |
| `binding_test_identities` | At `7979e85a`: `test_w9_expected_catalogue.py` `5a8e1c84` and `test_w9_contract_materialization.py` `4133b75e` (review m-7: `a7621a39` at `eab253f6` was written by PR #404 after O-8) |
| `independent_observation_ref` | Reserved external ref, kind `observation` |
| `independent_review_ref` | Reserved external ref, kind `review` |
| `acceptance_decision_ref` | Reserved external ref, kind `decision` |
| `accepted_at` | `2026-10-27T18:55:08Z`, the author and committer time of `eab253f6`, which records P-075 on `main` |
| `acceptance_scope` | "O-8: the W9 expected catalogue and its owner annex at main commit 7979e85a (P-075)" |

Every value is taken at `7979e85a` except `accepted_at`, so the envelope records what O-8 rested on.

**Reserved external refs.** Each ref names a committed file at a main commit:

| Kind | Referent | ID prefix and schema def |
|---|---|---|
| `observation` | The canonical-checkout verifier run that P-075 cites, as recorded in P-075's Evidence (the register file at `eab253f6`) | `obj_` (`recordRef`, which `anyRef` admits) |
| `review` | `reviews/wp9-1-stage-b2-confirmation-3241f0e9-2026-10-27.md` at `7979e85a` | `rev_` (`reviewRef`) |
| `decision` | P-075 in `03-decisions-and-open-questions.md` at `eab253f6` | `dec_` (`decisionRef`) |

The derivation, fixed:
1. The domain string is `w9-external:<kind>:<entry>:<repository_path>@<commit>`, where `<entry>` is `P-075` for the
   observation and the decision, and `B2-confirmation` for the review.
2. `d` is the SHA-256 of the string's UTF-8 bytes.
3. The UUID's 48-bit `unix_ts_ms` is `accepted_at` in milliseconds, `1793127308000`.
4. `rand_a` (12 bits) is the first 12 bits of `d`; `rand_b` (62 bits) is the next 62 bits of `d`.
5. The version nibble is `7` and the variant bits `10`, so the ID matches the schemas' UUIDv7 patterns
   (`revId`, `decId`).
6. `record_revision` is 1. `content_hash` is the raw SHA-256 of the named file at the named commit, which is not the
   record-content hash a store ref carries. No consumer dereferences these refs as store records, and a test shows
   it: no W9 or ARS reader resolves them against a store.

**Reservation, not probability (review M-4).** ARS review and Decision IDs are pre-assigned by the proposer (P-072
item 1; G5), and the derivation is public. So genesis records the three IDs in the W9 projection's identity set, and
the W9 identity check, W9-C25 (P-073 item 1), refuses any pre-assigned ID equal to one of them. A test proposes a
record that pre-assigns the reserved `dec_` and expects refusal; the proposing command is not admitted in WP9.2, so the
test drives the check directly.

## 6. The bootstrap contract amendment and the two PRs (P-077 items 4 to 6)

### 6.1 Why the contract must change

The contract at `96a63114` still describes the inert foundation. Its `forbidden` list includes "runtime handlers,
ledger append, reducers, or projectors", "catalogue acceptance envelope instance" and "W9 genesis import", and its
`verification_rules` say "no runtime production Python is changed" and "no acceptance instance is materialized in the
repository". Only the last is mechanically enforced, by `test_the_only_tracked_instance_is_the_w9_catalogue`
(`test_w9_expected_catalogue.py:499-501`).

Two precedents exist (review m-8). WP9.1 stage B amended the free-text lists and kept the consts, as the stage B note §6
directed (`wp9-1-stage-b-design-note.md:216-220`), applied in `7979e85a`. W11 never amended its own contract at all
(B2 review i-5). P-077 item 4 follows the first.

### 6.2 The amendment

- The schema consts stay: `materialization_status: inert_foundation_only`, `runtime_activation: forbidden`, and the two
  `forbidden_in_stage_a` values. No schema changes, so the catalogue's 19 schema source rows are unaffected.
- A new verification rule records their reading (review M-6): "runtime_activation and materialization_status govern
  the ars://legacy/ schemas' runtime bindings only; the W9 runtime is WP9.2's (P-077)". The rule they govern is "ars://legacy/
  schema ids remain absent from runtime bindings" (contract line 37), and it stays true: W9 commands bind
  `ars://core/command`. `test_w9_contract_materialization.py:347` keeps asserting `runtime_activation == "forbidden"`.
- `forbidden` drops "runtime handlers, ledger append, reducers, or projectors", "catalogue acceptance envelope
  instance" and "W9 genesis import". It keeps the Gate 6 store, legacy observation and transition, and provider
  actions, and adds "any W9 acceptance envelope instance other than
  .research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json".
- `verification_rules` drop "no runtime production Python is changed" and "no acceptance instance is materialized in
  the repository", and name the one envelope path.

### 6.3 The two PRs

1. **WP9.2-1, contract and envelope (data).**
   - The contract amendment of §6.2.
   - `.research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json` in canonical bytes, with every field
     from §5.3. It cites the contract at `7979e85a` (P-075), so it does not depend on the amendment's commit.
   - `test_the_only_tracked_instance_is_the_w9_catalogue` allows exactly that envelope path.
   - A test re-derives the three reserved IDs and the multiset hash from their sources.
   - It is reviewed. After merge, Stephen accepts the amended contract at its main commit (06v O-3), as its own
     decision.
2. **WP9.2-2, runtime.** Everything in §§2, 3, 4, 5.1, 5.2 and 7 to 9. `accepted_w9.py` pins the amended contract and
   the envelope at WP9.2-1's main commit, and the genesis payload names the amended contract. D-4 applies here.

The envelope records what O-8 rested on; the genesis payload records what the runtime runs under. Each identity is
exact, and the chain needs only these two steps.

**Departure recorded (P-077 item 6; review M-5).** P-072 item 6 placed the envelope "at L-3 in the store, or with
WP9.2's `accepted_w9.py`". The genesis schema's `external_envelope_identity` requires a repository path, commit, blob,
length and SHA-256 (`import-accepted-w9-catalogue-genesis.schema.json:52-80`), which neither placement supplies, so the
envelope is a committed file.

## 7. Runtime, Gate 6 refusal, genesis and reducers

### 7.1 The append site

`research_system/legacy/runtime.py::LegacyRuntime` follows `DiscoveryRuntime`:
- its own `_submit_authorized`, the only W9 append site;
- the same three-root `CompositeWriterLock` (`discovery/runtime.py:194-198`);
- scoped authority with the existing subject kinds, and the `authority.py` entries of §3;
- resolver rows Stephen-only (P-005), and the W9 §8.6 role rules;
- a whole-ledger replay before every command: generic, Discovery and legacy.

The append-site classification gains one entry, `legacy_command_producer`, beside `discovery_command_producer` (06h
manifest; D-4).

### 7.2 The Gate 6 refusal comes before any lock (review M-7)

Taking the writer lock writes into the control root: `WriterLock` creates its lock path (`store/writer.py:938`,
`:1069`), and `CompositeWriterLock` publishes a live lease (`:1503-1504`). So the refusal cannot sit under the lock.
It runs when `LegacyRuntime` binds a store, for every command, not for genesis only (catalogue precondition G1, "read
unbound before binding"):
1. read the target manifest with `load_store_manifest_unbound` (`store/identity.py:636-651`);
2. refuse with reason code `w9_gate6_store_refused` when `store_identity` is in `refused_store_identities`;
3. only then bind with `load_store_manifest` (`:857`), take the lock, and go on.

W9-T20's three cases (06v §4) use 1.0.0 scratch manifests, which may carry an arbitrary identity (06v §2.6):
- the frozen identity at its original path: refused with the W9 reason code;
- a byte copy at a second path: refused with the W9 reason code, before the path check at `identity.py:867-868` could
  fire;
- a different identity: passes the refusal.

In both refusing cases the control root is byte-identical afterwards: no lock, lease or receipt file.

### 7.3 Genesis

`ImportAcceptedW9CatalogueGenesis` emits `W9CatalogueGenesisImported`. Before binding, the payload must equal
`accepted_genesis_payload()`, and the Gate 6 refusal of §7.2 runs.

**Retries come first (confirmation n-2).** After its whole-ledger replay and before any preparation, `LegacyRuntime`
answers a retry as `DiscoveryRuntime` does (`discovery/runtime.py:474-511`): it looks up the scoped receipt by
idempotency scope, command payload hash and authority, and returns it; failing that, it looks up the receipt by
command ID. The guards below never see a retry. W9-C11-LR-001 tests that path. Any genesis command other than the
accepted payload is refused before binding, so no second, different genesis request can exist.

Then, under the lock, in order (review m-3 adds items 2 and 4):
1. the replayed Discovery projection holds W11's catalogue (O-5);
2. that catalogue's identity equals the payload's `required_w11_catalogue`;
3. no W9 genesis exists in the replayed legacy projection;
4. the target stream is `CATALOGUE_STREAM_ID`;
5. the catalogue stream is at version 0;
6. the catalogue, annex, amended contract and envelope bytes re-hash to `ACCEPTED`;
7. the catalogue's row set is LR-001 to LR-061, and its `owner_row_multiset_hash` equals the envelope's;
8. the route registry partitions the catalogue's 61 rows into 1 routed and 60 deferred, with the §3 tags.

On success the projection reserves the three external IDs (§5.3). Guard 7's hash adds nothing beyond guard 6, since
both read the same file (review i-2); the independent value comes from the WP9.2-1 reviewer, who reconstructs it.

`replay_legacy` refuses a second genesis, a payload that differs from `ACCEPTED`, and a W9 genesis with no prior W11
genesis in the ledger. It checks the last directly, because `replay` calls `replay_discovery` only when a Discovery
event exists (`projection/replay.py:1369-1381`).

**LR-001's two owner preconditions** are not code checks. "Stephen's O-8 acceptance current" is satisfied by
`ACCEPTED` and re-checked at L-3. "The bootstrap implementation independently verified against the accepted contract"
is WP9.2-2's independent review together with O-3. Both are L-3 owner gates, recorded in the L-3 checklist.

### 7.4 Reducers

`research_system/legacy/replay/` holds the reducers and transaction contracts. The invariants are 06v's:
- only the W9 §8.2 transitions: `legacy_owned → successor_owned`, `legacy_owned → closed_reference`,
  `successor_owned → closed_reference`; `successor_owned → legacy_owned` is refused (W9-T5);
- supersession is acyclic;
- a `legacy-paper-root` that names its own transition event, a recovery Decision that names its recovery root, or any
  cycle among root, mapping, transition and recovery Decision is refused (W9-T21, reducer half);
- a restricted-kind source never carries a frozen-copy ref (W9-T11, store half).

Each row's transaction contract is generated from the accepted catalogue's `ordered_events`, so a row's write set
cannot drift from the accepted bytes.

## 8. CLI

A new `ars legacy` group, on the `cli.py` group pattern (`cli.py:2184-2457`), with read-only `status` (genesis present,
catalogue identity, row and event counts) and `show <id>`. Both rebuild the legacy projection from the bound store and
write nothing; both run the Gate 6 refusal first. The group joins `main`'s error set. Mutating subcommands come with
their packages.

## 9. Tests

| Test | What it shows |
|---|---|
| Shared replay | A scratch store holding W11 genesis, W9 genesis (through the real preparer and lock), one W9 `LegacyRecordObserved` event, one schema-valid W2-typed W9 event (`ReviewRequested` under `RequestW9AuthorityReview`, test registry) and one generic command replays through `replay`, `rebuild_projection`, `replay_discovery` and `verify_restore_before_writer_lease`'s replay |
| Negative controls | The predicate removed: the §2.2 messages. Site 3 removed: "unsupported Discovery event". The lifecycle check restored at site 1: "exact lifecycle event provenance mismatch" on the W2-typed event |
| Consumer test | Every C4 consumer leaves W9 events out |
| C1, C2, C3, C5 | A missing command row; a W2-typed event without its producer binding, and one recorded as `ars://core/event`; a top-level `W11:OR-` reference; a catalogue row emitting a shared event type. Each is refused, and each asserts its message |
| `LEGACY_COMMAND_TYPES` | Equals the accepted catalogue's command set |
| Payload validation | A schema-invalid `E:` payload is refused by `replay_legacy` (P-069 item 2) |
| Route classes | The 1/60 partition and the per-row tags of §3; an event of a deferred row is refused |
| Row assignment | The §4 rules are a bijection onto the 61 rows' discriminants, including LR-035/LR-038, LR-054/LR-055 and the three record-less Decision pairs |
| Grant scope (O-4, G4) | A grant whose subject is not `CATALOGUE_STREAM_ID`, or has no exact subject, is refused; a genesis grant with an actor class other than exactly `human` is refused |
| Catalogue identities | `W9-C01-LR-001`, `W9-C03-LR-001-owner-row-mutation`, and `W9-C11-LR-001`, which retries the accepted genesis and gets the original receipt back from the scoped-receipt path before preparation (and the LR-002 three, on the test registry) |
| Genesis negatives | A second genesis after the first committed; the wrong target stream; the wrong stream version; tampered catalogue, annex, contract or envelope bytes; a missing W11 genesis, at the preparer and at replay; a W11 catalogue other than `required_w11_catalogue`; a route partition that is not 1/60; any payload other than `accepted_genesis_payload()`, refused before binding |
| Reserved IDs | Genesis reserves the three; a pre-assigned `dec_` equal to the reserved one is refused; no reader dereferences them |
| W9-T20 | The three cases of §7.2, with the control root byte-identical when refused |
| W9-T5, W9-T21 (reducer), W9-T11 (store) | The reducer invariants of §7.4, on forged ledgers through the test registry |
| Asymmetry (§2.5) | A Discovery command appended over an invalid legacy half; the next generic replay refuses |
| O-8 pin | `ACCEPTED` equals the test's `O8_ACCEPTED` literals |
| W11 unchanged | The 59/21/1 partition and every W11 pin, run unchanged |

Every negative control asserts its message.

## 10. D-4 at WP9.2-2

WP9.2-2 changes protected identities, so Stephen re-accepts, at exact bytes and as they stand in the merge-queue
entry:
- the runtime-binding census row set and digest (+1 row, P-077 item 1);
- the 06h manifest YAML;
- the append-site classification (`legacy_command_producer`);
- any changed tree ID (none expected: no core command or event schema changes);
- the T2 validator expectations and seal, if they read the census.

WP9.2-1 changes no protected identity. It carries the envelope's review and, after merge, O-3.

## 11. Stop rules (06v §8) checked

- An interface in §2.8 resolves differently: U-7 resolves as assumed (§2.6), with two corrections to 06v's text
  (§2.4) that do not change the design.
- A W11 pin would change: none does.
- The shared-replay edit cannot be confined, or reuses an existing partition value: it is confined, and `legacy` is
  new.
- A test needs live legacy, vault or restricted bytes: none does.
- A command would write a legacy file or the Gate 6 store: genesis writes only to the bound scratch store, and the
  Gate 6 refusal runs before any lock (§7.2).
- A protected identity changes without D-4: §10 lists them.
- A successor guard needs a core schema change the package did not carry to D-4: N/A. WP9.2 has no successor guard;
  those are WP9.7's.
- Any W9 §13.4 criterion applies: N/A. Those criteria govern live transition and cutover, none of which WP9.2 runs.

## Change log

- **Revision 3 (2026-10-27).** Folds the confirmation's n-1 to n-4 with no further round, at Stephen's request. §4's
  row identification: W2 Decision events by `governing_evidence_refs`, and an explicit discriminant function for the
  18 `E:`-only rows (n-1). Retries are answered from receipts before preparation; guard 9 is deleted;
  `requested_genesis_transaction_id` is a nominal string with no `txb_` prefix (n-2). The deferred-row tags, with
  `catalogue_revision` for LR-002 and WP9.7's D-4 consequence (n-3). The genesis grant's actor class is `human` (n-4).
- **Revision 2 (2026-10-27).** Reconciles the review of `6b5aeee3` under P-077. Site 1 skips the lifecycle check
  (B-1). C3 restated, §4 event payloads added, P-069 item 2 carried (M-1). `authority.py` entries and the grant scope
  (M-2). All three external refs, the envelope field table, reservation, and the fixed derivation (M-3, M-4, m-12).
  Two PRs, with the envelope citing `96a63114` (M-5). The const reading (M-6). The Gate 6 refusal before any lock
  (M-7). The D-6 exception and boundary extension are in P-077 (M-8). Minors m-1 to m-11 applied as the
  reconciliation records.
- **Revision 1 (`6b5aeee3`).** First draft.
