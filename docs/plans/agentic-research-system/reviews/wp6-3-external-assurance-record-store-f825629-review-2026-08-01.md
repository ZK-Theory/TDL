# WP6.3 external assurance-record store third-remediation exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 0 Critical, 1 Major, 1 Minor.

This is a fresh, independent, read-only review of the exact corrective
subject. It is not owner acceptance, PR or merge evidence, production
multi-party materialization, A7 closure, or Gate 6 acceptance.

## Exact review identity

- Producer task: `019fbebc-2423-7b32-a422-83cfd32e1225`
- Independent reviewer task: `019fbee7-2490-7081-9748-ba2854e4fd4b`
- Subject: `f825629887d05bc906cc9719d622bee4a7a56f0a`
- Parent: `159ece7c13f452da9942265586bced8d298cca6f`
- Tree: `867c09252e5d096be4654379ef7817d026001463`
- Producer remote: `origin/codex/kan67-external-assurance-record-store-r3`
- Exact corrective delta: 4 paths
  - `research_system/command/service.py`
  - `research_system/store/lock.py`
  - `tests/research_system/integration/test_external_assurance_record_publication.py`
  - `tests/research_system/unit/test_store.py`

The reviewer confirmed the exact subject, parent, tree, ancestry, remote and
local-review-ref equality, four-path boundary, and clean review state. All 16
protected WP6.3 contract, schema, and authority files matched parent and
subject at both Git-blob and raw-byte SHA-256 level.

## Executive disposition

The subject closes the prior critical cross-command rollback defect and the
stale-lock compare/unlink race. It also makes crashed marker-temp recovery
bounded and materially strengthens command, event, provenance, generation,
payload, and object ownership checks.

One exact identity remains incomplete. The recovery marker records the
resolved command-schema digest but records only the event schema's ID and
version. Replacing the event schema raw bytes without changing those advertised
fields is accepted on restart. A cleanup-order edge can also remove the final
committed marker before discovering a valid foreign temp, leaving retry in a
non-convergent conflict.

The subject remains quarantined. It is a clean rejected handoff point and must
not be integrated. Any later correction is a new exact subject requiring fresh
independent review.

## M-01 - event-schema raw-byte identity remains unbound

At `research_system/command/service.py:343`, the prepared recovery identity
stores only the event schema ID and version. The recovery match at
`research_system/command/service.py:603` compares only those advertised values,
not the resolved event schema digest or raw source identity.

The reviewer committed a marker, replaced only the event schema raw bytes while
retaining the same ID and version, and restarted recovery. The operation was
accepted and reported `ACCEPTED_CHANGED_EVENT_SCHEMA_BYTES`.

Recovery and exact retry must bind and compare the independently resolved event
schema digest/raw identity used to validate and append the event. ID/version
equality cannot substitute for exact schema-source identity.

## m-01 - cleanup ordering can strand valid foreign temporary residue

At `research_system/command/service.py:405`, committed-marker cleanup removes
the final marker before validating related temporary files. At
`research_system/command/service.py:417`, a valid foreign temp is then rejected.

That order can leave a committed operation with its final marker deleted while
the conflicting temp remains. A later exact retry sees conflict instead of
deterministically reconstructing the committed result or preserving an
unambiguous owner record. Cleanup must validate ownership of every candidate
residue before removing the final recovery authority.

## Preserved closures and validation

The fresh reviewer independently established:

```text
C1-to-C2 later-owner preservation: 1 passed
Marker and schema controls: 4 passed
Lock and recovery controls: 8 passed
Focused external-publication slice: 11 passed
Focused scoped-authority slice: 9 passed, 43 deselected
Focused Ruff and git diff --check: passed
Protected WP6.3 identities: all 16 byte- and blob-identical
Tracked and untracked review state: clean
```

The cross-command control proves that an interrupted first command no longer
deletes the later command's event, object, or replay projection when both use
the same grant bytes. Direct inspection and controls also establish that stale
lock reclaim now moves an observed lock into a private reclaim generation and
deletes only that private claim, closing the previous compare-then-unlink ABA.

Those green controls do not establish raw event-schema identity or the cleanup
ordering above. No provider, credential, live research, real grant, real
multi-party record, or acceptance pack was accessed or materialized.
