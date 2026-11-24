CONFIRM WITH FINDINGS

# WP9.5 design note: focused re-review of the Rule 0 exemption-row addendum, revision 2

| Field | Value |
|---|---|
| Date | 2026-11-24 |
| Reviewer | Fresh independent adversarial reviewer (`adversarial-design-review` skill); same reviewer as the first review of `b3500098`, no author context beyond the files named here |
| Subject | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, `git diff b3500098 189f51ea` (note hunks only; the merge commit's main-side changes ignored). Revision 2 is `e012be3f`; `189f51ea` adds four CodeRabbit fixes. P-090 item 5 is `813088e9` (plus three lines in `189f51ea`) |
| Citations | "note NNN" is a line of the note at `189f51ea`. Code is at `dbd54fe3` (unchanged) |
| Against | `reviews/wp9-5-note-exemption-addendum-review-2026-11-24.md` (REWORK REQUIRED: 0 Blocking, 2 Major, 7 Minor, 7 Info); revision brief `handoffs/wp9-5-gemini-note-exemption-addendum-r2-2026-11-24.md`; P-090 item 5 (register, `189f51ea`, lines 6241-6254) |
| Edits made | None to the repository. This report is the only file written |

## 1. Summary

Both Majors are resolved. Counts: **0 Blocking, 0 Major, 5 Minor, 5 Info.**

- **X-M1 (malformed intermediates)** is closed for the three scenarios I gave. The raw-read rule (note 762, repeated at note 780) does close the stray-key laundering scenario, because a version with a stray key still parses, so the comparison at F runs X-version to F and sees the rewrite. "Nearest earlier version that parses" is implementable as one pointer carried through the walk. Residuals are an over-broad "no row clears it" and nine unqualified restatements of the old exit-2 rule (XR-m1, XR-m2).
- **X-M2 (unrecoverable invalid row)** is resolved the way Stephen decided it: a required pre-merge `--head <candidate>` run (note 751), no later-row recovery, no `rule0_exemptions[k]` location, and the remaining risk named in HR-3 (note 1423). The command the author wrote is sound; its wording has three small gaps (XR-i1).
- **The author's departure on X-m1 is correct.** Rejecting a *violating* commit whose first parent is `b0` would block exemptions for the first walked commit, which can be the L-1 commit itself. The guard sits on the appending commit and on `e["commit"] == b0`, as my text said (the brief's paraphrase was wrong, not the note).
- **The two-point slice hash in `189f51ea` breaks no legitimate case.** It is always satisfiable (citing the last commit that changed the slice, or `P1` itself). It does not add security, and it leaves two inconsistencies and a missing control (XR-m3).
- **Stephen's item 5 is applied faithfully**, with one broadening (XR-i1).
- **The rebuilt controls are much better, but not yet one guard each.** The ordering controls cannot isolate their guard, and the new two-point hash has no control (XR-m3, XR-m4). I wrongly accepted `source_commit >= C_ex` as constructible in the first review; section 4 corrects that.

Nothing new rises to Major. I checked the scope rules: the diff has no hunk in 4.2.2, 4.3.3, 10.2, 10.3 or 21. Section 15.1 changed only in item 3 (my X-m7) and in one sentence of the recorded U-3 results (`189f51ea`, CodeRabbit).

## 2. Resolution of the X findings

| ID | Status | Basis |
|---|---|---|
| X-M1 | **Resolved**, residuals XR-m1, XR-m2, XR-i4 | Raw-read rule note 762 and 780; non-`<head>` parse and unknown-format faults are exit 1 and exemptable (note 742-743, 777); superseded reader kept (note 762, 768); three controls (note 1372) |
| X-M2 | **Resolved** (owner decision), residual XR-i1 | Required run note 751; "a later row cannot clear a validity fault in an earlier one" note 746; no `rule0_exemptions[k]` location (note 743); HR-3 recovery sentence (note 1423) |
| X-m1 | **Resolved** | `fp_index[b0] = -1`, `0 <= fp_index[commit] < fp_index[source_commit] <= fp_index[P1(C_ex)] < fp_index[C_ex]`, "stricter than" `is_ancestor` (note 748). Departure sound, see section 3 |
| X-m2 (a) | **Resolved** | `#check` sub-check in `location` (note 743, example in the row at notes 727-741); regexes behave as intended (section 6); sibling-sub-check control in N1 |
| X-m2 (b, c) | Carried | Note 1516 (accepted: these are code-brief items) |
| X-m3 | **Resolved** | Note 757 says "§10.2 does not read `format`" and rests the rule on §6.6 item 1 |
| X-m4 | **Resolved** | Note 587: "never the same commit as the violation", with the pin-advance carve-out |
| X-m5 | **Resolved** | "never in place without a cleared Rule 0 fault" (note 768, 1423, 1546); `walk-baseline.json` narrowing by P-090 item 5; deleted-then-restored risk stated in HR-3 (the author's stated choice). Sound |
| X-m6 | **Partly** | Rebuilt row (note 1372). See section 4 |
| X-m7 | **Resolved** | "any value other than `[]`" (note 753); section 16 intro, 15.1 item 3 and the "(not yet reviewed)" label updated; d8 written as decided (note 760) |
| X-i1 to X-i4 | **Resolved** | Notes 723, 766, 749 and 1423 |
| X-i5, X-i7 | Carried | Notes 1517-1518; X-i7's text is now stale (XR-m3 b) |
| X-i6 | **Not done in the note** | Change log note 1848 says "recorded pre-revision sizes"; no sizes appear in the note (XR-i2) |

## 3. The five focus questions

**Q1. X-m1 departure (reject `P1(C_ex) == b0` and `commit == b0`, not a violating commit whose first parent is `b0`).** Sound, and better than the brief. Take C_1, the first walked commit (`P1 = b0`). If C_1 carries a Rule 0 fault, a later row names it with `fp_index[C_1] = 0`, `source_commit` at index 1 or more, and `P1(C_ex)` at index 1 or more: valid. Blob confirmation reads `blob_at(b0, path)`, which is fine. Rejecting a violating commit whose parent is `b0` would make a defective L-1 row 0 (when `b0 = P1(C_0)`) unexemptable for the `#iii` sub-check. The note's two guards are the right ones, and `fp_index[P1] == -1` is already implied by the inequality (it cannot be satisfied), so the explicit sentence is belt and braces. Verified in the scratch repository used for the first review: `P1` of the first commit after `b0` is `b0`, which `b0..head` does not list.

**Q2. X-M1 raw-read rule: does it close the laundering scenario, and is it implementable?**
- *Scenario A closes.* X adds a stray key (valid JSON, schema-invalid). F removes it and rewrites `baselines[0].baseline_commit`. "Parses" means `json.loads` succeeds, so X-version parses. At F the comparison runs X-version to F raw, sees the rewrite, and reports an unexemptable violation at F. The "$" rows for X and F clear only the schema faults. Control (i) (note 1372) would fail if the raw-read rule were removed, so it proves its guard.
- *Scenario B closes* (conflict marker at X, fixed at F): X is unparseable; the comparison runs from the last parseable version (before X) to F; non-`<head>` parse faults are exit 1 and exemptable (note 777).
- *A type-corrupted intermediate* (`baselines` becomes a dict at X) is caught at X as a presence violation (note 759 says "immutability/presence").
- *Implementable.* Carry `last_parsed` through the walk; on a version that fails to parse, defer; at the next version that parses, compare against `last_parsed` and report at that commit. This costs one pointer and no look-back. Edge: if the file already fails to parse at `b0`, the earlier version is outside the walk. This cannot happen here because every evidence file is created at or after L-1 (§10.3, note 1319 onward).
- Two defects remain: the sentence "no row clears it" is wider than the invariants it was meant to protect (XR-m1), and the same rule is stated for Rule 0.2 only (XR-m1).

**Q3. X-M2 command with `--acknowledged-from` dropped.** The command is sound and, for this purpose, better than the step 4 form. With `--acknowledged-from <pr_base>` the candidate's own row would validate but would not clear anything (the active snapshot comes from `pr_base`), so the run would still be red on the fault the row exists for. Without it the snapshot is the candidate's, the row clears its tuple, and the X-i2 line names the row index, so "the row validates and clears" is observable. The author's stated reason ("so the appended candidate row itself validates", note 1840) is imprecise: validity is checked across `(b0, head]` either way (note 766); the flag only changes clearing. Three small gaps are in XR-i1.

**Q4. Does the two-point slice hash break a legitimate case?** No. For any row there is a valid choice of `source_commit`: let S be the last commit at or before `P1(C_ex)` that changed the `### <id>` slice. S is later than `commit`, because the slice at `P1` contains a line naming `commit[:8]` and that hash cannot be written before the commit exists. Any commit in `[S, P1]` has the same slice, so `source_commit = P1(C_ex)` always satisfies both hashes. A register entry edited after the first `source_commit` the author considered simply means citing the later commit. Two consequences:
- The check makes `source_commit` truthful (the cited commit really holds the entry) but adds no security: the slice at `P1` already proved the entry existed by then. I said in the first review that `source_commit` was decorative; it is now a truthful pointer, still not a proof of when the entry appeared.
- The wrong choice of `source_commit` is the new way to land an invalid row: a PR-branch SHA is off the first-parent chain; an earlier commit before a later edit fails the second hash. Both make a row invalid and unrecoverable. The mandatory pre-merge run catches both, so a one-line authoring note would help ("cite the commit on `main` that last changed the slice"). Inconsistencies and the missing control are XR-m3.

**Q5. Does each rebuilt control prove one guard?** Not all. Section 4.

## 4. Controls check (note 1372)

| Control | Proves one guard? | Note |
|---|---|---|
| Positive (paired) | Yes for the clearing. It bundles three extra assertions (verdict omission, X-i2 line, two-line slice) | Acceptable in one fixture; separate asserts would localise a failure |
| N1 exact tuple, parametrised | **Partly.** For `location` (valid sibling) and the sub-check case, yes | A wrong `commit`, `path`, `old_blob` or `new_blob` makes the row fail *blob confirmation or pairing*, not the exact-match guard. To isolate matching, use an otherwise-valid row that names a different real fault (XR-m4) |
| N2 slice, one fixture each | Yes for five cases | The new `source_commit` hash has no case (XR-m3) |
| N3 ordering, one fixture each | **Partly.** `commit == b0`, `P1 == b0`, off-chain `commit`, off-chain `source_commit`: yes | `source_commit <= commit` is rejected earlier by slice content (the slice at `source_commit` cannot name `commit`), so it does not isolate the inequality. `source_commit >= C_ex` cannot be built with real git: the row would have to cite a commit that does not exist when the row is written. My first review wrongly passed it (XR-m4) |
| N4 unexemptable, otherwise-valid row, with a re-point proof | **Yes.** This is what makes each guard testable | The strongest part of the rebuild |
| N5 deletion or mutation of an existing row, with a self-exemption attempt | Yes | |
| N6 separated extra/missing key (row, `disposition_ref`, top level) | Yes | |
| N7 replacements for `commit == C_ex` | **No.** Both my suggested variants (`source_commit == commit`; violation immediately followed by the row commit) are rejected by the slice-content guards first, since neither slice can name a hash that does not yet exist | Test the inequality as a predicate on indices (XR-m4). I owe this correction: the variants were mine |
| N8 recurrence | Yes (subsumed by N1, harmless) | |
| Scope controls (Rule 1 to 3 as `rule`, pairing, bad `location`, both-null, duplicate) | Yes | The `location` bullet bundles four cases |
| Three X-M1 controls | **Yes.** (i) proves the raw-read guard; (ii) the non-`<head>` parse fault; (iii) the superseded reader | (ii) assumes F directly follows X; commits between X and F with the blob unchanged are carried by X-m2 (b) |
| X-M2 | Procedural | Not a test; fine |

## 5. New findings

### Minor

**XR-m1. "No row clears it" is wider than the invariants, and the raw-read rule covers Rule 0.2 only.**
1. *Claim.* Note 762 and 779: "A violation found there is reported at the commit that produced the later version, and no row clears it."
2. *Evidence.* The sentence follows "Rule 0.2's append-only and immutability comparisons, including every unexemptable invariant". It does not say whether the *exemptable* append-only violations found across a gap (an entry dropped from `legacy-write-records.json`) are also unexemptable. Read literally, they are.
3. *Failure scenario.* A conflict-marker file at X is fixed at F, and the resolution also drops a record. By the sentence the drop is unexemptable, although the same drop without the gap is an exemptable "broken append-only file" (the named cause). This is the red-for-ever state the mechanism exists to avoid, and no control covers it. It is unlikely (it needs a bad file to land and a second error), so Minor. The wording is mine; the author adopted it.
4. *Related gap.* The comparison covers Rule 0.2. A deletion of manifest entries (Rule 0.1) or a backdate in `detector-controls.json` (Rule 0.3) behind a gap is reported only as a parse fault at F, so the human sees a "$" fault and not the deleted entries. These violations are exemptable by design, so this is visibility, not a bypass.
5. *Proposed text.* "A violation of an unexemptable invariant found there cannot be cleared by any row. Any other append-only violation found there is reported as a `Rule 0.1`, `0.2` or `0.3` fault at that commit with location `"$"` and may be exempted under item 3." Add a control: conflict marker at X, a dropped record at F, rows for both: exit 0.
6. *Affects.* Note 762, 780; §12.1.

**XR-m2. Nine restatements still give the old exit-2 rule without the `<head>` qualifier.** Notes 26, 52, 466, 570, 598, 628, 1436 and 1530 say tools exit 2 on "unparseable / unknown-`format` evidence" flatly; the test row at note 1373 says the entry shims "exit `2` on ... `EvidenceParseError`, `UnknownEvidenceFormatError`". Section 6.6 (note 777) now says exit 2 only at `<head>`, and exit 1 at any other commit; MC-2 (note 1407) already carries the qualifier. A test author following note 1373 would assert exit 2 for a historical parse error, and §15.2 item 6 (any misfiring control stops the code worker) would then stop on a correct implementation. *Proposed:* add "at `<head>`" at those nine sites, and the non-`<head>` exit-1 case to the note 1373 row. HR-3 (a) ("a lagging pin exits 2 on unparseable ... JSON") needs the same qualifier.

**XR-m3. The two-point slice hash: no control, and the `disposition_ref` family is now inconsistent.**
- *Control.* `acknowledged` (note 574) and exemption rows (note 749) now bind `source_commit` by hashing the slice at both points. No control in §12.1 exercises "hash at `P1` matches, hash at `source_commit` does not" for either. Add one fixture each.
- *Restatement-diff.* Other `disposition_ref`-shaped fields keep the older rule: `baselines[k].recorded_in_decision_ref` and `pre_baseline_dispositions_ref` pass "the `P1` hash-bound slice check" (note 689); `ruleset_gap_acknowledgements` needs a "`P1` slice" (note 691); the §6.4 owner note and independent review use `P1` plus ancestry (note 637); the d8 reference reads the slice at `source_commit` only (note 293). CodeRabbit's reason ("the cited commit really contains the entry") applies to each. The carried item X-i7 (note 1518) still says "reconcile §4.2.3 (`source_commit`) vs §6.2.2/§6.4/§6.5.1 (`P1`)", which is now wrong for §6.2.2 and §6.5.1. *Proposed:* say in X-i7 that §6.2.2 item 3.2 and §6.5.1 item 3 already read both points, and that the code task defines one shared slice check for every `source_commit` field.
- *Not a defect:* the check does not break any legitimate case (section 3, Q4).

**XR-m4. Ordering and exactness controls cannot isolate their guard.** See section 4. N3's `source_commit <= commit` and `>= C_ex`, and both N7 replacements, are rejected by the slice-content guards (the slice naming `commit[:8]` cannot exist before the commit) or are not constructible. Test the inequality as a pure predicate over synthetic indices and label the end-to-end fixtures as "invalid", not as proof of the ordering guard. For N1, specify that each case is an otherwise-valid row naming a different real fault (or a valid sibling `location`), so it fails only by not matching.

**XR-m5. A fault inside an exemption row has two classifications.** Note 746 makes any failure of the row's own closed-key check an unexemptable item 3 fault at `C_ex`; but §6.6 and note 743 classify a closed-key failure of `walk-baseline.json` as an `EvidenceSchemaError` at location `"$"`, which note 761 makes exemptable. A closed-key failure inside a `rule0_exemptions` row is both. The outcome does not change (a strict parse of `<head>` then fails for ever, and HR-3 says so), but an implementer could classify it as `"$"` and let a later row clear the `C_ex` tuple, which Stephen's item 5 forbids. *Proposed:* "A fault inside a `rule0_exemptions` row is an item 3 validity fault only, never a `"$"` schema fault."

### Info

**XR-i1. The required pre-merge run (note 751): four wording points.**
- Its trigger ("appends to `rule0_exemptions` or otherwise changes `walk-baseline.json`") is wider than P-090 item 5, which names exemption-row PRs and the L-1 PR. That is my proposal, so the breadth is harmless, but record it as an extension Stephen may keep or narrow.
- Say which assembled tree runs the tool: `baselines[-1]` at `pr_base` for ordinary PRs; for L-1 row 0 there is no pin at `pr_base`, so it is the tree assembled from the candidate's own row 0.
- "showing no new `Rule 0.2` fault" needs a reference point when the run has no `--verdict-json` diff. The observable outcome is: exit 0, and one cleared-tuple line for each row the PR appends (X-i2). If other faults are still red, the PR description should say which.
- The reason given for dropping `--acknowledged-from` is imprecise (section 3, Q3). The R8-i5(a) behaviour for a candidate absent from `--pr-map` is carried and unchanged.

**XR-i2. The revision-2 change log is partly stale.** Note 1835 says §20.3 leaves "§15.1 recorded results" untouched, but `189f51ea` (after §20.3 was written) edited the U-3 sentence in those results (note 1468). The edit narrows the claim, cites CodeRabbit, and carries the check to §15.3, so it is acceptable; the log should say so. Note 1848 says X-i6 "recorded pre-revision sizes", but no sizes appear anywhere in the note (the brief asked for them in the hand-back, not the note).

**XR-i3. Two small consistency points with the decisions.** (a) The §6.2.2 example still shows `"d8_rule_suites_limit_decision_ref": null` (note 495) although P-090 item 5 says it is set in row 0 at L-1 and U-3 recorded D-8 as applying; a comment on the example would avoid misreading. (b) H1's end at the writer revocation (item 5, last bullet) is not in the note; the revision brief put it in W9 §4.2 (d), outside this addendum, so no change is needed here.

**XR-i4. Coverage not yet in the controls.** (a) A pin-advance commit carrying exemption rows for an earlier `V` (the X-m4 change) has no positive control. (b) `#valid` for `acknowledged` and `ruleset_gap_acknowledgements` rows lumps slice, ordering and Rule 3 conditions into one sub-check; a coarser grain than `baselines[k]`'s. (c) The unchanged-blob commits between X and F still have no defined fault count (carried as X-m2 (b)), so the number of rows a gap needs is open.

**XR-i5. Placement of the carried items.** X-m2 (b, c), X-i5 and X-i7 now sit in §15.3 (notes 1516-1518). That is where I suggested them; X-m2 (b) names "unchanged-blob `old_blob == new_blob` scoping", which controls (ii) and the row-count question depend on, so the code brief should read it with note 777.

## 6. Stephen's decisions, applied

| P-090 item 5 | In the note | Faithful? |
|---|---|---|
| Pre-merge `--head <candidate>` run for exemption-row PRs; a later row cannot clear a validity fault; no `rule0_exemptions[k]` location | Notes 746, 751, 743; HR-3 note 1423; §16.2 note 1546 | Yes. Trigger broader (XR-i1) |
| `walk-baseline.json` changes format only by a new path, never in place or by an exemption row | Notes 757, 768, 1423, 1546 | Yes. The "$" exemption of a stray top-level key (note 761) is a transient fault, not a format change, since the file at `<head>` must have closed keys |
| d8 unexemptable, first transition included; set in row 0; L-1 PR gets a pre-merge run | Note 760 and note 751 ("including L-1 row `0`") | Yes. Example still `null` (XR-i3) |
| H1 revocation and its pin advance in one PR | Not in the note | Out of scope for this addendum |

Regex checks (scratch script, `python -I`): the location grammar (note 743) accepts `baselines[3]#iii`, `baselines[0]#append_only`, `acknowledged[2]#valid`, `ruleset_gap_acknowledgements[0]#append_only`; rejects `baselines[3]` (no sub-check), `baselines[01]#i`, `baselines[-1]#i`, `rule0_exemptions[0]#valid`, `acknowledged[2]#iii`, `baselines[3]#v`, trailing space, uppercase. The `R0-EXEMPT` line grammar matches lines with 8-hex prefixes, `null -> hex`, `hex -> null`, `$` and `#` locations; rejects uppercase hex and `Rule 0.4`.

## 7. Commands run and limits

- `git cat-file -t` for `e012be3f`, `189f51ea`, `b3500098`; `git log b3500098..189f51ea`; `git diff b3500098 189f51ea` (note, register, stat); `git show 189f51ea:<note>` and `:<register>`; `git show <commit> -- <note>` for `1b65fc7e`, `e012be3f`, `189f51ea` (to attribute each edit).
- Reads of the revision brief and the P-090 diff; greps over the saved note for the exit-2 restatements, `source_commit`, `rule0_exemptions[`, "not in place", "pre-merge", the change-log claims.
- One scratch script (`regex_check.py`, Write tool) run with `python -I`.
- `git status --short`: clean in both `wp9-5-note` and `wp9-5-amend` before this report was written (the first review's report is committed as `9b7b728f` on the amendments branch). After writing, the only change is this untracked file.
- *Not verified:* behaviour of the unwritten tool (every statement about it is a reading of the note); GitHub state (no calls); whether the pre-merge run reproduces the post-merge `P1` under a merge queue (HR-3 names the race); the live ruleset.
