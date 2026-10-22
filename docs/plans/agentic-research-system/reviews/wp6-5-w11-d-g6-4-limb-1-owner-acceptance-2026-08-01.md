# WP6.5 W11 D-G6-4 limb-1 exact-revision owner acceptance

## Decision provenance

Statement provenance: owner-supplied task message

Recorded date: 2026-08-01

Acceptance timestamp: not recorded; none is invented.

After the Manager supplied the corrected W11 raw-object tuple, the accepted R8
review identity, and the PR #202 integration identity, Stephen replied:

> I accept the corrected exact W11 revision for D-G6-4 limb 1 as PR 202

In its immediate context, this accepts the exact specification identity below.
It does not accept a mutable branch, a later commit, regenerated content, a
checkout-derived digest, or merely equivalent prose.

## Accepted identity tuple

- W11 path:
  `docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md`.
- Last W11 content commit:
  `892d1d1650cdcf71d2a886318e174a18e11d5de0`.
- PR #121 final head: `5b7afca85a134aea58a513853e85e2fdeae3fe57`.
- PR #121 merge commit: `c941965a5851d8d7063c411f65f26bb0e0957594`.
- W11 Git blob: `f90729d0c42a0de98d064fac0824d1969c871c82`.
- W11 raw object: 185,214 bytes; strict UTF-8; no BOM; 1,992 LF
  bytes; zero CR bytes; final LF.
- W11 raw-object SHA-256:
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`.

PR #202 supplies the additive correction and independent verification that make
that tuple owner-disposition-ready:

- Erratum subject: `e73938cdb0d014a84868c3cba2d19cb502cbea2a`.
- Erratum tree: `59fb11a62a5a132cf3185704578cb73c170de979`.
- Erratum parent: `a464eb5aefed2645da48e4495efa61a27f0e3954`.
- Erratum record:
  `docs/plans/agentic-research-system/reviews/adversarial-wp6-5-w11-raw-object-identity-erratum-2026-08-01.md`;
  Git blob `2e184891eb459c43652041c4bd453654da0a3653`; 5,862 raw
  bytes; raw SHA-256
  `4401a928bfe2c98c4c29d7704443e24084da4f55de48f9a0de85583a59f34a40`.
- R8/final PR head: `14975af6590282a8018ca8fcce05f08ef08fac2d`.
- R8/final tree: `56f8e572c75368810aa65598c4cb8ef07f81e12a`.
- R8 direct parent: `e73938cdb0d014a84868c3cba2d19cb502cbea2a`.
- R8 record:
  `docs/plans/agentic-research-system/reviews/adversarial-wp6-5-w11-raw-object-identity-erratum-r8-review-2026-08-01.md`;
  Git blob `7039d562f4cd9dac9ab06002aca12c0cc6d64043`; 6,965 raw
  bytes; raw SHA-256
  `245530ebf868f55c17afe5d37b9433d8cc865800ef352d281f598cf46df1ddb1`.
- PR #202 merge commit:
  `c84eb2aaf0890d36d3735d08a14169f4c50935cd`.
- PR #202 merge tree: `56f8e572c75368810aa65598c4cb8ef07f81e12a`.
- PR #202 merge parents:
  `a464eb5aefed2645da48e4495efa61a27f0e3954` and
  `14975af6590282a8018ca8fcce05f08ef08fac2d`.

The historical literal
`3011de88b6826b27bbc105dbf2ce0e2f3fa095666dec082aa0e460be9cca0799`
is explicitly excluded. It matches neither the five preserved raw W11 Git
objects nor their deterministic CRLF materializations and is not part of this
acceptance.

## Independent review basis

The W11-specific R5, R6, and R7 records approved the final W11 subject and its
bounded follow-up subjects while preserving the W11 blob:

- R5 reviewed exact W11 content subject
  `892d1d1650cdcf71d2a886318e174a18e11d5de0` and returned `approved`.
  Its immutable report is commit
  `07d2d1315accb211d4c257cc7ea28985871dc4f1`, Git blob
  `057789ec492db7e12560b0ec22aea439af569aad`.
- R6 reviewed follow-up subject
  `c21b366caa751265e455435f23d1232f0bb6220c` and returned `approved`.
  Its immutable report is commit
  `ef300900476a7479e7926fc345279bb09800447c`, Git blob
  `f105a4f8566585622fad976c0cc37d15406d8d22`.
- R7 reviewed erratum subject
  `4e7ec91a7815b808ae0ee8af3421eab20840094e` and returned `approved`.
  Its immutable report is commit
  `5b7afca85a134aea58a513853e85e2fdeae3fe57`, Git blob
  `570d2c03b56296eecf054aaec9d08fb27c3566cf`.

All three records resolve W11 to blob
`f90729d0c42a0de98d064fac0824d1969c871c82`, but their copied raw SHA-256
assertion was later shown to be unreproducible. PR #202 did not rewrite those
immutable review epochs. Its additive erratum supersedes only the three false
digest assertions.

Fresh R8 review recomputed every historical W11 object directly from Git,
reproduced the accepted blob and corrected raw digest, verified the three
protected historical occurrences, and confirmed that W11 and the R5/R6/R7
records were unchanged. Its verdict was `accept_exact_subject`, with 0
Critical, 0 Major, and 0 Minor findings.

## Effect and boundary

This decision closes **D-G6-4 limb 1** for the exact W11 specification identity
above. It permits KAN-58 to materialize and independently review the inert,
strict W11 schema catalogue and to prepare a separate external catalogue
acceptance envelope. The accepted W11 file is not rewritten merely to embed
this later lifecycle state; this external record supplies the disposition.

This acceptance does not:

- accept any not-yet-materialized schema, catalogue, observation, review, or
  catalogue-acceptance envelope;
- activate a runtime binding, command handler, ledger event, reducer,
  projection, dossier admission, path writer, or verified-genesis import;
- approve D-G6-4 limb 2 or any first ownership-transition batch;
- admit a dossier, transition ownership, migrate or cut over a path, revoke a
  writer, deprecate or retire a legacy surface;
- authorize provider activity, credentials, research dispatch, results,
  eligibility, claims, publication, Gate 6, or Gate 7; or
- infer acceptance from PR merge, tests, review, or Jira state alone.

## Mechanical verification and Jira record

Before recording this decision, the Manager resolved the accepted W11,
erratum, R8, PR-head, and merge identities from Git at current `main`, and
recomputed the two PR #202 record sizes and raw SHA-256 values. Every identity
above matched. No behavioural test was rerun for this provenance-only owner
record.

KAN-19 comments `10357` and `10358` record the integration evidence and the
owner statement. KAN-58 comment `10359` records the resulting narrow start of
the inert catalogue-materialization lane. Jira remains tracking evidence; this
Git record is the durable exact-byte decision surface.
