"""
Age-stratified regime persistence and escape rate analysis.

Partitions regime sequences by age group, separating lifecycle (retirement)
persistence from inequality-driven persistence. Computes age-adjusted
escape rates and logistic regression on escape probability.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# UK State Pension Age approximation for the BHPS/USoc cohorts (1991–2023)
# Women: 60 (rising to 66 by 2020); Men: 65 (rising to 66 by 2019)
# Simplification: use 60 as the retirement-age cutoff throughout
DEFAULT_RETIREMENT_AGE = 60


def attach_age_to_windows(
    windows: list[dict],
    metadata: pd.DataFrame,
) -> list[dict]:
    """Add age at window midpoint to each window record.

    Requires metadata to contain 'pidp' and 'birth_year' columns.
    Age is computed as window midpoint year minus birth year.

    Args:
        windows: Window records from build_windows().
        metadata: DataFrame with pidp and birth_year columns.

    Returns:
        windows with 'age_at_window' field added in-place.
    """
    birth_years = metadata.set_index("pidp")["birth_year"].to_dict()

    n_missing = 0
    for w in windows:
        by = birth_years.get(w["pidp"])
        if by is not None and not (isinstance(by, float) and np.isnan(by)) and by > 0:
            midpoint = (w["start_year"] + w["end_year"]) / 2
            w["age_at_window"] = int(midpoint - by)
        else:
            w["age_at_window"] = None
            n_missing += 1

    if n_missing:
        logger.warning(f"{n_missing} windows missing birth_year")
    logger.info(f"Attached age to {len(windows) - n_missing}/{len(windows)} windows")

    return windows


def build_age_stratified_sequences(
    windows: list[dict],
    window_regimes: np.ndarray,
    retirement_age: int = DEFAULT_RETIREMENT_AGE,
) -> tuple[dict, dict]:
    """Build regime sequences stratified by age group.

    Returns two sets of sequences:
        - working_age: only windows where age < retirement_age
        - retirement_age: only windows where age >= retirement_age

    Args:
        windows: Window records with 'age_at_window' field.
        window_regimes: (N_windows,) regime labels.
        retirement_age: Age threshold for stratification.

    Returns:
        (working_age_sequences, retirement_sequences): each is a
        dict[pidp, list[{regime, start_year, end_year, age}]].
    """
    working: dict[int | str, list[dict]] = defaultdict(list)
    retired: dict[int | str, list[dict]] = defaultdict(list)

    for w, regime in zip(windows, window_regimes):
        age = w.get("age_at_window")
        entry = {
            "regime": int(regime),
            "start_year": w["start_year"],
            "end_year": w["end_year"],
            "age": age,
        }

        if age is None or age < retirement_age:
            working[w["pidp"]].append(entry)
        else:
            retired[w["pidp"]].append(entry)

    # Sort by start_year
    for seqs in (working, retired):
        for pidp in seqs:
            seqs[pidp].sort(key=lambda x: x["start_year"])

    logger.info(f"Age stratification: {len(working)} working-age, " f"{len(retired)} retirement-age individuals")

    return dict(working), dict(retired)


def _count_regime_2_by_age(
    windows: list[dict],
    window_regimes: np.ndarray,
    retirement_age: int,
) -> tuple[int, int]:
    """Count Regime 2 (Inactive Low) windows by age group."""
    under, over = 0, 0
    for w, r in zip(windows, window_regimes):
        if int(r) != 2:
            continue
        age = w.get("age_at_window")
        if age is not None and age >= retirement_age:
            over += 1
        else:
            under += 1
    return under, over


def _strip_path_lengths(d: dict) -> dict:
    """Remove path_lengths key from escape probability dict."""
    return {k: v for k, v in d.items() if k != "path_lengths"}


def compute_age_stratified_escape_rates(
    windows: list[dict],
    window_regimes: np.ndarray,
    disadvantaged_regimes: set[int],
    good_regimes: set[int],
    retirement_age: int = DEFAULT_RETIREMENT_AGE,
) -> dict:
    """Compute escape rates separately for working-age and retirement-age.

    Args:
        windows: Window records with 'age_at_window' field.
        window_regimes: (N_windows,) regime labels.
        disadvantaged_regimes: Set of disadvantaged regime indices.
        good_regimes: Set of favourable regime indices.
        retirement_age: Age threshold.

    Returns:
        Dict with overall, working_age, retirement_age escape stats,
        and regime_2_composition by age.
    """
    from trajectory_tda.analysis.regime_switching import (
        build_regime_sequences,
        compute_escape_probabilities,
    )

    all_seqs = build_regime_sequences(windows, window_regimes)
    overall = compute_escape_probabilities(all_seqs, disadvantaged_regimes, good_regimes)

    working_seqs, retired_seqs = build_age_stratified_sequences(windows, window_regimes, retirement_age)
    working_escape = compute_escape_probabilities(working_seqs, disadvantaged_regimes, good_regimes)
    retired_escape = compute_escape_probabilities(retired_seqs, disadvantaged_regimes, good_regimes)

    regime_2_under, regime_2_over = _count_regime_2_by_age(windows, window_regimes, retirement_age)
    total_r2 = regime_2_under + regime_2_over

    result = {
        "overall": _strip_path_lengths(overall),
        "working_age": _strip_path_lengths(working_escape),
        "retirement_age": _strip_path_lengths(retired_escape),
        "regime_2_composition": {
            f"under_{retirement_age}": regime_2_under,
            f"over_{retirement_age}": regime_2_over,
            "retirement_fraction": regime_2_over / total_r2 if total_r2 > 0 else 0.0,
        },
        "retirement_age_threshold": retirement_age,
    }

    logger.info(
        f"Age-stratified escape rates: "
        f"overall={overall['ever_escape_rate']:.1%}, "
        f"working-age={working_escape['ever_escape_rate']:.1%}, "
        f"retirement={retired_escape['ever_escape_rate']:.1%}"
    )
    logger.info(
        f"Regime 2 composition: "
        f"{regime_2_under} under-{retirement_age}, "
        f"{regime_2_over} over-{retirement_age} "
        f"({result['regime_2_composition']['retirement_fraction']:.1%} retirement)"
    )

    return result


def _build_escape_dataframe(
    windows: list[dict],
    window_regimes: np.ndarray,
    metadata: pd.DataFrame,
    disadvantaged_regimes: set[int],
    good_regimes: set[int],
) -> pd.DataFrame:
    """Build DataFrame of individuals starting in disadvantaged regimes."""
    from trajectory_tda.analysis.regime_switching import build_regime_sequences

    regime_sequences = build_regime_sequences(windows, window_regimes)

    rows = []
    for pidp, seq in regime_sequences.items():
        if not seq or seq[0]["regime"] not in disadvantaged_regimes:
            continue

        escaped = any(s["regime"] in good_regimes for s in seq[1:])
        rows.append(
            {
                "pidp": pidp,
                "escaped": int(escaped),
                "start_year": seq[0]["start_year"],
                "start_regime": seq[0]["regime"],
                "initial_regime": seq[0]["regime"],
            }
        )

    df = pd.DataFrame(rows)

    # Merge metadata
    meta_cols = ["pidp"]
    for col in ("sex", "birth_year", "parental_nssec"):
        if col in metadata.columns:
            meta_cols.append(col)

    df = df.merge(metadata[meta_cols], on="pidp", how="left")

    # Compute age at first window from birth_year
    if "birth_year" in df.columns:
        df["age_first_window"] = df["start_year"] - df["birth_year"]
        df["birth_cohort"] = pd.cut(
            df["birth_year"],
            bins=[1920, 1950, 1960, 1970, 1980, 2010],
            labels=["pre-1950", "1950s", "1960s", "1970s", "post-1980"],
        )

    return df


def escape_logistic_regression(
    windows: list[dict],
    window_regimes: np.ndarray,
    metadata: pd.DataFrame,
    disadvantaged_regimes: set[int],
    good_regimes: set[int],
) -> dict:
    """Extended logistic regression of escape probability.

    Predicts P(escape) ~ age_at_first_window + sex + birth_cohort
                         + initial_regime + parental_nssec.

    Uses Firth penalised regression as the primary estimation method
    to handle quasi-complete separation.

    Args:
        windows: Window records with 'age_at_window' field.
        window_regimes: (N_windows,) regime labels.
        metadata: DataFrame with pidp, birth_year, sex, parental_nssec.
        disadvantaged_regimes: Set of disadvantaged regime indices.
        good_regimes: Set of favourable regime indices.

    Returns:
        Dict with coefficients, odds ratios, 95% CIs, p-values,
        pseudo-R², AIC, BIC, separation diagnostics, Firth flag.
    """
    df = _build_escape_dataframe(
        windows,
        window_regimes,
        metadata,
        disadvantaged_regimes,
        good_regimes,
    )

    # Minimum required predictor
    required = ["age_first_window"]
    df_model = df.dropna(subset=required)

    if len(df_model) < 20:
        logger.warning(f"Only {len(df_model)} observations — logistic regression skipped")
        return {"skipped": True, "n_obs": len(df_model)}

    return _fit_logistic_model(df_model)


def _fit_logistic_model(df_model: pd.DataFrame) -> dict:
    """Fit extended logistic regression with Firth correction and separation diagnostics."""
    try:
        import statsmodels.api as sm
    except ImportError:
        logger.warning("statsmodels not available — logistic regression skipped")
        return {"skipped": True, "reason": "statsmodels not installed"}

    df_model = df_model.copy()
    X_cols = ["age_first_window"]

    # Sex encoding
    if "sex" in df_model.columns:
        df_model["female"] = df_model["sex"].apply(lambda s: 1 if s in (2, "Female") else 0)
        X_cols.append("female")

    # Birth cohort dummies (reference: pre-1950)
    if "birth_cohort" in df_model.columns:
        cohort_dummies = pd.get_dummies(
            df_model["birth_cohort"], prefix="cohort", drop_first=True
        )
        for col in cohort_dummies.columns:
            df_model[col] = cohort_dummies[col]
            X_cols.append(col)

    # Initial regime dummies (reference: lowest regime)
    if "initial_regime" in df_model.columns:
        regime_dummies = pd.get_dummies(
            df_model["initial_regime"], prefix="regime", drop_first=True
        )
        for col in regime_dummies.columns:
            df_model[col] = regime_dummies[col]
            X_cols.append(col)

    # Parental NS-SEC dummies (reference: first category)
    if "parental_nssec" in df_model.columns:
        nssec_present = df_model["parental_nssec"].notna()
        if nssec_present.sum() > 20:
            nssec_dummies = pd.get_dummies(
                df_model.loc[nssec_present, "parental_nssec"],
                prefix="nssec",
                drop_first=True,
            )
            for col in nssec_dummies.columns:
                df_model[col] = nssec_dummies[col]
                X_cols.append(col)

    df_complete = df_model.dropna(subset=X_cols + ["escaped"])
    if len(df_complete) < 20:
        logger.warning(f"Only {len(df_complete)} complete cases — logistic regression skipped")
        return {"skipped": True, "n_obs": int(len(df_complete))}

    X = sm.add_constant(df_complete[X_cols].astype(float))
    y = df_complete["escaped"].astype(float)

    # Step 1: Fit standard Logit for separation diagnostics
    separation_detected = False
    standard_result = None
    try:
        standard_model = sm.Logit(y, X).fit(disp=0)
        standard_result = _extract_model_results(standard_model, len(df_complete), y)

        # Check for separation indicators
        extreme_coefs = any(abs(c) > 10 for c in standard_model.params)
        extreme_pvals = any(p < 1e-50 for p in standard_model.pvalues if not np.isnan(p))
        if extreme_coefs or extreme_pvals:
            separation_detected = True
            logger.warning(
                "Separation detected: "
                f"extreme coefficients={extreme_coefs}, "
                f"extreme p-values={extreme_pvals}"
            )
    except (np.linalg.LinAlgError, Exception) as e:
        separation_detected = True
        logger.warning(f"Standard Logit failed ({e}) — separation likely")

    # Step 2: Firth penalised regression (primary method)
    firth_result = _fit_firth_logistic(X, y, len(df_complete))
    firth_used = firth_result is not None and not firth_result.get("skipped", False)

    # Use Firth as primary if available, else standard
    if firth_used and firth_result is not None:
        result = firth_result
    elif standard_result is not None:
        result = standard_result
    else:
        return {
            "skipped": True,
            "reason": "both_standard_and_firth_failed",
            "n_obs": int(len(df_complete)),
            "separation_detected": separation_detected,
        }

    result["separation_detected"] = separation_detected
    result["firth_used"] = firth_used

    # Include standard results for comparison if both available
    if firth_used and standard_result is not None:
        result["standard_model"] = standard_result

    logger.info(f"Logistic regression (n={len(df_complete)}, firth={firth_used}):")
    for name in result.get("coefficients", {}):
        or_val = result["odds_ratios"].get(name, float("nan"))
        p_val = result["p_values"].get(name, float("nan"))
        logger.info(f"  {name}: OR={or_val:.3f}, p={p_val:.4f}")

    return result


def _extract_model_results(model, n_obs: int, y) -> dict:
    """Extract results dict from a fitted statsmodels model."""
    ci = model.conf_int(alpha=0.05)
    return {
        "n_obs": int(n_obs),
        "n_escaped": int(y.sum()),
        "coefficients": {
            name: float(coef)
            for name, coef in zip(model.params.index, model.params)
        },
        "odds_ratios": {
            name: float(np.exp(coef))
            for name, coef in zip(model.params.index, model.params)
        },
        "confidence_intervals_95": {
            name: [float(ci.loc[name, 0]), float(ci.loc[name, 1])]
            for name in model.params.index
        },
        "p_values": {
            name: float(p)
            for name, p in zip(model.pvalues.index, model.pvalues)
        },
        "pseudo_r2": float(model.prsquared),
        "aic": float(model.aic),
        "bic": float(model.bic),
    }


def _fit_firth_logistic(X, y, n_obs: int) -> dict | None:
    """Attempt Firth penalised logistic regression.

    Tries firthlogist package first, falls back to statsmodels
    L2-penalised logit with small penalty.
    """
    # Try firthlogist package
    try:
        from firthlogist import FirthLogisticRegression

        # firthlogist expects X without constant (adds its own intercept)
        X_no_const = X.drop(columns=["const"], errors="ignore")
        firth = FirthLogisticRegression(max_iter=200)
        firth.fit(X_no_const.values, y.values)

        coef_names = ["const"] + list(X_no_const.columns)
        coefs = np.concatenate([[firth.intercept_], firth.coef_])
        ci_lower = np.concatenate([[firth.intercept_ci_[0]], firth.ci_[:, 0]])
        ci_upper = np.concatenate([[firth.intercept_ci_[1]], firth.ci_[:, 1]])
        p_vals = np.concatenate([[firth.pval_intercept_], firth.pvalues_])

        logger.info("Firth regression via firthlogist package")
        return {
            "n_obs": int(n_obs),
            "n_escaped": int(y.sum()),
            "method": "firth_firthlogist",
            "coefficients": {n: float(c) for n, c in zip(coef_names, coefs)},
            "odds_ratios": {n: float(np.exp(c)) for n, c in zip(coef_names, coefs)},
            "confidence_intervals_95": {
                n: [float(lo), float(hi)]
                for n, lo, hi in zip(coef_names, ci_lower, ci_upper)
            },
            "p_values": {n: float(p) for n, p in zip(coef_names, p_vals)},
        }
    except ImportError:
        logger.info("firthlogist not installed, trying statsmodels L2 fallback")
    except Exception as e:
        logger.warning(f"firthlogist failed: {e}, trying statsmodels L2 fallback")

    # Fallback: statsmodels Logit with L2 penalty (small alpha)
    try:
        import statsmodels.api as sm

        model = sm.Logit(y, X).fit_regularized(
            method="l1",  # elastic net with alpha=0 is L2
            alpha=0.1,  # small penalty
            disp=0,
        )

        # Regularised models don't have conf_int; use normal approximation
        coefs = model.params
        se = np.sqrt(np.diag(np.linalg.inv(
            sm.Logit(y, X).information(coefs)
        ))) if hasattr(sm.Logit(y, X), "information") else np.full(len(coefs), np.nan)
        z = 1.96

        coef_names = list(coefs.index)
        ci_lower = coefs - z * se
        ci_upper = coefs + z * se

        logger.info("Firth fallback: statsmodels L2-penalised logit")
        return {
            "n_obs": int(n_obs),
            "n_escaped": int(y.sum()),
            "method": "l2_penalised_logit",
            "coefficients": {n: float(c) for n, c in zip(coef_names, coefs)},
            "odds_ratios": {n: float(np.exp(c)) for n, c in zip(coef_names, coefs)},
            "confidence_intervals_95": {
                n: [float(lo), float(hi)]
                for n, lo, hi in zip(coef_names, ci_lower, ci_upper)
            },
            "p_values": {
                n: float(p)
                for n, p in zip(model.pvalues.index, model.pvalues)
            } if hasattr(model, "pvalues") else {},
        }
    except Exception as e:
        logger.warning(f"L2-penalised logit failed: {e}")
        return {"skipped": True, "reason": f"firth_fallback_failed: {e}"}
