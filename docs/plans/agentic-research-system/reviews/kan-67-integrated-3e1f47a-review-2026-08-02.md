# KAN-67 corrected integrated exact-subject review — 2026-08-02

## Identity

- Subject: `3e1f47ad0b1c4ca0caa309a147b719353b2d7bb0`
- Tree: `bc3a3f50833d9cce64905ecfd2981e68495029bb`
- Base/current `origin/main`: `7275184e41fbfb149d2c91462ac872012d29a961`
- Correction parent: `c7004404b9b24155b88ee1bda5f9b6715dc79f63`
- Accepted producer ancestor: `1e0b04b69365b62ac28a6f8933faa9e41f44b4e9`
- Exact diff: 33 paths
- Verdict: `accepted`
- Findings: 0 Critical, 0 Major, 0 Minor

The subject, tree, base ancestry, path count, diff check, and equality of local
HEAD, upstream, and the live remote branch were independently verified. All 33
reviewed paths matched the committed subject bytes. The review worktree's only
local modifications were pre-existing setup changes outside the reviewed
paths.

## Prior-finding closure

### C-01 — closed

`ExternalAssuranceRecordStore.write()` obtains its injected trusted clock
inside the writer-lock interval and passes that time to fresh replay-backed
authority resolution. `occurred_at` remains validated action metadata and is
not used as the authority time. The expired-backdate and future-metadata
controls passed: 2 tests.

### C-02 — closed

Pack acceptance now requires the independent review's relationship identifier
to equal the resolved relationship and checks reviewer-to-producer roles,
context, current validity, and the relationship's minimum grade. Missing,
foreign, stale, insufficient-grade, and role controls passed: 7 parametrized
cases.

## Additional reviewed surfaces

The reviewer also confirmed the corrected CodeRabbit surfaces: strict
non-boolean revisions, shared selective durability-error handling, native
Windows sharing-denial plus live-writer classification, Windows/Linux
process-instance fail-closed behavior, activation cleanup invariants, CLI
actor-class choices and success path, narrow revocation mapping, and resolver
and provenance corrections.

The deliberate dispositions remain valid: final marker evidence fails closed;
recovery does not sweep ambiguous crash residue; `_RECORD_ENVELOPE` remains
private; and replay mapping was not generalized without a demonstrated defect.

## Residual boundary

Trusted clock provenance remains an in-process control-plane deployment
boundary. Unsupported lock-identity platforms fail closed. No broad suite was
rerun by the reviewer.

## Disposition

The corrected exact subject is accepted. C-01 and C-02 are closed, and no
required finding remains.
