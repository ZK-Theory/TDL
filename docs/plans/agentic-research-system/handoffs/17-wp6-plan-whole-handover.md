# WP6 plan whole-program handover (post 6.2 T3/T4 contract brief merge)

**Created:** 2026-07-24  
**Branch when captured:** `codex/wp6-2-t3-t4-parallel` (working tree had one extra non-authoritative docs commit above `origin/main`)  
**Workflow system:** standalone; read-only planning handoff

This handoff summarizes WP6 as a whole for a fresh manager/session. It treats current
planning and decision artifacts as the active authority and does not authorize runtime
code or dispatch.

## Governing references read

- `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md` (suite authority, graph, and gates)  
- `docs/plans/agentic-research-system/implementation/06a-wp6-1-runtime-task-lifecycle-plan.md`  
- `docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md`  
- `docs/plans/agentic-research-system/handoffs/14-wp6-gate6-7-handover.md` (WP6.6/7 conflict map)  
- `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`  
- `docs/plans/agentic-research-system/design/README.md`  
- `docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md`

## Current master-plan state (as a whole)

- **Global position:** The WP6 launch-basis plan is at the reviewed/signed revision
  `fe5f1d40bc8f05f061317c677b5891cea0711249`; this is review-approved but not a
  full runtime execution authorization.  
  (See `06-wp6-gate6-readiness-and-integration-plan.md:4`)

- **Plan authority shape:** `P-031` to `P-036` control most structural boundaries.
  The open owner-gate surface is still the same as the reviewed suite:
  - `D-G6-2` (T1a/T1b exact-hash acceptance)  
  - `D-G6-3` (WP6.1/WP6.2 catalogue+identity manifest acceptances)  
  - `D-G6-4` (W11 authority-transition batch approval)  
  - `D-G6-5` (Gate 6 preflight for SCALE-01)
  (`06-wp6-gate6-readiness-and-integration-plan.md:218-223`)

## Package-level status table

| Package | What is currently true | What is blocking progress |
|---|---|---|
| **WP6.1** | Plan and interface are accepted as reviewed plan content under P-036 (`06a` status + `06` suite). Runtime not yet authorized by this authority boundary. | Remaining `D-G6-3` approvals for schema/identity manifests and manifest-bound implementation authorization; implementation remains separate and review-gated. (`06a:4-7`, `06:219-221`, `06:296-303`) |
| **WP6.2** | WP6.2 child plan approved as planning authority under P-036 and is explicit about closed DAG and hard stops (`06b:4-8`, `06b:202-203`, `06:203-204`). `09` T2 addendum is `accepted_exact_bytes_only`. The T3/T4 contract brief is merged through PR #161 and immutable base is `2291b5d4736ad604ce9763d9c677e707970ef14e`; commit-level handoff in `13:12-13` records this as the immutable dispatch base for that brief. | `D-G6-2` remains open for exact-hash T1a and T1b-M/T1b-H owner acceptances. `06b` and `06` both require those before live-capability work, model/human gating, or M/H eligibility transitions can begin. (`06b:6-8`, `06:218-221`, `06:296-304`) |
| **WP6.3** | WP6.3 is the plan for assurance-pack content and is available as a package with merge provenance in campaign history snapshots (`08-handoff` context; no implementation authorization from the plan files alone). | No evidence in the current read-set that top-level WP6.3 Gate A closure is complete; it remains to be separately accepted by its package owner. |
| **WP6.4** | Binding and preflight plan exists as the A8/W6.2 closure lane (`06:125-132`, `06:191-192`, `06:209-211`). | Requires completed WP6.1–WP6.3 outputs and proof of A8; not dispatchable before preflight conditions are satisfied. (`06:329-330`) |
| **WP6.5** | W11 design spec is written and exists as the migration-spec lane, with `review_pending` status in design register. (`design/README:49`) | Needs fresh independent R3 review + D-G6-4 approval before any migration transition or cutover can begin. (`design/README:48-49`, `06:221`, `06:331`) |
| **WP6.6** | Defined as post-W11 dossier intake and admission lane (`06:172-178`). | Blocked pending WP6.5 acceptance + WP6.1 merge-readiness + separate implementation plan/dispatch authorizing dossier admission. (`06:172-178`) |
| **WP6.7** | Sequencing only under W9/T1.28 regime (`06:180-184`, `06:197`). | Remains gated by unresolved transition/closeout conditions and inconsistent doc phrasings around T1.28 status; see conflict map and rule below. (`14:19-37`, `14:62-63`) |

## WP6.6/7 conflict-risk that still tends to confuse fresh agents

Keep one consolidation rule for continuity:

- Treat `T1.28` and related current-paper legacy constraints as **live and active until
  explicit terminal disposition + W0 addendum** is confirmed, and never use any one stale sentence from one document as sole authority. (`14:62-63`)
- Use the sequencing state in `06` (`WP6.7` sequencing-only, no dispatch at this stage) and treat any stricter/older/contradictory wording as outdated until reconciled. (`06:180-184`)

## Current-accepted-next action (single vertical action)

For the next fresh manager action, the safest single vertical path is:

1. **WP6.2 pre-runtime sequencing closure:** complete and record the exact-hash
   D-G6-2 evidence/acceptance chain for T1a and then composite T1b-M/T1b-H under
   independent review, before permitting any T2/T3/T4 implementations to move past the
   current hard stops. (`06:297-304`, `06b:4-8`, `06b:63-64`)

No provider calls, migrations, eligibility transitions, or claims are authorized until
that chain is in place and separately recorded.

## Do not do next (hard-stop list)

- Do not authorize provider invocation, live-grade dispatch, or Gate 6 transition from this handoff alone. (`06:5`, `06b:5-8`)  
- Do not treat merge status in this handoff as runtime execution permission for T2/T3/T4. (`06:5`, `06:297-304`)  
- Do not override WP6.7 sequencing behavior from individual draft lines. (`14:19-37`, `06:180-184`)  

## Required reads for the next Manager (before any write)

- Re-verify this handoff file as the exact starting checkpoint.
- Re-read `06-wp6-gate6-readiness-and-integration-plan.md`, `06a`, `06b`, and
  `design/README.md` after any PR/main drift.
- Reconfirm whether D-G6-2 owner acceptances are now recorded after this checkpoint.
