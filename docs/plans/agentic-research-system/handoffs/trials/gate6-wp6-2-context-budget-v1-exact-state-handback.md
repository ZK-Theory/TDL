# Gate 6 / WP6.2 context-budget trial exact-state handback

## Trial termination

- Trial: `gate6-wp6-2-context-budget-v1`.
- Snapshot: `2026-07-22T13:44:43.7127962+01:00`, after refreshing the relevant `origin` refs.
- Lifecycle phase reached: integration and owner-state reconstruction; implementation preparation began but no T2 dispatch occurred.
- Termination condition: the first automatic Manager context compaction. This is the trial's explicit rotation trigger, so the Manager stopped before creating a branch, worktree, Worker, reviewer, or implementation change.
- Approximate context at rotation: approximately the declared 80,000-live-input-token envelope; the runtime exposed the compaction event but no exact token counter.

## Exact repository identities

- Manager worktree: `C:\Users\steph\.codex\worktrees\9333\TDL`.
- Manager branch: detached `HEAD` (read-only coordination checkout).
- `HEAD` and refreshed `origin/main`: `efcecd8669fb225061c6eaf300e31bc07d352f6e`.
- Experimental instruction commit: `e728d5117e626590adb6de4fbd4657db9d178125`.
- Refreshed `origin/codex/wp6-manager-efficiency-instructions`: `2c7d199b642f406ee3ed380b90fbe536aaac6e22`.
- The handoff 08 and proposal at `e728d5` governed this trial only; they were not treated as permanent conventions or a new gate.
- Worktree was clean before this untracked planning handback was written. No existing tracked file, branch, commit, PR, or remote state was changed.

## WP6.1 integration and Gate 6 state

The complete WP6.1 stack is integrated on `origin/main` in order:

| PR | Exact head | Merge commit | Exact base relationship |
|---|---|---|---|
| #153 | `897eb191ec2fcc5e510d8f9503e71628e6841d9b` | `f032c0d0119dff433ea3029dbfbc03b52d7d4324` | based on `4d6f480`; merged first |
| #154 | `3ec14ebd7403825a0eba7776f54ed9811f77f7d2` | `a876eaa886411dc88faae59c33f22e298a8e74e1` | based on #153 merge |
| #155 | `b57f9466c89244697f070266da19a0a0ace8906e` | `efcecd8669fb225061c6eaf300e31bc07d352f6e` | based on #154 merge; current main |

Ancestry is `897eb19 -> 3ec14eb -> b57f946 -> origin/main`. Each merge tree equals its PR-head tree, so integration introduced no conflict-resolution byte drift. The accepted WP6.1 scope is byte-identical on current main even though the accepted proposal/review subjects are not ancestors:

- commands tree: `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` (87 entries);
- events tree: `154ffc4bdde82fe903718734687e7a62797b1f69` (86 entries);
- core tree: `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` (173 entries);
- Stage-2 owner-acceptance record: blob `f1b73c729ed05c3bfdfcd50e0a916fa9fc70fff5`, SHA-256 `093d02bfbac5e6012c5f149abcf5b449a573863411f124fdcef928af79518ec4`;
- Stage-2 strict schema: blob `fac31545f7e90d7025ede973bbd39d8de4941c20`, SHA-256 `708d2ec8a1d7fab8a15650814a9bf7318328a62a1f8f70c90c2659b9f2b23c2a`;
- R11 review: commit `2f701c3b0f8b2ba3423c9ba07e0c5ce7a2813813`, report blob `496ff39639d405b50483d197858b1519e83270c8`, verdict `accept` with 0 Critical / 0 Major / 0 Minor.

This remains `accepted_exact_bytes_only`. The authoritative record still has `implementation_start_authorized: false`, `further_gate_6_transition_authorized: false`, and `separate_owner_authorization_required: true`. The merged stack supplies schemas, contracts, validators, and test seams; it does not prove or authorize WP6.1 runtime T1-T8, A4/A5, or a further Gate 6 transition.

Re-evaluated master exit checklist:

- Proven closed: rows 1, 2, 4, 5, 15, and 16.
- Open: rows 3, 6, 7, 9, 10, 12, and 13.
- No current closing record proved in this trial: rows 8, 11, and 14.

Row 2 is closed by the exact external T1a owner record below even though the repository checklist box and candidate-state fields remain stale. No other unchecked row was promoted from merge status alone.

## WP6.2 sole DAG and T1a certification

The sole authorized DAG is:

`T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8`

T3 and T4 may run in parallel only after T2. T1b requires both. Accepted T1b then gates serial T5-T8 and all M/H transitions.

T1a is proved owner-accepted and merged:

- exact subject: `599050b0809ed63a69e1a9ce6ac491b61f7ad33e`;
- protocol path: `.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml`;
- protocol blob: `4c9721a047c9b66912b9786a3b983c6f84e5ab00`;
- protocol canonical UTF-8/LF SHA-256: `e9512bef147d0de9bc9103b20eb1ede8b927979bfe43dd85e61fb6c27f05efda`;
- identity-manifest path: `.research-system/contracts/wp6-2-live-grader-calibration-protocol-identity-manifest.yaml`;
- identity-manifest blob: `47d87f27d802530f4f8ec92146ef6f7fca3d3c2f`;
- identity-manifest SHA-256: `5cfa7f20cdc3e5955377b894f7dc7ff9e2062001a6f56a647f2299554cb16ca4`;
- required-slot hash: `e8acc4ff5e068b1318c0de84e3b7329b211eb9c35f46a5d0c5cba040f59a513f`;
- execution-freeze hash: `5daa95e625b6df51cf7779c053adc8b945a6bd8db6e0aae5100e2587454e489b`;
- independent final R4: task `019f771a-f00b-7f31-9f60-3974f8f9e5ca`, exact subject `599050b`, verdict `accept`, 0 Critical / 0 Major / 2 Minor;
- R4 archive: `C:\Users\steph\.codex\sessions\2026\07\18\rollout-2026-07-18T18-51-09-019f765a-6903-7401-b103-e7a51aa2ee14.jsonl` (review result at line 2525); no repository report was intentionally created;
- Stephen's distinct exact-revision acceptance: GitHub owner comment `5013060835`, 2026-07-18T21:51:17Z, accepting `599050b` as-is: <https://github.com/stephendor/TDL/pull/122#issuecomment-5013060835>;
- PR #122 merge: `e68a7c3d393782cb900154d7fb399a7deab8e275`, 47 seconds after acceptance.

The owner comment predates and is distinct from the merge. Its exact commit-to-blob-to-canonical-hash chain proves the T1a protocol identity. Current `pending` candidate fields and the unchecked master box are stale candidate snapshots, not contrary lifecycle authority. There is no machine-readable T1a owner-acceptance file in the repository; external owner and archived independent-review records therefore remain required provenance.

T1a acceptance grants T2, then T3/T4 according to the DAG. It grants no live grading, T1b, T5-T8, M/H eligibility, publication, or claim authority.

## One next vertical deliverable

The sole next deliverable is WP6.2 T2: the typed credential and cost pre-issue boundary. It was selected but not dispatched because rotation occurred first.

Required T2 surface:

- opaque, byte-free `SecretReference` plus provider/credential class, resolver identity/version, allowed scope, expiry, and redaction proof;
- resolved use bound to exact Task/dispatch/attempt, route/profile, adapter revision, and `ProviderCommand`;
- `CostGrant` bound to the same identities, rate evidence, token and microunit ceilings, reservation/consumption/refund, expiry, and idempotency;
- one project writer atomically reserves before invocation and reconciles actuals afterward;
- the complete pre-issue negative matrix fails closed with a unique sentinel, zero provider invocation, and byte-identical canonical stores; a typed non-secret rejection may be returned but not canonically published.

Hard exclusions: T3, T4, any live provider call, T1b, T5-T8, eligibility transitions, results or claims, Gate 5 mutation, research computation, third-family providers, autonomous downgrade/cost optimization, secret bytes on any context/provider/canonical surface, and S-016 changes.

Next Manager action:

1. Refresh `origin/main` and require base `efcecd8669fb225061c6eaf300e31bc07d352f6e` unless a newer main is explicitly reconciled.
2. Preflight current contracts and implementation seams, then set exact allowed and forbidden paths. Do not dispatch with path scope unresolved.
3. Pre-create one unique T2 branch, suggested `pipe/ars-wp6-2-credential-cost-boundary`, at the reconciled base and dispatch into an exact authorized linked-worktree root. No branch or worktree currently exists.
4. Use a fresh, self-contained Worker with `fork_turns: none`, primary skills `schema-contract-design` and `contract-first-tdd`, plus conditional `tda-agent-safety-guardrails` because credential/cost pre-invocation failure boundaries are security-sensitive.
5. Require focused negative-matrix validation and candidate-head package/contract validation. Then dispatch a separate fresh independent reviewer with `fork_turns: none`; permit at most one author-review-remediation cycle.
6. Stop after T2. Stephen alone operates CodeRabbit and owns external review/acceptance.

## Trial measurements

- Manager context: fresh; automatic compactions: 1; rotation at first compaction, approximately 80,000 live input tokens, exact telemetry unavailable.
- Read-only state explorers: 2, both fresh/self-contained with `fork_turns: none`; they were not implementation Workers or independent deliverable reviewers.
- T2 Workers/reviewers: 0/0; no active delegated agent or write ownership remains.
- Manager primary skills: 2 (`apm-2-initiate-manager`, `tda-task-brief-from-plan`).
- Post-selection skills: 3. `schema-contract-design` fired for typed machine-readable authority and identity binding; `contract-first-tdd` fired for the consumed pre-issue boundary and negative matrix; `tda-agent-safety-guardrails` fired conditionally for credential/cost fail-closed controls.
- Existing-artifact certification: WP6.1 accepted bytes and T1a were certified from Git objects, live owner/PR records, and the archived final review; neither was regenerated.
- New-deliverable validation: focused 0, package/contract 0, full 0 because T2 was not dispatched. Historical T1a R4 evidence was 58/58 focused, 101/101 contract with pytest, 101/101 contract without pytest, and 2/2 outside-cwd checks; it was certified, not rerun.
- Author-review-remediation cycles: 0.
- External-review waits inside Manager: 0. No CodeRabbit trigger, poll, wait, schedule, or automation occurred.
- Reads required: exact `e728d5` handoff/proposal; current WP6 master, WP6.1/WP6.2 child plans and authority annexes; exact dispatch/review guidance; GitHub PR/owner metadata; the exact archived R4 result.
- Repeated reads avoided: the unrelated foreign `.apm` P01 revision lane after its identity was established; unrelated historical review chains; full observation logs beyond matching OPEN entries; regeneration of already content-addressed artifacts.
- Stale-state decisions corrected: the older handoff snapshot's open PR #153-#155 state; the unchecked T1a checklist/candidate fields. Merge alone was never treated as owner acceptance.
- Dropped requirements: none. False stops: none. Assurance weakening: none. Rotation deliberately prevented dispatch before an exact path-scoped brief could be completed.

## Do not do / files to reload

Do not infer runtime or transition authority from merged contracts; do not regenerate T1a; do not reopen the sole DAG; do not combine T2 with T3/T4 or a live call; do not use the foreign `.apm` tracker; do not let the Manager own an external-review wait.

The next fresh Manager must read:

- `AGENTS.md`;
- `git show e728d5117e626590adb6de4fbd4657db9d178125:docs/plans/agentic-research-system/handoffs/08-wp6-context-budgeted-manager-handoff-prompt.md`;
- `git show e728d5117e626590adb6de4fbd4657db9d178125:docs/plans/agentic-research-system/proposals/large-workflow-context-budget-and-orchestration-protocol-2026-07-22.md`;
- `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md`;
- `docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md`;
- `docs/plans/agentic-research-system/implementation/06f-wp6-2-p1-activation-contract.md`;
- `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` for P-035/P-036;
- `.research-system/contracts/wp6-2-live-grader-calibration-protocol-identity-manifest.yaml`;
- this handback.
