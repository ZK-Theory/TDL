# Proposal: verify on-disk state before dispatch / handoff / acceptance

**Status:** PROPOSAL — awaiting Stephen's approval (ARS gate change; not self-applied)
**Date:** 2026-07-21 · **Source:** weekly system review, skill-observations 58, 65, 68, 70, 73, 74, 76, 79, 80
**Owner decision required:** yes (gate + skill-guidance change)

## Problem

The single largest recurring failure cluster in the observation log: a dispatch,
handoff, or pre-registration prompt states things about the world as **facts**
that are already stale by execution time, and an agent acts on the assertion
instead of checking. Recurrences confirm it is systemic, not incidental:

- **58 → 80:** a task-prompt's "not dispatched / open" state was stale; the
  deliverable was already on disk. Correct move was to convert the author lane
  to review-only, not re-dispatch. It recurred verbatim.
- **68 → 73:** pre-reg `planned_contracts` reached the Worker unmaterialised;
  the extraction-agent rescue worked, then the *same* thing happened again.
- **65:** a dispatch prompt's claims about reference files are assertions, not
  findings — scope must be verified before trusting it.
- **70:** a Handoff prompt's "standing facts" and "blockers" decay fastest —
  the blocker must be verified before inheriting the plan built on it.
- **74:** pre-reg input paths carry no root declaration — a Worker cannot tell a
  committed file from a `PROJ_ROOT`-only intermediate until the script crashes.
- **76:** an owner-touchpoint precondition buried in a sub-plan's prose never
  surfaced into the gate checklist.
- **79:** brief-mandated output paths can be gitignored — trackability must be
  verified before authoring.

The common shape: **self-attestation of state** with **no re-validation trigger**
— exactly the two failure mechanisms the project's own failure inventory names.

## Proposed mechanism

Add a **state-verification step** to the dispatch/acceptance gates, driven by an
explicit machine-checkable manifest in each Task Prompt rather than prose.

### The Task-Prompt state manifest (define before the gate)

"Machine-checkable manifest" is not itself an implementation contract; two gate
implementations reading the same prose would diverge. So the manifest schema is
fixed **first**, and the gate is written against it. Proposed shape — a
`state_manifest:` block (YAML) in each Task Prompt, or a sidecar
`contracts/manifests/task-state/<task>.yaml`:

```yaml
task_id: <string, required>          # identity anchor; every claim is scoped to this Task
deliverables:                        # list; may be empty
  - path: <repo-relative string, required>
    root: worktree | proj_root       # required; resolves the path (default worktree)
    owner_task: <task_id, required>  # which Task is expected to have produced it
    completion_predicate: <string, required>
      # a runnable one-liner that exits 0 iff the artifact is complete for THIS task
      # (e.g. a jq field assertion, a schema-validate call, a row-count check)
blockers:
  - id: <string, required>
    check: <string, required>        # one-liner; exit 0 == blocker STILL true
planned_contracts:
  - id: <string, required>           # contract identifier, not just a filename
    path: <contracts/... string, required>
    ready_status: <string, required> # the field+value that means "authorized/ready"
                                     # (e.g. pending == false)
inputs:                              # (obs 74) — as in the input-provenance manifest
  - path: <string, required>
    root: worktree | proj_root       # required
outputs:
  - path: <string, required>         # (obs 79) git-trackability is asserted, see below
```

**Status values / missing-field behaviour (fail closed):** a *required* field
absent or unparseable → the gate **errors** (env-error, not a silent pass) and
names the field. An empty list is legal and means "no claim of this kind".
Every predicate/check one-liner is **executed**, not read: a claim whose command
is missing or non-zero-exit-on-setup is treated as unverified → block.

### The gate

1. **Extend `dispatch-readiness-guard.sh`** — the wired `.claude/hooks`
   enforcement point (registered in `.claude/settings.json`) — with
   `shared.manager_dispatch_check` as its **read-only predicate** (the guard
   invokes the check; the check computes PASS/FAIL and the guard enforces it).
   For every dispatched Task the check verifies on disk:
   - each **deliverable**: existence at `path` is necessary but **not
     sufficient**. The lane is downgraded to review-only *only* when the file
     exists **and** its `owner_task` matches **and** its `completion_predicate`
     exits 0. A file that is stale, partial, or produced by an unrelated task
     fails the predicate → fresh dispatch is retained (obs 58/80, but guarded
     against false-suppression).
   - each **blocker**: re-run `check`; exit 0 means still-true → the plan built
     on it may proceed, otherwise the inherited assumption is stale and is
     flagged (obs 70).
   - each **planned_contract**: verify the file at `path` exists **and** that its
     declared identifier matches `id` **and** that `ready_status` holds — a
     contract file can exist while still `pending: true`, which is exactly the
     infrastructure-ready-vs-contract-ready confusion this proposal prevents;
     presence alone never satisfies the criterion (obs 68/73).
   - each **input path**: is its `root` declared (committed vs `PROJ_ROOT`-only)
     and does it resolve? (obs 74).
   - each **output path**: is it git-trackable, not gitignored? (obs 79).
2. **Validation fixtures — one paired positive/negative control per predicate**,
   so every branch of the gate has a watched failure and cannot pass by
   path-existence alone. Each fixture is a Task Prompt manifest with a documented
   expected outcome:
   - **deliverable** — file exists **and** passes its completion predicate under
     the matching `owner_task` → downgraded to review-only; companion file exists
     but fails the predicate (stale/partial/foreign `owner_task`) → **still**
     dispatched.
   - **blocker** — `check` exits 0 (still-true) → dependent plan proceeds;
     companion `check` exits non-zero (stale assumption) → **flagged/blocked**.
   - **planned_contract** — file exists with `ready_status` satisfied → passes;
     companion file exists but `pending: true` → **blocked** (presence ≠ ready).
   - **input** — path resolves under its declared `root` → passes; companion with
     an unresolved or wrong `root` (committed-vs-`PROJ_ROOT` mismatch) →
     **errored/blocked**.
   - **output** — path is git-trackable → passes; companion path that is
     gitignored/untrackable → **blocked** (obs 79).
   - **fully-valid positive** — a manifest where every predicate holds → dispatched
     cleanly, proving the gate is not blocking unconditionally.
   Both directions of each predicate are asserted; the expected outcome is
   recorded alongside each fixture so a regression that inverts a branch is caught.
3. **Skill propagation** (a short "verify state on disk before acting" step) to
   `pre-reg-to-dispatch`, `tda-handoff`, `tda-task-brief-from-plan`,
   `apm-communication` — pointing at the gate, not restating it.

## Owner decision points

- Is the Task-Prompt state manifest (deliverables/blockers/contracts/inputs/
  outputs as structured fields) acceptable as a required dispatch input?
- Should the gate **block** (exit 1) on a stale-state finding, or **warn**?
- Scope: apply to all dispatches, or only result-bearing (assurance-lane) ones?

## Non-goals

Not a re-litigation of any specific past dispatch. Not a change to the ARS
review ladder. Purely: convert "the prompt says X about the world" into "the
gate checked X on disk before anyone acted".
