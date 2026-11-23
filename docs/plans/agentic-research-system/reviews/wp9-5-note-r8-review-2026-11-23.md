CONFIRM WITH FINDINGS

# Final focused review: WP9.5 design note, revision 8

| Field | Value |
|---|---|
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, revision 8, commit `526334c8`, blob `4d235950` (2,086 lines, 240,872 bytes; `wc -lc` and `git rev-parse` match the brief). Diff reviewed: `git diff c4c62b3b 526334c8` (72 insertions, 25 deletions, one file). Code cited at `dbd54fe3`. |
| Scope | Only the seven design statements revision 8 changed (R7-M1, R7-m1, R7-m2, R7-m5, R7-m9, R7-m10, R7-d1), the carried list (note 1424-1439), the change log (note 1712-1736) and their direct consequences. Not a re-review of the note. |
| Prior | `wp9-5-note-r7-review-2026-11-23.md` (`c4c62b3b`): REWORK REQUIRED, 0 Blocking, 1 Major, 10 Minor, 7 Info, plus R7-d1. |
| Brief | `handoffs/wp9-5-gemini-note-r8-followup-2026-11-23.md` (main checkout, untracked). The owner's pin decision (`handoffs/wp9-5-gemini-note-r6-followup-2026-11-22.md` section 1) was taken as settled and not relitigated. |
| Worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`, branch `docs/w9-wp9-5-design-note`, HEAD `526334c8`; `git status --short` empty before this report was written. |
| Reviewer | fresh session, no author context; skill `adversarial-design-review` |
| Date | 2026-11-23 |
| Verdict | **CONFIRM WITH FINDINGS**: 0 Blocking, 0 Major, 2 Minor, 6 Info |

"note NNN" is a line number in the note at `526334c8`. Other `path:line` values are at `dbd54fe3`.

## 0. Summary

Revision 8 does what the brief asked. All seven design statements are in the note, each at every place the r7 review listed, and each is consistent with the code. The carried list holds exactly the twelve items it should, in the r7 review's wording. No citation the diff adds or changes is broken, and nothing in the diff conflicts with the owner's pin decision. The note grew by 13,988 bytes (226,884 to 240,872, +6.2%), most of it the two sections the brief asked for.

Two Minor findings remain, both small:

- **R8-m1.** The new sentence "every exit 1 carries at least one `(rule, path)` pair" (note 723) is not true of three exit sites in the same tool that the revision left alone (note 734-735, 569, 609-611), and no precedence is stated when an exit-1 and an exit-2 condition occur together. The classification R7-m1 asked for is total for the buckets R7 named, not for the tool.
- **R8-m2.** The carried list points the code task at "row 1316" and "row 1315" (note 1430, 1432). Those are the r7 line numbers. In this note row 1316 is the `W9-T19 (CONVENTIONS.md)` row and 1315 is the table separator.

Neither changes an owner option or needs another revision. R8-m1 is a one-sentence design statement that can sit in the code brief next to R7-m1; R8-m2 is a two-word edit. The six Info items are for the code task.

One check the brief asked for specifically: the three new exception classes in `tools/_w9_detector_evidence.py` are sound and are not a mechanism beyond the brief. I ran `research_system/legacy/evidence.py` at `dbd54fe3` on nine input shapes (section 2.2): it raises the one class `EvidenceRefused`, with the same message, for unknown format, missing `format`, a non-object body, an extra key under a known format and a non-list `registrations`. The review's "name the exception classes" could not be met by naming existing ones because there are none (`EvidenceRefused.__subclasses__()` is empty). The pre-check before delegation is necessary, and sufficient if the helper takes its known formats from the delegate's own constants (R8-i1).

## 1. Findings

### 1.1 Blocking

None.

### 1.2 Major

None. I looked for a concrete failure the note's controls do not catch in three places and did not find one: the scoped closure tests (a defective row is still caught on the pin-advance PR, where `HEAD`'s `baselines[-1]` is the new row, and again by Rule 0.2 (ii) after merge); the exit-1 / exit-2 split (both outcomes are red, only the diagnosis differs); and the new exception classes (section 2.2).

### 1.3 Minor

- **R8-m1. The exit-code classification is total for the buckets R7-m1 named, but the new sentence over-claims for the tool (R7-m1 residual).**
  1. *Claim.* Note 723: "Under `--verdict-json`, every exit `1` carries at least one `(rule, path)` pair." Note 726 repeats it ("Exit `1` is reserved for violations of Rules 0 to 3 ... carrying >= 1 `(rule, path)` pair"), and note 1319, 1353 and 1451 restate it.
  2. *Evidence.* (a) Note 734-735 (section 6.6 item 2, unchanged): a `git_tracked` registered path missing or of the wrong object type at `<head>` "fail[s] closed (exit `1`)" with a message and no rule or path pair. Under `--verdict-json` with `--head <candidate>` (the comparison, note 583-584) this is reachable. (b) Note 609-611 and 569 (section 6.3 item 1): a shallow clone, or a `<baseline>` or referenced commit off `<head>`'s first-parent chain, is refused with no stated exit code. (c) Nothing says what a run prints when an exit-1 and an exit-2 condition both occur: for example a PR that deletes `registration-manifest.json` is a Rule 0.1 violation at `C` (note 680-681) and a missing required file at `<head>` (note 725). Step 5 (note 585) defines the diff only for "Exit `0`/`1`" and exit `2` as separate objects.
  3. *Failure scenario.* A candidate whose manifest names a registered path that is absent at the candidate head: the old and new tools both print `{"error": null, "verdicts": {}}` and exit 1. Step 5 shows no difference. This is the shape R7-m1 item 1 described (an exit-1 object with an empty verdicts map). Post-merge the run is still red, so this is a diagnostic and procedure gap, not a silent pass.
  4. *Impact.* Operations only. The comparison reads as clean-and-identical when both sides are red.
  5. *Disposition.* Fix now in one sentence, or carry to the code brief with the R7-m1 tests.
  6. *Proposed text* (append to note 726): "Every other exit-1 site under `--verdict-json` follows the same rule: a `git_tracked` registered path missing at `<head>` (section 6.6 item 2) exits 1 with `["Rule 0.2", "<normalized_path>"]`; a shallow clone or a baseline off the first-parent chain (section 6.3 item 1) exits 2. When a run meets an exit-1 and an exit-2 condition, exit 2 takes precedence and `--verdict-json` prints the error object only."
  7. *Affected.* Note 569, 609-611, 723-726, 734-735, 1319; R7-m1 tests; claim 2 (note 1382) and MC-2 (note 1353).

- **R8-m2. The carried list cites table rows by the r7 line numbers (R7-m6, R7-m8).** Note 1430 says "Restate row 1316's checks" and note 1432 says "reflect both in row 1315". At `526334c8` the rows are note 1319 (`Exit 2 & --assemble-only procedure`) and note 1318 (`Rule 0 & closure changes`); note 1315 is the table separator and note 1316 is the `W9-T19 (CONVENTIONS.md)` row. The list was copied from the review as the brief said, but the reference does not survive the revision's own line shifts. *Fix:* name the rows by title ("the `Exit 2 & --assemble-only procedure` row of section 12.1", "the `Rule 0 & closure changes` row"). *Affected:* note 1430, 1432.

### 1.4 Info (for the code task)

- **R8-i1. The helper's pre-check is sound; three details are unstated.** (a) The known-format set must be the delegate's own constant (`REGISTRATION_MANIFEST_FORMAT`, `evidence.py:40`), not a second list. If the helper accepted a format the delegate rejects (`evidence.py:122`), the failure would be labelled a schema error (exit 1) instead of an unknown format (exit 2). (b) Who converts the delegate's plain `EvidenceRefused` into `EvidenceSchemaError` is not said; the safe form is catch-and-re-raise only after the pre-check passed. (c) `require_registered` also raises `EvidenceRefused` for a membership failure (`evidence.py:129-130`, probe case G); the detector does not call it, but a blanket relabel would turn that into a schema error. Also: the change log (note 1719) justifies the helper placement with "`evidence.py:108-131` stays untouched pre-sign-off". Option A1 (Recommended) edits `evidence.py:40,114-131` (note 446-447, 1474), so the accurate reason is P-089's boundary: WP9.5 does not edit `research_system/legacy/` except through an owner point. The departure is recorded in substance (the "Note" in the R7-m1 row) though not labelled "departure".

- **R8-i2. R7-d1's "hash-bound exemption row" exists only under one Owner Point C option.** Note 1369 (HR-3 (d)) and note 1467 say a format moves "by a new file path, or by a hash-bound exemption row". The row is "not built" and exists only if Stephen picks `C-R0-exemption`; under `C-R0-permanent` only a new file path works. A row is also keyed by a merge commit hash that is unknown before the move merges, so an in-place move through the row has a red window. Suggest one clause: "(the exemption row exists only under Option C-R0-exemption and is entered after the move merges)". The note does not say that after a move to a new path the old file stays and must still be parsed (Rule 0.1, 0.2; note 722).

- **R8-i3. The scoped closure tests have two open edges.** (a) `test_derived_closure_tools_and_accepted_w9_are_codeowned` (note 594, 1322, 1396, 1453) is the one other test that derives the closure, and its tree is unstated. If it derives from the checkout, a non-owned closure module that adds an import of a new `tools/` module turns the lane red; in practice only `tools/w9_segmentation.py` could (under `I1-exempt-seg`), so this is a one-line statement, not a new burden. (b) Before L-1 there is no `baselines[-1]`, so the two scoped tests can run on synthetic repositories only; the first assembled-tree run is on the L-1 PR. The code task should say they skip, not pass vacuously, while `L1_LIVE is False`.

- **R8-i4. Four summary restatements are narrower than note 723-726.** Note 26, 52, 569 and 1382 list exit-2 causes as "unparseable/unknown-`format`/uncaught" and exit 1 as "reserved for Rules 0-3"; they omit import-time failures and a missing required `<head>` file. Harmless, since the body governs, but a reader of claim 2 alone gets the old rule. Two smaller points: note 1319 lists `run_w9_pinned_detectors.py` among the "entry shims" that "import inside guarded `main()`", but the wrapper has zero `tools.*` or `research_system.*` imports (note 55), so that test is vacuous for it; and `--require-manifest` (note 725) is in no flag list of section 6.3 and "once L-1 is active" has no tool-side definition (wording carried over from the pre-r8 exit-1 text).

- **R8-i5. Step 4's new sentence and the owner-facing label.** (a) "Run it with `--pr-map` from a prior run" (note 583): the tool's behaviour for a commit absent from the map, which the candidate always is, is not stated, so `gh api commits/<candidate>/pulls` could still run under Stephen's login. The precondition "read the step 3 diff before step 4" is the real control; the token limit constrains only the `gh` credential. Carry with R7-m3/m6. (b) The bullet at note 1451 is headed "decided by Stephen, `2026-11-22`" but now contains reviewer-derived consequences (R7-M1 scoping, R7-m1 classification, R7-m9). The owner should be told which parts are his decision and which he is asked to confirm; R7 named R7-M1 and R7-d1 as the two that touch what he was told.

- **R8-i6. Growth and housekeeping (section 4).** The garbled duplicate "Alongside `test_detector_closure_is_stdlib_only` ... and ..." sentence at the end of note 594 repeats the test names the sentence before it gives. The change log (note 1712-1714) is a `###` under "Change log: revision 6 to revision 7" (note 1687), and its "R7's proposed text for `§2` items" means the brief's section 2, not the note's. The §21.1 intro (note 1744) gained a clause saying R7 "reproduced all §21.1 items" although R7's timings differed (R7-i3, carried); it was not asked for and changes no check.

## 2. The seven fixes

### 2.1 Table

| ID | Status | Evidence |
|---|---|---|
| R7-M1 | **Resolved** | The review's sentence is in section 6.2.3 item 2 (note 594) and section 10.3 (note 1276), word for word. Both closure tests are scoped to the tree assembled from `HEAD`'s `baselines[-1]` and synthetic repositories at every other place that describes them: row note 1322, MC-2 note 1353, claim 16 note 1396, stop rule 6 note 1422, the pin-design bullet note 1451, Option F1 note 1499, change log note 1718. No sentence anywhere says they read the checkout; the only checkout-reading script is the one-off §21.1 item 9 check at `dbd54fe3`. The three green-lane cases are in the `L1_LIVE` row (note 1322): byte edit, new internal import, third-party import. The no-freeze reading is stated in F1 (note 1499). Residual: R8-i3. |
| R7-m1 | **Resolved** (residual R8-m1) | Under `--verdict-json` every exit 1 carries a pair (note 723): an evidence-validation failure is `["Rule 0.2", path]` exit 1 (`EvidenceSchemaError`, note 726) or exit 2 (`EvidenceParseError`, `UnknownEvidenceFormatError`, missing required `<head>` file, note 724-725). Classes named; §8.2 message ends "(if L-0b has landed, the pinned copy predates it: advance the pin)" (note 871, exact text); row note 1319 is a per-tool list; every entry shim imports inside the guarded function (note 627). The probe in 2.2 confirms the pre-check is needed and works. The totality statement is true for these buckets and false for three other exit sites (R8-m1). |
| R7-m2 | **Resolved** | "Lag silently" now covers new files, rules and constants, and a new key under a known `format` is an evidence-validation failure, at all five places the review listed: note 466, 597, 1369, 1451, 1518. "Every known evidence file present at `<head>` is parsed on every run" is at note 722 and repeated at those places. It does not conflict with the lazy per-commit read of `legacy-write-records.json` at `C` (note 634): the head parse checks format and shape; the per-commit read supplies Rule 1-3 semantics. No other "new keys" or "unread keys" sentence remains (grep over the note). |
| R7-m5 | **Resolved** | Note 583 carries the review's sentence in step 4: read the step 3 diff first; run with `--pr-map` from a prior run or a `pull-requests: read` token. Residual: R8-i5 (a). |
| R7-m9 | **Resolved** | HR-3 (c) and the pin-design bullet (c) say a pin advance takes in the whole current tree, including earlier unreviewed edits the PR's diff does not show (note 1369, 1451). HR-3 (b) and bullet (b) are narrowed to the review's wording: the lane runs the tool's unit tests and `--verify-watched-to-fail`, Rule 0 judges the row, a machine old-versus-new comparison is missing. Option I2 says "making a pin advance an ordinary PR" (note 1456); HR-3 says the same for I2 (note 1369). |
| R7-m10 | **Resolved** | Note 1660 reads "to be entered in `P-090`". No other past-tense use of `P-090` remains. |
| R7-d1 | **Resolved** | HR-3 (d) (note 1369) and Owner Point C (note 1467) both carry "After L-1 an evidence format moves by a new file path, or by a hash-bound exemption row, not in place", and say Options A1 and D3 are unaffected because they land before code. An in-place move is added to Owner Point C's list of causes. Residual: R8-i2. |

### 2.2 R7-m1: what `evidence.py` at `dbd54fe3` raises, and whether the helper separates it

`research_system/legacy/evidence.py:69` defines `EvidenceRefused`; `:108-111` is `_closed`, which raises it with "does not have the fixed format" when the key set differs; `:114-131` is `require_registered`, which runs `_closed` before it compares the format string (`:121-123`), then raises again for a missing registration (`:129-130`). I exported `dbd54fe3` to the scratch directory and ran `require_registered` on nine shapes (`r8_evidence_probe.py`, `python -B -I`; nothing written to the repository):

| Case | Raised |
|---|---|
| known format, valid | none |
| unknown format, same keys | `EvidenceRefused`, "manifest does not have the fixed format" |
| unknown format, extra key | the same |
| known format, extra key | the same |
| known format, `registrations` not a list | the same |
| known format, extra key inside an entry | `EvidenceRefused`, "manifest entry does not have the fixed format" |
| known format, registration absent | `EvidenceRefused`, "registration is not in the registration manifest" |
| missing `format` key | the same "fixed format" message |
| body is a list | the same |

`EvidenceRefused.__subclasses__()` is empty; invalid UTF-8 and bad JSON raise `EvidenceRefused` with one "is not JSON" message. So no existing class or message separates unknown format from closed-key failure, and the review's "name the exception classes" could only be met by defining some. Checking `body.get("format")` before delegating is both necessary and, if the format set is the delegate's own, sufficient: every `EvidenceRefused` that follows a passed pre-check is a known-format failure by construction (details in R8-i1). A non-object body has no `.get`; the note's "missing or unrecognized `format`" puts it in the exit-2 bucket, which is what the catch-all would do anyway.

Not a new mechanism beyond the brief: no new file, flag, gate, schema or workflow step. The three subclasses and the pre-check live in `tools/_w9_detector_evidence.py`, a file the note already creates, closes over and CODEOWNS (note 80, 592, 1453). The alternative, editing `evidence.py`, touches `research_system/legacy/`, which P-089 reserves to owner points.

## 3. The carried list (note 1424-1439)

Exactly twelve items: R7-m3, m4, m6, m7, m8 and R7-i1 to i7. The brief's list. Compared with the r7 review's wording:

| Item | Faithful? | Note |
|---|---|---|
| R7-m3, m6, m7, m8, i1, i2, i3, i4, i5, i7 | Yes | Wording is the review's; no answers designed. |
| R7-m4 | Almost | The review offered "state the minimum interpreter, or that an older one exits 2 with a named message"; the list asserts both and adds "never overwriting files". Light design creep. |
| R7-i6 | Almost | The review reported what six bad inputs do; the list turns them into "include ... in pin-step tests". Reasonable, not in the review. |
| R7-m6, m8 | Row references stale | R8-m2. |

Nothing carried needs a design statement before code. The closest is R7-m7, the mechanism by which `admission-controls` assembles the tree for the scoped tests of R7-M1. The r7 review itself gave two options that live inside pytest (extract the workflow heredoc, or call the checkout's wrapper with `--assemble-only --rev HEAD`), so neither adds an edit to `ci.yml:212` or `test_ci_platform_policy.py:228` beyond what Owner Point F lists. R7-i4 and R7-i5 carry nothing for the code task; listing them is harmless. R7-m4's I3 behaviour (the procedure fails at row k under I3 unless `--assemble-only` skips the I3 check) is an optional-I3 consequence the owner is not asked to decide.

## 4. Collateral, citations, growth

**Contradictions with unchanged text.** None with an owner decision. One contradiction with an unchanged exit site (R8-m1); stale summary restatements (R8-i4). The Rule 0.2 label for `EvidenceSchemaError` is a catch-all: §6.5 Rule 0.2 lists the ledgers, `walk-baseline.json` and the L-0b classification, not `registration-manifest.json` (Rule 0.1) or `detector-controls.json` (Rule 0.3), though its failure line already says "append-only, validation, or immutability" (note 693). Acceptable; the code task can add one clause.

**Citations.** The diff adds or changes one new pair, `research_system/legacy/evidence.py:108-131` and `:69` (note 723); both resolve to what the note says (section 2.2). The other path:line forms on lines the diff re-prints are unchanged from r7: `evidence.py:52-54,277-362`, `export_recheck.py:32-89`, `check_bypass_merges.py:41,135`, `affected_research_tests.py:120-147`, and the bare-name forms `ci.yml:166-216` (and `:210`, `:212`), `research-system-suite.yml:8-9,15,17`, `test_ci_platform_policy.py:175-229`, `admin-bypass-guard.sh:13-18`. I resolved all of them by hand against `dbd54fe3`: all in range and pointing at the stated text. `r8_cites.py` over the added lines found 12 distinct pairs, 0 out of range (4 bare names resolved by hand).

**Growth.** +13,988 bytes, +47 lines (226,884 to 240,872; 2,039 to 2,086). The brief asked for §15.3 (3,281 bytes) and §20.1 (3,535 bytes); the remaining 7,172 bytes are spread over about 20 places: the R7-M1 sentence twice as requested (about 2 KB), the section 6.6 rewrite (about 2.3 KB), HR-3 and the pin-design bullet (both restate (a) to (d)), a row each in the revision table and the prior-reviews header, and a clause in the §21.1 intro. Justified by the brief's own requirements; I do not recommend cutting now, because trimming restatements would risk the drift the restatements exist to prevent. Only the duplicate sentence in note 594 is worth removing (R8-i6).

**Anything the brief did not ask for.** Bookkeeping rows (status, prior reviews, revision table) and the §21.1 intro clause; the shim wording; the parenthetical on missing-file versus deletion (note 725). None adds a mechanism. The §21.1 clause "R7 ... reproduced all §21.1 items (`PIN_CASES_OK: 27` + 27 extra cases), YAML/`bash -n`, and `219` citation pairs (`0` out-of-range)" matches the r7 review's section 2.

**Bytes.** No BOM, no CR in the note. `git status --short` empty before this report.

## 5. Readiness for the owner

The note is ready to go to Stephen for the owner-point decisions, in the order I, C, F, then A, B, D, E, G, H, J, K. The two statements that touch what he was told are present where he will read them: the closure tests run on the pin, not the checkout, so import edits to the 13 non-owned modules need no pin advance (note 1499), and an evidence format cannot move in place after L-1 (note 1467). R8-m1 and R8-m2 can go to the code brief; neither alters an option. If a ninth revision is wanted at all, it would be R8-m1, R8-m2 and the one-clause R8-i2, and it would need no further independent review.

Carry to the WP9.5 code task, with the r7 list in note 1424-1439: R8-m1 (each exit-1 site under `--verdict-json` gets a pair or exit 2, plus precedence, with a test that enumerates the sites), R8-i1 (known-format source, catch-and-re-raise order), R8-i3 (what the scoped tests do before L-1; tree of the CODEOWNERS test) and R8-i5 (a) (`--pr-map` for the candidate).

Unchanged residual risks the note keeps stating: the detector is post-merge and a human merge is the only preventive control for a pin advance and the code-owned paths; a pin advance takes in the whole current tree; lag is silent for new files, rules and constants; a post-merge Rule 0 failure stays red unless the exemption row is chosen; the weekly vault run is self-attested.

## 6. Commands run

All read-only on the repository. No vault file was read or opened, no `gh` call was made (no live check was needed: revision 8 changes no ruleset or live-state claim), the U-3 probe and U-4 script were not run, no `uv`, `pytest` or workflow was run, nothing was pushed. No file was composed with a heredoc or `python -c`.

- `git` in the worktree: `rev-parse HEAD`, `rev-parse HEAD:<note>`, `branch --show-current`, `status --short` (empty before this report and after each scratch run), `diff c4c62b3b 526334c8` (stat and full text, saved to scratch), `show dbd54fe3:<path>` for `evidence.py`, `ci.yml`, `research-system-suite.yml`, `test_ci_platform_policy.py`, `admin-bypass-guard.sh`, `show c4c62b3b:<note>` (size), `log --oneline`, and one `git archive dbd54fe3 research_system tools/w9_segmentation.py` extracted into the scratch directory.
- Reads: the note around every changed hunk and every other place that names the closure tests, exit codes, lag or the carried items (sections 1, 2, 6.1 to 6.6, 8.2, 9.2, 10.3, 12.1, 13.1, 13.2, 14, 15, 16, 17, 19, 20, 21.1); the r7 review in full; the brief; `evidence.py:55-135` at `dbd54fe3`; `claims-checklist.md` (carried-obligation and prescribed-correction entries).
- `grep`/`sed`/`awk`/`wc`/`od`/`tr` over the note for the restatement sweeps, row and cell counts, byte and CR checks, section sizes (`### 15.3`: 3,281 bytes; `### 20.1`: 3,535 bytes).
- Scratch scripts, written with the Write tool to `C:\Users\steph\AppData\Local\Temp\claude\e088a017a981a492\f302c5e4-50e0-4fcc-b0af-3a36e9983c74\scratchpad\`: `r8_cites.py` (path:line check of the added lines against `dbd54fe3`) and `r8_evidence_probe.py` (nine shapes against the exported `evidence.py`), both run with `python -B -I`; the export is in `...\scratchpad\base`; the diff is `...\scratchpad\r8.diff`.
- Not re-run, as the brief said: §21.1. Not verifiable here: the behaviour of the six unwritten tools (exit codes, JSON shape, `--assemble-only`, `--pr-map` for an absent commit), the hosted `windows-latest` walk time (`UNVERIFIED-5`), who may write Actions variables (`UNVERIFIED-4`), the CI token's `rule-suites` read (`UNVERIFIED-1`), the scratch-store timing (`UNVERIFIED-3`).
