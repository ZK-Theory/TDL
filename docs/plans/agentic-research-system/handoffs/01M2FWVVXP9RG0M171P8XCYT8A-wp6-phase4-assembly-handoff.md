# WP6 Gate 6 Phase 4 handoff — remaining branches and assembled proof

**Capability status:** INCOMPLETE — the historical real SPEC run is PROVEN; the
complete public Gate 6 implementation is not integrated on main. STORE, Phase 1
SOURCE, Phase 2 AUTHORITY/TASK and Phase 3 RESULT are integrated. Phase 4, Phase 5,
the final independent evidence review and Stephen's closure remain.

**Dispatch state:** ready for Stephen's explicit Phase 4 dispatch. Do not begin
construction from this handoff alone. The first deliverable is a scope table for
Stephen, not code.

**Recommended model:** the strongest available reasoning model, at `xhigh`.
Phase 4 composes many existing W11 rows onto the public route. Most of the
difficulty is in scope and in binding evidence, not in volume. Keep a separate
fresh-context model for the exact-main boundary review.

**Predecessor:** Phase 3 handoff
`handoffs/01M2EJ8RGJ66MZYYD3RCWM08QG-wp6-phase3-result-handoff.md`. Phase 3 was
delivered through PR #288, merged at `3f3de7b5cf9a743b1fe920324e2d73a91479eae7`
under decision P-057.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 4: remaining branches and
assembled proof**, Jira **KAN-109**, in `C:\Users\steph\TDL`.

### Start identity

Stephen has merged Phase 3 PR #288. Refresh `origin/main`. It must contain
`3f3de7b5cf9a743b1fe920324e2d73a91479eae7`, and it may also contain the Phase 3
close-out docs PR that added this file. Record the exact SHA before the first
write.

Create one clean linked worktree under `C:/Users/steph/` on a `codex/` branch, and
copy the primary checkout's `.env` into it. Before any write, verify:
- the working directory;
- the symbolic branch and HEAD;
- a clean status;
- ancestry from the recorded SHA.

Preserve unrelated dirty files in the primary checkout.

### Read first

1. `docs/plans/agentic-research-system/implementation/06s-gate6-delivery-replan-and-gate7-integration.md`:
   §§3–5.0, **Phase 4**, the Phase 2 and Phase 3 status blocks, §8, §9 and §11.
2. `docs/plans/agentic-research-system/implementation/06q-gate6-spec-real-run-integration-and-follow-up.md`
   §4 **Step 5**, the table of 30 canonical actions. It is retained only as the
   action composition. 06s D1 removes its registry, seals, blob-hash bindings and
   frozen-catalogue ceremony.
3. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`:
   **P-050** and **P-051–P-057**.
4. The production surface you extend rather than duplicate:
   - `research_system/discovery/spec.py`:
     - `ACTION_EFFECTS`;
     - `SpecCoordinator.status`, `advance` and `result`;
     - the per-action `_advance_*` methods and `_submit_effect`;
     - `_DocumentRegistrationService` and `_REGISTRATION_SERVICES`.
   - `research_system/discovery/spec_task.py`, `spec_result.py` and
     `spec_source.py`.
   - `research_system/discovery/runtime.py` and `routes.py`, the W11 rows.
   - `research_system/operations/backups.py::verify_restore_before_writer_lease`.
5. The tests and fixtures you reuse:
   - `tests/research_system/integration/test_spec_result.py`: `bound_result`,
     `_governed_discovery`, which issues each W11 row its exact scoped grant, and
     `_park_candidate`, which drives OR-003/004/034/006/012/013 to an owner PARK.
   - `test_spec_task.py`, for the bound Task and CLI helpers.
   - `test_spec_source.py`, for `bind_scratch_route`.
   - `test_wp6_6_discovery_runtime.py`, for `_command`, `_accept_assay_bar`,
     `_scorecard` and `_promotion_relation`, plus the row sequences in
     `test_assay_partial_review_revisit_and_retry_run_through_public_seam`
     (OR-009/010/011) and
     `test_spike_positive_lifecycle_reaches_reviewed_atomically_and_without_provider_execution`
     (OR-014 onward).
6. PR #288's description: review rounds 1–2 and known limits 1–9.

### Verified state at `3f3de7b5` (confirm on your selected SHA)

- `ACTION_EFFECTS` holds five actions: `observe_source`, `correct_spec_01_source`,
  `close_task`, `register_project_use_decision` and
  `accept_project_use_decision`.
- `DiscoveryRuntime` already routes the W11 Discovery rows that SPEC-01 and SPEC-02
  compose, including:
  - revisit (OR-009) and the revisit decision (OR-010);
  - retry (OR-011) and the Assay decision (OR-012/013);
  - spike planning and start (OR-014–017);
  - spike returns, reviews and decision (OR-018–027);
  - the review requests (OR-034–037).

  None of these is on the SPEC route yet, except OR-029 inside `observe_source`.
- Outside `docs/`, no schema, writer or reader exists for
  `ars://portfolio/spec-02-live-run-approval`, `spec-operator-brief-package`,
  `spec-operator-return` or `spec-01-brief-input-set`. If the required list keeps
  those records, they are tooling to build.
- No `SpecActionIntent` type exists. Each route action validates its own closed
  intent schema (`spec-task-intent`, `spec-project-use-intent`).

### First deliverable: a scope decision for Stephen (before construction)

06q Step 5 names 30 actions. Four are delivered: `observe_source`,
`correct_spec_01_source`, `register_project_use_decision` and
`accept_project_use_decision`. `close_task` is the Phase 2 action from 06q Step 4
and is not one of the 30. The remaining 26 include:
- four `bootstrap_*` authority actions and `admit_dossier`;
- `request_spec_01`, the three `*_spec_01_brief_inputs` actions and
  `prepare_spec_01`;
- the complete and partial return and review pairs, and `decide_spec_01`;
- revisit, retry and PROMOTE;
- `approve_`, `prepare_`, `start_`, `return_`, `review_` and `decide_spec_02`.

06s D1 requires completing "the required list" by Phase 4. D6 makes a legitimate
PARK/no_spike sufficient and fresh SPEC-02 optional. P-057 removed historical
closure. Nothing records which of the 26 the Phase 5 fresh run needs, which only
the scratch revisit/retry/PROMOTE/SPEC-02 proof needs, and which are covered by
existing bootstrap helpers. A literal reading almost certainly exceeds the §5.0
checkpoint of 20 files and 2,500 added lines in one PR.

Build a short action-by-action table with these columns:
- canonical action;
- W11 rows or artefact effects;
- whether the fresh Phase 5 PARK/no_spike run needs it;
- whether only the scratch PROMOTE/SPEC-02 proof needs it;
- the existing runtime route and test helper;
- whether a new closed record is needed;
- a first measurement of what admission leaves unchecked.

Propose a delivery split, for example:
- 4a: the SPEC-01 sequence and terminal PARK/no_spike closure, ending in an
  accepted project-use result;
- 4b: revisit, retry, PROMOTE, SPEC-02 approval and the SPEC-02 sequence on
  scratch;
- 4c: the assembled exact-main selection and independent review.

Bring the table and the split to Stephen and let him decide inclusion and
sequencing. **Do not decide scope yourself.** Phase 3 had to stop and re-scope
mid-design because a conflict in its brief only surfaced during binding design.

**Outcome (2026-09-14):** Stephen decided this scope and its split as P-058, on
PR #290. That decision, not this section, now governs Phase 4 scope, including
how the §5.0 checkpoint applies to sub-phases.

### Measure before you build

For every W11 row or artefact effect the route will drive, measure on a scratch
store what admission checks and what it leaves unchecked:
- actor class;
- grant scope;
- subject identity;
- evidence fields and refs;
- the relation to earlier aggregates.

Take each pair of measurements at an identical state, so the actor or field is the
only difference. Phase 3 measured that:
- RegisterArtefact does not bind the manifest's producer, Task or content bytes;
- RecordScientificReview accepts the producer's own review;
- review evidence refs are not checked until use authority.

Expect similar gaps. Every field admission leaves unchecked must be bound by the
route. If an outcome can only be met by widening inherited authority or adding a
parallel policy, stop and bring the measurement to Stephen (D2).

### Required production outcome (06s Phase 4)

- **Scope.** Complete the approved remaining actions on the same action table,
  evaluator and public CLI, then verify the assembled route.
- **Reuse.** Use `DiscoveryRuntime.submit`, `CommandService.submit`,
  `replay_discovery` and `verify_restore_before_writer_lease`. The system derives
  IDs, envelopes and retry keys. There is no new persisted model or composite
  seal.
- **SPEC-02 gate.** SPEC-02 needs a valid PROMOTE plus its own separate approval.
- **After PARK.** The objective revisit predicate must be satisfied first. Then
  run `request_spec_01_revisit` → `authorize_spec_01_retry` (the owner selects
  RETRY) → `request_spec_01_retry` → a new Assay → a later PROMOTE.
- **Approval.** An approval alone never changes Candidate state.
- **Provider work.** It is operator-mediated. Construction never launches it and
  never fabricates provider, return or spike receipts. `return_*` actions
  register operator-supplied bytes.

### Initial packet (06s Phase 4)

**Positives:**
- the public SPEC-01 sequence and terminal PARK/no_spike closure;
- scratch revisit, retry and PROMOTE;
- the separately approved SPEC-02 sequence;
- exact Task and result closure.

**Negatives and controls:**
- wrong role;
- missing revisit or missing approval;
- conflicting concurrent advance;
- prepare and publication crash controls, with idempotent recovery and replay.

Run the real public positive path first, then the negatives, then the Phase 1–3
regression packet:
- `unit/test_spec_operator_config.py`;
- `integration/test_spec_source.py`;
- `integration/test_spec_task.py`;
- `integration/test_spec_result.py`.

### Assembly after construction merges

Run one bounded assembled selection on exact main:
- the Phase 0 STORE packet (the command in 06s §12);
- the Phase 1–4 packets;
- the CI `contract-and-session-currency` pytest list.

Then obtain one fresh-context independent exact-main boundary review before
proposing the live successor binding. This is assembly evidence, not Gate 6
closure. Report it with the §8 row "Assembled code integrated and passing".

### Carry forward from Phases 2–3 (do not re-derive)

**Evidence and retries**
- **Evaluate only evidence the route issued.** Evidence counts only if it passes
  identity (the route's own retry key), content (its payload equals what one
  build-and-verify function derives at that ledger position) and exclusivity
  (nothing else is on the action's streams).
- **Every input to a retry key must be recoverable from the recorded event.** Use
  `key_intent`; free-text `reason` is not recorded.
- **Take state, command and expected stream version from one ledger snapshot.**
  Answer exact retries from the stored receipt. Never resubmit.

**Refusals**
- **Put every refusal before the first durable mutation.** Sometimes admission
  would record an effect that a later effect must reject. In that case, run the
  inherited rule over the prospective effect before recording it; do not copy the
  rule. See `SpecCoordinator._check_review_evidence`, which calls
  `CommandService._validate_governing_review_evidence`.

**Documents and inputs**
- **Publish document bytes through a `_DocumentRegistrationService` subclass that
  names its object kind literally.** The 06i storage-boundary AST contract
  rejects variable kinds. Register the subclass in `_REGISTRATION_SERVICES`, and
  reuse orphaned bytes only when they re-derive exactly.
- **Verify cited bytes, not just ledger references.** Include derived inputs by
  their current replayed use authority, not by any past acceptance.

**Known limits you inherit**
- From PR #286:
  - a late SubmitForReview retry collides with AcceptTask;
  - the cross-stream race;
  - no rework path for failed or partial work.
- From PR #288:
  1. re-derivation cost, about 15 minutes for the scratch positive path;
  2. identical-content candidates are refused;
  3. the Spike branch and source corrections are tested at function level only.
     Phase 4's scratch Spike sequence should exercise the Spike branch of
     `spike_record` through the public path.
  4. artefact-level producer independence is route-enforced;
  5. orphaned bytes that bind another intent block that Task's registration;
  6. a registered decision keeps the sources of its causal prefix;
  7. manifest `input_dependencies` is empty.
     **Include this fix in your first push that changes `spec_result.py`:**
     derive `input_dependencies` from the `sources` and `evidence` references
     (Stephen's round-2 decision).

### Hard boundaries

- **No live or paid work.** No live control-store operations
  (`C:/Users/steph/TDL-ARS-WP64-Control`), provider or paid calls, credential use,
  successor binding, live SPEC-01/02 run, Gate 7 work, or final Gate 6 closure.
  Scratch stores only.
- **Scratch-only PROMOTE.** PROMOTE and SPEC-02 approval exist only on scratch
  stores in tests. Never manufacture a PROMOTE or rerun to force a gate.
- **No new machinery.** No new plan, framework, persisted workflow model,
  composite seal or speculative STORE change (D5). No replacement of
  `SpecOperatorConfig@1.0.0`.
- **No toy output.** Do not write toy or synthetic output into `results/`.
- **Owner controls.** Never bypass pre-commit hooks. Stephen controls CodeRabbit,
  merges and auto-merge. Do not trigger or poll CodeRabbit, merge, or enable
  auto-merge.
- **Scope checkpoint (06s §5.0).** 20 changed files, 2,500 added non-generated
  lines, or more than one session plus one follow-up requires Stephen's
  continuation decision. This applies to each approved sub-phase.

### Review process — advice from Phases 2–3

Phase 2 took six Codex rounds with 5, 8, 6, 4, 4 and 1 findings. Phase 3 took two
rounds: 6 comments (5 distinct issues, all fixed), then 2 (1 declined, 1 recorded
as a known limit, no push).

1. **Codex reviews every push automatically.** Batch fixes, and push only a tree
   whose full focused packet has passed.
2. **Verify each finding against the code before acting.** Several findings
   describe states that inherited admission already prevents. Cite the admission
   lines and decline them.
3. **A second material round needs Stephen's decision** (§5.0). Give him a short
   table: finding, verified?, assessment, recommendation.
4. **Treat a reviewer's suggested fix as a hypothesis.** Re-run the public positive
   path after every change.
5. **Prove each new control is decisive.** In a throwaway detached worktree at the
   candidate SHA, revert only that fix, run the control, and confirm it fails for
   the reported reason. Remove the throwaway worktrees afterwards.
6. **Document known limits** in the code docstring, the PR's Known limits
   section, Jira, and the resolving thread reply. Prefer not to push a code change
   only to document a limit.
7. **A reply retriggers Merge Admission; resolving a thread does not.** GitHub has
   no review-thread Actions trigger (`.github/workflows/merge-admission.yml`). The
   run a reply starts can fail at "Gate on review-thread finality at the candidate"
   while that thread is still open. The failure then stays after you resolve the
   thread. After resolving the last thread, rerun the check with
   `gh workflow run merge-admission.yml -f pull_request_number=<PR>` and read that
   run's job steps before reporting. Superseded runs show as cancelled.
8. **Reply in each thread with** what was confirmed, the change by SHA, the
   isolating control, and any limit stated plainly.

### Mechanics that cost time in Phases 2–3

- **Bound integration tests are slow.** They take 3–6 minutes alone; the Phase 3
  positive path takes about 15 minutes alone and 45–57 minutes under about 12
  parallel processes.
  - Run them in the background with `-o addopts=''`, `-p no:cacheprovider` and
    `-p no:cov`.
  - Use `--junitxml`, a short unique `--basetemp` per group, and non-overlapping
    node-id groups.
  - Never wrap them in a shell `timeout`.
- **Before pushing, run the CI `contract-and-session-currency` pytest list
  locally.** It takes about 1–2 minutes. Its 06i AST storage-boundary contract
  failed only in CI during Phase 3, because no feature packet includes it.
- **Never commit while tests are running from that worktree.** pre-commit stashes
  unstaged files under the running processes. Commit first, then test the
  committed tree.
- **Create worktree virtual environments one at a time.** When three new
  worktrees built `uv` venvs concurrently, one install failed with "Access is
  denied" on a trampoline executable. Run `uv sync` in each new worktree
  sequentially before launching tests.
- **The Repowise post-commit hook dirties `.claude/CLAUDE.md` and
  `.repowise-workspace.yaml`.** Restore them with `git checkout --` and stage by
  explicit path.
- **Write files with LF endings.** Write commit messages as BOM-free files and use
  `git commit -F`.
- **Write PR bodies and thread replies to files.** Publish with `--body-file` or
  `gh api -F body=@file`, then verify the published text byte for byte.
- **Use Git Bash, not PowerShell 5.1, for `gh api` calls with a `--jq` expression.**
  PowerShell 5.1 splits the quoted expression into several arguments. Resolve
  threads with the GraphQL `resolveReviewThread` mutation after mapping comment
  IDs to thread IDs.

### Handback

Lead with the applicable §8 capability status. Then give:
- the scope decision Stephen made, and the sub-phase delivered;
- the public path now demonstrated;
- the exact remaining Gate 6 gap and the next action;
- worktree, branch, base and candidate SHAs, and the file and line scope;
- positive and negative evidence, with exact commands and summaries;
- mutation controls;
- review identity, and declined findings with reasons;
- known limits;
- verified Jira changes (KAN-109 and, as applicable, KAN-103/KAN-12).

Component success never means Gate 6 closure. KAN-109 becomes a MILESTONE only
after its approved scope has merged and the assembled exact-main selection and
boundary review pass.
