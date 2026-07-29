# WP6.3 fresh semantic review handoff, after PR #173

**Created:** 2026-07-28
**Predecessor packets:** `22-wp6-3-post-pr171-semantic-review-handoff.md`, `23-wp6-3-post-pr171-semantic-review-result-handback.md`
**Workflow system:** `standalone`
**Repository:** `stephendor/TDL`
**Review subject:** `449b0d002edea3013dcc32a115f1870c4a082974` (PR #173 merge, verified `origin/main`)
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
   `449b0d002edea3013dcc32a115f1870c4a082974`. If it has moved, bind the review
   to that commit's artifact identities and account explicitly for later drift.
2. `gh pr view 173 --json state,mergeCommit` — expect `MERGED` at that commit.
   PRs #170, #171 and #172 merged earlier (`6bfc8dd`, `034fb494`, `7347ae95`).
3. CodeRabbit concluded on #173 before merge; its one valid nitpick was
   addressed in `d55226c` and Stephen merged without a further round. That is a
   recorded owner decision, not an omission — see "Closed items" below. Do not
   re-raise it and do not stop on it.
4. Create a fresh worktree detached at the subject commit. Do not use
   `C:\Users\steph\TDL` as a starting state; it carries unrelated local
   modifications to `.claude/CLAUDE.md`, `.repowise-workspace.yaml`, and
   untracked handoff documents.

Then compute, from the subject commit, the identities you are reviewing —
`git rev-parse HEAD:<path>` plus SHA-256 of the blob bytes:

| Artifact | Expected blob | Expected SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7298b994ca80fb43364ec53964b735f1c7e3929a` | `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `70583aaad3b60510753d0793d126de8b4c0bd030` | `39065c5bc395dbfa1fe9c9ab5443cb5fd7ae4f957dd7ceb006a538bb918ac25d` |

Treat these as a cross-check, not an assumption. Compute them yourself and
report any divergence.

**Every identity in packets 20–23 is superseded.** The subject has moved five
times. Do not carry forward `967a0d95…`, `e500b448…`, `f388dddc…`, `36164b2b…`,
`8f58b47a…`, `e19e5e20…`, `7636ee4f…`, `b9fbd4fb…`, or `c1a6e34b…`. If a
document you are reading cites any of them, it is a historical record.

### Read this before filing any "X is not enforced" finding

The dominant false-positive mode on this contract is a finding that is true
against the validator and already enforced by the schema. It has now occurred
three times across two review rounds:

- Packet 23's F-1 listed seven contract keys read by no executable code. All
  seven were genuinely unread — but five of the six areas are pinned exactly in
  the schema (`const`, `prefixItems`, closed enum plus fixed cardinality), so
  the contract-side violation the finding implied was unreachable. Only
  `required_distinct_pairs` was violable, its contents being unconstrained.
  Four successive negative controls were written and each failed schema
  validation *before* reaching the check under test.
- PR #173's review asked for per-entry `reference_kind` verification beside the
  count checks. The pack schema already pins `reference_kind`, the
  `reference_id` pattern, the `repository_path` pattern, `activation_state` and
  `maxItems` per list, and rejects a swap before the validator runs.
- The same shape appeared in the operator-model round: the schema and the
  validator disagreed, and the fix belonged in both.

**Therefore, for every candidate finding of the form "the contract declares X
but nothing enforces it":**

1. Resolve it against **both** layers — the JSON schema and the validator — and
   state which layer enforces it.
2. If the schema enforces it, that is not a gap. It may still be worth noting
   that the validator does not read the key, but say so as an observation about
   defence in depth, not as a rework finding.
3. Before proposing a new check, establish that a fixture could actually reach
   it. A check no fixture can trigger cannot be given a watched negative, and
   this contract's own fixture catalogue exists to prevent exactly that.
4. The inverse finding is more valuable and has not yet been looked for: an
   existing runtime check that is **unreachable** because a schema constraint
   fires first. That is dead enforcement wearing the appearance of coverage.
   Report any you find.

### Blocker state — re-resolve, do not trust

The KAN-56 readiness assessment
(`docs/plans/agentic-research-system/reviews/wp6-3-gate-a-readiness-assessment-2026-07-26.md`)
returned `blocked_not_ready_for_wp6_3_implementation` on four blockers:

| # | Blocker as filed | State at `449b0d00` | Check |
|---|---|---|---|
| 1 | Fresh independent review + owner acceptance | **OPEN — this task** | contract `status:` field |
| 2 | 6 skill pins stale | CLOSED | all 12 reference rows vs `git rev-parse HEAD:<path>` |
| 3 | Two contract references `pending: true` | CLOSED by `f523b1e` | both rows `activation_state: active`, `pack_acceptance_eligible: true`; `current_pending_reference_ids: []` |
| 4 | `assurance_pack` id-kind absent | Reframed as a W1 step sequenced *after* owner acceptance | `.research-system/config/id-kind-registry.yaml` still has only `assurance_requirement: asr` |

Re-resolve every row against your own subject commit. A blocker list decays from
the moment it is filed — rows 2 and 3 both changed without the record being
updated. The readiness assessment's own reference table (its lines 70–74) cites
blobs that are now many revisions stale; it is a historical record, not a
current-state source.

### What changed since the packet-23 review

PR #173 remediates packet 23's `rework_required`. Verify independently:

- **F-2** — the declared enforcement surface was `bound_names <= set(globals())`,
  a subset assertion that accepted silent shrinkage. Nine test functions were
  undeclared, including all five controls closing the previous round. Now a
  closed partition: `binding_closure` is declared in the contract, required by
  the schema, and asserted in both directions. 36 durable + 1 task-local = 37
  declared; the module defines 38 test functions including the two added this
  round, so confirm the arithmetic yourself against the current file.
- **F-1** — runtime bindings added so each declared governed set is read by the
  check it names: `review_provenance_required_record_types` /
  `review_provenance_partial_application`, `required_distinct_pairs`,
  `required_temporal_order`, both per-kind reference counts, and agreement
  across the three `required_executed_boundary_fixture_ids` copies. The existing
  hardcoded checks were retained; these are additional. Where a contract-side
  negative control is unreachable because the schema pins the key, the test
  asserts the wiring and states why in place — check that reasoning rather than
  treating the absence of a `pytest.raises` as a gap.
- **Boundary-copy comparison** changed from tuple to set equality, agreement
  being a set property.
- **`d55226c`** extracted `_assert_test_surface_closure` so the closure
  assertions are shared by the two tests that make them. Confirm no check was
  lost in the extraction: bound-name presence, task-local presence,
  durable/task-local disjointness, the `binding_closure` constant, and set
  equality with its diagnostic.

### Review scope

Verify, from the subject bytes and the repository, that:

1. **External authority resolution** — review, acceptance and requirement
   authority resolve to external records; candidate bytes cannot supply their own
   review or acceptance authority.
2. **Exact-reference currency** — all twelve `exact_reference_registry_snapshot`
   rows resolve at the subject commit, with re-resolution required at load,
   acceptance and consumption.
3. **Two-key obligation closure** — 69 rows closed by `(lane_id,
   obligation_id)` across six lanes; no duplicate, missing, extra or lane-swapped
   row; cross-lane compensation prohibited.
4. **Lifecycle ordering** — the acceptance sequence cannot be satisfied out of
   order; accepted state cannot be inferred from a candidate; supersession is
   immutable.
5. **Provenance typing** — typed operator, reviewer and stable handoff/session
   identity across all three review record types, with separate-task or
   fresh-context provenance, and the partial-application prohibition enforced
   rather than only declared.
6. **Operator model coherence** — neutral by configuration: the contract selects
   a non-empty subset of the governance enums, the validator reads the contract
   rather than literals, schema and validator agree on `human_owner`, and no
   provider-specific constraint remains without contract rationale. Consistent
   with P-042/06g.
7. **Fixture/lane agreement** — every lane's `exact_fixture_ids` agrees with each
   fixture's catalogued `lane_id` (`cross_lane` permitted).
8. **Intended negative cases** — declared fixtures fail for the stated reasons,
   including the PR #169 correction points and every control added since.
9. **Declared-set bindings (new)** — each governed set named in the contract is
   read by the check it governs, at whichever layer enforces it. Distinguish
   schema-enforced from validator-enforced and say which.
10. **Enforcement-surface closure (new)** — the declared test surface is closed
    over the module's test functions in both directions, and the controls that
    close prior findings are on the durable surface rather than merely present.

Assess whether any control is **vacuous** — a negative control that would pass
with the defect reintroduced, a positive control whose precondition the contract
no longer guarantees, or an assertion standing in for a `pytest.raises` where a
real trigger was in fact available.

Use neutral data-integrity and authority-separation language throughout. Do not
use security-testing or offensive-security vocabulary; a prior review task
(`019f9e3e-fb53-7431-9fba-6eefc3aac244`) was interrupted by an unrelated
classifier and returned no verdict. Do not infer anything from that
interruption.

### Environment

`.gitattributes` pins `.research-system/**` and `tests/research_system/contracts/**`
to `text eol=lf` as of PR #172, so a worktree created from this subject
materialises LF and needs no refresh — verified, working tree at `449b0d00`
contains zero CRLF in the three subject artifacts. If you branch from a
pre-#172 base, or reuse an older checkout, apply the refresh first or you will
see ~133 spurious contract failures:

```bash
git ls-files -z .research-system tests/research_system/contracts | xargs -0 rm -f && git checkout -- .research-system tests/research_system/contracts
```

The rule and its rationale are in repo-root `CONVENTIONS.md`.

`uv run` in a fresh worktree attempts to rebuild `petls` and fails on a missing
Boost dependency, unrelated to this work. Use
`C:\Users\steph\TDL\.venv\Scripts\python.exe`.

### Validation

```
"C:/Users/steph/TDL/.venv/Scripts/python.exe" -m pytest -q tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -o addopts='' -p no:cacheprovider -p no:cov
```

Expected at the subject commit: `38 passed`. The whole
`tests/research_system/contracts/` directory is expected to report **zero
failures**; its total has grown past the 734 recorded after PR #172 as controls
were added, so treat zero failures as the criterion rather than a fixed count.
Expand only for a named dependency or a failing check; do not rerun broad suites
to recreate evidence already in PRs #169–#173.

`test_upstream_contract_and_schema_subjects_resist_stale_foreign_and_coordinated_replacement`
compares working-tree identity against `HEAD:`, so it passes only on a clean
tree. Do not edit files in the review worktree.

### Required output

Exactly one verdict: `accept_exact_subject` or `rework_required`.

Handback must state: subject commit; the three artifact blob + SHA-256 pairs you
computed; verdict; per-scope-item findings with file and line anchors; for every
enforcement finding, which layer (schema or validator) enforces the property; the
exact validation commands and results; and an explicit statement that no file was
edited and no WP6 lifecycle gate was advanced.

If `rework_required`: stop and present findings. Do not begin a remediation
cycle. Two prior blocking findings generalised beyond their instance, so if you
find a defect, state explicitly which sibling artifacts the same governing clause
covers.

If `accept_exact_subject`: stop and ask Stephen whether he explicitly accepts
those exact contract and schema bytes. Do not manufacture that decision from PR
merges, CodeRabbit completion, passing tests, or Jira status.

### Closed items — do not re-raise

- **O-1 (packet 23): PR #171 merged at `0d4b11e` while CodeRabbit had reviewed
  `98c162a`.** Factually correct. Owner assessment 2026-07-28: no change needed,
  because `0d4b11e` implemented CodeRabbit's own comments and requiring
  reviewed-SHA to equal head-SHA at merge would force a re-review round on every
  review-fix commit. Recorded, closed.
- **PR #173's per-entry `reference_kind` suggestion.** Already enforced by the
  pack schema, more strictly than the suggestion; a runtime duplicate would be
  unreachable. Skipped with a comment in place at the count checks.

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
4. KAN-56 readiness is re-run. **Decided 2026-07-28: reopen KAN-56, no new
   ticket.** It is already `In Progress` with resolution cleared (verified live
   2026-07-28), so no transition is outstanding before the re-run.
5. A passing reassessment authorizes one bounded WP6.3 pack implementation
   brief. Pack authored, independently reviewed, owner-accepted → Gate A A7
   closes.
6. WP6.1 currency re-verified — KAN-54's `Done` covers the D-G6-3 precheck only,
   not broader runtime completion.
7. KAN-57 / WP6.4 binding and preflight → Gate 6.

## Jira state, verified live 2026-07-28

Site `nexusstephen.atlassian.net`, project `KAN` ("Topology"), cloudId
`091cb82d-1ac2-44ee-a4d4-3733dd0cd345`.

- **KAN-56: In Progress**, resolution cleared.
- Done: KAN-53, KAN-54, KAN-55, KAN-62, KAN-63 (55/62/63 as superseded).
- To Do: KAN-57, KAN-58, KAN-59, KAN-60, KAN-61.

Re-query before any write; do not rely on this snapshot.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
