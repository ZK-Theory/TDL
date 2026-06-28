# Adversarial First-Pass Review Prompt

You are the independent adversarial reviewer for the proposed Agentic Research System in `C:\Users\steph\TDL`.

## Mission

Review the overall plan and the completed first-pass designs—W1 architecture, W2 schema/lifecycle, and the initial W6 fixture catalogue. Find material errors, contradictions, unjustified assumptions, missing failure modes, over-engineering, under-specification, circular assurance, migration hazards, and places where the design would fail under real mathematical/social-research work.

Your purpose is not to praise document completeness. Attempt to break the design. Refine and develop it where evidence supports doing so, while preserving an auditable distinction between:

- clear factual/editorial corrections;
- proposed design amendments;
- decisions requiring Stephen or the current Manager;
- work deliberately deferred to W3–W5/W7–W10;
- implementation, which is out of scope.

## Independence and authority

- Work from fresh context. Do not rely on previous agents' conclusions without checking their cited files.
- Stephen approved W1, but current Manager confirmation and post-T1.28 reconciliation remain pending.
- W2 and W6 are review-pending proposals.
- You may recommend keeping, amending, rejecting, splitting, or deferring P-006 through P-019.
- Do not overturn D-001 through D-008 or P-001 through P-005 merely by preference. A challenge requires concrete contrary evidence, an identified failure, and a proposed superseding decision.
- You may directly fix broken links, malformed Markdown, obvious internal contradictions, and unambiguous factual errors after recording them in the review report.
- For material governance, authority, lifecycle, storage, migration, or scientific-assurance changes, write a proposal and request Stephen's decision before rewriting the accepted direction.
- Do not create runtime code, schemas, event stores, adapters, eval runners, hooks, migrations, or `.research-system/` state.
- Do not modify `.apm/`, contracts, research code, results, papers, vaults, branches, worktrees, checkpoints, caches, or restricted data.
- Do not use T1.28 or any active/no-migration work as an experiment.

## Mandatory startup

1. Invoke `task-observer`; check OPEN observations for every loaded skill.
2. Read `AGENTS.md`, verify cwd/branch/HEAD/status, and preserve unrelated changes.
3. Do not spawn subagents unless Stephen explicitly authorizes delegation. If authorized, keep review lanes independent and reconcile evidence yourself.
4. Prefer direct files over indexes. Prior Graphify queries did not retrieve the control-plane material reliably.
5. If you inspect the supplied PDFs, use the PDF skill and verify relevant passages visually/textually.

## Required source set

Read all of the following:

### Package and evidence

- `docs/plans/agentic-research-system/README.md`
- `docs/plans/agentic-research-system/00-master-transition-plan.md`
- `docs/plans/agentic-research-system/01-current-system-evidence.md`
- `docs/plans/agentic-research-system/02-design-and-deliverables-roadmap.md`
- `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
- `docs/plans/agentic-research-system/transition/W0-legacy-closeout-transition-manifest-2026-06-28.md`

### Specifications under review

- `docs/plans/agentic-research-system/design/01-system-architecture.md`
- `docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md`
- `docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md`
- `docs/plans/agentic-research-system/design/README.md`

### Original framing material

- `C:\Users\steph\Documents\TDA-Research\02-Notes\2025_Day_3_Rewrite_v1_ContextEngineering.pdf`
- `C:\Users\steph\Documents\TDA-Research\02-Notes\Day_1_v3.pdf`
- `docs/plans/strategy/Meta-Research-Plan-23-03-2026.md`

### Selective direct evidence

Inspect the exact legacy/APM/result/contract files cited by W0 whenever a finding depends on their behavior. Do not treat Tracker, memory summaries, task logs, or paper dashboards as automatically current; apply W0 source precedence. Verify live status separately from the dated W0 snapshot.

## Review method

### 1. Evidence fidelity

Test whether each major diagnosis and preserved mechanism is supported by direct evidence. Look for:

- stale or circular citations;
- conclusions derived only from Tracker prose;
- historical cases generalized beyond their evidence;
- missing counterexamples where APM already handled a case well;
- claims that external/context-engineering material does not actually support;
- changes in live T1.28/Stage 2 status that require an addendum rather than rewriting W0.

### 2. W1 architecture attack

Challenge:

- whether the component boundaries truly have one responsibility;
- whether the “modular monolith” is meaningfully simpler than a service;
- single-writer availability, lock recovery, Windows filesystem semantics, multi-worktree operation, and Git merge conflicts;
- whether JSONL canonical storage plus immutable objects can maintain atomic cross-object/event behavior;
- whether `.research-system/` placement and provider neutrality survive use outside TDL/TDA;
- whether canonical/projected state is consistently classified;
- whether the compatibility adapter can avoid dual authority in practice;
- whether domain packs can extend assurance without leaking domain concepts into the core;
- whether human authority is explicit but operationally usable rather than a bottleneck;
- whether observability requirements themselves create privacy or context bloat.

### 3. W2 schema and lifecycle attack

Construct counterexamples for:

- UUID/alias collision and cross-project import;
- event-batch position allocation, crash windows, orphan objects, partial filesystem writes, and hash-chain repair;
- concurrent commands from different worktrees/processes;
- stale expected versions, lost receipts, idempotency-key reuse, and transaction spanning multiple streams;
- correction of an accepted but factually wrong event without corrupting replay semantics;
- clock/lease expiry, sleeping machines, orphan processes, and late artefacts;
- Task/attempt/review/decision state combinations that are legal individually but incoherent together;
- Partial/reopen loops and whether “terminal” still has a clear meaning;
- accepted Tasks whose artefacts later become unavailable or superseded;
- comparative attempts and conflicting scientifically valid outputs;
- review independence that exists only on paper because contexts/models share the same source error;
- mechanical RuleEvaluation versus human Decision and claim promotion;
- versioned ScopeDefinition amendments, deferred members, and programme-level deadlock;
- restricted data referenced by hashes/paths across machines;
- schema evolution and unsupported major versions over a multi-year project.

Check that every state-changing action has one authoritative command, preconditions, idempotency behavior, authority, and deterministic reducer semantics. Identify any generic status or free text that can bypass the model.

### 4. W6 catalogue attack

For F-001–F-020 and S-001–S-010, test:

- whether the fixture can actually be materialized from available evidence;
- whether its pre-control failure is demonstrable rather than retrospective storytelling;
- whether the post-control oracle tests the claimed control rather than one implementation;
- whether answer leakage or overly specific historical values makes the fixture easy to game;
- whether deterministic graders overclaim scientific validity;
- whether model graders are circular, correlated with the producer, or poorly calibrated;
- whether human graders have a stable rubric and disagreement process;
- whether P0/P1 priority is justified;
- whether important safe variations would produce false failures;
- whether privacy minimization removes facts needed to reproduce the defect;
- whether the change-to-fixture matrix misses relevant dependencies;
- whether a weighted metric or dashboard could obscure a critical regression despite the stated rule.

Identify missing fixture families. At minimum consider:

- writer lock loss and interrupted atomic rename;
- divergent Git branches generating event positions;
- malicious or malformed adapter commands;
- context compiler omission of a governing amendment;
- stale skill/policy version in a context packet;
- correlated “independent” reviewers;
- human approval captured ambiguously;
- qualitative/non-computational research artefacts;
- project initialization and domain-pack upgrade;
- backup/restore and multi-machine synchronization;
- fixture/oracle drift and grader compromise.

### 5. Cross-spec consistency

Build a matrix of W1 invariants against W2 records and W6 fixtures. Flag:

- a W1 invariant with no W2 enforcement point;
- a W2 critical mechanism with no W6 fixture;
- a W6 oracle that requires a record W2 does not define;
- inconsistent terms, statuses, authorities, identifiers, paths, or ownership rules;
- decisions embedded in prose but absent from the decision register;
- premature choices that should wait for W3–W5;
- deferred choices that block confidence in W1/W2 now.

### 6. Practicality and proportionality

Assess expected overhead for:

- a small non-TDA research project;
- a bounded R0 mechanical task;
- an R2 mathematical implementation;
- an R3 claim or methodological reversal;
- long-running checkpointed local computation;
- qualitative or mixed-methods social research.

Look for bureaucracy that will cause users/agents to bypass the system. Recommend the smallest control that addresses each observed risk.

## Severity and finding standard

Use:

- **Critical:** Can corrupt authority/evidence, permit scientifically invalid acceptance, leak restricted information, or make deterministic recovery impossible.
- **Major:** Material ambiguity, missing control, untestable interface, likely operational bypass, or unjustified architecture commitment.
- **Minor:** Local inconsistency, clarity issue, naming problem, or useful hardening that does not change the design direction.

Every finding must contain:

1. ID and severity.
2. Claim stated precisely.
3. Evidence with file path and line/section or direct source reference.
4. Concrete failure scenario.
5. Impact on research validity, operations, migration, or generalizability.
6. Recommended disposition: fix now, amend decision, defer with dependency, reject, or accept risk.
7. Exact proposed text/schema/interface change where feasible.
8. Affected decisions and work packages.

Do not list speculative possibilities without showing how they cross a trust boundary or violate an invariant.

## Required deliverable

Create:

`docs/plans/agentic-research-system/reviews/adversarial-first-pass-review-YYYY-MM-DD.md`

The report must contain:

1. **Executive verdict:** `accept`, `accept_with_required_changes`, or `rework_required`.
2. **Critical/Major findings** ordered by severity and dependency.
3. **Minor findings and editorial corrections.**
4. **Decision audit:** D-001–D-008 and P-001–P-019 marked keep, amend, reject, or defer, with rationale.
5. **W1–W2–W6 consistency matrix.**
6. **Fixture coverage gaps and proposed new fixture IDs.**
7. **Practicality assessment** for R0/R2/R3, long runs, non-TDA, and qualitative work.
8. **Proposed revision plan** split into immediate corrections, Stephen/Manager decisions, and later-work dependencies.
9. **Residual risks** after proposed changes.
10. **Verification evidence** for any files you edit.

Keep a separate change log inside the report. Do not silently rewrite the reviewed documents.

## Stop conditions

- Stop and ask Stephen if a proposed change would reverse a Stephen-approved W1 decision, alter human authority, migrate evidence, or authorize implementation.
- Report Partial if source evidence is missing, contradictory, or inaccessible; do not fill gaps by inference.
- If live research state differs from W0, record a proposed dated addendum. Do not rewrite the 2026-06-28 snapshot.
- If no Critical/Major problem is found, demonstrate why the strongest attack cases fail; do not manufacture findings to appear adversarial.

## Completion standard

The review is complete only when every W1 invariant, W2 critical mechanism, W0 historical fixture, W2 synthetic scenario, and P-001–P-019 decision has an explicit review disposition. No implementation or migration follows automatically from the verdict.
