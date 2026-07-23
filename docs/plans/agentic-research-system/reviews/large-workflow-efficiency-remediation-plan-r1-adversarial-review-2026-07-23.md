# Independent Adversarial Review: Large-Workflow Efficiency Remediation Plan R1

**Review date:** 2026-07-23
**Workflow system:** standalone; APM was not loaded or used
**Lifecycle:** independent_plan_review_r1; certify
**Verdict:** rework_required
**Finding count:** 0 Critical, 7 Major, 3 Minor
**Implementation authority:** none

## 1. Exact reviewed subject

| Item | Exact identity |
|---|---|
| Subject commit | 03679c1648a04c3393918526b888003048580a04 |
| Subject tree | ce2e6bb9b70c108a078326f389c4dc005944ee95 |
| Plan path | docs/plans/agentic-research-system/proposals/large-workflow-efficiency-remediation-plan-2026-07-23.md |
| Plan Git blob | 2481777cb57f52b151741a1105c37f21e2c4f1fc |
| Plan raw-byte SHA-256 | f66428fb12e8837d90d2b82714d528692a24bf6eb45bdb7db6746b4a19c8a237 |
| Plan byte count | 22,489 |
| Planning base | 5e800c748394f717005e4f5e29140be095509ae3 |
| Reviewer branch at start | review/wp6-efficiency-remediation-plan-r1 |

The supplied commit, tree, blob, byte count, and SHA-256 were independently
recomputed and match. The plan is the only path added by the reviewed commit.

## 2. Executive verdict

The direction is worthwhile and the plan preserves several essential mechanisms:
standalone/APM exclusion, exact-subject review, Stephen-owned CodeRabbit operation,
the 100-file hard cap, P-039's human research-value gate, immutable accepted
candidate ancestry, advisory pilots before enforcement, negative controls, and a
separate owner gate for mandatory hooks or convention locks. Those mechanisms are
supported by direct governing sources and should remain.

The plan is not ready to authorize implementation. Its baseline is assembled from
the wrong task classification and from two different live-log cut points. The plan
then uses that baseline to motivate absolute interruption rules whose advisory versus
mandatory status is internally inconsistent. Three proposed mechanisms also cross
assurance boundaries without an adequate independent foundation: the preflight/write
lease, generic validation reuse, and the author-originated review bundle/read
manifest. Finally, telemetry privacy, global-log concurrency, Windows byte behavior,
and duplicated authority across instructions, skills, guides, and a future checker
are acknowledged as risks but are not yet controlled.

No Critical is assigned because the plan authorizes no implementation, preserves
owner gates, and explicitly stops on unresolved Major findings, PR-B absence,
assurance regression, real-JSONL exposure, and incomplete dependency identity.
Those stops prevent the present design defects from becoming accepted evidence.

Required outcome: amend the plan in the sequence in section 10 and obtain a fresh
independent review before requesting any implementation authority.

## 3. Severity rubric used

- **Critical:** can corrupt authority/evidence, permit invalid acceptance, leak
  restricted data, or make deterministic recovery impossible.
- **Major:** material ambiguity, missing control, untestable interface, likely
  operational bypass, or unjustified architecture commitment.
- **Minor:** local inconsistency, clarity/naming defect, or useful hardening that
  does not change direction.

## 4. Critical findings

None. This is not an absence-of-evidence conclusion: the no-implementation status,
separate owner gates, PR-B hard stop, exact-candidate ancestry rule, and explicit
assurance-regression stops are effective containment mechanisms and are preserved.

## 5. Major findings

### MAJ-01 — The baseline misclassifies the two approximately four-million-token tasks and is not one atomic snapshot

**Claim.** The baseline does not faithfully identify the sessions from which its
headline measures and causal observation 5 are derived.

**Direct evidence.**

- The plan says the campaign is six substantive sessions, two routing stops, and
  the Manager; it reports 242,518,491 accounted tokens, 236,630,926 cached tokens,
  1,853 model calls, 12 compactions, and says two tasks spent about four million
  tokens before routing stops (plan sections 3 and 4, lines 68-95).
- The completed-cycle assessment names only the six substantive session IDs and
  expressly excludes the Manager and two routing stops from its timed set
  (completed-cycle assessment, lines 34-50). It does not identify all nine JSONLs
  as the plan claims at line 36.
- The two logs whose final totals sum to 4,017,732 are
  019f8a30-8444-77a3-af51-3558ab7577b9 and
  019f8aa5-af01-7801-95f4-35a1b9959e2b. Their session_meta records identify them
  as the t2_authority_inventory and t2_r1_inventory explorer subagents, and their
  task_complete records report completed read-only inventories, not routing stops:
  C:\Users\steph\.codex\sessions\2026\07\22\rollout-2026-07-22T15-17-48-019f8a30-8444-77a3-af51-3558ab7577b9.jsonl
  lines 1 and 147-148; and
  C:\Users\steph\.codex\sessions\2026\07\22\rollout-2026-07-22T17-25-46-019f8aa5-af01-7801-95f4-35a1b9959e2b.jsonl
  lines 1 and 168-169.
- The genuine launch-source routing stops are
  019f8a1b-c117-7d22-988b-88e06c0c53b2 and
  019f8a29-196a-7a80-ac03-ecc5572fdb5d. Their final task messages stop on detached
  HEAD/source-SHA mismatch, and their final totals sum to only 797,952:
  C:\Users\steph\.codex\archived_sessions\rollout-2026-07-22T14-55-07-019f8a1b-c117-7d22-988b-88e06c0c53b2.jsonl
  lines 60-61; and
  C:\Users\steph\.codex\archived_sessions\rollout-2026-07-22T15-09-42-019f8a29-196a-7a80-ac03-ecc5572fdb5d.jsonl
  lines 74-75.
- A content-suppressing structural re-derivation over the six named sessions, the
  two inventory subagents, and the Manager reproduces the plan's token totals at
  Manager token_count event 611: 242,518,491 input-plus-output tokens and
  236,630,926 cached tokens, with 1,847 token_count events. Reaching the reported
  1,853 events requires Manager event 617, at which the corresponding totals are
  242,784,797 and 236,876,960. Thus the three headline measures do not share one
  cut. The Manager log at validation time had SHA-256
  c454f64914dba2e31d633cb573d8b58dc64b737968fd0a3178eed50f35026919;
  events 611 and 617 occurred at lines 3629 and 3666.

**Concrete failure scenario.** The plan attributes useful inventory work to routing
failure and tunes an early routing stop around its cost. A post-change campaign that
retains those inventories but removes the real startup failures can appear to miss
the efficiency target, or an early-stop control can suppress useful discovery.
Non-atomic reads of an active Manager log can also move a threshold while the audit
is being computed.

**Impact.** Evidence fidelity, causal validity, threshold calibration, and
generalizability of the claimed 50% target.

**Disposition.** Fix now; do not calibrate Phase 2 from the current table.

**Required amendment.** Add a dated baseline correction containing an exact telemetry
manifest: session ID, role, parent session where applicable, inclusion/exclusion
reason, file byte length and SHA-256 or an immutable end-offset digest, acquisition
timestamp, aggregation formula, call-event definition, and compaction definition.
Recompute the table from one frozen cut. Split productive subagent cost from genuine
routing-failure cost. Make Phase 1 acceptance of that correction a prerequisite for
selecting any Phase 2 numeric tripwire.

**Affected decisions/packages.** Baseline section 3; success criteria; O2, O11, and
O12 sequencing; Phase 1; all Phase 2 thresholds; PR C1; post-pilot comparison.

### MAJ-02 — “Advisory” tripwires become absolute hard stops without a safe interruption boundary or an implemented exception gate

**Claim.** The plan restates rotation more narrowly and more forcefully than its
governing sources, while leaving the acknowledged nearly-complete-validation case
unresolved.

**Direct evidence.**

- Phase 2 calls its controls advisory, but requires zero substantive continuation
  after first compaction, makes first compaction a hard handback, and says a compacted
  task cannot receive correction, remediation, or report-addendum work (plan lines
  98-113, 124-128, and 192-202).
- The same phase admits arbitrary thresholds can interrupt nearly complete validation
  and says each rule needs an exception gate, but specifies neither the safe checkpoint
  nor who may grant the exception (plan lines 223-241).
- The global and repository AGENTS.md rules rotate the coordinating task at first
  compaction; the plan broadens the hard prohibition to any compacted task. The
  governing protocol describes an 80k starting threshold and role-specific budgets,
  not an unconditional ban on finishing an already-running atomic evidence step
  (protocol sections 2.3 and 2.4, lines 73-92).

**Concrete failure scenario.** A reviewer reaches compaction after launching an
expensive read-only validation but before recording its digest and report. An absolute
zero-continuation rule forces a new task either to rerun the validation, losing the
intended saving, or to reuse a result without the complete provenance that Phase 4
demands. A threshold can also be gamed by splitting calls or suppressing necessary
negative-result exploration.

**Impact.** False stops, fragmented evidence, handback burden, lost tacit context,
stale-validation pressure, and possible research-assurance regression.

**Disposition.** Amend.

**Required amendment.** Define “substantive continuation” as starting a new semantic
action. At a trigger, permit only bounded completion of an already-running atomic
read-only operation, capture of its exact result, clean-state verification, and the
handback; forbid new edits, claims, or remediation. Specify role-specific tripwires,
an observable safe-point state, exception owner, maximum bounded exception, and a
negative control. Preserve first-compaction hard rotation for coordinating campaign
state. Treat 80 calls and 10 million cached tokens as separately calibrated warnings
until Phase 1 establishes their semantics and false-stop rate.

**Affected decisions/packages.** O2, O5, and O11; Phase 2 actions 1-3; handback rules;
PR C1; success criteria; later checker fields.

### MAJ-03 — Preflight-before-skills and a reusable write lease can certify mechanics as authority and weaken per-write protection

**Claim.** The routing preflight and lease lack an independent expected-state
foundation, conflict with always-loaded observer/per-write rules, and cannot close
the external-writer race they claim to address.

**Direct evidence.**

- The plan places routing preflight before skill loading or repository discovery,
  then proposes a “success record” covering root, branch/ref, SHA, status, and write
  scope (plan lines 203-210 and 247-255).
- Global AGENTS.md requires research-observer at the start of tool-using work and
  requires cwd/branch verification before any file write or commit (global AGENTS.md
  lines 1-13 and 20-21).
- Repository AGENTS.md requires exact-root authorization and a deterministic detached
  attachment protocol before writes (repository AGENTS.md lines 71-126).
- The lease is bound to worktree, branch, starting HEAD, paths, and epoch, but omits
  a mandatory dirty-state snapshot, independent authority provenance, and an atomic
  relation between revalidation and the write. “External mutation” is listed as a
  revalidation trigger even though no mechanism observes it (plan lines 256-267).

**Concrete failure scenario.** A Manager-authored envelope supplies both the expected
root/path scope and the inputs to the preflight. The helper strictly compares actual
state to that self-authored expectation and emits “success,” although the relevant
skill or owner record forbids the write. On Windows, another process or linked
worktree moves the branch or edits a path after lease validation but before the write;
no stale-lease event is emitted because the lease cannot observe the mutation.

**Impact.** False write authority, stale leases, multi-worktree races, observer blind
spots, and weaker exact-root/dirty-state assurance.

**Disposition.** Amend the preflight; replace the reusable lease.

**Required amendment.** Run only the smallest read-only mechanical preflight after
always-loaded instructions and observer activation, but before discretionary skill
and repository discovery. Label its output mechanical_state_ok, never write_ready.
Bind expectations to an independently identified dispatcher/owner record. After
loading the selected skill and authorities, perform a separate authority check.
Replace the reusable lease with a cheap stateless per-write/per-commit guard, or a
single-command guard-and-write transaction where feasible. It must resolve filesystem
identity, Git common directory/worktree identity, symbolic branch, HEAD, scoped
tracked/untracked/ignored status, allowed paths, and lifecycle epoch immediately
before mutation. External-writer exclusion requires an explicit cross-process lock or
must remain an unclosed advisory risk.

**Affected decisions/packages.** Phase 2 action 4; Phase 3A; Phase 3B; PR C2; future
checker; global/repository instruction changes.

### MAJ-04 — Generic validation reuse cannot prove complete dependency identity from a producer-declared manifest

**Claim.** Phase 4's hard stop is correct, but its proposed design has no independent
mechanism capable of proving the completeness it requires.

**Direct evidence.**

- Phase 4 binds declared paths, hashes, tools, environment settings, and outputs, and
  says reuse is allowed only if all declared inputs remain identical (plan lines
  296-317).
- Its negative controls include an undeclared dependency, but one known omitted input
  does not prove that every real input has been declared.
- The plan separately requires complete dependency identity and distinguishes
  independent-review validation, but does not define hermetic execution, filesystem/
  process tracing, network closure, Git config/attributes, locale, clock, registry,
  or cache inputs (plan lines 305-320 and 418).

**Concrete failure scenario.** A validation command reads core.autocrlf, a user Git
config, locale, a cache, or a file discovered by a glob that is not in the declared
manifest. The producer omits it unknowingly; every declared identity matches and the
record is reused as green on a different worktree. A producer can also populate both
the dependency list and the verdict.

**Impact.** Stale green evidence, cache poisoning, cross-worktree confusion, and loss
of independent-review assurance.

**Disposition.** Replace the generic mechanism with a narrow eligibility model.

**Required amendment.** Reuse only validations whose complete input surface is
independently established by a hermetic runner or an accepted build/contract graph.
Everything else may be recorded as a prior result but not admitted as current
acceptance evidence. Never reuse producer execution where independent execution is
the property being tested. Define an allowlist of reusable validation classes,
independent expected-input derivation, signer/producer roles, expiry/lifecycle rules,
and negative tests for filesystem, environment, Git config/attributes, toolchain,
network, and history. If closure cannot be proven, rerun or defer; do not prototype a
cache that appears authoritative.

**Affected decisions/packages.** Phase 4; PR C3; validation ladder; post-pilot owner
gate; hard stop at plan line 418.

### MAJ-05 — The bounded read manifest and review bundle have no independent required-set closure

**Claim.** Git can derive commits, paths, and diffs, but it cannot derive the complete
authority set, dependency set, or validation obligations that the plan puts in the
same bundle.

**Direct evidence.**

- Phase 2 adds a bounded read manifest containing governing authorities, relevant
  lines/symbols, validation commands, and exclusions (plan lines 207-210).
- Phase 3D says a review bundle is mechanically derived from Git and includes authority
  references and a dependency/read manifest; reviewer verification is against Git
  (plan lines 281-288).
- The plan recognizes author-selected omissions, and success still requires direct
  authorities, but no owning contract defines the exact required authority/evidence
  set (plan lines 107-113 and 231-238).

**Concrete failure scenario.** An author omits an authority whose path is unchanged
and therefore absent from the candidate diff. The generated bundle exactly matches
Git and all listed evidence passes. The reviewer verifies the bundle against Git but
cannot detect the missing authority because the bundle also defined what to read.

**Impact.** Author-controlled review scope, correlated omission, false independent
acceptance, and hidden unsafe PR seams.

**Disposition.** Amend.

**Required amendment.** Limit the Git-generated layer to mechanical facts. Derive the
required authority/evidence set from an independently accepted plan, contract, or
catalogue and require exact-set closure: missing, extra, duplicate, stale-revision,
and incompatible entries all fail. Record the producer of the bundle and the owner of
the acceptance bar separately. Require the reviewer to independently resolve the
base/subject and authority catalogue; generated summaries remain navigation aids and
cannot replace direct evidence.

**Affected decisions/packages.** O3, O6, and O11; Phase 2 actions 6-8; Phase 3D; PR C2;
independent review acceptance.

### MAJ-06 — The plan adds restatements across six authority surfaces without a canonical owner or drift control

**Claim.** The proposed edits can make maintenance overhead exceed savings and can
silently narrow an assurance rule in one of several always-loaded or procedural
copies.

**Direct evidence.**

- Phase 2 may edit three skills, the supervision guide, repository AGENTS.md, global
  AGENTS.md, and generated skill mirrors; Phase 5 adds a checker that restates a
  subset (plan lines 214-221 and 322-334).
- Skill sync controls only authoring-source/mirror equality. It does not reconcile
  global AGENTS.md, repository AGENTS.md, the guide, the protocol, the checker, and
  handback fields.
- Phase 3C proposes shortening the observer entrypoint and moving rationale, while
  acknowledging missed cross-cutting observations, stale indexes, concurrent IDs,
  encoding damage, and divergent global locations (plan lines 269-279).
- Current global AGENTS.md names ~/.claude/skill-observations/log.md, while the loaded
  research-observer skill identifies C:\Users\steph\.Codex\skill-observations\log.md
  as canonical. The plan does not resolve which location owns the contract before
  proposing an append helper.

**Concrete failure scenario.** The checker encodes the broad “any compacted task”
rule while global AGENTS.md retains “coordinating task”; or an observer append helper
writes one global location while startup selection reads the other. Both surfaces
pass their local checks and diverge silently.

**Impact.** Duplicated authority, maintenance burden, observer blind spots, stale
rules, and false checker decisions.

**Disposition.** Amend and defer observer shortening.

**Required amendment.** Add an invariant ownership map before editing: one canonical
owner per rule, generated mirrors where possible, and pointer-only restatements on
always-loaded surfaces. Add a cross-surface conformance test for fields that must be
repeated. Resolve the observer storage identity and atomic append contract through a
separate owner-reviewed system change before moving any observer content. Keep the
current observer safety entrypoint until selector/append negative controls include
concurrent writers, stale index, invalid UTF-8, CRLF, and both configured locations.

**Affected decisions/packages.** O9-O11; Phase 2 likely files; Phase 3C; Phase 5; PR
C1, C2, and C4; separate global system change.

### MAJ-07 — Telemetry handling is not yet a privacy-safe, immutable, cross-platform evidence contract

**Claim.** Phase 1 acknowledges sensitive raw JSONLs but its acceptance language,
default scope, and validation ladder do not prevent content exposure or unstable reads.

**Direct evidence.**

- The plan says raw session JSONLs may contain sensitive prompts, paths, commands, and
  tool output and must not be retained or published (plan lines 55-64).
- The utility locates active and archived logs, optionally delegates to ccusage, and
  emits no prompt/tool content “by default,” which leaves an unspecified non-default
  path and subprocess boundary (plan lines 157-190).
- The Manager baseline was read from an active log whose content continued beyond the
  audit cut; no end offset or immutable snapshot identity is recorded.
- The validation ladder requires a fresh history-bearing clone with
  core.autocrlf=false and core.longpaths=true, but does not require the same byte-bound
  check in the canonical checkout that the owner actually uses (plan lines 359-375).

**Concrete failure scenario.** A recursive default scan crosses another project's
session, a verbose/error path includes a command or absolute sensitive path, or
ccusage receives raw content not covered by the repository's output contract. On
Windows, a live file is partially read while appended, or an LF-clean fresh clone
passes while the canonical checkout contains CRLF-transformed fixture bytes.

**Impact.** Privacy leakage, incorrect telemetry, false exact-state claims, and
checkout-specific validation failure.

**Disposition.** Amend before Phase 1 implementation.

**Required amendment.** Default to one explicitly supplied session ID/path; require
an owner-authorized manifest for multi-session scans. Parse offline with a structural
field allowlist and never emit prompt, tool input/output, command text, or raw paths,
including on errors. Treat external tools as untrusted subprocesses until their exact
version, input boundary, offline behavior, and output schema are independently
reviewed. Bind active reads to an end offset plus prefix digest and record acquisition
failure on partial/locked data. Test malformed UTF-8, CRLF/LF, long paths, locked and
growing files, symlinks/reparse points, duplicate cumulative records, and concurrent
readers. For byte-hash-bound fixtures, validate both a fresh clone and the canonical
checkout.

**Affected decisions/packages.** Phase 1; PR C1; Phase 3C; validation ladder; success
criteria and handback telemetry.

## 6. Minor findings

### MIN-01 — PR B is a safe hard stop but is not defined by role

The assessment defines PR A as the advisory-instruction integration and then calls for
a distinct T2 integration branch; the plan uses “PR B” without stating that mapping
(assessment lines 152-163; plan lines 7-8, 135, 153, 338-340, and 410). Live evidence
on 2026-07-23 shows PR #157, codex/wp6-manager-efficiency-instructions to main, open at
head 5e800c748394f717005e4f5e29140be095509ae3 with 29 changed paths. No PR is associated
with accepted candidate 391a92753d7f746fa91a6b5455c9ce0fd01baa52.

**Disposition:** keep the hard stop; amend the plan to define PR B as the separately
authorized T2 integration PR, record URL/number/head/base/merge commit, and prove the
accepted candidate is an ancestor of its merged integration head. Current state:
PR B absent and implementation remains blocked.

### MIN-02 — PR path-count evidence must be refreshed before every update and merge

The plan says “before each PR,” while the governing assessment and guide require the
count before opening or updating a PR. A base can advance after initial counting.

**Disposition:** amend the packaging rule to resolve the exact remote base, recompute
merge-base changed paths before opening, every material update, external-review
handoff, and merge; keep 90 advisory and 100 hard. Preserve helper/tests/evidence
together and repeat the seam count after composing the stack.

### MIN-03 — Later packages lack package-specific rollback and residue ownership

Phases 1 and 2 name rollbacks, but the lease/selector/bundle/reuse/checker packages do
not define state-file cleanup, cache/index invalidation, or who removes ignored/global
residue after rollback.

**Disposition:** add per-package rollback, migration/no-migration statement, state
owner, residue check, and recovery validation before any package is authorized.

## 7. Complete plan-action disposition matrix

| Plan action | Credible cost and bearer | When cost appears | Mitigation adequacy | Disposition |
|---|---|---|---|---|
| Phase 0 immutable subject and fresh adversarial review | Reviewer/owner time | Before implementation | Adequate; it exposed material defects | **Keep** |
| Resolve every Critical/Major before authority | Owner and author amendment time | Phase 0 | Adequate and essential | **Keep** |
| Record and merge PR B before implementation | Integration delay borne by campaign | Before Phase 1 | Safe but PR B role is undefined | **Amend** per MIN-01 |
| Read-only session metrics utility | Implementation/maintenance plus privacy risk borne by all session owners | Phase 1 and every closeout | Inadequate scope/snapshot/privacy contract | **Amend** per MAJ-01/07 |
| Optional ccusage integration | Version drift and subprocess privacy borne by operator | Install/update and each run | Version check alone is insufficient | **Defer** until independently bounded |
| Synthetic minimized JSONL fixtures | Fixture maintenance borne by tool owner | Phase 1 changes | Adequate if no real content is copied | **Keep** |
| Handback session ID and acquisition status | Small handback overhead borne by task owner | Every completion | Adequate if unavailable remains valid | **Keep with privacy amendment** |
| Dated assessment correction | Editorial/provenance work borne by plan owner | Before threshold selection | Necessary and currently missing | **Keep; make blocking** |
| First-compaction tripwire | False stops/handbacks borne by active task and successor | At compaction | Inadequate safe-point semantics | **Amend** |
| 80 model-call tripwire | Threshold gaming and premature stops borne by reviewers/implementers | Long tasks | “Model call” undefined and baseline non-atomic | **Defer calibration** |
| 10m cached-token tripwire | Unit/provider drift borne by tasks with high cache reuse | Long tasks/model changes | No stable cross-model semantics | **Defer calibration** |
| No correction/remediation/addendum after compaction | Fragmentation and rerun cost borne by author/reviewer | Late-task corrections | Absolute rule is disproportionate | **Replace** with safe-point rule |
| Manager rotation after a complete cycle | Handback and lost tacit context borne by successor | Cycle boundary | Reasonable boundary with exact packet | **Keep, advisory pilot** |
| Routing preflight before skills/discovery | Observer/authority blind spot borne by repository owner | Task startup | Sequencing is unsafe | **Amend** per MAJ-03 |
| 8-12k returned-output expectation; truncation incomplete | Narrowing/retry time borne by operator | Large tool reads | Appropriate if advisory and evidence-driven | **Keep** |
| Approximately 2,500-character dispatch envelope | Compression/omission risk borne by recipient | Dispatch | Hash/path references help but characters are not semantic completeness | **Amend** to required fields first, size second |
| Bounded read manifest | Omission/correlation risk borne by reviewer | Review intake | Self-attested completeness unresolved | **Amend** per MAJ-05 |
| Bound parallel text aggregation | Some latency borne by task | Multi-query discovery | Proportionate and assurance-neutral | **Keep** |
| Phase 3A deterministic routing helper | Tool maintenance borne by repo maintainers | Every write task | Useful if mechanical-only and post-observer | **Amend** |
| Phase 3B write lease | State, race, cleanup, and false-confidence cost borne by all writers | Every write and external mutation | Advisory label does not close TOCTOU | **Replace** |
| Phase 3C observation selector | Index/selection maintenance borne by observer owner | Every skill load | Useful if full-log content stays out of model | **Keep with atomic exact-scan design** |
| Phase 3C concurrent append path | Locking/encoding/global-state risk borne by all environments | Every new observation | Not designed; canonical location unresolved | **Defer** |
| Shorten observer entrypoint | Missed-rule risk borne system-wide | Every task startup | Referenced files may silently be skipped | **Defer** |
| Phase 3D review bundle | Generator upkeep and omission risk borne by reviewer/author | Every review | Git verification does not prove authority closure | **Amend** |
| Phase 3E shell outcome normalization | Wrapper upkeep borne by maintainers | Common shell checks | Small, testable, and likely cheaper than repeated reasoning | **Keep** |
| Phase 4 validation reuse | Large design/bookkeeping and stale-pass risk borne by validators/reviewers | Every reused result | Generic completeness is unprovable | **Replace/narrow** |
| Phase 5 advisory dispatch checker | False positives, bypasses, and duplicated authority borne by dispatcher | Pilot cycle | Pilot/owner gate is sound; source-of-truth design is not | **Defer pending MAJ-06** |
| Mandatory hook/CI or convention lock | Workflow-wide false stops borne by all contributors | After activation | Separate owner gate, negatives, positive signal, and pilot are adequate | **Keep gate; no activation** |
| PR C1 telemetry plus minimal Phase 2 | Mixed evidence/behavior seam borne by reviewers | First implementation PR | Unsafe until baseline correction precedes behavior | **Amend split/order** |
| PR C2 combined helpers | Broad maintenance surface borne by maintainers | Second PR | Too many independent mechanisms in one review unit | **Replace with smaller semantic PRs** |
| PR C3 reuse design/prototype | Prototype can acquire false authority | Third PR | “No mandatory activation” helps but not enough | **Defer until eligibility contract** |
| PR C4 checker pilot | Pilot overhead borne by dispatchers | After owner gate | Proportionate only after canonical authority map | **Defer** |
| 90-target/100-hard file packaging and seam review | Some stack overhead borne by integrator | Every PR | Strong and proportionate | **Keep with recount amendment** |
| Separate global-system change | Additional review/backup work borne by system owner | Any global edit | Necessary isolation | **Keep** |
| Validation ladder | Test/runtime cost borne by implementers/reviewers | Every package | Preserves assurance but needs canonical-tree byte check | **Amend** per MAJ-07 |

## 8. Cross-source consistency matrix

| Invariant | Direct owning evidence | Plan enforcement | Review result |
|---|---|---|---|
| Standalone, never APM | Protocol lines 7-13 and 170-197; supervision skill lines 16-40; repo/global AGENTS.md | Plan lines 3-5, 40, 124, 416 | **Consistent; keep** |
| No author/Manager history for independent review | Protocol lines 84-92; guide lines 38-45; supervision skill lines 83-91 | Plan lines 42, 109, 149 | **Consistent; keep** |
| P-039 research-value gate remains human | P-039 lines 35-58; decision register lines 627-658 | Plan lines 43-48, 127, 319-329 | **Consistent direction; preserve exact category-4 denominator** |
| Second remediation is owner rescope | Assessment lines 100-106; supervision skill lines 89-91 | Plan lines 47-48, 128, 411 | **Consistent; keep** |
| Stephen owns CodeRabbit operation | Global AGENTS.md lines 24-32; protocol lines 101-105; guide lines 110-112 | Plan lines 9, 49, 329 | **Consistent; keep** |
| CodeRabbit hard cap 100, target 90 | Assessment lines 116-123; guide lines 120-125; supervision skill lines 104-109 | Plan lines 50, 130, 350-353, 417 | **Consistent; recount timing needs MIN-02** |
| Accepted candidate remains reachable | Assessment lines 108-114 and 156-160; P-040 lines 660-687; guide lines 114-125 | Plan lines 51, 129, 338-353 | **Consistent; keep** |
| Candidate identity is exact 391a927... | Decision register lines 660-687; owner acceptance lines 18-26 | O6 and PR-B gate | **Direct Git confirms tree 0254c541..., 27 paths, and direct-parent R3 review** |
| Mandatory enforcement needs separate owner gate | Protocol lines 250-271 and 299-326; assessment lines 140-150 | Plan lines 52-53, 319-334, 413 | **Consistent; keep** |
| Rotation at first compaction | Global/repo AGENTS.md says coordinating task; protocol has role budgets | Plan broadens to every compacted task and zero continuation | **Inconsistent; MAJ-02** |
| Per-write readiness | Global AGENTS.md line 20; repo worktree rules lines 71-126 | Reusable lease replaces visible checks | **Inconsistent; MAJ-03** |
| Observer starts before work | Global AGENTS.md lines 1-13 | Preflight before skill loading | **Inconsistent unless observer is explicit exception; MAJ-03** |
| Exact telemetry unavailable in dated assessment | Assessment lines 28-30 and 133-138 | Phase 1 proposes dated correction | **Proper dated-addendum approach; baseline correction must be atomic** |
| Handback points to authority, not copies | Protocol lines 33-64; handoff skill lines 35-58 and 82-90 | O11 and bounded references | **Consistent; bundle completeness still MAJ-05** |
| Skill authoring source and mirrors | Protocol lines 160-161; plan O10 and validation ladder | Sync checks | **Consistent; keep** |

## 9. Practicality and proportionality

| Workload/control | Likely overhead | Saving/risk judgment |
|---|---|---|
| Explicit-session structural telemetry | Low per run after medium implementation | Worthwhile; cheapest way to observe before changing behavior |
| Global recursive telemetry scan | Potentially high I/O and privacy review | Avoid by default; overhead and risk exceed benefit |
| Safe-point rotation with exact packet | One handback and startup per trigger | Likely worthwhile for supervisors; calibrate leaf tasks separately |
| Absolute first-trigger termination | Duplicate validation and re-derivation | Can exceed token saving; reject in present form |
| Stateless mechanical preflight | One compact command per write boundary | Cheap and strong if authority is separate |
| Stateful write lease | Cross-process state, invalidation, cleanup, races | Complexity likely exceeds saved checks; replace |
| Observation selector | Small deterministic parse/index cost | Worthwhile if exact scan/atomic append remains outside model context |
| Git-facts bundle | Low generation cost | Worthwhile as navigation only |
| Authority-complete review bundle | Catalogue/ownership machinery required | Worthwhile only after independent exact-set contract |
| Generic validation cache | High manifest, environment, and review burden | Overhead exceeds rerunning most short checks; narrow to expensive hermetic checks |
| Advisory checker | Medium implementation and ongoing drift cost | Pilot only after one canonical authority map exists |

The cheapest adequate initial programme is therefore: correct/freeze telemetry,
adopt privacy-safe explicit-session reporting, preserve current assurance gates,
add a stateless mechanical preflight, normalize bounded shell outcomes, and pilot
safe-point rotation. Lease state, generic validation reuse, observer restructuring,
and mandatory checking should not be in the first implementation wave.

## 10. Proposed revision sequence

1. **Correct evidence first.** Publish a dated baseline addendum with the exact
   telemetry manifest and one-cut aggregation. Reclassify the two inventories and two
   real routing stops.
2. **Resolve owner semantics.** Define PR B, the exact role scope of compaction
   rotation, the safe-point/exception owner, and whether any leaf-task threshold may
   become hard.
3. **Create the authority map.** Assign one canonical owner to every repeated rule and
   define generated versus pointer-only surfaces.
4. **Rewrite Phase 1 as a privacy contract.** Explicit sessions, structural allowlist,
   immutable end-offset digest, offline subprocess boundary, Windows/encoding tests,
   and canonical-plus-fresh byte validation.
5. **Narrow the first behavior pilot.** Safe-point rotation, stateless mechanical
   preflight after observer activation, bounded outputs, and shell normalization only.
6. **Replace unsafe architectures.** Remove the reusable lease; restrict validation
   reuse to independently closed hermetic classes; separate Git facts from independently
   owned review requirements.
7. **Repackage PRs.** Put telemetry/correction before behavioral changes; split helper
   families by responsibility; add per-package rollback and exact recount points.
8. **Fresh adversarial re-review.** Resolve every Major, verify live PR-B state and
   accepted-candidate ancestry, then seek explicit owner authority for the first pilot.

## 11. Residual risks after the required amendments

- Token and cache semantics may change across Codex/model versions; comparisons remain
  version- and role-stratified rather than universal.
- No advisory preflight can exclude an uncontrolled external writer without an atomic
  lock; that residual must remain explicit.
- Authority catalogues can themselves drift or be authored by the producer; their owner
  and acceptance identity require independent review.
- Hermetic dependency closure may be unavailable for some validators; those checks must
  rerun rather than reuse.
- A compact handback cannot preserve all tacit context; pilot false-stop and duplicate-
  research rates must be measured, not assumed.
- The 90-path target may still produce a cognitively oversized PR; file count is a cap,
  not a review-complexity metric.
- PR B is absent at review time. No efficiency implementation may start.

## 12. Exact validation and Git evidence

### Subject and source checks

- Recomputed subject commit/tree, plan blob, plan byte count, and raw SHA-256.
- Read the reviewed plan from the exact subject, not the working-tree summary.
- Resolved and inspected the exact-subject blobs for:
  - completed-cycle assessment: blob 488a15361364aa6f5df8e56baa02c4df9e243aba;
  - context/orchestration protocol: blob d031159247891e09f20f9e6ee3f358b0d20edcca;
  - supervision guide: blob fee078d90fd9d95aae91b16382706475a3c7065c;
  - supervision skill: blob 9ca6cbd9dc7bc1e97b9931c41b9cc29c9b3f2206;
  - task-brief skill: blob 28b222e9f4701fac726641974eea97ce7bd2a2b9;
  - handoff skill: blob 95064755e6259ba991d4752f41ac40e1206b309a;
  - repository AGENTS.md: blob 1fe6a0069a1f68bb7c3906b9addfa433163b37de.
- Inspected current global AGENTS.md; SHA-256
  1c1d1b13a6ee4806e51d9b323e507e8015b12ffc4d075cdc647a5bfd961181bd.
- Inspected P-039 and P-040 direct decision/acceptance records.

### Telemetry checks

- Used a local structural parser that emitted field counts and numeric telemetry only;
  no prompt, command, tool input, or tool output content was copied into the repository.
- Re-derived the nine-log token/cache/compaction figures at Manager cuts 611 and 617.
- Distinguished subagent metadata and task outcomes from the two archived detached-source
  routing stops.
- Confirmed that the plan's 40 repeated author preflights correspond to two exact
  repeated command forms (30 and 10), that approximately 290 calls contain git status,
  and that shell invocation scale is approximately 1,100. These supporting counts do
  not repair the session-classification or atomic-snapshot defect.

### Git and remote checks

- Fetched origin read-only. origin/main remained
  3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d.
- Accepted candidate 391a92753d7f746fa91a6b5455c9ce0fd01baa52
  has tree 0254c5416925126412867d61b3045ee1563abd0c and exactly 27 changed paths.
- R3 review 655f4173db93447a068adc6e92621455c4abc85d is a direct child of the
  accepted candidate.
- The accepted candidate is reachable from
  origin/pipe/ars-wp6-2-t2-r3-remediation and
  origin/review/ars-wp6-2-t2-authority-addendum-r3-static.
- The accepted candidate is not an ancestor of the planning base or reviewed subject,
  which is appropriate for a management/planning branch but makes the later integration
  ancestry proof mandatory.
- GitHub PR #157 is open, not merged, from
  codex/wp6-manager-efficiency-instructions at 5e800c748394f717005e4f5e29140be095509ae3
  to main at 3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d, with 29 changed files.
- No PR is associated with the accepted candidate or its three checked T2 branches.
  PR B is therefore not identified or merged.

No implementation, tests, hooks, CodeRabbit operation, global edit, plan edit, or
accepted-artifact mutation was performed.

## 13. Change log

- Added only this independent review report.
- Reviewed plan and governing sources were not edited.

## 14. Unresolved owner decisions and hard stops

### Owner decisions

1. Confirm the semantic identity of PR B and its required accepted-candidate ancestry.
2. Decide the role-specific scope of first-compaction hard rotation and the bounded
   safe-point exception authority.
3. Approve one canonical authority map before any global/observer/checker restructuring.
4. Decide whether any validation-reuse class is valuable enough to justify a hermetic
   closure contract.

### Hard stops

- PR B is absent/unmerged.
- Seven Major findings are unresolved.
- The baseline correction has not been frozen from one exact telemetry cut.
- No reusable write lease, generic validation cache, observer append path, generated
  authority bundle, or mandatory checker may be implemented from this revision.
- No real JSONL content may be committed, exposed, or passed to an unaudited external
  subprocess.
- No change may weaken research, mathematical, statistical, provenance, exact-state,
  or independent-review assurance.
