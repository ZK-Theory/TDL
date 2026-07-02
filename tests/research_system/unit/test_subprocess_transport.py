import subprocess

import pytest

from research_system.adapters.subprocess_transport import SubprocessTransport


@pytest.mark.parametrize(
    'failure, expected_exit_code, message',
    [
        (subprocess.TimeoutExpired(['provider'], 1), 124, 'timed out'),
        (FileNotFoundError('provider missing'), 127, 'provider missing'),
    ],
)
def test_subprocess_failures_return_terminal_result(
    monkeypatch, failure, expected_exit_code, message
):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, 'run', fail)
    result = SubprocessTransport().invoke(['provider'], '{}', 1.0)
    assert result.status == 'terminal'
    assert result.exit_code == expected_exit_code
    assert message in result.stderr
    assert result.stdout == ''
