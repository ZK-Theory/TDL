# Assay Playbook

Use this when no skill wrapper is available and a worker must score a triaged
Discovery candidate before any Spike or APM dispatch.

## Inputs

- `vault/00-Meta/Discovery/_backlog.md`
- The source `_inbox/YYYY-Www.md`
- `docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md` section 5
- `contracts/discovery-harness/assay-scorecard.yaml`

## Procedure

1. Read the candidate and source evidence.
2. Run Axis 1 first as an adversarial hard gate: metric space, falsifiable
   topological feature-to-claim map, reducibility check, and named baseline.
3. Score Axis 2 data feasibility from 0 to 3.
4. Score Axis 3 novelty and publishability from 0 to 3.
5. Decide `PROMOTE`, `PARK`, or `KILL`. PROMOTE requires the gate to pass and
   Axis2 + Axis3 >= 4 with neither score at 0.
6. Write `vault/00-Meta/Discovery/<slug>.md` with a fenced
   `assay_scorecard` block.
7. Update `_backlog.md` to `state: assayed`, recording decision, scores, note
   path, and next action.

## Outputs

- Candidate assay note with `assay_scorecard` block.
- Updated `_backlog.md` entry.

## Validation

Run `validate_assay_scorecard` from
`trajectory_tda.discovery.assay_scorecard` against the fenced block. The
scorecard must not contain programme-fit scoring.
