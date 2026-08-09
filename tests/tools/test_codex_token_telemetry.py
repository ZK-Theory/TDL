from __future__ import annotations

import json

from tools.codex_token_telemetry import audit_records, main


def _token(total, last):
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": total, "last_token_usage": last},
        },
    }


def _usage(input_tokens, output_tokens, *, cached=0, cache_write=0, total=None):
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "cache_write_input_tokens": cache_write,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": 0,
        "total_tokens": input_tokens + output_tokens if total is None else total,
    }


def test_repeated_last_and_compaction_records_are_not_added_twice():
    first = _usage(100, 10, cached=80, cache_write=3)
    repeated = _usage(100, 10, cached=80, cache_write=3)
    second = _usage(150, 15, cached=110, cache_write=7)
    records = [
        _token(first, first),
        _token(repeated, first),
        _token(repeated, _usage(0, 0, total=21)),
        _token(second, _usage(50, 5, cached=30, cache_write=4)),
    ]

    result = audit_records(records)

    assert result["usage"] == second
    assert result["repeated_last_records"] == 2
    assert [warning["code"] for warning in result["warnings"]] == [
        "repeated_last_usage_without_cumulative_advance",
        "bookkeeping_last_total_without_cumulative_advance",
    ]


def test_explicit_boundary_excludes_inherited_history_by_cumulative_delta():
    inherited = _usage(1_000, 100, cached=900, cache_write=20)
    local = _usage(1_040, 106, cached=925, cache_write=23)
    records = [
        _token(inherited, inherited),
        {"type": "event_msg", "payload": {"type": "task_started"}},
        _token(local, _usage(40, 6, cached=25, cache_write=3)),
    ]

    result = audit_records(records, boundary_seq=1)

    assert result["usage"] == _usage(40, 6, cached=25, cache_write=3)
    assert result["warnings"] == []


def test_last_call_mismatch_warns_but_raw_cache_write_delta_is_preserved():
    records = [
        _token(_usage(10, 2, cache_write=4), _usage(10, 2, cache_write=4)),
        _token(_usage(20, 5, cache_write=9), _usage(9, 3, cache_write=0)),
    ]

    result = audit_records(records)

    assert result["usage"]["cache_write_input_tokens"] == 9
    assert result["warnings"] == [
        {
            "seq": 1,
            "code": "last_usage_differs_from_cumulative_delta",
            "fields": ["input_tokens", "cache_write_input_tokens", "total_tokens"],
        }
    ]


def test_cli_reports_malformed_jsonl_without_hiding_valid_usage(tmp_path, capsys):
    path = tmp_path / "session.jsonl"
    record = _token(_usage(5, 1), _usage(5, 1))
    path.write_text(json.dumps(record) + "\nnot json\n", encoding="utf-8")

    assert main([str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["malformed_records"] == 1
    assert output["usage"]["total_tokens"] == 6


def test_cli_counts_structurally_malformed_telemetry_without_hiding_usage(tmp_path, capsys):
    path = tmp_path / "session.jsonl"
    valid = _token(_usage(5, 1), _usage(5, 1))
    malformed_payload = {"type": "event_msg", "payload": "not-an-object"}
    malformed_counter = _token({"total_tokens": "not-an-integer"}, None)
    path.write_text(
        "\n".join(json.dumps(record) for record in (valid, malformed_payload, malformed_counter)) + "\n",
        encoding="utf-8",
    )

    assert main([str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["malformed_records"] == 2
    assert output["usage"]["total_tokens"] == 6
