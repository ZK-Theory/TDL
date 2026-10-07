# WP6 Gate 6 Phase 5 prep handoff: the fresh store, the durable checkout and SOURCE provenance

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main. Phase 4 is complete. 4c finished at `e5179b57` with its blocking
review finding routed to Phase 5 prep (P-058, 4c disposition, 2026-10-07).

**Dispatch state:** ready for Stephen's explicit dispatch. Do not begin from this handoff alone. The first
deliverable is a design pass that Stephen accepts before any construction.

**Recommended model:** the strongest available reasoning model, at `xhigh`.

**Predecessors:** `handoffs/01M4677SY7MNV0FA274DM87YME-wp6-phase4c-assembly-handoff.md` (4c) and
`handoffs/01M2PFB005VNEA72FWKYZQPGND-wp6-phase4-remainder-handoff.md`. Their mechanics and hard boundaries
still apply, except where this handoff updates them.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 5 prep** in `C:\Users\steph\TDL`.

### Start identity

Refresh `origin/main`. It must contain `e5179b57811f74346707a4fe5fe7c407772cb3dc` (4c's subject) and the PR
that added this file. Record the exact SHA before the first write. Create one clean linked worktree under
`C:/Users/steph/`, copy the primary checkout's `.env` into it, run `uv sync --locked --extra dev` and prove
that pytest runs there. Before any write, verify the working directory, the symbolic branch and HEAD, a clean
status and ancestry from the recorded SHA.

### Read first

1. `implementation/06s-gate6-delivery-replan-and-gate7-integration.md`: §4, §5.0, Phase 4's status, and
   **Phase 5 with every P-058 amendment**, including 2026-10-07.
2. `03-decisions-and-open-questions.md`: P-058 in order, ending with "4c disposition (2026-10-07)".
3. `reviews/06s-phase4c-boundary-review-e5179b57-2026-10-07.md`. Read all of it, especially B-1 and its
   reproductions (§2.1), M-1 and M-2.
4. The known limits in the PR descriptions of #290, #291, #292, #296, #297, #298, #309 and #331.
5. How the live store was pinned: `.research-system/config/foundation.yaml` and the three commits that
   materialized it, `8cb5e71a`, `14e6862a` and `76babe02` (2026-08-05 to 2026-08-10). Each one also changed
   production code.
6. The code on the B-1 path: `research_system/cli.py` (`store init`, `_load_gate6_binding_context`),
   `research_system/config.py` (`canonical_foundation_path`, `load_foundation_origin_pins`),
   `research_system/store/identity.py` (the origin witness and `physical_root_identity`),
   `research_system/store/binding_service.py`, `research_system/store/current_binding.py` and
   `research_system/store/governed_code.py` (`validate_reviewed_documentation_successor`).

### Scope (06s Phase 5, P-058 2026-10-07)

1. **The fresh store: one store, created once.** Design the smallest owner-authorized procedure:
   1. create the control root;
   2. compute its origin-witness pin, which covers the root's physical identity;
   3. commit the foundation re-pin;
   4. run `store init`.

   Then bind it. No general store-creation feature (D5). The design decides:
   - whether a helper that computes the pin without writing is needed;
   - whether the fresh store replaces the live store in the foundation or sits beside it, and what that
     does to the tests and contracts that pin the live foundation;
   - the control root, the origin-authority root and the project identity.
2. **The durable checkout (M-1).** Choose one non-linked checkout outside the agent worktree directories:
   the primary or a dedicated clone. It stays clean and frozen from step 1 to step 6 and becomes the
   foundation's schema and code root. The foundation's `code_roots` currently lists about 14 agent
   worktrees; decide what it should list.
3. **SOURCE provenance (M-2, Stephen 2026-10-07: bind).** Derive the SOURCE registration's production
   references from the ledger and verify them, as the operator records and the project-use decision already
   are, so that they name a real running SOURCE Task and Attempt. This is a code change, in its own
   certified PR.
4. **Earlier prep items:**
   - the Assay authority content that expresses SPEC-01's axes, and its signing identity;
   - where SPEC-01's numeric PROMOTE rule is evaluated;
   - `adopt_default` against the SPEC-02 no-claim rule (#309 known limit 10);
   - the binding's schema-catalogue re-check cost;
   - the Task naming only the SPEC-01 Candidate, created and started before `prepare_spec_01`.
5. **The runbook note (m-4).** After an admission refusal of a time-free effect, retry under a new grant.

### First deliverable: the design pass, for Stephen

For each scope item, give:
- the current behaviour, measured on scratch roots where it can be;
- the options and a recommendation;
- whether it needs code (its own PR and certification), committed configuration, or procedure only.

Also give:
- **The live sequence.** The exact order of live operations and commits, from the empty control root to
  step 1. Show each point where Stephen authorizes, and show where the foundation re-pin merges relative to
  `store init`.
- **The delta assurance** that step 1 requires on the post-prep SHA:
  - the selection, full or delta-selected;
  - its time budget;
  - a fresh-context review brief scoped to the `e5179b57` to post-prep diff and to confirming that B-1, M-1
    and M-2 are closed.
- **The time budget.** 4c's packet breached its budget badly, but the A/B in the P-058 4c disposition
  showed the same route cost at `5d2a259c` and `e5179b57` (356 s each). The cause was machine conditions
  during the window. Before each certification window, check the machine for other heavy jobs, and record
  that check. Recommend how prep's certifications and the delta selection stay within P-058's budget, or
  bring that to Stephen as a decision.

### Mechanics

- **4c's runner** is `C:/Users/steph/.codex/tmp/g6-4c/assemble_4c.py`, with its frozen node list and
  results beside it. It is resumable, it reconciles every node against JUnit, and it keeps the
  02:00–11:00 window and the budget flags. Reuse it for the delta selection, with a new collected node list.
- **A terminal tab dies when the app quits.** On 2026-10-07 the first 4c launch died that way before 02:00,
  and re-running the same command recovered it. Launch long runs as one literal command in a terminal tab,
  and keep them resumable.
- The 4c handoff's mechanics still apply: every run must prove it executed tests (JUnit), the git stall is
  retried once, mutation controls use throwaway detached worktrees, `git commit` is never piped, and a head
  Codex did not review is recorded as such.

### Hard boundaries

- **Live work.** No live control-store operation during prep construction: no creating, initializing or
  binding the fresh store, no live SPEC run, and no provider, paid or credential work. Rehearse the
  procedure on scratch roots. Each live operation is prepared exactly and authorized separately by
  Stephen, as Phase 5 requires.
- **Live store.** It stays historical evidence. Never append to it (P-057, P-058).
- **Successor binding.** None until the delta assurance passes and Stephen records it.
- **No new structures.** No new plan, framework, persisted model, composite seal or speculative STORE
  change (D5). No replacement of `SpecOperatorConfig@1.0.0` without Stephen's decision.
- **Results directory.** No toy or synthetic output in `results/`.
- **Hooks, reviews and merges.** Never bypass hooks. Stephen controls CodeRabbit, merges and auto-merge.
  Do not apply a review stopping rule to a PR until Stephen accepts it for that PR.
- **06t (P-060).** Out of scope. It is dispatched only after Gate 6 closes.

### Handback

Lead with the applicable 06s §8 row. Then give:
- the exact SHA;
- the design pass, with its recommendations and the decisions Stephen needs to make;
- for any construction, the PRs, their certifications and known limits;
- verified Jira changes.
