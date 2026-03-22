# HMM τ-Augmented Model Report

**Generated:** 2025-12-17 20:39

## Model Configuration

| Parameter | Value |
|-----------|-------|
| States | 3 |
| Features | ret_1d, ret_5d, ret_21d, vix, vix_5d_chg, **τ** |
| τ included | **Yes** (augmented) |
| Observations | 5988 |

## Model Fit Metrics

| Metric | Value |
|--------|-------|
| Log-likelihood | -34384.19 |
| AIC | 68942.38 |
| BIC | 69525.06 |
| Parameters | 87 |

## State Distribution

| State | Days | Percentage |
|-------|------|------------|
| Transition | 2415 | 40.3% |
| Calm | 2531 | 42.3% |
| Crisis | 1042 | 17.4% |

## State Characteristics (with τ)

| State | Mean VIX | Mean τ | Mean Daily Return |
|-------|----------|--------|-------------------|
| Transition | 19.7 | -0.13 | 0.061% |
| Calm | 13.5 | -0.16 | 0.064% |
| Crisis | 33.4 | -0.13 | -0.086% |

## Crisis Detection Accuracy

| Crisis | Days in Crisis State | Accuracy |
|--------|---------------------|----------|
| 2008 GFC | 121 | 100.0% |
| 2020 COVID | 30 | 93.3% |
| 2022 Bear Market | 95 | 86.3% |

---
*τ-augmented model for comparison with baseline*