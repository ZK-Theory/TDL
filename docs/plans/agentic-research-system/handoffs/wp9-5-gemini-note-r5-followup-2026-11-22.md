# Follow-up 4: WP9.5 design note, revision 5

For: the Gemini agent that wrote revisions 1 to 4 of the WP9.5 design note. Written by the reviewing Claude session
on 2026-11-22.

A fourth fresh reviewer attacked revision 4 (`48b5e935`). The verdict is **REWORK REQUIRED**: 0 Blocking, 2 Major, 11
Minor and 8 Info. The report is committed on your branch at
`docs/plans/agentic-research-system/reviews/wp9-5-note-r4-review-2026-11-22.md` (`0e6d23e4`). Read all of it before
you change anything.

The reviewer reproduced every §21.1 check. It found every citation in range and none of the new ones wrong. It
assembled the content-pinned tree itself and confirmed the isolation. It found no mechanism the brief did not ask
for. Keep all of that; the review's §6 lists it.

Both Majors are in the pin-advance check, and the first is the reviewing session's fault: follow-up 3 prescribed a
two-tool verdict comparison inside the post-merge walk without defining it or bounding its cost. Revision 5 replaces
that design with a simpler one, set out in §2. It removes machinery; it does not add any.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`), same rules
as the handover (`handoffs/wp9-5-gemini-note-handover-2026-11-21.md` §4) and follow-ups 1 to 3. Before any write,
confirm the branch, that HEAD is `0e6d23e4`, and that `git status --short` is clean.

## 1. Scope rules for this revision

1. **Add no mechanism beyond §2.** If a finding seems to need more, say so in the change log and leave it.
2. **The note must get smaller.** It is 341,267 bytes now. Revision 5 must be smaller in bytes. Delete superseded
   text, and make the cuts in §3. Report the byte and line counts before and after.
3. **Nothing unverified, and no overclaim.** Follow-ups 1 to 3 still apply.
4. Read-only `gh api` GETs only, for the same endpoints as before. Do not run the U-3 probe or the U-4 dry run, and
   never read vault file contents. Any assembly, venv or timing run goes in a scratch directory outside the
   repository.

## 2. The design change (R4-M1, R4-M2, R4-m7)

1. **Check pin advances at pull-request time, not in the post-merge walk.** `admission-controls` is a required check
   on ruleset `20822054` and runs on `merge_group` (`.github/workflows/ci.yml:12,135`), so on the queue it judges the
   squash candidate. When `L1_LIVE` is true, `tests/tools/test_w9_detectors.py` asserts for the checked-out tree:
   - every path in `baselines[-1]["detector_closure_blobs"]` has the recorded blob, compared with
     `git rev-parse HEAD:<path>`. A closure edit without its row therefore cannot merge except by bypass;
   - Rule 0.2 checks (i) to (iv) hold for every row added since `origin/main`, and for row 0 when the file is
     created (R4-i1);
   - when the PR changes the blob map, the verdict comparison below holds.
2. **The verdict comparison runs once per closure-editing PR.**
   - It runs the tool pinned at `origin/main`'s last row and the candidate's tool over
     `(baselines[0]["baseline_commit"], candidate]`. The interval includes the candidate commit, so the old tool
     judges the commit that introduces the new one.
   - Define the verdict with the review's text: the set of `(rule, path)` pairs a tool reports as violations at a
     commit, after the `acknowledged` rows present at that PR's base. A run that does not complete is `ERROR`, never
     the empty set. Rule 0 is not part of the compared verdict, so nothing nests.
   - Any commit whose verdict differs must be named, by `V[:8]` and the differing `(rule, path)` pairs, in the new
     row's decision slice. Otherwise the test fails.
   - State the invocation each tool version must keep for this (the review's `--ruleset-check skip --head <rev>`
     form, or yours), and reconcile it with §6.3 item 4.
3. **The post-merge detector uses only the last row.** Delete Rule 0.2 (v) and the dual-tool walk from the post-merge
   design. Each run makes one walk with the tool pinned by `baselines[-1]`. Rule 0.3 stays as the post-merge
   backstop for a bypass or direct-push merge.
4. **An unrowed edit that lands anyway.** Put the exit to Stephen under Owner Point C, as R4-M2 (c) states it:
   - a narrow, hash-bound exemption row for a Rule 0.3 miss, keyed on `(commit, path, old_blob, new_blob)` with a
     decision slice, as `acknowledged` is;
   - or accept that the detector stays red, and list that in §13.2.

   Describe both options. Do not build the exemption into the design until Stephen picks it.
5. **Drop `pyproject.toml`, `uv.lock` and `uv sync` from the pin (R4-m7).** All 15 existing closure modules import
   only the standard library; the reviewer checked this under `python -S`.
   - The detector tools and their closure must stay standard-library only. Enforce that with a unit test that walks
     the AST closure and checks every import against `sys.stdlib_module_names` or the closure itself.
   - Specify how the workflow and the operator wrapper get the interpreter (for example a pinned
     `actions/setup-python` version), and the exact command line. It must keep the head's code and site-packages off
     `sys.path`. Note that `-I` and `-E` ignore `PYTHONPATH`, and that the review found `-m` without
     `PYTHONSAFEPATH` leaks the head's code. Test the command in scratch, and give its output in §21.
   - Remove the `.venv` reuse rule (review §0.1).
6. **Measure the cost of what remains.** Measure one post-merge walk and one PR-time comparison with a realistic
   stand-in (the review's six-call variant took 65.3 s for 320 commits) over the interval Option C1 would walk. Then
   give a stop rule: when a full run exceeds a stated wall time, the matter returns to Stephen. Add the full-walk
   time on `windows-latest` to §15.1 as UNVERIFIED.

Then make MC-2, claim 2, note 748, §6.2.3, §6.5, §10.2, §12.1 and §12.3 describe this design and nothing else.

## 3. Cuts (R4-i8, review §0.1)

1. **Replace §18 and §19** (the revision 1-to-2 and 2-to-3 change logs, about 31 KB) with one short table: each
   finding ID, the section that now answers it, and one of resolved, superseded or not taken. The full history stays
   in git and in the three review reports. Keep §20 and the new revision 4-to-5 log in the same compact form.
2. **Shorten the heading tag chains.** Put finding IDs in the change logs, not in headings.
3. **Split the Owner Points table into one short subsection per point**, each with options, recommendation, what it
   changes, and the records it needs. No 5 KB table cells.
4. **Replace the 22-row table with its summary line and a pointer to the §21.1 script** that reproduces it.
5. **Remove restatements.** Each rule is stated once, in its section; §1, §13, §14 and §16 point to it.

## 4. The other findings

- **R4-m1:** a Rule 3 acknowledgement also names an `independent_review` as §6.4.2 requires. It needs a non-empty
  `affected_registrations`, or "none derived" stated in the slice. Define `pr_number: null` for an unmapped commit,
  valid only for acknowledgement-backed entries. State the late-entry safety argument through
  `require_change_list`. Add the empty-list and null-PR controls.
- **R4-m2:** add the missing row controls: blobs that differ from the tree; a decision ref that is not an ancestor
  of `P1`; a wrong `entry_sha256`; extra keys; and a positive control for a named verdict change.
- **R4-m3:** confine the assembly. Reject any key that is not a normalised relative POSIX path, contains `..` or is
  absolute, and require the resolved path to lie inside the assembly directory. Add traversal and absolute-key
  cases, and rename "blob mismatch" to "absent object".
- **R4-m4:** the operator wrapper runs a pinned copy of itself, or checks its own blob against the row and refuses
  on mismatch. It fetches and checks `origin/main` against `git ls-remote` first. List the M-6 exporter's unpinned
  run as a residual in §13.2. Say whether the exporter stays in the blob map, given that it never runs from the
  assembled tree.
- **R4-m5:** give the controls runner separate code and repository roots.
- **R4-m6:** add a test that every `tools/` path in the derived closure, and `accepted_w9.py`, has a CODEOWNERS
  entry.
- **R4-m8:** say exactly how the throwaway rehearsal file differs from the committed YAML. Make a green
  `workflow_dispatch` run on the L-1 commit an L-1 exit criterion.
- **R4-m9:** take `config` and `hooks/` from `--git-common-dir`, in CI only.
- **R4-m10:**
  - fix "six" modules (note 803) and the count of 13 against 14 non-code-owned modules;
  - record the move of W9-T7 to the unit lane as a departure from `06v:230` (Owner Point F, plus a dated addendum
    row);
  - mark the deleted mechanisms as superseded in the compact change log.
- **R4-m11:** state Option I1-narrow's real reach. `reader.py` pulls in the five `store/` modules. Moving helpers
  cuts the 90-day count from 14 to 8 at most, or forks the handle-anchor code.
- **R4-i1** is in §2.1 above.
- **R4-i2:** word Owner Point K honestly. At PR time the check judges itself if a closure module changes in the same
  PR.
- **R4-i3:** say under Option A1 whether WP9.4's recorded pass counts are re-recorded, and leave the call to
  Stephen.
- **R4-i4:** recorded blobs are computed with `git rev-parse :<path>` or `hash-object --path`, and tested with a CRLF
  working copy.
- **R4-i5:** state the I3 update order and the expected red window. Say how the operator wrapper reads the variable.
- **R4-i6:** `pre_baseline_dispositions_ref` becomes a hash-bound register reference. HR-1 says the decision entry
  proves age, not authorship.
- **R4-i7:** record it.

## 5. Owner points

Put them to Stephen; do not decide them. Keep the order I first, then C, A, B, D, E, F, G, H, J, K. Update C for the
PR-time comparison, the stop rule and the Rule 0.3 exit choice. Update I for the dropped dependency pin and I1-narrow's
reach. Update F for the W9-T7 lane change.

## 6. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 5`, via `git commit -F` with a UTF-8
   file without a byte-order mark), the new HEAD, and `git status --short`.
3. Bytes and lines before and after.
4. For each R4 finding ID: what changed, with the section.
5. Owner points A to K, one line each, with your recommendation.
6. The Verification appendix's summary: what you ran (including the interpreter command test and the cost
   measurements), and every statement you marked UNVERIFIED.

Do not describe the note as reviewed or accepted. It goes to a fifth independent review next.
