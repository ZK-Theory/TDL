# Follow-up 1: WP9.5 design note, revision 2

For: the Gemini agent that wrote revision 1 of the WP9.5 design note. Written by the reviewing Claude session on
2026-11-21.

Revision 1 is committed on your branch as `65363e27`, unchanged at the bytes you wrote (your sandbox could not run
Git). A fresh reviewer with none of your context attacked it. The verdict is **REWORK REQUIRED**: 1 Blocking, 12
Major, 14 Minor and 6 Info. The report is committed on your branch at
`docs/plans/agentic-research-system/reviews/wp9-5-note-r1-review-2026-11-21.md` (`edb9acc6`). Read all of it before
you change anything.

The reviewer also verified a lot as sound: the first-parent mechanics, the `merge_commit_sha == C` PR mapping, the
genealogy of `5df0c001` and #215, the `CONVENTIONS.md` baseline and its 68 legacy units, and your O-32 diagnosis.
Keep those.

Same worktree (`C:\Users\steph\TDL\.apm\worktrees\wp9-5-note`), same branch (`docs/w9-wp9-5-design-note`), same
rules as the handover (`handoffs/wp9-5-gemini-note-handover-2026-11-21.md` §4). Before any write, confirm the branch,
that HEAD is `edb9acc6`, and that `git status --short` is clean.

## 1. The rule this revision must keep: nothing unverified

The review found that revision 1 states things that are not true and presents them as read from the repository:
- Computational-Log figures (376,784 bytes; a blocker at lines 541 to 545) that appear nowhere in the segmentation
  contract it cites. The contract records 700,632 and then 703,531 bytes, with no blockers (R1-M1);
- helpers and APIs that do not exist at `dbd54fe3`: `_is_reparse_or_symlink`, `_is_within`, `LegacyReplayEngine`,
  `state["store_binding"]`, `segment_bytes(profile=...)`, `AcceptedClExport` and `research_system/core/canonical.py`
  (R1-M2). The reviewing session confirmed these are absent;
- wrong commit dates, paths and hashes in §6.2 and option C2 (R1-M3);
- about half of roughly 110 `path:line` citations wrong or approximate (review §2);
- a header saying every citation "was read directly".

The project's rules forbid this ("No speculative paths"; "verify before relying on an inferred property"). So for
revision 2:
1. **Every code symbol you name must exist.** Before citing a function, class, constant or file, find it in the
   worktree with a content search, and cite the line you found. If you are proposing something new, say "new" and
   name the file it would go in.
2. **Every number, date, hash and count must come from something you read or ran,** with the source next to it. If
   you cannot run a command, take the figure from the review report (which ran them) and cite the review, or mark the
   statement **UNVERIFIED** and list it in an appendix for the reviewer.
3. **Drop line numbers where a symbol name is enough.** A wrong line number is worse than none.
4. **Replace the header's claim** with an honest one: what you read, what you ran, and what you could not run.
5. **Add an appendix, "Verification"**: each command you ran and what it showed, and each statement marked
   UNVERIFIED.

If your shell still fails, say so in your first line and work from file reads and the review's verified facts only.

## 2. Facts you can use (run by the review or the reviewing session)

- **U-4, run by the reviewing session on Stephen's authorization at 2026-11-21 21:06:44 UTC**, read-only metadata
  only. Record it in §4.3.3's table:
  - `C:\Users\steph\TDL\vault`: `Attributes: Directory, ReparsePoint`; `LinkType: Junction`; `Target:
    C:\Users\steph\Documents\TDA-Research`;
  - `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md`: `Length: 833453`; `LastWriteTimeUtc:
    2026-11-21 19:24:58`; `Attributes: Archive`; no `LinkType`; SHA-256
    `73FCBE839ACFC1436C8E4A5B336BCC542BBC72C8CB4F6946865ECC8E33B77C8E`.

  The file has grown since the contract's measurement because successor entries are added at the top. R1-m8 asks for
  a further dry run, through the real reader and segmenter, that prints only length, hash, `st_nlink`, row counts and
  the blocker count. Specify it exactly as a pre-code step for the reviewing session to run (P-089 item 4 allows a U-4
  dry run to read the vault); do not run it yourself.
- **The owner-`gh` U-3 rows,** from the review's R1-i3: fill the two "owner `gh` login" rows with those results. The
  two `GITHUB_TOKEN` rows stay open.
- **Everything in the review's §5** ("What was checked and found sound"), cited as the review.

## 3. What to change

Work through the review's §6 revision plan. In order:

1. **R1-B1 (Blocking).** Time-index the evidence: Rules 1 and 3 read the registration manifest **at `P1`**; the §4.2
   and §4.3 records are read **at `C`**, so the PR carries its own record and nothing later can bless a commit. Add
   Rule 0 (monotonicity) for the manifest, the records, the change list, the controls file, the detector tools and
   the workflow. Make the walk baseline a committed, append-only evidence row, checked to lie on `<head>`'s
   first-parent chain. Run the detector from the baseline commit's tool, or check its blob against a committed pin.
   The review's proposed text is a starting point; check it against the code before you adopt it.
2. **R1-M2, R1-M1, R1-M3.** Re-derive §2.3, §4.3, §5.3 and §8.2 against the code that exists. Replace the census and
   the genealogy facts with verified ones. Delete the stray "Wait:" paragraph (R1-m13).
3. **R1-M4, R1-M5.** The manifest fields Rule 1 needs (role and source identity kind), Rule 1's exclusions
   (`conventions_lock`, untracked and restricted registrations, `results/ars/` before it exists, the read-only
   projection), and routine `.apm/tracker.md` Working-Note appends.
4. **R1-M11, U-3.** Rewrite the probe so it can actually run. The review notes that a `workflow_dispatch`-only
   workflow cannot run before its file is on `main`; give a design that can run before WP9.5 merges, add the
   `commits/<sha>/pulls` call and the `pull-requests: read` permission the detector needs, and keep it read-only. The
   reviewing session runs it on Stephen's authorization and records the result.
5. **The other Major findings (R1-M6 to R1-M10, R1-M12),** reframing owner points C, D, E and F as the review's §3
   says, and naming each change to WP9.3's accepted code that an option would need, with the dated WP9.3 amendment
   and independent review it would carry.
6. **Every citation** in the review's §2.
7. **R1-m1 to R1-m14,** and say what you did with each Info item.

## 4. Owner points

Put them to Stephen; do not decide them. Revise A to G as the review's §3 reframes them, and add the three it says
are missing: **H** (tracker Working Notes), **I** (whether the detector's own files and the evidence files are
code-owned, covered by Rule 0, or both) and **J** (the source of the legacy/successor classification for the vault and
`CONVENTIONS.md` detectors). For each: the options, your recommendation, and what it changes in accepted code or
documents.

Two points to carry correctly:
- **F:** an agent must not bypass the merge rules. Any option that edits `ci.yml` needs Stephen's own merge, under its
  code owner, and the note must say so.
- **D:** add the review's D3 (blob-keyed, no commit field) alongside D1 and D2.

## 5. The change log

Add §18, "Change log: revision 1 to revision 2", listing every finding ID with what changed and where, or why it was
not taken. Keep §17.

## 6. What to hand back

1. **Status** first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`. If your shell still fails, say so here.
2. Whether you committed (subject `[PIPELINE] P06: WP9.5 design note revision 2`, via `git commit -F` with a UTF-8
   file without a byte-order mark). If you could not, say so and leave the file written but uncommitted.
3. For each finding ID: what changed, with the section.
4. The owner points A to J, one line each, with your recommendation.
5. The Verification appendix's summary: what you ran, and every statement you marked UNVERIFIED.

Do not describe the note as reviewed or accepted. It goes to a second independent review next.
