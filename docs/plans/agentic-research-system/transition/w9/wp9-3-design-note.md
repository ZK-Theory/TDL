# WP9.3 design note: the observation reader, selectors, inventories and acceptance

**Date:** 2026-10-28<br>
**Status:** Revision 1, for independent adversarial review. Nothing in it is implemented.<br>
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
**Probe:** none. No prototype was run for this note. Its code claims rest on reading the code at `1f0d8281`, and §20
lists the claims the review should probe rather than take on trust.

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
WP9.4, WP9.6 and WP9.7 rows that share them. A binding grants nothing by itself. The runtime assigns every prepared
transaction to its row and refuses a deferred row before append, as replay already does
(`research_system/legacy/replay/driver.py:139-141`). A test submits a schema-valid `ProposeLegacyRecord` for an
adoption decision (LR-023, `WP9.4`) and expects that refusal, with the store unchanged.

**Consequence for later D-4s.** After WP9.3 only three W9 command types stay unbound: `CreateLegacyPaperRoot` and
`RecordPaperCitationStatus` (WP9.4) and `RecordAdoptionUseMismatch` (WP9.7). WP9.6's rows use commands already bound,
`CreateLegacyPaperRoot` included if WP9.4 merges first. So the packages that add census rows become WP9.2, WP9.3, WP9.4
and WP9.7, and WP9.6 adds one only if it lands before WP9.4. 06v D-4 expected WP9.2, WP9.3, WP9.4 and WP9.6; the WP9.2
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
  and F-8's second limb (owner point E); the Computational-Log exporter and its recheck; the `.apm/bus/` and `.apm/`
  inventories (O-19, O-36).

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
| 5 | P-080 item 3; record §7 ("Preparers generally") | Superseding a record that does not exist | **Keep, placed.** The preparer refusal belongs to the supersession proposal (LR-056 to LR-060, WP9.6), which WP9.3 does not build, and is carried to WP9.6's brief by name. WP9.3 adds the replay refusal to `_apply_supersession` (`replay/reducers.py:304-317`) now, tested on a forged ledger, because N-2 touches every record reducer anyway |
| 6 | WP9.2-2 record §3 item 8 | LR-014 accepts only `approve` under LR-013, on a review whose paired subjects name the record | **Keep,** and apply the same rule to every W9 review (owner point B; §5.4). The hash is recomputed (§14) |
| 7 | WP9.2-2 record §7, test gaps | Guard 5's reachability; the §2.5 asymmetry; the CLI read-only test; the verify-restore replay | Genesis and shared-replay gaps, not WP9.3's. Unchanged, except that WP9.3's CLI test binds a real scratch store instead of monkeypatching `_verified_ledger` (§13) |
| 8 | Stage B note §6, "WP9.2 runtime obligations with no stage B artefact" | The record content-hash rule; `created_at` and `created_by_actor_id` taken from the proposal; the retry control W9-C11; the behavioural controls W9-C20 to W9-C25 | **Keep,** all for WP9.3's rows: §4.1, §5.1 and §17 |
| 9 | Stage B note §7; stage A note §2 | The kinds of the `anyRef` fields: the signature record; a `pilot_promotion` evidence ref; the inventory's independent reproduction | The reproduction is a `rev_` (stage B note §7; `replay/reducers.py:369-377`). The signature record: owner point C (§9.1). A `pilot_promotion` evidence ref is a `rev_` or an `art_` (§10.2). The adoption's successor use is WP9.4's |
| 10 | Stage A note §3, "Left to WP9.2 and WP9.3" | Family-name uniqueness and pointer exclusivity (W9-T3); one entry per fixture within an item and one item per observation; a legacy role under `.research-system/projections/legacy/`; an inverted locator line span; a read that ends before it starts; the W9 kind an `obj_` ref names; the `anyRef` kinds | **Keep,** each in replay (§6, §9.3, §14). The recovery-root and supersession items are WP9.6's |
| 11 | Stage A note §2, restricted bytes | "D-9 matches suffixes, not content. A `.csv.gz` or a `.pickle` passes, and WP9.3's reader and WP9.7 own that scope" | **Keep, narrowly** (§7.4). The reader adds no content test of its own: a wider rule would be a new D-9 list, which is Stephen's |
| 12 | Stage A note §2 (re-review n-5) | The importer adds the inventory's selector kind to each row and fills the absent fields with null | **Keep** (§8.3) |
| 13 | Stage A confirmation r-1, the alternative it offered | An observation's source matches its registration's path and root | **Keep,** in replay (§6, LR-015) |
| 14 | Stage A confirmation i-1, i-2 | Refuse a legacy role under the projection directory; refuse an inverted line span | Row 10 |
| 15 | Segmentation contract §6.3; 06v D-7 | WP9.3's reader re-segments the retained export copy and must reproduce every row; a mismatch voids the export | **Keep:** the exporter's recheck mode (§12.2) |
| 16 | Segmentation contract §7; P-068 "Not authorized here" | A session independent of the contract's author and of WP9.3's implementer re-implements the contract and reproduces every vector before any export or observation under it is accepted | **Keep.** Owner point I proposes WP9.3-1's independent reviewer as that session |
| 17 | P-068 item 4 (confirmation C-1) | The classified entry list classifies each structural or blocker row as in the legacy region or not | **Keep:** the exporter emits a classification slot for every row (§12.2). The classification itself is L-0b's |
| 18 | 06v reconciliation m-9 | An anchor is an ancestor of the binding's `git_head` at the first acceptance, or an ARS event at a lower global position | **Keep the commit half;** owner point G on the event half (§10.3) |
| 19 | 06v O-32; confirmation c-1 | The acceptance preparer reads WP9.5's change list at the binding's `git_head`, unchanged | **Keep.** WP9.3 fixes the reader-side format (owner point D; §11.1) |
| 20 | WP9.2 note §4 | "WP9.3 and later packages add bindings and reducers, not a layout" | **Keep.** The four U-7 sites, `LEGACY_COMMAND_TYPES` and the row-assignment rules do not change (§14) |
| 21 | WP9.2 note §2.3, C2 | A W9 command that emits a W2 event type needs a producer binding, and the event carries the W2 schema | **Keep** (§16). The runtime's fixed event schema (`legacy/runtime.py:438`) becomes per event type |
| 22 | WP9.2 note §2.3, C3 and C5 | No W11 row in a W9 payload; no event type shared with another partition | **Keep.** The encodings of §5.2 carry no `W11:OR-` string. No WP9.3 row emits a shared event type, which the existing C5 test pins |

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
ID>}`. It depends on neither hash. It ties the ref to the record that pre-assigns it, and replay recomputes it and
refuses any other value. This is a reading of the schemas the review should check (§20); it fixes stored bytes, so it
belongs in this note, not in the code PR.

### 4.3 Identity claims (W9-C25)

- **At a proposal,** replay claims the record ID and every pre-assigned `rev_` and `dec_` in it, the latter reserved
  to that proposal. Today `reduce_proposal` claims only the record ID (`replay/reducers.py:206`), so W9-C25's "whose
  pre-assigned IDs already exist" is checked for one of three IDs.
- **A review request or Decision proposal** must take exactly its proposal's reservation, and converts it. That is the
  precondition "the new review's ID is the proposal's pre-assigned rev_ ID" of LR-007, LR-012 and LR-017, now checked
  at replay too. A reservation used by any other request, or a second proposal that pre-assigns a reserved ID, is
  refused.
- **The reserved external refs** and `CATALOGUE_STREAM_ID` stay refused (`replay/reducers.py:145-154`).
- **A batch's ownership record IDs** are derived and reserved at LR-016 (§10.5).

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

## 5. The authority flow

### 5.1 Command payloads

W9 follows W11's pattern: the command payload is small, and the preparer builds the W2 payload
(`discovery/runtime.py:1042-1219`).

| Command | The payload carries | The preparer builds |
|---|---|---|
| `ProposeLegacyRecord` | the record, without the preparer-set fields | `E:<kind>-proposed`, whose payload is the completed record |
| `RequestW9AuthorityReview` | the subject record ID, the reviewer's actor ID, the review questions | `ReviewRequested` (§5.2) |
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

The closed W2 payloads have no W9 subject field, so the subject travels in fields that exist. The encodings below are
fixed. Replay checks every field named here; it does not check the other fields (questions, lanes, deadlines), which
the preparer fills from the payload or from constants.

**`ReviewRequested`:**
- `review_type`: `migration`, from the W2 enum (`review_requested.schema.json:8-22`);
- `new_review_id`: the proposal's pre-assigned `rev_`;
- `subject_ids` exactly `[<record ID>]` and `subject_hashes` exactly `[<recomputed content hash>]`, paired. Today
  `reduce_review_request` zips them with `strict=False` (`replay/reducers.py:225`), which admits unpaired lists of
  the kind W11's two-to-one shape uses (`discovery/runtime.py:1090-1094`);
- `governing_refs`: exactly `["W9:LR-nnn"]`, which assigns the row (`legacy/routes.py:594-595`);
- `reviewer_capability`: exactly `[<the named reviewer's actor ID>]`, as W11 names its reviewer (`:1108`);
- `allowed_verdicts`: `["approve", "changes_requested", "reject", "unable_to_verify"]`, W11's set (`:1111`), so a
  conditional approval cannot be recorded at all (owner point B);
- `required_independence_grade`: `independent`;
- `satisfaction_authority`: the constant `ars://legacy/policy/w9-authority-review@1.0.0`, a name for §5.4's rule, as
  W11's is a name (`:1112`).

**`ReviewVerdictRecorded`:**
- `review_id`: the request's;
- `reviewer_actor_id`: the event's actor, which must be the request's named reviewer (W9-C21);
- `unchanged_subject_sha256`: the request's subject hash, which must still be the subject's recomputed hash (W9-C22);
- `reviewer_session` and `reviewer_model_metadata`: recorded as given (§5.5).

**`DecisionProposed`:**
- `new_decision_id`: the proposal's pre-assigned `dec_`;
- `decision_kind`: `migration_authority` (G5);
- `governing_evidence_refs`: exactly `["W9:LR-nnn", "w9-subject:<record ID>", "w9-subject-sha256:<recomputed content
  hash>"]`, in that order. `decision_proposed.schema.json:108-122` has no subject field, and the list's items are free
  strings (`:54-62`). W11 puts its subject hash in the same list (`discovery/runtime.py:1210`). `w9_row_ref` accepts
  these refs, since exactly one is a `W9:LR-` string and the others carry no `W9:` prefix (`legacy/routes.py:540-552`).
  `_refuse_w11_row` ignores them (`replay/driver.py:37-47`). Only a recovery Decision turns bare `obj_` refs into
  graph edges (`replay/reducers.py:333-334`), and the prefixes keep a record family's subject out of that set;
- `options`: `["accept", "reject"]`. A resolution must select `accept`, because every WP9.3 resolution row writes its
  record event (`legacy/routes.py:609-627`). No catalogue row records a rejection: a rejected proposal is simply not
  resolved, and the preparer refuses a resolution after the proposal's `expires_at`. This is a known limit, noted for
  the next catalogue revision.

**`DecisionResolved`:**
- `decision_id`: the Decision's;
- `selected_option`: `accept`;
- `governing_evidence_refs`: equal to the proposal's;
- `considered_review_ids`: `[<the proposal's pre-assigned rev_>]`, or `[]` for a path registration, which has no
  review;
- `deciding_actor_id`: the event's actor; `decision_authority_grant_id`: the grant.

### 5.3 Authority subjects (G4)

A scoped grant names one subject kind and one exact ID (`scoped-authority-grant-v2.1.0.schema.json:88-119`). It cannot
carry a content hash. So G4's exact subject is the ID, and the hash half of each row's `authority_subject` is a replay
and preparer check (§6).

| Command | Subject kind | Subject ID |
|---|---|---|
| `ProposeLegacyRecord`, `RecordLegacyLightInventory` | `scope_definition` | the record ID (the target stream) |
| `RequestW9AuthorityReview`, `RecordW9AuthorityReview` | `review` | the review ID |
| `ProposeW9AuthorityDecision`, `ResolveW9AuthorityDecision` | `decision` | the Decision ID |
| `ObserveLegacyRecord` | `scope_definition` | the registration's record ID (annex LR-015: "registration + …"), read from the payload's `registration_ref`, as Discovery reads `candidate_id` (`discovery/runtime.py:241-256`). The target stream is the observation's own ID |

These are W11's kinds for the same steps (`research_system/authority.py:231-234`). `LegacyRuntime._resolve_authority`
hard-codes `scope_definition` and the target stream today (`legacy/runtime.py:259-273`), and becomes a table. The risk
tier stays R2 (`:268`).

**Operator burden.** Every proposal, review and Decision needs its own grant on its own ID, which Stephen issues. A
20-item pilot needs tens of grant activations: for the registrations, a membership table per JSON schema, an inventory
per Markdown file, an observation grant per registration, and one batch. W9 §13.4 makes "operator
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

**Recorded, not proved** (a known limit, as P-058's single-family limit is):
- "a different session from the analyst" (W9 §8.6). The verdict records `reviewer_session`. That it differs from the
  analyst's session is the operator's attestation;
- LR-012's exclusion of the segmentation contract's author;
- G3 against a legacy item's producer. Legacy producers were APM-era sessions, not ARS actors, so the item's reviewer
  checks it. Code cannot.

## 6. The checks for each row

**The rule.** Replay checks everything the ledger determines. The preparer adds what only the environment can show:
file bytes, Git, the evidence area, the store binding, authority and the clock. It then runs the prepared transaction
through the same reducers on a copy of the projection before it appends, as Discovery's preparers do
(`discovery/runtime.py:1069-1082`). So a preparer is never weaker than replay, and a forged or faulty append is refused
by the next replay.

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
| LR-003 | Schema; content hash; identity claims; pre-assigned ref hash. No recorded registration, and no open registration proposal, of the same root and normalized path or of the same `physical_identity` `canonical_target` and `stable_file_id`. No legacy role under `.research-system/projections/legacy/` (stage A i-1) | A handle-bound read shows the path resolves to the declared `physical_identity` (§7.1). Every §4.4 detector's negative control is recorded as watched to fail, in the evidence area at the binding's `git_head` (§11.1) |
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
| LR-016 | Schema; content hash; claims (the record, `independent_review_ref`, `decision_ref`). The batch rules of §10.1, the structural `pilot_promotion` rules of §10.2, and the derived ownership list stored with the proposal (§10.5) | The window (§7.2), the anchors (§10.3) and the change list (§10.4) |
| LR-017 | As LR-007. The reviewer observed none of the batch's items | — |
| LR-018 | As LR-008 | — |
| LR-019 | As LR-009 | — |
| LR-020 | G5. The ownership records equal the stored list and the list recomputed at this position (§10.5) | The window, the anchors and the change list again, against the binding at resolution |

## 7. The reader

### 7.1 Read modes

| Source | How it is read | Window |
|---|---|---|
| `git_tracked`, at the binding's `git_head` | A handle-bound working-tree read and a Git object read of `<git_head>:<path>`, which must be byte-identical, as W11 requires (`discovery/runtime.py:1313-1336`) | Yes |
| A `conventions_lock` registration (`CONVENTIONS.md`) | A Git object read of blob `4620c71607ca3a06c6df3b8e96a6bddffc783960` (commit `4b143c92`) only (W9 §7.3 item 3). Any other source for that registration is refused | None |
| A Computational-Log entry | The accepted export's retained copy (owner point C), a committed file read from Git at its pinned commit. A read of the live vault page is refused for any registration whose role is `legacy_decision_log_entry` | None |
| `untracked_file` | A handle-bound read, with a frozen copy (§7.3) | Yes |
| `vault_file`, other than the Computational-Log | A handle-bound read through the real vault path, never the repository's `vault/` junction. The path form is recorded (contract §5.2), and the read must resolve to the registration's `physical_identity` `canonical_target` | Yes |
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

**Stale observations are projected.** An open observation is stale when a later observation of the same registration
holds a different blob (`git_tracked`) or SHA-256 (other kinds), or when its source re-reads differently at
acceptance. LR-016 and LR-020 refuse a stale item. So a blob change blocks every open observation that binds the old
blob (W9 §4.2 item 3). Adoption suspension is WP9.4's, and no WP9.3 row creates an adoption or a transition.

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
frozen-copy kinds already refuse by schema. The review should probe this seam (§20).

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
  accepted as numbers and recorded; any other departure from RFC 8259 blocks.
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
- §4.5's closed-reference column. The machine part: genesis, the pinned W0 signature (§9.1), and the detector controls
  (LR-003 already required them before the first registration). The rest (Gate 7 opened; G7-A, G7-B and G7-C
  accepted) are owner facts, which go on the L-4 checklist.

### 10.2 `pilot_promotion` (O-37; owner point K)

- Each item lists each fixture at most once (stage A §3).
- LR-020's catalogue set is F-017 (when the item is a sensitivity or comparison file), F-018 and F-023
  (`wp9-1-catalogue-owner-annex.yaml:729-735`). F-018 and F-023 are unconditional, so every item carries both. F-017
  is present when the reviewer marks the item a sensitivity or comparison file, which code cannot decide.
- A `waiver` ref is a `dec_` (schema). An `evidence` ref is a `rev_` or an `art_`: a review that graded the fixture,
  or an artefact holding the graded run.
- Applicability is proposed by the reviewer and fixed by Stephen's batch Decision (W9 §12.3). In the flow the analyst
  writes the proposal, the reviewer approves its exact hash (§5.4), and Stephen resolves on that hash. A change of
  applicability is a new proposal (LR-020).
- S-007 is listed on every review row with no condition. It is met mechanically by the W9-C22 controls, not by refs.
- Whether a ref is sufficient evidence is the reviewer's and Stephen's question.

**A gap for owner point K.** W9 §12.3 also assigns F-037 to "every result-family observation", S-005 to "items where
two results compete for one object", and F-038 to "any item using the TDA pack's lanes". LR-020's set omits all
three, although it holds F-018, whose §12.3 assignment is the same as F-037's. The catalogue is accepted (P-075), so
WP9.3 does not change it.

### 10.3 Thresholds and anchors (O-25, W9-T16; owner point G)

- Both hashes are present, and there is one anchor for each (schema).
- A `git_commit` anchor holds when the commit is an ancestor of the binding's `git_head` (`git merge-base
  --is-ancestor`), and the commit adds or changes a file whose bytes hash to the anchored SHA-256. That is what W9
  §14.3's "the hash is anchored in a Git commit" requires: the commit's ancestry gives the time, and its content gives
  the binding to the hash.
- Both are checked at LR-016, and again at LR-020 against the binding at resolution.
- An `ars_event` anchor is refused in v1 (owner point G). No W9 event carries a threshold hash, so the anchor would
  need a new event family to mean anything.
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
Stephen's Decision binds the acceptance's content hash, which fixes the list. No hash depends on itself, and the list
cannot change between proposal and resolution, which is the purpose of the re-review M-1 text. The review packet shows
the derived list, and the builder tool prints it.

### 10.6 LR-020

G5 (§6.1), the ownership list (§10.5), and the window, anchors and change list re-checked against the binding at
resolution. Each emitted ownership record then applies through `_apply_ownership` (`replay/reducers.py:287-301`), which
already holds LR-020 to the one direction `legacy_owned → closed_reference` (`:34-38`). The ownership record's
`reviewer_ref` and `decision_ref` are the acceptance's refs copied exactly, pre-assigned hashes included (§4.2).

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
| The Computational-Log export and its retained copy (D-7) | WP9.3's exporter, at L-0b | LR-011 and LR-015, through the pinned identity (§11.3) |
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

### 12.2 The Computational-Log exporter (D-7; O-21)

- **Export mode** reads a retained copy under segmentation contract §6. It emits every row the segmentation gives for
  the legacy region (items, structural blocks and blockers), each with its hash and offsets, plus the read times, the
  path form, the copy's SHA-256 and size, and the read's recorded limits. Each row has a classification slot for L-0b's
  classified list (P-068 item 4).
- **Recheck mode** re-segments the retained copy and compares it with a committed export. Any mismatch reports the
  export void (contract §6.3).

The exporter is never run on the live log, because L-0b is not authorized. Its tests use synthetic logs.

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
2. only then binds, through `_verified_ledger(control_root, read_only=False)` (`cli.py:1452`);
3. submits through `LegacyRuntime.submit`, which runs its own refusal again before the lock
   (`legacy/runtime.py:231-237`).

This keeps F-4 ("run `refuse_gate6_store` on the target control root before `_verified_ledger`") and widens it from
the control root's own manifest to the ancestor scan the runtime uses. The read-only `ars legacy` binding
(`cli.py:1513-1521`) is unchanged.

**The test binds a real scratch store,** not a monkeypatched `_verified_ledger` (§3 row 7). A Gate 6 control root, and
a scratch control root nested inside one, are each refused with every root byte-identical afterwards, directories
included. A valid scratch store accepts the command.

The tool subcommands (`inventory build`, `inventory reproduce`, `export`, `export recheck`, `apm-inventory`) open no
store.

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

`replay/driver.py`, the four U-7 sites and `legacy/commands.py` do not change. `legacy/routes.py` changes only its
routed set and tags, and the partition check of §15.

## 15. Genesis guard 8 and the route partition (owner point F)

`validate_legacy_route_registry` requires exactly 1 routed and 60 deferred rows (`legacy/routes.py:644-645`), and
genesis guard 8 calls it (`legacy/runtime.py:523`). Routing WP9.3's rows changes the partition in each PR: 14 routed
and 47 deferred after WP9.3-1, and 19 and 42 after WP9.3-2.

**The change.** The function checks that the routed and deferred sets partition the accepted rows exactly, with no
overlap and every deferred tag valid. The counts and the tags are pinned by the route test for each PR, not written
into the guard.

**The consequence.** This changes the genesis code path that WP9.2-2's independent review verified, and LR-001's L-3
precondition rests on that verification ("the bootstrap implementation independently verified against the accepted
contract"; P-079, "Not decided here"). So WP9.3-1's independent review must re-verify the genesis path at its head,
and the L-3 checklist must record which review verified the genesis code at the checkout L-3 runs from (with R-1).

## 16. Binding rows, authority entries and D-4

**At WP9.3-1:**
- seven `SchemaBinding("ars://core/command", "1.0.0", command_type=…)` rows, one per command of §2.2;
- four producer bindings, by C2 (WP9.2 note §2.3): `ReviewRequested` under `RequestW9AuthorityReview`,
  `ReviewVerdictRecorded` under `RecordW9AuthorityReview`, `DecisionProposed` under `ProposeW9AuthorityDecision`, and
  `DecisionResolved` under `ResolveW9AuthorityDecision`, each with its `ars://core/event/<type>` schema, following
  W11's rows (`schema_registry.py:275-292`, `:444-449`). `E:` events keep the `ars://core/event` fallback;
- `research_system/authority.py`: each of the seven commands in `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` (`:171-207`)
  and with its §5.3 subject kind in `_SCOPED_COMMAND_SUBJECT_KINDS` (`:209-333`). These entries are not a protected
  identity (WP9.2 note §3).

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
| W9-C20 to W9-C23, W9-C25 | Each refused, through `submit` and on a forged ledger | 1, 2 |
| N-2 | A record whose `content_hash` hashes other content is refused at replay; a payload that supplies `content_hash` is refused before append | 1 |
| Pre-assigned refs | A ref hash other than §4.2's rule; a second proposal pre-assigning a reserved ID; a request using another proposal's reservation | 1 |
| F-8, first limb | A resolution whose Decision proposal names another record or hash, refused at replay and at the preparer | 1 |
| Deferred row through a bound command | A `ProposeLegacyRecord` for LR-023 refused before any write | 1 |
| Supersession of a missing record | Refused at replay, on a forged ledger with WP9.6's rows routed on a test registry (§3 row 5) | 1 |
| W9-T1, W9-T2, W9-T3, W9-T4, W9-T13, W9-T22 | §9.2, §8.2, §8.2, §9.4, §9.3, §8.4 | 1 |
| W9-T6 (with O-33) | The source changed between observation and commit, and between observation and acceptance: no event, and the observation stale | 1, 2 |
| W9-T11, reader half | A `*.pkl` observed with a frozen copy is refused; a restricted observation records hash, size and path only | 1 |
| Frozen copy | A copy whose bytes differ from the observed bytes is refused | 1 |
| Segmenter | The contract's vectors against both implementations, and the differential test | 1 |
| Genesis | The existing genesis tests unchanged; the generalized partition check refuses a missing, overlapping or untagged row | 1 |
| CLI (F-4) | §13, on a real scratch store | 1 |
| D-4 | The census, the 06h manifest and the registry count at their new values | 1 |
| W9-T16 | §10.3's two controls, and an `ars_event` anchor refused | 2 |
| O-32 | Fixture change lists with and without an entry affecting an item; an absent list refused | 2 |
| O-37 | A missing F-018 or F-023, a duplicated fixture, and an evidence ref of the wrong kind, each refused | 2 |
| Ownership list (E) | An LR-020 that omits, adds or alters an ownership record, refused at replay | 2 |
| Exporter | Export and recheck over synthetic logs; a one-byte change in the retained copy voids the export | 2 |
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
- the structural `pilot_promotion` rules: the O-37 controls;
- the ownership list: replay, with the E controls;
- restricted bytes: W9-T11's reader half.

**Human-review-only,** with the question each reviewer answers:
- the W0 class (LR-017 and LR-018): "Does each family's class equal the class the signed W0 record gives that
  object?";
- precedence and canonical sources (LR-018): "Is each conflict's tier right, and does each `corrected_by` name the
  canonical file?";
- `pilot_promotion` (LR-018, then Stephen's batch Decision): "Is the fixture set right for each item, and does each ref
  evidence its fixture?";
- the governing-record set (O-25; W9 §14.3): "Is the set the reviewer compiled from G7-A §§4–10 and the audit
  complete?";
- membership families (LR-008): "Does each family follow its `definition_source`, not a key's name (template §3 rule
  8)?";
- session independence (§5.5): the operator's attestation.

## 19. Stop rules (06v §8) checked

- **An interface in §2.8 resolves differently.** None does. Two seams 06v does not list are settled here without a
  core schema change: the frozen copy (§7.3) and the evidence area (§11.1). The closed acceptance schema (§10.5) is not
  a §2.8 interface; it goes to Stephen as owner point E.
- **A W11 pin would change.** None does.
- **The shared-replay edit cannot be confined.** The four sites do not change (§14).
- **A test needs live legacy, vault or restricted bytes.** None does (§17).
- **A command would write a legacy file or the Gate 6 store.** None does: the tools refuse those outputs, and the CLI
  refuses before binding (§12, §13).
- **A protected identity changes without D-4.** §16 lists them.
- **A successor guard needs a core schema change.** Not applicable: WP9.3 has no successor guard.
- **A W9 §13.4 criterion applies.** Not to code. They are checked at L-4.

## 20. For the independent review: claims to probe

The note ran no prototype. These claims should be probed, not taken from its text:
1. The census grows by exactly 11 rows (§16): add the 11 rows in a scratch tree and recompute the census.
2. The frozen-copy seam (§7.3): a `RegisterArtefact` by a non-owner observer, then an observation naming it, with the
   bytes re-read through `ControlRootArtefactContentReader`.
3. The §5.2 encodings pass `w9_row_ref`, `assign_row` and `_refuse_w11_row` unchanged, and the W2 schemas accept them.
4. The shadow run of §6 can call the reducers on a copy of the projection inside `_submit_authorized` without a second
   whole-ledger replay.
5. The ownership derivation (§10.5) is deterministic and collision-free across batches.
6. `_verified_ledger(read_only=False)` writes nothing outside the control root before `submit`'s refusal (§13).
7. A bound `ProposeLegacyRecord` cannot reach any deferred row (§2.2).
8. The pre-assigned ref rule (§4.2) is free of circularity under every family's proposal and resolution.
9. Python's JSON parsing can meet template §3 rule 1 exactly: duplicate keys refused, the three non-finite tokens
   accepted and recorded, every other departure refused.
10. The line-ending claim of §7.1, at the reviewer's own checkout.

## 21. Owner points

Each needs Stephen's decision before the code. Each has a recommended option.

| # | Decision | Recommended | Alternatives |
|---|---|---|---|
| A | **The split** (06v D-6; P-064 item 6; P-080 item 1) | **Two PRs, if the review asks:** WP9.3-1 (LR-003 to LR-015, all seven bindings, D-4) then WP9.3-2 (LR-016 to LR-020, the exporter and the `.apm/` tools, no D-4) (§2.3). P-064 item 6 allows a WP9.3 split without fixing its shape; this shape departs from 06v's D-6 row ("reader and selectors"), which the decision records | One PR; or 06v's reader and selectors split |
| B | **Review satisfaction** | **`approve` only, for every W9 review,** with `approve_with_conditions` not even recordable (§5.4). The catalogue has no row to discharge a condition | Admit `approve_with_conditions` for authority reviews only, which needs a condition-discharge rule and a catalogue revision |
| C | **Accepted identities from outside the store** (O-27; D-7) | **Frozen constants in `accepted_w9.py`,** empty in WP9.3, so LR-015 refuses in production until a reviewed PR pins each after Stephen's acceptance: the W0-D1 signature (§9.1) and the export with its classified list (§11.3) | Read them from committed evidence files at `git_head`, which leaves Stephen's acceptance unchecked by code |
| D | **The W9 evidence area** | **`.research-system/evidence/w9/`,** with WP9.3 fixing the reader-side formats of WP9.5's files (§11.1) | `docs/plans/agentic-research-system/transition/w9/evidence/`; or WP9.5 defines the formats first, and LR-003, LR-015 and LR-016 wait for it |
| E | **LR-016's ownership list**, which the closed acceptance schema cannot hold (§10.5) | **Derived, not listed:** the list is a deterministic function of the proposal and the projection, stored at LR-016 and required exactly at LR-020, read as meeting the annex text's purpose. Recorded as a reading of `wp9-1-catalogue-owner-annex.yaml:567` | A catalogue revision adding the field (a new schema identity, a new O-8 acceptance and LR-002's revision path); or the list in the command payload only, which replay cannot check |
| F | **Genesis guard 8** (§15) | **Generalize the partition check,** have WP9.3-1's review re-verify the genesis path, and add the verifying review to the L-3 checklist | Keep the 1/60 literals and edit them in each PR, with the same review consequence |
| G | **Anchor kinds** (O-25; W9-T16) | **`git_commit` only in v1;** `ars_event` refused (§10.3) | Define an event anchor now, which needs an event that carries a threshold hash |
| H | **Roles and independence** (W9 §8.6) | **Exact-subject grants plus the distinctness rules of §5.5,** the owner refused on every non-resolver row, and session distinctness and legacy-producer exclusion recorded as a known limit | A role registry, which needs a new record kind and a catalogue revision |
| I | **The runtime segmenter and its independent re-implementation** (contract §7; P-067; P-068) | **A new `research_system/legacy/segmentation.py`,** differential-tested against the reference tool, which stays untouched; and WP9.3-1's independent reviewer re-implements the contract and reproduces every vector, as P-068 requires before any acceptance | Promote `tools/w9_segmentation.py` into the runtime, which moves an accepted blob; or a separate session for the re-implementation |
| J | **Boundary extension** (P-080's Boundary line) | **Extend it by name** to `research_system/authority.py` (§16) and `research_system/cli.py` (§13), as P-077 item 5 did for WP9.2. No `tools/` file is added (§12) | Keep the tools under `tools/`, which extends the boundary further |
| K | **LR-020's fixture set against W9 §12.3** (§10.2) | **Enforce the catalogue's set as the minimum** (F-018 and F-023 always, F-017 when the reviewer marks the item), let the reviewer propose the further §12.3 fixtures (F-037, S-005, F-038) for Stephen to fix in the batch Decision, and record the gap for the next catalogue revision | Require F-037 in code, which departs from the accepted catalogue; or enforce the catalogue's set as the maximum |

## Change log

- **Revision 1 (2026-10-28).** First draft, for independent adversarial review.
