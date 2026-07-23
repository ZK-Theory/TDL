# Evidence-First Large-Workflow Improvement Plan v2

**Status:** Proposed for fresh independent adversarial review; no implementation authorized
**Date:** 2026-07-23
**Workflow system:** Standalone; never APM
**Planning branch:** `codex/wp6-efficiency-remediation-plan-review`
**Planning base:** `03679c1648a04c3393918526b888003048580a04`
**Supersedes:** `large-workflow-efficiency-remediation-plan-2026-07-23.md` only after owner acceptance
**External review owner:** Stephen triggers and monitors CodeRabbit manually

## 1. Decision requested

Approve this document as the replacement design for improving large, review-heavy TDL
workflows. Approval would authorize a fresh independent review of the design. It would
not authorize edits to instructions, skills, telemetry tooling, workflow gates, WP6
artifacts, or accepted research evidence.

The previous programme demonstrated useful assurance controls but did not demonstrate a
token or time saving. This revision therefore changes the order of work:

1. correct and freeze the evidence;
2. consolidate existing rules without inventing new enforcement;
3. pilot only a small set of observable, reversible practices;
4. evaluate a complete workflow without claiming causality from an unmatched comparison;
5. consider tooling or enforcement only after the pilot establishes a need.

## 2. Review boundary and exact sources

This plan jointly disposes the findings from two independent reviews.

| Review | Verdict | Exact identity |
|---|---|---|
| Remediation-plan R1 adversarial review | `rework_required`; 0 Critical, 7 Major, 3 Minor | commit `b32a2253a51c56d08dc509be47730c1f1f96d453`; tree `61d6633056d0990d195b0fa3cef260c7ee167ce1`; report blob `e0d7624a63fa41d0c0bab0397a2069d008cd6399`; raw SHA-256 `7199a7b49bc0ee2de6563209ec4b1c5ec52f90605a415af856b5177063eaa3cd` |
| Historical efficiency programme adversarial review | `partially_effective`; 0 Critical, 5 Major, 3 Minor | commit `3f5f65ca698b083b117c50fa84f9ec908ef83839`; tree `54dadecc08291424ffa78c4e5f28a152eb804167`; report blob `dddc5d2c7f22cb7dc0fc04752e7ae9f5c63a441d`; raw SHA-256 `b62d1346505adb56d24301410d094290120a7df362c8628f49f83505bdae3bd0` |

The historical review froze the active Manager JSONL at a parseable prefix of
10,925,376 bytes through `2026-07-23T00:13:11.352Z`, with prefix SHA-256
`f037dc90071b8cd51513c46715a8ddc8e3f2bf6c0a025f8a19adac239a03a16d`.
The future evidence addendum must carry the complete manifest, not only this Manager
cut.

The rejected R1 plan remains an immutable reviewed snapshot. It must not be silently
edited into compliance or cited as implementation authority.

## 3. Corrected conclusion

### 3.1 What the evidence supports

Retain the following because they protected research or provenance in the WP6.2 T2
cycle:

- explicit `standalone` workflow identity and exclusion of APM machinery;
- exact commit, tree, blob, raw-byte hash, branch, and worktree binding;
- compact state artifacts used as locators, never as authority substitutes;
- fresh, no-parent-history independent review of an exact subject;
- fail-closed canonical-transition and owner-authority checks;
- certify-before-regenerate for deterministic artifacts;
- P-039 research-value and lifecycle-stage triage before non-research controls block;
- focused independent validation plus one integration-level gate;
- a hard owner stop before a second ordinary remediation becomes a third cycle; and
- Stephen-owned CodeRabbit operation and the external 100-file PR limit.

### 3.2 What the evidence does not support

Withdraw or relabel as hypotheses:

- the approximately 80k live-input claim;
- the 30%-45% or 50% token-saving claims;
- any claim that fresh tasks necessarily reduce total context use;
- the two-primary-skill count as a measured efficiency control;
- the classification of the two approximately four-million-token inventory tasks as
  routing failures; and
- any claim that the historical V1/V2 comparison estimates a causal saving.

The direct logs instead show that fresh tasks improved independence while large
self-contained prompts, repeated authorities, skills, tool output, and handbacks kept
per-call inputs high. The genuine routing stops were different, much smaller sessions.

### 3.3 Design principle

No efficiency control becomes normative merely because it is plausible. A control must
have an observable input, a named bearer of its cost, a safe interruption boundary, an
assurance-preserving comparison, and a rollback. Human research-value judgments remain
human; mechanically decidable identity checks remain mechanical.

## 4. Non-negotiable assurance floor

No work package in this plan may weaken:

1. mathematical, statistical, research-design, result, or claim assurance;
2. exact-state and provenance binding;
3. independent review against the exact subject and direct authorities;
4. canonical writer and transition ownership;
5. immutable accepted artifacts and external lifecycle records;
6. complete validation required by the semantic delta; or
7. owner approval boundaries.

Savings produced by omitting one of these are invalid. Security or operational controls
outside the evidence-bearing lifecycle stage may become blocking only after the
research-value gate names the protected research asset, credible failure path, existing
control gap, cheapest adequate intervention, evidence-bearing stage, and bounded effort.

## 5. Replacement operating model

### 5.1 One canonical normative surface

Before changing prose, produce an authority-ownership map with these default roles:

| Surface | Owned content |
|---|---|
| Repository/global `AGENTS.md` | workflow selector, always-loaded safety boundaries, and pointer to the canonical skill |
| `tda-large-workflow-supervision` | normative standalone large-workflow procedure |
| `tda-task-brief-from-plan` | task-brief fields and dispatch closure only |
| `tda-handoff` | handback fields and continuity rules only |
| supervision guide | non-normative examples and worked templates |
| dated proposals, reviews, handbacks, assessments | immutable history and evidence, not current rules |
| future checker | only fields mechanically derived from the canonical owner |

Generated skill mirrors are not additional owners. Pointer-only surfaces must not
restate thresholds or lifecycle semantics. No observer restructuring or global storage
migration belongs in this programme until its canonical location and atomic append
contract receive a separate owner-reviewed design.

### 5.2 Small exact-state packet

The packet contains only:

- predecessor packet identity;
- repository, resolved worktree, branch/ref, and exact subject identity;
- lifecycle phase and workflow system;
- accepted owner decisions and unresolved findings;
- validation identities and current clean/dirty state;
- one next semantic action; and
- hard stops.

Everything else is an exact path/hash reference. Artifact counts must be derived and
must distinguish manifest-bound leaves, an externally bound manifest, and the total
candidate set. Dispatch bytes, packet bytes, loaded skill bytes, and governing-artifact
count are recorded prospectively; they are measurements, not acceptance thresholds.

### 5.3 Observable context and safe-point rule

There is no default 80k token rule.

- If the runtime exposes `last_token_usage.input_tokens`, record its exact source and
  cut. A task may adopt a declared warning level, but no cross-model threshold is
  inferred.
- If no live counter is exposed, use a declared lifecycle, turn, or artifact boundary
  and make no token-threshold claim.
- A coordinating task rotates at the completion of one author-review-remediation cycle
  or at first compaction, whichever reaches the next safe point first.
- A self-contained author or reviewer normally completes one deliverable or verdict.
  It is not fragmented merely to satisfy an unvalidated numeric heuristic.
- Compaction enters **drain mode**: start no new semantic action, edit, claim, or
  remediation. Finish only an already-running atomic read-only operation, capture its
  exact non-interpretive result, verify state, and produce the handback. Any exception
  beyond that boundary requires Stephen's explicit decision and a recorded maximum.

This keeps compaction as a hard rotation trigger without abandoning an in-flight
evidence operation or pretending that compaction proves an earlier token ceiling.

### 5.4 Startup and mutation checks

The sequence for write-capable tasks is:

1. load always-on instructions and activate the research observer;
2. run a minimal read-only **mechanical-state** check;
3. load only the primary skill(s) triggered by the lifecycle and deliverable;
4. resolve authority from an independently identified owner record;
5. perform the existing exact-root, branch, HEAD, scope, and dirty-state check
   immediately before mutation or commit.

Mechanical state is never labelled `write_ready`. A preflight cannot grant authority
from expectations written by the same producer. Detached starts permit one deterministic
same-commit switch to the pre-created branch; a mismatched launch source still stops.

The reusable write lease is rejected. Any later helper must be stateless or perform a
single guard-and-mutate transaction. Cross-process exclusion requires a real lock;
otherwise external-writer races remain an explicitly open risk.

### 5.5 Review scope and generated facts

A generated review bundle may contain only Git-derived mechanical facts: base, subject,
tree, changed paths, diff, object identities, and command outputs. It is a navigation
aid.

The required authority, dependency, and validation sets come from an independently
accepted plan, contract, or catalogue. The reviewer independently resolves both the
subject and that required set. Missing, extra, duplicate, stale, or incompatible entries
fail exact-set closure. An author-supplied read manifest is non-exhaustive and cannot
restrict reviewer discovery.

Every blocking review produces one durable neutral report bound to reviewer task ID,
exact subject, evidence, findings, and verdict. The report cannot grant acceptance;
owner acceptance remains a separate record.

### 5.6 Validation policy

Generic validation reuse is rejected. Producer-declared manifests cannot prove that all
filesystem, environment, Git, locale, network, clock, cache, and toolchain inputs have
been captured.

Use instead:

- certify exact existing deterministic artifacts before regeneration;
- create a semantic-delta map from changed paths and invariants to required focused,
  contract, and integration checks;
- run focused checks where the semantic delta requires them;
- run one full integration gate at the integration boundary; and
- rerun validation whenever independent execution is itself the assurance property.

An expensive validation may become reusable only in a later, separately approved
allowlist after an independent hermetic runner or accepted dependency graph proves its
complete input surface. Prior results may be retained as history but not admitted as
current green evidence without that closure.

## 6. Phased delivery plan

### Phase 0 - Accept the replacement design

Deliverable: this plan plus one fresh no-history adversarial review.

Acceptance:

- every finding from both prior reviews has an explicit disposition here;
- the new reviewer examines negative consequences, cost bearer, timing, mitigation,
  rollback, and cheaper alternatives for every retained action;
- every new Critical or Major is resolved by amendment or explicit owner disposition;
- no implementation occurs from the rejected R1 plan.

### Phase 1 - Correct the record and define the evidence contract

Deliverables:

1. dated addenda to V1, V2, and the completed-cycle assessment; never rewrite snapshots;
2. one exact session-role manifest that separates Manager, substantive work, productive
   inventory subagents, genuine routing stops, and incomplete/auxiliary tasks;
3. a privacy-safe structural telemetry specification and synthetic fixtures; and
4. an authority-ownership map for the workflow rules.

The telemetry contract must:

- accept one explicit session ID/path by default;
- require an owner-authorized manifest for a multi-session campaign;
- freeze byte length, last complete newline offset, prefix digest, acquisition time,
  parser version, role, parent, and inclusion reason before deriving metrics;
- use a structural allowlist and never emit prompts, tool arguments/output, commands,
  or raw paths, including on errors;
- parse offline and stream in bounded memory;
- treat `ccusage` or any external utility as untrusted and deferred until its version,
  input boundary, offline behaviour, and output schema are reviewed; and
- distinguish cached input, uncached input, output, peak per-call input, calls,
  compactions, truncations, task duration, and wall-clock span without collapsing them
  into one cost claim.

Synthetic tests cover malformed and partial lines, invalid UTF-8, CRLF/LF, locked and
growing files, long paths, reparse points, duplicate cumulative events, absent fields,
and concurrent readers. Byte-bound fixtures are checked in both the canonical checkout
and a fresh LF-controlled clone.

Phase 1 produces no behavioural threshold.

### Phase 2 - Minimal rule consolidation

Deliverables:

- one canonical normative skill and an invariant-ownership map;
- pointer-only reductions on duplicated instruction surfaces;
- corrected language withdrawing numeric efficiency claims;
- the compact packet, safe-point/drain-mode rule, research-value intake, and second-cycle
  owner stop; and
- a semantic validation-map template.

This phase adds no mandatory checker, convention lock, write lease, validation cache,
observer append helper, or authority-complete generated review bundle. A cross-surface
conformance test may check only repeated literal identifiers that genuinely must remain
on more than one surface.

Rollback owner: workflow-method owner. Rollback restores the last accepted canonical
skill and its pointers; dated evidence addenda remain.

### Phase 3 - One completed advisory pilot

Pilot subject: the first suitable complete research-facing or result-facing WP6 work
package after the T2 integration PR described in section 8 has merged. A contract-only
or startup-stop fragment is insufficient.

Before dispatch, preregister:

- lifecycle and deliverable class;
- exact task boundary and all expected task roles;
- exact session-manifest rule, including auxiliary tasks and routing failures;
- required assurance outcomes and semantic validation map;
- expected branch and PR structure;
- packet/dispatch/skill-byte measurements;
- safe points and the maximum action permitted after a trigger; and
- the selected comparison class and why it is comparable.

The pilot uses the replacement operating model but no mandatory checker. Stephen still
owns CodeRabbit; agent tasks neither trigger nor poll it.

Pilot acceptance requires a completed deliverable, exact-state continuity, independent
review, required validation, owner-gate compliance, no unresolved Critical/Major, no
unauthorized scope expansion, and a frozen whole-campaign telemetry manifest.

One pilot may establish operability and expose costs. It may not establish a causal
percentage saving. A quantitative claim requires a later matched or randomized/crossover
comparison with equivalent deliverables and assurance outcomes. Until then, report only
the observed metrics and qualitative mechanisms.

### Phase 4 - Post-pilot decision

Produce one assessment that answers:

1. Did the method preserve the assurance floor?
2. Which repeated work actually decreased, and where did cost move?
3. Did rotation create false stops, duplicate validation, omitted context, or handback
   burden?
4. Did rule consolidation reduce loaded bytes and drift without hiding a safety rule?
5. Which mechanisms should be retained, amended, removed, or studied again?

Possible decisions are `retain_advisory`, `revise_and_retrial`, or
`reject_intervention`. Mandatory enforcement is not an outcome of this phase.

### Phase 5 - Optional narrowly scoped tooling

Only a demonstrated recurring problem may enter this phase. Candidate tools are:

- the privacy-safe structural telemetry parser;
- compact shell outcome normalization for expected no-match and bounded summaries;
- a stateless mechanical-state helper; or
- a checker limited to exact workflow, root, subject, branch, lifecycle, and owner fields.

Each tool needs its own semantic PR, negative controls, positive execution signal,
residue/rollback owner, and independent review. Mandatory activation or a
`CONVENTIONS.md` lock requires a separate explicit owner decision after an observed
advisory pilot. Human research-value decisions and self-attested efficiency outcomes
must never be encoded as checker verdicts.

## 7. Prospective evaluation record

Record the following once from the frozen campaign manifest:

| Dimension | Required record |
|---|---|
| Work completed | deliverable identity, lifecycle phases, review/remediation count |
| Assurance equivalence | exact-state, review, validation, owner gates, provenance |
| Context | peak per-call input, compactions, counter source, safe-point actions |
| Total use | cached input, uncached input, output, model calls, all included sessions |
| Prompt burden | dispatch, packet, loaded-skill, and authority bytes |
| Tool burden | calls, truncated outputs, failed routing attempts, repeated checks |
| Time | active task minutes and campaign wall span reported separately |
| Fragmentation | tasks, handbacks, restarts, incomplete attempts |
| External review | owner and status only; no agent polling time |
| Maintenance | files/surfaces changed, drift fixes, tool upkeep, rollback effort |

Do not use cumulative token totals as billing cost, wall time, or unique context volume.
Do not compare only successful substantive sessions while excluding the Manager,
auxiliary work, or failed starts. Report uncertainty and unmeasured fixed platform
context explicitly.

## 8. Current Git and integration gates

As checked on 2026-07-23:

- PR A is [#157](https://github.com/stephendor/TDL/pull/157),
  `[DECISION] P00: integrate standalone large-workflow supervision v1.1`, and is open;
- PR B has not been identified in the live PR list.

For this plan, **PR B** means the integration PR that carries the independently reviewed
and owner-accepted WP6.2 T2 candidate and its separate review/acceptance records to
`main` while preserving the accepted candidate ancestry. Its URL, head, base, exact
subject, accepted identities, and merge commit must be recorded before Phase 3.

No efficiency-remediation implementation begins until PR B is merged. Before the next
substantive WP6 task begins, Phase 1 and the minimum Phase 2 corrections must also be
accepted and merged. PR A must not be cited as quantitative efficiency evidence; its
eventual merge or amendment does not resolve the two adversarial reviews by itself.

Any owner choice to amend PR A before merge, merge it as provisional advisory history,
or supersede it must be recorded explicitly. This plan does not make that Git decision.

## 9. Implementation packaging after approval

Use small semantic PRs from then-current `main`:

1. **C0 - Evidence correction:** dated addenda, frozen telemetry manifest/specification,
   and synthetic fixtures if tooling is authorized.
2. **C1 - Canonical rule consolidation:** ownership map, one normative skill, pointers,
   safe-point language, research-value intake, and semantic validation map.
3. **C2 - Optional telemetry implementation:** only after the Phase 1 contract is
   accepted; no external `ccusage` dependency by default.
4. **C3+ - One demonstrated helper per PR:** only after Phase 4 identifies a recurring
   cost worth mechanizing.

Recount `git diff --name-only <base>...<head>` immediately before every PR creation or
update and again before merge. Target at most 90 changed paths and split before the
CodeRabbit hard limit of 100. Keep every contract with its negative controls. Record a
package-specific rollback and residue owner. Run the integration gate once after the
stack is composed.

Global-system changes remain separate from repository PRs and require dated backup,
diff, validation, rollback, and explicit scope.

## 10. Complete finding disposition

| Finding | Disposition in v2 |
|---|---|
| R1 MAJ-01 / historical H4 | Atomic manifest and dated record correction are Phase 1 blockers |
| R1 MAJ-02 / historical H1 | Replace 80k and absolute termination with observable counters plus drain-mode safe points |
| R1 MAJ-03 | Mechanical preflight follows observer activation; authority is separate; reject reusable lease |
| R1 MAJ-04 | Reject generic validation cache; allow only future independently closed hermetic classes |
| R1 MAJ-05 | Git facts are navigation only; accepted authority catalogue owns exact required-set closure |
| R1 MAJ-06 / historical H3/H8 | One canonical normative skill, pointer-only surfaces, measured loaded bytes, no observer rewrite |
| R1 MAJ-07 | Explicit-session, structural, immutable-prefix, offline privacy contract with Windows/concurrency tests |
| Historical H2 | Withdraw quantitative saving claims; require later matched prospective comparison |
| Historical H5 | Move research-value and second-cycle triage to intake |
| Historical H6 | Retain one same-commit detached attachment attempt and exact launch-source precondition |
| Historical H7 | Keep skill count as heuristic; measure identities/bytes and wait class prospectively |
| R1 minor PR-B finding | Define semantic PR B in section 8; exact live identity remains a blocking acquisition |
| R1 minor PR-count finding | Recount before creation/update and merge; target 90, hard stop before 100 |
| R1 minor rollback finding | Name rollback and residue owner per package |

## 11. Explicitly rejected or deferred work

Rejected from the initial programme:

- reusable write lease;
- generic validation cache;
- author-defined exhaustive review/read manifest;
- absolute 80-call or 10-million-cache-token stop;
- universal 80k threshold; and
- quantitative saving claims from the historical V1/V2 comparison.

Deferred pending independent evidence and owner approval:

- mandatory dispatch checker or hook;
- `CONVENTIONS.md` lock;
- observer entrypoint shortening, append helper, or storage migration;
- external `ccusage` integration;
- model-routing policy;
- validation reuse for a specifically proven hermetic class; and
- any token-based hard stop not exposed by the runtime and validated prospectively.

## 12. Hard stops

- A Critical or Major from the fresh review remains unresolved.
- PR B is unidentified or unmerged when Phase 3 would begin.
- The evidence set is not frozen at exact byte cuts before metrics are derived.
- Real JSONL prompt, command, path, or tool content would be committed or exposed.
- A proposed efficiency change weakens the assurance floor.
- A producer supplies both the expected authority set and its acceptance verdict.
- A task starts a new semantic action after entering compaction drain mode.
- A second ordinary remediation is proposed without owner rescope and a fresh subject.
- A PR would reach 100 changed paths without a dependency-safe split.
- A global-system change is hidden inside a repository package.
- A mandatory checker, hook, cache, or convention lock is proposed without a later
  separate owner decision and observed negative control.

## 13. Required fresh-review mandate

The next reviewer receives no parent conversation and must review this exact committed
subject. The reviewer must particularly attack:

- whether drain mode can still duplicate or abandon necessary evidence;
- whether canonical consolidation hides an always-loaded safety rule;
- whether the telemetry allowlist can leak content through errors or metadata;
- whether the prospective comparison can support the claims this plan permits;
- whether the PR A/PR B sequence creates a period of contradictory authority;
- whether exact-set closure remains independently owned;
- whether the pilot remains practical for research rather than becoming process work;
- who bears each new cost and when; and
- whether an even smaller intervention would preserve the same assurance.

The verdict must be `accept`, `accept_with_required_changes`, or `rework_required`, with
severity-graded findings, a complete action disposition, residual uncertainty, and a
clear statement of what remains unauthorized.
