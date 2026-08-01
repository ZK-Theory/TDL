# WP6.5 W11 contract-foundation exact-envelope review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority,
  read-only
- Reviewed branch: `codex/review-kan58-w11-envelope-21e91d9`
- Reviewed subject: `21e91d926ca3964f46c45024796cb1c16532ee00`
- Direct parent: `f0b075eb7147da90b8df326688fcd0243769fedf`
- Tree: `5246db5929eb7e4f3727ac55b3c672521c80ae69`
- Full materialization base:
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Full range: 65 paths
- Corrective delta: 2 paths
- Verdict: `accept_exact_subject`
- Findings: 0 Critical, 0 Major, 0 Minor

## Executive disposition

The exact subject closes both remaining W11 envelope-control findings. The
committed tests no longer claim a stale candidate SHA, tree, or path count;
they exercise reusable envelope invariants through an independent synthetic
Git DAG. The verifier now requires its base to be an ancestor of its subject
before comparing the range and distinguishes the normal non-ancestor result
from Git execution failure.

The reviewer independently generated the final external envelope for the
actual candidate and verified all 65 strictly sorted path/blob pairs through
the real CLI. The accepted W11 source bytes and inert runtime boundary remain
unchanged. The subject is accepted for PR integration.

This verdict accepts only the inert W11 materialization foundation. It is not
owner acceptance of the future complete W11 catalogue, runtime activation,
OR-140 genesis, Discovery behavior, dossier admission, TDA-scale admission,
or Gate 6.

## Exact identity and range

The reviewer confirmed:

- exact branch, subject, parent, tree, remote, and required ancestry;
- clean substantive worktree status and clean `git diff --check`;
- corrective delta exactly:
  - `tools/verify_w11_materialization.py`;
  - `tests/research_system/contracts/test_w11_contract_materialization.py`;
- 65 paths in the complete materialization range; and
- no production `research_system`, contract, schema, or accepted W11-source
  path in the corrective delta.

The full range contains no net production `research_system` path and remains
outside runtime activation.

## Decisive behavioral evidence

```text
Focused W11 contract module: 26 passed
Ruff on the two corrective paths: passed
git diff --check: passed
External final-subject envelope: real CLI accepted
External envelope tree: 5246db5929eb7e4f3727ac55b3c672521c80ae69
External envelope manifest: 65 strictly Python-sorted path/blob pairs
```

The synthetic Git fixture contains a base, a real descendant, and an unrelated
root with an otherwise complete and correct envelope. Direct probes confirmed:

- ancestry exit 0 returns true;
- ancestry exit 1 returns false and yields the specific typed non-ancestor
  rejection before range comparison; and
- any other Git failure yields a typed lookup failure.

The production materialization base remains exactly
`c84eb2aaf0890d36d3735d08a14169f4c50935cd`. No candidate commit attempts to
contain its own future Git identity; the chronologically later independent
review record is the durable binding for the final SHA/tree/range.

## Protected authority

The accepted W11 source remained exact:

- commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

No contract/schema/W11-source byte changed in the corrective delta, and no
runtime binding, handler, ledger event, reducer, projection, OR-140 import,
dossier admission, transition, migration, or cutover was introduced.

## Integration boundary

The accepted subject may be opened as one PR because its complete 65-path
range is below the 100-file limit. The PR must retain this exact subject as an
ancestor and remain subject to the normal external review/check gate. KAN-58
must remain open after this foundation merges until its actual catalogue,
independent observation/review, and acceptance criteria are met.
