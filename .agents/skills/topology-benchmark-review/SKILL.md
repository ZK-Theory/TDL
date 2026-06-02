---
name: topology-benchmark-review
description: Use when a topological result (persistence diagram, W2/landscape distance, regime detection) is asserted as correct — to check it against known published benchmarks and the project's validation table before trusting it.
---

# Topology Benchmark Review

Use this for the Topology lane. A persistent-homology pipeline can run end-to-end
and produce a plausible-looking diagram that is quantitatively wrong. Before a
topological result is used in a paper or as a downstream input, check it against
an external benchmark, not just internal consistency.

## Core Check

1. **Known-result anchor.** Compare against a published benchmark where one exists
   (e.g. Gidea-Katz 2017 for financial pre-crash L1/L2 norm trends) or the
   project's `validate-topology` benchmark table.
2. **Sanity of the diagram.** Off-diagonal features are real, not numerical noise;
   H0/H1/H2 counts are plausible for the construction; total persistence scales
   sensibly with the filtration.
3. **Metric direction.** W2/landscape distances move in the expected direction for
   a known perturbation (a controlled change increases distance).
4. **Replication.** The result reproduces across eras/cohorts where the theory
   predicts it should.

## Output Format

**MATCHES BENCHMARK / DEVIATES / NO BENCHMARK AVAILABLE**, with the benchmark
cited and the discrepancy quantified.

## Pressure Scenario

A topological result asserted as correct on internal consistency alone, with no
comparison to a published anchor — a silent quantitative error would pass.

## Related Skills & Contracts

- Pairs with `validate-topology` (the sanity checklist) and `wasserstein-audit`
  (W1/W2 and order/internal_p ambiguity).
- Enforcing contracts: `topology-invariants/*`.
