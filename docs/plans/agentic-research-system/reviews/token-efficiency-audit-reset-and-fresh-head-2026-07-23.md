# Token-Efficiency Audit Reset and Fresh-Head Brief

**Date:** 2026-07-23  
**Status:** Evidence brief for independent continuation; no method change is accepted  
**Workflow system:** Standalone; not APM  
**Sole subject:** Token and context efficiency in Codex research workflows

## 1. Reset decision

This audit is deliberately separated from WP6 delivery and from repository delivery
mechanics. Its only question is:

> Where are tokens being spent in recent Codex sessions, which expenditure is avoidable,
> and what is the smallest evidence-backed change that can reduce it without weakening
> the quality of the research work?

The audit does not manage any work package, repository integration, external review,
branch topology, release, or acceptance decision. Those matters are neither prerequisites
nor evaluation criteria for this audit. A finding is relevant only when session evidence
shows that it materially affects token consumption, context growth, task duration, or the
amount of repeated model work.

Earlier workflow plans and reviews are historical evidence, not governing instructions.
The successor may reject all of their recommendations. In particular, it must not respond
to over-engineering by designing a larger governance system.

## 2. Success condition

Produce an independently evidenced report that:

1. reconstructs token use for a clearly defined session/campaign set;
2. distinguishes cache-read, uncached-input, output, reasoning-output, and aggregate
   token measures rather than presenting one ambiguous total;
3. identifies the largest avoidable causes in descending quantitative importance;
4. separates unavoidable research/assurance work from duplicated coordination work;
5. recommends the smallest interventions likely to produce the largest reduction;
6. analyses foreseeable negative consequences of each intervention;
7. proposes one bounded next-workflow trial with measurable before/after criteria; and
8. expressly identifies claims that the available evidence cannot support.

No fixed saving percentage or context threshold is assumed. Quantitative claims require
direct evidence and reproducible derivations.

## 3. Full evidence remit

The successor is authorized to inspect all local Codex session records needed to define,
discover, or test the campaign boundary, including sessions not listed below. The usual
locations are:

- `C:\Users\steph\.codex\sessions\YYYY\MM\DD\rollout-*.jsonl`
- `C:\Users\steph\.codex\archived_sessions\rollout-*.jsonl`

It may use `ccusage` directly, including:

```powershell
ccusage codex session --help
ccusage codex session --json --since 2026-07-18 --until 2026-07-23 --no-cost --offline
ccusage codex session --json --since 2026-07-18 --until 2026-07-23 --offline
```

The date range is a starting point, not a boundary. Expand it when a session was created
earlier but remained active in the measured interval, when a handoff names an earlier
predecessor, or when a useful comparison campaign lies outside it.

The JSONL is the primary behavioural evidence. Relevant record types observed in the
current data include `session_meta`, `turn_context`, `response_item`, `event_msg`,
`compacted`, and `world_state`. `event_msg.payload.type == "token_count"` supplies
cumulative and last-call usage, cached input, cache-write input, output, reasoning output,
and model context-window fields. `response_item` records messages and tool calls/outputs;
`compacted` and `context_compacted` identify actual compaction events. Inspect the schema
present in each file rather than assuming all files use one version.

The successor may write small local analysis scripts and derived tables in its own
worktree. It may hash source JSONL files or record byte sizes to make the evidence cut
reproducible. It should not reproduce sensitive payload text in the report when counts,
hashes, structural labels, or short paraphrases suffice.

## 4. Seed session set

These are discovery seeds, not a closed allowlist:

| Role | Session/thread ID | JSONL |
|---|---|---|
| Long coordinating and efficiency-audit task | `019f8954-d0cc-7d12-ae83-e8ccb8b61165` | `sessions/2026/07/22/rollout-2026-07-22T11-17-50-019f8954-d0cc-7d12-ae83-e8ccb8b61165.jsonl` |
| WP6.2 initial author and first remediation | `019f8a2e-61a5-7b40-8b07-adb0d8243dad` | `sessions/2026/07/22/rollout-2026-07-22T15-15-28-019f8a2e-61a5-7b40-8b07-adb0d8243dad.jsonl` |
| First independent review | `019f8a80-2e64-7633-acbd-f6fb7f12ef9b` | `sessions/2026/07/22/rollout-2026-07-22T16-44-49-019f8a80-2e64-7633-acbd-f6fb7f12ef9b.jsonl` |
| Aborted review at a cybersecurity boundary | `019f8b0f-6fca-72f2-a551-304ff0d5d811` | `sessions/2026/07/22/rollout-2026-07-22T19-21-17-019f8b0f-6fca-72f2-a551-304ff0d5d811.jsonl` |
| Static second review | `019f8b3e-5a2d-7552-9bd8-dfe7562c93b3` | `sessions/2026/07/22/rollout-2026-07-22T20-12-32-019f8b3e-5a2d-7552-9bd8-dfe7562c93b3.jsonl` |
| Final remediation author | `019f8bb8-b7e5-73b1-bb10-ca30a679cd73` | `sessions/2026/07/22/rollout-2026-07-22T22-26-11-019f8bb8-b7e5-73b1-bb10-ca30a679cd73.jsonl` |
| Final independent review | `019f8beb-f6f7-7900-b14c-3c7da567ba25` | `sessions/2026/07/22/rollout-2026-07-22T23-22-10-019f8beb-f6f7-7900-b14c-3c7da567ba25.jsonl` |
| Review of first efficiency-remediation plan | `019f8c3e-769d-77a3-9b7a-9d2fa1c24d25` | `sessions/2026/07/23/rollout-2026-07-23T00-52-16-019f8c3e-769d-77a3-9b7a-9d2fa1c24d25.jsonl` |
| Historical efficiency review | `019f8c51-a665-7581-ba15-9f00a1496707` | `sessions/2026/07/23/rollout-2026-07-23T01-13-16-019f8c51-a665-7581-ba15-9f00a1496707.jsonl` |
| Review of evidence-first plan v2 | `019f8c70-ba2f-7a61-9a14-f85d4d00fa0d` | `sessions/2026/07/23/rollout-2026-07-23T01-47-14-019f8c70-ba2f-7a61-9a14-f85d4d00fa0d.jsonl` |
| Review of evidence-first plan v2.1 | `019f8c84-6d2a-7782-a8de-352b06e6f382` | `sessions/2026/07/23/rollout-2026-07-23T02-08-46-019f8c84-6d2a-7782-a8de-352b06e6f382.jsonl` |

Also discover startup-only tasks, routing failures, delegated subtasks, and any task that
the listed JSONL records name. Excluding failed or zero-deliverable sessions would hide
one of the principal forms of waste.

## 5. Provisional quantitative anchors

The following `ccusage codex session --json --no-cost --offline` snapshot was taken on
2026-07-23 while the coordinating task was still active. It is a reproducibility check,
not the audit conclusion:

| Group | Cache-read | Uncached input | Output | Reasoning output | ccusage aggregate |
|---|---:|---:|---:|---:|---:|
| Six WP6.2 author/reviewer sessions | 155,242,440 | 2,458,080 | 567,572 | 169,657 | 158,268,092 |
| Four efficiency-plan review sessions | 28,017,563 | 906,267 | 212,132 | 68,578 | 29,135,962 |
| Long coordinating task at snapshot | 97,760,072 | 2,758,276 | 445,098 | 155,866 | 100,963,446 |

The successor must verify these figures against the source JSONL and current `ccusage`
output. It must explain `ccusage` field semantics, avoid double-counting cumulative
`token_count` events, and report whether its chosen aggregate represents processed,
billed, or effective tokens. Cache reads must not be treated as equivalent to uncached
input without an explicit reason.

## 6. Required analyses

At minimum, test and quantify:

- growth of prompt/context size across calls and turns;
- the token effect of keeping one coordinating task alive through multiple subjects;
- compaction count, pre/post-compaction context, and replay after compaction;
- repeated reading of the same files, reports, instructions, or Git state;
- large tool outputs returned to model context, including avoidable unbounded output;
- repeated validation and whether it tested a changed surface or merely replayed evidence;
- prompt and handoff packet size, duplicated policy text, and inherited conversation;
- stopped launches, wrong-source tasks, retries, and zero-deliverable sessions;
- review/remediation cycles caused by ambiguous scope or missing information;
- model and reasoning-level choices relative to the work actually performed;
- task splitting: savings from fresh context versus duplicated startup and certification;
- delegation/subtask overhead where it appears in JSONL; and
- tokens spent auditing or governing efficiency rather than improving it.

For each material cause, provide: observed count, measured tokens where derivable, a
conservative avoidable fraction or bounded range, confidence, and the evidence path.
Do not assign a token value from duration alone.

## 7. Intervention standard

Rank proposals by expected net token reduction, confidence, implementation cost, and
downside. Prefer deletions, shorter defaults, bounded reads, and better task boundaries
over new records, gates, or orchestration layers.

For every proposed action, test negative consequences such as:

- loss of research, mathematical, statistical, or provenance assurance;
- duplication shifted into more fresh-task startups;
- smaller prompts causing missed authority or repeated rediscovery;
- less validation concealing actual defects;
- aggressive summarisation losing decisive technical detail;
- lower model/reasoning settings increasing retries or remediation cycles; and
- measurement instrumentation costing more tokens than it saves.

An intervention should be rejected when its expected coordination or measurement cost
is comparable to its plausible saving.

## 8. Deliverable and authority boundary

Write one replacement audit report in the successor's own branch. It should contain:

1. evidence manifest and reproducible commands;
2. baseline and metric definitions;
3. ranked causes of token expenditure;
4. ranked interventions with negative-consequence analysis;
5. a minimal trial design for the next suitable research workflow; and
6. explicit unknowns and deferred questions.

The successor may review and further develop the audit method, but it may not change
repository instructions, skills, hooks, workflow conventions, or WP6 artifacts. It may
not conduct WP6 delivery work. It may recommend later changes, but those remain proposals
until Stephen reviews the evidence.

Stop before compaction and hand back a partial evidence report if the analysis cannot
finish cleanly in one fresh task. Do not turn task rotation into another mandatory
artifact system.

