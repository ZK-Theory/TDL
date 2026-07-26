---
name: pre-reg-to-dispatch
description: Use when an APM Manager is converting a pre-registration, decision rule, or amendment into a Task Prompt — to extract the parameters, decision rule, and outcome-to-prose mapping, and to detect when a task needs a pre-reg amendment filed BEFORE dispatch.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - output-provenance
  roles:
    - manager
  runtime: agnostic
---

# Pre-Registration to Dispatch

Use this when turning a pre-registered design into a dispatchable Task Prompt. It
operationalizes the Manager pre-reg / decision-rule check and Task-Prompt
construction. The decisive question it answers: does this task merely *execute* an
existing pre-registered design, or does it *change* the decision rule or
parameters — in which case a pre-registration amendment must be filed and locked
before any dispatch.

## Procedure

1. **Locate the governing pre-registration.** Find the vault `[DECISION]` /
   pre-registration entry in `04-Methods/Computational-Log.md` and the
   machine-readable mirror (`pre_registrations_<YYYY-MM-DD>.json`). If none exists
   for an outcome-contingent run, stop — the pre-reg must be filed first.
2. **Extract the locked content.** Record: parameter values; the decision rule;
   the prose-direction-per-outcome mapping (what each outcome A/B/C licenses in the
   manuscript); and the pre-registration timestamp.
3. **Detect amendment need.** Compare the task's intended design against the
   pre-reg. If it changes a parameter, the decision rule, the null model, or the
   eligibility rule — it is NOT a routine rerun. Require a pre-registration
   amendment, filed and locked (dated, with rationale) *before* dispatch.
4. **Confirm the JSON mirror.** A machine-readable pre-reg JSON exists alongside
   the vault entry so the dispatched run can reference it by path.
5. **Emit the Research Assurance Requirements block.** Populate the block (lanes
   touched, governing pre-reg/decision rule, parameters and seeds, contracts in
   scope, machine-checkable vs human-review-only claims, Partial criteria) for the
   Task Prompt.

## Output Format

Produce: (a) a one-line verdict — *execute existing design* or *requires
amendment before dispatch*; (b) the extracted parameters / decision rule /
outcome-to-prose mapping; (c) the filled `Research Assurance Requirements` block
ready to paste into the Task Prompt.

## Pre-Dispatch Scoping (No Branch Yet)

When a Manager scopes a task **well before dispatch** — and no task branch exists yet —
do NOT write contract YAMLs into `contracts/` on `main`. They become orphan files:
the future worktree (created from committed `main`) will not contain them, and they can
trip the contract gate.

**Clean path:** embed the complete contract specification **inside the pre-registration**
as a `planned_contracts` array:

```json
"planned_contracts": [
  {
    "id": "wr-result",
    "kind": "result",
    "applies_to": "results/trajectory_tda/*_*.json",
    "required_keys": {"w2_pvalue": "float", "n_permutations": "int"},
    "decision_coupling_invariants": ["n_permutations >= 500"],
    "forbidden_keys": ["synthetic"],
    "binding_test": {"file": "tests/trajectory_tda/test_result_contract.py", "function": "test_wr_result_schema", "must_assert": true}
  }
]
```

Dispatch becomes mechanical: the Manager materialises the YAMLs from this spec onto
the task branch at dispatch time. Nothing lands on `main` prematurely.

**Authorship split at dispatch (who writes what).** The **Manager** materialises the
`planned_contracts` YAMLs onto the task branch (`pending: true`, with the binding block
naming the test file/functions the Worker will create) and runs the contract gate
validate-only *before* the Worker starts; the **Worker** writes ONLY the binding test
and clears `pending`. This keeps the spec independent of the party being validated.
Pre-flight: if the Task Prompt tells the Worker to author the contract YAMLs, STOP — that
collapses the spec/validation separation.

## Confirmatory / Bug-Fix Re-Run Scoping

When a dispatch corrects a *derived* statistic computed from an expensive *cached
upstream artifact* (e.g. a landscape-L² distance downstream of cached persistence
diagrams), scope the re-run to recompute only from that cache. Do NOT restate the
original full compute parameters (B, n) unless the fix actually invalidates the upstream
artifact — restating `B=1000` silently forces an unneeded PH recompute. Prefer an
old-vs-new delta on the cached intermediate as the confirmation.

When a task must **reproduce a stored baseline value**, diff each input's mtime/hash
against the baseline's date and require the producing module to embed a **fail-closed
canary** (refuse to write unless the recomputed value matches within tol). Code-level
reproducibility ("regenerate from the committed script") does not guarantee the *input*
is the same vintage the baseline used.

## Dispatch Safety

Every Task Prompt this skill produces must, in addition to the Research Assurance
Requirements block:

- Bound scope with explicit hard stops — "build/run X only; do NOT proceed to Y/Z" —
  rather than an open-ended "complete the plan."
- Restate any user-decision gate named in the pre-reg (e.g. PROMOTE, APPROVE) as
  **blocking**, not advisory.
- Forbid writing toy/synthetic/illustrative output to `results/` — that tree is for
  real, provenance-tracked compute only; toy compute stays in a scratch path or
  uncommitted.
- Pre-author every fallback deliverable named by a stop rule: exact statement,
  exact constants, and the authority that accepted it. A downstream executor
  may select an accepted branch; it may not invent a weaker claim when a branch
  fails.

Without these, an autonomous Worker reads the Task Prompt maximally, and a
date-stamped synthetic file in `results/` is a landmine by review time.

## Escalate Or Stop When

- No pre-registration exists for an outcome-contingent run.
- The task changes the decision rule or a parameter but no amendment is on file.
- The outcome-to-prose mapping is missing, so a result could not be interpreted
  without a post-hoc choice.
- A dispatch delegates contract-YAML authorship to the Worker (the Manager authors them
  at dispatch; the Worker writes only the binding test).
- A confirmatory/bug-fix dispatch restates full compute parameters (B, n) for a fix that
  only touches a downstream derived statistic.
- The governing pre-registration's value proposition claims a step is "usable in the
  pipeline" (a theorem, a preprocessing step, a scaling mechanism) without a one-grep
  confirmation that the pipeline actually contains that step, or an explicit "planned,
  adoption-gated" annotation naming the gate. A formal argument can be correct and still
  license nothing the codebase does — verify the referent, not just the derivation,
  before dispatch.

## Pressure Scenarios From This Repo

- T1.2g first13 asymmetric-L rerun changed the design and required a pre-reg
  amendment before any feasible run — dispatching it as routine would have
  baked in an unregistered choice.
- A methodology change disguised as a routine rerun: same script name, different
  decision rule.

## Related Skills & Contracts

- Pairs with `research-assurance-triage` (which produces the Task Prompt block)
  and `vault-sync` (which files the amendment).
- Enforcing artifact: `apm_task_prompt_check.py` (verifies the dispatched prompt
  carries the assurance block and explicit parameters).
