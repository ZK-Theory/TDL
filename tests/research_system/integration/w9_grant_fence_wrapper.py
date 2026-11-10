# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §9.1, §17)
# Purpose: run a predecessor commit's own unchanged package, pause a W11 submit before its writer lock, and report
# what the grant fence does on resume. Run only as a subprocess by test_w9_wp9_3_grant_fence.py.
"""The grant fence on predecessor code (WP9.3 note §9.1; P-081 item 3, sixth amendment).

Usage: ``python w9_grant_fence_wrapper.py <predecessor root> <scratch directory> <revoked|expired|live>``.

The predecessor root is an extracted archive of a commit from before WP9.3-1. Its ``research_system`` and ``tests``
packages are put first on ``sys.path``, so the W11 runtime that runs is the predecessor's, without WP9.3-1's in-lock
binding recheck. A thread submits W11 genesis on an owner grant and pauses just before the writer lock is taken; the
main thread then revokes the grant, or moves the clock past its expiry, or leaves it live; the thread then resumes.
The result is printed as one JSON line.
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    predecessor_root, work, mode = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), sys.argv[3]
    sys.path.insert(0, str(predecessor_root))
    import research_system
    import research_system.discovery.runtime as discovery_runtime
    from research_system.discovery.accepted_w11 import CATALOGUE_STREAM_ID
    from research_system.discovery.runtime import DiscoveryRuntime
    from tests.research_system.factories import ACTORS, activate_lifecycle_grant, control_plane, revoke_lifecycle_grant
    from tests.research_system.integration.test_wp6_6_discovery_runtime import _genesis

    package = Path(research_system.__file__).resolve()
    assert package.is_relative_to(predecessor_root), package
    assert "binding_check" not in Path(discovery_runtime.__file__).read_text(encoding="utf-8")

    now = [datetime(2026, 8, 1, tzinfo=UTC)]
    harness = control_plane(work, clock=lambda: now[0])
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=CATALOGUE_STREAM_ID,
        actor_id=ACTORS["actor-a"],
        command_types=("ImportAcceptedW11CatalogueGenesis",),
        effective_at="2026-07-01T00:00:00Z",
        expires_at="2026-08-01T00:01:00Z",
    )
    root = work / "discovery"
    root.mkdir()
    runtime = DiscoveryRuntime(
        root,
        harness.ledger,
        harness.schemas,
        catalogue_path=predecessor_root / ".research-system/evals/expected/w11-portfolio-discovery-v1.json",
        authority_resolver=harness.authority_resolver,
        clock=lambda: now[0],
        repository_root=predecessor_root,
        root_tokens={"control": harness.ledger.control_root, "repo": predecessor_root},
        operational_ledger=harness.ledger,
    )
    paused, resume = threading.Event(), threading.Event()
    lock_class = discovery_runtime.CompositeWriterLock

    class PausingLock(lock_class):  # type: ignore[misc, valid-type]
        def __enter__(self):  # noqa: ANN204
            paused.set()
            resume.wait(60)
            return super().__enter__()

    discovery_runtime.CompositeWriterLock = PausingLock
    envelope = {**_genesis(), "authority_grant_id": grant_id}
    outcome: dict[str, object] = {}

    def submit() -> None:
        try:
            outcome["status"] = runtime.submit(envelope).status
        except Exception as exc:  # noqa: BLE001 - reported to the parent test
            outcome["error"] = f"{type(exc).__name__}: {exc}"

    events_before = [event["event_hash"] for event in harness.ledger.iter_events()]
    worker = threading.Thread(target=submit)
    worker.start()
    assert paused.wait(60), "the submit never reached its writer lock"
    if mode == "revoked":
        revoke_lifecycle_grant(harness, subject_id=CATALOGUE_STREAM_ID)
    elif mode == "expired":
        now[0] = datetime(2026, 8, 1, 0, 2, tzinfo=UTC)
    events_at_resume = [event["event_hash"] for event in harness.ledger.iter_events()]
    resume.set()
    worker.join(120)
    events_after = [event["event_hash"] for event in harness.ledger.iter_events()]
    print(
        json.dumps(
            {
                **outcome,
                "package": str(package),
                "appended": len(events_after) - len(events_at_resume),
                "ledger_identical": events_after == events_at_resume,
                "revocation_events": len(events_at_resume) - len(events_before),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
