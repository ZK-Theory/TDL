# Token-Efficiency Audit Evidence Report

**Date:** 2026-07-23
**Status:** Independent evidence report; recommendations are proposals, not workflow authority
**Workflow:** Standalone; no APM
**Subject:** Token and context efficiency in Codex research workflows only
**Evidence cut:** latest live-source event `2026-07-23T01:53:20.237Z`; per-file cuts below
**Exact starting commit:** `c8ab1399c280a63643b85bac8c3310c597849c49`

## Conclusion

The largest recorded number is cache-read input, but the largest *defensible avoidable* expenditure is not “long context” in the abstract. It is work that produced no durable return or had to be relaunched: four sessions consumed **24,957,116 processed tokens** while ending with a wrong-source stop, no substantive subtask return, or no review report. The directly defensible avoidable lower bound is **3.88 million processed tokens** (the two wrong-source launches plus the no-return subtask); **24.96 million** is the hard upper bound if the stopped adversarial review is assigned no reusable value. Its partial defect discovery means the true figure is below that upper bound but cannot be identified from token records alone.

The next largest actionable fact is the audit’s own cost. Before this report, the coordinating task spent **43,381,066 processed tokens** on the initial efficiency design and later token-audit phases, and four fresh efficiency-plan reviews spent another **28,982,721**. This fresh audit had reached **8,423,602 processed tokens** at the evidence cut (8,157,087 cache-read; 200,697 uncached input; 65,818 output, including 24,015 reasoning). Known efficiency-study expenditure was therefore already **80,787,389 processed tokens**, 31.7% of the 254,909,189 processed tokens used by the fresh WP6 tasks plus the coordinator’s WP6 phase. Another plan/review cycle would now be measurement overhead without a new empirical result. The right next step is one bounded trial, not another governance artifact.

Four proposed efficiency rules are rejected:

- An approximately-80k rotation threshold is contradicted by the telemetry. The 16 actual compactions occurred at **206,078–242,910 input tokens** (median **226,676**) and reduced the next model call to **27,811–34,322** (median **30,655**). Fourteen of the 16 fresh WP6 tasks crossed 80k; rotating each at that point would have multiplied startup and certification work.
- A fixed two-primary-skill cap is not a valid proxy. Skill-file reads were **845,279 characters**, 8.6% of the 9.83 million tool-output characters in the 16 fresh tasks, and the records do not link skill count causally to retries or defects. Removing a relevant review skill can increase remediation cost.
- Mandatory producer self-reporting of token metrics has no measured benefit in this campaign and adds prompt/output work. Usage should be reconstructed post hoc from JSONL.
- Fresh tasks do not inherently save tokens. They impose a measured startup floor and six fresh tasks still compacted. Fresh no-parent context remains justified for independent adversarial review as an independence control, not as a saving claim.

The smallest evidence-backed intervention is therefore: prevent zero-return launches, bound large reads and unchanged-file rereads within a task, keep normal validation and independent review, and measure one next comparable workflow externally. Continue a task until its subject changes or actual compaction degrades continuity; at that point use a compact exact-state handoff. Do not rotate on a fixed token number.

## 1. Authority, correction, and evidence boundary

The controlling correction removes the unsupported 80k threshold, fixed skill cap, producer metric self-reporting, and any presumption that fresh tasks save tokens. This report preserves:

- fresh no-parent context for independent adversarial review;
- actual-compaction handoff when continuity degrades;
- compact exact-state continuity; and
- evidence-based recommendations.

PR management, WP6 delivery management, external review, acceptance, and repository integration are outside scope. Historical efficiency review records were read as evidence where their sessions were part of the measured campaign; none was edited.

### Exact brief verification

The brief is committed at Git blob `f0a9d5a28968c1fc9f7091b34b092f8271bd67d2`. Its canonical LF blob has SHA-256 `e8f41c0d45a1d14c4ff50f513555ac1e570ef32ff81b1b744adeef3aeeda6b1d`, exactly the supplied identity. The Windows checkout has 178 CRLF sequences and hashes to `5fdb8d7ee107ac49c8a0931d9ec6d746c9bcc0d63775888409b30b6fc5228bcb`; CRLF-to-LF normalization reproduces the committed blob byte-for-byte. The checkout mismatch is therefore line-ending translation, not brief drift.

### Measured set

The measured set was defined from raw session relationships and outcomes, not from the seed list alone:

1. **WP6 observed workflow:** 16 fresh tasks from the first manager trial through the final independent review. This includes six manager/explorer trial tasks, two wrong-source launches, six core author/reviewer tasks, and two delegated research subtasks. It includes failed and zero-deliverable tasks.
2. **Coordinator:** session `019f8954-d0cc-7d12-ae83-e8ccb8b61165`, segmented at direct user-message boundaries into initial efficiency design, WP6 coordination, and token-efficiency audit. The phase totals use positive deltas between successive cumulative counters.
3. **Efficiency review loop:** four fresh independent plan/review sessions.
4. **Audit self-cost:** this report’s live session, reported as a lower bound through the stated cut because the session necessarily continues after measurement.

The simultaneously launched fresh WP6 manager session `019f8c99-fe13-79b3-a521-3835df6bb76e` is excluded: its delegation explicitly separates it from this audit and it began after the historical campaign. Older sessions named inside memory, instructions, or file contents are also excluded unless they were direct tasks in this campaign. This avoids treating incidental UUID mentions as session lineage.

### Session manifest

| ID | Role/outcome | Source | Bytes | Cut timestamp | SHA-256 |
|---|---|---|---:|---|---|
| `019f8954-d0cc-7d12-ae83-e8ccb8b61165` | coordinator / mixed_multi_subject | `sessions/2026/07/22/rollout-2026-07-22T11-17-50-019f8954-d0cc-7d12-ae83-e8ccb8b61165.jsonl` | 14,504,590 | `2026-07-23T01:45:14.549Z` | `c8f8a9f9b708c05c7e02cfa256f92e148dca4d5a74768ae15954c49dfa410366` |
| `019f89d0-7cdb-7163-8f1b-20a8c2e813f6` | initial_manager_trial / handback | `archived_sessions/rollout-2026-07-22T13-32-54-019f89d0-7cdb-7163-8f1b-20a8c2e813f6.jsonl` | 1,389,839 | `2026-07-22T12:46:15.972Z` | `94b653c25c37a23ee18fd05d5110764ad8ade854e13076e28168d177fe35627c` |
| `019f89d3-02e5-7af3-a02c-2f81d742c2bc` | initial_trial_acceptance_explorer / analysis_returned | `archived_sessions/rollout-2026-07-22T13-35-40-019f89d3-02e5-7af3-a02c-2f81d742c2bc.jsonl` | 600,244 | `2026-07-22T12:40:40.636Z` | `16c91283c3e2124c95c02c0490dadc27926ba7ead3e85e86b5d486ff4cd7529c` |
| `019f89d3-3f90-7af2-9fad-d7500a768562` | initial_trial_t2_explorer / analysis_returned | `archived_sessions/rollout-2026-07-22T13-35-55-019f89d3-3f90-7af2-9fad-d7500a768562.jsonl` | 795,552 | `2026-07-22T12:42:16.195Z` | `d3b994e510df8ba3dda4933ef753621778738ba5b6924ebe9d40d4048a338932` |
| `019f89ef-d36c-7720-b416-0823d02326ae` | standalone_manager_trial / handback | `archived_sessions/rollout-2026-07-22T14-07-08-019f89ef-d36c-7720-b416-0823d02326ae.jsonl` | 948,132 | `2026-07-22T13:17:14.861Z` | `d423db817d2c419815f39e3eb444d1dded4a786e7c3e2c5ef37059c5b8d92a98` |
| `019f89f2-23d0-7971-baa6-8ce6f8cb12dc` | standalone_trial_scope_explorer / analysis_returned | `archived_sessions/rollout-2026-07-22T14-09-40-019f89f2-23d0-7971-baa6-8ce6f8cb12dc.jsonl` | 754,963 | `2026-07-22T13:14:38.453Z` | `1b37b8ff80fc1b12baf5c1e4e3ab1caab3cf273807589f93916d20a3c8249989` |
| `019f89f2-b5fa-7cc3-8c70-1a22b636de94` | standalone_trial_seam_explorer / no_substantive_return | `archived_sessions/rollout-2026-07-22T14-10-17-019f89f2-b5fa-7cc3-8c70-1a22b636de94.jsonl` | 713,516 | `2026-07-22T13:13:54.594Z` | `f5460963aa1c95ad76308f5331b64419d14a619daabd69f361cba4b5739d4671` |
| `019f8a1b-c117-7d22-988b-88e06c0c53b2` | wrong_source_launch_1 / stopped_no_deliverable | `archived_sessions/rollout-2026-07-22T14-55-07-019f8a1b-c117-7d22-988b-88e06c0c53b2.jsonl` | 271,935 | `2026-07-22T13:57:02.195Z` | `f54d1737d15e117c6247acd85ef8c458a94152a9abd300ac81f743a1191946fe` |
| `019f8a29-196a-7a80-ac03-ecc5572fdb5d` | wrong_source_launch_2 / stopped_no_deliverable | `archived_sessions/rollout-2026-07-22T15-09-42-019f8a29-196a-7a80-ac03-ecc5572fdb5d.jsonl` | 293,217 | `2026-07-22T14:11:34.130Z` | `25f90d324b42d92f31c6cc64e9413be4f11bf53c40bfd16ef235cfe8f34b7d17` |
| `019f8a2e-61a5-7b40-8b07-adb0d8243dad` | t2_author_and_first_remediation / candidate_and_remediation | `sessions/2026/07/22/rollout-2026-07-22T15-15-28-019f8a2e-61a5-7b40-8b07-adb0d8243dad.jsonl` | 4,802,149 | `2026-07-22T17:20:15.996Z` | `af124c8f98bfa16cf344e3ec691992984e3e7fe4aca49d578ad4254a4cf8646c` |
| `019f8a30-8444-77a3-af51-3558ab7577b9` | author_authority_explorer / analysis_returned | `sessions/2026/07/22/rollout-2026-07-22T15-17-48-019f8a30-8444-77a3-af51-3558ab7577b9.jsonl` | 763,132 | `2026-07-22T14:23:15.426Z` | `d372efccfce5ebd2d6ecd987eb624baa9af3a340d0f145fec5cec3b56392ffe1` |
| `019f8a80-2e64-7633-acbd-f6fb7f12ef9b` | first_independent_review / review_report | `sessions/2026/07/22/rollout-2026-07-22T16-44-49-019f8a80-2e64-7633-acbd-f6fb7f12ef9b.jsonl` | 1,599,657 | `2026-07-22T16:00:54.837Z` | `2c3068520828d5a006a89a7796610dd89ced02d10de68c4dd5f9f07f56be02b8` |
| `019f8aa5-af01-7801-95f4-35a1b9959e2b` | review_remediation_explorer / analysis_returned | `sessions/2026/07/22/rollout-2026-07-22T17-25-46-019f8aa5-af01-7801-95f4-35a1b9959e2b.jsonl` | 570,951 | `2026-07-22T16:30:37.614Z` | `f4271c08c7684d0caf4c60ca95f2c1f588fa101b75c133d6618adbc7d8a1251e` |
| `019f8b0f-6fca-72f2-a551-304ff0d5d811` | cyber_boundary_review / stopped_no_report | `sessions/2026/07/22/rollout-2026-07-22T19-21-17-019f8b0f-6fca-72f2-a551-304ff0d5d811.jsonl` | 1,559,947 | `2026-07-22T18:47:57.062Z` | `3f6b4a583bbcdcc7073f40ec77fa874c1bd8d9ffe7a37ff2562719acb6003a4c` |
| `019f8b3e-5a2d-7552-9bd8-dfe7562c93b3` | static_second_review / review_report | `sessions/2026/07/22/rollout-2026-07-22T20-12-32-019f8b3e-5a2d-7552-9bd8-dfe7562c93b3.jsonl` | 2,044,274 | `2026-07-22T20:13:08.203Z` | `ac0761c8cd3d70ae6390ceb170258dabbfc18f1c732b4c9dcbb26a9cbdea4304` |
| `019f8bb8-b7e5-73b1-bb10-ca30a679cd73` | final_remediation_author / candidate | `sessions/2026/07/22/rollout-2026-07-22T22-26-11-019f8bb8-b7e5-73b1-bb10-ca30a679cd73.jsonl` | 2,674,461 | `2026-07-22T22:13:44.673Z` | `ae5dcdf796d2092a9c50b0448a4013f7c094cd2b25fbf78390adc316dec194f2` |
| `019f8beb-f6f7-7900-b14c-3c7da567ba25` | final_independent_review / review_report | `sessions/2026/07/22/rollout-2026-07-22T23-22-10-019f8beb-f6f7-7900-b14c-3c7da567ba25.jsonl` | 1,372,579 | `2026-07-22T22:42:03.488Z` | `76bbd83298c860e45c5cf90dde483c85f4afbc07a8ab452d5ddb784f6580cc41` |
| `019f8c3e-769d-77a3-9b7a-9d2fa1c24d25` | efficiency_plan_review_r1 / review_report | `sessions/2026/07/23/rollout-2026-07-23T00-52-16-019f8c3e-769d-77a3-9b7a-9d2fa1c24d25.jsonl` | 1,166,036 | `2026-07-23T00:08:45.280Z` | `20833ba30bdd16eb56d549c75de8d2688e2e1c0525a7516ffdae135f14277b60` |
| `019f8c51-a665-7581-ba15-9f00a1496707` | historical_efficiency_review / review_report | `sessions/2026/07/23/rollout-2026-07-23T01-13-16-019f8c51-a665-7581-ba15-9f00a1496707.jsonl` | 1,182,856 | `2026-07-23T00:29:21.157Z` | `23308d7ccbd41382ec87178d77e2ff7372e202336e28a5094eb6fee6626c7f4f` |
| `019f8c70-ba2f-7a61-9a14-f85d4d00fa0d` | efficiency_plan_v2_review / review_report | `sessions/2026/07/23/rollout-2026-07-23T01-47-14-019f8c70-ba2f-7a61-9a14-f85d4d00fa0d.jsonl` | 978,822 | `2026-07-23T00:57:17.640Z` | `51ec74f450a53961d477a689a258a1dcef349d1cb3dc4ce71ed3d827f7d79982` |
| `019f8c84-6d2a-7782-a8de-352b06e6f382` | efficiency_plan_v2_1_review / review_report | `sessions/2026/07/23/rollout-2026-07-23T02-08-46-019f8c84-6d2a-7782-a8de-352b06e6f382.jsonl` | 1,022,567 | `2026-07-23T01:18:13.838Z` | `8cdad88f551a8a017e74ebbb45b14124d566b679da3e2d93a3cfa453252c723f` |
| `019f8c99-a392-73d0-8138-733d24cbe9ad` | current_token_evidence_audit / live_lower_bound | `sessions/2026/07/23/rollout-2026-07-23T02-31-55-019f8c99-a392-73d0-8138-733d24cbe9ad.jsonl` | 1,204,523 | `2026-07-23T01:53:20.237Z` | `2e75268de0ad991ea818196cb642f745eb251524bcd1109decb1780b46c3d53a` |

The SHA-256 values bind the exact JSONL byte snapshots used. The coordinator and current audit are live files; their cut timestamps and hashes identify the bounded snapshots, not their future final state.

For the append-only current audit file, reproduce the bound after later activity by hashing its first 1,204,523 bytes; that prefix ends on a JSONL newline and hashes to `2e75268de0ad991ea818196cb642f745eb251524bcd1109decb1780b46c3d53a`. Later bytes are outside the evidence cut.

## 2. Reproducible method and commands

The adjacent script [token-efficiency-audit-analysis-2026-07-23.py](./token-efficiency-audit-analysis-2026-07-23.py) uses only the Python standard library and reads:

- `C:\Users\steph\.codex\sessions\**\rollout-*.jsonl`
- `C:\Users\steph\.codex\archived_sessions\rollout-*.jsonl`

Run from the repository root:

```powershell
python docs/plans/agentic-research-system/reviews/token-efficiency-audit-analysis-2026-07-23.py --pretty
ccusage codex session --json --since 2026-07-18 --until 2026-07-23 --no-cost --offline
ccusage codex session --json --since 2026-07-18 --until 2026-07-23 --offline
```

The first `ccusage` command is the cross-check used by the script. The cost-enabled command exposes an offline price estimate, not an invoice; it is included only so another auditor can inspect the interpretation.

The parser:

1. snapshots each source file as bytes and hashes that snapshot;
2. parses the schema actually present in each line;
3. uses the final cumulative `total_token_usage` for the session baseline;
4. infers model calls and phase usage only from positive deltas between cumulative records;
5. treats `reasoning_output_tokens` as a subset of output;
6. pairs each `compacted` record with the last advancing call before and first advancing call after it;
7. counts tool-output characters without converting them to model tokens; and
8. labels file-level rereads structurally without claiming that every reread was avoidable.

Payload text is not copied into the result. Roles and outcomes are bounded labels derived from dispatches and final returns.

## 3. Metric definitions and the `ccusage` discrepancy

| Metric | Definition | Additive? | Interpretation |
|---|---|---:|---|
| Cache-read input | Raw cumulative `cached_input_tokens` | Yes, as a final cumulative total | Previously supplied context served from cache; it is processed volume, not equivalent to new input or list-price input. |
| Uncached input | `input_tokens - cached_input_tokens` | Yes | New/non-cache input. Raw `input_tokens` already includes cache-read input. |
| Cache-write input | Raw cumulative `cache_write_input_tokens` | No extra addition | A subset of input associated with cache creation/write. It is reported separately and is not added again. |
| Output | Raw cumulative `output_tokens` | Yes | Generated output, including reasoning output. |
| Reasoning output | Raw cumulative `reasoning_output_tokens` | **No** | A subset of output, reported diagnostically. Adding it to output double-counts. |
| Processed | Raw cumulative `total_tokens` = input including cache + output | Yes | Aggregate model-processed volume. It is neither an invoice nor an assurance-normalized efficiency score. |
| Non-cache API volume | Uncached input + output | Yes | Useful secondary view; still not billed cost. |
| Tool-output characters | Serialized character count in tool results | Yes as characters | Structural context-loading measure. Exact model-token attribution is unavailable. |

### Why cumulative totals are primary

Eight of 22 sessions contain at least one `token_count` record where cumulative totals do not advance but `last_token_usage` repeats nonzero input/output components. Compaction also emits unchanged cumulative records whose input/output components are zero while `last_token_usage.total_tokens` is nonzero. Summing every “last” record therefore double-counts.

This explains the provisional anchors. For the six core author/reviewer sessions:

| Source | Cache-read | Uncached input | Output | Reasoning subset | Processed |
|---|---:|---:|---:|---:|---:|
| Final raw cumulative counters | 154,526,048 | 2,447,400 | 566,823 | 169,480 | 157,540,271 |
| `ccusage` / brief anchor | 155,242,440 | 2,458,080 | 567,572 | 169,657 | 158,268,092 |
| `ccusage` minus raw | **716,392** | **10,680** | **749** | **177** | **727,821** |

The four efficiency-review anchors also exactly reproduce current `ccusage`, but exceed the raw cumulative baseline by 153,241 processed tokens. Across the 22-session cut, `ccusage` differs on eight sessions. It also reports `cacheCreationTokens: 0` for all 22 while raw cache-write counters are nonzero in all 22 (4,167,635 for the 16 fresh WP6 tasks). The raw cumulative counters are therefore the report baseline; `ccusage` is a convenient but currently non-canonical cross-check.

No actual billed cost is present in JSONL. `ccusage --offline` applies cached model-pricing metadata and reports an estimate. Codex subscription/rate-limit accounting may not equal that estimate, and cache-read tokens must not be treated as uncached input without a stated weighting. This report does not rank interventions in dollars.

## 4. Quantitative baseline

### Fresh workflow tasks

| Group | Sessions | Inferred calls | Compactions | Cache-read | Uncached input | Output | Reasoning subset | Processed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All fresh WP6 tasks | 16 | 1,480 | 7 | 183,023,449 | 4,221,823 | 705,162 | 224,936 | 187,950,434 |
| Six core author/reviewer tasks | 6 | 1,180 | 6 | 154,526,048 | 2,447,400 | 566,823 | 169,480 | 157,540,271 |
| Manager/explorer trials | 6 | 237 | 1 | 24,100,253 | 1,395,997 | 98,229 | 34,188 | 25,594,479 |
| Wrong-source launches | 2 | 19 | 0 | 685,842 | 102,638 | 9,472 | 4,629 | 797,952 |
| Delegated research subtasks | 2 | 44 | 0 | 3,711,306 | 275,788 | 30,638 | 16,639 | 4,017,732 |
| Four no-report/no-substantive-return sessions (cross-group) | 4 | 170 | 1 | 24,248,255 | 647,798 | 61,063 | 22,700 | 24,957,116 |
| Four efficiency-plan reviews | 4 | 245 | 0 | 27,867,690 | 904,017 | 211,014 | 68,347 | 28,982,721 |

Cache reads are 97.7% of input across the 16 fresh tasks and 98.4% across the six core tasks. That makes context replay the dominant processed volume, but not automatically the dominant billed cost or avoidable volume.

All 16 fresh tasks used `gpt-5.6-sol`: six at `high` and ten at `xhigh`. All four efficiency reviews used `xhigh`. Reasoning output was 224,936 tokens across the 16 tasks—31.9% of output but only 0.12% of processed tokens. There is no matched model/effort experiment, so no causal saving can be assigned to a downgrade.

### Coordinator phases

| Phase | Calls | Cache-read | Uncached input | Output | Reasoning subset | Processed |
|---|---:|---:|---:|---:|---:|---:|
| Initial efficiency design | 110 | 12,289,573 | 437,374 | 68,894 | 23,199 | 12,795,841 |
| WP6 coordination | 488 | 64,960,582 | 1,746,168 | 252,005 | 82,925 | 66,958,755 |
| Token-efficiency audit before fresh head | 268 | 29,633,766 | 775,988 | 175,471 | 68,038 | 30,585,225 |

The coordinator crossed three subjects, accumulated nine actual compactions, and made 387 repeated file-path accesses under the structural detector. Its 110.34-million processed-token total is not a single comparable workflow result; the phase split is required.

### Startup, prompts, tools, and validation

Across the 16 fresh tasks:

- first calls consumed 422,074 input tokens in total (mean 26,380);
- first base-instruction text totalled 283,680 characters;
- first injected AGENTS/environment context totalled 194,628 characters;
- visible dispatch text totalled at least 42,147 characters (delegated subtask payloads are encrypted/absent from normal message text, so this is a lower bound);
- 51 skill-file reads returned 845,279 characters, of which 23 research-observer reads returned 456,199;
- all tool results returned 9,827,607 characters, including 186 results of at least 20,000 characters; no result reached 100,000;
- file reads returned 4,016,319 characters, searches 1,655,971, Git inspection 1,574,579, observation records 840,276, and validation 450,980; and
- the structural path detector found 686 same-session reread accesses. The most repeated paths were core authority materializers/validators and the 06b live-capability plan, so a large part of the count is plausibly research assurance, changed-file reinspection, or independent review rather than waste.

There were 167 validation calls. Seven were exact command repeats, all in the long author session; every consecutive repeat had at least one patch event between it and the prior run. The evidence therefore supports **zero** unchanged-surface exact validation duplicates. Removing validation because the command text repeated would weaken assurance without a measured saving.

## 5. Ranked causes

The rows below overlap and must not be added. “Avoidable” is a counterfactual bound, not a bill.

| Rank | Cause | Direct evidence | Conservative avoidable range | Confidence and assurance consequence |
|---:|---|---|---|---|
| 1 | Context-heavy navigation and replay | 183.0m cache-read tokens, 9.83m tool-output characters, 186 outputs ≥20k characters, 686 reread accesses in 16 fresh tasks | **0 directly proven; narrower upper bound unknown** because characters cannot be attributed to model tokens and exact duplicate reads were zero | Low-to-medium. Much of the evidence was needed for provenance, changed-file validation, or fresh independent review. Aggressive truncation can hide a decisive clause or defect. |
| 2 | No-report, no-return, and wrong-source work | Four sessions, 24.96m processed; includes two wrong-source stops (0.80m), one subtask with no substantive return (3.08m), and one stopped adversarial review (21.07m) | **3.88–24.96m processed**; the lower bound excludes the stopped review entirely, while the hard upper bound assigns it no reusable value | Medium. The aborted review did expose defects, so the true avoidable amount is below the upper bound. |
| 3 | Mixed-subject coordinator longevity | 66.96m WP coordination plus 43.38m efficiency work; nine compactions; 387 structural reread accesses | **0 directly proven; upper bound unknown**, non-additive with rank 1 | Low. A subject handoff may reduce rereads, but a fresh task repeats startup/certification and can also compact. Use subject/continuity evidence, not a fixed threshold. |
| 4 | Efficiency-method design/review loop | 43.38m coordinating efficiency work + 28.98m in four review sessions, before this audit | Historical avoidable fraction **unknown**; a further identical four-review loop would add about **29.0m** plus coordinating work without new trial evidence | High that another loop is poor value; low on hindsight attribution because the reviews exposed the unsupported rules now removed. Stopping design review too early can preserve a bad intervention. |
| 5 | Fresh-task startup and policy packets | 422k first-call input, 478k base/injected characters, at least 42k dispatch characters, 845k skill-output characters across 16 tasks | **0–0.422m first-call input** as a hard, deliberately loose bound; no component-level saving is attributable | Medium that it is real, high that it is not the main cause. Over-compression can drop authority, provenance, or stop conditions and cause larger retries. |
| 6 | Validation repetition or reasoning level | 167 validation calls; seven exact repeats all followed changes; reasoning is 0.12% of processed volume; no matched effort comparison | **0 measured** | High. Blanket cuts are unsupported and risk mathematical/statistical/provenance defects or retry cycles. |

### Compaction and the failed 80k premise

There were 16 actual compactions across the coordinator and measured fresh tasks. Pre-compaction input ranged from 206,078 to 242,910; the next advancing call ranged from 27,811 to 34,322. In the 16 fresh WP6 tasks alone, 1,024 of 1,480 inferred calls were already at or above 80k and 243 were at or above 200k. Fourteen tasks crossed 80k, but only six compacted.

An 80k rule would therefore be a large behavioural intervention, not a measurement boundary. The data do not show that the resulting fresh startups would be cheaper, and the rule would break long single-turn author/reviewer work well before the platform compacted it. Actual compaction is an observable continuity event; it is the defensible trigger to *consider* a handoff when the subject state has degraded.

## 6. Ranked minimal interventions

### 1. Stop the methodology loop and run one trial

Do not write or review another efficiency plan before observing one bounded workflow. A fresh efficiency review cost 4.12–10.80m processed tokens in this set (mean 7.25m); four reviews cost 28.98m. External post-hoc measurement can answer the next question more directly.

**Downside:** a plan flaw may survive into the trial. **Control:** keep the trial reversible, preserve ordinary validation and fresh independent adversarial review, and change no repository-wide convention based on one result.

### 2. Prevent provable zero-return launches with one pre-launch state check

Before creating a task, resolve the exact source commit and worktree start once. If they differ, correct the launch source before model work begins. Do not create a parallel exploratory subtask unless its one return is needed by the parent. This is a command-level preflight, not a new registry, report, or gate system.

**Expected effect:** the observed two wrong-source launches cost 0.80m processed tokens, and the no-return explorer cost 3.08m. Avoiding a stopped late review can save more, but that depends on scoping the research-value boundary without suppressing real adversarial checks.

**Downside:** preflight can itself grow into bureaucracy. **Control:** one read-only check with no durable artifact; do not repeat it after the exact state is unchanged.

### 3. Bound navigation output and reuse unchanged evidence within a task

For a known large file, search for the relevant section and read bounded ranges first. Read the full artifact when a whole-file identity, cross-section relationship, or independent-review claim requires it. Within one task, reuse a verified read until the file changes, actual compaction creates uncertainty, or a contradictory finding requires reinspection. Bound test/log output to the portion needed to decide pass/fail, while retaining full raw logs outside model context when necessary.

**Expected effect:** this targets the 7.25m characters returned by file reads, searches, and Git inspection and the 686 structural reread accesses. Exact token saving is not derivable; the trial should determine it.

**Downside:** bounded reads can omit a decisive caveat, and stale reuse can invalidate provenance. **Control:** full reads remain mandatory for source-critical whole-file review; reread any changed file; a fresh independent reviewer receives no inherited conclusions.

### 4. Use subject and actual continuity loss—not token count—to decide handoff

Continue a coherent task while its subject and verified state remain intact. At a subject transition, or after actual compaction when the task can no longer reliably reconstruct exact state, write the smallest exact-state handoff needed by the successor. Do not create a handoff merely because a counter crosses 80k.

**Expected effect:** unknown. This removes forced startup duplication while retaining compact continuity where it has evidence value.

**Downside:** waiting for visible degradation can keep a task alive too long. **Control:** actual `compacted` records, contradictory restatements, repeated reorientation reads, or loss of exact subject identity are observable handoff signals. Fresh no-parent context remains mandatory for independent adversarial review regardless of saving.

### 5. Measure externally; do not make producers optimize their own telemetry

Run the analysis script after the workflow. Producers should report research state, validation, and blockers, not token-efficiency metrics. Load whatever skills the task genuinely needs; do not enforce a numeric skill cap.

**Expected effect:** avoids unmeasured self-report and skill-selection gaming. Skill output was only 8.6% of fresh-task tool-output characters; relevance matters more than count.

**Downside:** a producer may not notice runaway context in real time. **Control:** the platform’s actual compaction signal and normal operator observation remain available; the external audit detects systematic issues without contaminating every prompt.

### Rejected interventions

- **Do not cut validation based on command repetition.** All exact repeated validations followed changes.
- **Do not downgrade model/reasoning globally.** There is no matched quality/retry comparison, and review assurance is high consequence.
- **Do not eliminate fresh independent review.** Fresh reviewers found critical/major relational and provenance defects that passing candidate tests did not establish.
- **Do not convert these findings into another mandatory governance layer.** The measured audit loop is already large enough to dominate plausible savings.

## 7. One bounded next-workflow trial

Use the next research workflow whose lifecycle is comparable to a bounded author task followed by an independent review. Do not choose a novel workflow with no historical comparator.

### Trial intervention

1. Resolve the exact starting source before task creation; no knowingly mismatched launch.
2. Keep one coherent subject in the author task. No fixed token/context threshold.
3. Search and range-read known large sources first; full-read any whole-file authority or provenance source.
4. Reuse unchanged same-task reads; reread after edits, actual compaction uncertainty, or contradiction.
5. Run the normal focused validation after each changed surface and the normal final validation. Do not weaken mathematical, statistical, provenance, or reproducibility checks.
6. Send the completed subject to one fresh no-parent independent adversarial reviewer as the independence control.
7. If actual compaction degrades continuity, hand off a compact exact-state packet. Otherwise continue.
8. After both tasks finish, run the script externally. Neither producer writes efficiency metrics or an efficiency report.

### Measurements

Record separately for author and reviewer:

- raw cache-read, uncached input, cache-write input, output, reasoning subset, and processed totals;
- inferred calls, actual compactions, first-call input, and pre/post-compaction input;
- tool-output characters, outputs ≥20k characters, and structural reread accesses;
- stopped launches, retries, and whether a durable deliverable was produced;
- changed paths and validation outcomes only to assess comparability, not as a denominator that rewards fragmented edits; and
- reviewer findings and any subsequent remediation, so a token reduction that shifts cost into defects/retries fails.

Use the final remediation author (`019f8bb8…`: 29.86m processed, 0.402m uncached input, 0.116m output) and final independent reviewer (`019f8beb…`: 13.81m processed, 0.241m uncached input, 0.059m output) only if scope and lifecycle are genuinely comparable. Otherwise report the trial without a causal saving percentage.

### Decision rule

The trial succeeds only if it produces the required research artifact and independent review with no assurance regression, no stopped/relaunched task, and a directional reduction in cache-read or navigation-output volume that is not offset by higher uncached input, output, remediation, or retry work. No fixed percentage is required. One result authorizes at most a second comparable observation; it does not create a repository-wide rule.

Stop after the post-hoc comparison. Do not send the efficiency result through another adversarial plan-review cycle unless it proposes a high-risk change to research assurance.

## 8. Explicit unknowns

- JSONL does not expose actual billed cost or Codex subscription accounting. Offline `ccusage` cost is an estimate.
- Cache-read weighting against uncached input is not established here; processed tokens are not a quality- or price-normalized efficiency score.
- Exact token attribution to an individual file read, tool output, skill, or prompt clause is unavailable. Character counts and next-call context growth are structural evidence only.
- The file-path detector can count a path referenced by a read-like command even when only part of that command read it. It is suitable for concentration/ranking, not billing.
- Subagent dispatch text may be encrypted or absent from ordinary message payloads, so visible dispatch characters are a lower bound.
- A no-report adversarial session may still influence later work. Its avoidable fraction cannot be set to 100% without reconstructing how its partial findings were used.
- The evidence does not support a universal best task length, compaction threshold, skill count, model, or reasoning level.
- The evidence cannot distinguish a necessary reread after changed state from every avoidable reread without semantic, call-by-call adjudication.
- The current audit’s own total is a lower bound at the cut; final response and Git operations occur later.
- One future trial cannot establish a universal saving. It can reject a harmful intervention and justify or reject one further comparable observation.

## 9. Evidence integrity checks

At the stated cut:

- analysis-script SHA-256: `4f5532bf059c372f6b0e8c7127f7413a1a0bdcd3fd5c2387c0f45c5a867284ea` (550 formatted lines);
- 22/22 named JSONL files were found and 22/22 appeared in `ccusage`;
- duplicate session IDs: 0; JSON parse errors: 0; negative cumulative deltas: 0;
- processed-token identity failures (`processed != input + output`): 0;
- compaction-to-pair mismatches: 0; `compacted`/`context_compacted` count mismatches: 0;
- `ccusage` field mismatches against raw cumulative totals: 8 sessions, reported rather than suppressed; and
- exact duplicate validations with no intervening patch: 0.

The historical review records, repository instructions, skills, hooks, workflow conventions, WP6 artifacts, and unrelated files were not changed.
