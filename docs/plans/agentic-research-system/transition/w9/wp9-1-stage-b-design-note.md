# WP9.1 stage B design note: the W9 command set and the catalogue row shape

**Date:** 2026-10-24<br>
**Status:** Draft, revision 3, for the reviewer's narrow confirmation. It reconciles the review
`reviews/wp9-1-stage-b-note-review-0cf8acd3-2026-10-24.md` and the re-review
`reviews/wp9-1-stage-b-note-re-review-479745fc-2026-10-24.md` (see
`reviews/wp9-1-stage-b-note-reconciliation-2026-10-24.md`), under Stephen's decisions P-071, P-072 and P-073. Nothing
in it is materialized.<br>
**Package:** 06v WP9.1, stage B (P-069 item 1), in two steps, B1 and B2 (P-072 item 6). Stage A is merged as
`5d325c5b` (PR #394).<br>
**Authority:** P-065 (WP9.0, WP9.1); 06v WP9.1 "Catalogue"; W9 §§4.4, 4.5, 5.2–5.5, 7.3, 8, 9, 11.2, 12, 13, 14 and 17<br>
**Normative owner annex:** `transition/w9/wp9-1-catalogue-owner-annex.yaml`, 61 rows (§3)<br>
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
3. **Three Stephen Decisions that write no W9 record** but gate rows that do:
   - the paper-root recovery Decision (W9 §13.1);
   - the adoption reviewer-eligibility Decision (W9 §11.2; P-073 item 3);
   - the integration-pilot outcome Decision (W9 §14.3; P-073 item 3).
4. **The catalogue's own import rows:** the genesis, and an inert revision import (P-072 item 5).

Not W9 commands, because they live elsewhere:
- the §4.4 detectors (W9-T7, W9-T19) are WP9.5 tools;
- the successor-side guards (W9-T10, W9-T12, and the use-time re-hash that requests `RecordAdoptionUseMismatch`) are
  WP9.7 guards on existing W2 commands;
- the read-only projection rebuild (O-16) is a projector.

The later-gate actions stay deferred to a reviewed catalogue revision (P-071 item 4): writer revocation, the bus
non-import inventory, file-level closure, cutover, retirement and manual-mode imports.

## 2. The authority flow

A record whose schema carries a review or a Decision is created in five steps, all on the W9 append site:

| Step | Command (payload discriminant `…/<kind>`) | Submitter | Event and binding |
|---|---|---|---|
| 1 | `ProposeLegacyRecord` | the content's proposer (W9 §8.6) | `E:<kind>-proposed`. It holds the full proposed content, its pre-assigned `obj_` ID, and the pre-assigned `rev_` and `dec_` IDs it will cite. For a closed-reference batch it also holds every ownership record the resolution will emit |
| 2 | `RequestW9AuthorityReview` | migration analyst | `W2:ReviewRequested`. The new review's ID is the proposal's pre-assigned `rev_` ID, and it names the reviewer |
| 3 | `RecordW9AuthorityReview` | the named reviewer, and only that reviewer | `W2:ReviewVerdictRecorded` on the proposal's current hash |
| 4 | `ProposeW9AuthorityDecision` | migration analyst | `W2:DecisionProposed`, with the pre-assigned `dec_` ID |
| 5 | `ResolveW9AuthorityDecision` | Stephen | `W2:DecisionResolved`, then `E:<kind>-recorded`, in one transaction (as W11's OR-127 and OR-133 emit their acceptance event) |

**Same bytes, no self-hash.** The review and the Decision bind the proposal's ID and content hash. The proposal binds
their IDs only as pre-assigned strings, so no hash depends on itself. G5 requires the written record's review and
Decision refs to be exactly those pre-assigned IDs, and W9-C23 refuses a resolution whose refs or bytes differ from
the proposal. A closed-reference resolution refuses if the ownership records it computes at commit differ from the
ones the proposal lists (LR-016, LR-020).

**Variants of the flow:**
- Records with a Decision but no review skip steps 2 and 3. These are the path registration and the three
  Decision-only rows of §1 item 3.
- The light inventory uses steps 1 to 3 as an independent reproduction (contract §7), then `RecordLegacyLightInventory`.
- An observation, an ordinary paper root, a citation status and a use-time mismatch are recorded directly by their
  actor.

**Naming (P-073 item 2).** The resolving command is `ResolveW9AuthorityDecision`. `ResolveDecision` already belongs to
both the generic W2 command set (`service.py:232`) and Discovery's (`discovery/commands.py:41`). U-7's `legacy`
command-type predicate needs a name of its own.

## 3. The owner annex and the row shape

`transition/w9/wp9-1-catalogue-owner-annex.yaml` is the normative expected side. It holds:
- `global_preconditions` G1 to G5, each with its scope;
- `suspension_rule`;
- `derivation_rules`;
- `catalogue_tests`: W9-C01, W9-C03 and W9-C11, the transcription tests, and W9-C20 to W9-C25, the behavioural
  negative controls (P-073 item 1);
- 61 `rows`.

The stage B verifier, `tools/verify_w9_materialization.py` (P-072 item 7), reads the annex blob at its pinned commit.
It derives each expected catalogue row from the annex by `derivation_rules`, and its tests compare row for row (W9-C01,
W9-C03), as W11's verifier does (`tools/verify_w11_materialization.py:539-579`).

**Catalogue row fields** (24; widened from stage A's 9 in B1):

| Field | Required | Source |
|---|---|---|
| `owner_row_id` (`LR-nnn`) | yes | annex |
| `command_type` | yes | annex |
| `payload_discriminant` | yes | annex; `/` separates a variant |
| `logical_key` | yes | derived: equal to `payload_discriminant` |
| `record_schema_id` | yes | annex. The `ars://legacy/` record the row creates or works on |
| `record_schema_version` | yes | annex |
| `eligible_actor` | yes | annex. The **submitter**, from the closed set `migration_analyst`, `membership_author`, `observer`, `independent_reviewer`, `stephen`, `operator`, `system_guard` |
| `requester` | nullable | annex. Null where the submitter is self-initiated |
| `resolver` | yes | annex: `stephen` or `none` |
| `authority_subject` | yes | annex. What the exact-subject grant binds (G4) |
| `preconditions` | yes | annex. The row's own list. G1 to G5 apply by their stated scope and are not repeated |
| `ordered_events` | yes | annex. Each entry is `{event, multiplicity, condition}`: the event is an `E:` or `W2:` token; multiplicity is `1` or `0..n` |
| `affected_streams` | yes | annex. Per-record streams, plus a kind index where one exists |
| `complete_write_set` | yes | derived |
| `projection_targets` (`P:`) | yes | annex |
| `reducer` (`U:`) | yes | annex |
| `receipt_identity` | yes | derived |
| `binding_tests` | yes | annex. W9 §17 tests (`W9-Tn`) and behavioural catalogue tests (`W9-C2n`) |
| `w9c_only_reason` | nullable | annex. Required when the row has no W9-T test: `authority_flow_step` or `discharge_no_w9_test`. Such a row must also bind at least one W9-C2x test (P-073 item 1) |
| `pilot_promotion_fixtures` | yes, may be empty | annex. `{fixture_id, when}` |
| `positive_test_identity` | yes | derived |
| `negative_mutation_test_identity` | yes | derived |
| `retry_test_identity` | yes | derived |
| `owner_annex_ref` | yes | derived. It replaces W11's `file_observation_ref`. `source_refs` stays in the annex as provenance |

**Schema changes in B1:**
- the catalogue row widens to these fields;
- the `ordered_events` entry shape changes, and its token may be `E:` or `W2:`;
- `binding_tests` admits `W9-C2n`;
- `membership_author` joins the actor set;
- `legacy-adoption-use-mismatch` is added as a 14th record;
- `import-accepted-w9-catalogue-revision` is added as a bootstrap schema.

All of these are made through `tools/w9_schema_gen.py`, with stage A's test widened to match.

## 4. Decisions applied

- **Ownership (P-072 item 2).** LR-020 emits `E:legacy-ownership-transitioned-recorded` (`0..n`) only for an
  accepted whole-file observation of a `legacy_owned` file. One event name now serves every ownership record (LR-020,
  LR-054, LR-055). An item observation never moves its file. The ownership flow (LR-050 to LR-055) refuses
  `legacy_owned → closed_reference` at the proposal (LR-050, W9-T5, W9-C24).
- **Suspension (P-072 item 3).** It is projected by `P:legacy-adoption-status` from three inputs:
  - a later observation of the adoption's source (LR-015);
  - a supersession of a record it relies on (LR-060);
  - a recorded use-time mismatch (LR-061).

  `suspension_rule` defines "source" (the registration plus the adoption's selector) and "relies on" (its
  observation, that observation's closed-reference acceptance, or the adoption itself).
- **The adoption bar (P-072 item 4; P-073 item 3).**
  1. Stephen resolves a reviewer-eligibility Decision (LR-024, LR-025). It names the session and its
     operator-recorded model family and version, role profile and context grade (W9 §11.2 a–c).
  2. The adoption's review request must name that session (LR-026).
  3. The verdict's `reviewer_model_metadata` must match the Decision (LR-027).
  4. Fixtures are listed per record-emitting row, with their W9 §12.3 conditions.
- **The integration pilot (P-073 item 3).** Stephen's outcome Decision, of kind `result_interpretation` (LR-021,
  LR-022), is what three rows read:
  - LR-016's first-batch and no-further-batch rules;
  - LR-035's ordinary root;
  - LR-054's paper-root column.
- **The detectors' controls.** LR-003 reads the control-output hash files that D-5 places in the W9 evidence area,
  at the binding's `git_head`.
- **Variants.** Paper roots (LR-035; LR-036 to LR-038) and the ownership resolutions (LR-054, LR-055) are split.
- **O-31 (P-073 item 4).** Stephen's reading: the full-path rows (LR-035 to LR-055) are built and tested, and refuse
  until their §4.5 gate. No paper-root transition runs under 06v.

## 5. W9 §17 tests against rows

| Test | Rows | Note |
|---|---|---|
| T1 | LR-015, LR-020, LR-029 | |
| T2, T3 | LR-010, LR-015 | |
| T4, T13 | LR-015 | |
| T5 | LR-050, LR-054, LR-055 | LR-050 refuses `legacy_owned → closed_reference` |
| T6 | LR-015, LR-020, LR-029, LR-044, LR-054, LR-055 | Windows (O-33) |
| T8 | LR-029 | Legacy side; WP9.7 guards the successor side |
| T9 | LR-015, LR-029, LR-060, LR-061 | Suspension is projected, including an unchanged-blob re-observation |
| T11 | LR-005, LR-015 | |
| T14 | LR-060 | |
| T15 | LR-037, LR-038 | |
| T16 | LR-020 | |
| T17 | LR-039, LR-044, LR-054 | |
| T20 | LR-001, LR-002, and G1 on every row | |
| T21 | LR-035, LR-037, LR-038, LR-044, LR-049, LR-054 | LR-037's Decision never names the recovery root |
| T22 | LR-014 | |
| T7, T19 | none | WP9.5 tools |
| T10, T12 | none | WP9.7 guards |
| T18 | none in v1 | File closure is deferred (P-071 item 4). In v1, T18 is a tool-level test of the O-36 inventory and closure tool |
| T23 | none in v1 | A unit test of WP9.6's importer. The manual-mode import row comes with the deferred revision |

The behavioural catalogue tests W9-C20 to W9-C25 bind the rows that exercise them: requests, verdicts, decision
proposals, resolutions, ownership proposals and content proposals.

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
- **WP9.2's runtime census** grows by the annex's distinct command types, not by its row count (re-review I-2).
  WP9.2 also names the payload schema for the W2-typed events, and puts the `legacy` predicate ahead of
  `shared_event_partition`'s event-type sets (re-review I-3).

## 7. Points still open

**`anyRef` kinds.** These are deferred by name to WP9.2's preparers:
- the signature record;
- a `pilot_promotion` evidence ref;
- an adoption's successor use;
- the envelope's independent observation.

The inventory's independent reproduction is a W9 review (`rev_`; LR-012, LR-013).
