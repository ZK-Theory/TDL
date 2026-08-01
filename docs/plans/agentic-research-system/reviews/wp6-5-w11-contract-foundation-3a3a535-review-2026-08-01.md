# WP6.5 W11 contract-foundation remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority, read-only
- Reviewed branch: `codex/kan58-w11-contract-foundation-r1`
- Reviewed subject: `3a3a5355c9fbc3b380e2be26fb364dbd0c0315d9`
- Direct parent: `04223674acdb82ee00d1410e960414d624c326b1`
- Tree: `a2a76186200754aa961209e9bc9133aba7214f60`
- Full subject range: 64 paths from `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Remediation range: 30 paths from the rejected `04223674acdb82ee00d1410e960414d624c326b1`
- Verdict: `rework_required`
- Findings: 0 Critical, 4 Major, 0 Minor

## Executive disposition

The remediation preserves the accepted W11 source bytes, remains inert, and
passes its focused contract suite. It corrects the earlier owner-row range,
reference-shape, assay-value-type, and subject-range weaknesses, but the actual
admission seam still accepts four semantically invalid records. The subject is
therefore quarantined and is not merge-authorized or evidence that KAN-58 is
complete.

Because this is a second semantic remediation of the original subject, the
remaining correction must be a new exact subject produced in a fresh task. It
must remain an inert contract/catalogue delivery; no runtime binding, handler,
ledger event, reducer, projection, OR-140 execution, dossier admission,
transition, or cutover is authorized.

## Exact identity and validation evidence

The reviewer verified the accepted W11 authority exactly at:

- commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256 `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes with no CRLF bytes.

The full subject changes no production Python or existing `research_system`
path, and W11 schema identifiers remain outside the runtime binding registry.
The focused contract suite passed all 15 tests:

```text
uv run pytest tests/research_system/contracts/test_w11_contract_materialization.py -p no:cacheprovider
15 passed
```

## M-01 - catalogue rows are not bound to their literal test identities

`w11-schema-catalogue-content.schema.json` validates the owner-row identifier
and the three test identifiers independently. A direct probe showed that an
`OR-140` row carrying the three `OR-001` test identities validates. W11 makes
those identities part of each literal row, so the admission control must bind
the exact row-to-test tuple and reject row/test swaps.

## M-02 - exact predecessor lineage is enforced only by a test helper

The admitted programme schema permits `revision` and
`supersedes_revision` independently. The test helper rejects a non-adjacent
predecessor, but `SchemaRegistry.validate` accepted revision 3 superseding
revision 1. Exact-predecessor validation must run at the real contract
admission seam, not only inside the test module.

## M-03 - assay scorecard domains are not resolved against the frozen rubric

The assay scorecard schema checks only the primitive value type selected by
`axis_kind`. It does not resolve the referenced frozen rubric axis or enforce
that axis's accepted bounds or set. A direct registry probe accepted an integer
score of 99 outside the intended domain. The admission seam must resolve the
rubric and reject unknown axes, kind mismatches, and out-of-domain values.

## M-04 - source references remain semantically untyped

The reference object now makes its field combinations exclusive, but a record
or artefact identity is still any non-empty string. A direct probe accepted an
artefact reference carrying an `obj_` record identifier. The admission seam
must resolve or type the identity according to `source_kind` and reject
cross-kind references.

## Residual control gap

The inertness test compares the original base through the earlier rejected
`04223674...` subject rather than the reviewed `3a3a535...` head. The current
full diff is inert, but the executable guard must be pinned to, or otherwise
cover, the actual admitted subject.

## Required bounded correction

The fresh corrective subject must add authoritative inert semantic/reference
validation for row/test binding, predecessor lineage, rubric-axis closure, and
source-reference kind. Its decisive negatives must exercise the actual
admission seam with an OR-row/test swap, non-adjacent lineage, out-of-domain
rubric value, and cross-kind reference. The accepted W11 source bytes and the
absence of runtime activation remain protected invariants.

