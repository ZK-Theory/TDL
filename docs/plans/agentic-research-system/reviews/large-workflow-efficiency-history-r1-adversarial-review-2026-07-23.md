# Large-Workflow Efficiency History R1 Adversarial Review

**Date:** 2026-07-23
**Workflow:** standalone; never APM
**Lifecycle:** `historical_efficiency_review_r1`
**Supervision phase:** `certify`
**Exact repository subject:** `5e800c748394f717005e4f5e29140be095509ae3`
**Exact subject tree:** `17fc75dcf43a3ae5e764223db41b0cf4002810d7`
**Reviewer branch:** `review/wp6-efficiency-history-r1`
**Executive verdict:** `partially_effective`
**Finding count:** 0 Critical, 5 Major, 3 Minor
**Review status:** complete for the authorized evidence set; the historical comparison
baseline remains unverified and is explicitly excluded from causal conclusions.

## 1. Executive verdict

The programme produced real assurance and some real efficiency mechanisms, but it did
not validate its headline context-budget or token-saving claims.

The mechanisms worth preserving are exact-state continuity, fresh independent review,
standalone/APM separation, fail-closed canonical-authority preflight, certification of
existing deterministic artifacts, and stage-proportionate validation. They worked
together to prevent an unauthorized T2 implementation, preserve accepted bytes, expose
material contract defects, and finish with an independently reviewed exact candidate.

The efficiency evidence is materially weaker. Direct JSONL telemetry shows:

- V1's supervisor reached a peak per-call input of **226,951 tokens**, not an
  approximately 80k envelope, and compacted once;
- V2's supervisor reached **175,519 tokens** despite the assessment saying it stopped
  below 80k;
- the six substantive delivery sessions consumed **156,973,448 cumulative input
  tokens**, completed 10 turns in **266.718 active minutes**, and recorded **six
  compactions**;
- final remediation itself recorded one compaction at a peak per-call input of
  **239,222**, contrary to the completed-cycle assessment's statement that final
  remediation and R3 reported none; and
- the authorized 17-log evidence set contains **275,101,629 cumulative input tokens**.
  That total is not a campaign wall-time or billing figure, and it cannot be compared
  causally with the proposal's unbound 549.9-million-token historical baseline.

Fresh tasks therefore reduced inherited conversation and improved reviewer
independence, but they did not keep model inputs small. Much cost moved into large
self-contained prompts, repeated governing material, tool output, handbacks, and
additional task boundaries. V1/V2 compared different phases and both stopped before an
implementation/review/remediation cycle, so their approval of advisory integration was
reasonable for workflow safety but premature as evidence of efficiency.

The overall disposition is **partially effective**: retain the assurance-preserving
mechanisms, replace the 80k rule with an observable metric contract, consolidate the
duplicated prose surfaces, and require a matched prospective trial before making any
quantitative saving claim or activating a mandatory checker.

## 2. Authority, independence, and method

This review used only this dispatch and direct evidence. It did not use author,
Manager, new-plan, prior-review, APM, Memory Bank, or later-remediation material as
authority. The selected review skill was `adversarial-design-review`; the required
meta-skill was `research-observer`. There were no matching OPEN observer entries and no
active cross-cutting principles beyond the observer skill's built-in principles.

The review began from a clean detached checkout. Detached `HEAD`, the pre-created
reviewer branch, the required commit, and the required tree all matched. The one
permitted deterministic attachment to `review/wp6-efficiency-history-r1` succeeded;
cwd, symbolic branch, `HEAD`, tree, and clean status were then reverified.

The reviewed repository material was read as Git objects at the exact subject. Key
content identities include:

| Artifact | Git blob |
|---|---|
| Protocol proposal | `d031159247891e09f20f9e6ee3f358b0d20edcca` |
| V1 assessment | `84a0a21aebab3bd3c0aaa4f49d44d61a30f954d1` |
| V2 assessment | `c36e984d0679fa4617a2e2335496fc0636eca9cd` |
| Completed-cycle assessment | `488a15361364aa6f5df8e56baa02c4df9e243aba` |
| V1 exact-state handback | `3a82a1f9e556eec3f677f35ac7bb1f99d4885b82` |
| V2 exact-state handback | `383c647b14a49656326f7fd65217859619c846c7` |
| Repository `AGENTS.md` | `1fe6a0069a1f68bb7c3906b9addfa433163b37de` |
| Supervision guide | `fee078d90fd9d95aae91b16382706475a3c7065c` |
| `tda-large-workflow-supervision` | `9ca6cbd9dc7bc1e97b9931c41b9cc29c9b3f2206` |
| `tda-task-brief-from-plan` | `28b222e9f4701fac726641974eea97ce7bd2a2b9` |
| `tda-handoff` | `95064755e6259ba991d4752f41ac40e1206b309a` |

The V1 and V2 handback hashes independently reproduce the assessments' claimed
identities:

- V1: raw SHA-256
  `209f1cd1f83fd2051d9da1738c4cea58b9262ccd6e5a79a7926dddf85b2e1e4f`;
- V2: raw SHA-256
  `255b187b36ca242ac19ee36aadd498ea5fae97b5b49a85fb77dac0e6ae09a239`.

The exact change series from `e728d5117e626590adb6de4fbd4657db9d178125`
through the review subject was inspected. P-035, P-036, P-039, and P-040 were read from
`03-decisions-and-open-questions.md`. The accepted final candidate, review, and owner
records were resolved directly:

- candidate `391a92753d7f746fa91a6b5455c9ce0fd01baa52`, tree
  `0254c5416925126412867d61b3045ee1563abd0c`;
- final R3 review `655f4173db93447a068adc6e92621455c4abc85d`, report blob
  `1ad44c1f79ea973f8ff5e2369bab3a32b4f940d`, raw SHA-256
  `17906c4ae1916840dfe94aab3f5991d17e8037940802ec1338c49b53f9506fd8`;
- P-039 proposal `1301d8a5f089d27270c36b216967000a35472efc`, blob
  `1c6703b37579a0ffa35bfec0f9cccc7180a37f79`, raw SHA-256
  `959ebeafa67368ffc87592134fd9c0caf385b4b562278789273563844295492f`;
- P-040 Manager commit `cbe47e1b7ed382308df61e9173722dc9085f4548`.

The candidate, R3 review, and P-040 record are on separate histories and are not
ancestors of the efficiency subject. That confirms, rather than merely repeats, the
completed-cycle assessment's integration-lane concern.

## 3. Telemetry method and safety

### 3.1 Structural parser

The parser used an explicit file allowlist. It decoded JSONL one complete record at a
time and emitted only these structural fields:

- `session_meta`: IDs, cwd, thread source, parent/depth/agent role;
- `turn_context`: model and effort;
- `event_msg`: event type, task timestamps/durations, compaction count, and numeric
  token counters;
- `compacted`: count only; and
- `response_item`: message role and tool name counts only.

It did **not** emit, copy, or commit prompts, messages, reasoning, tool arguments, tool
outputs, command text, `last_agent_message`, or compacted replacement history. It did
not recursively search unrelated sessions.

`cumulative input tokens` is the final `total_token_usage.input_tokens` counter for a
session. `Peak input` is the maximum
`last_token_usage.input_tokens` recorded for one call. `Active minutes` is the sum of
complete `task_complete.duration_ms` events. These units are not interchangeable with
wall time, live unique context, uncached tokens, cost, or human labour. Parallel or
nested sessions can overlap.

### 3.2 Frozen Manager cut

The mutable Manager JSONL was opened with read/write sharing and read once to a fixed
cut:

| Property | Exact value |
|---|---|
| Session | `019f8954-d0cc-7d12-ae83-e8ccb8b61165` |
| File cut length | `10,925,377` bytes |
| SHA-256 of exact file cut | `6b8a979b7092136710cf097610f3b4152e5f051a4c6c824108469d4312d8c387` |
| Parsed JSON prefix length | `10,925,376` bytes |
| SHA-256 of parsed prefix | `f037dc90071b8cd51513c46715a8ddc8e3f2bf6c0a025f8a19adac239a03a16d` |
| Excluded byte | one final LF byte (`0x0a`) |
| Parsed records | `4,140` |
| Last complete event | `2026-07-23T00:13:11.352Z` |

Every Manager metric in this report was derived from that same prefix after verifying
its SHA-256. Later bytes, if any, are excluded.

### 3.3 Session identity proof for V1 and V2

The handback worktrees and session metadata prove the identities rather than requiring
inference:

- V1 supervisor `019f89d0-7cdb-7163-8f1b-20a8c2e813f6` has cwd
  `C:\Users\steph\.codex\worktrees\9333\TDL`; its two depth-1 explorer records have
  the same root session ID and parent;
- V2 supervisor `019f89ef-d36c-7720-b416-0823d02326ae` has cwd
  `C:\Users\steph\.codex\worktrees\3751\TDL`; its scope explorer is depth 1 and the
  interrupted mapping probe is depth 2 under that explorer.

The V2 nested probe has no `task_complete` event, exactly matching the handback's
statement that it was interrupted. This is reported as incomplete, not silently counted
as a successful task.

### 3.4 Exact telemetry manifest

All hashes below are SHA-256 of the complete named file, except the Manager row, which
uses the fixed cut hash above. `Turns/comp.` means completed task turns / compaction
records. `Input/peak` is cumulative input / maximum per-call input. Active duration is
minutes; `n/a` means no complete task event.

| Role and session | Bytes | SHA-256 | Last event | Turns/comp. | Input/peak | Active |
|---|---:|---|---|---:|---:|---:|
| Manager `019f8954-d0cc-7d12-ae83-e8ccb8b61165` | 10,925,377 cut | `6b8a979b7092136710cf097610f3b4152e5f051a4c6c824108469d4312d8c387` | `2026-07-23T00:13:11.352Z` | 32/6 | 87,856,357 / 234,058 | 143.568 |
| Author `019f8a2e-61a5-7b40-8b07-adb0d8243dad` | 4,802,149 | `af124c8f98bfa16cf344e3ec691992984e3e7fe4aca49d578ad4254a4cf8646c` | `2026-07-22T17:20:15.996Z` | 3/2 | 69,690,359 / 235,128 | 137.428 |
| R1 `019f8a80-2e64-7633-acbd-f6fb7f12ef9b` | 1,599,657 | `2c3068520828d5a006a89a7796610dd89ced02d10de68c4dd5f9f07f56be02b8` | `2026-07-22T16:00:54.837Z` | 1/1 | 9,237,574 / 241,075 | 16.056 |
| First R2 attempt `019f8b0f-6fca-72f2-a551-304ff0d5d811` | 1,559,947 | `3f6b4a583bbcdcc7073f40ec77fa874c1bd8d9ffe7a37ff2562719acb6003a4c` | `2026-07-22T18:47:57.062Z` | 1/1 | 21,030,511 / 242,910 | 26.599 |
| Static R2 `019f8b3e-5a2d-7552-9bd8-dfe7562c93b3` | 2,044,274 | `ac0761c8cd3d70ae6390ceb170258dabbfc18f1c732b4c9dcbb26a9cbdea4304` | `2026-07-22T20:13:08.203Z` | 3/1 | 13,520,790 / 219,895 | 19.259 |
| Final remediation `019f8bb8-b7e5-73b1-bb10-ca30a679cd73` | 2,674,461 | `ae5dcdf796d2092a9c50b0448a4013f7c094cd2b25fbf78390adc316dec194f2` | `2026-07-22T22:13:44.673Z` | 1/1 | 29,745,892 / 239,222 | 47.534 |
| R3 `019f8beb-f6f7-7900-b14c-3c7da567ba25` | 1,372,579 | `76bbd83298c860e45c5cf90dde483c85f4afbc07a8ab452d5ddb784f6580cc41` | `2026-07-22T22:42:03.488Z` | 1/0 | 13,748,322 / 240,606 | 19.842 |
| Inventory 1 `019f8a30-8444-77a3-af51-3558ab7577b9` | 763,132 | `d372efccfce5ebd2d6ecd987eb624baa9af3a340d0f145fec5cec3b56392ffe1` | `2026-07-22T14:23:15.426Z` | 1/0 | 2,738,978 / 163,120 | 5.446 |
| Inventory 2 `019f8aa5-af01-7801-95f4-35a1b9959e2b` | 570,951 | `f4271c08c7684d0caf4c60ca95f2c1f588fa101b75c133d6618adbc7d8a1251e` | `2026-07-22T16:30:37.614Z` | 1/0 | 1,248,116 / 111,947 | 4.842 |
| Routing stop 1 `019f8a1b-c117-7d22-988b-88e06c0c53b2` | 271,935 | `f54d1737d15e117c6247acd85ef8c458a94152a9abd300ac81f743a1191946fe` | `2026-07-22T13:57:02.195Z` | 1/0 | 365,603 / 48,851 | 1.831 |
| Routing stop 2 `019f8a29-196a-7a80-ac03-ecc5572fdb5d` | 293,217 | `25f90d324b42d92f31c6cc64e9413be4f11bf53c40bfd16ef235cfe8f34b7d17` | `2026-07-22T14:11:34.130Z` | 1/0 | 422,877 / 53,736 | 1.849 |
| V1 supervisor `019f89d0-7cdb-7163-8f1b-20a8c2e813f6` | 1,389,839 | `94b653c25c37a23ee18fd05d5110764ad8ade854e13076e28168d177fe35627c` | `2026-07-22T12:46:15.972Z` | 1/1 | 8,325,973 / 226,951 | 13.321 |
| V1 explorer 1 `019f89d3-02e5-7af3-a02c-2f81d742c2bc` | 600,244 | `16c91283c3e2124c95c02c0490dadc27926ba7ead3e85e86b5d486ff4cd7529c` | `2026-07-22T12:40:40.636Z` | 1/0 | 1,739,952 / 129,620 | 5.003 |
| V1 explorer 2 `019f89d3-3f90-7af2-9fad-d7500a768562` | 795,552 | `d3b994e510df8ba3dda4933ef753621778738ba5b6924ebe9d40d4048a338932` | `2026-07-22T12:42:16.195Z` | 1/0 | 2,966,108 / 176,413 | 6.336 |
| V2 supervisor `019f89ef-d36c-7720-b416-0823d02326ae` | 948,132 | `d423db817d2c419815f39e3eb444d1dded4a786e7c3e2c5ef37059c5b8d92a98` | `2026-07-22T13:17:14.861Z` | 1/0 | 6,164,843 / 175,519 | 10.088 |
| V2 explorer `019f89f2-23d0-7971-baa6-8ce6f8cb12dc` | 754,963 | `1b37b8ff80fc1b12baf5c1e4e3ab1caab3cf273807589f93916d20a3c8249989` | `2026-07-22T13:14:38.453Z` | 1/0 | 3,222,312 / 155,596 | 4.966 |
| V2 nested probe `019f89f2-b5fa-7cc3-8c70-1a22b636de94` | 713,516 | `f5460963aa1c95ad76308f5331b64419d14a619daabd69f361cba4b5739d4671` | `2026-07-22T13:13:54.594Z` | 0/0 | 3,077,062 / 137,471 | n/a |

### 3.5 Group aggregates

| Group | Cumulative input | Cached input | Cached share | Output | Reasoning output | Completed active min | Turns | Compactions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Manager cut | 87,856,357 | 85,454,651 | 97.27% | 378,788 | 133,245 | 143.568 | 32 | 6 |
| Six substantive cycle tasks | 156,973,448 | 154,526,048 | 98.44% | 566,823 | 169,480 | 266.718 | 10 | 6 |
| Successful inventory subagents | 3,987,094 | 3,711,306 | 93.08% | 30,638 | 16,639 | 10.288 | 2 | 0 |
| Genuine routing stops | 788,480 | 685,842 | 86.98% | 9,472 | 4,629 | 3.680 | 2 | 0 |
| V1 supervisor and explorers | 13,032,033 | 12,491,116 | 95.85% | 57,850 | 20,942 | 24.660 | 3 | 1 |
| V2 supervisor and descendants | 12,464,217 | 11,609,137 | 93.14% | 40,379 | 13,246 | 15.054 complete | 2 | 0 |

The 17-log cumulative-input sum is **275,101,629**. It includes cached replay and
overlapping nested sessions. It is reported to show where cost landed, not as an
invoice or a clean counterfactual.

### 3.6 Inclusion and exclusion

Included:

- the explicitly named Manager, six substantive sessions, two successful inventory
  subagents, and two archived routing stops;
- the V1/V2 supervisors and their exact descendants, identified from handback worktree
  paths and `session_meta`; and
- immutable Git objects directly cited by the reviewed artifacts.

Excluded:

- Manager bytes after the frozen cut;
- all unrelated sessions and all recursive content scans;
- prompt, message, reasoning, command, tool-argument, and tool-output content;
- later remediation plans or reviews;
- task content needed to classify generic `wait` calls as shell wait, agent wait,
  polling, or external-review wait; and
- the proposal's historical 54-turn/15-compaction/549.9-million-token baseline because
  neither the proposal nor the authorized handbacks bind it to an exact session file or
  hash. Its numbers are therefore not re-used as verified evidence.

## 4. Severity-graded findings

### H1 — Major — The 80k context control was not measured and did not operate as claimed

**Claim.** The protocol says supervisors rotate at first auto-compaction or
approximately 80k live input tokens, V1 says rotation occurred approximately at that
envelope, and V2 says it stopped below 80k.

**Evidence.** Protocol proposal lines 73-82; V1 handback lines 3-9 and 101-115; V1
assessment lines 24-37; V2 handback lines 3-9 and 84-94; V2 assessment lines 22-37.
Direct telemetry records V1 supervisor peak input 226,951 and V2 supervisor peak input
175,519. The Manager cut peaked at 234,058. The six delivery sessions peaked between
219,895 and 242,910. The final remediation session compacted once at 239,222.

**Concrete failure scenario.** A supervisor has no exposed live counter, declares
itself below 80k from intuition, and continues until the platform compacts near the
model limit. The later assessment marks the budget as passed, so an ineffective control
is propagated into AGENTS, skills, and a guide.

**Impact.** Efficiency validity and provenance are materially weakened. The control
cannot be audited in real time, and first compaction is too late to enforce an 80k
ceiling. Research assurance was not corrupted, but the programme's principal numeric
acceptance claim was.

**Recommended disposition.** Replace the 80k rule. Keep compaction as a hard rotation
event, but do not call it evidence that a lower token ceiling operated.

**Exact proposed replacement.** "When the runtime exposes
`last_token_usage.input_tokens`, record it per turn and rotate before the declared
ceiling. When it does not, do not assert a token threshold; use an observable turn,
artifact, or phase bound and rotate immediately at the first compaction. A completion
record must state the exact counter source and cut identity."

**Affected decisions/work packages.** Protocol 2.3 and 6-8; handoffs 08-10; V1/V2
assessments; completed-cycle criteria; repository/global AGENTS blocks; supervision
guide; `tda-large-workflow-supervision`; any future checker.

### H2 — Major — The programme has no valid causal estimate of token or time saving

**Claim.** The proposal projects 30%-45% net reduction from theoretical replay
reductions, and the V1/V2 narrative treats packet reuse and task rotation as evidence
of improved efficiency.

**Evidence.** Proposal lines 15-25 and 73-82. V1 was a certification task ending at
first compaction; V2 was a delivery preflight ending at an authority blocker. They did
not execute the same work. Their aggregate cumulative inputs were 13.032 million and
12.464 million respectively, only a 4.36% difference, but even that is not a valid
comparison because scope, descendants, and termination differ. The proposal's claimed
549.9-million baseline has no exact session identity in the authorized evidence. The
current Manager cut is a different session with 87.856 million cumulative input tokens,
32 completed turns, six compactions, and 97.27% cached input.

**Concrete failure scenario.** A theoretical replay model is presented beside two
different stopped workflows. Readers infer an observed saving even though no matched
counterfactual, equivalent deliverable, or total-campaign boundary exists.

**Impact.** The method may be cheaper, equal, or more expensive for a completed
deliverable; the evidence cannot decide. Cost shifted across supervisor, author,
reviewers, inventory subagents, routing failures, and handback production.

**Recommended disposition.** Reject all quantitative saving claims for this historical
programme. Preserve them only as hypotheses.

**Exact proposed replacement.** "Historical records motivate the intervention but do
not estimate its saving. Efficiency is unquantified until a prospective matched trial
records an exact session set, workload boundary, telemetry cuts, and assurance-equivalent
outcome."

**Affected decisions/work packages.** Proposal problem statement and threshold
rationale; V1/V2 integration rationale; completed-cycle executive assessment; model
routing; prospective checker justification.

### H3 — Major — Fresh tasks improved independence but shifted context cost into large prompts and repeated evidence

**Claim.** No-history implementers/reviewers are expected to be both cheaper and more
independent, with exact-state packets replacing conversation replay.

**Evidence.** Proposal lines 84-99. Each substantive cycle session has its own root
session identity and no spawn parent, supporting fresh-session separation. Yet all six
reached peak per-call input between 219,895 and 242,910 tokens; five of six compacted,
and the reused author compacted twice. The two trial handbacks alone contain 254 lines
and 22,035 raw bytes. Core rules are restated across five to nine reviewed surfaces:
`80k` in five, `fork_turns` in seven, CodeRabbit ownership in nine, the two-primary
rule in six, and `exact-state` in seven.

**Concrete failure scenario.** A fresh reviewer receives no parent conversation, but a
long self-contained dispatch, repeated policies, complete skill bodies, handback,
authorities, and tool output fill nearly the whole context. Independence is preserved;
efficiency is not.

**Impact.** Task fragmentation adds startup, branch, handback, and integration burden.
It also increases the chance of omitted context or divergent restatements. No dropped
research requirement was demonstrated here, but the method did not control prompt
expansion.

**Recommended disposition.** Retain fresh independent sessions. Amend the method to
budget loaded bytes/artifacts and evidence reads, not merely inherited turns and skill
count.

**Exact proposed control.** One canonical dispatch envelope, one compact packet, and
paths to authorities. Record dispatch bytes, packet bytes, skill bytes loaded, and
number of governing artifacts. Load detail lazily after a concrete finding or touched
dependency.

**Affected decisions/work packages.** Protocol 2.1-2.5; handoff packet design; task
brief template; all three integrated skills; AGENTS and guide duplication.

### H4 — Major — Acceptance records contain telemetry statements refuted by the logs

**Claim.** The completed-cycle assessment says exact token telemetry was unavailable
and says no compaction was reported in final remediation/R3. V1/V2 make similar
unavailable/below-budget statements.

**Evidence.** Completed-cycle assessment lines 20-30, 60-76, and 133-138. The JSONLs
contain 683 Manager `token_count` events and corresponding events in every complete
session. Final remediation contains one `compacted` record and one
`context_compacted` event; R3 contains zero. Across the substantive cycle there are six
compactions. The published 10-turn and 266.7-minute totals do reproduce exactly, which
shows that the parser is aligned with the same task set while revealing omitted
telemetry.

**Concrete failure scenario.** A review relies on UI-visible metadata, records a field
as unavailable, and approves a control while the durable execution record contains a
contrary measurement.

**Impact.** The V1/V2 and completed-cycle acceptance claims are only partially
supported. This is a record/provenance defect, not evidence that the final T2 candidate
is invalid.

**Recommended disposition.** Amend the historical assessments by dated addendum in any
future authorized remediation; never rewrite their snapshots. Require a hash-bound
structural telemetry manifest for future efficiency certification.

**Exact proposed record rule.** "Unavailable means absent from the frozen JSONL prefix,
not absent from the UI. Bind the parser version, explicit session list, byte cut,
last complete timestamp, and SHA-256 before deriving any metric."

**Affected decisions/work packages.** V1/V2 acceptance; completed-cycle v1.1 approval;
efficiency proxy rule; future checker evidence; any published history of the programme.

### H5 — Major — The research-value and second-cycle controls arrived only after material avoidable cost

**Claim.** The completed-cycle method preserved assurance and became proportionate
after P-039; v1.1 moves the research-value gate before blocking non-research controls
and treats a second remediation as rescope.

**Evidence.** Completed-cycle assessment lines 20-30, 52-58, 60-76, and 89-138. The
first R2 attempt consumed 26.599 active minutes and 21.031 million cumulative input
tokens without a deliverable. The first remediation implemented security and complete
W7 surfaces later removed or deferred by P-039. P-039 explicitly narrowed C3/M2 and
authorized one final fresh remediation/R3. Final R3 independently matched 26/26 blobs,
recomputed the 220-member protected set, passed 135 focused tests and 102 contracts,
and retained runtime/security work for T3/T4.

**Concrete failure scenario.** Contract-stage review makes runtime-only assurance
blocking. The author expands scope, a reviewer crosses an operational-security
boundary, and a later owner ruling discards that work before research value is
assessed.

**Impact.** Time and tokens were wasted, research-facing progress was delayed, and the
one-cycle rule needed an exception. The later correction improved proportionality
without weakening mathematical, statistical, provenance, or exact-state assurance.

**Recommended disposition.** Retain P-039's research-value/stage gate and the v1.1
second-cycle rescope rule. Apply them at dispatch intake, not after R2.

**Exact proposed control.** A non-research finding becomes blocking only after naming
the protected research asset, credible failure path, insufficiency of existing
controls, cheapest adequate control, evidence-bearing lifecycle stage, and bounded
effort. A proposed second remediation stops for owner triage and a fresh exact subject.

**Affected decisions/work packages.** P-039; completed-cycle v1.1 revisions 1-2;
supervision skill; task brief; validation/review ladder; future T2 runtime and T3/T4.

### H6 — Minor — Two avoidable routing stops imposed measurable platform/protocol overhead

**Claim.** The completed-cycle assessment characterizes two archived startup-only
detached/routing stops as avoidable and says the corrected detached-start protocol later
worked.

**Evidence.** Sessions `019f8a1b...` and `019f8a29...` completed in 1.831 and 1.849
active minutes and consumed 365,603 and 422,877 cumulative input tokens. They produced
no substantive deliverable. Later tasks used the one deterministic attachment rule.

**Concrete failure scenario.** A dispatch incorrectly requires symbolic attachment at
startup but forbids the only authorized switch, causing a clean task to stop and be
recreated.

**Impact.** Small but real task fragmentation, latency, and token waste; no research or
candidate corruption.

**Recommended disposition.** Retain the corrected detached-start protocol. Do not
count these stops as evidence against fail-closed worktree ownership itself.

**Exact proposed control.** Pre-create one branch, allow one same-commit deterministic
switch, verify, then stop on metadata denial.

**Affected decisions/work packages.** AGENTS detached-start rule; dispatch template;
completed-cycle routing criterion.

### H7 — Minor — Skill-budget and no-polling claims are not directly certified by the structural evidence

**Claim.** V2 and the completed cycle passed skill-budget and zero-external-review-wait
criteria.

**Evidence.** The handbacks declare the skills and no CodeRabbit use, but the
content-suppressing parser cannot inspect tool arguments. Structurally, the Manager has
91 generic `wait` calls and the six substantive sessions have 295. These may be valid
shell/agent waits; they cannot be classified as CodeRabbit waits without prohibited
content inspection. Likewise, session metadata does not record which skill bodies were
loaded.

**Concrete failure scenario.** A self-reported checklist says no polling and at most two
skills, but no independent field records either property.

**Impact.** These criteria are plausible but unverified. The two-skill count is also a
weak cost proxy because skill bodies vary greatly in size.

**Recommended disposition.** Retain Stephen-owned external review as an authority rule.
Treat the skill cap as a heuristic until loaded-skill identities/bytes and wait purpose
are recorded structurally.

**Exact proposed record.** Add only `loaded_skill_identities`, `loaded_skill_bytes`, and
`wait_class` (`process`, `agent`, `external_review`, `other`) to prospective telemetry.

**Affected decisions/work packages.** Protocol 2.5-2.6; V1/V2 criteria; AGENTS, guide,
and all three skills; future optional checker.

### H8 — Minor — The advisory integration creates a broad restatement surface before its enforcement contract is stable

**Claim.** Advisory integration across AGENTS, skills, and guide is justified while a
checker and convention lock remain deferred.

**Evidence.** The exact PR-A delta has 29 changed paths, 3,195 insertions, and 19
deletions. Some are necessary trial/candidate records and some are generated skill
mirrors, but the workflow rules are still independently restated across the proposal,
AGENTS, guide, three skills, and three handoffs. There is no mandatory checker. The
guide says v1.1 is proposed while already carrying v1.1 content, and the protocol mixes
historical trial evidence with current operational rules.

**Concrete failure scenario.** A future edit updates the skill but not AGENTS/guide or
a copied handoff. Agents load the narrowest or stalest restatement and still appear
compliant because no exact owner/enforcement binding exists.

**Impact.** Prompt expansion, maintenance cost, and drift risk. The generated
`.claude/skills` mirror is mechanically synchronized and is not a separate authoring
source; the remaining prose surfaces are.

**Recommended disposition.** Consolidate, but do not activate a mandatory checker yet.

**Exact proposed structure.** AGENTS declares scope and points to one canonical
supervision skill. The skill owns normative rules. The guide owns examples only. The
dated proposal/assessments remain history. Task-brief and handoff skills reference the
canonical rule and retain only their own fields.

**Affected decisions/work packages.** Protocol update map; AGENTS; guide; three skills;
handoffs 08-10; skill-sync manifest; future checker/CONVENTIONS decision.

## 5. Claimed versus observed

| Claim | Direct observation | Disposition |
|---|---|---|
| Historical Manager had 54 turns, 15 compactions, final 195k input, 549.9m cumulative input | No exact authorized session/hash binds this baseline | Inconclusive; do not use quantitatively |
| 64k/80k rotation would reduce replay 53%-56% / 44%-47% | Theoretical only; no matched completed trial | Hypothesis, not result |
| V1 was fresh | Separate root session and exact cwd proved | Supported |
| V1 rotated at first compaction | One compaction recorded | Supported |
| V1 was approximately at 80k | Peak per-call input 226,951 | Refuted |
| V1 explorers used no-history fresh delegation | Depth-1 independent session records under V1; no inherited full Manager record | Supported structurally |
| V2 reused V1 packet | Packet raw hash reproduces exactly; main was recorded unchanged | Supported |
| V2 stopped below 80k | Peak supervisor input 175,519 | Refuted |
| V2 had zero compactions | Zero recorded | Supported |
| V2's authority blocker was genuine | Exact base plan requires one atomic project writer; `CommandService._build_event` implements six unrelated command types and rejects others; owner catalogue lacks the T2 transition family | Supported |
| V2 saved repeated campaign reads | Handback says zero; content suppression prevents read-content counting | Plausible, not independently measured |
| Completed cycle had six fresh tasks, ten turns, 266.7 active minutes | Exact sessions reproduce 10 turns and 266.718 minutes | Supported |
| Final remediation/R3 reported no compaction | Final remediation 1; R3 0 | Partly refuted |
| Exact token telemetry unavailable | Every complete session contains numeric token events | Refuted for durable JSONL; UI availability may still have been limited |
| Fresh R1/R2/R3 preserved independent review | Separate root session identities; final R3 independently bound exact candidate and authority | Supported |
| Certify-before-regenerate preserved accepted bytes | Final R3 matched 26/26 candidate blobs, verified authorized deletion, and did no regeneration | Supported |
| Validation became proportionate after P-039 | Final R3 omitted full 665 suite and runtime probes while passing 135 focused and 102 contract checks | Supported for final stage |
| Zero external-review waits/actions | Self-reported; generic waits cannot be classified structurally | Inconclusive, not contradicted |
| One remediation cycle | Initial remediation plus exceptional owner-authorized final remediation | Refuted for v1; v1.1 rescope correction supported |

## 6. Intervention disposition matrix

| Intervention | Claimed improvement | Observed effect | Cost shift / assurance effect | Disposition | Cheaper adequate alternative |
|---|---|---|---|---|---|
| Declare `standalone`, reject APM | Prevent lifecycle contamination | V1 exposed the error; V2/cycle stayed standalone by their records | Small prompt cost; clearer authority | **Retain** | One AGENTS rule plus canonical skill |
| Exact-state packet | Move state out of conversation | V1 packet was hash-reused by V2; exact identities survived rotations | 22,035 bytes/254 lines across two trial packets; no compactness cap | **Amend** | Minimal identity manifest with predecessor hash, paths, decisions, next action |
| Separate `certify` / `deliver` | Avoid repeating broad intake | V2 used the V1 packet and stopped on a new scope issue | V1/V2 not comparable; still large inputs | **Retain with measurement** | Verify packet + Git delta, then log exact paths read |
| First-compaction / ~80k rotation | Bound replay | Compaction stops worked; 80k did not | Compaction arrived after 175k-243k inputs | **Replace numeric rule** | Observable per-call counter or non-token phase/turn bound |
| `fork_turns="none"` independent work | Save replay and reduce correlation | Separate sessions and strong R1/R2/R3 review | Large self-contained prompts shifted cost | **Retain** | Fresh session plus concise exact packet |
| At most two primary skills | Limit startup context | Self-reported, not structurally measurable | Count ignores skill size and duplicated principles | **Defer as heuristic** | Record loaded skill IDs/bytes; load by trigger |
| No CodeRabbit polling | Remove passive waits from substantive tasks | No CodeRabbit-specific evidence; generic waits remain | Clear ownership; telemetry unclassified | **Retain authority rule** | Return control to Stephen; structural wait class |
| Certify before regenerate | Avoid duplicate work and byte drift | Strongly supported in V1/V2 and final R3 | Up-front identity check saved regeneration and protected provenance | **Retain unchanged** | Exact blob/hash comparison |
| Progressive validation ladder | Reduce redundant full suites | Early cycle over-ran; final cycle became proportionate | Independent focused reruns were valuable; second full run was not | **Amend** | Semantic-delta test map; full gate once at integration |
| One author-review-remediation cycle | Bound review churn | Exceeded under exceptional owner rescope | Prevented silent third cycle only after P-039 | **Amend as v1.1 does** | Second-cycle hard stop + owner triage + fresh subject |
| P-039 research-value gate | Stop assurance over-expansion | Correctly removed/deferred C3/M2 runtime work | Arrived after 26.6-minute dead R2 and overbuild | **Retain and move earlier** | Six-field research-value intake |
| Four branch roles | Preserve accepted candidate/integration identity | Existing split histories exposed the need | Four roles may be excessive for simple work | **Amend** | Require candidate + integration; add management/review only when they write |
| CodeRabbit 100-file packaging | Avoid unreviewable PR | No PR existed in measured cycle; subject delta is 29 paths | External platform constraint, not trial result | **Retain as external constraint, not efficiency evidence** | One pre-PR path count |
| Prospective efficiency proxies | Make future evaluation auditable | Historical reconstruction was possible but assessments missed token events | Small closeout cost | **Strengthen** | Hash-bound structural manifest generated once |
| Optional dispatch checker | Mechanize stable rules | Not implemented; numeric/context semantics are unstable | Premature checker would encode false 80k rule | **Defer** | Check only exact subject/root/workflow fields after revised contract |
| Model routing | Lower cost by task type | No controlled evidence | Adds choice and another policy surface | **Remove from accepted evidence; defer** | User/runtime default unless explicitly studied |
| Mandatory handoff at rotation | Preserve continuity | No dropped requirement demonstrated; packet reuse worked | Repeated handback burden and possible new source of truth | **Amend** | Identity-only packet with size/duplication check |

## 7. Invariant, enforcement, and evidence consistency matrix

| Invariant | Current enforcement point | Test/evidence at exact subject | Gap / disposition |
|---|---|---|---|
| Standalone never loads APM workflow | AGENTS, supervision skill, dispatch prose | V1 negative case; V2 self-report | No independent machine field; retain prose, later mechanical workflow-ID check |
| Packet is not authority | Proposal, guide, supervision skill | V2 verified hash and unchanged main | No schema/version validator; packet worked, keep advisory |
| Rotate before context accumulation | AGENTS, proposal, skill, guide, handoffs | V1/V2/cycle telemetry | 80k claims false; replace metric contract |
| Independent reviewer receives no parent history | AGENTS, skill, guide, briefs | Separate root sessions and exact-subject R3 | Prompt may still copy excess history; record dispatch size |
| At most two primary skills | Multiple prose surfaces | Handback self-report only | No structural test; count is not size |
| Stephen owns CodeRabbit | Global/repo instructions and skills | No CodeRabbit tool identity in structural logs | Shell-mediated use cannot be excluded; retain authority boundary |
| Existing deterministic artifacts certified first | Proposal, skill, guide | 26/26 blob match; no R3 regeneration | Strongly supported; preserve |
| Validation proportional to stage | Proposal, skill, guide | Early over-runs; final 135/102 targeted checks | Needs semantic-delta record, not only phase label |
| One normal remediation | Proposal/skill/guide | Cycle needed two after owner rescope | v1 failed; v1.1 correction appropriate |
| Non-research controls pass research-value gate | AGENTS/skill/guide after P-039 | P-039 removal/deferral and clean R3 | Applied late; retain at intake |
| Accepted subject survives integration | AGENTS/skill/guide | Candidate/review/acceptance split; no integration PR | Necessary but not yet exercised |
| PR stays within external capacity | AGENTS/skill/guide | PR-A delta 29 paths; T2 cycle had no PR | Platform rule, not programme evidence |
| Efficiency claims are prospectively measurable | Skill/guide/handoff closeout | Durable JSONLs existed but assessments missed them | Require parser/cut/hash manifest before verdict |
| Stacked PRs integrate bottom-up | Proposal 2.10 and handoff 09 | Historical WP6.1 packet reports exact integration | Useful historical mechanism; outside T2 cycle comparison |

No mandatory checker or convention lock exists at the exact subject. That is the
correct state while H1-H4 remain unresolved. A checker may eventually enforce exact
workflow/subject/root/branch fields, but it must not encode unobservable token ceilings,
research-value judgments, or self-attested efficiency outcomes.

## 8. Negative consequences and practicality

### 8.1 Effects attributable to the protocol

- V1's APM misrouting came from ambiguous workflow identity; the explicit standalone
  declaration fixed it.
- Fresh-task fragmentation produced two avoidable routing stops, repeated startup, and
  more handback/integration work.
- The 80k/first-compaction rule created a false sense of measured control.
- Repetition across AGENTS, guide, skills, proposal, and handoffs expanded prompts and
  created drift surfaces.
- The initial one-cycle and validation rules did not prevent security/runtime scope
  expansion; P-039 and v1.1 corrected this only after cost was incurred.

### 8.2 Pre-existing WP6 complexity, not protocol failure

- The T2 plan genuinely required an atomic sole-writer cost transition while the exact
  base `CommandService` supported only six unrelated commands and rejected others.
- The owner-source catalogue included request, lease, and release operations but no
  grant issuance/reservation/provider-issue/receipt/reconciliation family.
- The 27-path contract candidate, exact schemas, ordered event batches, replay rules,
  220-member protected set, and independent negative controls were substantive WP6
  assurance work. They would remain difficult under any orchestration method.
- R1/R2 findings were not created by the efficiency protocol. The protocol affected
  when and how they were scoped, reviewed, and remediated.

### 8.3 Platform overhead

- Codex worktrees started detached; two prompts mishandled that normal state before the
  deterministic-switch rule was corrected.
- All sessions carried a 256,500-token model window and large system/tool context.
  Fresh-session identity does not remove that fixed overhead.
- Compaction timing is platform-controlled and occurred much later than the proposed
  80k threshold.
- Generic `wait` calls and a blocked temporary-clone cleanup are tooling effects; they
  are not evidence of CodeRabbit polling or research-method failure.

### 8.4 Unrelated tooling and external review

CodeRabbit was not triggered or polled by this review. The historical structural logs
do not expose enough semantics to certify every generic wait as non-external. Repowise,
APM state, Memory Bank, and later workflow-remediation artifacts were not used.

## 9. Research and assurance consequences

### Preserved or improved

- **Research assurance:** P-039 correctly prioritized the research asset and moved
  runtime-only security evidence to the lifecycle stage where it can be observed.
- **Mathematical/statistical assurance:** no mathematical estimate, statistical result,
  dataset, or research claim was produced by this contract cycle, so the protocol did
  not weaken a result-level check. The final review explicitly preserved that boundary.
- **Provenance:** exact commit/tree/blob/raw-hash binding was strong and independently
  reproduced.
- **Exact-state assurance:** packets were continuity aids, not owner decisions; current
  Git/owner records remained authoritative.
- **Independent review:** fresh R1/R2/R3 sessions found defects and final R3
  independently recomputed the protected aggregate rather than trusting the producer.

### Negative or residual

- False efficiency telemetry weakens the provenance of the *workflow claim*, though not
  the T2 candidate.
- Fragmentation can lose unstated context; no dropped requirement was demonstrated in
  this cycle, but prompt copying and handback sprawl make that risk non-zero.
- Repeated author/reviewer validation was appropriate where independence was the
  property. Repeated full-framework or runtime-inapplicable validation was not.
- The accepted candidate, review report, owner record, and efficiency PR remain on
  split histories. Future integration must preserve the exact candidate as reachable
  and review the seam; this review grants no integration authority.
- The method has not yet demonstrated efficiency on mathematical, statistical, or
  result-producing work. Generalization beyond this contract-heavy WP6 case is
  unsupported.

## 10. Preserved mechanisms and cheaper alternatives

Preserve without weakening:

1. exact commit/tree/blob/raw-hash binding;
2. packet-as-locator, never packet-as-authority;
3. fresh independent exact-subject review;
4. owner gates and one-writer/canonical-transition closure;
5. certify-before-regenerate;
6. P-039 research-value and lifecycle-stage discipline;
7. focused independent validation plus one integration-level gate; and
8. a hard stop before a third remediation or unauthorized semantic subject.

Use cheaper implementations:

1. **One normative source.** Keep a short AGENTS trigger and one canonical supervision
   skill. Make the guide examples non-normative and keep dated proposals historical.
2. **Smaller packet.** Require only predecessor hash, exact repo/branch/root/subject,
   decisions, unresolved findings, validation identities, next action, and hard stops.
   Point to every other artifact.
3. **Observable context rule.** Use exact `last_token_usage.input_tokens` when available;
   otherwise use completed-turn/phase/artifact limits and make no token claim.
4. **Prospective telemetry once.** Freeze the explicit session set and Manager prefix at
   closeout, then generate one structural manifest. Reuse it for every assessment.
5. **Canonical-transition preflight.** A short table of writer, command/event/schema,
   reducer/projection, concurrency/idempotency, and version disposition would have found
   the V2 blocker without a full delivery trial.
6. **Semantic validation map.** Record which changed paths/invariants require focused,
   contract, or integration checks. Do not rerun a full suite merely because another
   lifecycle label was reached.
7. **Conditional branch roles.** Always name candidate and integration. Require separate
   management/review branches only when those lanes write.
8. **One-cycle escalation.** Stop after the first remediation and classify findings
   before authorizing a fresh second subject.

## 11. Residual uncertainty

- The historical baseline session behind the proposal's 54/15/195k/549.9m figures is
  unidentified in the authorized evidence, so no historical saving can be recomputed.
- Content suppression prevents direct counts of repeated document reads, loaded skill
  bodies, command-level validation invocations, and the purpose of generic waits.
- `total_token_usage` includes cached replay and is session-specific. It is not a unique
  context-volume or monetary-cost measure.
- Task durations can overlap and incomplete tasks lack `task_complete` duration; the V2
  nested probe is one such case.
- The final R3 validation report is immutable, internally exact, and consistent with
  the Git objects, but this efficiency review did not rerun the 135 tests or 102-contract
  check.
- No matched completed workflow without the protocol exists. Efficiency remains
  indeterminate in magnitude even though several mechanisms are qualitatively useful.

## 12. Implications for any future remediation plan

Any future remediation plan should treat this review as a fresh evidence boundary and
must not assume the later historical plan/review is correct merely because it exists.
It should:

1. issue dated addenda, not rewrite the historical V1/V2/completed-cycle snapshots;
2. withdraw or relabel the 30%-45%, approximately-80k, and below-80k claims;
3. bind a prospective matched workload and exact session manifest before defining
   quantitative success;
4. measure whole-campaign task sets, not only substantive author/reviewer sessions;
5. retain assurance equivalence as a hard comparison condition: same exact-state,
   independent-review, validation, owner-gate, and provenance outcomes;
6. consolidate normative prose before adding a checker;
7. limit any first checker to mechanically decidable identity/routing fields;
8. keep research-value judgments and false/true-stop classification human-reviewed;
9. preserve candidate `391a927...` and R3 `655f417...` identities through any later
   integration; and
10. run at least one matched completed research-facing or result-facing workflow before
    generalizing beyond contract-heavy WP6 work.

Mandatory checker activation and a `CONVENTIONS.md` lock remain **deferred**. The
current evidence supports checker design only after the metric contract is corrected;
it does not support self-activation.

## 13. Decision audit

| Reviewed decision/control | Final disposition |
|---|---|
| Campaign state as exact artifact | keep, make smaller and canonical |
| Certify/deliver split | keep with prospective read/metric evidence |
| 80k/first-compaction budget | replace numeric rule; keep compaction hard stop |
| No-history independent review | keep |
| Two-primary-skill cap | defer as heuristic; measure bytes |
| Stephen-owned CodeRabbit operation | keep |
| Certify before regenerate | keep |
| Progressive validation ladder | keep with semantic-delta mapping |
| Model routing table | defer/remove from accepted evidence |
| Stacked-PR bottom-up closure | keep where stacks exist |
| One remediation cycle | amend to v1.1 rescope/owner/fresh-subject rule |
| P-039 research-value gate | keep and apply before scope freeze |
| Four branch roles | make conditional; candidate/integration always required |
| 100-file external-review cap | keep as external constraint, not trial result |
| Prospective proxy record | strengthen to exact structural telemetry manifest |
| Mandatory checker | defer |
| `CONVENTIONS.md` lock | defer |
| V1 `revise_and_retrial` | supported |
| V2 `approve_advisory_integration` | supported for safety mechanisms, not efficiency claim |
| Completed-cycle `approve_advisory_v1_1_with_revisions` | partially supported; H1-H4 require addendum before quantitative reuse |

## 14. Change log and review validation

This review adds only:

- `docs/plans/agentic-research-system/reviews/large-workflow-efficiency-history-r1-adversarial-review-2026-07-23.md`

No reviewed artifact, global file, source, schema, test, result, branch history, PR, or
external-review state was changed. No CodeRabbit action was taken. Validation and exact
report identities are recorded in the reviewer commit handback rather than asserted in
advance here.
