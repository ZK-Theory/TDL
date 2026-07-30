# PR #198 Independent Pre-Merge Re-Review — Exact Subject `85f33e6`

## Verdict

`rework_required_before_merge`

Exact subject reviewed:
`85f33e6148b366b956eb7ca64f759c8a0da9c23e`.

Four of the five `d6c9647` findings are closed at plan level. The remaining
Major is a narrower continuation of PR198-RR1-A: 06j's normative caller table
still omits one current evaluation registry wrapper and misclassifies another
generic evaluation/provider wrapper as adapter-only. The omitted/misclassified
paths currently reach the same context-routing and direct provider-issue seams
that Stage B is supposed to place behind the lifecycle capability, immutable
prevalidated command template, and exactly-once failure-event boundary.

The sealed lifecycle-service design itself now contains the required runtime
capability/signature, prevalidated template, phase-qualified failure,
idempotency/replay, owner-authority, and manifest/fixture mechanisms. It cannot
close the exact subject while its own normative inventory permits a current
transitive path to remain outside that design.

This report is review-only. It grants no G-RM gate, stage dispatch, owner
acceptance, implementation, provider, result, claim, merge, GitHub-thread, or
review-service authority.

## Exact-subject and isolation evidence

| Item | Required | Independently observed | Result |
|---|---|---|---|
| Repository | `C:\Users\steph\TDL` | same Git repository | match |
| Review worktree | clean isolated worktree | `C:\Users\steph\TDL\.review-worktrees\pr198-85f33e6-20260731` | pass |
| Review checkout | detached exact subject | detached `HEAD` | pass |
| Base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | same commit object | match |
| Subject | `85f33e6148b366b956eb7ca64f759c8a0da9c23e` | same commit object | match |
| PR head | exact subject | GitHub PR #198 head equals exact subject | match |
| Remote branch head | exact subject | `refs/heads/codex/rm-lane-rereview-remediation` equals exact subject | match |
| Fetched PR ref | exact subject | `refs/remotes/origin/pull/198/head` equals exact subject | match |
| GitHub PR base | exact base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | match |
| Base ancestry | base is ancestor of subject | `git merge-base --is-ancestor` exit `0` | pass |
| Subject tree | exact detached tree | `7872c04302d045af08241155b0348333681f0053` | recorded |
| Initial/final subject status | clean | no porcelain entries before or after checks | pass |

The host worktree was already dirty on
`pipe/wp6-runtime-schema-binding-a0` at
`9df9fe07b8f1ed1de97012dd9873976b5d70dcd9`. Its pre-existing changes were
preserved and were not used as exact-subject evidence.

## Complete base-to-subject review

The complete `9ed1fa0..85f33e6` range, not only the commits after `d6c9647`,
was reviewed. It contains 24 commits and changes 18 Markdown paths: 3,759
insertions and 1,531 deletions.

The review read the complete RM review/response chain in the range; current
06h, 06i, 06j, implementation README, RM-00, and RM-01 through RM-04; the
accepted P-044 amendment; the governing W2/W3/W4/W7/W8/06c interfaces; and the
current context, routing, coordinator, provider, evaluation registration, CLI,
command, and replay seams. Prior reports and remediation responses were treated
as claims to verify, not as acceptance evidence.

## Finding

### PR198-RR1-A — Major — The normative evaluation caller inventory remains incomplete and semantically misclassifies a generic provider-issue path

**Claim.** 06j calls its exact-subject first-party inventory normative, but the
evaluation-registration row does not literally include all current wrappers,
and the adapter-only row classifies a generic fixture/provider path as exempt
even though that path executes W3 F-025 through F-028 rows and directly builds
and issues a `ProviderCommand`.

**Evidence.**

- 06j says the inventory is normative and may not be deferred
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:155-157`).
- Its registration row lists only `evals/harness.py`,
  `evals/executors/__init__.py`, and CLI scenario/eval dispatch (`06j:164`).
  The Stage B modify map likewise omits `research_system/evals/calibration.py`
  (`06j:108-134`).
- `calibrate_fixture` is a current registry wrapper: it calls
  `require_executor(fixture_id)` and then executes the returned function twice
  plus every mutation
  (`research_system/evals/calibration.py:131-153`).
- `run_p0_coverage` calls that calibration path for the selected P0 fixture
  set (`research_system/evals/harness.py:198-215,247-253`), and the registry
  maps F-025 through F-028 plus F-031/F-033 to
  `context_routing.py` (`research_system/evals/executors/__init__.py:20-28`;
  `research_system/evals/executors/context_routing.py:220-230`).
- 06j's adapter-only row names direct calls in
  `evals/executors/adapter_scientific.py` and `evals/variants.py` and permits
  them to remain outside W3 if they cannot accept a context packet or lifecycle
  dispatch (`06j:165`).
- `variants.py` is not adapter-only by fixture scope. Its generic
  `_execute_through_fake_provider(row, payload, execute, ...)` accepts an
  arbitrary fixture payload, constructs every W3/W4/W7 command field locally,
  and calls `ProviderAdapter.issue` directly
  (`research_system/evals/variants.py:288-341`).
- `execute_gate5_variant_rows_twice` obtains every row's executor through
  `require_executor` and routes the row through that generic direct issue path
  (`research_system/evals/variants.py:355-426`).
- The current variant matrix contains provider variants for each of F-025,
  F-026, F-027, and F-028
  (`.research-system/evals/p0-variant-matrix.yaml:190-321`). These are the same
  four executable P0 oracles that 06j requires Stage B to run through the
  production lifecycle (`06j:303-307,342-348`).

**Concrete failure scenario.** A Stage B Worker follows the normative table,
migrates the listed direct routing/coordinator executors, and retains
`variants.py` under the stated adapter-only exception. F-025–F-028 variant
execution then continues to build caller-supplied operation, policy, rendered
hash, wrapper accounting, and provider-command fields and invokes
`ProviderAdapter.issue` without the `ContextLifecycleCapability` or immutable
`PrevalidatedProviderCommandTemplate`. A policy/accounting rejection can again
escape without one accepted `ContextPacketFailed` event. Alternatively,
closing the path requires unplanned treatment of `calibration.py` and a
different classification of the generic variant wrapper, contradicting the
claim that the literal table is complete.

The repository-wide AST/import test is not sufficient to cure this: the
problem path is already named as an allowed conditional exception, and the
unlisted calibration wrapper reaches it through registry indirection rather
than a direct import of the protected symbols.

**Impact.** PR198-RR1-A remains open. The omission crosses the lifecycle,
provider-command, side-effect, and replay boundary. It also prevents global
credit for PR198-RR1-B/C because the sealed-template and exactly-once failure
mechanisms can be bypassed through a current transitive evaluation path.

**Required disposition.** Fix before merge. Add the exact current symbols and
dispositions for:

1. `evals/calibration.py::calibrate_fixture -> require_executor`;
2. `evals/variants.py::execute_gate5_variant_rows_twice ->
   require_executor -> _execute_through_fake_provider ->
   ProviderAdapter.issue`;
3. the exact CLI/rederivation roots that reach those wrappers; and
4. every registry entry that reaches context-routing, coordinator, or
   provider-issue behavior.

Separate truly adapter-only scientific fixtures from generic F-025–F-028 and
routing/release rows. Require the latter to consume the lifecycle capability
and sealed template, with a runtime negative proving that the full transitive
path is rejected before route/grant/lease/provider side effects when the
capability is missing or forged. The revised exact subject then needs a fresh
independent review.

**Affected decisions/work packages.** PR198-RR1; G-RM-3; G-RM-12; 06j Stage B;
RM-03; W3/W4/W7/W8/06c; executable F-025–F-028 evidence.

## `d6c9647` finding re-evaluation

| Finding | Disposition at exact subject |
|---|---|
| PR198-RR1-A — complete callers and structural firewall | **Open.** The opaque capability, non-optional signatures, guarded dispatch type, missing/forged-capability negatives, and pre-side-effect rejection are now specified at `06j:144-153,167-172,321-331`. The normative inventory is still incomplete/misclassified as described above. |
| PR198-RR1-B — immutable prevalidated provider command | **Mechanism closed inside the intended lifecycle boundary.** Before packet validation/issue, the template binds exact operation, provider/model/profile, adapter revision, context/rendered hashes, command revision/idempotency, timeout, policy/parity/currentness, provider-count evidence, complete canonical wrapper-accounting bytes/hash, and capability digest (`06j:183-192`). W8 adds only its sealed grant/lease envelope; no caller may rebuild W3/W4/W7 fields or perform a fresh policy lookup (`06j:194-201,228-242`). Global closure is withheld because PR198-RR1-A leaves a path around this boundary. |
| PR198-RR1-C — phase-constructible exactly-once failure | **Mechanism closed inside the intended lifecycle boundary.** Requested/compiling use explicit absent evidence and null revision/hash; compiled requires exact present evidence (`06j:203-211`). Every production-seam rejection requires one accepted event/batch, stable failure identity, original receipt on retry, no later lifecycle state, and genesis/incremental equality (`06j:270-277,281-301`). Global closure is withheld only through the PR198-RR1-A bypass. |
| PR198-AUTH1 — owner amendment and gate separation | **Closed.** Stephen-authored commit `24b570f01719b64627496ca435222acc229d1648` has exact parent `fa7d8a6dec4f8d31b9a94747c33e137d4048c376` and changes the bounded proposal to accepted. The current decision-register bytes are unchanged from that acceptance commit. G-RM-10 retains its accepted-family meaning; G-RM-12/13/14 are defined; authority is limited to inert 06i/06j Stage A after separate prerequisites; G-RM-3 and G-RM-12/13/14 remain open; no reviewer, merge, Stage B, provider, result, or claim authority is created (`03-decisions-and-open-questions.md:875-905`; `rm-00:78-105`). |
| PR198-GRM12 — manifest identity and executable/reserved fixtures | **Closed.** The 06j manifest hashes every other leaf only and receives its own blob/raw SHA-256 externally (`06j:31-50`). F-025–F-028 are executable P0; F-029/F-030 remain explicit P1 reservations owned by the pre-pilot follow-up, with no execution/pass claim (`06j:303-307,342-348`). |

## Cross-cutting attack audit

| Attack | Disposition |
|---|---|
| Direct or transitive consumer bypass | **Open.** The calibration/variant registry path is not correctly closed by the normative inventory (PR198-RR1-A). |
| Silent lifecycle failure without accepted failure event | Closed in the lifecycle-service contract; reachable again only through the open transitive bypass. |
| Late W7 policy/accounting failure after context issue | Closed in the lifecycle-service contract by the frozen template and no-new-lookup rule; reachable again only through the open variant direct-issue path. |
| Replay duplication or retry with a new receipt | Closed: deterministic failure identity, exactly one event/batch, and original receipt on retry are explicit. |
| Manifest self-hash or self-acceptance | Closed: every other leaf only; manifest identity supplied externally; no self-acceptance. |
| Reviewer-to-owner escalation | Closed: independent `accept` only makes the subject eligible for Stephen's separate G-RM-3 decision. |
| New or repurposed gate identities | Closed: Stephen's exact proposal acceptance preserves G-RM-10 and defines G-RM-12/13/14 without satisfying them. |
| Reserved fixture represented as executable evidence | Closed for F-029/F-030. Their schema/reservation mapping is explicitly not executable closure. |

## Remaining open owner gates

G-RM-1 and G-RM-2 are the only closed RM owner gates. All of the following
remain open or unsatisfied:

| Gate | Remaining owner action |
|---|---|
| G-RM-3 | Stephen separately accepts an admissibly reviewed exact RM suite subject. This report's rework verdict blocks that action for `85f33e6`. |
| G-RM-4 | Stephen accepts selected Methods Pack assets for exact consumer scope through replay-derived 06i authority. |
| G-RM-5 | Stephen selects the exact RM-04 manuscript-review pilot subject/scope. |
| G-RM-6 | Stephen selects the RM-01 smoke-gate installation location. |
| G-RM-7 | Stephen resolves the known closed-schema literal defect by addition or attributed deliberate omission with continuing non-green status and a follow-up owner. |
| G-RM-8 | Stephen selects the 06h migrate, bounded-grandfather, or independently evidenced no-store protocol after inspectable evidence exists. |
| G-RM-9 | Stephen accepts the exact `RegisteredSchema` interface after its required evidence and review. |
| G-RM-10 | Stephen confirms RM uses the already accepted `RegisterArtefact` / `SetArtefactUseAuthority` family; this does not accept 06i candidate bytes. |
| G-RM-11 | Execution remains deferred unless Stephen later accepts an independently reviewed exact isolation/threat-model subject. |
| G-RM-12 | Stephen accepts independently reviewed exact 06j Stage A candidate bytes before Stage B or RM-03 packet use. |
| G-RM-13 | Stephen accepts an exact independently reviewed `OperatorVerificationRun` for named review/manuscript scope only. |
| G-RM-14 | Stephen accepts independently reviewed exact 06i Stage A candidate bytes before Stage B or canonical RM consumption. |

No test, review response, PR mergeability state, this verdict, or eventual
merge closes any of these gates.

## Read-only verification evidence

- `git diff --check 9ed1fa0 85f33e6`: pass.
- Changed raw Git blobs: 18/18 strict UTF-8, no UTF-8 BOM, no CRLF or bare CR.
- Relative Markdown links across all 18 changed files: zero unresolved.
- Recorded review SHA-256 values recomputed from exact-subject raw Git blobs:
  - `adversarial-rm-lane-plan-suite-rereview-2026-07-30.md`:
    `c73ac88f2fb34dedefbe06dae690347443ced2303d4d957b43143d376aed9e1f`;
  - `pr-198-premerge-review-c7ace86-2026-07-30.md`:
    `cb54b4ceb05629237c9b5af3df0f3bc1b015b79c586ca6dd1d9b2bcde5824cdb`;
  - `pr-198-premerge-rereview-8e091a1-2026-07-30.md`:
    `7c71d00f993f8f6baf56a623a1d089c7cce578a3376ac7fc4b8b3c3dd6c71095`;
  - `pr-198-premerge-rereview-d6c9647-2026-07-30.md`:
    `2f8f44e279ca1471cc7c8987c0896e3a24c7da0efd7c81ff2649300e60d46175`.
- Focused current routing/adapter slice, with bytecode, cache, and coverage
  writes disabled: `23 passed in 0.95s`.

The runtime pass confirms current behavior only. It cannot substitute for the
semantic caller-inventory, lifecycle, replay, or owner-authority review.

## Files changed by this review

Only this required report was added outside the detached subject worktree:

`docs/plans/agentic-research-system/reviews/pr-198-premerge-rereview-85f33e6-2026-07-30.md`

No PR subject, plan, runtime, test, GitHub thread, review service, merge, or
owner-gate state was modified.
