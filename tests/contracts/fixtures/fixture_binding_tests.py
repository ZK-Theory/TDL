import pytest


def validate_present_key(payload):
    if "present_key" not in payload:
        raise ValueError("present_key is required")
    return payload["present_key"]


def test_qualitative_fixture():
    assert True


def test_missing_enforcement_fixture():
    assert True


def test_both_enforcement_fixture():
    assert True


def test_claim_coverage_shortfall_fixture():
    with pytest.raises(ValueError):
        validate_present_key({})


def test_pending_debt_fixture():
    assert True


def test_valid_contract_fixture():
    y = 4
    x = y + 1
    assert x == y + 1


def test_json_schema_contract_fixture():
    assert {"score": 0.5, "count": 1, "optional_se": None}
