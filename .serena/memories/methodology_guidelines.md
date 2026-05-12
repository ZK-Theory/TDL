# TDL Methodological Guidelines

## TDA Core Principles

### Distance Metrics (Mandatory)
- **Wasserstein-2 distance**: PRIMARY metric for persistence diagram comparisons
- **Persistence landscape L² distance**: MANDATORY complementary metric alongside Wasserstein-2
- **Bottleneck distance**: Insufficient as primary metric (captures only single worst discrepancy)
- **Never use bottleneck distance alone**

### Hypothesis Testing
- **Permutation nulls**: Standard for hypothesis testing on persistence features
- **Bootstrap resampling**: n=1000 for confidence intervals on topological summaries
- **FDR correction**: Benjamini-Hochberg for multiple comparisons
- **Always specify Markov order k** when describing null models

### Data Processing Rules

#### Financial Data
- Persistence thresholds tuned per domain (financial: shorter windows)
- Never apply persistent homology directly to raw time series
- Always embed first (Takens embedding, UMAP, etc.)

#### BHPS/Understanding Society Data  
- **Never assume variable coding is consistent** between BHPS and Understanding Society
- **Always check wave documentation** before assuming coding consistency
- **Verify harmonised variables** explicitly - don't infer properties

### Implementation Requirements

#### Python Code Standards
- **Type hints mandatory** with `numpy.typing.NDArray` (not bare `np.ndarray`)
- **Google-style docstrings** for all public functions
- **Random seeds specified and recorded** for all stochastic processes
- **Research context header** on every new script

#### Mathematical Validation
- All TDA functions must have validation tests
- Compare against known results where possible
- Verify mathematical invariants (birth ≤ death, etc.)
- Use established tolerance levels (10% for Betti numbers per Gidea-Katz)

## Research Workflow Mandates

### Empiricism-First Ordering
- Data analysis precedes prose for same section
- Wait for results to land in `results/` before drafting dependent prose
- Outcome-contingent prose requires vault `[DECISION]` entry first

### Vault Discipline  
- Every computational task ends with appropriate vault entry
- Pre-registration entries written BEFORE outcome-contingent runs
- Results format: parameter values, decision rule, prose-direction per outcome

### No Speculative Paths
- Do not pursue analyses on "probably true" or "should hold" foundations
- Verify properties before relying on them
- Surface uncertainty as user-decision points rather than guessing

### Cross-Domain Consistency
- Locked notational decisions in `papers/shared/notation.md`
- Never let two papers use divergent notation for same object
- Check `/notation-check` after every prose change