---
name: research-assurance-triage
description: Use when planning, dispatching, or reviewing TDL tasks that touch mathematical, statistical, topological, representation, output provenance, or paper-claim logic.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - topology
    - stochastic-null
    - statistical-panel
    - representation
    - output-provenance
    - paper-claim
  roles:
    - orchestrator
  runtime: agnostic
---

# Research Assurance Triage

Use this before an APM Manager dispatches or accepts work whose correctness is
scientific, not merely software-functional. A task can pass tests and still be
wrong if the formula, null model, topology, estimand, provenance, or paper claim
is wrong.

## Core Rule

APM owns coordination. This skill owns research-validity triage. Contracts and
hooks are enforcement tools, not the whole assurance process.

## Assurance Lanes

Classify each task against these lanes:

| Lane | Includes |
|---|---|
| Topology | PH construction, filtrations, H0/H1/H2 semantics, W2/landscape metrics, Mapper, zigzag, multipersistence, landmarks |
| Stochastic / Null Model | permutation exchangeability, Markov order, stratification, label/cohort/order shuffles, null-null construction, bootstrap, RNG, p-values |
| Statistical / Panel | IPW, MICE, FDR/BH/BY, GLMM/Firth/svyglm, Manski bounds, denominators, estimands, eligibility rules |
| Representation | PCA/UMAP/scaler fitting, frozen loadings, GMM labels, state recoding, windows, embedding comparability |
| Output / Provenance | JSON schema, cache path, date suffix, no overwrite, seeds, B/L/null params, vault trace |
| Paper Claim | pre-reg decision rules, outcome-to-prose mapping, table/figure claims, disclosure text |

## Manager Dispatch Checklist

Before writing a Task Prompt:

1. List touched assurance lanes.
2. Identify the governing pre-registration, decision rule, Spec lock, contract
   manifest, or vault/CONVENTIONS rule.
3. Decide which claims are machine-checkable.
4. For machine-checkable claims, choose at least one artifact: contract, binding
   test, output schema, validation command, smoke/canary, provenance check.
5. For human-review-only claims, state the review question explicitly.
6. If the task needs a changed decision rule or parameter design, require a
   pre-registration amendment before dispatch.
7. Add a `Research Assurance Requirements` section to the Task Prompt.
8. **Expected/sanity values are inputs to falsify, not targets.** Any expected
   value, sanity figure, or "lower bound" carried in a dispatch is to be
   independently re-derived, never reproduced-and-stopped. A "bound" is a value to
   test for tightness; a result landing suspiciously close to the quoted figure
   warrants an explicit "did I anchor?" check before reporting.
9. **Guard degenerate fallbacks.** For any statistic with a degenerate/identity
   fallback (returns a constant on empty/edge input — `n<2 → 1.0`, empty →
   identity), require an output-contract assertion that *excludes the degenerate
   constant* in the normal regime (value strictly inside the open interval) plus a
   binding test exercising the real computation against an independent oracle. A
   plausible in-range constant from a broken path passes lint, unit, and smoke.
10. **Verify supplied-source provenance.** When a task relies on an
    externally-supplied "framing" / "reference" / "primary" document, confirm
    authorship, venue, date, and authority class before weighting its claims, and
    check downstream prose attributes only what the source actually states. A
    source's authority is what it *is*, not what the prompt calls it.

## Task Prompt Block

Use this compact block and delete irrelevant rows:

```markdown
## Research Assurance Requirements

- Assurance lanes touched:
- Governing decision rule / pre-reg / contract manifest:
- Parameters and seeds that must be recorded:
- Contracts or schemas in scope:
- Machine-checkable claims:
- Human-review-only claims:
- Output and cache provenance requirements:
- Vault / CONVENTIONS obligations:
- Partial criteria: report Partial rather than weakening or bypassing these requirements.
```

## Worker Evidence Expectations

When a Task Prompt includes `Research Assurance Requirements`, the Worker
should return a `Research Assurance Evidence` section in the Task Log. It should
answer, for each touched lane:

- What requirement was checked.
- Which command, contract, schema, result file, cache, or code path supports it.
- Which parameters, seeds, null settings, or output paths were verified.
- Which claims remain human-review-only.
- Which gaps remain, if any; unresolved required evidence means Partial.

## Manager Review Checklist

Before accepting Success:

- Parameters, seeds, B, L, null model, Markov order, and sample restrictions match
  the prompt and pre-registration.
- P-value, FDR, bootstrap, effect-size, or estimator formulas match the governing
  design.
- Topological objects and interpretations match the claimed homology, metric, and
  filtration semantics.
- Output JSONs validate where schemas exist and expose required provenance fields.
- Caches are preserved, named distinctly, and not silently overwritten.
- Vault entries were actually written where required.
- Paper-facing conclusions follow the decision rule and cite result files.

## Escalate Or Stop When

- A machine-checkable claim has no enforcement artifact and no explicit reason.
- Code reality conflicts with the pre-registration or Task Prompt.
- A result supports a weaker claim than the prose direction assumes.
- A null model is invariant to the operation that is supposed to test it.
- A schema drops fields needed for downstream comparison or paper claims.

## Pressure Scenarios From This Repo

- T1.36 p-values used a diagnostic null-null cap as the denominator; tests passed
  but the Monte Carlo formula was wrong.
- T1.2g first13 needed a pre-reg amendment before any feasible asymmetric-L rerun.
- Label/cohort shuffles permuted already-embedded rows, making PH invariant to the
  null operation.
- LM sensitivity JSONs dropped T/d/mean fields needed for comparison tables.

## Lane Routing

Once lanes are classified, route to the lane skill for the judgment procedure and
to the enforcing contract for the deterministic check:

| Lane | Judgment skill | Deterministic enforcement |
|---|---|---|
| Topology | `validate-topology`, `wasserstein-audit`, `topology-benchmark-review` | `topology-invariants/*` contracts |
| Stochastic / Null Model | `markov-null-design`, `statistical-design-audit`, `null-operation-invariance-audit` | `monte-carlo-permutation-p-value`, `null-operation-changes-ph-input`, `markov-order-provenance` |
| Statistical / Panel | `statistical-design-audit`, `panel-estimand-audit` | `icc-cluster-bootstrap`, `rubin-pooling`, `normalised-ipw-trimming`, `mice-convergence-rule`, `svyglm-cluster-robust-se` |
| Representation | `representation-freeze-audit` | `frozen-loadings-null-threading`, `frozen-loadings-transform-only` |
| Output / Provenance | `result-provenance-review`, `reproducibility-package-review`, `sensitivity-comparison-review` | `*-output-json-validation`, `stage1-output-json-validation` |
| Paper Claim | `paper-claim-trace` | human-review-only (no contract) |

Cross-cutting: `pre-reg-to-dispatch` converts a pre-registration into the Task
Prompt block (Manager-facing); `schema-contract-design` is the procedure for
adding a new enforcing contract; `tda-experiment` covers result JSON schemas and
experiment logging.
## Artefact-stage routing

Classify the subject before selecting assurance: a plan needs design/dispatch scrutiny, while produced results need provenance, statistical, reproducibility, and claim checks. A result-shaped artefact must not be routed as a plan merely because it contains future-work language, and a plan must not receive result assurance before evidence exists.
