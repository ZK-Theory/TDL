---
name: assay
description: Use when a Discovery Harness backlog candidate needs viability scoring before any Spike or APM dispatch, especially for topology-earns-its-keep, data feasibility, novelty, PROMOTE/PARK/KILL, or assay scorecard work.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - topology
  roles:
    - orchestrator
    - manager
  runtime: agnostic
---

# Assay

Cheap front-door viability scoring for the Discovery Harness. Use this after
`/scout-review` has added a `state: triaged` candidate to
`vault/00-Meta/Discovery/_backlog.md`, and before any compute-heavy Spike or APM
worktree exists.

## Core Rule

Run Axis 1 first as an adversarial gate. If topology does not earn its keep,
KILL at zero compute cost. Programme fit is deliberately excluded from scoring.

## Pre-flight Self-check

Before emitting a scorecard, re-read:

1. `docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md` section 5.
2. The candidate's inbox/backlog entry and any linked paper/abstract metadata.
3. This rubric:
   - Axis 1 gate must pass before PROMOTE is possible.
   - Axis 2 and Axis 3 are integers from 0 to 3.
   - PROMOTE iff Axis 1 passes and Axis2 + Axis3 >= 4 with neither score at 0.
   - PROMOTE is a user-decision point, not automatic execution.
   - Do not add programme_fit to the machine-readable block.

## Procedure

1. **Locate the candidate.** Read `vault/00-Meta/Discovery/_backlog.md` and the
   source inbox note. Assay only `state: triaged` candidates unless the user
   explicitly supplies a candidate.
2. **Gather minimal evidence.** Use the Scout abstract, linked metadata, and
   existing project context. Do not start compute. If the abstract is too thin
   for Axis 1, PARK with the missing evidence named rather than guessing.
3. **Axis 1 - Topology earns its keep (gate).** Argue the null: why TDA is not
   needed here. Require all of:
   - a genuine metric space, not raw trajectories without a justified embedding;
   - a specific topological feature mapped to a falsifiable substantive claim;
   - a named non-TDA baseline the TDA claim must beat;
   - the claim is not reducible to clustering, PCA, GMM, or ordinary regression.
4. **Axis 2 - Data feasibility (0-3).** Score whether the metric space is
   realizable on available or obtainable data, sample size supports a null, the
   embedding is defensible, and BHPS/USoc coding issues are handled where needed.
5. **Axis 3 - Novelty and publishability (0-3).** Score the literature gap,
   distinctness from existing benchmarks, and an identifiable target venue. A
   citation used to justify KILL (a paper claimed to already do this, a
   near-miss) is more dangerous wrong than one justifying an inclusion — a
   wrong inclusion is caught at the next gate, a wrong exclusion silently
   removes the candidate forever. Verify any kill-justifying citation directly
   (fetch it, confirm it says what it is claimed to say, not just that a
   search tool returned it) before it can KILL a candidate.
6. **Decide.**
   - `KILL`: Axis 1 fails, data are inaccessible, or a red flag is decisive.
   - `PARK`: evidence is insufficient or scores are not strong enough for Spike.
   - `PROMOTE`: gate passes and Axis2 + Axis3 >= 4 with neither score at 0.
7. **Write the candidate note.** Create/update
   `vault/00-Meta/Discovery/<slug>.md` with concise prose plus the fenced
   machine-readable block below.
8. **Validate the block.** Use
   `trajectory_tda.discovery.assay_scorecard.extract_scorecard_block` and
   `validate_assay_scorecard` before reporting the Assay as done. For a
   multi-application note (two or more `assay_scorecard` blocks in one
   candidate note — a legitimate pattern for two papers/applications assessed
   together), `extract_scorecard_block` returns only the **first** block —
   iterate and validate every block explicitly (collect text between each
   pair of fence markers, reset, continue to the next) rather than trusting a
   single call; the standard extractor silently under-validates the second
   application.
9. **Update `_backlog.md`.** Change the candidate state to `assayed`, record the
   decision, score summary, scorecard note path, and next action. Keep `_backlog.md`
   the single source of truth for lifecycle state.

## Machine-readable Block

Use this exact fenced block label:

````markdown
```yaml assay_scorecard
schema_version: discovery/assay-scorecard/v1
candidate_id: arXiv:2606.11911
candidate_slug: from-persistence-to-survival
assayed_at: "2026-06-16"
source: _inbox/2026-W25.md
axis1_topology_gate:
  passes: true
  metric_space: Persistence diagrams with a named diagram metric.
  feature_claim_map: H1 persistence shift maps to a falsifiable survival contrast.
  reducible_to_baseline: false
  named_baseline: Cox model on non-topological summary features.
  adversarial_null: A standard survival baseline could explain the claim without PH.
axis2_data_feasibility:
  score: 2
  rationale: Existing outputs can provide diagrams; panel transfer needs a toy probe.
axis3_novelty_publishability:
  score: 2
  rationale: Clear methods gap with identifiable statistical-methods venues.
decision: PROMOTE
decision_rationale: Gate passes and scored axes sum to 4 with neither score at 0.
next: /spike
```
````

The enforcing contract is `contracts/discovery-harness/assay-scorecard.yaml`;
the binding test is `tests/discovery/test_assay_scorecard_contract.py`.

## Validation Snippet

```python
from pathlib import Path
from trajectory_tda.discovery.assay_scorecard import (
    extract_scorecard_block,
    validate_assay_scorecard,
)

note = Path("vault/00-Meta/Discovery/<slug>.md").read_text(encoding="utf-8")
validate_assay_scorecard(extract_scorecard_block(note))
```

## Escalate Or Stop When

- Axis 1 cannot name a metric space, falsifiable feature-to-claim mapping, and
  baseline. KILL or PARK; do not soften the gate.
- The only reason to continue is "it fits the programme." Programme fit is not a
  score axis.
- PROMOTE would bypass the user-decision point or start compute immediately.
- The scorecard block fails validation. Fix the block before updating backlog.
- A KILL decision rests on a citation that has not been directly verified —
  fetch and confirm it before finalizing KILL.
