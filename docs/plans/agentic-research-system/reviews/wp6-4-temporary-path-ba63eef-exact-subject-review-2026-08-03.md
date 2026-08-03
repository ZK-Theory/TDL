# WP6.4 temporary-path exact-subject review - `ba63eef13`

**Date:** 2026-08-03
**Reviewer role:** fresh independent exact-subject reviewer; no remediation
**Verdict:** `accept_exact_subject` (`Critical 0`, `Major 0`, `Minor 0`)

## Exact subject and scope

| Item | Verified value |
|---|---|
| Review branch | `codex/wp64-origin-witness-r11` |
| Candidate | `ba63eef13ee86ad39e9a69e67dff1f343edce40d` |
| Candidate tree | `83e70bca56a113a21b9923d2c4b15eba90733160` |
| Required / sole parent | `09b4edeb561459d765e99c59b85405c3d5eb2d9b` |
| Current main / merge base | `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e` |
| Pull request | [#208](https://github.com/stephendor/TDL/pull/208) |
| Candidate delta | `research_system/store/identity.py`; `tests/research_system/integration/test_gate5_release_tranche.py` |

At the exact-subject decision point, local `HEAD`, configured upstream,
live branch, and PR #208 head all resolved to the candidate. The live `main`
ref and the local `origin/main` ref both resolved to the recorded main SHA;
that SHA is the candidate merge base and an ancestor of the candidate.
`git diff --check 09b4ede ba63eef` passed.

This record is a later, review-only commit and is not part of the accepted
candidate delta.

## Temporary-path verdict

Accepted mechanics:

- `_restore_transaction_temporaries` reconstructs the complete semantic
  `output`, `manifest`, and `evidence` map from the canonical target, approval
  transaction ID, output digest, and intended canonical bytes. Each entry has
  the exact semantic key, `relative_path`, and `sha256`.
- Initial construction calls that helper. Transaction parsing exact-compares the
  complete map, and the immutable-approval join independently recomputes and
  exact-compares it again.
- On resume, parsing and immutable-approval validation occur before observable
  validation and before `_cleanup_current_transaction_temporary`; state/generation
  transitions and canonical output/manifest/evidence publication occur later.
- The initial flow validates the same helper-derived representation before the
  initial durable record and before canonical mutable-object publication.

The three alternate-path negatives use valid in-target fixture paths with the
matching bytes and digests. All reject before resume cleanup while preserving
the complete durable tree, transaction bytes/generation, canonical objects,
and alternate fixture unchanged.

## Retained critical seams

- Ordinary and T2 submits both enter the shared `_submission_lock`, which runs
  the moved-restore recheck/admission only after the composite writer lock is
  held. The T2 dispatch calls that same lock path.
- The immutable approval join remains before resumed cleanup and before all
  canonical effects. Coordinated intent rewrites fail closed before mutation.
- S-014 retains its exact known-bad mutation ID, exercises real physical
  `EvidenceStoreRegistry` topology and restore preflight, and reports predicates
  from that preflight rather than a fixture claim.
- The prior `bac13f4` POSIX quarantine/retry behavior and Message controlled
  receipt behavior remain present and exercised below.

## Targeted validation

All invocations used `C:\Users\steph\TDL\.venv\Scripts\python.exe -B` with
repository `addopts` reset, `-p no:cacheprovider`, and `--no-cov`.

| Cohort | Result |
|---|---:|
| g0/g1/g2/g3 valid resume/idempotence; three alternate temporary paths; generation-observable negatives; coordinated intent rewrite | 11 passed in 135.70s |
| locked ordinary/T2 admission, including generation-two T2 no-mutation | 4 passed in 44.05s |
| S-014 real command-service seam; POSIX quarantine retry; two Message controlled-receipt cases | 4 passed in 10.78s |

Total: `19 passed`. Post-test tracked/untracked status remained limited to the
two pre-existing environment setup paths below.

## Protected surfaces and setup residue

The two-path candidate diff leaves schemas, contracts, Message paths, and P-045
identity material unchanged. In particular, parent and candidate share:

- P-045 event schema Git blob `bc3efc0fd41e3d9f24c383f2d0d196e26ba0d1e5` and
  raw SHA-256 `3aaaa6d609dce1271db3e22d8620935929fc272add1fe5c06badb77050f6d021`;
- the P-045 decision and authority-validation blobs; and
- the Message lifecycle test blob `47e6ee22df00db67239779b68a33cd48e685b994`.

The only working-tree residue at review start and after validation was
`.claude/CLAUDE.md` and `.repowise-workspace.yaml`. Both are environment setup
state, excluded from the candidate, and excluded from staging. No other tracked
or untracked residue was present. Existing ignored `.coverage` and
`.pytest_cache` artifacts predate this review and were not updated by it.

## CodeRabbit disposition and boundary

No CodeRabbit finding was supplied, triggered, or polled. Accordingly, there
is no external-review finding disposition to infer; this acceptance is based
only on the pinned source and targeted local evidence.

`accept_exact_subject` accepts the temporary-path mechanics of this exact
candidate only. It does not materialize real A8 or KAN-57 work, accept the full
WP6.4 package, alter schemas/contracts/Message/P-045, merge the PR, update
Jira, authorize a CodeRabbit action, or grant any owner/foundation authority.

**Next action:** the PR owner may make the separate integration decision using
this exact-subject record; any later substantive commit requires focused
re-review against its new SHA.
