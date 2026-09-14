# WP6 Gate 6 Phase 3 handoff — accepted project-use RESULT

**Capability status:** INCOMPLETE — the historical real SPEC run is PROVEN; the
complete public Gate 6 implementation is not integrated on main. STORE, Phase 1
SOURCE and Phase 2 AUTHORITY/TASK are integrated; Phases 3–5, final independent
evidence review and Stephen's closure remain.

**Dispatch state:** ready for Stephen's explicit Phase 3 dispatch; do not begin
construction from this handoff alone.

**Recommended model:** `gpt-6-astra` or the strongest available reasoning model,
at `xhigh`. Phase 3 adds a new closed record, a registration and independent
acceptance path, a pure evaluator and a renderer on the same public route. The
difficult part is binding evidence correctly, not writing volume. Reserve `max`
for a separate final exact-head adversarial review.

**Predecessor:** Phase 2 handoff
`handoffs/35-wp6-phase2-authority-task-handoff-2026-09-11.md`; Phase 2 delivered
through PR #286, merged at `bed57bf8960046462e654d24bec7eedea3a516c7`.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 3 — accepted project-use
result on the same route**, Jira **KAN-108**, in `C:\Users\steph\TDL`.

### Start identity

Stephen has merged Phase 2 PR #286. Refresh `origin/main`; it must contain
`bed57bf8960046462e654d24bec7eedea3a516c7`, and it may also contain the Phase 2
close-out docs PR that added this file. Record the exact SHA before the first
write. Create one clean linked worktree under `C:/Users/steph/` with a `codex/`
branch, copy the primary checkout's `.env`, and verify cwd, symbolic branch,
HEAD, clean status and ancestry before any write. Preserve unrelated dirty
files in the primary checkout.

### Read first

1. `docs/plans/agentic-research-system/implementation/06s-gate6-delivery-replan-and-gate7-integration.md`:
   §§3–5.0, **Phase 3**, the Phase 2 status block, §8 and §9.
2. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`:
   **P-050** (historical SPEC outcome and research-use disposition) and
   **P-051–P-056**.
3. Phase 2's production surface, which you extend rather than parallel:
   `research_system/discovery/spec.py` (the `ACTION_EFFECTS` table,
   `SpecCoordinator.status/advance`, `_advance_task`, `_submit_effect`),
   `research_system/discovery/spec_task.py` (the evaluator pattern) and
   `tests/research_system/integration/test_spec_task.py` (the bound scratch
   fixtures `bound_task` / `_seed_bound_task` and the CLI helpers).
4. PR #286's description, especially its **Known limits** section.

### Required production outcome (06s Phase 3)

Extend the same action table, evaluator and public CLI so that registration and
independent acceptance of a **ProjectUseDecision** produce the Task-specific
JSON and Markdown result through
`ars discovery spec result --operator-config … --task-id … --format json|markdown`.
The result stays **pending** until both registration and independent acceptance
exist. The evaluator stays pure over ledger-derived evidence: not_started,
prepared or completed, with conjunctive completion over correctly bound required
effects. Conflicting evidence rejects. There is no fourth persisted state,
composite seal or second workflow model.

`ProjectUseDecision` / `ars://portfolio/project-use-decision` 1.0.0 is a closed
record under D3. It must reference:
- the Candidate, the current Assay, and the Spike (or an explicit `no_spike`
  reason);
- the terminal owner Decision and the source observation or correction;
- the evidence artefacts, the accepted operational Task and the governed-code
  subject.

Its disposition is one of `retain_experimental_benchmark`, `adopt_default` or
`reject`. It also carries a rationale, limitations, next gates and D6's
route-proof subset qualification. Preserve the historical PARK restriction:
**no promotion or replication wording for PARK**.

**This is tooling to be built, not an action to take.** On `bed57bf8` no
`ProjectUseDecision` schema, record, writer or reader exists anywhere in
`research_system/` or `.research-system/schemas/`. The `spec` CLI has only
`status` and `advance`, with no `result` subcommand. Confirm this on your
selected SHA before designing.

### Measure before you build

The Phase 2 brief spoke in role words, and the enforcement mapping had to be
measured before it could be built. Do the same here, on a scratch store, before
production code:
- Which existing governed commands can register the decision artefact and
  record independent acceptance, and what does each admit, by actor class?
- Which inherited preconditions bind the Task, Candidate, Assay and Spike
  references, and which are **not** validated by admission?
- Every field that admission leaves unchecked must be bound by the route.

Take each pair of measurements at an identical state so that the actor is the
only difference. If the brief's outcome can only be met by widening inherited
authority or adding a parallel policy, stop and bring the measurement to
Stephen (D2).

### Initial packet (06s Phase 3)

- Explicit action expectations.
- Empty, partial, complete, conflicting, unrelated and retry evidence for each
  required action class.
- Pending and accepted output, in both JSON and Markdown.
- Historical and fresh Task isolation by `--task-id`.
- No promotion wording for PARK.
- Hash-only, wrong-binding and unknown-field rejection.

Run the real public positive path first, then the negatives, then the Phase 1/2
regression packet (`test_spec_operator_config.py`, `test_spec_source.py`,
`test_spec_task.py`).

### Carry forward from Phase 2 (do not re-derive)

- **Evaluate only evidence the route issued.** Located evidence must pass three
  checks:
  1. *Identity:* it carries the route's own retry key.
  2. *Content:* its payload equals what the route derives at that ledger
     position, from one function that both builds and verifies.
  3. *Exclusivity:* nothing else is on the action's streams.

  Field-by-field checking of foreign evidence was an open-ended review surface
  across three rounds. Start from the class-level rule.
- **Every input to a retry key must be recoverable from the recorded event.**
  Free-text `reason` is not recorded, which is why `close_task` keys use
  `key_intent`.
- **Put every refusal of a closing precondition before the first durable
  mutation.** A refusal at the last effect strands the subject. When a review
  finding names a placement defect, sweep every check of that kind.
- **Take state, command and expected stream version from one ledger snapshot.**
  Answer exact retries from the stored receipt, never by resubmitting.
  Admission resolves authority before its receipt lookup.
- **Known limits you inherit** (PR #286, KAN-106/107):
  - A late `SubmitForReview` retry collides with `AcceptTask`, because an
    intent-level invocation does not name its effect.
  - The cross-stream race.
  - Candidate-bearing Attempts cannot be closed by `close_task`.
  - Failed and partial work has no rework path.

  **Adding an effect identity to the public intent, or artefact selection, is not
  in the 06s Phase 3 brief.** If your design needs either, raise it with Stephen
  as a scope decision before building. Do not widen scope yourself.

### Hard boundaries

- No live control-store operations (`C:/Users/steph/TDL-ARS-WP64-Control`),
  provider or paid calls, credential use, successor binding, historical Task or
  ProjectUseDecision closure (Phase 5), Gate 7 work, or final Gate 6 closure.
  Scratch stores only.
- No new plan, framework, persisted workflow model, composite seal or
  speculative STORE change (D5). No replacement of `SpecOperatorConfig@1.0.0`.
- Once Phase 3 merges, the historical ProjectUseDecision **still** may only be
  registered and accepted in Phase 5, under Stephen's explicit per-step
  authorization. Merging this code does not authorize using it on the live
  store.
- Do not write toy or synthetic output into `results/`.
- Never bypass pre-commit hooks. Stephen controls CodeRabbit, merges and
  auto-merge. Do not trigger or poll CodeRabbit, merge, or enable auto-merge.
- Scope checkpoint (06s §5.0): 20 changed files, 2,500 added non-generated lines,
  or more than one session plus one follow-up requires Stephen's continuation
  decision.

### Review process — advice from Phase 2

Phase 2 took one independent review and six Codex rounds (findings 5, 8, 6, 4,
4, 1). What worked:

1. **Codex reviews every push automatically, so each push opens a new round.**
   Batch fixes, and push only a tree whose full focused packet has passed.
2. **Verify each finding against the code before acting**, then classify it:
   - blocking under §5.0;
   - backed by explicit 06s/06q text;
   - an edge case.

   All Phase 2 findings were real, but their severity fell steadily.
3. **Under 06s §5.0, a second material round needs Stephen's decision.** Give him
   a short table: finding, verified?, assessment, recommendation. He decides the
   remediation scope.
4. **If the count does not fall by round 3, stop patching and find the shared
   shape.** Phase 2's structural change was to evaluate only route-issued
   evidence. It removed a whole class, and that class never recurred.
5. **Treat a reviewer's suggested fix as a hypothesis.** Twice, the public positive
   path caught a defect that every negative control missed: a retry key over an
   unrecorded field, and a retry-scope widening that made `AcceptTask` replay
   `SubmitForReview`. Re-run the positive path after every change. Before
   widening a scoped safety argument ("latest", "adjacent", "first"), re-derive
   it.
6. **Prove each new negative control is decisive.** Run it against the previous
   candidate, in a throwaway detached worktree, and confirm it fails there for the
   reported reason. Where admission would accept the refused input, add a control
   that shows admission accepts it.
7. **Once findings plateau into retry or concurrency edges with bounded impact,
   record them as known limits.** Stephen adopted this rule at round 5. Document
   each limit in:
   - the code docstring;
   - the PR description's Known limits section;
   - Jira;
   - the thread reply, resolving the thread.

   Prefer not to push a code change just to document a limit, since a push starts
   another round.
8. **Replies and resolves retrigger the Merge Admission workflow.** Superseded
   runs show as red "cancelled" checks. Read the run annotations before reporting
   a failure. Thread finality requires every thread to be resolved.
9. **Reply in each thread with:**
   - what was confirmed;
   - the change, by SHA;
   - the isolating control;
   - any limit, stated plainly.

   Keep the PR description current: evidence counts, review rounds, known limits.

### Mechanics that cost time in Phase 2

- **Bound integration tests take about 3–6 minutes each here.**
  - Run them in the background with `--no-cov`, `-p no:cacheprovider`,
    `--junitxml`, and non-overlapping `-k` groups in parallel.
  - Never wrap them in a shell `timeout`: exit 143 is the wrapper, not a test.
  - Use a short `--basetemp`, for example `C:/Users/steph/AppData/Local/Temp/p3a`.
    Deep paths exceed Windows git's 260-character limit, and the fixture hides
    git's stderr.
- **The Repowise post-commit hook dirties `.claude/CLAUDE.md` and
  `.repowise-workspace.yaml`.** Restore them with `git checkout --` and stage by
  explicit path.
- **Write files with LF endings.** The pre-commit CRLF byte-surface gate blocks
  CRLF writes; renormalise rather than bypass.
- **Write commit messages, PR bodies and thread replies to files.** Use
  `git commit -F`, `--body-file` and `gh api --input`, never shell heredocs.
  Verify the published text.

### Handback

Lead with the applicable §8 capability status. Then give:
- the public path now demonstrated;
- the exact remaining Gate 6 gap and the next action;
- worktree, branch, base and candidate SHAs, and the file and line scope;
- positive and negative evidence, with exact commands and summaries;
- review identity, and declined findings with reasons;
- known limits;
- verified Jira changes (KAN-108 and, as applicable, KAN-103/KAN-12).

Component success never means Gate 6 closure. KAN-108 becomes a MILESTONE only
after its PR merges.
