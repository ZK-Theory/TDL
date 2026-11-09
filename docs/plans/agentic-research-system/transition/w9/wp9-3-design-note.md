# WP9.3 design note: the observation reader, selectors, inventories and acceptance

**Date:** 2026-10-28<br>
**Status:** Revision 2. It reconciles the independent review of revision 1 (`a8604641`):
`reviews/wp9-3-design-note-review-a8604641-2026-10-28.md`, on branch `review/w9-wp9-3-note` at `0dc63404`, verdict
accept with required changes (1 Blocking, 4 Major, 10 Minor, 6 Info). The change log says where each finding went.
Stephen decided every owner point at its recommended option (P-081, 2026-10-29). Revision 3 (2026-11-08) answers the
review comments on PR #411, and amends P-081 item 8 to cover the membership-table author's session. Revision 4
(2026-11-08) answers the second round, and amends P-081 item 10 to extend the boundary to W11's identity check.
Revision 5 (2026-11-08) answers Codex's third round, with no owner decision changed. Revision 6 (2026-11-08) makes a
later W0 pin's release a store binding advance (issue #415, option C), and amends P-081 item 3. Revision 7
(2026-11-08) answers a fourth round, amending P-081 items 10 and 12 and adding the O-33 reading. Revision 8
(2026-11-08) answers a fifth, amending P-081 items 3 and 12 and the O-33 addition. Revision 9 (2026-11-08) answers
a sixth, amending P-081 items 3 and 12 and the O-33 addition again. Revision 10 (2026-11-09) answers a seventh,
amending P-081 items 3 and 10 and the O-33 addition. Revision 11 (2026-11-09) answers an eighth, amending them
again. Revision 12 (2026-11-09) answers a ninth, amending P-081 items 3 and 10. Revision 13 (2026-11-09) answers a
tenth, amending P-081 item 3. Revision 14 (2026-11-09) answers an eleventh, amending P-081 items 3, 10 and 12.
Nothing in it is implemented.<br>
**Package:** 06v WP9.3 ("Observation reader, selectors, inventories and acceptance"), proposed as two PRs, WP9.3-1
and WP9.3-2 (owner point A).<br>
**Authority:** P-080 (WP9.3, note first). WP9.2 is complete: PRs #406 and #408, O-3 accepted (P-078), D-4
re-accepted at `31f675fe` (P-079).<br>
**Base:** `main` at `1f0d8281` (tree `8d8aead2`), which records P-079 and P-080 (PR #409). Every `path:line` below was
read at that commit.<br>
**Not authorized (P-080):** WP9.4 to WP9.7; live operations L-0 to L-5, including the D-7 baseline export and the real
observations, inventories and acceptances these commands will later run; creating a real store, or running genesis or
issuing a grant on one; any legacy write. Every store in this note is a scratch store that a test creates under
`tmp_path`.<br>
**Probe:** the author ran no prototype. The review probed §20's claims with 22 asserting pytest cases on in-memory
registries, reducers and payloads (review §2). Its results are cited where they bear on the design.

## 1. What this note settles

06v WP9.3 predates the stage B command set. It maps no row to a command and leaves several interfaces open. This note
settles them, so that the code has nothing left to decide:
1. the rows WP9.3 routes, the seven commands it binds, and the split (§2; owner point A);
2. every obligation carried into WP9.3, each with a disposition (§3);
3. the record identity rules: the content hash (N-2), pre-assigned refs, identity claims and streams (§4);
4. the authority flow: payloads, W2 encodings, grant subjects, review satisfaction and roles (§5);
5. the checks for each of LR-003 to LR-020, split between replay and the preparer (§6);
6. the reader (§7), the selectors and inventories (§8), and classes, qualifiers and precedence (§9);
7. the closed-reference acceptance (§10) and the inputs it reads from outside the store (§11);
8. the tools (§12), the CLI (§13), the reducers kept and changed (§14), genesis guard 8 (§15) and D-4 (§16);
9. the tests (§17), research assurance (§18), the stop rules (§19), the review probes (§20) and the owner points
   (§21).

## 2. Scope: rows, commands and the split

### 2.1 The rows

The legacy route table tags LR-003 to LR-020 `WP9.3` (`research_system/legacy/routes.py:447`). They are the five
record families 06v WP9.3 owns:

| Rows | Record | Flow (stage B note §2) |
|---|---|---|
| LR-003 to LR-005 | `legacy-path-registration` | propose, propose Decision, resolve. No review step |
| LR-006 to LR-010 | `legacy-field-family-membership` | all five steps |
| LR-011 to LR-014 | `legacy-light-inventory` | propose, request and record the reproduction review, record |
| LR-015 | `legacy-observation` | recorded directly by the observer |
| LR-016 to LR-020 | `legacy-closed-reference-acceptance`, plus its ownership records | all five steps |

No row moves between packages (WP9.2 note §3). LR-021 and LR-022, the integration-pilot outcome Decision, stay with
WP9.7. One consequence: LR-016's precondition "a batch after the first requires the integration-pilot outcome Decision
resolved as passed" cannot be met until WP9.7 routes LR-022. WP9.3's code therefore admits the first batch only, which
is the integration pilot. No later batch is authorized anyway.

### 2.2 The commands

Seven command types execute those rows: `ProposeLegacyRecord`, `RequestW9AuthorityReview`, `RecordW9AuthorityReview`,
`ProposeW9AuthorityDecision`, `ResolveW9AuthorityDecision`, `RecordLegacyLightInventory` and `ObserveLegacyRecord`.

A runtime-binding row belongs to a command type, not to a row (`research_system/schema_registry.py:209-265`; WP9.2
note §3). Binding `ProposeLegacyRecord` and the four authority-flow commands here therefore also binds them for the
WP9.4, WP9.6 and WP9.7 rows that share them: 37 rows in all (review i-3). A binding grants nothing by itself. The
runtime assigns every prepared transaction to its row with `assign_row`, replacing today's `_COMMAND_ROWS` lookup
(`legacy/runtime.py:68`, `:418-421`), and refuses a deferred row before append, as replay already does
(`research_system/legacy/replay/driver.py:139-141`). A test submits a schema-valid `ProposeLegacyRecord` for an
adoption decision (LR-023, `WP9.4`) and expects that refusal, with the store unchanged.

**Consequence for later D-4s.** After WP9.3 four W9 command types stay unbound: `CreateLegacyPaperRoot` and
`RecordPaperCitationStatus` (WP9.4), `RecordAdoptionUseMismatch` (WP9.7), and `ImportAcceptedW9CatalogueRevision`
(LR-002), which only an accepted catalogue revision's package would bind, under its own D-4 (review m-1). WP9.6's rows
use commands already bound, `CreateLegacyPaperRoot` included if WP9.4 merges first. So the packages that add census
rows become WP9.2, WP9.3, WP9.4 and WP9.7, and WP9.6 adds one only if it lands before WP9.4. 06v D-4 expected WP9.2, WP9.3, WP9.4 and WP9.6; the WP9.2
note added WP9.7 (confirmation n-3). This changes no accepted text: D-4 applies to whichever package adds a row.

### 2.3 The split (owner point A)

P-080 item 1 allows a split under 06v D-6 if the review asks for one. P-064 item 6 does not fix the split's shape,
and 06v's D-6 row suggests a reader PR and a selectors PR. This note proposes a different shape now, so that the
review can confirm or refuse it:

- **WP9.3-1: LR-003 to LR-015.** The bindings for all seven commands, which is the whole D-4 delta (§16); the reader;
  the runtime segmenter; the light-inventory builder and its reproduction mode; the membership checks; the
  observation; the record identity rules (§4), which close N-2; F-4 (§13); F-8's first limb; the reducer changes of
  §14; the mutating CLI.
- **WP9.3-2: LR-016 to LR-020.** The acceptance preparers (O-25, O-32, O-33 at acceptance, O-37); the ownership list
  and F-8's second limb (owner point E); the Computational-Log export reader and its recheck (§12.2); the `.apm/bus/`
  and `.apm/` inventories (O-19, O-36).

The reasons:
- WP9.3-2 adds no command type, so it changes no protected identity and carries no D-4. The package needs one
  re-acceptance, not two.
- The acceptance rows read three inputs that WP9.5 produces (§11.1) and are the largest test surface. Reviewing them
  apart keeps each review bounded.
- 06v D-6's own suggestion, a reader PR and a selectors PR, would split LR-015's preparer across two PRs, because an
  observation needs both.

WP9.3-1 merges first, and WP9.3-2 is cut from its main commit.

## 3. Carried obligations

Each forward obligation that names WP9.3, or a WP9.3 row, is listed with its disposition.

| # | Source | Obligation | Disposition |
|---|---|---|---|
| 1 | P-080 item 3; WP9.2-2 record §7 (review N-2) | A W9 record content-hash rule, stamped by the preparer and recomputed at replay | **Keep.** The rule is already fixed by the accepted owner annex: "a content hash is SHA-256 of canonical_bytes over the record without content_hash (the W11 rule)" (`wp9-1-catalogue-owner-annex.yaml:19`), as W11's `content_sha256` computes it (`research_system/discovery/assay_authority.py:47-52`). §4.1 |
| 2 | P-080 item 3; record §7 (F-4) | Refuse-before-bind in any mutating CLI | **Keep, and widen** to every root known before binding (§13) |
| 3 | P-080 item 3; record §7 (F-8, first limb) | The resolving Decision's proposal named the record by its pre-assigned ID and exact content hash | **Keep at the preparer, and add to replay.** The subject is now persisted in the Decision proposal's `governing_evidence_refs` (§5.2), so replay can check it (§6.1) |
| 4 | P-080 item 3; record §7 (F-8, second limb) | LR-020's ownership records equal the acceptance proposal's list | **Keep, in replay too,** with the list derived rather than listed (owner point E; §10.5). The record's suggestion "consider adding the LR-020 list check to replay" is taken |
| 5 | P-080 item 3; record §7 ("Preparers generally") | Superseding a record that does not exist | **Keep, placed.** The preparer refusal belongs to the supersession proposal (LR-056 to LR-060, WP9.6), which WP9.3 does not build. Because WP9.6's brief does not exist yet, the decision entry for this note records the carry, as P-080 item 3 recorded the obligation (review m-10). WP9.3 adds the replay refusal to `_apply_supersession` (`replay/reducers.py:304-317`) now, tested on a forged ledger, because N-2 touches every record reducer anyway |
| 6 | WP9.2-2 record §3 item 8 | LR-014 accepts only `approve` under LR-013, on a review whose paired subjects name the record | **Keep,** and apply the same rule to every W9 review (owner point B; §5.4). The hash is recomputed (§14) |
| 7 | WP9.2-2 record §7, test gaps | Guard 5's reachability; the §2.5 asymmetry; the CLI read-only test; the verify-restore replay | Genesis and shared-replay gaps, not WP9.3's. Unchanged, except that WP9.3's CLI test binds a real scratch store instead of monkeypatching `_verified_ledger` (§13) |
| 8 | Stage B note §6, "WP9.2 runtime obligations with no stage B artefact" | The record content-hash rule; `created_at` and `created_by_actor_id` taken from the proposal; the retry control W9-C11; the behavioural controls W9-C20 to W9-C25 | **Keep,** all for WP9.3's rows: §4.1, §5.1 and §17 |
| 9 | Stage B note §7; stage A note §2 | The kinds of the `anyRef` fields: the signature record; a `pilot_promotion` evidence ref; the inventory's independent reproduction | The reproduction is a `rev_` (stage B note §7; `replay/reducers.py:369-377`). The signature record: owner point C (§9.1). A `pilot_promotion` evidence ref is a `rev_` or an `art_` (§10.2). The adoption's successor use is WP9.4's |
| 10 | Stage A note §3, "Left to WP9.2 and WP9.3" | Family-name uniqueness and pointer exclusivity (W9-T3); one entry per fixture within an item and one item per observation; a legacy role under `.research-system/projections/legacy/`; an inverted locator line span; a read that ends before it starts; the W9 kind an `obj_` ref names; the `anyRef` kinds | **Keep,** each in replay (§6, §9.3, §14). The recovery-root and supersession items are WP9.6's |
| 11 | Stage A note §2, restricted bytes | "D-9 matches suffixes, not content. A `.csv.gz` or a `.pickle` passes, and WP9.3's reader and WP9.7 own that scope" | **Keep, narrowly** (§7.4). The reader adds no content test of its own: a wider rule would be a new D-9 list, which is Stephen's |
| 12 | Stage A note §2 (re-review n-5) | The importer adds the inventory's selector kind to each row and fills the absent fields with null | **Keep** (§8.3) |
| 13 | Stage A confirmation r-1, the alternative it offered | An observation's source matches its registration's path and root | **Keep,** in replay (§6, LR-015) |
| 14 | Stage A confirmation i-1, i-2 | Refuse a legacy role under the projection directory; refuse an inverted line span | Row 10 |
| 15 | Segmentation contract §6.1, §6.3; 06v D-7 | The export is read by the reference implementation; WP9.3's reader re-segments the retained copy and must reproduce every row; a mismatch voids the export | **Keep.** The reference implementation produces the export at L-0b, and WP9.3's runtime segmenter rechecks it, so two implementations agree (§12.2; review M-4) |
| 16 | Segmentation contract §7; P-068 "Not authorized here" | A session independent of the contract's author and of WP9.3's implementer re-implements the contract and reproduces every vector before any export or observation under it is accepted | **Keep.** Owner point I proposes WP9.3-1's independent reviewer as that session |
| 17 | P-068 item 4 (confirmation C-1) | The classified entry list classifies each structural or blocker row as in the legacy region or not | **Keep:** the export format WP9.3 reads carries a classification slot for every row (§12.2). The classification itself is L-0b's |
| 18 | 06v reconciliation m-9 | An anchor is an ancestor of the binding's `git_head` at the first acceptance, or an ARS event at a lower global position | **Keep the commit half;** owner point G on the event half (§10.3) |
| 19 | 06v O-32; confirmation c-1 | The acceptance preparer reads WP9.5's change list at the binding's `git_head`, unchanged | **Keep.** WP9.3 fixes the reader-side format (owner point D; §11.1) |
| 20 | WP9.2 note §4 | "WP9.3 and later packages add bindings and reducers, not a layout" | **Keep.** The four U-7 sites, `LEGACY_COMMAND_TYPES` and the row-assignment rules do not change (§14) |
| 21 | WP9.2 note §2.3, C2 | A W9 command that emits a W2 event type needs a producer binding, and the event carries the W2 schema | **Keep** (§16). The runtime's fixed event schema (`legacy/runtime.py:438`) becomes per event type |
| 22 | WP9.2 note §2.3, C3 and C5 | No W11 row in a W9 payload; no event type shared with another partition | **Keep.** The encodings of §5.2 carry no `W11:OR-` string. No WP9.3 row emits a shared event type, which the existing C5 test pins |
| 23 | 06v WP9.3 | "The `CONVENTIONS.md` vault alias is refused" | **Keep:** a `vault_file` registration or source whose resolved target is the repository's `CONVENTIONS.md` is refused, by path and by `physical_identity` (§7.1; review m-10) |
| 24 | Annex `catalogue_tests` W9-C20; P-073 item 1 | "A reviewer who … shares the analyst's session … is refused"; "each is refused" | **Keep, as far as the payloads allow.** The analyst's session is encoded in the request and the verdict's session must differ, both strings attested (owner point H; §5.5; review M-3) |

## 4. Record identity

### 4.1 The content hash (N-2)

The rule is fixed by the accepted annex (§3 row 1): the SHA-256 of `canonical_bytes` over the record with
`content_hash` removed. One helper in `research_system/legacy/records.py` computes it for the preparers, replay and the
tools.

- **The preparer stamps it.** It computes the value and writes it into the event record. A command payload that
  supplies a `content_hash` is refused, as are the other preparer-set fields (§5.1). This keeps P-080's "stamped by the
  preparer": a submitter never chooses the value, so a payload cannot carry one hash and record another.
- **Replay recomputes it** before any comparison: in `reduce_proposal`, `_record_resolved`, `reduce_light_inventory`
  and `reduce_record`, and for LR-020's ownership records. A record whose declared value differs is refused. Review
  subjects, Decision subjects and every `recordRef` to a W9 record (§4.4) then compare against recomputed values,
  never against the record's own claim.
- **Negative control through the guard.** A forged record whose `content_hash` is the hash of other content is
  replayed through `replay_legacy` with WP9.3's rows routed, and refused with the rule's message. A scratch mutation
  that deletes the recomputation must let the same ledger through, which shows the control reaches the guard itself
  (§17).

### 4.2 Pre-assigned review and Decision refs

A proposal carries the review and Decision it will cite as refs: `registration_decision_ref`, `review_ref`,
`acceptance_decision_ref`, `independent_review_ref`, `decision_ref` and `independent_reproduction_ref`. Each ref
requires a `record_revision` and a `content_hash` (the `decisionRef` and `reviewRef` definitions). But the review or
Decision does not exist yet, and its own payload will name the proposal's hash, so the ref cannot hold the review's
or Decision's hash without circularity (P-072 item 1: "no hash depends on itself"). WP9.2-2's forged ledgers use a
constant placeholder (`tests/research_system/integration/test_w9_legacy_replay.py:363-364`). No rule is fixed yet.

**The rule.** A pre-assigned ref has `record_revision: 1`, and its `content_hash` is the SHA-256 of `canonical_bytes`
over `{"w9_pre_assigned": "review" or "decision", "id": <the rev_ or dec_ ID>, "record_id": <the proposal's record
ID>}`. It depends on neither hash (review §2, item 8). It ties the ref to the record that pre-assigns it, and replay
recomputes it and refuses any other value. A ref copied into another record keeps the value computed for the record
that pre-assigned it: LR-020's ownership records carry the acceptance's `independent_review_ref` and `decision_ref`
(§10.6), and replay checks those copies against the acceptance's record ID, not the ownership record's (review m-3).
The rule puts a synthetic value in a field the schemas call `content_hash`, so it is a reading of accepted schemas that
fixes stored bytes. It is owner point M.

### 4.3 Identity claims (W9-C25)

- **At a proposal,** replay claims the record ID and every pre-assigned `rev_` and `dec_` in it, the latter reserved
  to that proposal. Today `reduce_proposal` claims only the record ID (`replay/reducers.py:206`), so W9-C25's "whose
  pre-assigned IDs already exist" is checked for one of three IDs.
- **A review request or Decision proposal** must take exactly its proposal's reservation, and converts it. That is the
  precondition "the new review's ID is the proposal's pre-assigned rev_ ID" of LR-007, LR-012 and LR-017, now checked
  at replay too. A reservation used by any other request, or a second proposal that pre-assigns a reserved ID, is
  refused.
- **The reserved external refs** and `CATALOGUE_STREAM_ID` stay refused (`replay/reducers.py:145-154`), and so does
  every pinned W0 signature ref, at every ledger position, from the PR that pins it (§9.1).
- **A batch's ownership record IDs** are derived and reserved at LR-016 (§10.5).
- **Across the shared ledger.** `replay_legacy` reads every event but reduces only W9 transactions, so its identity
  map holds W9 claims alone (`replay/driver.py:93-160`), and the runtime compares only the supplied and observed
  stream versions (`legacy/runtime.py:406-415`). A W9 command that reuses a W11 aggregate's ID with that stream's
  current version would append to it. So replay refuses a W9 claim of any ID that a non-W9 event uses as its
  `stream_id`, or creates in its payload, before or after the claim. Each claiming event must also stand at version
  1 of its own stream (§4.5), and the preparer refuses a claiming command whose `expected_stream_version` is not 0.
- **Created IDs, not only streams.** A non-W9 event can create a record ID in its payload without making it a
  stream: `RecordScientificReview` appends to the artefact stream (`command/service.py:4426`) but creates a `rev_`
  `review_id` (`:4457-4469`; `core/events/scientific_review_recorded.schema.json:13-16`). So every identity check
  below, and replay's, compares the event's `stream_id` and the record IDs it creates. Those are read from one table
  in `research_system/legacy/` that classifies each ID-shaped payload field of each non-W9 event type as a creation
  or a reference; `ScientificReviewRecorded`'s `review_id` is a creation. The schemas do not mark creations, so a
  test walks every core, W11 and T2 event schema, collects each payload field whose pattern is a record ID, and fails
  on one the table does not classify. A reference, such as a review's `artefact_id`, is not a creation, so referring
  to a W9 record stays allowed.
- **The W11 side, before append.** W11's identity contract, `discovery_identity_exists` (`discovery/routes.py:292-298`),
  reads only Discovery's projection. `DiscoveryRuntime._require_admissible_target` applies it
  (`discovery/runtime.py:334-361`). A W11 command can therefore take an ID that W9 has claimed or reserved, such as a
  pre-assigned `rev_` that is not yet a stream. The shared ledger would then fail replay only after the append. So
  WP9.3-1 adds a symmetric check. W11's admissible-target check also refuses a target, or a record ID the command's
  events would create, that the W9 projection claims or reserves. It also refuses W9's fixed identities, read from
  the code constants rather than the projection, so that they are refused before W9 genesis too: W9's
  `CATALOGUE_STREAM_ID`, `RESERVED_IDS` and the pinned W0 signature refs. The catalogue stream ID needs this,
  because `reduce_genesis` stores the catalogue payload but never enters that ID in `identities` or `reserved_ids`
  (`replay/reducers.py:145-154`, `:161-180`). It reads that projection through a
  lazy import of `research_system.legacy`, as `shared_event_partition` already does (U-7 site 2,
  `discovery/routes.py:313-315`), so `research_system.legacy` stays out of Discovery's import graph. Replay keeps the
  backstop: a W11 event on a W9 identity makes `replay_legacy` refuse the ledger. This extends WP9.3's boundary to
  `discovery/routes.py` and `discovery/runtime.py` (P-081 item 10, as amended; §16). The W11 catalogue, schemas and
  bindings do not change, and WP9.3-1's independent review re-verifies the W11 pins (§19).
- **The generic side, before append.** The generic `CommandService` checks only the target's stream version
  (`command/service.py:1541-1550`), and its creation commands accept any unused target ID, as
  `_prepare_scope_command` does for `CreateScopeDefinition` (`:6134-6175`). A generic command could therefore create a
  stream on W9's `CATALOGUE_STREAM_ID` before W9 genesis, so that genesis can never append on that store. After genesis
  it could create a stream on an ID W9 claims or reserves, and under the rule above `replay_legacy` would then refuse
  the whole shared ledger, which the public replay runs (U-7 site 4). The T2 path is a second generic writer with its
  own append site: `submit_t2` checks each write-set entry's expected version and appends directly
  (`command/t2.py:1179-1195`), and its creations take version 0 on a new stream (`:553`). So WP9.3-1 gives both
  generic append sites in the 06h manifest, `CommandService.submit` and `submit_t2`, the same check as W11's: after
  the stream-version check and before any append, a command is refused if any stream its events would append to, or
  any record ID they would create (the table above), is one of W9's fixed identities (read from the code constants)
  or an ID the W9 projection claims or reserves. Each reads
  the projection through the same lazy-imported helper as W11's check, over the snapshot it has already materialized.
  The third non-W9 site, the authority store's bootstrap (`authority.py`, `initialize_authority_control_store`), runs
  once on an empty store with its own fixed IDs; a test asserts they are disjoint from W9's fixed identities. This
  extends WP9.3's boundary to `command/service.py` and `command/t2.py` (P-081 item 10, as amended again on
  2026-11-08; §16). No append site, generic command type, schema, binding or census row changes, and the existing
  generic and T2 suites must pass unchanged.
- **Discovery-only replay is not the cross-partition check (a known limit).** `replay_discovery` runs the shared
  partitions and Discovery's own reducers, never `replay_legacy` (`discovery/replay/driver.py:35-80`). An event
  appended outside the guarded writers, by a direct `EventLedger.append`, on a W9 identity would therefore still give a
  Discovery projection. Adding the check there would put a fifth site beyond U-7's four, an 06v §8 stop rule, so the
  note does not. The check stays where U-7 puts it: the public shared replay runs `replay_legacy` whenever the ledger
  holds a W9 event (`projection/replay.py:1391-1395`) and refuses such a ledger, and every dispatch writer, W9, W11
  and generic, checks before append. The runtime-construction census (§17) keeps the W9 and W11 runtimes behind the
  binding. Before W9 genesis no W9 event exists, so the public replay runs no W9 check: a direct append on the
  catalogue stream ID then shows up only as W9 genesis failing on that store. Stephen chose this on 2026-11-08.
- **The controls (§17):**
  - a W9 proposal reusing a W11 aggregate's ID at that stream's current version, refused at `submit` and on a forged
    ledger;
  - a valid W11 request whose `new_review_id` is a W9-reserved `rev_`, refused by `DiscoveryRuntime.submit` before
    any append;
  - a W11 minting command targeting W9's `CATALOGUE_STREAM_ID`, refused before any append, both before and after W9
    genesis;
  - a forged W11 event on a reserved `rev_`, refused by `replay_legacy`;
  - a generic `CreateScopeDefinition` on W9's `CATALOGUE_STREAM_ID`, refused by `CommandService.submit` before any
    append, both before and after W9 genesis, and a generic creation on a W9-reserved `rev_`, refused the same way;
  - a T2 creation whose write set names a W9-reserved ID, refused by `submit_t2` before any append; and the authority
    bootstrap's fixed IDs disjoint from W9's;
  - the known limit's boundary: a forged ledger holding a W9 event and a W11 event on a reserved `rev_`, refused by
    the public shared replay.

### 4.4 References to W9 records

Every `recordRef` that names a W9 record must resolve in the replayed projection to a recorded record of a kind the
stage A edge table admits for that field (stage A note §2, the test's `RECORD_EDGES`), at the ref's `record_revision`
and at the record's recomputed `content_hash`. An open proposal is not a recorded record. Refs to things outside the
store, such as a signature record or a source locator, follow §9.1 and §7.

### 4.5 Streams

The catalogue's `affected_streams` name record, review, Decision and index streams. The reading:
- each pre-assigned ID is one ledger stream. A record ID's stream holds its proposal event at version 1 and its
  recorded event at version 2. A review ID's stream holds the request and the verdict. A Decision ID's stream holds the
  proposal and the resolution;
- an observation's own ID is its stream, at version 1. Each LR-020 ownership record has its own derived ID's stream,
  at version 1;
- a row's "index" entries are projection keys, not ledger streams. No catalogue event targets them, and each row's
  event list is fixed (`legacy/routes.py:609-627`);
- `target_stream_id` is the stream of the row's first event, and the receipt reports that stream's version
  (`legacy/runtime.py:349-361`).

### 4.6 Open and lapsed proposals

No catalogue row records a rejection or retires a proposal (§5.2). Without a rule, a declined or abandoned proposal
would stay open forever. That would block every later proposal its uniqueness rules exclude, such as a corrected
registration of the same path (LR-003). So a proposal is **open** while it is unresolved and has not lapsed.

- **The lapse time.** An unresolved proposal lapses at the later of two times: its own `created_at` plus 30 days (the
  Decision term of §5.2), and, if its Decision has been proposed, that Decision's `expires_at`. The latest possible
  lapse is therefore 60 days after the proposal. Replay judges lapse by each later event's `occurred_at`, so it
  depends only on the ledger.
- **A lapsed proposal stays in the projection, but:**
  - it no longer counts as live for any uniqueness rule over open proposals (§6.2 LR-003);
  - no review request, Decision proposal or resolution may name it. This extends §5.2's refusal of a resolution after
    `expires_at` to every step;
  - its record ID and pre-assigned IDs stay claimed for good (§4.3), so a corrected proposal takes new IDs.
- **To decline a proposal,** Stephen leaves it unresolved, and it releases what it held when it lapses. A rejection row
  would release it at once; that waits for the next catalogue revision (§5.2).
- **The controls (§17):** a corrected LR-003 registration of the same path, refused while the first proposal is open
  and admitted once it has lapsed; and a review request, Decision proposal and resolution, each refused on a lapsed
  proposal.

## 5. The authority flow

### 5.1 Command payloads

W9 follows W11's pattern: the command payload is small, and the preparer builds the W2 payload
(`discovery/runtime.py:1042-1219`).

| Command | The payload carries | The preparer builds |
|---|---|---|
| `ProposeLegacyRecord` | the record, without the preparer-set fields | `E:<kind>-proposed`, whose payload is the completed record |
| `RequestW9AuthorityReview` | the subject record ID, the reviewer's actor ID, the review questions, the analyst's session and, for a membership table, the table author's session (§5.5) | `ReviewRequested` (§5.2) |
| `RecordW9AuthorityReview` | the verdict, findings, limitations, reviewer session and model metadata, context manifest hash | `ReviewVerdictRecorded` |
| `ProposeW9AuthorityDecision` | the subject record ID, the question, the recommendation, the consequences | `DecisionProposed` |
| `ResolveW9AuthorityDecision` | the Decision ID and `selected_option: accept` | `DecisionResolved`, then `E:<kind>-recorded` with the proposal's exact record, and LR-020's ownership records |
| `RecordLegacyLightInventory` | the inventory's record ID | `E:legacy-light-inventory-recorded`, with the proposal's exact record |
| `ObserveLegacyRecord` | the observation, without the preparer-set and read-derived fields | `E:legacy-record-observed` |

**Preparer-set fields.** For a record a command creates (a proposal, or an observation), the preparer sets
`created_by_actor_id` (the command's actor), `created_at` (the runtime clock), `content_hash` (§4.1) and, for an
observation, `observed_at`. A payload that supplies any of them is refused. A record written at resolution takes its
`created_at` and `created_by_actor_id` from its proposal (annex `derivation_rules`, line 20), because it is the
proposal's exact bytes.

**Read-derived fields** (source identities, file facts, inventory rows, the importer identity) are a function of the
bytes. An observation's payload omits them, and the preparer fills them from its own read; a payload that supplies
one is refused. A proposal's payload carries them, because the review will bind its bytes, and the preparer
recomputes each one and refuses any difference. It never fills a proposal's read-derived field.

### 5.2 W2 payload encodings

The closed W2 payloads have no W9 subject field, so the subject travels in fields that exist. Every field each payload
requires is listed below, with its source and whether replay checks it (review M-2). "Fixed" means a constant the
preparer writes and replay requires. "Recorded" means the value is stored as the submitter gave it and replay checks
only its type, because no rule constrains it. Each checked field gets a forged-ledger control (§17).

**Two derived IDs.** `context_manifest_id` (`ctx_`) and `producing_attempt_id` (`att_`) are required on a verdict. W11
fixes them as constants (`discovery/runtime.py:1130`, `:1162-1167`). W9 derives them per review, as the WP9.2 external
refs are derived (WP9.2 note §5.3, steps 2 to 5): from the domain strings `w9-review-context:<review ID>` and
`w9-review-attempt:<review ID>`, with the request event's `occurred_at` in milliseconds. Replay recomputes them.

**`ReviewRequested`** (`review_requested.schema.json:129-145`):

| Field | Value | Source | Replay checks |
|---|---|---|---|
| `review_type` | `migration`, from the W2 enum (`:8-22`) | fixed | yes |
| `new_review_id` | the proposal's pre-assigned `rev_` | derived | yes |
| `subject_ids`, `subject_hashes` | exactly `[<record ID>]` and `[<recomputed content hash>]`, paired. Today `reduce_review_request` zips them with `strict=False` (`replay/reducers.py:225`), which admits unpaired lists of the kind W11's two-to-one shape uses (`discovery/runtime.py:1090-1094`) | derived | yes |
| `governing_refs` | exactly `["W9:LR-nnn"]`, which assigns the row (`legacy/routes.py:594-595`) | derived | yes |
| `review_questions` | non-empty. The schema sets no `minItems` (`review_requested.schema.json`), so replay enforces it | payload | yes: at least one entry |
| `required_evidence_refs` | exactly `["w9-analyst-session:<the analyst's session>"]`; for the review of a membership table, exactly `["w9-analyst-session:<…>", "w9-author-session:<the table author's session>"]`, in that order (§5.5) | payload | yes: that count, those prefixes, that order, and a non-empty session string after each prefix |
| `required_lanes` | `["provenance"]` | fixed | yes |
| `reviewer_capability` | exactly `[<the named reviewer's actor ID>]`, as W11 names its reviewer (`:1108`) | payload | yes |
| `required_independence_grade` | `independent` | fixed | yes |
| `visibility_policy` | `owner-visible`, as W11 (`:1110`) | fixed | yes |
| `allowed_verdicts` | `["approve", "changes_requested", "reject", "unable_to_verify"]`, W11's set (`:1111`), so a conditional approval cannot be recorded (owner point B) | fixed | yes |
| `satisfaction_authority` | `ars://legacy/policy/w9-authority-review@1.0.0`, a name for §5.4's rule, as W11's is a name (`:1112`) | fixed | yes |
| `deadline` | the request time plus one day, as W11 (`:1040`) | derived | yes: after the request |
| `escalation_rule` | `owner-ruling`, as W11 (`:1114`) | fixed | yes |

**`ReviewVerdictRecorded`** (`review_verdict_recorded.schema.json:115-132`):

| Field | Value | Source | Replay checks |
|---|---|---|---|
| `review_id` | the request's | derived | yes |
| `verdict` | one of the request's `allowed_verdicts` | payload | yes |
| `findings`, `limitations` | as given | payload | recorded |
| `conditions` | `[]` (owner point B) | fixed | yes |
| `required_evidence_refs` | the request's | derived | yes |
| `reviewer_actor_id` | the event's actor, which must be the request's named reviewer (W9-C21) | derived | yes |
| `reviewer_profile` | `w9-independent-reviewer` | fixed | yes |
| `reviewer_session` | the reviewer's session, attested | payload | yes: it differs from every session the request records (§5.5) |
| `reviewer_model_metadata` | attested | payload | recorded |
| `context_manifest_id` | derived as above | derived | yes |
| `context_manifest_sha256` | the reviewer's context, attested | payload | recorded |
| `unchanged_subject_sha256` | the request's subject hash, which must still be the subject's recomputed hash (W9-C22) | derived | yes |
| `producing_attempt_id` | derived as above | derived | yes |
| `trace_visibility_evidence_refs` | `[<the subject hash>]`, as W11 (`:1166`) | derived | yes |
| `computed_independence_grade` | equal to the request's `required_independence_grade`, `independent`, as Discovery refuses otherwise (`discovery/runtime.py:2487`) | fixed | yes |

**`DecisionProposed`** (`decision_proposed.schema.json:108-122`):

| Field | Value | Source | Replay checks |
|---|---|---|---|
| `new_decision_id` | the proposal's pre-assigned `dec_` | derived | yes |
| `decision_revision` | 1 | fixed | yes |
| `decision_kind` | `migration_authority` (G5) | fixed | yes |
| `governing_evidence_refs` | exactly `["W9:LR-nnn", "w9-subject:<record ID>", "w9-subject-sha256:<recomputed content hash>"]`, in that order. The schema has no subject field, and the list's items are free strings (`:54-62`). W11 puts its subject hash in the same list (`discovery/runtime.py:1210`). `w9_row_ref` accepts these refs, since exactly one is a `W9:LR-` string and the others carry no `W9:` prefix (`legacy/routes.py:540-552`; review i-2). `_refuse_w11_row` ignores them (`replay/driver.py:37-47`). Only a recovery Decision turns bare `obj_` refs into graph edges (`replay/reducers.py:333-334`), and the prefixes keep a record family's subject out of that set | derived | yes |
| `question`, `recommendation`, `consequences` | as given | payload | recorded |
| `options` | `["accept", "reject"]` | fixed | yes |
| `affected_task_ids`, `affected_claim_ids` | `[]` | fixed | yes |
| `required_authority` | `owner` | fixed | yes |
| `review_date` | the proposal time | derived | yes |
| `expires_at` | the proposal time plus a fixed term (30 days) | derived | yes |

A resolution must select `accept`, because every WP9.3 resolution row writes its record event
(`legacy/routes.py:609-627`). No catalogue row records a rejection: a rejected proposal is simply not resolved, and
replay refuses a resolution after the proposal's `expires_at`. The proposed record lapses and releases what it held
(§4.6). This is a known limit, noted for the next catalogue revision.

**`DecisionResolved`** (`decision_resolved.schema.json:100-114`):

| Field | Value | Source | Replay checks |
|---|---|---|---|
| `decision_id` | the Decision's | payload | yes |
| `selected_option` | `accept` | payload | yes |
| `effective_scope` | `w9-record:<record ID>` | derived | yes |
| `decision_revision` | 1 | fixed | yes |
| `deciding_actor_id` | the event's actor | derived | yes |
| `decision_authority_grant_id` | the event's grant | derived | yes |
| `governing_evidence_refs` | equal to the proposal's | derived | yes |
| `considered_review_ids` | `[<the proposal's pre-assigned rev_>]`, or `[]` for a path registration, which has no review | derived | yes |
| `effective_at` | the resolution time, not after the proposal's `expires_at` | derived | yes |
| `permitted_commands`, `superseded_decision_ids`, `conditions`, `revisit_triggers` | `[]` each | fixed | yes |

### 5.3 Authority subjects (G4)

A scoped grant names one subject kind and one exact ID (`scoped-authority-grant-v2.1.0.schema.json:88-119`). It cannot
carry a content hash. So G4's exact subject is the ID, and the hash half of each row's `authority_subject` is a replay
and preparer check (§6).

**The proposal rows** (LR-003, LR-006, LR-011, LR-016) are the exception. Their annex subject is "pre-assigned record
ID + exact proposed content hash", but at a proposal there is no earlier hash to compare against: the proposal creates
it. So the proposal grant authorizes any content under its ID, and the content hash is bound later, by the review
request and verdict and by the Decision, each on the recomputed hash (review m-10). That is a reading of the accepted
global precondition G4, so it is owner point L.

| Command | Subject kind | Subject ID |
|---|---|---|
| `ProposeLegacyRecord`, `RecordLegacyLightInventory` | `scope_definition` | the record ID (the target stream) |
| `RequestW9AuthorityReview`, `RecordW9AuthorityReview` | `review` | the review ID |
| `ProposeW9AuthorityDecision`, `ResolveW9AuthorityDecision` | `decision` | the Decision ID |
| `ObserveLegacyRecord` | `scope_definition` | the observation's own record ID (the target stream), derived from LR-015's full subject, below |

These are W11's kinds for the same steps (`research_system/authority.py:231-234`). `LegacyRuntime._resolve_authority`
hard-codes `scope_definition` and the target stream today (`legacy/runtime.py:259-273`), and becomes a table. The risk
tier stays R2 (`:268`).

**The observation's ID binds LR-015's full subject.** The annex subject is "registration + physical identity + bytes or
baseline + selector + importer tool identity" (`wp9-1-catalogue-owner-annex.yaml:515`). A grant on the registration's
ID alone would let one grant cover a second observation of that registration with another selector or baseline. Since
a grant names one ID, the observation's ID carries the rest:
- the **subject digest** is the SHA-256 of `canonical_bytes` over `{"w9_observation_subject": {"registration_id":
  <registration_ref.id>, "source_identity": <source_identity>, "selector": <selector>, "importer_tool": {"tool_id",
  "tool_version", "tool_sha256"}}}`, the last three copied from the record's `importer`. `source_identity` carries
  the source's location and its bytes or baseline: the path, and for `git_tracked` the commit and blob, with the
  SHA-256 and length. It carries no file identity: the accepted schema's `source_identity` holds only those fields
  and admits no others (`legacy-observation.schema.json:721-876`). The physical identity enters as the reading
  below;
- the **observation count** `n` is the number of observations of that registration already in the ledger, so the
  first observation has `n` 0;
- `record_id` is an `obj_` UUIDv7 built as WP9.2's external refs are (WP9.2 note §5.3, steps 2 to 5), from the domain
  string `w9-observation:<registration record ID>:<subject digest>:<n>` and, as its timestamp, the **registration
  record's** `created_at` in milliseconds. The observation's own `created_at` comes from the runtime clock at submit
  (§5.1), so it cannot be known when the grant is issued; the registration's is already in the ledger. Nothing ties an
  ID's UUIDv7 timestamp to its record's `created_at`: `validate_id` checks the version and variant only
  (`ids.py:100`);
- the preparer, under the writer lock, and replay each recompute it, `n` included, and refuse a record whose
  `record_id` differs. So a grant on that ID authorizes exactly one subject at one position in the registration's
  history, and two observations of one registration need two grants.

**Why the count.** Without it, the ID would be a function of the subject alone. A source observed as A, then B, then
A again could then never be accepted: the first A observation is stale, because B came later (§7.2), and a new A
observation would derive the first one's ID and be refused as an existing identity (W9-C25). With `n`, each
observation gets a fresh ID, and re-observing an unchanged subject is admitted under its own grant. Only another
observation of the same registration moves `n`; if one lands after the grant is issued, the preparer derives a
different ID, the grant no longer matches, and the command is refused before append.

The read-only `ars legacy observation-id` command prints the ID for an observation envelope, from the store's W9
projection and the source bytes, so that Stephen can grant it before it is submitted (§13). If the bytes change
before submission, the subject digest, and so the ID, changes, and the grant no longer matches: the command is
refused before append. Stephen chose this on 2026-11-08 over recording a narrowing like owner point L; on the same
day he chose the registration's timestamp, over a prepare-then-grant step that would have let a payload supply
`created_at`, and the observation count, over un-staling an observation whose source returns.

**The physical identity in LR-015's subject (a reading).** The annex subject names the physical identity, but the
observation cannot record it (above), and LR-015 matches the registration by kind, root and path only (§6). The note
reads the annex as follows. The physical identity is fixed and checked when the path is registered: LR-003's
handle-bound read shows the path resolves to the declared `physical_identity`, and LR-005 re-reads it unchanged
(§6). At observation, the handle-bound read (§7.1) still refuses a symlink or junction leaf, a file with more than one
link, a changed parent anchor, and a file whose identity changes during the read; a `vault_file` read must also
resolve to the registration's `canonical_target`. A file replaced at the registered path is the same source: its
bytes are what the observation binds. A replacement with different bytes changes the subject digest, so the ID and
the grant no longer match and the command is refused before append; one with identical bytes yields an identical
observation. The observation does not require the read's `stable_file_id` to equal the registration's, because a
tool that saves by writing a new file and renaming it over the old one gives the file a new ID on every save, and the
registration could then not be observed again until it was re-registered. Stephen chose this reading on 2026-11-09
over that strict match.

**Operator burden.** Every proposal, review and Decision needs its own grant on its own ID, which Stephen issues. A
20-item pilot needs tens of grant activations: for the registrations, a membership table per JSON schema, an inventory
per Markdown file, an observation grant per observation (one per registration in the pilot), and one batch. W9 §13.4 makes "operator
burden makes routine bypass of a control likely" a stop criterion, and §14.3 measures burden. The pilot's owner log
records the grant count. Nothing here changes it: G4 is accepted.

### 5.4 Review satisfaction (owner point B)

A W9 review is **satisfied** when its one verdict, recorded under the verdict row that answers its request row
(`legacy/routes.py:471-478`), is `approve`, on the subject hash it was requested on, and that hash is still the
subject's recomputed hash. WP9.2-2 took this reading for LR-014 (record §3 item 8). WP9.3 applies it to every W9
review. The reason: the catalogue has no row that records or discharges a condition, so an `approve_with_conditions`
verdict could never be shown met.

### 5.5 Roles and independence (owner point H)

W9 roles bind through Stephen's exact-subject grants and a set of distinctness rules, not through a role registry. No
record kind exists for one, and a new kind would be a catalogue revision.

**Checked at replay,** over the actor IDs the ledger attributes to events:
- the analyst who requests a review or proposes a Decision is not the proposal's creator, where the creator is an
  observer (LR-011) or a membership author (LR-006);
- a reviewer is not the proposal's creator, the requesting analyst, or, for a membership table, its author, or, for a
  batch, the observer of any of its items (G3, W9-C20);
- a reproducer (LR-012) is not the inventory's observer;
- a membership table's author is not the importer or the observer of any observation that binds the table (LR-015;
  template §2);
- the verdict's actor is the reviewer the request named (W9-C21).

**Checked by the preparer,** because the owner is known only from authority (`authority.py:2723-2731`): a resolver row
requires the owner actor, and every other W9 row refuses it. Stephen resolves; he does not observe, review or propose.

**The session limb of W9-C20.** The accepted annex defines W9-C20 as "a reviewer who produced the item, shares the
analyst's session, or is not the eligible session is refused", and P-073 item 1 says each such control "is refused".
LR-007, LR-012 and LR-017 bind W9-C20. The closed `ReviewRequested` payload has no session field, so the request
carries the analyst's session as the one entry of `required_evidence_refs`, `w9-analyst-session:<session>` (§5.2). Replay
refuses a verdict whose `reviewer_session` equals it. Both strings are attested by their submitters, so the check
catches the honest same-session mistake W9-C20 names, but not a false session string. This is owner point H, option
(a) (review M-3).

**The author's session, for a membership table.** The template's reviewer must be "on a session distinct from the
author's and from the migration analyst's" (`w9-membership-table-template.md` §2). The actor checks above do not
reach the case of distinct actors on one session. So the review request for a membership table carries the table
author's session as a second entry, `w9-author-session:<session>`, after the analyst's (§5.2). The reviewer checks it
against the table file's `author.session` (template §4), which is in the bytes under review. Replay refuses a verdict
whose `reviewer_session` equals either entry. The strings are attested, so the limit is the same as for the analyst's
session. This applies option (a) to the template's second session (P-081 item 8, as amended).

**Recorded, not proved** (a known limit, as P-058's single-family limit is):
- that the attested session strings are true;
- LR-012's exclusion of the segmentation contract's author;
- G3 against a legacy item's producer. Legacy producers were APM-era sessions, not ARS actors, so the item's reviewer
  checks it. Code cannot.

## 6. The checks for each row

**The rule.** Replay checks everything the ledger determines. The preparer adds what only the environment can show:
file bytes, Git, the evidence area, the store binding, authority and the clock. It then runs the prepared transaction
through replay's own per-transaction step on a copy of the projection before it appends, as Discovery's preparers do
(`discovery/runtime.py:1069-1082`). So a preparer is never weaker than replay, and a forged or faulty append is refused
by the next replay.

**The per-transaction step** is the body of `replay_legacy`'s loop (`replay/driver.py:136-159`), factored out into one
function: row assignment, the routed-row check, the transaction shape, C3, payload-schema validation, the genesis
precondition and the reducer. The reducers alone are not enough, because those other checks run in the loop: a
schema-invalid payload naming `OR-101` passes a reducer called alone (review m-6). `assign_row`'s
`review_request_rows` is rebuilt from the projection, so the shadow run needs no second whole-ledger replay (review §2,
item 4).

### 6.1 G5 at every resolution (LR-005, LR-010, LR-020)

At replay:
- the Decision is open, and was proposed under the same family (`replay/reducers.py:330-331`);
- its proposal's subject (§5.2) is this record's ID and recomputed hash (F-8, first limb);
- `selected_option` is `accept`, and the kind is `migration_authority`;
- the resolved record equals the open proposal's record byte for byte, under its ID (`_record_resolved`,
  `replay/reducers.py:263-284`);
- the record's Decision ref is the resolving Decision;
- where the family has a review, the record's review ref is a review satisfied on the same hash (§5.4), and
  `considered_review_ids` names exactly it.

At the preparer: the actor is the owner (P-005).

### 6.2 The rows

| Row | Replay | Preparer only |
|---|---|---|
| LR-003 | Schema; content hash; identity claims; pre-assigned ref hash. No recorded registration, and no open (unlapsed, §4.6) registration proposal, of the same root and normalized path or of the same `physical_identity` `canonical_target` and `stable_file_id`. No legacy role under `.research-system/projections/legacy/` (stage A i-1) | A handle-bound read shows the path resolves to the declared `physical_identity` (§7.1). Every §4.4 detector's negative control is recorded as watched to fail, in the evidence area at the binding's `git_head` (§11.1) |
| LR-004 | The subject is an open LR-003 proposal at its recomputed hash. `new_decision_id` is its `registration_decision_ref` ID | — |
| LR-005 | G5, with no review | The physical identity re-read unchanged |
| LR-006 | Schema; content hash; claims (the record, `review_ref`, `acceptance_decision_ref`). The event's actor is `author_actor_id`. Family names are unique, no pointer or pattern is in two families, and `unassigned` is disjoint from every family (W9-T3) | Each `applies_to` entry re-read: its bytes match its `sha256`, `size_bytes` and, if tracked, `git_blob`. Template §3 rule 1 parsing. The table is exhaustive in both directions over the bytes read (template §3 rule 2) |
| LR-007 | The subject is an open LR-006 proposal at its hash. `new_review_id` is its `review_ref` ID. One named reviewer. §5.5's distinctness | — |
| LR-008 | §5.2's verdict rules (W9-C21, W9-C22). One verdict per review | — |
| LR-009 | The subject as LR-007. `new_decision_id` is its `acceptance_decision_ref` ID. The review is satisfied on the current hash | — |
| LR-010 | G5 | `applies_to` bytes re-hashed equal (template §3 rule 10) |
| LR-011 | Schema; content hash; claims (the record, and `independent_reproduction_ref`, which must be a `rev_`). The registration is recorded, at its hash, and its source kind and path equal the inventory's `source_identity`. `observer_actor_id` is the event's actor. Row ordinals run 1 to n, and every row repeats the inventory's selector kind. `read_ended_at` is not before `read_started_at` | The source re-read by its kind equals `source_identity`. Re-segmentation reproduces every row exactly, so no blocker row is dropped. The region and structural-range declarations match their anchor-line hashes (contract §3) |
| LR-012 | The subject is an open LR-011 proposal at its hash. `new_review_id` is its `independent_reproduction_ref` ID. §5.5's distinctness | — |
| LR-013 | As LR-008 | — |
| LR-014 | As WP9.2-2 built it (record §3 item 8), with the hash recomputed | The source bytes re-read unchanged |
| LR-015 | Schema; content hash; claim. The registration is recorded, at its hash, and its kind, root and path match the observation's `source_identity` (§3 row 13), with §7.1's one exception for the Computational-Log. A restricted source carries no frozen copy. The selector by its kind (§8.2, §8.4); a `whole_file` or `inventory_item` observation carries exactly one family, named `whole_file` or `item`. The signature refs (§9.1), qualifiers (§9.3) and conflicts (§9.4). §5.5's distinctness. `observer_actor_id` is the event's actor | The read (§7). The frozen copy (§7.3). The registration appears in the registration manifest at `git_head` (§11.1). The importer identity (§7.5). A Computational-Log entry only from the accepted export, and a `CONVENTIONS.md` lock only from blob `4620c716` (§7.1) |
| LR-016 | Schema; content hash; claims (the record, `independent_review_ref`, `decision_ref`). The batch rules of §10.1. The structural `pilot_promotion` rules of §10.2, and the derived ownership list stored with the proposal (§10.5) | The window (§7.2), the anchors (§10.3) and the change list (§10.4) |
| LR-017 | As LR-007. The reviewer observed none of the batch's items | — |
| LR-018 | As LR-008 | — |
| LR-019 | As LR-009 | — |
| LR-020 | G5. The batch rules of §10.1 re-checked at this position: no acceptance is recorded yet, and no item's observation is in a recorded acceptance (review M-1). The ownership records equal the stored list and the list recomputed at this position (§10.5) | The window, the anchors and the change list again, against the binding at resolution |

## 7. The reader

### 7.1 Read modes

| Source | How it is read | Window |
|---|---|---|
| `git_tracked`, at the binding's `git_head` | A handle-bound working-tree read and a Git object read of `<git_head>:<path>`, which must be byte-identical, as W11 requires (`discovery/runtime.py:1313-1336`) | Yes |
| A `conventions_lock` registration (`CONVENTIONS.md`) | A Git object read of blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` (commit `4b143c92`) only (W9 §7.3 item 3). Any other source for that registration is refused | None |
| A Computational-Log entry | The accepted export's retained copy (owner point C), a committed file read from Git at its pinned commit. A read of the live vault page is refused for any registration whose role is `legacy_decision_log_entry` | None |
| `untracked_file` | A handle-bound read, with a frozen copy (§7.3) | Yes |
| `vault_file`, other than the Computational-Log | A handle-bound read through the real vault path, never the repository's `vault/` junction. The path form is recorded (contract §5.2), and the read must resolve to the registration's `physical_identity` `canonical_target`. The vault's `CONVENTIONS.md` is a symlink to the repository file, so a `vault_file` registration or source whose resolved target is the repository's `CONVENTIONS.md` is refused, by path and by physical identity (06v WP9.3; review m-10) | Yes |
| `restricted_untracked_file` | A handle-bound read: hash, size and path only | Yes |

**The one source exception.** For a registration whose role is `legacy_decision_log_entry`, the light inventory's and
the observation's `source_identity` is the `git_tracked` identity of the accepted export's retained copy, not the
vault page the registration names. This is the only exception to §6.2's rule that an observation's source matches its
registration's kind, root and path, and replay applies it only with an export identity pinned in `ACCEPTED_CL_EXPORT`
(§11.3).

**The handle-bound protocol** is W11 §7.3's (open, hash, re-check identity, close), on the repository's existing
primitives: the root anchor of `research_system/store/anchor.py` (`open_registered_root_anchor`, `:1934`) and the
member read of `research_system/discovery/dossier.py` (`_open_registered_member`, `:231-328`). That read refuses a
symlink or junction leaf and a file with more than one link, and requires the same file identity before, during and
after the read, with every parent anchor unchanged. A registration's `physical_identity` is computed from the same
identity calls.

**Line endings (verified).** The dual read of a tracked legacy file could refuse if Git converted line endings on
checkout. At `1f0d8281`, `.gitattributes` sets `* text=auto eol=lf`, and `git ls-files --eol` gives 3,630 files with
`i/lf w/lf`. Only two tracked files have CRLF in the index, and neither lies under `results/`, `.apm/` or `papers/`.

### 7.2 The window (O-33, W9-T6)

At commit, under the lock and after the shadow run of §6, the preparer re-reads every source the row binds. Any
change aborts the command with no event and no receipt. The rows that re-read are LR-005 (the physical identity),
LR-010 (`applies_to`), LR-014 (the inventory's source), LR-015 (the read itself), LR-016 and LR-020 (every item's
source must still equal its observation).

**The gap after the final re-read.** The writer lock covers the control, authority and ledger roots
(`legacy/runtime.py:241-245`), not the registered source, and nothing can lock a vault or untracked file against an
outside editor. So a change after the final re-read and before the append is committed. The note reads 06v's O-33
line ("A change aborts with no event") as follows:
- **The observation records one real moment.** The recorded `source_identity` hashes, and the frozen copy of §7.3, are
  taken from the bytes of the final re-read itself, not from an earlier read. Any change up to that re-read aborts with
  no event and no receipt.
- **A later change is a change after the observation.** It cannot be told apart from a change just after the commit,
  and §4.2 item 3 of W9 treats it the same way: the observation becomes stale. The acceptance re-reads every item's
  source at LR-016 and LR-020 and refuses an item whose source re-reads differently, or that is stale in the
  projection, so no acceptance rests on bytes that changed before its final re-read.
- **For `git_tracked` sources the recorded bytes cannot move,** because they are the blob at the binding's
  `git_head` (§11.2). A working-tree edit makes the checkout dirty, which the binding refuses at the next command.
- **The same gap at LR-020: acceptance binds the recorded bytes.** LR-020's final re-read has the same gap before its
  append, and no catalogue row can undo an appended acceptance. So the acceptance accepts the observation's recorded
  bytes, named by its `source_identity` hashes and kept in its frozen copy (§7.3) or, for `git_tracked`, the blob, and
  not the live file. A change after LR-020's final re-read is therefore a change after acceptance: the next
  observation of the registration records the new hash, and the accepted record projects as stale (below). What
  follows from a stale accepted record (adoption suspension) is WP9.4's.
- **LR-020 re-checks the frozen copy, and its retention is a known limit.** At LR-020's final re-read, for each
  `untracked_file` or `vault_file` item, the kinds that have a frozen copy, the preparer also reads the copy through
  `ControlRootArtefactContentReader`, as LR-015 does (§7.3), and requires the observation's `sha256` and
  `byte_length`. A missing or altered copy aborts the command with no event and no receipt. A `git_tracked` item
  reads the blob at the binding's `git_head`, and a `restricted_untracked_file` item has no copy to check (below). So
  the copy held the recorded bytes at the re-check. The writer lock is advisory and does not cover a deletion from
  outside ARS, so from that re-check onward, including the moment before the append, ARS keeps the copy in the
  control root but cannot stop it being deleted or altered, and no ARS mechanism retains a second copy. Every later
  use of the artefact re-hashes it (`artefacts/use_resolver.py:317`), so a lost or altered copy is detected, not
  prevented. Recovering one, from a backup or from the source if it still matches, is an owner operation. This is a
  known limit (§18).
- **A restricted source is accepted by hash only.** A `restricted_untracked_file` observation records hash, size and
  path, and the ARS store holds no copy (§7.4; W9 §5.4). Its acceptance binds those recorded values. After a change,
  ARS cannot return the accepted bytes; whoever holds them can still verify them against the recorded hash, and the
  record's fixed non-inference, "no frozen copy in the ARS store", says so. The next observation makes the record
  stale, as for the other kinds. No restricted byte enters the store.

Stephen chose these readings on 2026-11-08. One control injects a mutation between LR-015's final re-read and the
append: the observation commits with the re-read's hashes; LR-016's re-read then finds different bytes and refuses
with no event and no receipt, and the projection does not mark the observation stale, since no later observation
records the change (below). A second
injects one between LR-020's final re-read and the append: the acceptance commits naming the observation's recorded
hashes, the frozen copy still hashes to them, and a following observation of the registration records the new hash
and makes the accepted record stale. The same control runs for a restricted source, with no frozen copy to check.
A third deletes, and separately alters, an `untracked_file` item's frozen copy before LR-020's re-check: the command
aborts with no event and no receipt. A restricted item in the same batch is not refused for having no copy (§17).

**Stale observations are projected, from recorded observations only.** An observation, open or accepted, is stale
when a later recorded observation of the same registration holds a different blob (`git_tracked`) or SHA-256 (other
kinds). Replay projects only that. An acceptance-time re-read that finds different bytes is a preparer refusal: the
LR-016 or LR-020 command aborts with no event and no receipt, so replay cannot see it, and the projection does not
mark the item stale. The change becomes visible to replay when a new observation of the registration records the new
bytes. LR-016 and LR-020 refuse an item that is stale in the projection or whose source re-reads differently. So a
blob change blocks every open observation that binds the old blob (W9 §4.2 item 3). Adoption suspension is WP9.4's,
and no WP9.3 row creates an adoption or a transition.

### 7.3 Frozen copies: a seam 06v does not list

The schemas give `untracked_file` and `vault_file` a required `frozen_copy_ref`, which is an `artefactRef` (`art_`).
The W9 runtime cannot register an artefact: `RegisterArtefact` is a generic command, and D-2 keeps W9 on its own
append site. So:
1. the observer first registers the copy through the generic `RegisterArtefact` path, with `root_id: control`
   (`.research-system/schemas/core/commands/register_artefact.schema.json:114-135`, required `:197-201`);
2. the observation names that artefact;
3. the LR-015 preparer resolves the ref in the replayed generic projection, reads the bytes through
   `ControlRootArtefactContentReader` (`research_system/artefacts/runtime.py:32-51`), and requires them to hash to the
   observation's `sha256` and `byte_length`. The ref's `content_hash` is read as the artefact's `content_sha256`.

This needs no core schema change: the fields exist. Replay checks the ref's shape only; the byte check needs the
artefact store, so it is the preparer's. WP9.7's `RegisterArtefact` guard refuses restricted suffixes, which the
frozen-copy kinds already refuse by schema.

Two consequences, from the review's reading of the seam (review i-5; it was not run):
- `LegacyRuntime._replay` discards the generic projection today (`legacy/runtime.py:283`). It must return it, so that
  the LR-015 preparer can resolve the artefact.
- The code PR's frozen-copy test runs the seam end to end on a scratch store, with a non-owner observer. No live
  `untracked_file` or `vault_file` observation runs before WP9.7's `RegisterArtefact` guard (O-22) lands.

### 7.4 Restricted bytes (O-22, reader half; W9-T11)

- The reader refuses a frozen copy for `restricted_untracked_file`, at the schema and at the reducer
  (`refuse_restricted_frozen_copy`, `replay/reducers.py:93-108`).
- It records hash, size and path only.
- A path with a D-9 suffix can be read only as restricted (schema).
- It adds no content test. `.csv.gz` and `.pickle` are a question for D-9's committed list, which is Stephen's (§3
  row 11).

**Non-inferences** are fixed strings, per identity kind, so that every observer writes the same ones:
- every kind: "no authority from file presence (W0 §4)";
- `untracked_file` and `vault_file`: also "no Git identity";
- `restricted_untracked_file`: also "no Git identity" and "no frozen copy in the ARS store" (W9 §5.4).

### 7.5 The importer identity

`importer.tool_id` is `research_system.legacy.reader`, `tool_version` is the module's version constant, and
`tool_sha256` is the SHA-256 of `canonical_bytes` over `{repository path: Git blob}` for the reader and segmenter
modules at the binding's `git_head`. The preparer fills it (§5.1). Replay checks its shape only: replay must give
the same answer over an old ledger after the reader's code changes, so it cannot compare the value with today's
modules.

## 8. Selectors and inventories

### 8.1 The runtime segmenter (owner point I)

`research_system/legacy/segmentation.py` implements `w9-segmentation/1.0.0` for the runtime. The reference
implementation, `tools/w9_segmentation.py`, stays as it is: it is accepted at blob `43e1454d` (P-068 correction) and
stays non-runtime (P-067 item 2). Importing it from `research_system/` would make it runtime code. The contract's
vectors (`tests/tools/test_w9_segmentation.py`) run against both implementations, and a differential test compares
the two on generated inputs from a fixed seed. Where they disagree, the contract governs (contract §7).

### 8.2 JSON families (W9-T2, W9-T3)

- **Parsing** follows template §3 rule 1: a duplicate key anywhere blocks; `NaN`, `Infinity` and `-Infinity` are
  accepted as numbers and recorded; any other departure from RFC 8259 blocks. Python's `json` does not meet the rule
  by default (review m-5), so the reader adds these checks, each with a vector:
  - the bytes are decoded strictly as UTF-8, and a BOM or any other encoding blocks (`json.loads` on bytes accepts a
    BOM and UTF-16);
  - duplicate keys are refused through an `object_pairs_hook` (`json.loads` keeps the last one silently);
  - the three non-finite tokens are detected at token level with `parse_constant`, and recorded. A finite literal that
    overflows to infinity, such as `1e400`, is a valid RFC 8259 number that `parse_constant` never sees, so it blocks:
    the template does not say how to record it;
  - a lone-surrogate escape blocks.
- **Patterns** expand against the observed pointers (template §3 rules 2 to 5). Every observed pointer is in exactly
  one family, every table pointer is present, and containers carry shape only.
- **At LR-015** the observed bytes must equal the bytes the table's `applies_to` names (template §3 rule 10). A table
  with a non-empty `unassigned` refuses the observation (W9-T3). The observation's families equal
  `selector.family_names` exactly, and each is a family of the table.
- **W9-T2** observes a committed fixture copy of
  `results/trajectory_tda_integration/stage1/usoc_headline_frozen_2026-05-28.json` under a fixture table, and its H₁
  W₂ family records `superseded`.

### 8.3 Inventories

The LR-011 proposal comes from the builder (§12.1). Each row is the segmenter's, with the inventory's selector kind
added and absent fields null (§3 row 12). The builder resolves a "from the first anchor after" region to a line range
and records both, and compares a declared region's anchor-line hashes, which are the inventory's checks under contract
§3. The LR-011 preparer re-segments the source and requires identical rows.

### 8.4 Selector binding and blockers (W9-T22)

An `inventory_item` selector names a recorded (LR-014) inventory of the same registration, and a row whose ordinal,
anchor text and raw-row hash all match and whose kind is `item`. A blocker or structural row is never observable. A
duplicate anchor stays a blocker (contract §4.3) and is never resolved by position: the ordinal locates the row, but
replay also checks its anchor text and hash.

W9-T22 builds a synthetic tracker with two rows for one task ID. Both rows are `duplicate_anchor` blockers, and LR-015
refuses an observation of either. W9-T18 is the tool-level bijection test of §12.4.

## 9. Classes, qualifiers and precedence

### 9.1 W0 classes come only from a signed record (O-27; owner point C)

Each observed family carries a `w0_class` with a `signed_w0_revision_ref` (a `sourceRef`) and a `signature_record_ref`
(an `anyRef`). The signature is L-0's (06v §7), and it does not exist yet.

- WP9.3 adds `ACCEPTED_W0_SIGNATURES` to `accepted_w9.py`, an empty tuple. While it is empty, LR-015 refuses every
  observation ("no accepted W0-D1 signature"), which is O-27's "an unsigned class refuses the observation".
- After L-0, a separate reviewed PR pins the signing record: its path, commit, blob and SHA-256; its derived ref; and
  the W0 documents it signs, by blob. Independent test literals guard the pin, as `O8_ACCEPTED` guards `ACCEPTED` (WP9.2
  note §5.1). The tuple is append-only: a later signature is added, never substituted, so that replay of an earlier
  observation still finds the signature it names.
- Then every family's `signature_record_ref` must equal a pinned ref (the latest one, at the preparer), and its
  `signed_w0_revision_ref` must be a `git_file` locator naming one of that signature's W0 documents at its signed blob.
- The ref is derived as the WP9.2 external refs are (WP9.2 note §5.3), as a `dec_` from the register entry that records
  the signature. Genesis could not reserve it. As with R-3, no reader dereferences it as a store record, and W9-C25
  refuses it as a pre-assigned ID once it is pinned.
- **When the ID becomes reserved.** At the pin, in code. From the PR that pins a signature, replay treats its ref ID
  as reserved at every ledger position, as it treats `RESERVED_IDS` (§4.3). The ID can be derived as soon as the
  register entry exists. A W9 proposal made between that entry and the pin could therefore pre-assign it, and the pin
  would then make that ledger fail replay. Two rules close the window:
  - **The first pin lands before W9 genesis (L-3) on any store.** No W9 proposal can exist before genesis. The L-3
    checklist records the pin.
  - **A later pin, made while W9 stores exist, carries a pre-pin check.** Before Stephen accepts the pin, he runs a
    read-only check over each W9 store with the candidate pin added. `replay_legacy` alone is not enough: it reduces
    W9 transactions only (`legacy/replay/driver.py:136-160`), so it would miss a W11 or generic aggregate that already
    uses the derived ID. The check therefore has two parts: the public shared replay, with the candidate pin added;
    and a scan of every event in the ledger, of any partition, that refuses the candidate if it equals the event's
    `stream_id` or any record ID the event creates, read from §4.3's created-ID table. WP9.3-1 provides the scan as a
    read-only function in `research_system/legacy/`, which writes nothing and takes no lock. **Both parts and the
    recorded head come from one snapshot.** The function materializes one `LedgerSnapshot` (`store/ledger.py:41-48`),
    runs the public shared replay and the scan over its `events`, and records its `global_position` and `event_hash`
    as the checked head. A head read separately could include an event the scan never saw, and the advance's compare
    below would then pass a colliding claim. With one snapshot, an append during the check moves the ledger past the
    recorded head, and the advance refuses. If either part finds the ID in use, the ref is
    derived again from the same domain with a `#<n>` suffix, using the next unused `n`, and the check is repeated. The
    pin records the domain it used and the check's result. Running the check is an owner operation. §4.3's writer
    guards stop a later claim of a pinned ID; they cannot remove one made before the pin, which is why the check runs
    first.
  - **Release is a binding advance (issue #415, option C).** A later pin is released on each W9 store by the existing
    owner operation `AdvanceStoreBinding` (`advance-clean-descendant-store-binding`, `store/binding_service.py:167-232`)
    to a `main` commit that holds the pin. Every later `main` commit holds it too, because the tuple is append-only.
    The store's current binding then decides which code may write to it:
    - `load_current_binding` compares the checkout's `HEAD` and tree with the binding's `git_head` and `git_tree` on
      every operation, and requires a clean worktree, untracked files included (`store/current_binding.py:847-853`).
      The binding names one code root, which the CLI takes from the running package's own location (`cli.py:119-134`),
      so the `HEAD` checked belongs to the checkout the running code came from.
    - A schema 1.2.0 binding also admits a non-exact checkout, but only a reviewed, documentation-only descendant of
      the bound commit that equals `refs/heads/main` (`current_binding.py:913-921`; `governed_code.py:784-795`). The
      pin commit changes `research_system/legacy/accepted_w9.py`, a governed file (`governed_code.py:75-77`). So after
      the advance, a pre-pin checkout is refused, because it is an ancestor of the bound commit, not a descendant; and
      before the advance, a pinned checkout is refused, because it changes governed code.
    - W11 writers already admit through the binding: production builds `DiscoveryRuntime` only in
      `SpecCoordinator._discovery` (`discovery/spec.py:339-351`), which revalidates the binding when it is built
      (`:213`) and in its operations. W9 writers admit through it once §13's `ars legacy submit` lands. W11 needs the
      cover too: W11 code from before the pin holds the old constants of §4.3's check.
    - Not covered: code that builds `LegacyRuntime` or `DiscoveryRuntime` directly (tests and scripts), and local
      administration through `--config` (`cli.py:161-167`). Neither is the dispatch path. A census test keeps
      production constructions to the two bound sites (§17).
  - **The write freeze, from the final check to the advance.** Until the advance, only pre-pin code can write, so an
    old-version writer could still claim the candidate ID after the check. So on each W9 store:
    - From the final check until the store's binding is advanced, no W9 or W11 command is submitted to the store,
      and no grant that admits a write on it is live (the grant fence, below). Stephen dispatches every write and
      issues every grant (§5.3), so the freeze is his.
    - **The pin goes in a separate checkout; the bound one does not move.** `AdvanceStoreBinding` re-admits the
      predecessor through `load_current_binding` on the predecessor's own code root
      (`store/binding_service.py:1474-1492`), so the bound checkout must still be at its bound commit when the advance
      runs; updated in place to the pin commit, it would be refused, and the store would stay frozen. So the pin
      commit is checked out in a separate, durable candidate checkout, the intent's `candidate_repository_root`, which
      the advanced binding then names as its code root (`:1605-1622`). The bound checkout stays at its commit until
      the advance succeeds.
    - **The candidate checkout is fresh, or drained before it moves.** The candidate checkout is created at the pin
      commit. If an existing checkout is reused instead, every process started from it exits before it is updated to
      the pin commit, and none starts from it until it is there. Otherwise a process that loaded pre-pin modules from
      the reused checkout would be admitted after the advance, because the binding then names that root and its
      `HEAD` matches. The pin's checklist records which case applies.
    - **The code-root check refuses the old checkout after the advance.** `load_current_binding` refuses any
      repository root other than the one the binding names (`store/current_binding.py:842`). It checks the checkout
      on disk, not the modules a process has loaded, but once the binding names the candidate root, a process still
      running from the old checkout is refused on its next admission, whatever code it holds. Before the advance, the
      same check refuses a writer from the candidate checkout.
    - **Drain the old checkout.** Before the final check, every process started from the bound checkout has exited,
      and none starts from it until the advance. That keeps an old-version writer from claiming the candidate ID
      inside the freeze. The pin's checklist records the drain. A process started outside Stephen's dispatch is not
      drained, but any write it makes before the advance moves the ledger head, which the advance refuses (below).
    - **The advance compares the checked head under its lock.** The check records the store's ledger head: the last
      global position and that event's hash. Today the advance compares only the project stream's version, between
      its own plan and its append (`store/binding_service.py:1648-1649`, `:1721-1722`), not the head the check saw,
      so a write between a manual re-read and the advance would go unseen. WP9.3-1 passes the checked head to the
      advance as a parameter of the binding service, beside the intent and not inside it, so the accepted
      `AdvanceStoreBinding` intent and command schemas do not change. The operator passes it through the supported
      command: `ars store advance-binding`, which today takes only `--intent` (`cli.py:2291-2293`, handler `:817`),
      gains `--expected-ledger-head <global position>:<event hash>`, handed to the service beside the intent. It is
      optional for other advances; the pin's checklist requires it for a pin release. The advance compares it with the
      ledger's head under its writer lock, before it writes its transaction marker. If the head moved, the advance
      refuses with no effect: the store stays frozen at its old binding, and the check is re-run for a new advance.
      W9 and W11 writers take the same control-root lock (`legacy/runtime.py:241-245`,
      `discovery/runtime.py:194-198`), so no write lands between the compare and the advance's event, whose global
      position is then the checked head's plus one; the pin's record shows both. An advance resumed from its marker
      after a crash compares again. The compare passes if the head is the checked head, or the checked head followed
      by exactly one event, this advance's own (`command_id` `binding-advance-<payload hash>`, which the advance
      already looks up through `_binding_event`, `:1718`), so a crash after the event's append recovers. Any other
      moved head refuses, and Stephen rules on the marker, because the advance had already begun.
    - **Writers recheck the binding under their lock.** The head compare cannot see a write that has not happened
      yet: a writer admitted before the advance could pause and append after it. W11 rechecks the binding at the
      start of each operation (`discovery/spec.py:331`, `:355`, `:699`), before `DiscoveryRuntime.submit` takes its
      writer lock (`discovery/runtime.py:194-198`). So WP9.3-1 has `LegacyRuntime` and `DiscoveryRuntime` each
      recheck the current binding inside the writer lock, immediately before append. It does the same in
      `CommandService`: `_submission_lock` (`command/service.py:1875-1915`), which both the generic `submit`
      (`:1385`) and `submit_t2` (`command/t2.py:1020`) take, rechecks the binding after the lock is taken and before
      the snapshot it hands out, through a binding check the CLI passes in where it builds the service
      (`cli.py:890-915`). Revision 11 covered only the W9 and W11 runtimes, which left the generic and T2 writers,
      grant-free ones included, able to append after the advance on WP9.3-1 code. A census test lists every
      `CommandService` site that takes the control-root writer lock and can append, `with_locked_authority`
      (`:1917`) and the scoped-activation recovery lock (`:1030`) included, and fails on one without the recheck. A
      process on pre-pin code that admitted before the advance is then refused on resume by the code-root check,
      and a writer holding the lock blocks the advance until it has appended, which the head compare then sees.
    - **A later pin's predecessor already holds WP9.3-1.** A later pin is made only on W9 stores. W9 genesis waits
      for the first pin (above), and the first pin is an entry in `ACCEPTED_W0_SIGNATURES`, which WP9.3-1 adds
      (§11.3). Bindings advance only to descendants. So the binding a later pin advances from holds WP9.3-1's code:
      the in-lock recheck and §4.3's identity checks. A writer without them is one paused since before its store
      first bound WP9.3-1 code, which is before W9 genesis on that store.
    - **The grant fence covers such a writer when it holds a grant.** Admitted before the advance and outside the
      drain, it takes its lock and a fresh snapshot after the advance (`discovery/runtime.py:194-198`, `:474`) and
      can append, claiming the pinned ID. But every W9 and W11 writer, and every generic lifecycle writer
      (`_LIFECYCLE_COMMAND_TYPES`, `command/service.py:251-261`, `:1397-1400`), resolves the grant its command names
      (`authority_grant_id`) under the writer lock, from one fresh replay of the authority store
      (`authority.py:2691`; `legacy/runtime.py:241-246`, `:259`; `discovery/runtime.py:194-199`, `:260`;
      `command/service.py:1385-1400`). That replay refuses a revoked or expired grant (`authority.py:2260-2265`,
      `:2505-2512`), and predecessor code already does it. So, from before the final check until the advance, no
      grant that admits a write on the store is live: each is revoked or has expired before the check, and new
      grants are issued only after the advance. A paused predecessor operation carries its old grant's ID in its
      envelope, so on resume it is refused under the lock before any append, whichever checkout it runs from.
    - **Known limit: a grant-free command paused since before WP9.3-1.** A command type whose grant is not resolved
      against the authority store is not fenced. `VerifyEvidenceDeletion` is one: production `ars submit` wires its
      authorizer when given `--evidence-store-registry` (`cli.py:909-915`), the authorizer validates a deletion
      manifest and takes the envelope's grant ID without resolving it (`evals/retention_authorizer.py:175-188`,
      `command/service.py:6895-6906`), and its target stream is the caller's, a `dec_` in the existing test
      (`tests/research_system/unit/test_retention.py:328`). On WP9.3-1 code the `CommandService` recheck refuses it.
      On older code it is unfenced, but only if it has been paused since before its store first bound WP9.3-1 code.
      WP9.3-1's census names each grant-free type that can create an ID in §4.3's created-ID table, and the pin's
      checklist lists them as this known limit. Such a claim is caught by the first replay on the pinned code
      (below), and recovery is Stephen's ruling.
    - If a collision is found before the advance, the ref is re-derived in a follow-up commit, which replaces the
      unreleased entry. No store is bound to it, so no writer ran it and no record names it, and replacing it breaks
      no replay; the append-only rule exists to protect exactly that.
    - If a claim lands anyway, through a path the binding does not cover (above), the first replay on the pinned code
      refuses the ledger (the cross-pin control below). The store then refuses writes rather than being silently
      corrupted. Recovering from that after the advance needs Stephen's ruling, because the replace-before-release
      rule no longer applies.

  Revisions 4 and 5 said code could not refuse an old writer after release, citing `validate_persisted_governed_code_manifest`
  (`store/governed_code.py:551-553`). That function checks historical links in the binding chain
  (`current_binding.py:908-912`), not the current admission, so the premise was too narrow (issue #415's findings).

  A ledger that claimed a pinned ID anyway fails closed. The controls (§17):
  - a proposal pre-assigning a pinned ID is refused;
  - a forged ledger that claimed the ID before the pin replays under the earlier pin set and fails under the new one
    (the cross-pin control);
  - a re-derived `#2` ref is accepted.

Whether a family's class is the class the signed W0 record gives that object is the reviewer's question (W9 §8.1 step
2), not code's.

### 9.2 A status word never yields acceptance (W9-T1)

No code path derives a class, an acceptance or an adoption from source text. Classes come only from the payload,
checked as §9.1 says and by the reviewer. The test observes a synthetic `Done` tracker row, and shows that no
acceptance or adoption event follows and that the record's class is the payload's whatever the row's text says.

### 9.3 Qualifiers (W9-T13)

- The four kinds are typed (schema).
- A `corrected_by` qualifier's `source_ref` must name the canonical source by precedence tier 1 (W9 §6.4): either a
  `recordRef` to a recorded observation of a registration whose role is `legacy_research_result`,
  `legacy_pre_registration` or `legacy_contract`, or a `git_file` locator to a registered path with one of those roles.
  A source in a decision-log entry, the tracker, a log or a vault note is refused for `corrected_by`, because a
  correction entry's prose is never the value source (W9 §6.4's H10 example). That the named file is the right one is
  the reviewer's question.
- The other kinds take any source kind the edge table admits.
- A `git_file` locator's `line_span` has `first_line` ≤ `last_line` (stage A i-2).

### 9.4 Precedence (W9-T4)

The schema already requires a tier for a conflict `resolved_by_precedence` and forbids one for a `blocked` conflict.
Replay adds:
- a `stale_projection` family carries at least one conflict naming the observed record and a stronger one;
- an item whose observation holds a `blocked` conflict cannot be accepted (W9 §13.4: "a precedence conflict is
  unresolved").

The tier itself is the reviewer's question.

**The W9-T4 fixture.** Lines 69 to 71 of `results/trajectory_tda_integration/stage1/SUPERSEDED.md`, copied from blob
`ee7557ad` into a fixture file of exactly those lines, with a manifest naming the source path, blob and line span.
That blob is the file before PR #401 (`633ed58e`), which appended a dated UNVERIFIABLE update after line 71. Copying
from the earlier blob tests what W9-T4 states, the lines alone. The observation records `stale_projection`, with a
conflict naming those lines and `w2_gap_closure_phase1_2026-07-16.json`, resolved at tier 1, and the summary's W₂
family `unverified`.

## 10. The closed-reference acceptance (LR-016 to LR-020)

### 10.1 The batch

- Items are unique, one per observation. Each observation is recorded, is the latest for its source and selector, and
  is accepted by no earlier batch.
- The first batch only (§2.1): no acceptance is recorded yet, and the batch holds at most 20 items.
- **Both batch rules are checked again at LR-020** (review M-1). Without that, two batches proposed before either
  resolved could both resolve: one item accepted twice, and the second batch admitted without the integration-pilot
  outcome Decision the annex requires for any batch after the first. A test proposes two batches sharing an item and
  shows the second resolution refused at replay.
- The review also offered "one open batch at a time" at LR-016. It is not adopted. One abandoned proposal would block
  every later batch until it lapsed, which can take up to 60 days (§4.6), and the LR-020 re-check already closes the gap.
- §4.5's closed-reference column. The machine part: genesis, the pinned W0 signature (§9.1), and the detector controls
  (LR-003 already required them before the first registration). The rest (Gate 7 opened; G7-A, G7-B and G7-C
  accepted) are owner facts, which go on the L-4 checklist.

### 10.2 `pilot_promotion` (O-37; owner point K′)

- Each item lists each fixture at most once (stage A §3).
- LR-020's accepted set (`wp9-1-catalogue-owner-annex.yaml:729-743`, and the same seven entries in the catalogue) is:
  - **on every item:** F-018, F-023, F-037 and S-014;
  - **when the condition holds:** F-017 (a sensitivity or comparison file), S-005 (two results compete for one object)
    and F-038 (the item uses the TDA pack's lanes).

  The preparer and replay require the four unconditional fixtures on every item. Code cannot decide a `when`
  condition, so the reviewer marks each conditional fixture's applicability, and Stephen's batch Decision fixes it (W9
  §12.3). Revision 1 read the row only to line 735 and listed three fixtures; the review's B-1 corrected it, and the
  owner point that rested on the misreading (K) is withdrawn.
- A `waiver` ref is a `dec_` (schema). An `evidence` ref is a `rev_` or an `art_`: a review that graded the fixture,
  or an artefact holding the graded run.
- Applicability is proposed by the reviewer and fixed by Stephen's batch Decision (W9 §12.3). In the flow the analyst
  writes the proposal, the reviewer approves its exact hash (§5.4), and Stephen resolves on that hash. A change of
  applicability is a new proposal (LR-020).
- S-007 is listed on every review row with no condition. It is met mechanically by the W9-C22 controls, not by refs.
- Whether a ref is sufficient evidence is the reviewer's and Stephen's question.

**S-014's timing (owner point K′).** W9 §12.3 assigns S-014 (backup, restore, machine move) as "re-run after each W9
batch". But the batch's `pilot_promotion` refs must exist at LR-016 and LR-020, before the batch is accepted. So a
per-item S-014 ref can name only a restore run made before the batch, or a waiver. The recommended reading: the S-014
ref names the latest restore run before LR-020, and the post-batch re-run W9 §12.3 requires goes on the L-4 checklist
(06v §7's "after every batch: replay and restore").

**S-014's freshness at LR-020.** The proposal binds the S-014 ref at LR-016. A restore run made between LR-016 and
LR-020 makes that ref stale without changing the proposal's hash. No record kind identifies a restore run, so code
cannot tell which `art_` or `rev_` is the latest one. The check is therefore Stephen's, at resolution, and is an L-4
checklist line: "No restore run has been made since the run each item's S-014 ref names." If a later run exists,
Stephen does not resolve, and the analyst re-proposes the batch with the newer ref. A change of evidence is a new
proposal, as a change of applicability is. This is recorded, not proved (§18).

### 10.3 Thresholds and anchors (O-25, W9-T16; owner point G)

- Both hashes are present, and there is one anchor for each (schema).
- A `git_commit` anchor holds when the commit is an ancestor of the binding's `git_head` (`git merge-base
  --is-ancestor`), and the commit adds or changes a file whose bytes hash to the anchored SHA-256. That is what W9
  §14.3's "the hash is anchored in a Git commit" requires: the commit's ancestry gives the time, and its content gives
  the binding to the hash.
- Both are checked at LR-016, and again at LR-020 against the binding at resolution.
- An `ars_event` anchor is refused in v1 (owner point G), for simplicity: one anchor kind and one test. Revision 1
  said such an anchor would need a new event family. That was wrong (review m-9): an `ArtefactRegistered` event
  carries `content_sha256` (`.research-system/schemas/core/events/artefact_registered.schema.json`), at a global
  position, under the generic `RegisterArtefact` path §7.3 already uses. The alternative is an `ars_event` anchor
  naming an `ArtefactRegistered` event at a lower global position whose `content_sha256` equals the anchored hash.
- W9-T16's controls: a threshold commit that is not an ancestor of `git_head` at LR-020, and an ancestor commit that
  does not introduce the hashed bytes. Each invalidates the batch.

### 10.4 Shared-surface changes (O-32)

- `enforcement_change_list` names the list's commit and blob, and must equal the list at the binding's `git_head`.
- For each list entry and each item whose registration is among that entry's affected results, the item is refused
  when the entry's merge commit is not an ancestor of the observation's source `git_commit`. An affected item that is
  not `git_tracked` cannot be ordered against a commit, so it is refused too.
- The list is WP9.5's, and it does not exist yet. While it is absent at `git_head`, LR-016 refuses. The schema's
  `null` is therefore never accepted in v1, because "no list" cannot be told apart from "no changes recorded".
- The test uses fixture lists with and without an entry affecting an item (06v O-32).

### 10.5 The ownership records (owner point E; F-8, second limb)

**The gap.** LR-016's precondition reads "the proposal lists, with pre-assigned IDs and full content, every
legacy-ownership-transitioned record the resolution will emit" (`wp9-1-catalogue-owner-annex.yaml:567`). But the
proposal event's payload is the acceptance record, validated against its schema (`replay/driver.py:54-67`), and that
schema is closed and has no field for ownership records: `additionalProperties: false`, and the word "ownership" does
not occur in it. LR-016 emits one event (`legacy/routes.py:140-145`). So the precondition cannot be met as written
without a catalogue change.

**The recommended reading: derived, not listed.** Every ownership record LR-020 emits is a deterministic function of
the acceptance proposal and the projection at the proposal's position:
- one per item whose observation covers the whole file (`whole_file`, or the complete family set of the file's
  accepted membership table), when the registration's mode is `legacy_owned` (P-072 item 2);
- `record_id`: an `obj_` UUIDv7 built as WP9.2's external refs are (WP9.2 note §5.3, steps 2 to 5), from the domain
  string `w9-ownership:<acceptance record ID>:<registration record ID>` and the proposal's `created_at` in
  milliseconds;
- `created_at` and `created_by_actor_id`: the proposal's (annex line 20);
- `subject_registration_ref`: the observation's registration; `mapping_ref` and `paper_root_ref`: null;
  `from_mode: legacy_owned`, `to_mode: closed_reference`;
- `reviewer_ref` and `decision_ref`: the acceptance's `independent_review_ref` and `decision_ref`;
- `content_hash`: by §4.1.

At LR-016, replay computes this list, reserves its IDs (§4.3), and stores it with the proposal. At LR-020 the emitted
ownership records must equal the stored list exactly, and the list recomputed at LR-020's position must equal it too.
Stephen's Decision binds the acceptance's content hash, which together with the ledger before LR-016 fixes the list.
No hash depends on itself, and the list cannot change between proposal and resolution, which is the purpose of the
re-review M-1 text. The review packet shows the derived list, and the builder tool prints it. The review found the
derivation deterministic and distinct across batches (review §2, item 5).

**One whole-file item per registration.** A batch could hold a `whole_file` observation and a complete-family-set
observation of the same JSON registration, since their selectors differ. Both would derive the same ID, and the second
transition would be refused anyway (review m-2). LR-016 therefore refuses a batch with two whole-file items of one
registration, so that the annex's "one per accepted whole-file observation" and the derivation agree.

**An alternative the review offered.** The derived records' IDs and hashes could also be listed among the LR-017
review's subjects, so that the hashed bytes the reviewer and Stephen act on contain the list itself. That would widen
§5.2's single-subject request for this one row. It is shown to Stephen under owner point E; the recommendation does
not need it, because the list is a function of what the Decision already binds.

### 10.6 LR-020

G5 (§6.1), the ownership list (§10.5), and the window, anchors and change list re-checked against the binding at
resolution. Each emitted ownership record then applies through `_apply_ownership` (`replay/reducers.py:287-301`), which
already holds LR-020 to the one direction `legacy_owned → closed_reference` (`:34-38`). The ownership record's
`reviewer_ref` and `decision_ref` are the acceptance's refs copied exactly, pre-assigned hashes included, and replay
checks them against the acceptance's record ID (§4.2).

## 11. Inputs from outside the store

### 11.1 The W9 evidence area (owner point D)

06v names "the W9 evidence area" six times and never gives its path. WP9.3 is the first package that reads it. The
recommended path is `.research-system/evidence/w9/`, beside the other machine-read W9 data. It is tracked: `git
check-ignore` matches nothing there.

WP9.3 fixes the reader-side formats as closed JSON, validated by `research_system/legacy/evidence.py`. They are not
`ars://legacy/` schemas, because the W9 schema directory is pinned to its 19 owned files
(`tests/research_system/contracts/test_w9_contract_materialization.py:316-318`), and a new schema there would be a new
catalogue identity.

| File | Producer | WP9.3 reads it at |
|---|---|---|
| The registration manifest (06v M-6) | WP9.5, per batch | LR-015: the registration is listed |
| The detector control-output hash files (D-5, O-13) | WP9.5 | LR-003: every §4.4 detector's negative control watched to fail |
| The shared-surface change list (O-32) | each PR that changes a shared surface | LR-016, LR-020 |
| The Computational-Log export and its retained copy (D-7) | The reference implementation, `tools/w9_segmentation.py`, at L-0b (contract §6.1) | LR-011 and LR-015, through the pinned identity (§11.3); rechecked by WP9.3's runtime segmenter (§12.2) |
| The `.apm/bus/` and `.apm/` inventories (O-19, O-36) | WP9.3's tools, at L-5 | Nothing in v1: no store record (P-071 item 4) |
| The D-9 suffix list | WP9.7 | Nothing: the schemas carry the copy (P-069 item 3) |

Every file is read from Git at the binding's `git_head` (`git show <git_head>:<path>`), never from the working tree. A
row whose file is absent refuses. WP9.5 then writes these formats, and a change to one is a change to WP9.3's reader,
reviewed with it.

### 11.2 The binding's `git_head`

The CLI loads the binding through `load_current_binding` (`research_system/store/current_binding.py:801`, giving a
`VerifiedCurrentBinding`, `:761`) and passes it to `LegacyRuntime`. A `git_tracked` read compares the working tree with
`<git_head>:<path>`, so the reader refuses unless the repository's `HEAD` is the binding's `git_head`. This is the same
discipline as WP9.2-2's R-1 for L-3.

### 11.3 Accepted identities from outside the store (owner point C)

`accepted_w9.py` gains two empty, append-only tuples: `ACCEPTED_W0_SIGNATURES` (§9.1) and `ACCEPTED_CL_EXPORT`, whose
entry is the export's identity and its retained copy's, together with Stephen's classified entry list. Each entry is
added by its own reviewed PR after Stephen's acceptance, with independent test literals. Until then, LR-015 refuses
every observation in production, and LR-011 and LR-015 refuse a Computational-Log registration in any case. Tests
inject values, as the runtime's `accepted_revisions` parameter does today (`legacy/runtime.py:159`). The
`CONVENTIONS.md` baseline needs no constant: the accepted segmentation contract fixes blob `4620c716` (contract §3, the
`conventions_unit` row).

## 12. Tools

Every tool reads its inputs and writes only to an output path the operator names. Each refuses an output path under
`.apm/`, under the vault, or inside a store, and none opens a store. They live in `research_system/legacy/` and run as
`ars legacy` subcommands, so WP9.3 adds no `tools/` file (owner point J).

### 12.1 The light-inventory builder

- **Build mode** produces an LR-011 proposal's content from the bytes of a registered source (§8.3), and prints the
  derived ownership list when it builds a batch (§10.5).
- **Reproduction mode** re-segments the same bytes (the Git blob, or the frozen copy) and reports row-by-row equality.
  LR-013's reproducer uses it.
- It does not compute observation IDs: that needs the store's projection, which no tool opens. The read-only `ars
  legacy observation-id` command does (§13).

### 12.2 The Computational-Log export and its recheck (D-7; O-21)

The export and its check must come from two implementations (review M-4). Segmentation contract §6.1 has the export
read by the reference implementation, and §6.3 has WP9.3's reader re-segment the retained copy. If one module produced
the export and also rechecked it, a defect in that module would certify its own wrong hashes. So:
- **The export is produced by the reference implementation,** `tools/w9_segmentation.py` (blob `43e1454d`, P-068), at
  L-0b, as contract §6.1 says. WP9.3 adds no export mode. The export carries every row the segmentation gives for the
  legacy region (items, structural blocks and blockers), each with its hash and offsets; the read times, the path
  form, the retained copy's SHA-256 and size, and the read's recorded limits; a classification slot per row for L-0b's
  classified list (P-068 item 4); and the producing implementation's path and blob.
- **WP9.3 fixes the export's format** (`research_system/legacy/evidence.py`, §11.1) and provides the **recheck**: the
  runtime segmenter re-segments the retained copy and compares every row with the committed export. Any mismatch
  reports the export void (contract §6.3). The recheck refuses an export whose recorded producer is the runtime
  segmenter itself.

Nothing runs on the live log, because L-0b is not authorized. The tests use synthetic logs, with exports produced by
the reference implementation.

### 12.3 The `.apm/bus/` inventory (O-19)

A dated, handle-bound list of the directory's files: name, size and SHA-256. It is the non-import record W9 §13.3 item
2 asks for, written as a file. In v1 it has no store record (P-071 item 4).

### 12.4 The `.apm/` file-level inventory (O-36; W9-T18)

It lists the tracked files at a commit (`git ls-files .apm` gives 34 at `1f0d8281`, the count W9 §13.3 item 5 states),
the untracked `.apm/memory/stage-NN/` logs and the bus directory. It maps each file to exactly one closure (a light
inventory plus accepted observations) or one non-import record. A missing or extra file or item, or a blocker row left
in a closure, blocks. File closure is deferred (P-071 item 4), so in v1 W9-T18 is this tool's test (stage B note §5),
run on a synthetic `.apm/` tree.

## 13. The CLI (F-4)

`ars legacy submit <envelope.json>` is the one mutating subcommand. It:
1. refuses with `refuse_gate6_lock_roots` (`legacy/runtime.py:104-128`) over the target control root and every other
   root the command will lock that is known before binding: the W9 receipt root, and the authority root where the
   configuration names it;
2. only then loads the binding through `load_current_binding` (`store/current_binding.py:801`), which gives the
   `git_head` §11.2 needs, and builds the ledger from it with `create_directories=True`, inside the refused-and-cleared
   control root only (review §2, item 6);
3. builds `LegacyRuntime` with the store's control root as its receipt root, as Discovery does
   (`discovery/spec.py:341-342`);
4. submits through `LegacyRuntime.submit`, which runs its own refusal again before the lock
   (`legacy/runtime.py:231-237`).

This keeps F-4 ("run `refuse_gate6_store` on the target control root before `_verified_ledger`") and widens it from
the control root's own manifest to the ancestor scan the runtime uses. Step 2 also carries §9.1's release of a later
W0 pin: because every submit admits through the store's current binding, a W9 writer on a commit the binding does not
admit is refused before it replays or appends. The read-only `ars legacy` binding
(`cli.py:1513-1521`) is unchanged; `ars legacy observation-id`, below, reuses it.

**A dependency on D-1 (review m-7).** `load_current_binding` requires a clean worktree, untracked files included
(`:852-853`); `HEAD` at the binding's `git_head` unless the binding is schema 1.2.0 (`:847-851`); and a foundation that
names the target store (`:822-827`). Today's foundation names the Gate 6 store (`.research-system/config/foundation.yaml:4-6`),
so no mutating W9 command can bind a non-Gate-6 store until D-1's foundation re-pin (06v §2.6). The tests stub the
foundation, as tests that read it must.

**The test binds a real scratch store,** not a monkeypatched `_verified_ledger` (§3 row 7). A Gate 6 control root, and
a scratch control root nested inside one, are each refused with every root byte-identical afterwards, directories
included. A valid scratch store accepts the command.

The tool subcommands (`inventory build`, `inventory reproduce`, `export recheck`, `apm-inventory`) open no store.

**`ars legacy observation-id`** is a read-only store command, not a tool. Given an observation envelope and a control
root, it runs through the existing read-only binding `_legacy_projection` (`cli.py:1513-1524`): `refuse_gate6_store`
first, then `_verified_ledger(read_only=True)`, the public replay and `replay_legacy`. From that projection it takes
the registration's `created_at` and the observation count `n`; it reads the source bytes as the preparer would; and
it prints the derived `record_id` of §5.3. It appends nothing, takes no writer lock and writes no file. Its test
leaves a scratch store byte-identical, refuses a Gate 6 control root before binding, and prints the ID the preparer
then derives.

## 14. Reducers: kept and changed

| Function (`replay/reducers.py`) | WP9.3 |
|---|---|
| `reduce_genesis`, `reduce_revision`, `claim_identity`, `_add_edges`, `_apply_ownership`, `refuse_restricted_frozen_copy`, `ownership_transition_allowed` | Kept |
| `reduce_proposal` (`:199-212`) | Changed: recomputes the hash; claims the pre-assigned IDs; checks the pre-assigned ref hashes; runs each family's proposal checks of §6.2; for LR-016, derives and stores the ownership list |
| `reduce_review_request` (`:215-228`) | Changed: one paired subject naming an open proposal at its recomputed hash; the proposal's reservation as the review ID; one named reviewer; §5.5's distinctness |
| `reduce_review_verdict` (`:231-241`) | Changed: the verdict's actor is the named reviewer, and its subject hash is the request's and the current one |
| `reduce_decision_proposal` (`:244-256`) | Changed: the subject encoding; the proposal's reservation as the Decision ID; `migration_authority`; the review satisfied where the family has one |
| `reduce_decision_resolution` and `_record_resolved` (`:263-345`) | Changed: G5 of §6.1; for LR-020, the stored ownership list in place of each ownership record claiming its own ID (`:275-278`) |
| `reduce_light_inventory` (`:348-379`) | Kept, as record §3 item 8 built it, with the hash recomputed before the subject check (`:375`) |
| `reduce_record` (`:382-405`) | Changed for observations only: the checks of §6.2 LR-015. Paper roots, citation status and use mismatches are unchanged (other packages) |
| `_apply_supersession` (`:304-317`) | Changed: refuses a superseded ref that names no recorded record (§3 row 5) |

`replay/driver.py` changes only by factoring its loop body into the per-transaction step that the preparer's shadow run
reuses (§6; review m-6). Its checks do not change. The four U-7 sites and `legacy/commands.py` do not change. W11's
admissible-target check gains §4.3's symmetric W9 identity check. That is a preparer check beside U-7 site 2 in
`discovery/routes.py`, not a change to the site.
`legacy/routes.py` changes only its routed set and tags, and the partition check of §15.

## 15. Genesis guard 8 and the route partition (owner point F)

`validate_legacy_route_registry` requires exactly 1 routed and 60 deferred rows (`legacy/routes.py:644-645`), and
genesis guard 8 calls it (`legacy/runtime.py:523`). Routing WP9.3's rows changes the partition in each PR: 14 routed
and 47 deferred after WP9.3-1, and 19 and 42 after WP9.3-2.

**The change.** The function checks that the routed and deferred sets partition the accepted rows exactly, with no
overlap and every deferred tag valid. The counts and the tags are pinned by the route test for each PR, not written
into the guard.

**The consequence.** This changes the genesis code path that WP9.2-2's independent review verified, and LR-001's L-3
precondition rests on that verification ("the bootstrap implementation independently verified against the accepted
contract"; P-079, "Not decided here"). Both PRs change guard 8's input (review m-8). So each PR's independent review
re-verifies the genesis path at its head, and the L-3 checklist records which review verified the genesis code at the
checkout L-3 runs from (with R-1), whichever PR that is.

## 16. Binding rows, authority entries and D-4

**At WP9.3-1:**
- seven `SchemaBinding("ars://core/command", "1.0.0", command_type=…)` rows, one per command of §2.2;
- four producer bindings, by C2 (WP9.2 note §2.3): `ReviewRequested` under `RequestW9AuthorityReview`,
  `ReviewVerdictRecorded` under `RecordW9AuthorityReview`, `DecisionProposed` under `ProposeW9AuthorityDecision`, and
  `DecisionResolved` under `ResolveW9AuthorityDecision`, each with its `ars://core/event/<type>` schema, following
  W11's rows (`schema_registry.py:275-292`, `:444-449`). `E:` events keep the `ars://core/event` fallback;
- `research_system/authority.py`: each of the seven commands in `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` (`:171-207`)
  and with its §5.3 subject kind in `_SCOPED_COMMAND_SUBJECT_KINDS` (`:209-333`). These entries are not a protected
  identity (WP9.2 note §3);
- `research_system/discovery/routes.py` and `research_system/discovery/runtime.py`: the symmetric W9 identity check in
  W11's admissible-target check (§4.3), and in `discovery/runtime.py` the binding recheck inside the writer lock
  (§9.1). They add no binding row and change no protected identity;
- `research_system/command/service.py` and `research_system/command/t2.py`: the same check at the two generic append
  sites (§4.3), and in `command/service.py` the binding recheck inside `_submission_lock`, which T2 also takes
  (§9.1). The 06h manifest lists append sites by path and symbol, so it does not change, and no binding row or
  protected identity changes;
- `research_system/store/binding_service.py`: the checked ledger head, passed to `AdvanceStoreBinding` beside its
  intent and compared under the writer lock before the marker (§9.1). The intent's exact field set and the accepted
  `wp6-6/gate6-binding-repair` intent and command schemas do not change, so no protected identity changes;
- `research_system/cli.py`, beyond §13's commands: `ars store advance-binding`'s `--expected-ledger-head`, and the
  binding check handed to `CommandService` where `ars submit` builds it (§9.1);
- `research_system/legacy/`: the created-ID table that the W9, W11, generic and T2 identity checks and the pre-pin
  scan share (§4.3). It adds no binding row and changes no protected identity.

**The D-4 delta.** The census counts command and event binding rows alike (its row format,
`tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py:104-108`), so it grows by 11, from 262 to 273, with
a digest the code PR computes. With it change the 06h manifest's count and digest, and the count pin in
`tests/research_system/unit/test_schema_registry.py`. The append sites do not change: `LegacyRuntime._submit_authorized`
stays the one W9 site, so the append-site classification is unchanged. No core command or event schema changes, so the
protected trees and the T2 expectations and seal are unaffected. Stephen re-accepts the bytes in the merge-queue entry
(06v §5), and WP9.3-1 merges alone.

**At WP9.3-2:** no protected identity changes.

## 17. Tests

Every negative control asserts its message, and runs through the guard's own predicate rather than beside it. A scratch
mutation script deletes or weakens each new guard alone and shows its test fails, as WP9.2-2 revision 2 did. Every role
guard is tested with a non-owner actor holding a grant, because the owner short-circuits actor classification
(`authority.py:2723-2731`), and every non-resolver row is tested refusing the owner.

| Test | What it shows | PR |
|---|---|---|
| Whole-flow replay | A scratch store holding W11 genesis, W9 genesis, one registration, one membership table, one inventory, one observation of each selector kind and, in WP9.3-2, one accepted batch, replays through `replay`, `rebuild_projection`, `replay_discovery` and `replay_legacy` | 1, 2 |
| W9-C01, W9-C03, W9-C11 | For each routed row: the positive flow, a mutated catalogue row detected, and a retry answered from receipts with nothing appended | 1, 2 |
| W9-C20 to W9-C23, W9-C25 | Each refused, through `submit` and on a forged ledger. W9-C20 includes a verdict whose `reviewer_session` equals the request's analyst session, and, for a membership table, a reviewer and author who are distinct actors on one session (§5.5) | 1, 2 |
| The W2 payload fields (§5.2) | One forged-ledger control per checked field, including a verdict whose `computed_independence_grade` is not `independent`, a verdict or resolution with non-empty `conditions`, a resolution with non-empty `permitted_commands`, and a resolution after `expires_at` | 1 |
| `ReviewRequested` cardinality | A forged request with empty `review_questions`, or with a `reviewer_capability` of zero or two entries, refused by replay; a `required_evidence_refs` entry with an empty session after its prefix, refused at `submit` and by replay | 1 |
| Cross-partition identity (§4.3) | A W9 proposal reusing a W11 aggregate's ID at that stream's current version, refused at `submit` and on a forged ledger; a valid W11 request whose `new_review_id` is a W9-reserved `rev_`, refused by `DiscoveryRuntime.submit` before any append; a forged W11 event on a reserved `rev_`, refused by `replay_legacy` and by the public shared replay. The generic and T2 controls of §4.3: a `CreateScopeDefinition` on `CATALOGUE_STREAM_ID` before and after W9 genesis, and a generic and a T2 creation on a reserved `rev_`, each refused before any append; the bootstrap IDs disjoint from W9's. Created IDs: a generic `RecordScientificReview` whose `review_id` is a W9-reserved `rev_`, refused before append, and the same event on a forged ledger, refused by `replay_legacy`; a fixture non-W9 event that names a W9 record ID in a reference field the table does not list, admitted, since a reference is not a creation; and the table-coverage test, failing on a fixture event schema whose created-ID field the table omits. The existing W11, generic and T2 suites pass unchanged | 1 |
| Observation ID (§5.3) | An observation whose `record_id` is not the derivation from its subject, refused at `submit` and by replay; a grant for one observation refused for a second observation of the same registration with another selector, and with another baseline; the ID `ars legacy observation-id` prints before submission equals the ID the preparer derives, with the runtime clock set to a different time; a source observed as A, then B, then A again, where the third observation gets a fresh ID, is admitted and is not stale; a grant issued before another observation of the same registration lands, refused before append because `n` moved; a forged observation with the wrong `n`, refused by replay. The physical-identity reading: an `untracked_file` source replaced at its registered path, after the grant, by a new file with identical bytes, admitted under the same grant; one replaced with different bytes, refused before append; one replaced by a symlink, and one by a second hard link, each refused by the read | 1 |
| The O-33 gap (§7.2) | A scratch source mutated between LR-015's final re-read and the append: the observation commits with the re-read's hashes and frozen copy; LR-016's re-read then refuses the changed source with no event and no receipt, and the projection does not mark the observation stale. In WP9.3-2, a scratch source mutated between LR-020's final re-read and the append: the acceptance commits naming the recorded hashes, the frozen copy still hashes to them, and a following observation of the registration makes the accepted record stale; the same for a restricted source, accepted on its recorded hash with no copy in the store. A failed acceptance-time re-read leaves the ledger and the projection unchanged. In WP9.3-2, an `untracked_file` item's frozen copy deleted, and separately altered, before LR-020's re-check: the command aborts with no event and no receipt; a restricted item in the same batch is not refused for having no copy | 1, 2 |
| Proposal lapse (§4.6) | A corrected LR-003 registration of the same path, refused while the first proposal is open and admitted once it has lapsed; a review request, Decision proposal and resolution, each refused on a lapsed proposal; the lapse time computed from both `created_at` and a later Decision's `expires_at` | 1 |
| W0 signature pin (§9.1) | A proposal pre-assigning a pinned ID refused; a ledger that claimed the ID before the pin replays under the earlier pin set and fails under the new one; a re-derived `#2` ref accepted. The pre-pin check: on a scratch W9 store whose ledger holds a W11 stream, and separately a generic stream, on the candidate's derived ID, the check reports the collision that `replay_legacy` alone misses, and the `#1` re-derivation passes. One snapshot: an event claiming the candidate ID, appended after the check's snapshot is taken and before the check returns, is not in the recorded head, and an advance given that head refuses; the recorded head equals the snapshot's `global_position` and `event_hash` | 1 |
| Pin release by binding advance (§9.1) | On a scratch store and Git repository under `tmp_path`, through `load_current_binding` itself rather than the validators alone: a schema 1.2.0 binding advanced to a commit that changes `accepted_w9.py` refuses a checkout at its parent, with `refs/heads/main` at the bound commit and rewound to the parent; the binding before the advance refuses the pinned checkout; a documentation-only descendant on `main` is admitted; and `ars legacy submit` from a pre-pin checkout is refused before any append. The separate checkout: an advance whose candidate is a second checkout at the pin commit succeeds with the bound checkout left at its commit, and one attempted after updating the bound checkout in place is refused; after the advance, an operation from the old checkout's root is refused by the code-root check, including one from a process that admitted before the advance. The head compare: an advance given the checked head, with one event appended after the check, refuses before writing its marker and leaves the binding, the manifest and the config byte-identical; with no event appended, it succeeds and its event's global position is the checked head's plus one; an advance resumed from its marker after another writer's append refuses, and one resumed after a crash that followed its own event's append completes. The command path: `ars store advance-binding --intent … --expected-ledger-head …` on a scratch store refuses on a moved head and advances on a matching one, and a malformed head value is refused before the service runs. The lock recheck: a W9 submit and a W11 submit, each paused after admission and before its writer lock, the binding then advanced, each refused on resume by the code-root check before any append. The grant fence, on the predecessor's own code: a checkout of a commit from before WP9.3-1 under `tmp_path`, whose unchanged package a test wrapper imports and pauses on a signal file before its writer lock is taken; a W11 submit from it, admitted before the advance on a grant then revoked, refused on resume with "authority grant revoked" and the ledger byte-identical; the same with the grant expired instead; and the same submit with its grant left live, which appends, showing the fence is what refuses it. The census of command types that write without a grant, failing on a fixture type that does. The generic and T2 recheck: a generic lifecycle submit, a T2 submit and a `VerifyEvidenceDeletion` on the candidate's derived `dec_`, each paused after admission and before `_submission_lock`, the binding then advanced, each refused on resume by the code-root check before any append; the census of `CommandService` lock sites that can append, failing on a fixture site without the recheck. The existing binding-advance, W11, generic and T2 suites pass unchanged | 1 |
| Runtime-construction census (§9.1) | An AST census over every Python file outside `tests/` that counts constructions of `LegacyRuntime` or `DiscoveryRuntime`, not imports. Imports, re-exports and annotations are allowed anywhere: `discovery/spec.py:19` imports `DiscoveryRuntime` at module scope, `discovery/__init__.py:1` re-exports it, and `spec.py:339` names it as a return type. The census follows every name an import or assignment binds to either class, so a call through an alias, or through `functools.partial` or `getattr` on such a name, counts as a construction; a subclass of either class outside its own module fails outright. Each construction sits at an allowed site, exactly two: `SpecCoordinator._discovery` (`discovery/spec.py:339-351`, the only one on `main` at `1f0d8281`) and §13's `ars legacy submit`, each taking its binding from a `VerifiedCurrentBinding` that `load_current_binding` returned. A positive control: the census passes on the tree as it stands, imports and re-export included. Negative controls: fixture modules that construct either runtime without the binding, construct it through an alias, and subclass it, each fail the census with the file and line named | 1 |
| C1 and C2 controls kept | `test_c1_a_w9_command_without_its_binding_row_is_refused` and `test_c2_a_w2_typed_event_without_its_producer_binding_is_refused` (`test_w9_legacy_replay.py:228`, `:245`) rely on rows WP9.3-1 adds. Each removes the row by monkeypatch inside the test, so it keeps refusing whatever is bound (review m-4) | 1 |
| JSON parsing | Vectors for a BOM, UTF-16 input, a duplicate key, each non-finite token, `1e400` and a lone surrogate (§8.2) | 1 |
| The `CONVENTIONS.md` vault alias | A `vault_file` registration resolving to the repository's `CONVENTIONS.md` is refused (§7.1) | 1 |
| N-2 | A record whose `content_hash` hashes other content is refused at replay; a payload that supplies `content_hash` is refused before append | 1 |
| Pre-assigned refs | A ref hash other than §4.2's rule; a second proposal pre-assigning a reserved ID; a request using another proposal's reservation | 1 |
| F-8, first limb | A resolution whose Decision proposal names another record or hash, refused at replay and at the preparer | 1 |
| Deferred row through a bound command | A `ProposeLegacyRecord` for LR-023 refused before any write | 1 |
| Supersession of a missing record | Refused at replay, on a forged ledger with WP9.6's rows routed on a test registry (§3 row 5) | 1 |
| W9-T1, W9-T2, W9-T3, W9-T4, W9-T13, W9-T22 | §9.2, §8.2, §8.2, §9.4, §9.3, §8.4 | 1 |
| W9-T6 (with O-33) | The source changed between observation and commit, and between observation and acceptance: the command refused with no event and no receipt, and the projection unchanged. The observation is stale in the projection only once a later observation of the same registration records the changed bytes (§7.2) | 1, 2 |
| W9-T11, reader half | A `*.pkl` observed with a frozen copy is refused; a restricted observation records hash, size and path only | 1 |
| Frozen copy | A copy whose bytes differ from the observed bytes is refused | 1 |
| Segmenter | The contract's vectors against both implementations, and the differential test | 1 |
| Genesis | The existing genesis tests unchanged; the generalized partition check refuses a missing, overlapping or untagged row | 1, 2 |
| Shadow step | The preparer's shadow run refuses what replay refuses, including a schema-invalid payload that a reducer alone admits (§6) | 1 |
| CLI (F-4) | §13, on a real scratch store | 1 |
| D-4 | The census, the 06h manifest and the registry count at their new values | 1 |
| W9-T16 | §10.3's two controls, and an `ars_event` anchor refused | 2 |
| O-32 | Fixture change lists with and without an entry affecting an item; an absent list refused | 2 |
| O-37 | A missing F-018, F-023, F-037 or S-014, a duplicated fixture, and an evidence ref of the wrong kind, each refused (§10.2) | 2 |
| Two batches (M-1) | Two acceptance proposals sharing an item: the second resolution refused at replay | 2 |
| Ownership list (E) | An LR-020 that omits, adds or alters an ownership record, refused at replay; two whole-file items of one registration refused at LR-016; the copied refs checked against the acceptance's record ID | 2 |
| Export recheck | Over synthetic logs, with the export produced by the reference implementation: a one-byte change in the retained copy voids the export, and an export recorded as produced by the runtime segmenter is refused (§12.2) | 2 |
| W9-T18 | §12.4's bijection over a synthetic `.apm/` tree: a missing file, an extra file and a remaining blocker each block | 2 |
| Tools write nothing | Each tool leaves its input tree byte-identical, and refuses an output path under `.apm/` | 1, 2 |

**Fixtures** follow 06v §4. No test reads a live legacy file, the vault or restricted bytes. Each fixture copy carries
a manifest naming its source path and blob at a pinned commit, and the test re-derives the blob. The tracker, log,
`.apm/` and restricted fixtures are synthetic. Tests that read the canonical foundation stub `canonical_foundation_path`.

## 18. Research assurance

**Lanes touched.** Output and provenance: content hashes, references, anchors, fixture manifests and the reader's
identities. Paper claim, indirectly: W0 classes and precedence decide what may later become citable, but WP9.3 changes
no claim. WP9.3 computes no statistic, null or embedding, so the topology, null-model, statistical and representation
lanes are untouched.

**Governing records.** W9 §§4.2, 5.4, 5.5, 6, 7.3, 8, 12.3, 13.3, 14.3 and 17; 06v WP9.3; the catalogue and owner annex
(O-8, P-075); the segmentation contract (P-068); the membership template; P-072, P-073 and P-080.

**Machine-checkable, with the artefact that checks each:**
- the content hash, pre-assigned refs, identity claims and references: replay, with forged-ledger controls (§4);
- G5, review satisfaction and the verdict's actor and hash: replay, with W9-C20 to W9-C23 (§6.1, §5.4);
- the window: the preparer's re-read, with W9-T6 (§7.2);
- segmentation: the contract's vectors, the differential test, and the independent re-implementation (owner point I);
- family exhaustiveness and exclusivity: W9-T3;
- the anchors: W9-T16;
- the change list: the O-32 fixtures;
- the structural `pilot_promotion` rules, including the four fixtures required on every item: the O-37 controls;
- one acceptance per item, and the first batch only, re-checked at LR-020: the two-batch control;
- the W2 payload fields, including the verdict's independence grade and empty conditions: the per-field controls;
- W9-C20's session limb, and the membership-table author's session, as equality checks on attested strings: the
  W9-C20 controls;
- identity claims across the shared ledger, at the W9, W11, generic and T2 writers, and the pinned W0 signature IDs:
  the cross-partition and pin controls;
- LR-015's full authority subject, through the derived observation ID: the observation-ID controls;
- the O-33 gap after the final re-read, closed at acceptance, and the same gap at LR-020, where the acceptance binds
  the recorded bytes: the O-33 gap controls;
- that the observation ID can be computed before submission, and that a returning source gets a fresh one: the
  observation-ID controls, run through `ars legacy observation-id`, which leaves the store byte-identical;
- that the bound checkout stays put until the advance, and that the old checkout is refused after it: the
  separate-checkout controls;
- that no write lands between a later pin's check and its binding advance: the advance's head compare under its
  writer lock, passed through `ars store advance-binding`, with the head-compare and command-path controls, and the
  check's single snapshot, with its concurrent-append control;
- identity claims against the IDs non-W9 events create in their payloads, not only their streams: the created-ID
  table, its coverage test and the created-ID controls;
- that a writer admitted before a later pin's advance cannot append after it: the W9 and W11 binding recheck inside
  the writer lock, and the generic and T2 recheck inside `_submission_lock`, with the paused-submit controls and the
  lock-site census; and, for a writer on predecessor code without that recheck, the grant fence, with the
  predecessor-version controls and the grant-free census;
- that LR-020's frozen copies held the recorded bytes at its re-check, for the kinds that have one: the preparer's
  copy re-check, with the deleted-copy and altered-copy controls;
- that replay marks stale only from recorded observations: the failed-re-read control;
- a later pin's collision check across every partition: the pre-pin check controls;
- after a later pin's release, refusal of a writer on pre-pin code: `load_current_binding`, with the pin-release
  controls (§9.1). Whether a store has been released is a fact the store records: its current binding's `git_head`;
- that production code builds `LegacyRuntime` and `DiscoveryRuntime` only behind `load_current_binding`: the
  runtime-construction census and its negative controls (§17);
- the export and its recheck by different implementations: the export-recheck controls;
- the ownership list: replay, with the E controls;
- restricted bytes: W9-T11's reader half.

**Human-review-only,** with the question each reviewer answers:
- the W0 class (LR-017 and LR-018): "Does each family's class equal the class the signed W0 record gives that
  object?";
- precedence and canonical sources (LR-018): "Is each conflict's tier right, and does each `corrected_by` name the
  canonical file?";
- `pilot_promotion` (LR-018, then Stephen's batch Decision): "Is each conditional fixture's applicability right for
  each item, and does each item's evidence, F-018, F-037 and S-014 included, actually evidence its fixture?";
- the governing-record set (O-25; W9 §14.3): "Is the set the reviewer compiled from G7-A §§4–10 and the audit
  complete?";
- membership families (LR-008): "Does each family follow its `definition_source`, not a key's name (template §3 rule
  8)?";
- the created-ID table (§4.3), for WP9.3-1's independent reviewer: "Does each entry's class, creation or reference,
  match what that event's reducer does with the field?" The coverage test proves every ID-pattern field is
  classified, not that it is classified rightly, and the non-W9 reducers expose no uniform record of the IDs an
  event creates, so no mechanical oracle exists; the reviewer reads each reducer;
- session independence (§5.5): the same-session case is a refusal test; whether the attested session strings are true
  is the operator's attestation;
- S-014's freshness at LR-020 (§10.2), checked by Stephen at resolution and on the L-4 checklist: "Has any restore run
  been made since the run each item's S-014 ref names?";
- a later W0 pin's write freeze (§9.1), on the pin's checklist: "Was each store's advance given the head its final
  check recorded, and is the advance's event at that head's position plus one? Before the final check, was every
  grant that admits a write on the store revoked or expired, and was none issued until the advance?" Each command
  type the grant-free census names is a known limit the checklist lists;
- the drain before a later pin (§9.1), on the pin's checklist: "Was the pin in a separate, durable checkout, with the
  bound checkout left at its commit? Was the candidate checkout created at the pin commit, or, if reused, had every
  process started from it exited before it was updated, with none starting from it until it was at the pin commit?
  Had every process started from the bound checkout exited before the final check, and did none start from it until
  the advance?" A write from a process started outside Stephen's dispatch moves the head, which the advance refuses;
  after the advance, the code-root check refuses the old checkout. A process from a reused candidate checkout that
  loaded pre-pin modules is not visible to code, so the candidate question is the check;
- the retention of accepted frozen copies (§7.2, a known limit): from LR-020's re-check onward, the moment before the
  append included, ARS detects a deleted or altered copy on its next use but cannot prevent it, so the question for
  each reviewer who relies on an accepted untracked or vault record is "Does its frozen copy still hash to the
  recorded `sha256`?";
- a restricted source's acceptance (§7.2): ARS holds only its hash, size and path, so "Do the custodians of each
  accepted restricted source still hold bytes that match the recorded hash?" is answered outside ARS;
- Discovery-only replay (§4.3, a known limit): `replay_discovery` runs no W9 check, so a W11 reader would project
  over a ledger that a direct append broke for W9. Before W9 genesis the public shared replay runs no W9 check either,
  so a direct append on the catalogue stream ID shows up only as W9 genesis failing on that store. The question for
  each reviewer of a Discovery output is "Did the public shared replay pass on this ledger?";
- the census's reach (§17): it sees Python source in the repository, not a runtime built by code outside it or by a
  dynamic import. Local administration through `--config` is outside the dispatch path (§9.1), and the reviewer
  answers: "Does any dispatch path build a W9 or W11 runtime the census cannot see?"

## 19. Stop rules (06v §8) checked

- **An interface in §2.8 resolves differently.** None does. Two seams 06v does not list are settled here without a
  core schema change: the frozen copy (§7.3) and the evidence area (§11.1). The closed acceptance schema (§10.5) is not
  a §2.8 interface; it goes to Stephen as owner point E.
- **A W11 pin would change.** None does. Revision 4 changes W11 code: the admissible-target check of §4.3. It does not
  change the W11 catalogue, schemas, bindings or census. WP9.3-1's independent review re-verifies the W11 pins at its
  head, and the existing W11 suites must pass unchanged.
- **The shared-replay edit cannot be confined.** The four sites do not change (§14). Revision 7 keeps it so: CodeRabbit's
  case for a W9 check inside `replay_discovery` would be a fifth site, so it is recorded as a known limit instead
  (§4.3), at Stephen's choice. The generic and T2 checks are before append, not in replay.
- **A test needs live legacy, vault or restricted bytes.** None does (§17).
- **A command would write a legacy file or the Gate 6 store.** None does: the tools refuse those outputs, and the CLI
  refuses before binding (§12, §13).
- **A protected identity changes without D-4.** §16 lists them.
- **A successor guard needs a core schema change.** Not applicable: WP9.3 has no successor guard.
- **A W9 §13.4 criterion applies.** Not to code. They are checked at L-4.

## 20. The claims the review probed

Revision 1 ran no prototype and listed these claims for the review to probe. The review's results (review §2) are in
brackets; the text above carries each correction.
1. The census grows by exactly 11 rows (§16). [Holds: 273 active rows.]
2. The frozen-copy seam (§7.3). [Read, not run; the code PR's end-to-end test runs it.]
3. The §5.2 encodings pass `w9_row_ref`, `assign_row` and `_refuse_w11_row` unchanged, and the W2 schemas accept them.
   [Holds for the fields revision 1 named; revision 2 names every required field (M-2).]
4. The shadow run of §6 needs no second whole-ledger replay. [Holds, with the driver's step factored out (m-6).]
5. The ownership derivation (§10.5) is deterministic and collision-free across batches. [Holds across batches; within
   a batch, two whole-file items of one registration collided, now refused (m-2).]
6. `_verified_ledger(read_only=False)` writes nothing outside the control root before `submit`'s refusal (§13).
   [Holds, by reading.]
7. A bound `ProposeLegacyRecord` cannot reach any deferred row (§2.2). [Holds, given `assign_row` in the runtime.]
8. The pre-assigned ref rule (§4.2) is free of circularity. [Holds; the copied refs needed a rule (m-3).]
9. Python's JSON parsing can meet template §3 rule 1 exactly. [Only with the checks §8.2 now names (m-5).]
10. The line-ending claim of §7.1. [Holds at both checkouts.]

## 21. Owner points

Each needs Stephen's decision before the code. Each has a recommended option.

| # | Decision | Recommended | Alternatives |
|---|---|---|---|
| A | **The split** (06v D-6; P-064 item 6; P-080 item 1) | **Two PRs, which the review asks for (review §4):** WP9.3-1 (LR-003 to LR-015, all seven bindings, D-4) then WP9.3-2 (LR-016 to LR-020, the export recheck and the `.apm/` tools, no D-4) (§2.3). P-064 item 6 allows a WP9.3 split without fixing its shape; this shape departs from 06v's D-6 row ("reader and selectors"), which the decision records | One PR; or 06v's reader and selectors split |
| B | **Review satisfaction** | **`approve` only, for every W9 review,** with `approve_with_conditions` not even recordable (§5.4). The catalogue has no row to discharge a condition | Admit `approve_with_conditions` for authority reviews only, which needs a condition-discharge rule and a catalogue revision |
| C | **Accepted identities from outside the store** (O-27; D-7) | **Frozen constants in `accepted_w9.py`,** empty in WP9.3, so LR-015 refuses in production until a reviewed PR pins each after Stephen's acceptance: the W0-D1 signature (§9.1) and the export with its classified list (§11.3). Amended 2026-11-08: a later W0 pin is released on each W9 store by advancing its binding to a `main` commit that holds the pin, and the write freeze runs from the final pre-pin check to that advance (§9.1; issue #415, option C). Amended again the same day: the pin goes in a separate, durable candidate checkout while the bound checkout stays at its commit until the advance, and every process started from the bound checkout exits before the final check, none starting from it until the advance (§9.1). Amended a third time (2026-11-09): the candidate checkout is created at the pin commit, or drained before a reused one moves; and the advance is given the checked ledger head beside its intent and compares it under its writer lock, refusing with no effect if it moved (§9.1). Amended a fourth time (2026-11-09): W9 and W11 writers recheck the binding inside their writer lock before append, and a resumed advance accepts a head moved only by its own event (§9.1). Amended a fifth time (2026-11-09): `ars store advance-binding` takes `--expected-ledger-head`, and the pre-pin check takes its replay, scan and recorded head from one snapshot (§9.1). Amended a sixth time (2026-11-09): before the final check every grant that admits a write on the store is revoked or expired, with none issued until the advance, so a writer on predecessor code without the in-lock recheck is refused under its lock; a census names command types that write without a grant (§9.1). Amended a seventh time (2026-11-09): `CommandService._submission_lock`, taken by generic and T2 submits, also rechecks the binding inside the lock; a later pin's predecessor already holds WP9.3-1, so the known limit is a grant-free command paused since before its store first bound WP9.3-1 code (§9.1) | Read them from committed evidence files at `git_head`, which leaves Stephen's acceptance unchecked by code |
| D | **The W9 evidence area** | **`.research-system/evidence/w9/`,** with WP9.3 fixing the reader-side formats of WP9.5's files (§11.1). The path is recorded once, in the decision entry, so that WP9.5 (D-5's run hashes) and WP9.7 (D-9's suffix list) use the same one | `docs/plans/agentic-research-system/transition/w9/evidence/`; or WP9.5 defines the formats first, and LR-003, LR-015 and LR-016 wait for it |
| E | **LR-016's ownership list**, which the closed acceptance schema cannot hold (§10.5) | **Derived, not listed:** the list is a deterministic function of the proposal and the ledger before it, stored at LR-016 and required exactly at LR-020, read as meeting the annex text's purpose; a batch may hold at most one whole-file item per registration. Recorded as a reading of `wp9-1-catalogue-owner-annex.yaml:567` | Derived, and also listed among the LR-017 review's subjects, so the reviewed bytes contain the list (the review's alternative); a catalogue revision adding the field (a new schema identity, a new O-8 acceptance and LR-002's revision path); or the list in the command payload only, which replay cannot check |
| F | **Genesis guard 8** (§15) | **Generalize the partition check,** have each WP9.3 PR's review re-verify the genesis path, and add the verifying review to the L-3 checklist | Keep the 1/60 literals and edit them in each PR, with the same review consequence |
| G | **Anchor kinds** (O-25; W9-T16) | **`git_commit` only in v1,** for simplicity: one anchor kind and one test (§10.3) | An `ars_event` anchor naming an `ArtefactRegistered` event, at a lower global position, whose `content_sha256` is the anchored hash |
| H | **Roles and independence** (W9 §8.6; W9-C20; P-073 item 1) | **Option (a):** exact-subject grants plus the distinctness rules of §5.5, the owner refused on every non-resolver row, and W9-C20's session limb checked as far as the payloads allow: the request encodes the analyst's session, and replay refuses a verdict from the same session. That both session strings are true, and the legacy-producer exclusion, are recorded as known limits. Amended 2026-11-08: a membership-table review also records the author's session, which the verdict must differ from (§5.5) | **Option (b):** record the session limb as a known limit, which narrows the accepted W9-C20, as P-058 did for model families; or a role registry, which needs a new record kind and a catalogue revision |
| I | **The runtime segmenter and its independent re-implementation** (contract §7; P-067; P-068) | **A new `research_system/legacy/segmentation.py`,** differential-tested against the reference tool, which stays untouched. WP9.3-1's independent reviewer, shown independent of both the contract's author and WP9.3's implementer, re-implements the contract and reproduces every vector, with the results recorded in the review report where the acceptance can cite them. The export is produced by the reference tool and rechecked by the runtime segmenter (§12.2) | Promote `tools/w9_segmentation.py` into the runtime, which moves an accepted blob; or a separate session for the re-implementation |
| J | **Boundary extension** (P-080's Boundary line) | **Extend it by name** to `research_system/authority.py` (§16) and `research_system/cli.py` (§13), as P-077 item 5 did for WP9.2. No `tools/` file is added (§12). Amended 2026-11-08: also `research_system/discovery/routes.py` and `research_system/discovery/runtime.py`, for W11's symmetric identity check (§4.3); amended again the same day: also `research_system/command/service.py` and `research_system/command/t2.py`, for the same check at the generic append sites (§4.3). Amended 2026-11-09: also `research_system/store/binding_service.py`, for the advance's head compare (§9.1, §16); amended again the same day: `research_system/discovery/runtime.py` also carries the binding recheck inside the writer lock (§9.1, §16); and again: `cli.py` also carries `ars store advance-binding`'s `--expected-ledger-head` (§9.1), and every identity check also compares the record IDs a non-W9 event creates, through a created-ID table in `research_system/legacy/` (§4.3, §16); amended again the same day: `command/service.py` also carries the binding recheck inside `_submission_lock`, and `cli.py` passes the service its binding check (§9.1, §16) | Keep the tools under `tools/`, which extends the boundary further |
| K | Withdrawn in revision 2. It rested on reading LR-020's fixture set as three fixtures, not seven (review B-1; §10.2) | — | — |
| K′ | **S-014's timing:** "re-run after each W9 batch" (W9 §12.3), against evidence required before the batch is accepted (§10.2) | **The S-014 ref names the latest restore run before LR-020,** and the post-batch re-run goes on the L-4 checklist | A waiver for S-014 in the pilot batch, with the re-run after it |
| L | **G4 at the four proposal rows** (§5.3): the grant binds the ID, and the hash half has nothing to compare against until the review | **Record it as a reading:** the proposal grant is ID-exact, and the content hash is bound by the review and the Decision. Amended 2026-11-08: LR-015 is not read this way; its grant binds the full subject through a derived observation ID (§5.3), whose timestamp is the registration's `created_at` and whose domain includes the registration's observation count, so the ID is known before submission and a returning source gets a fresh one. Amended 2026-11-09: the subject's physical identity is read as fixed at registration (LR-003, LR-005); the observation's read refuses aliasing, and a file replaced at the registered path is the same source, with no `stable_file_id` match required (§5.3) | Pre-register the hash in a separate step before the proposal, which no catalogue row provides |
| M | **The pre-assigned ref hash** (§4.2): a synthetic value in a field the schemas call `content_hash` | **Accept the rule as written,** with copied refs checked against the record that pre-assigned them, and record it as a reading of the accepted schemas | Any other non-circular rule, fixed before the code PR, because it fixes stored bytes |

## Change log

- **Revision 14 (2026-11-09).** Answers CodeRabbit's review of revision 13 on PR #411: two comments outside the diff
  and one nitpick. Stephen chose all three recommendations in chat on 2026-11-09.
  - **The generic and T2 recheck** (outside diff): `VerifyEvidenceDeletion` resolves no grant and takes a caller's
    target stream, so the grant fence does not stop it, and revision 11's in-lock recheck covered only the W9 and
    W11 runtimes. `CommandService._submission_lock`, which generic and T2 submits take, now rechecks the binding,
    with a census of its lock sites. A later pin's predecessor already holds WP9.3-1, so the remaining gap is a
    grant-free command paused since before its store first bound WP9.3-1 code, a known limit. P-081 items 3 and 10
    amended (§9.1, §16, §17, §18, §21 C and J).
  - **The physical identity in LR-015's subject** (outside diff): the note said `source_identity` carries the
    physical identity; it does not, and the accepted schema admits no such field. The note records a reading: the
    physical identity is fixed at registration, the observation's read refuses aliasing, and a file replaced at the
    registered path is the same source, over a strict `stable_file_id` match. P-081 item 12 amended (§5.3, §17,
    §21 L).
  - **Created-ID classifications** (nitpick): a human-review question for WP9.3-1's independent reviewer. The
    negative control is declined: without a uniform record of the IDs a reducer creates, no mechanical check can
    tell a wrong class from a right one (§18).
- **Revision 13 (2026-11-09).** Answers CodeRabbit's review of revision 12 on PR #411: one inline comment. Stephen
  chose the option in chat on 2026-11-09.
  - **The grant fence** (inline, Major): the in-lock binding recheck is WP9.3-1 code, so a W11 writer on a
    predecessor from before WP9.3-1, admitted before a pin's advance and outside the drain, could still append after
    it. Every W9, W11 and governed generic writer already resolves its command's grant under the writer lock from a
    fresh replay that refuses revoked or expired grants. So before the final check every grant that admits a write on
    the store is revoked or expired, and none is issued until the advance; a census names any command type that
    writes without a grant as a known limit. The control runs the predecessor commit's own code. P-081 item 3
    amended (§9.1, §17, §18, §21 C). No boundary file is added.
- **Revision 12 (2026-11-09).** Answers CodeRabbit's review of revision 11 on PR #411: one inline comment and two
  outside the diff. Stephen chose the two options that change P-081 in chat on 2026-11-09; the single snapshot
  changes the note only.
  - **The head through the supported command** (inline, Major): `ars store advance-binding` took only `--intent`, so
    the checked head could not reach the service. It gains `--expected-ledger-head`, optional for other advances and
    required by the pin's checklist. P-081 items 3 and 10 amended (§9.1, §16, §17, §18, §21 C and J).
  - **Created IDs** (outside diff): `RecordScientificReview` appends to the artefact stream but creates a `rev_`
    `review_id`, so a stream-ID comparison missed it. Every identity check, and replay, also compares the record IDs a
    non-W9 event creates, through a created-ID table with a coverage test. P-081 item 10 amended (§4.3, §16, §17,
    §18, §21 J).
  - **One snapshot for the pre-pin check** (outside diff, note only): the public shared replay, the scan and the
    recorded head come from one `LedgerSnapshot`, so an append during the check makes the advance refuse (§9.1, §17,
    §18, §21 C).
- **Revision 11 (2026-11-09).** Answers CodeRabbit's review of revision 10 on PR #411: three inline comments and two
  outside the diff. Codex's review did not run (usage limit). Stephen chose the three options that change P-081 text
  or code behaviour in chat on 2026-11-09; the O-33 control's wording changes the note only.
  - **Binding recheck under the lock** (inline): W11 rechecks the binding at the start of each operation, before
    `DiscoveryRuntime.submit` takes its writer lock, so a writer admitted before the advance could pause and append
    after it, which no head compare can see. `LegacyRuntime` and `DiscoveryRuntime` now recheck the binding inside
    the writer lock before append. P-081 items 3 and 10 amended (§9.1, §16, §17, §18, §21 C and J).
  - **Resuming after the advance's own event** (outside diff): a crash after the event's append moved the head, so
    revision 10's resume would have refused. The resume now accepts a head moved only by this advance's own event.
    P-081 item 3 amended (§9.1, §17, §21 C).
  - **The frozen-copy re-check's scope and gap** (two inline): the re-check names `untracked_file` and `vault_file`
    only, since a restricted source has no copy; and the copy can still be deleted between the re-check and the
    append, so the guarantee is that the copy held the recorded bytes at the re-check, and the known limit starts
    there. P-081's O-33 amendment corrected (§7.2, §17, §18).
  - **The O-33 control at LR-016** (outside diff, note only): after a mutation following LR-015's final re-read,
    LR-016's re-read refuses with no event, and the projection does not mark the observation stale, matching
    revision 9's rule (§7.2, §17).
- **Revision 10 (2026-11-09).** Answers CodeRabbit's review of revision 9 on PR #411: two inline comments and two
  outside the diff. Stephen chose the three options that change P-081 text or code behaviour in chat on 2026-11-09;
  the fourth changes the note only.
  - **The head check bound to the advance** (inline, Major): the advance compared only the project stream's version
    within its own lock, so a write between the manual head re-read and the advance went unseen. WP9.3-1 passes the
    checked head to the advance beside its intent and compares it under the writer lock before the marker; a moved
    head refuses with no effect. Stephen chose to keep it out of the intent, so the accepted Gate 6 schemas do not
    change. P-081 items 3 and 10 amended (§9.1, §16, §17, §18, §21 C and J).
  - **The candidate checkout's drain** (inline): a reused candidate checkout could hold processes with pre-pin
    modules that the advance would then admit. The candidate checkout is created at the pin commit, or drained before
    a reused one moves. P-081 item 3 amended (§9.1, §18, §21 C).
  - **Frozen copies at LR-020** (outside diff): LR-020's preparer re-checks each item's frozen copy against the
    recorded hash and size, and a missing or altered copy aborts with no event. Retention after acceptance is a known
    limit: ARS detects a lost copy on its next use but cannot prevent it. P-081's O-33 amendment extended (§7.2, §17,
    §18).
  - **W9-T6** (outside diff, note only): the row now matches §7.2. A changed source at commit or acceptance is a
    refusal with no event, and the projection marks stale only after a later recorded observation (§7.2, §17).
- **Revision 9 (2026-11-08).** Answers CodeRabbit's review of revision 8 on PR #411: one inline comment and four
  outside the diff. Codex's review of revision 8 did not run (usage limit). Stephen chose the four options that change
  P-081 text or code behaviour in chat on 2026-11-08; the fifth changes the note only.
  - **The pin's checkout** (inline): the advance re-admits the predecessor on its own code root, so revision 8's
    in-place update would have been refused. The pin now goes in a separate, durable candidate checkout, and the
    bound checkout stays at its commit until the advance. After it, the code-root check refuses the old checkout,
    whatever its processes have loaded. The drain is kept for the old checkout. P-081 item 3 amended again (§9.1,
    §17, §18, §21 C).
  - **A returning source** (outside diff): the ID domain adds `n`, the registration's observation count, so a source
    observed as A, B, then A again gets a fresh ID for the third observation. Revision 8's refusal of a repeated
    subject is dropped. P-081 item 12 amended again (§5.3, §17, §21 L).
  - **Where the ID is computed** (outside diff): a read-only `ars legacy observation-id` command through the existing
    read-only binding, so the tools still open no store (§5.3, §12.1, §13, §17).
  - **Restricted sources** (outside diff): accepted on their recorded hash, size and path; ARS cannot return the
    bytes after a change, and the record's non-inference says so. P-081's O-33 amendment extended (§7.2, §17, §18).
  - **The stale projection** (outside diff, note only): replay marks stale only from recorded observations. A failed
    acceptance-time re-read is a preparer refusal with no event, so replay cannot see it (§7.2, §17, §18).
- **Revision 8 (2026-11-08).** Answers a fifth round on PR #411: three CodeRabbit comments and three Codex comments
  (one P1, two P2). Stephen chose the four options that change P-081 text in chat on 2026-11-08; the other two change
  the note only.
  - **The observation ID before submission** (Codex P1): the ID's timestamp is the registration's `created_at`, not
    the observation's, which the runtime clock sets at submit. The builder can then print the ID for the grant. A
    second observation of an unchanged subject is refused as an existing identity. P-081 item 12 amended (§5.3,
    §12.1, §17, §21 L).
  - **The LR-020 window** (CodeRabbit): the acceptance binds the observation's recorded bytes, not the live file, and
    a change after LR-020's final re-read is a change after acceptance, caught as stale by the next observation.
    P-081's O-33 addition amended, with a WP9.3-2 control (§7.2, §17, §18).
  - **The drain** (CodeRabbit): before a later pin's final check, every process started from the candidate checkout
    has exited, and none starts from it until the advance, because `load_current_binding` checks the checkout on disk,
    not the loaded modules. P-081 item 3 amended again (§9.1, §18, §21 C).
  - **The register's Discovery-only line** (CodeRabbit): qualified, as §4.3 already was: before W9 genesis the
    shared replay runs no W9 check (§18).
  - **The pre-pin collision check** (Codex P2): `replay_legacy` reduces W9 transactions only, so the check adds the
    public shared replay and a scan of every event's stream and created record IDs, with controls for a pre-existing
    W11 and generic collision (§9.1, §17, §18). Note only.
  - **The census counts constructions, not imports** (Codex P2): `discovery/spec.py:19` and
    `discovery/__init__.py:1` import and re-export `DiscoveryRuntime`, which the census as written would have failed.
    A positive control runs it on the current tree (§17). Note only.
- **Revision 7 (2026-11-08).** Answers a fourth round on PR #411: one CodeRabbit comment and three Codex P2s. Stephen
  chose each option in chat on 2026-11-08.
  - **LR-015's full subject** (Codex): an observation's `record_id` is derived from its registration, source identity,
    selector and importer tool, and the grant names that ID, so one grant covers one observation. P-081 item 12
    amended (§5.3, §12.1, §17, §21 L).
  - **Generic writers** (Codex): `CommandService.submit` and `submit_t2`, the two generic append sites, get W11's W9
    identity check before append. The T2 site was found while checking the comment. P-081 item 10 amended again (§4.3,
    §16, §17, §21 J).
  - **Discovery-only replay** (CodeRabbit): recorded as a known limit, because a check in `replay_discovery` would be a
    fifth U-7 site; the public shared replay refuses such a ledger, and a control shows it (§4.3, §17, §18, §19).
  - **The O-33 gap** (Codex): the observation's hashes and frozen copy come from the final re-read's bytes, and a later
    change is caught as stale at acceptance. Recorded as a reading of 06v's O-33 line, with a control that mutates the
    source in the gap (§7.2, §17, §18).
- **Revision 6 (2026-11-08).** Answers CodeRabbit's question on writer versions, tracked as issue #415. Stephen accepted
  option C of the issue's findings (posted on PR #411 as comment 6726327810), in his words "Yes, option C", as an
  amendment to P-081 item 3.
  - **Release is a binding advance.** A later pin is released on each W9 store by `AdvanceStoreBinding` to a `main`
    commit that holds the pin. From then on `load_current_binding` refuses a writer on pre-pin code, on the W11 path
    today and on the W9 path through §13's `ars legacy submit` (§9.1, §13).
  - **The premise of revision 4 was too narrow.** It cited the validator for historical binding links, which never
    compares with `HEAD`. The current-binding admission does compare it (§9.1).
  - **The freeze narrows** to the window from the final check to the advance, with the ledger head re-read just before
    the advance (§9.1). §18's writer-version item moves from human review to machine-checkable, and a pin-release
    control through the loader itself is added (§17, §18).
  - **The runtime-construction census** joins WP9.3-1 at Stephen's word ("Yes, add it", 2026-11-08): an AST census
    that production code builds `LegacyRuntime` and `DiscoveryRuntime` only at two allowed sites, both behind
    `load_current_binding`, with negative controls (§17). What the census cannot see is a human-review item (§18).
- **Revision 5 (2026-11-08).** Answers Codex's third round on PR #411. No owner decision changes.
  - **W9's catalogue stream ID in the W11 guard.** W11's check reads W9's fixed identities (`CATALOGUE_STREAM_ID`,
    `RESERVED_IDS` and the pinned W0 refs) from the code constants, so they are refused before W9 genesis too.
    `reduce_genesis` never enters the catalogue stream ID in `identities` (§4.3, §17).
  - **Open and lapsed proposals.** A proposal is open while it is unresolved and has not lapsed. It lapses 30 days
    after it is made, or at its Decision's `expires_at` if that is later. A lapsed proposal releases what LR-003's
    uniqueness rule held, and it can be neither reviewed nor resolved. This replaces the note's reading of the annex's
    "no live registration", under which a declined registration held its path forever (§4.6, §5.2, §6.2, §10.1, §17).
- **Revision 4 (2026-11-08).** Answers the second round of review comments on PR #411.
  - **W11 writes to W9 identities** (CodeRabbit and Codex): W11's admissible-target check also refuses a target that
    W9 claims or reserves. This is checked before append, through a lazy import, and is backed by replay. The boundary
    extends to `discovery/routes.py` and `discovery/runtime.py`. Stephen chose this on 2026-11-08, as an amendment to
    P-081 item 10 (§4.3, §16, §17, §19).
  - **The author's session as an input** (CodeRabbit and Codex): `RequestW9AuthorityReview` carries it for a
    membership table (§5.1). Each session ref needs a non-empty string after its prefix (§5.2, §17).
  - **The later-pin race** (CodeRabbit): a write freeze on each store from the final check to release, a recorded
    ledger head, and a re-check if the head moved. That every writer runs the pinned commit is recorded, not proved
    (§9.1, §18).
- **Revision 3 (2026-11-08).** Answers the review comments on PR #411. No owner decision changes, except item 8's
  amendment below.
  - **CodeRabbit:** `review_questions` is replay-checked as non-empty, because the schema sets no `minItems`. A
    `ReviewRequested` cardinality control is added (§5.2, §17). S-014's freshness at LR-020 is an owner check at
    resolution and an L-4 checklist line, because no record kind identifies a restore run (§10.2, §18). K′ is unchanged.
  - **Codex:** a pinned W0 signature ID is reserved from the pin. The first pin lands before L-3, and a later pin
    carries a pre-pin replay check, with re-derivation if the ID is already taken (§4.3, §9.1, §17). W9 identity claims
    are refused against non-W9 streams across the shared ledger, and each claiming event stands at version 1 of its
    own stream (§4.3, §17). For a membership table, the review request also carries the author's session, and replay
    refuses a verdict from it (§5.2, §5.5, §17). Stephen chose this on 2026-11-08, as an amendment to P-081 item 8.
- **Revision 2 (2026-10-29).** Reconciles the review of `a8604641` (`0dc63404` on `review/w9-wp9-3-note`):
  - **B-1:** LR-020's seven fixtures (§10.2, §17, §18); owner point K withdrawn; K′ added on S-014's timing.
  - **M-1:** the batch rules re-checked at LR-020 (§6.2, §10.1, §17). The review's "one open batch at a time" is not
    adopted, with the reason (§10.1).
  - **M-2:** every required field of the four W2 payloads, with its source and replay check, and the two derived IDs
    (§5.2, §17).
  - **M-3:** W9-C20's session limb checked as far as the payloads allow, and owner point H rewritten with options (a)
    and (b) (§3 row 24, §5.5, §21).
  - **M-4:** the export comes from the reference implementation and is rechecked by the runtime segmenter (§3 row 15,
    §11.1, §12.2, §17).
  - **m-1:** four commands stay unbound (§2.2). **m-2:** one whole-file item per registration (§10.5). **m-3:** copied
    refs (§4.2, §10.6). **m-4:** the C1 and C2 controls kept (§17). **m-5:** the JSON checks (§8.2). **m-6:** the
    per-transaction step (§6, §14). **m-7:** the binding sequence and the D-1 dependency (§13). **m-8:** both PRs
    re-verify genesis (§15). **m-9:** owner point G's rationale (§10.3, §21). **m-10:** the supersession carry (§3 row
    5), the `CONVENTIONS.md` vault alias (§3 row 23, §7.1), and owner point L.
  - **Info:** i-3 (§2.2), i-5 (§7.3); the review's probe results in §20. Owner point M added; D, E, F and I amended as
    the review disposed them.
- **Revision 1 (2026-10-28, `a8604641`).** First draft, for independent adversarial review.
