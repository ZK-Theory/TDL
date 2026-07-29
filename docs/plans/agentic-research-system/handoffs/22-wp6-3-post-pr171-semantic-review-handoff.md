# WP6.3 fresh semantic review handoff, after PR #171

**Created:** 2026-07-28
**Predecessor packets:** `20-wp6-3-post-pr170-semantic-review-handoff.md`, `21-wp6-3-post-pr170-semantic-review-result-handback.md`
**Workflow system:** `standalone`
**Repository:** `stephendor/TDL`
**Review subject:** `034fb49475ae6d8c234835b02926b271f4485a7b` (PR #171 merge, verified `origin/main`)
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

### Precondition — verify, and stop if it fails

1. `git fetch origin && git rev-parse origin/main` — expect
   `034fb49475ae6d8c234835b02926b271f4485a7b`. If it has moved, bind the review
   to that commit's artifact identities and account explicitly for later drift.
2. `gh pr view 171 --json state,mergeCommit` — expect `MERGED` with that merge
   commit. `gh pr view 172` likewise (merged earlier, at `7347ae95`).
3. Confirm CodeRabbit concluded on **both** PRs before they merged. If either
   merged before CodeRabbit concluded, stop and report.
4. Create a fresh worktree detached at the subject commit. Do not use
   `C:\Users\steph\TDL` as a starting state; it carries unrelated local
   modifications to `.claude/CLAUDE.md`, `.repowise-workspace.yaml`, and two
   untracked handoff documents.
5. **Immediately after creating the worktree, apply the LF refresh** (see
   "Environment" below). Skipping it produces 133 spurious contract failures.

Then compute, from the subject commit, the identities you are reviewing —
`git rev-parse HEAD:<path>` plus SHA-256 of the blob bytes:

| Artifact | Expected blob | Expected SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `36164b2b32e211a2cbc7f980af14bcf7af59bf3f` | `8f58b47ad142dc17cdea31497af9070a8c09c0562da5afb51c832ebf150f6ba5` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `b9fbd4fbd4af06f9695c4b67fe45832291f258bc` | `c1a6e34b0a42de9ac0cb9f892a7fc199c20ec4e5b13318e63b54c66af4c0257f` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `c95ceee33ce396d5be5b036abbf6be26dac8e4cb` | `2a53469e112445ba7b8fb2a3c34c7889e8891593c51c7ce5ec1d091d84bc719c` |

Treat these as a cross-check, not an assumption. Compute them yourself and
report any divergence. Every identity from packets 20 and 21 is superseded —
do not carry forward `967a0d95…`, `e500b448…`, `f388dddc…`, `e19e5e20…`, or
`7636ee4f…`.

### Blocker state — re-resolve, do not trust

The KAN-56 readiness assessment
(`docs/plans/agentic-research-system/reviews/wp6-3-gate-a-readiness-assessment-2026-07-26.md`)
returned `blocked_not_ready_for_wp6_3_implementation` on four blockers. State
re-resolved at `034fb494`:

| # | Blocker as filed | State | Check |
|---|---|---|---|
| 1 | Fresh independent review + owner acceptance | **OPEN — this task** | contract `status:` field |
| 2 | 6 skill pins stale | CLOSED | all 12 reference rows vs `git rev-parse HEAD:<path>` |
| 3 | Two contract references `pending: true` | CLOSED by `f523b1e` | both rows `activation_state: active`, `pack_acceptance_eligible: true`; `current_pending_reference_ids: []` |
| 4 | `assurance_pack` id-kind absent | Reframed as a W1 step sequenced *after* owner acceptance | `.research-system/config/id-kind-registry.yaml` still has only `assurance_requirement: asr` |

Re-resolve every row against your own subject commit. A blocker list decays
from the moment it is filed — rows 2 and 3 both changed without the record
being updated. The readiness assessment's own reference table (its lines 70–74)
cites blobs that are now several revisions stale; it is a historical record, not
a current-state source.

### What changed since the last review

PR #171 remediates the `rework_required` verdict in packet 21, then a nitpick
round. Verify these independently rather than accepting the description:

- **F-1** — `operator_provenance` is now required on `independentContractReviewRecord`
  and `independentSchemaReviewRecord` as well as `independentPackReviewRecord`, and
  all three are checked by one `_validate_review_operator_provenance` helper. The
  contract declares `review_provenance_required_record_types` and
  `review_provenance_partial_application: prohibited`.
- **F-2** — the operator model is provider-neutral: `session_family` and
  `operator_type` are enums over a contract-declared `operator_model`, and the
  validator reads its allowed sets from the contract. `agentOperatorIdentity`
  restricts review operators to agent types at the schema layer, narrowing
  `typedOperatorIdentity` via `allOf`.
- **N-1** — `apf_representation_frozen_fallback` added with
  `lane_id: representation` and
  `invariant.representation.prohibited_refit_and_fallback`, replacing the
  foreign-catalogued `apf_degenerate_fallback` in the representation lane; plus a
  lane/catalogue agreement check.
- **N-2** — cross-reference id patterns anchored to full UUIDv7.
- **N-3** — `handoff_binding` declared; one stable `handoff_id` required across
  all three review provenance records.
- **Nitpick round** — `allowed_agent_operator_types` and
  `allowed_session_families` changed from `minItems/maxItems: 2` to `minItems: 1`
  with no maximum, enums retained as governance boundaries; the validator derives
  permitted review-operator types from
  `review_operator_must_be_agent_operator_type` and
  `human_owner_may_act_as_review_operator` rather than from the agent allowlist.

### Review scope

Verify, from the subject bytes and the repository, that:

1. **External authority resolution** — review, acceptance, and requirement
   authority resolve to external records; candidate bytes cannot supply their own
   review or acceptance authority.
2. **Exact-reference currency** — every row of
   `exact_reference_registry_snapshot` resolves to the blob and canonical hash
   present at the subject commit, for all twelve rows, with re-resolution
   required at load, acceptance, and consumption.
3. **Two-key obligation closure** — the 69-row applicability surface is closed by
   `(lane_id, obligation_id)` across six lanes, no duplicate, missing, extra, or
   lane-swapped row, cross-lane compensation prohibited.
4. **Lifecycle ordering** — the acceptance sequence cannot be satisfied out of
   order; accepted state cannot be inferred from a candidate; supersession is
   immutable.
5. **Provenance typing** — typed operator, reviewer, and stable handoff/session
   identity required across all three review record types, with separate-task or
   fresh-context provenance. Confirm the governed set and the partial-application
   prohibition are enforced, not merely declared.
6. **Operator model coherence** — the model is genuinely neutral by
   configuration: the contract selects a non-empty subset of the governance
   enums, the validator reads the contract rather than literals, schema and
   validator agree on `human_owner`, and no provider-specific constraint remains
   without contract rationale. Check consistency with P-042/06g.
7. **Fixture/lane agreement** — every lane's `exact_fixture_ids` agrees with each
   fixture's catalogued `lane_id` (`cross_lane` permitted), and the new
   representation fixture is coherent with the obligation it serves.
8. **Intended negative cases** — the declared fixtures fail for the stated
   reasons, including the PR #169 correction points (negative-test messages,
   tuple-key lane swaps, independent Git subject comparison, canonical byte
   reuse, prohibited semantic variants) and the five controls added by #171.

Assess in particular whether any of the five #171 controls is **vacuous** — a
negative control that would pass even with the defect reintroduced, or a
positive control whose precondition the contract no longer guarantees.

Use neutral data-integrity and authority-separation language throughout. Do not
use security-testing or offensive-security vocabulary; a prior review task
(`019f9e3e-fb53-7431-9fba-6eefc3aac244`) was interrupted by an unrelated
classifier and returned no verdict. Do not infer anything from that
interruption.

### Environment

**Apply the LF refresh in any fresh worktree before running tests.** The
contract system declares `canonical_byte_surface: git_blob_utf8_lf`;
`core.autocrlf=true` on this machine materialises those LF blobs as CRLF.
PR #172 pinned `.gitattributes`, but attributes apply on checkout, so a
worktree created from a pre-#172 state — or any checkout not yet refreshed —
still carries CRLF:

```bash
git ls-files -z .research-system tests/research_system/contracts | xargs -0 rm -f && git checkout -- .research-system tests/research_system/contracts
```

Without it you will see ~133 contract failures that have nothing to do with
WP6.3. This is recorded in repo-root `CONVENTIONS.md`.

`uv run` in a fresh worktree attempts to rebuild `petls` and fails on a missing
Boost dependency, unrelated to this work. Use
`C:\Users\steph\TDL\.venv\Scripts\python.exe`.

### Validation

```
"C:/Users/steph/TDL/.venv/Scripts/python.exe" -m pytest -q tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -o addopts='' -p no:cacheprovider -p no:cov
```

Expected at the subject commit: `36 passed`. The whole
`tests/research_system/contracts/` directory is expected at `734 passed` after
the LF refresh. Expand only for a named dependency or a failing check; do not
rerun broad suites to recreate evidence already in PRs #169–#172.

Note that `test_upstream_contract_and_schema_subjects_resist_stale_foreign_and_coordinated_replacement`
compares working-tree identity against `HEAD:`, so it only passes on a clean
tree. Do not edit files in the review worktree.

### Required output

Exactly one verdict: `accept_exact_subject` or `rework_required`.

Handback must state: subject commit; the three artifact blob + SHA-256 pairs you
computed; verdict; per-scope-item findings with file and line anchors; the exact
validation commands and results; and an explicit statement that no file was
edited and no WP6 lifecycle gate was advanced.

If `rework_required`: stop and present findings. Do not begin a remediation
cycle. Note that two prior findings (F-1 partial remediation, F-2 specificity
leak) both generalised beyond their instance — if you find a defect, state
explicitly which sibling artifacts the same governing clause covers.

If `accept_exact_subject`: stop and ask Stephen whether he explicitly accepts
those exact contract and schema bytes. Do not manufacture that decision from PR
merges, CodeRabbit completion, passing tests, or Jira status.

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
4. KAN-56 readiness is re-run against the accepted identities. **Decided
   2026-07-28: reopen KAN-56; do not create a new ticket.** The readiness re-run
   is tracked on the existing issue, which currently sits `Done` with resolution
   `Done`. The transition is Stephen's to make or to authorize explicitly — do
   not transition Jira from this packet.
5. A passing reassessment authorizes one bounded WP6.3 pack implementation
   brief. Pack authored, independently reviewed, owner-accepted → Gate A A7
   closes.
6. WP6.1 currency re-verified — KAN-54's `Done` covers the D-G6-3 precheck only.
7. KAN-57 / WP6.4 binding and preflight → Gate 6.

## Jira state, verified live 2026-07-27

Site `nexusstephen.atlassian.net`, project `KAN` ("Topology"), cloudId
`091cb82d-1ac2-44ee-a4d4-3733dd0cd345`.

Done: KAN-53, KAN-54, KAN-55, KAN-56, KAN-62, KAN-63.
To Do: KAN-57, KAN-58, KAN-59, KAN-60, KAN-61.

KAN-55/62/63 are Done as superseded. KAN-56 Done means the readiness assessment
completed, recording a fail-closed decision. Neither authorizes WP6.3 or WP6.4
execution. Re-query before any write; do not rely on this snapshot.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
