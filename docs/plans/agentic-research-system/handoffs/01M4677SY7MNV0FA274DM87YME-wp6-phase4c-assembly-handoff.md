# WP6 Gate 6 Phase 4c handoff: the assembled exact-main selection and the boundary review

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6 implementation is not integrated on main. STORE, Phase 1 SOURCE, Phase 2 AUTHORITY/TASK, Phase 3 RESULT and Phase 4a, 4a′, 4b-1, 4b-2a and 4b-2b are integrated. 4c remains, then Phase 5 and Stephen's closure.

**Dispatch state:** ready for Stephen's explicit 4c dispatch. Do not begin from this handoff alone. 4c is assembly evidence and an independent review, not construction. Its first deliverable is a selection plan that Stephen accepts before the packet runs.

**Recommended model:** the strongest available reasoning model, at `xhigh`, for the selection and its evidence. Use a separate fresh-context model for the boundary review. It must not inherit this campaign's context.

**Predecessors:**
- `handoffs/01M2PFB005VNEA72FWKYZQPGND-wp6-phase4-remainder-handoff.md` (4a′, 4b and 4c). Its "What 4a decided, and how", "Mechanics" and "Hard boundaries" still apply, except where this handoff updates them.
- `handoffs/01M2FWVVXP9RG0M171P8XCYT8A-wp6-phase4-assembly-handoff.md`, whose 4c definition this handoff carries forward.

Read both; this document does not repeat them.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 4c**, Jira **KAN-109**, in `C:\Users\steph\TDL`.

### Start identity

Refresh `origin/main`. It must contain:
- `e7b8f1da607c2ff13a8a615a02ff860911c7caa6` (the PR #309 merge, 4b-2b);
- `8792fe8a` (#310, schema-validator reuse);
- the PR that added this file.

Record the exact SHA before the first write. That SHA is 4c's subject; every packet and the review name it.

Create one clean linked worktree under `C:/Users/steph/` on a `codex/` branch, copy the primary checkout's `.env` into it, run `uv sync --locked --extra dev`, and prove pytest runs there before any red or green run. Before any write, verify:
- the working directory;
- the symbolic branch and HEAD;
- a clean status;
- ancestry from the recorded SHA.

### Read first

1. `docs/plans/agentic-research-system/implementation/06s-gate6-delivery-replan-and-gate7-integration.md`:
   - **Phase 4**, every status block and P-058 bullet;
   - **Phase 5**, every P-058 amendment, including 2026-10-01;
   - **§8** (capability rows);
   - **§9** (Jira);
   - **§12** (the Phase 0 STORE packet and its exact command).
2. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`: **P-058** and every block, in order. The newest are "4b-2b design decisions (2026-09-25)", with its decision 2 extended by the PR #309 review, and "Test-cost decisions (2026-10-01)".
3. The PR descriptions of **#290, #291, #292, #296, #297, #298, #309 and #310**. They hold each sub-phase's review tables, route bindings and numbered known limits. #309's description holds the latest certification packet, its 18 mutation controls and the time-budget breach.
4. The production surface: `research_system/discovery/spec.py`, `spec_assay.py`, `spec_result.py`, `spec_task.py`, `spec_source.py` and `spec_replay.py`.

### Verified state at `e7b8f1da` (confirm on your SHA)

- **`ACTION_EFFECTS` holds 25 actions:**
  - SOURCE: `observe_source` and `correct_spec_01_source`;
  - Task: `close_task`;
  - project use: `register_project_use_decision` and `accept_project_use_decision`;
  - bootstrap: `bootstrap_genesis` and `bootstrap_assay_authority`;
  - SPEC-01: `request_spec_01`, `prepare_spec_01`, `return_spec_01_complete`, `return_spec_01_partial`, `review_spec_01_complete`, `review_spec_01_partial` and `decide_spec_01`;
  - revisit and retry: `request_spec_01_revisit`, `authorize_spec_01_retry` and `request_spec_01_retry`;
  - SPEC-02: `approve_spec_02`, `prepare_spec_02`, `start_spec_02`, `return_spec_02_complete`, `return_spec_02_partial`, `review_spec_02_complete`, `review_spec_02_partial` and `decide_spec_02`.
- **Public paths demonstrated on scratch stores:**
  - genesis → bar → SOURCE → SPEC-01 → PARK or PROMOTE → `close_task` → accepted project use;
  - a reviewed Partial → revisit → owner RETRY → a second Assay to PROMOTE;
  - PROMOTE → SPEC-02 approval, brief and start → return → review → decision → accepted project use that records the Spike.
  - A Partial Spike is terminal.
- **Every route read replays through `spec_replay`**, once per coordinator operation. Route modules must not import the uncached replays; `tests/research_system/unit/test_spec_replay.py` guards that.
- **78 public-route tests are marked `slow`.** The fast route suite is `-m "not slow"` over the six `test_spec_*.py` integration modules: 29 tests.

### 4c scope (06s Phase 4 and P-058)

1. **One bounded assembled selection on the exact SHA:**
   - the **Phase 0 STORE packet** (the exact command in 06s §12);
   - the **Phase 1–4 packets**: every test in `test_spec_source.py`, `test_spec_task.py`, `test_spec_result.py`, `test_spec_assay.py`, `test_spec_spike.py`, `test_spec_spike_outcome.py` and `tests/research_system/unit/test_spec_replay.py`, plus `test_spec_operator_config.py`;
   - the CI `contract-and-session-currency` pytest list (`.github/workflows/ars-artefact-currency.yml`);
   - `tests/research_system/unit/test_schema_registry.py`.
2. **One fresh-context independent exact-main boundary review** of the integrated SPEC route, before anyone proposes the live successor binding.
3. **Report** with the §8 row "Assembled code integrated and passing" if both pass. This is assembly evidence, not Gate 6 closure.

### First deliverable: the selection plan, for Stephen

Bring these to Stephen as decisions before running anything long.

1. **The selection's exact node list and grouping.** Use groups of at most about five tests, so the 60-minute group budget measures tests, not batch size.
2. **Pre-existing failures on main inside the selection. Decide before running.**
   - On 2026-10-02 a full research_system run at `54808984` found 195 tests failing on main in 23 files. No CI lane runs them.
   - Two of those files are in the **Phase 0 STORE packet**: `integration/test_current_binding.py` (23 failures) and `integration/test_store_binding_service.py` (9).
   - The `test_current_binding.py` failures report git's Windows 260-character path limit under a long `--basetemp`. The test itself suggests a short `--basetemp`, and 06s §12's original packet used one.
   - A separate triage task was started on 2026-10-02 (session task "Triage 195 tests failing on main in research_system"). Read its findings first.
   - For each failing node in the selection, establish whether it is environmental (and passes under the documented conditions) or a real defect. Bring the disposition to Stephen. A selection that "passes" by excluding failing nodes is not assembly evidence.
3. **The time budget** (P-058, 2026-10-01).
   - The rules: certification runs only between 02:00 and 11:00, on at most 8 workers. A group over 60 minutes fails the packet's budget; record it and let the group finish. The packet takes 5 hours or less.
   - The last two packets (#309) breached the group budget. Up to six jobs ran 60–90 minutes: the complete SPEC-02 path, the SPEC-02 refusals test, and the controls that re-run it.
   - A follow-up PR splitting the SPEC-02 refusals test by refusal family was started on 2026-10-05. Use main after it merges, or record the breach again.
4. **The boundary review's brief:**
   - its scope (the integrated route against 06q §4 Step 5's composition, P-058 and the §4 closure contract);
   - its inputs (exact SHA, PR descriptions, known-limit lists);
   - what it must not see (this campaign's conversation);
   - its output: findings graded by severity, with a disposition for each.

   Stephen decides who or what runs it.

### Mechanics updates since the predecessor handoff

- **Launch long runs in a tab of the app's terminal panel** (`mcp__terminal__run_in_terminal`, one literal command line), not as a Bash background task. On 2026-10-02 a background task was stopped after about 30 minutes, before its run began.
- **Keep runners resumable,** with per-group result files and a start file per group. Re-running the same command reuses finished groups.
- **Every run must prove it executed tests** (JUnit `tests >= 1`) before its exit code is read. Never combine `-m` or `-k` with explicit slow node IDs: the filter deselects them silently.
- **Retry the git stall once.** On 2026-09-26, eleven groups failed in the same second with "Git inspection is unavailable", a stall of more than 10 seconds across the whole process tree. A run with that signature is retried once, and both attempts are kept.
- **Mutation controls.**
  - Fast in-place controls use `tools/mutation_check.py`.
  - Multi-hour controls use throwaway detached worktrees, one span each, dry-run against the committed SHA. Confirm that `research_system` imports from the worktree.
  - Remove each worktree after checking it is at the candidate with exactly its one mutation. Never run `git worktree prune`.
- **Commits must not be piped.** The commit-state guard (#300) refuses a piped `git commit`. Redirect the output to a file and confirm `git log -1`.
- **Codex review can hit its usage limit.** It did on #309's final head. Record an unreviewed head as such.
- **Timings with the replay cache, 8-way load:** the SPEC-01 path test takes about 30 minutes; the complete SPEC-02 path 62–78; the refusals test 62–65; and the whole #309 packet 3.5–3.8 hours. The SPEC-01 path test alone, idle machine, takes 9m47s.

### Open items outside 4c

- **Phase 5 prep:**
  - replace the fixture Assay authority content, and decide its signing identity;
  - decide where SPEC-01's numeric PROMOTE rule is evaluated;
  - account for `adopt_default` against the SPEC-02 no-claim rule;
  - account for the binding's schema-catalogue re-check cost (about five per invocation, D5);
  - the Task naming only the SPEC-01 Candidate is created before `prepare_spec_01`.
- **Known limits carried** in the PR descriptions of #290–#309.
- **CI.** No lane runs the full research_system suite (observation 2026-10-02-full-suite-red-on-main-unseen).

### Hard boundaries

The predecessor's hard boundaries apply unchanged:
- no live control-store, provider, paid or credential work;
- no successor binding, live SPEC run, Gate 7 work or Gate 6 closure;
- PROMOTE and SPEC-02 approval only on scratch stores, in tests;
- no new plan, framework, persisted model, composite seal or speculative STORE change (D5);
- no replacement of `SpecOperatorConfig@1.0.0`;
- no toy or synthetic output in `results/`;
- never bypass hooks;
- Stephen controls CodeRabbit, merges and auto-merge.

In addition:
- 4c changes no production code. A defect the selection or the review finds goes to Stephen as a decision. If he approves a fix, it ships in its own PR with its own certification.
- Do not apply a review stopping rule to a PR until Stephen accepts it for that PR.
- Do not propose the successor binding until both the selection and the boundary review pass and Stephen records it.

### Handback

Lead with the applicable §8 row. Then give:
- the exact SHA tested;
- the selection, its node count and grouping;
- each group's result and time, and every failure with its disposition;
- the budget outcome;
- the boundary review's findings and dispositions;
- verified Jira changes. KAN-109 becomes a MILESTONE only after Stephen accepts 4c.
