"""Disabled-by-policy subprocess transport for later bounded live use."""

import subprocess

from research_system.adapters.base import TransportResult


class SubprocessTransport:
    def invoke(self, argv, stdin, timeout_s):
        completed = subprocess.run(
            argv,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
            shell=False,
        )
        return TransportResult(
            status="terminal",
            stdout=completed.stdout,
            stderr=completed.stderr,
            provider_request_id=None,
            exit_code=completed.returncode,
        )
