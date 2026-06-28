# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Tests for covariate_extractor BHPS parental NS-SEC bug fix (T1.28).
"""Tests for trajectory_tda.data.covariate_extractor.

Covers:
- _load_bhps_covariates: parental NS-SEC pa/ma read (was hardcoded NaN)
- _load_bhps_later_waves: recovery of post-wave-1 BHPS entrants
- extract_covariates: BHPS coverage integration tests (require real data)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trajectory_tda.data.covariate_extractor import (
    _load_bhps_covariates,
    _load_bhps_later_waves,
    extract_covariates,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

PROJ_ROOT = Path("C:/Users/steph/TDL")
DATA_DIR = PROJ_ROOT / "data"


def _write_tab(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, sep="\t", index=False)


# ── _load_bhps_covariates ─────────────────────────────────────────────────────


class TestLoadBhpsCovariates:
    def test_reads_ba_panssec8_dv_father_first(self, tmp_path: Path) -> None:
        """Father's NS-SEC (ba_panssec8_dv) is used when valid."""
        _write_tab(
            tmp_path / "ba_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [1001, 1002],
                    "ba_sex": [1, 2],
                    "ba_doby": [1965, 1970],
                    "ba_panssec8_dv": [1, 3],
                    "ba_manssec8_dv": [2, 7],
                }
            ),
        )
        result = _load_bhps_covariates(tmp_path, {1001, 1002})
        assert result.loc[result["pidp"] == 1001, "parental_nssec8"].iloc[0] == 1
        assert result.loc[result["pidp"] == 1002, "parental_nssec8"].iloc[0] == 3

    def test_falls_back_to_mother_when_father_missing(self, tmp_path: Path) -> None:
        """When father's NS-SEC is ≤0, mother's value is used."""
        _write_tab(
            tmp_path / "ba_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [1003],
                    "ba_sex": [2],
                    "ba_doby": [1972],
                    "ba_panssec8_dv": [-9],  # missing code
                    "ba_manssec8_dv": [4],
                }
            ),
        )
        result = _load_bhps_covariates(tmp_path, {1003})
        assert result.loc[result["pidp"] == 1003, "parental_nssec8"].iloc[0] == 4

    def test_nan_when_both_parents_missing(self, tmp_path: Path) -> None:
        """NaN when both pa and ma codes are ≤0 (missing/inapplicable)."""
        _write_tab(
            tmp_path / "ba_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [1004],
                    "ba_sex": [1],
                    "ba_doby": [1968],
                    "ba_panssec8_dv": [-9],
                    "ba_manssec8_dv": [-8],
                }
            ),
        )
        result = _load_bhps_covariates(tmp_path, {1004})
        assert pd.isna(result.loc[result["pidp"] == 1004, "parental_nssec8"].iloc[0])

    def test_nan_when_parental_columns_absent(self, tmp_path: Path) -> None:
        """Files without ba_panssec8_dv produce NaN parental_nssec8 (graceful fallback)."""
        _write_tab(
            tmp_path / "ba_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [1005],
                    "ba_sex": [1],
                    "ba_doby": [1975],
                }
            ),
        )
        result = _load_bhps_covariates(tmp_path, {1005})
        assert pd.isna(result.loc[result["pidp"] == 1005, "parental_nssec8"].iloc[0])

    def test_empty_directory_returns_empty_df(self, tmp_path: Path) -> None:
        result = _load_bhps_covariates(tmp_path, {9999})
        assert result.empty
        assert list(result.columns) == ["pidp", "sex", "birth_year", "parental_nssec8"]

    def test_pidp_filter_applied(self, tmp_path: Path) -> None:
        """Only requested pidps are returned."""
        _write_tab(
            tmp_path / "ba_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [1001, 1002, 1003],
                    "ba_sex": [1, 2, 1],
                    "ba_doby": [1960, 1965, 1970],
                    "ba_panssec8_dv": [1, 2, 3],
                    "ba_manssec8_dv": [4, 5, 6],
                }
            ),
        )
        result = _load_bhps_covariates(tmp_path, {1001})
        assert set(result["pidp"]) == {1001}


# ── _load_bhps_later_waves ────────────────────────────────────────────────────


class TestLoadBhpsLaterWaves:
    def test_recovers_wave2_entrant(self, tmp_path: Path) -> None:
        """pidp absent from wave 1 is recovered from wave 2 (bb_indresp)."""
        _write_tab(
            tmp_path / "bb_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [2001, 2002],
                    "bb_sex": [2, 1],
                    "bb_doby": [1958, 1962],
                    "bb_panssec8_dv": [2, -9],
                    "bb_manssec8_dv": [-8, 5],
                }
            ),
        )
        result = _load_bhps_later_waves(tmp_path, {2001, 2002})
        assert set(result["pidp"]) == {2001, 2002}
        assert result.loc[result["pidp"] == 2001, "sex"].iloc[0] == "Female"
        assert result.loc[result["pidp"] == 2002, "sex"].iloc[0] == "Male"
        # 2001: pa=2 valid; 2002: pa=-9 invalid → ma=5
        assert result.loc[result["pidp"] == 2001, "parental_nssec8"].iloc[0] == 2
        assert result.loc[result["pidp"] == 2002, "parental_nssec8"].iloc[0] == 5

    def test_skips_wave_with_no_matching_pidps(self, tmp_path: Path) -> None:
        """Returns empty when no pidp in the wave matches the requested set."""
        _write_tab(
            tmp_path / "bb_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [3001],
                    "bb_sex": [1],
                    "bb_doby": [1970],
                    "bb_panssec8_dv": [3],
                    "bb_manssec8_dv": [-9],
                }
            ),
        )
        result = _load_bhps_later_waves(tmp_path, {9999})
        assert result.empty

    def test_returns_empty_when_no_wave_files(self, tmp_path: Path) -> None:
        result = _load_bhps_later_waves(tmp_path, {9999})
        assert result.empty
        assert "parental_nssec8" in result.columns

    def test_graceful_fallback_when_parental_columns_absent(self, tmp_path: Path) -> None:
        """Waves without parental NS-SEC columns still return sex/dob, nssec=NaN."""
        _write_tab(
            tmp_path / "bb_indresp.tab",
            pd.DataFrame(
                {
                    "pidp": [4001],
                    "bb_sex": [1],
                    "bb_doby": [1966],
                }
            ),
        )
        result = _load_bhps_later_waves(tmp_path, {4001})
        assert set(result["pidp"]) == {4001}
        assert pd.isna(result.loc[result["pidp"] == 4001, "parental_nssec8"].iloc[0])


# ── extract_covariates — BHPS integration tests ───────────────────────────────


@pytest.mark.integration
class TestExtractCovariatesIntegration:
    @pytest.fixture(autouse=True)
    def require_bhps_checkpoint(self) -> None:
        bhps_meta = PROJ_ROOT / "results/trajectory_tda_bhps/01_trajectories.json"
        if not bhps_meta.exists():
            pytest.skip("BHPS checkpoint not on disk (integration test)")

    def _load_bhps_pidps(self) -> np.ndarray:
        bhps_meta = PROJ_ROOT / "results/trajectory_tda_bhps/01_trajectories.json"
        with open(bhps_meta) as f:
            meta = json.load(f)["metadata"]
        pidp_raw = meta.get("pidp", {})
        n = len(pidp_raw)
        return np.array([int(pidp_raw[str(i)]) for i in range(n)], dtype=np.int64)

    def test_bhps_parental_nssec8_coverage_positive(self) -> None:
        """BHPS parental_nssec8 must be >0 after the extractor bug fix."""
        pidps = self._load_bhps_pidps()
        covs = extract_covariates(DATA_DIR, pidps)
        coverage = int(covs["parental_nssec8"].notna().sum())
        assert coverage > 0, (
            f"BHPS parental_nssec8 still all-NaN ({coverage}/{len(covs)}) — "
            "bug fix did not take effect"
        )

    def test_bhps_parental_nssec3_coverage_positive(self) -> None:
        """BHPS parental_nssec3 derives from parental_nssec8 via NSSEC3_MAP; must be >0."""
        pidps = self._load_bhps_pidps()
        covs = extract_covariates(DATA_DIR, pidps)
        coverage = int(covs["parental_nssec3"].notna().sum())
        assert coverage > 0, (
            f"BHPS parental_nssec3 still all-NaN ({coverage}/{len(covs)}) — "
            "NSSEC3_MAP derivation failed"
        )

    def test_bhps_total_matched_coverage_above_wave1_baseline(self) -> None:
        """Later-wave fallback should push total match rate above wave-1-only 65%."""
        pidps = self._load_bhps_pidps()
        covs = extract_covariates(DATA_DIR, pidps)
        n_matched = len(covs.drop_duplicates("pidp"))
        pct = n_matched / len(pidps)
        assert pct > 0.65, (
            f"Total match rate {pct:.1%} still at wave-1-only level — "
            "later-wave fallback may not work"
        )
