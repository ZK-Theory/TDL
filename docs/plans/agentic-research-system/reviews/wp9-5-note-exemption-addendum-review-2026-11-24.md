REWORK REQUIRED

# WP9.5 design note: independent review of the Rule 0 exemption-row addendum

| Field | Value |
|---|---|
| Date | 2026-11-24 |
| Reviewer | Fresh independent adversarial reviewer (`adversarial-design-review` skill); no author context |
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md` at `b3500098` (diff `git diff 79d8a684 b3500098`, one file, +88 / -22). New section 6.5.1 plus edits in sections 1, 2.1, 6.1, 6.2.2, 6.5, 12.1, 13.1, 13.2, 14, 16.2, 17, 20.2 |
| Citations | "note NNN" is a line of the note at `b3500098`. Code is at `dbd54fe3` |
| Governing text | Brief `handoffs/wp9-5-gemini-note-exemption-addendum-2026-11-24.md`; `P-090` item 2 C and item 4 (`03-decisions-and-open-questions.md` at `b3500098`, lines 6192-6196 and 6228-6230); R7-d1 in `wp9-5-note-r7-review-2026-11-23.md:93` |
| Not relitigated | The owner's pin design ("pin, no lockstep"); the rest of the note (passed r8) |
| Edits made | None to the repository. This report is the only file written |

## 1. Summary

The addendum is a careful piece of work. It chooses the right home for the list (a closed top-level key in `walk-baseline.json`, present as `[]` from row 0), a closed seven-key row, an exact six-field tuple, a hash-bound register slice with a stated line grammar, and a strict first-parent ordering. Every attack I tried on forgery by ordering (same-PR register entry, backdated `source_commit`, off-chain commit, same-commit row, reused entry for a different tuple) fails against the design, for the reasons in section 7. The scope rules were kept: the diff touches none of 4.2.2, 4.3.3, 10.2, 10.3, 15.1, 15.3 or 21, as the change log claims, and the code citations I checked (`evidence.py:36`, `:108-111`, `:159-176`, `:179-187`) are correct.

Two things are not sound enough to go to code as written.

1. **X-M1.** The note does not say what Rule 0 does when an evidence file is malformed at `P1` or at an intermediate commit. Both available readings break a stated property: either the "unexemptable, checked unconditionally" invariants cannot be evaluated behind a malformed commit (so two exemptable rows launder a change to `baselines[0].baseline_commit`), or a historically unparseable ledger exits 2 for ever and no exemption can reach it (which includes the likeliest "broken append-only file", a merge-conflict marker in JSON).
2. **X-M2.** The one append-only ledger whose faults cannot be exempted is the exemption list itself. One typo in an exemption row (a wrong `entry_sha256`, or a register slice edited between candidate and merge) leaves Rule 0 permanently red, and the only exit is an undesigned re-baseline at a new file path. Nothing requires a pre-merge run of the tool on the PR that appends the row.

Both fixes are additive (a few lines in 6.5.1 and 6.6 item 1, and four controls). Neither reverses an owner decision. Counts: 0 Blocking, 2 Major, 7 Minor, 7 Info.

## 2. Findings

### Major

#### X-M1. Behaviour on a malformed intermediate version of an evidence file is undefined, and both readings break a stated property

1. **Claim.** Note 752 says the unexemptable invariants are "checked unconditionally so a same-commit row on another field never masks them"; note 761 says extra top-level keys on `walk-baseline.json` are exemptable, "clearing `$` only"; MC-2 (note 1404) claims the tool never clears the unexemptable invariants.
2. **Evidence.** `EvidenceSchemaError` is raised "at `P1` or `C`" (note 777), and a closed-key failure returns no content (`evidence.py:108-111`, `_closed` raises). The note never says what Rule 0.2's append-only and immutability comparisons do when one side failed validation. `EvidenceParseError` (unparseable JSON) is exit 2 and "unexemptable" (note 775, 760), and is not scoped to `<head>`; only the schema error names `P1`/`C`. The `"$"` row keys on the two file blobs only (note 743, 764).
3. **Failure scenario A (laundering).** Commit X adds a stray top-level key to `walk-baseline.json`: a schema fault at `("Rule 0.2", path, "$")`, exemptable by note 761. Commit F removes the key and, in the same commit, changes `baselines[0].baseline_commit` (or deletes a `rule0_exemptions` row, or rewrites `d8_rule_suites_limit_decision_ref`). `P1(F)` is X's malformed file, so the comparisons that enforce item 4 cannot run on a strict parse. The only finding at F is the schema fault on `P1`, tuple `(F, Rule 0.2, path, "$", blob_X, blob_F)`. Two valid rows (X and F), each backed by a register line that names only 8-hex blob prefixes (note 749), turn the walk green with an unexemptable invariant broken. The "extra keys" and "self-exemption" controls (note 1369) use schema-valid fixtures and pass.
4. **Failure scenario B (a named cause is unreachable).** A merge-conflict marker or trailing comma in `legacy-write-records.json` at X, fixed at F. This is the most likely "broken append-only file". The walk re-parses X's version on every run. By the literal text this is `EvidenceParseError`, exit 2, unexemptable (note 760), so every later run exits 2 for ever. If instead the tool turns a historical parse failure into a fault, the note does not say so, and item 4 excludes it.
5. **Failure scenario C (format).** After an in-place format move (R7-d1), the latest pin re-parses `P1(C_f)` in the old format on every run. If any later pin drops the old reader, `UnknownEvidenceFormatError` (exit 2, unexemptable) makes the walk permanently red. Note 766 asks for a pin that supports both formats once, not for ever.
6. **Impact.** The self-protection guarantee the brief asked for (question 1) is not delivered for the two-step case; one of the five causes the exemption row exists for is unreachable; the red window in R7-d1 can become permanent.
7. **Disposition.** Fix now, in the note, before the code brief. Proposed text, to add to 6.5.1 item 4 and to 6.6 item 1:
   - "Malformed intermediates. When an evidence file fails parsing or schema validation at `P1` or `C`, Rule 0.2's append-only and immutability comparisons (including every unexemptable invariant of item 4) run on raw `json.loads` reads (no closed-key validation) between the nearest earlier first-parent version that parses and the first version at or after `C` that parses. A violation is reported at the commit that produced the later version, and no row clears it. A `"$"` row on a schema fault clears the schema fault only."
   - "`EvidenceParseError` or `UnknownEvidenceFormatError` at a commit other than `<head>` is a `Rule 0.2` fault at that commit (location `"$"`, exit 1, exemptable under item 3). At `<head>` it stays exit 2."
   - "A pin that replaces an evidence format in place keeps the superseded reader for as long as the walk covers the superseded versions."
   - Add to 12.1: (i) X adds a stray key, F removes it and rewrites `baselines[0].baseline_commit`, rows for X and F: exit 1 at F; (ii) conflict marker at X, fixed at F, rows for X and F: exit 0 with no row for F's unchanged-blob successors; (iii) a pin that drops the old reader: exit 2.
8. **Affects.** 6.5.1 items 2, 4, 5; 6.6 item 1; 12.1 row 1369; MC-2 (note 1404); HR-3 (d); `P-090` item 2 C.

#### X-M2. An invalid exemption row can never be recovered from, and no pre-merge check is required

1. **Claim.** Note 746: "any failure emits an unexemptable `Rule 0.2` error at `C_ex` and grants no exemption". Note 753 adds "invalid appended rows" to the unexemptable list. The brief required only that the list not clear its own *append-only* tampering (brief section 2, question 4).
2. **Evidence.** The location grammar (note 743) has no `rule0_exemptions[k]` form, so the fault at `C_ex` has no tuple that a row can name. The list is append-only, so the bad row stays. The only recovery named is a new file path for `walk-baseline.json` (note 766, "mandatory"), and that path is not designed anywhere: the pin step (note 1186-1193), the tool's known-file list (note 773) and the L-1 test (note 1316 onward) all hardcode `walk-baseline.json`. The comparison procedure with `--head <candidate>` is required for pin advances only (note 579), so nothing runs the tool on an exemption PR before it merges.
3. **Failure scenario.** Stephen appends a row after a post-merge failure. The row has a mistyped `entry_sha256`, or the register slice is edited by another PR between his candidate run and the squash. At `C_ex` Rule 0.2 reports an invalid row. No row can clear it, and the bad row cannot be removed. Rule 0 stays red from `C_ex` onward, which is exactly the "red for good" state the exemption row exists to prevent (brief section 1). If the defect is row-internal schema (an extra key), strict whole-file validation at `<head>` also fails, so the tool cannot read `baselines[0]` or the pin source in the same file (note 1192-1193 is the pin step; the tool's own read is the one at risk). The control list (note 1369, "extra/missing keys", "mismatched ref") proves the failure, never a recovery. Compare: a defective `baselines[k]`, `acknowledged[j]` or `ruleset_gap_acknowledgements[j]` row is exemptable (note 761); the mechanism's own rows are the only unrecoverable ones, and they are written in the panic situation the mechanism exists for.
4. **Impact.** Operational: one hand-typed hash can end the post-merge detector's usefulness until an undesigned re-baseline. It also makes a rare owner action unusually costly, which pushes toward not using the mechanism.
5. **Disposition.** Fix now, plus one owner decision. Proposed text:
   - To 6.5.1 item 3 (a required step, not a new mechanism): "A PR that appends to `rule0_exemptions` or otherwise changes `walk-baseline.json` carries, in its description, the output of `check_legacy_writes.py --ruleset-check skip --baseline <b0> --head <candidate>` (the 6.2.2 step 4 command, no `--verdict-json` diff) showing no new `Rule 0.2` fault at `<candidate>`. The register slice's SHA-256 is recomputed against `<pr_base>` after the last rebase."
   - To HR-3: "An exemption row that makes `walk-baseline.json` unparseable at `<head>`, or that is a schema-valid but invalid row, is recoverable only by re-baselining at a new path (not designed here)."
   - Owner option (Stephen to choose): allow a *validity* fault of an appended row (not deletion or mutation of an existing row, not a non-empty row 0, not a parse failure at `<head>`) to be cleared by a later valid row at location `rule0_exemptions[k]`. This is not self-exemption in the sense P-090 forbids: the invalid row grants nothing, so clearing its fault widens nothing, and the clearing row is itself validated in full. My recommendation is to adopt the required pre-merge run now and take the option only if Stephen wants a recovery that does not need a re-baseline.
6. **Affects.** 6.5.1 items 3, 4; 12.1; HR-3; Owner Point C; `P-090` item 4.

### Minor

**X-m1. Ordering edges (question 3).** `fp_index` is built from `rev-list --first-parent --reverse <b0>..<head>` (note 748), which excludes `b0`. I checked this in a scratch repository: for the first commit after `b0`, `P1` is `b0` and it is not in the index (scratch session, section 8). A row appended there would raise a `KeyError`, which the `main()` wrapper turns into exit 2 (note 628) instead of an invalid-row fault. The fix is one clause: "`fp_index[b0] = -1`; a row at a commit whose first parent is `b0` is invalid". This cannot occur for a valid row (`commit < source_commit <= P1` needs at least two commits after `b0`) and does not occur at the L-1 commit, because row 0's list is `[]`. The sentence "consistent with `is_ancestor`" (note 748) is also loose: `is_ancestor` is `merge-base --is-ancestor` over all parents (`evidence.py:159-176`), while `fp_index` is first-parent only. They differ for a commit merged as a second parent, and the note's stricter rule is the right one. Say "stricter than".

**X-m2. Granularity and `location` (question 2).** The tuple names a fault *site*, not a fault. The brief asked that one row clear one violation. Three gaps:
- (a) A `baselines[k]` row that fails both (ii) and (iii) is cleared in full by one row written for a "slice typo"; the `R0-EXEMPT` line carries no check discriminator, so a pin-integrity mismatch (ii) hides behind a typo exemption. Add the failed check to the location (for example `baselines[3]#iii`), and test it with a sibling-sub-check control.
- (b) `location` is undefined for: a top-level non-schema fault (for example `d8_rule_suites_limit_decision_ref`, `rule0_exemptions` mutation); a schema error inside a row (the strict validator fails the whole file, so it cannot name an index); an index for a deleted or mutated row (index at `P1` or at `C`?); and the `old_blob == new_blob` form (note 744), which is attached to "`<head>`/`P1` `EvidenceSchemaError`" although a `<head>` fault has no commit (so a row for it could never satisfy `commit < C_ex`) and §6.5 evaluates only commits whose diff touches the file.
- (c) The L-0b `ACCEPTED_CONVENTIONS_CLASSIFICATION` path in the allowed-pairs list (note 742) is not yet a path, so the table cannot be closed.
- Null handling itself is correct (section 3, question 2).

**X-m3. Wrong rationale for `format` (question 1).** Note 756 says `format` is "read by §10.2 pin assembly". It is not: the pin heredoc reads `wb["baselines"][-1]["detector_closure_blobs"]` and `wb["baselines"][0]["baseline_commit"]` only (note 1192-1193; no `format` anywhere in the heredoc, checked). Also, with one known format, "`format` immutable" is vacuous: any change is `UnknownEvidenceFormatError` (exit 2) before Rule 0 runs. The unexemptability stands, but the reason should be §6.6 item 1 alone. Correct the sentence.

**X-m4. Step 6 contradicts 6.5.1 (question 4).** Note 587: "post-merge Rule 0 recovery uses §6.5.1 `rule0_exemptions` in a later PR, never the same commit". 6.5.1 only forbids `commit == C_ex`. A pin advance at `C_k` that makes the new tool flag an old `V` in `(b0, pr_base]` may carry the exemption rows for `V` in the same commit, provided the `R0-EXEMPT` lines are already in a register slice at `P1`; that avoids a red window after the pin advance. As written, the note creates a red window it does not need and a second PR. Reword to: "never the same commit as the violation".

**X-m5. R7-d1 and P-090 wording (question 4).** The addendum's reading is the only coherent one and matches R7-d1's own scenario (r7 review line 93: the move "stays red until the exemption row"). So there is no contradiction with P-090's "never in place". But the sentence "moves by a new file path, or by a hash-bound exemption row ... not in place" (notes 1420, 1535) describes an in-place move as "not in place". Say "never in place without a cleared Rule 0 fault". Three further points:
- P-090 allows an exemption row for any evidence format; the addendum excludes `walk-baseline.json` and requires a new path. That is a narrowing of a decision, so it needs Stephen's confirmation (see section 6).
- The "red window" is the interval between the merge of the format change and `C_ex`; during it the post-merge run is red.
- "Deleted-then-restored" (note 761) needs two rows (the deletion `new_blob: null`, and the re-creation at `old_blob: null`, which is itself a Rule 0.2 fault for `legacy-write-records.json` because every re-created entry is "new" under note 684). Nothing binds the restored bytes to the deleted file's last state; the exempted deletion launders any re-created content. Require the register line for a deletion row to name the restoring commit and its blob, or accept the risk in HR-3.

**X-m6. Controls (question 7).** See section 4. Summary: the nine controls name the right cases but bundle many guards per control, do not require otherwise-valid rows, and omit six cases.

**X-m7. Stale and garbled text.**
- Note 753 says "non-empty `[]` at row `0`"; it means "any value other than `[]`".
- The section 16 intro (note 1513) still says "his decision is needed on open choices across all eleven points ... Nothing here decides for him", while 16.2 now records the decision. Section 15.1 item 3 (note 1459) is in the same state, but that sentence predates the addendum.
- The section 17 row 17 text in the section 1 table says "(not yet reviewed)"; remove after this review.

### Info

- **X-i1. Placement (question 1).** The "I1 CODEOWNERS" reason (note 723) is redundant: the whole directory `/.research-system/evidence/w9/` is owned (note 465), so a second file would be owned too. The real reasons (no new `06v-addendum` row, no new `<head>` parse target, one `git show` for `--acknowledged-from`) stand. The cost of co-location is blast radius: a defective exemption row sits in the file that holds the pin and the walk start (see X-M2). Accept, but state it.
- **X-i2. Cleared faults leave no trace.** Cleared tuples are omitted from `verdicts[commit]` (note 765) and nothing says the tool reports them. Add one stderr or `$GITHUB_STEP_SUMMARY` line per cleared tuple naming the row index, so exemptions stay visible in CI output. This is output only, not a mechanism.
- **X-i3. Authority and "before the PR".** The register is not code-owned (HR-1, note 1418), so the `R0-EXEMPT` line proves age, not authorship. The authority is the CODEOWNERS review of the row PR. "Already on `main` before the PR" (note 748) is guaranteed as "before the appending commit": under squash-only (ruleset, note 138) it is the PR; a bypass actor could push a register commit and a row commit together, and both would validate. `source_commit` is used only for the inequality (the slice is read at `P1`), so it is a declaration, not a proof. Same as `acknowledged`; HR-1 already carries this.
- **X-i4. Rule 0.1 exemption.** Exempting a deleted registration entry leaves it deleted; Rules 1 and 3 use `Manifest(P1) union Manifest(C)` per commit, so the path is unguarded afterwards. M-6 `--check` (store equality, MC-1) is the second tripwire. Worth one sentence in HR-3.
- **X-i5. Flag name.** `--acknowledged-from` now also supplies `rule0_exemptions` (note 585). 6.3 item 4 (note 625), unchanged, still describes the flag by its old name. Consider documenting in 6.3 item 4 in the code brief.
- **X-i6. Size and scope claim.** Note 243,205 to 257,719 bytes (+14,514) and 2,103 to 2,169 lines (+66); 6.5.1 alone is 8,756 bytes in 50 lines. The "untouched" list in 20.2 is accurate: the diff has no hunk in 4.2.2, 4.3.3, 10.2, 10.3, 15.1, 15.3 or 21.
- **X-i7. Slice extraction.** "Extract the `### <id>` slice" (note 749) is "identical to `acknowledged`", but no section defines where a slice ends, and 4.2.3 (note 293) reads the D-8 slice at `source_commit` while 6.5.1 reads it at `P1`. Pre-existing and shared; for the code brief.

## 3. The seven brief questions

| # | Question | Answered | Basis |
|---|---|---|---|
| 1 | Self-protection | **Partly** | `rule0_exemptions`, `format`, `baselines[0].baseline_commit`, d8 and `walk-baseline.json` deletion are unexemptable and tested on valid files. A malformed intermediate defeats this (X-M1). Forgery by ordering fails (section 7). An invalid row is unrecoverable (X-M2) |
| 2 | Exactness | **Partly** | Tuple is exact per fault site, not per fault (X-m2 a). `location` is undefined for several cases (X-m2 b). Creation uses `old_blob: null` (a creating commit sees `blob_at(P1, path)` = `None`, checked at `evidence.py:179-187`; `diff-tree` gives the zero OID, checked in the scratch repo), deletion uses `new_blob: null`, both-null is refused. Correct |
| 3 | Ordering | **Soundly** | `fp_index[commit] < fp_index[source_commit] <= fp_index[P1(C_ex)] < fp_index[C_ex]` is implementable and strict. One edge (X-m1): `P1 == b0`. The L-1 commit is safe because row 0 is `[]` |
| 4 | Interactions | **Partly** | `--verdict-json` and `--acknowledged-from <pr_base>` are consistent (rows from `pr_base`, candidate faults stay visible). Pinned-copy rule is consistent: row 0 is created at L-1 by the first pin, so no earlier pin meets a file without the key. Step 6 contradicts 6.5.1 (X-m4). R7-d1 is coherent with P-090 but worded confusingly (X-m5). Dual-format must persist (X-M1 C) |
| 5 | Scope | **Soundly** | No new mechanism beyond `fp_index` and the `R0-EXEMPT` grammar, both within the row. The seven sections claimed byte-identical are untouched (X-i6). Stale section 16 intro (X-m7) |
| 6 | d8 first transition | **Answered** | Section 5 |
| 7 | Controls | **Partly** | Section 4 |

## 4. Controls check (section 12.1, note 1369)

Test of each: does it prove the rule it names, and would it fail if its guard were removed?

| Control | Proves | Fails without its guard? | Gap |
|---|---|---|---|
| Positive: violation, pre-existing slice, valid row, walk exit 0 | Clearing works | Only if the same history without the row exits 1 | Add the paired no-row run. A fixture bug that never triggers Rule 0 would pass vacuously |
| N1 wrong 6-tuple / sibling `location` | Exact match | Only for the one varied field | Parametrise over all six fields, and add a sibling *sub-check* case (X-m2 a) |
| N2 missing / mismatched `disposition_ref` or slice | Hash-bound slice | Four cases bundled | One fixture per case; add "slice at `P1` differs from the one hashed at candidate time" (feeds X-M2) |
| N3 `source_commit` ordering (`<= commit`, `>= C_ex`, off-chain) | `fp_index` | Yes for the three listed | Add `commit` itself off the first-parent chain (a second-parent commit), `commit == b0`, and `P1 == b0` (X-m1) |
| N4 self-exemption plus `format`, `baselines[0].baseline_commit`, d8, deletion | Unexemptable list | **No.** Five guards in one control; the unexemptable faults are red with or without a row, so any invalid row also passes | Each row must be otherwise valid and be shown to clear when re-pointed at an exemptable location. Add the malformed-`P1` variants (X-M1). The deletion case exits 2 if `<head>` lacks the file (note 776); fix the fixture to delete at D and restore at R, `head = R` |
| N5 deletion / mutation of an existing row | Append-only | Yes | Pair with a row that tries to exempt it |
| N6 extra / missing keys | Closed keys | Yes | Say whether on the row, the `disposition_ref`, or the top level (they differ in effect, X-M2) |
| N7 row in the same commit as the violation (`commit == C_ex`) | Strict `<` | Not constructible with real git | The row would have to contain its own commit's hash. Realistic variants: `source_commit == commit`; violation commit immediately followed by the row commit with no register commit between |
| N8 recurrence at `C2 > C_ex` | No blanket clearing | Yes (subsumed by N1: a later commit has a different `commit`) | Fine |

Missing controls (add): `rule` set to `Rule 1` to `Rule 3`; `(rule, path)` mismatch (for example `Rule 0.1` with `legacy-write-records.json`); `location` forms outside the grammar (`rule0_exemptions[0]`, `baselines[01]`, `baselines[-1]`); both blobs `null`; duplicate tuple; one register entry carrying two lines used by two rows; the three X-M1 scenarios; the X-M2 pre-merge-run requirement as a documented step.

## 5. d8 recommendation for Stephen: `d8_rule_suites_limit_decision_ref` first null-to-non-null

**Recommendation: keep it unexemptable, and make the L-1 rehearsal and a pre-merge candidate run carry the real reference.** Reasons:

1. **An exemption cannot repair it.** The field is immutable once non-null (note 685), and `--ruleset-check ci-d8` independently refuses to run unless the reference verifies at `<head>` (note 293). An exempted but defective first value silences one Rule 0 fault while the other still fails closed on every run. An exemption row would therefore buy no recovery.
2. **There is probably no later transition.** U-3 recorded rule-suites as HTTP 403 (note 1466), so D-8 applies and row 0 will carry a non-null reference at creation. The "first transition" is creation at the L-1 commit.
3. **The cost is small and early.** If the value is defective, the first post-merge run fails, before any history exists. A re-baseline at that point costs almost nothing (no walk to preserve).
4. **The check can be run before merge.** Add to the L-1 exit criteria (note 1316 onward, 10.2 item 5): the throwaway rehearsal fixture carries the real `d8` reference and real row 0, and the L-1 PR is run through the tool with `--head <candidate>` before merge. This is the same control X-M2 asks for.

Alternative for Stephen, not recommended now: define immutability to bind only after a value has *passed* its check once, so a never-validated value may be replaced one time. That is a new mechanism, outside the brief's scope, and it is only worth considering if he wants recovery without a re-baseline.

## 6. Owner decisions and revision plan

**Owner decisions (Stephen):**
1. X-M2: adopt the pre-merge run as mandatory (recommended); decide whether to allow `rule0_exemptions[k]` validity faults to be cleared by a later valid row.
2. X-m5: confirm that `walk-baseline.json` moves only by a new file path, narrowing P-090 item 2 C's "or by an exemption row" for that file; and that a new file path is a re-baseline to be designed when needed.
3. d8: keep unexemptable (section 5).

**Immediate corrections (author):** X-M1 text and controls; X-M2 text; X-m1, X-m3, X-m4, X-m5 (wording), X-m7; X-i2 one line.

**Later work (code brief):** X-m2 (b, c), X-m6 control list, X-i5, X-i7. No revision of the note is needed for these beyond naming them as obligations.

## 7. Attacks that failed (and why)

- **Register entry written in the same PR.** The slice is read at `P1(C_ex)` (note 749). Under squash-only (note 138) the register commit and the row cannot be in one commit, so the slice is absent at `P1`. A bypass push of two commits would pass, but that is the owner and X-i3.
- **Backdated `source_commit`.** Free to choose anywhere in `(commit, P1]`, but the slice naming `commit[:8]` and the blob prefixes can exist only after `commit` exists, so backdating buys nothing; a pre-written slice cannot name a hash that does not exist yet.
- **Commit off the first-parent chain.** Not in `fp_index`; invalid (note 748, 754).
- **Same-commit row.** Needs the row to contain its own commit hash; infeasible. The strict inequality is a declaration check (X-m6).
- **Reused entry for a different tuple.** The line grammar is per tuple (note 749); the line must match all six fields.
- **Pinned-copy rule.** Consistent: the pins that exist after L-1 all descend from the first pin, which is built from the WP9.5 code that knows the key. R7-m2 would make a late-added key an exit-1 fault, which is why row 0 carries `[]`.
- **`null` for creation and deletion.** Correct (section 3, question 2); both-null refused; `walk-baseline.json` deletion refused.
- **A format move on `walk-baseline.json`.** Excluded (note 766); only the new-path route remains, which is undesigned (X-m5, section 6).

## 8. Commands run and what I could not verify

Commands (all read-only; scratch files under the session scratchpad):
- `git branch --show-current`, `git log`, `git cat-file -t` for `b3500098`, `dbd54fe3`, `79d8a684`, `0e1269bd`, `526334c8`, `ae608701`; `git merge-base --is-ancestor 79d8a684 b3500098`.
- `git diff 79d8a684 b3500098 -- <note>` (stat and full diff); `git show b3500098:<note>` and `79d8a684:<note>` (line counts and bytes by `wc`); `git show b3500098:03-decisions-and-open-questions.md` (P-090, lines 6147-6261); `git show ae608701:...r8...md` and `c4c62b3b:...r7...md` (grep for R7-d1, exemption).
- `git show dbd54fe3:research_system/legacy/evidence.py` (lines 36, 77-107, 108-111, 159-188) to verify the four citations.
- Grep over the saved note for `exemption`, `acknowledged-from`, `EvidenceSchemaError`, `EvidenceParseError`, `fp_index`, `d8_rule_suites_limit_decision_ref`, `merge_method`, `format` (inside the pin heredoc, none).
- A scratch git repository (outside the project): four commits, then `git rev-list --first-parent --reverse b0..HEAD`, `git rev-list --parents -n1`, `git rev-parse --verify --quiet b0:nonexistent` (exit 1) and `git diff-tree -r --no-renames -z b0 HEAD~2` (zero OID on creation). Confirmed that `P1` of the first commit after `b0` is not in the index, and that creation yields the zero OID.
- No GitHub calls, no vault reads, no edits to the note, the register or any store.

Not verified:
- Behaviour of the unwritten tool: every statement about how the tool treats a malformed `P1` is a reading of the note (it is silent), not a test.
- `git rev-list --first-parent <b0>..<head>` when the hidden side contains merge commits. I ran only the linear case. Under squash-only `main` this does not arise.
- The slice-extraction rule (where a `### P-0xx` slice ends) is not defined in the note (X-i7).
- The live ruleset (squash-only, one bypass actor) was read from the note's own record, not re-queried.
- Whether Stephen intends P-090's "or by an exemption row" to include `walk-baseline.json` (section 6, decision 2).
