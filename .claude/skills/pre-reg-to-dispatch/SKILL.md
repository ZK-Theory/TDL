---
name: pre-reg-to-dispatch
description: Use when an APM Manager is converting a pre-registration, decision rule, or amendment into a Task Prompt — to extract the parameters, decision rule, and outcome-to-prose mapping, and to detect when a task needs a pre-reg amendment filed BEFORE dispatch.
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

## Escalate Or Stop When

- No pre-registration exists for an outcome-contingent run.
- The task changes the decision rule or a parameter but no amendment is on file.
- The outcome-to-prose mapping is missing, so a result could not be interpreted
  without a post-hoc choice.

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
