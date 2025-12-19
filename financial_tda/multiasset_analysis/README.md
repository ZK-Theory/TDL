# Multi-Asset TDA Analysis Package

> [!CAUTION]
> **METHODOLOGY COMPLIANCE REQUIRED**
> Before running ANY experiment, read **[METHODOLOGY_REFERENCE.md](../docs/METHODOLOGY_REFERENCE.md)**.
> - Use the canonical Gidea & Katz pipeline (Takens embedding → H₁ → L²/L¹ → Kendall-τ)
> - Use validated parameter sets (Standard: W=500/P=250, Fast: W=450/P=200)
> - Do NOT invent alternative approaches or optimize parameters to "improve" failing results
> - Report failures honestly — negative results are valid scientific findings

This directory contains the implementation for **Project B: Multi-Asset Topological Analysis**.

## Overview

Extends TDA-based crisis detection from single-asset-class (equities) to cross-asset surveillance, enabling:
1. Detection of systemic stress propagation across asset classes
2. Distinction between "Risk-Off Rotations" and "Liquidity Crises"
3. Analysis of crypto's role in portfolio topology

## Files

| File | Purpose |
|------|---------|
| `fetch_multiasset_data.py` | Data infrastructure: fetches, aligns, preprocesses multi-asset data |
| `tda_analysis.py` | Core TDA pipeline: point cloud construction, GUDHI persistence, Kendall-tau |
| `experiment_macro_manifold.py` | **Exp A**: Cross-asset topology for stress detection |
| `experiment_regime_classify.py` | **Exp B**: Regime classification (Normal/Risk-Off/Liquidity) |
| `experiment_crypto_role.py` | **Exp C**: Crypto's impact on portfolio topology |

## Quick Start

```bash
# Validate data infrastructure
python fetch_multiasset_data.py

# Run Experiment A (Macro Manifold)
python experiment_macro_manifold.py --config extended

# Run comparison across asset configs
python experiment_macro_manifold.py --compare

# Run Experiment B (Regime Classification)
python experiment_regime_classify.py --config extended --model random_forest

# Run Experiment C (Crypto Analysis)
python experiment_crypto_role.py
```

## Asset Configurations

| Config | Assets | Available From |
|--------|--------|----------------|
| `minimal` | SPY, TLT, GLD, UUP | 2007 |
| `extended` | +QQQ, HYG, USO, FXE | 2007 |
| `full_crypto` | +BTC-USD, ETH-USD | 2017 |

## Key Stress Events (for validation)

- 2008 GFC (Risk-Off)
- 2011 Debt Ceiling (Risk-Off)
- 2020 COVID (Liquidity Crisis)
- 2022 Rate Shock (Duration Pain)

## Dependencies

- yfinance
- gudhi
- pandas, numpy
- scipy.stats
- scikit-learn (for regime classification)
