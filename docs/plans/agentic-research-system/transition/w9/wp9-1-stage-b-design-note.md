# WP9.1 stage B design note: the W9 command set and the catalogue row shape

**Date:** 2026-10-24<br>
**Status:** Draft, revision 2, for re-review. It reconciles the review
`reviews/wp9-1-stage-b-note-review-0cf8acd3-2026-10-24.md` (see `reviews/wp9-1-stage-b-note-reconciliation-2026-10-24.md`)
under Stephen's decisions P-071 and P-072. Nothing in it is materialized.<br>
**Package:** 06v WP9.1, stage B (P-069 item 1), in two steps, B1 and B2 (P-072 item 6). Stage A is merged as
`5d325c5b` (PR #394).<br>
**Authority:** P-065 (WP9.0, WP9.1); 06v WP9.1 "Catalogue"; W9 §§4.4, 4.5, 5.2–5.5, 7.3, 8, 9, 11.2, 12, 13, 14 and 17<br>
**Normative owner annex:** `transition/w9/wp9-1-catalogue-owner-annex.yaml`, 57 rows (§3)<br>
**Implementation authority:** None. This note and its annex define the rows that stage B's catalogue
(`.research-system/evals/expected/w9-legacy-integration-v1.json`) will hold. Stephen's O-8 acceptance names the
catalogue and the annex by main commit, blob and SHA-256 (P-072 item 6). After that, every row change is a new
catalogue identity and a new acceptance.

## 1. The gap, and the derivation rule

06v WP9.1 requires one catalogue row per W9 command, but neither W9 nor 06v lists the commands. The rows are derived
here as follows:

1. **One record-emitting row per W9 record kind.** That is stage A's 13 kinds, plus `legacy-adoption-use-mismatch`
   (P-072 item 3).
2. **W9-path review and decision rows** for every record that carries a review or a Decision (P-072 item 1). Generic
   W2 `RequestReview` refuses a subject that is not a replayed generic stream (`research_system/command/service.py:3713-3720`),
   and W9 records replay into the separate `legacy` partition (06v WP9.2, U-7). W11 met the same constraint with its
   own rows (`discovery/commands.py:14-44`; OR-122 to OR-133); W9 follows that pattern.
3. **The catalogue's own import rows:** the genesis, and an inert revision import (P-072 item 5).

Not W9 commands, because they live elsewhere:
- the §4.4 detectors (W9-T7, W9-T19) are WP9.5 tools;
- the successor-side guards (W9-T10, W9-T12, and the use-time re-hash that requests `RecordAdoptionUseMismatch`) are
  WP9.7 guards on existing W2 commands;
- the read-only projection rebuild (O-16) is a projector.

The later-gate actions stay deferred to a reviewed catalogue revision (P-071 item 4): writer revocation, the bus
non-import inventory, file-level closure, cutover, retirement and manual-mode imports.

## 2. The authority flow

A record whose schema carries a review or a Decision is created in five steps, all on the W9 append site:

| Step | Command (payload discriminant `…/<kind>`) | Submitter | Event |
|---|---|---|---|
| 1 | `ProposeLegacyRecord` | the content's proposer (W9 §8.6) | `E:<kind>-proposed`, holding the full proposed content, its pre-assigned `obj_` ID and the pre-assigned `rev_` and `dec_` IDs it will cite |
| 2 | `RequestW9AuthorityReview` | migration analyst | `W2:ReviewRequested`, on the proposal's ID and exact content hash |
| 3 | `RecordW9AuthorityReview` | independent reviewer | `W2:ReviewVerdictRecorded` |
| 4 | `ProposeW9AuthorityDecision` | migration analyst | `W2:DecisionProposed`, with the pre-assigned `dec_` ID |
| 5 | `ResolveW9AuthorityDecision` | Stephen | `W2:DecisionResolved`, then `E:<kind>-recorded`, in one transaction (as W11's OR-127 and OR-133 emit their acceptance event) |

Records that carry a Decision but no review skip steps 2 and 3: the path registration, and the paper-root recovery
Decision. The pre-assigned IDs mean no hash depends on itself. The record is written only by step 5, so a reviewed
proposal can never be committed with different bytes.

The light inventory uses steps 1 to 3 as an independent reproduction (contract §7), then `RecordLegacyLightInventory`.
An observation, an ordinary paper root, a citation status and a use-time mismatch are recorded directly by their
actor.

**Naming.** The resolving command is `ResolveW9AuthorityDecision`, not `ResolveDecision`. Discovery's command set
already holds `ResolveDecision` (`discovery/commands.py:41`), and U-7's `legacy` command-type predicate must not
overlap Discovery's set. Otherwise one command type would sit in two partitions (§7, open point 2).

## 3. The owner annex and the row shape

`transition/w9/wp9-1-catalogue-owner-annex.yaml` is the normative expected side (review M-2). It holds:
- **global preconditions G1 to G5**, which bind every row (G2 binds every row but LR-001; G5 binds every row Stephen
  resolves);
- **57 rows**, each with every field below that is not mechanically derived.

The stage B verifier, `tools/verify_w9_materialization.py` (P-072 item 7), reads the annex blob at its pinned commit.
It derives each expected catalogue row from the annex, and its tests compare row for row (W9-C01, W9-C03), as W11's
verifier does (`tools/verify_w11_materialization.py:539-579`).

**Catalogue row fields** (23; widened from stage A's 9 in B1):

| Field | Required | Source |
|---|---|---|
| `owner_row_id` (`LR-nnn`) | yes | annex |
| `command_type` | yes | annex |
| `payload_discriminant`, `logical_key` | yes | annex. The two are equal; `/` separates a variant |
| `record_schema_id`, `record_schema_version` | yes | annex. The `ars://legacy/` record the row creates or works on |
| `eligible_actor` | yes | annex. The **submitter**, from the closed set `migration_analyst`, `membership_author`, `observer`, `independent_reviewer`, `stephen`, `operator`, `system_guard` |
| `requester` | nullable | annex. Null where the submitter is self-initiated (an observer's or reviewer's own step, or the genesis) |
| `resolver` | yes | annex: `stephen` or `none` |
| `authority_subject` | yes | annex. What the exact-subject grant binds (G4) |
| `preconditions` | yes | annex. Each item cites its source |
| `ordered_events` | yes | annex. `E:` events or `W2:` events; `x0..n` marks a conditional, repeated event |
| `affected_streams` | yes | annex. Per-record streams, plus a kind index where one exists |
| `complete_write_set` | yes | derived: `ordered_events` then `affected_streams` |
| `projection_targets` (`P:`), `reducer` (`U:`) | yes | annex |
| `receipt_identity` | yes | derived: `R:<logical_key>` |
| `binding_tests` | may be empty | annex. W9 §17 tests |
| `w9c_only_reason` | nullable | annex. Required when `binding_tests` is empty: `authority_flow_step` or `discharge_no_w9_test` (§7, open point 1) |
| `pilot_promotion_fixtures` | may be empty | annex. `{fixture_id, when}`, where `when` is null or the W9 §12.3 condition |
| `positive_test_identity`, `negative_mutation_test_identity`, `retry_test_identity` | yes | derived: `W9-C01-LR-nnn`, `W9-C03-LR-nnn-owner-row-mutation`, `W9-C11-LR-nnn` |
| `owner_annex_ref` | yes | derived: the annex's commit, blob and SHA-256, plus the SHA-256 of the row's canonical JSON. This is the analogue of W11's `file_observation_ref`, and it replaces revision 1's free-text `source_refs`, which stays in the annex as provenance |

**Schema changes in B1:**
- the catalogue row widens to these fields;
- event names may be `E:` or `W2:`;
- `membership_author` joins the actor set;
- `legacy-adoption-use-mismatch` is added as a 14th record;
- `import-accepted-w9-catalogue-revision` is added as a bootstrap schema.

All of these are made through `tools/w9_schema_gen.py`, with stage A's test widened to match.

## 4. Decisions applied

- **Ownership (P-072 item 2).** The closed-reference resolution (LR-020) emits `E:legacy-ownership-transitioned`
  (`x0..n`) only for an accepted whole-file observation of a `legacy_owned` file. An item observation never moves its
  file. The ownership flow (LR-046 to LR-051) admits only `legacy_owned → successor_owned` (LR-050) and
  `successor_owned → closed_reference` (LR-051), and refuses `legacy_owned → closed_reference`.
- **Suspension (P-072 item 3).** `P:legacy-adoption-status` projects an adoption as suspended whenever one of these
  exists:
  - a later observation of its source (LR-015, on any re-observation, whatever the bytes);
  - a supersession of a record it relies on (LR-056);
  - a recorded use-time mismatch (LR-057).

  No suspension event exists. Re-resolution is a new adoption flow (LR-021 to LR-025).
- **The adoption bar (P-072 item 4).** Each record-emitting row lists its W9 §12.3 fixtures, with conditions.
  Evidence or waiver refs travel in the resolving Decision, or in the batch record (LR-020). LR-021's preconditions
  require a W9 §11.2 second-family coverage record, which Stephen checks before the adoption's review starts.
- **Preconditions (review M-3)** are added with their sources. Examples:
  - the detectors' controls watched before the first registration (LR-003);
  - the §4.5 column, the registration manifest, the frozen baselines and the membership-author exclusion (LR-015);
  - the enforcement-change rule, the reviewer-fixed applicability and the first-batch bounds (LR-016, LR-020);
  - use-scoped active adoptions (LR-035);
  - inventory completeness (LR-036);
  - D-3, active adoptions and the enumerated §4.5 paper-root column (LR-050);
  - same-kind replacement and no re-supersession (LR-052).
- **Variants (review m-4).** The ordinary and recovery paper roots are split (LR-031; LR-032 to LR-034), and so are
  the two ownership transitions (LR-050, LR-051).
- **Naming (review m-5).** No content row is named "Propose…" unless it is a proposal: the content proposal is
  `ProposeLegacyRecord`, and the Decision commits it.

## 5. W9 §17 tests against rows

| Test | Rows | Note |
|---|---|---|
| T1 | LR-015, LR-020, LR-025 | |
| T2, T3 | LR-010, LR-015 | |
| T4, T13 | LR-015 | |
| T5 | LR-050, LR-051 | Includes the refusal of `legacy_owned → closed_reference` |
| T6 | LR-015, LR-020, LR-025, LR-040, LR-050, LR-051 | Windows (O-33) |
| T8 | LR-025 | Legacy side; WP9.7 guards the successor side |
| T9 | LR-015, LR-025, LR-056, LR-057 | Suspension is projected (P-072 item 3), including an unchanged-blob re-observation |
| T11 | LR-005, LR-015 | |
| T14 | LR-056 | |
| T15 | LR-033, LR-034 | |
| T16 | LR-020 | |
| T17 | LR-035, LR-040, LR-050 | |
| T20 | LR-001, LR-002, and G1 on every row | |
| T21 | LR-031, LR-034, LR-040, LR-045, LR-050 | |
| T22 | LR-014 | |
| T7, T19 | none | WP9.5 tools |
| T10, T12 | none | WP9.7 guards (revision 1's T10 on registration is removed, review m-1) |
| T18 | none in v1 | File closure is deferred (P-071 item 4). In v1, T18 is a tool-level test of the O-36 inventory and closure tool |
| T23 | none in v1 | A unit test of WP9.6's importer. The manual-mode import row comes with the deferred revision |

## 6. What B1 and B2 produce

- **B1:**
  - the schema widening in §3, through the generator, with stage A's test widened;
  - the verifier `tools/verify_w9_materialization.py`;
  - its test `tests/research_system/contracts/test_w9_expected_catalogue.py` (P-072 item 7).

  B1 is reviewed and merged.
- **B2:**
  - the catalogue, with every schema source row pinned at B1's main commit;
  - each row's `owner_annex_ref` pinned to the annex at its main commit;
  - the verifier run green.

  B2 is reviewed, then goes to Stephen's O-8 acceptance.
- **The acceptance-envelope instance** is written at L-3 in the store, or with WP9.2's `accepted_w9.py` (P-072 item 6;
  P-066 item 2). It is not a stage B file.

## 7. Open points for the re-review and for Stephen

1. **Authority-flow rows with no §17 test.** P-071 item 6 allowed a catalogue-level `W9-C` test to meet the
   binding-test minimum for the discharge row: LR-008 in revision 1, LR-030 now. P-072 item 1's review and decision
   rows (proposal, request, review and decision-proposal steps) also have no §17 test of their own. The annex marks
   them `w9c_only_reason: authority_flow_step`. Extending P-071 item 6 to them is an owner decision. The verifier
   refuses an empty `binding_tests` without one of the two reasons.
2. **`ResolveW9AuthorityDecision`** in place of a W9 `ResolveDecision`, so that the command-type sets stay disjoint
   (§2).
3. **The `anyRef` kinds** that stage A's note left open are deferred by name to WP9.2's preparers:
   - the signature record;
   - a `pilot_promotion` evidence ref;
   - an adoption's successor use;
   - the inventory's independent reproduction, which this annex makes a W9 review, `rev_` (LR-012, LR-013);
   - the envelope's independent observation.
4. **O-31.** 06v puts paper-root transitions out of scope "for this plan's code", while assigning W9-T5, T17 and T21
   to code. The reading here is that the full-path rows (LR-031 to LR-051) are built and tested, and refuse until
   their §4.5 gate; no transition runs under this plan.
