# WP9.4 design note re-review at `4629d1fd`: revision 2

**Date:** 2026-11-16<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md`, revision 2, at `4629d1fd`
(`4629d1fd34b33b9c2b02e898225313f335a32ed6`) on `claude/confident-volta-0e5dvm`, PR #437. `git rev-parse` of the
fetched branch head gave that commit. `git diff --stat 3c10de9a 4629d1fd` shows one file, the note (+671/-275).
`git diff --stat 4312dc63 4629d1fd -- research_system .research-system tools tests` is empty, so every code citation
reads the same at the note's base and at its head. The probe file asserts both diffs.<br>
**First review:** `reviews/wp9-4-design-note-review-3c10de9a-2026-11-16.md` and its probes, read from
`origin/review/w9-wp9-4-note` at `a9935c0b` (not merged).<br>
**Reviewer:** a fresh session. It wrote none of WP9.2, WP9.3, this note or the first review, and it did not read the
author's or the first reviewer's transcript.<br>
**Mode:** `adversarial-design-review` (remediation re-review, then a fresh attack on revision 2), with
`research-assurance-triage` for §16. Every `path:line` the note cites was re-read at `4629d1fd`; the ones that matter to a
finding are quoted below.<br>
**Branch:** `review/w9-wp9-4-note-re-review`, cut from `4629d1fd`. Only this report and the probe file are added.<br>
**Known limit (P-058):** the author, the first reviewer and this reviewer are one model family. Recorded as a limit, not
a finding.

## Verdict

**Return for revision 3.**

Revision 2 is a real repair. Twenty-five of the thirty first-round findings are closed, the five qualified or partly
fixed ones are narrow, and the three author qualifications hold. The claim path now exists in the note, the stale rule
suspends the first review's case, `review_id_for` leaves no fail-open read, and the fixture encoding passes row
assignment and the resolution rewrite unchanged.

It goes back because Stephen would still decide six owner points on a premise that the code or an accepted text
contradicts, and because one owner point is missing:
- **E** rests on "accepted_for_scope needs a claim_promotion Decision". The scratch-store run shows a byte copy of a
  legacy result promoted for manuscript evidence with no Decision at all (R-M1). The content rule also leaves WP9.4's own
  discharge path open (R-M2), and it matches recorded bytes only (R-M3).
- **I** cannot record either real root: run on P01-A and P01-B, the §11.1 rule yields 36 and 28 blocker entries, most
  of them directories and filename templates that no registration can ever clear, and the cited set depends on a
  tokenizer the note does not define (R-M6).
- **K** says "either way K needs an accepted text to change". W9 §3.1 and the source-inventory schema support a reading
  that needs none, and the note's own m-4 fix forecloses it (R-M7).
- **L** lets the producer choose fixture applicability after the review, which W9 §12.3 forbids, and P-084 i-3 does
  not carry over (R-M5).
- **B**'s encoding binds no eligible session at the verdict, and `review_id_for` at the generic Decision check refuses
  LR-024 before its review can exist (R-M4).
- **F**'s task-input key names nothing a Task carries, so J's "wrong-use" test cannot be built (R-M9).
- **Missing:** G4 for WP9.4's rows. P-081 item 12 reads G4 for four WP9.3 rows only, and LR-039 has no review or
  Decision to bind its hash later (R-M8).

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | — |
| Major | 9 | R-M1 to R-M9 |
| Minor | 5 | R-m1 to R-m5 |
| Info | 4 | R-i1 to R-i4 |

Every change asked for is local to the note, and WP9.4-1's code can start once B, E, F, L and the G4 point are settled.
I, K and R-m1 to R-m3 touch WP9.4-2 only, so they could be carried to that PR's note instead, if Stephen prefers
(revision plan).

## Research-assurance triage (§16)

- **Stage.** A design note under re-review. Design and dispatch scrutiny, not acceptance of any result.
- **Lanes.** `output_provenance` (every row) and `paper_claim` (LR-039, LR-054, §9's predicate, and E's content rule).
  The note's §16 says the same. I agree that no topology, null-model, statistical or representation logic is touched.
- **Governing records.** The annex rows LR-021 to LR-055 and LR-061 with G1 to G5 and `suspension_rule`; the W9 record
  schemas; W9 §§3.1, 4.2, 4.5, 5.2, 8, 9, 12.1, 12.3; 06v §2.7, §2.8, WP9.4, WP9.7, §4; P-072, P-073, P-081 (items 10
  and 12, the O-33 addition), P-084 (i-3), P-085.
- **Machine-checkable claims, and what checks them here.** §17's twelve claims, each probed below except claim 11,
  which needs code that does not exist. The extractor rule was run on the real roots through Git.
- **Human-review-only claims.** The §16 table is sound as far as it goes. Two rows are missing: the choice of fixture
  applicability (R-M5) and the open-item `feeds_papers` check on a replayed ledger (R-m1). The "use keys" row should
  also name the Task-side carrier once R-M9 fixes it.
- **Software tests are not sufficient.** The scratch-store run is the important case: every probe step passed, and the
  passes are the defect (R-M1, R-M2).

## 1. Closure of the first-round findings

Each disposition is bound to the note's text at `4629d1fd` and, where a check exists, to code or a probe. "Closed" means
the change is real, complete and not contradicted elsewhere in the note. New defects found in a fixed area are new
findings, cross-referenced.

| Finding | Note's disposition | Re-review | Evidence |
|---|---|---|---|
| B-1 | Fixed | **Partly closed.** The false premise ("no path") is gone: §4.2 states the path, cites `service.py:4409-4440` and `:4618-4631`, and binds WP9.7 with a content rule and a test. But §4.2 describes the path as needing "a governing review and a `claim_promotion` Decision", which is true for the claim predicate only. A manuscript promotion needs no Decision (R-M1), so E is again put to Stephen on a partly false description of the path | probe `test_claim12_defect_manuscript_promotion_needs_no_claim_promotion_decision`; `service.py:4901-4902` |
| M-1 | Fixed | **Closed.** §7's third bullet suspends on `stale_observations`; §15's W9-T9 control lists the disjoint-family, new-blob case | `test_claim3_holds_the_first_reviews_case_now_suspends`. Residual on unobserved edits: R-M3 |
| M-2 | Fixed | **Closed.** One resolver, "Any other kind raises", every read site listed, a negative control in §15. New interaction with LR-024: R-M4 | `test_claim4_holds_every_read_of_the_two_tables_is_a_listed_site` |
| M-3 | Fixed | **Closed.** Four kinds exempt; `_creator_role_actor` gains the inventory's observer. Matches annex LR-040 (`eligible_actor: observer`) | annex rows LR-023, LR-030, LR-040, LR-045, LR-050 |
| M-4 | Raised as L, with an encoding. *Qualified* | **Closed as a disposition; the qualification holds.** LR-020 carries `pilot_promotion` in its record items (`reducers.py:575-596`), which is P-072 item 4's second route. L's encoding has its own defects (R-M5) | `03-decisions-and-open-questions.md:4618-4620` |
| M-5 | Fixed | **Partly closed.** Escapes, basenames, blocker entries for ambiguous and `results/` tokens, scope, executable routes and the 06v departure are all stated. "Nothing is dropped silently" fails for a bare basename no registered result has, and the rule's "token" is undefined; on the real roots the rule blocks both papers (R-M6) | `test_claim5_*` probes |
| M-6 | Fixed, kept as G | **Closed.** §6.3 refuses a claim use with an open finding at LR-023 | §6.3, §6.5 LR-023 row |
| M-7 | Fixed, kept as F | **Partly closed.** Both uses now name a target. The task-input key is an attested string that no Task field carries, so the guard that consumes it cannot compare it (R-M9) | `test_owner_point_f_defect_a_task_carries_no_field_named_for_the_use_key` |
| M-8 | Fixed | **Closed.** G3 for a discharge is at the preparer, and §16 records that a forged ledger replays clean | §8, §16 |
| M-9 | Fixed | **Closed.** §11.3's last row checks the status's reviewer and submitter against the ownership proposal's creator, the mapping's analyst and the inventory's observer, at LR-054 | §11.3 |
| M-10 | Fixed | **Closed.** §10.5 binds `subject_registration_ref.id` to the mapping's inventory's root and its path to the root's path | §10.5, §15 W9-T21 row. Supersession gap: R-m3 |
| M-11 | Raised as J. *Qualified* | **Closed; the qualification holds.** 06v §4 does assign the guard to "WP9.7 (CreateTask guard)" (`06v-w9-implementation-plan.md:231`), and WP9.7's own list (`:523-557`) omits it | — |
| M-12 | Fixed | **Partly closed.** Derived ID, eight refs, the kind, a record-less LR-025 branch and the human-only limbs are all given. The verdict's session is bound to nothing, the request has no field for the session, `review_id_for` refuses LR-024, and the preparer has no payload for any of the new refs (R-M4) | `test_claim8_*` probes |
| M-13 | Raised as K. *Qualified* | **Closed as an owner point; the qualification holds in substance, with a wording fix (R-i3).** Annex LR-016 does require LR-022 for a later batch, and the WP9.3 note §2.1 says so. The code refuses every later batch unconditionally (`reducers.py:542`), so "already need LR-022" describes the annex, not a branch that exists. K itself misses a reading (R-M7) | `test_m13_qualification_defect_the_second_batch_is_refused_unconditionally_not_after_lr022` |
| m-1 | Fixed | **Closed.** Ten sites (re-derived), W2 rows at `schema_registry.py:279-302`, the four extra imports | `test_claim6_the_ten_gate_sites_are_where_section_5_1_says`; `service.py:640`, `t2.py:1197`, `discovery/routes.py:313`, `:332` |
| m-2 | Fixed | **Closed.** The seam test allowlists the existing imports by module and importer | §9 |
| m-3 | Fixed | **Closed.** `projection_read.py` | §9 |
| m-4 | Fixed | **Closed as asked, but it now conflicts with a reading of K** (R-M7) | §10.2 |
| m-5 | Fixed | **Closed.** Exact-set equality is in the preparer column | §11.3 |
| m-6 | Fixed | **Partly closed.** U-11 is settled correctly (`reducers.py:1299-1302`). U-10's reading is wrong: only the claim predicate needs a `claim_promotion` Decision (R-M1), so "a discharge needs its successor result promoted at claim level first" overstates the cost | `service.py:4901-4902` |
| m-7 | Fixed | **Closed.** The open-items blob travels in the Decision proposal and is checked at the preparer. The `feeds_papers` check is mis-placed in replay (R-m1) | §8 |
| m-8 | Fixed | **Closed.** The two W9 §12.1 conditions and LR-024's (a) to (c) are in §16 | §16 |
| m-9 | Fixed | **Closed.** "Registration live" is defined; W9-T17 has a control at LR-044 | §10.3, §15 |
| m-10 | Raised as M | **Closed.** Cites P-081 item 10 (`03-decisions-and-open-questions.md:5167`, verified). See R-i4 on scope | §13 |
| m-11 | Fixed | **Closed.** Owner point C cites P-072 item 1 and is put as a reading | §5.2 |
| m-12 | Fixed | **Closed.** The projection is applied at LR-023 | §6.5, §7 |
| i-1 | Noted | **Closed.** Re-checked: `source_import_refs` appears in no file under `research_system/command/`; its only writer is `evals/executors/release_tranche.py:376` | probe `test_claim1_holds_…` of the first review, re-run |
| i-2 | Noted, runtime citation added | **Closed.** `legacy/runtime.py:553-560` records an `E:` event under `ars://core/event` 1.0.0 | — |
| i-3 | Noted | **Closed** | — |
| i-4 | Noted | **Closed** | — |

**Totals:** 25 closed, 5 partly closed (B-1, M-5, M-7, M-12, m-6), 0 open.

**The three qualifications.**
- **M-4:** holds. The first review's "as WP9.3 did for LR-020" reads as if LR-020 used the Decision; it uses the record.
- **M-11:** holds. 06v §4's table and 06v WP9.4's text disagree; revision 1 followed the table.
- **M-13:** holds in substance. The dependency on LR-022 is the annex's LR-016 precondition. The note should say the
  admitting branch does not exist yet and is the work of whichever package routes LR-022 (R-i3).

## 2. New findings

### R-M1 (Major). Claim 12 is false: `accepted_for_scope` needs a `claim_promotion` Decision only under the claim predicate. A byte copy of a legacy result reaches manuscript evidence with no Decision

**Claim.** §4.2: "`SetArtefactUseAuthority` to `accepted_for_scope` needs a governing review and a `claim_promotion`
Decision". §4.4 (U-10): "Reaching it needs a governing review and a `claim_promotion` Decision … So a discharge needs
its successor result promoted at claim level first. That is a real cost". §17 claim 12.

**Evidence.**
- `_claim_promotion_binding` returns the empty list whenever the use authority binds any predicate other than
  `claim_evidence` (`research_system/command/service.py:4901-4902`: `if … consumer_predicate != claim_reference:
  return []`). The manuscript predicate's `required_decision_kind` is `null` (the accepted contract,
  `ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load().predicate_for("manuscript_evidence")`).
- Probe `test_claim12_defect_manuscript_promotion_needs_no_claim_promotion_decision`, on a scratch store: a byte copy of
  fixture "legacy" bytes at `results/legacy_copy/escape_wilson_ci_2026-05-16.json` under the control root is registered,
  reviewed and set `accepted_for_scope` under the manuscript predicate, with no Decision. `resolve_for_manuscript`
  (consumer `rm03_brief_manuscript`) resolves it, and `decision_id` is `None`.
- One use authority binds one predicate, so a claim-promoted artefact is refused by `resolve_for_manuscript` for its
  predicate binding, never for its content (`test_claim1_one_use_authority_binds_one_consumer_predicate`).

**Failure scenario.** Stephen accepts E believing every legacy-copy promotion passes his `claim_promotion` Decision. A
successor registers a byte copy for manuscript evidence. Only a governing scientific review stands between the copy and
a manuscript consumer until WP9.7 lands, and WP9.7's binding test, as §4.2 words it, need not exercise the manuscript
route with no Decision.

**Impact.** Paper-claim validity; an owner point decided on an inaccurate description of the path. U-10's cost is also
overstated: a discharge's successor result can be accepted under any predicate with a review only.

**Required change.**
- §4.2 and §4.4: state that only the claim predicate binds a `claim_promotion` Decision; the manuscript, result and
  review predicates bind a governing review only (`service.py:4901-4902`). Correct §17 claim 12.
- WP9.7's inherited binding test: one artefact per consumer predicate, the manuscript one with no Decision.
- §8 (LR-030): say which predicate a discharge's successor result must be accepted under, or that any will do, and drop
  "promoted at claim level" as the stated cost.

**Affects:** owner point E; §4.2, §4.4, §8, §17 claims 1, 2 and 12; WP9.7's binding test.

### R-M2 (Major). The content rule sits only at `resolve_for_*`. WP9.4's own discharge reads `use_authority` directly, so a byte copy of a legacy result can discharge that result's own open item

**Claim.** §4.2, owner point E: the content rule runs "when `resolve_for_claim` or `resolve_for_manuscript` resolves
an artefact". §17 claim 2 asks whether `SetArtefactUseAuthority` needs it too.

**Evidence.**
- §8's LR-030 and LR-034 preparers check that "the successor result artefact's current `use_authority` is
  `accepted_for_scope`". That is a direct read of the projection, not a call to `resolve_for_*`.
- The scratch-store run shows the byte copy's replayed stream at `use_authority: accepted_for_scope` (probe above,
  last two asserts).
- Other production readers of `accepted_for_scope` outside the resolver exist: `discovery/spec.py:533`,
  `discovery/spec_result.py:248` (correction artefacts as decision sources) and `cli.py:2258` (release evidence).
  They are not legacy paths today, but they show the field is consumed directly.

**Failure scenario.** A successor registers a byte copy of the A-001 item's own legacy result, promotes it under any
predicate (R-M1), and proposes a discharge relation naming it. LR-030 and LR-034 pass. The legacy open item is
"discharged" by the legacy bytes themselves, and LR-054's "every open item … has a recorded discharge relation" then
passes for the paper.

**Answer to claim 2's question.** Use time is the right site for the consumers that go through the resolver, because
an adoption can suspend after registration, as §4.2 says. It is not the only site: harm can occur between
registration and use wherever `use_authority` is read directly, and the first such reader is in this package.

**Required change.**
- WP9.4-1's LR-030 and LR-034 preparers refuse a successor result whose SHA-256 or Git blob matches any recorded legacy
  observation (`legacy_content_matches`), whatever its adoption status. A discharge needs a new result. Add the control
  to §15's LR-034 row.
- Owner point E: state that WP9.4 binds the rule at its own discharge, and ask Stephen whether WP9.7 also applies it at
  `SetArtefactUseAuthority` (so that no legacy copy can enter `accepted_for_scope` unless an active adoption admits
  it), which closes the direct readers at once.

**Affects:** owner point E; §4.2, §8, §15, §16.

### R-M3 (Major). The content rule matches recorded bytes only. An edited or never-observed legacy file escapes it, and claim 3 holds only over recorded observations

**Claim.** §4.2: "content identity catches a byte copy. It does not catch a re-serialized or partly copied result."
§9: `legacy_content_matches` returns "every recorded observation whose source has that SHA-256 or that Git blob".
§17 claim 3: "no case leaves an adoption active on bytes that no longer exist".

**Evidence.**
- Replay marks an observation stale only when a later observation is recorded (`reducers.py:1404-1414`). Between a
  change to a registered file and its re-observation, the adoption projects active
  (`test_claim3_defect_a_source_edit_with_no_reobservation_leaves_the_adoption_active`). W9 §4.2 item 3 makes
  re-observation an obligation, detected by WP9.5's detectors, not a replay event.
- A byte copy of the file's current, unobserved bytes matches no recorded observation, so `legacy_content_matches`
  returns nothing and the use-time rule admits it. The same holds for any registered file that has never been observed.
- §9's `resolve_adoption_ref` returns the source's path, SHA-256 and length "for a whole-file subject" only. A family
  adoption hands its consumer no observed identity to re-check, and LR-061 is whole-file only (annex LR-061).

**Failure scenario.** A legacy result is edited under a §4.2(b) note and not yet re-observed. Its old family adoption
stays active, and a byte copy of the new bytes registered under the control root resolves for claim use, because no
observation records those bytes.

**Required change.**
- §4.2's known limit: say the rule matches recorded bytes only, and that an unobserved change escapes it.
- Recommend that WP9.7's content rule also compare against the current blob, at the binding's `git_head`, of every
  registered `git_tracked` legacy path (one `git ls-tree` per check), as the path rule (a) already covers the path.
- §9: `resolve_adoption_ref` returns the observed source identity (path, Git blob or SHA-256, length) for every
  adoption, and §4.3 says WP9.7's guard refuses a family-adopted input whose current bytes differ.
- §17 claim 3: restate as "over recorded observations".

**Affects:** owner point E; §4.2, §4.3, §7, §9, §17 claim 3.

### R-M4 (Major). §5.5's eligibility encoding binds no session at the verdict, refuses LR-024 through `review_id_for`, and has no command payload

**Claim.** §5.5 and §6.5: LR-026 "refuses unless that Decision is resolved `accept`, and the request names its
`w9-eligible-session:`"; LR-027's profile and model metadata equal the Decision's. §5.2: `review_id_for` replaces the
tables "in replay (`:797`, `:965-969`, …)", and "returns … the derived ID for an adoption". §17 claim 8.

**Evidence, against annex LR-024 to LR-027 and P-073 item 3.**
1. **The verdict's session.** P-073 item 3: "The review request must name that session (LR-026)." W9-C20: "a reviewer
   who … is not the eligible session is refused". Replay checks only that the verdict's `reviewer_session` differs from
   the sessions the request records (`reducers.py:893-895`). §5.5 adds a profile and metadata check at LR-027, and no
   session check. Probe `test_claim8_defect_the_verdict_session_is_bound_to_no_eligible_session` records a verdict from
   a session Stephen never named.
2. **Where the request names the session.** The request names its reviewer as an actor (`reviewer_capability`), and its
   `required_evidence_refs` are fixed at exactly the analyst's session for every row but LR-007
   (`reducers.py:744-755`). §5.1's table does not list `_session_refs`.
3. **LR-024 behind its own review.** LR-024 is a Decision proposal on the adoption proposal. If it runs through
   `_check_decision_proposal`, §5.2's `review_id_for` at `:965-969` requires the derived adoption review satisfied, and
   LR-026 cannot open that review until LR-025 resolves. Probe
   `test_claim8_defect_review_id_for_at_the_decision_proposal_refuses_lr024_before_its_review_can_exist`. §5.5 says the
   rows "fit none of WP9.3's Decision checks" but gives LR-024 no branch of its own, only LR-025.
4. **No payload.** `prepare_decision_proposal` takes exactly `subject_record_id`, `question`, `recommendation`,
   `consequences`, and maps a proposal kind to one Decision row (`preparers.py:457-466`). An adoption has two Decision
   rows (LR-024, LR-028), and the eligibility refs, the fixture entries (§5.4) and the open-items blob (§8) have no
   field to arrive in (`test_claim8_the_preparer_payloads_have_no_field_for_the_new_refs`).
5. **Metadata.** `reviewer_model_metadata` is one string (`review_verdict_recorded.schema.json`); §5.5 binds two values,
   family and version, without an encoding.

LR-024's "the adoption proposal current" and LR-025's "resolved before the adoption's review is requested" are met by
§5.5. (a) to (c) are correctly human-only.

**Failure scenario.** An implementer reuses `_check_decision_proposal` for LR-024 and finds it refuses every eligibility
proposal; or bypasses it and loses the subject-hash check. Separately, the eligible reviewer's colleague session records
the verdict, and replay accepts it.

**Required change.** In §5.5:
- the request carries `w9-eligible-session:<s>` as a second `required_evidence_refs` entry for LR-026, and
  `_session_refs` admits it for that row only;
- LR-027 requires the verdict's `reviewer_session` to equal it, and fixes `reviewer_model_metadata` as
  `<family>@<version>` (or another stated form);
- LR-024 has its own proposal branch: the generic fixed fields, the reservation, the stale-hash check, the eight refs,
  and **no** review requirement;
- the preparer payloads: name the new fields (`eligibility`, `fixture_refs`, `open_items_blob`) and the row
  discriminator for a kind with two Decision rows;
- say whether an eligibility proposal extends the adoption proposal's lapse, as `reducers.py:973-974` would.

**Affects:** owner point B; §5.1, §5.5, §6.5, §15 (W9-C20 at LR-027).

### R-M5 (Major). Owner point L lets the producer choose fixture applicability after the review. P-084 i-3 does not carry over, and F-019 at LR-029 is decidable

**Claim.** §5.4: fixture entries go in the Decision proposal's refs; "a conditional fixture that is listed counts as
applicable … That is the reading P-084 item 3 recorded for LR-020 (i-3)."

**Evidence.**
- W9 §12.3: "Per-item applicability is proposed by the item's independent reviewer and fixed by Stephen …, never by
  the item's producer." Annex LR-016 repeats it: "per-item pilot_promotion applicability proposed by the reviewer,
  never the producer".
- P-084 item 3, i-3: the listed-equals-applicable reading "is fixed when the reviewer approves the hash and Stephen
  resolves on it". It works for LR-020 because the list sits inside the acceptance record, whose hash the reviewer
  approves. WP9.4's five records have no fixture field (`test_owner_point_l_defect_decision_fixture_refs_are_outside_the_reviewed_hash`),
  so §5.4's entries are chosen at the Decision proposal (LR-028, LR-033, …) after the review, by `migration_analyst`,
  who §5.3 says is the proposal's own producer.
- LR-029's F-019 condition is "the intended use is evidence for a claim" (annex). §6.2's `w9-use:` string decides that
  exactly, yet §5.4 leaves F-019 optional for a claim use (`test_owner_point_l_defect_lr029_conditional_f019_is_decidable_from_the_record_yet_left_optional`).

The unconditional sets in §5.4 equal the annex's (claim 7, below).

**Failure scenario.** The analyst adopts a family for claim evidence and omits F-019 (result-to-claim overreach) from the
Decision proposal. Replay admits it, the reviewer never saw the list, and only Stephen's reading of the refs at LR-029
stands between the omission and the record.

**Required change.**
- Replay requires F-019 at LR-029 whenever the use is `w9-use:manuscript-claims/…` or `w9-use:claim-evidence/…`.
- For the other conditional fixtures, either bind the list to the reviewer (for example, the review request's
  `review_questions` carry the proposed list and LR-028's entries must equal it), or record that WP9.4 departs from W9
  §12.3 for these rows and put that departure in owner point L. "As P-084 i-3" should be removed as the justification.

**Affects:** owner point L; §5.4, §15 (fixture entries), §16.

### R-M6 (Major). Claim 5, run on the real roots: the §11.1 rule makes LR-039 unrecordable for both papers, depends on an undefined tokenizer, and still drops some names silently

**Claim.** §11.1: a candidate is "every token that ends in a registered result's basename, or that contains
`results/`"; an unresolved `results/` token is an `unregistered` blocker; "Nothing is dropped silently. A set with a
blocker entry cannot be recorded at LR-039." Scope: the whole root. §17 claim 5.

**Method.** The rule implemented as written, over every tracked file under `papers/P01-A-JRSSA/` (33 files) and
`papers/P01-B-JRSSB/` (22) read through Git at `4629d1fd`, with the 506 tracked files under `results/` as the
registration set. Every file in both roots decodes as UTF-8. Tokens are split on whitespace and on
`` ` ' " ( ) [ ] < > , ; | * ``, with trailing `.` and `:` stripped. Probes `test_claim5_*`.

**Results.**

| | P01-A | P01-B |
|---|---|---|
| cited files | 47 | 10 |
| `ambiguous` blocker entries | 4 (`04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json`, `05_analysis.json`, `stratified_markov1_W2_L5000_20260502.json`) | 2 (`04_nulls_wasserstein.json`, `04_nulls_wasserstein_w2_20260407.json`) |
| `unregistered` blocker entries | 36 | 28 |
| of which name no file (a directory, a stem or a template) | 29 | 28 |
| distinct blocker entries under `drafts/` only | 8: the 4 ambiguous names and 4 directory paths (in `compute_table1_effects.py` and `supplement-S0-null-specification.md`) | 2 directory paths (in `v1-2026-04.md`) |
| cited files under whitespace-only tokens | 17 | 1 |

Examples of `unregistered` entries that name no file: `results/`, `results/trajectory_tda_bhps/post_audit/`,
`results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_` (a filename template), and
`results/trajectory_tda_robustness/threshold_sensitivity/ph_thresh_{p50`. The real untracked results also appear, for
example `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_20260501.json`.

**Defects.**
1. **Permanent blockers.** Registration is per exact file (W9 §3.1), so a directory or a template can never be
   registered. Under §11.1 such a token blocks LR-039 until the file citing it is edited, which is a write to a
   registered legacy file that re-triggers observation, the inventory and the mapping (W9 §4.2 item 3). Even drafts-only
   scope leaves P01-B blocked by two directory paths in `v1-2026-04.md`.
2. **The tokenizer is undefined.** "Take every token" fits both a whitespace split and a punctuation-aware one. The
   first misses 30 of P01-A's 47 cited files and 9 of P01-B's 10, because backticks and Markdown table pipes stay
   attached. The extractor's hash, and so D-3's comparison, depends on a choice the note does not make.
3. **Silent drops remain.** A bare basename that no registered result has is never a candidate, for example
   `regime_labels.npy` in `notes/2026-05-01-reviewer-response-plan.md`
   (`test_claim5_defect_a_bare_untracked_result_name_is_dropped_silently`).
4. **Whole-file results never project.** The cited-family set uses membership tables only, and a cited file with no
   table is a blocker. P01-A cites `results/trajectory_tda_integration/embeddings.npy` and `embeddings_umap16.npy`,
   which §6.1 adopts whole. They block however they are adopted.
5. **Citation forms still missed:** a path composed in code from a directory string and a basename on the next line
   (`compute_table1_effects.py:22-53`) yields a directory token plus an ambiguous basename, not the cited file; a result
   cited by stem without its extension is never taken.

Unclassified candidates (a token ending in a registered basename that resolves to none of the three classes) did not
occur, so §11.1's three classes are exhaustive on these roots.

**Required change.** In §11.1 and owner point I:
- fix the tokenizer (the separators above, or a stated grammar);
- add a non-blocking `not_a_file` class for a `results/` token that is a directory in Git, ends in `/`, or has no file
  extension, reported to the reviewer and excluded from the hash;
- project a cited whole-file result as `(observation ID, "whole_file")`;
- treat a bare token with a result-like extension that no registered result has as an `unregistered` blocker, not a
  drop;
- state the cost on the real roots (the table above), and reconsider the scope (owner point I, §4 below).

**Affects:** owner point I; §11.1, §11.2, §15 (the extractor row); D-3.

### R-M7 (Major). Owner point K misses the reading W9 §3.1 gives, which needs no catalogue revision, and m-4's fix forecloses it

**Claim.** §10.2: "each tracked file under a root needs its own registration: 55 files"; "Either way K needs an
accepted text to change." §17 claim 10.

**Evidence.**
- W9 §3.1, Manuscripts row: "`papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/` as whole roots … A root is the one directory
  registration W9 allows. As in W11 §7.2, it authorizes no nested file its inventory does not list; the root's full-path
  inventory lists every file under it." The same section: "Registration is per exact file, never by glob".
- The source-inventory schema carries `root_registration_ref` on the record and, per row, `repository_path`,
  `git_blob` and `observation_ref`, with no per-row registration (`legacy-source-inventory.schema.json`, `rows`). That
  shape fits members listed by the root's inventory, not members registered one by one.
- The "one observation per registered path" rule is WP9.3's code (`reducers.py:485-491`), not an annex text: LR-015's
  preconditions name the registration manifest, the window, the membership table, the selector and the signature, not
  path equality (annex LR-015).
- P-072 item 2 closes a registration only for "an accepted observation whose selector covers the whole registered
  file". A member observation under a root registration does not cover the whole root.
- §10.2's m-4 fix refuses **every** observation of a `legacy_manuscript_root` registration at LR-015, which rules this
  reading out.

Claim 10 holds as stated (`test_claim10_holds_no_member_role_and_w9_reads_the_root_as_the_one_directory_registration`):
no accepted role fits a member file. What fails is the conclusion that K therefore needs a catalogue revision.

**The reading.** A member file is observed under the root's registration, its source path under the root's path, with
a `whole_file` selector over that member. LR-015's path rule admits a path under a root registration's directory. LR-020
never emits an ownership record for such an observation, because it does not cover the whole registration. The root
stays `legacy_owned` until LR-054, the members are listed by the inventory and never registered, and after LR-054 the
whole root is `successor_owned`. The writer-rule question disappears, because no member has a `closed_reference`
record. Its cost: three readings of WP9.3 row checks (LR-015's path rule, m-4's refusal narrowed to a non-member path,
`_whole_file` for a root registration), each a recorded reading like P-084's, and no new catalogue identity.

**Required change.** Put this reading to Stephen as K's first option, with its cost. Make m-4's LR-015 refusal
conditional on K: under this reading it refuses an observation of a root registration whose path is not a regular file
strictly under the root.

**Affects:** owner point K; §10.2, §10.3, §17 claim 10; m-4.

### R-M8 (Major). Missing owner point: G4 for WP9.4's rows

**Claim.** §6.5: "G1 to G5 and the flow checks of §5 apply to every row and are not repeated." The note says nothing
else about grants.

**Evidence.**
- A scoped grant names one subject kind and one exact ID and cannot carry a hash (WP9.3 note §5.3,
  `scoped-authority-grant-v2.1.0.schema.json:88-119` as cited there). WP9.3 therefore read G4 for its proposal rows as
  "the grant is exact on the pre-assigned record ID, and the content hash is bound later, by the review and the
  Decision". Stephen accepted that reading for LR-003, LR-006, LR-011 and LR-016 only (P-081 item 12).
- WP9.4 adds five proposal rows (LR-023, LR-030, LR-040, LR-045, LR-050) that need the same reading.
- LR-039 and LR-035 have no review and no Decision. LR-039's annex subject is "the root + the frozen cited-family set's
  hash + the reviewer's derivation", and nothing later binds that hash to Stephen's grant except the preparer's own
  extractor run. LR-035's is "the P01 key + its manuscript root path".
- LR-024's subject adds the session, its family and version, its profile and its grade.
- `LegacyRuntime._resolve_authority` hard-codes the subject kind and the target stream (WP9.3 note §5.3), and the two new
  commands need `_SCOPED_COMMAND_SUBJECT_KINDS` entries (`authority.py`); §14 says only "with their authority entries".

**Failure scenario.** WP9.4-1's code reads G4 as WP9.3 did, for five more rows, without an owner record; WP9.4-2 grants
LR-039 on the record ID alone, so Stephen's grant authorizes any cited-family set the reviewer submits.

**Required change.** A §5.6 on authority subjects: the subject kind and ID for each WP9.4 command, the extension of
P-081 item 12 to the five proposal rows, and for LR-035 and LR-039 what binds the hash half (for LR-039, the preparer's
extractor hash, with the grant issued after `ars legacy cited-families` prints it, or an owner reading that the grant
binds the record ID only). Add it as owner point N.

**Affects:** §5, §13, §14, §19; P-081 item 12.

### R-M9 (Major). Owner point F's task-input key names nothing a Task carries, so the W9-T8 guard cannot refuse "wrong use"

**Claim.** §6.2: `<key>` for a task input "is the successor Task's pre-registration ID or plan task key … nothing in
the store resolves them. `family_admissible` compares the whole `description`, so an adoption for one Task … admits no
other." §4.1, owner point J: WP9.7's binding test refuses a Task naming a "wrong-use adoption".

**Evidence.** The CreateTask `task_definition` has no field for a pre-registration ID, a plan task key or a use
(`create_task.schema.json`, `$defs.task_definition.properties`); `aliases` (`namespace`, `scope_id`, `value`) is the only
plausible carrier, and the note does not name it (`test_owner_point_f_defect_a_task_carries_no_field_named_for_the_use_key`).
`family_admissible(state, observation_id, family_name, use)` needs a `use` argument that the guard must derive from the
Task.

**Failure scenario.** An adoption for `w9-use:task-input/t1-41-prereg` exists. A different Task names it in
`source_import_refs`. The guard has no field from which to build `use`, so it either skips the use comparison or
compares nothing; the adoption is admissible to every Task that names it, which is M-7's defect moved to the guard.

**Required change.** Fix the carrier in §6.2 (for example, a Task alias in a reserved namespace `w9-use-key`, whose
value must equal `<key>`), and make J's binding test include a Task that names an adoption for another key.

**Affects:** owner points F and J; §4.1, §6.2, §9.

### R-m1 (Minor). The `feeds_papers` check at LR-054 is placed in replay, which cannot read the file

§10.5 lists "every open item whose `feeds_papers` names this paper has a recorded discharge relation" under "LR-054, in
replay". Replay sees only the `w9-open-items-blob:<sha1>` string; its context has five keys and no Git access
(`replay/driver.py:199-205`), and WP9.3 reads every outside input at the preparer (WP9.3 note §11.1). Move the check to
the preparer column and add a §16 row: a forged ledger with an undischarged item replays clean. This is M-8's pattern.

### R-m2 (Minor). §6.1 widens W9 §9 item 1's whole-file exception

§6.1 admits a whole-file adoption of "a `git_tracked` file with no accepted membership table". W9 §9 item 1 limits the
exception to "a binary or restricted input with no JSON family". A JSON result whose table was never accepted has a JSON
family but no table, and §6.1 would adopt it whole, skipping family-grained adoption. Say "a source with no JSON family
(not a `.json` file)", or record the widening as a reading.

### R-m3 (Minor). LR-054 does not require the mapping and the inventory to be current

§10.4 checks at LR-045 that the inventory is "recorded and not superseded". §10.5 checks at LR-054 only that "the mapping
is recorded". A mapping or inventory superseded between LR-049 and LR-054 (LR-056 to LR-060, WP9.6) would still carry
the transition. Add "neither superseded" at LR-054; it is testable on a forged ledger now.

### R-m4 (Minor). U-6's disposition does not record 06v's predicted site or the production callers

06v §2.7 put U-6's hook in `research_system/assurance/` ("likely `resolver.py`"). That package has no claim hook: only
`assurance/models.py:13` names the `paper_claim` lane. The production callers of the two resolvers are
`research_system/methods/brief.py:31-33` and `:57` (consumers `rm03_claim_assessment`, `rm03_brief_manuscript`,
`rm04_manuscript_pilot`). §4.2 should record both, and WP9.7's binding test should run through those consumer IDs.

### R-m5 (Minor). The artifact map is a committed file, and its scope bears on owner point I

§11.1: "the author has not read the map's format". The map is §3.2 of `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md`,
named as the source of the cited-family set at `04-parallel-specification-and-foundation-pilot-plan.md:186`. It is prose
with elided basenames (for example `` `…_2026-06-01.json` ``), so it is not machine-readable, which supports the note's
deferral. The audit covers `drafts/sections/` only (its Parts 1 and 2), which supports W9 §12.1's drafts scope.
Separately, `papers/P01-A-JRSSA/notes/claim-trace-escape-foo-2026-06.md` is a per-section claim trace inside the root;
under whole-root scope its 15 backing files enter the set. Cite all three (`test_owner_point_i_the_artifact_map_is_a_committed_prose_list`).

### R-i1 (Info). Claim 7 holds

Fixture and open-items entries after the three subject refs leave `w9_row_ref` and `assign_row` on the `W9:` row
(`routes.py:541-552`, `:603`); the resolution's rewrite (`reducers.py:1102`, `preparers.py:520`) carries them;
`w9-fixture:` is lower case and cannot read as a row ref; WP9.3's rows still refuse a fourth ref (`reducers.py:938`); the
W2 schemas' `uniqueItems` (`decision_proposed.schema.json`, `decision_resolved.schema.json`) is met because each entry
names a distinct fixture. The unconditional sets equal the annex's for LR-029, LR-034, LR-044, LR-049, LR-054 and LR-055
(`test_claim7_*`).

### R-i2 (Info). The O-33 citation

§3 row 3 cites "P-081 item 12 (O-33 addition)". The O-33 text is in P-081's "Added 2026-11-08" block after item 13;
item 12 is the G4 reading. The wording is inherited from P-085 item 3.

### R-i3 (Info). M-13's qualification, worded

"Batches after the first already need LR-022 (`replay/reducers.py:539-542`)" describes annex LR-016's precondition. The
code refuses every later batch whatever LR-022 says (`reducers.py:542`), and the admitting branch belongs to the package
that routes LR-022. Cite the WP9.3 note §2.1, which says so, and record it as WP9.7's carry.

### R-i4 (Info). Owner point M's scope

P-085's Boundary already covers "its runtime-binding rows", which are in `research_system/schema_registry.py`. M needs
`research_system/cli.py` and `research_system/authority.py` by name; listing `schema_registry.py` is harmless.

## 3. The §17 claims

| # | Claim | Disposition | Evidence |
|---|---|---|---|
| 1 | A legacy byte copy can be registered, promoted and resolved for claim, with no content check | **Holds.** Run end to end on a scratch store: register, governing review, the owner's `claim_promotion` Decision with its satisfied review, `SetArtefactUseAuthority`, then `resolve_for_claim` through the production consumer and the control-root content reader. No step reads the path for legacy status; the one content check is that the bytes equal the registered hash. `resolve_for_manuscript` resolves a second copy promoted under its own predicate | `test_claim1_defect_…`, `test_claim12_defect_…` |
| 2 | The use-time content rule suffices for byte copies; is use time the right site? | **Fails as stated.** Use time is right for resolver consumers. WP9.4's own discharge reads `use_authority` directly (R-M2), and the rule misses unobserved bytes (R-M3) | R-M2, R-M3 |
| 3 | The stale rule suspends the review's case; no adoption stays active on bytes that no longer exist | **First half holds; second half holds only over recorded observations** | `test_claim3_holds_…`, `test_claim3_defect_…`; R-M3 |
| 4 | Every read of the two tables is among the seven listed sites | **Holds.** Five reads (`reducers.py:797`, `:965`, `:1092`; `preparers.py:389`, `:512`) and their uses (`:966-969`, `:1093`, `:1118`; `:521`). No other place reads a missing review field as "none": `_DECISION_FIELDS.get(…, "decision_ref")` defaults a Decision field, not a review, and `REQUEST_ROWS.get` / `DECISION_ROWS.get` refuse. `PRE_ASSIGNED_REFS.get(kind, {})` (`reducers.py:365`, `:720`) skips the pre-assigned checks for an unlisted kind, which fails closed later at `_take_reservation`; §5.1 extends it. The resolver introduces the LR-024 interaction (R-M4) | `test_claim4_holds_…` |
| 5 | The extractor rule finds every cited result and reports every ambiguous or unregistered one | **Fails.** Results, blocker entries and missed forms in R-M6 | `test_claim5_*` |
| 6 | The six widened sites are right and the four others need no WP9.4 row | **Holds.** 737 stores LR-016's list; 1025 is LR-020's reservation; 1179 is LR-014; 1387 is LR-015, whose stale-list update (`:1404`) the §7 rule depends on and which stays WP9.3-gated. LR-035 and LR-039 go through `reduce_record` and need new checks, not a widened gate | `test_claim6_…` |
| 7 | Fixture entries break no WP9.3 check; the unconditional sets equal the annex's | **Holds** | R-i1 |
| 8 | §5.5 meets every LR-024 to LR-027 precondition replay can meet | **Fails.** Walk: LR-024 "proposal current" met; (a) to (c) human-only, correctly; LR-025 "before the review is requested" met; LR-026 "pre-assigned rev_ ID" met (derived), "independent of the producer and a distinct session" met by §5.3, "the named reviewer is the session Stephen's Decision names" not met (no field, R-M4 items 1-2); LR-027 "submitter is the named reviewer" met, "open on the current hash" met, "metadata and profile match" met for the profile, the metadata encoding unstated, and the session unchecked. LR-024 cannot pass the generic check under §5.2 (item 3) | `test_claim8_*` |
| 9 | F and G refuse too much only, never too little | **Fails for F; holds for G.** F's task-input key is unenforceable at the guard (R-M9). G refuses every open finding for a claim use, which W9 §9 item 4 permits; I found no case where G admits a blocking qualifier. Against annex LR-023, §6.1's whole-file test refuses too little (R-m2), and §5.4's optional F-019 does too (R-M5) | R-M9, R-m2, R-M5 |
| 10 | No member-file role exists, so K needs a revision or a reading | **First half holds; the conclusion does not** (R-M7) | `test_claim10_…` |
| 11 | LR-054's binding leaves no way to use another root's mapping | **Holds on reading** for the cross-root case: §10.4 ties the mapping's target to its inventory's root path, and §10.5 ties the subject to that inventory's root. **Not decided by probe**, because the check is not built. Supersession is open (R-m3) | §10.4, §10.5 |
| 12 | `accepted_for_scope` is the only accepted state and always needs a `claim_promotion` Decision | **Fails.** The first half holds; the second holds for the claim predicate only | R-M1 |

## 4. Owner points

| # | Needs Stephen? | Recommendation sound? | Alternative fair? | Disposition |
|---|---|---|---|---|
| A, the split | Yes (D-6; P-085 item 1) | Yes | Yes | **Agree** |
| B, LR-024 and LR-025 to WP9.4-1 | Yes (P-085 item 1: a row moves only by an owner decision) | Yes in direction; §5.5 is incomplete | Yes | **Agree after R-M4** |
| C, derive the review ID | Yes (a reading of P-072 item 1, LR-023, G5) | Yes | Yes | **Agree** |
| D, LR-021 and LR-022 stay | Yes | Yes | Yes | **Agree** |
| E, U-6 and the content rule | Yes | Structure sound; premise and coverage not (R-M1 to R-M3) | Yes | **Disagree as written** |
| F, the intended use | Yes | Mostly; the task-input key has no carrier | Yes | **Agree after R-M9** |
| G, qualifiers | Yes | Yes | Yes | **Agree** |
| H, the open-item list | Yes | Yes | Yes | **Agree after R-m1** |
| I, the citation comparison | Yes | No, on the real roots | Partly | **Disagree** |
| J, the CreateTask guard | Yes (moves work between packages) | Yes | Yes | **Agree, with R-M9's test** |
| K, member files | Yes | No: misses a reading | No: "either way … revision" is not so | **Disagree** |
| L, fixture refs | Yes | Presence yes; applicability no | The departure alternative is fair | **Disagree with the P-084 carry** |
| M, the boundary | Yes (P-085 Boundary) | Yes | Yes | **Agree** (R-i4) |

**On E (the WP9.4 and WP9.7 split, and the re-serialization limit).** WP9.4 building two read functions and WP9.7
binding them is the right shape for resolver consumers, and WP9.7 already edits the command service. But WP9.4 is
itself a consumer of `accepted_for_scope` at LR-030 and LR-034, so it must bind the content rule there (R-M2). The known
limit as worded ("re-serialized or partly copied") is accurate but incomplete: the rule also misses unobserved bytes,
and the manuscript route has no Decision (R-M1, R-M3). The alternative ("refuse every legacy-matching artefact") is
stated fairly, including its real cost.

**On K.** It is true that no accepted role fits a member file. It is not true that K therefore needs an accepted text
to change: W9 §3.1 says the root is the one directory registration and its inventory lists the members, and the
inventory schema has no per-row registration. That reading needs three recorded readings of WP9.3's row checks and no
catalogue revision (R-M7). I recommend it as K's first option. The note's "member role" option contradicts the plain
sense of W9 §3.1 and creates the writer-rule question it then has to answer.

**On L.** The encoding meets P-072 item 4's letter (refs travel in the resolving Decision) and the WP9.3 rows are
untouched. "A conditional fixture that is listed counts as applicable" is not a fair carry of P-084 i-3: there, the list
is inside the bytes the reviewer approved; here, the producer writes it after the review. That reverses W9 §12.3's "never
by the item's producer". I recommend either binding the list to the review or recording the departure, and requiring
F-019 for claim uses in replay (R-M5).

**On I (scope and blocked-until-cited).** The brief's order of authority puts W9 §12.1 ("every result family its
**drafts** cite") above 06v ("every file in the root's inventory"). The note follows the lower text. The audit that
supplies the artifact map is itself scoped to `drafts/sections/` (R-m5). On the real roots, whole-root scope gives 40
and 30 blocker entries, against 8 and 2 for drafts only, and most of the difference is directories and templates in
reviewer notes. I recommend drafts scope for the blocking set, with the extractor reporting the rest of the root to the reviewer
without blocking, plus R-M6's fixes; otherwise the cost of "blocked until cited" is that neither paper can record a
citation status without editing its legacy notes. The note's statement of that cost ("a real cost Stephen should know")
covers indirect citations only, not this.

**On J and M.** Both boundary questions are put correctly. J's alternative (widen P-085 to `service.py`) is fair and has
precedent (P-081 item 10, amended twice for `service.py`). J's binding test needs R-M9's carrier to test "wrong use". M is
correct; `schema_registry.py` is already inside P-085's "runtime-binding rows" (R-i4).

**Missing owner points.** N, G4 for WP9.4's rows (R-M8). Also, inside existing points: E should ask whether WP9.7 applies
the content rule at `SetArtefactUseAuthority` (R-M2); L should ask who proposes applicability (R-M5); I should ask drafts
or whole root against W9 §12.1, as a departure if whole root is kept (R-M6).

## 5. Consistency matrix (rows revision 2 changed or this review touched)

| Invariant | Source | Note's enforcement | Test (§15) | Gap |
|---|---|---|---|---|
| No legacy copy reaches claim or manuscript evidence unadopted | W9 §8.1; W9-T17 last clause | E: content rule at `resolve_for_*` (WP9.7) | WP9.7's inherited test | Manuscript needs no Decision (R-M1); discharge path (R-M2); unobserved bytes (R-M3) |
| Stale observation suspends | P-081 O-33 addition | §7 third bullet | W9-T9 incl. disjoint case | Unobserved edits (R-M3) |
| Eligible session reviews the adoption | P-073 item 3; W9-C20 | §5.5 | LR-024/025/027 row | No session binding; LR-024 path (R-M4) |
| Applicability by the reviewer, never the producer | W9 §12.3; annex LR-016 | §5.4 listed = applicable | fixture-entries row | Producer chooses after review (R-M5) |
| Cited set complete and reproducible | D-3; W9-T17 | §11.1 rule | extractor row | Tokenizer; permanent blockers; drops; whole-file (R-M6) |
| Root is the one directory registration | W9 §3.1 | §10.2 member registrations | — | Reading missed; m-4 forecloses it (R-M7) |
| Grant binds the exact subject | G4; P-081 item 12 | not addressed | — | Missing owner point (R-M8) |
| Named use only | W9 §9 items 2, 4 | §6.2 keyed uses | W9-T8 legacy half | Task-side key has no carrier (R-M9) |
| A-001 items discharged before transition | W9 §12.1 | §10.5 in replay | LR-034 negatives | Replay cannot read the file (R-m1) |

## 6. Probes

**File:** `wp9-4-design-note-re-review-artifacts/test_re_review_wp9_4_note_probes.py`, SHA-256
`dd16d9d340b8ba21f07baf2c112624d1f68d01f1f29a4b1f16c55c859c43ea3a`, unchanged by the pre-commit hook.

**Command**, from the worktree root at `4629d1fd`:

```bash
uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider docs/plans/agentic-research-system/reviews/wp9-4-design-note-re-review-artifacts/
```

**Result:** 28 passed, 0 failed (42.4 s). A probe whose name contains `defect` passes because the defect is present.
The scratch store is the test harness's `control_plane(tmp_path)` authority store; the "legacy" bytes are a fixture
literal, not a result file. The claim-5 probes read `papers/` and `results/` through `git show 4629d1fd:<path>` only.
The first run had one failure, a probe bug: the decision review needs the same review ID as the artefact's governing
review, as the accepted flow in `test_artefact_authority_commands.py:635-935` does, because `_claim_promotion_binding`
compares `considered_review_ids` with the governing set. Fixed and re-run. `ruff check` and `ruff format --check` are
clean on the file.

**The first review's probes, re-run.** Its file, read from `a9935c0b` (SHA-256 `0ce246c5…c69a1`, matching its §9), was
placed at its own path in this worktree, run, and removed; it is not committed here. Result: **20 passed, 0 failed**
(13.1 s). Its nine `test_defect_*` probes describe the code, which is unchanged, so all still pass. Whether revision 2
designs each defect out:

| Probe | Still passes | Designed out by revision 2? |
|---|---|---|
| `test_defect_claim2_register_artefact_admits_a_legacy_result_path_today` | Yes | Assigned, not designed out: WP9.7's guard and content rule (E), with R-M1 to R-M3 |
| `test_defect_wp9_3_g5_check_passes_an_adoption_with_no_review_at_all` | Yes | **Yes**: `review_id_for` raises for an unlisted kind and returns the derived review for an adoption (§5.2) |
| `test_defect_session_rule_refuses_the_analyst_on_every_analyst_proposed_wp9_4_kind` | Yes | **Yes**: §5.3's exempt set |
| `test_defect_eligibility_resolution_has_no_record_event_for_the_generic_g5_check` | Yes | **Yes**: LR-025's own branch (§5.5) |
| `test_defect_decision_proposal_admits_exactly_three_refs_so_no_fixture_or_eligibility_ref_fits` | Yes | **Yes for WP9.4's rows** (§5.4, §5.5); WP9.3's rows keep three, which the probe's LR-019 half still asserts |
| `test_defect_claim6_stale_observation_leaves_family_adoption_active_under_note_rule` | Yes | **Yes**: the probe models revision 1's rule; revision 2's rule suspends (`test_claim3_holds_…`) |
| `test_defect_claim7_basename_citations_in_p01a_drafts_are_missed` | Yes | **Yes**: unique basenames are cited files (§11.1) |
| `test_defect_claim7_json_escaped_windows_paths_are_not_read_as_paths` | Yes | **Yes**: JSON string values are decoded (§11.1 step 1) |
| `test_defect_note_counts_eight_row_gate_sites_the_reducers_have_ten` | Yes | **Yes**: §5.1 lists ten |
| `test_defect_citation_status_carries_no_ref_to_inventory_mapping_or_transition` | Yes | **Yes**: the check moves to LR-054 (§11.3) |

## 7. What I did not check, and why

- **The accepted catalogue JSON against the annex.** I read the annex only, as the first review did; the WP9.3 reviews
  check their equality.
- **Untracked results.** The claim-5 registration set is the 506 tracked files under `results/`. Gitignored results at
  `PROJ_ROOT` were not scanned, so the `unregistered` count would fall if some were registered as `untracked_file`; the
  directory and template entries would not.
- **Indirect citations** by table or figure in the drafts' prose. Not read.
- **Claim 11 by probe.** LR-054's checks are not built; checked by reading only.
- **The WP9.2 note §3, the stage B note, and the WP9.3 note §§3, 4, 7.2 and 16 in full.** I read the WP9.3 note §2.1,
  §5.3 and §11.1, and the WP9.2 note at the cited lines. The findings do not rest on the unread sections.
- **The vault.** Not read and not written. No store other than `tmp_path` scratch stores was opened.
- **Line-ending state of the canonical `main` tree.** `.gitattributes` sets `* text=auto eol=lf`, so a byte copy from a
  fresh checkout matches its blob; an old CRLF checkout could defeat a byte-exact content rule. Not measured.
- **The full test suite.** Not run; no code changed.

## 8. Revision plan

**Revision 3 (author), before Stephen decides:**
- WP9.4-1: R-M1, R-M2, R-M3 (E and §4); R-M4 (§5.5, B); R-M5 (§5.4, L); R-M8 (new §5.6 and owner point N); R-M9 (F and
  J); R-m4; R-i2.
- WP9.4-2, which can instead go to that PR's own note if Stephen prefers: R-M6 (§11.1, I); R-M7 (§10.2, K); R-m1;
  R-m2; R-m3; R-m5; R-i3.

**Owner decisions:** A, C, D, G, M as recommended. B after R-M4. E, F, I, K and L amended as above. J with R-M9's test.
N added.

**Later-work dependencies:** WP9.7: the content rule at `SetArtefactUseAuthority` if Stephen takes it, the current-blob
comparison (R-M3), the family-adoption re-check (R-M3), the manuscript-route binding test (R-M1), the CreateTask guard
with the key carrier (R-M9), and the later-batch branch at LR-016 (R-i3). WP9.6: LR-054's supersession check has a live
subject once supersession is routed (R-m3).

**Re-review:** a narrow confirmation of R-M1 to R-M9 against revision 3, re-running this file's `defect` probes against
the new design (most will keep passing until WP9.4's code exists, as the first review's do).

**Residual risks:** one model family; attested session and key strings; the extractor and the reviewer may still differ
on indirect citations; operator burden from more grants (WP9.3 note §5.3 already records it).

## 9. Commits and process

- `git config core.hooksPath` is `.githooks` in this worktree. The report and the probes were committed as `9cd60a9d`
  through the pre-commit gate, with no bypass: the pack-pin check (12 checked, 0 drifted), ruff, ruff format and the
  contract framework (104 contracts) passed. The two `results/trajectory_tda_integration/01_trajectories_sequences.json`
  tests the brief warned of did not fail here: this machine has the file at `PROJ_ROOT`. The hook left the probe file's
  bytes unchanged (SHA-256 `dd16d9d3…43ea3a`).
- No file under `papers/`, `results/`, `.apm/`, `research_system/`, `tests/`, the note, the register, the annex or any
  schema was edited. No ARS store was written.
- This review decides no owner point and accepts nothing.
