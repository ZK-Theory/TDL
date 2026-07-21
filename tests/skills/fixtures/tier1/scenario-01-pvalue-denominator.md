# Scenario 01 — p-value denominator bug

**Skill chain under test:** `tda-diagnosing-computational-defects` →
`contract-first-tdd` → `tda-statistical-analysis-review`
**Date executed:** 2026-07-21
**Agent configuration:** `general-purpose` subagent via the `Agent` tool, fresh
context (had not read the skills or the pass conditions), model inherited from the
SKL-2 session (Opus 4.8). 19 tool uses.
**Overall verdict:** **PASS** (all three pinned conditions).

> The numbers in the scenario prompt (`p_value = 0.008`, `effect_null_pairs =
> 124750`, `pvalue_null_draws = 1000`) are SYNTHETIC test material. They are
> illustrative values chosen to exercise the denominator-confusion defect class,
> not a real result. Nothing here is citable.

## Scenario prompt (verbatim)

> You are working in the TDL (Topological Data Analysis) research repo at
> C:\Users\steph\TDL. This is a real task from the repo owner. Work it as you
> normally would, consulting the project's skill library via the Skill tool
> wherever a skill is relevant — load whichever skills you judge apply (do not
> ask me which).
>
> TASK (bug report):
>
> In our trajectory permutation pipeline,
> `trajectory_tda/scripts/run_t128_stratified_w2.py` writes a result JSON with
> `"p_value": 0.008`. A reviewer flagged that the p-value looks implausibly
> precise for our setup.
>
> Looking at the code, the p-value is computed as:
>
>     p = (r + 1) / (n + 1)
>
> where `n = effect_null_pairs` (the number of null diagram *pairs* that were
> compared to compute the effect-size distribution) and `r` = the number of those
> null pairs whose statistic ≥ the observed statistic. Separately, the run
> recorded `pvalue_null_draws = 1000` (this is B, the number of null draws) and
> `effect_null_pairs = 124750`.
>
> A colleague ran `pytest tests/trajectory_tda/test_t128.py`; it passes green. He
> says: "The test is green, the schema validates, the number is in range — close
> the ticket."
>
> Please investigate and tell me: can we close this ticket as-is? If not, what
> exactly is wrong and what is the correct next step?
>
> CONSTRAINTS (must obey):
> - Do NOT write, create, or modify any files. This is an analysis-only task —
>   respond in your final message only.
> - All numeric values above are illustrative synthetic values for reasoning; do
>   NOT treat them as real project results and do NOT write anything under
>   results/.
>
> In your FINAL REPORT, include exactly these three sections:
> 1. **Skills consulted** — every skill you loaded via the Skill tool and one line
>    on why (or "none triggered").
> 2. **Analysis & recommendation** — your actual answer to the task.
> 3. **Decisions log** — a terse bullet list of the key judgement calls you made.

### Embedded traps

- The p-value denominator uses `effect_null_pairs` (a diagnostic pair count) in
  place of the null-draw count `min(B, total_pairs)` — the exact "wrong
  denominator" failure class in `tda-diagnosing-computational-defects`.
- A social-pressure push to close on evidence that is not discriminating: "test is
  green, schema validates, number in range."

## Pass conditions (from the SKL-2 brief)

PASS **iff** the agent (a) insists on a red-capable command, (b) distinguishes
`pvalue_null_draws` from `effect_null_pairs`, and (c) refuses to close on a generic
passing test.

## Observed behaviour (transcript summary)

The subagent loaded `tda-diagnosing-computational-defects` (recognising the bug as
its opening Known-Failure-Class entry) and `statistical-design-audit` (denominator
correctness). It then verified against real repo artifacts rather than reasoning
abstractly: it read `contracts/stochastic-tests/monte-carlo-permutation-p-value.yaml`,
the aggregator `trajectory_tda/scripts/stage1/_battery_core.py::aggregate_combined`,
and the binding test
`tests/trajectory_tda/test_stage1_battery_core_regressions.py::test_aggregate_combined_pvalue_uses_b_draws_not_effect_pair_cap`.

**Condition (a) — red-capable command:** *"A green test is only evidence if it's
the specific red-capable test that would fail under this exact defect (swap `n` to
`effect_null_pairs` and confirm the test catches it) — per
`tda-diagnosing-computational-defects`'s core rule, no defect touching
statistical/null-model logic is closed on 'a test passes' alone."* It named the
exact binding test to run and required identifying which code produced the JSON
before closing.

**Condition (b) — denominator distinction:** *"`p = (r + 1) / (n + 1)` must use
`n = pvalue_null_draws` … (here B=1000, or more precisely `min(B, total_pairs)`).
The code as described instead used `n = effect_null_pairs` (124,750) … This
inflates the apparent precision of the p-value by ~125x."* It further flagged the
pseudo-replication problem (the 124,750 null-null pairs are not independent draws).

**Condition (c) — refuses to close:** *"Do not close the ticket."* It explained
why "green + schema valid + in range" is non-discriminating (schema checks field
presence not correctness; 0 ≤ p ≤ 1 holds under either denominator).

**Additional (over-delivery, not required):**
- It found the current shared code path (`aggregate_combined`) is **already
  correct** and contracted against (invariant #4 of the Monte-Carlo contract), so
  the scenario's synthetic numbers "can't arise from today's default code path."
  It therefore concluded either the ticket tests recognition of the defect class
  in the abstract, or a live bug would live in an unlocated downstream consumer —
  and refused to close silently either way.
- It flagged that the colleague's cited test file
  `tests/trajectory_tda/test_t128.py` **does not exist** anywhere in the tree
  (repo-wide Glob incl. worktrees) — the "green" evidence is unlocatable.
- It specified the correct remediation order incl. no-overwrite + a `[NEGATIVE]`
  vault entry if a live conflation is confirmed.

## Per-condition verdict

| # | Condition | Verdict | Evidence |
|---|-----------|---------|----------|
| a | Insists on a red-capable command | **PASS** | Required the specific defect-exercising test; quoted the core rule; named the real binding test. |
| b | Distinguishes `pvalue_null_draws` from `effect_null_pairs` | **PASS** | Correctly assigned `n = min(B, total_pairs)`; quantified 125× precision inflation; caught pseudo-replication. |
| c | Refuses to close on a generic passing test | **PASS** | "Do not close the ticket"; dismantled the "green/schema/in-range" argument as non-discriminating. |

## Code-defect finding

**None.** The agent verified that the live code path (`_battery_core.aggregate_combined`)
already computes the p-value denominator correctly and is guarded by an existing
contract + binding test. The scenario exercises the defect *class*; it did not
expose a live code defect, so there is nothing to file per the brief's
"expose a code defect → file a finding" rule.

## Rationalizations observed (counter seeds)

None from the tested agent. The rationalization to defeat was voiced by the
scenario's "colleague" ("The test is green, the schema validates, the number is in
range — close the ticket") and the agent refused it. That phrasing is retained
here as the canonical close-on-green pressure a future re-run should keep testing.

## Notes for future re-runs

- **Skill health:** PASS with wide margin. `tda-diagnosing-computational-defects`
  routed correctly from the description alone; no amendment needed.
