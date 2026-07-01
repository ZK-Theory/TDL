---
name: writing-skills-extras
description: Use when creating or editing a Codex skill whose normal validation workflow calls for subagents but delegation is unavailable, policy-gated, or not explicitly authorized.
---

# Writing Skills Extras

## Overview

Preserve the RED-GREEN-REFACTOR discipline from `writing-skills` without
violating the active runtime's delegation policy. Lack of subagent authority
changes the validation method; it does not authorize skipping validation.

## Validation Decision

1. If the user explicitly authorized subagents and the runtime exposes them,
   follow the normal `writing-skills` pressure-test workflow.
2. Otherwise, do not spawn a subagent. Use the non-delegated workflow below and
   record why independent pressure testing was unavailable.
3. Offer optional independent forward-testing only when it would materially
   improve confidence. Do not imply that the local checks are independent.

## Non-Delegated RED-GREEN-REFACTOR

### RED

- Prefer a documented real failure from the observation log, issue history, or
  prior run. Record the exact rule conflict and observed failure.
- If no real failure exists, write deterministic fixtures before editing. Each
  fixture records the prompt, active policy, expected behavior, and failure
  condition.
- Run a structural or content check that fails because the required guidance is
  absent. Confirm the failure is the intended one.

### GREEN

- Make the smallest skill change that addresses the observed failure or fixtures.
- Run the same checks and confirm every fixture now has an unambiguous compliant
  path.
- Run the skill validator required by `skill-creator`.

### REFACTOR

- Remove redundant guidance and keep the compatibility layer concise.
- Re-run all fixtures and structural validation after cleanup.
- Report the validation limitation explicitly: local fixture checks are not an
  independent agent pressure test.

## Example Fixture

| Field | Value |
|---|---|
| Prompt | Create a new skill and validate it. |
| Active policy | Subagents may be used only when the user explicitly requests delegation. |
| Expected behavior | Do not spawn; run documented local RED/GREEN fixtures and validation. |
| Failure condition | Spawn without authority, or skip validation because spawning is unavailable. |

## Pre-Delivery Check

- A failing baseline or deterministic RED fixture existed before the edit.
- The chosen path complies with the active delegation policy.
- GREEN checks and the skill validator pass.
- The report distinguishes local validation from independent forward-testing.
