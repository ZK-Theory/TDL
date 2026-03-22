# HMM Baseline Model Report

**Generated:** 2025-12-17 20:37

## Model Configuration

| Parameter | Value |
|-----------|-------|
| States | 3 |
| Features | ret_1d, ret_5d, ret_21d, vix, vix_5d_chg |
| τ included | **No** (baseline) |
| Observations | 5988 |

## Model Fit Metrics

| Metric | Value |
|--------|-------|
| Log-likelihood | -26429.63 |
| AIC | 52991.27 |
| BIC | 53433.30 |
| Parameters | 66 |

## State Distribution

| State | Days | Percentage |
|-------|------|------------|
| Transition | 2449 | 40.9% |
| Calm | 2205 | 36.8% |
| Crisis | 1334 | 22.3% |

## Crisis Detection Accuracy

| Crisis | Days in Crisis State | Accuracy |
|--------|---------------------|----------|
| 2008 GFC | 121 | 100.0% |
| 2020 COVID | 30 | 93.3% |
| 2022 Bear Market | 95 | 86.3% |

---
*Baseline model for comparison with τ-augmented model*