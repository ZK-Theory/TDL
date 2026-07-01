# ARS P0 Plan-Suite Adversarial-Review Reconciliation

**Date:** 2026-07-01<br>
**Status:** `proposed_reconciliation_pending_approval`<br>
**Review:** `adversarial-p0-plan-suite-review-2026-07-01.md`<br>
**Subjects:** master P0 plan, implementation index, and Work Packages 1–4<br>
**Authority:** Stephen's instruction to incorporate the accepted review findings; implementation remains unauthorized

## 1. Outcome

The review's three Critical, seven Major, and five Minor/editorial findings are accepted for plan reconciliation. The plan suite now uses exact shared-interface ownership, fail-on-omission gates, unit-safe provider accounting, event-derived receipt recovery, explicit retention verification, and a forward-obligation matrix.

This record does not accept the resulting implementation scope. The plans remain `review_reconciled_pending_approval` until Stephen explicitly accepts the exact revised suite and the owner decisions in the master plan.

## 2. Finding disposition

| Finding | Disposition in reconciled plan | Status |
|---|---|---|
| P0-C1 mandatory source omission | WP2 requires `required_source_ids` closure; omissions are optional-only; missing mandatory sources fail compilation | resolved in plan |
| P0-C2 missing required graders | WP4 derives exact required result tuples and blocks empty/partial/stale/duplicate/unexpected/incompatible sets | resolved in plan |
| P0-C3 commit-before-receipt crash | WP1 rebuilds accepted-command/idempotency evidence from committed events and injects failures at every publication boundary | resolved in plan |
| P0-M1 identity contract | WP1 uses an owner-kind registry and UUIDv7; arbitrary-prefix creation is removed; field-scoped validation handles accepted shared prefix text without inventing an alias | resolved in plan; owner catalogue remains authoritative |
| P0-M2 byte/token mismatch | UTF-8 bytes are diagnostic only; provider evidence uses provider-token units scoped to provider/model/rendering/evidence revision | resolved in plan |
| P0-M3 W5 lane/authority drift | WP2 uses the exact six W5 lanes, `asr_`, independent scope review, action-semantic risk, and human gates | resolved in plan |
| P0-M4 prepared-dispatch/fixture collision | WP2 owns one `PreparedDispatch`; F-031/F-033 remain WP2 and F-032/F-034 remain WP3/WP4 | resolved in plan |
| P0-M5 parity/resource false pass | WP3 requires complete Claude/Codex rows and a symmetric resource-mode matrix | resolved in plan |
| P0-M6 sizing/calibration/variants | master forward-obligation matrix plus WP2/WP4 sizing, two-run deterministic calibration, explicit no-wildcard variants, and blocking M/H policy | resolved without live-provider default |
| P0-M7 asserted deletion | WP4 derives checks from an authorized evidence-store registry and blocks unregistered/inaccessible/contaminated locations | resolved in plan |
| Minor/editorial items | malformed snippets/commands, helper ownership, review-lead meaning, and root/reparse coverage are corrected or made explicit | resolved in plan |

## 3. Owner decisions presented for exact-scope approval

1. **Retention.** Accept the master-plan R1/R2 maxima, review-lead times, owners, extension authorities, explicit consumers, no-unregistered-replica rule, and evidence-derived deletion semantics.
2. **Identity validation.** Accept exact owner-field kind/prefix catalogues with UUIDv7 bodies and field-scoped validators. The implementation may not invent prefixes or infer kind from a prefix shared by accepted owner catalogues.
3. **P0 calibration boundary.** Accept two deterministic repetitions for every known-bad, known-good, and declared mutation under identical immutable inputs. Stochastic cases require their own accepted seed/repeat/uncertainty policy. Required M/H evidence remains blocked until a separate live-grader threshold policy and authority are accepted.
4. **Variant boundary.** Accept explicit fixture-revision/provider/adapter/rendering/transport/OS/operational-profile rows with no wildcard activation.

Approval of these decisions authorizes only the later creation of the isolated implementation worktree and task-by-task execution under the child plans. It does not authorize live providers, migration, Gate 5, a pilot, or research claims.

## 4. Preserved boundaries

- The exact P0 set remains 37 cases; F-021 remains P1 with a `p0_materialization` sizing variant.
- S-014/S-015/S-016 remain outside P0 and block the later Gate 5/pilot capabilities they govern.
- T1.28, active APM work, current papers, `.apm/`, contracts, results, checkpoints, caches, vault state, and external data remain untouched.
- P0 uses deterministic fake transports only; full stdout/stderr, provider transcripts, hidden reasoning, secrets, and raw restricted data remain prohibited.
- No fixture defect, missing grader, missing source, missing independence, missing threshold, or provider outage becomes pass.

## 5. Files changed by reconciliation

- `05-p0-materialization-and-foundation-implementation-plan.md`
- `implementation/README.md`
- `implementation/01-control-plane-and-replay-plan.md`
- `implementation/02-context-routing-and-assurance-plan.md`
- `implementation/03-adapters-and-operations-plan.md`
- `implementation/04-evaluation-and-p0-fixtures-plan.md`
- this reconciliation record

The original adversarial review remains an immutable review snapshot and is not rewritten.

## 6. Approval gate

- [x] Every review finding has an explicit plan disposition.
- [x] Every governing forward obligation is mapped to an owner, test, policy, or explicit block.
- [x] Shared helper/type ownership and fixture ownership are non-overlapping.
- [x] Missing required evidence is attacked through empty/partial/stale/duplicate/incompatible cases.
- [x] Documentation integrity and staged-scope verification pass.
- [ ] Stephen approves the exact reconciled scope and owner decisions.

**Outcome:** `PROPOSED_RECONCILIATION — required review changes are incorporated; implementation remains unauthorized pending validation and Stephen's explicit exact-scope approval`.