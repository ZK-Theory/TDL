# WP9.1 stage B design note: the W9 command set and the catalogue row shape

**Date:** 2026-10-24<br>
**Status:** Draft, revision 1, for Stephen's scope decisions and then an independent review. Nothing in it is
materialized.<br>
**Package:** 06v WP9.1, stage B (P-069 item 1). Stage A is merged as `5d325c5b` (PR #394).<br>
**Authority:** P-065 (WP9.1); 06v WP9.1 "Catalogue"; W9 §§5.2, 5.3, 8, 9, 12.1, 13 and 17<br>
**Implementation authority:** None. This note proposes the rows that stage B's catalogue
(`.research-system/evals/expected/w9-legacy-integration-v1.json`) will hold. Stephen accepts the catalogue at an exact
identity, and that is where stage B ends (O-8). After acceptance, every change to a row is a new catalogue identity and
a new acceptance.

## 1. The gap this note closes

06v WP9.1 says the catalogue "has one row per W9 command, with IDs `LR-001` onward … Each row lists the command, actor
class, preconditions, events, touched streams and binding tests." Neither W9 nor 06v lists the W9 commands. The only
one named is `AdoptLegacyAuthority` (W9 §9). Two more are named in 06v:
- `ImportAcceptedW9CatalogueGenesis`, which emits `W9CatalogueGenesisImported` (WP9.2);
- the record kinds' preparers (WP9.3 to WP9.6).

This note derives the command set from W9's records and procedures, so that the set is reviewed before it is pinned.

**Derivation rule.** There is one command per W9 §5.2 record kind, because each record is created by exactly one
command. The genesis import is added. Decisions and reviews are not W9 commands. Stephen's Decisions (`dec_`) and
independent reviews (`rev_`) are recorded through W2's existing decision and review commands, and W9 records cite them
(stage A's typed references). So no row records a Decision or a review.

## 2. Row shape, against W11's catalogue

W11's accepted catalogue (`.research-system/evals/expected/w11-portfolio-discovery-v1.json`, blob `8d588185`) has 81
rows, each with the same 19 fields. Stage A's `w9-schema-catalogue-content` row (`OWNER_ROW`) has 9. The proposal is to
follow W11's shape, adapted where W9 differs:

| W11 field | Proposed W9 field | Note |
|---|---|---|
| `owner_row_id` (`OR-nnn`) | `owner_row_id` (`LR-nnn`) | Kept (06v) |
| `command_type` | `command_type` | Kept |
| `logical_key`, `payload_discriminant` | `logical_key`, `payload_discriminant` | Kept; kebab-case of the command |
| `schema_id`, `schema_version` | `record_schema_id`, `record_schema_version` | The `ars://legacy/` record the command creates |
| `eligible_profile` (free text) | `eligible_actor` (closed enum) plus `requester` | W9 §8.6 roles, closed (stage A's enum, extended by SB-Q5) |
| — | `resolver` (`stephen` or `none`) | W9 §8.6: Stephen resolves; P-005 |
| `authority_subject` | `authority_subject` | What the scoped grant binds |
| `preconditions` | `preconditions` | Each cites its W9 or 06v source |
| `ordered_events` (`E:kebab`) | `ordered_events` | Kept |
| `complete_write_set` | `complete_write_set` | Kept: the events and every touched stream |
| `affected_streams` | `affected_streams` | Kept |
| `projection_targets` (`P:`) | `projection_targets` | Kept |
| `reducer` (`U:`) | `reducer` | Kept |
| `receipt_identity` (`R:`) | `receipt_identity` | Kept |
| `positive_test_identity`, `negative_mutation_test_identity`, `retry_test_identity` | Same three, `W9-C01`, `W9-C03` and `W9-C11` style | The catalogue verifier's generic tests, as W11's `W11-T01`, `T03` and `T11` |
| — | `binding_tests` (`W9-T<n>`) | W9 §17 tests the row's behaviour must pass (stage A field) |
| `file_observation_ref` | `source_refs` | W11's rows came from an observed owner table in W11 itself. W9 has no owner table, so each row cites the W9 and 06v sections it derives from (§1 rule) |

Widening stage A's `OWNER_ROW` to this shape changes the catalogue-content schema and needs stage A's generator and
test. That is still allowed, because nothing is pinned until the catalogue is accepted (SB-Q1).

## 3. Proposed rows

Throughout: **A** is the migration analyst (requester and proposer), **O** the observer, **R** the independent
reviewer, and **S** Stephen (W9 §8.6). Every command refuses an actor who produced the item for the O and R roles
(06v WP9.2), and refuses the Gate 6 store (W9-T20, before binding). "Window" means the W9 §8.3 rule: the blob, or the
item hash, is re-hashed at commit and an unchanged value is required.

| Row | Command | Record | Actor / resolver | Key preconditions | Ordered events | Binding tests |
|---|---|---|---|---|---|---|
| LR-001 | `ImportAcceptedW9CatalogueGenesis` | bootstrap genesis input | operator holding the exact verified bootstrap grant / none (Stephen's acceptance is the external envelope) | Envelope current and re-hashed; the accepted W11 catalogue's genesis replayed in the store (O-5); store identity not Gate 6; no prior W9 genesis; stream version 0; row-set and route-partition checks (06v WP9.2) | `E:w9-catalogue-genesis-imported` | W9-T20 |
| LR-002 | `RegisterLegacyPath` | `legacy-path-registration` | A / S (`registration_decision_ref`) | W9 genesis present; one physical identity, read handle-bound; role rules (writers, `CONVENTIONS.md`, roots, restricted suffix; stage A); no live registration of the same physical identity | `E:legacy-path-registered` | W9-T10, W9-T11 |
| LR-003 | `RecordFieldFamilyMembership` | `legacy-field-family-membership` | membership author (SB-Q5) / S (`acceptance_decision_ref`) | Author excluded per template §2; `applies_to` bytes re-hashed equal; review on the table's SHA-256; Stephen's acceptance of those bytes | `E:legacy-field-family-membership-recorded` | W9-T2, W9-T3 |
| LR-004 | `RecordLegacyLightInventory` | `legacy-light-inventory` | O / none | Registration live; read under `w9-segmentation/1.0.0`; independent reproduction by a distinct session; no blocker row may be dropped | `E:legacy-light-inventory-recorded` | W9-T18, W9-T22 |
| LR-005 | `ObserveLegacyRecord` | `legacy-observation` | O / none | Registration live; handle-bound read in its window; JSON families from an accepted membership table; item selector bound to an inventory row; W0 class from a signed W0 record (O-27); restricted kinds carry no frozen copy | `E:legacy-record-observed`; then `E:legacy-adoption-suspended` for each adoption whose source blob changed (SB-Q3) | W9-T1, T2, T3, T4, T6, T9, T11, T13 |
| LR-006 | `AcceptClosedReferenceBatch` | `legacy-closed-reference-acceptance` | A requests / S | §4.5 column; Stephen's W0-D1 signature (§8.5 item 2); independent review on current hashes; per-item `pilot_promotion`; threshold and governing-record hashes anchored before the batch; every item in its window | `E:legacy-closed-reference-accepted`; and the light-path ownership change (SB-Q2) | W9-T1, W9-T6, W9-T16 |
| LR-007 | `AdoptLegacyAuthority` | `legacy-adoption-decision` | A requests / S | The source's closed-reference acceptance; families and signed classes; intended successor use; qualifiers to discharge; no blocking qualifier for that use (W9 §9) | `E:legacy-authority-adopted` | W9-T8, W9-T9 |
| LR-008 | `RecordLegacyDischarge` | `legacy-discharge-relation` | A requests; R reviews / S (under W0-D1) | A successor result artefact; the legacy open item named; reviewer independent of the result's producer | `E:legacy-item-discharged` | none in W9 §17 (SB-Q6) |
| LR-009 | `CreateLegacyPaperRoot` | `legacy-paper-root` | A requests / S | A P01 key bound to its root path. A recovery root names its predecessor and a recovery Decision that came first (W9 §13.1) | `E:legacy-paper-root-created` | W9-T15, W9-T21 |
| LR-010 | `RecordPaperCitationStatus` | `legacy-paper-citation-status` | R derives the cited-family set / S | The root exists; the frozen cited-family hash; every family adopted or marked unadopted (W9 §12.1) | `E:legacy-paper-citation-status-recorded` | W9-T17 |
| LR-011 | `RecordLegacySourceInventory` | `legacy-source-inventory` | O; R reviews / S | The root's registration; every row bound to an accepted observation; the window held | `E:legacy-source-inventory-recorded` | W9-T17, W9-T21 |
| LR-012 | `ProposeLegacyTransitionMapping` | `legacy-transition-mapping` | A proposes; R reviews / S | The accepted source inventory; the target paper root; the mapped rows a subset of the inventory | `E:legacy-transition-mapping-recorded` | W9-T21 |
| LR-013 | `TransitionLegacyOwnership` | `legacy-ownership-transitioned` | A requests; R reviews / S | Only W9 §8.2's three transitions; to `successor_owned`: the accepted mapping, the root, the citation status complete and the §4.5 column; the window held | `E:legacy-ownership-transitioned` | W9-T5, W9-T17, W9-T21 |
| LR-014 | `SupersedeLegacyRecord` | `legacy-record-supersession` | A requests; R reviews / S | The target is one of P-070's four kinds; a reason; no cycle; current use re-points | `E:legacy-record-superseded`; then `E:legacy-adoption-suspended` for each adoption relying on the superseded record | W9-T14 |

**Streams, projections, reducers and receipts** follow one pattern, which the catalogue spells out per row:
- each record kind has its own stream;
- a registry projection exists per kind (`P:legacy-<kind>`);
- the reducer is named after the record (`U:legacy-<kind>`);
- a receipt is named after the command (`R:<logical-key>`).

LR-005, LR-006, LR-013 and LR-014 also touch the registration's ownership or adoption state (see SB-Q2 and SB-Q3).

**Not W9 commands.** Each of these belongs elsewhere:
- the §4.4 detectors (W9-T7, W9-T19) are tools (WP9.5);
- the successor-side guards (W9-T10's RegisterArtefact half, W9-T12's dispatch guard) are WP9.7 guards on existing W2
  commands;
- the read-only projection rebuild (O-16) is a projector, not a command.

## 4. Scope questions for Stephen

- **SB-Q1, row shape.** Adopt §2's W11-derived row shape, which widens stage A's `OWNER_ROW` from 9 to about 20 fields
  before the catalogue is pinned? The alternative is to keep stage A's 9 fields and carry streams, projections,
  reducers and receipts only in WP9.2's code. **Recommendation: adopt it.** The catalogue is the accepted contract
  that WP9.2 implements, as W11's was.
- **SB-Q2, light-path ownership.** W9 §8.2 lists `legacy_owned → closed_reference` as a transition, and stage A's
  `legacy-ownership-transitioned` admits it with a null mapping. Does the closed-reference batch acceptance (LR-006)
  emit each item's ownership change itself, or must each item then take its own `TransitionLegacyOwnership` (LR-013)?
  **Recommendation: LR-006 emits one `E:legacy-ownership-transitioned` per item, in the same transaction.** That
  avoids a window between acceptance and ownership.
- **SB-Q3, adoption suspension.** W9 §9 item 5 says a re-observation, a new qualifier or a supersession suspends an
  adoption until it is re-resolved. Is suspension an event emitted by the command that causes it (LR-005, LR-014), or
  its own command? **Recommendation: an event emitted by the causing command.** Re-resolution is a new
  `AdoptLegacyAuthority` (LR-007).
- **SB-Q4, later-gate actions.** W9 §13.3 and §13.1 also describe:
  - writer revocation for `.apm/`;
  - the bus's non-import inventory record;
  - the file-level inventory and closure;
  - cutover and retirement records;
  - manual-mode edit imports (O-35, W9-T23).

  Include them now as inert rows, or leave them to a later catalogue revision, which would be a new identity and a
  new acceptance? **Recommendation: leave them to a later revision.** Their gates (W9 §4.5) are far off, and pinning
  their shape now would freeze guesses.
- **SB-Q5, actor classes.** Stage A's `eligible_actor` enum is: `migration_analyst`, `observer`,
  `independent_reviewer`, `stephen`, `operator` and `system_guard`. The membership table's author (template §2) is
  none of these. **Recommendation:** add `membership_author`, and add a `requester` field so that the A-requests,
  S-resolves rows are explicit.
- **SB-Q6, rows with no W9 §17 test.** LR-008 (discharge) has no W9 binding test, and stage A's schema requires at
  least one. **Recommendation:** allow catalogue-level tests (`W9-C…`) to satisfy the minimum, and name the stage B
  verifier's positive and negative-mutation tests for the row. Adding a new W9 §17 test would mean editing W9, which
  is accepted.

## 5. What stage B then materializes

After Stephen's answers, stage B will produce:
- the catalogue, with every row derived from §3 and every schema source row pinned at `5d325c5b`;
- the acceptance-envelope instance;
- a materialization verifier: the owner-row count and range hash; row-ID uniqueness; every binding test named in W9
  §17 or the `W9-C…` set; every fixture within S-001 to S-017 and F-001 to F-038 (stage A note §3);
- any `OWNER_ROW` widening, made through `tools/w9_schema_gen.py` and stage A's test.

Stage B then goes to an independent review, then to Stephen's acceptance of the catalogue at an exact identity (O-8).
`accepted_w9.py` stays in WP9.2 (P-066 item 2).
