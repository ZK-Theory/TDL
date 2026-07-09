"""Deterministic scripted transport used by all P0 tests."""

from research_system.adapters.base import TransportResult


class FakeTransport:
    def __init__(self, results: list[TransportResult]):
        self._results = list(results)
        self.invocations: list[tuple[tuple[str, ...], float]] = []

    def invoke(self, argv, stdin, timeout_s):
        del stdin
        self.invocations.append((tuple(argv), timeout_s))
        if not self._results:
            raise RuntimeError("fake transport script exhausted")
        return self._results.pop(0)
