from pathlib import Path

import pytest

from trajectory_tda.analysis.panel.t124b_stability_stored_se import (
    binomial_se,
    dispatch_t124b_json,
    validate_stability_stored_se_output,
    wilson_ci,
)


def test_stability_stored_se_output_schema():
    payload = _se_payload()
    validate_stability_stored_se_output(payload)

    # (a) schema_version must be the stored-SE tag.
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(_mutated("schema_version", "wrong-v9"))

    # (b) computed_on must be exactly 'stability_stored' (R3 self-description).
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(_mutated("computed_on", "stability_from_seqs"))

    # (c) supersedes must name the prior file as do-not-cite for Table 2.
    bad_super_file = _se_payload()
    bad_super_file["supersedes"]["file"] = "results/other/unrelated.json"
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_super_file)
    bad_super_flag = _se_payload()
    bad_super_flag["supersedes"]["do_not_cite_for_table2"] = False
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_super_flag)

    # (d) each regime SE must equal sqrt(stored*(1-stored)/n_members).
    bad_se = _se_payload()
    bad_se["stability_by_regime"]["R0"]["SE"] = 0.05
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_se)

    # (e) stored proportion in [0, 1] and n_members > 0.
    bad_stored = _se_payload()
    bad_stored["stability_by_regime"]["R0"]["stability_stored"] = 1.4
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_stored)
    bad_n = _se_payload()
    bad_n["stability_by_regime"]["R0"]["n_members"] = 0
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_n)

    # (f) CI95 bounds must be ordered.
    bad_ci = _se_payload()
    bad_ci["stability_by_regime"]["R0"]["CI95_lo"] = 0.9
    bad_ci["stability_by_regime"]["R0"]["CI95_hi"] = 0.1
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_ci)

    # (g) the forbidden stability_from_seqs_se key must be absent.
    bad_forbidden_top = _se_payload()
    bad_forbidden_top["stability_from_seqs_se"] = {"R0": 0.0024}
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_forbidden_top)
    bad_forbidden_regime = _se_payload()
    bad_forbidden_regime["stability_by_regime"]["R0"]["stability_from_seqs_se"] = 0.0024
    with pytest.raises(AssertionError):
        validate_stability_stored_se_output(bad_forbidden_regime)


def test_stability_stored_se_json_validation_dispatch():
    payload = _se_payload()
    # Stored-SE files are routed to the schema validator.
    assert dispatch_t124b_json(
        Path("results/panel_methodology/uncertainty_addons/stability_se_stored_2026-06-22.json"),
        payload,
    )
    with pytest.raises(AssertionError):
        dispatch_t124b_json(
            Path("results/panel_methodology/uncertainty_addons/stability_se_stored_2026-06-22.json"),
            _mutated("computed_on", "stability_from_seqs"),
        )
    # (b) The legacy stability_se files are NOT captured.
    assert not dispatch_t124b_json(
        Path("results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json"),
        {"schema_version": "legacy"},
    )
    assert not dispatch_t124b_json(
        Path("results/panel_methodology/uncertainty_addons/stability_se_2026-05-14.json"),
        {"schema_version": "legacy"},
    )


def _mutated(key, value):
    payload = _se_payload()
    payload[key] = value
    return payload


def _regime_block(regime: int, stored: float, n_members: int, n_transitions: int):
    lo, hi = wilson_ci(stored, n_members)
    return {
        "regime": regime,
        "stability_stored": stored,
        "n_members": n_members,
        "SE": binomial_se(stored, n_members),
        "CI95_lo": lo,
        "CI95_hi": hi,
        "CI95_method": "Wilson score interval",
        "n_transitions": n_transitions,
        "SE_window_pair_alt": binomial_se(stored, n_transitions),
    }


def _se_payload():
    return {
        "schema_version": "stability-stored-se-v1",
        "created_at": "2026-06-22",
        "computed_on": "stability_stored",
        "supersedes": {
            "file": ("results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json"),
            "column": "SE / CI95 (Table 2 stability uncertainty column)",
            "reason": "prior SE/CI95 were computed on stability_from_seqs",
            "do_not_cite_for_table2": True,
            "retained_valid": "stability_stored point values remain valid",
        },
        "source_file": ("C:/Users/steph/TDL/results/panel_methodology/uncertainty_addons/stability_se_2026-05-16.json"),
        "method": ("SE = sqrt(stored*(1-stored)/n_members) with a Wilson 95% CI on the stored proportion."),
        "denominator": "n_members",
        "stability_by_regime": {
            "R0": _regime_block(0, 0.2341, 3787, 44694),
            "R1": _regime_block(1, 0.7795, 7358, 88364),
        },
    }
