# Follow-up 8: WP9.5 design note, the Rule 0 exemption-row addendum

For: the Gemini agent that wrote revisions 1 to 8 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-24.

Revision 8 passed its focused review (CONFIRM WITH FINDINGS, `ae608701`). Stephen has now decided all owner points,
recorded in P-090 on the same branch (`0e1269bd`). The U-3, U-4 and scratch-store gates have run, and their results
are in note §15.1 (`79d8a684`). One item in P-090 item 4 is still missing before code: **the design of the Rule 0
exemption row**. This brief asks for that design, and nothing else.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`), now
behind PR #449. Before any write, confirm the branch, that HEAD is `79d8a684`, and that `git status --short` is
clean.

## 1. What Stephen decided

Owner Point C (note §16.2; P-090 item 2, C):
- a Rule 0 violation found by the post-merge walk is cleared by an exemption row;
- the row is append-only and hash-bound, keyed on the exact violation, and backed by a register entry;
- after L-1, an evidence format changes by a new file path or by an exemption row, never in place (R7-d1).

The causes the note already names are:
- a bad `baselines` row;
- a concurrent merge that breaks Rule 0.2 (ii) between a row being written and landing (R6-m7 (c));
- a slice typo;
- an in-place evidence-format change;
- a broken append-only file.

Today Rule 0 cannot be acknowledged (note §6.2.2, §6.5), so any of these leaves the post-merge detector red for good.
The exemption row is the one sanctioned exit.

## 2. What to design

Write it as one new subsection, §6.5.1 "Rule 0 exemption rows", plus the edits it forces elsewhere. Answer each
question below with the mechanism and the reason for it, against the code at `dbd54fe3` and the note as it stands.
These are questions, not answers: earlier briefs that prescribed designs carried new defects, so design it
yourself, and the review will attack it.

1. **Where it lives.** A new closed top-level key in `walk-baseline.json`, or something else. Say why. It must be
   inside `.research-system/evidence/w9/`, so that I1 code-owns it.
2. **Its row format.** Closed keys only. How does it name the violation exactly: the commit, the Rule 0 label (0.1,
   0.2 or 0.3), the path or the JSON location, and the old and new blobs? What happens when a field has no blob, for
   example a deleted file?
3. **When a row is valid.** The decision reference is hash-bound as for `acknowledged` rows. The register entry is
   already on `main` before the PR that appends the row (its `source_commit` is an ancestor of `P1`). The slice names
   the exempted violation in a stated line grammar. And the violating commit comes strictly before the commit that
   appends the row. Say how each is checked.
4. **What it may not exempt.** At least these:
   - a violation of the exemption list's own append-only rule. The list cannot clear its own tampering;
   - a commit that is not on `<head>`'s first-parent chain after `baselines[0]["baseline_commit"]`;
   - Rules 1 to 3, which already have `acknowledged`.

   Say whether any other Rule 0 case must stay unexemptable, for example a change to `format` or
   `d8_rule_suites_limit_decision_ref`, and why.
5. **How it matches.** Is it an exact tuple match, so that one row clears one violation and nothing else? What
   happens when the same violation recurs at a later commit?
6. **Its interaction with the rest of the note:**
   - exemptions feed the `--verdict-json` verdict the same way `acknowledged` rows do (§6.2.2 step 4);
   - the pin-advance comparison;
   - the pinned-copy rule: an old pinned tool meeting a `walk-baseline.json` with the new key must exit 2, or the
     key must be present from row 0. Say which;
   - the evidence-format statement R7-d1 adds.
7. **Controls** for §12.1:
   - a positive control: a Rule 0 violation followed by a valid exemption row leaves the walk green;
   - negative controls for: a wrong tuple; a missing reference; a reference not on `main` before the PR; a
     self-exemption of the list; deletion of a row; extra keys; an exemption appended in the same commit as the
     violation; and a recurrence at a later commit.

## 3. Scope rules

1. **Add only the exemption row and what it forces.** No other mechanism and no restructuring. Update Owner Point C,
   HR-3 and §13.1 to point at §6.5.1. In §1, change "not built" to say where it is designed.
2. **Keep it short.** The subsection should be a page, not a chapter. Report bytes and lines before and after.
3. **Nothing unverified, and no overclaim.** Follow-ups 1 to 7 still apply. Cite code at `dbd54fe3`.
4. Do not touch §4.2.2, §4.3.3 or §15.1's recorded results. Read-only `gh api` GETs only, and never read vault file
   contents.

## 4. The change log

Add a compact "Change log: exemption-row addendum" after §20.1, listing what changed and where.

## 5. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note, the Rule 0 exemption-row addendum`, via
   `git commit -F` with a UTF-8 file without a byte-order mark), the new HEAD, and `git status --short`. Do not push;
   the reviewing session pushes after review.
3. Bytes and lines before and after.
4. Your answer to each question in §2, one short paragraph each, with the sections changed.
5. Anything you could not decide from the code and the note, as a question for Stephen.

Do not describe the addendum as reviewed or accepted. It goes to one independent review next.
