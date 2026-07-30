# PR #198 Independent Pre-Merge Re-Review — Exact Subject `d6c9647`

## Verdict

`rework_required_before_merge`

PR198-RR1 is not closed at the exact subject. The revised 06j plan states the
required W4/W7 ordering and lifecycle outcomes, but it does not inventory all
current first-party callers or define a structural capability boundary that
makes direct calls unreachable. More importantly, the actual provider command
and wrapper accounting are still built and validated after
`IssueContextPacket`; a late W7 policy/accounting failure can therefore occur
after the packet is no longer eligible for `FailContextPacket`.

The complete base-to-subject review also found independent blockers in the
failure-event contract, owner-authority chain, and G-RM-12 candidate/fixture
closure. PR198-F1, F3, F4's Stage A/Stage B separation, and F5 remain preserved.
PR198-F2 is not fully closed because the failure contract requires a packet
revision/hash during `requested` and `compiling`, before those bytes exist.
G-RM-10 identity/materialization remains internally complete; G-RM-12 does not.

This report is review-only. It grants no G-RM-3, G-RM-10, G-RM-12,
implementation, dispatch, owner-acceptance, or merge authority. No remediation,
merge, GitHub-thread action, or CodeRabbit action was performed.

## Exact-subject and isolation evidence

| Item | Required | Independently observed | Result |
|---|---|---|---|
| Repository | `C:\Users\steph\TDL` | same Git repository | match |
| Fresh review cwd | isolated exact-subject worktree | `C:\Users\steph\.codex\review-worktrees\pr198-d6c9647-20260730` | pass |
| Checkout state | exact subject | detached `HEAD` | pass |
| Base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | same | match |
| Subject | `d6c964751c866caaa68e36a48aa0b017d44a8f2e` | same | match |
| Merge base | exact base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | match |
| Base ancestry | base is ancestor of subject | `git merge-base --is-ancestor` exit `0` | pass |
| Remote PR head | exact subject | `d6c964751c866caaa68e36a48aa0b017d44a8f2e` | match |
| Remote branch head | exact subject | `d6c964751c866caaa68e36a48aa0b017d44a8f2e` | match |
| GitHub PR base | exact base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | match |
| Subject tree | exact tree object | `67b8b91744e854ed98e4febe74657d0640db5c01` | match across `HEAD`, subject, and remote PR head |
| Initial subject status | clean | no porcelain entries; `diff-index` exit `0` | pass |
| Final subject status | clean | no porcelain entries | pass |

All subject evidence came from the fresh detached worktree. The older linked
remediation worktree was not used as subject evidence.

## Complete base-to-subject diff

The range contains ten commits and changes fifteen Markdown files: 3,196
insertions and 1,531 deletions. The review covered the complete range, including
06h, 06i, 06j, README, RM-00 through RM-04, both PR #198 review/response pairs,
the RM lane rereview/response, governing W2/W3/W4/W7/06c interfaces, the
decision register, and the current production routing, coordinator, provider,
command, replay, evaluation, and fixture seams.

Mechanical checks against the exact Git blobs found:

- `git diff --check <base> <subject>`: pass;
- changed-file count: `15`;
- relative Markdown links missing: `0`;
- UTF-8 BOMs in changed blobs: `0`;
- CRLF sequences in changed blobs: `0`;
- the three recorded review SHA-256 values resolve exactly against raw Git blob
  bytes.

## Findings

### PR198-RR1-A — Major — The production caller inventory and direct-call firewall are not structural

**Claim.** 06j promises that Stage B will inventory callers and that a structural
test will reject bypasses, but the plan itself does not provide the required
complete inventory or a capability/signature boundary that makes direct calls
unreachable.

**Evidence.**

- 06j names core modules and selected tests in its file map
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:77-119`),
  then defers the caller inventory to Stage B (`:129-134`, `:245-253`).
- The map omits current shipped callers:
  `research_system/evals/scenarios.py:148,154,169-176,192,195`;
  `research_system/evals/executors/context_routing.py:156,188-189`; and
  `research_system/evals/executors/release_tranche.py:346-358,509,520,523-544`.
  Their transitive registration/call surfaces include
  `research_system/evals/harness.py` and
  `research_system/evals/executors/__init__.py`.
- The named firewall symbols also omit the direct compiled-candidate
  provider-capacity seam
  `research_system/context/compiler.py:96-115`.
- The current functions remain ordinary public Python call surfaces:
  `routing/orchestrator.py:64-100`, `routing/engine.py:60-101`, and
  `operations/coordinator.py:89-134`.

**Failure scenario.** A Worker implements an AST allowlist over the files named
in 06j. A current evaluation executor, or a later first-party caller, continues
to construct `PreparedDispatch` or call `select_route`,
`validate_provider_gate`, or `issue_prepared_dispatch` directly. A failure
dictionary or exception remains the terminal outcome without
`FailContextPacket`.

**Impact.** RR1 criteria 1, 2, and 6 fail. The lifecycle rule depends on
call-site discipline and a test inventory rather than an enforceable runtime
boundary, leaving silent-absence, replay, and consumer-bypass paths reachable.

**Required disposition.** Fix now in 06j. Add a literal
symbol/caller/disposition table for every `research_system/**` call site and
wrapper. Define a sealed lifecycle-service capability or equivalent guarded
type/signature that routing, revalidation, accounting, and provider-issue seams
must consume. The negative must prove that a direct call cannot be formed or
accepted, not merely that current source files avoid it.

**Affected decisions/work packages.** PR198-RR1; G-RM-3; G-RM-12; 06j Stage A
and Stage B; RM-03; W3/W4/W7/06c.

### PR198-RR1-B — Major — Late provider-command validation can fail after `ContextPacketIssued`

**Claim.** 06j prevalidates W7 evidence and issues the context packet before W8
grant/lease and provider issue, but it does not bind that evidence to an
immutable final `ProviderCommand`. The existing provider seam therefore retains
fallible W7 policy and wrapper-accounting validation after
`IssueContextPacket`.

**Evidence.**

- 06j performs selected-route W7 revalidation, then
  `ValidateContextPacket`/`IssueContextPacket`, and only afterward hands the
  packet downstream to W8 and provider issue (`06j:167-178`).
- The current coordinator constructs the actual provider command only after
  resource request, grant, and lease (`research_system/operations/coordinator.py:117-130`).
- The command's operation and wrapper accounting are supplied during that late
  build (`research_system/evals/executors/release_tranche.py:360-390`).
- `ProviderAdapter.issue` independently rechecks authorization, operation
  policy, and wrapper accounting and can raise before transport
  (`research_system/adapters/provider.py:193-201`).
- 06j binds generic W7 evidence identities to validation (`06j:145-150`) but
  defines no immutable command-template/accounting digest that the later
  command must equal.

**Failure scenario.** Early W7 evidence passes and the lifecycle records
`ContextPacketValidated` and `ContextPacketIssued`. The downstream command is
built with missing, invalid, overflowing, or drifted wrapper accounting, or an
undeclared/disabled operation. `ProviderAdapter.issue` raises. The packet is
already `issued`, so the permitted `requested|compiling|compiled -> failed`
transition cannot record the required `ContextPacketFailed`.

**Impact.** RR1 criteria 2, 3, 4, 5, 6, and 7 remain open. The response's claim
that wrapper, policy, and security failures are converted while the packet is
compiled is not true for the actual final command.

**Required disposition.** Fix now in 06j. Specify a sealed, immutable
prevalidated dispatch/command template binding the exact operation, provider,
adapter, rendered hash, policy/parity/currentness identities, and complete
wrapper-accounting fields/digest. After W8 adds only its separately owned
grant/lease bindings, the final command must consume those bytes unchanged.
Retain fail-closed provider enforcement, but make divergence structurally
unrepresentable before `IssueContextPacket`.

**Affected decisions/work packages.** PR198-RR1; G-RM-12; 06j; W3/W7/W8/06c;
RM-03.

### PR198-RR1-C — Major — The failure contract is not phase-constructible or exactly-once

**Claim.** The plan requires every `FailContextPacket` to bind a packet
revision/hash even for failures before a packet exists, and its negatives do
not explicitly prove exactly one failure event/batch and the original receipt
after retry.

**Evidence.**

- `FailContextPacket` is stated to bind the exact packet revision/hash
  (`06j:149-150`).
- The same service must fail before source resolution and during compilation
  (`06j:154-162`, `:222-229`).
- W3 creates the rendered hash and `compiled` candidate only after retrieval,
  packing, and the reference gate
  (`design/03-context-memory-and-retrieval.md:301-311`), while its lifecycle
  permits `requested|compiling -> failed` (`:358-368`).
- 06j says failures emit “one attributable failed state” and requires “an
  attributable `ContextPacketFailed` replay record” plus idempotent retry
  (`06j:204-209`, `:225-229`), but it does not assert one accepted failure
  event/batch and reconstruction of the original receipt.
- W2 requires stable retry identity and original-receipt/one-batch behavior
  (`design/02-task-event-and-artifact-schema.md:233-250`, `:273-280`,
  `:1071`).

**Failure scenario.** Stage A either invents a placeholder packet hash for a
`requested` failure or weakens the schema ad hoc. Separately, a retry uses a new
command/idempotency identity and appends a second `ContextPacketFailed`; current
state and “an attributable record” assertions still pass.

**Impact.** PR198-F2 and RR1 criteria 3 and 7 are not closed. Requested and
compiling failures lack a valid exact evidence shape, and replay equality does
not prove exactly-once attribution.

**Required disposition.** Fix now in 06j. Define a phase-qualified failure
schema: request/context identity is always required; packet revision/hash is
required only after immutable packet bytes exist, with explicit absent/null
semantics for earlier phases. For every production-seam negative, require a
deterministic failure command/idempotency key and assert exactly one accepted
`ContextPacketFailed` event/batch, the original receipt on retry, and no
validated/issued/delivered state in genesis and incremental replay.

**Affected decisions/work packages.** PR198-F2; PR198-RR1; G-RM-12; 06j; W2/W3.

### PR198-AUTH1 — Major — Plan prose self-clears G-RM-3 and expands owner authority without a decision record

**Claim.** RM-00 classifies G-RM-3 as an owner action, but also says an
independent `accept` clears it. The same plan authorizes 06i/06j Stage A
candidate writes and introduces/redefines gates beyond the accepted P-044
record.

**Evidence.**

- RM-00's gate table is headed “Required owner action” and includes G-RM-3
  (`implementation/rm-00-research-methods-lane-master-plan.md:64-82`), but its
  verdict semantics say `accept` “clears G-RM-3” (`:84-90`).
- README similarly says a fresh independent review “clears” the suite
  (`implementation/README.md:53-64`).
- RM-00 and 06i/06j allow Stage A after accepted 06h and G-RM-3
  (`rm-00:56-62`; `06i:48-72`; `06j:27-50`).
- Accepted P-044 authorizes post-review implementation of RM-01 through RM-04
  only and records gates only through G-RM-11
  (`03-decisions-and-open-questions.md:820-868`).
- The earlier G-RM-10 meant confirming use of the already accepted artefact
  family (`reviews/rm-lane-review-response-2026-07-29.md:147-157`); current
  RM-00 repurposes it and adds G-RM-12/G-RM-13 without a decision-register
  amendment.
- Both committed PR review records expressly disclaim G-RM-3 and owner
  acceptance.

**Failure scenario.** An independent `accept` is treated as the G-RM-3 owner
decision and dispatches Stage A. Candidate schemas/contracts are committed under
new or repurposed gate identities that exist only in plan prose, despite P-044
authorizing only RM-01 through RM-04 implementation.

**Impact.** The plan can escalate reviewer disposition into owner and dispatch
authority. G-RM-3 may be textually “open” before review yet self-close on review,
contrary to the required separate owner-acceptance boundary.

**Required disposition.** Fix now. State that independent acceptance makes the
exact subject eligible for Stephen's separate explicit G-RM-3 decision; it does
not close G-RM-3, dispatch any stage, or authorize merge. Obtain and cite an
owner-accepted decision-register amendment that explicitly authorizes the
bounded Stage A scope, defines G-RM-12/G-RM-13, and preserves, supersedes, or
renames the earlier G-RM-10. Until then, keep 06i/06j Stage A non-dispatchable.

**Affected decisions/work packages.** P-042; P-044; G-RM-3; G-RM-10; G-RM-12;
G-RM-13; RM-00; README; 06i; 06j.

### PR198-GRM12 — Major — The G-RM-12 identity and fixture close-out is not constructible

**Claim.** The 06j candidate manifest is described as hashing every leaf while
being one of those leaves, and the plan requires F-025 through F-030 to pass
without creating the missing F-029/F-030 fixture packages.

**Evidence.**

- Stage A lists `identity-manifest.yaml` inside the candidate package and then
  says the manifest binds “every leaf” by Git blob and SHA-256
  (`06j:31-50`). “Does not accept itself” excludes self-acceptance, not
  self-hashing.
- The parallel 06i plan correctly says its manifest “does not hash or accept
  itself” (`06i:52-64`).
- 06j calls F-025 through F-030 its exact-subject oracle and requires them in
  the adversarial corpus and close-out (`06j:231-232`, `:264-268`, `:277-283`),
  but its file map creates no fixture packages.
- The exact subject contains packages only for F-025 through F-028. The named
  corpus test enumerates those four, not F-029/F-030
  (`tests/research_system/integration/test_context_routing_fixture_corpus.py:14-24`).
- F-029/F-030 remain explicitly deferred
  (`research_system/evals/coverage.py:25-33`;
  `.research-system/evals/p0-coverage.yaml:77-82`) and resolve only to design
  reservations
  (`design/06a-w3-retrieval-fixture-addendum-2026-06-30.md:15-24,36,52-60`).

**Failure scenario.** The manifest attempts to contain its own final
blob/SHA-256 and cannot be serialized. If that is silently omitted, the plan
has invented an exception absent from the accepted subject. Separately, the
listed validation command passes while F-029/F-030 remain absent, yet close-out
claims all six fixtures passed.

**Impact.** G-RM-12 candidate identity is circular/ambiguous and its fixture
evidence can silently omit two required cases. The previous G-RM-12
materialization/identity closure has regressed.

**Required disposition.** Fix now in 06j. Define the manifest as binding every
other candidate leaf while its own Git blob/SHA-256 is supplied only by the
external independent review/owner record. Either add exact F-029/F-030 fixture,
materializer, coverage, and test paths to the file map or explicitly retain
their P1 deferral and remove claims that the Stage B command/close-out executes
them. G-RM-12's fixture mapping must distinguish a reserved design from
materialized executable evidence.

**Affected decisions/work packages.** G-RM-12; 06j Stage A/Stage B; W3/W6/W7;
RM-03.

## PR198-RR1 closure matrix

| Required closure | Disposition at exact subject |
|---|---|
| 1. Complete production W4/W7 caller inventory | **Open.** Current `research_system/evals/**` callers and `validate_provider_gate` are omitted; inventory is deferred to Stage B. |
| 2. Every listed failure contained by W3 writer | **Open.** Direct public callers remain; final provider policy/accounting validation occurs after context issue. |
| 3. Failure while compiled, exactly one record, no later state | **Open.** State/no-later-state prose exists, but precompiled evidence is unconstructible and exactly-one event/batch/original-receipt assertions are absent. |
| 4. Validate after immutable W4 decision/witness and successful selected-route W7 | **Closed in normative ordering only.** 06j states this at `:145-175,198-201`. |
| 5. Authority/version/idempotency under lock; no fallible W3/W4/W7 check before issue | **Partially closed.** The lock ordering is stated, but the actual final command retains later fallible W7 checks. |
| 6. Structurally unreachable bypass | **Open.** A future structural test is not a runtime capability boundary. |
| 7. Production negatives with exact bindings, replay equality, retry, and state absence | **Open.** The listed negatives/replay assertions are broad, but omit exact event-count/original-receipt proof and do not cover the late final-command seam. |

## PR198-F1 through PR198-F5 regression matrix

| Finding | Disposition |
|---|---|
| PR198-F1 — existing release-consumer bypass | **Remains closed at plan level.** 06i still inventories and migrates `StoredReleasePublicationEvidence` and both release CLI paths, requires result-scoped use authority, and applies the repository-wide boundary. |
| PR198-F2 — requested/compiling failure lifecycle | **Reopened in part.** The states and commands remain present, but `FailContextPacket` requires a packet revision/hash before packet bytes exist, and exactly-once failure evidence is incomplete (PR198-RR1-C). |
| PR198-F3 — merge-order smoke hole | **Remains closed at plan level.** Final-candidate family inventory and second-to-merge ownership remain in RM-01, RM-00, 06i, and 06j. |
| PR198-F4 — circular exact-subject gate | **Stage separation remains closed.** Stage A precedes owner acceptance and Stage B, but Stage A's authorization and new gate identities lack an accepted owner record (PR198-AUTH1). |
| PR198-F5 — candidate verification run reaches follow-up consumer | **Remains closed at plan level.** RM-04 retains candidate state until unrelated review and exact-scope G-RM-13 authority; result/claim use remains prohibited. |

## Materialization, identity, and cross-cutting audit

| Attack | Disposition |
|---|---|
| G-RM-10 candidate materialization/identity | **Intact at plan level.** Five candidate components, canonical mappings, explicit no-self-hash rule, external manifest identity, load-time equality, and divergence negatives remain present. |
| G-RM-12 candidate materialization/identity | **Open.** Manifest self-hash wording and missing F-029/F-030 executable evidence are blocking (PR198-GRM12). |
| Circular gate/hash dependency | Stage A/Stage B ordering is acyclic, but the 06j manifest's “every leaf” wording creates a self-hash edge. |
| Self-attestation | No accepted manifest self-acceptance was found; external owner binding is retained. The self-hash constructibility defect remains separate. |
| Silent absence/replay gap | Open through direct/late W4/W7 failure paths and incomplete exactly-once failure controls. |
| Consumer bypass | Open for current public routing/coordinator/evaluation call surfaces. |
| Merge-order hole | No regression found in the second-to-merge smoke ownership. |
| New authority escalation | Present: independent review can textually clear an owner gate, and Stage A/new gates exceed the accepted P-044 record. |
| G-RM-3/G-RM-12 state | Both are explicitly described as open, but G-RM-3's self-clearing semantics and Stage A permission make the authority record inconsistent. |
| README/review/response accuracy | Not accurate at the exact subject: README and the RR1 response claim closure that findings PR198-RR1-A/B/C disprove. |

## Focused runtime evidence

The focused current routing/adapter slice was run read-only from the exact
subject with bytecode, pytest cache, and coverage writes disabled:

```text
23 passed in 0.15s
```

The selection was:

```text
tests/research_system/integration/test_context_routing_fixtures.py
tests/research_system/integration/test_adapter_operations_fixtures.py
tests/research_system/unit/test_routing_engine.py
tests/research_system/unit/test_routing_orchestrator.py
```

The pass confirms current behavior; it is not acceptance evidence. An
independent read-only probe reproduced both reachable exits:

```text
plan_dispatch_kind=failure
plan_dispatch_command_submissions=0
revalidation_error=wrapper_accounting_incomplete
command_submissions_after_revalidation_failure=0
```

No `.coverage`, `.pytest_cache`, `.venv`, bytecode, tracked, or untracked
artifact appeared in the subject worktree.

## Decision audit and next action

- Keep P-042/P-044 provider, credential, execution, result, and claim hard
  stops.
- Keep G-RM-3 and G-RM-12 open.
- Do not dispatch 06i/06j Stage A or Stage B from this report.
- Do not treat prior reviews, responses, tests, schemas, PR mergeability, or
  this report as owner acceptance.
- Revise only the bounded findings above, obtain the required owner decision
  amendment for the gate/Stage A authority chain, and request a fresh
  independent exact-subject pre-merge review.

## Files changed by this review

Only this mandated report was added outside the subject worktree:

`docs/plans/agentic-research-system/reviews/pr-198-premerge-rereview-d6c9647-2026-07-30.md`

No subject, plan, runtime, test, GitHub, or review-service state was modified.
