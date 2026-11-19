# WP9.4 design note review at `32755276`: revision 5

**Date:** 2026-11-19<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md`, revision 5, at `32755276`, on
`claude/confident-volta-0e5dvm` (PR #437, unmerged). `git diff --name-only 7bd7d6a6 32755276` names the note only.
`git diff 4312dc63 53ac0d64 -- research_system .research-system tools` is empty, so every code citation reads the same
at the note's base and at its head. P-086's commit (`53ac0d64`) changes one line of the note, the status line.<br>
**Decision checked against:** P-086 in `03-decisions-and-open-questions.md` at `53ac0d64`.<br>
**Earlier reviews read for context:** the r4 review (`review/w9-wp9-4-note-r4`, `0a84ce83`) and its probe file, read
with `git show`. The three earlier reviews were not re-read. I did not reuse the r4 probe code. The §11.1 extractor
here was written fresh from revision 5's text.<br>
**Reviewer:** a fresh session. It wrote none of WP9.3, the note or any earlier review of it.<br>
**Mode:** narrow. It covers `git diff 7bd7d6a6 32755276`, judged against the rest of the note, the accepted schemas,
the WP9.3 code, W9, W11 §7 and P-086.<br>
**Branch:** `claude/review-w9-wp9-4-note-r5-bdb004`, cut from `53ac0d64`. This commit adds only this report and its
probe files.<br>
**Known limit (P-058):** the author, the reviewers and this session are one model family. This is recorded as a
limit, not as a finding.

## Verdict

**Confirm, with residuals.** 0 Blocking, 1 Major, 3 Minor, 5 Info.

Revision 5 answers the r4 review. Both Majors are folded in, and the new text holds up when run against the code:

- **The `member_path` carrier is sound against the accepted schemas.** The command payload schema is an open object
  (`.research-system/schemas/core/command.schema.json`: `payload` is `{"type": "object"}`), so a new payload key
  changes no accepted byte. The key must be stripped, as the note says, because the observation schema is closed.
  The member's path then reaches the derived ID through `source_identity` (`records.py:157-178`). The four read
  sites the note names are the only reader calls on option 1's route. The carrier can be tested: it needs one
  scratch Git repository.
- **Owner point O's reading has support.** W11 §7.2 gives a registration a "stable directory/file ID", and
  W11 §7.3 steps 1 and 2 bind every traversed directory by handle. A directory identity fits the schema's
  `physicalIdentity` unchanged. On Windows, which is the platform CI uses, it is stable when entries are added.
- **The §11.1 rerun confirms the note.** I ran the rule as revision 5 writes it over both roots at `32755276`. P01-A's
  drafts leave exactly four `ambiguous` basenames, and two token-keyed disambiguation rows clear them. P01-B's drafts
  leave no blocker, and no candidate on either root falls in no class.

One new Major comes from O itself. O makes the first directory registration possible, which brings W11 §7.2's
resolved-prefix collision rule into play for the first time. Replay checks only exact equality, so a file registered
under a paper root is admitted, and option 1's "no member has a registration" has no enforcement point (R5-M1). The
Minors are as follows:

- the brace fix (R4-m3) disables the template test that the R4-m4 fix relies on (R5-m1);
- the carrier text assumes a `git_tracked` root, which nothing fixes (R5-m2);
- P-086 carries a writer-guard reading that the note never states (R5-m3).

None of these touches WP9.4-1. None reverses an owner point. Each folds into WP9.4-2's own note or its tests. No
revision 6 is needed before WP9.4-1's code.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | — |
| Major | 1 | R5-M1 |
| Minor | 3 | R5-m1, R5-m2, R5-m3 |
| Info | 5 | R5-i1 to R5-i5 |

## 1. The §23 dispositions

| Finding | §23 says | This review | Evidence |
|---|---|---|---|
| R4-M1 | Fixed | **Closed.** §10.2 item 5 names a carrier, the read, all four read sites and the acceptance re-read, and it is gated on the role. The four sites are the only `reader.read` calls on the route. The other two calls, `inventory.py:141` and `preparers.py:360`, are on the light-inventory route. Residual: the carrier assumes `git_tracked` (R5-m2) | `test_item_5_names_every_reader_call_on_option_1s_route`; `test_member_path_*` |
| R4-M2 | Raised as owner point O | **Closed** as an owner point, which P-086 item 15 decided. The reading has support (§3). Residual: R5-M1, R5-i2, R5-i3 | `test_r4_major2_holds_*`, `test_owner_point_o_*` |
| R4-m1 | Fixed | **Closed.** "Each reading is gated on the role" replaces the false reason. §15 has the Computational-Log control | §10.2; §15 root-registration row |
| R4-m2 | Fixed | **Closed.** §4.2, claim 13 and E say that the promotion-site rule closes result and review evidence at promotion only, and recommend the at-use rule for them. P-086 item 5 took both | §4.2 item 3; §17 claim 13; §19 E |
| R4-m3 | Fixed | **Closed** for the defect it names: a LaTeX-wrapped path is now a cited token. The fix creates R5-m1 | `test_latex_wrapped_path_is_cited_under_revision_5` |
| R4-m4 | Fixed | **Partly closed.** The partial-path rows close the no-class hole, and nothing on either root falls in no class. "The template test reads every component" does not work under the new tokenizer: braces now split tokens, so no token holds `{` or `}`, and the example the note gives does not become `not_a_file` (R5-m1) | `test_r5_defect_braces_are_separators_*` |
| R4-i1 | Fixed | **Closed.** `methods/brief.py:27-28` is named. `resolve_sensitive_sidecar` has no caller | §4.2 |
| R4-i2 | Noted | **Closed** as noted | §10.2 |
| R4-i3 | Fixed | **Closed.** §5.3 separates the creator exclusion from the session exclusion. The §5.6 LR-024 cell reads in order | §5.3; §5.6 |
| R4-i4 | Fixed | **Closed** | §11.1 item 4 |
| R4-i5 | Fixed | **Closed.** Item 1 says replay checks "strictly under, not ending in `/`" and item 5 has the preparer check "regular file". The m-4 bullet in §10.2 agrees | §10.2 |
| CodeRabbit: result and review after promotion | Fixed | **Closed,** with R4-m2 | §4.2 |
| CodeRabbit: exact paths before the template test | Fixed | **Closed.** Cited files are tested first. No real cited file is lost: the drafts' cited count is 23, as at r4 | extractor run (§4) |
| CodeRabbit: token-keyed disambiguation | Fixed | **Closed.** My run clears P01-A's four blockers with rows keyed by citing file and token | `test_extractor_p01a_four_names_*` |
| CodeRabbit: relist the root at LR-054 | Fixed | **Closed.** §10.5's window re-lists the root, and §15's W9-T6 row has the test | §10.5; §15 |

**Totals:** 14 closed and 1 partly closed (R4-m4). None is marked closed without a change in the text. §23's
statement that "revision 5's §11.1 changes were not re-run on the roots" was honest. §4 below runs them.

## 2. New findings

### R5-M1 (Major). O makes directory registrations possible, and replay has no resolved-prefix collision check

**Note section:** §10.2 (the root registration, owner point O; option 1's "no member has a registration or an
ownership record"); §15 "The root registration's identity"; §17 claim 15.

**Claim.** Under O, a `legacy_manuscript_root` registration can be recorded for the first time. Nothing then stops a
second registration of a file under that root. Option 1's consequence that "no member has a registration" is an
invariant with no enforcement point.

**Evidence.**
- W11 §7.2 (`design/11-portfolio-and-discovery-lifecycle.md`, the paragraph after the state list): "Registration
  rejects exact, case-folded, Unicode-normalized, 8.3-name, symlink, reparse-point, or resolved-prefix collisions that
  would allow two writer sets to reach one physical target. A directory registration cannot authorize an unregistered
  nested authority file." W9 §3.1 (`design/09-migration-compatibility-and-pilot.md:134`) repeats the second sentence
  for paper roots.
- Replay's LR-003 check, `_registration_conflicts` (`research_system/legacy/replay/reducers.py:401-420`), compares
  `(root_kind, root_id, normalized_path)` and `(canonical_target, stable_file_id)` for equality only.
- The registration schema confines the root role's path to the two roots. It confines no other role's path away
  from them: `papers/P01-A-JRSSA/` occurs once in the schema, in that enum.
- Probe `test_r5_defect_replay_has_no_prefix_collision_check_*`: with the root registration recorded,
  `_registration_conflicts` returns `False` for a registration of `papers/P01-A-JRSSA/_project.md`.
- Revision 5's O text, claim 15 and §15's new row do not mention prefix collisions.

**Failure scenario.** A later registration manifest lists `papers/P01-A-JRSSA/_project.md` under another role, for
example `legacy_coordination`, and LR-003 to LR-005 record it. That file is then a member under the root and a
registration of its own. LR-054 moves the root to `successor_owned`, and the file's own registration stays
`legacy_owned`. Two ownership modes and two writer sets now reach one physical file, which is the state W11 §7.2
forbids. The file's own registration can also be observed and accepted to `closed_reference` at LR-020 while it is
listed as a root member. Only Stephen's LR-004 Decision would stop this, and that Decision is not a mechanical check.

**Impact.** Validity of the ownership state for paper roots. Before O no directory registration could exist
(R4-M2), so this gap could not be reached. O is what makes it reachable.

**Disposition.** Fix in WP9.4-2, within owner point O's scope. No owner point changes. The change is one more replay
check, which belongs with O's reading.

**Proposed text** (§10.2, after O's *Recommended* paragraph): "Replay's LR-003 check (`_registration_conflicts`)
also refuses a resolved-prefix collision with a `legacy_manuscript_root` registration, recorded or proposed. A path
strictly under a root's path, or a root whose path is a prefix of a registered path, is refused (W11 §7.2). This
makes option 1's 'no member has a registration' a replay invariant." §15 should add, to the root registration's
identity row: "a file registration under a recorded or proposed root is refused, and a root proposed over a
registered file under it is refused."

**Affected:** owner point O (P-086 item 15), K's consequences (P-086 item 11), WP9.4-2.

### R5-m1 (Minor). Braces as separators make the brace half of the template test unreachable, and R4-m4's example no longer works

**Note section:** §11.1 item 1 (separators), item 3's `not_a_file` row, the paragraph after the class table, §15's
extractor row (`results/x_{survey}/a.json` as `not_a_file`), §18's stop rule "blocks on a template".

**Evidence.**
- Item 1 now splits on `{` and `}`. After that split, no token can contain either character, so the `not_a_file`
  test "it contains `{`, `}`" can never be true. Only `YYYYMMDD`, `YYYY-MM-DD` and the empty stem are left to fire.
- The note says that "Testing every component, not only the last, makes
  `results/trajectory_tda_{survey}/post_audit/04_nulls.json` a template". Under its own tokenizer, that string
  becomes three tokens: `results/trajectory_tda_` (`not_a_file`, no extension), `survey` (not a candidate) and
  `/post_audit/04_nulls_….json`.
- The third token is a partial path with no `results/`. When its basename is registered under both
  `trajectory_tda_bhps/` and `trajectory_tda_integration/`, as the real `04_nulls_wasserstein_w2_20260407.json` is,
  that token is `ambiguous`: a blocker. When the basename is registered once, the token is a cited file.
- Probe `test_r5_defect_braces_are_separators_*` shows both outcomes. §15's fixture `results/x_{survey}/a.json` comes
  out as `results/x_` (`not_a_file`) and `/a.json`, which is cited when `results/x_bhps/a.json` is registered. It does
  not come out as `not_a_file`.
- Neither form occurs in either root's drafts today. My run finds no fragment of this kind there (§4).

**Failure scenario.** WP9.4-2 writes §15's fixture as the note words it, and the test fails. Or a draft writes a path
template with a directory placeholder whose basename has two registrations, and that template blocks LR-039. That
outcome trips §18's own stop rule ("blocks on a template"). The block can be cleared by a disambiguation row, so it is
a stop and not a permanent block.

**Disposition.** Fix in WP9.4-2's note or in its extractor tests. Owner point I (P-086 item 9) is unchanged.

**Proposed text.** Replace the R4-m4 sentence with this: "With braces as separators, a directory placeholder splits
the token. The part before it ends without an extension and is `not_a_file`. The part after it is classed as a
partial path: cited when one registered path ends in it, `ambiguous` (cleared by a disambiguation row) when several
do. A template therefore never blocks unless its tail names a shared basename." Drop `{` and `}` from the `not_a_file`
row, or say that only the date placeholders and the empty stem can fire there. Restate §15's fixture as
"`results/x_{survey}/a.json` gives `results/x_` as `not_a_file` and `/a.json` as cited (one registration) or
`ambiguous` (two)". Reword §18's stop rule to "blocks on a template that no disambiguation row can clear".

**Affected:** owner point I; WP9.4-2's extractor tests.

### R5-m2 (Minor). The carrier names `source_identity.repository_path`, but nothing fixes the root's source kind to `git_tracked`

**Note section:** §10.2 item 5 ("The record carries the path where it already does: the read-derived
`source_identity.repository_path`"; "`reread_items` takes it from the observation's
`source_identity.repository_path`").

**Evidence.**
- The registration schema's `legacy_manuscript_root` clause fixes `root_kind` and `normalized_path` only. Its
  repository-root branch admits `git_tracked`, `untracked_file` and `restricted_untracked_file` for any role.
- `LegacyReader.read` (`reader.py:318-331`) records `repository_path` for `git_tracked` and `path` for the two
  untracked kinds. Replay's `_source_location` (`reducers.py:454-461`) reads whichever key the kind uses.
- The probe `test_r5_defect_the_carrier_names_repository_path_*` and the reader probe show both shapes. §10.2 never
  states the root's `source_identity_kind`.
- The D-9 restricted rule keys on the registration's `normalized_path` suffix (the schema's last `allOf`). A root's
  path ends in `/`, so the rule never applies to a member. Neither root holds a tracked `.csv` or `.pkl` file today.

**Failure scenario.** A root registered as `untracked_file` gives member observations with no `repository_path`. The
re-read in item 5 then has no path to read, and a restricted member would be read as an ordinary file.

**Disposition.** Fix in WP9.4-2's note. This is a preparer-side check. It adds no schema change.

**Proposed text** (item 5, after "the carrier."): "A `legacy_manuscript_root` registration is `git_tracked`. LR-003's
preparer refuses any other kind for that role, as a recorded reading under O, so every member's path is its
`source_identity.repository_path`. The inventory lists tracked files only (§10.3). A member whose path has a D-9 suffix
is refused at LR-015."

**Affected:** owner points K and O; WP9.4-2.

### R5-m3 (Minor). P-086 carries a writer-guard reading to WP9.7 that the note does not state

**Evidence.** P-086's "Carried to later packages" includes "the writer guard's reading that a path under a
`successor_owned` root is writable". The note states no such carry. §10.2's consequences bullet says only that "after
LR-054 the whole root is `successor_owned`" and that "the writer-rule question of revision 2 does not arise". Its
option 2 text says "WP9.7's guard would need an exception" under that option. `grep -n -i "writer guard\|writable"`
on the note finds nothing. The other P-086 carries are in the note: the content rule at use and at promotion (§4.2),
the CreateTask and AmendTask guard (§4.1), the use-time re-hash (§4.3), the later-batch branch (§10.2, Timing), and
the LR-060 and LR-061 binding tests (§7).

**Assessment.** The carry looks correct and needed. Under option 1, a member has no registration of its own, so after
LR-054 only a reading of the root can let a successor write a draft. The divergence is that the register records an
obligation that the note, which WP9.7 will inherit, never states. This is a case of P-086 saying something revision 5
does not. It does not contradict the note.

**Disposition.** Record it in the note's carry list when the note is next touched (WP9.4-2), with the same words as
P-086. No owner decision is needed.

### Info

- **R5-i1 (stale restatements).** §18's stop rule still reads "a fifth site keys on registration where K's option 1
  needs a path". There are five sites now, so it should read "a sixth site" or "another site". §10.2's lead-in says
  "four readings … and one change to its preparer and reader", while item 5, the cost line, K and P-086 call it "the
  fifth recorded reading". The meaning is the same; one term would be better.
- **R5-i2 (O's identity encoding).** O does not say which encoding the directory identity uses. A file identity is
  `str(st_dev)` and `str(st_ino)` from `fstat` (`reader.py:123-133`). The store's `DirectoryAnchor.identity` is a
  different form: `windows-file-id-v1`, with a `bytes` file ID (`store/anchor.py:407-410`). `_registration_conflicts`
  compares `stable_file_id` strings across registrations, so O should name the `fstat` encoding. `link_count` is
  stable for a directory on Windows (probe), but on POSIX it moves with subdirectories. It is "where applicable" in
  W11 §7.2, so O should say that it is recorded but not compared for a directory, or that it is Windows only.
- **R5-i3 (O's negative test).** §15's "a file path under that role is refused" is already the schema's rule: the role
  admits two directory paths only. The control that tests O is a root path that resolves to a regular file, a
  junction or a reparse point, and that is refused at LR-003 and at LR-005's re-read.
- **R5-i4 (suffix reading).** Item 3 does not say whether "a suffix of" matches at a path-component boundary or as a
  plain string. On both roots the two readings give identical classes (probe
  `test_extractor_string_suffix_reading_gives_the_same_classes`). The component reading is the safe one (for example,
  `audit/x.json` against `post_audit/x.json`), and the note should state it.
- **R5-i5 (decided points still phrased as open).** §4.2 ("for Stephen to decide") and §19 E ("for Stephen to
  choose") still read as open, although P-086 has now decided them. The status line says P-086 decided A to O, which
  is enough for a decided note.

## 3. Focus 1 and 2: the carrier and the directory identity

**§10.2 item 5, the `member_path` carrier.**

| Check | Result | Evidence |
|---|---|---|
| No accepted byte changes | **Holds.** The core command payload is an open object. `_refuse_supplied` does not list `member_path`. The observation schema is closed, so the key must be stripped, as the note says. Today the key would reach the record, because `prepare_observation` and `observation_id` strip `frozen_copy_ref` only (`preparers.py:586`, `:647`) | `test_member_path_needs_no_command_schema_change_*`, `test_member_path_must_be_stripped_*` |
| The path is bound | **Holds.** `observation_subject_digest` hashes `source_identity`, so two members with one blob and one selector get distinct subjects and IDs | `test_member_path_is_bound_by_the_derived_id_*` |
| Every read site named | **Holds.** The `reader.read` calls in `research_system/legacy` are `acceptance.py:69` and `preparers.py:594`, `:633` and `:652`, which are on option 1's route, plus `inventory.py:141` and `preparers.py:360` (LR-011 and LR-014) | `test_item_5_names_every_reader_call_*` |
| `observation-id` CLI | **Holds.** `cli.py:1901` takes a whole `ObserveLegacyRecord` envelope, so the key flows through with no CLI change | `cli.py:1901-1902` |
| Replay needs reading 1 | **Holds.** `_source_matches_registration` refuses a member path today | `test_replay_path_rule_today_refuses_a_member_*` |
| Gated on role | **Holds,** with the R4-m1 control in §15 | §10.2 |
| Testable | **Yes.** A member read is feasible on a scratch repository: reading by the member path gives a `git_tracked` identity whose `repository_path` is the member. Residual: R5-m2 | `test_r4_major1_holds_today_*` |

**Owner point O, the directory identity.**

| Check | Result | Evidence |
|---|---|---|
| Reading supported | **Yes.** W11 §7.2 lists "stable directory/file ID, link count where applicable". W11 §7.3 step 1 binds the root's "directory file ID", and step 2 binds each component by handle. `handle_bound_read` already opens each parent with `open_registered_member_directory_anchor`, so a directory mode reuses existing machinery | `design/11-…:1150-1155`, `:1179-1195`; `reader.py:149-160` |
| Fits the schema unchanged | **Yes.** A directory's identity, built in the reader's own shape, validates against `physicalIdentity`. `relPath` admits the slash form | `test_owner_point_o_directory_identity_fits_*` |
| Stable and checkable | **Yes on Windows** (`st_dev`, `st_ino` and `st_nlink` unchanged after a subdirectory and a file are added). CI is `windows-latest` in all 14 jobs. On POSIX, `link_count` would move (R5-i2) | same probe |
| Needed today | **Yes.** `handle_bound_read` refuses both `papers/P01-A-JRSSA/` and `papers/P01-A-JRSSA` | `test_r4_major2_holds_*` |
| Nothing else on LR-003 and LR-005 assumes a file (claim 15) | **Holds** for the preparer: the detector controls, `_require_physical_identity` and the vault-only CONVENTIONS check. Replay's LR-003 check fails in the other direction: it is too weak for a directory (R5-M1) | `preparers.py:326-332`, `:541-543`; `reducers.py:401-433` |

## 4. Focus 3: the extractor run

**Method.** `wp9-4-note-r5-review-artifacts/r5_extractor.py` implements §11.1 as revision 5 writes it:
- tokens split on whitespace and `` ` ' " ( ) [ ] { } < > , ; | * ``, with `\` read as `/`, repeated `/` collapsed,
  and a trailing `.` or `:` stripped;
- in a `.json` file, decoded string values are scanned as well;
- the classes are tested in the order cited file, then `not_a_file` with every component checked, then `ambiguous`,
  then `unregistered`. Anything left over is recorded as "no class".

The registration set is the tracked files under `results/` at `32755276`, and the tracked directories under
`results/` are used for the directory test. Every file under each root was read with `git show 32755276:<path>`.
Nothing was written outside pytest's `tmp_path`.

| | P01-A drafts (blocking) | P01-B drafts (blocking) |
|---|---|---|
| Cited files | 23 | 2 (both `04_nulls_wasserstein_w2_20260407.json`, bhps and integration) |
| `ambiguous` | **4:** `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json`, `stratified_markov1_W2_L5000_20260502.json` (from `compute_table1_effects.py`), `05_analysis.json` (from `supplement-S0-null-specification.md`) | **0** |
| `unregistered` | 0 | 0 |
| `not_a_file` | `.json` (from `table1_effects_{date_suffix}.json`) and the four `post_audit/` and `stratified_markov/` directory paths | the two `post_audit/` directory paths |
| No class | 0 | 0 |
| `not_text` | 0 | 0 |

**The disambiguation file clears P01-A.** Rows keyed by `(citing file, token)` are enough: each of
`compute_table1_effects.py`'s three tokens maps to its two paths, and the supplement's `05_analysis.json` maps to one
path. With those rows, P01-A's drafts leave no blocker (`test_extractor_p01a_four_names_*`). Which path
`05_analysis.json` means is the reviewer's question for that row. I chose one only to show the mechanism.

**Outside `drafts/` (reported, not hashed).** P01-A has 31 cited files, 2 `ambiguous`, 8 `unregistered` (the
untracked `…_20260501.json` results, `regime_labels.npy` and `results/trajectory_tda_bhps/embeddings.npy`) and 26
`not_a_file`. P01-B has 10 cited, 2 `ambiguous` and 32 `not_a_file`. With braces as separators, the brace-templated
paths outside the drafts now split into `…_` stems, which are classed `not_a_file` for having no extension. Brace
expansion (`ph_L{2500,5000,8000}.json`) is still missed, as r4 said.

**The string-suffix reading** gives identical classes on both roots (R5-i4).

**Result.** The note's counts are confirmed. P01-A has four ambiguous basenames, which a disambiguation file can
clear. P01-B has none, and drafts-only blocking holds. No real citation in either root's drafts is lost to the
template test.

## 5. Focus 4b: agreement with P-086

| P-086 item | Note at revision 5 | Agreement |
|---|---|---|
| 1 A | §2.1 (two PRs; WP9.4-2 cut from WP9.4-1's main commit; WP9.4-1 has no new command and no D-4) | Agrees |
| 5 E | §4.2 items 1 to 6; §19 E. Stephen chose "at use and promotion" | Agrees. P-086 states the choice the note left open |
| 9 I | §11.1: cited files first, token-keyed disambiguation, drafts block | Agrees. R5-m1 is wording inside I |
| 11 K | §10.2: five readings, each gated on the role, `member_path` | Agrees |
| 15 O | §10.2 O; §19 O | Agrees |
| Carries | §4.1, §4.2, §4.3, §7, §10.2 | **One addition:** the writer-guard reading (R5-m3) |
| "Revision 5 itself has not been reviewed" | — | True when P-086 was written. This report is that review |

The other items (B, C, D, F, G, H, J, L, M, N) restate §19 rows that revision 5 did not change, and I checked their
wording only. I found no place where P-086 contradicts the note.

## 6. Owner points

P-086 has decided all of them. I disagree with none. R5-M1 and R5-m2 add checks inside O's and K's decided scope, and
R5-m1 is wording inside I. None needs a new decision.

## 7. Revision plan

- **Immediate, before WP9.4-1:** none.
- **WP9.4-2's note or tests:** R5-M1 (the prefix-collision replay check and its two tests), R5-m1 (the template
  wording and §15's fixture), R5-m2 (fix the root's kind to `git_tracked`, and refuse D-9 members), R5-m3 (the
  writer-guard carry), and R5-i1 to R5-i4.
- **Owner decisions:** none new.

## 8. Probes

**Files:** `wp9-4-note-r5-review-artifacts/r5_extractor.py` (the §11.1 rule) and
`wp9-4-note-r5-review-artifacts/test_r5_review_wp9_4_note_probes.py` (20 probes). Legacy state is built in memory.
The reader probes use a scratch Git repository under `tmp_path`. `papers/` and `results/` are read through `git show`.
No store is opened.

**Command,** from the worktree root:

```bash
uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider docs/plans/agentic-research-system/reviews/wp9-4-note-r5-review-artifacts/
```

**Result:** 20 passed, 0 failed (about 7 s) on Windows, Python 3.13. `ruff check` and `ruff format` are clean on both
files.

## 9. What I did not check

- §11.1 step 4 (projection through accepted tables) on a real store. No store holds those tables.
- Sections revision 5 did not change, beyond reading them for consistency. The earlier change logs (§20 to §22).
- The CodeRabbit threads on GitHub. I took their content from §23 and the diff.
- POSIX behaviour, which I reasoned about but did not run.
- The vault. Nothing was read from it or written to it.

## 10. Process

`core.hooksPath` is `.githooks`. No file under `papers/`, `results/`, `.apm/`, `research_system/`, `tests/` or the
vault was edited. The note, the register, the annex and the schemas were not edited. No ARS store, genesis, grant,
legacy write or paper-root transition was made.
