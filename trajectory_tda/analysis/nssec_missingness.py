"""
NS-SEC missingness analysis: test whether 39.1% missing parental NS-SEC
is non-random with respect to trajectory characteristics.

Phase 4, Concern #5.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def _build_person_features(
    trajectories: list[list[str]],
    regime_labels: np.ndarray,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Build person-level feature DataFrame for missingness comparison.

    Args:
        trajectories: List of state sequences.
        regime_labels: (N,) regime assignments.
        metadata: DataFrame with pidp, n_years, start_year, end_year columns.

    Returns:
        DataFrame with one row per person and trajectory characteristics.
    """
    rows = []
    for i in range(len(trajectories)):
        traj = trajectories[i]
        n = len(traj)
        if n == 0:
            continue

        # State frequencies
        emp_rate = sum(1 for s in traj if s.startswith("E")) / n
        unemp_rate = sum(1 for s in traj if s.startswith("U")) / n
        inact_rate = sum(1 for s in traj if s.startswith("I")) / n
        low_rate = sum(1 for s in traj if s.endswith("L")) / n
        mid_rate = sum(1 for s in traj if s.endswith("M")) / n
        high_rate = sum(1 for s in traj if s.endswith("H")) / n

        # Stability: fraction of time in dominant state
        from collections import Counter

        state_counts = Counter(traj)
        dominant_state = state_counts.most_common(1)[0][0]
        stability = state_counts[dominant_state] / n

        # Transition rate
        n_transitions = sum(1 for t in range(n - 1) if traj[t] != traj[t + 1])
        transition_rate = n_transitions / (n - 1) if n > 1 else 0.0

        rows.append(
            {
                "idx": i,
                "regime": int(regime_labels[i]),
                "traj_length": n,
                "emp_rate": emp_rate,
                "unemp_rate": unemp_rate,
                "inact_rate": inact_rate,
                "low_rate": low_rate,
                "mid_rate": mid_rate,
                "high_rate": high_rate,
                "stability": stability,
                "dominant_state": dominant_state,
                "transition_rate": transition_rate,
            }
        )

    return pd.DataFrame(rows)


def nssec_missingness_analysis(
    trajectories: list[list[str]],
    regime_labels: np.ndarray,
    metadata: pd.DataFrame,
    covariates: pd.DataFrame,
    pidp_array: np.ndarray,
) -> dict:
    """Test whether NS-SEC missingness is random with respect to trajectory features.

    Args:
        trajectories: List of state sequences.
        regime_labels: (N,) GMM regime assignments.
        metadata: DataFrame with pidp, n_years, etc.
        covariates: DataFrame from extract_covariates (pidp, sex, birth_year,
                    parental_nssec columns).
        pidp_array: (N,) pidps aligned with trajectories.

    Returns:
        Dict with test results, comparison tables, regression coefficients.
    """
    n = len(trajectories)
    regime_labels = np.asarray(regime_labels)

    logger.info(f"NS-SEC missingness analysis: {n} trajectories")

    # Build person-level features
    person_df = _build_person_features(trajectories, regime_labels, metadata)
    person_df["pidp"] = [pidp_array[i] for i in person_df["idx"].values]

    # Merge covariates (extractor returns parental_nssec8 and parental_nssec3)
    cov_cols = ["pidp"]
    for col in ("sex", "birth_year", "parental_nssec8", "parental_nssec3"):
        if col in covariates.columns:
            cov_cols.append(col)
    cov_dedup = covariates[cov_cols].drop_duplicates(subset="pidp", keep="first")
    person_df = person_df.merge(cov_dedup, on="pidp", how="left")

    # Use parental_nssec3 as the primary NS-SEC indicator
    nssec_col = "parental_nssec3" if "parental_nssec3" in person_df.columns else "parental_nssec8"
    person_df["parental_nssec"] = person_df[nssec_col]

    # Split into present vs absent
    has_nssec = person_df["parental_nssec"].notna()
    present = person_df[has_nssec].copy()
    absent = person_df[~has_nssec].copy()

    n_present = len(present)
    n_absent = len(absent)
    n_total = n_present + n_absent

    logger.info(
        f"  NS-SEC present: {n_present} ({n_present / n_total:.1%}), "
        f"absent: {n_absent} ({n_absent / n_total:.1%})"
    )

    results: dict = {
        "n_total": n_total,
        "n_present": n_present,
        "n_absent": n_absent,
        "missing_rate": n_absent / n_total if n_total > 0 else 0.0,
    }

    # 1. Regime distribution: chi-squared test
    unique_regimes = sorted(person_df["regime"].unique())
    regime_present = present["regime"].value_counts().reindex(unique_regimes, fill_value=0)
    regime_absent = absent["regime"].value_counts().reindex(unique_regimes, fill_value=0)

    contingency = np.array([regime_present.values, regime_absent.values])
    chi2, chi2_p, chi2_dof, _ = stats.chi2_contingency(contingency)

    results["regime_distribution"] = {
        "chi2_statistic": float(chi2),
        "chi2_p_value": float(chi2_p),
        "chi2_dof": int(chi2_dof),
        "present_counts": {int(k): int(v) for k, v in regime_present.items()},
        "absent_counts": {int(k): int(v) for k, v in regime_absent.items()},
        "present_proportions": {
            int(k): float(v / n_present) for k, v in regime_present.items()
        },
        "absent_proportions": {
            int(k): float(v / n_absent) for k, v in regime_absent.items()
        },
    }

    logger.info(
        f"  Regime × NS-SEC chi²={chi2:.2f}, p={chi2_p:.4f}, dof={chi2_dof}"
    )

    # 2. State frequency comparisons (t-tests)
    freq_vars = [
        "emp_rate", "unemp_rate", "inact_rate",
        "low_rate", "mid_rate", "high_rate",
    ]
    state_comparisons = {}
    for var in freq_vars:
        t_stat, t_p = stats.ttest_ind(
            present[var].dropna(), absent[var].dropna(), equal_var=False
        )
        state_comparisons[var] = {
            "present_mean": float(present[var].mean()),
            "absent_mean": float(absent[var].mean()),
            "difference": float(present[var].mean() - absent[var].mean()),
            "t_statistic": float(t_stat),
            "p_value": float(t_p),
        }
    results["state_frequencies"] = state_comparisons

    # 3. Trajectory characteristics
    char_vars = ["traj_length", "stability", "transition_rate"]
    char_comparisons = {}
    for var in char_vars:
        t_stat, t_p = stats.ttest_ind(
            present[var].dropna(), absent[var].dropna(), equal_var=False
        )
        char_comparisons[var] = {
            "present_mean": float(present[var].mean()),
            "absent_mean": float(absent[var].mean()),
            "difference": float(present[var].mean() - absent[var].mean()),
            "t_statistic": float(t_stat),
            "p_value": float(t_p),
        }
    results["trajectory_characteristics"] = char_comparisons

    # 4. Birth cohort distribution (if available)
    if "birth_year" in person_df.columns:
        person_df["birth_cohort"] = pd.cut(
            person_df["birth_year"],
            bins=[1920, 1950, 1960, 1970, 1980, 2010],
            labels=["pre-1950", "1950s", "1960s", "1970s", "post-1980"],
        )
        present_cohort = present.copy()
        present_cohort["birth_cohort"] = pd.cut(
            present_cohort["birth_year"],
            bins=[1920, 1950, 1960, 1970, 1980, 2010],
            labels=["pre-1950", "1950s", "1960s", "1970s", "post-1980"],
        )
        absent_cohort = absent.copy()
        absent_cohort["birth_cohort"] = pd.cut(
            absent_cohort["birth_year"],
            bins=[1920, 1950, 1960, 1970, 1980, 2010],
            labels=["pre-1950", "1950s", "1960s", "1970s", "post-1980"],
        )

        cohort_labels = ["pre-1950", "1950s", "1960s", "1970s", "post-1980"]
        cohort_present = (
            present_cohort["birth_cohort"]
            .value_counts()
            .reindex(cohort_labels, fill_value=0)
        )
        cohort_absent = (
            absent_cohort["birth_cohort"]
            .value_counts()
            .reindex(cohort_labels, fill_value=0)
        )

        # Drop zero rows for chi-squared validity
        mask = (cohort_present.values + cohort_absent.values) > 0
        if mask.sum() >= 2:
            cohort_contingency = np.array(
                [cohort_present.values[mask], cohort_absent.values[mask]]
            )
            cohort_chi2, cohort_p, cohort_dof, _ = stats.chi2_contingency(
                cohort_contingency
            )
        else:
            cohort_chi2, cohort_p, cohort_dof = 0.0, 1.0, 0

        results["birth_cohort"] = {
            "chi2_statistic": float(cohort_chi2),
            "chi2_p_value": float(cohort_p),
            "chi2_dof": int(cohort_dof),
            "present_counts": {
                str(k): int(v) for k, v in cohort_present.items()
            },
            "absent_counts": {
                str(k): int(v) for k, v in cohort_absent.items()
            },
        }

    # 5. Logistic regression predicting missingness
    results["logistic_regression"] = _missingness_logistic_regression(person_df)

    # 6. Summary assessment
    significant_tests = []
    if results["regime_distribution"]["chi2_p_value"] < 0.05:
        significant_tests.append("regime_distribution")
    for var, comp in results["state_frequencies"].items():
        if comp["p_value"] < 0.05:
            significant_tests.append(f"state_freq_{var}")
    for var, comp in results["trajectory_characteristics"].items():
        if comp["p_value"] < 0.05:
            significant_tests.append(f"traj_char_{var}")

    results["summary"] = {
        "n_significant_tests": len(significant_tests),
        "significant_tests": significant_tests,
        "subsample_representative": len(significant_tests) == 0,
        "assessment": (
            "NS-SEC missingness appears random (subsample is representative)"
            if len(significant_tests) == 0
            else f"NS-SEC missingness is non-random on {len(significant_tests)} tests — "
            "stratified results should be interpreted with caution"
        ),
    }

    logger.info(f"  Summary: {results['summary']['assessment']}")
    return results


def _missingness_logistic_regression(person_df: pd.DataFrame) -> dict:
    """Logistic regression predicting NS-SEC missingness from trajectory features."""
    try:
        import statsmodels.api as sm
    except ImportError:
        return {"skipped": True, "reason": "statsmodels not installed"}

    df = person_df.copy()
    df["nssec_missing"] = df["parental_nssec"].isna().astype(int)

    # Predictors
    predictors = ["emp_rate", "low_rate", "traj_length", "transition_rate"]

    # Add regime dummies (drop first as reference)
    regime_dummies = pd.get_dummies(df["regime"], prefix="regime", drop_first=True)
    for col in regime_dummies.columns:
        df[col] = regime_dummies[col]
        predictors.append(col)

    # Add birth cohort if available
    if "birth_year" in df.columns:
        df["birth_cohort_cat"] = pd.cut(
            df["birth_year"],
            bins=[1920, 1950, 1960, 1970, 1980, 2010],
            labels=["pre-1950", "1950s", "1960s", "1970s", "post-1980"],
        )
        cohort_dummies = pd.get_dummies(
            df["birth_cohort_cat"], prefix="cohort", drop_first=True
        )
        for col in cohort_dummies.columns:
            df[col] = cohort_dummies[col]
            predictors.append(col)

    df_model = df.dropna(subset=predictors + ["nssec_missing"])
    if len(df_model) < 50:
        return {"skipped": True, "reason": f"only {len(df_model)} complete cases"}

    X = sm.add_constant(df_model[predictors].astype(float))
    y = df_model["nssec_missing"].astype(float)

    try:
        model = sm.Logit(y, X).fit(disp=0)
    except Exception as e:
        return {"skipped": True, "reason": str(e)}

    return {
        "n_obs": int(len(df_model)),
        "coefficients": {
            name: float(c) for name, c in zip(model.params.index, model.params)
        },
        "odds_ratios": {
            name: float(np.exp(c))
            for name, c in zip(model.params.index, model.params)
        },
        "p_values": {
            name: float(p) for name, p in zip(model.pvalues.index, model.pvalues)
        },
        "confidence_intervals_95": {
            name: [float(model.conf_int().loc[name, 0]), float(model.conf_int().loc[name, 1])]
            for name in model.params.index
        },
        "pseudo_r2": float(model.prsquared),
        "aic": float(model.aic),
        "bic": float(model.bic),
    }


def run_nssec_missingness(
    results_dir: str | Path,
    data_dir: str | Path,
    output_path: str | Path | None = None,
) -> dict:
    """Load pipeline outputs and run NS-SEC missingness analysis.

    Args:
        results_dir: Directory containing pipeline checkpoints.
        data_dir: Raw data directory for covariate extraction.
        output_path: Path to save results JSON.

    Returns:
        Missingness analysis results dict.
    """
    from trajectory_tda.data.covariate_extractor import extract_covariates

    results_dir = Path(results_dir)

    # Load trajectories
    seq_path = results_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)

    # Load metadata
    with open(results_dir / "01_trajectories.json") as f:
        traj_data = json.load(f)
    metadata = pd.DataFrame(traj_data["metadata"])

    # Load regime labels
    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    regime_labels = np.array(analysis["gmm_labels"])

    # Build pidp array
    n = len(trajectories)
    pidp_array = np.array(
        [int(metadata["pidp"][str(i)]) for i in range(n)]
    )

    # Extract covariates
    covariates = extract_covariates(data_dir=data_dir, pidps=pidp_array)

    result = nssec_missingness_analysis(
        trajectories=trajectories,
        regime_labels=regime_labels,
        metadata=metadata,
        covariates=covariates,
        pidp_array=pidp_array,
    )

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, dict):
                return {str(k): convert(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [convert(v) for v in obj]
            return obj

        with open(output_path, "w") as f:
            json.dump(convert(result), f, indent=2)
        logger.info(f"Results saved: {output_path}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="NS-SEC missingness analysis"
    )
    parser.add_argument(
        "--results-dir",
        default="results/trajectory_tda_integration",
    )
    parser.add_argument("--data-dir", default="trajectory_tda/data")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    run_nssec_missingness(
        results_dir=args.results_dir,
        data_dir=args.data_dir,
        output_path=args.output
        or f"{args.results_dir}/nssec_missingness.json",
    )
