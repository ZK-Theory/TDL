# 06s Phase 5 runbook: the fresh store, the bounded live run and closure

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main.

**Date:** 2026-10-07. **Status:** a draft for Stephen. It is prepared from the accepted prep design
(`06s-phase5-prep-design-pass-2026-10-07.md`, P5-1 to P5-12), the C0 census
(`06s-phase5-prep-census-2026-10-07.md`) and the prep PRs (#348 to #351, plus PR-C).

**Rule for every step marked A#:** I prepare the exact command and inputs, Stephen authorizes that step
alone, I run only that step, and the durable result is verified before the next one. Nothing here authorizes
a live operation by itself (06s Phase 5).

## 0. Before any live step

1. **Prep PRs merged:** PR-A (#348), PR-B (#349), PR-C, PR-D (#350), PR-G (#351), each certified.
2. **Delta assurance passed** on the post-prep main SHA, and Stephen recorded it (P5-12):
   - the full 4c selection plus the new nodes;
   - a recorded machine check before the window;
   - a fresh-context review of the `e5179b57` to post-prep diff. It must confirm B-1, B-2, M-1, M-2, the
     SPEC-01 rule and bar, and B-3 closed.
3. **A0: Stephen's decisions for the run:**
   - the owner actor ID and the actor plan (§1);
   - the authority bootstrap (§2);
   - the paid-run subset and cost ceiling (06s Phase 5 step 3, D6).

## 1. Actor plan

Every effect needs an actor with an activated grant, and the route refuses the role collapses P-058
recorded. The identities below are the fewest the route admits. The author is fixed by PR-C's committed bar;
the others are allocated at A0 (`ars` accepts any `act_` UUIDv7). Each non-owner actor is an owner-operated
agent session, and its actor ID is recorded in that session's operator config (P-042).

| Role | Actor | Commands | Must differ from |
|---|---|---|---|
| Owner (Stephen, human) | the bootstrap owner | genesis; the bar's `ResolveDecision`; source registration; brief, return and project-use registration; `ResolveDecision` on the Assay; Task closure (SubmitForReview, AcceptTask, RequestReview, AssignReview, SatisfyReview); `SetArtefactUseAuthority`; every grant activation | every reviewer and proposer |
| Bar author | `act_01a1169f-019f-7fbb-b9f6-0246970f1d9a` (fixed by the bar) | `RegisterAssayRubricContent`, `RegisterAssayEvidenceScopeContent` | the bar requester, reviewer and observers |
| Rubric observer | allocate | `ObserveW11AuthorityFile` (rubric) | the author |
| Scope observer | allocate | `ObserveW11AuthorityFile` (scope) | the author |
| Bar review requester | allocate | `RequestW11AuthorityReview` | the author |
| Bar reviewer | allocate | `RecordW11AuthorityReview` | the author, the requester and the prospective producer |
| Bar proposer | allocate | `ProposeW11AuthorityDecision` | the bar reviewer |
| Steward | allocate | `RequestAssay`, `RequestDiscoveryOutcomeReview` | the producer and the owner |
| Producer (operator) | allocate; named in the bar acceptance | `RecordAssayScore` (re-supplies the exact return) | the reviewers and the proposer |
| Outcome reviewer | allocate | `ReviewDiscoveryOutcome` | the producer, the steward and the owner |
| Decision proposer | allocate | `ProposePromotionDecision` | the producer, the outcome reviewer and the owner |
| Task reviewer | allocate | `StartReview`, `RecordReviewVerdict` | the owner |
| Project-use reviewer | allocate | `RecordScientificReview` | the owner |

## 2. The fresh store's authority bootstrap (A0)

- **Shape:** the bootstrap input is `ars://core/authority-bootstrap-input` 1.0.0, with the same shape as the
  W11 fixture (`tests/research_system/factories.py::authority_bootstrap`).
- **Its fields:**
  - `owner_actor_id`: Stephen's owner actor;
  - `project_id`: `prj_01978abc-1000-7000-8000-000000001000` (P5-6);
  - the root grant: the owner, `RevokeAuthorityGrant`, scoped to its own grant ID;
  - the publication grant;
  - effective and expiry dates covering the whole Phase 5 window.
- **Its digest:** `approved_bootstrap_sha256` is
  `research_system.authority.authority_bootstrap_sha256(manifest)`.
- **Where it is kept:** the file is retained beside the run's evidence, and its digest is recorded in the
  Computational-Log.

## 3. The live sequence

All `ars` commands run from the durable checkout as
`C:/Users/steph/TDL-ARS-G6-Checkout/.venv/Scripts/python.exe -m research_system.cli …`, written `ars` below.

| Step | Authorize | Exact action | Verify |
|---|---|---|---|
| L1 | A1 | `git clone https://github.com/ZK-Theory/TDL.git C:/Users/steph/TDL-ARS-G6-Checkout`; set local `main` to the post-prep SHA `M1`; `uv sync --locked`. | Not linked (`.git` is a directory); clean; `git worktree list` shows one entry; `main` at `M1`. |
| L2 | A2 | Create the empty `C:/Users/steph/TDL-ARS-G6-Origin-Authority`. | `C:/Users/steph/TDL-ARS-G6-Control` does not exist. |
| L3 | A3 | `ars store reserve --code-root C:/Users/steph/TDL-ARS-G6-Checkout --control-root C:/Users/steph/TDL-ARS-G6-Control --origin-authority-root C:/Users/steph/TDL-ARS-G6-Origin-Authority --project-id prj_01978abc-1000-7000-8000-000000001000 --authority-bootstrap <bootstrap.json> --foundation-output <foundation.yaml>` | One stage, one witness and no store. The printed digest is the witness's bytes. |
| L4 | A4 | **PR-F:** commit `<foundation.yaml>` as `.research-system/config/foundation.yaml`. In the same commit, update `test_foundation_origin_witness_contract.py`'s expected values. Stephen reviews and merges, giving `M2`. | The diff is only the foundation and its contract test. |
| L5 | A5 | **Delta assurance on `M2`** (it is `M1` plus PR-F); Stephen records it. | 06s Phase 5 amendment. |
| L6 | A6 | Fast-forward the checkout's `main` to `M2` (the only update in Phase 5), then `ars store init --code-root <checkout> --control-root C:/Users/steph/TDL-ARS-G6-Control --project-id … --authority-bootstrap <bootstrap.json>`. | Identity and witness digest equal the pins; no stage is left; `ApprovedProjectBinding` loads. |
| L7 | A7: **step 1** | `ars store repair-binding --intent <first-binding.json>`, where the intent is `RepairStoreBinding` 1.1.0, `owner_action: bind-initialized-store`, `stale_evidence_refs: []`, the checkout as candidate, a 30-minute validity window, and the owner. | `status: initial-binding-published`, and `ars discovery spec status --operator-config <owner.json>` succeeds. **From here, nothing is pulled into the checkout and no worktree is added.** |

## 4. Step 3, the bounded run: order of operations

Each operation is one owner-authorized batch. Each grant is activated just before its first use.

1. **Grants:** `ars authority activate-grant --config <checkout control binding> --request <request.json>`,
   one request per actor, command set and subject (§1). Each request's `decided_at` is fixed when it is
   prepared, so a retry is exact.
2. **W11 genesis:** `ars discovery spec advance --action bootstrap_genesis` (the owner).
3. **The Assay bar:** `bootstrap_assay_authority`. Eight effects, each by its own actor in §1's order.
4. **The SPEC-01 Task, before `observe_source`** (P5-7 amended).
   - **Derive the Candidate ID.** Read-only:
     `python -c "from research_system.discovery.spec_source import source_ids; …"`, using the intent's
     `production.task_id` and `source_key`. There is no CLI for this yet, a known limit.
   - **Create and start the Task.** Run the 13 C1 commands through `ars command submit --config …
     --host-identity … --boot-identity …`, as the census did:
     - `CreateTask`, with `portfolio_refs` naming that Candidate ID;
     - readiness, dispatch, the resource grant and lease;
     - `CreateAttempt`, `ClaimAttempt`, `StartAttempt`, with `code_identity` `git:sha1:<M2>` and the checkout's
       environment fingerprint.
   - **Hold it.** Do not amend the Task, and keep the Attempt running until the operator return is
     registered.
5. **The source:** `observe_source` for `https://github.com/berenslab/eff-ph.git` at `neurips2024`. Its
   `production` repeats the running Attempt's dispatch, Attempt, context packet, code and environment
   exactly; PR-B refuses anything else.
6. **SPEC-01:**
   - `request_spec_01` (the steward);
   - `prepare_spec_01` (the owner);
   - the operator works from the issued brief;
   - `return_spec_01_complete` (the owner registers; the producer re-supplies the exact return);
   - `review_spec_01_complete` (the steward requests; the outcome reviewer records);
   - `decide_spec_01`.
7. **Closure:** end the Attempt (`CompleteAttempt` naming the evidence artefacts), register the evidence
   artefacts, run `close_task`, then `register_project_use_decision` and `accept_project_use_decision`.
8. **Result:** `ars discovery spec result --task-id … --format json` and `--format markdown`, after a fresh
   process.

What SPEC-01's own bar does (PR-C):
- topology failing gives a mechanical KILL;
- any further PROMOTE requirement failing gives PARK;
- PROMOTE needs Axis 2 + Axis 3 ≥ 4 with neither zero; otherwise PARK.

A PARK/no_spike outcome satisfies D6. A PROMOTE stops at the owner decision; SPEC-02 needs a separate
approval.

**After an admission refusal of a time-free effect** (4c review m-4): `RecordScientificReview` or
`SetArtefactUseAuthority`, on a correction or the project-use decision. Do not retry under the same actor and
grant, because the same command identity returns the stored refusal. Activate a new grant (step 1) and retry
under it.

## 5. Steps 4 to 6

- **Step 4:** render the JSON and Markdown results from a fresh process. Check Task isolation and the PARK
  limitation wording.
- **Step 5:** `ars store backup --operator-config <owner.json> …` into
  `C:/Users/steph/TDL-ARS-WP64-Backups/<run>`, then `ars store verify-restore --operator-config …` into
  `C:/Users/steph/TDL-ARS-WP64-Restore-Verification/<run>`. Compare identity, ledger, artefacts and bytes.
  This is same-disk recovery only.
- **Step 6** (P5-4): independent final evidence review; Stephen's recorded closure; the docs-only final PR,
  merged on GitHub and **not** pulled into the checkout; then replay from the frozen checkout at the bound
  SHA. The 1.0.0 initial root admits no documentation-only successor.

## 6. Known limits carried into Phase 5

- **The Candidate ID:** it is derived by a read-only Python call. There is no `ars` command for it.
- **The bar's hashes:** the W11 domain-pack reference pins the design document's bytes as of 2026-10-07.
  The brief and route-package references are protected by the binding.
- **What the evidence cannot show:** the producer profile, branch, worktree and accepted scope in a SOURCE
  manifest stay caller strings.
- **Inherited limits:** the OR-006 context fields, the fixed OR-106 review context, and the approving-only
  outcome review (P-058).
