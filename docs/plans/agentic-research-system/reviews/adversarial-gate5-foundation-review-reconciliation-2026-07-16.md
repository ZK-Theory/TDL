# WP5.6 Gate 5 acceptance reconciliation — 2026-07-16

**Status:** `owner_acceptance_pending`
**Acceptance branch:** `codex/ars-gate5-acceptance-continuation`
**Execution baseline:** `9f2c4a4540e049d44bcc59cffff382496d912661`
**Independent review:**
[`adversarial-gate5-foundation-review-2026-07-16.md`](adversarial-gate5-foundation-review-2026-07-16.md)
(preserved unchanged; SHA-256
`17782861e3ff934226aa8cb64a2285e72a820c1715a995c160c8226a1d97d357`)

This record reconciles the independent review with the subsequent Owner-approved
production authority bootstrap and the corrected production initialization and
publication run. It does not alter the review's historical `rework_required`
verdict, claim that the reviewer performed the later work, accept Gate 5, or
authorize Gate 6.

## 1. Reviewed delta and authority

- PR #99's WP5.2 oracle remediation was already included in the reviewed target.
  Its missing vault record (G5R-3) is folded into the final 2026-07-16 vault
  reconciliation rather than represented as a separate decision.
- PR #103 remediated the multi-worktree schema-authority defect discovered on the
  first Phase 2 production attempt. The failed old-code attempt stopped before
  creating the control root, stage, store identity, authority genesis, or event.
  PR #103 head `4a32b69277c0a626fe6afdb7fa1e91d9507638e1` is the second parent of merge
  `9f2c4a4540e049d44bcc59cffff382496d912661`; its reviewed ten-path delta binds
  store schema authority to the explicit initializer code root while preserving
  the complete worktree set as topology.
- Stephen's Owner decision approved the exact production authority-bootstrap
  manifest SHA-256
  `90d3bacb87c6ef77385556d618fa15604af09e416700fb248a0448db8249d7e3`.
  The approval binds release decision
  `rgd_019f6ba3-57c9-7716-9b01-72cf068df03d`, source-decision SHA-256
  `e3120e1538ae605a5bf3f021faa1b2a95fa521ab33453af97f4dbb93e3899133`,
  project `prj_01978abc-1000-7000-8000-000000001000`, and Owner actor
  `act_01978abc-1002-7000-8000-000000001002`.
- Root grant: `agr_019f6ba4-8771-73b3-9d68-09d09b815f7a`, object SHA-256
  `cc07ae1ab39bd1cda3128a610b4b832c6423c5aa446d5a758bb6e9cbbdb2c34f`.
- Publication grant: `agr_019f6ba4-8771-7611-803e-c1ec0b5fdc73`, object SHA-256
  `f0a7ec35f2ca5398f5608999706146caa855da9ed92f3d6d3e82ccea19787dda`.

The four frozen Phase 1 files were re-hashed immediately before mutation and
matched their approved values:

| File | SHA-256 |
|---|---|
| `production-authority-bootstrap-manifest.json` | `90d3bacb87c6ef77385556d618fa15604af09e416700fb248a0448db8249d7e3` |
| `production-unpublished-release-gate-decision.json` | `e3120e1538ae605a5bf3f021faa1b2a95fa521ab33453af97f4dbb93e3899133` |
| `production-bootstrap-approval-packet.json` | `40283ad46182c16e23bdd813b09ca9648b50349a1ac5a00bc521292d9ece3c7a` |
| `production-authority-bootstrap-input.json` | `f1df97d661e86ad96988af40824fcfb917da123231a662e0afe75129555e28a8` |

All three Owner records still contained the exact approved hash and bindings.

## 2. Runtime topology and schema authority

The production control root is
`C:\Users\steph\TDL-ARS-Gate5-Control`. It was absent before initialization
and was disjoint from every code root. The explicit schema authority is
`C:\Users\steph\.codex\worktrees\4b98\TDL\.research-system\schemas`,
persisted with `schema_binding_version=1.0.0`.

The frozen approval packet recorded 29 worktrees. Independent enumeration at
runtime found exactly the following 30 roots; the sole addition was PR #103's
dedicated remediation worktree `C:\Users\steph\.codex\worktrees\4a35\TDL`.
All 30 remained disjoint from the control root:

1. `C:\Users\steph\.codex\worktrees\1702\TDL`
2. `C:\Users\steph\.codex\worktrees\1877\TDL`
3. `C:\Users\steph\.codex\worktrees\4a35\TDL`
4. `C:\Users\steph\.codex\worktrees\4b98\TDL`
5. `C:\Users\steph\.codex\worktrees\a2e5\TDL`
6. `C:\Users\steph\.codex\worktrees\b068\TDL`
7. `C:\Users\steph\.codex\worktrees\d3d3\TDL`
8. `C:\Users\steph\.codex\worktrees\d614\TDL`
9. `C:\Users\steph\.codex\worktrees\wp56-gate5-review`
10. `C:\Users\steph\TDL`
11. `C:\Users\steph\TDL\.apm\worktrees\ars-gate5-release-tranche-plan`
12. `C:\Users\steph\TDL\.apm\worktrees\compute-profile-adoption`
13. `C:\Users\steph\TDL\.apm\worktrees\discovery-spikes-mcbif`
14. `C:\Users\steph\TDL\.apm\worktrees\gate-coderabbit-fixes`
15. `C:\Users\steph\TDL\.apm\worktrees\gate-liveness-audit`
16. `C:\Users\steph\TDL\.apm\worktrees\headline-vintage-materiality`
17. `C:\Users\steph\TDL\.apm\worktrees\mcbif-deprivation-scale-coherence`
18. `C:\Users\steph\TDL\.apm\worktrees\mcbif-weighted-nerve`
19. `C:\Users\steph\TDL\.apm\worktrees\paper-p01a-dedup-rewrite`
20. `C:\Users\steph\TDL\.apm\worktrees\paper-p01a-sec6`
21. `C:\Users\steph\TDL\.apm\worktrees\paper-p01b-methods-results`
22. `C:\Users\steph\TDL\.apm\worktrees\pipe-two-machine-check`
23. `C:\Users\steph\TDL\.apm\worktrees\sheaf-pl-confirmatory`
24. `C:\Users\steph\TDL\.apm\worktrees\sparse-witness-assay`
25. `C:\Users\steph\TDL\.apm\worktrees\w2-fallback-audit`
26. `C:\Users\steph\TDL\.apm\worktrees\w2-gap-closure`
27. `C:\Users\steph\TDL\.apm\worktrees\wp52-dg55-amendment`
28. `C:\Users\steph\TDL\.apm\worktrees\wp52-plan-fix`
29. `C:\Users\steph\TDL\.apm\worktrees\wp54-review-fix`
30. `C:\tmp\tdl-gate5-merged-review`

The persisted store-identity manifest has SHA-256
`25852dc9ca087a31eb84669920d2d8c0a17ea3dee5f9ae6224cf3ed17319b942`,
manifest hash
`5250750f564c06e9ab7a237e7e980e90e6b567460a9db83c85a4818cab67e00c`,
store nonce `96bf9c31b2febcd0b8e71a3c36207ce9`, and stable store identity
`14fa1ffd0969b66b4e2e0f176c213b084a8607a807f0c39e4273ebddb1515e02`.

## 3. Atomic authority initialization

The production CLI initialized the store once from the unchanged approved input.
The atomic genesis batch is
`txb_019f6d1a-32c6-7bb9-960b-ee0730c0227b`, stored at positions 1–2 with
batch-file SHA-256
`588a385dcd41c2635c84061a56fb9b5025fae3fa3353a62bc53e6b3c052c011d`:

| Position | Event | ID | Event hash |
|---:|---|---|---|
| 1 | `AuthorityRootInitialized` | `evt_019f6d1a-32c6-735d-9eff-39f1ca178ace` | `1ddebf26834bfb836afc659b4854260c842539cbd4b545c037428523c728a6c6` |
| 2 | `AuthorityGrantActivated` | `evt_019f6d1a-32c7-7383-a4f1-707975c55ecb` | `ee1a138c491f96567deb4fab666e2b8bf85f20738971ac9cc121c97fb4881094` |

Both events bind command `cmd_019f6d1a-32c6-7c6e-9f35-8df23159fad7`.
There was no staging residue after initialization.

Accepted initializer behavior was proved after publication:

- An identical lost-response retry returned the original verified store identity
  and left the complete five-file initialized store byte-identical.
- A separately derived internally consistent bootstrap changed only the
  publication-grant expiry, yielding publication object SHA-256
  `60dd4e7f33f9983f2767f89cdc300d3c4723854469c8e5ea23aa4c4b8abe02c1`
  and bootstrap hash
  `69ba51cca2357d99bd0268cbecc74851b31f57e1e7a9cf90e2c716bccd724111`.
  It exited 1 with `ConflictError: authority bootstrap conflicts with existing
  store`; the store bytes were unchanged. The approved input file retained SHA-256
  `f1df97d661e86ad96988af40824fcfb917da123231a662e0afe75129555e28a8`.

## 4. Canonical release publication

The frozen unpublished decision was published only through
`ars eval publish-release`. The accepted receipt is:

- command ID `cmd_019f6d1e-e4c0-7a06-8514-828148b1f617`;
- event batch ID `txb_019f6d1e-e7bd-78c6-8b18-7a779c9428f8`;
- status `accepted`, observed stream version `1`;
- payload hash
  `a1c2b63801110d4fafe0073f63e24099bb81d14524868d7e23ad36eb59dfe79d`;
- canonical scratch receipt SHA-256
  `f51d9238ff5c233d7d2c765ec65aa2b923ab1a3a9430fe322be97498cebfc934`;
- persisted receipt-object SHA-256
  `2e22d0da9ec4414f639ab64d8687aadf0980d2384edea18bcc538cf9dd38a9ff`.

Exactly one `ReleaseGateDecisionPublished` event exists:

- event ID / `canonical_event_ref`:
  `evt_019f6d1e-e7bd-7d7a-ac9d-9f7290f9cb8e`;
- stream `rgd_019f6ba3-57c9-7716-9b01-72cf068df03d`, version 1;
- global position 3;
- event hash
  `c3d3391bc34f6a8fcc87e6d8c931ac95dbcd14838019e438a99dc1e75cf9539c`;
- event-batch file SHA-256
  `1c063a258c0b5c7cf3b44665a84cad5fe54def490914494473df81c0b107409f`;
- evaluation-runs manifest
  `art_537a1cbb-5dc9-76de-b83c-9a2a05fedd99`, SHA-256
  `537a1cbb5dc9d6def83c9a2a05fedd99ca3e73cf661e6b04ff465a17a7574175`;
- control-binding artefact
  `art_53699378-135d-7f20-857b-dc77aa3bd5ab`, SHA-256
  `53699378135d8f20c57bdc77aa3bd5ab86c4e0a866fbf9af16e7216d664d82d2`;
- source-decision SHA-256
  `e3120e1538ae605a5bf3f021faa1b2a95fa521ab33453af97f4dbb93e3899133`;
- publication authority SHA-256
  `f0a7ec35f2ca5398f5608999706146caa855da9ed92f3d6d3e82ccea19787dda`.

The exact publication retry returned the original receipt byte-for-byte and did
not append an event. A source with only `decided_at` advanced by one second used
the same release-decision idempotency key and returned status `conflict`, reason
`idempotency_conflict`, no event batch, and observed stream version 1. Its command
was `cmd_019f6d20-fe14-73e4-984e-05820429d786`; the canonical conflict-receipt
SHA-256 is
`b76c9b3e1a74594197c169ef50929f0f4a8ddd45eb7859203bafeb22a75a1e3a`.
The conflict created no second canonical publication. The complete control root
contained two event-batch files (genesis and publication) and no staging residue.

## 5. Replay, release, and frozen invariants

`ars replay verify --control-root C:\Users\steph\TDL-ARS-Gate5-Control`
exited 0. The manifest-only projection ended at position 3 and last hash
`c3d3391bc34f6a8fcc87e6d8c931ac95dbcd14838019e438a99dc1e75cf9539c`,
with both authority grants active and the one release decision bound to the
event and content-addressed evidence above.

`ars eval release` against the published decision exited 0 and returned:

```json
{"candidate_status":"blocked","canonical_event_ref":"evt_019f6d1e-e7bd-7d7a-ac9d-9f7290f9cb8e","decision":"blocked","gate5_authorized":false}
```

The acceptance evidence remains exactly:

- 40 fixtures;
- 15 blocked fixtures;
- 0 uncalibrated fixtures;
- 302 unique results;
- mutation calibration `calibrated`;
- parity `pass`;
- operations `pass`;
- candidate `blocked`;
- `gate5_authorized=false`.

There are 51 `unable_to_grade` results and zero `fixture_error` results. The
blocking fixtures remain exactly F-005, F-009, F-012, F-014, F-020, F-021,
F-022, F-025, F-026, F-031, F-032, F-033, F-035, F-036, and S-016.

D-G5-1(a), D-G5-2 deferral/O15, D-G5-3, D-G5-4, D-G5-5, G5.3-A, and
G5.3-B(a) remain unchanged. M/H capability remains restricted; no live M/H
grading, deletion initiation, credential, live provider/model, raw transcript,
restricted data, network publication, research-result mutation, or Gate 6 work
occurred.

## 6. Independent-review finding disposition

| Finding | Acceptance reconciliation |
|---|---|
| G5R-1 | **Resolved.** Canonical and acceptance worktrees have LF bytes with SHA-256 `e7d61c32c817ca95d21f17d6d8557656b0c99bb3a823a85ee7704d245b0de94f`; the strict matrix materializer exits 0. |
| G5R-2 | **Satisfied.** Stephen's exact Owner decision approved manifest SHA-256 `90d3bacb87c6ef77385556d618fa15604af09e416700fb248a0448db8249d7e3` before initialization. Exact equality was enforced. |
| G5R-3 | **Closed by final reconciliation.** PR #99 is included in the appended 2026-07-16 vault publication evidence. |
| G5R-4 | **Accepted as non-blocking.** Optional nested schema defense-in-depth was not implemented. The reviewed code-side enforcement remains load-bearing. |

## 7. Commands and environment

Every Python command used:

```text
UV_PROJECT_ENVIRONMENT=C:\Users\steph\TDL\.venv
PYTHONPATH=C:\Users\steph\.codex\worktrees\4b98\TDL
uv run --no-sync
```

Production operations were the accepted CLI paths:

```text
python -m research_system.cli store init --code-root <acceptance-worktree> --control-root <external-control-root> --project-id <project> --authority-bootstrap <approved-input>
python -m research_system.cli eval publish-release --config <persisted-store-identity> --actor-id <owner> --authority-grant-id <publication-grant> --evaluation-runs <frozen-decision> --output <receipt>
python -m research_system.cli replay verify --control-root <external-control-root>
python -m research_system.cli eval release --config <persisted-store-identity> --evaluation-runs <published-decision>
```

The final repository status is `owner_acceptance_pending`. Stephen's separate
recorded acceptance remains the last Gate 5 exit-checklist item. Gate 5 is not
marked accepted and Gate 6 remains ineligible.
