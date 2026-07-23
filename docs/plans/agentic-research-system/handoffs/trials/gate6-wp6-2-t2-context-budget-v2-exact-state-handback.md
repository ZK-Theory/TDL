# Gate 6 / WP6.2 T2 context-budget V2 exact-state handback

## Trial termination

- Trial: `gate6-wp6-2-t2-context-budget-v2`.
- Snapshot: `2026-07-22T14:15:59.0090342+01:00`, after fetching `origin` and completing read-only T2 path-scope preflight.
- Workflow/lifecycle reached: standalone `implement_review_remediate` supervision, `deliver` phase; certified intake and implementation-seam preflight completed.
- Termination condition: first genuine blocker before implementer dispatch. The accepted plans do not assign canonical ownership or command/event identities for the atomic `CostGrant` reservation/reconciliation transition required by T2. The prompt forbids dispatch while path scope is unresolved.
- Automatic compactions: 0. Approximate live input context at stop: below the declared 80,000-token rotation threshold; exact runtime telemetry was unavailable.

## Exact repository and packet identities

- Supervisor worktree: `C:\Users\steph\.codex\worktrees\3751\TDL`.
- Supervisor state: detached clean `HEAD` at `efcecd8669fb225061c6eaf300e31bc07d352f6e` before this handback was written.
- Refreshed `origin/main`: `efcecd8669fb225061c6eaf300e31bc07d352f6e`; unchanged from the certified V1 snapshot, so no commit/path delta review was required.
- Authoritative V1 packet was resolved from the explicitly supplied plan checkout at `C:\Users\steph\.codex\worktrees\0757\TDL\docs\plans\agentic-research-system\handoffs\trials\gate6-wp6-2-context-budget-v1-exact-state-handback.md` because that file was absent from the detached supervisor checkout. Its SHA-256 matched exactly: `209f1cd1f83fd2051d9da1738c4cea58b9262ccd6e5a79a7926dddf85b2e1e4f`.
- Pre-created task branch: `pipe/ars-wp6-2-credential-cost-boundary`, exact ref `efcecd8669fb225061c6eaf300e31bc07d352f6e`; it remains unattached and has no commits or write owner.
- No separate linked worktree was created. The intended writable root was the already-authorized `3751` worktree, with the one deterministic attachment reserved for the implementer.
- No tracked source, contract, schema, test, result, claim, Gate 5, T1a, or APM file was changed. No commit, push, PR, live-provider call, or CodeRabbit action occurred.

## Gate and DAG state

- T1a exact-hash acceptance remains current from the certified packet because `origin/main` is unchanged.
- The sole accepted WP6.2 DAG remains `T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8`.
- T2 remains the sole next eligible deliverable, but is not dispatchable until the blocker below is resolved. Nothing authorizes T3, T4, a live call, T1b, T5-T8, M/H eligibility, research work, results, claims, Gate 5 mutation, S-016 changes, or third-family providers.
- WP6.1 accepted artifacts and T1a were certified and reused; none was regenerated.

## Genuine blocker and exact evidence

T2 requires one project writer to atomically reserve sufficient `CostGrant` before transport invocation and reconcile receipt actuals afterward. Current authority and implementation do not define that canonical transition:

- `research_system/operations/coordinator.py` exposes protocol/mock seams for issue and receipt recording, but no implemented canonical cost-reservation/reconciliation owner.
- `research_system/command/service.py::_build_event` supports only six implemented command types and rejects every other type as unsupported.
- `docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md` defines `RequestResourceGrant -> ResourceGrantRequested` and lease activation, but no grant issuance, `CostGrant` reservation/refund/reconciliation, `ProviderCommandIssued`, or `ProviderReceiptRecorded` identities.
- The accepted WP6.1 command/event schemas and identity manifests are exact-byte artifacts and must not be silently extended or regenerated inside T2.
- A separate direct cost writer would invent a second canonical writer unless an owner-approved authority explicitly assigns it.
- Accepted W7/W8 `1.0.0` schemas also do not state whether T2 may mutate them in place or must introduce versioned successors.

Required owner ruling before a new brief/dispatch:

1. Authorize and name the canonical writer and exact transition family for cost grant creation/reservation, provider issue, receipt reconciliation, refund, concurrency arbitration, and replay; either approve new CommandService command/event identities with an accepted schema-owner source or identify an already-authoritative existing transition.
2. State the schema-versioning rule for the T2 extensions: versioned successors versus an explicitly authorized in-place change.

After that ruling, the supervisor must re-freeze the exact allowed paths. Do not infer the answer from implementation convenience.

## Candidate path scope after owner resolution

Likely provider-neutral paths, subject to the ruling:

- `research_system/adapters/base.py`
- `research_system/adapters/provider.py`
- `research_system/operations/coordinator.py`
- `research_system/operations/models.py` or narrowly named new T2 modules in that package
- `research_system/routing/engine.py`
- `research_system/routing/orchestrator.py`
- strict new or versioned schemas under `.research-system/schemas/adapters/` and `.research-system/schemas/operations/`
- `tests/research_system/unit/test_wp6_2_preissue_boundary.py`
- `tests/research_system/integration/test_wp6_2_preissue_boundary.py`
- focused existing provider, routing, configuration, and adapter/operations tests

Only if the owner approves CommandService ownership may the scope include `research_system/command/service.py`, replay/projection code, and new core command/event schemas. Accepted WP6.1 generated schemas, owner-source contracts, and their binding tests remain forbidden from silent mutation.

Provider-specific Claude/Codex adapters, subprocess transport, adapter manifests, all eval/result/claim surfaces, T1a contracts, `research_system/store/**` redesign, plans/reviews, and `.apm/**` remain forbidden.

## Validation evidence

Preflight commands at exact base:

```powershell
python -B .claude\hooks\contract_binding_check.py --validate-only
python -B .claude\hooks\contract_binding_check.py --no-pytest
python -B -m pytest tests\research_system\unit\test_provider_receipts.py tests\research_system\integration\test_adapter_operations_fixtures.py -q -p no:cacheprovider --no-cov
```

Results:

- contract validation: all gates passed against 102 contracts;
- contract no-pytest mode: all gates passed against 102 contracts;
- focused baseline: 19/19 passed;
- candidate-head/package/full implementation validation: 0, because no implementer was dispatched and no implementation subject exists.

The eventual T2 candidate must run every WP6.2 section 4 negative row separately, assert a zero invocation count, and compare raw canonical ledger/object/receipt/store bytes before and after. Concurrency must prove exactly one reservation/invocation against one remaining allowance; replay must return only the original receipt with no second reservation or invocation.

## Trial measurements

- Supervisor: fresh standalone context; requested envelope `gpt-5.6-sol`, high effort, 80,000-token/first-compaction rotation; runtime did not expose model/effort or exact token telemetry for independent verification.
- Read-only scope explorer: fresh, `fork_turns: none`; one nested mapping probe was interrupted when the ownership blocker was established. Neither had write authority or deliverable-review status.
- Implementers: 0. Independent deliverable reviewers: 0. Remediation cycles: 0.
- Supervisor primary skills: `tda-task-brief-from-plan` only. Conditional `tda-handoff` triggered at the genuine blocker. `research-observer` ran as the required meta-skill.
- Planned implementer skills `schema-contract-design`, `contract-first-tdd`, and conditional `tda-agent-safety-guardrails` did not fire because dispatch was blocked.
- Packet verification: exact SHA-256 match. Main delta reads: 0 because refreshed main equalled the packet snapshot. Repeated campaign reads: 0. Certification regeneration: 0.
- Focused validation: 19 tests. Package/contract validation: two 102-contract passes. Full validation: 0.
- External-review waits/actions inside supervision: 0. CodeRabbit was not requested, triggered, polled, scheduled, or awaited.
- Dropped requirements: none. Assurance weakening: none. Stale-state decisions: none. False-stop risk to assess: whether the owner intended T2 itself to introduce a separately authoritative canonical cost writer despite the current single-writer and accepted-catalogue constraints.

## Next action and do-not-do list

Return this handback to the instruction-design/owner task for the two rulings above. If resolved, issue a fresh self-contained T2 brief against the same branch only after re-fetching main and re-freezing exact allowed paths; then dispatch one implementer with `fork_turns: none`, followed by one exact-subject independent reviewer with `fork_turns: none`, and permit at most one bounded remediation cycle.

- Do not attach or write on `pipe/ars-wp6-2-credential-cost-boundary` until the ownership/versioning ruling is recorded and the path scope is reissued.
- Do not invent command/event or canonical-writer authority inside implementation.
- Do not mutate accepted WP6.1 or T1a artifacts.
- Do not begin T3/T4 or perform any live provider call.
- Do not use `.apm`, APM skills/guides/checkers, or the APM Memory Bank.
- Do not operate or wait on CodeRabbit.
- Do not write toy/synthetic output to `results/`.
- Do not bypass hooks.

## Files to reload

- `docs/plans/agentic-research-system/handoffs/10-wp6-2-t2-standalone-context-budget-v2-prompt.md`
- `docs/plans/agentic-research-system/handoffs/trials/gate6-wp6-2-context-budget-v1-exact-state-handback.md`
- this V2 handback
- `docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md`
- `docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md`
- `research_system/operations/coordinator.py`
- `research_system/command/service.py`
- `research_system/adapters/base.py`
- `research_system/adapters/provider.py`

## Sensitive information

No credential bytes, `.env` contents, restricted data, provider payloads, or live-provider responses were read or recorded.
