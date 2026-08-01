# WP6 / Gate 6 completion manager exact-state handoff 38

Date: 2026-08-01 (Europe/London)

This is the compact continuity record written after the next actual context
compaction. It supersedes handoff 37 for current routing. It is not semantic
acceptance, owner acceptance, merge authority, or Gate 6 closure.

## Management identity

- Worktree: `C:\Users\steph\.codex\worktrees\6f50\TDL`
- Branch: `codex/wp6-gate6-completion`
- HEAD at capture: `c848eedca98c5716ae3ccb914c91c60fcba4236f`
- Remote management ref: equal to that HEAD
- `origin/main`: `6c32f17a7951ee1a01ca48b9fcaf7782125ac09e`
  (PR 201 merge)
- Setup-only unstaged drift, never task output: `.claude/CLAUDE.md` and
  `.repowise-workspace.yaml`

Commit `c848eedca98c5716ae3ccb914c91c60fcba4236f` added the two current
rework-review records:

- `docs/plans/agentic-research-system/reviews/wp6-3-external-assurance-record-store-b7575d5-review-2026-08-01.md`
- `docs/plans/agentic-research-system/reviews/wp6-4-store-restore-binding-523a354-review-2026-08-01.md`

## Integrated or durably accepted state

- PR 199 / KAN-64: merged and Done.
- PR 200: merged. KAN-65 remains In Progress because only six WP6.1 rows are
  active and the remaining lifecycle catalogue is not complete.
- PR 201 / KAN-66: final head
  `75d27ef8caca506b6a98e75f4f819355eeb964a0`, merged as
  `6c32f17a7951ee1a01ca48b9fcaf7782125ac09e`, Jira Done.
- PR 202: merged. Stephen accepted the corrected exact W11 revision for
  D-G6-4 limb 1. Protected tuple: commit
  `892d1d1650cdcf71d2a886318e174a18e11d5de0`, blob
  `f90729d0c42a0de98d064fac0824d1969c871c82`, raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`,
  185214 LF-only bytes.
- PR 203: merged as `62699c2aa6565783961bf5bf720f8b9fc095cd99`.
- WP6.2 direct-provider automation remains deferred/superseded for the first
  release under P-042.

## PR 204 / KAN-58 W11 foundation correction

- PR: https://github.com/stephendor/TDL/pull/204
- Current PR branch/head: `codex/kan58-w11-exact-envelope-r3` at
  `21e91d926ca3964f46c45024796cb1c16532ee00`
- Remediation branch: `codex/kan58-w11-foundation-cr-r1`, starting at that
  exact head
- Luna Max producer task: `019fbdc7-d6c0-7fa3-acf5-86619d5f638e`
- Worktree: `C:\Users\steph\.codex\worktrees\459e\TDL`
- External review at the exact PR head completed with CodeRabbit success,
  eleven substantive comments, seven nits, and Codacy action-required
  annotations. No external review remains pending at that head.
- The active correction verifies each finding rather than applying comments
  mechanically. Its focused contract suite reached 36 passing tests before
  final lint/diff validation.
- The extra independently found nested-schema escape is included. The verifier
  must enumerate the same recursive schema set that `SchemaRegistry` loads.
- PR 204 must not move until the new candidate has a fresh exact-subject review.
  After that review, update the existing PR branch rather than opening a
  duplicate PR.

The prior expected-catalogue candidate
`f826781904f7f37857230c444928805564b5f820` is superseded because its parent is
the now-remediated foundation. Rebuild it only on the corrected, accepted PR
204 foundation. Its earlier reviewer also found that catalogue mutation tests
must recompute `content_hash` so semantic negatives are reachable.

## PR 205 / KAN-65 WP6.1 durable authority correction

- PR: https://github.com/stephendor/TDL/pull/205
- Accepted exact PR head:
  `bf2649c6a6fbc02bbd66e1b16403f564e1a22029`
- Parent/tree: `0454ce9614f8ebcfe48fc68c441833738ee0b3bd` /
  `0d51126f7e9b417ff7d4be92f25619c4989cdcda`
- Prior fresh exact-subject verdict: `accept_exact_subject`, 0 Critical,
  0 Major, 0 Minor. Durable record:
  `docs/plans/agentic-research-system/reviews/wp6-1-durable-authority-evidence-bf2649c-review-2026-08-01.md`
- Remediation branch: `codex/wp61-durable-authority-cr-r1`, starting at the
  accepted PR head
- Luna Max producer task: `019fbdda-b4fe-7210-aec9-aa823bf2d689`
- Worktree: `C:\Users\steph\.codex\worktrees\5531\TDL`
- Stephen reported the CodeRabbit review complete. One exact fetch confirmed
  six unresolved inline findings, one outside-diff functional negative, and
  nineteen nits. The producer has reproduced the valid functional findings and
  is keeping optional cleanup separate.
- Required functional seams include: independent authority-resolution key
  comparison; one immutable projection under the writer lock without a TOCTOU
  shortcut; missing release-tranche binding rejection; collision-free test
  identities; one injected test clock; line-preserving JSONL tamper; and a true
  `authority_resolver=None` no-ledger-mutation negative.
- PR 205 remains unchanged. Update it only after focused validation and a fresh
  independent review of the corrected exact subject.

This lane still closes authority evidence only for the six active Scope/Task
rows. It does not complete the remaining WP6.1 runtime catalogue.

## KAN-67 external assurance record writer atomicity correction

- Rejected subject: `b7575d518a4b93e46f61a371651f220e0602048c`
- Parent/tree: `a2aa9f16a7660fa492a80be86496b6d317ff4611` /
  `58c53261ea8becf02f28764523469d3aeadd762a`
- Exact 23-path delta
- Durable verdict: `rework_required`, 0 Critical, 1 Major, 0 Minor
- Sole reviewed blocker: grant activation persists the canonical ObjectStore
  object before ledger append. An injected append failure leaves durable state
  that replay does not recognize, and retry can later activate it.
- Branch: `codex/kan67-external-assurance-record-store-r2`, local and remote
  refs both at the rejected subject at dispatch
- Luna Max producer task: `019fbde9-b27b-7d13-96b9-a53a0b3a9449`
- Worktree: `C:\Users\steph\.codex\worktrees\d76d\TDL`
- Correction scope is only crash-safe object/ledger publication or exact safe
  recovery/rollback, with injected failure, restart, retry, pre-existing-object,
  success, and revocation controls. Live grants/records, KAN-68, wildcard
  authority, and authority-model redesign are forbidden.

KAN-67 must receive a fresh exact-subject review and integrate before KAN-68
can produce genuine multi-party acceptance.

## KAN-57 WP6.4 restored-store binding correction

- Rejected subject: `523a354ada0ccbdd6c459f4e106c30443fb89c9f`
- Parent/tree: `d46535c081eada7e6efa67ecfa6d48f027aeff00` /
  `c7366060204d31fad7501f104abf623e0ed076cf`
- Exact nine-path delta
- Durable verdict: `rework_required`, 1 Critical, 3 Major, 0 Minor
- Branch: `codex/wp64-store-restore-binding-r3`, starting at the rejected
  subject
- Luna Max producer task: `019fbdd8-5092-73a3-9239-7cf36e332d6c`
- Worktree: `C:\Users\steph\.codex\worktrees\fd36\TDL`
- Bounded correction: use independently approved expected roots and recheck
  them under final locks; reject unsupported durability and all other fallible
  preconditions before mutation; make manifest/evidence/configuration/command
  outcome atomic or durably recoverable; prove every rejection unchanged.
- Protected `VerifyRestore`, grant, administrator, and additive-action bytes
  must remain unchanged.

## Jira evidence after handoff 37

- KAN-67 durable rework record: comment `10407`.
- KAN-57 durable rework record: comment `10408`.
- KAN-65 live PR 205 remediation routing: comment `10409`.
- KAN-67 live atomicity remediation routing: comment `10410`.
- KAN-57, KAN-58, KAN-65, and KAN-67 remain In Progress.
- KAN-68, KAN-59, KAN-23 through KAN-26, KAN-60, and KAN-61 are not complete.
- KAN-22 remains In Progress.

## Downstream dependency facts

- The 81 W11 rows are a closed authority/semantic catalogue, not 81 separate
  bespoke services. Implement them by aggregate/pipeline groups after the
  corrected foundation and externally accepted exact catalogue.
- TDA-scale dossier admission can be delivered as a bounded dependency-first
  subset around OR-140, OR-110 through OR-121, and OR-028; that does not by
  itself complete all Discovery semantics.
- Genuine multi-party acceptance needs the integrated KAN-67 writer, then a
  production KAN-68 runner that constructs `ControlStoreAuthorityResolver` and
  `LedgerBackedAuthorityPolicy` and invokes requirement validation plus pack
  loading. Test fixtures or one session authoring every party do not count.
- Actual first ownership transition, legacy migration, cutover, or retirement
  remains gated by its independent prerequisites. Specification work may
  continue without executing those mutations.

## Tool-routing note

The Codex app intermittently returned `No handler registered` for list/read/send
task operations. Task creation still provisioned real worktrees and sessions;
the exact task IDs above are confirmed from their local session metadata. Do
not ask Stephen to reconnect. Monitor event-driven when the app handler returns
or use read-only branch/session evidence in the interim.

## Exact next action

Take the first correction producer that finishes. Verify its exact local and
remote candidate identity and focused evidence, archive the producer, and
dispatch a fresh independent exact-subject reviewer with no producer history.
Do not update PR 204 or PR 205, integrate KAN-67, or advance KAN-57 until that
fresh verdict accepts the exact corrected subject.
