"""Disabled-by-policy subprocess transport for later bounded live use."""

import subprocess  # nosec B404 - explicit argv-only provider process boundary

from research_system.adapters.base import TransportResult


class SubprocessTransport:
    """Invoke a provider process without leaking process exceptions."""

    def invoke(
        self, argv: list[str], stdin: str, timeout_s: float
    ) -> TransportResult:
        """Return a classified result without leaking process exceptions."""
        try:
            completed = subprocess.run(  # nosemgrep  # nosec B603 - reviewed argv-only boundary
                argv,
                input=stdin,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TransportResult(
                status='timed_out',
                stdout=exc.stdout or '',
                stderr=f'provider process timed out after {timeout_s} seconds: {exc}',
                provider_request_id=None,
                exit_code=124,
            )
        except OSError as exc:
            return TransportResult(
                status='terminal',
                stdout='',
                stderr=f'provider process could not be started: {exc}',
                provider_request_id=None,
                exit_code=127,
            )
        return TransportResult(
            status='terminal',
            stdout=completed.stdout,
            stderr=completed.stderr,
            provider_request_id=None,
            exit_code=completed.returncode,
        )
