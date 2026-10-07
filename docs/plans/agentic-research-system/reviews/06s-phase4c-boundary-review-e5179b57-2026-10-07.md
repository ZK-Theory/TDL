# 06s Phase 4c: independent exact-main boundary review

**Reviewed SHA:** `e5179b57811f74346707a4fe5fe7c407772cb3dc` (main after #338), in my own detached worktree
`C:/Users/steph/TDL-4c-review`, with `.env` copied and `uv sync --locked --extra dev` done. I did not use
`TDL-06s-phase4c` or the primary checkout. I did not touch the live control store, any provider or paid call,
or any credential. I made no binding, no commit and no push.
**Reviewer:** Claude (Opus 5.5), fresh context. I did not read the campaign's handoffs, checkpoint or session
history.
**Date:** 2026-10-07.

## 1. Verdict

**FAIL at `e5179b57`: one Blocking finding (B-1).** The integrated route cannot create a fresh control store, or
point at one, through the public CLI at this SHA. The committed `.research-system/config/foundation.yaml` pins
exactly one store, the live store, and both `ars store init` and `ars discovery spec status|advance|result`
derive their store from that file. To re-pin it you must change governed configuration. That change is not a
documentation-only successor, so the SHA that Phase 5 step 1 actually binds cannot be `e5179b57`. That SHA would
also not have had this review.

Apart from B-1, I found no authority bypass, owner bypass or paid-gate bypass, no durable corruption, no
mispublication and no replay divergence. The route logic itself (composition, role bindings, close_task,
project-use, replay) holds against the contracts, subject to its recorded known limits.

## 2. Findings (most severe first)

| ID | Severity | Contract clause | Location at `e5179b57` | Reachable path | Evidence | Proposed disposition | Confidence |
|---|---|---|---|---|---|---|---|
| B-1 | **Blocking** | 06s §4 item 1 (and items 2–6, which all run on the fresh store). P-058 2026-09-14 "Fresh store". Phase 5 amendment: "Step 1 binds the reviewed main SHA to that fresh store" | `research_system/cli.py:120-135`; `research_system/config.py:534-536`, `539-569` (raise at `565`); `research_system/store/current_binding.py:794-803`; `research_system/store/identity.py:374-375`; `.research-system/config/foundation.yaml:4-9`; `research_system/store/governed_code.py:792` | (a) `ars store init --control-root <fresh root> …` is refused before any write. (b) With any fresh store, `ars discovery spec status --operator-config <config naming it>` is refused. The same applies to `advance`, `result` and `store backup --operator-config`. (c) Re-pinning the foundation is a configuration change, which the binding refuses as a documentation-only successor. | Two reproductions; see §2.1 | **Fix before the successor binding.** Stephen decides how a fresh store enters the committed foundation, and in what order relative to `store init` (see the open question in §2.1). The foundation delta, together with the Phase 5 prep commits already recorded (replacement Assay authority content, the SPEC-01 rule's location, the signing identity), lands on main first. The SHA actually bound then gets an exact-main delta review. | High |
| M-1 | Material | Phase 5 step 1 (P-058 2026-09-14 amendment); §4 item 1 | `research_system/config.py:94-113`, `295`; `research_system/store/binding_service.py:457-460`; `research_system/store/governed_code.py:510`; `research_system/store/current_binding.py:812-831`, `952-957`; `research_system/cli.py:124-126` | #341 refuses a candidate root that is a linked Git worktree or sits under `.codex/`, `.claude/` or `.apm/worktrees`. After binding, every route operation runs `load_current_binding` about five times. That call requires the same checkout to be clean (`git status --porcelain=v1 --untracked-files=all` empty) and at the bound head or a documentation-only successor. The CLI also takes the repository root from the running package (`foundation_path.parents[2]`). So every Phase 5 invocation must run from that one checkout, kept clean and frozen for the whole run. The primary checkout `C:/Users/steph/TDL` is at `e5179b57` today but has one staged file, so a binding from it would be refused now (`governed_code.py:510`, clean subject). | Static reading. `git status` on the primary checkout shows `M  docs/plans/agentic-research-system/implementation/06t-artefact-authority-pin-binding-proposal.md`. | **Phase 5 prep.** Choose the durable checkout. This can be the primary checkout, frozen for the run, or a dedicated non-linked clone outside the agent worktree directories. The code accepts either: the brief's "must run from the main checkout" is stronger than the code requires. Keep that checkout clean. Pull no non-documentation merge into it until Phase 5 step 6. Make it the foundation's `schema_root` and code root. | High |
| M-2 | Material | §4 item 3 ("effects retain actor/authority provenance"); Q3 "a durable record that misstates what happened"; contrast P-058 4a-2 decisions (2026-09-15), which derive operational provenance from the ledger | `research_system/discovery/spec_source.py:234-245`; `.research-system/schemas/contracts/wp6-6/spec-source-intent.schema.json:12-22`; `research_system/discovery/spec.py:583-593` | The SOURCE registration's manifest copies `production` (task, dispatch, attempt, context packet, code commit, environment fingerprint) verbatim from the caller's intent. Only the schema checks it, and admission checks none of it (the measurement P-058 records). On the Phase 5 order, `observe_source` creates the Candidate. The operational Task that must name that Candidate is created only after it. So the SOURCE manifest cannot name that Task, and whatever it does name, the system never verifies. The ProjectUseDecision later cites this registration as its source. | Code and schema. The tests copy a fixture manifest's fields (`test_spec_source.py:289-305`). No PR known limit or P-058 block records this for SOURCE: #291 and P-058 apply ledger derivation to the operator records and the project-use decision only. | **Phase 5 prep** (decide what the SOURCE `production` refs name on the fresh store, for example a separate running SOURCE Task and Attempt, and whether to bind them as P-058 did for the operator records). Otherwise record it as a known limit. | High on the mechanism. Medium on whether Phase 5 planning already intends a real SOURCE Task. |
| m-1 | Minor | 06q Step 5 rows `return_spec_02_*` and `review_spec_02_*` (aliases `return_spec_02`, `review_spec_02`) | `research_system/discovery/spec.py:41-48`; `research_system/discovery/spec_assay.py:187-208` | The route exposes no SPEC-02 aliases. P-058 (4a′ decisions, 2026-09-17) explicitly drops only the SPEC-01 aliases. No P-058 block decides the SPEC-02 aliases. | `ACTION_EFFECTS` printout (25 keys, no aliases) | Stephen confirms the drop (decline), by analogy with 4a′. | High |
| m-2 | Minor | Step 5 `start_spec_02` completion proof: "exact Assay PROMOTE Decision and separate SPEC-02 approval both bind the plan" | `spec_assay.py:1834-1857`, `1910` | The plan binds the PROMOTE Decision by reference. It binds the approval only through its copied scope and checked ceiling. OR-015 cites `approval:<id>` without a hash. The approval is immutable and is re-verified at its causal prefix, so I found no exploitable path. The divergence itself is undecided. | Code | Info for Stephen; known limit or decline. | High |
| m-3 | Minor | §4 item 2 (correction under D4) | `spec.py:634-642` versus `spec_result.py:672-674` | `correct_spec_01_source` records the review without the governing-review pre-check that project-use runs. If the review evidence cannot govern use authority, the route's next effect is always `SetArtefactUseAuthority`, which admission refuses. The correction then cannot complete. It fails closed and sits off the planned PARK path (a correction runs only when evidence needs one). | Code comparison, not reproduced | Known limit, or a Phase 5 prep check if a correction becomes necessary. | Medium |
| m-4 | Minor | §5.0 (operability of an exact retry) | `research_system/command/service.py:1434-1439`, `5671-5686`; `spec.py:867-880` | Non-lifecycle CommandService commands persist a *rejected* receipt and return it again for the same command ID. The route derives the command ID from (intent key, effect, actor, grant, payload). So a transient admission refusal of a time-free effect (`RecordScientificReview` or `SetArtefactUseAuthority` on a correction or project-use decision; for example, a grant not yet effective) repeats for that actor and grant. Recovery needs a new grant. The refusal leaves no authoritative effect. | Code, not reproduced | Phase 5 runbook note: "after a refusal, retry under a new grant". | Medium |
| i-1 | Info | Step 5 `accept_project_use_decision` actor column | `spec_result.py:4-6`; `.research-system/contracts/wp6-1-owner-source-catalogue.yaml:6885-6890` | The module docstring says "the owner's use authority". Admission allows use authority from human, agent and service grants, and the route does not require the owner. The contract (Step 5; §4 item 5) requires only an independent reviewer and separate non-producer grants, which the route enforces (`spec_result.py:536-556`, `676-681`). | Code | Correct the wording at a later touch; no gate change. | High |

### 2.1 Reproductions for B-1

**(a) `store init` for a fresh root is refused before any write.** I ran this from the review worktree, with a
scratch root and a schema-shaped bootstrap input:

```
uv run python -c "import sys; from research_system import cli; raise SystemExit(cli.main(sys.argv[1:]))" \
  store init --code-root C:/Users/steph/TDL-4c-review --control-root <scratch>/fresh-control \
  --project-id prj_01978abc-1000-7000-8000-000000001000 --authority-bootstrap <scratch>/bootstrap.json
-> research_system.errors.ConfigurationError: canonical foundation origin witness path is not canonical
   (research_system/config.py:565)
```

No `fresh-control` directory was created. The foundation's pinned witness path is the slot for the live store's
`initial_control_root`. Any other root derives a different slot (`config.py:556-566`).

**(b) The SPEC CLI cannot address a store the committed foundation does not name.** I used a scratch analogue
built from the repository's own fixtures. Store A stands for the live store that main's foundation names; store
B stands for a fresh store. The test file was uncommitted and deleted after the run:

```python
def test_fresh_store_is_unreachable_through_the_committed_foundation(tmp_path, monkeypatch, capsys):
    store_a = bind_scratch_route(tmp_path / "a", monkeypatch)
    store_b = bind_scratch_route(tmp_path / "b", monkeypatch)
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: store_a.fixture.foundation_path)
    config_b = tmp_path / "operator-b.json"
    config_b.write_bytes(canonical_bytes(store_b.config))
    events_before = len(store_b.coordinator.ledger.snapshot().events)
    code = cli.main(["discovery", "spec", "status", "--operator-config", str(config_b)])
    assert code != 0
    assert "SPEC operator identity differs from the repository foundation" in capsys.readouterr().err
    assert len(store_b.coordinator.ledger.snapshot().events) == events_before
```

Result: **1 passed** (55 s). The refusal comes from `current_binding.py:798-803`. Every SPEC test reaches its
scratch store only by monkeypatching `cli.canonical_foundation_path` (`test_spec_source.py:241`, `390`;
`test_spec_result.py:823`; `test_spec_task.py:365`). No test runs the genuine CLI against a store that the
committed foundation does not name.

**(c) A foundation re-pin cannot ride as a documentation-only successor.**
`validate_reviewed_documentation_successor` refuses "governed code, configuration, contracts, or locks"
(`governed_code.py:792`).

**Open question for Phase 5 prep (not resolved here).** `store init` passes the foundation's
`origin_witness_sha256` as the expected digest of the witness it writes (`identity.py:374-375`). #324 notes that
a witness binds its own stage's physical identity. So whether the new store's witness digest can be known, and
committed, before initialization needs an answer as part of B-1's fix.

**Why Blocking.** This is an exact-head reachable failure of §4. At `e5179b57`, items 1–6 cannot be produced on
any fresh store through the public CLI, and Phase 5 step 1 ("bind the reviewed main SHA to that fresh store") is
unachievable at this SHA. It fails closed: there is no corruption and nothing is appended. The live store is
also not a fallback: its ledger fails replay, and P-058 forbids appending to it.

## 3. Coverage

### 3.1 Tests run (scratch stores only)

- `pytest -m "not slow"` over `tests/research_system/integration/test_spec_*.py` and
  `tests/research_system/unit/test_spec_replay.py`: **44 passed, 1 skipped, 80 deselected (23.9 s)**. The run
  was in my linked worktree. The two full-table equality tests (`test_spec_result.py::test_the_action_table_…`
  and `test_spec_source.py::test_source_failure_classification_and_action_contract`) are included. They pin all
  25 actions and their ordered effects.
- The B-1 reproductions in §2.1.
- I did not run any slow public-route test.

### 3.2 The 25 actions

For every action I read the route's row tuple, effect derivation, `_check_relation` binding, evaluation and
exact-retry handling. "No finding" means nothing beyond the recorded known limits.

| Action | What I examined | Result |
|---|---|---|
| `observe_source` | `spec.py:429-668` (state, effects, OR-029 batch, Candidate binding); `spec_source.py` (resolution, document, causal prefix, manifest) | M-2; otherwise no finding. #292 KL4 (no exact-retry machinery) applies. |
| `correct_spec_01_source` | `spec.py:507-548`, `630-657` (independent review, separate use actor and three distinct grants); D4 2.0.0 | m-3, m-4 |
| `close_task` | `spec_task.py` in full; `spec.py:670-755` | No finding. #286 KL1 and KL2 apply. |
| `register_project_use_decision` | `spec_result.py:175-367`, `484-514`, `611-659`; terminal-status and disposition gates; ledger-derived references | No finding. #288 KL6 and KL7 and #292 KL1 apply. |
| `accept_project_use_decision` | `spec_result.py:517-584`, `660-681` (review independent of the registrant, governing-review pre-check, separate use actor and grants) | i-1, m-4 |
| `bootstrap_genesis` | `spec_assay.py:2281-2282` (owner-only binding at the prefix) | No finding |
| `bootstrap_assay_authority` | Rows OR-101–108 payloads (`1467-1497`); OR-105 author binding; admission owner-only at OR-108 | No finding. #290 KL2, KL3, KL5 and KL8 apply. |
| `request_spec_01` | OR-003 payload; refuses the producer or owner as requester; foreign-Assay refusal (`2560-2563`) | No finding |
| `prepare_spec_01` | `_brief` (`765-794`); `_task_provenance` (`683-733`); manifest (`1330-1408`); orphan reuse (`2621-2642`) | No finding. #291 KL2 and KL14 (now refused in-lock, `spec.py:76-93`) apply. |
| `return_spec_01_complete` | `_return_basis`, `_scorecard`, OR-004 exact re-supply (canonical comparison) | No finding. #291 KL1 and KL3 apply. |
| `return_spec_01_partial` | `_partial_artifact`, OR-005 re-supply, alternative exclusion (`_return_taken`) | No finding. #296 KL1 applies. |
| `review_spec_01_complete` | OR-034 contract; OR-006 approving verdict; refuses the producer or owner as requester and the owner as reviewer | No finding. #291 KL4 and KL9 apply. |
| `review_spec_01_partial` | As above for OR-035 and OR-007 | No finding. #296 KL2 applies. |
| `decide_spec_01` | OR-012 (refuses the producer, reviewer or owner as proposer; mechanical PROMOTE; `_refuse_blocked_promote`); OR-013 (PARK needs triggers; PROMOTE refusal) | No finding. #291 KL1 and KL11 apply (Phase 5 prep: the SPEC-01 rule). |
| `request_spec_01_revisit` | `_revisit_payload` (`2208-2276`), `_route_source_observation` | No finding. #297 KL1, KL2 and KL7 apply. |
| `authorize_spec_01_retry` | OR-010 payload (RETRY fixed); admission owner-only | No finding. #297 KL3 applies. |
| `request_spec_01_retry` | OR-011 payload; requester binding; ordinal lineage (`_subjects`) | No finding. #297 KL6 applies. |
| `approve_spec_02` | `_live_run_approval` (`1036-1077`); owner binding; ceiling at most the contract limits | No finding. #298 KL8 applies. |
| `prepare_spec_02` | `_spec_02_brief` (`1080-1116`); requires the approval | No finding |
| `start_spec_02` | `_spike_start`, `_execution_pair`, `_execution_relation`, `_spike_plan`; Lease liveness at `taken_at` | m-2. #298 KL3 and KL7 apply. |
| `return_spec_02_complete` | `_spike_return` (`1148-1240`); own-Attempt evidence; OR-018 producer binding | No finding. #309 KL3–KL5 apply. |
| `return_spec_02_partial` | `_partial_closure`; OR-019 | No finding. #309 KL1 and KL2 apply. |
| `review_spec_02_complete` | OR-036 and OR-020 bindings (`2337-2367`) | No finding |
| `review_spec_02_partial` | OR-037 and OR-021 | No finding |
| `decide_spec_02` | OR-026 and OR-027; `_refuse_spike_option` (no KILL after a PASS); Partial terminal | No finding. #309 KL10 applies (Phase 5 prep: `adopt_default` after a Spike PROMOTE). |

### 3.3 §4 items 1–6

| Item | What I examined | Result |
|---|---|---|
| 1. The CLI consumes `SpecOperatorConfig@1.0.0` and the shared verified-binding loader | `cli.py:120-157`; `SpecCoordinator.__init__`; `load_current_binding` in full; #341 | **B-1** (fresh store unreachable), **M-1** (durable clean checkout). The consumption itself is correct. |
| 2. Exact Git resolution; bytes and SHA-256 registered append-only; correction under D4 | `spec_source.py` in full; SOURCE state and advance; the correction path | **M-2**, m-3. I did not re-resolve `neurips2024` over the network (no provider calls); PR #282's real resolution is the record. |
| 3. Provenance; independent review and owner-only decisions not supplied by the wrong actor | Every route binding (`_check_relation`, `_check_spike_relation`, `_check_actor_relation`, `_verify_review`, `_verify_use`); the generic path (`ars command submit` builds a CommandService with no Discovery types; generic `ResolveDecision` requires a C1 `under_review` Decision, `service.py:4609-4640`, so it cannot resolve a route Decision) | No finding beyond the known limits; i-1 |
| 4. The fresh Task closes only through SubmitForReview then AcceptTask | `spec_task.py` (identity, content and exclusivity layers; independence; accept-all); `_accepted_closure` requires a route-issued completed closure | No finding |
| 5. An independently accepted ProjectUseDecision; `--task-id` isolation; PARK and no_spike imply no adoption | `derive`; `_PERMITTED_DISPOSITIONS` (PARK permits only `retain_experimental_benchmark`); `_DISPOSITION_TEXT` and `_SUBSET_TEXT`; `result` stays pending until registration, review and use authority are all verified; Markdown rendering | No finding |
| 6. Fresh-process replay; governed backup and restore | `spec_replay.py` (per-operation cache keyed by canonical event bytes, registry and validator identity; deep copies; nothing cached across processes); `operations/backups.py:573-590` (copies `objects/`, `events/`, `manifests/`, `receipts/`, `snapshots/` and `runtime/` whole, so all eight route object kinds are included) | No replay finding. B-1 also blocks `store backup --operator-config` on a fresh store. **Not examined:** VerifyRestore end to end over the route's document kinds (slow; that belongs to the Phase 0 and assembled packets). |

### 3.4 Boundary questions (Q3)

| Question | Answer |
|---|---|
| Wrong actor for an independent review or owner-only decision | Not reachable through the public route (§3.3 item 3). |
| PROMOTE, SPEC-02 approval or a Spike start without its predecessor | Not reachable. OR-012 requires a completed route review; PROMOTE needs a mechanical PROMOTE and passes `_refuse_blocked_promote`. `approve_spec_02` requires a route-completed `decide_spec_01` PROMOTE (`_promoted_assay`). Every `start_spec_02` row requires a completed `prepare_spec_02`, which requires a completed `approve_spec_02`. |
| A durable write before a refusal | Not found. Document bytes are published inside admission's lock and withdrawn if nothing was appended. Every route refusal precedes submission. |
| A durable record that misstates what happened | M-2: caller-asserted SOURCE provenance. |
| Mispublication | Not found. |
| Replay divergence from a fresh process | Not found. |
| A Task closed other than through SubmitForReview then AcceptTask | Not found. |
| A project-use result shown as accepted too early, or a PARK result implying adoption | Not found. |

### 3.5 Platform changes since `e7b8f1da` (Q4)

| PR | Effect on route guarantees |
|---|---|
| #313 | Message text only. No change. |
| #322 | A fresh command ID under a committed key now returns the original receipt for non-C1 commands. The route derives every command ID from its key, so it never presents a fresh ID under a committed key. No change. |
| #324 | Concurrent identical store initializers converge. Phase 5 creates its store with a single operator. No change. |
| #325 | The tests' own foundation. No production route change. |
| #333 | Witness paths are compared in one form. This removes false refusals. No change. |
| #341 | **Yes, this changes Phase 5.** See M-1. Step 1 must run from a non-linked checkout outside the agent worktree directories. That checkout becomes the store's schema root and code root, and it must stay clean, and at the bound head or a documentation-only successor, through every later route invocation. |

### 3.6 Known limits (Q5)

I found no recorded known limit that falsifies a durable claim on the planned PARK/no_spike Phase 5 path,
provided Phase 5 prep completes its recorded prerequisites. Those are the replacement Assay authority content
(#291 KL1) and SPEC-01 rule evaluation before any PROMOTE. #291 KL4 (the outcome review records the route-fixed
grade `independent` while demonstrating only distinct actors) is reachable on that path. It is recorded, and I
do not argue that it is false.

## 4. Composition map: Step 5 → P-058 → `ACTION_EFFECTS`

Step 5 lists 30 actions. P-058 removes six: `bootstrap_dossier_authority`, `bootstrap_path_authority`,
`admit_dossier` and the three `*_spec_01_brief_inputs` actions. That leaves 24, and Phase 2's `close_task` brings
the route to **25**, which matches `ACTION_EFFECTS` (`spec.py:41-48`) and the full-table tests.

| Step 5 action (alias) | Ordered effects at `e5179b57` | Divergence from Step 5 | Covered by |
|---|---|---|---|
| `bootstrap_genesis` | OR-140 | Actor bound to the owner | P-058 amendment (route bindings) |
| `bootstrap_assay_authority` | OR-101…OR-108 | None | — |
| `bootstrap_dossier_authority`, `bootstrap_path_authority`, `admit_dossier` | — | Removed | P-058 |
| `observe_source` | AR → OR-029 | Manifest provenance is caller-supplied (M-2) | **Not decided** |
| `request_spec_01` | OR-003 | Requester is neither the producer nor the owner | P-058 amendment |
| `register_`, `review_`, `accept_spec_01_brief_inputs` | — | Removed | P-058 |
| `prepare_spec_01` | AR (brief 1.0.0; 1.1.0 from ordinal 2) | Owner registers (inherited); later-Assay version | P-058 4a-2 review; #297 decision |
| `return_spec_01_complete` (`return_spec_01`) | AR → OR-004 | Alias dropped; owner registers and the producer re-supplies | P-058 4a′; 4a-2 review |
| `return_spec_01_partial` (`return_spec_01`) | AR (own Partial record) → OR-005 | Separate record, not "same schema" | P-058 4a′ |
| `review_spec_01_complete` (`review_spec_01`) | OR-034 → OR-006 | Alias dropped; approving review only | P-058 4a′; 4a-2 review |
| `review_spec_01_partial` (`review_spec_01`) | OR-035 → OR-007 | Alias dropped | P-058 4a′ |
| `decide_spec_01` | OR-012 → OR-013 | PROMOTE refusals added | P-058 4a-2 round 2 and round 3 |
| `request_spec_01_revisit` | OR-009 | From a reviewed Partial, not "parked" | P-058 2026-09-14 and 4b |
| `authorize_spec_01_retry` | OR-010 (RETRY fixed) | None | P-058 4b |
| `request_spec_01_retry` | OR-011 | `assay_ordinal` identities | P-058 4b |
| `correct_spec_01_source` | AR → SR → AU (2.0.0) | Version 2.0.0 | D4 / P-054 |
| `approve_spec_02` | AR (approval 1.0.0) | None | P-058 4b-2 |
| `prepare_spec_02` | AR (SPEC-02 brief 1.0.0) | Own record, not the SPEC-01 brief package | P-058 4b-2 |
| `start_spec_02` | OR-014 → OR-015 → OR-016 → OR-017 | The approval binds the plan by content, not by reference (m-2) | **Not decided** |
| `return_spec_02_complete` (`return_spec_02`) | AR (SPEC-02 return) → OR-018 | Own record (decided); **alias dropped (m-1)** | 4b-2b decision 1; alias **not decided** |
| `return_spec_02_partial` (`return_spec_02`) | AR (SPEC-02 return) → OR-019 | As above | As above |
| `review_spec_02_complete` (`review_spec_02`) | OR-036 → OR-020 | **Alias dropped (m-1)** | **Not decided** |
| `review_spec_02_partial` (`review_spec_02`) | OR-037 → OR-021 | **Alias dropped (m-1)** | **Not decided** |
| `decide_spec_02` | OR-026 → OR-027 | No KILL after a PASS | P-058 4b-2b decision 5 |
| `register_project_use_decision` | AR | None | — |
| `accept_project_use_decision` | SR → AU | None | — |
| *(not in Step 5)* `close_task` | SubmitForReview → … → AcceptTask (7) | Added | P-058 preamble; Phase 2 |

Step 5's "one sealed completion" per action is replaced by evidence-derived state with no composite seal, under
D1 (P-051). That is decided.
