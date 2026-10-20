# 06s Phase 5 runbook: the fresh store, the bounded live run and closure

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main.

**Date:** 2026-10-07, updated 2026-10-15 for the merged prep. **Status:** a draft for Stephen. It is prepared
from:
- the accepted prep design (`06s-phase5-prep-design-pass-2026-10-07.md`, P5-1 to P5-12);
- the C0 census (`06s-phase5-prep-census-2026-10-07.md`);
- the merged prep PRs, #348 to #352 (P-058, "Prep construction complete (2026-10-15)").

**Rule for every step marked A#:** I prepare the exact command and inputs, Stephen authorizes that step
alone, I run only that step, and the durable result is verified before the next one. Nothing here authorizes
a live operation by itself (06s Phase 5).

## 0. Before any live step

1. **Prep PRs merged and certified (done, 2026-10-15).**
   - **Merged:** PR-A (#348), PR-B (#349), PR-C (#352), PR-D (#350) and PR-G (#351).
   - **Certified:** one integrated packet at `b09813e6`, whose tree equals main `bbdcb068`. 606 of 607 passed,
     plus one opt-in skip (P-058, 2026-10-15).
2. **Delta assurance passed** on the post-prep main SHA, and Stephen recorded it (P5-12). **Done
   (2026-10-15):** the selection, the network probe and the review passed. Stephen recorded the dispositions
   and KAN-110's exit (P-058, "Delta assurance complete", 2026-10-15).
   - **The selection (Stephen, option A, 2026-10-15):** the 57 nodes of the 4c selection that the integrated
     packet did not run. The packet already ran the other 253 and every prep node at the same tree, and it
     counts toward this selection. **Done:** 57 of 57 passed on M1, each reconciled once against JUnit.
   - a recorded machine check before the window. **Done.**
   - **The review:** a fresh-context review of the `e5179b57` to post-prep diff. **Done: PASS**, with two Minor
     residuals, m-1 and m-2, handled in §3 and §4 below. It had to confirm closed:
     - B-1, B-2 and B-3;
     - M-1 and M-2;
     - the SPEC-01 rule and bar.
   - **The post-prep SHA, M1:** `100730e0319ff975116fb1e18eb897f46d81a627`, main after #354, the prep close-out
     docs PR. That PR changes documentation only.
3. **A0: Stephen's decisions for the run:**
   - the owner actor ID and the actor plan (§1);
   - the authority bootstrap (§2);
   - the paid-run subset and cost ceiling (06s Phase 5 step 3, D6).

   **Done (2026-10-15):** P-058, "A0: Stephen's decisions for the run".
   - **Owner:** `act_01978abc-1002-7000-8000-000000001002`.
   - **The other actors:** in the §1 table.
   - **Bootstrap digest:** `a68cfbed4bb83d5f7bba9d674dcce19e111adb26c8023d0055d49192e487138b`.
   - **D6:** SPEC-01 only, with SPEC-02 at 0/126 + 0/42.
   - **For L5:** main has moved past M1 with non-docs PRs, so M2 is not "M1 plus PR-F". L5's scope is
     `100730e0..M2` (see L5).

## 1. Actor plan

Every effect needs an actor with an activated grant, and the route refuses the role collapses P-058
recorded. The identities below are the fewest the route admits. The author is fixed by the committed SPEC-01 bar (#352);
the others were allocated at A0 (2026-10-15; `ars` accepts any `act_` UUIDv7). Each non-owner actor is an owner-operated
agent session, and its actor ID is recorded in that session's operator config (P-042).

| Role | Actor | Commands | Must differ from |
|---|---|---|---|
| Owner (Stephen, human) | `act_01978abc-1002-7000-8000-000000001002` (the bootstrap owner) | genesis; the Task and Attempt commands of §4 step 4 (A0); the bar's `ResolveDecision`; source registration; brief, return and project-use registration; `ResolveDecision` on the Assay; Task closure (SubmitForReview, AcceptTask, RequestReview, AssignReview, SatisfyReview); `SetArtefactUseAuthority`; every grant activation | every reviewer and proposer |
| Bar author | `act_01a1169f-019f-7fbb-b9f6-0246970f1d9a` (fixed by the bar) | `RegisterAssayRubricContent`, `RegisterAssayEvidenceScopeContent` | the bar requester, reviewer and observers |
| Rubric observer | `act_01a14020-044d-7a2a-8f17-cb417f5a80a3` | `ObserveW11AuthorityFile` (rubric) | the author |
| Scope observer | `act_01a14020-044f-7877-b62d-04221f9f6949` | `ObserveW11AuthorityFile` (scope) | the author |
| Bar review requester | `act_01a14020-0451-7b04-bed0-137bbfb8871b` | `RequestW11AuthorityReview` | the author |
| Bar reviewer | `act_01a14020-0454-778d-9ee1-402fc21947b3` | `RecordW11AuthorityReview` | the author, the requester and the prospective producer |
| Bar proposer | `act_01a14020-0456-792c-8a1d-18855aae1f7b` | `ProposeW11AuthorityDecision` | the bar reviewer |
| Steward | `act_01a14020-0459-708d-ae88-bbbe336eae97` | `RequestAssay`, `RequestDiscoveryOutcomeReview` | the producer and the owner |
| Producer (operator) | `act_01a14020-045b-7374-b432-b180a4e67a27`; named in the bar acceptance | `RecordAssayScore` (re-supplies the exact return) | the reviewers and the proposer |
| Outcome reviewer | `act_01a14020-045e-71e9-9c6a-e5d8409cbc2d` | `ReviewDiscoveryOutcome` | the producer, the steward and the owner |
| Decision proposer | `act_01a14020-0460-7fd4-8c59-cc3e1a70d874` | `ProposePromotionDecision` | the producer, the outcome reviewer and the owner |
| Task reviewer | `act_01a14020-0462-70d7-9c6c-b563450976a0` | `StartReview`, `RecordReviewVerdict` | the owner |
| Project-use reviewer | `act_01a14020-0465-7cef-8e72-d4f66f4e2f7a` | `RecordScientificReview` | the owner |

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

**Where files go** (delta review m-2, Stephen, 2026-10-15). Nothing is written inside the durable checkout.
- **Operator files.** Every operator-supplied file lives in the run's evidence folder, outside the checkout.
  - **Which files:** `<bootstrap.json>`, `<foundation.yaml>` (`--foundation-output`), the binding intents, the
    operator configs, the grant requests and every SPEC input.
  - **Why:** an untracked file in the checkout makes the L7 binding, and every later binding load, refuse. A
    `--foundation-output` aimed at the checkout's own `foundation.yaml` is refused only after the reservation
    has been written.
- **PR-F (L4)** is authored in a fresh worktree of the primary repository `C:/Users/steph/TDL`, never in the
  durable checkout. A commit made in the checkout would make its `main` diverge from the merged M2, and L6's
  fast-forward would fail.
- **Check before L7:** `git -C C:/Users/steph/TDL-ARS-G6-Checkout status --porcelain=v1 --untracked-files=all`
  prints nothing.

**Status (2026-10-16):**
- **L1 to L3 are done and verified.**
  - **Store identity:** `5e3b95a9…`.
  - **Witness:** `1a7aa957…`.
- **L4** is PR #365 (`a40b3f01`), merged as M2 `4d867d85`.
- **L5 is done (2026-10-17):** the review passed, and the selection passed 327/327.
- **L6 is done (2026-10-17).** The checkout is at M2, and the store is initialized: identity `5e3b95a9…`, witness
  `1a7aa957…`.
- **L7 is done (2026-10-17): Phase 5 step 1.** The first binding `594ab323…` is published at M2.
- **Step 3 batch 1 is done (2026-10-17).** The genesis grant `agr_01a147fc…` is active, and `bootstrap_genesis` is
  completed (§4 items 1 and 2).
- **Step 3 batch 2 is done (2026-10-17).** SPEC-01's Assay bar is accepted: 8 effects by 7 actors (§4 item 3).
- **Step 3 batch 3 is done (2026-10-17).** The SPEC-01 Task `tsk_01a14850-ab08-…` names the Candidate
  `obj_a9ba6213-…`, and its Attempt is running (§4 item 4). The lease is 1 h (option A).
- **Step 3 batch 4 is done (2026-10-17).** `observe_source` registered `neurips2024` at `145efcde…` (sha256
  `3eea9174…`) and the Candidate (§4 item 5).
- **Step 3 batch 5 is done (2026-10-17).** The steward requested the Assay, and the owner issued the brief
  `art_13fdb997-…` (§4 item 6, first two steps).
- **Step 3 batch 6 is done (2026-10-20).** The owner registered the operator return `art_fc1c4531-…`, byte-equal
  to the producer's draft `568447c7…`. The producer re-supplied it at `RecordAssayScore`, and the Assay is scored
  PARK (§4 item 6, the return).
- **Step 3 batch 7 is done (2026-10-20).** The steward requested the outcome review `rev_0e21fa01-…`. It is
  pending on the registered scorecard, with a deadline of 2026-11-19 (§4 item 6, the review's first effect). The
  verdict follows the independent review session, under its own authorization.
- **The record:** P-058, "Live steps A1 to A4", "L5 review: PASS, and M2", "L5 delta assurance on M2", "A6 (L6)",
  "A7 (L7)", "Step 3 batch 1", "Step 3 batch 2", "Step 3 batch 3: decisions…", "Step 3 batch 3, live",
  "Step 3 batch 4, live", "Step 3 batch 5, live", "Step 3 batch 6, live" and "Step 3 batch 7, live".

| Step | Authorize | Exact action | Verify |
|---|---|---|---|
| L1 | A1 | `git clone https://github.com/ZK-Theory/TDL.git C:/Users/steph/TDL-ARS-G6-Checkout`; set local `main` to the post-prep SHA `M1`; `uv sync --locked`. | Not linked (`.git` is a directory); clean; `git worktree list` shows one entry; `main` at `M1`. |
| L2 | A2 | Create the empty `C:/Users/steph/TDL-ARS-G6-Origin-Authority`. | `C:/Users/steph/TDL-ARS-G6-Control` does not exist. |
| L3 | A3 | `ars store reserve --code-root C:/Users/steph/TDL-ARS-G6-Checkout --control-root C:/Users/steph/TDL-ARS-G6-Control --origin-authority-root C:/Users/steph/TDL-ARS-G6-Origin-Authority --project-id prj_01978abc-1000-7000-8000-000000001000 --authority-bootstrap <bootstrap.json> --foundation-output <foundation.yaml>` | One stage, one witness and no store. The printed digest is the witness's bytes. |
| L4 | A4 | **PR-F:** commit `<foundation.yaml>` as `.research-system/config/foundation.yaml`. In the same commit, update `test_foundation_origin_witness_contract.py`'s expected values. Stephen reviews and merges, giving `M2`. | The diff is only the foundation and its contract test. |
| L5 | A5 | **Delta assurance on `M2`**, scoped to `100730e0..M2`: M2 is `M1` plus #355 to #364 plus PR-F. Scope (Stephen, 2026-10-16): `test_fresh_store_public_procedure.py`, the STORE packet (06s §12), `unit/test_store.py`, the five `release_tranche` test files, test files of any further non-docs change, and a short fresh-context review of the non-docs diff; the `live_store` foundation contract test moves to L6. | 06s Phase 5 amendment. |
| L6 | A6 | Fast-forward the checkout's `main` to `M2` (the only update in Phase 5) with `git -C <checkout> fetch origin` then `git -C <checkout> merge --ff-only <M2>`, never `reset`/`checkout`/`switch`/`rebase` (L5 review F1: the harness primary-checkout guard denies those on a non-linked `main`); M2 is `4d867d85574dcf90300f059ab1fd52324be3c85a`. Then `ars store init --code-root <checkout> --control-root C:/Users/steph/TDL-ARS-G6-Control --project-id … --authority-bootstrap <bootstrap.json>`. | Identity and witness digest equal the pins; no stage is left; `ApprovedProjectBinding` loads. |
| L7 | A7: **step 1** | `ars store repair-binding --intent <first-binding.json>`, where the intent is `RepairStoreBinding` 1.1.0, `owner_action: bind-initialized-store`, `stale_evidence_refs: []`, the checkout as candidate, a 30-minute validity window, and the owner. | `status: initial-binding-published`, and `ars discovery spec status --operator-config <owner.json>` succeeds. **From here, nothing is pulled into the checkout and no worktree is added.** |

## 4. Step 3, the bounded run: order of operations

Each operation is one owner-authorized batch. Each grant is activated just before its first use.

1. **Grants:** `ars authority activate-grant --config <checkout control binding> --request <request.json>`,
   one request per actor, command set and subject (§1). Each request's `decided_at` is fixed when it is
   prepared, so a retry is exact.
   - **What the CLI refuses before writing anything** (`error: …`, exit 1):
     - a request whose commands do not fit its subject kind;
     - a request that is not current at run time. `effective_at` and `decided_at` must be at or before the
       moment the command runs, and `expires_at` after it. So prepare `decided_at` a little before the
       authorized run.
   - **A changed request** needs a new `authority_grant_id`. The grant ID fixes the decision and command IDs,
     and a rejected activation keeps its receipt (#351).
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
   - **Verify before `observe_source`** (delta review m-1). The Task's `portfolio_refs` include
     `source_ids(...)["candidate_id"]` for this intent. The route does not check this, so the procedure must.
   - **Hold it.** Do not amend the Task, and keep the Attempt running until the operator return is
     registered.
5. **The source:** `observe_source` for `https://github.com/berenslab/eff-ph.git` at `neurips2024`. Its
   `production` repeats the running Attempt's dispatch, Attempt, context packet, code and environment
   exactly; the route refuses anything else (#349).
   - **Corrections** (`correct_spec_01_source`) run under the same SPEC-01 Task. Every link of a SOURCE lineage
     must cite that Task, or the route refuses.
   - **The Task may name** only Candidates that SOURCE observations citing it derive.
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

What SPEC-01's own bar does (#352). Admission evaluates its rule only for the registered algorithm ID, version
and descriptor hash, and the route's PROMOTE guard checks the same, on the frozen rubric:
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
- **One Task from SOURCE to closure is held by procedure** (delta review m-1). The route does not require the
  SOURCE production Task to name the derived Candidate. Step 4's verify line holds it.
- **The initial-root store's first end-to-end exercise is the live run** (delta review i-4). No test writes a
  SPEC record, or runs backup or verify-restore, on an initial-root store. Watch steps 3 and 5.
- **An `activate-grant` admission refusal on other grounds leaves an inert owner decision** (delta review i-1,
  PR-G).
- **Inherited limits:** the OR-006 context fields, the fixed OR-106 review context, and the approving-only
  outcome review (P-058).
