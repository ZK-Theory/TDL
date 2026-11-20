# Review of the WP9.4 design note, revision 6, and the two W9 paths addendum rows

**Date:** 2026-11-20<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md` at `b13f1592` (revision 6), judged
on `git diff 32755276 b13f1592`; and `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md`
at `642c56d3`, judged on `git diff b13f1592 642c56d3`. Both commits are on `claude/confident-volta-0e5dvm` (PR #437).<br>
**Against:** the rest of the note; the code at `642c56d3` (`research_system/legacy/`, `research_system/store/anchor.py`);
the W9 schemas under `.research-system/schemas/contracts/w9/`; W11 §7.2 and §7.3
(`design/11-portfolio-and-discovery-lifecycle.md:1174-1196`); W9 §3.1 (`design/09-migration-compatibility-and-pilot.md:134`);
P-086 (`03-decisions-and-open-questions.md:5753`); the r5 review (`reviews/wp9-4-note-r5-review-2026-11-19.md` on
`claude/review-w9-wp9-4-note-r5-bdb004`, `3e7846b2`).<br>
**Method:** `adversarial-design-review`. Every claim below about code was run, not read only. Probes and their output
are in `reviews/wp9-4-note-r6-review-artifacts/`. Scratch files only, under a temporary directory; no store, ledger,
vault, `papers/` or `results/` write. Both paper roots were read through `git show b13f1592:<path>`.<br>
**Reviewer independence:** a fresh session, the same model family as the author (P-058).

## 1. Verdict

**Confirm with residuals (accept with required changes): 0 Blocking, 2 Major, 3 Minor, 6 Info.**

Revision 6 folds in all nine r5 findings, and most of the new text holds up when run. The §11.1 rule, rebuilt from
revision 6's text, gives exactly what the note says on both real roots: P01-A's drafts leave four ambiguous names and
P01-B's none, no candidate falls in no class, and all 22 extractor fixtures in §15 come out as written. The addendum
rows agree with the note and with P-086 items 8 and 9 on path, format, producer and package.

The weak point is R5-M1's fix. W11 §7.2 asks registration to reject "exact, case-folded, Unicode-normalized, 8.3-name,
symlink, reparse-point, or resolved-prefix collisions", and §7.3 says "string prefix checks are not proof". Revision 6
chose a string prefix on `normalized_path` with no case-folding, and said the physical-identity half needs no prefix
form. On Windows, the platform this runs on, both statements fail. A member path that differs from the root only in
letter case is read by LR-003's preparer, and it passes today's check and revision 6's. So option 1's "no member has a
registration" is still not a replay invariant (R6-M1). The physical-identity equality that revision 6 leans on can
also be defeated, because replay compares the declared `canonical_target` string exactly while the preparer checks it
case-insensitively (R6-M2).

Neither Major touches WP9.4-1's code: both sit in LR-003's registration checks, which O puts in WP9.4-2. Both can be
fixed in WP9.4-2's note before its code. R6-M2's fix reaches every role, not only the root, so its scope is Stephen's
to confirm. No finding reopens an owner point.

## 2. Findings

### R6-M1 (Major). The prefix-collision check misses a case-variant path, and the physical half does need a prefix form

**Note section:** §10.2 "Prefix collisions (R5-M1)" (lines 921-941); §15 "Prefix collisions" row (line 1278); §17
claim 15; §19 O; §24 R5-M1.

**Claim.** Revision 6 says the check compares `normalized_path` "at a path-component boundary", with no case-folding,
relying "on the schema's normalized form", and that "the physical-identity half needs no prefix form: a member file
and its root have different identities". It concludes that option 1's "no member has a registration" becomes a replay
invariant.

**Evidence.**
- The schema's normalized form does not fold case. `relPath` (`legacy-path-registration.schema.json`, `$defs.relPath`)
  forbids `\`, `:`, `//`, `.`/`..` segments, a trailing dot or space, and `~<digit>` (8.3 names), and nothing else.
  `papers/p01-a-jrssa/_project.md` is schema-valid.
- LR-003's preparer reads a case variant. `_require_physical_identity` (`preparers.py:151-170`) calls
  `handle_bound_read`, which compares each parent with `os.path.normcase` (`reader.py:161`), so on Windows a parent
  spelled in another case passes. Probe [1]: `papers/p01-a-jrssa/_project.md` and `PAPERS/P01-A-JRSSA/_project.md`
  are both READ, with the same file ID and a `canonical_target` in the on-disk case.
- The vehicle is an untracked kind. A `git_tracked` registration of the variant is refused, because the Git object
  read is case-sensitive (probe [2]: "git show failed"). An `untracked_file` registration is READ (probe [2]); nothing
  in LR-003 checks that an `untracked_file` path is untracked.
- Probe [3], with the root recorded: for the case variant, today's `_registration_conflicts` gives `False`, revision 6's
  rule gives `False`, and a prefix rule on `os.path.normcase(canonical_target)` gives `True`. Controls behave: the
  exact-case member is refused by both rules, and `papers/P01-A-JRSSA-old/x.md` by neither. In the reverse direction
  (member recorded first, then the root) revision 6's rule again gives `False` and the target rule `True`.
- W11 §7.2 (`design/11-portfolio-and-discovery-lifecycle.md:1174`) lists "case-folded" next to "resolved-prefix";
  §7.3 step 2 (line 1193) says "string prefix checks are not proof", and step 3 (line 1196) asks to reject a
  "physical-prefix collision even when path strings differ". Revision 6 quotes §7.2 with an ellipsis over "case-folded".
- Other aliases are closed by the read already: an 8.3 name by `relPath`; a junction or symlink parent by the anchor
  check at `reader.py:161`; a symlink leaf by `reader.py:165`; a hard link by `st_nlink != 1` (`reader.py:170`); a
  Unicode-normalization variant because NTFS does not normalize names, so it names no file. Letter case is the one alias
  that survives to LR-003.

**Failure scenario.** A registration manifest lists `papers/p01-a-jrssa/_project.md` as `legacy_coordination`,
`untracked_file`. LR-003 reads it, replay and the preparer pass it, and Stephen's LR-004 Decision is the only stop.
After LR-054 the file is a member of a `successor_owned` root and a `legacy_owned` registration of its own: the two
writer sets that R5-M1 was raised to prevent.

**Impact.** Validity of the ownership state for paper roots. The note's stated invariant is false on Windows.

**Disposition.** Fix in WP9.4-2's note, within O's scope.

**Proposed text** (replacing §10.2's paragraph that begins "The comparison is on `normalized_path`"): "The comparison
is made twice, and either refuses. First on `normalized_path`, case-folded (`str.casefold`), at a path-component
boundary, within one `(root_kind, root_id)`: W11 §7.2 names case-folded collisions, and the handle-bound read accepts
a parent in another case on Windows. Second on the physical target: a registration whose `canonical_target`,
case-folded with `/` separators, lies strictly under a root's `canonical_target` is refused, and the converse for a
root (W11 §7.3 step 3, 'physical-prefix collision even when path strings differ'). Replay folds with `casefold`, not
`os.path.normcase`, so that replay gives one answer on every platform." Add to §15's prefix row: "a case variant
`papers/p01-a-jrssa/_project.md` as `untracked_file`, refused in both directions; a `vault_root` registration whose
vault path happens to begin `papers/P01-A-JRSSA/` is not refused (root scope)". Strike "The physical-identity half
needs no prefix form" from §10.2.

**Affected:** owner point O (P-086 item 15), K (item 11), WP9.4-2, §17 claim 15, §18's new stop rule.

### R6-M2 (Major). The physical-identity equality compares the declared `canonical_target` string exactly

**Note section:** §10.2 "Prefix collisions" ("The physical-identity half needs no prefix form") and "The identity's
encoding" ("`_registration_conflicts` compares `stable_file_id` strings across registrations").

**Claim.** Revision 6 relies on the physical half of `_registration_conflicts` to catch one file registered twice.

**Evidence.**
- Replay compares `(canonical_target, stable_file_id)` for exact equality (`replay/reducers.py:409-413`).
  `volume_serial_number` is not compared.
- The preparer checks the declared target against the observed one with `os.path.normcase` on both sides
  (`preparers.py:143-148`). So a registrant can declare `canonical_target` in any letter case.
- Probe [4]: `_same_physical_identity(observed, declared upper-cased)` is `True`. With `papers/P01-A-JRSSA/_project.md`
  recorded, a second registration of the same file at `papers/p01-a-jrssa/_project.md` whose declared target is
  upper-cased gives `_registration_conflicts = False`. The control, the same second registration with the target as
  observed, gives `True`.
- W11 §7.3 step 3: "Compare every opened volume/file ID against all registered authority and writer paths. Reject a
  hardlink or file-ID alias".

**Failure scenario.** One file, two registrations, two roles and two writer sets, for any role on Windows. This is in
WP9.3's accepted code, not in revision 6's text. Revision 6 makes it matter more, because it now names the physical half
as the thing that needs no further form.

**Impact.** The equality half of W11 §7.2's rule can be defeated by a spelling the preparer accepts.

**Disposition.** Owner decision on scope; recommend fixing in WP9.4-2 with O's reading.

**Proposed text** (§10.2, after the prefix paragraph): "The equality half compares `(volume_serial_number,
stable_file_id)`, the identity W11 §7.3 step 3 names, and `normalized_path` case-folded. The declared
`canonical_target` string is not an identity: the preparer accepts it in any case. This changes WP9.3's check for every
role, so it is recorded as a correction to WP9.3's LR-003 replay check, with a forged-ledger test of one file
registered twice in two cases." The decision for Stephen: fix it in WP9.4-2 as an extension of O to all roles, or in a
separate WP9.3 follow-up PR before any real store.

**Affected:** WP9.3's LR-003 (P-081, P-084), owner point O, WP9.4-2.

### R6-m1 (Minor). The root's `git_tracked` rule is preparer-only, with no replay check and no §16 row

**Note section:** §10.2 K item 5, "the root's source kind" (line 844); §15 root identity row; §19 O.

**Evidence.** Revision 6 places the rule at "LR-003's preparer". Replay's `_check_registration`
(`replay/reducers.py:423-433`) sees `role` and `source_identity_kind` and could refuse it in one line, as revision 6
puts the prefix check there. §16 lists the forged-ledger gaps that preparer-only checks leave (G3, the content check,
the open items) but not this one.

**Failure scenario.** A forged or hand-built ledger records the root as `untracked_file`. Replay passes it. By the
kind-equality rule (`_source_matches_registration`, `reducers.py:464-491`) every member observation is then
`untracked_file`: read without Git, with a frozen copy, under `path` rather than `repository_path`. That inverts the
inventory's "tracked files only" (§10.3).

**Disposition.** Fix now in the note. Put the rule in replay's LR-003 check as well as the preparer: "Replay's LR-003
check refuses a `legacy_manuscript_root` registration whose `source_identity_kind` is not `git_tracked`." The rule is
at the right row (LR-003) and fits the reader (`reader.py:310-325`), whose `git_tracked` branch is the one that records
`repository_path`.

### R6-m2 (Minor). A template's tail is matched without its head, so it can cite an unrelated result

**Note section:** §11.1 item 1 (the new bullet) and the paragraph after item 3's table ("A template therefore blocks
only when its tail names a shared basename, and a disambiguation row can always clear that block").

**Evidence.** `r6_extractor.py`, fixtures "PROBE: template tail". `results/x_{survey}/a.json` with only
`results/zzz/a.json` registered gives `results/x_` as `not_a_file` and `/a.json` as **cited**, meaning
`results/zzz/a.json`. The head that said `x_…` is dropped. The cited-file class is tested first and never consults the
disambiguation file, so no row can clear a wrong citation. And `results/x_{survey}/post/a.json` with `results/y/a.json`
registered makes `/post/a.json` **ambiguous** by the third ambiguous clause, though no basename is shared. So the
sentence "blocks only when its tail names a shared basename" is too narrow. Neither case occurs on the real roots
today: no draft token, and no token elsewhere in either root, begins with `/` (`r6_extractor_output.txt`).

**Failure scenario.** A draft names a templated output path whose tail happens to end in a registered basename
elsewhere. The extractor's set gains a result the draft does not cite. The reviewer's derivation differs, LR-054
refuses, and the only routes are a new extractor or a draft write.

**Disposition.** Fix in WP9.4-2's note (the extractor ships there). Smallest change: "A tail produced by a brace split
(a token that begins with `/`) is never a cited file by itself. It is `ambiguous` when any registered path ends in it,
and a disambiguation row names its set; otherwise it is reported." Reword the sentence: "A template blocks when its
tail ends in a registered basename and no disambiguation row covers it; a row can always clear it." Add the two probe
fixtures to §15.

### R6-m3 (Minor). R5-m1's fix missed the "Why templates are `not_a_file`" paragraph

**Note section:** §11.1, lines 1078-1085.

**Evidence.** The paragraph still says "The tokenizer splits on `"`, which leaves `table1_effects_{date_suffix}.json`",
and that outside `drafts/` "the same rule reports `.json`, `8000}.json`, `ladder_{survey}_L{landmarks}_B{B}_{date}.json`
and `level1_comparison_YYYYMMDD.json`". Under item 1, which revision 6 now states plainly, no token holds `{` or `}`.
The rule actually yields `.json` for the first, and the brace pieces of the others are not candidates.

**Disposition.** Fix now: "Under revision 3's tokenizer that left `table1_effects_{date_suffix}.json`… Under item 1 the
same text gives the empty-stem token `.json`. Outside `drafts/`, the rule reports `.json` and
`level1_comparison_YYYYMMDD.json` as `not_a_file`; the brace pieces of `ladder_{survey}_L{landmarks}_B{B}_{date}.json`
are not candidates."

### R6-i1 (Info). A directory's identity cannot come "from `fstat` on the bound handle" on Windows

**Note section:** §10.2 "The identity's encoding" (lines 913-919); §15; §24 R5-i2.

**Evidence.** `r6_dir_identity_probe_output.txt`: `os.open` on a directory, which `os.fstat` needs, is refused on
Windows (PermissionError). The store's directory anchor gives the same numbers: `volume_or_device == st_dev`, and
`file_id` read little-endian equals `st_ino`, as `_windows_handle_matches_stat` (`store/anchor.py:1561-1573`) already
does. A directory's `st_nlink` stayed 1 after adding a subdirectory and a file, so revision 6's Windows statement holds.
The site that must skip `link_count` for a directory is `_same_physical_identity` (`preparers.py:143-148`), which LR-003
and LR-005 both call. The note does not name it.

**Disposition.** Fix the wording: "from the bound directory anchor (`DirectoryIdentity`), written in the reader's
encoding: `str(volume_or_device)` and `str(int.from_bytes(file_id, 'little'))` (the conversion
`_windows_handle_matches_stat` uses); `_same_physical_identity` skips `link_count` for this role."

### R6-i2 (Info). The D-9 member refusal duplicates the observation schema

**Note section:** §10.2 K item 5 ("so it never reaches a member", line 850); §15 root identity row.

**Evidence.** The member observation's source is `git_tracked` (R6-m1), and the observation schema's `git_tracked`
`repository_path` already refuses a `.csv`/`.pkl` suffix (`legacy-observation.schema.json`,
`$defs.sourceIdentity.oneOf[0]`). The registration schema's D-9 rule does not reach a member, as the note says; the
observation schema does. Neither root holds a tracked `.csv` or `.pkl` file at `b13f1592` (0 found).

**Disposition.** Keep the preparer check as belt and braces, but say the schema refuses it too, and make §15's negative
control assert the preparer's own refusal, not just any refusal. Otherwise the test passes with the check absent.

### R6-i3 (Info). §19's decided rows were edited after P-086

**Evidence.** P-086's Decision is "The note's §19, as revision 5 states it". Revision 6 changes row E (to state item
5's choice) and adds to row O: "LR-003 refuses a resolved-prefix collision with a root (R5-M1), and a root is
`git_tracked` (R5-m2)". Neither reopens a point, and both follow reviews that placed them inside O. But §19 no longer
matches what P-086 records, and R6-M2 would widen O to every role.

**Disposition.** Stephen records, in the entry that dispatches WP9.4-2, that O's reading includes the prefix check, the
`git_tracked` rule and R6-M1/R6-M2's fixes as he decides them. No register edit here.

### R6-i4 (Info). §24's two corrections answer statements the committed r5 review does not make

**Evidence.** §24 says two statements of the r5 review were narrowed: no case-folding, and open proposals not a batch.
The committed r5 report (`3e7846b2`) and its two artifact files contain neither statement: "case-folded" occurs only
inside the W11 quotation, and "batch" only as "the later-batch branch". Both corrections are right about the code
(`_registration_conflicts` folds nothing; it reads `state["proposals"]` filtered by `proposal_open`,
`reducers.py:415-419`). The first was then used to justify leaving out a case-folding that W11 requires (R6-M1).

**Disposition.** Name where each statement came from (the r5 session's relay, if that is it), or drop "of the
review's statements" and say "two points of the code".

### R6-i5 (Info). The addendum rows: row numbers, readers and the header's scope

**Evidence.**
- The open-item row says the blob is "bound in his Decision at LR-033 and LR-053". That matches the note (§5.4 item 3,
  line 425; §8, lines 721 and 748). P-086 item 8 says "named in the Decision at LR-034 and LR-054", the resolution
  rows of the same Decisions. One object, two row pairs in two records. The addendum follows the note, which is right
  about where the entry is carried.
- Its reader column, "discharge (LR-030 to LR-034)", is wider than §8: LR-030, LR-033 and LR-034 read the file; LR-031
  and LR-032 do not.
- The disambiguation row's readers omit the reviewer's derivation, whose hash covers the same blob (§11.1 item 6).
- "06v names neither file" holds: `06v-w9-implementation-plan.md` names "a legacy open item" (line 449) and O-14
  (line 194), and no file. Neither file exists on any branch (`git log --all` on both paths is empty), and no code
  names either.
- The addendum's header says it "gives a path to each place 06v names without one". The two new rows give paths 06v
  does not name. The dated entry says so, but the header is now narrower than the table.

**Disposition.** Optional edits: "LR-030, LR-033, LR-034, LR-053, LR-054" in the reader column; "and the citation
reviewer's derivation" in the second row; one header clause, "and, from 2026-11-20, to files a W9 note adds". A
one-line note against P-086 item 8 at the next register edit, naming LR-033 and LR-053 as the proposal rows.

### R6-i6 (Info). `successor_results_root` is a second directory role

**Evidence.** The registration schema fixes `successor_results_root` to `results/ars/`, a directory. It is not
recordable today, because `_relative` refuses the trailing `/` (`reader.py:105-111`), so "for the first time" is true.
W11 §7.2's prefix rule is general. Revision 6's check is scoped to `legacy_manuscript_root`.

**Disposition.** Carry: whichever package makes `results/ars/` recordable (W9-D14) applies the same prefix check. One
line in §3's carry table.

## 3. §17 claim 15: does any other site need a prefix form for a root?

Each site that compares registrations at `642c56d3`, run against the K option 1 shape (members observed under the
root's registration, never registered):

| Site | What it compares | With a root | Prefix form needed? |
|---|---|---|---|
| `_registration_conflicts` (`reducers.py:401-420`) | path and physical identity, equality | Revision 6's change | Yes, and case-folded with a physical-target form (R6-M1, R6-M2) |
| `_check_registration`, the projection prefix and `CONVENTIONS.md` (`reducers.py:428-433`) | path prefix, name regex | the root's path is fixed by the schema | No |
| `_source_matches_registration` (`reducers.py:464-491`) | source path equals registration path | K's reading 1 replaces it for the root | Already a reading |
| LR-005's re-read, `_require_physical_identity` (`preparers.py:151-170`, `541-542`) | one registration against the disk | compares no other registration | No; it needs O's directory mode and the `link_count` skip (R6-i1) |
| `check_change_list` (`acceptance.py:118-133`) | `(root_kind, root_id, normalized_path)` equality against `affected_registrations` | a member's item is keyed by the root's registration, so a change naming the root covers every member | No; it is coarse, not unsafe |
| `require_registered` (`evidence.py:92-108`) | manifest equality | the root is listed by its own path | No |
| `_registered_role` for `corrected_by` (`reducers.py:1235-1242`) | path equality | a member path finds no role and is refused | No: manuscripts are not precedence tier 1 (`TIER_ONE_ROLES`, `reducers.py:134`), so the refusal is right |
| LR-020's closure and LR-054's subject check | not built; WP9.4 and the annex | K's readings 2 to 4 (`_whole_file`, the stale rule, `_batch_rules`) already key on the member path | No new prefix form beyond those readings |

So LR-003's conflict check is the one site that needs a prefix form, as revision 6 says; it needs the stronger form of
R6-M1.

## 4. §24 dispositions, re-checked

| r5 finding | §24 says | Re-check |
|---|---|---|
| R5-M1 | Fixed | **Partly.** The check exists in both directions, against open proposals, at a component boundary, with controls. It misses case variants and declines the physical prefix W11 §7.3 asks for (R6-M1, R6-M2) |
| R5-m1 | Fixed | **Fixed in item 1, item 3's row, the following paragraph, §15 and §18;** missed in the "Why templates" paragraph (R6-m3). The new tail rule has a gap (R6-m2) |
| R5-m2 | Fixed | **Fixed at the right rows** (LR-003 for the kind, LR-015 for D-9). Preparer-only for the kind (R6-m1); the D-9 check duplicates the schema (R6-i2) |
| R5-m3 | Fixed | **Fixed.** §3 row 16 uses P-086's carried words |
| R5-i1 | Fixed | **Fixed.** "Five recorded readings" at lines 812, 861, 1276, 1349 and 1403; no "four readings" remains except the historical sentence at 813 |
| R5-i2 | Fixed | **Fixed in substance;** the "`fstat` on the bound handle" wording cannot be built for a directory on Windows (R6-i1) |
| R5-i3 | Fixed | **Fixed.** The schema's enum does refuse a file path for the role, so the new control is the right one |
| R5-i4 | Fixed | **Fixed.** On both roots the component and string readings give identical classes (`r6_extractor_output.txt`, three modes) |
| R5-i5 | Fixed | **Fixed.** §4.2 and §19 E state P-086 item 5 |

## 5. §11.1 re-run (focus 3) and §17 claim 16

`r6_extractor.py`, written from revision 6's text (the r5 extractor was read as a reference; differences are listed in
its docstring, chiefly that braces are no longer a template marker). Registration set: the 506 tracked files under
`results/` at `b13f1592`. Roots read through `git show b13f1592:<path>`.

| Drafts only, revision 6 | P01-A | P01-B |
|---|---|---|
| Files in root / not text | 33 / 0 | 22 / 0 |
| Cited files | 23 | 2 |
| `ambiguous` | 4: `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json`, `05_analysis.json`, `stratified_markov1_W2_L5000_20260502.json` | none |
| `unregistered` | none | none |
| `not_a_file` | 4 directory paths and `.json` | 2 directory paths |
| A candidate in no class | none | none |
| Tokens beginning `/` (template tails) | none | none |

The same counts come out under a string reading of "a suffix of" and under a string reading of "ends in a registered
result's basename". Claim 16 is **confirmed**. All 22 §15 extractor fixtures come out as the note states, including
the two R5-m1 ones (`results/x_` `not_a_file`; `/a.json` cited with one registered and `ambiguous` with two) and the
R5-i4 one (`x/a.json` is not a suffix of `results/xx/a.json`; it then classes `ambiguous` by the third ambiguous
clause, which §15 could state).

## 6. Owner points and P-086

No new text reopens or contradicts an owner point. E's row now states item 5's choice. O's row gains two checks that
the r5 review placed inside O (R6-i3 asks that this be recorded). R6-M2 would widen O's change to every role, which is
Stephen's to confirm. §3 row 16 matches P-086's "Carried to later packages". The addendum rows match items 8 and 9 on
path, format, content owner and package (R6-i5 for the row-number and reader details).

## 7. Revision plan

- **Before WP9.4-2's code (in its note):** R6-M1 (case-folded path prefix plus physical-target prefix, root-scoped,
  with the §15 fixtures); R6-m1 (the kind rule in replay); R6-m2 (tails never cited alone); R6-m3; R6-i1; R6-i2.
- **Stephen:** R6-M2's scope (WP9.4-2 under O, or a WP9.3 follow-up PR before any real store); recording O's
  added checks when WP9.4-2 is dispatched (R6-i3).
- **Optional, any time:** R6-i4 wording; R6-i5's addendum edits; R6-i6's carry line.
- **WP9.4-1:** nothing here blocks it.

## 8. Residual risks

- The reviewer is the author's model family (P-058).
- The probes ran on Windows (`win32`, Python 3.13.5) on NTFS. On a case-sensitive filesystem R6-M1's vehicle does not
  exist, but replay must give one answer on both, which is why R6-M1 asks for `casefold` rather than
  `os.path.normcase`.
- `canonical_target` is an absolute path under the binding's repository root. The physical-prefix form in R6-M1 is
  sound only while every registration is made under one binding; the case-folded path form does not depend on that.
- Each registration still needs Stephen's LR-004 Decision, a human stop the probes do not model.

## 9. Files

Written: this report and `reviews/wp9-4-note-r6-review-artifacts/`:
- `r6_prefix_probe.py` and `r6_prefix_probe_output.txt` (R6-M1, R6-M2);
- `r6_extractor.py` and `r6_extractor_output.txt` (§5, R6-m2, R6-m3);
- `r6_dir_identity_probe.py` and `r6_dir_identity_probe_output.txt` (R6-i1).

Not edited: the note, the addendum, the register, any store, `.apm/`, `papers/`, `results/` or the vault.
