# WP9.2 design note: the legacy runtime, genesis, shared replay and CLI

**Date:** 2026-10-27<br>
**Status:** Revision 1, for independent adversarial review. Nothing in it is implemented. The U-7 prototype in §2 was
a throwaway: it was run in a working tree and reverted, and it is not committed. To reproduce it, the probe test
(`test_u7_probe.py`), the prototype diff of the three shared files and the prototype `research_system/legacy/commands.py`
are kept outside the repository, in the session notes folder `wp9-2-u7-probe/`. Apply the diff and the module at
`eab253f6`, then run the probe with `PYTHONPATH=.` from the repository root.<br>
**Package:** 06v WP9.2 ("Legacy runtime, genesis, shared replay and CLI").<br>
**Authority:** P-076 (WP9.2, note first). WP9.0 and WP9.1 are complete; the catalogue and annex were accepted at
`7979e85a` (O-8, P-075).<br>
**Base:** `main` at `eab253f6` (tree `0962a5a4`).<br>
**Not authorized (P-076):** WP9.3 to WP9.7; live operations L-0 to L-5; creating a real store, or running genesis or
issuing a grant on one; any legacy write. Every store in this note is a scratch store that a test creates under a
temporary directory and discards.

## 1. What this note settles

06v WP9.2 lists the package. This note settles what 06v leaves open or states wrongly, so that the code PR has nothing
to decide:
1. U-7: whether the shared-replay edit can be confined to four sites (§2). **It can**, under four conditions.
2. Which W9 commands WP9.2 admits, and so which runtime-binding rows it adds (§3, owner point A).
3. What `accepted_w9.py` holds, and what the genesis payload and the acceptance envelope cite (§4, owner points B
   and C, and B2 review i-3 and i-4).
4. The bootstrap contract still forbids WP9.2's runtime, and the contract, envelope and genesis identities chain by
   main commit, so the package lands in three PRs (§4.5, owner point D).
5. The genesis guards, the Gate 6 refusal and the reducers (§5); the CLI (§6); the tests (§7); D-4 (§8).

## 2. U-7: the shared-replay edit is confined to four sites

### 2.1 The sites at `eab253f6`

06v cites the sites at `e82f9630`. They have not moved materially:

| # | Site | Location at `eab253f6` | Edit |
|---|---|---|---|
| 1 | Generic replay's per-event loop | `research_system/projection/replay.py:1319-1360` (`_replay`), where `discovery_projection_event` is computed and `apply_event` is called | Compute `legacy = is_legacy_projection_event(event)`. When it holds, do not call `apply_event`. Every envelope, schema, hash-chain, stream-version and transaction check before it still runs |
| 2 | `shared_event_partition` | `research_system/discovery/routes.py:301-319` | Directly after the `discovery` branch and before the artefact, context and control branches, return a **new** value, `"legacy"`, when the predicate holds |
| 3 | `replay_discovery`'s partition dispatch | `research_system/discovery/replay/driver.py:379-408` | One branch: `if partition == "legacy": continue` |
| 4 | The generic boundary | `research_system/projection/replay.py:1369-1381`, beside the lazy `replay_discovery` call | When `validate_discovery_semantics` holds and the ledger holds a legacy event, lazily import and call `replay_legacy(ordered_events, schemas=...)` |

The predicate is `research_system/legacy/commands.py::is_legacy_projection_event`: the event's `command_type` is in
`LEGACY_COMMAND_TYPES`. That set is the 12 command types of the accepted catalogue: a literal in the leaf module, so
the replay path reads no file, and a test requires it to equal the accepted catalogue's command set (§3). Sites 1, 2
and 4 import it lazily, inside the function, as replay.py already imports `replay_discovery`.
That keeps `research_system/legacy/` out of the import graph of the Discovery architecture pins.

Site 1 is one site with two touch points inside the same loop body: the predicate's evaluation, and the guard on
`apply_event`. The prototype instead set `discovery_projection_event = True` for legacy events, which reuses the
Discovery no-op path but also skips `_validate_active_lifecycle_binding`. The code PR does not do that: it keeps the
lifecycle-binding check for legacy events and skips only `apply_event`. The probe did not exercise that check on W9
events, so the code PR's shared-replay test must show it passes them, and a control must show it still runs.

### 2.2 Probe

The probe built a scratch store with W11 genesis through the Discovery test harness
(`tests/research_system/integration/test_wp6_6_discovery_runtime.py::_runtime`, `_genesis`). It then appended forged,
re-hashed W9 events: a `W9CatalogueGenesisImported` under `ImportAcceptedW9CatalogueGenesis`, and a legacy observation
under `ObserveLegacyRecord`. Each was schema `ars://core/event` 1.0.0 and command schema `ars://core/command` 1.0.0.
The registry carried prototype binding rows for the 12 W9 commands.

| Case | Result |
|---|---|
| W11 genesis alone | `replay` and `replay_discovery` pass |
| W11 genesis + two W9 events, four sites + binding rows | `replay`, `replay_discovery` and `rebuild_projection` pass. Both W9 events partition as `legacy`. `replay_legacy` runs once per `replay` and once per `rebuild_projection`, and not from `replay_discovery`'s internal shared replay (it passes `validate_discovery_semantics=False`), so legacy semantics are not validated twice |
| **Negative control:** the predicate returns `False` | `replay`: "unsupported event type: W9CatalogueGenesisImported". `replay_discovery`: "invalid Discovery operational partition" |
| Site 3 alone removed (sites 1, 2 and 4 in place) | `replay_discovery`: "unsupported Discovery event: W9CatalogueGenesisImported" |
| No W9 command binding rows | Both refuse in the Discovery envelope validator: "Discovery persisted schema provenance mismatch", cause "active command binding mismatch" |
| A W2-typed event (`ReviewRequested` under `RequestW9AuthorityReview`) with no producer binding | Both refuse: cause "unbound event producer" |
| The same event with a producer binding but recorded as `ars://core/event` | Refused: "active event binding mismatch" |
| A W9 payload carrying `governing_refs: ["W11:OR-010"]` | `replay_discovery` refuses: "Discovery transaction carries conflicting W11 owner rows" |

Against the prototype, these suites passed unchanged: `test_wp6_6_discovery_activation.py`,
`test_wp6_6_discovery_architecture.py`, `test_p045_envelope_decision.py`, `test_w11_expected_catalogue.py` and
`test_w11_contract_materialization.py` (339 tests), and `test_wp6_6_discovery_runtime.py` (100 tests, 26 minutes). The 59/21/1
partition, the excluded rows and every W11 pin are untouched: no W11 route, row, schema or binding changes.

### 2.3 The conditions the confinement depends on

The edit stays at four sites only while these hold. Each is a rule for the W9 package, with a test:
1. **C1, command rows.** Every W9 command that appends has its `ars://core/command` 1.0.0 runtime-binding row. The
   Discovery envelope validator (`discovery/ledger_integrity.py:38-170`) runs over the whole ledger and refuses any
   command without one.
2. **C2, W2-typed events.** A W9 command that emits a W2 event type (`ReviewRequested`, `ReviewVerdictRecorded`,
   `DecisionProposed`, `DecisionResolved`; stage B note §2) needs a producer binding for that pair, and the event
   carries the W2 event schema with a payload valid against it. W11's `RequestW11AuthorityReview` rows are the
   pattern. This corrects 06v WP9.2 "Events fall back to `ars://core/event`", which holds only for event types with
   no producer bindings. None of these commands is admitted in WP9.2 (§3), so the rows land with their package, under
   D-4.
3. **C3, no W11 row in a W9 payload's top level.** `_owner_row_id` (`discovery/replay/transactions.py:173-192`) reads
   `owner_row_id`, `row_id`, `governing_refs` and `governing_evidence_refs` from every event's top-level payload. A
   W9 transaction must carry exactly one `LR-` row there and no `W11:OR-` reference. A W9 record that cites W11
   carries the reference below the top level. The W9 preparer refuses a violating payload before append, and a test
   shows replay refuses it too.
4. **C4, positive-equality consumers.** Every other partition consumer selects by equality
   (`discovery/runtime.py:2214` and `:2254`, `discovery/spec.py:284`, `discovery/spec_assay.py:1133`), so a new value
   is excluded from each without an edit. Without site 2 the W9 events would partition as `operational` and enter the
   `spec.py:284` and `runtime.py:2214` filters. The consumer test (06v) pins all four.

### 2.4 Corrections to 06v's text

- 06v WP9.2 says that without the `continue` branch a legacy event "falls through to 'unsupported Discovery event'".
  With sites 1 and 2 in place but site 3 removed, that is right (§2.2). With the predicate removed altogether, the event
  never reaches the reducer table: it partitions as `operational`, and `replay_control_plane` refuses it. The
  negative control asserts the observed messages.
- "Events fall back to `ars://core/event`" (C2 above).

### 2.5 Verdict

U-7 resolves as the plan assumed. The package does not stop.

## 3. Which commands WP9.2 admits (owner point A)

WP9.2's tests need reducers for the record kinds (W9-T5, the reducer half of W9-T21, the store half of W9-T11), but
only genesis appends in this package. The other commands' preparers are WP9.3, WP9.4 and WP9.6 work.

- **The predicate covers all 12 command types** in WP9.2. Membership grants nothing; it only routes replay. Fixing the
  set now means later packages never touch the four shared sites again.
- **The set** is a literal, `LEGACY_COMMAND_TYPES`, checked by a test against the accepted catalogue's rows.
- **Binding rows (A).** Options:
  - **(a) Recommended: rows only for what WP9.2 admits:** `ImportAcceptedW9CatalogueGenesis` and
    `ImportAcceptedW9CatalogueRevision` (the inert revision import, P-072 item 5, which shares the genesis guards).
    The census grows by 2. Each later package adds its own rows and has its own D-4 re-acceptance, as 06v D-4
    already expects ("WP9.2, WP9.3, WP9.4 and WP9.6"). A command with no row cannot be granted, so nothing can append
    an event that WP9.2's replay has no preparer for.
  - **(b)** All 12 rows now, one D-4. Ten commands would then be grantable with no preparer; the runtime refuses them,
    but the refusal is code rather than the binding table.
- **Reducers** for every record kind are in WP9.2, as 06v lists. Their tests drive forged, re-hashed ledgers, as the
  probe did, and the Discovery tests already do (`_rehash_events`).

## 4. `accepted_w9.py`, the genesis payload and the envelope

### 4.1 `research_system/legacy/accepted_w9.py`

A leaf module, as `discovery/accepted_w11.py` is. It holds a frozen `ACCEPTED` mapping from P-075:

| Key | Value |
|---|---|
| `accepted_commit` | `7979e85a075ab6a643a7b201ac4186b0b2090d74` |
| `accepted_tree` | `d6746b4d583f3f6e1beefd74723290ac30e5fa3f` |
| `catalogue_path`, `catalogue_blob`, `catalogue_bytes`, `catalogue_sha256` | `.research-system/evals/expected/w9-legacy-integration-v1.json`, `d1916ffd…`, 128,583, `f7e2d9e2…db8c` |
| `content_hash` | `fd94dc94…5e676` |
| `annex_path`, `annex_blob`, `annex_bytes`, `annex_sha256` | `…/wp9-1-catalogue-owner-annex.yaml`, `d8fbda41…`, 85,664, `36a3d1ac…36fc` |
| `bootstrap_path`, `bootstrap_commit`, `bootstrap_blob`, `bootstrap_bytes`, `bootstrap_sha256` | `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml`, as amended and merged by WP9.2-1 (§4.5). Today it is `96a63114…`, 3,820 bytes, `b3352b2c…3ac1`, which still forbids genesis |
| `envelope_path`, `envelope_commit`, `envelope_blob`, `envelope_bytes`, `envelope_sha256` | The envelope as merged by WP9.2-2 (§4.5) |
| `owner_decision` | P-075's quoted text |

`ROW_IDS` is LR-001 to LR-061. `CATALOGUE_STREAM_ID` is a fixed `obj_` constant. The O-8 pin in
`test_w9_expected_catalogue.py` then imports `ACCEPTED`, and its literals are removed, as W11's test reads
`accepted_w11.ACCEPTED`.

### 4.2 The envelope's review and decision refs (owner point B)

The genesis schema (`import-accepted-w9-catalogue-genesis`) cites an `external_envelope_identity`. The envelope
schema (`w9-catalogue-acceptance-envelope`) requires `independent_review_ref` and `acceptance_decision_ref` as ARS
refs: a `rev_` or `dec_` ID with `record_revision` and `content_hash`. But O-8's review and acceptance happened
outside any store: the review and confirmation are committed Markdown files, and the decision is P-075. W11 met this
by citing its review by file identity (`accepted_w11.py`: `review_commit`, `review_blob`, `review_sha256`). The W9
schemas cannot be changed: they are pinned by the accepted catalogue's 19 schema source rows, so a schema change is a
new catalogue identity and a new O-8.

Options:
- **(a) Recommended: deterministic external refs.** The envelope gives each out-of-store record an ID derived from its
  identity, with `record_revision: 1` and `content_hash` the raw SHA-256 of the committed file. The schemas' `revId`
  and `decId` patterns require a UUIDv7 shape (version nibble `7`, variant `10`), so the ID is a valid UUIDv7:
  - its 48-bit timestamp is the acceptance time in milliseconds (`accepted_at`, the P-075 commit's time);
  - its remaining 74 bits come from the SHA-256 of `w9-external:<kind>:<repository_path>@<commit>`.

  The review ref names the B2 confirmation, which is the last independent review of the accepted bytes. The decision
  ref names P-075's register file at the commit that records it. `accepted_w9.py` holds both file identities, and a
  test re-derives each ID. Genesis refuses an envelope whose refs differ. A store-minted ID collides only if a store
  mints at that same millisecond and draws the same 74 bits; the scratch stores and any later W9 store are created
  after that time, so their IDs cannot.
- **(b)** Record the review and decision in the store first, then cite them. That needs W9 review and decision
  commands before genesis, which the catalogue orders after genesis. It does not work.
- **(c)** Revise the envelope schema to accept file identities. That is a new catalogue identity and a new O-8.

The ID scheme in (a) is also the one point where this note proposes a convention that no earlier record fixes, so the
review should attack it directly.

### 4.3 `owner_row_multiset_hash` (B2 review i-3) (owner point C)

P-074 item 1 defines the hash. The B2 review computed both candidates:
- over the catalogue's 24-field owner rows: `a8078818…ffde7`;
- over the annex rows (their `row_sha256` values): `c55e68dc…47623`.

**Recommended: the catalogue's rows.** O-8 accepted the catalogue's bytes, and genesis re-hashes the catalogue, so the
hash should bind what genesis reads. The annex is cited separately by `owner_annex_identity`. W11 has no precedent: its
genesis payload carries `row_ids` and `row_count`, not a multiset hash.

### 4.4 The envelope's code identities (B2 review i-4)

The envelope cites these, as merged on `main` at `eab253f6`. `bootstrap_contract_identity` is the exception: it names
the amended contract at WP9.2-1's main commit (§4.5), not `96a63114`.

| Field | Path | Blob | SHA-256 | Bytes |
|---|---|---|---|---|
| `verifier_identity` | `tools/verify_w9_materialization.py` | `e8bb5085` | `a19c23ab…5368` | 28,330 |
| `schema_generator_identity` | `tools/w9_schema_gen.py` | `5b068f9d` | `932985f4…4c14` | 56,544 |
| `binding_test_identities` | `tests/research_system/contracts/test_w9_expected_catalogue.py` | `a7621a39` | `6c4e1c7d…0126` | 24,626 |
| | `tests/research_system/contracts/test_w9_contract_materialization.py` | `4133b75e` | `d6819a52…36e5` | 52,688 |

`test_w9_expected_catalogue.py` changes again in WP9.2 (§4.1). The envelope cites the blob O-8 rested on, at
`eab253f6`, not the WP9.2 one: the envelope records the evidence the acceptance rested on, and that evidence ends at
the PR #404 merge.

### 4.5 The bootstrap contract forbids WP9.2, and the identities chain (owner point D)

The bootstrap contract at `96a63114` still describes the inert foundation. Its `forbidden` list includes "runtime
handlers, ledger append, reducers, or projectors", "catalogue acceptance envelope instance" and "W9 genesis import".
One verification rule says "no runtime production Python is changed", and another says "no acceptance instance is
materialized in the repository". The WP9.2 code would break all five. The contract schema fixes
`materialization_status: inert_foundation_only`, `runtime_activation: forbidden` and the two `forbidden_in_stage_a`
values as consts, so those stay. B2 set the pattern: it kept the consts and edited only the free-text `forbidden` and
`verification_rules` lists to the stage's state (B2 review i-5). WP9.2 does the same, and changes no schema.

That amendment changes the contract blob, and three identities then chain, each naming a main commit that exists only
after the previous one merges (06v §2.4: a squash commit cannot be named inside the PR that creates it):
1. the envelope's `bootstrap_contract_identity` names the amended contract by commit;
2. the genesis payload's `external_envelope_identity` names the envelope by commit;
3. `accepted_w9.accepted_genesis_payload()` pins both.

Options:
- **(a) Recommended: three PRs, as WP9.1 stage B split into B1 and B2.**
  1. **WP9.2-1, contract.** The free-text amendment only: the `forbidden` list drops the runtime, envelope and genesis
     entries and keeps the rest (the Gate 6 store, legacy writes, live operations, provider actions); the rules name
     the one envelope path and drop the "no runtime" and "no acceptance instance" clauses. The tracked-instance scan
     allows that one envelope path. After merge, Stephen accepts the contract at its main commit (06v O-3, "separately
     accepted minimal bootstrap contract"), which no decision has yet done.
  2. **WP9.2-2, envelope.** `.research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json` in canonical
     bytes. It cites the catalogue and annex at `7979e85a`, the contract at WP9.2-1's main commit, the code identities
     of §4.4, the refs of owner point B and the hash of owner point C. It is reviewed, and its acceptance can join the
     O-3 one.
  3. **WP9.2-3, runtime.** Everything else in this note. `accepted_w9.py` pins the envelope at WP9.2-2's main commit.
     D-4 applies here.
- **(b)** One code PR, with genesis taking the envelope's and contract's commits from the operator at L-3 and checking
  only that each named commit on `main` holds the pinned blob. The accepted payload is then not fully pinned in code,
  which W11's genesis is.

(a) costs two short data PRs. It keeps every identity exact, and each step is small enough to review alone.

## 5. Runtime, genesis, refusal and reducers

### 5.1 The append site

`research_system/legacy/runtime.py::LegacyRuntime` follows `DiscoveryRuntime`:
- its own `_submit_authorized`, the only W9 append site;
- the same three-root `CompositeWriterLock` (`discovery/runtime.py:194-198`);
- scoped authority with the existing subject kinds `scope_definition`, `review` and `decision` (06v WP9.2
  "Authority");
- resolver rows Stephen-only (P-005), and the W9 §8.6 role rules;
- a whole-ledger replay (generic, Discovery and legacy) before every command, as Discovery replays before its own.

The append-site classification gains one entry, `legacy_command_producer`, beside `discovery_command_producer` (06h
manifest; D-4).

### 5.2 Genesis

`ImportAcceptedW9CatalogueGenesis` emits `W9CatalogueGenesisImported`. Before the lock it checks that the payload
equals `accepted_genesis_payload()`. Under the lock, in order:
1. the target store's identity is not a refused identity (§5.3);
2. the replayed Discovery projection holds W11's catalogue (O-5);
3. no W9 genesis exists in the replayed legacy projection;
4. the catalogue stream is at version 0;
5. the catalogue, annex, bootstrap contract and envelope bytes re-hash to `ACCEPTED`;
6. the catalogue's row set is LR-001 to LR-061, and its `owner_row_multiset_hash` equals the envelope's;
7. every catalogue row has a route in the legacy route registry, or a recorded exclusion.

The replay reducer refuses a second genesis and a payload that differs from `ACCEPTED`. The revision import has the
same guards and is inert in WP9.2, as P-072 item 5 says.

### 5.3 The Gate 6 store refusal

As 06v WP9.2 and §2.6 specify: read the target manifest with `load_store_manifest_unbound`, refuse with the dedicated
reason code `w9_gate6_store_refused` when `store_identity` equals the frozen value, and only then bind with
`load_store_manifest`. The genesis payload's `refused_store_identities` holds the frozen identity, so the refusal is
also part of the accepted payload. W9-T20 uses a scratch store whose 1.0.0 manifest carries the frozen identity
(06v §2.6), at a path that is not the Gate 6 store's.

### 5.4 Reducers

`research_system/legacy/replay/` holds the reducers and transaction contracts. The invariants are 06v's:
- only the W9 §8.2 transitions: `legacy_owned → successor_owned`, `legacy_owned → closed_reference`,
  `successor_owned → closed_reference`; `successor_owned → legacy_owned` is refused (W9-T5);
- supersession is acyclic;
- a `legacy-paper-root` that names its own transition event, a recovery Decision that names its recovery root, or any
  cycle among root, mapping, transition and recovery Decision is refused (W9-T21, reducer half);
- a restricted-kind source never carries a frozen-copy ref (W9-T11, store half).

The transaction contract for each catalogue row is generated from the accepted catalogue's `ordered_events`, as W11's
are from its catalogue, so a row's write set cannot drift from the accepted bytes.

## 6. CLI

A new `ars legacy` group, on the `cli.py` group pattern, with read-only `status` (genesis present, catalogue identity,
row and event counts) and `show <id>`. Both rebuild the legacy projection from the bound store and write nothing. The
group joins `main`'s error set. Mutating subcommands come with their packages.

## 7. Tests

| Test | What it shows |
|---|---|
| Shared replay | A scratch store holding W11 genesis, W9 genesis, one W9 observation and one generic command replays through `replay`, `rebuild_projection`, `replay_discovery` and `verify_restore_before_writer_lease`'s replay |
| Its negative control | The predicate removed: the observed refusals of §2.2 |
| Site 3's control | The `continue` branch removed: "unsupported Discovery event" |
| Consumer test | The four positive-equality consumers leave W9 events out (C4) |
| C1 to C3 | A missing command row; a W2-typed event without its producer binding; a top-level `W11:OR-` reference. Each is refused |
| `LEGACY_COMMAND_TYPES` | Equals the accepted catalogue's command set |
| Genesis negatives | A second genesis; the wrong stream version; tampered catalogue, annex, contract or envelope bytes; a missing W11 genesis; a catalogue row with no route and no recorded exclusion; an envelope whose external refs differ (§4.2) |
| W9-T20 | The frozen Gate 6 identity is refused before binding |
| W9-T5, W9-T21 (reducer), W9-T11 (store) | The reducer invariants of §5.4, on forged ledgers |
| W11 unchanged | The 59/21/1 partition and every W11 pin, run unchanged |

## 8. D-4 at the code PR

The code PR changes protected identities, so Stephen re-accepts, at exact bytes and as they stand in the merge-queue
entry:
- the runtime-binding census row set and digest (+2 rows under owner point A (a));
- the 06h manifest YAML;
- the append-site classification (`legacy_command_producer`);
- any changed tree ID (none expected: no core command or event schema changes);
- the T2 validator expectations and seal, if they read the census.

Under owner point D (a), D-4 applies at WP9.2-3. WP9.2-1 and WP9.2-2 change no protected identity; they carry the O-3
contract acceptance and the envelope's review instead.

## 9. Owner points

| Point | Question | Recommendation |
|---|---|---|
| A | Which runtime-binding rows WP9.2 adds | (a) Genesis and revision import only; the predicate covers all 12 |
| B | How the envelope cites the out-of-store review and decision | (a) Deterministic external refs, re-derived by a test |
| C | The `owner_row_multiset_hash` row set (i-3) | The catalogue's 24-field rows |
| D | How the contract amendment, the envelope and the runtime land, given that each names the previous one's main commit | (a) Three PRs: contract (then O-3), envelope, runtime |

## 10. Stop rules (06v §8) checked

- An interface in §2.8 resolves differently: U-7 resolves as assumed (§2.5), with two corrections to 06v's text
  (§2.4) that do not change the design.
- A W11 pin would change: none does.
- The shared-replay edit cannot be confined, or reuses an existing partition value: it is confined, and `legacy` is
  new.
- A test needs live legacy, vault or restricted bytes: none does.
- A command would write a legacy file or the Gate 6 store: genesis writes only to the bound scratch store, and refuses
  the Gate 6 identity.
- A protected identity changes without D-4: §8 lists them.
