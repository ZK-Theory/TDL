import json
import math

import numpy as np
import pytest
from sklearn.metrics import adjusted_rand_score

from tests.panel.test_t123_ari_normalisation_contracts import _ari_payload
from trajectory_tda.analysis.panel.t123_ari_normalisation import (
    adjusted_rand_fast,
    adjusted_rand_from_contingency,
    comb2,
    compute_max_ari,
    validate_payload,
    write_json_no_overwrite,
)


def test_fast_ari_matches_sklearn_on_toy_labels():
    left = np.array([0, 0, 1, 1, 1, 2, 2])
    right = np.array([1, 1, 1, 0, 0, 2, 2])
    assert adjusted_rand_fast(left, right) == pytest.approx(
        adjusted_rand_score(left, right)
    )


def test_adjusted_rand_from_contingency_matches_known_value():
    table = np.array([[2, 0], [1, 2], [0, 2]])
    left = np.array([0, 0, 1, 1, 1, 2, 2])
    right = np.array([0, 0, 0, 1, 1, 1, 1])
    assert adjusted_rand_from_contingency(table) == pytest.approx(
        adjusted_rand_score(left, right)
    )


def test_exact_max_ari_certificate_packs_non_singleton_rows_whole():
    row_counts = np.array([4, 3, 2, 1, 1])
    col_counts = np.array([5, 4, 2])
    observed_ari = 0.25
    result = compute_max_ari(row_counts, col_counts, observed_ari)

    assert result.exact is True
    assert result.split_non_singleton_components == 0
    assert result.contingency.sum(axis=1).tolist() == row_counts.tolist()
    assert result.contingency.sum(axis=0).tolist() == col_counts.tolist()
    assert result.pair_overlap_sum == int(comb2(row_counts).sum())
    assert result.normalised_observed == pytest.approx(observed_ari / result.ari)


def test_validate_payload_rejects_invalid_numeric_outputs():
    payload = _valid_payload()
    payload["bootstrap_ci"]["percentile_95"] = [0.2, 0.1]
    with pytest.raises(AssertionError):
        validate_payload(payload)

    payload = _valid_payload()
    payload["null_distribution"]["se"] = math.inf
    with pytest.raises(AssertionError):
        validate_payload(payload)


def test_write_json_no_overwrite(tmp_path):
    payload = _valid_payload()
    out = tmp_path / "ari_normalised_2026-06-06.json"
    write_json_no_overwrite(out, payload)
    assert json.loads(out.read_text(encoding="utf-8"))["observed_ari"] == 0.1
    with pytest.raises(FileExistsError):
        write_json_no_overwrite(out, payload)


def _valid_payload():
    return _ari_payload()
