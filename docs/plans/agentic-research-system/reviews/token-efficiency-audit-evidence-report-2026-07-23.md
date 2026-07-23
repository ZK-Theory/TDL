# Token-Efficiency Audit: All Retained Codex History

**Date:** 2026-07-23
**Status:** Independent evidence report; recommendations are proposals, not workflow authority
**Workflow:** Standalone; no APM
**Scope:** Token and context efficiency in Codex research workflows only
**Evidence cut:** Every retained complete-line JSONL prefix through `2026-07-23T04:34:46.621Z`
**Exact starting commit:** `c8ab1399c280a63643b85bac8c3310c597849c49`

## Conclusion

The earlier version of this report did not answer the commissioned question. It measured a hand-selected WP6 campaign and then generalized from it. This replacement measures all 480 retained Codex session JSONLs beneath both live and archived stores, from 2026-05-25 through the frozen cut. Earlier review records have not been edited.

The all-history evidence supports one concrete new workflow improvement:

> For known long-running processes, request a 60-second initial yield/wait and continue with waits of up to 60 seconds, allowing the tool to return early on output or completion. Do not repeatedly ask the model to issue 1-, 10-, or 30-second polling calls.

Across retained history, 6,895 positive-token inference rounds did nothing except call `wait`, `wait_agent`, or `list_agents`. They consumed 1.024 billion processed tokens, 21.47% of the measured total. For long-process `wait` calls alone, grouping consecutive waits on the same process and retaining `ceil(total requested wait / 60 seconds)` calls would have removed 2,782 inference rounds. A conservative within-sequence lower bound is 413.99 million processed tokens, 8.68% of the corpus. Of that lower bound, 410.47 million was cache-read input, 3.41 million uncached input, and 115,092 output. This is a processed-token reduction, not a claim about currency cost.

The evidence also supports preserving an existing practice: use a focused delta review for a remediation follow-up when the exact base, subject, prior broad review, and changed/dependency surface are known. One annotated same-reviewer sequence reduced input by 50.8% and tool output by 80.6% from broad review R5 to targeted follow-up R6 while reaching an accepted result. That is not authority to narrow fresh independent review or review after subject drift.

No other new workflow control is justified by this evidence. In particular, this report does **not** recommend extra exact-source preflight, bounded-read rules, fixed task rotation, a primary-skill cap, producer token self-reporting, model downgrades, weakened validation, or fresh tasks as a saving mechanism. Fresh no-parent review remains an independence control; actual-compaction handoff and compact exact-state continuity remain continuity controls.

## 1. Evidence boundary and manifest

The controlling brief is Git blob `f0a9d5a28968c1fc9f7091b34b092f8271bd67d2`, with canonical raw-byte SHA-256 `e8f41c0d45a1d14c4ff50f513555ac1e570ef32ff81b1b744adeef3aeeda6b1d`.

The census includes every `*.jsonl` found beneath:

- `C:\Users\steph\.codex\sessions`
- `C:\Users\steph\.codex\archived_sessions`

The cut contains 329 live-store files and 151 archived files: 480 physical files, 480 unique primary session IDs, 643,548,255 bytes, and no parse errors. The first record is `2026-05-25T15:49:30.193Z`; the last is `2026-07-23T04:34:46.621Z`.

The [CSV manifest](token-efficiency-audit-all-history-manifest-2026-07-23.csv) binds each complete-line byte prefix by absolute path, byte count, SHA-256, timestamps, lineage, telemetry tier, and derived measurements. Its logical content identity is `62e190919ea1cb2f4ff95ac97e9bef6a7a58bee90191d906b9f942953fe5ea16`. The [JSON summary](token-efficiency-audit-all-history-summary-2026-07-23.json) contains the aggregates and integrity checks. The [analysis script](token-efficiency-audit-analysis-2026-07-23.py) is standard-library Python.

This is all **retained local Codex history**, not all work ever performed. Deleted sessions, non-Codex work, and records outside the two stores are unknowable from this evidence. A physical session is not necessarily one task: the report separately counts child-local task-start and turn proxies, but durable accepted-artifact outcomes are not universally recorded.

### Spawn-lineage correction

Thirty-four spawned child files contain a copied prefix of their parent's conversation. Naively summing their final counters double-counts that history. The parser excludes records before the child's adjacent team-marker/task-start boundary. Another 121 spawned child files contain no parent history. There were no ambiguous inherited-history boundaries in the cut.

Usage counters are cumulative, not per-event. The parser partitions two observed counter resets into monotone epochs and sums only positive advances. It never adds cache-read input to total input again, and never adds reasoning output to output again.

### Telemetry coverage

| Tier | Sessions | Processed tokens | Interpretation |
|---|---:|---:|---|
| Full components | 397 | 4,765,452,494 | Input, cache-read, output, and reasoning components available |
| Total only | 76 | 5,254,043 | Older summaries expose processed total but not components |
| No usage | 7 | 0 | No usable token record |

There are 22 tool calls without a matching output record, consistent with interruption or censoring; they are retained as an explicit integrity limitation.

## 2. Metric definitions

- **Processed tokens:** Positive child-local advances in cumulative `total_tokens`. For full-component records this equals input including cache plus output.
- **Input including cache:** Positive advances in cumulative `input_tokens`.
- **Cache-read input:** The cache-read component of input. It is not added again to processed total.
- **Uncached input:** Input including cache minus cache-read input.
- **Cache-write input:** Reported separately where the telemetry records it. The corpus records 11,489,496.
- **Output:** Positive cumulative output advances.
- **Reasoning output:** A subset of output, reported separately and not added again.
- **Inference round:** A positive usage-counter advance. This is the appropriate denominator for repeated model-mediated polling; it is not a task count.
- **Pure poll round:** An inference round whose only tool activity is `wait`, `wait_agent`, or `list_agents`.
- **Tool-output characters:** Structural I/O volume, not tokens. It is used only to describe evidence handling and never converted into token savings.
- **Cost:** Unknown. The JSONL establishes processed-token components, not billed currency or cache pricing.

`ccusage` 20.0.18 was used as a cross-check, not the primary counter. Its session command returned 396 sessions and 5,028,384,746 total tokens, compared with 397 raw full-component sessions and 4,765,452,494 child-local processed tokens. Its excess was 259,270,750 cache-read, 3,099,108 uncached input, and 562,394 output tokens. It also reported no cache-write input where raw telemetry recorded 11,489,496. The discrepancy follows from summing repeated non-advancing `last_token_usage` snapshots and from different session inclusion. Raw cumulative positive deltas are therefore the primary measure.

## 3. Quantitative baseline

| Measure | All retained history |
|---|---:|
| Physical sessions | 480 |
| Child-local task starts | 3,836 |
| Active turns | 2,958 |
| Positive-token inference rounds | 36,216 |
| Compactions | 206 |
| Tool calls | 39,038 |
| Tool-output characters | 186,221,338 |
| Processed tokens | 4,770,706,537 |
| Input including cache | 4,749,083,370 |
| Cache-read input | 4,573,801,529 |
| Uncached input | 175,281,841 |
| Output | 16,369,124 |
| Reasoning output subset | 5,235,351 |

Cache-read tokens are 96.31% of input. This explains why small changes in repeated inference rounds can create large processed-token differences while producing much smaller uncached-input and output differences.

TDL accounts for 320 sessions and 4,516,942,932 processed tokens, 94.68% of the retained total. Web-design work accounts for 149 sessions and 151,996,680 processed tokens. The other 11 sessions account for the remainder. The audit therefore covers the requested historical set, while the aggregate is still primarily evidence about TDL workflows.

At the frozen cut, this audit's root session and three no-parent census/validation subtasks used 27,179,087 processed tokens. That overhead is included in the baseline. It is another reason not to commission a duplicate workflow trial.

## 4. Ranked causes

### 1. Model-mediated polling

The corpus contains:

| Pure-poll tool | Positive-token rounds |
|---|---:|
| `wait` | 5,956 |
| `wait_agent` | 813 |
| `list_agents` | 126 |
| **Total** | **6,895** |

Those rounds used 1,024,304,707 processed tokens: 1,012,820,803 cache-read input, 11,142,833 uncached input, and 341,071 output. They produced no substantive model work beyond deciding to poll again.

For `wait`, the parser found 2,256 consecutive same-process sequences. Replacing short requested durations with no more than one call per 60 requested seconds would retain at least one call per sequence and eliminate 2,782 of 5,956 rounds. To avoid attributing the most expensive rounds to the intervention, the 413,989,375-token lower bound sums the smallest removable token deltas within each sequence. It is deliberately conservative.

This is the strongest finding because the change removes repeated inference without reducing research, mathematics, statistics, provenance checking, testing, or independent review.

### 2. Review breadth repeated after a bounded remediation

The best available natural comparison is an annotated same-reviewer, exact-lineage WP6.3 R5-R10 sequence. It does not generalize to fresh independent review, but it tests whether every follow-up must repeat the initial broad evidence acquisition.

| Review | Input | Uncached input | Output | Inference rounds | Tool-output chars | Recorded outcome |
|---|---:|---:|---:|---:|---:|---|
| R5 | 3,844,865 | 138,753 | 24,451 | 43 | 333,274 | Rework, two Major findings |
| R6 | 1,890,003 | 36,819 | 10,021 | 13 | 64,579 | Accepted |
| R7 | 2,584,206 | 39,310 | 9,664 | 15 | 79,450 | Rework, one Major finding |
| R8 | 2,770,964 | 30,228 | 9,070 | 14 | 56,964 | Accepted |
| R9 | 2,107,448 | 15,928 | 5,363 | 10 | 10,226 | Process rework |
| R10 | 1,961,909 | 105,909 | 12,569 | 26 | 278,281 | Accepted after exact-head checks |

R5 to R6 reduced input by 50.8% and tool-output characters by 80.6%. R9 to R10 reduced processed input by only 6.6%, while uncached input rose 565% and inference rounds rose 160%. The second pair demonstrates why cache-heavy processed totals cannot alone establish efficiency.

The defensible lesson is narrow: reuse a prior broad review's evidence map for the immediate exact-lineage remediation follow-up, while checking the delta, affected dependencies, and normal validation. A changed base, changed subject, cross-surface risk, or independent-review requirement triggers a full review.

### 3. Context inheritance, already controlled

For 34 spawned sessions with inherited history, first-call input had a median of 33,004 and p90 of 38,583. For 121 no-parent sessions, the median was 22,603 and p90 25,359. The groups are not task-matched, so the difference is not a causal saving estimate.

This validates the already-actioned use of self-contained no-parent dispatches. It does not justify relaunching ordinary bounded tasks, and it does not turn fresh independent review into an efficiency measure. Its primary value there is independence.

## 5. Findings that do not support new controls

- **Compaction and rotation:** There were 206 local compactions. Paired pre-compaction input had a median of 225,767 (p10 206,078; p90 290,508), and the next call had a median of 29,425. These are observed compaction points, not an optimal rotation threshold. Task length and difficulty confound comparisons, so neither an approximately-80k threshold nor any replacement fixed threshold is supported.
- **Task decomposition:** The records do not show that generally bounded tasks should be interrupted or rotated sooner. Doing so can duplicate startup, exact-state certification, and evidence acquisition.
- **Large reads:** Tool-output volume is measurable, but the records do not establish which large reads were unnecessary or what assurance would have been lost. A bounded-read rule remains speculative and is not recommended.
- **Exact-source checks:** Two wrong-source launches exist, but exact-source preflight normally occurs and the counterfactual prevention rate is unknown. Adding another universal preflight layer could cost more than it saves. No new check is recommended.
- **Model and reasoning effort:** Model, effort, task difficulty, and workflow design changed together. Available natural comparisons do not isolate a reliable saving from a fixed effort rule or downgrade.
- **Observer records:** Research/task-observer skill reads produced 10.64 million characters and observer-log/principles reads produced 9.64 million. Character volume is not attributable token cost, and the records do not show which assurance was dispensable. No weakening is recommended.
- **Guardian checks:** Guardian sessions used 138.92 million processed tokens and recorded 1,710 allows and two denials. The denials demonstrate assurance value; the evidence does not support disabling or bypassing the guard.
- **Validation and provenance:** Historical outcomes are not universally joinable to token events, so no reduction in tests, mathematical/statistical checks, provenance review, or fresh adversarial review can be justified.

## 6. Ranked minimal interventions and downsides

### 1. Use the longest bounded wait appropriate to known long work

For commands or agent work expected to exceed the default yield, request up to 60 seconds initially and on subsequent waits. Let completion or new output return early. Avoid alternating `list_agents` with short `wait_agent` calls when event-driven waiting is available.

**Expected benefit:** Fewer model inference rounds; historical conservative lower bound 413.99 million processed tokens if applied to long-process `wait` sequences.

**Downside:** A quiet process may delay a progress or cancellation decision by up to 60 seconds. Use a shorter interval only when the operation is genuinely latency-sensitive. Do not suppress progress messages for active work that exceeds the user-visible update interval.

### 2. Preserve focused exact-lineage remediation review

For the immediate follow-up to a broad review, reuse its evidence map and inspect the exact delta, affected dependencies, and required validation. This is an existing good practice, not a new governance layer.

**Expected benefit:** The best matched sequence shows a 50.8% input reduction from R5 to R6.

**Downside:** Narrowing can miss cross-file or newly introduced defects. Require exact base/head identity and escalate to full review on subject drift, dependency expansion, unexplained validation change, or an independent-review requirement.

### 3. Preserve current context and assurance controls

Continue self-contained no-parent context for independent adversarial review, compact exact-state continuity, and handoff when actual compaction degrades the continuation surface. Keep normal tests, provenance checks, and research assurance.

**Expected benefit:** Avoids reintroducing measured context inheritance while preventing retry costs caused by lost assurance.

**Downside:** These controls themselves consume tokens. The current evidence cannot isolate a cheaper alternative with equivalent assurance, so changing them would be speculation.

## 7. Bounded next-workflow observation, not a separate trial

No duplicate workflow trial is warranted. The historical counterfactual already establishes the processed-token opportunity. The only unresolved operational question is whether 60-second waits create unacceptable progress/cancellation latency.

Measure that without commissioning extra work: on the next naturally occurring long process, use a 60-second initial yield/wait, perform the substantive task once, and inspect its JSONL afterwards. Success means fewer wait-only inference rounds with no missed process output, forced retry, or material user-visible delay. Revert to a shorter wait only for the operation class that demonstrates such a delay. This adds no duplicate research, new agent, new review, or producer report.

## 8. Reproduction

Create the frozen cut and outputs:

```powershell
python docs/plans/agentic-research-system/reviews/token-efficiency-audit-analysis-2026-07-23.py `
  --pretty `
  --manifest-out docs/plans/agentic-research-system/reviews/token-efficiency-audit-all-history-manifest-2026-07-23.csv `
  --summary-out docs/plans/agentic-research-system/reviews/token-efficiency-audit-all-history-summary-2026-07-23.json
```

Recompute against the same byte prefixes after live files grow:

```powershell
python docs/plans/agentic-research-system/reviews/token-efficiency-audit-analysis-2026-07-23.py `
  --pretty `
  --cut-manifest docs/plans/agentic-research-system/reviews/token-efficiency-audit-all-history-manifest-2026-07-23.csv `
  --summary-out token-efficiency-audit-reproduction.json
```

Cross-check the overlapping telemetry:

```powershell
ccusage codex session --json --since 2026-05-25 --until 2026-07-24 --no-cost --offline
```

The frozen-cut replay reports zero SHA-256 failures, zero duplicate primary IDs, zero parse errors, zero ambiguous inherited-history boundaries, and zero processed/component identity failures among full-component sessions.

## 9. Explicit unknowns

- Currency cost and cache pricing are not established by local JSONL.
- Deleted or unretained sessions are absent.
- Older total-only sessions lack input/cache/output components.
- Twenty-two tool calls have no recorded output.
- Durable quality, acceptance, and retry outcomes are not encoded consistently enough for a corpus-wide causal join.
- The 60-second estimate is a replay counterfactual; actual latency acceptability can only be observed during naturally occurring work.
- Context-mode, model-effort, compaction, and review comparisons remain task-confounded.
- Tool-output character volume cannot be converted reliably into input tokens or assurance value.

The appropriate stop is therefore narrow: implement the polling-cadence improvement, retain the already-effective exact-lineage review and independence controls, and do not add speculative efficiency governance.
