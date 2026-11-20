# WP9.4 design note: adoption, discharge, citation status and the full path

**Date:** 2026-11-16<br>
**Status:** Revision 6. It folds in the review of revision 5 (`32755276`):
`reviews/wp9-4-note-r5-review-2026-11-19.md`, on branch `claude/review-w9-wp9-4-note-r5-bdb004` at `3e7846b2`,
verdict confirm with residuals (0 Blocking, 1 Major, 3 Minor, 5 Info). §24 says where each finding went. No finding
reopens an owner point. Revision 5 folded in the review of revision 4 (`7bd7d6a6`):
`reviews/wp9-4-design-note-r4-review-7bd7d6a6-2026-11-19.md`, on branch `review/w9-wp9-4-note-r4` at `0a84ce83`,
verdict confirm with residuals (0 Blocking, 2 Major, 4 Minor, 5 Info), and CodeRabbit's review of revision 4. §23
says where each finding went. Revision 4 folded in the confirming re-review of revision 3 (`ede231e5`):
`reviews/wp9-4-design-note-confirmation-ede231e5-2026-11-19.md`, on branch `review/w9-wp9-4-note-confirmation` at
`3499dd21`, verdict confirm with residuals (0 Blocking, 2 Major, 4 Minor, 5 Info), and CodeRabbit's review of
revision 3. §22 says where each finding went.
Revision 2 reconciled the independent review of revision 1
(`3c10de9a`): `reviews/wp9-4-design-note-review-3c10de9a-2026-11-16.md`, on branch `review/w9-wp9-4-note` at
`a9935c0b`, verdict accept with required changes (1 Blocking, 13 Major, 12 Minor, 4 Info). Revision 3 reconciles the
re-review of revision 2 (`4629d1fd`): `reviews/wp9-4-design-note-re-review-4629d1fd-2026-11-16.md`, on branch
`review/w9-wp9-4-note-re-review` at `a704d9b3`, verdict return for revision 3 (0 Blocking, 9 Major, 5 Minor, 4 Info),
and CodeRabbit's five threads on revision 2 (PR #437). §20 and §21 say where those findings went. Nothing in this
note is implemented. Stephen decided owner points A to O on 2026-11-19, each at its recommended option (P-086).<br>
**Package:** 06v WP9.4 ("Adoption, discharge and citation status"), proposed as two PRs, WP9.4-1 and WP9.4-2 (owner
point A).<br>
**Authority:** P-085 (WP9.4, note first). WP9.3 is complete: PRs #420, #428, #429, #432 and #434 (P-082, P-083,
P-084).<br>
**Base:** `main` at `4312dc63` (tree `f0662c10`), which records P-084 (PR #436). No code changed between that commit
and `3c10de9a`, so every `path:line` below reads the same at both.<br>
**Not authorized (P-085):** WP9.5 to WP9.7; live operations L-0 to L-5; creating a real store, or running genesis or
issuing a grant on one; any legacy write; any paper-root transition (P-073 item 4). Every store in this note is a
scratch store that a test creates under `tmp_path`.<br>
**Probe:** the author ran no prototype. The review ran 20 asserting pytest cases and the re-review 28, including a
scratch-store run of the artefact path and a run of the extractor rule over both paper roots through Git. The author
re-ran both files (20 passed at `3c10de9a`; 28 passed at `4629d1fd`) and re-read the code behind each finding before
acting on it. The confirming re-review ran 28 more, and the review of revision 4 26 more, each including the §11.1
rule over both roots; the author re-read the code behind every Major finding. §17 lists the claims revision 5
makes.

## 1. What this note settles

06v WP9.4 predates the stage B command set. It lists three record kinds, but the route table gives the package 28
rows and seven record kinds, and three of 06v's interface questions (U-5, U-6, U-9) were open. This note settles:

1. the rows WP9.4 routes, the commands it binds, and the split (§2; owner points A, B and D);
2. every obligation carried into WP9.4, each with a disposition (§3);
3. U-5, U-6, U-9, U-10 and U-11, each with `path:line` (§4; owner points E and J);
4. what the WP9.3 authority flow gives these rows, and the five places it does not fit (§5; owner points C, L and
   N);
5. adoption (§6; owner points F and G), the suspension projection (§7) and discharge (§8; owner point H);
6. the legacy read interface that successor guards will call (§9);
7. the full path: paper root, source inventory, mapping and ownership (§10; owner point K), and the citation status
   with its extractor (§11; owner point I);
8. the reference graph (§12), the CLI (§13; owner point M), bindings and D-4 (§14);
9. the tests (§15), research assurance (§16), the claims for the re-review (§17), the stop rules (§18), the owner
   points (§19) and the four change logs (§20 to §23).

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

The rows do not fit WP9.3's Decision checks as they stand (review M-12; re-review R-M4). §5.5 gives the encoding the
move needs, with a proposal branch and a resolution branch of their own. One part of it is Stephen's to confirm: the
eligibility Decision's kind. P-073 item 3 names a kind for the pilot outcome
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
| 3 | P-085 item 3; P-081's "Added 2026-11-08" block, the O-33 addition (`03-decisions-and-open-questions.md:5241-5250`; P-085 item 3 cites it as "item 12", which is the G4 reading); WP9.3 note §7.2 | What follows from an observation that WP9.3 projects as stale is WP9.4's | §7. An adoption whose observation is stale is suspended, whatever the later observation selects |
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
| 16 | P-086, "Carried to later packages" | The writer guard's reading that a path under a `successor_owned` root is writable | **WP9.7's.** Under K's option 1 a member has no registration of its own, so after LR-054 only a reading of the root's ownership mode lets a successor write a draft. WP9.4 records the carry and builds no guard (review of revision 5, R5-m3) |

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

*Recommended:* move the guard to WP9.7 by a recorded decision, with its binding test: a Task whose `source_import_refs`
name `w9-adoption:<id>` for an unknown or suspended adoption, for an adoption that is not a task-input use, or for a
task-input adoption whose key is not the Task's own (§6.2 names the carrier), or that name a legacy observation
directly, is refused. The guard runs on AmendTask as well as CreateTask, because an amendment carries the whole Task
definition, `aliases` and `source_import_refs` included
(`.research-system/schemas/core/commands/amend_task.schema.json`). Its binding test has an amendment that adds a
`w9-adoption:` ref and one that changes the `w9-use-key` alias (confirmation C-m4). WP9.7 already edits the command
service for its other guards and takes them to one review. *The alternative* is to widen P-085's boundary to
`service.py` for this one guard. That puts a generic-service edit in WP9.4-1 and gives it a successor-side review
surface it otherwise lacks.

Until J is decided, §15's "W9-T8, legacy side" is half of what 06v's WP9.4 text asks.

### 4.2 U-6: the evidence path is the artefact path, and it is open today

Revision 1 said no code path lets a claim take a legacy family. That was wrong (review B-1). Revision 2 described the
path but said every promotion needs a `claim_promotion` Decision. That was wrong too (re-review R-M1). The author
checked both reviews' evidence, and the re-review ran the path end to end on a scratch store.

**The path, as it is.**
- `RegisterArtefact`'s preparer checks the artefact's identity, its initial `candidate` authority, its
  regenerability claim and an empty stream, and nothing about its path or content
  (`research_system/command/service.py:4409-4440`).
- `SetArtefactUseAuthority` to `accepted_for_scope` needs a governing review (`:4618-4631`). It needs a
  `claim_promotion` Decision **only when the use authority binds the claim predicate**:
  `_claim_promotion_binding` returns an empty list for any other predicate (`:4901-4902`). One use authority binds
  one consumer predicate.
- The consumers are `resolve_for_claim` and `resolve_for_manuscript`
  (`research_system/evidence/consumers.py:63-78`; kinds at `research_system/artefacts/authority.py:32-37`). Their
  production callers are in `research_system/methods/brief.py:31-33` and `:57`, under the consumer IDs
  `rm03_brief_manuscript`, `rm03_claim_assessment` and `rm04_manuscript_pilot`.
- 06v §2.7 predicted the hook in `research_system/assurance/` ("likely `resolver.py`"). That package has none: it
  names the `paper_claim` lane once (`assurance/models.py:13`) and takes no claim's evidence as input (re-review
  R-m4).

**What the re-review ran.** A byte copy of fixture "legacy" bytes, placed under the control root, was registered,
given a governing review, and set `accepted_for_scope` under the manuscript predicate with no Decision.
`resolve_for_manuscript` resolved it. A second copy took the claim route, with Stephen's `claim_promotion` Decision,
and `resolve_for_claim` resolved it. No step read the path or the content for legacy status.

**The guard that would stop it is not built, and is keyed by path.** It is WP9.7's (06v WP9.7, O-22), and P-081
records it as a dependency (`03-decisions-and-open-questions.md:5274`). Its rule (a) refuses when "the resolved path
is a manifest-registered legacy file". The use resolver reads bytes only under the control root
(`research_system/artefacts/runtime.py:31-50`), so a copy there passes rule (a), rule (b) and, for a `.json`, rule
(d).

So W9-T17's last clause ("a family marked unadopted blocks its claims in W5") has a call site, and that call site
admits an unadopted family today. Until WP9.7 lands, a governing scientific review is all that stands between a
legacy copy and a manuscript consumer, and for a claim consumer that review plus Stephen's Decision.

**Owner point E.**

*Recommended:*
1. **WP9.4 builds two read functions** (§9): `family_admissible`, and `legacy_content_matches`, which returns every
   recorded observation whose source SHA-256 or Git blob equals a given artefact's.
2. **WP9.4 binds the content rule at its own reader.** LR-030 and LR-034 read an artefact's `use_authority` directly,
   not through a resolver. Their preparers refuse a successor result that `legacy_content_matches` finds, whatever
   its adoption status: a discharge needs a new result (§8; re-review R-M2).
3. **WP9.7 binds both functions on the artefact path**, in addition to 06v's path rule (a):
   - at use: `resolve_for_claim` and `resolve_for_manuscript` refuse an artefact whose bytes match a recorded
     legacy observation unless every family of every matching observation is admissible for that consumer's use.
     The check is needed at use because an adoption can suspend after the artefact is promoted;
   - **the other three consumer kinds.** The facade has five (`research_system/evidence/consumers.py`: result,
     review, manuscript, claim, sensitive sidecar). Two of the other three have production callers:
     `resolve_for_result` (`research_system/evals/release_publication.py:174-183`;
     `research_system/methods/brief.py:27-28` for the purposes `result_analysis` and `result_reproduction`) and
     `resolve_for_review` (`research_system/methods/brief.py:29-30`, `:55`;
     `research_system/session_exchange/exchange.py:439`).
     `resolve_sensitive_sidecar` (`evidence/consumers.py:80-87`) has none. W9-T17's clause is about claims, so the
     at-use rule above covers claim and manuscript. For result and review evidence the note recommends the same
     at-use rule as well (owner point E). The promotion-site rule below closes those two kinds **at promotion only**:
     a copy promoted while its adoption was active stays resolvable by them after the adoption suspends, unless the
     at-use rule also covers them (revision 4 review R4-m2; CodeRabbit, on revision 4);
   - **at promotion, which Stephen took (P-086 item 5, "at use and promotion"):** `SetArtefactUseAuthority` to `accepted_for_scope` applies the same
     rule. That closes every direct reader of `use_authority` at promotion (others exist today at
     `discovery/spec.py:533`, `discovery/spec_result.py:248` and `cli.py:2258`). The note recommends it.
4. **WP9.7's rule also compares current bytes.** `legacy_content_matches` sees recorded observations only. A legacy
   file that was edited and not yet re-observed, or never observed, matches nothing (re-review R-M3). So WP9.7's
   guard also compares the artefact's Git blob with the blob, at the binding's `git_head`, of every registered
   `git_tracked` legacy path, and refuses a match that no active adoption admits.
5. **WP9.7's note inherits a binding test** with one artefact per consumer predicate, run through the production
   consumer IDs above: an unadopted family's bytes, copied under the control root and promoted, are refused. The
   manuscript case has no Decision in it. The decision entry for this note records the carry.
6. **WP9.4 proves the predicate and its own discharge rule only.** W9-T17's last clause is complete when WP9.7's
   binding test passes, not before.

**Known limits that stay.** Content identity catches a byte copy of bytes that are recorded, or current at a
registered path. It does not catch a re-serialized or partly copied result, or a copy of bytes that were at a path
only between two observations. Those are for the artefact's own governing review (§16).

*The alternative* is for WP9.7 to refuse every artefact whose bytes match a legacy observation, adopted or not. It
is simpler and needs no use mapping. Its cost is that an adoption for a claim use then has no consumer until some
other path is designed, so W9 §12.1's "adopted for 'evidence for the manuscript claims of paper X'" could not be
acted on.

### 4.3 U-9: where an adopted input is read and re-hashed

- The artefact use resolver re-hashes at use (`artefacts/use_resolver.py:310-317`), but it reads through the control
  root's content reader, and restricted bytes never enter the store (W9 §5.4).
- So an adopted input reaches a successor Task by reference only: a `w9-adoption:` string in `source_import_refs`
  (§4.1), resolved against the adoption record through §9's interface.
- `resolve_adoption_ref` returns the observed source identity for **every** adoption, family or whole file: the
  path, the SHA-256, the Git blob where there is one, and the byte length. Revision 2 returned it for whole-file
  adoptions only, which left a family adoption's consumer nothing to re-check (re-review R-M3).
- The re-hash is successor-side code at dispatch or at use, and it is WP9.7's (06v WP9.7, "Use-time re-hash"). WP9.7's
  guard refuses an adopted input, of either kind, whose current bytes differ from the observed identity. For a
  whole-file adoption it also requests `RecordAdoptionUseMismatch` (LR-061). The annex gives that row to whole-file
  adoptions only, so a family mismatch is refused without a record, and the fix is a re-observation, which suspends
  the adoption (§7).

WP9.4's half is the adoption subject (§6.1) and the lookup (§9). It adds no successor-side read.

### 4.4 U-10 and U-11, settled

Revision 1 left both to the code PR. The first review showed they can be settled now (m-6).

- **U-10: "the successor result artefact accepted, not only registered" (LR-030).** The one accepted state is
  `use_authority: accepted_for_scope`. Reaching it needs a governing review under any predicate, and a
  `claim_promotion` Decision under the claim predicate only (`service.py:4618-4631`, `:4901-4902`). Revision 2 said
  every discharge therefore needs its result promoted at claim level. That overstated the cost (re-review R-M1). §8
  reads the row as: accepted under any predicate. Which predicate fits a given discharge is for its reviewer (§16).
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
| `_session_refs` | `replay/reducers.py:744-755` | under owner point B, a second entry for LR-026, the eligible session (§5.5) |
| the Decision-proposal preparer's payload | `legacy/preparers.py:452-466` | three optional fields and a row discriminator (§5.5) |
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
- LR-024 does not call it. An eligibility Decision is proposed before the adoption's review can exist, so it has a
  proposal branch of its own with no review requirement (§5.5; re-review R-M4).

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

The reviewer exclusions are unchanged: a reviewer is never the proposal's creator, at every row, LR-027 included.
The session exclusion changes at LR-027 only: there the reviewer's session must differ from the analyst's session and
equal the eligible session (§5.5), and at every other row it differs from every session the request records
(`:865-896`; confirmation C-m1; review of revision 4 R4-i3).

### 5.4 Fixture refs in the resolving Decision (owner point L)

P-072 item 4 (accepted): "Per-fixture evidence or waiver refs travel in the resolving Decision, or, for a
closed-reference batch, in the record itself" (`03-decisions-and-open-questions.md:4618-4620`). LR-020 took the
second route: its items carry `pilot_promotion` in the record. WP9.4's five records have no fixture field, so the
first route applies to them.

Revision 1 made the fixtures a reviewer's checklist. That drops an accepted decision, and it also misread the annex:
several fixtures are unconditional (`when: null`), S-017 on LR-029 among them (review M-4).

WP9.3's encoding has no room for them. A Decision proposal's `governing_evidence_refs` must be exactly three
entries, and the resolution's are those same three (`replay/reducers.py:938-946`, `:1102`).

*Recommended: encode them, with the applicable set bound to the review.*

**The entries.** A WP9.4 Decision proposal's `governing_evidence_refs` is, in this order:
1. the three subject refs, as today;
2. zero or more `w9-fixture:<fixture ID>:<ref ID>` entries, sorted by fixture ID, at most one per fixture;
3. for LR-033 and LR-053 only, exactly one `w9-open-items-blob:<sha1>` entry (§8).

Each `<ref ID>` is a `rev_` or an `art_` for evidence, or a `dec_` for a waiver, as LR-020's rule has it
(`:575-596`). The resolution repeats the proposal's list after its own row ref, as it does today. The re-review
confirmed that entries after the three subject refs leave row assignment, the resolution's rewrite and every WP9.3
check for WP9.3's rows unchanged (R-i1). WP9.3's rows keep exactly three refs.

**Which fixtures must appear.**
- **Unconditional fixtures** of the resolution row: always. From the annex: LR-029: S-017. LR-044: F-018, F-023,
  F-037. LR-054: F-006, F-019, F-023, F-037. LR-055: F-006, F-019, F-037. LR-034 and LR-049 list none. S-007 on the
  review and Decision-proposal rows is the stale-hash control those rows already enforce (W9-C22), not an evidence
  ref.
- **F-019 at LR-029** whenever the use is `w9-use:manuscript-claims/…` or `w9-use:claim-evidence/…`. Its annex
  condition is "the intended use is evidence for a claim", which §6.2's use string decides exactly.
- **The other conditional fixtures** are F-015 and F-038 on LR-029, and F-038 on LR-054 and LR-055. Their conditions
  ("the adopted family is statistical", "uses the TDA pack's lanes") are not decidable from the record.

**Who decides applicability.** W9 §12.3: "Per-item applicability is proposed by the item's independent reviewer and
fixed by Stephen …, never by the item's producer." Revision 2 let the analyst choose it at the Decision proposal,
after the review, and cited P-084 item 3. That precedent does not carry (re-review R-M5): for LR-020 the list is
inside the record whose hash the reviewer approves. Here it would be outside every reviewed hash.

So the applicable set is put in front of the reviewer. The review request's `review_questions`
(`replay/reducers.py:813`; `legacy/preparers.py:380-396`) must contain one entry of the form
`w9-applicable-fixtures:<sorted fixture IDs, comma-separated>`, naming every fixture the request proposes as applicable.
Replay requires that set to hold every fixture the two rules above require, and nothing outside the resolution row's
list. The request row's own list (S-007 at LR-026) is the stale-hash control and is not part of the set (confirmation
C-i5). The Decision proposal's fixture entries must name exactly that set. The reviewer approves or refuses the
request's set with the proposal, and Stephen resolves on it.

This is still the analyst writing the list and the reviewer approving it, as at LR-020, and not the reviewer
proposing it. Read literally, W9 §12.3 is not met: the analyst who writes the list is the item's producer (§5.3),
and an approve-only verdict cannot carry a different set. So the note does not claim compliance. It asks Stephen to
record the encoding as **an extension of P-084 item 3's i-3 reading** to WP9.4's five families: for LR-020, the
analyst's list is "fixed when the reviewer approves the hash and Stephen resolves on it", and here the list is fixed
before the verdict and cannot change after it. The confirming re-review judged that a fair extension, and not plain
compliance (confirmation §2, addition 3).

This changes an encoding P-081 fixed, for WP9.4's rows only.

*The alternative* is a recorded departure from P-072 item 4 and W9 §12.3: fixtures stay a reviewer's checklist for
these rows, and nothing in the ledger shows whether S-017 or F-037 was ever named.

### 5.5 The eligibility Decision's encoding (if owner point B is taken)

LR-024 and LR-025 fit none of WP9.3's Decision checks: they bind more than a subject, they have no Decision ID in
any record, LR-024 comes before the adoption's review, and LR-025 writes no record (review M-12; re-review R-M4).

- **The Decision ID** is derived: `derived_id("dec", "w9-adoption-eligibility:" + record_id,
  utc_milliseconds(created_at))`, reserved at LR-023 with the proposal. So an adoption proposal has exactly one
  eligibility Decision. A rejected or lapsed one needs a new adoption proposal.
- **LR-024 has a proposal branch of its own.** It does not run through `_check_decision_proposal`
  (`replay/reducers.py:931-975`), which would require the adoption's review satisfied before that review can exist.
  The branch checks: the generic fixed fields (`:952-961`); the subject's current hash; the Decision ID is the
  derived one and its reservation is taken; the eight refs below; the analyst rule of §5.3; and **no** review. It
  extends the adoption proposal's lapse to the Decision's expiry, as the generic branch does (`:973-974`), so an
  eligibility Decision that is still open keeps its adoption proposal open.
- **LR-024's `governing_evidence_refs`** are exactly eight, in this order: `W9:LR-024`; the adoption's
  `w9-subject:` and `w9-subject-sha256:`; then `w9-eligible-session:`, `w9-eligible-family:`,
  `w9-eligible-version:`, `w9-eligible-profile:` and `w9-eligible-grade:`, each non-empty. LR-024 refuses a grade
  other than the constant `independent` (`:117`).
- **The kind** is `migration_authority`, subject to owner point B's confirmation (§2.2).
- **LR-025 is a record-less resolution.** Its transaction is the one `DecisionResolved` event. `_check_resolution`
  reads a second event (`:1087`) and would fail on it, so LR-025 gets its own branch: the Decision is open and of
  this family; the fixed resolution fields hold; it is resolved before it expires and before the adoption proposal
  lapses; and no record follows. It is not a G5 row (annex G5). `prepare_resolution` always appends a recorded
  event (`legacy/preparers.py:528`), and `RECORDED_EVENTS` has no LR-025, so the preparer gets the same record-less
  branch: for an eligibility Decision it prepares the one `DecisionResolved` event (confirmation C-i1).
- **LR-026 names the eligible session in the request.** A W9 request names its reviewer as an actor, and its
  `required_evidence_refs` are fixed to the analyst's session alone for every row but LR-007 (`:744-755`). For
  LR-026, `_session_refs` requires two entries: the analyst's session, then `w9-eligible-session:<s>`. Replay
  refuses unless the eligibility Decision is resolved `accept` and `<s>` equals its `w9-eligible-session:`. The
  review state stores the two apart: the analyst's session in `sessions`, which `_check_verdict` excludes
  (`:819`, `:853`, `:893-895`), and the eligible session in its own field. Revision 3 left both in `sessions`, so
  the check would have refused the one session LR-027 requires (confirmation C-m1).
- **LR-027 binds the verdict to that session.** Today replay checks only that the verdict's `reviewer_session` differs
  from the sessions the request records (`:893-895`). For an adoption verdict it must differ from the analyst's session
  and **equal** the request's eligible session. `reviewer_profile` must equal the Decision's `w9-eligible-profile:` in
  place of the constant `w9-independent-reviewer` (`:884`). `reviewer_model_metadata` is one string in the verdict's
  schema (`.research-system/schemas/core/events/review_verdict_recorded.schema.json:75-79`), and must equal
  `<family>@<version>` from the Decision. `computed_independence_grade` stays `independent`.
- **The preparer's payload.** `prepare_decision_proposal` takes exactly four fields and maps a kind to one Decision
  row (`legacy/preparers.py:452-466`). It gains three optional fields:
  - `eligibility`, an object with the five facts. Its presence on an adoption proposal selects LR-024, and its
    absence LR-028. It is refused on any other kind;
  - `fixture_refs`, the entries of §5.4, refused on a WP9.3 row and on LR-024;
  - `open_items_blob`, required on LR-033 and LR-053 and refused elsewhere (§8).

  `prepare_review_request` gains `eligible_session`, required for an adoption and refused elsewhere, and reads the
  applicable-fixtures entry from `review_questions` (§5.4).
- **What replay does not check.** The annex's (a) to (c), that the session's family differs from the producer's,
  that its role profile declares the lane's capability, and that its context is independent, are Stephen's check at
  LR-025 (annex: "checked by Stephen, never by the producer or the named session"). Replay sees attested strings.
  §16 lists them.

### 5.6 Authority subjects: G4 for WP9.4's rows (owner point N)

A scoped grant names one subject kind and one exact ID, and cannot carry a content hash (WP9.3 note §5.3). WP9.3
therefore read G4 for a proposal row as: the grant is exact on the pre-assigned record ID, and the content hash is
bound later by the review and the Decision. Stephen accepted that reading for LR-003, LR-006, LR-011 and LR-016 only
(P-081 item 12, `03-decisions-and-open-questions.md:5206`). Revision 2 did not address G4 at all (re-review R-M8).

| Rows | Command | Subject kind and ID | What binds the hash half |
|---|---|---|---|
| LR-023, LR-030, LR-040, LR-045, LR-050 | `ProposeLegacyRecord` | `scope_definition`, the pre-assigned record ID | The review and the Decision, each on the recomputed hash. **This extends P-081 item 12 to five more rows** |
| LR-026, LR-031, LR-041, LR-046, LR-051 and their verdict rows | the two review commands | `review`, the review ID | As WP9.3: the request and verdict carry the subject hash |
| LR-028, LR-033, LR-043, LR-048, LR-053 and their resolution rows | the two Decision commands | `decision`, the Decision ID | As WP9.3: the proposal's subject refs |
| LR-024, LR-025 (owner point B) | the two Decision commands | `decision`, the derived eligibility Decision ID (§5.5) | The eight refs, which replay fixes at LR-024. The ID is derived from the adoption alone, so LR-024's grant binds none of the five facts; Stephen's grant at LR-025 names the Decision and his resolution binds them. That is P-081 item 12's shape on a sixth row, which N names (confirmation C-i3) |
| LR-035 | `CreateLegacyPaperRoot` | `scope_definition`, the root's record ID | The schema closes the key and path to two values, and replay admits one root per key. The annex subject is "the P01 key + its manuscript root path", so the ID alone leaves nothing unbound that replay does not check |
| LR-039 | `RecordPaperCitationStatus` | `scope_definition`, the status's record ID, **which is derived** | See below |

**LR-039 needs a derived record ID.** Its annex subject is "the root + the frozen cited-family set's hash + the
reviewer's derivation". It has no review and no Decision, so nothing later binds those hashes. A grant on a free
record ID would authorize any cited-family set the reviewer then submits.

WP9.3 met the same problem for an observation and solved it by deriving the record ID from a digest of the full
subject (`legacy/records.py:157-203`). LR-039 does the same: the status's `record_id` is
`derived_id("obj", "w9-citation-status:" + root ID + ":" + supersedes ID or "none" + ":" +
cited_family_set_sha256 + ":" + extractor_output_sha256 + ":" + reviewer_derivation_sha256,
utc_milliseconds(root created_at))`. The preparer refuses a supplied ID that is not that value. `ars legacy
cited-families` prints the ID for a given reviewer hash (§13), and Stephen's grant names it. The grant then binds
all three hashes.

**The registry.** `_SCOPED_COMMAND_SUBJECT_KINDS` (`research_system/authority.py:217`) gains the two new commands as
`scope_definition`, with WP9.4-2's D-4 (§14).

*Recommended:* extend P-081 item 12 to the five proposal rows, and to LR-024, by this note's decision entry, and
take the derived
ID for LR-039. *The alternative* for LR-039 is an owner reading that its grant binds the record ID only, which
leaves the cited-family set outside G4.

## 6. Adoption (LR-023 to LR-029)

### 6.1 Subject

- **By family** (`subject_kind: families`). The observation is a `json_family_set` observation. Every named family
  is one of the observation's families. The observation is in a recorded closed-reference acceptance, and neither is
  superseded.
- **Whole file** (`subject_kind: whole_file`, `rehash_at_use: true`). The observation's selector is `whole_file`,
  the source has no JSON family (its registered path does not end in `.json`), **and it is binary or restricted**:
  - restricted: its source kind is `restricted_untracked_file`, or its path has a suffix on the D-9 list (`.csv`,
    `.pkl`);
  - binary: its bytes are not valid UTF-8. Replay cannot read the bytes, so this is the preparer's check at LR-023,
    re-read at LR-029 with the window. Replay checks the restricted half, and that the path does not end in `.json`.

  A tracked, unrestricted text file, such as a `notes.txt`, is not a whole-file subject (CodeRabbit, on revision 3).
  Its class is the `w0_class` of its one `whole_file` family entry (§4.4).

W9 §9 item 1 limits the whole-file route to "a binary or restricted input with no JSON family (an embedding, a null
cache)". Revision 2 tested for "no accepted membership table", which would have adopted whole a JSON result whose
table was simply never accepted, and applied even that test to tracked files only (re-review R-m2; CodeRabbit). A
JSON result is adopted by family, and until its membership table is accepted it cannot be adopted at all.

An item observation (`inventory_item`) is not an adoption subject. W9 §9 item 1 names families and whole files only,
and a tracker row or a log entry has no successor use that W9 defines. The proposal refuses it.

W9-T1 holds as in WP9.3: no code derives adoption from source text. The class is the observation's, from its signed
W0 record.

### 6.2 Intended use (owner point F)

The schema gives `intended_use` a free `description` and a nullable `successor_ref` of any kind. Two things compare
uses exactly: LR-039 ("an active adoption for the use 'evidence for the manuscript claims of paper X'") and the
admissibility predicate (W9 §9 item 4: "admissible to W5 for the named use only"). A free string cannot be compared
safely.

Revision 1 proposed three fixed values, two of them with no target. Those two refuse too little (review M-7): W9 §9
item 2 binds a named use ("input to T1.41 successor Task", "evidence for claim candidate X"), and one
`claim-evidence` adoption with no target would be admissible for every claim.

*Recommended:* replay accepts three forms of `description`, each naming its target:

| `description` | Target | `successor_ref` | Source |
|---|---|---|---|
| `w9-use:manuscript-claims/<paper key>` | The paper key is exactly `P01-A` or `P01-B`, as the paper-root schema spells them | null. The root may not exist yet (LR-035 comes later) | W9 §12.1 |
| `w9-use:task-input/<key>` | `<key>` matches `[a-z0-9][a-z0-9._-]*` | null, or a `tsk_` ref. Null when the Task is created after the adoption, which W9-T8 requires | W9 §9 item 2; §10 item 3 |
| `w9-use:claim-evidence/<key>` | `<key>` matches the same pattern | null | W9 §9 item 2 |

The lower-case pattern applies to the task and claim keys only, not to the paper key (CodeRabbit).

**What a key names, and where the consumer finds it.** A claim key is the claim candidate's key, an attested
string. A task-input key must be something the successor Task itself carries, or the guard that consumes the
adoption cannot compare it (re-review R-M9). The Task definition has no field for a pre-registration ID or a use. Its
`aliases` are the one carrier: each has a `namespace`, a `value` and a `scope_id`
(`.research-system/schemas/core/commands/create_task.schema.json:42-49`, `$defs/alias`). So:
- a task-input key is the `value` of an alias the Task carries in the reserved namespace `w9-use-key`;
- WP9.7's CreateTask guard (owner point J) builds the use string from that alias and calls `family_admissible`
  with it. A Task with no such alias, or with another key, is refused for that adoption;
- the alias's `scope_id` is WP9.7's to fix when it designs the guard.

`family_admissible` compares the whole `description`, so an adoption for one Task or claim admits no other.

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
| LR-026 | The review ID is the derived one; the request's second session ref is the resolved eligibility Decision's session (§5.5); the applicable-fixtures entry (§5.4); W9-C20, W9-C22 | — |
| LR-027 | The submitter is the named reviewer; the verdict's session equals the eligible session; the profile and model metadata equal the Decision's (§5.5); W9-C21 | — |
| LR-028 | `review_id_for` returns the derived review, and it is satisfied on the current hash; the subject is the record's ID and hash; the fixture entries name exactly the request's applicable set (§5.4) | — |
| LR-029 | G5 with F-8's first limb; `considered_review_ids` is exactly the derived review; the fixture entries repeat the proposal's; the adoption would not be projected suspended at this position (§7) | The source re-reads to the observed identity at commit (W9-T6, O-33) |

## 7. The suspension projection (`P:legacy-adoption-status`)

An adoption's status is derived at replay, never stored in the record. It is `active` or `suspended`, with the cause.
The annex's `suspension_rule` gives three causes:

1. **A later observation of its source,** "whether or not the bytes changed". An adoption is suspended by:
   - any later observation of the same registration, for a whole-file adoption. Under owner point K's option 1, a
     root registration's members share one registration, so for a member the test is a later observation of the
     same registration **and the same source path**: observing an unchanged `root/b.npy` leaves an adoption of
     `root/a.npy` active (CodeRabbit, on revision 3). It is the same per-path reading as K's readings 3 and 4, applied
     to this note's own rule;
   - a later observation of the same registration whose selector names at least one adopted family, for a family
     adoption;
   - **its own observation being in `stale_observations`, for either kind.** `reduce_record` marks every earlier
     observation of a registration stale when a later one records a different source fingerprint, whatever the
     later one selects (`replay/reducers.py:1403-1414`). So when a result file changes and the observer re-observes
     only other families, the old adoption still suspends. Revision 1 missed this case (review M-1). It is the
     carried obligation of P-081's 2026-11-08 addition ("the accepted record projects as stale, and what follows is
     WP9.4's").

   `observations_by_registration` is in ledger order, so "later" is a position in that list after the adoption's
   observation (review i-4).
2. **A supersession of a record it relies on:** its observation, that observation's closed-reference acceptance, or
   the adoption itself. `state["supersessions"]` already holds the chain (`:1062-1077`).
3. **A recorded use-time mismatch** naming the adoption (LR-061).

The annex's item-adoption clause ("a later observation of the same item selector") has no subject under §6.1. The
projection implements it anyway, so that a later reading of §6.1 does not need a reducer change.

**What the projection cannot see.** It reads recorded observations. A registered file that changes and is not yet
re-observed leaves its adoption projected `active` (re-review R-M3). W9 §4.2 item 3 makes the re-observation an
obligation, and WP9.5's detectors are what notice a missed one. Until then the adopted bytes are protected by the
use-time comparison of §4.3, not by this projection.

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
| LR-030 | The schema; the pre-assigned refs reserved; one open relation per `(item_kind, item_id)` | `item_id` resolves against the accepted open-item list (owner point H); the successor result artefact's current `use_authority` is `accepted_for_scope`, under any predicate (§4.4); **the artefact's bytes match no recorded legacy observation** (`legacy_content_matches`) |
| LR-031 | WP9.3's request checks, with §5.3 and §5.4 | **G3:** the named reviewer is not the artefact's producer, read from the artefact's manifest in the generic projection |
| LR-032 | WP9.3's verdict checks | — |
| LR-033 | WP9.3's Decision-proposal checks; the fixture entries; exactly one `w9-open-items-blob:` entry | The blob is the open-item file's at the binding's `git_head` |
| LR-034 | G5 with F-8's first limb | The artefact is still `accepted_for_scope` and still matches no legacy observation; the open-item file's blob still equals the Decision's entry and still holds the item; G3 again |

**A discharge needs a new result.** Without the content check, a byte copy of the legacy result that the open item
is about could be registered, promoted under any predicate with a review only, and named as the result that
discharges it. LR-054's "every open item has a discharge" would then pass on the legacy bytes themselves (re-review
R-M2). The check refuses any match, adopted or not: an adopted family is still not a new result.

**G3 for a discharge holds at the preparer only.** Revision 1 placed it in replay, "by the actor the proposal
recorded". Replay has no such input (review M-8): the discharge record has no producer field, the proposal state
keeps only the proposer's `actor_id` (`replay/reducers.py:727-736`), and replay's context carries five keys and no
artefact state (`replay/driver.py:199-205`). Passing the generic artefact manifests into legacy replay would change
the shared replay boundary that WP9.2 confined to four sites (06v U-7). So the check stays at the preparer, and §16
records that a forged ledger with the producer as reviewer replays clean. The same holds for the content check and
the accepted-state check: both read the generic projection.

LR-034 has no W9 §17 test (`discharge_no_w9_test`), so its controls are W9-C23 and the row's own negatives (§15).

**Owner point H: the open-item list.** "The accepted A-001 list or the audit (W0-D1)" is outside the store. It is read
as WP9.3 reads its outside inputs: a committed file in the W9 evidence area, `.research-system/evidence/w9/`, read at
the binding's `git_head` (WP9.3 note §11.1; P-081, owner point D).

*Recommended:*
- the file is `legacy-open-items.json`, of format `w9-legacy-open-items/1`: one row per item with `item_kind`,
  `item_id`, the source it comes from, and `feeds_papers`, the paper keys whose claims the item feeds;
- its content is Stephen's, under W0-D1, and it is written at the live stage, not by this package. WP9.4 fixes the
  reader and the format, and its tests use fixture lists;
- **the file's blob is bound in Stephen's Decision.** The Decision proposals at LR-033 and LR-053 each carry one
  `w9-open-items-blob:<sha1>` entry, after the fixture entries (§5.4), and the preparer refuses unless it is the
  file's blob at the binding's `git_head`. So "scoped out by Stephen" (W9 §12.1) is an edit Stephen has resolved on,
  not a PR edit alone (review m-7);
- **every check that reads the file is the preparer's.** Replay sees the blob string and nothing else (re-review
  R-m1). §16 records that a forged ledger naming a wrong blob, or leaving an item undischarged, replays clean;
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
  use and status, and the observed source identity for every adoption: path, SHA-256, Git blob where there is one,
  and byte length (§4.3). A malformed ref, or one that names no recorded adoption, raises.
- `family_admissible(state, observation_id, family_name, use)`: true only when an active adoption of that
  observation names that family and its `description` equals `use` exactly (§6.2). Otherwise false, with one of the
  reasons `unadopted`, `suspended` or `other_use`. A whole-file adoption answers for the family name `whole_file`.
- `legacy_content_matches(state, sha256, git_blob)`: every recorded observation whose source has that SHA-256, or
  that Git blob when both the argument and the observation carry a blob. An absent value never matches, so two
  untracked files with no blob are not a match (CodeRabbit, on revision 3). It sees recorded observations only
  (§4.2).

The functions read. A test asserts that a module outside the legacy package imports from it only
`projection_read`, plus the existing imports listed above, which the test allowlists by module and importer
(review m-2).

## 10. The full path (LR-035, LR-040 to LR-055)

### 10.1 The ordinary paper root (LR-035)

The schema closes the key and the path to P01-A and P01-B. Replay refuses a second root for a key, a `recovery`
value that is not null (that is LR-038, WP9.6), and a root with no passed pilot outcome Decision (LR-022). The last
check refuses on every store until WP9.7 (owner point D).

### 10.2 The root's registration and its member files (owner point K)

**What the accepted texts say.** W9 §3.1, on manuscripts: "A root is the one directory registration W9 allows. As in
W11 §7.2, it authorizes no nested file its inventory does not list; the root's full-path inventory lists every file
under it" (`design/09-migration-compatibility-and-pilot.md:134`). The registration schema fixes the role
`legacy_manuscript_root` to the two root directories
(`.research-system/schemas/contracts/w9/legacy-path-registration.schema.json:190-`), and no other role names a
manuscript file. The source-inventory schema carries `root_registration_ref` once on the record, and per row a
`repository_path`, a `git_blob` and an `observation_ref`, with no per-row registration.

Revision 2 concluded that each of the 55 member files needs its own registration, that no role fits one, and that
owner point K therefore needs a catalogue revision. The first two statements hold. The conclusion does not: W9 §3.1
gives a reading that needs no revision, and revision 2 missed it (re-review R-M7).

**Option 1 (recommended): members are observed under the root's registration.**
- A member file is observed with a `whole_file` selector over that file, its `registration_ref` naming the root
  registration, and its source path strictly under the root's path. It is never registered itself. The inventory
  lists it, which is what W9 §3.1 says authorizes it.
- That needs five recorded readings, each recorded as P-084 recorded its readings: four of WP9.3's replay checks
  (items 1 to 4) and one of its preparer and reader (item 5). Revision 3 listed three readings; the confirming re-review found the fourth (C-M1),
  and the review of revision 4 found the preparer side (R4-M1):
  1. **LR-015's path rule.** Replay requires an observation's source path to equal its registration's path
     (`replay/reducers.py:485-491`). That rule is WP9.3's code, not an annex text. For a registration of role
     `legacy_manuscript_root` replay reads it as: the path is strictly under the root's path and does not end in
     `/`. Replay sees a path string only; "a regular file" is the preparer's check, in item 5 (R4-i5);
  2. **`_whole_file` for a root registration** (`:526-536`). A member observation covers one file, not the whole
     registration, so `_whole_file` itself returns false for it. The change is made in `_whole_file`, not only at
     LR-020's emission, because two other sites read it: `check_acceptance`'s "two whole-file items of one
     registration" refusal (`:614-616`), which would otherwise refuse a batch of two members, and `derive_ownership`
     (`:629`), which then emits no ownership record. P-072 item 2 ("an accepted observation whose selector covers
     the whole registered file") is not met for the root;
  3. **the stale rule** (`:1403-1414`) compares fingerprints across all observations of one registration. For a
     root registration it must compare per source path, or every member observation would mark the others stale;
  4. **"the latest for its source and selector"** (`_batch_rules`, `:550-559`). An acceptance item is refused when
     any later observation of the same registration has the same selector key. Every member has the selector
     `{"selector_kind": "whole_file"}`, which names no path, so every member but the last observed would be refused,
     and the inventory could never be completed. For a root registration the key must include the source path. The
     confirming re-review showed the refusal on two real members, `drafts/.gitkeep` and `figures/.gitkeep`, which
     share one blob and so are not stale;
  5. **the preparer and the reader read a member, not the root** (R4-M1). `LegacyReader.read(registration)`
     (`research_system/legacy/reader.py:275-285`) reads the registration's own path. Under option 1 that is the root
     directory, which the reader refuses, and all four reads on option 1's route pass the registration: the LR-015
     preparer's read and final re-read (`legacy/preparers.py:594`, `:633`), the `observation_id` helper behind
     `ars legacy observation-id` (`:652`), and the acceptance's window re-read at LR-016 and LR-020
     (`legacy/acceptance.py:69`). The change:
     - **the carrier.** The `ObserveLegacyRecord` payload gains a `member_path` key, admitted only when the
       registration's role is `legacy_manuscript_root` and required then. It is a payload key, like the existing
       `frozen_copy_ref` (`preparers.py` module docstring, "``ObserveLegacyRecord``"), and is stripped before the
       record is built, so the observation schema does not change. The record carries the path where it already
       does: the read-derived `source_identity.repository_path`;
     - **the root's source kind.** A `legacy_manuscript_root` registration is `git_tracked`. The schema does not
       fix it: its repository-root branch admits `git_tracked`, `untracked_file` and `restricted_untracked_file` for
       any role, and `LegacyReader.read` records `repository_path` for the first kind only, and `path` for the two
       untracked kinds (`legacy/reader.py:317-325`). So LR-003's preparer refuses any other kind for that role, as part of this
       reading, and every member's path is then its `source_identity.repository_path`. The inventory lists tracked
       files only (§10.3). The D-9 restricted rule keys on the registration's path suffix, which for a root ends in
       `/`, so it never reaches a member; LR-015's preparer therefore refuses a member whose path has a D-9 suffix
       (`.csv`, `.pkl`). Neither root holds such a tracked file today (review of revision 5, R5-m2);
     - **the read.** `LegacyReader.read` takes an optional member path. For a root registration it requires one,
       refuses it unless it is a regular file strictly under the root's path (resolved handle-bound, as today), and
       reads it; for every other role it refuses one. The preparer's read and re-read pass `member_path`;
       `observation_id` takes it from the same payload; `reread_items` takes it from the observation's
       `source_identity.repository_path`;
     - this is a change to WP9.3's preparer and reader, not to an accepted byte. It is the fifth recorded reading.
- The consequences: the root registration stays `legacy_owned` until LR-054 moves it; no member has a registration
  or an ownership record; and after LR-054 the whole root is `successor_owned`. The writer-rule question of revision
  2 does not arise, because no member is a `closed_reference` file.
- Its cost: the five readings change checks on WP9.3 rows (LR-015 and LR-016 to LR-020), so they need Stephen's
  record and a test each. All five are code changes in WP9.4-2: to the path rule, to `_whole_file`, to the stale
  update in LR-015's reducer, to `_batch_rules`, and to the observation preparer and reader. None changes an accepted
  byte.
- **Each reading is gated on the role.** It applies to a registration of role `legacy_manuscript_root` only, and
  every other registration keeps today's check exactly. Revision 4 gave a different reason ("LR-015's path rule gives
  such a registration one path"), which is false for a `legacy_decision_log_entry` registration: its source is any
  accepted export's retained copy (`replay/reducers.py:472-484`), so two of its observations can have two paths,
  and today the later one marks the earlier stale. A per-path stale rule for every role would leave the older one
  live (R4-m1).
- **One check refuses too much under option 1.** `check_change_list` keys a shared-surface change by the
  registration (`legacy/acceptance.py:125`). A change list can name only the root, so one affected member makes
  every member observed before that merge unacceptable until it is re-observed. That refuses too much only, and the
  note leaves it (R4-i2).

**Option 2: a member-file role by catalogue revision.** Add a role such as `legacy_manuscript_member`, register each
file, and let LR-020 close each one. That needs a new catalogue identity and a routed LR-002. It also sits badly
with W9 §3.1's "the one directory registration", and it leaves every draft a `closed_reference` file under a
`successor_owned` root, so WP9.7's guard would need an exception before a successor could write any draft.

**Option 3: an inventory with no per-file observation.** It contradicts annex LR-040 ("every row bound to an
accepted observation") and the inventory schema, so it too needs a catalogue revision.

**The replay refusal that protects the root** (review m-4) depends on K. A forged whole-file observation of the root
directory itself would, at LR-020, close the root before LR-054 needs it `legacy_owned`
(`replay/reducers.py:619-650`). The reader refuses a non-regular file (`research_system/legacy/reader.py:168-169`),
but replay does not check it.
- Under option 1, LR-015's replay refuses an observation of a root registration whose path is not strictly under
  the root or ends in `/`, and the preparer refuses one that is not a regular file (item 5).
- Under option 2 or 3, LR-015 refuses every observation of a root registration, as revision 2 had it.

**The root registration itself (owner point O).** Under every option of K, LR-040 needs "the root's registration
live", and today no store can record one (review of revision 4, R4-M2). The schema fixes a root's `normalized_path`
to `papers/P01-A-JRSSA/` or `papers/P01-B-JRSSB/`, with the trailing slash
(`.research-system/schemas/contracts/w9/legacy-path-registration.schema.json:189-211`). LR-003's preparer, and
LR-005's at resolution and at commit, require "one physical identity, read handle-bound" (annex LR-003; LR-005: "its
physical identity re-read unchanged") through `_require_physical_identity` (`legacy/preparers.py:151-172`, called at
`:332` and `:541-542`). That runs `handle_bound_read`, a file protocol that refuses the slash form as non-canonical
and the bare directory as "not a regular file".

*Recommended:* for a registration of role `legacy_manuscript_root` only, LR-003 and LR-005 read the path as a
directory under W11 §7.3's protocol: open the registered root anchor, bind to the directory's handle, and record
the same physical-identity fields the schema already requires (canonical target, reparse chain, volume serial
number, stable ID, link count, aliases). W11 §7.2 defines a registration's physical identity with a "stable
directory/file ID" (`design/11-portfolio-and-discovery-lifecycle.md:1153-1155`), so a directory identity fits the
accepted schema unchanged. This is a reading of annex LR-003's "read handle-bound" and LR-005's re-read for a
directory, which Stephen records. It is a change to WP9.3's registration preparer (a directory mode of the
handle-bound read), built in WP9.4-2, with two tests: a root registration records and re-reads its directory
identity, and a root path that resolves to a regular file, a junction or another reparse point is refused at LR-003
and at LR-005's re-read. A file path under that role is already refused by the schema, which admits the two
directory paths only, so it is not the control for O (review of revision 5, R5-i3).

**The identity's encoding.** The directory identity uses the reader's file encoding: `stable_file_id` is
`str(st_ino)`, with `volume_serial_number` `str(st_dev)`, from `fstat` on the bound handle
(`_physical_identity`, `legacy/reader.py:124-134`), not the store's
`DirectoryAnchor.identity` form (`windows-file-id-v1`, `store/anchor.py:407-410`). `_registration_conflicts` compares
`stable_file_id` strings across registrations, so the two encodings must not mix. `link_count` is recorded and is
not compared for a directory: on Windows it is stable when entries are added, and on POSIX it moves with
subdirectories; W11 §7.2 gives it "where applicable" (R5-i2).

**Prefix collisions (R5-M1).** O makes a directory registration recordable for the first time, and with it W11
§7.2's rule that "registration rejects … resolved-prefix collisions that would allow two writer sets to reach one
physical target. A directory registration cannot authorize an unregistered nested authority file"
(`design/11-portfolio-and-discovery-lifecycle.md`; W9 §3.1 repeats the second sentence for paper roots,
`design/09-migration-compatibility-and-pilot.md:134`). Replay's LR-003 check, `_registration_conflicts`
(`replay/reducers.py:401-420`), compares `(root_kind, root_id, normalized_path)` and
`(canonical_target, stable_file_id)` for equality only, and the schema confines no other role's path away from the
roots. So today a file under a recorded root could be registered under another role, for example
`papers/P01-A-JRSSA/_project.md` as `legacy_coordination`. After LR-054 it would be a member of a `successor_owned`
root and a `legacy_owned` registration of its own: two writer sets on one file.

So, as part of O's reading, replay's LR-003 check (and LR-003's preparer, before append) also refuses a
resolved-prefix collision with a `legacy_manuscript_root` registration, recorded or in an open proposal, as
`_registration_conflicts` already reads both today:
- a registration whose `normalized_path` is strictly under a root's path is refused;
- a root registration is refused when a recorded or proposed registration's path is strictly under its path.
The comparison is on `normalized_path`, at a path-component boundary. `_registration_conflicts` applies no
case-folding of its own; it relies on the schema's normalized form, and so does this check. The physical-identity
half needs no prefix form: a member file and its root have different identities. That makes option 1's "no member has a registration" a replay
invariant, not a consequence that only Stephen's LR-004 Decision protects. It is one more check in WP9.4-2, with two
tests (§15). It changes no accepted byte.

*The alternative* is to register the root under a file that stands for it, such as its `_project.md`. That
contradicts the schema's fixed directory paths, so it needs a catalogue revision.

**Timing.** One batch of at most 20 items is admitted today, and the code refuses every later batch whatever LR-022
says (`replay/reducers.py:104`, `:542`). Annex LR-016 makes a later batch depend on a passed LR-022, and the branch
that admits one belongs to the package that routes LR-022 (WP9.3 note §2.1). A root has more than 20 members, so its
inventory needs that branch under any option. It is WP9.7's carry.

### 10.3 The source inventory (LR-040 to LR-044)

- **"The root's registration live"** (annex LR-040): recorded, not superseded, of role `legacy_manuscript_root`, and
  currently `legacy_owned`. Replay checks all four (review m-9).
- **Complete membership.** The inventory is "complete over every file under the root at the observation commit".
  The preparer lists the root's tracked files at the binding's `git_head` with `git ls-tree -r`, and refuses unless
  the inventory's rows are exactly that set, by path and blob. Replay cannot see Git, so it checks what it can: row
  ordinals are 1 to n with no gap, paths are unique and under the root's path, and every row's observation is
  recorded, names the registration that K's option gives the member (the root's, under option 1), has that source
  path, and carries that blob.
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
  - **neither the mapping nor its inventory is superseded** at this position. Revision 2 checked that at LR-045 only
    (re-review R-m3). It is testable now on a forged ledger, and has a live subject once WP9.6 routes supersession;
  - **the subject is the root the mapping targets:** `subject_registration_ref.id` equals the
    `root_registration_ref.id` of the mapping's inventory, and that registration's `normalized_path` equals the
    root's `manuscript_root_path`. Without this a P01-A mapping could transition the P01-B registration (review
    M-10);
  - the root's current citation status exists, its two derivation hashes are equal, and every adoption it cites is
    active at this position (§11.3);
  - **the citation set was not made by the transition's producer** (§11.3);
  - the pilot outcome is passed (LR-022);
  - the fixture entries of §5.4 and the open-item blob entry of §8 are present.
- **LR-054, at the preparer:**
  - **the citation status covers the mapped inventory.** The status record has no inventory ref, and its closed
    schema admits none. So the preparer re-runs the extractor over the mapping's inventory and refuses unless its
    output hash equals the current status's `extractor_output_sha256`. A status derived from an earlier inventory
    then cannot carry a transition under a later one (CodeRabbit);
  - **the open items.** Every item in the open-item file whose `feeds_papers` names this paper has a recorded
    discharge relation, and the file's blob equals the Decision's entry. Replay cannot read the file (re-review
    R-m1), so a forged ledger with an undischarged item replays clean (§16);
  - the window: every inventory row's blob is re-read **and the root is re-listed**, as at LR-044. A tracked
    file added under the root after LR-044, or one removed, refuses with no event. Revision 4 re-read the rows only
    (CodeRabbit, on revision 4).
- **LR-055** (`successor_owned → closed_reference`). The subject is currently `successor_owned`. The annex adds no
  further precondition, and neither does this note. The preparer re-reads the window.

**The rest of §4.5's paper-root column is not machine-checkable in v1.** §16 lists each condition with the question
its reviewer answers.

## 11. Citation status and the extractor (LR-039; D-3)

### 11.1 What is compared (owner point I)

D-3 is decided: both an extractor and a reviewer's derivation, and "a difference blocks" (06v §6). The record holds
`extractor_output_sha256`, `reviewer_derivation_sha256` and `cited_family_set_sha256`.

Revision 1's rule was a bare path literal. Revision 2 added escapes, basenames and blocker entries, and scanned the
whole root. The re-review implemented revision 2's rule and ran it over both roots through Git (R-M6). It could not
record a citation status for either paper:

| At `4629d1fd`, revision 2's rule | P01-A | P01-B |
|---|---|---|
| Cited files | 47 | 10 |
| `ambiguous` blocker entries | 4 | 2 |
| `unregistered` blocker entries | 36 | 28 |
| of which name a directory, a stem or a filename template, not a file | 29 | 28 |
| Distinct blocker entries under `drafts/` only | 8 (4 ambiguous names, 4 directory paths) | 2 (directory paths) |
| Cited files if tokens are split on whitespace only | 17 | 1 |

Four defects follow from that table, and each is fixed below: a directory or a template can never be registered, so
it blocked for ever; "token" was undefined, and the cited set depended on the choice; a bare name that no
registered result has was dropped silently; and a result adopted whole, such as an embedding, had no family to
project to.

*Recommended:*

**1. Text and tokens.**
- A file that is valid UTF-8 is text. In a `.json` file every decoded string value is scanned as well, so that a
  JSON-escaped Windows path is read as its path.
- A file that is not valid UTF-8 is not scanned. It is listed as `not_text` in the extractor's report, and it does
  not block (CodeRabbit). A citation inside a binary file is for the reviewer's derivation.
- In text, `\` is read as `/` and repeated `/` is collapsed. Tokens are split on whitespace and on each of
  `` ` ' " ( ) [ ] { } < > , ; | * ``. A trailing `.` or `:` is stripped. Revision 4 did not split on `{` and `}`, so
  a LaTeX-wrapped path such as `\texttt{results/…/ph_L5000.json}` ended in `}` and was dropped as a template. With
  braces as separators the wrapped path is a clean token, and a template such as `table1_effects_{date_suffix}.json`
  still ends as the empty-stem token `.json` (review of revision 4, R4-m3).
- With braces as separators no token holds `{` or `}`. A directory placeholder therefore splits a templated path:
  `results/trajectory_tda_{survey}/post_audit/04_nulls.json` gives `results/trajectory_tda_`, `survey` and
  `/post_audit/04_nulls.json`. The first has no extension and is `not_a_file`; the second is not a candidate; the
  third is classed as a partial path under item 3 (review of revision 5, R5-m1).

**2. Candidates.** A token is a candidate when it contains `results/`, or ends in a registered result's basename,
or is a bare name with a result extension: `.json`, `.npy`, `.npz`, `.csv` or `.pkl`.

**3. Each candidate resolves to exactly one class.**

| Class | When | Blocks LR-039? |
|---|---|---|
| cited file | **Tested first.** A suffix of the token equals a registered `legacy_research_result`'s normalized path; or the token is a bare basename that exactly one registered result has; or the token has a directory part, no `results/`, and is a suffix of exactly one registered path (`trajectory_tda_integration/post_audit/04_….json`) | No. It enters the set |
| `ambiguous` | A bare basename that more than one registered result has; a token with a directory part, no `results/`, that is a suffix of more than one registered path; or a token with a directory part that ends in a registered result's basename but is neither under `results/` nor a suffix of a registered path, such as `notes/data.json` when `results/x/data.json` is registered (CodeRabbit, on revision 3). In each case, with no entry in the disambiguation file (below) | Yes |
| `not_a_file` | Tested after cited file. A token under `results/` that is a directory in Git at the binding's `git_head`, ends in `/`, or has no file extension; or any candidate **any of whose path components** is not a name: it contains `YYYYMMDD` or `YYYY-MM-DD`, or the last component's stem is empty (`.json`). Braces cannot occur in a token (item 1), so a brace placeholder reaches this row only as the extensionless stem before it (R5-m1) | No. It is reported and excluded from the hash |
| `unregistered` | Not `not_a_file`, and: a token under `results/` that names a file with no registration; or a bare name with a result extension that no registered result has | Yes |

The order is cited file, then `not_a_file`, then `ambiguous`, then `unregistered`. Revision 4 tested `not_a_file`
first, so a registered result whose real name held `YYYYMMDD` would have been dropped from the set; no tracked file
under `results/` has such a name today, but nothing forbade one (CodeRabbit, on revision 4). A template is never
registered, so testing cited files first changes nothing for templates. Revision 4 left
`results/trajectory_tda_{survey}/post_audit/04_nulls.json` an `unregistered` blocker that nothing could clear
(R4-m4). Revision 5 said that testing every component made it a template, which its own tokenizer does not do
(R5-m1). Under item 1 a directory placeholder splits the token: the part before it ends without an extension and is
`not_a_file`; the part after it is a partial path, cited when exactly one registered path ends in it and `ambiguous`
(cleared by a disambiguation row) when several do. A template therefore blocks only when its tail names a shared
basename, and a disambiguation row can always clear that block. The partial-path rows also close the other R4-m4 gap:
such a token had no class.

**"A suffix of" is read at a path-component boundary** (R5-i4): `audit/x.json` is not a suffix of
`post_audit/x.json`. On both roots the component reading and a plain string reading give identical classes (review of
revision 5, §4); the component reading is the safe one.

Nothing is dropped silently: every candidate is in the set, in a blocker entry or in the report.

**Why templates are `not_a_file`.** Revision 3's bare-name rule made a filename template a blocker that nothing could
clear (confirmation C-M2). P01-A's `drafts/sections/compute_table1_effects.py:205` names its own output as
`f"table1_effects_{date_suffix}.json"`. The tokenizer splits on `"`, which leaves `table1_effects_{date_suffix}.json`:
a bare name with a result extension that no registered result has. A template cannot be registered (W9 §3.1: "per
exact file"), it is not ambiguous, and a new status changes nothing, so the only routes were a draft write or an
extractor change. A template is not a citation of a file, so it is reported to the reviewer and does not block.
Outside `drafts/`, the same rule reports `.json`, `8000}.json`, `ladder_{survey}_L{landmarks}_B{B}_{date}.json` and
`level1_comparison_YYYYMMDD.json`, which would otherwise block under the whole-root alternative.

**4. The cited-family set.** For each cited file: every family of its accepted membership table, as
`(observation ID, family name)` pairs; or, for a file with no JSON family (§6.1), the one pair
`(observation ID, "whole_file")`. The pairs are sorted and written as canonical JSON. A cited JSON file with no
accepted table, or a cited file with no accepted observation, is a blocker entry. A cited text result that is not
JSON (a `.md` or `.txt` under `results/`) projects to a `whole_file` pair, but §6.1 lets no adoption admit it, so it
can only be marked unadopted. That is W9 §9 item 1's consequence, and no file the drafts cite is of that kind today
(R4-i4).

**5. The disambiguation file.** P01-A's drafts cite four basenames that more than one result has, for example
`05_analysis.json`. Without a way to resolve them, the only route is to edit the drafts, which are registered legacy
files. So an ambiguous basename can be resolved by a committed file in the W9 evidence area,
`citation-disambiguation.json`, of format `w9-citation-disambiguation/1`: one row per `(citing file path, normalized
token)` giving the **set** of registered paths it means, sorted and non-empty, or the value `not_a_result` when the
token names a file that is not a result (for example a copy under `notes/`). Every path in the set is a cited file, and
a `not_a_result` row moves the token to the report. Each row is the reviewer's proposal and Stephen's acceptance, so no
row can clear a citation by itself. A set, not one path, because one citing file can mean two results by one basename:
`drafts/sections/compute_table1_effects.py:22-53` composes each of three ambiguous basenames twice, under
`trajectory_tda_integration/` and under `trajectory_tda_bhps/` (confirmation C-m2). The key is the whole
normalized token, not the basename, because one citing file can hold `notes/data.json` as a non-result and
`alias/data.json` meaning a registered result, and one basename-keyed row could not say both (CodeRabbit, on revision
4). For a bare basename the token is the basename. The extractor reads it at the
binding's `git_head`, and its blob is part of the extractor's output, so the output hash changes when the file does. Its
content is the reviewer's proposal and Stephen's acceptance, as the membership tables are. It adds one row to the W9
paths addendum.

**6. Both hashes are of the same object:** the cited-family set, the blocker entries and the disambiguation blob.
The extractor's is computed by the preparer. The reviewer's is supplied, from a derivation made without the
extractor's output.

**7. Scope: the drafts block; the rest of the root is reported.** W9 §12.1 says "every result family its drafts
cite". 06v WP9.4 says "every file in the root's inventory". W9 is the higher text, and the claim-trace audit that
supplies the artifact map covers `drafts/sections/` only (below). So:
- the blocking set is derived from the files under the root's `drafts/` directory;
- the extractor still scans every other file in the inventory and reports what it finds there, without blocking and
  outside the hash.

Revision 2 followed 06v and scanned the whole root. On the real roots that added 24 and 8 cited files (47 against
23 for P01-A, 10 against 2 for P01-B; confirmation C-i2) and most of
the directory-and-template blockers, which sit in reviewer notes and `_project.md`. The decision entry records that
this note reads 06v's "every file in the root's inventory" as the extractor's scan, not as the blocking set.

**What still blocks, on the real roots.** The confirming re-review ran revision 3's rule over both roots through
Git at `ede231e5`, with the 506 tracked files under `results/` as the registration set and no disambiguation file
(confirmation §5):

| Drafts only | P01-A | P01-B |
|---|---|---|
| Cited files | 23 | 2 |
| `ambiguous` | 4: `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json`, `stratified_markov1_W2_L5000_20260502.json`, `05_analysis.json` | none |
| `unregistered` under revision 3 | 1: `table1_effects_{date_suffix}.json` | none |
| `not_a_file` | 4 directory paths | 2 directory paths |
| `not_text` | none | none |
| A candidate in no class | none | none |

Under revision 4's `not_a_file` rule the template moves to the report, so P01-A's drafts leave exactly the four
ambiguous names and P01-B's leave none. That is the re-review's run with one token reclassified by the rule as
written; the author did not re-run it. The disambiguation file can then clear P01-A's four. On a real store every
cited file also needs an accepted observation, and a JSON file an accepted membership table, or it blocks
(item 4).

**Citation forms the rule still misses.** A path composed in code from a directory string and a basename on another
line, as in `drafts/sections/compute_table1_effects.py:22-53`, gives a `not_a_file` token and an ambiguous basename,
not the cited file. A result cited by its stem, without an extension, is not a candidate. Both are for the
reviewer's derivation, and a difference then blocks.

**A departure from 06v.** 06v WP9.4 defines the extractor's output as "projected to families through the accepted
membership tables and the audit's artifact map". This note projects through the membership tables only. The
artifact map is §3.2 of `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md`, named as the source of the
cited-family set at `04-parallel-specification-and-foundation-pilot-plan.md:186`. It is prose with elided basenames,
so it is not machine-readable, and it is scoped to `drafts/sections/` (re-review R-m5). The reviewer reads it. One
related file sits inside the root, `papers/P01-A-JRSSA/notes/claim-trace-escape-foo-2026-06.md`. It is outside
`drafts/`, so its 15 backing files are reported and do not block. The decision entry for this note records the
departure.

**When the two derivations differ.** LR-054 refuses, and that is all the accepted row provides. The executable
routes are:
- **a new citation status** (LR-039 with `supersedes_status_ref`), when the reviewer's derivation was wrong;
- **a disambiguation entry,** when a basename was ambiguous;
- **a draft change,** when the drafts cite something they should not. That is a write to a registered legacy file,
  so it needs an allowed writer under W9 §4.2 item 1, and it re-triggers observation, the inventory and the mapping
  (W9 §4.2 item 3);
- **an extractor change,** when the rule is wrong. That is a code change with its own review, and a binding
  advance.

If the reviewer finds a result cited indirectly, by a table or a figure, that the extractor cannot see, the
transition stays blocked until the draft cites the file by name or the claim is removed. That is D-3 working as
decided.

*The alternatives:* the whole root as the blocking set, recorded as a departure from W9 §12.1, with the cost in the
table above; or narrowing the comparison to the claim-level families the artifact map names, which needs the map
rewritten in a machine-readable form first.

### 11.2 The extractor

`research_system/legacy/citations.py` is a pure function over bytes. Its input is the source inventory's rows: for
each, the blob named by the row's accepted observation, read from Git by blob ID at the binding's checkout. It never
reads the live tree (06v WP9.4, "Input"). Every file in the inventory is scanned or listed as `not_text`. It also
needs the registered result paths, from the replayed state, and Git's tree at the binding's `git_head`, to tell a
directory from a file.

Its output is one object: the cited-family set, the blocker entries, the disambiguation file's blob or null, and a
report of `not_a_file` tokens, `not_text` files and out-of-scope citations. `extractor_output_sha256` is the hash of
the first three. The preparer for LR-039 runs it, stamps that hash, and refuses a supplied value, as preparers do
for the content hash.

So LR-039 needs the root's accepted inventory first. The order is LR-044, LR-049, LR-039, then LR-050 to LR-054.
The annex's "hashed and filed before the transition" is met by that order, and LR-054's preparer re-runs the
extractor over the mapped inventory (§10.5).

### 11.3 The record's checks

| Check | Where |
|---|---|
| The root is recorded; the submitter is not the root's creator | Replay, at LR-039 |
| `cited_family_set_sha256` is the hash of `families`; no pair repeats | Replay, at LR-039 |
| A family marked `adopted` names an active adoption of that observation and family whose use is `w9-use:manuscript-claims/<the root's key>`. One marked `unadopted` names none | Replay, at LR-039 |
| `supersedes_status_ref` names the root's current status, or is null when there is none | Replay, at LR-039 |
| The `record_id` is the derived one (§5.6) | Replay, at LR-039 |
| `families` is exactly the extractor's cited-family set, with no blocker entry. When the reviewer's set differs from the extractor's, `families` is still the extractor's, and the two hashes record the difference | Preparer, at LR-039. Replay cannot run the extractor (review m-5) |
| The root's current status exists; the two derivation hashes are equal; every cited adoption is still active | Replay, at LR-054 |
| The status's `extractor_output_sha256` equals a fresh run over the mapping's inventory | Preparer, at LR-054 (§10.5) |
| **Not the transition's producer** (W9 §12.1): the current status's `derivation.reviewer_actor_id` and its submitter are none of the ownership proposal's creator, the mapping's `analyst_actor_id`, and the `observer_actor_id` of the inventory that mapping names | Replay, at LR-054. At LR-039 the transition does not exist yet (review M-9) |

W9-T17's first two clauses are the sixth and seventh rows: a status that omits a family in the set is refused at
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
- `ars legacy cited-families --root <root id> [--reviewer-sha256 <hash>]`: runs the extractor at the binding's
  `git_head` and prints its output object and hash. With the reviewer's hash it also prints the derived status
  record ID that Stephen's grant names (§5.6). It writes nothing.

**Owner point M: the boundary.** P-085's boundary is "WP9.4's code under `research_system/legacy/`, its
runtime-binding rows, tests and docs". The binding rows are in `research_system/schema_registry.py`, so that file is
inside it already (re-review R-i4). Two files are not: `research_system/cli.py`, for these verbs, and
`research_system/authority.py`, for WP9.4-2's two subject-kind entries (§5.6). WP9.3 had the same need, and Stephen
extended P-080's boundary by name (P-081 item 10, `03-decisions-and-open-questions.md:5167`). *Recommended:* the same
extension for P-085, to those two files. *The alternative* is no CLI verbs: the reviewer would then run the
extractor from a Python prompt, and the two bindings still need the authority file.

## 14. Bindings and D-4

- **WP9.4-1** adds no `SchemaBinding` row. The census stays 273 rows, `0cca0414…4712`, and the 06h manifest and the
  smoke test keep their blobs. The PR states that and its review checks it. If the code finds it needs a row, that is
  a stop (§18).
- **WP9.4-2** adds command rows for `CreateLegacyPaperRoot` and `RecordPaperCitationStatus`, with their authority
  entries (`research_system/authority.py:208-252` and `_SCOPED_COMMAND_SUBJECT_KINDS` at `:217`; §5.6). The expected
  census is 275 rows: both commands emit `E:` events only (§2.3). The code PR gives the exact row set, digest,
  manifest bytes and append-site classification, and Stephen re-accepts them at exact bytes in the merge-queue entry
  (06v D-4).
- Command-adding packages merge one at a time (06v §5). WP9.4-2 must not be in the queue with another one.

## 15. Tests

| Test | PR | Kind | Control |
|---|---|---|---|
| W9-T1 at LR-029 | 1 | unit | A `Done` status word in the source yields no adoption |
| W9-T6 at LR-029 | 1 | integration, scratch store | The source's bytes change after the proposal; resolution writes no event |
| W9-T8, legacy side | 1 | integration | `family_admissible` is false for an accepted, unadopted family, and for a task-input adoption asked about under another key; `resolve_adoption_ref` raises for an unknown adoption and returns the observed identity for a family adoption. The successor half is owner point J |
| W9-T9 | 1 | integration | Re-observe an adopted source: the same family with a new blob; the same family with the same blob; a disjoint family set with a new blob (M-1). All three suspend. Supersession and mismatch on forged ledgers |
| W9-T17, last clause | 1 | unit | §9's predicate, for unadopted, suspended and other-use; `legacy_content_matches` finds a byte copy, misses unrecorded bytes, and does not match two sources that both lack a Git blob. The binding test is WP9.7's (owner point E) |
| G5 for an adoption | 1 | unit and integration | An adoption with no review, with an unsatisfied derived review, or with another review ID is refused at LR-028 and at LR-029. `review_id_for` raises for an unlisted kind (M-2) |
| The analyst rule | 1 | unit | The analyst may request on their own adoption, discharge, mapping and ownership proposals; the inventory's observer may not request on it (M-3) |
| Fixture entries | both | unit | A resolution missing an unconditional fixture, naming an unlisted one, or differing from its proposal is refused; a claim-use adoption with no F-019 is refused; a Decision proposal whose fixture set differs from the request's applicable set is refused; a WP9.3 row with a fourth ref is still refused (owner point L; R-M5) |
| LR-023's refusals | 1 | unit | A claim use with an open finding; a task-input use whose qualifier set differs from the observation's; a target-free use; `P01-A` accepted and `p01-a` refused as a paper key; a whole-file adoption of a `.json` source; a whole-file adoption of a tracked, unrestricted text file; an adoption suspended at birth (M-6, M-7, m-12, R-m2) |
| LR-024, LR-025 | 1 | integration | Under owner point B: an eligibility proposal is accepted before any review exists; one with seven refs, another grade or a stale subject hash is refused; LR-025 with a record event is refused (R-M4) |
| LR-026, LR-027 | 1 | integration | A request before the eligibility Decision resolves; a request naming another session; **a verdict from a session other than the eligible one**; **a verdict from the analyst's session is refused and one from the eligible session passes** (C-m1); a verdict whose profile or `<family>@<version>` differs; W9-C20 (R-M4) |
| LR-025's preparer | 1 | unit | The eligibility resolution prepares one `DecisionResolved` event and no record event (C-i1) |
| LR-034's negatives | 1 | integration, at the preparer | An unknown `item_id`; a registered artefact that is not `accepted_for_scope`; **a byte copy of a recorded legacy observation as the successor result** (R-M2); the producer as reviewer; an open-item blob that is not the file's |
| The CreateTask and AmendTask guard | WP9.7 | integration | Inherited by WP9.7 under owner point J: a wrong-key Task; an amendment adding a `w9-adoption:` ref; an amendment changing the `w9-use-key` alias (C-m4) |
| Grant subjects | both | integration | A grant on another record ID is refused for each of the five proposal rows; for LR-039, a status whose `record_id` is not the derived one is refused, and a grant on the derived ID admits no other cited-family set (owner point N) |
| W9-T5 | 2 | unit | `successor_owned → legacy_owned` fails the schema; `legacy_owned → closed_reference` is refused at LR-050 |
| W9-T6 at LR-044, LR-054, LR-055 | 2 | integration | A row's blob changes inside the window; at LR-054, a file added under the root after LR-044 (CodeRabbit, on revision 4) |
| W9-T17 at LR-044 | 2 | integration | An inventory that omits a tracked file under the root is refused (m-9) |
| W9-T17 at LR-039, LR-054 | 2 | integration | A status omitting a family; a draft citing a result outside the set; unequal derivation hashes; the citation reviewer as the ownership proposal's creator, the mapping's analyst or the inventory's observer (M-9); **a status derived from another inventory than the mapping's** |
| LR-054's other refusals | 2 | forged ledger and preparer | A superseded mapping or inventory (R-m3); an open item feeding the paper with no discharge, at the preparer (R-m1) |
| The extractor | 2 | unit, on fixture bytes | A path literal; a JSON-escaped Windows path; a unique basename; an ambiguous basename, with and without a disambiguation entry; an unregistered `results/` file and a bare unregistered `new_result.json`, each a blocker; a directory and a trailing-`/` path as `not_a_file`; an ordinary word that is not a candidate; a LaTeX-wrapped path `\texttt{results/…/ph_L5000.json}` as a cited file (R4-m3); a registered result whose name holds `YYYYMMDD` as a cited file; a partial path that is a suffix of one registered path as cited and of two as `ambiguous`; `results/x_{survey}/a.json` giving `results/x_` as `not_a_file` and `/a.json` as cited when `results/x_bhps/a.json` alone is registered, and as `ambiguous` when `results/x_usoc/a.json` is registered too (R4-m4, R5-m1); `x/a.json` not matched as a suffix of `results/xx/a.json` (R5-i4); two tokens with one basename in one citing file, resolved by two token-keyed rows; `table1_effects_{date_suffix}.json`, `level1_comparison_YYYYMMDD.json` and a lone `.json` as `not_a_file` (C-M2); a disambiguation row giving two paths for one basename in one citing file (C-m2); `notes/data.json` with `results/x/data.json` registered as `ambiguous`, and cleared by a `not_a_result` row; a PNG as `not_text`; a cited `.npy` projected as `whole_file`; a citation outside `drafts/` reported and not hashed; the backtick and table-pipe separators (M-5, R-M6) |
| W9-T21, graph half | 2 | unit | A cycle among root, inventory, mapping and transition; a P01-A mapping used to transition the P01-B registration (M-10) |
| The root registration | 2 | unit | Under K's option 1: a member observation under the root is accepted and closes nothing at LR-020; two member observations do not mark each other stale; **two members with one blob are both accepted, and a batch holding both passes `check_acceptance`** (C-M1); observing an unchanged member `b.npy` leaves a whole-file adoption of member `a.npy` active; an observation of the root directory itself is refused at LR-015 (m-4, R-M7); **a member is read by its `member_path`, a member path outside the root or not a regular file is refused, and `member_path` on a non-root registration is refused** (R4-M1); the acceptance re-read reads a member by its recorded path. For a non-root registration each of the five readings is today's check, **including two observations of one `legacy_decision_log_entry` registration with two paths, where the later still marks the earlier stale** (R4-m1) |
| The root registration's identity | 2 | integration | Under owner point O: a `legacy_manuscript_root` registration records a directory identity, in the reader's `fstat` encoding, at LR-003 and re-reads it unchanged at LR-005 (R4-M2, R5-i2); a root path that resolves to a regular file, a junction or another reparse point is refused at LR-003 and at LR-005's re-read (R5-i3); a root registration of a kind other than `git_tracked` is refused at LR-003, and a member with a D-9 suffix is refused at LR-015 (R5-m2) |
| Prefix collisions | 2 | unit and forged ledger | With a root registration recorded, a registration of `papers/P01-A-JRSSA/_project.md` under any role is refused at LR-003, in replay and at the preparer; with that file registration recorded, a root registration over it is refused; each also with the other side in an open proposal. Controls: `papers/P01-A-JRSSA-old/x.md` is not under the root (component boundary), and every non-root registration pair keeps today's equality check (R5-M1) |
| W9-C11, W9-C20 to W9-C25 | both | integration | Per row, as the annex binds them |
| The route partition | both | unit | The routed and deferred counts after each PR; a deferred row is still refused before append |
| The import seam | 1 | unit | §9's allowlist (m-2) |
| D-4 identities | 1 | contract | The census, manifest and tree IDs are unchanged |

No test reads a file under `papers/`. The extractor's tests use fixture bytes that reproduce the citation forms the
two reviews found in the drafts.

Both PRs report their added test runtime. The test-runtime escalation is still open with Stephen (P-084, "Not decided
here"), and WP9.3-2 added about 4.4 minutes.

## 16. Research assurance

**Lanes.** `output_provenance` (every row) and `paper_claim` (LR-039, LR-054, §9's predicate and the content rule of
§4.2). No topology, null-model, statistical or representation logic is touched: the package computes no research
number.

**Governing texts.** W9 §§3.1, 4.2, 4.5, 8.2, 8.3, 9, 12.1, 12.3 and 17; the owner annex rows LR-023 to LR-055;
P-072, P-073, P-081 and P-085; 06v §2.7, §2.8 and D-3.

**Machine-checkable, with an enforcement artifact:** every replay and preparer check in §5 to §8, §10 and §11.3,
each with a negative control in §15; the D-4 identities.

**Human-review only.** Each line gives what the reviewer or Stephen is asked, and why no check exists.

| Condition | Source | The question | Why not checked |
|---|---|---|---|
| The eligible session's family differs from the producer's; its role profile declares the lane's capability; its context is independent | Annex LR-024 (a) to (c); W9 §11.2 | Does the operator's record show each? | Replay sees attested strings (§5.5) |
| Which conditional fixtures apply (F-015, F-038) | W9 §12.3 | Is the family statistical? Does it use the TDA pack's lanes? | Not decidable from the record. The applicable set is fixed before the verdict and approved with it (§5.4) |
| A discharge's reviewer is not the result's producer; its result is accepted and is not a legacy copy; its item is in the open-item list, on a replayed ledger | G3; §8 | — | Replay has no artefact state and cannot read the file. The preparer checks each |
| The predicate a discharge's result is accepted under fits the discharge | §4.4 | Is this result evidence of the kind the item needs? | Any predicate is admitted |
| Every open item feeding the paper is discharged, on a replayed ledger | W9 §12.1 | — | Replay cannot read the open-item file. The preparer checks it (§10.5) |
| W0-D2 Stage 2 scope covers the root's rows | W9 §4.5; §12.1 | Does the Stage 2 decision name them? | The ownership record has no field |
| The audit verdicts and the §6.2 HOLD are carried as qualifiers | W9 §12.1 | Does the root's `qualifiers` list hold each? | No accepted list of them exists to compare with |
| For any rung-4/5 claim the paper keeps, the A1 fork is decided and the calibration has run | W9 §12.1 | Which claims are kept, and where is each calibration result? | A claim is not a W9 record |
| The W9-D7 manuscript route | W9 §4.5; §12.2 | Has Gate 9's review capability been met for this paper? | Outside W9 |
| Stephen's batch approval | D-G6-4 limb 2 | — | It is the resolving Decision itself |
| The reviewer's citation derivation is independent of the extractor, and covers indirect, composed and stem citations | D-3; §11.1 | Was it made before `cited-families` was run? Does it read the artifact map? | Only its hash is checked |
| A disambiguation entry names the result the draft means | §11.1 | Does the draft's context support it? | Stephen's acceptance, as for a membership table |
| The content of the open-item list | W0-D1 | — | Stephen's. Its blob is bound (§8) |
| A legacy result re-serialized into an artefact, or copied from bytes that were never observed | §4.2 | Does the artefact's review trace its inputs? | Content identity catches recorded or current bytes only |
| A registered file changed and not re-observed | W9 §4.2 item 3 | — | The projection reads recorded observations. WP9.5's detectors and WP9.7's use-time comparison cover it (§7) |
| Use keys name a real Task or claim | §6.2 | Does the key match the Task's alias or the claim candidate? | Attested strings |

Passing these tests does not show that any real adoption is sound. That is the adoption's own review. The
re-review's scratch-store run is the example to keep in mind: every step passed, and the passes were the defect.

## 17. Claims for review

Revision 3's eleven claims, as the confirming re-review disposed of them: 1, 3, 5, 8, 9, 10 and 11 hold; 2 holds for
direct readers (C-m3); 4 holds in part (C-m1, C-i1); 6 holds for P01-B and fails for P01-A (C-M2); 7 holds in its
second half and fails in its first (C-M1). Revision 4 restates 6 and 7 and adds 12 to 14. The others stand as
revision 3 wrote them.

1. **The path, as described** (R-M1): only the claim predicate binds a `claim_promotion` Decision, and §4.2, §4.4
   and §8 say nothing that contradicts `service.py:4901-4902`.
2. **The content rule's sites** (R-M2): with the rule at LR-030 and LR-034, no byte copy of a recorded legacy
   observation can discharge an open item. With it also at `SetArtefactUseAuthority`, no direct reader of
   `use_authority` can be reached by one. Are there readers the note has not named?
3. **The stale rule, over recorded observations** (R-M3): the first review's case suspends, and §7 and §16 state the
   unobserved-edit limit without overclaiming.
4. **The eligibility encoding** (R-M4): walk annex LR-024 to LR-027 against §5.5 again. LR-024 passes before any
   review exists; a verdict from a session other than the eligible one is refused; every new ref has a preparer
   field.
5. **Fixture applicability** (R-M5): the applicable set is fixed in the review request, so no fixture can be dropped
   after the verdict; F-019 is required for both claim uses. Is reading "proposed by the reviewer" as "approved by
   the reviewer before the verdict" a fair reading of W9 §12.3, or a departure Stephen must record?
6. **The extractor on the real roots** (R-M6, C-M2): with revision 4's `not_a_file` rule for templates and empty
   stems, P01-A's drafts leave exactly the four ambiguous names and P01-B's none, and no candidate falls in no class.
   Does the template test misclass a real citation as `not_a_file`, so that a cited file is dropped from the set?
7. **K's option 1** (R-M7, C-M1, R4-M1, R4-m1): the five readings are the only changes to WP9.3's checks it needs,
   each is gated on the role, and no other site, in replay, the preparers or the reader, keys on registration where
   option 1 needs a path. `check_change_list` keys on registration and refuses too much only (R4-i2).
8. **G4** (R-M8): the derived status ID binds all three hashes, as the observation's derived ID binds its subject,
   and no WP9.4 row is left with a subject the table of §5.6 does not cover.
9. **The use-key carrier** (R-M9): a Task alias can carry the key, and J's binding test can now express "wrong
   use".
10. **LR-054's inventory binding:** re-running the extractor over the mapped inventory at the preparer leaves no way
    to transition under an inventory the status was not derived from.
11. **Nothing regressed:** the 25 first-round findings the re-review closed are still closed in revision 3.
12. **The eligible session** (C-m1): with the analyst's session and the eligible session stored apart, LR-027
    refuses the analyst's session and any session but the eligible one, and admits the eligible one.
13. **The consumer kinds** (C-m3, R4-m2): with the at-use rule on claim, manuscript, result and review evidence, no
    consumer with a production caller resolves a legacy copy that no active adoption admits at the time of use. With
    the promotion-site rule alone, result and review evidence are closed at promotion only.
14. **AmendTask** (C-m4): no command other than CreateTask and AmendTask can set a Task's `aliases` or
    `source_import_refs`.
15. **The root registration** (R4-M2): a directory handle-bound read under W11 §7.3 can produce every field the
    registration schema's physical identity requires, and nothing else on LR-003's or LR-005's route assumes a file.
    Revision 6 adds the converse found by the review of revision 5 (R5-M1): replay's LR-003 check was too weak for a
    directory, and the prefix-collision check of §10.2 is the only change it needs. Is any other site that compares
    registrations (for example LR-005's re-read, LR-020's closure or LR-054's subject check) also equality-only where
    a root needs a prefix?
16. **The extractor's order** (R4-m3, R4-m4, CodeRabbit): with braces as separators and cited files tested first, no
    candidate falls in no class on fixtures of every form §11.1 lists, and the real roots still give four ambiguous
    names in P01-A's drafts and none in P01-B's.

## 18. Stop rules

06v §8 applies. In addition, the code stops and returns Partial when:
- WP9.4-1 needs a runtime-binding row or a schema change;
- a WP9.4 row needs an edit outside the boundary as Stephen sets it under owner point M;
- a test needs a real paper file, a vault file or restricted bytes;
- a positive path for LR-035 or LR-054 can run without a passed LR-022;
- WP9.4-2's code reaches a member file's observation or registration before owner point K is decided;
- the extractor, run on fixture copies of the citation forms in §11.1, leaves a candidate in no class, or blocks on
  a template that no disambiguation row can clear;
- another site, beyond the five readings of §10.2, keys on registration where K's option 1 needs a path;
- a site other than LR-003's conflict check needs a prefix comparison for a root registration (§17 claim 15).

## 19. Owner points

| # | Point | Recommended | Alternative |
|---|---|---|---|
| A | The split | Two PRs: WP9.4-1 (adoption and discharge, no D-4), then WP9.4-2 (the full path, with D-4) (§2.4) | One PR |
| B | LR-024 and LR-025 | Move them from WP9.7 to WP9.4-1, with §5.5's encoding and the kind `migration_authority` (§2.2) | Leave them with WP9.7; adoption stops at LR-023 until then |
| C | The adoption's review ID | Derive it, behind `review_id_for`; a reading of P-072 item 1, LR-023 and G5 (§5.2) | Add `reviewer_ref` by a catalogue revision |
| D | LR-021 and LR-022 | Leave them with WP9.7. LR-035 and LR-054 refuse on every store until then (§2.2) | Move them, with the metric helper |
| E | U-6, the W5 clause of W9-T17 | WP9.4 builds the two read functions and binds the content rule at its own discharge. WP9.7 binds both at use for claim, manuscript, result and review evidence and, **as P-086 item 5 chose**, at `SetArtefactUseAuthority` as well, which closes the direct readers of `use_authority`; compares current blobs as well; and inherits a binding test per consumer predicate (§4.2) | WP9.7 refuses every artefact whose bytes match a legacy observation |
| F | The intended use | Three forms, each naming its target; a task-input key is the Task's `w9-use-key` alias (§6.2) | Target-free values, recorded as widening W9 §9 item 2; or a free string |
| G | Qualifiers and the W5 consequence | Refuse a claim use with an open finding at LR-023; task inputs keep their findings (§6.3) | Record and mark blocked, as an amendment to LR-023 |
| H | The open-item list | A committed `w9-legacy-open-items/1` file with `feeds_papers`, its blob bound in Stephen's Decision, read at the preparer (§8) | Leave the list to the discharge's reviewer |
| I | The citation comparison | A defined tokenizer; four classes, one non-blocking, with templates and empty stems non-blocking; whole-file results projected; a disambiguation file whose rows give a set of paths; the drafts block and the rest of the root is reported; no artifact map in the extractor (§11.1) | The whole root as the blocking set, as a departure from W9 §12.1; or the artifact map, once machine-readable |
| J | The W9-T8 CreateTask and AmendTask guard | Move it to WP9.7 by decision, with a binding test that includes a wrong-key Task and two amendments (§4.1) | Widen P-085's boundary to `service.py` |
| K | A paper root's member files | Observe members under the root's registration, with five recorded readings of WP9.3's checks (four in replay, one in the preparer and reader), each gated on the role, and no catalogue revision (§10.2) | A member role by catalogue revision; or an inventory with no per-file observation, also by revision |
| L | Fixture refs | `w9-fixture:` entries in the resolving Decision; the applicable set fixed in the review request; F-019 required for claim uses; recorded as an extension of P-084 item 3's i-3 reading (§5.4) | A recorded departure from P-072 item 4 and W9 §12.3 |
| M | The boundary | Extend P-085's to `cli.py` and `authority.py`, as P-081 item 10 did (§13) | No CLI verbs |
| N | G4 for WP9.4's rows | Extend P-081 item 12 to the five proposal rows and to LR-024; derive LR-039's record ID from its three hashes (§5.6) | LR-039's grant binds the record ID only |
| O | The root registration's identity | For `legacy_manuscript_root` only, LR-003 and LR-005 read the directory handle-bound under W11 §7.3 and record its identity in the existing fields; a recorded reading of annex LR-003 and LR-005, built in WP9.4-2 (§10.2). Revision 6 adds, within O's decided scope: LR-003 refuses a resolved-prefix collision with a root (R5-M1), and a root is `git_tracked` (R5-m2) | Register the root under a file that stands for it, by catalogue revision |

**What each asks of Stephen.**
- A, C, D, G, J and M: confirm a recommendation both reviews support.
- B, F, H and N: confirm, with the encodings the revisions added.
- E: confirm the split, with the at-use rule on four consumer kinds, and choose whether WP9.7 also applies the
  content rule at promotion.
- I: choose the blocking scope. The note recommends the drafts, which is W9 §12.1's text.
- K: choose among three options. The note recommends the one that changes no accepted bytes, at the cost of five
  recorded readings of WP9.3's checks.
- O: confirm the directory reading of LR-003 and LR-005. It is needed under every option of K.
- L: confirm the encoding, and record it as an extension of P-084 item 3's i-3 reading, or as a departure from W9
  §12.3 if you decline the extension.

The re-review notes that B, E, F, L and N are what WP9.4-1's code waits for, and that I and K touch WP9.4-2 only. The
confirming re-review judged B, E, F, L and N decidable on revision 3, and I and K once C-M2 and C-M1 are folded in,
which revision 4 does. It disagreed with none of the fourteen points.

## 20. Change log: revision 1 to revision 2 (the first review)

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
| M-13 | **Raised as owner point K.** *Qualified:* the review counts "at least three batches" for 55 files. That holds. Annex LR-016 makes a later batch depend on a passed LR-022, as LR-054 does, so it adds no new dependency. The code refuses every later batch today (`replay/reducers.py:542`), and the admitting branch is WP9.7's carry (re-review R-i3) | §10.2 |
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

Revision 1's §17 claims, as the first review disposed of them: 1 and 3 held; 2 and 7 failed; 4, 5 and 6 held in
part. Revision 2 replaced them with twelve, and §17 says how the re-review disposed of those.

## 21. Change log: revision 2 to revision 3 (the re-review and CodeRabbit)

The author re-read the code and the accepted texts behind every finding at `4629d1fd` and re-ran the re-review's 28
probes (28 passed). No finding is disputed. Three rows carry a note on how far the fix goes.

**The first round's partly closed findings.**

| Finding | Re-review | Now |
|---|---|---|
| B-1 | Partly closed: the path's description was still wrong for the manuscript predicate | Fixed with R-M1 to R-M3 (§4.2) |
| M-5 | Partly closed: silent drops, and an undefined token | Fixed with R-M6 (§11.1) |
| M-7 | Partly closed: the task-input key had no carrier | Fixed with R-M9 (§6.2) |
| M-12 | Partly closed: no session binding, no LR-024 branch, no payload | Fixed with R-M4 (§5.5) |
| m-6 | Partly closed: U-10's cost was overstated | Fixed with R-M1 (§4.4) |

**The re-review's findings.**

| Finding | Disposition | Where |
|---|---|---|
| R-M1 | **Fixed.** Only the claim predicate binds a `claim_promotion` Decision. Claim 12 is withdrawn. WP9.7's inherited test has one artefact per predicate | §4.2, §4.4, §8, §17 claim 1 |
| R-M2 | **Fixed.** The content rule is bound at LR-030 and LR-034. The promotion site is put to Stephen inside owner point E | §4.2, §8, §15 |
| R-M3 | **Fixed.** The limit is stated; WP9.7 compares current blobs; `resolve_adoption_ref` returns the observed identity for every adoption; claim 3 is restated | §4.2, §4.3, §7, §9, §16, §17 claim 3 |
| R-M4 | **Fixed.** The eligible session in the request and at the verdict; `<family>@<version>`; LR-024's own branch with no review; the preparer fields and the row discriminator; the lapse rule | §5.1, §5.2, §5.5, §6.5, §15 |
| R-M5 | **Fixed, and kept inside owner point L.** F-019 is required for claim uses. The applicable set is fixed in the review request. *Note:* this is the reviewer approving a list, not proposing one, and §5.4 puts that reading to Stephen | §5.4, §15, §16 |
| R-M6 | **Fixed.** The tokenizer, the `not_a_file` class, whole-file projection, bare unregistered names as blockers, the cost table, and drafts as the blocking scope. *Note:* a disambiguation file is added so that P01-A's four ambiguous names have a route other than editing the drafts; the re-review did not ask for it. The author did not re-run the rule | §11.1, §11.2, §15, §17 claim 6 |
| R-M7 | **Fixed.** The W9 §3.1 reading is K's first option, and m-4's refusal is conditional on K. *Note:* the note adds a third reading the re-review did not list, the per-path stale comparison, without which member observations would mark each other stale (`replay/reducers.py:1403-1414`) | §10.2, §10.3, §15, §17 claim 7 |
| R-M8 | **Raised as owner point N,** with a new §5.6 | §5.6, §13, §14, §15 |
| R-M9 | **Fixed.** The carrier is a Task alias in the namespace `w9-use-key`, and J's test includes a wrong-key Task | §4.1, §6.2, §15 |
| R-m1 | **Fixed.** The `feeds_papers` check is the preparer's, with a §16 row | §8, §10.5, §16 |
| R-m2 | **Fixed.** The whole-file route is for a source with no JSON family | §6.1, §15 |
| R-m3 | **Fixed.** LR-054 requires the mapping and inventory not superseded | §10.5, §15 |
| R-m4 | **Fixed.** The assurance package's lack of a hook and the production callers are recorded | §4.2 |
| R-m5 | **Fixed.** The artifact map and the in-root claim trace are cited | §11.1 |
| R-i1 | Noted. Claim 7 held | §5.4 |
| R-i2 | **Fixed.** The O-33 text is cited at its block | §3 row 3 |
| R-i3 | **Fixed.** M-13's qualification is reworded | §10.2, §20 |
| R-i4 | **Fixed.** Owner point M names `cli.py` and `authority.py` | §13 |

**CodeRabbit's threads on revision 2.**

| Thread | Disposition | Where |
|---|---|---|
| The open-item blob has no place in the Decision-ref encoding | **Fixed.** §5.4 lists it as the third group, for LR-033 and LR-053 | §5.4, §8 |
| The key pattern rejects `P01-A` | **Fixed.** The lower-case pattern is for task and claim keys only | §6.2 |
| Non-UTF-8 inventory files | **Fixed.** `not_text`: listed, not scanned, not blocking | §11.1, §15 |
| An unregistered result cited by bare basename is dropped | **Fixed,** with R-M6 | §11.1, §15 |
| The citation status is not bound to the mapped inventory | **Fixed by another route.** The suggested `source_inventory_ref` field cannot be added to a closed, accepted schema without a catalogue revision. LR-054's preparer re-runs the extractor over the mapped inventory instead | §10.5, §11.3, §15 |

CodeRabbit's three threads on revision 1 are outdated. Two were fixed in revision 2 (the membership-table rule,
since replaced by R-m2's; the stale rule, M-1), and the third is R-m1.

The confirming re-review of revision 3 followed. §22 records its findings.

## 22. Change log: revision 3 to revision 4 (the confirming re-review)

The author re-read the code behind C-M1 and C-M2 at `ede231e5` (`replay/reducers.py:550-559`, `:614-616`, `:629`;
`drafts/sections/compute_table1_effects.py:205`) and the cited lines of the Minor and Info findings. No finding is
disputed. Revision 4 is limited to the sections the findings name. CodeRabbit's four threads on revision 3 also
touch §6.1, §7 and §9, and one of its comments is not taken (below).

| Finding | Disposition | Where |
|---|---|---|
| C-M1 | **Fixed.** A fourth reading, for `_batch_rules`; reading 2 is made in `_whole_file`, which `check_acceptance` and `derive_ownership` both read; the cost line restated; claim 7 restated; a §15 control on two members with one blob | §10.2, §15, §17 claim 7, §18, §19 K |
| C-M2 | **Fixed.** `not_a_file` covers templates and empty stems, tested before `unregistered`; "What still blocks" restated from the confirmation's run | §11.1, §15, §17 claim 6, §18, §19 I |
| C-m1 | **Fixed.** The eligible session is stored apart from the excluded sessions; LR-027 refuses the analyst's session and requires the eligible one | §5.3, §5.5, §15, §17 claim 12 |
| C-m2 | **Fixed.** A disambiguation row gives a sorted, non-empty set of paths, or `not_a_result` (a CodeRabbit thread on revision 3) | §11.1, §15, §19 I |
| C-m3 | **Fixed.** All five consumer kinds named; result and review evidence are closed only by the promotion-site rule, and declining it leaves them open | §4.2, §17 claim 13, §19 E |
| C-m4 | **Fixed.** The guard covers AmendTask, with two amendment cases in its binding test | §4.1, §15, §17 claim 14, §19 J |
| C-i1 | **Fixed.** LR-025's preparer has a record-less branch | §5.5, §15 |
| C-i2 | **Fixed.** The whole-root counts are 24 and 8 | §11.1 |
| C-i3 | **Fixed.** N names LR-024's grant reading | §5.6, §19 N |
| C-i4 | Noted. Claim 10 holds as equality of the extractor's output, which is what "derived from" means | §17 |
| C-i5 | **Fixed.** "the resolution row's list" | §5.4 |

**CodeRabbit's review of revision 3** (`ede231e5`, PR #437).

| Thread | Disposition | Where |
|---|---|---|
| Whole-file adoption admits a tracked, unrestricted text file | **Fixed.** The route needs a binary or restricted input, as W9 §9 item 1 says | §6.1, §15 |
| `legacy_content_matches` could match two absent blobs | **Fixed.** An absent value never matches | §9, §15 |
| Under K's option 1, observing one member suspends a whole-file adoption of another | **Fixed.** The whole-file cause compares the source path for a root registration | §7, §15 |
| A path elsewhere ending in a registered basename falls in no class | **Fixed.** It is `ambiguous`, and the disambiguation file can map it or mark it `not_a_result` | §11.1, §15 |
| "Require an adoption for every cited family" (outside the diff, marked unverified by CodeRabbit) | **Not taken.** W9 §12.1 requires each cited family to be "either adopted … or marked unadopted", and annex LR-054 says "every cited family adopted or marked unadopted". An unadopted family is allowed in the status by design; what W9 forbids is a claim resting on it, which is the W5 clause of W9-T17 (§4.2, owner point E). Requiring an adoption for every family would refuse a transition the accepted texts admit | — |

The confirmation's reading of owner point L (§2, addition 3) is taken: §5.4 no longer claims compliance with W9
§12.3, and asks Stephen to record the encoding as an extension of P-084 item 3's i-3.

A review of revision 4, narrow to §10.2 and §11.1, followed. §23 records its findings.

## 23. Change log: revision 4 to revision 5 (the review of revision 4, and CodeRabbit)

The author re-read the code behind R4-M1 and R4-M2 at `7bd7d6a6` (`research_system/legacy/reader.py:275-285`;
`legacy/preparers.py:151-172`, `:332`, `:541-542`, `:584-596`; W11 §7.2) and the cited lines of the Minor and Info
findings, and checked CodeRabbit's four comments against the note and the tracked tree. No finding is disputed. The
review's extractor run at `7bd7d6a6` gave P01-A's drafts exactly four ambiguous names and P01-B's none; revision 5's
§11.1 changes were not re-run on the roots.

| Finding | Disposition | Where |
|---|---|---|
| R4-M1 | **Fixed.** A fifth reading: the observation preparer and reader read a member by a `member_path` payload key, admitted for a root registration only; the acceptance re-read reads the recorded path. No accepted byte changes | §10.2 item 5, §15, §17 claim 7, §19 K |
| R4-M2 | **Raised as owner point O.** A root registration's identity is a directory identity read under W11 §7.3, in the existing schema fields; a recorded reading of LR-003 and LR-005 | §10.2, §15, §17 claim 15, §19 O |
| R4-m1 | **Fixed.** Each reading is gated on the role; the false reason is withdrawn; the Computational-Log case has a control | §10.2, §15 |
| R4-m2 | **Fixed.** The at-use rule is recommended for result and review evidence too; the promotion-site rule is described as closing them at promotion only | §4.2, §17 claim 13, §19 E |
| R4-m3 | **Fixed.** `{` and `}` are separators | §11.1, §15 |
| R4-m4 | **Fixed.** A partial path is cited or ambiguous; the template test reads every component | §11.1, §15 |
| R4-i1 | **Fixed.** `methods/brief.py:27-28` named; the sensitive-sidecar resolver has no caller | §4.2 |
| R4-i2 | **Noted** as refusing too much only | §10.2 |
| R4-i3 | **Fixed.** §5.3 separates the two exclusions; §5.6's LR-024 cell reordered | §5.3, §5.6 |
| R4-i4 | **Fixed.** A cited non-JSON text result can only be marked unadopted | §11.1 item 4 |
| R4-i5 | **Fixed.** Replay checks "strictly under, not ending in `/`"; the preparer checks "regular file" | §10.2 |

**CodeRabbit's review of revision 4** (`7bd7d6a6`, PR #437).

| Comment | Disposition | Where |
|---|---|---|
| Result and review consumers need a check after promotion (line 241) | **Fixed,** with R4-m2 | §4.2 |
| Check exact registered paths before the template test (line 945) | **Fixed.** Cited files are tested first | §11.1, §15 |
| Key disambiguation by the complete token (line 970) | **Fixed** | §11.1, §15 |
| Relist the root before the ownership transition (review body, line 894, marked unverified) | **Fixed.** LR-054's window re-lists the root | §10.5, §15 |

Stephen decides the owner points next, A to O. The review of revision 4 judged B, E, F, L and N decidable on
revision 4, and K once R4-M1 and R4-M2 are folded in, which revision 5 does with owner point O.

## 24. Change log: revision 5 to revision 6 (the review of revision 5)

Stephen decided owner points A to O at revision 5 (P-086). The review of revision 5 (`3e7846b2`) found no
disagreement with any of them and placed every finding inside a decided owner point's scope, so revision 6 changes no
owner point. The review judged that none of its findings blocks WP9.4-1's code, and its plan put them in WP9.4-2's
note. Stephen asked for them folded in now, so that WP9.4-2 inherits one note. The author re-read
`_registration_conflicts` (`replay/reducers.py:401-420`), `_physical_identity` (`legacy/reader.py:124-134`) and
`LegacyReader.read`'s source kinds (`:317-325`) at `53ac0d64`. Two of the review's statements were narrowed:
`_registration_conflicts` applies no case-folding of its own, and it reads open proposals, not a batch.

| Finding | Disposition | Where |
|---|---|---|
| R5-M1 | **Fixed.** LR-003 refuses a resolved-prefix collision with a `legacy_manuscript_root` registration, in either direction, against recorded registrations and open proposals, at a path-component boundary. Option 1's "no member has a registration" becomes a replay invariant | §10.2 (O), §15, §17 claim 15, §18, §19 O |
| R5-m1 | **Fixed.** A brace placeholder splits a templated path; the parts are `not_a_file` and a partial path. `{` and `}` leave the `not_a_file` row. §15's fixture and §18's stop rule are restated | §11.1 items 1 and 3, §15, §18 |
| R5-m2 | **Fixed.** A root registration is `git_tracked`, refused otherwise at LR-003; a member with a D-9 suffix is refused at LR-015 | §10.2 item 5, §15, §19 O |
| R5-m3 | **Fixed.** The writer-guard carry is recorded in P-086's words | §3 row 16 |
| R5-i1 | **Fixed.** "Five recorded readings" throughout; the stop rule says "another site" | §10.2, §18 |
| R5-i2 | **Fixed.** The directory identity uses the reader's `fstat` encoding; `link_count` is recorded and not compared for a directory | §10.2 (O), §15 |
| R5-i3 | **Fixed.** O's negative control is a root path that resolves to a file, a junction or a reparse point | §10.2 (O), §15 |
| R5-i4 | **Fixed.** "A suffix of" is read at a path-component boundary, with a fixture | §11.1, §15 |
| R5-i5 | **Fixed.** §4.2 and §19 E state P-086 item 5's choice | §4.2, §19 E |

This revision has not been reviewed. Its changes add checks and wording inside decided scope, and add no owner point.
