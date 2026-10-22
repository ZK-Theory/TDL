# Legacy Discovery backlog: dated read-only observation, 2026-10-22

**Document:** Discovery backlog observation (proposed G7-B Discovery inventory)
**Date:** 2026-10-22
**Observer:** the non-author observer session started by the Gate 7 prep session for this task. It is neither the W9 author nor the W9 reviewer.
**Authority:** this is a read-only observation. It is not import, adoption, inventory acceptance, transition or Decision authority. It becomes the G7-B Discovery inventory only after independent review and Stephen's acceptance.
**Reference:** owner decision W9-D8c (accepted conditionally by Stephen 2026-10-22); W9 §15 (`design/09-migration-compatibility-and-pilot.md`, draft 0.5); W0-D4.

The backlog stays `legacy_owned` and legacy-written. Nothing here imports, adopts, freezes or transitions any row. Status words below are copied as untrusted text. They are not read as decisions, lifecycle states or commands.

## 1. Observation record

| Field | Value |
|---|---|
| Path read | `C:\Users\steph\Documents\TDA-Research\00-Meta\Discovery\_backlog.md` (absolute vault path; not via the `C:\Users\steph\TDL\vault\` junction) |
| Read method | One `open(path, "rb").read()` in Python run with `-I`, from a script in this session's scratchpad. All figures below come from that single byte read; the bytes were kept in a scratch snapshot and parsed from there. |
| Read time (UTC) | 2026-10-22T12:14:17.172875Z (start) to 2026-10-22T12:14:17.180813Z (end) |
| Byte length | 27,590 |
| SHA-256 (full file) | `96b5775ca3ba777d7cf13ebdd1f60bc187c08316bf5c2683c5496d7ff2b818a1` |
| Line count | 154 (154 LF terminators; the file ends with LF; no CR, tab, NUL or BOM) |
| Encoding | Decodes as UTF-8; contains non-ASCII characters (em dash, en dash, arrows, Greek letters, maths symbols) |
| Final re-read | See §6 |

**Comparison with the earlier observation.** `01-current-system-evidence.md` §8.1 records 26,392 bytes and SHA-256 `37eec1ba6bb7929d95d5349ada2f75d93636c8356aad5dffc6a59981fc0269e7` on 2026-07-18, read at the junction path `C:\Users\steph\TDL\vault\00-Meta\Discovery\_backlog.md`. **The file has changed since then.** It is now 1,198 bytes longer and the hash differs. No earlier byte copy was available to me, so I cannot say which lines changed. The latest date written anywhere in the file is 2026-07-18; nothing in the text is dated after that. So the change was either made later on 2026-07-18 than the §8.1 read, or made afterwards without a date in the text. The filesystem modification time (§6, metadata only) is 2026-07-18T15:26:39Z, which fits the first reading. It does not prove it.

## 2. Parsing convention

So a reviewer can reproduce the hashes:

- Lines are the file's LF-terminated lines, numbered from 1. Each hashed span is the exact raw bytes of its lines, **including** every line's terminating LF.
- An **item** is a level-2 heading (`## `) after the `---` rule at L22, running to the last non-blank line before the next level-2 heading or the end of the file. Blank separator lines between items are structural and are not part of any item.
- The **row anchor** is the heading text after `## ` up to the first ` — ` or ` - ` separator.
- The **status text** is the bullet whose bold label starts with `state`. The table quotes its leading status phrase verbatim and hashes the whole line. Where an item has `previous state` bullets too, they are listed in §3.1.

## 3. Item inventory (source order)

Nine items. No duplicate anchors.

| # | Row anchor | Lines | Item SHA-256 (raw bytes) | Item bytes | Status line | Status text, as written (leading phrase) | Status-line SHA-256 |
|---|---|---|---|---|---|---|---|
| 1 | `tda-scale-research-ars` | L24–L33 | `4b32597338a6fe5afc170322476e2b7e20fb3168932abe74294bfdcabdad10b9` | 1,593 | L26, label `state (2026-07-16):` | `**planned / not dispatchable**` | `732b883280d26da4288e1aa55976d7e732c736deebdabc1e29273bf23c141ed3` |
| 2 | `sheaf-laplacian-employment-transitions` | L35–L42 | `757ac0cf70042a037b594de51434258cc35fdb6da97c3b53a2fb9cfe559d6048` | 1,626 | L37, label `state:` | `**registered** 2026-07-10 — dispatch pre-reg **LOCKED**` | `5ed95f4f835edfa9b304316554850efbca80eab3a6826ad917ebebdc4c0f6478` |
| 3 | `mcbif-multiscale-clustering` | L44–L62 | `0a47cdca9e0b5ea0d99a5c84fbbf34c6dc0619b79d1fe38ce94aceb447437863` | 8,161 | L46, label `state (updated 2026-07-18):` | `**deprivation scale-coherence confirmatory battery COMPLETE — PARTIAL-SIGNAL (locked rule)**`; later in the line: `**USER DECISION PENDING on refinement versus PARK**` | `dfe001591a2a29f2a1614a80ec6f1cbd645519b267e98c4164f832b619d78146` |
| 4 | `c1-persistent-laplacian-nonharmonic-spectrum` | L64–L77 | `0135c5eea0210a90b5d10107965fe8941ab16acf0cd849e6cd43f3891f5de6b8` | 3,857 | L66, label `state:` | `gate-check complete → ADDITIVE-CANDIDATE GO (2026-07-03) → dispatch pre-reg LOCKED (2026-07-07) → T-C1-1 battery run (2026-07-07) → **KILL/PARK — NEGATIVE**` | `2d512d448ed509cdade9e60d33314149f1e3550541d3807f5123f8e971ed8361` |
| 5 | `t128-spike-1-battery-instrumentation-giotto-dispatch` | L79–L87 | `9d164fd99fdb0cf49f7bdd7d87ed3753484b52ccc28d947375a3e508b14e20d6` | 1,470 | L81, label `state (updated 2026-07-16):` | `**superseded / absorbed**` | `ea7cada4375e6d3ea1ab023a73f8642f7c9ed6f0528399d04bf4d890840967b7` |
| 6 | `t128-spike-2-complex-reduction` | L89–L97 | `0c5610e6298d2e10af932607ba371def7b78a268374c59cb4a932572fbf04b22` | 1,452 | L91, label `state (updated 2026-07-16):` | `**superseded / narrowed**` | `ff067dd024d1cb09a4db067d3c83f6c4c587ce6af33b797ba935ab168e61c1f6` |
| 7 | `t128-spike-3-w2-truncation` | L99–L108 | `c4ff10218192034b3cf575a369666fdc2a1c141d41e7eb7b78dff0f8d375ef7f` | 1,683 | L101, label `state (updated 2026-07-16):` | `**superseded / absorbed**` | `0a4197bdb7062f0dd596e4716798ed1916b0f0a404a0d6bcd2d26cfdf6f66404` |
| 8 | `t128-spike-4-persistent-laplacians` | L110–L118 | `63cfc3d1a66a25d123e573ff71380dfe5736be7d0f3fa21e474bcfdea15a118d` | 1,492 | L112, label `state (updated 2026-07-16):` | `**superseded / constrained by completed evidence**` | `2668f3877fdf278838607fe217316d0a9f320c67aee96dc6e9109ef6ccb55401` |
| 9 | `strand-persistence-survival-testing` | L120–L154 | `c723a2453e81006568ab7b9b3d95bfba8aa21710f79cd98e4f98785891a80ecd` | 5,454 | L122, label `state:` | `spiked + toy-comparison run (T-STRAND-1, 2026-06-17); full-scale PROMOTE/PARK pending` (whole line) | `46933c62d6c4b4afdf9d24267598ecdd93ce96f02d332c730929706dc66e6f78` |

This observation does not classify any item as active or inactive, since that would mean reading the status words as decisions. All nine rows are listed, whatever their status text says.

### 3.1 Secondary status lines in item 3

Item 3 has one `state` bullet and three `previous state` bullets. They are recorded so none is lost. They are listed, not interpreted:

| Line | Label | Leading phrase, as written | Line SHA-256 |
|---|---|---|---|
| L47 | `previous state (updated 2026-07-16):` | `**employment confirmatory battery COMPLETE — PARTIAL-SIGNAL (locked rule)**`; later in the line: `**USER DECISION PENDING on replication**` | `e2e8b0d6b4f16c7c30b0439a8fed4d0009046fbbcd20af45ed9719e0f8de9f51` |
| L48 | `previous state:` | `**employment redesign spiked 2026-07-10 — PASS at chosen tau = 2 (smallest-tau rule)**` | `93b40e59c705d50727b5f6ccc9255227eec65dc4b3f12c6ef0f59bb4e58b6525` |
| L49 | `previous state:` | ``spiked 2026-07-03 — App 1 PASS (H1=6, Leeds 488 LSOAs, k={3,5,7}); App 2 PASS (H1=266, 500 trajectories, 5 waves); both dispatch pre-regs written → awaiting `/pre-reg-to-dispatch` `` (whole line) | `008a7d7935f128beb07e00a3bbda0970c4547682a181872f129c98a7612b0229` |

Item 3 also has four `next` bullets (L58–L61). Three of them carry `superseded` in their labels. The live-labelled one, L58 (`next (updated 2026-07-18, post-batteries):`, SHA-256 `42589664e3b423832bd7d7d424b6e5700288a067aa65c1692d61bc37bdd5875b`), names two pending User decisions on PARTIAL-SIGNAL outcomes, plus the merges of PR #101 and PR #125.

### 3.2 Other irregularities (not blocker rows)

- Item 9's heading uses ` - ` as its separator; the other eight use ` — `. The anchor is unaffected.
- Item 9 has multi-line bullets with indented continuation lines (L137–L143, L144–L147, L149–L154). They are inside the item's range and hash.
- Item 9's `note (2026-06-16)` bullet (L149–L154) records an earlier unauthorised advance of the entry to `spiked`/`registered`, and its reversion. That is history inside the item, not a separate row.
- The preamble (L10) says new entries go top of page, reverse-chronological. Item 1 (state dated 2026-07-16) sits above item 2 (2026-07-10) and item 3 (updated 2026-07-18). This observation does not check whether the order follows that rule.

## 4. Blocker rows

These are regions that are neither part of an item nor clearly structural. Structural regions are not listed: front matter L1–L4 (SHA-256 `d80c6327a0a5544d58b9b1f8881616aaea464376457dd0be63a9d2ab65b0e649`), the title L6, the section heading L14, the `---` rule L22 and blank lines.

| # | Lines | What it is | SHA-256 (raw bytes) |
|---|---|---|---|
| B1 | L8–L12 | Preamble prose under the title. It describes the backlog as the "single source of truth for lifecycle state" and gives its entry rules (top-of-page order; entries are never deleted on KILL/PARK). | `cf83674f84a5fb5758e49a94d7a7cb61036205e57e2cb56af5bdf2a0c57e1d3b` |
| B2 | L16–L20 | Fenced code block under the heading `## Lifecycle states (plan section 8)` (L14): a lifecycle diagram running `inbox -> triaged -> assayed -(PROMOTE)-> spiked -> registered -> in-progress -> submitted -> ...`, with PARK and KILL branches. It is a `## ` heading, but it describes the backlog rather than listing an item, so it is not counted in §3. | `264f88bb85820eec3eb770afddb22b2aec8918de81c4409eb9de8f3e430281d7` |

Duplicate anchors: none.

B1 and B2 are legacy self-descriptions, recorded as untrusted text. B1 calls the backlog the "single source of truth for lifecycle state", and that claim is not authority under P-004/P-032. The reviewer should decide whether B1 and B2 are accepted as non-item preamble or need a disposition of their own.

## 5. Cross-reference against W9 §15 "known from the record"

W9 §15 lists these items as things for the observer to confirm. It does not offer them as the inventory.

| W9 §15 item | Matching inventory row | Notes |
|---|---|---|
| Registered sheaf-Laplacian dispatch (P-032) | **Row 2**, `sheaf-laplacian-employment-transitions` (L35–L42) | Status text `**registered** 2026-07-10 — dispatch pre-reg **LOCKED**` (L37). `next:` (L42) reads `` `/pre-reg-to-dispatch` (Manager-side; approval on file 2026-07-10). `` The backlog does not record a dispatch taking place. |
| MCbiF decision-pending battery (P-032) | **Row 3**, `mcbif-multiscale-clustering` (L44–L62) | The literal string `decision-pending` does not occur in the file. Row 3 carries `**USER DECISION PENDING on refinement versus PARK**` (L46, deprivation) and `**USER DECISION PENDING on replication**` (L47, employment), and L58 names both User decisions. Row 1 (L32) also mentions "active MCbiF deprivation scale-coherence work" as an external dependency. |
| WT-2 (freeze handoff §3) | **not found** | No `WT` token or `WT-<n>` pattern anywhere in the file. |
| WT-3 (freeze handoff §3) | **not found** | As for WT-2. |
| MCbiF battery, Computational-Log 2026-07-16 (labelled P01) | **Row 3**, L47 (employment confirmatory battery; "Computational-Log `[RESULT]` entry filed 2026-07-16") | The backlog row carries no paper label. I did not read the Computational-Log (outside this task's read scope), so the P01 label is W9's record, not observed here. |
| MCbiF battery, Computational-Log 2026-07-18 (labelled P04) | **Row 3**, L46 (deprivation scale-coherence battery; "Computational-Log `[RESULT]` entry filed 2026-07-18") | Same caveat as above: no paper label in the backlog, and the P04 label was not observed here. |
| Any P04 items | **not found** | The string `P04` does not occur in the file. The only text W9 links to P04 is the deprivation arm of row 3, and it gets that link from the Computational-Log label, not from the backlog. W9-D13 governs P04's ownership mode. |

**Items naming P04, P01-A or P01-B, or the SPEC-01 Candidate:**

- **P04:** none.
- **P01-A:** none.
- **P01-B:** row 9, `strand-persistence-survival-testing`, at L133 ("a cached P01-B H0 diagram"), L139 and L146 (relevance and assay rationale), and L148 (`next:`, "a full-scale P01-B methods-extension pre-reg"; "PROMOTE-to-Tier-2 vs PARK not yet taken"). No other row names any `P01` variant.
- **SPEC-01:** no row of its own. It is named once inside row 1, at L30 (`**greenfield order:** SPEC-01 spectral-distance PH Assay after SCALE-01; …`, line SHA-256 `73728495650bb4444d86cad6ecb7df443e1853d2c9c3cdb5ec3927b18bb20d98`). The successor object id `obj_a9ba6213` does not occur. This fits W9 §15's statement that the SPEC-01 Candidate is successor-owned and not a legacy item. It does not prove it.

## 6. Final re-read

| Field | Value |
|---|---|
| Re-read time (UTC) | 2026-10-22T12:17:06.685905Z, after this file's sections 1–5 were written |
| Byte length | 27,590 |
| SHA-256 | `96b5775ca3ba777d7cf13ebdd1f60bc187c08316bf5c2683c5496d7ff2b818a1` |
| Byte-identical to the first read | yes |
| Filesystem last-modified time (`os.stat`, metadata only) | 2026-07-18T15:26:39.075334Z |
| `C:\Users\steph\TDL\vault` resolved target (`os.path.realpath`, metadata only) | `C:\Users\steph\Documents\TDA-Research` |

The file did not change while this observation was taken. The modification time is filesystem metadata, not content evidence, and it can be rewritten. It is consistent with the change since §8.1 having been made later on 2026-07-18 than the §8.1 read. §8.1 does not record a time of day, so this cannot be confirmed.

## 7. Limits of this observation

- **Not handle-bound.** The read went through an ordinary path-string `open()`, not a W11 §7.3 handle-bound read. Volume serial, file ID and reparse chain were not checked, and nothing ties the bytes read to a verified file identity. A reparse or hardlink swap between the path check and the read would not have been detected. A later transition or cutover still needs the fresh handle-bound observation that §8.1 calls for.
- **Path, not junction.** I read the absolute vault path. The §8.1 observation used the junction path. §6 records the junction's resolved target as metadata, but I did not hash the file through the junction.
- **No diff against 2026-07-18.** Only the old length and hash were available, so the content of the change since then is unknown.
- **Status words not interpreted.** PROMOTE/PARK/KILL, `registered`, `LOCKED`, `superseded`, `USER DECISION PENDING` and the rest are legacy text. Whether any of them reflects an accepted Decision was not checked.
- **Linked files not opened.** The briefs, pre-regs, scorecards, result notes, result JSONs, PRs and commits the items cite were not opened or checked. The Computational-Log, `papers/`, `.apm/`, ARS stores and Jira were not read.
- **W9 §15 source items checked only against the backlog.** I did not open the freeze handoff §3, so what WT-2 and WT-3 refer to was not established. "Not found" means only that no such token appears in this file.
- **Item boundary convention is mine.** The boundaries in §2 are this observer's choice. Another convention (for example, counting trailing blank lines as part of an item) would give different item hashes, though the full-file hash would not change.
- **Single observer, no independent recomputation.** The hashes were computed once by this session. The independent reviewer should recompute them from the source bytes, which is possible only while the file still has the hash in §1.
