# /validate-topology — Validate Topological Results

Check mathematical correctness of TDA results against known benchmarks and internal consistency checks.

## Usage

```
/validate-topology [domain] [result-file]
```

Example: `/validate-topology trajectory_tda results/trajectory_tda_integration/04_nulls_wasserstein.json`

---

## Validation checklist

### Persistence diagram sanity

- [ ] All birth values ≥ 0
- [ ] All death values > birth (finite features)
- [ ] H₀ has exactly one infinite feature (the final connected component)
- [ ] Feature counts are plausible for landmark count L: H₀ has L-1 finite features; H₁ count varies

### Total persistence scaling

- [ ] Total persistence scales approximately linearly with L (±15% across a 2× range)
- [ ] Maximum persistence is stable across L values (should vary < 5%)

### Null model consistency

- [ ] Label/cohort shuffle p-values are non-significant (negative control)
- [ ] Markov-2 null generates more total persistence than Markov-1 (higher-order Markov → more structured surrogates)
- [ ] Null distribution standard deviations are plausible (not near-zero, not huge)

### Wasserstein-specific

- [ ] W(obs↔null) and W(null↔null) are of comparable magnitude (within ~3×)
- [ ] p-value = proportion of null-null distances ≥ mean(obs-null distances)
- [ ] 500 null-null pairs is sufficient for stable p-value at 3 decimal places

### Cross-era replication

- [ ] BHPS-era order-shuffle H₀ p-value ≈ USoc order-shuffle direction (both significant or both not)
- [ ] BHPS-era Markov-1 direction ≈ USoc (both non-significant under total persistence)

## Known benchmarks (trajectory_tda / P01)

| Test | Expected | Source |
|---|---|---|
| USoc order-shuffle H₀ (total persistence, L=5000) | p < 0.005 | P01 v5 Table 2 |
| USoc Markov-1 H₀ (total persistence) | p = 1.000 | P01 v5 Table 2 |
| USoc Markov-1 H₀ (Wasserstein, L=2000) | p = 0.002 | P01 v5 Table 2b |
| BHPS order-shuffle H₀ | p = 0.000 | P01 v5 §4.7 |
| BHPS Markov-1 H₀ | p = 1.000 | P01 v5 §4.7 |
| GMM bootstrap ARI | 0.646 ± 0.086 | P01 v5 §3.5 |
