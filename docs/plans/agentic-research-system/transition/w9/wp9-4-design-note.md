# WP9.4 design note: adoption, discharge, citation status and the full path

**Date:** 2026-11-16<br>
**Status:** Revision 1, for independent review. Nothing in it is implemented, and no owner point is decided.<br>
**Package:** 06v WP9.4 ("Adoption, discharge and citation status"), proposed as two PRs, WP9.4-1 and WP9.4-2 (owner
point A).<br>
**Authority:** P-085 (WP9.4, note first). WP9.3 is complete: PRs #420, #428, #429, #432 and #434 (P-082, P-083,
P-084).<br>
**Base:** `main` at `4312dc63` (tree `f0662c10`), which records P-084 (PR #436). Every `path:line` below was read at
that commit.<br>
**Not authorized (P-085):** WP9.5 to WP9.7; live operations L-0 to L-5; creating a real store, or running genesis or
issuing a grant on one; any legacy write; any paper-root transition (P-073 item 4). Every store in this note is a
scratch store that a test creates under `tmp_path`.<br>
**Probe:** the author ran no prototype. §4's interface findings come from reading the code and schemas named there.
Each claim the review should probe is listed in §17.

## 1. What this note settles

06v WP9.4 predates the stage B command set. It lists three record kinds, but the route table gives the package 28
rows and seven record kinds, and three of 06v's interface questions (U-5, U-6, U-9) are still open. This note settles:

1. the rows WP9.4 routes, the commands it binds, and the split (§2; owner points A, B and D);
2. every obligation carried into WP9.4, each with a disposition (§3);
3. U-5, U-6 and U-9, each with `path:line`, and two further unverified interfaces (§4; owner point E);
4. what the WP9.3 authority flow already gives these rows, and the one record that does not fit it (§5; owner point
   C);
5. adoption (§6; owner points F and G), the suspension projection (§7) and discharge (§8; owner point H);
6. the legacy read interface that successor guards will call (§9);
7. the full path: paper root, source inventory, mapping and ownership (§10), and the citation status with its
   extractor (§11; owner point I);
8. the reference graph (§12), the CLI (§13), bindings and D-4 (§14);
9. the tests (§15), research assurance (§16), the review probes (§17), the stop rules (§18) and the owner points
   (§19).

## 2. Scope: rows, commands and the split

### 2.1 The rows

The legacy route table tags these rows `WP9.4` (`research_system/legacy/routes.py:450-454`):

| Rows | Record | Flow (stage B note §2) |
|---|---|---|
| LR-023, LR-026 to LR-029 | `legacy-adoption-decision` | all five steps |
| LR-030 to LR-034 | `legacy-discharge-relation` | all five steps |
| LR-035 | `legacy-paper-root`, ordinary | recorded directly by the analyst |
| LR-039 | `legacy-paper-citation-status` | recorded directly by the independent reviewer |
| LR-040 to LR-044 | `legacy-source-inventory` | all five steps |
| LR-045 to LR-049 | `legacy-transition-mapping` | all five steps |
| LR-050 to LR-055 | `legacy-ownership-transitioned` | all five steps, with two resolution rows |

That is 28 rows. 06v's WP9.4 text names only the first three records and the "legacy-side refusals" of a transition.
The WP9.2 note assigned the full path here because those refusals are the transition's own preconditions (WP9.2 note
§3, the `WP9.4` row of its tag table).

### 2.2 Rows the package depends on but does not own

Three WP9.4 rows read a Decision that another package routes:

| WP9.4 row | Reads | Owner today |
|---|---|---|
| LR-026, LR-027: the adoption's review names and matches the eligible session | LR-025, the reviewer-eligibility Decision | `WP9.7` (`routes.py:449`) |
| LR-035: an ordinary root needs the integration pilot passed | LR-022, the pilot outcome Decision | `WP9.7` |
| LR-054: the paper-root column of W9 §4.5 | LR-022 | `WP9.7` |

The suspension projection (§7) also reads two rows it does not own: LR-060 (`WP9.6`) and LR-061 (`WP9.7`).

**Owner point B: LR-024 and LR-025 move to WP9.4.** Without LR-025, LR-026 can never be met, so no adoption could be
reviewed, resolved or suspended on a store this code runs. W9-T8 and W9-T9 would then be tested only on forged
ledgers. The two rows use `ProposeW9AuthorityDecision` and `ResolveW9AuthorityDecision`, which are bound already, so
the move adds no census row. The WP9.2 note allows it: "Any later move of a row between packages is a change to this
table, made by the package that takes the row" (WP9.2 note §3). The alternative is to leave them with WP9.7 and
accept that adoption stops at LR-023 until then.

**Owner point D: LR-021 and LR-022 stay with WP9.7.** The pilot outcome binds every W9 §14.3 metric by hash, and the
metric helper is WP9.7's (06v WP9.7, O-26). Moving the rows would move that work. So on any store this package's code
runs, LR-035 and LR-054 refuse, which is what P-073 item 4 asks of the full-path rows: "built and tested, and refuse
until their §4.5 gate". Their positive paths are tested against a test route set that adds LR-021 and LR-022, as
WP9.2 tested its deferred reducers (WP9.2 note §3, "Reducers").

### 2.3 The commands

Seven command types execute the rows. Five are bound (`research_system/schema_registry.py:271-275`):
`ProposeLegacyRecord`, `RequestW9AuthorityReview`, `RecordW9AuthorityReview`, `ProposeW9AuthorityDecision` and
`ResolveW9AuthorityDecision`. Two are not: `CreateLegacyPaperRoot` (LR-035) and `RecordPaperCitationStatus` (LR-039).
The WP9.3 note foresaw exactly these two (WP9.3 note §2.2, "Consequence for later D-4s").

A W9 record event (`E:`) has no runtime-binding row of its own. Only command types and the four W2 event types have
rows (`schema_registry.py:268-282`), which is why WP9.3-2 added events and carried no D-4.

### 2.4 The split (owner point A)

- **WP9.4-1: adoption and discharge.** LR-023 and LR-026 to LR-034, plus LR-024 and LR-025 if owner point B is
  taken. It carries the suspension projection (§7), the legacy read interface (§9), and the interface records for U-5,
  U-6 and U-9. It binds no new command, so it changes no protected identity and carries no D-4.
- **WP9.4-2: the full path.** LR-035 and LR-039 to LR-055, the citation extractor (§11) and the reference-graph
  checks (§12). It binds `CreateLegacyPaperRoot` and `RecordPaperCitationStatus`, which is the whole D-4 delta (§14).

The reasons:
- the package then needs one D-4, in the PR whose rows cannot run on any store before WP9.7 anyway;
- WP9.4-2's citation status reads adoptions and their suspension, so it needs WP9.4-1 merged first;
- WP9.4-1 is the half that W9 §4.5 opens first (adoption follows a closed-reference acceptance; a paper-root
  transition comes last), so its review is the more urgent one.

WP9.4-1 merges first, and WP9.4-2 is cut from its main commit.

## 3. Carried obligations

| # | Source | Obligation | Disposition |
|---|---|---|---|
| 1 | P-085 item 3; 06v §2.8 | U-5, U-6 and U-9 recorded with `path:line` before code | §4. U-5 is answered. U-6 resolves differently from 06v's assumption (owner point E). U-9 is answered for WP9.4's half |
| 2 | P-085 item 3; WP9.2-2 record §7 (F-8, first limb) | The resolving Decision's proposal named the record by its pre-assigned ID and exact content hash | **Keep, in replay and at the preparer,** by widening `_check_resolution`'s gate from `WP9_3_ROWS` (`replay/reducers.py:1138`) to the WP9.4 resolution rows (§5.1) |
| 3 | P-085 item 3; P-081 item 12 (O-33 addition); WP9.3 note §7.2 | What follows from an observation that WP9.3 projects as stale is WP9.4's | §7. A stale or re-observed source suspends the adoption |
| 4 | Stage B note §7; WP9.3 note §3 row 9 | The kind of an adoption's successor use (`intended_use.successor_ref`, an `anyRef`) | §6.2 (owner point F) |
| 5 | P-073 item 4 (O-31) | The full-path rows are built and tested, and refuse until their §4.5 gate | §2.2 (owner point D) and §10 |
| 6 | Annex `suspension_rule`; P-072 item 3 | Suspension is projected from three inputs | §7 |
| 7 | 06v O-33 | A blob change blocks every open adoption or transition that binds the old blob | §6.4 and §10.4: the window re-read at LR-029, LR-044, LR-054 and LR-055 |
| 8 | 06v O-34 | Whole-file adoption of a binary or restricted input; the successor Task re-hashes at use | §6.1 gives the adoption subject. The re-hash is WP9.7's (§4.3) |
| 9 | 06v O-14, D-3 | The citation extractor and the reviewer's second derivation, compared | §11 |
| 10 | 06v O-29; W9-T21 | The paper-root records are acyclic | §12 |
| 11 | Stage B note §6 | `created_at` and `created_by_actor_id` from the proposal; W9-C11; W9-C20 to W9-C25 | **Keep,** for WP9.4's rows (§5.1, §15) |
| 12 | WP9.3 note §3 row 5 | Superseding a record that does not exist is refused at the preparer | Not WP9.4's. It stays with WP9.6 (LR-056) |
| 13 | P-084 item 7 | The L-0b and L-4 checklist lines | Not WP9.4's. Unchanged |

## 4. Interface findings (06v §2.8)

### 4.1 U-5: `source_import_refs` can carry a legacy reference without a schema change

- The field is an array of unique, non-empty strings, with no pattern
  (`.research-system/schemas/core/commands/create_task.schema.json:264-272`). `amend_task`, `task_created` and
  `task_amended` carry the same shape.
- No code under `research_system/command/` reads it. `_prepare_task_command` checks the Task's identity, project,
  revision and content hash, and returns the payload (`research_system/command/service.py:6020-6075`). The only
  writer of the field in the package sets it to `[]` (`research_system/evals/executors/release_tranche.py:376`).

So a legacy reference fits as a string, and no `core/commands` or `core/events` schema changes. What is missing is a
grammar. §9 fixes one: `w9-adoption:<obj_ id>`. WP9.7's CreateTask guard is the reader (06v §2.7, W9-T8). WP9.4
writes no successor-side code for it.

### 4.2 U-6: there is no W5 claim path that a legacy family can enter

06v assumed a hook in `research_system/assurance/` (06v §2.7, "likely `resolver.py`"). The reading does not support
that:

- `research_system/assurance/` holds the authority resolver, the lane model, the pack loader, the requirement
  validators and the relationship-facts store. None of them takes a claim's evidence as an input. `paper_claim`
  appears once, as a lane name (`assurance/models.py:13`).
- No command promotes a claim. The core command set has no such schema
  (`.research-system/schemas/core/commands/`).
- The one place a claim meets evidence is the artefact use resolver. Its consumer kinds include `claim_evidence`
  (`research_system/artefacts/authority.py:32-37`), its decision rules are exactly `claim_promotion` (`:295`), and a
  use request may require that decision kind (`research_system/artefacts/use_resolver.py:97`).
- That path takes registered artefacts only. A legacy result is never one: WP9.7's RegisterArtefact guard refuses a
  registered legacy file, and restricted bytes on every path (06v WP9.7, rules (a), (c) and (d)).

So today an unadopted legacy family cannot reach a claim through any code path, and no call site exists for "W5 blocks
claims resting on a family marked unadopted" (W9-T17's last clause).

06v §8's first stop rule applies: "an interface in §2.8 resolves differently from the plan's assumption". In a
note-first package the note is where that stop is taken.

**Owner point E.** The recommended reading:
- WP9.4 builds the predicate, `family_admissible` (§9), with its negative controls: an unadopted family, a suspended
  adoption, and an adoption for another use each return "not admissible", with the reason.
- WP9.4 binds it to no W5 call site, because none exists. W9-T17's last clause is then proven at the read interface
  only, and that limit is recorded in the decision entry for this note.
- The package that first gives a claim a legacy input carries the binding: a test that the new path calls
  `family_admissible` and refuses on "not admissible". No such package is planned under 06v; manuscript review is
  Gate 9's (W9 §12.2; P-047).

The alternative is to hold WP9.4 until such a path is designed.

### 4.3 U-9: where an adopted whole-file input is read and re-hashed

- The artefact use resolver re-hashes at use (`artefacts/use_resolver.py:310-317`), but it reads through the artefact
  content reader, and a restricted file is never an artefact (§4.2).
- So an adopted whole-file input reaches a successor Task by reference only: a `w9-adoption:` string in
  `source_import_refs` (§4.1), resolved against the adoption record through §9's interface, which returns the source's
  path, expected SHA-256 and byte length.
- The re-hash is successor-side code at dispatch or at use. That seam, and the request for
  `RecordAdoptionUseMismatch` (LR-061), are WP9.7's (06v WP9.7, "Use-time re-hash").

WP9.4's half is the adoption subject (§6.1) and the lookup (§9). It adds no successor-side read.

### 4.4 Two further unverified interfaces

They are recorded here in 06v's manner, and each is resolved in the code PR, with `path:line`, before the code that
depends on it.

| ID | Unverified | PR | How it is resolved |
|---|---|---|---|
| U-10 | LR-030's "the successor result artefact accepted, not only registered": which state of the generic projection means "accepted" for an artefact | WP9.4-1 | Read the artefact reducers and the use-authority stream. If no single state means it, stop and bring the choice to Stephen (§18) |
| U-11 | How a whole-file observation of a binary or restricted file carries its class. W9 §9 item 1 says the class is "the signed class of its producing task, or one the W0 signatory assigns", but an observation's `families` needs at least one named family (`.research-system/schemas/contracts/w9/legacy-observation.schema.json:179-`) | WP9.4-1 | Read WP9.3's observation checks for a `whole_file` selector. §6.1 assumes the class sits in the observation's one family entry |

## 5. What the WP9.3 flow gives, and what it does not

### 5.1 Reused unchanged

The five-step flow, the content hash, the pre-assigned refs, the streams, the lapse rules, review satisfaction
(approve only), the session rules and the grant subjects are WP9.3's (WP9.3 note §4 and §5; P-081). WP9.4 changes
none of them. It extends the tables that key them by kind or row:

| Table | Where | WP9.4 adds |
|---|---|---|
| `PRE_ASSIGNED_REFS` | `replay/reducers.py:83-88` | discharge, source inventory, mapping and ownership: `reviewer_ref` (review) and `decision_ref` (decision); adoption: `decision_ref` (and §5.2) |
| `_REQUEST_REVIEW_FIELD`, `_DECISION_PROPOSAL_FIELD`, `_FAMILY_REVIEW_FIELD` | `replay/reducers.py:90-102` | the request, decision-proposal and review fields of the five families |
| `REQUEST_ROWS`, `DECISION_ROWS`, `RESOLUTION_ROWS`, `RECORDED_EVENTS` | `legacy/preparers.py:57-73` | the same families' rows and recorded events |
| the row gate `WP9_3_ROWS` | `replay/reducers.py:79`, tested at eight sites (`:703`, `:719`, `:847`, `:908`, `:991`, `:1025`, `:1138`, `:1179`) | a `WP9_4_ROWS` set at the proposal, request, verdict, decision-proposal and resolution sites, so that each full check runs for WP9.4's rows. At `:1138` that is `_check_resolution` (G5, F-8's first limb) for LR-029, LR-034, LR-044, LR-049, LR-054 and LR-055 |
| `LEGACY_ROUTED_ROWS`, `LEGACY_DEFERRED_ROWS` | `routes.py:446-456` | each PR moves its rows from deferred to routed; the route test pins the counts |

`RESOLUTION_ROWS` maps one decision-proposal row to one resolution row. Ownership has two (LR-054, LR-055) for one
proposal row (LR-053). The resolution row is chosen by the record's direction, which `_ROW_DIRECTIONS` already fixes
(`replay/reducers.py:58-62`), and `_apply_ownership` already refuses a record whose direction differs from its row
(`:1041-1055`).

### 5.2 The adoption record has no review field (owner point C)

The accepted annex says the adoption proposal carries "its pre-assigned rev_ and dec_ IDs inside"
(`wp9-1-catalogue-owner-annex.yaml`, LR-023), that LR-026's new review "is the proposal's pre-assigned rev_ ID", and
that G5 requires "the record's review and Decision refs" to be the pre-assigned ones. The accepted schema does not
agree. `legacy-adoption-decision` has `decision_ref` and no review ref
(`.research-system/schemas/contracts/w9/legacy-adoption-decision.schema.json`; its properties are `observation_ref`,
`subject`, `intended_use`, `w5_consequence`, `qualifiers_to_discharge` and `decision_ref`). The other four families
all carry `reviewer_ref`.

Two ways to close it:

- **Derive the review ID (recommended).** The adoption's review ID is
  `derived_id("rev", "w9-adoption-review:" + record_id, utc_milliseconds(created_at))`, the rule that already derives
  an ownership record's ID (`legacy/records.py:111-143`). LR-023 reserves it with the proposal. LR-026 must open
  exactly that review. LR-029's `considered_review_ids` must be exactly it, and it must be satisfied on the record's
  hash. No schema changes, and G5 holds with "the record's review ref" read as the derived ID.
- **Revise the schema.** Add `reviewer_ref` to the adoption record. That is a new catalogue identity, a new O-8
  acceptance and a routed LR-002 (P-071 item 4; P-072 item 5).

The first keeps the accepted bytes. Its cost is that the adoption record does not show its review, so a reader must
derive the ID or follow the Decision.

## 6. Adoption (LR-023 to LR-029)

### 6.1 Subject

- **By family** (`subject_kind: families`). The observation is a `json_family_set` observation. Every named family
  is one of the observation's families. The observation is in a recorded closed-reference acceptance, and neither is
  superseded.
- **Whole file** (`subject_kind: whole_file`, `rehash_at_use: true`). The observation's selector is `whole_file`
  and its source kind is `restricted_untracked_file` or `untracked_file`, or it is a `git_tracked` file with no
  accepted membership table. A JSON result that has a membership table is adopted by family, never whole (W9 §9
  item 1: "For a binary or restricted input with no JSON family"). U-11 covers where its class sits.

An item observation (`inventory_item`) is not an adoption subject. W9 §9 item 1 names families and whole files only,
and a tracker row or a log entry has no successor use that W9 defines. The proposal refuses it.

W9-T1 holds as in WP9.3: no code derives adoption from source text. The class is the observation's, from its signed
W0 record.

### 6.2 Intended use (owner point F)

The schema gives `intended_use` a free `description` and a nullable `successor_ref` of any kind. Two rows need to
compare uses exactly: LR-039 ("an active adoption for the use 'evidence for the manuscript claims of paper X'") and
the admissibility predicate (W9 §9 item 4: "admissible to W5 for the named use only"). A free string cannot be
compared safely.

**Recommended:** replay accepts three `description` values only, each fixing `successor_ref`'s kind:

| `description` | `successor_ref` | Source |
|---|---|---|
| `w9-use:manuscript-claims/P01-A` or `…/P01-B` | null. The root may not exist yet (LR-035 comes later) | W9 §12.1 |
| `w9-use:task-input` | null, or a `tsk_` ref. Null when the Task is created after the adoption, which W9-T8 requires | W9 §9 item 2; §10 item 3 |
| `w9-use:claim-evidence` | null | W9 §9 item 2 |

This is narrower than the schema, as WP9.3's Q2 was narrower than note §10.2 (P-084 item 2). A use outside the three
is refused at LR-023. The alternative is to compare the free string byte for byte, which makes a typing difference a
silent mismatch at LR-039.

### 6.3 Qualifiers and the W5 consequence (owner point G)

LR-023 requires "no blocking qualifier for that use (W9 §9 item 4)". W9 §9 item 4 also says open
`open_review_finding` qualifiers "stay attached". The schema gives a qualifier a kind, a source ref and a text, and
no identifier, so no later record can name one qualifier as discharged. A discharge relation names a legacy item by
`item_kind` and `item_id` (§8), not a qualifier.

**Recommended reading:**
- `qualifiers_to_discharge` must equal the observation's `open_review_finding` qualifiers, as a set. An adoption can
  neither drop one nor add one.
- `w5_consequence` is one of two values: `admissible_for_named_use` when that set is empty, and
  `blocked_until_qualifiers_discharged` when it is not.
- A blocked adoption is admissible for `w9-use:task-input` and not for the two claim uses. It is unblocked only by a
  new adoption of a later observation whose qualifier set is empty. Nothing in v1 computes "discharged" for a
  qualifier.

That refuses too much, never too little. Its cost falls on the rung-4/5 families under A1 to A3, which stay blocked
for claim uses until their re-observation, which is what W9 §9 item 4 says of them.

### 6.4 The checks, by row

G1 to G5 and WP9.3's flow checks apply to every row and are not repeated.

| Row | Replay | Preparer only |
|---|---|---|
| LR-023 | The schema; §6.1's subject rules; §6.2's use; §6.3's qualifier set and consequence; the observation's acceptance recorded and not superseded; the derived review ID reserved (§5.2) | The observation is not stale and its source re-reads to the same identity (the window opens) |
| LR-024, LR-025 (owner point B) | The Decision names the adoption proposal by ID and hash, one session string, and its family, version, role profile and context grade. It is resolved by Stephen. It is not a G5 row (annex G5) | The session differs from the analyst's and from the observer's, as the attested strings show (WP9.3 note §5.5) |
| LR-026 | The review ID is the derived one; the named reviewer session is the resolved eligibility Decision's; W9-C20 and W9-C22 | — |
| LR-027 | The submitter is the named reviewer; `reviewer_model_metadata` and `reviewer_profile` equal the Decision's recorded values; W9-C21 | — |
| LR-028 | A positive review on the current hash; the Decision proposal's subject is the record's ID and hash | — |
| LR-029 | G5 with F-8's first limb; the adoption would not be projected suspended at this position (§7) | The source re-reads to the observed identity at commit (W9-T6, O-33) |

LR-029's fixtures (F-015, F-019, S-017, F-038) are conditional on facts about the family and the use. The record has
no fixture field, unlike the acceptance's `pilot_promotion`. They are evidence the review cites, and the row's
fixture list is a checklist line for the adoption's reviewer, not a replay check. The note records that as a limit.

## 7. The suspension projection (`P:legacy-adoption-status`)

An adoption's status is derived at replay, never stored in the record. It is `active` or `suspended`, with the cause.
The annex's `suspension_rule` gives three causes:

1. **A later observation of its source,** "whether or not the bytes changed". For a whole-file adoption that is any
   later observation of the same registration. For a family adoption it is a later observation of the same
   registration whose selector names at least one adopted family. `reduce_record` already keeps
   `observations_by_registration` in ledger order (`replay/reducers.py:1403-1414`), so "later" is a position in that
   list after the adoption's observation.
2. **A supersession of a record it relies on:** its observation, that observation's closed-reference acceptance, or
   the adoption itself. `state["supersessions"]` already holds the chain (`:1062-1077`).
3. **A recorded use-time mismatch** naming the adoption (LR-061).

The annex's item-adoption clause ("a later observation of the same item selector") has no subject under §6.1. The
projection implements it anyway, so that a later reading of §6.1 does not need a reducer change.

Suspension is permanent for that adoption record. "Until re-resolved" (W9 §9 item 5) is read as a new adoption of the
later observation, through LR-023 to LR-029 again. No row re-resolves an existing adoption, and the annex has none.

Causes 2 and 3 are written by rows WP9.4 does not route. Their reducers exist, and the projection reads their state.
They are tested on forged ledgers through a test route set, and the note for WP9.6 and WP9.7 inherits a binding test
each: a real LR-060 and a real LR-061 suspend an adoption.

W9-T9's control ("re-observe an adopted source with a new blob; the adoption suspends") runs on a real scratch store,
because LR-015 is routed.

## 8. Discharge (LR-030 to LR-034)

A discharge relation lets a successor result close a legacy open item. The checks:

| Row | Replay | Preparer only |
|---|---|---|
| LR-030 | The schema; the pre-assigned refs reserved; one open relation per `(item_kind, item_id)` | `item_id` resolves against the accepted open-item list (owner point H); the successor result artefact is accepted (U-10); the result's producer is read from the generic projection |
| LR-031 to LR-033 | WP9.3's flow checks; the reviewer is not the result's producer (G3), by the actor the proposal recorded | — |
| LR-034 | G5 with F-8's first limb | The artefact is still accepted, and the open-item list at the binding's `git_head` still holds the item |

LR-034 has no W9 §17 test (`discharge_no_w9_test`), so its controls are W9-C23 and the row's own negatives (§15).

**Owner point H: the open-item list.** "The accepted A-001 list or the audit (W0-D1)" is outside the store. It is read
as WP9.3 reads its outside inputs: a committed file in the W9 evidence area, `.research-system/evidence/w9/`, read at
the binding's `git_head` (WP9.3 note §11.1; P-081, owner point D). The proposed file is
`legacy-open-items.json`, of format `w9-legacy-open-items/1`: one row per item with `item_kind`, `item_id` and the
source it comes from. Its content is Stephen's, under W0-D1, and it is written at the live stage, not by this
package. WP9.4 fixes the reader and the format, and its tests use fixture lists. This adds one row to the W9 paths
addendum, as a dated amendment.

## 9. The legacy read interface

06v §2.7: "Each guard reads the store's W9 projection through the legacy package's read interface, not by importing
its internals." No such interface exists yet. Outside `research_system/legacy/`, the package is imported only by the
CLI, by replay and by the identity-collision check.

WP9.4-1 adds `research_system/legacy/read.py`, a leaf over the replayed legacy state, with three pure functions:

- `adoption_status(state, adoption_id)`: `active` or `suspended`, with the cause (§7).
- `resolve_adoption_ref(state, ref)`: parses `w9-adoption:<obj_ id>` and returns the adoption's observation, subject,
  use, status, and for a whole-file subject the source's path, SHA-256 and byte length. A malformed ref, or one that
  names no recorded adoption, raises.
- `family_admissible(state, observation_id, family_name, use)`: true only when an active adoption of that
  observation names that family for exactly that use and is not blocked for it (§6.3). Otherwise false, with one of
  the reasons `unadopted`, `suspended`, `other_use` or `blocked_by_qualifier`.

The functions read. A test asserts that no command preparer outside the legacy package imports anything else from
it, so the interface stays the only seam.

## 10. The full path (LR-035, LR-040 to LR-055)

### 10.1 The ordinary paper root (LR-035)

The schema closes the key and the path to P01-A and P01-B. Replay refuses a second root for a key, a `recovery`
value that is not null (that is LR-038, WP9.6), and a root with no passed pilot outcome Decision (LR-022). The last
check refuses on every store until WP9.7 (owner point D).

### 10.2 The source inventory (LR-040 to LR-044)

- **Complete membership.** The inventory is "complete over every file under the root at the observation commit"
  (LR-040). The preparer lists the root's tracked files at the binding's `git_head` with `git ls-tree -r`, and
  refuses unless the inventory's rows are exactly that set, by path and blob. Replay cannot see Git, so it checks
  what it can: row ordinals are 1 to n with no gap, paths are unique and under the root's `manuscript_root_path`, and
  every row's observation is recorded, names that path's registration, and carries that blob.
- **"Every row bound to an accepted observation."** Each row's observation is a `whole_file` observation in a
  recorded closed-reference acceptance. So a root's files are all observed and accepted before its inventory.
- **The window (LR-044).** At resolution the preparer re-reads every row's blob at `git_head`. A difference refuses
  with no event (W9-T6).

**A consequence the review should weigh.** An accepted whole-file observation of a `legacy_owned` file moves it to
`closed_reference` at LR-020 (P-072 item 2). LR-054 then needs `legacy_owned → successor_owned`. So the root's own
registration, the `legacy_manuscript_root`, must not be closed by a batch: its files are accepted, and the root
registration is the subject that transitions. §10.4 reads "subject" that way.

### 10.3 The mapping (LR-045 to LR-049)

Replay checks that the inventory is recorded and not superseded, that the target root is recorded and its key's path
is the inventory's root path, and that `mapped_row_ordinals` is a non-empty subset of the inventory's ordinals with
no repeat.

### 10.4 Ownership (LR-050 to LR-055)

- **LR-050** refuses `legacy_owned → closed_reference` (W9-C24, W9-T5). That direction is LR-020's only.
- **LR-054** (`legacy_owned → successor_owned`). The subject registration's role is `legacy_manuscript_root`.
  `mapping_ref` and `paper_root_ref` are both set, the mapping is recorded, and its target is that root. The current
  citation status of the root is complete and consistent (§11.3). Every adoption it cites is active at this position.
  The pilot outcome is passed (LR-022).
- **LR-055** (`successor_owned → closed_reference`). The subject is currently `successor_owned`. The annex adds no
  further precondition, and neither does this note.
- **The window.** At LR-054 and LR-055 the preparer re-reads the inventory's rows, as at LR-044.

**The rest of §4.5's paper-root column is not machine-checkable in v1.** LR-054 lists W0-D2 Stage 2 scope, the A-001
items "resolved or scoped out", the `pilot_promotion` evidence, the W9-D7 manuscript route and Stephen's batch
approval. The ownership record has no field for any of them. They are what the independent reviewer checks and what
Stephen's Decision attests, and the note records that as a limit, with one exception: the A-001 items. Replay can
check that every open item the evidence-area list marks as feeding this paper has a recorded discharge relation,
if owner point H's file carries a `feeds_papers` column. The recommendation is to add that column and that check, and
to treat "scoped out" as Stephen removing the paper from the item's row.

## 11. Citation status and the extractor (LR-039; D-3)

### 11.1 What is compared

D-3 is decided: both an extractor and a reviewer's derivation, and "a difference blocks" (06v §6). The record holds
two hashes, `extractor_output_sha256` and `reviewer_derivation_sha256`, and one `cited_family_set_sha256`. Three
things need a fixed form so the hashes mean something.

**Owner point I.** The recommended forms:

- **A cited file** is a registered `legacy_research_result` whose normalized repository path appears as a literal in
  the bytes of a file of the root, after `\` is read as `/`. The basename alone does not count: two results can share
  one.
- **The cited-family set** is every family of every cited file's accepted membership table, as sorted
  `(observation ID, family name)` pairs, in canonical JSON. A cited file with no accepted table, or no accepted
  observation, is a blocker entry, and a set with a blocker cannot be recorded.
- **Both hashes are of that same object.** The extractor's is computed by the preparer. The reviewer's is supplied,
  from a derivation made without the extractor's output.

The reviewer also reads the claim-trace audit's artifact map (W9 §12.1), which can show a file that the drafts cite
indirectly, by a table or a figure. The extractor cannot see that. The two hashes then differ and LR-054 blocks. That
is D-3 working, and the way out is a draft change or a recorded reading by Stephen, not a wider extractor.

Narrowing a cited file to the families a claim uses is not done in v1. It would need the artifact map in a format
this note cannot fix without reading it, and the wider set only asks for more adoption decisions or more "unadopted"
marks.

### 11.2 The extractor

`research_system/legacy/citations.py` is a pure function over bytes. Its input is the source inventory's rows: for
each, the blob named by the row's accepted observation, read from Git by blob ID at the binding's checkout. It never
reads the live tree (06v WP9.4, "Input"). Every file in the inventory is scanned, whatever its type. The preparer for
LR-039 runs it, stamps `extractor_output_sha256`, and refuses a supplied value, as preparers do for the content hash.

So LR-039 needs the root's accepted inventory first. The annex's "hashed and filed before the transition" is then
met by order: LR-044, then LR-039, then LR-050 to LR-054.

### 11.3 The record's checks

| Check | Where |
|---|---|
| The root is recorded; the submitter is not the root's creator, the mapping's analyst or the inventory's observer (the "transition's producer") | Replay |
| `families` is exactly the cited-family set: no pair missing, none extra, and `cited_family_set_sha256` is its hash | Replay recomputes the hash from `families`. The preparer checks it against the extractor's set when the two derivations agree |
| A family marked `adopted` names an active adoption of that observation and family for `w9-use:manuscript-claims/<key>`. One marked `unadopted` names none | Replay, at LR-039 |
| `supersedes_status_ref` names the root's current status, or is null when there is none | Replay |
| At LR-054: the root's current status exists; the two derivation hashes are equal; every cited adoption is still active | Replay |

W9-T17's first two clauses are the second and fifth rows: a status that omits a family in the set is refused at
LR-039, and drafts that cite a family missing from the set change the extractor's hash, which blocks LR-054.

## 12. The reference graph (W9-T21)

Replay already records edges for paper roots, mappings and ownership records (`replay/reducers.py:1152-1153`,
`:1390-1402`). WP9.4-2 adds the inventory and the citation status as sources, and refuses any edge that closes a
cycle among root, inventory, mapping, transition and citation status. The schema already keeps a root from naming its
transition. The recovery half of W9-T21 is WP9.6's.

## 13. The CLI

No new mutating verb. `ars legacy submit` already takes any W9 command envelope and refuses before bind (WP9.3 note
§13). WP9.4 adds read-only verbs only:

- `ars legacy adoption-status <adoption id>`: §9's status and cause;
- `ars legacy cited-families --root <root id>`: runs the extractor at the binding's `git_head` and prints the set and
  its hash, for the reviewer to compare after making their own derivation. It writes nothing.

## 14. Bindings and D-4

- **WP9.4-1** adds no `SchemaBinding` row. The census stays 273 rows, `0cca0414…4712`, and the 06h manifest and the
  smoke test keep their blobs. The PR states that and its review checks it. If the code finds it needs a row, that is
  a stop (§18).
- **WP9.4-2** adds command rows for `CreateLegacyPaperRoot` and `RecordPaperCitationStatus`, with their authority
  entries (`research_system/authority.py:208-252` lists the bound W9 commands and their subject kinds). The expected
  census is 275 rows. The code PR gives the exact row set, digest, manifest bytes and append-site classification, and
  Stephen re-accepts them at exact bytes in the merge-queue entry (06v D-4).
- Command-adding packages merge one at a time (06v §5). WP9.4-2 must not be in the queue with another one.

## 15. Tests

| Test | PR | Kind | Control |
|---|---|---|---|
| W9-T1 at LR-029 | 1 | unit | A `Done` status word in the source yields no adoption |
| W9-T6 at LR-029 | 1 | integration, scratch store | The source's bytes change after the proposal; resolution writes no event |
| W9-T8, legacy side | 1 | integration | `family_admissible` is false for an accepted, unadopted family; `resolve_adoption_ref` raises for an unknown adoption |
| W9-T9 | 1 | integration | Re-observe an adopted source, with a new blob and with the same blob; both suspend. Supersession and mismatch on forged ledgers |
| W9-T17, last clause | 1 | unit | §9's predicate, for unadopted, suspended, other-use and blocked (owner point E) |
| LR-034's negatives | 1 | integration | An unknown `item_id`; a registered but unaccepted artefact; the producer as reviewer |
| W9-T5 | 2 | unit | `successor_owned → legacy_owned` fails the schema; `legacy_owned → closed_reference` is refused at LR-050 |
| W9-T6 at LR-044, LR-054, LR-055 | 2 | integration | A row's blob changes inside the window |
| W9-T17 | 2 | integration | A status omitting a family; a draft citing a result outside the set; unequal derivation hashes at LR-054 |
| W9-T21, graph half | 2 | unit | A cycle among root, inventory, mapping and transition |
| W9-C11, W9-C20 to W9-C25 | both | integration | Per row, as the annex binds them |
| The route partition | both | unit | The routed and deferred counts after each PR; a deferred row is still refused before append |
| D-4 identities | 1 | contract | The census, manifest and tree IDs are unchanged |

Both PRs report their added test runtime. The test-runtime escalation is still open with Stephen (P-084, "Not decided
here"), and WP9.3-2 added about 4.4 minutes.

## 16. Research assurance

**Lanes.** `output_provenance` (every row) and `paper_claim` (LR-039, LR-054 and §9's predicate). No topology,
null-model, statistical or representation logic is touched: the package computes no research number.

**Governing texts.** W9 §§4.2, 4.5, 8.2, 8.3, 9, 12.1 and 17; the owner annex rows LR-023 to LR-055; P-072, P-073,
P-081 and P-085; 06v §2.7, §2.8 and D-3.

**Machine-checkable, with an enforcement artifact:** every replay check in §6, §7, §8, §10 and §11.3, each with a
negative control in §15; the D-4 identities.

**Human-review only, and why:**
- LR-029's conditional fixtures (§6.4): the record has no field for them;
- the rest of §4.5's paper-root column (§10.4): the ownership record has no field for it;
- the reviewer's citation derivation (§11.1): its independence is attested, and only its hash is checked;
- the content of the open-item list (§8): Stephen's, under W0-D1.

Passing these tests does not show that any real adoption is sound. That is the adoption's own review.

## 17. Claims the independent review should probe

1. `source_import_refs` is read nowhere under `research_system/command/` (§4.1).
2. No code path lets a claim take a legacy family as evidence (§4.2).
3. A W9 record event needs no runtime-binding row, so WP9.4-1 carries no D-4 (§2.3, §14).
4. The adoption schema has no review field, and a derived ID satisfies G5 as the annex states it (§5.2).
5. A root's registration is never closed by LR-020 before LR-054 needs it `legacy_owned` (§10.2).
6. `observations_by_registration` gives "later" correctly for a family adoption when two observations of one
   registration select disjoint family sets (§7).
7. The extractor's path-literal rule finds every result file the P01-A and P01-B drafts cite directly. The author
   did not read the drafts: `papers/P01-A-JRSSA/` and `papers/P01-B-JRSSB/` are outside this package's boundary.

## 18. Stop rules

06v §8 applies. In addition, the code stops and returns Partial when:
- U-10 or U-11 resolves so that §6.1 or §8 cannot be built as written;
- WP9.4-1 needs a runtime-binding row or a schema change;
- a WP9.4 row needs a successor-side edit outside `research_system/legacy/` and `research_system/cli.py`;
- a test needs a real paper file, a vault file or restricted bytes;
- a positive path for LR-035 or LR-054 can run without a passed LR-022.

## 19. Owner points

| # | Point | Recommended |
|---|---|---|
| A | The split | Two PRs: WP9.4-1 (adoption and discharge, no D-4), then WP9.4-2 (the full path, with D-4) (§2.4) |
| B | LR-024 and LR-025 | Move them from WP9.7 to WP9.4-1 (§2.2) |
| C | The adoption's review ID | Derive it; change no schema (§5.2) |
| D | LR-021 and LR-022 | Leave them with WP9.7. LR-035 and LR-054 refuse on every store until then (§2.2) |
| E | U-6, the W5 clause of W9-T17 | Build and test the predicate; record that no W5 call site exists; carry the binding to the first package that gives a claim a legacy input (§4.2) |
| F | The intended use | Three fixed `w9-use:` values (§6.2) |
| G | Qualifiers and the W5 consequence | The qualifier set is exact; two consequence values; a blocked adoption is admissible for task input only (§6.3) |
| H | The open-item list | A committed `w9-legacy-open-items/1` file in the W9 evidence area, with a `feeds_papers` column (§8, §10.4) |
| I | The citation comparison | Path-literal cited files; all families of each cited file; both hashes over that one set (§11.1) |

The note's review comes next, in a fresh session that wrote none of WP9.2, WP9.3 or this note. Stephen then decides
these points, and the code follows.
