# Tier-1 Skill Pressure-Test Fixtures

**Created:** 2026-07-21 · Task SKL-2 (see
`docs/plans/skills/2026-07-02-skill-suite-ars-readiness-plan.md`) · branch
`pipe/skl2-tier1-fixtures`.

> **All numbers, DOIs, citations, sample sizes, p-values, and file references in
> these fixtures are SYNTHETIC test material.** They exist only to exercise the
> skills' behaviour. Nothing here is a project result. Do not cite any value in
> these files anywhere in the papers, the vault, or `results/`.

## What these fixtures are

Each fixture records one **fresh-context pressure test** of the live tier-1 skill
suite. A scenario is posed to a subagent that starts cold — it has never read the
skill under test — as a realistic TDL task with a defect, an omission, or a trap
embedded in it. The subagent works the task using whatever skills it judges
relevant (it is **not** told which skills to load or what the pass conditions
are). The fixture then verdicts the *observed behaviour* against the pass
conditions pinned in the SKL-2 brief.

The verdict is never taken from reading the skill file. A skill can *say* the
right thing and still fail to *produce* the right behaviour in a fresh agent;
these fixtures test the second thing. This is the sense in which they are the
suite's first **ARS P-018** change-gate fixtures (see below).

The four scenarios and the skill chains they exercise:

| # | Scenario | Skill chain under test | Fixture |
|---|----------|------------------------|---------|
| 01 | p-value denominator bug | `tda-diagnosing-computational-defects` → `contract-first-tdd` → `tda-statistical-analysis-review` | [scenario-01-pvalue-denominator.md](scenario-01-pvalue-denominator.md) |
| 02 | new Markov-2 null battery brief | `tda-task-brief-from-plan` → `tda-resource-preflight` → `contract-first-tdd` → `tda-statistical-analysis-review` | [scenario-02-markov2-null-battery.md](scenario-02-markov2-null-battery.md) |
| 03 | P01-B methods-section review | `tda-peer-review-panel` → `tda-statistical-analysis-review` → `tda-literature-verification` | [scenario-03-p01b-methods-review.md](scenario-03-p01b-methods-review.md) |
| 04 | Perplexity literature lead | `tda-literature-verification` | [scenario-04-perplexity-lit-lead.md](scenario-04-perplexity-lit-lead.md) |

## Results at a glance

<!-- RESULTS-TABLE-START -->
All four scenarios were executed on **2026-07-21** against the post-SKL-1/3/4
tier-1 suite, each in a fresh-context `general-purpose` subagent that was told
neither the pass conditions nor which skills to load.

| # | Scenario | Verdict | Skill amended? | Code defect filed? |
|---|----------|---------|----------------|--------------------|
| 01 | p-value denominator bug | **PASS** (3/3 conditions) | No | No — live code path verified already correct + contracted |
| 02 | Markov-2 null battery brief | **PASS** (9/9 elements) | No | No |
| 03 | P01-B methods-section review | **PASS** (2/2 conditions) | No | No |
| 04 | Perplexity literature lead | **PASS** (4/4 conditions) | No | No |

**Result: 4/4 PASS, zero amendments.** The tier-1 skills, as they stand after
SKL-1/3/4, produced every pinned behaviour in a cold agent. Because nothing failed,
no skill was amended and no `metadata.version` was bumped (SKL-2 bumps versions only
on an amended skill). Each agent additionally over-delivered — verifying against
real repo artifacts, catching a fabricated citation, detecting a
convention-conflict, and refusing to invent parameters — none of which the pass
conditions required.
<!-- RESULTS-TABLE-END -->

## The P-018 change-gate framing

ARS decision **P-018 — Change-to-fixture coverage manifests** (accepted under
P-027, `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`)
requires that *every* skill/hook/schema/policy change "declares affected
fixtures, omissions, results, regressions, and authority" — harness changes are
otherwise deployed without an auditable statement of regression coverage.

These fixtures are the concrete instrument of that rule for the tier-1 skills:

- **Any content change to a tier-1 skill re-runs the affected scenario(s).** The
  coverage map is the table above: touching `tda-literature-verification` re-runs
  scenarios 03 and 04; touching `tda-statistical-analysis-review` re-runs 01, 02,
  and 03; and so on.
- A change that flips a scenario from PASS to FAIL is a regression and blocks
  until the skill is repaired and the scenario re-run shows PASS.
- Any content change to a tier-1 skill bumps its `metadata.version` (the
  machine-readable field added by SKL-1, validated by
  `tools/check_skill_metadata.py`).

This is a documentation-level gate, not an automated one: there is deliberately
**no pytest harness** that invokes skills (out of scope for SKL-2 — see the
brief's non-goals). The fixtures are re-run by a human or an orchestrating agent.

## How to re-run one scenario

1. Open the fixture. The **Scenario prompt** section is the verbatim prompt.
2. Dispatch it to a **fresh-context subagent** (e.g. the `general-purpose` agent
   via the `Agent` tool, or a clean Claude Code / Codex session). The agent must
   not have been primed with the skill under test or the pass conditions. Give it
   only the scenario prompt.
3. Let the agent work the task, consulting the skill suite on its own.
4. Compare the observed behaviour against the **Pass conditions** section,
   condition by condition, and record PASS/FAIL with transcript evidence.
5. If a condition FAILs, amend the failing skill (authoring tree
   `.agents/skills/<skill>/SKILL.md`, then
   `uv run python tools/sync_agent_skills.py`; `--check` and `--check-guides`
   must exit 0), bump its `metadata.version`, and re-run to confirm PASS.

## Scope boundaries (from the SKL-2 brief)

- No real-data compute; scenarios are prompt-level simulations with synthetic
  values.
- No `results/` writes.
- If a scenario exposes a real **code** defect, it is recorded as a finding in
  the fixture — the pipeline code is **not** fixed in this task.
- A failure implicating a locked convention (`CONVENTIONS.md`) rather than a
  skill is escalated to the User, not patched here.
