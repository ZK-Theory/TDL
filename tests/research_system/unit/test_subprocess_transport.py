import subprocess

import pytest

from research_system.adapters.subprocess_transport import SubprocessTransport


@pytest.mark.parametrize(
    'failure, expected_status, expected_exit_code, message',
    [
        (subprocess.TimeoutExpired(['provider'], 1), 'timed_out', 124, 'timed out'),
        (FileNotFoundError('provider missing'), 'terminal', 127, 'provider missing'),
    ],
)
def test_subprocess_failures_return_classified_result(
    monkeypatch, failure, expected_status, expected_exit_code, message
):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, 'run', fail)
    result = SubprocessTransport().invoke(['provider'], '{}', 1.0)
    assert result.status == expected_status
    assert result.exit_code == expected_exit_code
    assert message in result.stderr
    assert result.stdout == ''
