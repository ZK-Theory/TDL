# WP6.5 W11 raw-object identity erratum — 2026-08-01

**Record class:** additive factual erratum; evidence input only
**Governing issue:** KAN-19
**Correction scope:** the three downstream W11 SHA-256 assertions identified below
**Authority:** none; Stephen retains D-G6-4 owner authority

## 1. Correct raw-object tuple

The corrected repository subject is:

| Field | Exact value |
|---|---|
| W11 path | `docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md` |
| Last W11 content commit | `892d1d1650cdcf71d2a886318e174a18e11d5de0` |
| PR #121 final head | `5b7afca85a134aea58a513853e85e2fdeae3fe57` |
| PR #121 merge commit | `c941965a5851d8d7063c411f65f26bb0e0957594` |
| Git object type | `blob` |
| Git blob | `f90729d0c42a0de98d064fac0824d1969c871c82` |
| Raw object size | `185214` bytes |
| Encoding and line endings | strict UTF-8, no BOM, `1992` LF bytes, `0` CR bytes, final LF |
| Raw-object SHA-256 | `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70` |

The bytes were read directly from the Git object database with `git cat-file
blob`, before any checkout filter or text conversion. Rehashing those same
bytes with `git hash-object --stdin` reproduces
`f90729d0c42a0de98d064fac0824d1969c871c82`.

## 2. Historical-revision exclusion

The complete W11 path-change chain through PR #121 contains these five raw
objects:

| Content commit | Git blob | Bytes | LF / CR | Raw SHA-256 |
|---|---|---:|---:|---|
| `70074d42eade8460808e4d1d29348b7806eff2d0` | `aa6bcef43d3d98b5aff29265abde75d587979f5b` | 57765 | 855 / 0 | `4ba9028c519f8b1104e4a889c9b06de03f3707a163f1a31138a1e34e4c0a0899` |
| `d24df9d26f0d906d177eafa1eaeabb65a5515004` | `b3f45f0c88243e7fa078afeb2316211a0130a12a` | 102864 | 1355 / 0 | `ba570a94878e2c77d5661875e7bd3fca1c4363efee4f9bd9b3f9ac28ccbb6cae` |
| `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b` | `1e3deac4935b7e656985658b92c70e4a3e0da46a` | 158742 | 1765 / 0 | `c186b2381513ccdc1011a8068e7b35e15e4a128702e8179163b68837b787fa5f` |
| `4b941326e290582db7be07113d5d7bb78d8b97a3` | `db781ee046be07ffabfc0553a00bec62bf2a7917` | 176972 | 1931 / 0 | `91f03a701c1cf13c1972de01f5022b3bafef2dd261c7a6f7a7dd458674cb94ce` |
| `892d1d1650cdcf71d2a886318e174a18e11d5de0` | `f90729d0c42a0de98d064fac0824d1969c871c82` | 185214 | 1992 / 0 | `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70` |

The historical literal
`3011de88b6826b27bbc105dbf2ce0e2f3fa095666dec082aa0e460be9cca0799`
matches none of these raw revisions. It also matches none of their deterministic
CRLF materializations. No preserved byte subject reproduces that value, so its
source cannot now be independently reconstructed. It is an unrecoverable
checkout-derived observation, not a defensible raw Git-object identity.

## 3. Precisely superseded assertions

Before this erratum, the historical literal occurred in exactly three
downstream review assertions:

| Historical record | Immutable identity | Affected line |
|---|---|---:|
| `reviews/adversarial-wp6-5-w11-spec-remediation-r5-review-2026-07-19.md` | commit `07d2d1315accb211d4c257cc7ea28985871dc4f1`; blob `057789ec492db7e12560b0ec22aea439af569aad`; SHA-256 `f7c5d37736661d7c62b7ee94420e185eb93f73796b0347ea7ed439e46cee83b2` | 9 |
| `reviews/adversarial-wp6-5-w11-coderabbit-remediation-r6-review-2026-07-19.md` | commit `ef300900476a7479e7926fc345279bb09800447c`; blob `f105a4f8566585622fad976c0cc37d15406d8d22`; SHA-256 `8cbe0f88a4e5fb0813e2815625a82c0e8bba5eb180dc26bf85fd0a78d6a6c7c9` | 9 |
| `reviews/adversarial-wp6-5-w11-r5-erratum-r7-review-2026-07-19.md` | commit `5b7afca85a134aea58a513853e85e2fdeae3fe57`; blob `570d2c03b56296eecf054aaec9d08fb27c3566cf`; SHA-256 `13abf242226fa76ed7117da0c2c4c128a3e10d75e034cc1c4a4a5a8ce8d23b03` | 112, paired with the correct blob at line 111 |

For every later interpretation or citation of those lines, resolve W11 as the
tuple:

`(Git blob f90729d0c42a0de98d064fac0824d1969c871c82,
raw size 185214,
raw SHA-256 65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70)`.

This supersession applies only to the literal SHA-256 identity assertion. The
historical text remains unchanged. R5, R6, and R7 retain their exact reviewed
subjects, `approved` semantic verdicts, zero-finding counts, finding
dispositions, chronology, and action boundaries.

## 4. Preservation and authority boundary

This erratum does not modify W11, R5, R6, R7, their Git objects, or their
historical review epochs. It does not create a new W11 subject merely to repair
an external provenance assertion.

The accepted 2026-07-18 bounded catalogue-bootstrap and annotation-epoch policy
choices remain unchanged. This record does not:

- accept W11 or change its recorded status;
- satisfy D-G6-4 limb 1 or supply Stephen's exact-revision disposition;
- satisfy D-G6-4 limb 2 or approve an ownership-transition batch;
- close KAN-19 or unblock KAN-58;
- materialize schemas, catalogues, runtime, or projections;
- admit a dossier, register a path, migrate or transition an item, or cut over
  a path;
- authorize any implementation, result, eligibility, claim, merge, Jira, or
  remote action.

Any later D-G6-4 limb-1 owner record must cite this erratum by its externally
computed committed Git blob and raw SHA-256, together with the corrected W11
tuple. This erratum is evidence for that separate owner decision; it is not the
owner record itself. No owner disposition may be requested against
`3011de88...`.

## 5. Action boundary

Creating and recording this one new erratum file is the sole repository change
attributable to this correction step. Pre-existing unrelated worktree changes
remain untouched. No earlier evidence, branch, Jira issue, pull request,
comment, review thread, remote ref, acceptance state, schema/runtime state,
admission, transition, cutover, result, eligibility, or claim state is changed.
