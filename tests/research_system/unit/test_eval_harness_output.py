"""Runtime evaluation output boundaries."""

import pytest

from research_system.evals.harness import write_external_output


def test_runtime_output_is_external_date_suffixed_and_non_overwriting(tmp_path):
    output = tmp_path / 'p0-run_2026-07-03.json'
    write_external_output(output, {'status': 'blocked'})
    assert output.read_text(encoding='utf-8') == '{"status":"blocked"}\n'
    with pytest.raises(FileExistsError):
        write_external_output(output, {'status': 'blocked'})

def test_invalid_payload_does_not_leave_empty_output(tmp_path):
    output = tmp_path / 'invalid_2026-07-03.json'
    with pytest.raises(TypeError, match='tuple'):
        write_external_output(output, {'invalid': ('not', 'canonical')})
    assert not output.exists()



def test_runtime_output_rejects_missing_date_suffix(tmp_path):
    with pytest.raises(ValueError, match='date-suffixed'):
        write_external_output(tmp_path / 'p0-run.json', {'status': 'blocked'})


def test_runtime_output_rejects_repository_paths():
    with pytest.raises(ValueError, match='external'):
        write_external_output(
            '.research-system/evals/p0-run_2026-07-03.json',
            {'status': 'blocked'},
        )
