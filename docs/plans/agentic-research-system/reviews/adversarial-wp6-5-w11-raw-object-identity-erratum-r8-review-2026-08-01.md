# WP6.5 W11 raw-object identity erratum R8 exact-subject review — 2026-08-01

**Verdict:** `accept_exact_subject`

**Review mode:** fresh independent, evidence-only adversarial review.

**Authority boundary:** This verdict is evidence for a separate owner decision. It
does not accept W11 for Stephen, close D-G6-4 or KAN-19, unblock KAN-58, or
authorize implementation, transition, cutover, merge, Jira, or remote action.

## 1. Exact reviewed subject and one-path manifest

| Field | Verified value |
|---|---|
| Branch | `codex/wp65-w11-raw-object-identity-erratum` |
| Exact subject | `e73938cdb0d014a84868c3cba2d19cb502cbea2a` |
| Parent/base | `a464eb5aefed2645da48e4495efa61a27f0e3954` (`origin/main`) |
| Subject delta | one added path: `docs/plans/agentic-research-system/reviews/adversarial-wp6-5-w11-raw-object-identity-erratum-2026-08-01.md` |
| Markdown links in subject | none; all cited repository identities resolve directly from Git |

`git diff-tree` showed no other subject path. Before this review record was
created, the worktree contained only the pre-existing Repowise setup changes to
`.claude/CLAUDE.md` and `.repowise-workspace.yaml`; neither is in the subject
delta or this review's change set.

## 2. Recomputed raw W11 objects

For `docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md`,
`git log --follow` resolves exactly the five claimed path-content revisions.
Each object was read from `git cat-file blob`, strictly decoded as UTF-8, and
checked directly for BOM, LF, CR, final LF, byte size, Git blob identity, and
SHA-256. `git hash-object --stdin` over the final raw bytes also returns
`f90729d0c42a0de98d064fac0824d1969c871c82`.

| Content commit | Git blob | Bytes | LF / CR | Raw SHA-256 | Deterministic CRLF SHA-256 |
|---|---|---:|---:|---|---|
| `70074d42eade8460808e4d1d29348b7806eff2d0` | `aa6bcef43d3d98b5aff29265abde75d587979f5b` | 57765 | 855 / 0 | `4ba9028c519f8b1104e4a889c9b06de03f3707a163f1a31138a1e34e4c0a0899` | `e9f66435a4f65aa6ad10d8ee18aa69db69174a89ce1ccd989b7257b0d0a0579a` |
| `d24df9d26f0d906d177eafa1eaeabb65a5515004` | `b3f45f0c88243e7fa078afeb2316211a0130a12a` | 102864 | 1355 / 0 | `ba570a94878e2c77d5661875e7bd3fca1c4363efee4f9bd9b3f9ac28ccbb6cae` | `5f0f04373df31e411e6bb2ae125737e1ec82ba1b6bd646ad3ae068a2873abb6a` |
| `3e068c1ee5100e5a6e0bc57d0d047d993b406b2b` | `1e3deac4935b7e656985658b92c70e4a3e0da46a` | 158742 | 1765 / 0 | `c186b2381513ccdc1011a8068e7b35e15e4a128702e8179163b68837b787fa5f` | `b62afe6e8bf07f5caa3dc006bdc9fdbc42e52d304cad55ab79251af76d5b0f1c` |
| `4b941326e290582db7be07113d5d7bb78d8b97a3` | `db781ee046be07ffabfc0553a00bec62bf2a7917` | 176972 | 1931 / 0 | `91f03a701c1cf13c1972de01f5022b3bafef2dd261c7a6f7a7dd458674cb94ce` | `d7a4ca0e4b8c895d032139b222aadc64a7d082aec731530402e421d4174e1dcf` |
| `892d1d1650cdcf71d2a886318e174a18e11d5de0` | `f90729d0c42a0de98d064fac0824d1969c871c82` | 185214 | 1992 / 0 | `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70` | `93b9c2a6efad74168889cea2723280a46b80e0bd1b9b8435366dd183b6ee11b7` |

All five objects have no UTF-8 BOM and a final LF. The erratum's size, line-ending,
blob, and raw-hash assertions therefore match direct Git-object evidence.

The obsolete literal
`3011de88b6826b27bbc105dbf2ce0e2f3fa095666dec082aa0e460be9cca0799`
matches none of the ten independently hashed byte subjects in the table: neither
any raw Git object nor its deterministic CRLF materialization.

## 3. Historical literal and cited immutable evidence

`git log -S` identifies exactly three immutable assertion-introducing commits:
R5 `07d2d1315accb211d4c257cc7ea28985871dc4f1`, R6
`ef300900476a7479e7926fc345279bb09800447c`, and R7
`5b7afca85a134aea58a513853e85e2fdeae3fe57`. At the PR #121 final head,
the full literal occurs only in the three listed review records. At the reviewed
subject it occurs once more, at erratum line 43, solely to identify the value
being superseded rather than to assert it as W11's raw identity.

| Record | Commit/blob/raw SHA-256 recomputation | Literal location | Result |
|---|---|---|---|
| R5 | `07d2d1315accb211d4c257cc7ea28985871dc4f1` / `057789ec492db7e12560b0ec22aea439af569aad` / `f7c5d37736661d7c62b7ee94420e185eb93f73796b0347ea7ed439e46cee83b2` | line 9 | exact match |
| R6 | `ef300900476a7479e7926fc345279bb09800447c` / `f105a4f8566585622fad976c0cc37d15406d8d22` / `8cbe0f88a4e5fb0813e2815625a82c0e8bba5eb180dc26bf85fd0a78d6a6c7c9` | line 9 | exact match |
| R7 | `5b7afca85a134aea58a513853e85e2fdeae3fe57` / `570d2c03b56296eecf054aaec9d08fb27c3566cf` / `13abf242226fa76ed7117da0c2c4c128a3e10d75e034cc1c4a4a5a8ce8d23b03` | line 112; correct W11 blob at line 111 | exact match |

The cited PR final head is a commit and is the second parent of merge commit
`c941965a5851d8d7063c411f65f26bb0e0957594`; that merge and last W11-content
commit `892d1d1650cdcf71d2a886318e174a18e11d5de0` also resolve as commits.

## 4. Protected-byte and authority-boundary checks

At the exact subject, the protected paths still resolve to their cited blobs:

| Protected record | Current blob | Reference diff |
|---|---|---|
| W11 | `f90729d0c42a0de98d064fac0824d1969c871c82` | no difference from `892d1d1650cdcf71d2a886318e174a18e11d5de0` |
| R5 | `057789ec492db7e12560b0ec22aea439af569aad` | no difference from `07d2d1315accb211d4c257cc7ea28985871dc4f1` |
| R6 | `f105a4f8566585622fad976c0cc37d15406d8d22` | no difference from `ef300900476a7479e7926fc345279bb09800447c` |
| R7 | `570d2c03b56296eecf054aaec9d08fb27c3566cf` | no difference from `5b7afca85a134aea58a513853e85e2fdeae3fe57` |

The subject expressly preserves the historical R5/R6/R7 review records and
their semantic verdicts, but does not treat those verdicts as owner acceptance.
Its explicit negative boundary says it does not accept W11, satisfy either
D-G6-4 limb, close KAN-19, or unblock KAN-58. It instead requires any later
D-G6-4 limb-1 owner record to independently cite the committed erratum and the
corrected W11 tuple. This preserves the required separation between independent
review evidence and Stephen's owner decision.

## 5. Findings, disposition, and residual risk

No Critical, Major, Minor, or editorial finding. The correction is narrowly
factual, directly reproducible from immutable objects, limits supersession to
the three false SHA-256 assertions, leaves protected W11/R5/R6/R7 bytes intact,
and adds no acceptance or operational authority.

The residual risk is intentionally historical: the superseded value's original
checkout-derived source cannot be reconstructed from the preserved raw or
deterministic-CRLF W11 bytes. Consumers must use the corrected raw tuple and
must obtain any D-G6-4/KAN-19 disposition from its separately attributed owner
record.

## 6. Review status

`accept_exact_subject` applies only to
`e73938cdb0d014a84868c3cba2d19cb502cbea2a`. This review created only this
record. It neither stages nor changes the two pre-existing Repowise setup
modifications.
