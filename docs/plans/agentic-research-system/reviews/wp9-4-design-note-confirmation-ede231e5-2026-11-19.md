# WP9.4 design note confirmation at `ede231e5`: revision 3

**Date:** 2026-11-19<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md`, revision 3, at `ede231e5`
(`ede231e55bbc653580528870778e2224674da8b3`) on `claude/confident-volta-0e5dvm`, PR #437. I fetched the branch and ran
`git rev-parse`, which gave that commit. `git diff --stat 4629d1fd ede231e5` shows one file, the note (+595/-301).
`git diff --stat 4312dc63 ede231e5 -- research_system .research-system tools tests` is empty, so every code citation
reads the same at the note's base and at its head. The probe file asserts both diffs.<br>
**Re-review answered:** `reviews/wp9-4-design-note-re-review-4629d1fd-2026-11-16.md` and its probes, read with `git
show` from `origin/review/w9-wp9-4-note-re-review` at `a704d9b3` (not merged). The first review
(`reviews/wp9-4-design-note-review-3c10de9a-2026-11-16.md`, `a9935c0b`) was read for background only.<br>
**Reviewer:** a fresh session. It wrote none of WP9.2, WP9.3, the note, the first review or the re-review, and it did not
see the author's session.<br>
**Mode:** a narrow confirmation. Every `path:line` the report relies on was re-read at `ede231e5`.<br>
**Branch:** `review/w9-wp9-4-note-confirmation`, cut from `ede231e5`. Only this report and the probe file are added.<br>
**Known limit (P-058):** the author, the reviewers and this session are one model family. This is recorded as a limit,
not a finding.

## Verdict

**Confirm, with residuals.**

Revision 3 answers the re-review. Of its 18 findings, 16 are closed and 2 are partly closed. Of the five first-round
findings the re-review left partly closed, 4 are closed and 1 is partly closed. All five CodeRabbit threads are closed.
The scratch-store run and the code agree with the note's new description of the artefact path (R-M1). The content rule
now covers WP9.4's own discharge (R-M2). The stale rule's limit is stated without overclaiming (R-M3). G4 has an owner
point and a derived ID that binds all three hashes (R-M8). The use key has a carrier (R-M9).

The residuals are two Major findings and four Minor ones. None of them changes a recommendation.
- **C-M1 (K).** Option 1 needs a fourth reading of a WP9.3 check, not three. `_batch_rules` keys "the latest for its
  source and selector" by registration and selector. So for two members observed whole under the root registration, the
  earlier member can never be accepted. Claim 7 fails as stated.
- **C-M2 (I).** Claim 6 holds for P01-B and fails for P01-A. P01-A's drafts leave the four ambiguous names and a fifth
  blocker: a filename template, `table1_effects_{date_suffix}.json`, which the new bare-name rule classes as
  `unregistered`. No registration, disambiguation entry or new status can clear it.
- **Minors.** C-m1 is a conflict between §5.3 and §5.5 on the eligible session. C-m2: the disambiguation file is
  one-to-one, so it cannot record a single basename that means two results. C-m3: the at-use rule leaves three of the
  five consumer kinds unnamed. C-m4: J's guard needs AmendTask as well as CreateTask.

C-M1 and C-M2 touch WP9.4-2 only, in owner points K and I. They should be folded in before Stephen decides those two
points. That needs either a short revision 4 limited to §10.2 and §11.1, or WP9.4-2's own note, as the re-review's
revision plan already allows. The owner points WP9.4-1 waits for (B, E, F, L and N) can be decided on revision 3, with
C-m1, C-m3 and C-m4 as edits to carry.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | — |
| Major | 2 | C-M1, C-M2 |
| Minor | 4 | C-m1 to C-m4 |
| Info | 5 | C-i1 to C-i5 |

## 1. Closure of the re-review's findings

| Finding | Note's disposition (§21) | Confirmation | Evidence at `ede231e5` |
|---|---|---|---|
| R-M1 | Fixed | **Closed.** §4.2, §4.4 and §8 say that only the claim predicate binds a `claim_promotion` Decision, and nothing in the note says otherwise (the note's text was searched for `claim_promotion` and "claim level"). Claim 12 is withdrawn. WP9.7's test has one artefact per predicate | `service.py:4901-4902` returns `[]` for any predicate other than the claim predicate. Probe `test_claim1_holds_…`: a scratch-store byte copy is promoted for the manuscript predicate with no Decision, and `resolve_for_manuscript` (`rm03_brief_manuscript`) resolves it with `decision_id is None` |
| R-M2 | Fixed | **Closed.** LR-030's and LR-034's preparer columns refuse a result that `legacy_content_matches` finds, whatever its adoption status. §15's LR-034 row has the byte-copy control. E asks Stephen about the promotion site. Unnamed resolver consumers: C-m3 | §8 table; §4.2 items 2-3; `test_claim2_holds_the_direct_readers_…` (the four direct readers are `cli.py:2258`, `service.py:4618`, `discovery/spec.py:533` and `discovery/spec_result.py:248`) |
| R-M3 | Fixed | **Closed.** The limit is stated in §4.2, §7 and §16. WP9.7 compares current blobs (§4.2 item 4). §9's `resolve_adoption_ref` returns the observed identity for every adoption. Claim 3 is restated | `reducers.py:1404-1414`; `test_claim3_holds_…` (both) |
| R-M4 | Fixed | **Partly closed.** LR-024 has its own branch with no review, eight refs, the lapse rule and a payload. LR-026 carries the eligible session, and LR-027 requires equality. But §5.3 keeps "the reviewer's session differs from every session the request records" unchanged. `_session_refs` returns every session it parses, and `_check_verdict` refuses any verdict session in that list (`reducers.py:819`, `:893-895`). As written, the one session LR-027 requires is the one session that check refuses (C-m1). LR-025's preparer also has no record-less branch (C-i1) | `test_claim4_defect_the_unchanged_session_exclusion_…`, `test_claim4_holds_lr024_…`, `test_claim4_defect_the_resolution_preparer_…` |
| R-M5 | Fixed, kept in L | **Closed as an encoding.** F-019 is required for both claim uses. The applicable set is fixed in the request's `review_questions` (`reducers.py:813`; `preparers.py:380-396`) and repeated exactly in the Decision and the resolution. The reading is judged in §3 | `test_claim5_*` |
| R-M6 | Fixed | **Partly closed.** The tokenizer, `not_a_file`, whole-file projection, bare unregistered names, the cost table and drafts-only scope are all in §11.1. Run as written, P01-B records with no blocker. P01-A leaves a fifth, permanent blocker that the note does not expect, introduced by the new bare-name rule (C-M2) | §5, claim 6 |
| R-M7 | Fixed | **Closed as asked.** Option 1 is K's first option, with its cost, and m-4's refusal depends on K. The cost is incomplete, which is a new finding (C-M1) | §10.2; `reducers.py:485-491`, `:526-536`, `:1403-1414` |
| R-M8 | Raised as N | **Closed.** §5.6 covers every WP9.4 row (checked row by row), extends P-081 item 12 by name, and derives LR-039's ID from root, supersedes and the three hashes. LR-024's grant reading: C-i3 | `test_claim8_*`; `records.py:111-131`, `:157-202`; `authority.py:217` |
| R-M9 | Fixed | **Closed.** A Task alias in the namespace `w9-use-key` carries the key (`create_task.schema.json:42-49`; `$defs/alias` has a free `namespace`), and J's test has a wrong-key Task. AmendTask: C-m4 | `test_claim9_holds_…` |
| R-m1 | Fixed | **Closed.** §10.5 puts the `feeds_papers` check in the preparer column, §8 says every check that reads the file is the preparer's, and §16 has the row | §8, §10.5, §16 |
| R-m2 | Fixed | **Closed.** §6.1 uses "no JSON family: its registered path does not end in `.json`", for every source kind, which matches W9 §9 item 1 | design `09-…:487-490` |
| R-m3 | Fixed | **Closed.** §10.5 requires that neither the mapping nor its inventory is superseded at LR-054 | §10.5, §15 |
| R-m4 | Fixed | **Closed.** §4.2 records 06v §2.7's predicted site and `assurance/models.py:13`, and the production callers `methods/brief.py:31-33` and `:57` | verified |
| R-m5 | Fixed | **Closed.** The artifact map, the plan line and the in-root claim trace are cited. My run gives 15 backing files for `notes/claim-trace-escape-foo-2026-06.md`, as the note says | extractor run |
| R-i1 | Noted | **Closed** | §5.4 |
| R-i2 | Fixed | **Closed.** §3 row 3 cites the "Added 2026-11-08" block at `03-decisions-and-open-questions.md:5241-5250`, which is the O-33 text | verified |
| R-i3 | Fixed | **Closed.** §10.2's "Timing" says the later-batch branch is WP9.7's carry, and the code refuses every later batch (`reducers.py:542`) | verified |
| R-i4 | Fixed | **Closed.** M names `cli.py` and `authority.py` and treats `schema_registry.py` as inside P-085 already | P-085 Boundary |

**Totals:** 16 closed, 2 partly closed (R-M4, R-M6), 0 open.

### The five first-round findings left partly closed

| Finding | §21 says | Confirmation | Evidence |
|---|---|---|---|
| B-1 | Fixed with R-M1 to R-M3 | **Closed.** The path's description is right for every predicate, and the scratch-store run agrees | `test_claim1_holds_…` |
| M-5 | Fixed with R-M6 | **Closed.** No candidate is dropped silently, and the tokenizer is defined. The template blocker is a new defect introduced by the fix (C-M2), not M-5 | claim 6 |
| M-7 | Fixed with R-M9 | **Closed** | §6.2 |
| M-12 | Fixed with R-M4 | **Partly closed.** This is the same item as R-M4: the session binding is stated in §5.5 and contradicted by §5.3 (C-m1) | as R-M4 |
| m-6 | Fixed with R-M1 | **Closed.** U-10 is "accepted under any predicate" | §4.4, §8 |

The re-review's 28 probes, re-run unchanged at `ede231e5` (SHA-256 `dd16d9d3…43ea3a`, matching its §6), placed at their
own path, run and then removed: **28 passed.** Their defect probes describe the code, which has not changed.

## 2. The three additions §21 flags as not asked for

1. **The citation disambiguation file (§11.1 item 5): sound, with one defect.** It gives P01-A's four ambiguous names a
   route that does not need a draft edit. Its blob enters the extractor's output, so a change to it changes the hash.
   Stephen accepts it, as he accepts membership tables, and it adds one W9 paths addendum row. The defect is its key: one
   row per `(citing file path, basename)` names one registered path. `drafts/sections/compute_table1_effects.py` composes
   each of three ambiguous basenames twice, once under `trajectory_tda_integration/` and once under
   `trajectory_tda_bhps/` (lines 22-53), so that file means two results by one basename (C-m2). No family is lost on the
   real roots today, because other drafts cite both full paths, but the format cannot record what that file says. The
   file does not help with C-M2.
2. **The per-path stale comparison (§10.2, K option 1): sound and necessary, but not enough.** Without it, member
   observations make each other stale (`test_claim7_holds_members_with_different_blobs_…`). For every other registration
   it does not weaken the stale rule. LR-015's path rule gives such a registration one path, so grouping by path equals
   grouping by registration (`test_claim7_holds_a_per_path_stale_rule_equals_…`). The same per-registration key also sits
   in `_batch_rules`' "latest for its source and selector" rule, which the note does not list (C-M1).
3. **§5.4's reading of W9 §12.3: fair as an extension of an accepted reading, but not literal compliance. Stephen must
   record it either way.** W9 §12.3 says that applicability "is proposed by the item's independent reviewer and fixed by
   Stephen …, never by the item's producer". Under §5.4 the list is written by `migration_analyst`, who is the proposer,
   and so the producer, of the adoption, discharge, mapping and ownership proposals (annex LR-023, LR-030, LR-045, LR-050;
   §5.3: "the analyst's own proposals"). The approve-only verdict cannot carry a different set, because `conditions` is
   fixed to `[]`. Read literally, that is the producer proposing. But P-084 item 3's i-3 already accepted the same shape
   for LR-020: the analyst lists the fixtures, and the list is "fixed when the reviewer approves the hash and Stephen
   resolves on it". Revision 3 closes the gap the re-review found (the list was outside every reviewed object), because
   the list now precedes the verdict and cannot change after it. So I judge it a fair extension of P-084 i-3 to five more
   families. Stephen should record it as such under L, naming i-3, and not as plain compliance with §12.3. The
   alternative L offers, a recorded departure, is the honest name if he declines the extension.

## 3. CodeRabbit's five threads on revision 2

I read them on PR #437 through the GitHub API, all on `4629d1fd`.

| Thread | §21 | Confirmation |
|---|---|---|
| The open-item blob has no place in the Decision refs (line 354) | Fixed | **Closed.** §5.4 item 3 |
| The key pattern rejects `P01-A` (line 434) | Fixed | **Closed.** §6.2 applies the lower-case pattern to task and claim keys only |
| Non-UTF-8 inventory files (line 701) | Fixed | **Closed.** `not_text` is listed, not scanned and not blocking, and §15 has a PNG control. No tracked file in either root fails to decode |
| An unregistered result cited by bare basename is dropped (line 704) | Fixed | **Closed** as asked. The same rule creates C-M2 for bare templates |
| The citation status is not bound to the mapped inventory (line 767) | Fixed by another route | **Closed.** The schema is closed, and LR-054's preparer re-runs the extractor over the mapped inventory and compares hashes. The binding is equality of output, not of identity (C-i4) |

## 4. New findings

### C-M1 (Major). K's option 1 needs a fourth reading of WP9.3's checks: "the latest for its source and selector" refuses every member but the last

**Note section:** §10.2 ("That needs three readings of WP9.3's row checks"); §17 claim 7; §19 K.

**Evidence.**
- `_batch_rules` (`replay/reducers.py:550-559`) refuses an acceptance item when any later observation of the same
  registration has the same `_selector_key`. Under option 1, every member is observed under the root registration with
  the selector `{"selector_kind": "whole_file"}`, and that selector names no path. So every member observed before
  another one is "not the latest for its source and selector", and LR-016 and LR-020 refuse it. §10.3 needs every
  inventory row "in a recorded closed-reference acceptance", so the inventory can never be completed.
- The stale rule does not hide this. The two real members `papers/P01-A-JRSSA/drafts/.gitkeep` and `figures/.gitkeep`
  share blob `e69de29b…5391`, so neither is stale. Probe
  `test_claim7_defect_the_latest_for_source_and_selector_rule_refuses_an_earlier_member` shows the earlier one refused
  and the later one admitted.
- Reading 2 has to change `_whole_file` itself, not only LR-020's emission. `check_acceptance` (`:614-616`) also uses
  `_whole_file` and refuses "two whole-file items of one registration", so a batch of two members fails as well
  (`test_claim7_reading_two_is_real_…`).

**Failure scenario.** Stephen accepts K on "three readings". WP9.4-2's implementer finds that no inventory can be
completed. The implementer then either changes `_batch_rules` with no record (an unrecorded change to a WP9.3 row's
check) or stops.

**Change required.** In §10.2, add reading 4: for a root registration, "the latest for its source and selector" compares
the source path as well as the selector (`:555-559`). Say that reading 2 is made in `_whole_file`, so that `:614-616`
and `derive_ownership` (`:629`) both follow it. Update K's cost line and §15's root-registration row, with a test for
each. Restate claim 7.

### C-M2 (Major). A bare filename template is an `unregistered` blocker that nothing can clear, and P01-A's drafts contain one

**Note section:** §11.1 items 2-3 and "What still blocks, on the real roots"; §17 claim 6; §19 I.

**Evidence.** Claim 6's results are in §5. `drafts/sections/compute_table1_effects.py:205` reads
`json_path = output_dir / f"table1_effects_{date_suffix}.json"`. The tokenizer splits on `"`, which leaves
`table1_effects_{date_suffix}.json`. That is a bare name with a result extension that no registered result has, so the
revision 3 rule classes it as `unregistered` and it blocks. It is the script's own output name, not a citation. Revision
2 never took it as a candidate, so revision 3's fix for the dropped bare name (CodeRabbit; R-M6 item 3) introduced it.
Outside `drafts/`, the same class takes `.json` (a lone extension), `8000}.json`, `ladder_{survey}_L{landmarks}_B{B}_{date}.json`
and `level1_comparison_YYYYMMDD.json` as `unregistered`.

**Failure scenario.** P01-A can never record LR-039. A template cannot be registered (W9 §3.1: "per exact file"), it is
not ambiguous, so the disambiguation file does not apply, and a new status changes nothing. The only routes are a write
to a registered legacy draft (W9 §4.2 items 1 and 3, which re-triggers observation, the inventory and the mapping) or an
extractor change. Under I's whole-root alternative, both roots would also block on the lone `.json` tokens. That is the
permanent-blocker defect R-M6 item 1 described, back in a different class.

**Change required.** In §11.1 item 3, extend `not_a_file` to any candidate whose last path component does not name a
file: one containing a template marker (`{`, `}`, `YYYYMMDD`, `YYYY-MM-DD`), or one with an empty stem (`.json`).
Classify such a token by name, before the `unregistered` test. Re-state "What still blocks" as P01-A: four ambiguous
names, P01-B: none, and add the template to §15's extractor row and §18's last stop rule. If Stephen prefers to keep it
blocking, I must say that P01-A cannot record a status without a draft write.

### C-m1 (Minor). §5.3 and §5.5 conflict on the eligible session

**Note section:** §5.3 ("The reviewer exclusions are unchanged … the reviewer's session differs from every session the
request records"); §5.5 (LR-026 and LR-027).

**Evidence.** `_session_refs` returns every session it parses (`reducers.py:744-755`), and `_check_review_request` stores
them as `sessions` (`:819`, `:853`). §5.5 adds `w9-eligible-session:<s>` as the second entry, and `_check_verdict` refuses
a verdict whose session is in `sessions` (`:893-895`). The literal design therefore refuses the eligible session and
admits any other one. Probe `test_claim4_defect_the_unchanged_session_exclusion_refuses_the_eligible_session` shows
both, on the current check with a two-entry list.

**Change required.** §5.5 should say that for LR-026 the eligible session is stored apart from the excluded sessions, and
that the exclusion at `:893-895` covers the analyst's session only. LR-027's equality replaces it for that row. Add a
§15 control: the analyst's session is refused, and the eligible session passes.

### C-m2 (Minor). The disambiguation file cannot record one basename that means two results

**Note section:** §11.1 item 5.

**Evidence and change.** See §2, addition 1, and `test_claim6_defect_one_citing_file_means_two_results_by_one_basename`.
Let a row give a set of registered paths, sorted and non-empty, and let §15's extractor row test a file that cites one
basename for two results.

### C-m3 (Minor). The at-use rule names two of the five consumer kinds

**Note section:** §4.2 item 3 (E); §17 claim 2's question.

**Evidence.** The consumer facade has five kinds (`evidence/consumers.py`: result, review, manuscript, claim, sensitive
sidecar). The two the rule omits that have production callers are `resolve_for_result`, called by
`evals/release_publication.py:174-183` (`release_publication`, which loads the bytes as publication evidence), and
`resolve_for_review`, called by `methods/brief.py:29-30` and `:55` and by `session_exchange/exchange.py:439`. The
promotion-site option of E closes these as well. If Stephen declines it, a legacy copy promoted under the result or
review predicate stays usable there (`test_claim2_defect_the_at_use_rule_names_two_of_five_consumer_kinds`).

**Change required.** E should list all five kinds and say which are in scope at use. If result and review evidence are
out of scope, say why (W9-T17's clause is about claims), and say that declining the promotion site leaves them open.

### C-m4 (Minor). J's guard is named for CreateTask, but AmendTask can change the key and the refs

**Note section:** §4.1 (J); §6.2.

**Evidence.** `amend_task.schema.json` carries the whole `task_definition`, including `aliases` and
`source_import_refs`. A Task created clean can therefore be amended to name a `w9-adoption:` ref, or to change its
`w9-use-key` alias (`test_claim9_defect_amend_task_…`). The note says neither "AmendTask" nor how the guard treats an
amendment.

**Change required.** J's carry and its binding test should cover AmendTask, with one case adding the ref and one
changing the alias.

### Info

- **C-i1.** LR-025's preparer. `prepare_resolution` always appends `RECORDED_EVENTS[row]` (`preparers.py:528`), and
  `RECORDED_EVENTS` has no LR-025. §5.5 gives LR-025 a replay branch only. Name the preparer branch too.
- **C-i2.** §11.1 says whole-root scope "added 19 and 4 cited files". Under the rule as written it adds 24 (47 against 23)
  and 8 (10 against 2) (`test_claim6_whole_root_and_drafts_cited_counts`).
- **C-i3.** LR-024's grant is on the derived eligibility Decision ID, which is derived from the adoption alone. So the
  grant binds none of the five facts, and Stephen's LR-025 resolution binds them. That is the P-081 item 12 shape, on a
  sixth row that N's text ("five more rows") does not list. N should name it.
- **C-i4.** Claim 10 holds as equality of the extractor's output: a different inventory with the same output passes
  LR-054. That is harmless, because the citation object is then the same. The note's words "derived from" mean exactly
  that.
- **C-i5.** §5.4 says the request's set may hold "nothing outside the row's list". The request row (LR-026) lists only
  S-007. Say "the resolution row's list", or S-017 reads as refused.

## 5. The §17 claims

| # | Claim | Disposition | Evidence |
|---|---|---|---|
| 1 | Only the claim predicate binds a `claim_promotion` Decision; §4.2, §4.4 and §8 agree | **Holds** | Scratch-store probe; `service.py:4901-4902` |
| 2 | The content rule at LR-030 and LR-034, and at promotion, closes the readers; are there unnamed ones? | **Holds for direct readers** (the four the note names are all of them). **Unnamed:** the result and review resolver consumers (C-m3) | `test_claim2_*` |
| 3 | The first review's case suspends; the unobserved-edit limit is stated without overclaiming | **Holds** | `test_claim3_*` |
| 4 | LR-024 passes before any review; a wrong-session verdict is refused; every new ref has a preparer field | **Holds in part.** The branch and the fields hold. The session exclusion conflicts with the equality (C-m1), and LR-025's preparer is missing (C-i1) | `test_claim4_*` |
| 5 | The set is fixed in the request; F-019 is required for claim uses; is the reading fair? | **Holds.** The reading is a fair extension of P-084 i-3, but Stephen must record it (§2) | `test_claim5_*` |
| 6 | P01-B has no blocker, P01-A exactly four ambiguous names, and no candidate falls in no class | **Holds for P01-B and for "no class". Fails for P01-A:** four ambiguous names plus one `unregistered` template (C-M2) | below |
| 7 | Three readings are the only changes K's option 1 needs; per-path stale weakens nothing else | **Second half holds. First half fails:** a fourth reading is needed (C-M1) | `test_claim7_*` |
| 8 | The derived status ID binds all three hashes; no row lacks a subject | **Holds.** LR-024's reading is unlisted (C-i3) | `test_claim8_*` |
| 9 | An alias carries the key, and J's test can express "wrong use" | **Holds.** AmendTask is a residual (C-m4) | `test_claim9_*` |
| 10 | Re-running the extractor at LR-054 leaves no transition under another inventory | **Holds**, as output equality (C-i4). Checked by reading, because the check is not built | §10.5, §11.3 |
| 11 | The 25 first-round closures are still closed | **Holds.** Re-checked: the ten gate sites (m-1), the review-field read sites (M-2), the import seam (m-2), and the re-review's 28 probes (28 passed). M-12 is partly closed again through C-m1, which is a revision 3 addition, not a first-round regression | `test_claim11_*` |

### Claim 6 in full

**Method.** I implemented §11.1 as written, in the probe's `Extractor`:
- UTF-8 text, plus every decoded string value of a `.json` file;
- `\` read as `/`, and repeated `/` collapsed;
- tokens split on whitespace and `` ` ' " ( ) [ ] < > , ; | * ``, with trailing `.` and `:` stripped;
- candidates: contains `results/`, ends in a registered basename, or is a bare name ending in `.json`, `.npy`, `.npz`,
  `.csv` or `.pkl`;
- the four classes, with "a directory in Git" read from the whole tree at `ede231e5`;
- a file that is not UTF-8 listed as `not_text`;
- blocking only under `<root>drafts/`;
- no disambiguation file.

I read every tracked file under both roots through `git show ede231e5:<path>` (33 files in P01-A, 22 in P01-B). The
registration set is the 506 tracked files under `results/`. The step-4 projection (families, observations) needs a
store, so it is not run. On a real store, every cited file also needs an accepted observation, and a JSON file also
needs an accepted table, or it blocks.

**P01-A, drafts (blocking).**
- **Cited files, 23**, each resolving to one registered `results/` path. They include both the bhps and the integration
  copies of `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json` and
  `stratified_markov1_W2_L5000_20260502.json`, which are cited by full path from `table1_effects_2026-05-22.json`,
  `table1-effects-d_perm-rho-CI.md` and `results-negative-control-wording.md`, so the ambiguous basenames lose no family
  today.
- **Blockers, 5:**
  - `ambiguous`: `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json` and
    `stratified_markov1_W2_L5000_20260502.json` (each from `compute_table1_effects.py`), and `05_analysis.json` (from
    `supplement-S0-null-specification.md`; three registered results have it);
  - `unregistered`: `table1_effects_{date_suffix}.json` (`compute_table1_effects.py:205`).
- **`not_a_file`, 4:** `results/trajectory_tda_bhps/post_audit/`, `results/trajectory_tda_bhps/stratified_markov/`,
  `results/trajectory_tda_integration/post_audit/` and `results/trajectory_tda_integration/stratified_markov/`.

**P01-B, drafts (blocking).**
- **Cited files, 2:** `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json` and
  `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json` (from `v1-2026-04.md`).
- **Blockers:** none.
- **`not_a_file`, 2:** `results/trajectory_tda_bhps/post_audit/` and `results/trajectory_tda_integration/post_audit/`.

**Outside `drafts/` (reported, not hashed).**
- P01-A: 31 cited files, 24 of them cited only there; 2 ambiguous names; 25 `not_a_file` tokens (mostly prefix templates
  such as `…/04_nulls_wasserstein_w2_L5000_`); 10 `unregistered`. Of those 10, seven are the untracked
  `…_20260501.json` results and `results/trajectory_tda_bhps/embeddings.npy` from `2026-05-01-parallel-run-commands.md`,
  and the others are `regime_labels.npy`, `.json` and `8000}.json`.
- P01-B: 10 cited files, 8 of them cited only there; 2 ambiguous names; 28 `not_a_file`; 5 `unregistered`: `.json` and
  four `…YYYYMMDD.json` or `{…}` templates.

**`not_text`:** none in either root. **A candidate in no class:** none in either root, under both readings of "ends in
a registered basename" (as a path component, or as a string suffix).

**Result.** P01-B holds. P01-A does not leave exactly the four ambiguous names: a fifth, permanent blocker remains (C-M2).

## 6. Regressions

- Revision 3's bare-name rule turns a filename template into a permanent blocker (C-M2). That is a regression of the
  class R-M6 closed.
- Revision 3's eligible-session ref meets an exclusion that revision 3 keeps unchanged (C-m1). That reopens M-12 in part.
- No other first-round or re-review closure regressed (claim 11). No new defect of Major weight was found outside I and K.

## 7. Owner points (§19)

None is decided here.

| # | Line |
|---|---|
| A | **Agree.** The one D-4 goes in the PR whose rows cannot run before WP9.7 anyway |
| B | **Agree, with residual.** §5.5 now meets LR-024 to LR-027, subject to C-m1 and C-i1. The kind `migration_authority` equals the fixed `DECISION_KIND` (`reducers.py:123`) |
| C | **Agree.** The derived ID is fixed by hashed fields. It is correctly put as a reading |
| D | **Agree.** LR-035 and LR-054 refuse until WP9.7, as P-073 item 4 asks |
| E | **Agree, with residual.** The premise is now accurate. Name the result and review consumers (C-m3). The promotion-site choice is rightly Stephen's |
| F | **Agree.** The forms and the alias carrier work |
| G | **Agree.** It refuses too much only |
| H | **Agree.** Every file read is the preparer's, and the blob is bound in Stephen's Decision |
| I | **Agree with the direction (the drafts are W9 §12.1's text), with residual.** The `not_a_file` class misses templates (C-M2), and the disambiguation format is one-to-one (C-m2). Do not decide I until C-M2 is folded in |
| J | **Agree, with residual.** Include AmendTask (C-m4) |
| K | **Agree that option 1 is the right first option, with residual.** Its cost is four readings, not three (C-M1). Do not decide K until the cost is restated |
| L | **Agree, with residual.** The encoding is sound. The reading is a fair extension of P-084 i-3, which Stephen should record as such (§2). Fix the wording in C-i5 |
| M | **Agree** |
| N | **Agree, with residual.** Name LR-024's grant reading (C-i3) |

I disagree with none of the 14 points.

## 8. Probes

**File:** `wp9-4-design-note-confirmation-artifacts/test_confirmation_wp9_4_note_probes.py`. It holds my own probes,
written fresh. Some helpers follow the re-review's shapes. The claim 1 store is the test harness's
`control_plane(tmp_path)` scratch authority store, and the "legacy" bytes are a fixture literal. `papers/` and `results/`
are read through `git show ede231e5:<path>` only.

**Command**, from the worktree root at `ede231e5`:

```bash
uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider docs/plans/agentic-research-system/reviews/wp9-4-design-note-confirmation-artifacts/
```

**Result:** 28 passed, 0 failed (about 10 s). A probe whose name contains `defect` passes because the defect is present.
`ruff check` and `ruff format --check` are clean on the file, after one `ruff format`.

## 9. What I did not check, and why

- **Step 4 of §11.1 on a real store** (families, accepted observations and tables for the cited files). No store holds
  these observations, so the claim 6 run stops at classification.
- **Untracked results at `PROJ_ROOT`.** The registration set is tracked files only, as in the re-review. Registering
  untracked results would change the `unregistered` counts outside the drafts, not C-M2.
- **Indirect citations** (tables and figures in prose). Not read.
- **Claim 10 by probe.** The check is not built.
- **A third full attack** on sections revision 3 did not change (§2, §3, §12 to §14). They were read for consistency
  only, as a confirmation requires.
- **The accepted catalogue JSON against the annex.** Only the annex was read, as in both earlier reviews.
- **The vault** was not read or written. No store other than `tmp_path` scratch stores was opened. The full test suite
  was not run, because no code changed.

## 10. Commits and process

- `git config core.hooksPath` is `.githooks`.
- No file under `papers/`, `results/`, `.apm/`, `research_system/` or `tests/` was edited, and neither were the note, the
  register, the annex or any schema. No ARS store was written. No owner point is decided and nothing is accepted.
