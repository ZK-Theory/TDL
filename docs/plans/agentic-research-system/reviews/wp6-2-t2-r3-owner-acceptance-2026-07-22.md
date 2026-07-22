# WP6.2 T2 R3 exact-byte owner acceptance

## Decision provenance

Statement provenance: owner-supplied task message
Recorded date: 2026-07-22
Acceptance timestamp: not recorded; none is invented.

After the Manager supplied the exact candidate and final R3 review identities,
Stephen replied:

> Exact has acceptance is given

In its immediate context, this accepts the exact WP6.2 T2 candidate identified
below. It does not accept a mutable branch name, later commit, regenerated
artifact, or merely equivalent content.

## Accepted identity tuple

- Candidate commit: `391a92753d7f746fa91a6b5455c9ce0fd01baa52`.
- Candidate tree: `0254c5416925126412867d61b3045ee1563abd0c`.
- Direct parent: `bba49c11ef8cd37dee7fa571f712d77a954f6b16`.
- Candidate subject: `[PIPELINE] P00: finalize research-first WP6.2 T2 contracts`.
- Candidate delta: exactly 27 paths, comprising 26 present blobs and the
  P-039-authorized deletion of
  `.research-system/schemas/wp6-2-t2/pre-issue-evidence-manifest.schema.json`.
- Authority catalogue
  `.research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml`:
  Git blob `af58e8eef39722d54d79b2b3e19d98942403e647`; raw-byte SHA-256
  `f2897076fd64372ab94747f372dae4ba5a5b19cafa28bc614931b1534727c6bf`.
- Normative crosswalk
  `.research-system/contracts/wp6-2-t2-normative-crosswalk.yaml`: Git blob
  `c47fd6bcdbcbbfe3d266646a4ad433d71041971b`; raw-byte SHA-256
  `c03350d240cdf42efd6847effe41fa453ed3943780493be367b6d401686825bb`.
- Protected-membership manifest
  `.research-system/contracts/wp6-2-t2-protected-membership.yaml`: Git blob
  `e682ef7860b6d7fab5eaeb80bdeaea7a6401aaca`; raw-byte SHA-256
  `9e71924d9cfc9610490ffa6fe9bad15f5aa3c6cf32ef2f473a5fabf5497df64e`;
  exactly 220 protected predecessor members.
- Schema-identity manifest
  `.research-system/contracts/wp6-2-t2-schema-identities.yaml`: Git blob
  `d9a4c5e39c668aef7e84660ba1e9b8ea36905c60`; raw-byte SHA-256
  `2107efff8946e714d667446f0edb922ab474559ef4714a0f28f2ef7d1b0e2c52`.
- Authority addendum
  `docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md`:
  Git blob `052eb24806f28eeab33234ce839d855b4288d0f7`; raw-byte SHA-256
  `42409dc287ce2aaba1bb18c64aa18333221bfc393da8b8066e47bef453f6d65c`.

The candidate commit and tree bind the remaining candidate paths and the
authorized absence exactly. The complete path/blob/raw-SHA-256 table is bound by
the author handback at commit
`e1fe6b95cc9024cf40f1aa410f1a8970091bf4dc`, report path
`docs/plans/agentic-research-system/handoffs/trials/gate6-wp6-2-t2-authority-addendum-exact-state-handback.md`,
Git blob `4eb59472d31f682a99f34fd234c06055e5827545`, raw-byte SHA-256
`4387b03d37632c577892489e6764d8996a4bb166ef39cb999a1f331e8d627ed0`.

## Independent review basis

- Final R3 review commit:
  `655f4173db93447a068adc6e92621455c4abc85d`.
- Review report:
  `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t2-authority-addendum-r3-review-2026-07-22.md`.
- Report Git blob: `1ad44c1f79ea9738f8ff5e2369bab3a32b4f940d`.
- Report raw-byte SHA-256:
  `17906c4ae1916840dfe94aab3f5991d17e8037940802ec1338c49b53f9506fd8`.
- Verdict: `accept`, with 0 Critical, 0 Major, and 0 Minor findings.
- Validation: 135/135 focused tests; 102/102 contracts; independent
  220-member aggregate reproduction; all 27 candidate-path identities verified.
- R3 ruled C1, C2, C4, M1, M3, and I1 closed and confirmed the P-039 C3/M2
  narrowing.

## Effect and boundary

This decision accepts the WP6.2 T2 contract/addendum candidate for these exact
bytes only and closes the exact-candidate owner-acceptance limb left by P-037.
The accepted candidate bytes are not rewritten to embed later lifecycle state;
this external decision record supplies that state.

This acceptance grants no runtime implementation, credential resolution,
provider call, T3/T4, T1b, eligibility transition, result, claim, publication,
accepted-artifact mutation, PR merge, or further Gate 6 transition. Any later
implementation brief or integration action requires separate authority and must
cite this exact accepted tuple.

## Mechanical verification

The Manager independently resolved and rehashed the candidate's five governing
addendum/manifest objects and the R3 report from Git before recording this
decision. Every blob and raw-byte SHA-256 identity above matched. The review
commit was also verified as a direct child of the candidate, containing only the
R3 report; its local branch, tracking ref, and live remote were equal. No tests
or contract gates were rerun for this provenance-only acceptance record.
