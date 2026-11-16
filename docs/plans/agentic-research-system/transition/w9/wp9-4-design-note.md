# WP9.4 design note: adoption, discharge, citation status and the full path

**Date:** 2026-11-16<br>
**Status:** Revision 2, for independent re-review. It reconciles the independent review of revision 1 (`3c10de9a`):
`reviews/wp9-4-design-note-review-3c10de9a-2026-11-16.md`, on branch `review/w9-wp9-4-note` at `a9935c0b`, verdict
accept with required changes (1 Blocking, 13 Major, 12 Minor, 4 Info). §20 says where each finding went. Nothing in
this note is implemented, and no owner point is decided.<br>
**Package:** 06v WP9.4 ("Adoption, discharge and citation status"), proposed as two PRs, WP9.4-1 and WP9.4-2 (owner
point A).<br>
**Authority:** P-085 (WP9.4, note first). WP9.3 is complete: PRs #420, #428, #429, #432 and #434 (P-082, P-083,
P-084).<br>
**Base:** `main` at `4312dc63` (tree `f0662c10`), which records P-084 (PR #436). No code changed between that commit
and `3c10de9a`, so every `path:line` below reads the same at both.<br>
**Not authorized (P-085):** WP9.5 to WP9.7; live operations L-0 to L-5; creating a real store, or running genesis or
issuing a grant on one; any legacy write; any paper-root transition (P-073 item 4). Every store in this note is a
scratch store that a test creates under `tmp_path`.<br>
**Probe:** the author ran no prototype. The review ran 20 asserting pytest cases on pure functions, in-memory legacy
states, forged transactions and Git object reads (review §9). The author re-ran them at `3c10de9a` (20 passed) and
re-read the code behind each finding before acting on it. §17 lists the claims revision 2 makes for the re-review.

## 1. What this note settles

06v WP9.4 predates the stage B command set. It lists three record kinds, but the route table gives the package 28
rows and seven record kinds, and three of 06v's interface questions (U-5, U-6, U-9) were open. This note settles:

1. the rows WP9.4 routes, the commands it binds, and the split (§2; owner points A, B and D);
2. every obligation carried into WP9.4, each with a disposition (§3);
3. U-5, U-6, U-9, U-10 and U-11, each with `path:line` (§4; owner points E and J);
4. what the WP9.3 authority flow gives these rows, and the four places it does not fit (§5; owner points C and L);
5. adoption (§6; owner points F and G), the suspension projection (§7) and discharge (§8; owner point H);
6. the legacy read interface that successor guards will call (§9);
7. the full path: paper root, source inventory, mapping and ownership (§10; owner point K), and the citation status
   with its extractor (§11; owner point I);
8. the reference graph (§12), the CLI (§13; owner point M), bindings and D-4 (§14);
9. the tests (§15), research assurance (§16), the claims for the re-review (§17), the stop rules (§18), the owner
   points (§19) and the change log (§20).

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
table, made by the package that takes the row" (`wp9-2-design-note.md:191-192`).

The rows do not fit WP9.3's Decision checks as they stand (review M-12). §5.5 gives the encoding the move needs. One
part of it is Stephen's to confirm: the eligibility Decision's kind. P-073 item 3 names a kind for the pilot outcome
(`result_interpretation`) and none for eligibility, and the annex is silent. §5.5 proposes `migration_authority`.

The alternative is to leave the rows with WP9.7 and accept that adoption stops at LR-023 until then. WP9.7 would
then own §5.5.

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

A W9 record event (`E:`) has no runtime-binding row of its own. It is recorded under `ars://core/event` 1.0.0 with no
binding lookup (`research_system/legacy/runtime.py:553-560`; review i-2). Only command types
(`schema_registry.py:268-277`) and the W2 event types a W9 command produces (`:279-302`) have rows. That is why
WP9.3-2 added events and carried no D-4.

### 2.4 The split (owner point A)

- **WP9.4-1: adoption and discharge.** LR-023 and LR-026 to LR-034, plus LR-024 and LR-025 if owner point B is
  taken. It carries the suspension projection (§7), the legacy read interface (§9), and the G5 changes of §5. It
  binds no new command, so it changes no protected identity and carries no D-4.
- **WP9.4-2: the full path.** LR-035 and LR-039 to LR-055, the citation extractor (§11) and the reference-graph
  checks (§12). It binds `CreateLegacyPaperRoot` and `RecordPaperCitationStatus`, which is the whole D-4 delta (§14).

The reasons:
- the package then needs one D-4, in the PR whose rows cannot run on any store before WP9.7 anyway;
- WP9.4-2's citation status reads adoptions and their suspension, so it needs WP9.4-1 merged first;
- WP9.4-1 is the half that W9 §4.5 opens first (adoption follows a closed-reference acceptance; a paper-root
  transition comes last), so its review is the more urgent one.

WP9.4-1 merges first, and WP9.4-2 is cut from its main commit. The alternative is one PR, with one larger review.

## 3. Carried obligations

| # | Source | Obligation | Disposition |
|---|---|---|---|
| 1 | P-085 item 3; 06v §2.8 | U-5, U-6 and U-9 recorded with `path:line` before code | §4. U-5 is answered. U-6 is answered: the call site is the artefact path, and WP9.7 binds it (owner point E). U-9 is answered for WP9.4's half |
| 2 | P-085 item 3; WP9.2-2 record §7 (F-8, first limb) | The resolving Decision's proposal named the record by its pre-assigned ID and exact content hash | **Keep, in replay and at the preparer,** by widening the row gate to the WP9.4 resolution rows (§5.1) |
| 3 | P-085 item 3; P-081 item 12 (O-33 addition); WP9.3 note §7.2 | What follows from an observation that WP9.3 projects as stale is WP9.4's | §7. An adoption whose observation is stale is suspended, whatever the later observation selects |
| 4 | Stage B note §7; WP9.3 note §3 row 9 | The kind of an adoption's successor use (`intended_use.successor_ref`, an `anyRef`) | §6.2 (owner point F) |
| 5 | P-073 item 4 (O-31) | The full-path rows are built and tested, and refuse until their §4.5 gate | §2.2 (owner point D) and §10 |
| 6 | Annex `suspension_rule`; P-072 item 3 | Suspension is projected from three inputs | §7 |
| 7 | 06v O-33 | A blob change blocks every open adoption or transition that binds the old blob | §6.5, §7 and §10.5: the window re-read at LR-029, LR-044, LR-054 and LR-055, and the stale rule |
| 8 | 06v O-34 | Whole-file adoption of a binary or restricted input; the successor Task re-hashes at use | §6.1 gives the adoption subject. The re-hash is WP9.7's (§4.3) |
| 9 | 06v O-14, D-3 | The citation extractor and the reviewer's second derivation, compared | §11 |
| 10 | 06v O-29; W9-T21 | The paper-root records are acyclic | §12 |
| 11 | Stage B note §6 | `created_at` and `created_by_actor_id` from the proposal; W9-C11; W9-C20 to W9-C25 | **Keep,** for WP9.4's rows (§5.1, §15) |
| 12 | WP9.3 note §3 row 5 | Superseding a record that does not exist is refused at the preparer | Not WP9.4's. It stays with WP9.6 (LR-056) |
| 13 | P-084 item 7 | The L-0b and L-4 checklist lines | Not WP9.4's. Unchanged |
| 14 | P-072 item 4 | Per-fixture evidence or waiver refs travel in the resolving Decision | §5.4 (owner point L) |
| 15 | 06v WP9.4, "Successor-side refusals" | The CreateTask guard refuses a Task whose `source_import_refs` reference an unadopted family (W9-T8) | Outside P-085's boundary (owner point J; §4.1) |

## 4. Interface findings (06v §2.8)

### 4.1 U-5: `source_import_refs` can carry a legacy reference without a schema change

- The field is an array of unique, non-empty strings, with no pattern
  (`.research-system/schemas/core/commands/create_task.schema.json:264-272`). `amend_task`, `task_created` and
  `task_amended` carry the same shape.
- No file under `research_system/command/` contains the name. `_prepare_task_command` checks the Task's identity,
  project, revision and content hash, and returns the payload (`research_system/command/service.py:6020-6075`). The
  only writer of the field in the package sets it to `[]` (`research_system/evals/executors/release_tranche.py:376`).
  The review confirmed this (i-1).

So a legacy reference fits as a string, and no `core/commands` or `core/events` schema changes. §9 fixes the grammar:
`w9-adoption:<obj_ id>`.

**Owner point J: who builds the CreateTask guard.** 06v is not consistent about it:
- 06v WP9.4 lists it under "Successor-side refusals (resolve U-5 and U-6 first)"
  (`06v-w9-implementation-plan.md:463-465`);
- 06v §4's test table assigns "W9-T8 no successor use without adoption" to "WP9.4 (legacy side), WP9.7 (CreateTask
  guard)" (`:231`);
- 06v WP9.7's own list does not include it (`:523-557`).

Revision 1 followed the test table and said the guard was WP9.7's. The review is right that nothing then makes
WP9.7 build it (M-11). The guard edits `research_system/command/service.py`, which P-085's boundary excludes.

*Recommended:* move the guard to WP9.7 by a recorded decision, with its binding test: a Task whose
`source_import_refs` name `w9-adoption:<id>` for an unknown, suspended or wrong-use adoption, or name a legacy
observation directly, is refused. WP9.7 already edits the command service for its other guards and takes them to
one review. *The alternative* is to widen P-085's boundary to `service.py` for this one guard. That puts a
generic-service edit in WP9.4-1 and gives it a successor-side review surface it otherwise lacks.

Until J is decided, §15's "W9-T8, legacy side" is half of what 06v's WP9.4 text asks.

### 4.2 U-6: the claim path is the artefact path, and it is open today

Revision 1 said no code path lets a claim take a legacy family. That was wrong (review B-1). The author checked the
review's evidence and it holds:

- **The path.** `SetArtefactUseAuthority` to `accepted_for_scope` needs a governing review and a `claim_promotion`
  Decision (`research_system/command/service.py:4618-4631`; `_claim_promotion_binding` requires the Decision's kind
  and an `effective_scope` of `claim_promotion:<accepted_scope>`, `:4927`, `:4940-4943`). `resolve_for_claim` and
  `resolve_for_manuscript` then resolve `claim_evidence` and `manuscript_evidence`
  (`research_system/evidence/consumers.py:63-78`; `research_system/artefacts/authority.py:32-37`).
- **Nothing keeps legacy bytes out of it.** `RegisterArtefact`'s preparer checks the artefact's identity, its
  initial `candidate` authority, its regenerability claim and an empty stream, and nothing about its path or content
  (`service.py:4409-4440`).
- **The guard revision 1 relied on is not built.** It is WP9.7's (06v WP9.7, O-22), and P-081 already records it as a
  dependency (`03-decisions-and-open-questions.md:5274`).
- **That guard is keyed by path.** 06v WP9.7 rule (a) refuses when "the resolved path is a manifest-registered legacy
  file". The use resolver reads bytes only under the control root (`research_system/artefacts/runtime.py:31-50`). So
  a byte copy of a legacy result, registered under the control root, passes rule (a), rule (b) (not the `repo` root)
  and rule (d) (a `.json`). The review reasoned this from the code and did not run it. Neither did the author.

So W9-T17's last clause ("a family marked unadopted blocks its claims in W5") has a call site, and that call site
admits an unadopted family today.

**Owner point E.**

*Recommended:*
- **WP9.4 builds two read functions** (§9): `family_admissible`, and `legacy_content_matches`, which returns every
  recorded observation whose source SHA-256 or Git blob equals a given artefact's.
- **WP9.7 binds them, in two places.** Its `RegisterArtefact` guard keeps 06v's path rule (a). Its guard on the use
  path adds a content rule: when `resolve_for_claim` or `resolve_for_manuscript` resolves an artefact whose bytes
  match a recorded legacy observation, it is refused unless every family of every matching observation is
  admissible for that consumer's use. The check sits at use, not only at registration, because an adoption can
  suspend after the artefact is registered.
- **WP9.7's note inherits a binding test:** an unadopted family's bytes, copied under the control root, registered
  and promoted, are refused at `resolve_for_claim` and at `resolve_for_manuscript`. The decision entry for this note
  records that carry, as P-081 recorded WP9.3's.
- **WP9.4 proves the predicate only.** W9-T17's last clause is complete when WP9.7's binding test passes, not
  before.

A known limit stays: content identity catches a byte copy. It does not catch a re-serialized or partly copied
result. That case is for the artefact's own governing review.

*The alternative* is for WP9.7 to refuse every artefact whose bytes match a legacy observation, adopted or not. It
is simpler and needs no use mapping. Its cost is that an adoption for a claim use then has no consumer until some
other path is designed, so W9 §12.1's "adopted for 'evidence for the manuscript claims of paper X'" could not be
acted on.

Revision 1's other alternative, holding WP9.4 until a claim path is designed, is withdrawn. The path exists.

### 4.3 U-9: where an adopted whole-file input is read and re-hashed

- The artefact use resolver re-hashes at use (`artefacts/use_resolver.py:310-317`), but it reads through the control
  root's content reader, and restricted bytes never enter the store (W9 §5.4).
- So an adopted whole-file input reaches a successor Task by reference only: a `w9-adoption:` string in
  `source_import_refs` (§4.1), resolved against the adoption record through §9's interface, which returns the source's
  path, expected SHA-256 and byte length.
- The re-hash is successor-side code at dispatch or at use. That seam, and the request for
  `RecordAdoptionUseMismatch` (LR-061), are WP9.7's (06v WP9.7, "Use-time re-hash").

WP9.4's half is the adoption subject (§6.1) and the lookup (§9). It adds no successor-side read.

### 4.4 U-10 and U-11, settled

Revision 1 left both to the code PR. The review showed they can be settled now (m-6), and the author re-read both.

- **U-10: "the successor result artefact accepted, not only registered" (LR-030).** The one accepted state is
  `use_authority: accepted_for_scope`. Reaching it needs a governing review and a `claim_promotion` Decision whose
  `effective_scope` is `claim_promotion:<accepted_scope>` (`service.py:4618-4631`, `:4927`). So a discharge needs
  its successor result promoted at claim level first. That is a real cost, and it is the accepted row's. §8 adds the
  check that follows: the discharge's preparer reads the artefact's current authority and refuses anything else.
- **U-11: where a whole-file observation carries its class.** A `whole_file` observation carries exactly one family
  entry, named `whole_file`, and that entry has the `w0_class` (`replay/reducers.py:1299-1302`;
  `.research-system/schemas/contracts/w9/legacy-observation.schema.json:179-`). §6.1's assumption holds.

## 5. What the WP9.3 flow gives, and where it does not fit

### 5.1 Reused, with the tables extended

The five-step flow, the content hash, the pre-assigned refs, the streams, the lapse rules and review satisfaction
(approve only) are WP9.3's (WP9.3 note §4 and §5; P-081). WP9.4 extends the tables that key them by kind or row:

| Table | Where | WP9.4 adds |
|---|---|---|
| `PRE_ASSIGNED_REFS` | `replay/reducers.py:83-88` | discharge, source inventory, mapping and ownership: `reviewer_ref` (review) and `decision_ref` (decision); adoption: `decision_ref`, plus the derived review ID (§5.2) and, under owner point B, the derived eligibility Decision ID (§5.5) |
| `_REQUEST_REVIEW_FIELD`, `_FAMILY_REVIEW_FIELD` | `replay/reducers.py:90-94`, `:102` | **Replaced** by the resolver of §5.2 |
| `_DECISION_PROPOSAL_FIELD` | `replay/reducers.py:95-99` | the five families' Decision field, which is `decision_ref` for each |
| `REQUEST_ROWS`, `DECISION_ROWS`, `RESOLUTION_ROWS`, `RECORDED_EVENTS` | `legacy/preparers.py:57-73` | the same families' rows and recorded events |
| the analyst rule | `replay/reducers.py:758-778` | §5.3 |
| `LEGACY_ROUTED_ROWS`, `LEGACY_DEFERRED_ROWS` | `routes.py:446-456` | each PR moves its rows from deferred to routed; the route test pins the counts |

**The row gate.** `row_id in WP9_3_ROWS` occurs at ten lines of the reducers (review m-1). A `WP9_4_ROWS` set joins
it at six of them:

| Line | Site | Widens? |
|---|---|---|
| 703 | proposal checks | Yes: every WP9.4 proposal row |
| 719 | pre-assigned reservations | Yes |
| 737 | storing an acceptance's derived ownership list | No. Only LR-016 has one |
| 847 | review request | Yes |
| 908 | review verdict | Yes |
| 991 | Decision proposal | Yes |
| 1025 | LR-020's ownership reservation | No. LR-054 and LR-055 have proposals of their own |
| 1138 | `_check_resolution` (G5, F-8's first limb) | Yes: LR-029, LR-034, LR-044, LR-049, LR-054, LR-055 |
| 1179 | light inventory | No |
| 1387 | observation checks | No. LR-015 is WP9.3's, apart from §10.2's one refusal |

`RESOLUTION_ROWS` maps one decision-proposal row to one resolution row. Ownership has two (LR-054, LR-055) for one
proposal row (LR-053). The resolution row is chosen by the record's direction, which `_ROW_DIRECTIONS` already fixes
(`replay/reducers.py:58-62`), and `_apply_ownership` already refuses a record whose direction differs from its row
(`:1041-1055`).

### 5.2 The adoption record has no review field (owner point C)

**The gap.** Two accepted texts say the adoption proposal carries its review ID:
- P-072 item 1: "The proposed content already carries the pre-assigned `dec_` and `rev_` IDs, so no hash depends on
  itself";
- the annex, LR-023: "its pre-assigned rev_ and dec_ IDs inside"; LR-026: the new review "is the proposal's
  pre-assigned rev_ ID"; and G5: "the record's review and Decision refs" are the pre-assigned ones.

The accepted schema does not. `legacy-adoption-decision` has `decision_ref` and no review ref. Its properties are
`observation_ref`, `subject`, `intended_use`, `w5_consequence`, `qualifiers_to_discharge` and `decision_ref`
(`.research-system/schemas/contracts/w9/legacy-adoption-decision.schema.json`). The other four families all carry
`reviewer_ref`.

**Why it is dangerous as the code stands.** The three G5 tables map a row or kind to a record field name. Where
`_FAMILY_REVIEW_FIELD.get(kind)` is `None`, three sites read that as "this kind needs no review": the Decision
proposal (`replay/reducers.py:965-969`), the resolution (`:1092-1093`, `:1118-1119`) and the preparer
(`legacy/preparers.py:512`, `:521`). That default exists for path registrations. An adoption left out of the table
would be resolved with no review at all, and the review's probe shows `_check_resolution` accepting exactly that
(M-2).

*Recommended: derive the ID, behind one resolver.*
- The adoption's review ID is `derived_id("rev", "w9-adoption-review:" + record_id, utc_milliseconds(created_at))`,
  the rule that already derives an ownership record's ID (`legacy/records.py:111-143`). LR-023 reserves it with the
  proposal.
- One function, `review_id_for(kind, record)`, replaces `_REQUEST_REVIEW_FIELD` and `_FAMILY_REVIEW_FIELD`. It
  returns the field's ID for the kinds that carry one, the derived ID for an adoption, and the constant "none
  required" for a path registration only. Any other kind raises. Every site that reads those tables today calls it,
  in replay (`:797`, `:965-969`, `:1092-1093`, `:1118-1119`) and in the preparer (`preparers.py:389`, `:512`,
  `:521`). Those are all of them: a search for the two names finds no other read.
- LR-026 must open exactly that review. LR-028 needs it satisfied on the current hash. LR-029's
  `considered_review_ids` must be exactly it.

This is a reading of P-072 item 1, LR-023 and G5, not a literal match. The derived ID is fixed by `record_id` and
`created_at`, both of which the content hash covers, so the proposal still fixes its review and no hash depends on
itself. But the ID is not "inside" the record, and "the record's review ref" is read as "the review ID the record
determines". A reader of an adoption record must derive the ID or follow the Decision.

*The alternative: revise the schema.* Add `reviewer_ref` to the adoption record. That meets both texts literally. It
is a new catalogue identity, a new O-8 acceptance and a routed LR-002 (P-071 item 4; P-072 item 5).

### 5.3 The analyst rule

`_refuse_analyst_creator` refuses an analyst who requests a review of, or proposes a Decision on, a proposal they
created, and exempts only the path registration and the acceptance (`replay/reducers.py:769-778`). The exemption's
reason is that those are "the analyst's own proposals" (WP9.3 note §5.5). Unchanged, it refuses the analyst on
every WP9.4 kind the analyst proposes (review M-3).

The annex makes `migration_analyst` the proposer of LR-023, LR-030, LR-045 and LR-050, and the requester of their
review and Decision rows. So:
- **adoption, discharge, mapping and ownership join the exempt set.** They are the analyst's own proposals, by the
  accepted rows;
- **the source inventory does not.** Its proposer is its observer (LR-040). `_creator_role_actor`
  (`:758-766`) gains a case returning the inventory's `observer_actor_id`, so the analyst who requests its review
  cannot be that observer.

The reviewer exclusions are unchanged: a reviewer is never the proposal's creator, and the reviewer's session
differs from every session the request records (`:865-896`).

### 5.4 Fixture refs in the resolving Decision (owner point L)

P-072 item 4 (accepted): "Per-fixture evidence or waiver refs travel in the resolving Decision, or, for a
closed-reference batch, in the record itself" (`03-decisions-and-open-questions.md:4618-4620`). LR-020 took the
second route: its items carry `pilot_promotion` in the record. WP9.4's five records have no fixture field, so the
first route applies to them.

Revision 1 made the fixtures a reviewer's checklist. That drops an accepted decision, and it also misread the annex:
several fixtures are unconditional (`when: null`), S-017 on LR-029 among them (review M-4).

WP9.3's encoding has no room for them. A Decision proposal's `governing_evidence_refs` must be exactly three
entries, and the resolution's are those same three (`replay/reducers.py:938-946`, `:1102`).

*Recommended: encode them.*
- A WP9.4 Decision proposal's `governing_evidence_refs` is the three subject refs, then zero or more
  `w9-fixture:<fixture ID>:<ref ID>` entries, sorted by fixture ID.
- Each `<ref ID>` is a `rev_` or an `art_` for evidence, or a `dec_` for a waiver, as LR-020's rule has it
  (`:575-596`).
- Replay requires one entry for every unconditional fixture of the resolution row, admits only the fixtures that
  row lists, and admits at most one entry per fixture. The resolution repeats the proposal's list, as it does today.
- A conditional fixture that is listed counts as applicable, and one that is absent as not applicable. That is the
  reading P-084 item 3 recorded for LR-020 (i-3).
- The unconditional sets, from the annex: LR-029: S-017. LR-044: F-018, F-023, F-037. LR-054: F-006, F-019, F-023,
  F-037. LR-055: F-006, F-019, F-037. LR-034 and LR-049 list none. S-007 on the review and Decision-proposal rows is
  the stale-hash control those rows already enforce (W9-C22), not an evidence ref.

This changes an encoding P-081 fixed, for WP9.4's rows only. WP9.3's rows keep exactly three refs.

*The alternative* is a recorded departure from P-072 item 4: fixtures stay a reviewer's checklist for these rows,
and nothing in the ledger shows whether S-017 or F-037 was ever named.

### 5.5 The eligibility Decision's encoding (if owner point B is taken)

LR-024 and LR-025 fit none of WP9.3's Decision checks: they bind more than a subject, they have no Decision ID in
any record, and LR-025 writes no record (review M-12). The encoding:

- **The Decision ID** is derived: `derived_id("dec", "w9-adoption-eligibility:" + record_id,
  utc_milliseconds(created_at))`, reserved at LR-023 with the proposal. So an adoption proposal has exactly one
  eligibility Decision. A rejected or lapsed one needs a new adoption proposal.
- **LR-024's `governing_evidence_refs`** are exactly eight, in this order: `W9:LR-024`; the adoption's
  `w9-subject:` and `w9-subject-sha256:`; then `w9-eligible-session:`, `w9-eligible-family:`,
  `w9-eligible-version:`, `w9-eligible-profile:` and `w9-eligible-grade:`, each non-empty.
- **The kind** is `migration_authority`, subject to owner point B's confirmation (§2.2).
- **LR-025 is a record-less resolution.** Its transaction is the one `DecisionResolved` event. `_check_resolution`
  reads a second event (`replay/reducers.py:1087`) and would fail on it, so LR-025 gets its own branch: the Decision
  is open and of this family; the fixed resolution fields hold; it is resolved before it expires and before the
  adoption proposal lapses; and no record follows. It is not a G5 row (annex G5).
- **LR-026** refuses unless that Decision is resolved `accept`, and the request names its `w9-eligible-session:`.
- **LR-027's verdict.** `_check_verdict` fixes `reviewer_profile` to the constant `w9-independent-reviewer`
  (`:884`). For an adoption verdict the fixed value becomes the Decision's `w9-eligible-profile:`, and
  `reviewer_model_metadata` must equal the Decision's family and version. `computed_independence_grade` stays the
  constant `independent` (`:117`), and LR-024 refuses a `w9-eligible-grade:` other than that value.
- **What replay does not check.** The annex's (a) to (c), that the session's family differs from the producer's,
  that its role profile declares the lane's capability, and that its context is independent, are Stephen's check at
  LR-025 (annex: "checked by Stephen, never by the producer or the named session"). Replay sees attested strings.
  §16 lists them.

## 6. Adoption (LR-023 to LR-029)

### 6.1 Subject

- **By family** (`subject_kind: families`). The observation is a `json_family_set` observation. Every named family
  is one of the observation's families. The observation is in a recorded closed-reference acceptance, and neither is
  superseded.
- **Whole file** (`subject_kind: whole_file`, `rehash_at_use: true`). The observation's selector is `whole_file`
  and its source kind is `restricted_untracked_file` or `untracked_file`, or it is a `git_tracked` file with no
  accepted membership table. Its class is the `w0_class` of its one `whole_file` family entry (§4.4). A JSON result
  that has a membership table is adopted by family, never whole (W9 §9 item 1: "For a binary or restricted input with
  no JSON family").

An item observation (`inventory_item`) is not an adoption subject. W9 §9 item 1 names families and whole files only,
and a tracker row or a log entry has no successor use that W9 defines. The proposal refuses it.

W9-T1 holds as in WP9.3: no code derives adoption from source text. The class is the observation's, from its signed
W0 record.

### 6.2 Intended use (owner point F)

The schema gives `intended_use` a free `description` and a nullable `successor_ref` of any kind. Two things compare
uses exactly: LR-039 ("an active adoption for the use 'evidence for the manuscript claims of paper X'") and the
admissibility predicate (W9 §9 item 4: "admissible to W5 for the named use only"). A free string cannot be compared
safely.

Revision 1 proposed three fixed values, two of them with no target. The review is right that those two refuse too
little (M-7): W9 §9 item 2 binds a named use ("input to T1.41 successor Task", "evidence for claim candidate X"),
and one `claim-evidence` adoption with no target would be admissible for every claim.

*Recommended:* replay accepts three forms of `description`, each naming its target:

| `description` | `successor_ref` | Source |
|---|---|---|
| `w9-use:manuscript-claims/<paper key>`, the key being `P01-A` or `P01-B` | null. The root may not exist yet (LR-035 comes later) | W9 §12.1 |
| `w9-use:task-input/<key>` | null, or a `tsk_` ref. Null when the Task is created after the adoption, which W9-T8 requires | W9 §9 item 2; §10 item 3 |
| `w9-use:claim-evidence/<key>` | null | W9 §9 item 2 |

`<key>` matches `[a-z0-9][a-z0-9._-]*`. For a task input it is the successor Task's pre-registration ID or plan task
key. For claim evidence it is the claim candidate's key. Both are attested strings: nothing in the store resolves
them. `family_admissible` compares the whole `description`, so an adoption for one Task or claim admits no other.

This is narrower than the schema, as WP9.3's Q2 was narrower than its note (P-084 item 2). *The alternatives:* the
three target-free values of revision 1, which widen W9 §9 item 2 and would need recording as such; or comparing a
free string byte for byte, which makes a typing difference a silent mismatch at LR-039.

### 6.3 Qualifiers and the W5 consequence (owner point G)

Annex LR-023: "the intended successor use named; no blocking qualifier for that use (W9 §9 item 4)". W9 §9 item 4
says open `open_review_finding` qualifiers "stay attached", and that W5 cannot promote a claim resting on a family
whose qualifier blocks it. The schema gives a qualifier a kind, a source ref and a text, and no identifier, so no
later record can name one qualifier as discharged.

Revision 1 recorded a claim-use adoption with open findings and marked it blocked. That records an adoption the
accepted row refuses, and LR-039 would then have counted it as adopted (review M-6).

*Recommended:*
- **A claim use with an open finding is refused at LR-023.** For `w9-use:manuscript-claims/…` and
  `w9-use:claim-evidence/…`, the observation's `open_review_finding` set must be empty, and
  `qualifiers_to_discharge` is empty.
- **A task-input use keeps its findings attached.** `qualifiers_to_discharge` must equal the observation's
  `open_review_finding` qualifiers, as a set. An adoption can neither drop one nor add one.
- **`w5_consequence` is one of two values:** `admissible_for_named_use` when that set is empty, and
  `task_input_with_open_findings` when it is not. The second can occur only on a task-input use.

So "blocking" is read as: any open review finding blocks a claim or manuscript use, and none blocks a task input.
The rung-4/5 families under A1 to A3 then cannot be adopted for a claim use until a re-observation carries no open
finding, which is what W9 §9 item 4 says of them. They can be adopted as inputs to the successor Task that runs the
calibration (W9 §10).

*The alternative* is revision 1's: record the adoption and mark it blocked. That amends LR-023's precondition, and
it would also need §11.3's "adopted" to test the consequence as well as the status.

### 6.4 The eligible reviewer

Under owner point B, §5.5 gives the rows. Without it, LR-026 refuses on every store until WP9.7 routes LR-025.

### 6.5 The checks, by row

G1 to G5 and the flow checks of §5 apply to every row and are not repeated.

| Row | Replay | Preparer only |
|---|---|---|
| LR-023 | The schema; §6.1's subject rules; §6.2's use; §6.3's qualifier rules and consequence; the observation's acceptance recorded and not superseded; the adoption would not be projected suspended at this position (§7); the derived review ID, and under B the derived eligibility Decision ID, reserved | The source re-reads to the observed identity (the window opens) |
| LR-024, LR-025 (owner point B) | §5.5 | — |
| LR-026 | The review ID is the derived one; the named session is the resolved eligibility Decision's; W9-C20, W9-C22 | — |
| LR-027 | The submitter is the named reviewer; the profile and model metadata equal the Decision's (§5.5); W9-C21 | — |
| LR-028 | `review_id_for` returns the derived review, and it is satisfied on the current hash; the subject is the record's ID and hash; the fixture entries of §5.4 | — |
| LR-029 | G5 with F-8's first limb; `considered_review_ids` is exactly the derived review; the fixture entries repeat the proposal's; the adoption would not be projected suspended at this position (§7) | The source re-reads to the observed identity at commit (W9-T6, O-33) |

## 7. The suspension projection (`P:legacy-adoption-status`)

An adoption's status is derived at replay, never stored in the record. It is `active` or `suspended`, with the cause.
The annex's `suspension_rule` gives three causes:

1. **A later observation of its source,** "whether or not the bytes changed". An adoption is suspended by:
   - any later observation of the same registration, for a whole-file adoption;
   - a later observation of the same registration whose selector names at least one adopted family, for a family
     adoption;
   - **its own observation being in `stale_observations`, for either kind.** `reduce_record` marks every earlier
     observation of a registration stale when a later one records a different source fingerprint, whatever the
     later one selects (`replay/reducers.py:1403-1414`). So when a result file changes and the observer re-observes
     only other families, the old adoption still suspends. Revision 1 missed this case (review M-1). It is the
     carried obligation of P-081 item 12 ("the accepted record projects as stale, and what follows is WP9.4's").

   `observations_by_registration` is in ledger order, so "later" is a position in that list after the adoption's
   observation (review i-4).
2. **A supersession of a record it relies on:** its observation, that observation's closed-reference acceptance, or
   the adoption itself. `state["supersessions"]` already holds the chain (`:1062-1077`).
3. **A recorded use-time mismatch** naming the adoption (LR-061).

The annex's item-adoption clause ("a later observation of the same item selector") has no subject under §6.1. The
projection implements it anyway, so that a later reading of §6.1 does not need a reducer change.

Suspension is permanent for that adoption record. P-072 item 3 says so: "Re-resolution is a new
`AdoptLegacyAuthority`" (`03-decisions-and-open-questions.md:4617`), which is LR-023 to LR-029 again on the later
observation.

The projection is applied at LR-023 as well as LR-029, so an adoption that would be suspended at birth is refused
before its review, not after (review m-12).

Causes 2 and 3 are written by rows WP9.4 does not route. Their reducers exist, and the projection reads their state.
They are tested on forged ledgers through a test route set, and the notes for WP9.6 and WP9.7 inherit a binding test
each: a real LR-060 and a real LR-061 suspend an adoption.

W9-T9's control runs on a real scratch store, because LR-015 is routed.

## 8. Discharge (LR-030 to LR-034)

A discharge relation lets a successor result close a legacy open item. The checks:

| Row | Replay | Preparer only |
|---|---|---|
| LR-030 | The schema; the pre-assigned refs reserved; one open relation per `(item_kind, item_id)` | `item_id` resolves against the accepted open-item list (owner point H); the successor result artefact's current `use_authority` is `accepted_for_scope` (§4.4) |
| LR-031 | WP9.3's request checks, with §5.3 | **G3:** the named reviewer is not the artefact's producer, read from the artefact's manifest in the generic projection |
| LR-032, LR-033 | WP9.3's verdict and Decision-proposal checks | — |
| LR-034 | G5 with F-8's first limb | The artefact is still `accepted_for_scope`; the open-item list at the binding's `git_head` still holds the item; G3 again |

**G3 for a discharge holds at the preparer only.** Revision 1 placed it in replay, "by the actor the proposal
recorded". Replay has no such input (review M-8): the discharge record has no producer field, the proposal state
keeps only the proposer's `actor_id` (`replay/reducers.py:727-736`), and replay's context carries five keys and no
artefact state (`replay/driver.py:199-205`). Passing the generic artefact manifests into legacy replay would change
the shared replay boundary that WP9.2 confined to four sites (06v U-7). So the check stays at the preparer, and §16
records that a forged ledger with the producer as reviewer replays clean. §15's control for it is a preparer test.

LR-034 has no W9 §17 test (`discharge_no_w9_test`), so its controls are W9-C23 and the row's own negatives (§15).

**Owner point H: the open-item list.** "The accepted A-001 list or the audit (W0-D1)" is outside the store. It is read
as WP9.3 reads its outside inputs: a committed file in the W9 evidence area, `.research-system/evidence/w9/`, read at
the binding's `git_head` (WP9.3 note §11.1; P-081, owner point D).

*Recommended:*
- the file is `legacy-open-items.json`, of format `w9-legacy-open-items/1`: one row per item with `item_kind`,
  `item_id`, the source it comes from, and `feeds_papers`, the paper keys whose claims the item feeds;
- its content is Stephen's, under W0-D1, and it is written at the live stage, not by this package. WP9.4 fixes the
  reader and the format, and its tests use fixture lists;
- **the file's blob is bound in Stephen's Decision.** LR-034 and LR-054 each carry a `w9-open-items-blob:<sha1>`
  entry among the Decision proposal's refs (after the fixture entries of §5.4), and the preparer refuses unless it
  is the file's blob at the binding's `git_head`. So "scoped out by Stephen" (W9 §12.1) is an edit Stephen has
  resolved on, not a PR edit alone (review m-7);
- this adds one row to the W9 paths addendum, as a dated amendment.

*The alternative* is to keep the list out of the machine checks and leave "resolves against the accepted list" to
the discharge's reviewer.

## 9. The legacy read interface

06v §2.7: "Each guard reads the store's W9 projection through the legacy package's read interface, not by importing
its internals." No such interface exists yet. Outside `research_system/legacy/`, the package is imported by the CLI
and by replay (`projection/replay.py:1215`, `:1393`), and for two leaf modules: `legacy.identities` by
`command/service.py:640`, `command/t2.py:1197` and `discovery/routes.py:313`, and `legacy.commands` by
`discovery/routes.py:332`.

WP9.4-1 adds `research_system/legacy/projection_read.py`. The name avoids `reader.py`, which is WP9.3's observation
reader (review m-3). It is a leaf over the replayed legacy state, with four pure functions:

- `adoption_status(state, adoption_id)`: `active` or `suspended`, with the cause (§7).
- `resolve_adoption_ref(state, ref)`: parses `w9-adoption:<obj_ id>` and returns the adoption's observation, subject,
  use, status, and for a whole-file subject the source's path, SHA-256 and byte length. A malformed ref, or one that
  names no recorded adoption, raises.
- `family_admissible(state, observation_id, family_name, use)`: true only when an active adoption of that
  observation names that family and its `description` equals `use` exactly (§6.2). Otherwise false, with one of the
  reasons `unadopted`, `suspended` or `other_use`. A whole-file adoption answers for the family name `whole_file`.
- `legacy_content_matches(state, sha256, git_blob)`: every recorded observation whose source has that SHA-256 or
  that Git blob (§4.2).

The functions read. A test asserts that a module outside the legacy package imports from it only
`projection_read`, plus the existing imports listed above, which the test allowlists by module and importer
(review m-2).

## 10. The full path (LR-035, LR-040 to LR-055)

### 10.1 The ordinary paper root (LR-035)

The schema closes the key and the path to P01-A and P01-B. Replay refuses a second root for a key, a `recovery`
value that is not null (that is LR-038, WP9.6), and a root with no passed pilot outcome Decision (LR-022). The last
check refuses on every store until WP9.7 (owner point D).

### 10.2 The root's registration and its member files (owner point K)

Two registrations of different kinds are involved, and revision 1 weighed only the first.

**The root registration.** Its role is `legacy_manuscript_root`, and the schema fixes its path to one of the two root
directories (`.research-system/schemas/contracts/w9/legacy-path-registration.schema.json:190-`). It is the subject
that LR-054 moves from `legacy_owned` to `successor_owned`, so no batch may close it first. The reader refuses a
path that is not a regular file (`research_system/legacy/reader.py:168-169`), so no observation made through a
preparer names it. Replay does not check that: a forged whole-file observation of a root registration replays, and
`derive_ownership` would then close the root at LR-020 (`replay/reducers.py:619-650`; review m-4). WP9.4-2 adds the
replay refusal: an observation whose registration has the role `legacy_manuscript_root` is refused at LR-015. This
is the one change to a WP9.3 row's check.

**The member files.** Annex LR-040 needs "every row bound to an accepted observation", and an observation's source
path must equal its registration's path (`replay/reducers.py:485-491`). So each tracked file under a root needs its
own registration: 55 files across the two roots at `3c10de9a`. Three things follow, and none is settled by an
accepted text (review M-13):

1. **No role fits.** The role enum is closed, and `legacy_manuscript_root` is fixed to the two directories. A draft
   section, a `_project.md` or a figure script is none of the other roles.
2. **Every member file ends `closed_reference`.** LR-020 closes each accepted whole-file observation's
   `legacy_owned` registration (P-072 item 2). After LR-054 the root is `successor_owned` and every file in it is
   `closed_reference`.
3. **The writer rule is then unclear.** WP9.7's guard refuses a successor write to a registered legacy file (06v
   WP9.7, rule (a)). Read literally, a successor could not write any draft under the root it owns.

*Recommended, for Stephen to decide before WP9.4-2's code:*
- **Role.** Add a member-file role by a catalogue revision, for example `legacy_manuscript_member`. A registration
  is an accepted record with a closed enum, so this needs a new catalogue identity and a routed LR-002. The
  alternative that needs no revision is to register members under an existing role, and `legacy_research_result` is
  the nearest. That would put drafts among the files the citation extractor treats as results (§11.1), so it is not
  recommended.
- **End state.** Read `closed_reference` on a member file as closing the legacy bytes at the observed blob, which is
  what the acceptance attests. It is intended.
- **Writer rule.** A path under a root whose registration is `successor_owned` is writable by the successor, and
  the member's `closed_reference` record stands as the reference for the bytes it observed. This is a reading of W9
  §4.2 and §8.2 together, and WP9.7's guard would carry it as an exception to rule (a).

*The alternative* is a root transition that binds no per-file observation: the inventory's rows would carry blobs
only. That contradicts annex LR-040 and the inventory schema, which requires `observation_ref` on every row, so it
too needs a catalogue revision.

Either way K needs an accepted text to change. If Stephen prefers not to revise the catalogue now, WP9.4-2 can
build and test the full path on fixture registrations and leave the role to the revision. The batch rule also
bears on timing: one batch of at most 20 items is admitted before the pilot outcome
(`replay/reducers.py:104`, `:539-542`), so a root's members are accepted in batches after LR-022, which is when
LR-054 can first run anyway.

### 10.3 The source inventory (LR-040 to LR-044)

- **"The root's registration live"** (annex LR-040): recorded, not superseded, of role `legacy_manuscript_root`, and
  currently `legacy_owned`. Replay checks all four (review m-9).
- **Complete membership.** The inventory is "complete over every file under the root at the observation commit".
  The preparer lists the root's tracked files at the binding's `git_head` with `git ls-tree -r`, and refuses unless
  the inventory's rows are exactly that set, by path and blob. Replay cannot see Git, so it checks what it can: row
  ordinals are 1 to n with no gap, paths are unique and under the root's path, and every row's observation is
  recorded, names that path's registration, and carries that blob.
- **"Every row bound to an accepted observation."** Each row's observation is a `whole_file` observation in a
  recorded closed-reference acceptance.
- **The window (LR-044).** At resolution the preparer re-reads every row's blob at `git_head` and re-lists the
  root. A changed blob, or a tracked file the inventory omits, refuses with no event (W9-T6; W9-T17 at LR-044).

### 10.4 The mapping (LR-045 to LR-049)

Replay checks that the inventory is recorded and not superseded, that the target root is recorded and its
`manuscript_root_path` equals the path of the inventory's root registration, and that `mapped_row_ordinals` is a
non-empty subset of the inventory's ordinals with no repeat.

### 10.5 Ownership (LR-050 to LR-055)

- **LR-050** refuses `legacy_owned → closed_reference` (W9-C24, W9-T5). That direction is LR-020's only.
- **LR-054** (`legacy_owned → successor_owned`), in replay:
  - the subject registration's role is `legacy_manuscript_root`;
  - `mapping_ref` and `paper_root_ref` are both set, the mapping is recorded, and its target is that root;
  - **the subject is the root the mapping targets:** `subject_registration_ref.id` equals the
    `root_registration_ref.id` of the mapping's inventory, and that registration's `normalized_path` equals the
    root's `manuscript_root_path`. Without this a P01-A mapping could transition the P01-B registration (review
    M-10);
  - the root's current citation status is complete and consistent (§11.3), and every adoption it cites is active at
    this position;
  - **the citation set was not made by the transition's producer** (§11.3);
  - the pilot outcome is passed (LR-022);
  - the fixture entries of §5.4 and the open-item blob of §8 are present;
  - every open item whose `feeds_papers` names this paper has a recorded discharge relation.
- **LR-055** (`successor_owned → closed_reference`). The subject is currently `successor_owned`. The annex adds no
  further precondition, and neither does this note.
- **The window.** At LR-054 and LR-055 the preparer re-reads the inventory's rows, as at LR-044.

**The rest of §4.5's paper-root column is not machine-checkable in v1.** §16 lists each condition with the question
its reviewer answers.

## 11. Citation status and the extractor (LR-039; D-3)

### 11.1 What is compared (owner point I)

D-3 is decided: both an extractor and a reviewer's derivation, and "a difference blocks" (06v §6). The record holds
`extractor_output_sha256`, `reviewer_derivation_sha256` and `cited_family_set_sha256`. Three things need a fixed form
so the hashes mean something.

Revision 1's rule was a path literal, with `\` read as `/`, and no basenames. The review ran it against the P01-A
drafts and it fails (M-5; claim 7). The author re-checked two of its cases at `3c10de9a`:
`results-ari-stability.md:75` cites `` `escape_wilson_ci_2026-05-16.json` `` by basename only, and that name
resolves to one tracked file; `05_analysis.json` resolves to three.

*Recommended:*

**A candidate citation** is found in a file's bytes by this procedure:
1. decode the bytes as UTF-8. In a `.json` file, also scan every decoded string value, so that a JSON-escaped
   Windows path is read as its path;
2. read `\` as `/` and collapse repeated `/`;
3. take every token that ends in a registered result's basename, or that contains `results/`.

**Each candidate resolves to one of three things:**
- **a cited file:** the token's path suffix equals a registered `legacy_research_result`'s normalized path, or the
  token is a bare basename that exactly one registered result has;
- **a blocker entry, `ambiguous`:** a bare basename that more than one registered result has;
- **a blocker entry, `unregistered`:** a token naming a path under `results/` that no registration has.

Nothing is dropped silently. A set with a blocker entry cannot be recorded at LR-039.

**The cited-family set** is every family of every cited file's accepted membership table, as sorted
`(observation ID, family name)` pairs, in canonical JSON. A cited file with no accepted table, or no accepted
observation, is also a blocker entry.

**Both hashes are of that same object.** The extractor's is computed by the preparer. The reviewer's is supplied,
from a derivation made without the extractor's output.

**Scope: the whole root, not the drafts only.** W9 §12.1 says "every result family its drafts cite". 06v WP9.4 says
"every file in the root's inventory". This note follows 06v. For P01-A that adds 19 result files cited only outside
`drafts/` to the 17 cited inside, and for P01-B 4 to 2 (the review's count). The wider scope asks for more adoption
decisions or more "unadopted" marks, and never fewer. Stephen may prefer the drafts-only reading of W9 §12.1.

**A departure from 06v.** 06v WP9.4 defines the extractor's output as "projected to families through the accepted
membership tables and the audit's artifact map". This note projects through the membership tables only, and leaves
the artifact map to the reviewer. The reasons: the author has not read the map's format, and narrowing a cited file
to the families a claim uses can only shrink the set. The decision entry for this note records the departure.

**When the two derivations differ.** LR-054 refuses, and that is all the accepted row provides: no row records a
reading that overrides it. Revision 1's "a recorded reading by Stephen" named a route that does not exist and is
withdrawn. The executable routes are:
- **a new citation status** (LR-039 with `supersedes_status_ref`), when the reviewer's derivation was wrong;
- **a draft change,** when the drafts cite something they should not. That is a write to a registered legacy file,
  so it needs an allowed writer under W9 §4.2 item 1, and it re-triggers observation, the inventory and the mapping
  (W9 §4.2 item 3);
- **an extractor change,** when the rule is wrong. That is a code change with its own review, and a binding
  advance.

If the reviewer finds a result cited indirectly, by a table or a figure, that the extractor cannot see, the
transition stays blocked until the draft cites the file by name or the claim is removed. That is D-3 working as
decided, and it is a real cost Stephen should know before accepting I.

*The alternative* is to narrow the comparison to the claim-level families the artifact map names. That needs the
map's format fixed in a note first.

### 11.2 The extractor

`research_system/legacy/citations.py` is a pure function over bytes. Its input is the source inventory's rows: for
each, the blob named by the row's accepted observation, read from Git by blob ID at the binding's checkout. It never
reads the live tree (06v WP9.4, "Input"). Every file in the inventory is scanned, whatever its type. The preparer for
LR-039 runs it, stamps `extractor_output_sha256`, and refuses a supplied value, as preparers do for the content hash.

So LR-039 needs the root's accepted inventory first. The order is LR-044, LR-049, LR-039, then LR-050 to LR-054.
The annex's "hashed and filed before the transition" is met by that order.

### 11.3 The record's checks

| Check | Where |
|---|---|
| The root is recorded; the submitter is not the root's creator | Replay, at LR-039 |
| `cited_family_set_sha256` is the hash of `families`; no pair repeats | Replay, at LR-039 |
| A family marked `adopted` names an active adoption of that observation and family whose use is `w9-use:manuscript-claims/<the root's key>`. One marked `unadopted` names none | Replay, at LR-039 |
| `supersedes_status_ref` names the root's current status, or is null when there is none | Replay, at LR-039 |
| `families` is exactly the extractor's cited-family set, with no blocker entry. When the reviewer's set differs from the extractor's, `families` is still the extractor's, and the two hashes record the difference | Preparer, at LR-039. Replay cannot run the extractor (review m-5) |
| The root's current status exists; the two derivation hashes are equal; every cited adoption is still active | Replay, at LR-054 |
| **Not the transition's producer** (W9 §12.1): the current status's `derivation.reviewer_actor_id` and its submitter are none of the ownership proposal's creator, the mapping's `analyst_actor_id`, and the `observer_actor_id` of the inventory that mapping names | Replay, at LR-054. At LR-039 the transition does not exist yet (review M-9) |

W9-T17's first two clauses are the fifth and sixth rows: a status that omits a family in the set is refused at
LR-039, and drafts that cite a family missing from the set change the extractor's hash, which blocks LR-054.

## 12. The reference graph (W9-T21)

Replay already records edges for paper roots, mappings and ownership records (`replay/reducers.py:1152-1153`,
`:1390-1402`). WP9.4-2 adds the inventory and the citation status as sources, and refuses any edge that closes a
cycle among root, inventory, mapping, transition and citation status. The schema already keeps a root from naming its
transition. The recovery half of W9-T21 is WP9.6's.

## 13. The CLI (owner point M)

No new mutating verb. `ars legacy submit` already takes any W9 command envelope and refuses before bind
(`research_system/cli.py:2898`; WP9.3 note §13). WP9.4 adds read-only verbs only:

- `ars legacy adoption-status <adoption id>`: §9's status and cause;
- `ars legacy cited-families --root <root id>`: runs the extractor at the binding's `git_head` and prints the set,
  its blocker entries and its hash, for the reviewer to compare after making their own derivation. It writes
  nothing.

**Owner point M: the boundary.** P-085's boundary is "WP9.4's code under `research_system/legacy/`". These verbs
edit `research_system/cli.py`. WP9.3 had the same need, and Stephen extended P-080's boundary by name (P-081 item
10, `03-decisions-and-open-questions.md:5167`). *Recommended:* the same extension for P-085, to
`research_system/cli.py` and, for WP9.4-2's two bindings, to `research_system/schema_registry.py` and
`research_system/authority.py`. *The alternative* is no CLI verbs: the reviewer would then run the extractor from a
Python prompt, and the two bindings still need the registry and authority files.

## 14. Bindings and D-4

- **WP9.4-1** adds no `SchemaBinding` row. The census stays 273 rows, `0cca0414…4712`, and the 06h manifest and the
  smoke test keep their blobs. The PR states that and its review checks it. If the code finds it needs a row, that is
  a stop (§18).
- **WP9.4-2** adds command rows for `CreateLegacyPaperRoot` and `RecordPaperCitationStatus`, with their authority
  entries (`research_system/authority.py:208-252` lists the bound W9 commands and their subject kinds). The expected
  census is 275 rows: both commands emit `E:` events only (§2.3). The code PR gives the exact row set, digest,
  manifest bytes and append-site classification, and Stephen re-accepts them at exact bytes in the merge-queue entry
  (06v D-4).
- Command-adding packages merge one at a time (06v §5). WP9.4-2 must not be in the queue with another one.

## 15. Tests

| Test | PR | Kind | Control |
|---|---|---|---|
| W9-T1 at LR-029 | 1 | unit | A `Done` status word in the source yields no adoption |
| W9-T6 at LR-029 | 1 | integration, scratch store | The source's bytes change after the proposal; resolution writes no event |
| W9-T8, legacy side | 1 | integration | `family_admissible` is false for an accepted, unadopted family; `resolve_adoption_ref` raises for an unknown adoption. The successor half is owner point J |
| W9-T9 | 1 | integration | Re-observe an adopted source: the same family with a new blob; the same family with the same blob; **a disjoint family set with a new blob** (M-1). All three suspend. Supersession and mismatch on forged ledgers |
| W9-T17, last clause | 1 | unit | §9's predicate, for unadopted, suspended and other-use; `legacy_content_matches` finds a byte copy. The binding test is WP9.7's (owner point E) |
| G5 for an adoption | 1 | unit and integration | An adoption with no review, with an unsatisfied derived review, or with another review ID is refused at LR-028 and at LR-029. `review_id_for` raises for an unlisted kind (M-2) |
| The analyst rule | 1 | unit | The analyst may request on their own adoption, discharge, mapping and ownership proposals; the inventory's observer may not request on it (M-3) |
| Fixture entries | both | unit | A resolution missing an unconditional fixture, naming an unlisted one, or differing from its proposal is refused (owner point L) |
| LR-023's refusals | 1 | unit | A claim use with an open finding; a task-input use whose qualifier set differs from the observation's; a target-free use; an adoption suspended at birth (M-6, M-7, m-12) |
| LR-024, LR-025, LR-027 | 1 | integration | Under owner point B: a request before the eligibility Decision resolves; a request naming another session; a verdict whose profile or model metadata differs; W9-C20 at LR-025 |
| LR-034's negatives | 1 | integration, at the preparer | An unknown `item_id`; a registered artefact that is not `accepted_for_scope`; the producer as reviewer; an open-item blob that is not the file's |
| W9-T5 | 2 | unit | `successor_owned → legacy_owned` fails the schema; `legacy_owned → closed_reference` is refused at LR-050 |
| W9-T6 at LR-044, LR-054, LR-055 | 2 | integration | A row's blob changes inside the window |
| W9-T17 at LR-044 | 2 | integration | An inventory that omits a tracked file under the root is refused (m-9) |
| W9-T17 at LR-039, LR-054 | 2 | integration | A status omitting a family; a draft citing a result outside the set; unequal derivation hashes; the citation reviewer as the ownership proposal's creator, the mapping's analyst or the inventory's observer (M-9) |
| The extractor | 2 | unit, on fixture bytes | A path literal; a JSON-escaped Windows path; a unique basename; an ambiguous basename and an unregistered `results/` path, each a blocker entry (M-5) |
| W9-T21, graph half | 2 | unit | A cycle among root, inventory, mapping and transition; **a P01-A mapping used to transition the P01-B registration** (M-10) |
| The root registration | 2 | unit | A forged whole-file observation of a `legacy_manuscript_root` registration is refused at LR-015 (m-4) |
| W9-C11, W9-C20 to W9-C25 | both | integration | Per row, as the annex binds them |
| The route partition | both | unit | The routed and deferred counts after each PR; a deferred row is still refused before append |
| The import seam | 1 | unit | §9's allowlist (m-2) |
| D-4 identities | 1 | contract | The census, manifest and tree IDs are unchanged |

No test reads a file under `papers/`. The extractor's tests use fixture bytes that reproduce the citation forms the
review found in the drafts.

Both PRs report their added test runtime. The test-runtime escalation is still open with Stephen (P-084, "Not decided
here"), and WP9.3-2 added about 4.4 minutes.

## 16. Research assurance

**Lanes.** `output_provenance` (every row) and `paper_claim` (LR-039, LR-054 and §9's predicate). No topology,
null-model, statistical or representation logic is touched: the package computes no research number.

**Governing texts.** W9 §§4.2, 4.5, 8.2, 8.3, 9, 12.1 and 17; the owner annex rows LR-023 to LR-055; P-072, P-073,
P-081 and P-085; 06v §2.7, §2.8 and D-3.

**Machine-checkable, with an enforcement artifact:** every replay and preparer check in §5 to §8, §10 and §11.3,
each with a negative control in §15; the D-4 identities.

**Human-review only.** Each line gives what the reviewer or Stephen is asked, and why no check exists.

| Condition | Source | The question | Why not checked |
|---|---|---|---|
| The eligible session's family differs from the producer's; its role profile declares the lane's capability; its context is independent | Annex LR-024 (a) to (c); W9 §11.2 | Does the operator's record show each? | Replay sees attested strings (§5.5) |
| A discharge's reviewer is not the result's producer, on a replayed ledger | G3 | — | Replay has no artefact state; the preparer checks it (§8) |
| W0-D2 Stage 2 scope covers the root's rows | W9 §4.5; §12.1 | Does the Stage 2 decision name them? | The ownership record has no field |
| The audit verdicts and the §6.2 HOLD are carried as qualifiers | W9 §12.1 | Does the root's `qualifiers` list hold each? | No accepted list of them exists to compare with |
| For any rung-4/5 claim the paper keeps, the A1 fork is decided and the calibration has run | W9 §12.1 | Which claims are kept, and where is each calibration result? | A claim is not a W9 record |
| The W9-D7 manuscript route | W9 §4.5; §12.2 | Has Gate 9's review capability been met for this paper? | Outside W9 |
| Stephen's batch approval | D-G6-4 limb 2 | — | It is the resolving Decision itself |
| The reviewer's citation derivation is independent of the extractor | D-3 | Was it made before `cited-families` was run? | Only its hash is checked |
| The content of the open-item list | W0-D1 | — | Stephen's. Its blob is bound (§8) |
| A legacy result re-serialized into an artefact | §4.2 | Does the artefact's review trace its inputs? | Content identity catches a byte copy only |
| Use keys name a real Task or claim | §6.2 | Does the key match the pre-registration or the claim candidate? | Attested strings |

The fixture evidence is machine-checked for presence under owner point L, and human-reviewed for content.

Passing these tests does not show that any real adoption is sound. That is the adoption's own review.

## 17. Claims the re-review should probe

Each is a claim revision 2 makes. The first five are corrections to revision 1's claims.

1. **The claim path.** A legacy byte copy can be registered under the control root, promoted to
   `accepted_for_scope` and resolved by `resolve_for_claim`, with no check on its content (§4.2). Neither the review
   nor the author ran this end to end. A scratch-store run would settle it.
2. **The use-time content rule is sufficient for byte copies.** With `legacy_content_matches` called at
   `resolve_for_claim` and `resolve_for_manuscript`, no byte copy of an unadopted family resolves (§4.2, owner
   point E). Is use time the right site, or does `SetArtefactUseAuthority` need the rule too?
3. **The stale rule.** With §7's third bullet, the review's probe case (O1 selects `{a}` at blob X, O2 selects `{b}`
   at blob Y) suspends an adoption of O1's family `a`, and no case leaves an adoption active on bytes that no longer
   exist.
4. **`review_id_for` leaves no fail-open site.** Every read of `_REQUEST_REVIEW_FIELD` and `_FAMILY_REVIEW_FIELD`
   is among the seven sites §5.2 lists.
5. **The extractor rule** of §11.1 finds every result the P01-A and P01-B files cite by path, escaped path or
   unique basename, and reports every ambiguous or unregistered one. The author read two cases from Git and no
   more. The re-review should run the rule on the real roots, read through Git.
6. **The six widened gate sites** of §5.1 are the right six, and the four left alone need no WP9.4 row.
7. **Fixture entries after the three subject refs** break no WP9.3 check for WP9.3's rows (§5.4), and the
   unconditional sets listed there equal the annex's.
8. **The eligibility encoding** of §5.5 meets every precondition of annex LR-024 to LR-027 that replay can meet.
9. **The parameterized uses** of §6.2 and the refusal of §6.3 refuse too much only, never too little, against W9 §9
   items 2 and 4 and annex LR-023.
10. **No member-file role exists** in the accepted registration schema (§10.2), so owner point K cannot be closed
    without a catalogue revision or a reading Stephen records.
11. **LR-054's binding** (§10.5) leaves no way to transition one root's registration with another root's mapping.
12. **The U-10 reading:** `accepted_for_scope` is the only accepted artefact state, and it always needs a
    `claim_promotion` Decision (§4.4).

## 18. Stop rules

06v §8 applies. In addition, the code stops and returns Partial when:
- WP9.4-1 needs a runtime-binding row or a schema change;
- a WP9.4 row needs an edit outside the boundary as Stephen sets it under owner point M;
- a test needs a real paper file, a vault file or restricted bytes;
- a positive path for LR-035 or LR-054 can run without a passed LR-022;
- WP9.4-2's code reaches a member-file registration before owner point K is decided.

## 19. Owner points

| # | Point | Recommended | Alternative |
|---|---|---|---|
| A | The split | Two PRs: WP9.4-1 (adoption and discharge, no D-4), then WP9.4-2 (the full path, with D-4) (§2.4) | One PR |
| B | LR-024 and LR-025 | Move them from WP9.7 to WP9.4-1, with §5.5's encoding and the kind `migration_authority` (§2.2) | Leave them with WP9.7; adoption stops at LR-023 until then |
| C | The adoption's review ID | Derive it, behind `review_id_for`; a reading of P-072 item 1, LR-023 and G5 (§5.2) | Add `reviewer_ref` by a catalogue revision |
| D | LR-021 and LR-022 | Leave them with WP9.7. LR-035 and LR-054 refuse on every store until then (§2.2) | Move them, with the metric helper |
| E | U-6, the W5 clause of W9-T17 | WP9.4 builds `family_admissible` and `legacy_content_matches`; WP9.7 binds them on the artefact path, with a content rule at use, and inherits the binding test (§4.2) | WP9.7 refuses every artefact whose bytes match a legacy observation |
| F | The intended use | Three forms, each naming its target (§6.2) | Target-free values, recorded as widening W9 §9 item 2; or a free string |
| G | Qualifiers and the W5 consequence | Refuse a claim use with an open finding at LR-023; task inputs keep their findings (§6.3) | Record and mark blocked, as an amendment to LR-023 |
| H | The open-item list | A committed `w9-legacy-open-items/1` file with `feeds_papers`, its blob bound in Stephen's Decision (§8) | Leave the list to the discharge's reviewer |
| I | The citation comparison | Decoded paths and unique basenames; blocker entries; the whole root; no artifact map in the extractor (§11.1) | Narrow to the artifact map's families, after its format is fixed; or the drafts only |
| J | The W9-T8 CreateTask guard | Move it to WP9.7 by decision, with its binding test (§4.1) | Widen P-085's boundary to `service.py` |
| K | A paper root's member files | A member role by catalogue revision; `closed_reference` is intended; a path under a `successor_owned` root is writable (§10.2) | An inventory with no per-file observation, also by revision |
| L | Fixture refs | `w9-fixture:` entries in the resolving Decision (§5.4) | A recorded departure from P-072 item 4 |
| M | The boundary | Extend P-085's to `cli.py`, `schema_registry.py` and `authority.py`, as P-081 item 10 did (§13) | No CLI verbs |

A, D and M ask Stephen to confirm a recommendation the review supports. B, C, E, F, G, H, I and L are amended from
revision 1 or new, and each changes what an accepted text is read to say. J and K need a decision that this note
cannot make: J moves work between packages, and K needs a catalogue revision or a recorded reading.

## 20. Change log: revision 1 to revision 2

The author re-read the code behind every finding at `3c10de9a` and re-ran the review's 20 probes (20 passed). No
finding is disputed in substance. Three are qualified, and each qualification is stated in its row.

| Finding | Disposition | Where |
|---|---|---|
| B-1 | **Fixed.** Claim 2 was false. §4.2 and owner point E are rewritten | §4.2, §9, §15, §16, §17 claims 1 and 2 |
| M-1 | **Fixed.** A stale observation suspends its adoption | §3 row 3, §7, §15 |
| M-2 | **Fixed.** One resolver, no default, with the negative control | §5.2, §6.5, §15 |
| M-3 | **Fixed.** The exempt set and the inventory's creator are stated | §5.3, §15 |
| M-4 | **Raised as owner point L,** with the encoding recommended. *Qualified:* the review and the brief say LR-020 carries fixture refs in its Decision. It carries them in the record (`replay/reducers.py:575-596`), which is P-072 item 4's other route | §5.4 |
| M-5 | **Fixed.** Escapes, basenames, blocker entries, scope, the executable routes, and the departure from 06v | §11.1, §11.2, §15 |
| M-6 | **Fixed in the note, and kept as owner point G** | §6.3, §6.5 |
| M-7 | **Fixed in the note, and kept as owner point F** | §6.2, §9 |
| M-8 | **Fixed** by placing G3 at the preparer and recording the limit | §8, §15, §16 |
| M-9 | **Fixed.** The producer check moves to LR-054 | §10.5, §11.3, §15 |
| M-10 | **Fixed.** LR-054 binds the subject to the mapping's root | §10.5, §15 |
| M-11 | **Raised as owner point J.** *Qualified:* 06v §4's test table does assign the guard to WP9.7 (`06v-w9-implementation-plan.md:231`), which is what revision 1 followed. The finding stands because WP9.7's own list omits it | §4.1 |
| M-12 | **Fixed.** The encoding, the record-less branch, the verdict's profile and the human-only limbs | §2.2, §5.5, §6.5, §16 |
| M-13 | **Raised as owner point K.** *Qualified:* the review counts "at least three batches" for 55 files. That holds, but batches after the first already need LR-022 (`replay/reducers.py:539-542`), as LR-054 does, so it adds no new dependency | §10.2 |
| m-1 | **Fixed.** Ten gate sites, six widened; the W2 rows at `:279-302`; the full import list | §2.3, §5.1, §9 |
| m-2 | **Fixed.** The seam test allowlists the existing imports | §9, §15 |
| m-3 | **Fixed.** The module is `projection_read.py` | §9 |
| m-4 | **Fixed.** A replay refusal at LR-015 for a root registration | §10.2, §15 |
| m-5 | **Fixed.** Exact-set equality is the preparer's | §11.3 |
| m-6 | **Fixed.** U-10 and U-11 are settled with `path:line` | §4.4, §6.1, §8 |
| m-7 | **Fixed.** The open-item file's blob is bound in Stephen's Decision | §8, §10.5 |
| m-8 | **Fixed.** The two W9 §12.1 conditions and (a) to (c) are listed | §16 |
| m-9 | **Fixed.** "Registration live" is defined, and W9-T17 has a control at LR-044 | §10.3, §15 |
| m-10 | **Raised as owner point M,** citing P-081 item 10 | §13 |
| m-11 | **Fixed.** Owner point C cites P-072 item 1 and is put as a reading | §5.2 |
| m-12 | **Fixed.** The projection is applied at LR-023 | §6.5, §7, §15 |
| i-1 | Noted. Claim 1 holds | §4.1 |
| i-2 | Noted. Claim 3 holds; the runtime citation is added | §2.3, §14 |
| i-3 | Noted | — |
| i-4 | Noted. The ordering holds | §7 |

Revision 1's §17 claims, as the review disposed of them: 1 and 3 hold; 2 and 7 failed and are replaced by claims 1,
2 and 5 above; 4, 5 and 6 held in part and are replaced by claims 4, 10 and 3.

The re-review comes next, in a fresh session that wrote none of WP9.2, WP9.3, this note or the first review. Stephen
then decides the owner points, and the code follows.
