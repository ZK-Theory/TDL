from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from research_system.errors import ArsError
from research_system.evidence.consumers import ArtefactConsumerContext
from research_system.methods.brief import _resolve_artefact


class Consumers:
    def __getattr__(self, name):
        def resolve(context, *, consumer_id):
            return SimpleNamespace(method=name, context=context, consumer_id=consumer_id)

        return resolve


@pytest.mark.parametrize(
    ("purpose", "method", "consumer_id"),
    (
        ("result_analysis", "resolve_for_result", "rm03_result_assessment"),
        ("independent_review", "resolve_for_review", "rm03_brief_review"),
        ("manuscript_review", "resolve_for_manuscript", "rm03_brief_manuscript"),
        ("claim_review", "resolve_for_claim", "rm03_claim_assessment"),
    ),
)
def test_closed_purpose_uses_fixed_production_consumer(purpose, method, consumer_id) -> None:
    context = ArtefactConsumerContext("art_x", "1" * 64, "prj_x", "tsk_x", "scope", datetime.now(UTC))
    result = _resolve_artefact(Consumers(), purpose=purpose, context=context)
    assert (result.method, result.consumer_id) == (method, consumer_id)


def test_attachment_is_closed_to_review_and_manuscript() -> None:
    context = ArtefactConsumerContext("art_x", "1" * 64, "prj_x", "tsk_x", "scope", datetime.now(UTC))
    with pytest.raises(ArsError, match="only to review or manuscript"):
        _resolve_artefact(Consumers(), purpose="result_analysis", context=context, attachment=True)
