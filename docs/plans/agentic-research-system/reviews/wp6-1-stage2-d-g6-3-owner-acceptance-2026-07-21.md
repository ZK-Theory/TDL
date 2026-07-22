# WP6.1 Stage-2 D-G6-3 owner acceptance

> This Markdown document is the human-readable audit rendering, not the sole
> machine authority. The machine decision layer is
> `.research-system/contracts/wp6-1-stage2-owner-acceptance-record.yaml`,
> validated by
> `.research-system/schemas/contracts/wp6-1-stage2-owner-acceptance-record.schema.json`.
> Effective `accepted_exact_bytes_only` is derived from that external strict
> record, the immutable candidate, and the immutable R10 review.

## Decision record

Statement provenance: owner-supplied task message  
Recorded date: 2026-07-21  
Acceptance timestamp: not recorded; none is invented.

> “I explicitly accept the Stage-2 WP6.1 generated-output tuple reviewed at c7e32755e9adb2f39f6a40056ef6058986c9263d: exactly 173 schemas—87 command schemas under tree 9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea and 86 event schemas under tree 154ffc4bdde82fe903718734687e7a62797b1f69, forming core tree b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46—plus the associated manifests and strict validation contracts. I accept the R10 verdict of 0 Critical, 0 Major, and 0 Minor and record D-G6-3 as accepted for these exact bytes only. This does not authorize runtime registration, dispatch, reduction, projection, migration, hooks, PR merge, or any further Gate 6 transition.”

## Accepted identity tuple

- Subject implementation: `c7e32755e9adb2f39f6a40056ef6058986c9263d`.
- Command-schema tree: `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` (87 schemas).
- Event-schema tree: `154ffc4bdde82fe903718734687e7a62797b1f69` (86 schemas).
- Core schema tree: `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` (173 schemas).
- Identity manifest: `.research-system/contracts/wp6-1-schema-identities.yaml`; ID `ars://contracts/wp6-1-schema-identities`; version `1.0.0`; Git blob `54a2938d34cea9c4a88d23585ce012a86bc3209d`; canonical UTF-8/LF SHA-256 `d6d537088f41179b993b94991d5bf5790499cce80bf419c098ca899e794b37e7`.
- Owner catalogue: `.research-system/contracts/wp6-1-owner-source-catalogue.yaml`; ID `ars://contracts/wp6-1-owner-source-catalogue`; version `1.0.0`; Git blob `1adc66921ee9c90d8786ff173748150922f1035e`; canonical UTF-8/LF SHA-256 `bddc6882b969d322cab88af99f15a214edec9ef90c5f563dc9a9fbd082a632ab`.
- Identity strict schema: `.research-system/schemas/contracts/wp6-1-schema-identities.schema.json`; ID `ars://contracts/wp6-1-schema-identities`; Git blob `5857d1dbf80ca86d711641b1206267fa2fa44202`; canonical UTF-8/LF SHA-256 `43e20dd7307381c22237daf92bc53b405aaf88fe526dec38dcaffd8be0159e91`.
- Catalogue strict schema: `.research-system/schemas/contracts/wp6-1-owner-source-catalogue.schema.json`; ID `ars://contracts/wp6-1-owner-source-catalogue`; Git blob `8e7ae9079304e20de6d70f74f581d479391f8a31`; canonical UTF-8/LF SHA-256 `537ffab03f21c3ca8c8ec040ae65babf4c371d06f582dc56d82fd14c0d0736e5`.
- Stage-1 acceptance record: `.research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml`; ID `ars://contracts/wp6-1-stage1-owner-acceptance-record`; version `1.0.0`; Git blob `42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83`; canonical UTF-8/LF SHA-256 `70a37499528b7d5fdb2fb4627723ae726156c33229aeba5400fd382c752aa648`.
- Stage-1 acceptance strict schema: `.research-system/schemas/contracts/wp6-1-stage1-owner-acceptance-record.schema.json`; ID `ars://contracts/wp6-1-stage1-owner-acceptance-record`; Git blob `63762c1555515ae9a2db071663d7fe9e2e86a96a`; canonical UTF-8/LF SHA-256 `ba0b1ebfa070c04b52923acd09810677c46936027b1197d01621fc941d2f4fe3`.
- R10 review commit: `b1863e33106e02edaf3ccf0a18aa9385005b25bd`; report `docs/plans/agentic-research-system/reviews/adversarial-wp6-1-stage2-schema-overlay-r10-review-2026-07-21.md`; report Git blob `64e5f18a1b851f991689fdcc9db11bec0143539c`; canonical UTF-8/LF SHA-256 `383b4680ad2812941cad6b1c1907277f3f00c0fa43ab4aa8775f5bc9541088d8`; verdict `accept` (0 Critical / 0 Major / 0 Minor).
- Provenance head immediately before this decision record: `1a288c3006d0b36987bec8f5209eb6071b43e346`.

The manifests retain their embedded `pending_independent_review` and
`pending_d_g6_3_owner_acceptance` values as immutable pre-decision
candidate-state fields. They are not live lifecycle authority. The external
YAML acceptance record is the machine decision layer and derives the later
owner decision against the immutable candidate and R10 review; this Markdown
is its human-readable audit rendering. Neither changes any accepted schema,
manifest, or strict validation-contract bytes.

## Decision boundary and hard stops

D-G6-3 is accepted for the exact identity tuple above only. Although 06a
normally treats D-G6-3 as releasing a later implementation phase, this owner
decision expressly does not authorize starting that phase; a separate owner
authorization is required.

The owner-supplied hard stops remain in force: no runtime registration,
dispatch, reduction, projection, migration, hooks, PR merge, or further Gate 6
transition. PR #124 remains unmerged. CodeRabbit has not been substantively
requested on this final tuple.

## Mechanical verification

| Check | Observed result |
| --- | --- |
| `git rev-parse c7e3275:.research-system/schemas/core/commands` | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` |
| `git rev-parse c7e3275:.research-system/schemas/core/events` | `154ffc4bdde82fe903718734687e7a62797b1f69` |
| `git rev-parse c7e3275:.research-system/schemas/core` | `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` |
| `git cat-file` blob IDs and SHA-256 recomputation for both manifests, three strict schemas, and the Stage-1 record | Every supplied blob and canonical UTF-8/LF SHA-256 matched exactly |
| R10 commit/report identity and SHA-256 recomputation | `b1863e33106e02edaf3ccf0a18aa9385005b25bd`; blob `64e5f18a1b851f991689fdcc9db11bec0143539c`; SHA-256 `383b4680ad2812941cad6b1c1907277f3f00c0fa43ab4aa8775f5bc9541088d8` |
| Pre-record subject head | `1a288c3006d0b36987bec8f5209eb6071b43e346` |

No tests or contract gates were rerun for this provenance-only record.

## Owner confirmation of external acceptance layer

Statement provenance: owner-supplied task message
Recorded date: 2026-07-22
No acceptance timestamp is invented.

The identities referred to as “listed above” are:

- Acceptance-layer subject: `dd1a65a65009a6d2221c10dc0285ae0ec2c7a3ae`.
- Acceptance record `.research-system/contracts/wp6-1-stage2-owner-acceptance-record.yaml`: blob `f1b73c729ed05c3bfdfcd50e0a916fa9fc70fff5`; SHA-256 `093d02bfbac5e6012c5f149abcf5b449a573863411f124fdcef928af79518ec4`.
- Strict schema `.research-system/schemas/contracts/wp6-1-stage2-owner-acceptance-record.schema.json`: blob `fac31545f7e90d7025ede973bbd39d8de4941c20`; SHA-256 `708d2ec8a1d7fab8a15650814a9bf7318328a62a1f8f70c90c2659b9f2b23c2a`.
- R11 review commit: `2f701c3b0f8b2ba3423c9ba07e0c5ce7a2813813`; report blob `496ff39639d405b50483d197858b1519e83270c8`; SHA-256 `a4bbcf3c0ce0c00d2f04d21f00bee2fb8a361e853e7f6f783447235b54e5dffa`; verdict `accept` (0 Critical / 0 Major / 0 Minor).

> confirm that the WP6.1 Stage-2 external acceptance layer at dd1a65a65009a6d2221c10dc0285ae0ec2c7a3ae faithfully records and machine-binds my existing D-G6-3 decision. I accept the exact acceptance-record and strict-schema identities listed above, together with the R11 verdict of 0 Critical, 0 Major, and 0 Minor. This confirmation does not alter or re-accept the existing 173-schema tuple and does not authorize runtime implementation, registration, dispatch, reduction, projection, migration, hooks, PR merge, or any further Gate 6 transition.

This is an audit provenance entry, not machine authority. The already accepted
YAML acceptance record and strict schema remain authoritative and unchanged.
