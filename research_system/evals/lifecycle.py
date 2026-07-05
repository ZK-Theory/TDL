"""Owner-defined evaluation execution identity allocation."""

from research_system.ids import new_id


def start_evaluation(
    fixture_id: str,
    fixture_revision: str,
    subject_hash: str,
    *,
    retry_of: str | None = None,
) -> str:
    """Allocate a fresh run identity; content and lineage remain separate."""
    del fixture_id, fixture_revision, subject_hash, retry_of
    return new_id("evaluation_run")
