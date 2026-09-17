# WP6 Gate 6 Phase 4 remainder handoff: 4a′, 4b and 4c

**Capability status:** INCOMPLETE — the historical real SPEC run is PROVEN; the
complete public Gate 6 implementation is not integrated on main. STORE, Phase 1
SOURCE, Phase 2 AUTHORITY/TASK, Phase 3 RESULT and Phase 4a are integrated. The
rest of Phase 4 remains: 4a′, then 4b, then 4c. So do Phase 5, the final
independent evidence review and Stephen's closure.

**Dispatch state:** ready for Stephen's explicit 4a′ dispatch. Do not begin
construction from this handoff alone. The first deliverable of each sub-phase is a
design pass that brings findings to Stephen as decisions, not code.

**Recommended model:** the strongest available reasoning model, at `xhigh`. Keep a
separate fresh-context model for 4c's exact-main boundary review.

**Predecessor:** the Phase 4 handoff
`handoffs/01M2FWVVXP9RG0M171P8XCYT8A-wp6-phase4-assembly-handoff.md`. Its sections
"Measure before you build", "Carry forward from Phases 2–3", "Hard boundaries",
"Review process" and "Mechanics" still apply, except where this handoff updates
them. Read it; this document does not repeat it.

## Handoff prompt

You are the primary executor for the rest of **06s Gate 6 Phase 4**, Jira
**KAN-109**, in `C:\Users\steph\TDL`. Work one sub-phase at a time, in the order
4a′ → 4b → 4c. Each sub-phase needs its own dispatch from Stephen.

### Start identity

Refresh `origin/main`. It must contain
`781f1e6028cbe7624c1c07b7905d448f2a75eaa3` (the PR #292 merge) and the close-out
PR that added this file. Record the exact SHA before the first write.

Create one clean linked worktree under `C:/Users/steph/` on a `codex/` branch, copy
the primary checkout's `.env` into it, and run `uv sync --extra dev` there. Before
any write, verify:
- the working directory;
- the symbolic branch and HEAD;
- a clean status;
- ancestry from the recorded SHA.

Preserve unrelated dirty files in the primary checkout.

### Read first

1. `docs/plans/agentic-research-system/implementation/06s-gate6-delivery-replan-and-gate7-integration.md`:
   §§3–5.0; **Phase 4**, including its 4a status block and every P-058 bullet;
   **Phase 5**, including the P-058 amendments of 2026-09-14, 2026-09-15 and
   2026-09-16; §8; §9; §11.
2. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`:
   **P-058** and its blocks, in order. Together they are the decision record for
   4a:
   - the measured-admission amendment;
   - the design acceptance;
   - the 4a-2 design decisions;
   - the 4a-2 review decisions for rounds 1, 2 and 3;
   - the 4a-2 follow-up decisions.
3. `docs/plans/agentic-research-system/implementation/06q-gate6-spec-real-run-integration-and-follow-up.md`
   §4 Step 5: the rows for `return_spec_01_partial`, `review_spec_01_partial`,
   `request_spec_01_revisit`, `authorize_spec_01_retry`, `request_spec_01_retry`
   and the eight SPEC-02 actions. It is retained only as the action composition.
4. The PR descriptions for **#290**, **#291** and **#292**. They hold the review
   tables, the route bindings and the numbered known limits.
5. The production surface:
   - `research_system/discovery/spec_assay.py` (the whole module);
   - `research_system/discovery/spec.py`: `ACTION_EFFECTS`, `_advance_assay`,
     `_submit_effect`, `_DocumentRegistrationService` and
     `_REGISTRATION_SERVICES`;
   - `research_system/discovery/spec_result.py::derive`;
   - `research_system/discovery/runtime.py`, `rules.py` and `routes.py`.
6. The tests: `tests/research_system/integration/test_spec_assay.py` (16 tests)
   and its helpers, including:
   - `_requested`, which runs genesis, the bar, observation and the request;
   - `_seed_task_naming`, with `also_naming` and `outcome`;
   - `_invoke` and `_run`, which drive the public CLI;
   - `_direct`, for decisive admission controls;
   - `_ingest_direct`;
   - `bind_scratch_route`, with `repository_overrides`.

### Verified state at `781f1e60` (confirm on your selected SHA)

- `ACTION_EFFECTS` holds 12 actions:
  - `observe_source`, `correct_spec_01_source` and `close_task`;
  - `register_project_use_decision` and `accept_project_use_decision`;
  - `bootstrap_genesis`, `bootstrap_assay_authority` and `request_spec_01`;
  - `prepare_spec_01`, `return_spec_01_complete`, `review_spec_01_complete` and
    `decide_spec_01`.
- **The 4a′ and 4b rows are routed but not on the SPEC route.** `DiscoveryRuntime`
  routes:
  - OR-005 `RecordAssayPartial`, OR-035 and OR-007 (the Partial outcome review);
  - OR-009 `ProposeRevisitDecision`, OR-010 `ResolveDecision` and OR-011
    `RequestAssay` (retry);
  - OR-014–017 (the Spike plan, execution decision and start);
  - OR-018 and OR-019 `RecordSpikeVerdict`;
  - OR-036, OR-037, OR-020 and OR-021 (the Spike outcome reviews);
  - OR-026 and OR-027 (the Spike decision).
- **Closed records.** `spec-assay-intent`, `spec-operator-brief-package` and
  `spec-operator-return` exist at 1.0.0 in `.research-system/schemas/contracts/wp6-6/`,
  and they are on main now. No schema, writer or reader exists for
  `ars://portfolio/spec-02-live-run-approval`; that record is tooling to build
  in 4b.
- **Admission's Partial record is a different artefact.** OR-005 binds an
  `ars://portfolio/assay-partial` artefact (`rules.py:54-67, 717-760`), not an
  Assay scorecard. The merged `spec-operator-return` 1.0.0 requires `scorecard` and
  `scorecard_sha256`.

### What 4a decided, and how (retain this)

The conclusions below are in force. Change none of them without a recorded decision
from Stephen. Each is stated in full, with its evidence, in the P-058 blocks named
under "Read first".

**Conclusions in force (from P-058 and its amendments)**
- **Route-issued evidence only.** An effect counts only when three things hold:
  it carries this route's retry key, its payload re-derives at its ledger position,
  and nothing else sits on a stream the action owns.
- **Relations admission leaves unchecked are refused by the route, before the first
  durable mutation.** The measured list is in P-058. Each refusal has a decisive
  control showing that admission would accept the input.
- **Operational provenance.** Operator records derive their Task, dispatch,
  Attempt, context packet and the Attempt's own code and environment identities
  from the ledger. The Task must:
  - be the only Task naming the Candidate;
  - name no other registered Candidate;
  - be unamended since its Attempt's dispatch.

  The Attempt must be running. The caller supplies none of these.
- **Registration.** The owner registers the operator records, because
  `RegisterArtefact` is owner-only. The Assay producer's own OR-004 invocation
  re-supplies the exact registered return, compared as canonical JSON.
- **Completed actions.** A completed action answers only an exact repeat of a
  committed effect, from its receipt; an exact repeat also needs the exact evidence
  field set. Every other invocation conflicts without publication, including
  changed evidence. This applies to the Assay, `close_task` and project-use routes.
  The SOURCE path still returns state, as PR #292 known limit 4.
- **Document registrations** (SOURCE, project-use and operator records) refuse
  inside the writer lock, before publishing, once the ledger has moved past the
  snapshot the document was derived from.
- **PROMOTE** is neither proposed (OR-012) nor selected (OR-013) in two cases.
  Admission does not bind selection to the proposal, so both rows check.
  - The Assay's frozen bar, read from the registered return's scorecard, has an axis
    the inherited rule does not evaluate.
  - The return lists any unresolved finding.
- **SPEC-01's numeric rule** is not evaluated anywhere. Phase 5 prep must decide
  where it is evaluated before `decide_spec_01` runs live.
- **Only an approving outcome review can be recorded,** matching 06q's
  "satisfying verdict".
- **Fixture bar.** The committed Assay bar is W11 fixture content with one required
  gate. Phase 5 prep replaces it and decides its signing identity.

**The decision process that produced them**
1. **Design pass before construction.** Read the 06q rows and the governing brief.
   Measure admission with paired scratch probes that change one actor or field at
   an identical state.
   - Bring every place where the code cannot meet a spec row, or where a record
     would be tooling to build, to Stephen as a decision with a recommendation.
   - **Lesson (PR #291 round 1):** the owner-only registrar diverged from 06q's
     authority column. It shipped as a known limit instead of a design-pass
     decision, and cost a review round and a re-certification.
2. **Record the decision before the code.** A `[DECISION]` commit adds the P-058
   block, the 06s Phase 4/5 bullets and a Computational-Log entry. The `[PIPELINE]`
   commit follows it.
3. **Construction.** Contract-first: watch each new test fail first.
   - Develop the changed tests green on the uncommitted tree.
   - Commit through the hooks.
   - Run the certifying packet on the committed tree, with one mutation control per
     new check at the same time. Each control runs in a throwaway detached
     worktree, with exactly one source span replaced.
   - Push only a certified tree.
4. **Each review round.**
   - Verify every finding against the code, and record its origin commit.
   - Reply per thread with what was confirmed, the change by SHA and the isolating
     control, and resolve the thread.
   - Rerun Merge Admission with `--ref`.
   - A second material round goes to Stephen as a decision table: finding,
     verified?, origin, reachability on the Phase 5 path, consequence and
     recommendation.
5. **Convergence assessment** (PR #291 round 3). Judge convergence by kind, not
   count:
   - findings and P1 count per round;
   - new finding families opened;
   - findings caused by the previous round's fix;
   - findings latent since the original build;
   - findings reachable on the planned Phase 5 path.

   PR #291 went 5, 5, 5, then 2 findings. Round 3 opened no new family, and none of
   its findings was reachable on the planned path.
6. **The review stopping rule.** Stephen accepted it for PR #291 from round 4, and
   for PR #292 from round 1. A finding gets code in the PR only if it is:
   - a defect in the code the latest round added; or
   - a false durable claim reachable on the planned Phase 5 path.

   Everything else becomes a known limit or a follow-up. **Propose the rule to
   Stephen when each new PR opens. Do not apply it until he accepts it for that
   PR.**
7. **Known limits.** Record each in the code docstring, the PR's known limits, the
   thread reply and Jira. Do not push a code change only to document a limit.
8. **Follow-ups.** Batch related post-merge follow-ups into one PR, one commit per
   item, in dependency order: mechanical ports first, a new shared mechanism last.
   That is how PR #292 closed PR #291 known limits 10, 14 and 17.

### 4a′ first deliverable: a design pass for Stephen (before construction)

06s and P-058 scope 4a′ as `return_spec_01_partial` (the operator return, then
OR-005) and `review_spec_01_partial` (OR-035, then OR-007), so that a real Partial
outcome is not a dead end. Bring at least these questions to Stephen as decisions,
each with a measured recommendation:
1. **The Partial return record.** 06q says "same schema/version", but the merged
   `spec-operator-return` 1.0.0 requires a scorecard and OR-005 binds an
   `assay-partial` artefact. Options include:
   - a new version of the return schema;
   - a separate closed Partial return record;
   - another shape you measure.

   Changing a merged schema version is Stephen's decision.
2. **Action family identity.** 06q groups `return_spec_01_complete` and
   `_partial` as `return_spec_01`, and the two review actions as `review_spec_01`.
   The route derives `return_id` and `review_id` from the `…_complete` action names
   (`spec_assay.py:205-213`). Decide whether the pair shares identities, so the
   alternatives exclude each other through owned streams, or uses distinct ones,
   and how evaluation refuses the other alternative once one has an effect.
3. **Where the Partial path ends in 4a′.** `spec_result.derive` needs a terminal
   owner Decision, so a reviewed Partial Assay cannot reach a project-use result.
   Confirm on a scratch store which Candidate and Assay states follow OR-007. Then
   decide whether 4a′ ends at a reviewed Partial Assay that 4b's revisit starts from
   (P-058), and what the route's status reports.
4. **Measured admission for OR-005, OR-035 and OR-007.** Run the P-058 procedure:
   paired probes, then a route refusal and a decisive control for each relation
   admission accepts, such as the producer or owner requesting the Partial review,
   or the owner recording it.
5. **Reuse of the 4a-2 rules.** The operator records carry the provenance,
   running-Attempt, canonical-return, in-lock and completed-conflict rules.
   Confirm each applies to the Partial record unchanged, or bring the exception as
   a decision.

Apply the §5.0 checkpoint to 4a′ on its own: 20 files, 2,500 added non-generated
lines, or more than one session plus one follow-up.

### Known 4b design risks (raise at the 4b design pass)

- **Identities collide on retry.** Every SPEC-01 route identity (Assay, brief,
  return, review and decision) is derived from the Candidate and action name alone
  (`spec_assay.py:205-213`). An OR-011 retry opens a new Assay for the same
  Candidate, so the second sequence would derive the first sequence's IDs.
  `enumerated_intents` also lists only the Assay whose ID matches that derivation.
  The identity model needs a decision, for example keying by Assay or by retry
  ordinal.
- **The one-Task rules versus retry.** `_task_provenance` requires exactly one Task
  naming the Candidate, and exactly one started Attempt of it. Decide how a retry's
  operator records get their operational provenance: the same Task with a new
  Attempt, or a new Task.
- **A scored-Assay PARK revisit is expected to be refused.** OR-009 needs non-empty
  `revisit_requirements`, which replay sets only for Partial and cancelled Assays
  and for Spikes (P-058). Reproduce it on scratch first. If it is refused, record it
  as a known limit with no runtime change.
- **Scratch PROMOTE** passes the route's refusals only on a gate-only bar and a
  return with no unresolved findings. Never manufacture a PROMOTE outside scratch
  tests.
- **The SPEC-02 approval record** is tooling to build, and closed under D3. An
  approval alone never changes Candidate state.
- **Seeding `start_spec_02`.** OR-017 needs a running attempt, lease and resource
  grant. Seed them through the existing operational fixture. If that is not
  enough, return to Stephen before adding anything (P-058).
- **Bar succession.** PR #291 known limit 16 stands: inherited OR-004 admission
  validates a score against the current bar, so an Assay opened before a bar
  succession cannot be scored. It is W11 runtime intake, not 4b work.

### 4c

As in the predecessor handoff:
- after 4a′ and 4b merge, run one bounded assembled selection on exact main: the
  Phase 0 STORE packet (06s §12), the Phase 1–4 packets, and the CI
  `contract-and-session-currency` list;
- then obtain one fresh-context independent exact-main boundary review.

Report it with the §8 row "Assembled code integrated and passing". It is assembly
evidence, not Gate 6 closure.

### Open items outside Phase 4 construction

- **Phase 5 prep:**
  - replace the fixture Assay authority content, and decide its signing identity;
  - decide where SPEC-01's numeric PROMOTE rule is evaluated;
  - create the Task naming only the SPEC-01 Candidate, and start its Attempt,
    before `prepare_spec_01`;
  - do not amend the Task while the Attempt runs, and keep the Attempt running until
    the return is registered.
- **W11 runtime intake (D5):** scoring against an Assay's frozen bar after a bar
  succession (PR #291 known limit 16).
- **Follow-ups recorded as known limits** (PR #292):
  - project-use orphan reuse does not re-check prerequisites on the current ledger;
  - the SOURCE advance path has no exact-retry machinery.

### Mechanics updates since the predecessor handoff

- **Repowise no longer dirties linked worktrees.** PR #293 makes the post-commit
  hook exit in a linked worktree, and PR #294 adjusted its test. Back-to-back
  commits in a worktree no longer need a restore-and-retry loop. The main
  checkout's quiesce-and-restore logic is unchanged.
- **Timings.** The 4a-2 public path takes about 21–23 minutes alone. On 20
  threads, a 19-group packet plus 21 mutation controls took about 2 hours of wall
  time. Start the controls after the commit lands, and let them run alongside the
  packet.
- **Mutation controls.** Replace exactly one source span per control, and dry-run
  every mutation against copies first to confirm each span matches exactly once. A
  schema mutation is read from the worktree under test. The PR #291 control scripts
  were session-local, so rebuild them from this description.
- **Never compose Python containing `\n` inside a shell heredoc.** Twice it broke
  generated mutation tables. Write such files with an editor tool.
- **Earlier mechanics still apply.** These are in the predecessor handoff:
  - never commit while tests run;
  - LF endings, and BOM-free `git commit -F` messages;
  - PR bodies and replies published from files and verified byte for byte;
  - Merge Admission rerun with `--ref` after the last resolve;
  - Git Bash for `gh api --jq`.

### Hard boundaries

The predecessor's hard boundaries apply unchanged:
- no live control-store, provider, paid or credential work;
- no successor binding, live SPEC run, Gate 7 work or Gate 6 closure;
- PROMOTE and SPEC-02 approval only on scratch stores, in tests;
- no new plan, framework, persisted model, composite seal or speculative STORE
  change (D5);
- no replacement of `SpecOperatorConfig@1.0.0`;
- no toy or synthetic output in `results/`;
- never bypass hooks;
- Stephen controls CodeRabbit, merges and auto-merge.

In addition:
- **Do not change a merged schema version** (`spec-assay-intent`,
  `spec-operator-brief-package`, `spec-operator-return`, `project-use-decision`)
  without Stephen's recorded decision.
- **Do not apply a review stopping rule to a PR** until Stephen accepts it for that
  PR.
- **Do not start 4b's construction from the 4a′ dispatch, or 4c from either.** Once
  a predecessor merges, the next sub-phase still needs Stephen's own dispatch and
  its own design pass.

### Handback

Lead with the applicable §8 capability status. Then give:
- the decisions Stephen made at the design pass, and the sub-phase delivered;
- the public path now demonstrated;
- the exact remaining Gate 6 gap and the next action;
- worktree, branch, base and candidate SHAs, and the file and line scope;
- positive and negative evidence, with exact commands and summaries;
- mutation controls;
- each review round's table, with declined findings and reasons;
- known limits;
- verified Jira changes (KAN-109 and, as applicable, KAN-103 and KAN-12).

Component success never means Gate 6 closure. KAN-109 becomes a MILESTONE only
after its approved scope has merged and 4c's assembled selection and boundary review
pass.
