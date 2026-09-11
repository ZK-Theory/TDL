# WP6 Gate 6 Phase 2 handoff — AUTHORITY and TASK

**Dispatch state:** ready for Stephen's explicit Phase 2 dispatch; do not begin
construction from this handoff alone.

**Recommended model:** `gpt-6-astra`

**Recommended thinking level:** `xhigh`

Phase 2 crosses inherited authority semantics, multi-actor decisions, Task
acceptance, replay and exact-retry behavior. `gpt-6-astra` at `xhigh` provides
the reasoning headroom for those contract boundaries while keeping the work
bounded. Reserve `max` for a separate final exact-head adversarial review if
the candidate's dependency surface warrants it.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 2 — AUTHORITY and TASK** in
`C:\Users\steph\TDL`.

Stephen has merged Phase 1 SOURCE PR #282. Start from a freshly fetched
`origin/main`, currently expected to contain merge commit
`3ce730d94402781767e7602660506e4b06cf8d68`; record the exact current SHA at
dispatch. Create one clean linked worktree and a `codex/` task branch, then
verify cwd, symbolic branch, HEAD, clean status and required ancestry before
any write. Preserve unrelated dirty files in the primary checkout.

Deliver the smallest integrated Phase 2 candidate covering **KAN-106
AUTHORITY** and **KAN-107 TASK** on the same public route. A single PR is
preferred unless a real dependency or review boundary requires a split.

### Required production outcome

Extend the existing Phase 1 public CLI/action-table path so that:

1. inherited authority records and existing expiry checks authorize each
   individual actor in a multi-actor action;
2. an authorized producer can submit a Task for review;
3. an independent reviewer can satisfy the review without self-review;
4. an owner-only decision can accept the Task after the required evidence; and
5. status and replay reconstruct the accepted state, while an exact retry reads
   the existing receipt and creates no new authoritative effects.

Use D2 and the existing governed contracts. Keep
`SpecOperatorConfig@1.0.0` authority-neutral (actor/session/grant IDs only).
Do not introduce session containment, a grant-expiry subsystem, a new Task
state, a parallel evaluator, or a bypass around Phase 1 validation. Supply
Task evidence through existing contracts on scratch stores only; historical
live closure is Phase 5.

### Decisive negatives

Prove rejection and no authoritative effect for self-review, non-owner
decisions, missing/unsatisfied `SubmitForReview` or `AcceptTask` evidence,
expired or otherwise unauthorized actors, and attempts to infer closure from
attempt completion, lease release or result presence alone. Check exact retry
and replay equality explicitly.

### Evidence and review boundary

Exercise the real public positive path first, then the decisive negatives and
shared-seam retry/replay regression. Run the focused Phase 2 tests, relevant
lint/format checks and mandatory hooks; retain exact commands and summaries.
Perform an independent exact-head semantic review before calling the candidate
ready. Resolve only current, evidenced findings. Stephen controls CodeRabbit,
protected merges and any later live/provider/paid operations.

### Hard boundaries

No live control-store writes, provider or paid calls, successor binding,
historical Task/ProjectUseDecision closure, Gate 7 work, or final Gate 6
closure. Do not create a replacement plan. If a required contract is missing,
implement the smallest compatible production seam and its regression within
this Phase 2 scope; do not defer a required capability gap to a comment or
handoff.

At completion report the exact worktree, branch, base and candidate SHAs, file
scope, real-path evidence, negative controls, review identity, and the precise
remaining Gate 6 gap. The capability remains **INCOMPLETE** until Phases 3–5,
final review and Stephen's closure decision are complete.
