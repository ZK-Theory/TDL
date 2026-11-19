# WP9.4 design note review at `7bd7d6a6`: revision 4

**Date:** 2026-11-19<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md`, revision 4, at `7bd7d6a6`
(`7bd7d6a6e69be23670b152de7d57e247e9da1014`) on `claude/confident-volta-0e5dvm`, PR #437. I fetched the branch and ran
`git rev-parse`, which gave that commit. `git diff --stat ede231e5 7bd7d6a6` shows one file, the note (+212/-78).
`git diff --stat 4312dc63 7bd7d6a6 -- research_system .research-system tools tests` is empty, so every code citation
reads the same at the note's base and at its head. The probe file asserts both diffs.<br>
**Review answered by revision 4:** `reviews/wp9-4-design-note-confirmation-ede231e5-2026-11-19.md` and its probe file,
read with `git show` from `origin/review/w9-wp9-4-note-confirmation` at `3499dd21` (not merged), and CodeRabbit's
review of revision 3 as §22 tables it. The first review (`a9935c0b`) and the re-review (`a704d9b3`) were read for
background only.<br>
**Reviewer:** a fresh session. It wrote none of WP9.2, WP9.3, the note or any earlier review of it, and it did not see
the author's session.<br>
**Mode:** narrow. §10.2 and §11.1, plus every other place `git diff ede231e5 7bd7d6a6` changes. Every `path:line`
below was re-read at `7bd7d6a6`.<br>
**Branch:** `review/w9-wp9-4-note-r4`, cut from `7bd7d6a6`. Only this report and the probe file are added.<br>
**Known limit (P-058):** the author, the reviewers and this session are one model family. This is recorded as a limit,
not a finding.

## Verdict

**Confirm, with residuals.**

Revision 4 folds in the confirmation correctly. Of the 15 dispositions §22 tables, 13 are closed and 2 are partly
closed (C-m3 and CodeRabbit's fourth thread). None is open. The comment the author did not take is rightly not taken.
My own run of §11.1's rule, as revision 4 writes it, gives what the note expects: P01-A's drafts leave exactly the four
ambiguous names, P01-B's leave none, and no candidate on either root falls in no class.

Claim 7's new last clause ("no other site keys on registration where option 1 needs a path") does not hold, and the
note's own new stop rule fires on it. The four readings are all replay checks. Option 1 also needs the **preparer and
reader** to read a member, and they cannot: `LegacyReader.read` takes the registration only and reads its path, and the
`ObserveLegacyRecord` payload has no field that could name a member (R4-M1). Separately, and under every option of K,
**no `legacy_manuscript_root` registration can be recorded at all**: LR-003 and LR-005 read the registration's path
handle-bound, and the reader refuses the schema-fixed root path (R4-M2).

Both touch WP9.4-2 only, through owner point K and §10.3. Neither changes a recommendation for WP9.4-1. So B, E, F, L
and N can be decided on revision 4, with R4-m2 as an edit to carry on E. I can be decided with R4-m3 and R4-m4 carried.
K should wait for R4-M1 and R4-M2 to be folded in, by a short revision 5 limited to §10.2 and §10.3 or by WP9.4-2's own
note.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | — |
| Major | 2 | R4-M1, R4-M2 |
| Minor | 4 | R4-m1 to R4-m4 |
| Info | 5 | R4-i1 to R4-i5 |

## 1. The §22 dispositions

| Finding | §22 says | This review | Evidence at `7bd7d6a6` |
|---|---|---|---|
| C-M1 | Fixed | **Closed.** Reading 4 is in §10.2 with the right site (`_batch_rules`, `replay/reducers.py:539-560`, the refusal at `:559`). Reading 2 is made in `_whole_file` (`:526-536`), and the two callers it names are the only two (`:614`, `:629`). The cost line, §15's root-registration row, claim 7, §18 and K are restated. For a one-path registration a per-path model of readings 3 and 4 equals today's checks. Claim 7's new last clause is a separate failure (R4-M1) | `test_c_major1_*` (three probes) |
| C-M2 | Fixed | **Closed.** `not_a_file` is tested first and covers `{`, `}`, `YYYYMMDD`, `YYYY-MM-DD` and an empty stem. My run of the rule as written moves `table1_effects_{date_suffix}.json` to the report, and P01-A's drafts then leave exactly the four ambiguous names (§3). The template test has two edge defects of its own (R4-m3, R4-m4) | `test_extractor_holds_*` |
| C-m1 | Fixed | **Closed.** §5.3 and §5.5 now agree: the request stores the analyst's session in `sessions` (`:819`, `:853`) and the eligible session in its own field, and LR-027 requires "differ from the analyst's session and equal the eligible session". The check at `:893-895` then refuses the analyst only. Wording residual on the creator exclusion: R4-i3 | `test_c_minor1_*` |
| C-m2 | Fixed | **Closed.** A row gives a sorted, non-empty set of paths or `not_a_result`, and §15 has the two-paths case | §11.1 item 5; §15 extractor row |
| C-m3 | Fixed | **Partly closed.** All five kinds are named, and every predicate does require `accepted_for_scope` (`.research-system/policies/artefact-consumer-predicates.v1.yaml:24`, `:38`, `:52`, `:65`, `:78`), so the promotion-site rule does refuse at promotion. But §19 E ("which alone also closes result and review evidence") and claim 13 contradict §4.2's own reason for the at-use check: an adoption can suspend after promotion, and nothing re-checks result or review evidence then (R4-m2). The caller list also omits `methods/brief.py:27-28` (R4-i1) | `test_r4_minor2_*`, `test_r4_info_a_third_*` |
| C-m4 | Fixed | **Closed.** §4.1 names AmendTask and its schema; the binding test has both amendment cases. Claim 14 holds: only `create_task` and `amend_task` among the core command schemas carry a task definition | `test_c_minor4_*` |
| C-i1 | Fixed | **Closed.** §5.5 names the preparer branch; `preparers.py:528` still appends `RECORDED_EVENTS[row]` for every row, and LR-025 is not in it, so the branch is needed as written | `test_c_info1_*` |
| C-i2 | Fixed | **Closed.** My run gives 47 against 23 for P01-A and 10 against 2 for P01-B: 24 and 8 added | §3 |
| C-i3 | Fixed | **Closed.** §5.6 and N name LR-024. The §5.6 cell now reads awkwardly (R4-i3) | §5.6, §19 N |
| C-i4 | Noted | **Closed** | §17 |
| C-i5 | Fixed | **Closed.** Annex LR-026 to LR-028 list S-007 only, and LR-029 lists F-015, F-019, S-017 and F-038, which is what "the resolution row's list" now means | annex |
| CodeRabbit: whole-file of a tracked text file | Fixed | **Closed.** §6.1 needs binary or restricted, as W9 §9 item 1 says. The restricted half equals the code's D-9 copy (`reducers.py:68`: `.csv`, `.pkl`). Consequence for a cited text result: R4-i4 | `test_coderabbit_holds_*` |
| CodeRabbit: absent blobs match | Fixed | **Closed.** Every read sets `sha256` (`reader.py:342`), so only the blob can be absent, and an absent value now never matches | §9 |
| CodeRabbit: a member's observation suspends another member's whole-file adoption | Fixed | **Closed.** §7's whole-file cause compares the source path for a root registration | §7 |
| CodeRabbit: a path elsewhere ending in a registered basename | Fixed | **Partly closed.** `notes/data.json` is now `ambiguous`. But the class excludes "a suffix of a registered path", and no other class takes such a token, so a partial path such as `trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json` falls in no class (R4-m4). No such token is on either root today | `test_r4_minor4_defect_a_partial_*` |
| CodeRabbit comment, "require an adoption for every cited family" | Not taken | **The reason holds.** W9 §12.1 (`design/09-migration-compatibility-and-pilot.md:565-566`): "every result family its drafts cite is either adopted for … or marked unadopted in a `legacy-paper-citation-status` relation; W5 blocks any claim that rests on an unadopted family". Annex LR-054: "every cited family adopted or marked unadopted (§12.1)". W9 §3's table (`:212`) says the same. An unadopted family is allowed in the status; what is forbidden is a claim resting on it, which is W9-T17's last clause (owner point E). Requiring an adoption for every family would refuse transitions the accepted texts admit | `test_coderabbit_comment_not_taken_*` |

**Totals:** 13 closed, 2 partly closed (C-m3, CodeRabbit's fourth thread), 0 open. The comment not taken: the reason
holds.

## 2. New findings

### R4-M1 (Major). Option 1 needs the preparer and the reader to read a member, and they read only the registration's path

**Note section:** §10.2 ("That needs four readings of WP9.3's row checks"; the cost line at lines 821-825); §17 claim 7;
§18's new stop rule; §19 K.

**Evidence.** I searched `research_system/legacy/` for every site that keys on a registration. The four readings cover
every replay site (the path rule `:485-491`, `_whole_file` and its callers `:614`/`:629`, the stale update
`:1403-1414`, `_batch_rules` `:550-559`), and §7's own whole-file cause. They do not cover the preparer side:
- `LegacyReader.read(self, registration)` (`research_system/legacy/reader.py:275-285`) takes no path and reads
  `registration["normalized_path"]`. Its callers on option 1's route all pass the registration: the LR-015 preparer's
  read and final re-read (`legacy/preparers.py:594`, `:633`), the `observation_id` helper behind
  `ars legacy observation-id` (`:652`), and the closed-reference acceptance's window re-read at LR-016 and LR-020
  (`legacy/acceptance.py:69`, through `check_environment`).
- Under option 1 every member's registration is the root, whose path is `papers/P01-A-JRSSA/`. The reader refuses it
  ("registered path is not a canonical relative path"; without the slash it would be "not a regular file",
  `reader.py:168-169`). On a scratch Git repository, `acceptance.reread_items` refuses a member observation of the root
  registration: "W9 acceptance item's source cannot be read".
- Nor can the command say which member to read. `prepare_observation` refuses a supplied `source_identity`
  (`preparers.py:584`; `records.py:30`), and the `whole_file` selector is closed with no other property
  (`.research-system/schemas/contracts/w9/legacy-observation.schema.json`, `selector.oneOf[0]`). So there is no
  carrier for the member's path in the payload at all.
- §10.2 names none of `LegacyReader.read`, `prepare_observation`, `observation_id` or `reread_items`.

**Failure scenario.** Stephen accepts K on "four readings, none changes an accepted byte". WP9.4-2's implementer finds
that no member can be observed, because the preparer reads the root directory, and meets §18's new stop rule. The
choices are then an unrecorded change to the LR-015 preparer's refusal list and to the reader (a change to WP9.3 rows'
preparer checks), or a schema change to give the selector a path, which would change an accepted byte and contradict
K's stated cost.

**Change required.** In §10.2, add the preparer-side change as a fifth item, with its carrier: for a registration of
role `legacy_manuscript_root`, the `ObserveLegacyRecord` payload names the member's repository path (say how: a
supplied `source_identity.repository_path` admitted for that role only, or another field), and the reader reads that
path, checked strictly under the root, at LR-015, at `observation_id`, and in the acceptance re-read. Say whether that
is a reading of a WP9.3 preparer rule (no accepted byte changes) or needs a schema change. Update the cost line, claim 7,
§15's root-registration row (one test: a member is read by its own path, and a member path outside the root is
refused), and K's cost.

### R4-M2 (Major). No root registration can be recorded: LR-003 and LR-005 read the registration's path handle-bound

**Note section:** §10.2; §10.3 ("The root's registration live", line 850); §19 K.

**Evidence.**
- The registration schema fixes a root's `normalized_path` to `papers/P01-A-JRSSA/` or `papers/P01-B-JRSSB/`, with the
  trailing slash (`legacy-path-registration.schema.json:189-211`).
- `prepare_proposal` for a registration (LR-003) calls `_require_physical_identity` (`preparers.py:332`), and LR-005
  calls it again and at commit (`:541-542`). It runs `handle_bound_read` on the registration's path (`:151-160`, the read at `:156`). Annex
  LR-003's precondition is "one physical identity, read handle-bound", and LR-005's is "its physical identity re-read
  unchanged".
- `handle_bound_read` is a file protocol: it refuses the slash form as non-canonical and the bare directory as "not a
  regular file". On a scratch repository both forms are refused: "W9 registration path cannot be read handle-bound".
- The note says nothing about how the root registration comes to exist. LR-003 is not mentioned in §10.

**Failure scenario.** Under every option of K, LR-040 needs "the root's registration live", and no store can ever hold
one. LR-040 to LR-055 and LR-039 cannot run anywhere, and the gap surfaces only when WP9.4-2 writes its first
integration test. Fixing it then is a change to a WP9.3 row's preparer, and probably a reading of annex LR-003's
"read handle-bound" for a directory, with no record.

**Change required.** §10.2 or §10.3 should say how a `legacy_manuscript_root` registration is proposed and resolved:
which identity a directory has (W11 §7.2's root anchor is the obvious candidate), how LR-003's "read handle-bound" and
LR-005's re-read are read for it, which package owns that change (WP9.4-2 or WP9.5), and the test. If it is a reading of
an annex row's text, say that Stephen records it.

### R4-m1 (Minor). The reason given for "each reading reduces to today's check" is false for the Computational-Log role

**Note section:** §10.2, lines 823-825 ("because LR-015's path rule gives such a registration one path").

**Evidence.** The path rule has an exception: a `legacy_decision_log_entry` registration's source is any accepted
export's retained copy (`_source_matches_registration`, `reducers.py:472-484`). So two observations of one such
registration can have two paths, and both are admitted. Today the second one marks the first stale; under a per-path
stale rule it would not (`test_r4_minor1_defect_*`).

**Failure scenario.** An implementer reads the sentence as licence to key the stale rule and `_batch_rules` by
`(registration, path)` for every role. The older Computational-Log observation then stays live and acceptable after a
new export with different bytes.

**Change required.** Say that the four readings are gated on the role, and that they reduce to today's check because
they apply to `legacy_manuscript_root` only, not because every other registration has one path. Add the
Computational-Log case to §15's "each reduces to today's check" control.

### R4-m2 (Minor). E and claim 13 say the promotion-site rule closes result and review evidence; it closes them only at promotion

**Note section:** §4.2 item 3 (line 240); §17 claim 13 (line 1224); §19 E (line 1249); §22's C-m3 row.

**Evidence.** §4.2 says the at-use check "is needed at use because an adoption can suspend after the artefact is
promoted", and limits the at-use rule to claim and manuscript. A legacy copy promoted under the result or review
predicate while its adoption was active is admitted by the promotion-site rule and stays resolvable by
`resolve_for_result` and `resolve_for_review` after the adoption suspends. So claim 13 ("with the promotion-site rule,
no consumer of any of the five kinds can resolve a legacy copy that no active adoption admits") fails for those two
kinds, and E's "which alone also closes result and review evidence" overclaims.

**Failure scenario.** Stephen takes the promotion-site rule believing result and review evidence are closed. A
`release_publication` run then loads, as publication evidence, the bytes of an adoption that suspended after
promotion.

**Change required.** Say that the promotion-site rule closes result and review evidence at promotion only, and that a
later suspension leaves them open unless WP9.7 also applies the at-use rule to those two kinds. Let E offer that as a
choice, or record it as a known limit. Restate claim 13.

### R4-m3 (Minor). The template test drops real citations wrapped in braces

**Note section:** §11.1 item 3, the `not_a_file` row (line 945); §17 claim 6's question.

**Evidence.** The tokenizer does not split on `{` or `}`, and the template test looks for either in the last component.
So:
- `papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md` (and its copy) cites `ph_L{2500,5000,8000}.json` under
  `results/trajectory_tda_robustness/landmark_sensitivity/`. All three files are registered. The fragment `8000}.json`
  is classed `not_a_file`, and the other two fragments are not candidates. It is outside `drafts/`, so it is reported
  and does not block. Under I's whole-root alternative, three cited files would leave the set.
- A LaTeX-wrapped path, `\texttt{results/…/ph_L5000.json}` or `\path{…}`, becomes `/texttt{results/…/ph_L5000.json}`,
  whose last component ends in `}`: `not_a_file`. A wrapped bare name, `\texttt{ph_L5000.json}`, is not even a
  candidate. Neither form is in either root's drafts today.

**Failure scenario.** A draft cites a result inside a LaTeX macro. The extractor drops it from the set. D-3 then blocks
LR-054 only if the reviewer's derivation includes it; if both miss it, the family escapes W9 §12.1 silently.

**Change required.** Add `{` and `}` to the tokenizer's separators. Then a wrapped path is a clean token, a template such
as `table1_effects_{date_suffix}.json` still ends as an empty-stem `.json` (`not_a_file`), and only brace expansion is
left, which the note can name as a form the rule misses, next to the composed path. Add a LaTeX-wrapped case to §15's
extractor row.

### R4-m4 (Minor). Two candidate shapes still fall outside the classes or block for ever

**Note section:** §11.1 item 3 (lines 943-946); §18's stop rule on "a candidate in no class, or blocks on a template".

**Evidence.**
- A token with a directory part, no `results/`, that is a proper suffix of a registered path (for example
  `trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json`) is a candidate (it ends in a
  registered basename). It is not `cited` (no suffix of the token equals a registered path), the widened `ambiguous`
  explicitly excludes it, and it is neither `unregistered` nor `not_a_file`. It falls in no class.
- A template in a directory part, `results/trajectory_tda_{survey}/post_audit/04_nulls.json`, passes the template test
  (which reads the last component only), names a file under `results/` with no registration, and is `unregistered`: a
  blocker nothing can clear, as C-M2 was.
- Neither shape occurs in either root today (§3), so claim 6 holds. Both would trip §18's stop rule on a fixture.

**Change required.** Class the partial path as `cited` when it is a suffix of exactly one registered path and
`ambiguous` when of several. Apply the template test to every path component, not only the last. Add both to §15.

### Info

- **R4-i1.** `methods/brief.py:27-28` routes the purposes `result_analysis` and `result_reproduction` to
  `resolve_for_result`. §4.2 names `release_publication` only for that kind. `resolve_sensitive_sidecar`
  (`evidence/consumers.py:80-87`) has no production caller, as the note implies.
- **R4-i2.** `check_change_list` keys a shared-surface change by the registration triple (`acceptance.py:125`). Under
  option 1 a change list can name only the root, so one affected member makes every member observed before that merge
  unacceptable. That refuses too much only; name it next to R4-M1.
- **R4-i3.** Two wording residuals. §5.3 (line 390) says "The reviewer exclusions are unchanged for every row but
  LR-027", then lists the creator exclusion too, so it can read as relaxing the creator exclusion at LR-027; only the
  session exclusion changes. §5.6's LR-024 cell (line 519) appends the new text before the old, leaving "The eight
  refs." as a fragment.
- **R4-i4.** After §6.1's change, a cited non-JSON text result (a `.txt` or `.md` under `results/`) still projects to a
  `whole_file` pair (§11.1 item 4), but no adoption can ever admit it, so it can only be marked unadopted. That is W9
  §9 item 1's consequence, not an error, and no cited file in either root's drafts is of that kind today. §11.1 item 4
  should say so.
- **R4-i5.** Reading 1's "a regular file strictly under the root's path" cannot be checked by replay, which sees a path
  string only. It is harmless, because reading 2 already makes a member observation unable to close the root. Say that
  replay checks "strictly under, not ending in `/`", and that the preparer checks "regular file".

## 3. The extractor run

**Method.** The probe's `Extractor` implements §11.1 as revision 4 writes it:
- a file that is valid UTF-8 is text; a `.json` file's decoded string values (keys included) are scanned as well; a
  file that is not UTF-8 is `not_text`;
- `\` is read as `/` and repeated `/` collapsed; tokens split on whitespace and `` ` ' " ( ) [ ] < > , ; | * ``;
  trailing `.` and `:` stripped;
- a candidate contains `results/`, or has a last component equal to a registered basename, or is a bare name with a
  result extension. I also checked the string-suffix reading of "ends in a registered basename": it adds no candidate
  on either root;
- `not_a_file` first: under `results/` and a directory in Git at `7bd7d6a6`, ending in `/`, or with no extension; or a
  last component containing `{`, `}`, `YYYYMMDD` or `YYYY-MM-DD`, or with an empty stem. Then `cited` (a suffix of the
  token equals a registered path, or a unique bare basename), then `ambiguous` (bare and shared, or the widened class),
  then `unregistered`. Anything else is recorded as "no class";
- blocking under `<root>drafts/` only; no disambiguation file; the `whole_file` projection tested on fixture facts.

Every tracked file under both roots was read through `git show 7bd7d6a6:<path>` (33 files in P01-A, 22 in P01-B). The
registration set is the 506 tracked files under `results/`, and 90 tracked directories under `results/` were used for
the directory test.

**P01-A, drafts (blocking).**
- **Cited files, 23.** They include both copies of `04_nulls_wasserstein_w2_20260407.json`,
  `04_nulls_wasserstein_w2_L5000_20260502.json` and `stratified_markov1_W2_L5000_20260502.json`, cited by full path from
  `table1_effects_2026-05-22.json`, `table1-effects-d_perm-rho-CI.md` and `results-negative-control-wording.md`.
- **`ambiguous`, 4:** `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json`,
  `stratified_markov1_W2_L5000_20260502.json` (each from `compute_table1_effects.py`) and `05_analysis.json` (from
  `supplement-S0-null-specification.md`).
- **`unregistered`:** none.
- **`not_a_file`, 5:** the four directory paths (`results/trajectory_tda_{bhps,integration}/{post_audit,stratified_markov}/`)
  and `table1_effects_{date_suffix}.json`.
- **No class:** none.

**P01-B, drafts (blocking).**
- **Cited files, 2:** `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json` and
  `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json` (from `v1-2026-04.md`).
- **Blockers:** none. **`not_a_file`, 2:** `results/trajectory_tda_bhps/post_audit/` and
  `results/trajectory_tda_integration/post_audit/`. **No class:** none.

**Outside `drafts/` (reported, not hashed).**
- P01-A: 31 cited files (24 cited only there; whole root 47); 2 ambiguous (`04_nulls_wasserstein_w2_20260407.json`,
  `05_analysis.json`); 8 `unregistered`: `regime_labels.npy`, `results/trajectory_tda_bhps/embeddings.npy` and six
  untracked `…_20260501.json` results, all from `2026-05-01-parallel-run-commands.md` or the reviewer-response plan;
  27 `not_a_file`, including `.json` and `8000}.json` (R4-m3).
- P01-B: 10 cited files (8 only there; whole root 10); 2 ambiguous (`04_nulls_wasserstein.json`,
  `04_nulls_wasserstein_w2_20260407.json`); no `unregistered`; 33 `not_a_file`, including `.json`,
  `ladder_{survey}_L{landmarks}_B{B}_{date}.json`, `level1_comparison_YYYYMMDD.json` and two
  `ladder_bhps_…_YYYYMMDD.json`.

**`not_text`:** none in either root. **A candidate in no class:** none in either root.

**Blockers, in full:** P01-A drafts: the four ambiguous names above. P01-B drafts: none. On a real store, every cited
file also needs an accepted observation, and a JSON file an accepted membership table, or it blocks (item 4); that step
was not run.

**Result.** The note's expectation holds: P01-A's drafts leave exactly four `ambiguous` names, P01-B's none, and no
candidate falls in no class. **A real citation the template test wrongly classes as `not_a_file`:** yes, outside the
drafts: `ph_L{2500,5000,8000}.json` in P01-A's reviewer-response plan names three registered files (R4-m3). None in
either root's drafts, so no cited file leaves the blocking set today.

## 4. The other revision 4 changes

| Section | Check | Result |
|---|---|---|
| §5.3, §5.5 | The eligible session stored apart | Correct against `:744-755`, `:819`, `:853`, `:893-895`. §5.3 and §5.5 agree. Wording: R4-i3 |
| §5.4 | The L reading | Correct. The text no longer claims compliance with W9 §12.3 and names P-084 item 3's i-3. "The resolution row's list" matches the annex (C-i5) |
| §5.6, §19 N | LR-024 | Consistent: annex LR-024's subject lists the five facts, and the derived ID binds none of them, so naming it under P-081 item 12's shape is right. Cell wording: R4-i3 |
| §6.1 | Binary or restricted | Correct against W9 §9 item 1 and `RESTRICTED_SUFFIXES`. Consequence: R4-i4 |
| §7 | Per-path suspension | Correct, and it is the only §7 cause that keys on registration; the family cause cannot meet a member, which is observed whole |
| §9 | Absent blobs | Correct; `sha256` is never absent (`reader.py:342`) |
| §4.1 | AmendTask | Correct; claim 14 holds on the schemas |
| §4.2 | Five consumer kinds | Kinds and predicates correct. R4-m2, R4-i1 |
| §15 | New rows | Each new row tests what its finding asks. Missing: the preparer and registration cases (R4-M1, R4-M2), the Computational-Log reduction (R4-m1), the wrapped and partial-path tokens (R4-m3, R4-m4) |
| §17 | Claims | 6 holds. 7 fails in its last clause (R4-M1). 12 and 14 hold. 13 fails for result and review evidence after a later suspension (R4-m2) |
| §18 | Stop rules | Sound, and the new "fifth site" rule fires now (R4-M1) |

## 5. Regressions

None of Major weight. The earlier closures I re-read for the sections revision 4 changed (M-12 through C-m1; R-M6 and
M-5 through C-M2; R-m2 through §6.1; m-4 through §10.2) are still closed. CodeRabbit's widened `ambiguous` class
leaves the partial-path hole (R4-m4), which is a gap the fix did not cover rather than one it opened: revision 3 had
the same token in no class.

## 6. Owner points (§19)

None is decided here.

| # | Line |
|---|---|
| A | **Agree.** Unchanged, and nothing in revision 4 touches it |
| B | **Agree.** §5.5 now meets LR-024 to LR-027, with the session stored apart and the LR-025 preparer branch |
| C | **Agree.** Unchanged |
| D | **Agree.** Unchanged |
| E | **Agree, with residual.** The split is right; the promotion-site rule closes result and review evidence at promotion only (R4-m2), and one caller is unnamed (R4-i1) |
| F | **Agree.** Unchanged |
| G | **Agree.** Unchanged |
| H | **Agree.** Unchanged |
| I | **Agree, with residual.** The rule meets the note's expectation on both roots. Carry R4-m3 (braces as separators) and R4-m4 (partial paths, directory templates) |
| J | **Agree.** AmendTask is now covered |
| K | **Agree that option 1 is the right first option, with residual.** Its cost is understated: the preparer, the reader and the payload carrier (R4-M1), and the root registration itself, which every option needs (R4-M2). Do not decide K until both are folded in |
| L | **Agree.** Recorded as an extension of P-084 item 3's i-3, which is the honest name |
| M | **Agree.** Unchanged |
| N | **Agree.** LR-024 is named |

I disagree with none of the 14 points.

## 7. Probes

**File:** `wp9-4-design-note-r4-review-artifacts/test_r4_review_wp9_4_note_probes.py`, written fresh. Some helper shapes
follow the confirmation's. Legacy states are in-memory `new_legacy_state()` projections. The reader, preparer and
acceptance probes use a scratch Git repository under `tmp_path`. `papers/` and `results/` are read through
`git show 7bd7d6a6:<path>` only. No store is opened.

**Command**, from the worktree root at `7bd7d6a6`:

```bash
uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider docs/plans/agentic-research-system/reviews/wp9-4-design-note-r4-review-artifacts/
```

**Result:** 26 passed, 0 failed (about 1 s). A probe whose name contains `defect` passes because the defect is present.
`ruff check` and `ruff format --check` are clean on the file.

## 8. What I did not check, and why

- **§11.1 step 4 on a real store.** No store holds the observations or tables, so the run stops at classification; the
  projection is tested on fixture facts.
- **Untracked results at `PROJ_ROOT`.** The registration set is tracked files only, as in the earlier rounds.
- **Sections revision 4 did not change** (§2, §3, §8, §10.4, §10.5, §12 to §14), beyond reading them for consistency,
  and the first two change logs. This is a narrow review.
- **A fix for R4-M1 and R4-M2.** I did not design the member carrier or the directory identity; that is the author's.
- **W11 §7.2's root anchor** as a directory identity for R4-M2 was not read in detail.
- **CodeRabbit's review on GitHub.** I took its four threads and one comment from §22's table and the diff, and did
  not read them on the PR.
- **The vault** was not read or written. No ARS store was opened. The full test suite was not run, because no code
  changed.

## 9. Commits and process

- `git config core.hooksPath` is `.githooks`.
- No file under `papers/`, `results/`, `.apm/`, `research_system/` or `tests/` was edited, and neither were the note,
  the register, the annex or any schema. No owner point is decided and nothing is accepted.
