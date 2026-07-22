# Large-Workflow Efficiency Remediation Plan

**Status:** Proposed for independent adversarial review; not authorized for implementation
**Date:** 2026-07-23
**Workflow system:** Standalone; never APM
**Planning base:** `5e800c748394f717005e4f5e29140be095509ae3`
**Implementation prerequisite:** PR B must be identified by URL, branch, base, and merge
commit and must be merged before any implementation task begins.
**External review owner:** Stephen triggers and monitors CodeRabbit manually.

## 1. Purpose

Reduce the token, time, and operational overhead of large standalone TDL workflows
without weakening research, mathematical, statistical, provenance, exact-state, or
independent-review assurance.

This plan converts the completed WP6.2 T2 trial evidence and subsequent JSONL audit into
a staged improvement programme. It deliberately separates measurement, advisory
workflow changes, helper tooling, and mandatory enforcement so that a useful efficiency
idea cannot silently become a new source of false stops, stale evidence, or bureaucracy.

The plan itself authorizes no changes to skills, instructions, hooks, validators,
workflow state, research contracts, WP6 implementation, or accepted artifacts.

## 2. Authority and boundaries

### 2.1 Governing sources

- `reviews/large-workflow-completed-cycle-assessment-2026-07-23.md`
- `proposals/large-workflow-context-budget-and-orchestration-protocol-2026-07-22.md`
- `docs/guides/large-workflow-supervision.md`
- `.agents/skills/tda-large-workflow-supervision/SKILL.md`
- `.agents/skills/tda-task-brief-from-plan/SKILL.md`
- `.agents/skills/tda-handoff/SKILL.md`
- repository and global `AGENTS.md` instructions
- the nine local WP6.2 T2 session JSONLs identified in the completed-cycle audit

### 2.2 Preserved decisions

- The workflow remains standalone and must not load or mutate APM state.
- Exact-state packets remain continuity aids, not self-authoritative decisions.
- Independent reviewers receive no author or Manager conversation history.
- Research assurance outranks token reduction. A budget may stop or rotate work; it may
  not waive a required mathematical, statistical, provenance, or exact-state check.
- The P-039 research-value gate remains binding before non-research assurance becomes
  blocking. General hardening remains capped at 10% absent Stephen's elevation.
- One author-review-remediation cycle remains the default. A second cycle is a rescope
  and owner-decision event.
- Stephen owns CodeRabbit triggering and monitoring. Agents do not poll it.
- CodeRabbit's hard limit is 100 files; implementation PRs target no more than 90.
- Accepted candidate identities and ancestry must not be rewritten for convenience.
- A mandatory checker, hook, or `CONVENTIONS.md` lock requires a separate owner gate,
  negative controls, a positive execution signal, and an observed advisory pilot.

### 2.3 Explicit non-goals

- No WP6 runtime, T3/T4, credential, provider, eligibility, result, claim, or publication
  implementation.
- No reduction in independent-review scope merely to meet a token target.
- No retention or publication of raw session JSONLs; they may contain sensitive prompts,
  paths, commands, and tool output.
- No assumption that cached and uncached tokens have identical cost or quota semantics.
- No attempt to remove platform-injected context that repository code cannot control.
- No automatic activation of a new gate merely because its implementation exists.

## 3. Baseline evidence

The audited campaign comprised nine sessions: six substantive author/reviewer tasks,
two routing-stop attempts, and the supervising Manager.

| Measure | Observed value |
|---|---:|
| Total accounted tokens | 242,518,491 |
| Cache-read tokens | 236,630,926 (97.6%) |
| Model calls at the audit snapshot | 1,853 |
| Compactions | 12 across six substantive sessions |
| Shell invocations | approximately 1,100 |
| Truncated tool responses | 59 |
| Returned characters in truncated responses | approximately 2.34 million |
| Repeated identical author write preflight | 40 calls |
| Commands containing `git status` | approximately 291 |
| Failed patches | 10 |

The strongest causal observations are:

1. Fresh context (`fork_turns="none"`) prevented inherited-history contamination but did
   not prevent rapid within-task growth.
2. Successful compaction reduced immediate context by roughly 85-88%, but continued
   tasks regrew to the context ceiling and compacted again.
3. Large raw reads, aggregated parallel outputs, repeated skill/log loads, repeated
   preflights, and repeated validation dominated avoidable calls.
4. Output and reasoning were a small fraction of total tokens; model downgrades alone
   cannot solve repeated-prefix cost.
5. Two tasks consumed about four million tokens before stopping on routing mismatches.

## 4. Success criteria and anti-gaming rules

The first post-change pilot is successful only if assurance remains intact and all of
the following are measured from exact session telemetry:

- zero substantive continuation after first compaction;
- zero accepted truncated tool responses;
- routing mismatch stops before repository discovery and, where measurable, within two
  model calls after the first executable preflight;
- no identical write-readiness command repeated before unchanged consecutive writes;
- no full observation-log read during an ordinary task;
- every validation reuse cites the exact command, dependency identities, interpreter,
  and prior result it relies on;
- every independent reviewer still examines the exact candidate and direct authorities;
- every handback contains session ID and exact telemetry or an explicit acquisition
  failure, never an estimate;
- no new ignored or tracked residue in read-only review roots;
- no Critical or unresolved Major assurance regression in the post-pilot review.

A directional campaign target is at least a 50% reduction in accounted tokens for a
comparable author-review-remediation cycle. This is an evaluation signal, not a gate:
different scientific scope must be normalized, and no assurance step may be removed to
manufacture the reduction.

## 5. Obligation register

| ID | Source obligation | Trigger / owner | Plan disposition |
|---|---|---|---|
| O1 | Standalone work must not use APM skills, state, guides, or checkers | Every task / dispatcher | Preserve in dispatch schema and negative control |
| O2 | Rotate at first compaction or declared context threshold | Live task / task owner | Make observable; first compaction is a hard handback |
| O3 | No parent history for independent reviewers | Review dispatch / Manager | Preserve; verify dispatch metadata |
| O4 | Research-value closure precedes blocking non-research assurance | Intake / Manager and Stephen | Preserve as human decision; never reduce to a linter verdict |
| O5 | Second remediation requires rescope and owner ruling | Review cycle / Stephen | Preserve as hard stop and fresh-task requirement |
| O6 | Exact accepted candidate remains reachable | Integration / Manager | Preserve ancestry verification |
| O7 | CodeRabbit limit 100, target 90 | PR packaging / Manager | Count merge-base paths before PR creation |
| O8 | Read-only validation includes launcher and ignored residue | Every review / reviewer | Preserve; helpers must not create local environments |
| O9 | Checker activation requires separate decision, negatives, and positive signal | Enforcement phase / Stephen | Design and pilot advisory-only before activation decision |
| O10 | Skill authoring source is `.agents/skills`; mirrors come from sync tool | Skill changes / implementer | Edit source, then run both sync checks |
| O11 | Handback points to authorities rather than copying them | Rotation / task owner | Add bounded read manifest and telemetry references |
| O12 | Implementation waits for PR B merge | Before Phase 1 / Manager | Hard stop until exact PR B merge commit is recorded |

## 6. Delivery strategy

Use separate semantic work packages and PRs. Do not combine all changes into one
cross-cutting rewrite. Each package receives a fresh implementer and independent
reviewer; later packages begin only after the previous package's findings are resolved
or explicitly deferred.

### Phase 0 - Freeze and adversarially review this plan

Deliverables:

1. Commit this plan as an immutable review subject.
2. Dispatch a fresh, no-history adversarial reviewer.
3. Require a severity-graded report with a complete decision disposition.
4. Resolve every Critical and Major finding through explicit plan amendment or owner
   disposition before implementation authority is requested.
5. Record PR B's exact identity. Stop if PR B is not merged.

No implementation or trial occurs in Phase 0.

### Phase 1 - Read-only telemetry and baseline correction

Objective: make usage and stop conditions observable before changing behaviour.

Proposed deliverables:

- A read-only session metrics utility that locates active and archived Codex JSONLs and
  reports session ID, model-call count, compactions, current/maximum input context,
  truncated outputs, failure-coded tool calls, and file size.
- Optional `ccusage` integration that is explicitly version-checked and degrades to
  JSONL-only metrics without inventing cost.
- Synthetic, minimized JSONL fixtures. Never commit real session transcripts.
- Handback fields for exact session ID and telemetry acquisition status.
- A dated correction/addendum to the completed-cycle assessment replacing the obsolete
  statement that exact token telemetry was unavailable.

Acceptance:

- The utility is read-only, bounded-memory or streaming, works on Windows active and
  archived layouts, and emits no prompt/tool content by default.
- Tests cover malformed lines, an active locked file, missing `ccusage`, compaction,
  truncation, and absent token fields.
- Running it leaves repository and session directories byte-for-byte unchanged.

Adverse effects to test:

- privacy leakage through verbose output;
- double-counting cumulative token records;
- version drift in `ccusage` JSON;
- slow scans over all historical sessions;
- false precision when comparing materially different tasks.

Rollback: remove the optional reporting path; handbacks retain explicit `unavailable`
status rather than estimates.

### Phase 2 - Advisory context and lifecycle controls

Objective: remove the highest-value repeated work without adding mandatory gates.

Proposed changes:

1. Replace the approximate 80k-only rule with observable advisory tripwires: first
   compaction, 80 model calls, or 10 million cache-read tokens, whichever occurs first.
2. State that a compacted task cannot receive correction, remediation, or report-addendum
   work; a fresh exact-state task is required.
3. Rotate the Manager after each complete author-review-remediation cycle.
4. Require routing preflight before skill loading or repository discovery for a task
   that may write.
5. Set an expected returned-output budget of 8-12k characters. A truncated response is
   incomplete evidence and must be narrowed, not accepted.
6. Add a compact dispatch envelope target of approximately 2,500 characters plus an
   exact path/hash reference to the state packet.
7. Add a bounded read manifest: candidate diff, governing authorities, relevant
   lines/symbols, validation commands, and explicit exclusions.
8. Clarify that parallelism applies to bounded computations, not aggregation of
   unbounded text output.

Likely files:

- `.agents/skills/tda-large-workflow-supervision/SKILL.md`
- `.agents/skills/tda-task-brief-from-plan/SKILL.md`
- `.agents/skills/tda-handoff/SKILL.md`
- `docs/guides/large-workflow-supervision.md`
- repository and global `AGENTS.md`, only where a binding always-loaded rule is needed
- corresponding synced skill mirrors generated by `tools/sync_agent_skills.py`

Acceptance:

- Every rule identifies an observable trigger, owner, stop action, and exception gate.
- No instruction tells an agent to ignore history while continuing in a task whose
  history remains technically present.
- Dispatches remain sufficient for a fresh reviewer to identify exact scope and stop
  safely without trusting an author's summary.

Adverse effects to test:

- excessive task fragmentation and handback overhead;
- loss of tacit context that causes duplicate research or wrong decisions;
- arbitrary thresholds that interrupt a nearly complete validation;
- a short prompt omitting a critical prohibition;
- a bounded read manifest becoming self-attested authority;
- token targets discouraging legitimate negative-result exploration.

Rollback: retain telemetry and exact-state records, revert thresholds to advisory
warnings, and require owner-directed rotation while evidence is reassessed.

### Phase 3 - Noisy-work elimination helpers

Objective: replace repeated model-mediated checks with small deterministic tools.

#### 3A. Routing preflight

One command validates root, expected branch/ref, detached-head attachment eligibility,
required SHA, status, and write scope. It emits a compact success record or one precise
failure. It runs before other skill/repository loading in a write-capable task.

Negative controls: wrong root, wrong SHA, dirty tracked path, detached matching ref,
detached mismatching ref, missing ref, and non-writable Git metadata.

#### 3B. Write lease

Replace repeated visible pre-write checks with a lease bound to resolved worktree,
symbolic branch, starting HEAD, allowed paths, and lifecycle epoch. Revalidate after a
branch/checkout operation, compaction, external mutation, scope change, commit, or push.

The initial implementation must be advisory or explicit-command based. Silent hook
enforcement is deferred until liveness, stale-lease, and multi-worktree tests pass.

Negative consequences to attack: stale leases, branch movement without detection,
false confidence from a self-authored lease, race conditions, hidden state files, and
failure to notice an external writer.

#### 3C. Observation selector and append path

Return only OPEN observations matching selected skills and active principles. Provide a
safe append mechanism that allocates and verifies an observation ID without loading the
whole log into model context.

The mandatory runtime observer entrypoint should be shortened; weekly-review procedure
and extended rationale may move to referenced files loaded only when triggered.

Negative consequences to attack: missed cross-cutting observations, stale index,
concurrent number allocation, encoding damage, and divergence between global locations.

#### 3D. Review bundle

Mechanically derive a review bundle from Git: base/subject identities, changed paths,
diff, authority references, dependency/read manifest, validation commands, and hashes.
The reviewer independently verifies the bundle against Git before relying on it.

Negative consequences to attack: author-selected omissions, stale base, generated
summary replacing direct evidence, very large diffs, and accidental sensitive content.

#### 3E. Shell outcome normalization

Provide checked helpers or documented wrappers for expected `rg` no-match, compact Git
state, bounded line extraction, and structured validation summaries. Expected absence
must not masquerade as tool failure; genuine errors must not be swallowed.

### Phase 4 - Validation reuse by exact dependency identity

Objective: avoid rerunning unchanged checks while preventing stale green evidence.

Design before implementation:

- Every reusable validation record binds command, working directory, candidate SHA or
  exact uncommitted bytes, dependency paths/hashes, interpreter/tool versions,
  environment-affecting settings, timestamp, exit status, and output digest.
- Reuse is permitted only when all declared inputs remain identical and the lifecycle
  accepts prior-stage evidence.
- Candidate-head, integration, and independent-review validation remain distinct where
  independence is the assurance property.
- A changed validator, authority, environment, Git history requirement, or relevant
  configuration invalidates the record.

Negative controls must cover undeclared dependencies, changed interpreter, changed
environment variable, changed historical Git object, partial path sets, and a producer
attempting to certify its own output.

Adverse effects to attack: stale passes, incomplete dependency declarations, cache
poisoning, cross-worktree confusion, and increased bookkeeping exceeding saved work.

Activation requires a separate owner decision after the design and negative controls
are independently reviewed.

### Phase 5 - Optional dispatch checker and enforcement pilot

This phase is not automatically authorized by acceptance of earlier phases.

The checker may validate only mechanically decidable properties such as workflow
identity, exact subject/root/branch/write owner, skill count, context tripwires,
external-review owner, lifecycle cycle count, branch roles, validation levels, and PR
file cap. Human research-value judgments remain outside the checker.

Run advisory-only for at least one completed delivery cycle. Record false positives,
false negatives, bypasses, maintenance effort, task fragmentation, and token change.
Mandatory hook/CI activation and any `CONVENTIONS.md` lock require Stephen's separate
approval after the pilot report and adversarial re-review.

## 7. Packaging and merge order

After PR B is merged and the reviewed plan is accepted, prepare implementation from
then-current `main`, not from this planning branch.

Recommended semantic sequence:

1. **PR C1 - Telemetry and advisory rotation:** Phase 1 plus the smallest Phase 2
   documentation/skill changes needed to consume telemetry.
2. **PR C2 - Deterministic workflow helpers:** routing preflight, bounded output/read
   helpers, observation selector, and review-bundle generator with negative controls.
3. **PR C3 - Validation-reuse design and prototype:** no mandatory activation.
4. **PR C4 - Optional dispatch checker pilot:** only after an explicit owner gate.

Before each PR, count `git diff --name-only <base>...<head>`. Target at most 90 paths and
split before 100. Keep a helper with its tests and evidence; do not split a contract from
the negative controls required to review it. Record merge order and run a final seam
review after the stack is composed.

Global observer or global `AGENTS.md` changes require a separate explicitly identified
system change with dated backup, diff, validation, and rollback. They must not be hidden
inside a repository PR that cannot carry them.

## 8. Validation ladder

Each implementation package must define exact commands, but the minimum ladder is:

1. focused unit and negative-control tests for touched helpers;
2. formatting/lint/type checks for touched code;
3. skill synchronization through the authoring source, followed by
   `tools/sync_agent_skills.py --check` and `--check-guides`;
4. synthetic end-to-end dispatch/handback exercise;
5. clean-status and ignored-residue checks;
6. independent adversarial review against the accepted plan;
7. one live advisory pilot with exact session telemetry;
8. post-pilot comparison and owner decision before mandatory enforcement.

Historical-object validation must use a history-bearing clone with
`core.autocrlf=false` and `core.longpaths=true`. Use a verified external interpreter;
the launcher must not bootstrap a repository-local environment.

## 9. Reviewer mandate for this plan

The independent reviewer must not implement or edit the plan. The review must attack:

1. assurance regressions caused by token or call budgets;
2. false stops, over-fragmentation, handback burden, and loss of necessary tacit context;
3. whether preflight-before-skill-loading creates an observer or safety blind spot;
4. whether a write lease weakens exact-root, branch, dirty-state, or external-mutation
   protection;
5. whether bounded reads or generated bundles let authors hide relevant evidence;
6. whether validation reuse can certify stale, incomplete, correlated, or
   producer-authored evidence;
7. whether shortened skills and `AGENTS.md` remove rules that must remain always loaded;
8. privacy, security, Windows, long-path, encoding, multi-worktree, and concurrency
   consequences of new helpers;
9. maintenance burden and duplicated sources of truth;
10. whether thresholds and success metrics are dimensionally comparable and resistant
    to gaming;
11. whether the proposed PR split creates unsafe integration seams or violates the
    100-file review limit;
12. any cheaper or less invasive control that preserves the same assurance.

For every proposed action, the reviewer must state the credible negative consequences,
who bears them, when they appear, whether the mitigation is adequate, and whether the
action should be kept, amended, deferred, replaced, or rejected.

The report must use the `adversarial-design-review` severity rubric, provide direct
file/section evidence, include a plan-decision disposition matrix, and conclude with
`accept`, `accept_with_required_changes`, or `rework_required`. Absence of findings is
not sufficient; preserved mechanisms require an explicit justification.

## 10. Owner gates and hard stops

- Stop if PR B cannot be identified exactly or is not merged.
- Stop if the adversarial review has an unresolved Critical or Major finding.
- Stop before changing global instructions or observer storage without explicit scope.
- Stop before mandatory checker/hook/CI activation without a separate owner decision.
- Stop if an efficiency change weakens research, mathematical, statistical,
  provenance, exact-state, or independent-review assurance.
- Stop if real JSONL content would need to be committed or exposed.
- Stop if a proposed PR exceeds 100 files without a dependency-safe split.
- Stop if validation reuse cannot prove complete dependency identity.
- Stop if the implementation base differs from the recorded post-PR-B `main` and the
  delta has not been reviewed.

## 11. Completion record

Completion requires:

- accepted adversarial review and disposition of every finding;
- exact PR B merge identity;
- per-PR implementation and independent review evidence;
- a completed advisory pilot with exact session telemetry;
- before/after efficiency comparison with scope caveats;
- assurance-regression assessment;
- residual-risk and rollback record;
- explicit owner decision on any proposed mandatory enforcement.
