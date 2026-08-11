# WP6.4 final certification exact-subject review

**Date:** 2026-08-10
**Workflow:** standalone
**Reviewer:** fresh independent read-only Codex reviewer with no producer context
**Verdict:** `accept_exact_subject`

## Exact reviewed subject

- Candidate commit: `9ef1e3028440a714d3528ffcb3ec2f3a301eb067`
- Candidate tree: `29be3decd2405a3adb0414be56f5fa7fc5159217`
- Current-main parent: `9e135e266dd752c514a1353feac8bdcede53a21a`
- Accepted WP6.4 artifact subject: `056cd683be21b7046c3943208e3ba8e9898051dc`
- Accepted WP6.4 artifact tree: `2c29ba05e10c93f20e9d0a28fe7f548b960c3255`
- PR #239 merge: `b61dddec8f2ba0a7e456b1e3a57d265db1f60caf`
- PR #241 merge: `9e135e266dd752c514a1353feac8bdcede53a21a`

The reviewer verified that the parent, PR #239 merge, PR #241 merge and accepted
artifact subject are in the required ancestry. Live `origin/main` and the live
remote `main` both resolved to the exact reviewed parent. The candidate delta
against that parent contains exactly:

1. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
2. `docs/plans/agentic-research-system/implementation/README.md`
3. `tests/research_system/integration/test_wp64_create_backup.py`

`git diff --check` passed, PR #241 has no overlap with those paths, and the
detached review worktree remained clean.

## Protected identities and authority boundary

The reviewer independently verified:

| Artifact | Git blob | Raw SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-4/tda-scale-v1.0.3/package-index.json` | `a95c44cb701ff06cdc43a91ab70c4575cd149dc4` | `18413c8cd6ea10978a8ef7a5011b67d940edbbf340cc95d3c72bf8753e7d7279` |
| `.research-system/contracts/wp6-4/tda-scale-v1.0.3/scale01-gate6-preflight.json` | `8a1f1c02ad799cbd1bbcd33de29fdd312b7c9992` | `204b2a219eaf603f0eafd45cb253848c072ed2c46a35ac48268ac92f7597ef49` |

The values match the canonical main checkout. No production or protected bytes
differ from the successor parent. The package remains
`admission_status: pending_wp6_6`, `dispatchable: false` and
`execution_authorized: false`.

Live KAN-57 readback records WP6.4 as integrated and D-G6-5 as accepted for the
exact artifact subject, tree, blobs and raw hashes above. That decision does not
authorize WP6.6 admission, provider use, pilot execution, research execution,
result promotion or claim promotion.

## Direct evidence

Producer terminal evidence used the repository interpreter with coverage and
pytest cache disabled:

- exact nine-file WP6.4 selection partitioned to terminal file results:
  `172 passed`;
- direct restore-before-writer-lease selection: `19 passed in 59.67s`;
- successor PR #241 composition selection: `34 passed in 77.86s`;
- decisive backup CLI remediation-red failed on the legacy fixture identity,
  then passed after the candidate's one-line correction; the full backup file
  passed `6` tests.

The independent reviewer reran bounded decisive public and cross-record seams
with
`C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -o addopts= -p no:cacheprovider`,
coverage disabled and bytecode writes suppressed:

- restore-before-writer decisive set, backup file, brief round trip and
  verification round trip: `29 passed in 115.41s`;
- governed session authority and cross-record joins: `9 passed in 54.44s`;
- closed production-consumer mapping: `5 passed in 0.32s`.

These checks exercised real CLI export/import with restart and replay,
distinct-party returned-record authority, event-first retryable backup, complete
bound-evidence drift rejection, verified-and-cleared public `CommandService`
admission, pre-lock rechecks, incomplete-restore and T2 no-mutation,
wrong-source rejection, and late artifact-change rejection.

The candidate's scoped-grant fixture correction from `2.0.0` to `2.1.0` matches
the active `ActivateAuthorityGrant` contract and `SchemaRegistry`. Historical
v2.0 replay remains separately supported. The reviewer found this to be a stale
test-fixture repair, not concealment of a production defect.

## Status-record review

Repository and live owner records support the corrected status:

- WP6.3 is integrated;
- WP6.4 is integrated and D-G6-5 is accepted;
- WP6.1 C1-C3 plus 06h, 06i and 06j are integrated after PR #241;
- WP6.1 R1/KAN-102 and final KAN-75 proof remain open;
- WP6.5 remains independent under P-042/06g;
- WP6.6 and WP6.7 retain their separate gates.

## Verdict and residual risk

`accept_exact_subject`

There are zero blocking findings. The narrow residual risk is that the reviewer
did not repeat the complete `172`-test partition or treat the non-terminal
aggregate timeout as green. Acceptance rests on exact identity and provenance
checks, terminal per-file evidence, and independently rerun decisive public and
cross-record seams. No provider, dispatch, pilot or research authority follows
from this verdict.
