# WP6.3 fresh semantic review handoff, after PR #170

**Created:** 2026-07-27
**Workflow system:** `standalone`
**Repository:** `stephendor/TDL`
**Predecessor packet:** `19-wp6-whole-program-post-pr169-handover.md`
**Preferred model:** GPT-5.5, per Stephen's standing direction
**Authority:** review only; no acceptance, implementation, Jira-transition, provider, migration, pilot, result, or claim authority

## Copy-paste prompt

You are performing a fresh, read-only semantic consistency review of the WP6.3
upstream contract and schema in `stephendor/TDL`.

Workflow:
- Standalone WP6, not APM. Do not initialize or use `.apm`.
- Start with `research-observer`.
- Use `tda-large-workflow-supervision` for standalone boundary discipline only.
- This is a review. Do not edit any file. Do not remediate anything you find.

### Precondition — verify before reviewing, and stop if it fails

PR #170 repins two skill references that went stale at the PR #169 merge seam.
The review subject is the commit that merges PR #170, not PR #169's merge.

1. `gh pr view 170 --json state,mergeCommit,headRefOid` — confirm `MERGED` and
   record the exact merge commit.
2. `git fetch origin && git rev-parse origin/main` — confirm it equals that
   merge commit. If `origin/main` has moved past it, bind the review to the
   merge commit's artifact identities and account explicitly for later drift.
3. Confirm CodeRabbit concluded on PR #170 before it merged. If PR #170 is not
   merged, or merged before CodeRabbit concluded, stop and report — do not
   review a subject the merge gate did not clear.
4. Create a fresh worktree detached at that exact commit. Do not use
   `C:\Users\steph\TDL` as a starting state; it carries unrelated local
   modifications to `.claude/CLAUDE.md` and `.repowise-workspace.yaml`.

Then record, from the subject commit, the exact identities you are reviewing —
`git rev-parse HEAD:<path>` plus SHA-256 of the blob bytes for:

- `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
- `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`
- `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py`

Expected contract identity if `origin/main` is exactly the PR #170 merge and
nothing else landed: blob `967a0d9532e6871d8487084855a5680972544def`, SHA-256
`e500b448feb964e4c738ef52d74a2683f99157be0b793f04911d5f6ce4675330`. Treat that
as a cross-check, not an assumption — compute it yourself and report divergence.

### What has already been established — re-resolve, do not trust

The KAN-56 readiness assessment
(`docs/plans/agentic-research-system/reviews/wp6-3-gate-a-readiness-assessment-2026-07-26.md`)
returned `blocked_not_ready_for_wp6_3_implementation` on four blockers. Their
state was re-resolved against `main` at `2111ce6` on 2026-07-27:

| # | Blocker as filed | State at re-resolution | Check |
|---|---|---|---|
| 1 | Contract needs fresh independent review + Stephen's exact-subject acceptance | OPEN — this is your task | contract `status:` field |
| 2 | All 6 skill pins stale | Closed by PR #169; 2 re-staled by the merge seam; PR #170 fixes those 2 | `git rev-parse HEAD:<skill path>` vs each pinned `git_blob` |
| 3 | `null-operation-changes-ph-input` and `markov-order-provenance` `pending: true` and pack-ineligible | CLOSED by `f523b1e` — both now `activation_state: active, pack_acceptance_eligible: true` | grep those two rows in the contract |
| 4 | `assurance_pack` id-kind missing from registry | Reframed by PR #169 as a W1 step sequenced *after* owner acceptance, not a bar to contract acceptance | `.research-system/config/id-kind-registry.yaml` still has only `assurance_requirement: asr` |

Re-resolve every row above against your subject commit before relying on it. A
blocker list decays from the moment it is filed; rows 2 and 3 both changed
without the record being updated. Note also that the readiness assessment's own
reference table (its lines 70–74) cites blobs that are now stale — it is a
historical record, not a current-state source.

### Review scope

Verify, from the subject bytes and the repository, that:

1. **External authority resolution** — review, acceptance, and requirement
   authority resolve to external records. Candidate bytes must not be able to
   supply their own review or acceptance authority.
2. **Exact-reference currency** — every row of
   `exact_reference_registry_snapshot` resolves to the blob and canonical hash
   actually present at the subject commit, for all twelve rows, and the
   re-resolution obligation is stated for load, acceptance, and consumption.
3. **Two-key obligation closure** — the complete 69-row applicability surface is
   closed by `(lane_id, obligation_id)` across the six lanes, with no duplicate,
   missing, extra, or lane-swapped row, and cross-lane compensation prohibited.
4. **Lifecycle ordering** — the acceptance sequence cannot be satisfied out of
   order, accepted state cannot be inferred from a candidate, and supersession
   is immutable.
5. **Provenance typing** — operator, reviewer, and stable handoff/session
   identity are required and typed, with separate-task or fresh-context
   provenance for owner-operated model sessions.
6. **Semantic compatibility** — formula and skill semantics are consistent with
   their referenced contracts, and with P-042/06g.
7. **Intended negative cases** — the declared fixtures fail for the reasons the
   contract says they should, including the PR #169 CodeRabbit correction
   points: negative-test messages, tuple-key lane swaps, independent Git subject
   comparison, canonical byte reuse, and prohibited semantic variants.

Use neutral data-integrity and authority-separation language throughout. Do not
use security-testing or offensive-security vocabulary; a prior review task
(`019f9e3e-fb53-7431-9fba-6eefc3aac244`) was interrupted by an unrelated
classifier and returned no verdict. Do not infer anything from that
interruption.

### Validation

Run the smallest direct set that establishes an independent verdict. Start with:

```
python -m pytest -q tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -o addopts='' -p no:cacheprovider -p no:cov
```

Expected at the PR #170 merge: `31 passed`. Expand only for a named dependency
or a failing check. Do not rerun broad suites to recreate evidence that already
exists in PR #169 and PR #170.

Environment note: `uv run` in a fresh worktree attempts to rebuild `petls` and
fails on a missing Boost dependency, unrelated to this work. Use the primary
interpreter at `C:\Users\steph\TDL\.venv\Scripts\python.exe` instead.

### Required output

Exactly one verdict: `accept_exact_subject` or `rework_required`.

Handback must state: subject commit; the three artifact blob + SHA-256 pairs you
computed; verdict; per-scope-item findings with file and line anchors; the exact
validation commands and their results; and an explicit statement that no file
was edited and no WP6 lifecycle gate was advanced.

If `rework_required`: stop and present findings. Do not begin a remediation
cycle.

If `accept_exact_subject`: stop and ask Stephen whether he explicitly accepts
those exact contract and schema bytes. Do not manufacture that decision from the
PR merge, CodeRabbit completion, passing tests, or Jira status.

### Hard stops

- Do not edit, stage, commit, push, or open a PR.
- Do not create `.research-system/packs/tdl-private-assurance.yaml` or register
  an `assurance_pack` object or id-kind.
- Do not close Gate A / A7, dispatch WP6.4, or reassess KAN-56 readiness.
- Do not transition Jira or add Jira comments.
- Do not trigger, poll, or wait for CodeRabbit; Stephen owns that.
- Do not perform provider, API, OAuth, or session-credential work. ARS must not
  invoke Claude or Codex, route model requests, or handle credentials.
- Do not treat PR merge, CodeRabbit completion, passing tests, or Jira Done as
  semantic or owner acceptance.

## What happens after this review

1. This review returns `accept_exact_subject`.
2. Stephen explicitly accepts the exact contract and schema bytes.
3. W1 authority registers the `assurance_pack` id-kind and object in
   `.research-system/config/id-kind-registry.yaml`.
4. KAN-56 readiness is re-run against the accepted identities. KAN-56 is already
   `Done` with resolution `Done`, so this needs a new Jira issue or a reopen —
   Stephen's call.
5. A passing reassessment authorizes one bounded WP6.3 pack implementation
   brief. Pack authored, independently reviewed, owner-accepted → Gate A A7
   closes.
6. WP6.1 currency is re-verified — KAN-54's `Done` covers the D-G6-3 precheck
   only, not broader runtime completion.
7. KAN-57 / WP6.4 binding and preflight → Gate 6.

## Jira state, verified live 2026-07-27

Site `nexusstephen.atlassian.net`, project `KAN` ("Topology"), cloudId
`091cb82d-1ac2-44ee-a4d4-3733dd0cd345`.

Done: KAN-53, KAN-54, KAN-55, KAN-56, KAN-62, KAN-63.
To Do: KAN-57, KAN-58, KAN-59, KAN-60, KAN-61.

KAN-55/62/63 are Done as superseded. KAN-56 Done means the blocked readiness
assessment completed, recording a fail-closed decision. Neither authorizes WP6.3
or WP6.4 execution. Re-query before any write; do not rely on this snapshot.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
