# PR #198 Independent Pre-Merge Re-Review — Exact Subject `8e091a1`

## Verdict

`rework_required_before_merge`

The exact subject is mechanically stable and most prior remediation is
semantically preserved. The G-RM-10/G-RM-12 materialization and identity
requirements are now complete at plan level, and PR198-F1 through PR198-F5
remain closed. One dispatch-blocking lifecycle defect remains: the revised 06j
contract states that post-compilation provider-capacity and packet/manifest
validation failures produce `FailContextPacket -> ContextPacketFailed`, but it
does not bring the existing W4/W7 routing and selected-route revalidation seams
under that lifecycle writer or make them structurally unreachable. Those
production paths can still fail before any lifecycle command is submitted.

This is an independent pre-merge review only. It grants no G-RM-3, G-RM-10,
G-RM-12, implementation, dispatch, owner-acceptance, or merge authority.

## Exact subject and isolation evidence

| Item | Required | Independently observed | Result |
|---|---|---|---|
| Repository | `C:\Users\steph\TDL` | same | match |
| Review cwd | fresh isolated worktree | `C:\Users\steph\.codex\worktrees\pr198-8e091a1-review\TDL` | pass |
| Review state | symbolic branch or detached exact head | detached | pass |
| Base SHA | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | same | match |
| Subject SHA | `8e091a1784de380595e4cef7215b0a3eecf41399` | same | match |
| Subject tree | exact Git tree | `68da0af8a0c2350f5a61a7d16e2e0d59720a4c8a` | recorded |
| Merge base | required base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | match |
| Commit count | complete base-to-subject range | 5 | match |
| Remote branch head | required subject | `8e091a1784de380595e4cef7215b0a3eecf41399` | match |
| Remote PR head | required subject | `8e091a1784de380595e4cef7215b0a3eecf41399` | match |
| Initial status | clean | `git status --short` returned no entries | pass |
| Final status before report | clean | `git status --short` returned no entries | pass |

The review used the detached exact-subject worktree for all subject evidence.
The host checkout was already dirty on
`pipe/wp6-runtime-schema-binding-a0` at
`9df9fe07b8f1ed1de97012dd9873976b5d70dcd9`; those pre-existing changes were
not read as subject evidence and were not modified.

The repository has `core.autocrlf=true`. All byte identities in this review
were therefore resolved from raw Git blobs with `git cat-file`, not from
platform-translated worktree bytes.

## Complete PR diff

The range contains these five commits:

1. `9be7f0ed0ab717b782076a2d6da823e298f09dc2`
2. `c7ace86ca097c831930a54f1dd6e99b7c341cddf`
3. `464a2e7233059112b276d5a08cb0358cfd7a5fa9`
4. `cf3dfd88a0a26793fb2f76102ff0330ccfd80060`
5. `8e091a1784de380595e4cef7215b0a3eecf41399`

The complete diff changes 13 Markdown paths, with 2,768 insertions and 1,531
deletions:

| Exact-subject blob | Path |
|---|---|
| `8d93c11f2cf0c8f989f9c3a0bab44046a779e1ce` | `implementation/06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md` |
| `de3f6e11dc9baa8dafc48b4880e05b430d0f176d` | `implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md` |
| `ff810855c59273d81b347b831d6fc1b22f023629` | `implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md` |
| `b6e1595953f551a097374c8b84e5ee1600cc8724` | `implementation/README.md` |
| `715fa23503998f3a24c58007bff5a899687d5240` | `implementation/rm-00-research-methods-lane-master-plan.md` |
| `bfe29bdaadff4ad244523b98e387f60d77517d7b` | `implementation/rm-01-unblock-and-suite-recovery-plan.md` |
| `35eea6b44fb5a84c9d43cdc4bb0bb3d9d518ac08` | `implementation/rm-02-research-methods-pack-plan.md` |
| `9722b03f894bb3021153debbd91d453c677c1418` | `implementation/rm-03-brief-export-import-plan.md` |
| `501e2b13cb7668d27107dd6ca7ff9005019fd77e` | `implementation/rm-04-manuscript-review-and-verification-records-plan.md` |
| `915a7b11f9b95af05e9fb8684f9a0061aac62434` | `reviews/adversarial-rm-lane-plan-suite-rereview-2026-07-30.md` |
| `4ecfa278a75d8a6e041b918f6124124213c6178d` | `reviews/pr-198-premerge-review-c7ace86-2026-07-30.md` |
| `75ecda7a62bd3bee152bf50f8c66f480d9f3461d` | `reviews/rm-lane-pr198-premerge-review-response-2026-07-30.md` |
| `e2393061546f288b0a8be42dbb987be1f59d2ef8` | `reviews/rm-lane-rereview-response-2026-07-30.md` |

Paths in the table are relative to
`docs/plans/agentic-research-system/`. The current versions of all changed
plans and responses, the complete base-to-subject patch, the governing W2/W3
sections, accepted 06c ordering, and current runtime seams were inspected.

## Dispatch-blocking finding

### PR198-RR1 — Major — Post-compilation W4/W7 failures can still bypass `FailContextPacket`

**Claim**

The revised 06j text does not yet guarantee that every provider-capacity or
packet/manifest validation-precondition failure after compilation submits
`FailContextPacket` and leaves an attributable, replayable
`ContextPacketFailed` record.

**Plan evidence**

- 06j correctly defines
  `FailContextPacket -> ContextPacketFailed`
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:58-67`).
- The compiler text now says provider-capacity, manifest, security, and
  independence checks precede validation, and that failures submit
  `FailContextPacket`
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:127-143`).
- The transition and control sections require an attributable failed state,
  provider-capacity and packet/manifest negatives after `compiled`, and a
  replay record for each validation-precondition rejection
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:158-186`).
- However, the Stage B create/modify map names context models/compiler/service,
  command service, replay, and CLI, but not the existing routing orchestrator,
  routing engine, operations coordinator, or provider adapter
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:77-107`).
- Its final production-seam instruction runs controls through
  “producer/resolver call sites”; it does not inventory or structurally close
  W4/W7 routing and pre-issue revalidation callers
  (`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:212-216`).

**Current exact-subject behavior**

- `plan_dispatch` accepts a compiled, unissued candidate and returns an
  ordinary route-failure object without a command submission
  (`research_system/routing/orchestrator.py:64-85`).
- `select_route` represents “no eligible route”, including
  `context_budget_exceeded`, as a returned failure dictionary
  (`research_system/routing/engine.py:46-82`).
- `issue_prepared_dispatch` calls `adapter.revalidate(...)` before its first
  command submission
  (`research_system/operations/coordinator.py:89-123`).
- Wrapper-accounting absence, invalid shape, and capacity overflow raise
  directly
  (`research_system/adapters/provider.py:68-93`).
- Existing F-028 checks only that the provider-capacity gate throws
  `ContextBudgetExceeded`; it does not require a lifecycle command or replayed
  failure state
  (`tests/research_system/integration/test_context_routing_fixtures.py:89-115`).

A read-only dynamic probe at the exact subject confirmed both reachable forms:

```text
plan_dispatch_kind=failure
plan_dispatch_failures=context_budget_exceeded,context_budget_exceeded
revalidation_error=wrapper_accounting_incomplete
command_submissions_after_revalidation_failure=0
```

**Ordering defect**

The accepted 06c interface requires:

1. W4 candidate-specific provider-capacity evaluation;
2. a recorded route decision;
3. W7 selected-route revalidation of rendered hash, provider accounting,
   wrapper/system reserve, both token gates, policy, parity, and currentness;
4. only then issue.

That order is explicit at
`design/06c-gate3-foundation-critical-interface-manifest-2026-07-01.md:35-60`
and `:127-142`. 06j permits failure only from
`requested|compiling|compiled`, not from `validated`
(`implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:158-162`),
but does not pin `ValidateContextPacket` after the final W7 revalidation. If
the packet is validated before that revalidation and accounting/currentness
then fails, `FailContextPacket` is no longer a valid transition. W2 command
rejection cannot fill the gap: a rejected command writes no lifecycle event
and yields only an operational receipt
(`design/02-task-event-and-artifact-schema.md:255-280`).

**Concrete failure**

A compiled packet passes the W4 route capacity check. The packet is marked
validated. W7 then discovers incomplete wrapper accounting, capacity overflow,
rendered-hash drift, or stale currentness. The current seam raises before any
command submission. Replay retains a live validated packet and no
`ContextPacketFailed`, so the failure is silent at the canonical lifecycle
surface and retry/recovery cannot reconstruct it.

**Impact**

This is a replay and lifecycle-authority gap at the exact validation/issue seam
the latest remediation was meant to close. Passing schema tests or a negative
that exercises only `context/compiler.py` would not cover the reachable W4/W7
paths.

**Bounded required correction**

Revise 06j only far enough to:

1. inventory every production W4/W7 call site that consumes a compiled packet
   or performs provider-capacity, accounting, packet/manifest, security,
   independence, rendered-hash, parity, or currentness checks before issue;
2. require each failure path to invoke the W3 lifecycle service and submit
   `FailContextPacket`, or make the direct path structurally unreachable;
3. pin `ValidateContextPacket` after successful selected-route W7
   revalidation and before packet/provider issue, splitting the current
   coordinator seam if necessary so no fallible validation remains between
   validation and issue;
4. run provider-capacity, no-eligible-route, accounting-unavailable,
   wrapper-accounting missing/invalid/overflow, packet/manifest mismatch,
   rendered-hash drift, and currentness-drift negatives through the production
   seams; and
5. assert one attributable `ContextPacketFailed` in both genesis and
   incremental replay, with no issued/delivered state, plus idempotent retry.

No implementation or remediation was performed by this review.

## Latest-finding verification

### 1. Failure lifecycle

**Open**, for PR198-RR1 above. The abstract command, transition, and negative
control text is present, but the complete governed production path is not.

### 2. G-RM-10/G-RM-12 canonical materialization and load-time identity

**Closed at plan level.**

For G-RM-10:

- all five Stage A components are enumerated at
  `implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:50-60`;
- each has a canonical Stage B destination at `:91-100`;
- Stephen's decision record binds the policy registry, review rules, identity
  manifest, and interface by Git blob and canonical SHA-256 at `:74-89`;
- every canonical loader requires the exact accepted manifest and verifies
  each mapped file against its accepted candidate identity before
  registration/use at `:125-131`; and
- Stage B requires byte-for-byte materialization and explicit missing-component,
  manifest-substitution, candidate/canonical-divergence, and self-pinned-policy
  negatives at `:222-230`.

For G-RM-12:

- Stage A enumerates the catalogue addendum, nine command schemas, nine event
  schemas, three object schemas, transition table, authority scopes, and
  identity manifest at
  `implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:27-41`;
- canonical Stage B destinations cover every category at `:77-95`;
- the governing RM-00 gate defines the whole Stage A package as the exact
  accepted subject and requires exact candidate Git blobs/canonical hashes
  (`implementation/rm-00-research-methods-lane-master-plan.md:40-48,67-80`);
- every loader requires that accepted manifest identity and verifies catalogue,
  transition, authority, command/event, and object-schema bytes before
  registration/use at
  `implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:110-116`;
  and
- Stage B requires byte-for-byte materialization and rejects missing
  components, manifest substitution, and candidate/canonical divergence at
  `:191-198`.

Both Stage A manifests bind their leaves but do not accept themselves; the
independent review plus Stephen's exact gate record supplies the external
manifest identity. The future candidate directories and loaders do not yet
exist, as expected. This is acceptance of the plan's identity mechanism, not
runtime or candidate-byte acceptance.

## PR198-F1 through PR198-F5 regression matrix

| Finding | Current disposition | Exact-subject evidence |
|---|---|---|
| PR198-F1 — existing release consumer bypass | Closed | 06i identifies the existing `StoredReleasePublicationEvidence` and both release CLI paths (`06i:20-27,41-43`), maps them to `resolve_for_result` (`06i:179-188`), makes the direct-read inventory repository-wide (`06i:194-201`), specifies the two-phase migration (`06i:203-216`), and includes candidate/wrong-scope/stale/substitution/direct-fallback negatives (`06i:251-267`). |
| PR198-F2 — missing requested/compiling failure lifecycle | Closed | 06j defines all nine commands/events (`06j:52-68`), command-writes request and compiling before fallible work and failure from every pre-validation phase (`06j:127-143`), and requires requested/compiling/compiled/retry/genesis/incremental/never-requested controls (`06j:158-186,199-216`). PR198-RR1 is narrower: it concerns existing post-compilation W4/W7 call sites. |
| PR198-F3 — merge-order smoke hole | Closed | RM-01 inventories every family at final candidate head and fails on absence (`rm-01:124-138`), assigns all relative merge orders (`rm-01:140-148`), and includes an unmanifested-family negative (`rm-01:150-154`). The same second-to-merge rule appears in RM-00 (`rm-00:55-61`), 06i (`06i:276-283`), and 06j (`06j:225-233`). |
| PR198-F4 — circular exact-subject gates | Closed | 06i and 06j each split inert Stage A candidate authoring from separately gated Stage B implementation (`06i:48-89`; `06j:22-71`); RM-00 orders both stages and gates (`rm-00:40-61,67-80`). Later Worker outputs cannot become the owner decision subject. |
| PR198-F5 — candidate verification run cannot reach follow-up consumer | Closed | RM-04 keeps the run candidate until an eligible unrelated review and exact-scope G-RM-13 decision (`rm-04:19-31`), forbids RM-04 from writing its own review/use authority (`rm-04:34-48`), gates follow-up resolution (`rm-04:98-110`), and tests the complete external-review/owner-transition path while result/claim use remains blocked (`rm-04:128-148`). |

## Cross-cutting adversarial audit

| Attack | Disposition |
|---|---|
| Circular gate | No new circular gate found. Stage A produces inert bytes; independent review and the owner gate precede Stage B. |
| Self-attestation | No new accepted self-attestation found in the identity mechanisms. G-RM-10/G-RM-12 external gate records bind the future exact candidate; the manifests do not accept themselves. |
| Silent absence | One material instance remains: post-compilation W4/W7 failure can produce no W3 lifecycle event (PR198-RR1). |
| Replay gap | One material instance remains: the same failure can be absent from genesis and incremental context-packet replay (PR198-RR1). |
| Consumer bypass | Prior bypass remains closed by the 06i repository-wide boundary and concrete release/RM consumer migrations. |
| Merge-order hole | Prior smoke-manifest ordering hole remains closed by final-candidate inventory and second-to-merge ownership. |
| New unrelated plan regression | None found in 06h, RM-00 through RM-04, README, or the committed response/provenance files. |

## Identity and validation evidence

1. `git diff --check <base>..<subject>` passed.
2. A raw-Git-blob Markdown link resolver checked all 13 changed files:
   `MISSING_LINKS=0`.
3. Raw changed blobs contained no UTF-8 BOM and no CRLF bytes.
4. All ten Git blob identities recorded in the preceding rereview resolved
   against its exact subject `c99cec8051be634b00681e92022ebadc9cb66019`.
5. The rereview report's raw Git-blob SHA-256 is
   `c73ac88f2fb34dedefbe06dae690347443ced2303d4d957b43143d376aed9e1f`,
   matching its response record.
6. The PR198 pre-merge report's raw Git-blob SHA-256 is
   `cb54b4ceb05629237c9b5af3df0f3bc1b015b79c586ca6dd1d9b2bcde5824cdb`,
   matching its response record.
7. The focused existing WP6.1 catalogue/materialization slice passed:
   `3 passed in 33.40s`. These tests establish the current generated-schema
   substrate only; they do not establish the future G-RM-10/G-RM-12 candidate
   or lifecycle design.
8. A focused current context/routing slice passed 20 tests. The pass confirms
   the existing exception/failure-dictionary behavior; it does not create a
   `ContextPacketFailed` record and therefore is not acceptance evidence.
9. The read-only dynamic probes reproduced route-return and revalidation-raise
   paths with zero lifecycle command submissions.

One attempted focused-test bootstrap transiently created an ignored empty
`.venv` directory in the isolated review worktree before discovering that the
environment was unavailable there. It was removed immediately. No tracked
subject file or Git object was changed, and final status was clean. The
successful checks used the existing repository interpreter with bytecode,
cache, and coverage writes disabled.

## Residual risk and next action

The future G-RM-10/G-RM-12 candidate bytes, materializers, loaders, lifecycle
writer, and controls do not yet exist. Their owner gates remain open and must
bind their future exact subjects separately. That prospective risk is properly
gated.

The immediate merge blocker is narrower: revise the 06j plan to close
PR198-RR1 across the real W4/W7 production seams, then request a fresh
independent review of the new exact subject. Do not merge or infer owner
acceptance from plan prose, the focused test results, prior review responses,
or PR mergeability.
