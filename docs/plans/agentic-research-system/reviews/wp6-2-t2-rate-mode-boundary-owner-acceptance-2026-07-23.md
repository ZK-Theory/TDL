# WP6.2 T2 rate-mode boundary exact-byte owner acceptance

## Decision provenance

Statement provenance: owner-supplied task message

Recorded date: 2026-07-23

Acceptance timestamp: not recorded; none is invented.

After the Manager supplied the exact candidate and zero-finding independent
review tuple, Stephen replied:

> Accepted

In its immediate context, this accepts the exact six-path WP6.2 T2 candidate
identified below for its exact bytes only. It does not accept a mutable branch
name, later commit, regenerated artifact, or merely equivalent content.

## Accepted identity tuple

- Candidate commit: `2048f6470a9542db967186cc260d235c3373de2e`.
- Candidate tree: `1be775711befa047c7baa36fa485e5690b2277f1`.
- Direct parent: `15341a472cbe1a236d97e20110cb9ba35cc08708`.
- Candidate subject: `[PIPELINE] P00: bind reservation cost to rate mode`.
- Candidate delta: exactly six paths.

| Repository path | Git blob | Raw-byte SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml` | `ddc142344278d4628b8e70d5de1c5924896600d1` | `9220565626125fc33eb187e8e340f9a96f3c887efe080935613d51ad48257482` |
| `.research-system/contracts/wp6-2-t2-schema-identities.yaml` | `0e48e4b4e1c21f3a3da3dbfc707dc8fb811074fd` | `53e9cd265864529ee1f3e3614e820e9d3c95f06be0631a9869b81a413be7050c` |
| `.research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json` | `0f28ab00a4fa29de8f20d3760ef264fd69993f5f` | `d0c62b6db974b5d69325450d24779a16c805e11a8edd96dbb054a4850a3a8085` |
| `.research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json` | `991a2db89461242465ceeff45d3cf5ba44d3de2b` | `c9fbe9632429a986c6a9924fb6e170f9d97cc69bda97f779c2a2647c775e2305` |
| `tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py` | `bf12b00792f8388ab2661a920f6e7623fe0d841f` | `0d9fb0dd04f3cd3e79c4b58b8f03dc49d150ddad352830b1058234a4f8a5bf9c` |
| `tests/research_system/contracts/wp6_2_t2_schema_materializer.py` | `8b430299ed148ead4264d10901bc3e6da3deedfb` | `20d5981cd3793c0a4c29a564ce28b5ce382e211c7c681bb2e22f55e8779c651e` |

## Independent review basis

- Review report:
  `docs/plans/agentic-research-system/reviews/wp6-2-t2-rate-mode-boundary-review-2026-07-23.md`.
- Report Git blob: `8070235a93dc5554418a3e9408ec6acc0ca2f960`.
- Report raw-byte SHA-256:
  `7c463252c2cf6cfeac01d66da87f381665af65f1f0dfe3c71b12e3aa7abf5153`.
- Verdict: `accept`, with 0 Critical, 0 Major, and 0 Minor findings.
- Proportionate validation: six directly relevant boundary cases passed; all
  generated schemas matched the materializer; all changed catalogue and
  manifest identities matched immutable Git objects.

## Effect and boundary

This decision accepts only the six changed WP6.2 T2 contract/schema/test
elements at the exact candidate commit and tree. The external record supplies
the lifecycle decision without mutating the accepted candidate.

This acceptance grants no runtime T2 implementation, credential resolution,
provider call, T3/T4, T1b, eligibility transition, result, claim, publication,
PR merge, or Gate 6 transition authority. A runtime-T2 brief remains separately
owner-authorized work after the accepted remediation is integrated.
