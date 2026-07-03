"""Versioned count evidence with explicit, non-interchangeable units."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CountEvidence:
    counter_id: str
    units: str
    count: int
    exact: bool


@dataclass(frozen=True)
class ProviderCountEvidence:
    counter_id: str
    units: str
    count: int
    exact: bool
    provider: str
    model: str
    rendering_revision: str
    evidence_revision: str


class ReferenceRegexV1:
    counter_id = "ars-reference-regex-v1"

    def count(self, text: str) -> CountEvidence:
        count = len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
        return CountEvidence(self.counter_id, "ars_reference_tokens", count, True)


class Utf8ByteEvidenceV1:
    counter_id = "utf8-byte-evidence-v1"

    def count(self, text: str) -> CountEvidence:
        return CountEvidence(
            self.counter_id, "utf8_bytes", len(text.encode("utf-8")), True
        )
