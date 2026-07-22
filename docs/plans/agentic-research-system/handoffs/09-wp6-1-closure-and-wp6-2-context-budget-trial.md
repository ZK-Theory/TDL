# WP6.1 Closure and WP6.2 Context-Budget Trial Handoff

**Created:** 2026-07-22
**Status:** Experimental handoff on `codex/wp6-manager-efficiency-instructions`
**Purpose:** Close the existing WP6.1 review stack without importing its accumulated
context into the first context-budgeted Manager trial, then trial the proposed method
on WP6.2 and return an exact-state handback for assessment.

This runbook deliberately uses two fresh tasks. WP6.1 closure is not part of the
efficiency trial. The trial begins only after all three WP6.1 layers are proven present
on `origin/main`.

## Fixed sequence

1. Run **Prompt A** in a task rooted at the PR155 owning worktree.
2. Stephen supplies the current unanswered PR155 CodeRabbit findings. No agent
   requests, triggers, polls, waits on, or schedules CodeRabbit.
3. After the valid current findings are addressed and validation passes, merge the
   stack using the base-retarget procedure in Prompt A.
4. Start a completely fresh Manager task and run **Prompt B**. Do not continue the
   WP6.1 closure task.
5. When the trial reaches its bounded end or rotation trigger, return its handback to
   this instruction-design task and use **Prompt C** for assessment.
6. Integrate only the method changes Stephen approves after assessment.

## Prompt A — close PR155 and integrate the WP6.1 stack

Paste into a fresh task whose exact writable root owns
`codex/wp6-1-review-3-contracts`. Include the current unanswered PR155 CodeRabbit
finding bodies or thread URLs with the prompt.

```text
Close the existing WP6.1 three-PR stack. This is a narrow remediation and integration
task, not the context-budget trial.

Authority granted in this prompt:
- Address the current PR155 CodeRabbit findings supplied by Stephen, and only those
  findings, against their exact current head.
- No second review is required for PR153 or PR154.
- Do not request, trigger, poll, wait on, or schedule CodeRabbit. No new CodeRabbit run
  is required unless Stephen explicitly asks in this task.
- Once every supplied valid current PR155 finding is fixed or dispositioned with
  evidence, all required validation is green, and the reviewed deltas remain intact,
  Stephen authorizes PR153, PR154, and PR155 to be marked ready where necessary and
  merged into main in the safe order below.

Verified 2026-07-22 snapshot to re-fetch before acting:
- PR153: base main; head codex/wp6-1-review-1-commands at
  897eb191ec2fcc5e510d8f9503e71628e6841d9b; draft; mergeable.
- PR154: base codex/wp6-1-review-1-commands; head
  codex/wp6-1-review-2-events at
  3ec14ebd7403825a0eba7776f54ed9811f77f7d2; draft; mergeable.
- PR155: base codex/wp6-1-review-2-events; head
  codex/wp6-1-review-3-contracts at
  7d612284b18db69d2b301e5a00a03f275b757bed; ready; mergeable.

Before any write:
1. Invoke research-observer and load only the one or two skills needed for the
   supplied finding classes.
2. Verify cwd, exact writable root, symbolic branch, HEAD, status, upstream, and PR155
   ownership. A foreign Manager may inspect but must route edits to this exact root.
3. Fetch origin. Re-record all three PR bases, heads, states, checks, and stack
   ancestry. A head mismatch makes the snapshot stale; rebind each finding before
   editing.
4. Prove that the immutable WP6.1 command, event, and core schema trees and accepted
   R11/owner-acceptance identities still match their accepted bytes. Do not regenerate
   or reformat accepted artifacts.

Remediation:
1. Classify each supplied PR155 finding as current-valid, current-invalid, already
   fixed, or stale, with exact path/line and authority evidence.
2. Make the smallest fix for current-valid findings only. Preserve existing branch,
   PR, accepted artifacts, and scope.
3. Run focused tests while editing, then the affected contract/package gates, Ruff or
   format checks for touched code, pre-commit hooks, and git diff --check at candidate
   head. Rerun any test changed by hook formatting.
4. Commit with the permitted repository research prefix and push the same PR155
   branch. Reply to and resolve only the supplied threads whose disposition is now
   evidenced. Do not search for or poll for additional bot findings.

Stack integration invariant:
1. Confirm PR155 has no unresolved supplied finding, all required checks are green,
   and the three reviewed layer deltas are still exact.
2. Mark PR153 ready if required and merge PR153 into main using the repository's
   established merge method. Fetch origin/main and prove the PR153 layer is reachable.
3. Retarget PR154 to main before merging it. Verify that its resulting diff is exactly
   the reviewed event-layer delta, with no dropped or newly introduced semantic path.
   Mark ready if required, merge, fetch, and prove the PR154 layer is reachable from
   origin/main.
4. Retarget PR155 to main before merging it. Verify that its resulting diff is exactly
   the reviewed contracts/evidence layer plus the approved PR155 remediations. Merge,
   fetch, and prove the final PR155 head or equivalent reviewed commits and all accepted
   immutable trees are reachable from origin/main.
5. Do not merge PR154 or PR155 while its base is still an intermediate stack branch.
   Mergeability against that branch is not evidence that the layer reached main.

Stop and ask Stephen if any supplied finding requests an accepted-byte change; a PR
head, ancestry, accepted identity, or reviewed delta cannot be proven; retargeting
changes scope; conflicts appear; required validation fails; or the established merge
method would rewrite or omit reviewed content.

Hand back: final main SHA, each PR's merge commit/state, exact paths changed for PR155,
finding dispositions, validation commands/counts, accepted-tree identity proof, and
any residual risk. Do not begin WP6.2 in this task.
```

## Prompt B — run the first context-budgeted trial on WP6.2

Start this only after Prompt A proves all three WP6.1 layers are on `origin/main`.
Create a fresh Manager task from the updated main line. Do not fork or continue the
WP6.1 closure conversation.

```text
Run trial `gate6-wp6-2-context-budget-v1` as a fresh coordinating Manager for WP6.2.
The trial is governed by the experimental instructions at exact commit
e728d5117e626590adb6de4fbd4657db9d178125 on branch
origin/codex/wp6-manager-efficiency-instructions, especially:
- docs/plans/agentic-research-system/handoffs/08-wp6-context-budgeted-manager-handoff-prompt.md
- docs/plans/agentic-research-system/proposals/large-workflow-context-budget-and-orchestration-protocol-2026-07-22.md

Read those files with `git show` from that exact commit if they are not present on the
updated main checkout. Treat the proposal as trial instructions, not yet a permanent
convention or gate.

Trial envelope:
  lifecycle_phase: integrate_then_prepare_implementation
  context_mode: fresh
  context_budget_tokens: 80000
  fork_turns: none for self-contained Workers and every independent reviewer
  primary_skills: [apm-2-initiate-manager, tda-task-brief-from-plan]
  conditional_skills: select only after the exact first deliverable is known
  external_review_owner: stephen
  author_review_cycle: 1
  rotation_trigger: first auto-compaction or approximately 80000 live input tokens

Scope:
1. Reconstruct the post-WP6.1 exact state from origin/main and authoritative repository
   and owner records. Do not trust this prompt as current state.
2. Confirm WP6.1 stack integration and re-evaluate the Gate 6/WP6 exit checklist.
3. Reconstruct WP6.2's sole DAG exactly:
   T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8.
4. Verify the merged T1a artifact, its independent review, and Stephen's distinct exact
   protocol-hash acceptance. Merge status is not owner acceptance.
5. If the exact T1a owner-acceptance record is absent or unproven, produce one compact
   acceptance packet naming the exact subject/path/blob/canonical hash, review identity,
   open decision, and downstream authority that acceptance would grant. Stop for
   Stephen; do not implement T2.
6. If and only if T1a acceptance is proven or Stephen records it in this task, select
   one next vertical deliverable. The default is WP6.2 T2, the typed credential and cost
   pre-issue boundary. Do not include T3, T4, a live provider call, T1b, or later work.
7. Dispatch that deliverable using a self-contained brief with exact base/subject,
   branch, writable root, allowed/forbidden paths, at most two primary skills, focused
   and candidate-head validation, one author-review-remediation cycle, and hard stops.
8. Stephen alone operates CodeRabbit. Do not trigger, poll, wait on, or schedule it.

Trial measurements to retain in the handback:
- Manager compactions and approximate context at rotation;
- every Worker/reviewer context mode and fork-turn value;
- primary and conditional skill counts and why each conditional skill fired;
- repeated plan/report reads avoided or required;
- existing artifact certification versus regeneration;
- focused, package/contract, and full validation counts;
- author-review-remediation cycles;
- external-review waits kept outside the Manager;
- any dropped requirement, false stop, stale-state decision, or assurance weakening;
- exact final branch/head/worktree, owner gates, validation evidence, and next action.

End the trial after one completed vertical deliverable and at most one remediation
cycle, or earlier at the rotation trigger or a genuine owner gate. Write the compact
exact-state handback required by handoff 08. Do not start a second WP6.2 deliverable.
```

## Prompt C — assess the trial here

Return to this instruction-design task with the complete Prompt B handback, then use:

```text
Assess trial gate6-wp6-2-context-budget-v1 against the experimental protocol. Do not
activate or merge broader workflow rules before reporting the evidence.

Compare the trial with the recent WP5/WP6 pattern on: compactions/context size, context
inheritance, skills loaded, duplicated reads/generation, validation repetition,
review/remediation cycles, external-review waiting, exact-state recovery, dropped
requirements, false stops, and assurance defects. Separate measured evidence from
inference and from unavailable telemetry.

Return one verdict:
1. revise_and_retrial — specify the smallest instruction changes and the next bounded
   trial;
2. approve_advisory_integration — specify exact AGENTS/skill/guide edits, but keep the
   checker and CONVENTIONS lock deferred;
3. reject — explain why the method did not earn integration.

For verdict 2, prepare a normal reviewed repo change from the authoring skill sources,
run both skill-sync checks and guide checks, and retain negative-control design for a
later enforcement task. Only after a second successful large-workflow use should we
decide whether to make the dispatch checker mandatory and lock the protocol in
CONVENTIONS.md.
```

## Recommended integration ladder

- **Now:** keep this branch experimental and use the prompts by exact commit or paste.
- **After trial 1:** assess here, revise if necessary, and ask Stephen to approve the
  resulting advisory rules.
- **Advisory integration:** merge approved documentation, `AGENTS.md`, APM skill, task
  brief, and guide changes through a normal reviewed PR with skill-sync validation.
- **After trial 2:** decide separately whether evidence justifies the strict dispatch
  checker, its negative controls, and a `CONVENTIONS.md` lock.
