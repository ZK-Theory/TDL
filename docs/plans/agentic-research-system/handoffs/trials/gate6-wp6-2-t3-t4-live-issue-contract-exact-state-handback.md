# TDL Handoff: WP6.2 T3/T4 live-issue binding contract

## Purpose of next session

Perform one fresh, history-free independent static review of the immutable
proposed contract candidate. Do not implement or invoke any runtime surface.

## Active project and workflow

- Project: Agentic Research System, WP6.2 T3/T4.
- Workflow system: standalone.
- Supervision phase completed: deliver.
- Lifecycle: proposed candidate; neither review nor acceptance is implied.

## Packet predecessor

- Governing brief:
  `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`.
- Read from commit `ac50847fb49f27d412adc45fc2e0a2e10b80c2d2`.
- Brief Git blob: `8e5766b86d77bcccb1c0a7c154f57e2853eadca1`.
- Brief raw-byte SHA-256:
  `49e465790f5dd7b4b09ff6039ce43030c81a70c876aaf4f4104608a880b6dd3a`.

## Exact candidate state

- Immutable dispatch base:
  `2291b5d4736ad604ce9763d9c677e707970ef14e`.
- Candidate branch: `codex/wp6-2-t3-t4-live-issue-contract`.
- Candidate commit: `cba7973f4b060a286566e30e5e89404869885324`.
- Candidate tree: `b45eb173e5615a4112d86104ba48ad3b864805a4`.
- Direct parent: `2291b5d4736ad604ce9763d9c677e707970ef14e`.
- Candidate subject:
  `[PIPELINE] P00: bind WP6.2 T3/T4 live issue evidence`.
- Candidate delta: exactly 21 paths.

| Repository path | Git blob | Raw-byte SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-2-t3-t4-live-issue-catalogue.yaml` | `95157e6022f84d2ff28ad83e6cfe259eb9935eec` | `9628cf5adea860ba86b50206e1f463d8fb383ff1eceab65607bdb60af14ce812` |
| `.research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml` | `359ae73f27a9f984aef7c41537bf44375b470a77` | `b0bc92da103f5ca192e77a887e4e2dfe79bad17b0126c1d304aae562baffc2f9` |
| `.research-system/schemas/contracts/wp6-2-t3-t4-live-issue-catalogue.schema.json` | `3ea253777f22c52786e910f8ad8dd372396e0c76` | `20a0d043b27a18a222ea47380da5c06296dadcd05c8ca596012661d6b63bd16b` |
| `.research-system/schemas/contracts/wp6-2-t3-t4-live-issue-schema-identities.schema.json` | `e7e7d07fe6095dd3348c4f18f886c520d1b24d74` | `5d7360715d1adef7df6d68de3528a852b975f96a8fef3755d936cf8f89ce7571` |
| `.research-system/schemas/wp6-2-live-issue/commands/claim-live-provider-invocation.schema.json` | `0607035fd49e515edf43c902504341d404ec2e04` | `ef2e7f0a6503ca2fb6a1f0fba233094ff5604b6fad02a38657398a43294f0c7e` |
| `.research-system/schemas/wp6-2-live-issue/commands/record-live-provider-invocation-outcome.schema.json` | `dcf15737252131a422f05604783a86515173d538` | `920e3041139ac603ae1fe10c5ef39314ef6ae57678cca570641e8dd43929315c` |
| `.research-system/schemas/wp6-2-live-issue/credential-use-receipt.schema.json` | `81bf9a6ace106fbc8109f19c663de903142d68d2` | `4721899df04f0407d7a0be733df750439e75be314445e971d00b98b049dc1801` |
| `.research-system/schemas/wp6-2-live-issue/events/live-cost-grant-reconciled.schema.json` | `e35bdad63905a9f5264f966e03d12d33273e7aef` | `14f15690cb7e20d0806f6f5a0522a76a53d92e6d24b062781634b9a20f58c920` |
| `.research-system/schemas/wp6-2-live-issue/events/live-provider-invocation-claimed.schema.json` | `3dc370d7e42fb551aeb7579f63ab06b2d9a90da2` | `e4913e0223b3083b781c44eb05c35a569496a75f6583b8245a92ac7118cbb67d` |
| `.research-system/schemas/wp6-2-live-issue/events/live-provider-receipt-recorded.schema.json` | `ed89959902e2d30b495cea188d19644952f28022` | `f180224ace13d4df6fe72ed26fdd3775495a7ab76e99a26d406381c655d18450` |
| `.research-system/schemas/wp6-2-live-issue/events/provider-invocation-outcome-recorded.schema.json` | `643b6decf5eba85551e82a59d0af87399e819959` | `e3bb45eefc2fbd9297b5caa83a096a33f908c47aaa35a9b7d4cc90ee50c4e44f` |
| `.research-system/schemas/wp6-2-live-issue/live-issue-binding.schema.json` | `09e0a166325c21fcacd8da2e5c7aba0ba7732c69` | `838917fda399fbead54b15a8e4cc02c15b15e4a397a37553864a479415c57f25` |
| `.research-system/schemas/wp6-2-live-issue/live-provider-receipt-v3.schema.json` | `856e63d1eb99aaa2579c54b2e1477f77b40f95e6` | `edd95df9d70588eec090f72e06820ea71832159ca9db77216eefec2f3db349e4` |
| `.research-system/schemas/wp6-2-live-issue/provider-invocation-evidence.schema.json` | `f55996f16f789d18abaf6aa551db3b18dddbf415` | `8b788a44ebfcdd2911db2977966875eac0151365dc224ecc160179617ccc33a0` |
| `docs/plans/agentic-research-system/README.md` | `3a206c3df23cf83a9d85e4fc0cbdc956b0b5c4aa` | `1d7a35c14115bb882ffbf6e000099311ae61602f85acf26866362b8521d35621` |
| `docs/plans/agentic-research-system/design/10-wp6-2-t3-t4-live-issue-binding-addendum-2026-07-23.md` | `127f827dfbd94d093c1f821e1b664fdc28892053` | `61aa86ceabb410952caedfd70ce0800a13c7606484714cb6b2d4d0968abddb14` |
| `docs/plans/agentic-research-system/design/README.md` | `937db811e74cf977a8719ff3d1613281e2194f93` | `7afd0007b706af63ebe45944c76cfdba1810c3344d6e3571497ebc05902e1072` |
| `tests/research_system/contracts/test_wp6_2_live_issue_contract.py` | `eae3ddd57e2f7a486061528fe3e485c5ef55f874` | `a774c7450071edc609336d1d5b1a554456022a5aeb8bee5ca87347489dc55e98` |
| `tests/research_system/contracts/wp6_2_live_issue_expectations.py` | `61b9562a33f5fb099d9cc12f831bed34583c3d57` | `bde931796fac73057b0a20329146a44eb2a4e6eb94ba9c6daa588a6b4e0c0d1a` |
| `tests/research_system/contracts/wp6_2_live_issue_fixtures.py` | `eb935ab471cfcf514ad895dc9a9bf251413101a0` | `a96bd256986d0635fea1aa725b8188218f3d8d309761d9978c2e9fbcd60ca17a` |
| `tests/research_system/contracts/wp6_2_live_issue_validation.py` | `f8adaf2e93bd547e3c8de3aea82ad1d7cc95e425` | `75ae73e7e8d9fbc21f30732766142fc3ec13c3d4d4eb63d66b13627f759d146b` |

## Contracts and validation

- RED: required-artifact test failed on all absent authorized artifacts.
- GREEN after the one author-review remediation: 68/68 focused tests passed.
- Strict Draft 2020-12 schemas were checked with format validation.
- The independent accepted-byte proof matched all 220 protected WP6.1/T1a
  predecessor members and all 27 entries in the effective accepted T2 identity
  manifest.
- `git diff --check` passed after ten extra EOF blank lines were removed.
- Commit hooks passed: skill sync, Ruff, Ruff format, and the 102-contract
  framework.
- Historical T2 and package-wide suites were intentionally not run because no
  shared or predecessor surface changed and no focused failure triggered
  expansion.

## Decisions and boundaries

- The new claim uses a separate `provider_invocation` stream.
- `CommandService` remains the sole ledger writer.
- `CanonicalObjectStore` is the named idempotent evidence-object owner.
- `LiveIssueCoordinator` is the future shared live owner; naming it grants no
  implementation authority.
- ProviderReceipt 2.0 remains immutable; live evidence uses an explicit 3.0
  successor.
- Evidence publication precedes the atomic outcome/reconciliation ledger batch;
  a publication-only crash leaves an inert orphan.
- No result files or research claims were produced.

## Open risks

- This is author-produced evidence and has not received fresh independent
  semantic review.
- The schemas name future runtime owners and seams but do not prove that those
  implementations exist or conform.
- Provider-native model/profile, credential-context, delivery, and accounting
  proof remain provider-specific runtime obligations.
- The rejected prototype bytes were not used and remain outside candidate
  ancestry.

## Next action

One fresh independent static review of candidate
`cba7973f4b060a286566e30e5e89404869885324`, using brief 13 and accepted
authorities. A still-valid finding may receive at most one separately
authorized bounded remediation; a second `rework_required` verdict stops for
Stephen. Passing review still does not accept the candidate.

## Branch and integration state

- Candidate branch role: contract-only proposed candidate plus this handback.
- Management, review, and integration roles remain separate.
- Merge strategy: preserve the exact accepted candidate as a reachable
  ancestor; do not squash or rebase it away after acceptance.
- Candidate path count: 21; wrapper adds this one handback path, for 22 total
  against the immutable base, below the 30-path task cap and the 100-path
  external-review limit.
- No PR was opened or merged. Jira was not updated.

## Do not do

- Do not invoke a provider, resolve credentials, run a live smoke, or use
  ambient CLI defaults.
- Do not implement the shared coordinator, provider adapters, or runtime
  remediation.
- Do not modify accepted T2/WP6.1/T1a, provider predecessor, Gate 5, result,
  claim, profile, T1b, or T5-T8 surfaces.
- Do not treat passing tests or review as acceptance.
- Do not trigger or poll CodeRabbit.
- Do not update Jira from the review task.
- Do not place toy or synthetic output in `results/`.

## Sensitive information

No credential material, UKDA data, secret sentinel, or provider payload is
included.
