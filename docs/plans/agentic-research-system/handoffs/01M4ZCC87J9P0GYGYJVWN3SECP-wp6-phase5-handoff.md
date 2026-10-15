# WP6 Gate 6 Phase 5 handoff: the delta assurance, the fresh store and the bounded live run

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main. Phase 5 prep construction is complete: #348 to #352 are merged. The
integrated certification packet ran at `b09813e6`, the #352 head (P-058, "Prep construction complete
(2026-10-15)"). Its tree, `6ec37ed1…`, is identical to main `bbdcb068`, so its result applies to that main.

**Dispatch state:** ready for Stephen's explicit dispatch. Stephen made both decisions in that P-058 entry on
2026-10-15:
- he confirmed the PR-B naming rule;
- he chose option A for the delta assurance's selection.

The first deliverable is the delta assurance. Nothing live happens before Stephen records it.

**Recommended model:** the strongest available reasoning model, at `xhigh`.

**Predecessors:** `handoffs/01M4AJCXSVTDDDDAYZTZWZ9AQK-wp6-phase5-prep-handoff.md` (prep) and
`handoffs/01M4677SY7MNV0FA274DM87YME-wp6-phase4c-assembly-handoff.md` (4c). Their mechanics and hard boundaries
still apply, except where this handoff updates them.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 5**: KAN-110's exit (the delta assurance), then KAN-103's
remaining Phase 5 steps, in `C:\Users\steph\TDL`.

### Start identity

1. Refresh `origin/main`. It must contain `bbdcb068` (#352) and the prep close-out docs PR that added this file.
   Record that exact SHA as **M1** before the first write.
2. Create one clean linked worktree under `C:/Users/steph/` for docs and evidence work. Copy the primary
   checkout's `.env` into it, run `uv sync --locked --extra dev` and prove that pytest runs there.
3. Before any write, verify:
   - the working directory;
   - the symbolic branch and HEAD;
   - a clean status;
   - ancestry from M1.

### Read first

1. `implementation/06s-phase5-runbook.md`. It is the live sequence, the actor plan, the bootstrap and step 3's
   order of operations, updated 2026-10-15 for the merged code.
2. `03-decisions-and-open-questions.md`, P-058 from "Phase 5 prep design decisions (2026-10-07)" to "Prep
   construction complete (2026-10-15)". It holds P5-1 to P5-12, the census, PR-A's decisions, the P5-7 amendment
   and the close-out.
3. `implementation/06s-phase5-prep-design-pass-2026-10-07.md` §4 (A1 to A7) and
   `implementation/06s-phase5-prep-census-2026-10-07.md`.
4. `implementation/06s-gate6-delivery-replan-and-gate7-integration.md`: Phase 5, with every P-058 amendment.
5. `reviews/06s-phase4c-boundary-review-e5179b57-2026-10-07.md`: B-1, M-1 and M-2.
6. The known limits and review rounds in the PR descriptions of #348 to #352.

### Scope, in order

1. **The delta assurance (P5-12; KAN-110's exit).** No live operation.
   - **The selection (Stephen, option A).** The 57 nodes of the 4c selection that the integrated packet did not
     run. They are listed in the appendix.
     - **How the list was derived:** from `C:/Users/steph/.codex/tmp/g6-4c/4c-collect-e5179b57.txt` (4c, with CRLF
       endings) and `C:/Users/steph/.codex/tmp/g6-p5prep/prep-collect-b09813e6.txt`. The files are in pytest
       collection order, so normalize and sort both before comparing:
       `LC_ALL=C comm -23 <(tr -d '\r' < 4c | grep '::' | sort -u) <(tr -d '\r' < prep | grep '::' | sort -u)`.
       It must yield exactly the appendix's 57 lines.
     - Collect them at M1, and confirm all 57 are present. They were at `bbdcb068`.
     - Reconcile every node against JUnit.
     - If M1 changes any code or test file beyond `bbdcb068` (it should not: the close-out PR is docs only),
       stop and bring the selection back to Stephen.
   - **The window and budget.** Run in the 02:00–11:00 window under P-058's budget, with a machine check
     recorded before the window.
   - **The network probe.** Propose to Stephen running the opt-in probe
     `test_spec_source.py::test_neurips2024_exact_public_registration` once with `ARS_SOURCE_NETWORK_PROOF=1`. It
     is read-only public Git, with no credentials, against the step 3 source. Run it only if he agrees.
   - **The fresh-context review.**
     - Write its brief, scoped to the `e5179b57..M1` diff. It must confirm closed: B-1, B-2 and B-3; M-1 and M-2;
       and the SPEC-01 rule and bar.
     - Stephen dispatches the reviewer. You do not review your own construction.
   - **Hand back** the results for Stephen to record. KAN-110 closes on his record.
2. **A0, Stephen's decisions for the run** (runbook §0 and §2). Prepare them, without executing anything:
   - the owner actor and the allocated actor plan (runbook §1);
   - the authority bootstrap manifest and its digest;
   - the paid-run subset and cost ceiling (D6).
3. **The live sequence L1 to L7** (runbook §3). Each A# is prepared exactly, authorized by Stephen on its own,
   run alone, and verified from durable state before the next.
   - **PR-F, the re-pin,** is a docs-and-config PR that Stephen merges, giving M2.
   - **L5, the delta assurance on M2.** Propose its scope before L4. M2 is M1 plus the foundation and its
     contract test, so a re-pin-scoped selection plus that diff's review may be enough. That is Stephen's call.
4. **Step 3, the bounded run** (runbook §4), then **steps 4 to 6** (runbook §5), each under its own
   authorization.

### Mechanics

- **The runner.** `C:/Users/steph/.codex/tmp/g6-p5prep/certify_prep.py` is the 4c runner adapted for prep.
  - It takes a SHA, a label, a worktree and a collected node list. `--now` skips the window, and only on
    Stephen's say-so.
  - It is resumable, reconciles every node against JUnit and records the budget flags.
  - Copy it next to your evidence. Do not edit it in place.
- **Known runner traps** (observations 2026-10-07 to 2026-10-15):
  - **The app restart.** A terminal tab dies when the app or session restarts. After any resume, check
    `waiting.json`/`started.json` and the live runner processes, and relaunch if needed.
  - **Interrupted results.** Stopping the runner with Ctrl-C writes result files for the groups it interrupts.
    They show exit 1/2, `KeyboardInterrupt` or "no tests ran", and a resume trusts them. Before resuming, move
    any such result aside.
  - **A run proves nothing on environment failure.** "Git inspection is unavailable (timed out)" appears under
    load. Do not overlap heavy runs. A mutation control holds only when its failure is the one the guard
    causes.
- **Durations.** The SPEC-01, SPEC-02 and spike-outcome public-path tests take 30 to 70 minutes each.
  `p14-spec_spike_outcome-2` exceeded the 60-minute group budget once (69.7 min).
- **The Candidate ID.** Step 3 derives it with a read-only Python call (`spec_source.source_ids`). There is no
  CLI for it.
- **The CI suite lane is red on main** (P-058, 2026-10-15): the nightly's failures are outside the
  known-failures list and are not prep regressions. The delta assurance runs locally. Do not treat CI red as
  evidence either way, and do not fix it inside Phase 5.
- **Commits.** The 4c mechanics still apply:
  - commit with `git commit -F`, never piped;
  - throwaway detached worktrees for mutation controls;
  - a head Codex did not review is recorded as such.

### Hard boundaries

- **Live work.** Each live operation (A1 to A7, step 3's effects, backup and restore) is prepared exactly and
  authorized separately by Stephen. Nothing in this handoff authorizes one. No provider, paid or credential
  work beyond the subset and ceiling Stephen sets at A0.
- **The live store.** `C:/Users/steph/TDL-ARS-WP64-Control` stays historical evidence. Never append to it
  (P-057, P-058).
- **The successor binding.** None until the delta assurance passes and Stephen records it.
- **The durable checkout.** `C:/Users/steph/TDL-ARS-G6-Checkout` stays clean and frozen once bound: nothing is
  pulled into it and no worktree is added (P5-5).
- **No new structures.** No new plan, framework, persisted model, composite seal or speculative STORE change
  (D5). No replacement of `SpecOperatorConfig@1.0.0` without Stephen's decision.
- **The results directory.** No toy or synthetic output in `results/`.
- **Hooks, reviews and merges.**
  - Never bypass hooks.
  - Stephen controls CodeRabbit, merges and auto-merge.
  - Do not apply a review stopping rule to a PR until Stephen accepts it for that PR.
- **06t (P-060).** Out of scope until Gate 6 closes.

### Handback

Lead with the applicable 06s §8 row. Then give:
- the exact SHAs (M1, and M2 once it exists);
- the delta assurance evidence and the review brief;
- each authorized live step with its durable verification;
- the decisions Stephen needs to make;
- verified Jira changes.

## Appendix: the delta assurance's 57 nodes (option A)

The 4c selection's nodes that the integrated packet did not run, in C-locale order. All 57 were collected at `bbdcb068`.

```text
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_candidate_is_exactly_the_five_file_inert_stage_a_subject
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_command_families_bind_exact_owner_catalogue_authority_and_controls
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_consumer_inventory_is_exactly_closed_over_policy_and_production_dispatch
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_direct_artefact_storage_boundary_is_exact_including_history_and_content_reads
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_identity_manifest_binds_every_leaf_by_raw_sha256_and_git_blob
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_object_store_boundary_analysis_catches_alias_method_and_typed_wrapper_bypasses
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_resolver_and_command_failures_distinguish_rejection_from_acceptance
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_review_universe_and_p005_are_deterministic_and_no_omission
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_session_exchange_storage_inventory_names_only_the_live_artefact_writer
tests/research_system/contracts/test_06i_stage_a_candidate.py::test_transitive_root_analysis_ignores_statically_dead_and_uncalled_nested_calls
tests/research_system/contracts/test_wp64_session_exchange.py::test_caller_json_keywords_cannot_publish_later_revisions[acceptance_evidence]
tests/research_system/contracts/test_wp64_session_exchange.py::test_caller_json_keywords_cannot_publish_later_revisions[acceptor_actor_id]
tests/research_system/contracts/test_wp64_session_exchange.py::test_caller_json_keywords_cannot_publish_later_revisions[authority_grant_id]
tests/research_system/contracts/test_wp64_session_exchange.py::test_caller_json_keywords_cannot_publish_later_revisions[review_evidence]
tests/research_system/contracts/test_wp64_session_exchange.py::test_closed_schemas_reject_malformed_hashes_and_future_fields
tests/research_system/contracts/test_wp64_session_exchange.py::test_document_returned_and_test_artifact_identities_must_be_disjoint
tests/research_system/contracts/test_wp64_session_exchange.py::test_foreign_brief_identity_rejects_without_publication[attempt_id-att_01978abc-6400-7000-8000-000000000099]
tests/research_system/contracts/test_wp64_session_exchange.py::test_foreign_brief_identity_rejects_without_publication[handoff_id-hnd_01978abc-6400-7000-8000-000000000099]
tests/research_system/contracts/test_wp64_session_exchange.py::test_foreign_brief_identity_rejects_without_publication[session_id-ses_01978abc-6400-7000-8000-000000000099]
tests/research_system/contracts/test_wp64_session_exchange.py::test_identical_retry_converges_and_changed_inputs_conflict_without_mutation
tests/research_system/contracts/test_wp64_session_exchange.py::test_interruption_before_r1_publication_allows_only_identical_retry
tests/research_system/contracts/test_wp64_session_exchange.py::test_malformed_time_git_subject_or_brief_encoding_rejects_without_publication[brief_bytes-\xef\xbb\xbfnot BOM-free]
tests/research_system/contracts/test_wp64_session_exchange.py::test_malformed_time_git_subject_or_brief_encoding_rejects_without_publication[git_commit_sha-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA]
tests/research_system/contracts/test_wp64_session_exchange.py::test_malformed_time_git_subject_or_brief_encoding_rejects_without_publication[git_tree_sha-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb]
tests/research_system/contracts/test_wp64_session_exchange.py::test_malformed_time_git_subject_or_brief_encoding_rejects_without_publication[prepared_at-2026-02-30T09:00:00Z]
tests/research_system/contracts/test_wp64_session_exchange.py::test_malformed_time_git_subject_or_brief_encoding_rejects_without_publication[prepared_at-2026-08-04T09:00:00+00:00]
tests/research_system/contracts/test_wp64_session_exchange.py::test_missing_artifact_and_self_review_reject_without_publication
tests/research_system/contracts/test_wp64_session_exchange.py::test_prepare_session_brief_publishes_exact_provider_free_subject
tests/research_system/contracts/test_wp64_session_exchange.py::test_r1_evidence_binds_exact_brief_artifacts_and_pending_authority
tests/research_system/contracts/test_wp64_session_exchange.py::test_review_transition_requires_the_adjacent_r1_predecessor_without_mutation[0]
tests/research_system/contracts/test_wp64_session_exchange.py::test_review_transition_requires_the_adjacent_r1_predecessor_without_mutation[2]
tests/research_system/contracts/test_wp64_session_exchange.py::test_unresolved_finding_identities_are_unique_without_reordering
tests/research_system/integration/test_artefact_authority_commands.py::test_register_review_and_use_authority_are_real_durable_commands
tests/research_system/integration/test_artefact_authority_commands.py::test_use_authority_rejects_without_independent_review_resolver
tests/research_system/unit/test_artefact_consumer_boundary.py::test_contract_loader_materialization_is_exact_and_catalogue_complete
tests/research_system/unit/test_artefact_consumer_boundary.py::test_contract_loader_rejects_wrong_independent_manifest_subject
tests/research_system/unit/test_artefact_consumer_boundary.py::test_first_party_artefact_accesses_are_exactly_classified
tests/research_system/unit/test_artefact_consumer_boundary.py::test_migrated_canonical_consumers_use_fixed_policy_methods_and_purposes
tests/research_system/unit/test_artefact_runtime.py::test_control_content_reader_rejects_escape_and_foreign_root
tests/research_system/unit/test_artefact_runtime.py::test_governing_review_store_is_write_once_and_project_bound
tests/research_system/unit/test_artefact_runtime.py::test_production_consumers_validate_scoped_authority_replay_before_resolution
tests/tools/test_ars_currency_workflow_controls.py::test_currency_control_jobs_cannot_be_successfully_skipped
tests/tools/test_ars_currency_workflow_controls.py::test_currency_controls_record_their_exact_checked_out_subject
tests/tools/test_ars_currency_workflow_controls.py::test_currency_controls_run_on_pull_requests_and_merge_groups
tests/tools/test_check_workflow_liveness.py::test_a_malformed_run_response_fails_closed
tests/tools/test_check_workflow_liveness.py::test_a_pull_request_run_checks_the_base_branch_workflow_set
tests/tools/test_check_workflow_liveness.py::test_a_recent_scheduled_run_passes
tests/tools/test_check_workflow_liveness.py::test_a_stale_scheduled_run_fails_closed
tests/tools/test_check_workflow_liveness.py::test_a_watchdog_that_never_ran_on_its_schedule_fails_closed
tests/tools/test_check_workflow_liveness.py::test_active_target_workflow_passes
tests/tools/test_check_workflow_liveness.py::test_all_tracked_defaults_to_the_workflow_files_git_tracks
tests/tools/test_check_workflow_liveness.py::test_all_tracked_fails_when_a_tracked_workflow_is_missing_from_github
tests/tools/test_check_workflow_liveness.py::test_all_tracked_names_every_inactive_tracked_workflow
tests/tools/test_check_workflow_liveness.py::test_all_tracked_passes_when_every_tracked_workflow_is_active
tests/tools/test_check_workflow_liveness.py::test_ci_asserts_the_watchdogs_own_schedule_is_still_firing
tests/tools/test_check_workflow_liveness.py::test_manually_disabled_target_workflow_fails_closed
tests/tools/test_check_workflow_liveness.py::test_the_watchdog_checks_every_tracked_workflow
```
