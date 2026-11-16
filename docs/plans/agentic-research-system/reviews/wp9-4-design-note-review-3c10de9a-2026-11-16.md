# Independent review: WP9.4 design note, revision 1 (`3c10de9a`)

**Date:** 2026-11-16<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md`, revision 1, at `3c10de9a`
(`3c10de9a69c56d46d398fb327851ad11d1493d08`) on `claude/confident-volta-0e5dvm`, PR #437. `git rev-parse` of the fetched
branch head gave that commit. Its parent `c67bd93` records P-085. `git diff --stat 4312dc63 3c10de9a` shows two files:
the note (580 lines) and the register (+50 lines, P-085). No code changed after the note's base, so the note's
`path:line` citations at `4312dc63` can be read at `3c10de9a` unchanged.<br>
**Reviewer:** a fresh session. It wrote none of WP9.2, WP9.3 or this note, and it did not read the author's transcript.<br>
**Branch:** `review/w9-wp9-4-note`, cut from `3c10de9a`. The note, the register, the annex, the schemas, `research_system/`,
`tests/` and `papers/` are not edited.<br>
**Method:** `adversarial-design-review`, with `research-assurance-triage` for §16. Every `path:line` below was read at
`3c10de9a`. Twenty probes in `wp9-4-design-note-review-artifacts/test_review_wp9_4_note_probes.py` run on pure functions,
in-memory legacy states, forged transactions and Git object reads at `3c10de9a`. None opens a store.<br>
**Known limit:** the author and the reviewer are the same model family (P-058).

## Verdict

**Accept with required changes.** Revision 2 is needed before Stephen decides the owner points.

The package boundary, the split (A), the D-4 accounting, the decision to keep LR-021 and LR-022 with WP9.7 (D), and the
suspension-as-projection structure all hold. Claims 1 and 3 hold at the code.

One finding is Blocking. Owner point E rests on claim 2, and claim 2 is false: a claim path exists, it is the artefact
path, and WP9.7 is the package that binds it. As written, Stephen would decide E on a false premise, which is the same
pattern as the WP9.3 note's B-1. Thirteen Major findings follow. Four of them change what Stephen is asked: F and G each
refuse too little against an accepted text, P-072 item 4 is dropped, and two owner points are missing. Claim 7 fails on
the real P01-A drafts.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 1 | B-1 |
| Major | 13 | M-1 to M-13 |
| Minor | 12 | m-1 to m-12 |
| Info | 4 | i-1 to i-4 |

## Research-assurance triage

- **Stage.** A design note, not a result. It gets design and dispatch scrutiny.
- **Lanes.** `output_provenance` (every row) and `paper_claim` (LR-039, LR-054, the admissibility predicate). The note
  says the same (§16). No topology, null-model, statistical or representation logic is touched.
- **Governing records.** The owner annex (LR-021 to LR-061, G1 to G5, `suspension_rule`); the W9 record schemas;
  W9 §§4.2, 4.5, 8.2, 8.3, 9, 12.1, 13 and 17; 06v §2.7, §2.8, §5 (WP9.4, WP9.7), D-3, D-4, D-6 and §8; P-072,
  P-073, P-081 and P-085.
- **Machine-checkable claims.** §17 claims 1 to 7, the census, the route counts, the G5 tables, the staleness and
  ordering rules, and the extractor rule on the real drafts. Each was probed (§2).
- **Human-review-only claims.** §5 of this report audits the note's §16 split. Passing these probes shows nothing about
  any real adoption.

## 1. Findings

### B-1 (Blocking). Claim 2 is false, so owner point E is decided on a false premise. The claim path is the artefact path, and WP9.7 binds it

**Claim.** §4.2: "today an unadopted legacy family cannot reach a claim through any code path, and no call site exists
for 'W5 blocks claims resting on a family marked unadopted'". Owner point E then carries the binding to "the package that
first gives a claim a legacy input … No such package is planned under 06v".

**Evidence.**
- The claim path exists. `SetArtefactUseAuthority` to `accepted_for_scope` binds a `claim_promotion` Decision
  (`research_system/command/service.py:4618-4631`, `_claim_promotion_binding` at `:4883-4980`). `resolve_for_claim` and
  `resolve_for_manuscript` resolve `claim_evidence` and `manuscript_evidence` (`research_system/evidence/consumers.py:63-78`;
  `research_system/artefacts/authority.py:32-37`). The note cites the use resolver but not `manuscript_evidence`, which a
  paper's claims would also read.
- Nothing keeps legacy bytes out of that path today. `RegisterArtefact`'s preparer checks identity, the initial
  `candidate` authority and an empty stream, and nothing else (`service.py:4409-4440`). `manifest.relative_path` is a
  free string with no pattern (`register_artefact.schema.json`, `$defs/artefact_manifest/properties/relative_path`). Probe
  `test_defect_claim2_register_artefact_admits_a_legacy_result_path_today`.
- The note's own argument rests on "WP9.7's RegisterArtefact guard refuses a registered legacy file". That guard is not
  built. P-081 already records it as a dependency ("WP9.7's `RegisterArtefact` guard (O-22) before any live
  `untracked_file` or `vault_file` observation", `03-decisions-and-open-questions.md:5274`).
- Even with that guard, 06v WP9.7 rule (a) refuses by **path** ("the resolved path is a manifest-registered legacy
  file"). The use resolver reads only `root_id == "control"` (`research_system/artefacts/runtime.py:31-50`). So a legacy
  file read in place at `repo` fails at use. But a byte copy of a legacy result registered under the control root passes
  rule (a), passes (b) (not the `repo` root), and passes (d) for a `.json`. I reasoned this from the code. I did not run
  it end to end on a scratch store.

**Failure scenario.** Stephen accepts E. WP9.4 records "W9-T17's last clause is proven at the read interface only" and
carries the binding to a package that never exists. WP9.7 builds its path-keyed guard. A successor registers a copy of an
unadopted legacy result as an artefact, promotes it with a `claim_promotion` Decision, and resolves it as claim or
manuscript evidence. `family_admissible` is never called, so W9-T17's last clause and W9 §8.1 ("A closed-reference item
is not usable by a successor until adopted") both fail.

**Impact.** Paper-claim validity. An owner decision would rest on a false statement.

**Required change.** Rewrite §4.2 and owner point E:
- state that the call site exists (the artefact registration and use path) and is open today;
- bind the W5 clause to WP9.7: its `RegisterArtefact` guard, or the use resolver for `claim_evidence` and
  `manuscript_evidence`, calls `family_admissible` (or refuses every legacy-derived artefact outright);
- add a content rule alongside 06v rule (a): refuse an artefact whose SHA-256 equals any recorded legacy observation's
  `sha256` (or whose Git blob equals an observed `git_blob`) unless an active adoption admits it for that consumer kind;
- give WP9.7's note a binding test: an unadopted family's bytes, copied under the control root, are refused at
  registration or at `resolve_for_claim`.

The alternative of holding WP9.4 is then unnecessary. WP9.4 builds the predicate, and WP9.7 inherits a named call site.

**Affects:** owner point E; §4.2, §15 (W9-T17 last clause), §16; 06v WP9.7 (O-22).

### M-1 (Major). §7's "later observation" rule does not suspend a family adoption whose observation WP9.3 projects stale

**Claim.** §7 cause 1, for a family adoption, counts "a later observation of the same registration whose selector names
at least one adopted family". §3 row 3 disposes of the carried obligation as "A stale or re-observed source suspends the
adoption".

**Evidence.** `reduce_record` marks every earlier observation of a registration stale when a later one records a
different blob, whatever its selector (`research_system/legacy/replay/reducers.py:1403-1414`). P-081's O-33 addition says
"the next observation of the registration records the new hash and the accepted record projects as stale, and what
follows is WP9.4's" (`03-decisions-and-open-questions.md:5248-5250`). W9 §4.2 item 3: a blob change "blocks every open
observation, adoption or transition that binds the old blob". Probe
`test_defect_claim6_stale_observation_leaves_family_adoption_active_under_note_rule`: O1 selects `{a}` at blob X; O2
selects `{b}` at blob Y. O1 is stale, and §7's rule does not suspend an adoption of O1's family `a`.

**Failure scenario.** A result file is edited. The observer re-observes only the families a new task needs. The old
adoption stays `active`, `family_admissible` returns true, and LR-039 and LR-054 accept it, all on bytes that no longer
exist.

**Required change.** Make cause 1 "any later observation of the registration whose selector names an adopted family,
**or** whose source fingerprint differs from the adoption's observation (equivalently, the adoption's observation is in
`stale_observations`)". Add the disjoint-family, new-blob case to W9-T9's controls in §15.

**Affects:** §3 row 3, §7, §9 `adoption_status`, §15 W9-T9; claim 6.

### M-2 (Major). The adoption's derived review ID has no slot in the field-keyed G5 tables, and the existing default fails open

**Claim.** §5.1 says WP9.4 extends `_REQUEST_REVIEW_FIELD`, `_DECISION_PROPOSAL_FIELD` and `_FAMILY_REVIEW_FIELD` with
"the request, decision-proposal and review fields of the five families". §5.2 derives the adoption's review ID instead
of storing it.

**Evidence.** All three tables map a row or kind to a **record field name** (`reducers.py:90-102`). The adoption has no
review field (`legacy-adoption-decision.schema.json`; probe `test_claim4_first_half_holds_adoption_schema_has_no_review_ref`).
Where `_FAMILY_REVIEW_FIELD.get(kind)` is `None`, three sites treat the kind as "needs no review": the Decision proposal
(`reducers.py:966-969`), the resolution (`:1092-1093`, `:1118-1119`), and the preparer (`legacy/preparers.py:512`,
`:521`). That default exists for path registrations (LR-004). Probe
`test_defect_wp9_3_g5_check_passes_an_adoption_with_no_review_at_all`: `_check_resolution` accepts an LR-029 adoption
with `considered_review_ids: []` and no review in the state.

**Failure scenario.** An implementer follows the §5.1 table, finds no field to add for the adoption, and leaves it out.
LR-028 and LR-029 then resolve an adoption that no one reviewed, and G5's "the review it names is satisfied" is skipped.

**Required change.** In §5.1 and §5.2, name a review-ID resolver, `review_id_for(kind, record)`, that returns the field's
ID for the four families and the derived ID for the adoption. Use it at every site that today reads the three tables,
in replay and in the preparer. Make a missing entry raise, never default to "no review". Add a negative control: an
adoption resolved with an unsatisfied, or absent, derived review is refused at LR-028 and at LR-029.

**Affects:** owner point C; §5.1, §5.2, §6.4, §15.

### M-3 (Major). "The session rules are unchanged" refuses the analyst on every analyst-proposed WP9.4 kind

**Claim.** §5.1: the session rules "are WP9.3's … WP9.4 changes none of them".

**Evidence.** `_refuse_analyst_creator` exempts only `legacy_path_registration` and the acceptance
(`reducers.py:769-778`). It refuses an analyst who requests a review of, or proposes a Decision on, a proposal they
created. LR-023, LR-030, LR-045 and LR-050 are proposed by `migration_analyst`, and LR-026/031/046/051 and
LR-028/033/048/053 are requested by `migration_analyst` (annex). Probe
`test_defect_session_rule_refuses_the_analyst_on_every_analyst_proposed_wp9_4_kind`. WP9.3 note §5.5 states the
exemption's reason: those are "the analyst's own proposals". The four WP9.4 kinds are too.
`_creator_role_actor` also has no case for `legacy_source_inventory`, whose creator is its observer (LR-040).

**Failure scenario.** Unchanged, no adoption, discharge, mapping or ownership can be reviewed by a single analyst.
Changed without a design statement, the change goes unreviewed.

**Required change.** Add `_refuse_analyst_creator`'s exempt set and `_creator_role_actor` to the §5.1 table. State
which WP9.4 kinds are the analyst's own (adoption, discharge, mapping, ownership) and that the source inventory's creator
is its observer.

**Affects:** §5.1, §6.4, §8, §10; W9-C20.

### M-4 (Major). P-072 item 4 puts fixture evidence refs in the resolving Decision. The note makes them human-only, and the WP9.3 encoding forbids them

**Claim.** §6.4: LR-029's fixtures "are conditional on facts about the family and the use. The record has no fixture
field … the row's fixture list is a checklist line for the adoption's reviewer, not a replay check". §10.4 and §16 say
the same of LR-054's `pilot_promotion` evidence.

**Evidence.**
- P-072 item 4 (accepted): "Per-fixture evidence or waiver refs travel in the resolving Decision, or, for a
  closed-reference batch, in the record itself" (`03-decisions-and-open-questions.md:4619-4620`).
- S-017 on LR-029 is unconditional (`when: null`, annex LR-029). So are F-006, F-019, F-023 and F-037 on LR-054,
  F-018, F-023 and F-037 on LR-044, and S-007 on every review row. Probe `test_annex_lr029_fixture_s017_is_unconditional`.
- WP9.3's encoding fixes the proposal's `governing_evidence_refs` to exactly three entries, and the resolution's to those
  same three (`reducers.py:938-946`, `:1102`). No fixture ref fits. Probe
  `test_defect_decision_proposal_admits_exactly_three_refs_so_no_fixture_or_eligibility_ref_fits`.

**Failure scenario.** An adoption or a paper-root transition is resolved with no S-017, F-019 or F-037 evidence named
anywhere in the ledger. Nothing in replay can show the gap, although an accepted decision says the refs travel in the
Decision.

**Required change.** Either encode fixture refs in the resolving Decision (for example `w9-fixture:<id>:<rev_|art_|dec_>`
entries after the three subject refs, with replay requiring every unconditional fixture and admitting only the row's
listed ones, as WP9.3 did for LR-020), or put the departure from P-072 item 4 to Stephen as an owner point. Correct §6.4:
S-017 is unconditional.

**Affects:** §6.4, §10.4, §16; P-072 item 4; LR-029, LR-034, LR-044, LR-049, LR-054, LR-055.

### M-5 (Major). Claim 7 fails. The path-literal extractor misses directly cited results in the P01-A drafts, and its blocking contingency cannot run

**Claim.** §11.1, owner point I: a cited file is a registered `legacy_research_result` whose normalized repository path
appears literally, "after `\` is read as `/`". "The basename alone does not count." A disagreement is resolved by "a
draft change or a recorded reading by Stephen". §17 claim 7.

**Evidence** (probes read the drafts from Git at `3c10de9a`; no file under `papers/` was edited):
- **Basename citations.** P01-A's drafts cite seven tracked result files by basename only. Six resolve uniquely under
  `results/`: `03_multi_threshold.json`, `ari_om_gmm_normalised_2026-06-24.json`, `bhps_headline_frozen_2026-05-28.json`,
  `escape_wilson_ci_2026-05-16.json`, `stability_se_stored_2026-06-22.json` and `sub_regime_thresh_sweep_2026-06-07.json`
  (for example `results-ari-stability.md:75`, "Cleanly supported by `escape_wilson_ci_2026-05-16.json`"). The seventh,
  `05_analysis.json`, has three candidates. Probe `test_defect_claim7_basename_citations_in_p01a_drafts_are_missed`.
- **JSON-escaped Windows paths.** `drafts/sections/table1_effects_2026-05-22.json` cites seven results as
  `"C:\\Users\\steph\\TDL\\…\\results\\…"`. The bytes hold doubled backslashes, so the rule yields `results//…` and finds
  none of them in that file. They are found today only because other files repeat them with `/`. Probe
  `test_defect_claim7_json_escaped_windows_paths_are_not_read_as_paths`.
- **Unregistered results drop silently.** A literal that names a result file with no registration is not a "cited file"
  under the rule, so it never becomes a blocker.
- **Scope.** "Every file in the inventory" includes `_project.md` and the reviewer-response notes. For P01-A that adds 19
  result files cited only outside `drafts/`, against 17 inside. For P01-B it adds 4, against 2. Probe
  `test_claim7_whole_root_scan_adds_files_cited_only_outside_the_drafts`. W9 §12.1 says "every result family its
  **drafts** cite". This refuses more, not less, but it is a reading the note does not state.
- **The contingency.** LR-054's precondition is "the citation extractor's output equals the reviewer's derivation, else
  blocked" (annex). No row records "a reading by Stephen". A draft change is a write to a registered legacy file, which
  re-triggers observation, inventory and mapping (W9 §4.2 item 3).
- **06v.** 06v WP9.4 defines the extractor's output as "projected to families through the accepted membership tables
  **and the audit's artifact map**". The note moves the artifact map to the reviewer only and does not say this departs
  from 06v.

**Failure scenario.** An honest reviewer includes the six basename-cited files, so the hashes differ and P01-A's
transition is blocked with no executable way out. A reviewer who conforms to the extractor omits them, the hashes agree,
and W9-T17's second clause ("drafts cite a family missing from that set") passes on a set that omits six cited results.

**Required change.** In owner point I:
- decode JSON string escapes before normalizing, and collapse repeated `/`;
- resolve a basename against registered paths: a unique match is a cited file, and an ambiguous or unregistered match
  is a **blocker entry**, never a silent drop;
- treat a literal naming an unregistered file under `results/` as a blocker;
- state the scope: drafts only, or the whole root, and why;
- replace "a recorded reading by Stephen" with an executable route (a row, or "blocked until a new citation status"), or
  remove it;
- record the departure from 06v's artifact-map output.

**Affects:** owner point I; §11.1, §11.2, §15 (W9-T17), D-3.

### M-6 (Major). Owner point G records an adoption that LR-023 says to refuse

**Claim.** §6.3: a claim-use adoption with open `open_review_finding` qualifiers is recorded with
`w5_consequence: blocked_until_qualifiers_discharged`. The note says this "refuses too much, never too little".

**Evidence.** Annex LR-023: "the intended successor use named; **no blocking qualifier for that use** (W9 §9 item 4)".
That is a precondition of the proposal, so a blocking qualifier refuses at LR-023. Under G, a `w9-use:claim-evidence` or
`manuscript-claims` proposal with an open finding passes LR-023 and runs the whole flow to Stephen's resolution.

**Failure scenario.** An adoption the accepted row forbids is reviewed and resolved by Stephen. Its admissibility is
"blocked", but it is recorded, and LR-039 can then count it under "adopted" unless §11.3's "active" check also reads the
consequence. The note's §11.3 row checks "active", not "not blocked".

**Required change.** At LR-023, refuse a claim-use or manuscript-use proposal whose qualifier set is non-empty. Keep
`qualifiers_to_discharge` equal to the observation's open findings for a task-input use. `w5_consequence` then has one
value for recorded claim uses. If Stephen prefers G as written, put it to him as a reading that amends LR-023.

**Affects:** owner point G; §6.3, §6.4, §11.3.

### M-7 (Major). Owner point F refuses too little: two of the three uses name no target

**Claim.** §6.2: three fixed `description` values. `w9-use:claim-evidence` has `successor_ref: null`.
`w9-use:task-input` may have `successor_ref: null`. The note calls this "narrower than the schema".

**Evidence.** W9 §9 item 2 binds "the intended successor use (for example 'input to T1.41 successor Task' or 'evidence
for claim candidate X')", and item 4 makes the family "admissible to W5 for the named use only". With a null target,
one claim-evidence adoption is admissible for every claim, and one task-input adoption for every Task. The note's own
reason for nulls (W9-T8 requires the adoption to exist before the Task) needs a target other than a `tsk_` ref, not no
target.

**Required change.** Parameterize the two values: `w9-use:task-input/<pre-registration ID or plan task key>` and
`w9-use:claim-evidence/<claim candidate key>`. `family_admissible` then compares the full string. If Stephen accepts
the generic values, record that this widens W9 §9 item 2.

**Affects:** owner point F; §6.2, §9 `family_admissible`.

### M-8 (Major). Discharge's G3 check is placed in replay, but replay has no input for it

**Claim.** §8, LR-031 to LR-033, replay: "the reviewer is not the result's producer (G3), by the actor the proposal
recorded". LR-030, preparer only: "the result's producer is read from the generic projection".

**Evidence.** The discharge record has no producer field (`legacy-discharge-relation.schema.json`; probe
`test_defect_citation_status_carries_no_ref_to_inventory_mapping_or_transition`). The legacy proposal state stores the
proposer's `actor_id` only (`reducers.py:727-736`). Replay's context carries five keys and no artefact state
(`replay/driver.py:199-205`; probe `test_replay_context_carries_no_generic_artefact_state`).

**Failure scenario.** An implementer has no replay input for the check and quietly drops it, or checks the proposer
instead of the producer. G3 then holds only at the preparer, and a forged ledger with the producer as reviewer replays
clean.

**Required change.** Either pass the generic artefact manifests up to the transaction's position into replay's context
and check `manifest.producer_actor_id`, or place G3 for discharge at the preparer only and record that limit in §16.

**Affects:** §8, §15 (LR-034's negatives), §16.

### M-9 (Major). The citation status's "never the transition's producer" cannot be checked at LR-039 and is not checked later

**Claim.** §11.3, replay at LR-039: "the submitter is not the root's creator, the mapping's analyst or the inventory's
observer (the 'transition's producer')".

**Evidence.** The citation status carries `root_ref` and `supersedes_status_ref` only (probe above). §11.2 orders
LR-044, then LR-039, then LR-050 to LR-054. The mapping's place relative to LR-039 is unstated, and the transition
(LR-050) does not exist yet at LR-039. A root may have more than one inventory or mapping over time. The ownership record
names no citation status.

**Failure scenario.** The analyst who later proposes the transition (LR-050) is the same actor who recorded the
citation status. Nothing refuses it, against W9 §12.1 ("never by the transition's producer").

**Required change.** Check at LR-054 that the current citation status's `derivation.reviewer_actor_id` and submitting
actor are neither the ownership proposal's creator, nor the mapping's analyst, nor the inventory's observer named by
that mapping. At LR-039, define "the root's mapping and inventory" (current, not superseded) or drop those two limbs.

**Affects:** §11.3, §10.4, §15 (W9-T17); W9-C20.

### M-10 (Major). LR-054 does not bind the subject registration to the root it transitions

**Claim.** §10.4, LR-054: the subject registration's role is `legacy_manuscript_root`; `mapping_ref` and
`paper_root_ref` are set; the mapping's target is that root.

**Evidence.** The paper root carries `manuscript_root_path` and no registration ref. The inventory carries
`root_registration_ref` (schemas). No listed check ties the ownership record's `subject_registration_ref` to the
mapping's inventory's `root_registration_ref`, or its `normalized_path` to the root's `manuscript_root_path`.

**Failure scenario.** A P01-A mapping and root are used to transition the P01-B root registration. Every listed check
passes.

**Required change.** Add to LR-054 (replay): `subject_registration_ref.id` equals the mapping's inventory's
`root_registration_ref.id`, and that registration's `normalized_path` equals the root's `manuscript_root_path`. Add the
cross-root case to §15.

**Affects:** §10.4, §15 (W9-T17, W9-T21).

### M-11 (Major). The W9-T8 CreateTask guard is orphaned. 06v gives it to WP9.4, and WP9.7's list does not include it. This is a missing owner point

**Claim.** §4.1: "WP9.7's CreateTask guard is the reader (06v §2.7, W9-T8). WP9.4 writes no successor-side code for it."

**Evidence.** 06v WP9.4, "Successor-side refusals (resolve U-5 and U-6 first): The CreateTask guard (§2.7) refuses a
Task whose `source_import_refs` reference an unadopted family (W9-T8)" (`06v-w9-implementation-plan.md:463-465`). 06v
WP9.7 lists the family-coverage guard, the RegisterArtefact guard, the use-time re-hash and the metric helper, not the
CreateTask guard (`:523-557`). 06v §2.7 names the module (`service.py:6019`) but no package. P-085's boundary is "WP9.4's
code under `research_system/legacy/`", so the guard is outside it, and §18's stop rule says so.

**Failure scenario.** Neither package builds the guard. A successor Task names `w9-adoption:<id>` for an unadopted or
suspended family, or names a legacy observation directly, and nothing refuses it.

**Required change.** Add an owner point: move the CreateTask guard to WP9.7 by a recorded decision (with a W9-T8
successor-side binding test there), or widen P-085's boundary for it. Until then, §15's "W9-T8, legacy side" is half of
the test 06v assigns to WP9.4.

**Affects:** §4.1, §15, §19; 06v WP9.4 and WP9.7; P-085.

### M-12 (Major). Owner point B moves two rows the WP9.3 Decision checks cannot carry, and the note does not specify their encoding

**Claim.** §2.2: LR-024 and LR-025 "use `ProposeW9AuthorityDecision` and `ResolveW9AuthorityDecision`, which are bound
already, so the move adds no census row". §6.4 gives their checks.

**Evidence.**
- `_check_decision_proposal` requires exactly three `governing_evidence_refs`, `decision_kind: migration_authority`, and
  a pre-assigned Decision ID read from a record field (`reducers.py:938-962`). LR-024's subject adds a session and its
  model family and version, role profile and context grade (annex LR-024; P-073 item 3). Its "pre-assigned dec_ ID" has
  no field in the adoption record, whose only `dec_` is the adoption Decision.
- LR-025 writes no record (annex `ordered_events`: `W2:DecisionResolved` only). `_check_resolution` reads
  `transaction[1]` and fails with `IndexError` on a one-event transaction. Probe
  `test_defect_eligibility_resolution_has_no_record_event_for_the_generic_g5_check`.
- LR-027 needs `reviewer_profile` to equal the eligibility Decision's role profile (annex LR-027). WP9.3's
  `_check_verdict` fixes `reviewer_profile` to the constant `w9-independent-reviewer` (`reducers.py:884`), and §5.1
  calls verdict handling "reused unchanged".
- The note's LR-024 preparer check ("the session differs from the analyst's and from the observer's") is not the annex's
  (a) to (c), which Stephen checks (LR-025). The note does not say that (a) to (c) are human-only.

**Required change.** If B is taken, specify: the `governing_evidence_refs` encoding for LR-024 (each fact as a prefixed
string); the Decision kind; where its `dec_` comes from (a derived ID, as in M-2); a record-less resolution branch for
LR-025 with its own checks; how LR-027's profile check coexists with the fixed profile; and (a) to (c) in §16.

**Affects:** owner point B; §2.2, §5.1, §6.4, §16.

### M-13 (Major). Every file under a paper root ends `closed_reference`. The note weighs the root's half of this, not the files'. This is a missing owner point

**Claim.** §10.2: every inventory row's observation is a `whole_file` observation in a recorded closed-reference
acceptance, and it "names that path's registration". §10.2's "consequence the review should weigh" covers only the
root registration.

**Evidence.** An observation's source path must equal its registration's `normalized_path` (`reducers.py:484-491`). The
root registration's path is the directory (`legacy-path-registration.schema.json`, the `legacy_manuscript_root` rule).
So each of the 55 tracked files under the two roots needs its own registration, with some role from the closed enum.
None names a manuscript file. LR-020 closes each accepted whole-file observation's `legacy_owned` registration
(annex LR-020; P-072 item 2; `reducers.py:619-650`). After LR-054, the root registration is `successor_owned` and every
file in it is `closed_reference`. The batch rule allows one batch before the pilot Decision (`reducers.py:539-542`), so
55 files take at least three batches.

**Failure scenario.** WP9.7's guards refuse every successor write to a draft, because each draft file is a registered
legacy file in `closed_reference`. "Successor owned" then owns no writable file.

**Required change.** Add an owner point: which role the member files are registered under; whether their
`closed_reference` end state is intended; and how W9 §4.2's writer rule treats a `closed_reference` file under a
`successor_owned` root.

**Affects:** §10.2, §10.4, §19; W9 §8.2, §8.4; WP9.7's guard.

### m-1 (Minor). Several citations are off

- §5.1: "tested at eight sites". `row_id in WP9_3_ROWS` occurs at ten lines: 703, 719, 737, 847, 908, 991, 1025, 1138,
  1179 and 1387 (probe `test_defect_note_counts_eight_row_gate_sites_the_reducers_have_ten`). Line 737 (the acceptance
  ownership store) and 1387 (the observation check) matter for the `WP9_4_ROWS` widening. Say which sites widen and why
  the others do not.
- §2.3: the W2 event rows span `schema_registry.py:279-302`, not `:268-282`.
- §9: outside `research_system/legacy/`, the package is also imported by `command/service.py:640`,
  `command/t2.py:1197` and `discovery/routes.py:313`, `:332`, not only by the CLI, replay and the identity check.

### m-2 (Minor). §9's import-seam test fails on day one

"No command preparer outside the legacy package imports anything else from it." `service.py:640` and `t2.py:1197`
already import `legacy.identities`. Allowlist `identities` and `commands`, or the test fails before any WP9.4 code
exists.

### m-3 (Minor). §9 names a new `read.py` beside the existing `reader.py`

`research_system/legacy/reader.py` is WP9.3's observation reader. A second module named `read.py` invites the wrong
import. Name it, for example, `projection_read.py` or `interface.py`.

### m-4 (Minor). Claim 5 holds at the reader only. Replay would close a root registration

The reader refuses a non-regular file (`reader.py:168-169`), so no preparer-made observation names the root directory.
Replay does not check this: `derive_ownership` emits `legacy_owned → closed_reference` for a forged whole-file
observation of a `legacy_manuscript_root` registration (probe
`test_claim5_holds_only_at_the_reader_replay_would_close_a_root_registration`). Add a replay refusal: an observation of
a `legacy_manuscript_root` registration is refused at LR-015, or LR-020 never emits for that role.

### m-5 (Minor). §11.3 puts a preparer check in the replay column

"`families` is exactly the cited-family set" needs the extractor, which needs Git bytes. Replay can check only that
`cited_family_set_sha256` is the hash of `families`, and the adopted and unadopted rules. Move exact-set equality to the
preparer column, and say what `families` must equal when the two derivations differ.

### m-6 (Minor). U-10 and U-11 can be settled now. Neither invalidates the design

- **U-11.** A whole-file observation carries exactly one family, named `whole_file`, and that entry has `w0_class`
  (`reducers.py:1299-1302`; `legacy-observation.schema.json` `families`). §6.1's assumption holds. Record it and drop
  U-11.
- **U-10.** The one "accepted" artefact state is `use_authority: accepted_for_scope`, and reaching it requires a
  governing review and a `claim_promotion` Decision (`service.py:4618-4631`). So a discharge first needs the successor
  result promoted at claim level. That is a real cost, and the scope must cover the discharge. Record it now, with the
  scope check, instead of leaving it to the code PR.

### m-7 (Minor). Owner point H makes "scoped out" a file edit, without Stephen's attribution

"Treat 'scoped out' as Stephen removing the paper from the item's row." The file changes by PR, and W9 §12.1 says
"scoped out **by Stephen**". Require LR-054 to bind the file's blob, and require that blob to be named in Stephen's
resolving Decision (or accepted as D-9's list is), so that a PR edit alone cannot clear an A-001 item.

### m-8 (Minor). §16 omits two W9 §12.1 conditions and LR-024's (a) to (c)

W9 §12.1 also requires "the audit verdicts and the §6.2 HOLD are carried as qualifiers" and "for any rung-4/5 claim it
keeps, the A1 fork is decided and the calibration has run". Neither appears in §10.4 or §16. Add both to the
human-review list, with their question. See M-12 for (a) to (c).

### m-9 (Minor). LR-040's "registration live" has no check, and LR-044's W9-T17 binding has no control

§10.2 checks completeness, accepted observations and the window, but not "the root's registration live" (annex LR-040).
Define it (recorded, not superseded, `legacy_owned`). The annex binds W9-T17 at LR-044. §15's W9-T17 row names controls
at LR-039 and LR-054 only. Add one at LR-044, for example an inventory that omits a tracked file under the root.

### m-10 (Minor). P-085's boundary names `research_system/legacy/`. §13 and §18 add `cli.py`

WP9.3 had the same need, and Stephen extended P-080's boundary (WP9.3 note owner point J; P-081 item 10). Cite that
precedent and ask for the same extension, rather than assuming it.

### m-11 (Minor). Owner point C contradicts P-072 item 1's premise, not only the annex

P-072 item 1: "The proposed content already carries the pre-assigned `dec_` and `rev_` IDs, so no hash depends on
itself." LR-023's authority subject says the same ("its pre-assigned rev_ and dec_ IDs inside"). A derived ID is bound
through `record_id` and `created_at`, which the hash covers, so G5's intent holds. But the words "inside" and "the
record's review ref" are read, not met. Cite P-072 item 1, and put C to Stephen as a reading of both texts.

### m-12 (Minor). An adoption that is suspended at birth is refused only at LR-029

LR-023's replay checks do not include "the adoption would not be projected suspended". An adoption of an observation
that already has a later observation naming its family runs through review and Decision proposal, then fails at LR-029.
Apply §7's projection at LR-023 as well, as an ordering control.

### i-1 (Info). Claim 1 holds

No file under `research_system/command/` contains `source_import_refs`. Its only writer in `research_system/` is
`evals/executors/release_tranche.py:376`. It is not a creation field for the W9 identity check (`identities.py:152-173`).
Probe `test_claim1_holds_source_import_refs_unread_under_command`.

### i-2 (Info). Claim 3 holds, and the census is 273

An `E:` event is recorded under `ars://core/event` 1.0.0 with no binding lookup (`legacy/runtime.py:553-560`). The
runtime census is 273 rows. Probe `test_claim3_holds_e_event_needs_no_binding_row_and_census_is_273`. WP9.4-2's 275 is
plausible: its two commands emit `E:` events only.

### i-3 (Info). Citations checked and found right

`routes.py:446-456` and `:449-454`; `preparers.py:57-73`; `reducers.py:58-62`, `:79`, `:83-88`, `:90-102`,
`:1041-1055`, `:1062-1077`, `:1403-1414`; `records.py:111-143`; `service.py:6020-6075`; `create_task.schema.json:264-272`;
`artefacts/authority.py:32-37`, `:295`; `use_resolver.py:97`, `:310-317`; `assurance/models.py:13`;
`schema_registry.py:271-275`; `authority.py:208-252`. The WP9.2 note quote ("Any later move of a row …") is at
`wp9-2-design-note.md:191-192`. The 28-row count and the row list equal P-085 item 1.

### i-4 (Info). The `observations_by_registration` ordering is correct

With two observations of one registration, "later" is the list position after the adoption's observation. A later
observation naming the adopted family is found, and an earlier one is not (probe
`test_claim6_ordering_holds_a_later_observation_naming_the_family_is_after`). The defect in claim 6 is the selector
condition (M-1), not the order.

## 2. The §17 claims

| # | Claim | Disposition | Evidence |
|---|---|---|---|
| 1 | `source_import_refs` is read nowhere under `research_system/command/` | **Holds** | i-1 |
| 2 | No code path lets a claim take a legacy family as evidence | **Fails.** The artefact claim and manuscript path exists and admits legacy bytes today, and by copy after a path-only guard | B-1 |
| 3 | A W9 record event needs no runtime-binding row, so WP9.4-1 carries no D-4 | **Holds**, given owner point B's rows need no new command | i-2; M-12 |
| 4 | The adoption schema has no review field, and a derived ID satisfies G5 as the annex states it | **First half holds. Second half holds only as a reading** of LR-023, G5 and P-072 item 1, and only with a review-ID resolver the note does not specify | M-2, m-11 |
| 5 | A root's registration is never closed by LR-020 before LR-054 needs it `legacy_owned` | **Holds at the reader, not in replay**. Member files are closed, which the note does not weigh | m-4, M-13 |
| 6 | `observations_by_registration` gives "later" correctly for disjoint family sets | **Ordering holds; the rule built on it fails** on a stale observation | i-4, M-1 |
| 7 | The path-literal rule finds every result file the P01-A and P01-B drafts cite directly | **Fails.** Six uniquely resolvable basename citations and the JSON-escaped paths are missed | M-5 |

## 3. Consistency matrix (the parts the findings touch)

| Invariant | Source | Note's enforcement | Test | Gap |
|---|---|---|---|---|
| Review satisfied on the record's hash (G5) | annex G5 | §5.2 derived ID | LR-029 G5 | No slot in field-keyed tables; default fails open (M-2) |
| Analyst may request on own proposals | WP9.3 note §5.5 | "unchanged" | none | Unchanged refuses all four kinds (M-3) |
| Fixture refs in the resolving Decision | P-072 item 4 | human-only | none | Dropped (M-4) |
| No blocking qualifier at LR-023 | annex LR-023 | records "blocked" | §15 W9-T17 unit | Refuses too little (M-6) |
| Named use only | W9 §9 items 2, 4 | three fixed strings | W9-T17 unit | Two generic uses (M-7) |
| Stale observation suspends | P-081 O-33; §3 row 3 | §7 cause 1 | W9-T9 | Disjoint selectors escape (M-1) |
| Reviewer not the result's producer | annex LR-030; G3 | replay at LR-031 | LR-034 negatives | No replay input (M-8) |
| Citation set not by the transition's producer | W9 §12.1; annex LR-039 | LR-039 replay | W9-T17 | Not checkable then, never checked later (M-9) |
| The subject is the root the mapping targets | W9 §8.2 | role check only | W9-T17, T21 | No binding (M-10) |
| Unadopted family blocks its claims | W9-T17 last clause | predicate only | unit | Call site exists, unbound (B-1) |
| No successor use without adoption | W9-T8 | legacy side only | integration | Successor guard orphaned (M-11) |
| Drafts' cited set complete | W9-T17; D-3 | path literal | W9-T17 | Basenames, escapes, unregistered (M-5) |

## 4. Owner points: dispositions

| # | Needs Stephen? | Recommendation sound? | Alternative fair? | Disposition |
|---|---|---|---|---|
| A, the split | Yes (D-6; P-085 item 1) | **Yes.** One D-4, in the PR that cannot run before WP9.7 | Yes | Keep |
| B, LR-024 and LR-025 to WP9.4-1 | Yes (P-085 item 1) | **Yes in direction**, but the rows do not fit the WP9.3 checks | Yes | Keep, after M-12's specification |
| C, derive the adoption's review ID | Yes | **Yes**, it keeps the accepted bytes, but it needs M-2's resolver | Yes, but it omits P-072 item 1 | Keep, amended by M-2 and m-11 |
| D, LR-021 and LR-022 stay with WP9.7 | Yes | **Yes.** Matches P-073 item 4 | Yes | Keep |
| E, U-6 | Yes | **No.** The premise is false | The "hold WP9.4" alternative is not needed | **Rewrite** per B-1: bind to WP9.7's artefact guard, with a content rule |
| F, three fixed uses | Yes | **No.** Two values refuse too little | Partly: byte-for-byte comparison is not the only alternative | Amend per M-7 |
| G, qualifiers and consequence | Yes | **No.** It records adoptions LR-023 refuses | Yes | Amend per M-6 |
| H, the open-item list | Yes | **Mostly** | Yes | Keep, with m-7's attribution |
| I, the citation comparison | Yes | **No, as written.** Claim 7 fails | Narrowing to claim families is fairly deferred | Amend per M-5 |

**Missing owner points.**

| # | Point | Why it is Stephen's | Recommendation |
|---|---|---|---|
| J | Who builds the W9-T8 CreateTask guard | 06v assigns it to WP9.4; P-085's boundary excludes `service.py` (M-11) | Move it to WP9.7 by decision, with its binding test |
| K | The member files of a paper root: role, end state, and the writer rule under a `successor_owned` root | It reads P-072 item 2 and W9 §8.2 together (M-13) | Decide before WP9.4-2's code |
| L | Fixture refs in the resolving Decision, or a recorded departure from P-072 item 4 | An accepted decision (M-4) | Encode the refs, as LR-020 does |
| M | The `cli.py` boundary extension | P-085's boundary (m-10) | As P-081 item 10 |

## 5. Rows LR-023 to LR-055: preconditions placed

Each annex precondition has a place in the note, and G1 to G5 apply by scope, except as follows. Each item is placed
between replay and the preparer as the note says, unless marked.

- **LR-023:** "no blocking qualifier for that use": placed, but not refused (M-6).
- **LR-024, LR-025:** (a) to (c) are not placed as Stephen's (M-12). "Resolved before the adoption's review is requested"
  is placed at LR-026, correctly.
- **LR-026 to LR-028:** placed. The analyst rule needs M-3. LR-027's profile check conflicts with the fixed profile
  (M-12).
- **LR-029:** G5 placed (M-2). The suspension check is placed (M-1). The window is preparer-only, correctly. Fixtures:
  M-4.
- **LR-030:** `item_id` and "accepted, not only registered" are preparer-only, correctly (U-10, m-6). "Reviewer
  independent of the result's producer" is misplaced in replay (M-8).
- **LR-031 to LR-034:** placed, with M-8.
- **LR-035:** placed. It refuses until LR-022, correctly.
- **LR-039:** "never by the transition's producer" cannot be checked where placed (M-9). "Every adoption_ref active"
  is placed in replay. "Hashed and filed before the transition" is met by order.
- **LR-040:** "registration live" is missing (m-9). Completeness is split between preparer (Git) and replay
  (ordinals, observations), correctly.
- **LR-041 to LR-044:** placed. The window at LR-044 is preparer-only, correctly.
- **LR-045:** placed in replay, correctly.
- **LR-046 to LR-049:** placed.
- **LR-050:** the direction refusal is placed in replay, correctly (`reducers.py:1053-1054` already refuses it at LR-054
  and LR-055).
- **LR-051 to LR-053:** placed, with M-3.
- **LR-054:** placed, with M-9 and M-10. The non-machine conditions are listed as human-only, with m-8's omissions.
- **LR-055:** placed. "No further precondition" matches the annex.

## 6. Tests against W9 §17 and the annex's `binding_tests`

| Bound test | Rows | §15 control | Gap |
|---|---|---|---|
| W9-T1 | LR-029 | Yes | — |
| W9-T5 | LR-050, LR-054, LR-055 | Yes | — |
| W9-T6 | LR-029, LR-044, LR-054, LR-055 | Yes | — |
| W9-T8 | LR-029 | Legacy side only | Successor half orphaned (M-11) |
| W9-T9 | LR-029 | Yes | Add the disjoint-selector, new-blob case (M-1) |
| W9-T17 | LR-039, LR-044, LR-054 | LR-039, LR-054 | None at LR-044 (m-9); last clause unbound (B-1) |
| W9-T21 | LR-035, LR-044, LR-049, LR-054 | Graph half | Add the cross-root case (M-10) |
| W9-C11, W9-C20 to W9-C25 | every row | "per row" | W9-C20 at LR-025 (eligible session) needs M-12's branch |

## 7. What I did not check, and why

- **End-to-end runs on a scratch store.** No probe created a store. The copy route in B-1 is reasoned from the code, not
  run. Running it needs a bound `CommandService` and a promotion flow, which is WP9.7 review work.
- **The accepted catalogue JSON against the annex YAML** for WP9.4's rows. I read the annex only. WP9.3's reviews checked
  the catalogue's equality.
- **Whether the six basename-cited files are registered or will be.** No registration manifest exists yet. The probe
  uses tracked `results/` paths as the candidate set. Untracked (gitignored) results were not scanned.
- **P01-B's drafts beyond path and basename literals.** I found no basename-only citation there. I did not read the prose
  for indirect citations by table or figure.
- **The claim-trace artifact map**'s format. I did not read it.
- **The vault.** Not read and not written.

## 8. Revision plan

**Immediate corrections (revision 2):** B-1, M-1 to M-3, M-5, M-8 to M-10, M-12, and m-1 to m-12.

**Owner decisions:** A, D kept. B, C, H kept with amendments. E rewritten. F, G, I amended. J, K, L and M added. M-4
either becomes L or is fixed in the note. M-6 and M-7 can be fixed in the note or put to Stephen as readings that widen
an accepted text.

**Later-work dependencies:** WP9.7's artefact guard with a content rule and `family_admissible` (B-1); the CreateTask
guard (J); WP9.6 and WP9.7 binding tests for causes 2 and 3 of §7 (as the note says).

**Residual risks:** the single model family; session and producer independence rest on attested strings; the
extractor's set and the reviewer's derivation may still differ on indirect citations after M-5.

## 9. Probes, commits and process

- **Probes.** `wp9-4-design-note-review-artifacts/test_review_wp9_4_note_probes.py`, SHA-256
  `0ce246c5be99822b5ca770089830155f358c5dac5fa0079dbb608bc74c7c69a1`. Run from the repository root:

  ```bash
  uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider docs/plans/agentic-research-system/reviews/wp9-4-design-note-review-artifacts/
  ```

  Result: **20 passed, 0 failed** (8.8 s). Nine are `test_defect_` probes, each passing because its defect is present.
  The first run had 2 failures, both bugs in the probe file rather than findings: a list shared between the forged
  Decision and its resolution, and a regex that missed the digit in `w11_genesis_seen`. Both were fixed and the file
  re-ran. `ruff check` and `ruff format` are clean on the file.
- **The contract gate blocked the commit.** This clone had `core.hooksPath` unset. My first commit of the probes went in
  without the gate, so I undid it (unpushed, `git reset --soft`), ran `install-git-hooks.py --install`, and committed
  again. The gate then failed on two tests outside this change, and both fail the same way with my files stashed:
  - `tests/provenance/test_input_provenance_manifests.py::test_active_input_provenance_manifests_match_disk`:
    "enforced manifest b9-om-gmm-inputs failed against disk: ['missing on disk (proj_root):
    results/trajectory_tda_integration/01_trajectories_sequences.json']";
  - `tests/discovery/test_mcbif_employment_contract.py::test_mcbif_employment_result_contract_rejects_invalid_payloads`:
    `FileNotFoundError` for the same file.

  That file is gitignored data this cloud container does not have. Under the brief, I stopped and reported it. Stephen
  then told me, in chat on 2026-11-16, to commit around the gate. The report and the probes were committed with
  `--no-verify` as `7f3f93d` on `review/w9-wp9-4-note` and pushed, and this correction was committed the same way.
  `ruff check` was run by hand on the probe file and is clean. The contract gate should be re-run on a checkout that
  has the data file.
- **No store, no vault, no `.apm/`, no `results/`** was written. `papers/` was read through Git only.
