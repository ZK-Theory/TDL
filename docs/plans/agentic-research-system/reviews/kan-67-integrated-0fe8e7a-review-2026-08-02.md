# KAN-67 integrated exact-subject review — 2026-08-02

## Identity

- Subject: `0fe8e7ae1ac2ed3edab5b4dfe2f85d5ab8ab1f67`
- Pinned base: `7341a657cb94fd6ff0ef598f0dd02893a3938f83`
- Accepted producer ancestor: `1e0b04b69365b62ac28a6f8933faa9e41f44b4e9`
- Pre-integration review-record ancestor: `268b0ac21bff5ff4323fe245bb47c90d9f94b754`
- Exact diff: 31 paths
- Verdict: `rework_required`
- Findings: 2 Critical, 0 Major, 0 Minor

The subject, base ancestry, remote equality, path count, and clean source diff
were independently verified. The KAN-67 receipt-recovery and composite-lock
integration seams did not produce a separate finding.

## Findings

### C-01 — caller-controlled record time can revive an expired grant

`ExternalAssuranceRecordStore.write()` passes
`publication_context.occurred_at` into authority resolution. Grant
effectiveness and expiry are consequently evaluated against caller-controlled
record metadata. A grant that is now expired but is not revoked can authorize a
new publication when the caller backdates `occurred_at` into its former
validity window.

Required correction: evaluate publication authority under the writer lock
against an injected trusted current clock. Retain `occurred_at` only as record
metadata. Add expired-backdate and future-timestamp negative controls.

### C-02 — independent-review relationship evidence is not joined at acceptance

The writer compares the supplied relationship identifier with the record field
but does not establish that the relationship exists or is the correct current
relationship. The pack loader validates an independent review's subject,
owner link, and timing but does not join its `relationship_record_id`, actor
endpoints, minimum independence grade, or validity window to the resolved
producer-relationship evidence. A schema-valid review can therefore cite a
missing or foreign relationship and still contribute to acceptance.

Required correction: at the acceptance boundary, require the review's
relationship identifier, actor endpoints, grade, and validity window to match
the resolved current relationship. Add missing, foreign, stale, and
insufficient-grade controls.

## Evidence disposition

Manager combined-head evidence before this review remains useful but does not
override the reachable findings: 43 external-publication tests, 52 scoped
activation tests, 39 scope/task authority tests, and 51 store tests passed.
The reviewer selected 13 additional exact nodes, but that run produced no
result before its cap and was stopped; it is not counted as green evidence.

No remediation, acceptance, Jira completion, or merge was performed by the
reviewer.
