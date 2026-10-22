# Independent review: the W9-D8c Discovery backlog observation at `46c2adf0`

**Date:** 2026-10-22
**Reviewer:** the independent session that reviewed W9 drafts 0.1 to 0.5. It is neither the observer session nor the
W9 author.
**Authority:** read-only review. By Stephen's instruction for this round, the reviewer read the live vault backlog
once, read only, and the freeze handoff §3, read only. Nothing was written to the vault, `papers/`, `.apm/`, any ARS
store, GitHub or Jira. This file is the only file written in the repository.

## 1. Subject

| Identity | Value |
|---|---|
| File | `docs/plans/agentic-research-system/transition/discovery-backlog-observation-2026-10-22.md` |
| Commit | `46c2adf0` on `claude/gate7-prep-docs-5202cf` |
| Blob | `a0bb971a38682b05f4b59384408bbcc50b7d24d3` (`git rev-parse 46c2adf0:<path>`) |
| origin/main at review | `3fa437a160ab75c5fa0083fd35176006b1ee19a4` (after `git fetch origin`; unchanged) |

## 2. My read of the live file

| Field | Value |
|---|---|
| Method | One `open(path, "rb").read()` of `C:\Users\steph\Documents\TDA-Research\00-Meta\Discovery\_backlog.md`, run with `python -I`. The script is a reviewer-written scratchpad file with an independent parser of the observation's §2 convention; the observer's code was not used. The bytes were kept in memory and saved as a scratch snapshot outside the vault. Everything below comes from that single read. |
| Read time (UTC) | 2026-10-22T12:20:15.578265Z to 12:20:15.578452Z |
| Result | 27,590 bytes; SHA-256 `96b5775ca3ba777d7cf13ebdd1f60bc187c08316bf5c2683c5496d7ff2b818a1`: **matches**. The file had not changed since the observation (12:14:17Z), so a full recomputation was possible. |
| Metadata (not content evidence) | `os.stat` mtime 2026-07-18T15:26:39.075334Z, size 27,590; `os.path.realpath(C:\Users\steph\TDL\vault)` = `C:\Users\steph\Documents\TDA-Research`. Both match §6. |

## 3. Verdict

**PASS WITH FINDINGS.**

| Severity | Count |
|---|---|
| Blocking | 0 |
| Major | 0 |
| Minor | 3 |
| Info | 3 |

Every number in the observation reproduces exactly from an independent parse, and the coverage is complete. The
findings are a miscounted bullet list in §3.1 (not a hashed field), a §5 cross-reference that W0-D4 needs completed
for WT-2 and WT-3, and selector hardening before the convention is reused. None affects the hashed inventory.

## 4. Recomputation

| Figure | Observation | Recomputed | Result |
|---|---|---|---|
| Byte length | 27,590 | 27,590 | match |
| Full-file SHA-256 | `96b5775c…b818a1` | `96b5775c…b818a1` | match |
| Line count / LF / CR / tab / NUL / BOM / final LF | 154 / 154 / 0 / 0 / 0 / no / yes | 154 / 154 / 0 / 0 / 0 / no / yes | match |
| UTF-8 decode | yes | yes | match |
| Item 1 `tda-scale-research-ars` L24–L33, 1,593 B | `4b325973…` | `4b32597338a6fe5afc170322476e2b7e20fb3168932abe74294bfdcabdad10b9` | match |
| Item 2 `sheaf-laplacian-employment-transitions` L35–L42, 1,626 B | `757ac0cf…` | `757ac0cf70042a037b594de51434258cc35fdb6da97c3b53a2fb9cfe559d6048` | match |
| Item 3 `mcbif-multiscale-clustering` L44–L62, 8,161 B | `0a47cdca…` | `0a47cdca9e0b5ea0d99a5c84fbbf34c6dc0619b79d1fe38ce94aceb447437863` | match |
| Item 4 `c1-persistent-laplacian-nonharmonic-spectrum` L64–L77, 3,857 B | `0135c5ee…` | `0135c5eea0210a90b5d10107965fe8941ab16acf0cd849e6cd43f3891f5de6b8` | match |
| Item 5 `t128-spike-1-…-giotto-dispatch` L79–L87, 1,470 B | `9d164fd9…` | `9d164fd99fdb0cf49f7bdd7d87ed3753484b52ccc28d947375a3e508b14e20d6` | match |
| Item 6 `t128-spike-2-complex-reduction` L89–L97, 1,452 B | `0c5610e6…` | `0c5610e6298d2e10af932607ba371def7b78a268374c59cb4a932572fbf04b22` | match |
| Item 7 `t128-spike-3-w2-truncation` L99–L108, 1,683 B | `c4ff1021…` | `c4ff10218192034b3cf575a369666fdc2a1c141d41e7eb7b78dff0f8d375ef7f` | match |
| Item 8 `t128-spike-4-persistent-laplacians` L110–L118, 1,492 B | `63cfc3d1…` | `63cfc3d1a66a25d123e573ff71380dfe5736be7d0f3fa21e474bcfdea15a118d` | match |
| Item 9 `strand-persistence-survival-testing` L120–L154, 5,454 B | `c723a245…` | `c723a2453e81006568ab7b9b3d95bfba8aa21710f79cd98e4f98785891a80ecd` | match |
| Status lines L26, L37, L46, L66, L81, L91, L101, L112, L122 | as in §3 | `732b8832…`, `5ed95f4f…`, `dfe00159…`, `2d512d44…`, `ea7cada4…`, `ff067dd0…`, `0a4197bd…`, `2668f387…`, `46933c62…` | all 9 match; each is the first bullet whose bold label starts with `state` |
| Secondary lines L47, L48, L49 | as in §3.1 | `e2e8b0d6…`, `93b40e59…`, `008a7d79…` | all match |
| L58 (`next (updated 2026-07-18 …)`) | `42589664…` | `42589664e3b423832bd7d7d424b6e5700288a067aa65c1692d61bc37bdd5875b` | match |
| L30 (SPEC-01 mention) | `73728495…` | `73728495650bb4444d86cad6ecb7df443e1853d2c9c3cdb5ec3927b18bb20d98` | match |
| Front matter L1–L4 | `d80c6327…` | `d80c6327a0a5544d58b9b1f8881616aaea464376457dd0be63a9d2ab65b0e649` | match |
| B1 L8–L12 | `cf83674f…` | `cf83674f84a5fb5758e49a94d7a7cb61036205e57e2cb56af5bdf2a0c57e1d3b` | match |
| B2 L16–L20 | `264f88bb…` | `264f88bb85820eec3eb770afddb22b2aec8918de81c4409eb9de8f3e430281d7` | match |

Spot checks of non-hashed claims also hold:
- the latest date in the file is 2026-07-18;
- the only lines naming `P01-B` or `SPEC-01` are L30, L133, L139, L146 and L148;
- no `WT-<n>`, `P04` or `obj_` token appears anywhere;
- item 9's continuation lines are L138–L143, L145–L147 and L150–L154, under bullets at L137, L144 and L149.

## 5. Completeness

My parser classified every one of the 154 lines (`recompute_result.json`, scratchpad):
- **Items:** the nine items cover L24–L33, L35–L42, L44–L62, L64–L77, L79–L87, L89–L97, L99–L108, L110–L118 and
  L120–L154.
- **Non-blank lines outside items:** exactly front matter L1–L4, title L6, B1 L8–L12, heading L14, B2 L16–L20 and
  the rule L22. These are the §4 blocker rows and structural regions, and nothing else.
- **Blank lines:** every remaining line (L5, L7, L13, L15, L21, L23 and the separators between items) is blank.
- **Overlaps:** no line is covered twice.
- **Headings:** the only headings are L6 (`#`) and L14, L24, L35, L44, L64, L79, L89, L99, L110, L120 (`##`).
  Nothing is omitted or doubled.

## 6. Findings

### Minor

- **m-1. §3.1 miscounts item 3's `next` bullets (observation line 63).** It says "four `next` bullets (L58–L61).
  Three of them carry `superseded`". The file has **five**, L58 to L62. L62 is `next (superseded 2026-07-03):`,
  and **four** carry `superseded` (L59–L62). Because L62 is inside item 3's hashed range (L44–L62), no hash is
  affected. Correct the sentence before acceptance.
- **m-2. §5's "not found" for WT-2 and WT-3 is accurate as a token search but incomplete for W0-D4.** The freeze
  handoff §3 (read for this review) gives their content:
  - **WT-3:** "BHPS non-replication follow-up: PARKED. The USoc-only signal is recorded in the 2026-07-16
    `[RESULT]`; any finer-state-space or different-window follow-up is an ARS-native pre-registered candidate".
    That is the employment arm of **row 3**: L47 reads "pursue the BHPS non-replication (finer state space /
    different window) or record the USoc-only signal and PARK", and L58 names the same decision.
  - **WT-2:** "time-resolved-PL substrate disagreement (+7.2 sd vs −0.11 sd): PARKED". That is the time-resolved
    redesign in **row 4**: L76–L77 record the "Time-resolved-substrate pre-reg LOCKED 2026-07-10 … →
    `/pre-reg-to-dispatch`".
  - Neither park is recorded in the backlog. Row 3 still reads "USER DECISION PENDING on replication", and row 4
    still shows the redesign awaiting dispatch, with no "+7.2" or "0.11" anywhere. Both are stale relative to the
    2026-07-17 handoff.

  Recommended correction: map WT-3 → row 3 (L47, L58) and WT-2 → row 4 (L76–L77) in §5, each with a
  `stale_projection_of` note naming freeze handoff §3 as the stronger record (W0 manifest §8.4). Do not add them as
  rows.
- **m-3. The §2 convention is reproducible but should be hardened before it serves as a selector beyond this dated
  inventory.** I reproduced all nine items from the text of §2 alone, so the convention is reproducible. Before it
  is reused (W9 §5.5 for later re-observations, or as input to W11's §7.6.1 inventory):
  - replace "the `---` rule at L22" with a positional-free rule: the first thematic break after the front matter;
  - record each item's start and end byte offsets next to its line range, since W11's selectors are byte ranges
    plus raw-row hashes;
  - say how a future level-1 or level-3 heading or an extra `---` inside an item is treated (blocker row, by
    analogy with W9 §5.5);
  - state that duplicate anchors are blocker rows (W9 §5.5 already does).

  None of this changes a hash at today's bytes.

### Info

- **I-1.** Every hash, length and count the observation reports reproduces exactly (§4). The single-observer
  limitation in its §7 is now discharged for these bytes.
- **I-2. Bounding the 2026-07-18 change.** The old hash `37eec1ba…` was first committed in `70074d42`
  (2026-07-18T00:58:21+01:00, i.e. 2026-07-17T23:58:21Z; `git log -S`). The earlier read therefore happened by then.
  The file's mtime (2026-07-18T15:26:39Z, metadata only) is later. Row 3's state "updated 2026-07-18" (L46, the
  deprivation battery completion) is the most likely candidate for the 1,198-byte change. This supports, but does
  not prove, the observer's first reading in §1. No earlier byte copy exists to diff.
- **I-3. Legacy status text is stale in at least two rows (from m-2).** That confirms the observation's decision
  not to read status words as states. Any later W11 transition of rows 3 or 4 should take the freeze handoff's
  PARK records as the stronger source.

## 7. Recommendations

**B1 and B2: accept as classified non-item structural regions, not as items and not as open blockers.**
- B1 (L8–L12, `cf83674f…`) is preamble.
- B2 (L16–L20, `264f88bb…`) is the lifecycle diagram, together with its heading L14.
- Record both with their hashes as explicitly classified structural bytes. W11 §7.6.1 requires structural bytes to
  be classified, not left as uncovered regions.
- Attach one qualifier to B1: its "single source of truth for lifecycle state" claim is legacy self-description,
  bounded by P-004/P-032. It has no authority over successor-owned Discovery objects.
- Neither needs a transition. At any later whole-path cutover they are part of the closure's structural bytes.

**WT-2 and WT-3 under W0-D4:**
- Treat them as **sub-items of rows 4 and 3**, through the m-2 mapping, not as missing rows. W0-D4's condition is
  then satisfied for them once the inventory is accepted with that mapping.
- Any 06l Step 3 or later action touching them is an action on row 3 or row 4. That action must take the freeze
  handoff's PARK as the stronger record.
- The handoff calls both "ARS-native pre-registered candidates". Reviving either is therefore a **new successor
  Candidate** (W11 OR-001), citing the legacy row by lineage. It is not a legacy transition of the backlog row.
- Stephen should confirm this reading when accepting the inventory.

**Acceptance:** with m-1 corrected and m-2's mapping added, the observation is fit to be accepted as the G7-B
Discovery inventory at blob `96b5775c…`. m-3 can be applied at the next re-observation.

## 8. Limits

- **Not handle-bound.** My read, like the observer's, used a path-string `open()`, not a W11 §7.3 handle-bound read.
  Any later transition or cutover still needs that.
- **Absolute path only.** I read the absolute vault path, not the junction; the junction target was checked as
  metadata.
- **Same model family.** I run on Claude Opus 5.5, the same family as the observer and the W9 author. The
  recomputation uses my own parser but the same platform.
- **Scope of reads.** I read nothing else in the vault. Of the freeze handoff I read only §3, plus the heading list
  used to find it. Linked briefs, results and the Computational-Log were not opened for this review.
- **What "match" covers.** It confirms the bytes as of 12:20:15Z. It says nothing about the file after that.
