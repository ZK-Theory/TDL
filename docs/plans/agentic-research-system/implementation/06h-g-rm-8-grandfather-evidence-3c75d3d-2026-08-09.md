# WP6.1 06h G-RM-8 GRANDFATHER construction evidence

**Evidence date:** 2026-08-09

**Candidate lineage:** `3c75d3d102d8fe14746b19662005e88c4b776ffa`

**Owner packet ancestor:** `a23ef34d5521c16b489412ba7ac04247cb4fe8e2`

**Branch:** `codex/wp6-1-kan95-06h-reconcile-9736c90`

**Decision record:**
`06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json`

**Decision SHA-256:**
`07eac8199ffb48ceea6e0d235f0f2193fac4ebaae4b1e3340e39899e59927c74`

## Capability status

Capability status is **INCOMPLETE**. The real current-producer path and the
selected G-RM-8 exact-prefix admission path are constructed and proven. The
exact remaining 06h gap is the final G-RM-9 binding census after PR #229 is
integrated, followed by one fresh no-history exact-subject review and Stephen's
separate acceptance of that complete subject.

No review was commissioned from this construction subject. No PR, merge, 06i,
G-RM-14, C2 mutation, provider action, Gate 6 closure, C3, or R1 action occurred.

## Attributed decision and frozen prefix

Stephen recorded:

`SELECT G-RM-8 GRANDFATHER for candidate lineage 3c75d3d; authorize bounded construction and required evidence capture.`

The public capture seam read the bound store manifest and an expected
`LedgerSnapshot`, then re-read the tail after deriving the evidence. The
canonical decision binds:

| Field | Exact value |
|---|---|
| Project | `prj_01978abc-1000-7000-8000-000000001000` |
| Store identity | `2df87684ef33136d85adff91d58a8e91fc31a061a53ced6932988df4e687cd7a` |
| Maximum global position | `79` |
| Tail event hash | `aaa83100505c0f8298a334904e0c969f89bd73cb7ee2fbbbee20d020316b17bb` |
| Raw path-and-byte prefix SHA-256 | `84b466194993c94eaa80a30d90cd5f2dbdc74537d57b7fa94303b231d185a0e4` |
| Exact 79-event set SHA-256 | `afbfdc724a7e288e49021f8ce4947ed720245e122b28851bc11b9ef3fb3cfdd3` |
| Missing-triple positions | exact empty set `[]` |
| Empty missing-triple-set SHA-256 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| Batch count | `76` |
| Evidence SHA-256 | `f1bd38e309dbad817e09eb1fa76e36b3b7fca847562e8cab357bc52d6a30e7a7` |

The tail file is
`00000000000000000079-txb_019fe641-0d01-7a22-87b8-47660717bc32.jsonl`.
Its event at position 79 is `ArtefactRegistered`.

## Executable protocol

`research_system.projection.grandfather` supplies the deterministic public
capture, canonical decision load/materialization, exact-prefix verification,
and replay seam. Admission fails closed when the store identity, project,
maximum, tail hash, raw prefix, event set, or missing-triple evidence differs.
A non-empty missing-triple set is never admitted by this decision.

Later batches are excluded from the frozen raw-prefix fingerprint and may be
replayed only when their command-schema identity is complete and registry
valid. Repeated replay returns the same projection. Decision materialization is
write-once/idempotent and checks the caller-witnessed ledger snapshot before
capture, before publication, and after publication. A changed expected tail
raises `ConflictError` rather than publishing a silently stale decision.

The old `legacy_command_provenance_through_position` argument now rejects every
non-zero value. A position alone is not an admissible historical protocol.

## Watched public evidence

The first contract run failed during collection because the public module did
not yet exist. After implementation:

* 13 focused G-RM-8/position-only tests passed in 13.33 seconds.
* Capture and canonical materialization were stable and idempotent.
* A changed expected tail failed before decision publication and left no file.
* The exact frozen prefix plus a later complete event replayed successfully.
* A later event missing the command-schema triple failed at its new position.
* Prefix rewrite, changed identity/fingerprint/maximum/event set/missing-set
  pins, and non-empty missing-triple evidence all failed closed.

Against the real paused Control store, the public seam captured the exact cut
with `runtime/writer.lock` absent both before and after. Two full replays using
the real `LedgerAuthorityGrantResolver` validator both reached position 79,
returned the same projection, and ended at the exact tail hash. A read-only
changed-prefix negative raised:

`IntegrityError: grandfather prefix evidence mismatch`

No canonical Control file was written.

## Candidate-head validation

Interpreter: `C:\Users\steph\TDL\.venv\Scripts\python.exe`.

With plugin autoload, pytest cache, and coverage disabled, the exact mandated
five-file set passed:

~~~text
tests/research_system/unit/test_schema_registry.py
tests/research_system/unit/test_command_service.py
tests/research_system/unit/test_wp6_2_t2_runtime.py
tests/research_system/unit/test_replay.py
tests/research_system/unit/test_grandfather_prefix.py

168 passed in 196.50s
~~~

`ruff check research_system tests/research_system/unit/test_grandfather_prefix.py tests/research_system/unit/test_replay.py`
also passed.

The previously recorded release-publication failures remain parent-baseline;
this G-RM-8 change does not reclassify them. The absent pre-06h freeze remains
non-reconstructible and no substitute was created.

## Preserved authority and next action

The protected command-schema tree
`8a86a0c4921343e6a3afca3f491fad33e9a8a10f`, event-schema tree
`058c1d5ddcb9d249916977f12b11768b6d15de0f`, and owner-catalogue blob
`1adc66921ee9c90d8786ff173748150922f1035e` remain unchanged.

PR #229 is active WP6.4 schema work. Its integration does not invalidate this
frozen prefix, but it can change the final active-binding census. The next
production action is therefore to reconcile that census after PR #229 lands,
form the complete exact 06h subject, and only then commission the single fresh
no-history reviewer.
