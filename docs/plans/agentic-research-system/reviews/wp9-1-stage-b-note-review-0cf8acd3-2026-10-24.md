# Review: WP9.1 stage B design note, revision 1 (`0cf8acd3`)

**Date:** 2026-10-24<br>
**Reviewer:** an independent session that did not author the note (adversarial-design-review skill).<br>
**Subject:** `transition/w9/wp9-1-stage-b-design-note.md`, revision 1, blob `0630ef99`, and register entry P-071 in
`03-decisions-and-open-questions.md` (blob `9c5aab43` at `0cf8acd3`). The diff `5d325c5b..0cf8acd3` is two commits
(`e15a55d1`, `0cf8acd3`) and touches only those two files.<br>
**Governing texts read:** W9 (`design/09-migration-compatibility-and-pilot.md`) §4–§9, §12–§14, §16–§17; 06v
(`implementation/06v-w9-implementation-plan.md`) §1–§8; P-005 and P-064 to P-071; stage A on main at `5d325c5b`
(the 17 `w9/*.schema.json` files, the bootstrap contract, `tools/w9_schema_gen.py`, the stage A note); the W11
catalogue (`w11-portfolio-discovery-v1.json`, blob `8d588185`), `tests/research_system/contracts/test_w11_expected_catalogue.py`
and `tools/verify_w11_materialization.py`; the Discovery and generic command code the note relies on.<br>
**Known limit (P-058).** Every review in this chain, this one included, runs on one model family. This is recorded
as a known limit, not as a finding.<br>
**Edits:** none to the subject. This file is the only file written.

## 1. Verdict

**`rework_required`.** 2 Blocking, 6 Major, 7 Minor, 5 Info.

The note derives one command per W9 §5.2 record and maps W11's 19 fields faithfully at the level of field names. Two
things stop the catalogue being written from it as it stands.

1. The derivation rule sends every review and Decision to "W2's existing decision and review commands". The generic
   `RequestReview` preparer cannot take a W9 record as its subject, and W11, the precedent the note follows, minted
   its own review and decision rows for this reason. The command set is therefore incomplete (B-1).
2. SB-Q2's per-item ownership event keys on a whole-file registration. Most of the light path, including the
   integration pilot's tracker rows and decision entries, is item-grained, so the first batch would close a whole
   file (B-2).

Both are fixable before materialization. Both amend owner decisions recorded in P-071, so each needs Stephen. The
Majors are missing preconditions, a verifier with no independent expected side, gaps in SB-Q3's triggers, and
sequencing problems in the deferral and in stage B's own identities.

## 2. Blocking findings

### B-1 (Blocking). Reviews and Decisions have no command route; the command set is incomplete

**Claim.** The note's derivation rule (note §1, lines 23–26) says reviews (`rev_`) and Decisions (`dec_`) are
recorded "through W2's existing decision and review commands", so no LR row records one. For reviews this does not
work against the code, and it departs from W11 without saying so.

**Evidence.**
- The generic `RequestReview` preparer requires each subject to be a **current replayed stream at its exact hash**:
  `research_system/command/service.py:3704-3720` (`streams.get(subject_id)` and the `stale_subject_hash` rejection,
  "RequestReview must bind each exact current replayed subject hash").
- A W9 record cannot be such a subject. Stage A's records **carry** their review and Decision refs as required
  fields: `reviewer_ref`/`review_ref`/`independent_review_ref` and `decision_ref`/`registration_decision_ref`/
  `acceptance_decision_ref` are required in the closed-reference acceptance, discharge, membership, ownership,
  source-inventory, mapping, supersession and registration schemas. So the review exists before the record it
  reviews. When the record does exist, it is replayed into the new `legacy` partition, which 06v WP9.2 (lines
  342–351) and U-7 keep out of the generic projection.
- W11 met the same problem by minting review and decision commands inside the Discovery path:
  `RequestW11AuthorityReview`, `RecordW11AuthorityReview`, `ProposeW11AuthorityDecision` and a Discovery
  `ResolveDecision` (`research_system/discovery/commands.py:14-44`; subject kinds at `discovery/runtime.py:209-236`).
  Its catalogue gives each a row: for example OR-103 to OR-108 for the assay bar, OR-122 to OR-127 for the legacy
  source inventory, and OR-128 to OR-133 for the mapping. There, `ResolveDecision` emits the acceptance event in the
  same transaction (`W2:DecisionResolved`, `E:legacy-transition-mapping-accepted`).
- The note's §2 table treats W11 as the precedent for the row shape. Its §1 drops W11's review and decision rows
  without citing a `path:line` showing that the generic path can serve them. APM_RULES ("verify before relying on
  it") requires that check.
- For Decisions the generic path is unverified, not refuted. `ProposeDecision` does not resolve a subject stream
  (`service.py:4119-4131`), and `decision_kind` includes `migration_authority`. Nothing shows that a W9 preparer on the
  separate Discovery-style append site (06v D-2) can read a generic Decision stream and check that it is resolved by
  Stephen, of the right kind, bound to this record's content, and whether its `permitted_commands` name the W9
  command.

**Failure scenario.** WP9.2 implements LR-006 to its catalogue row. At L-4 the analyst asks for the batch's
independent review through generic `RequestReview`, naming the observations as subjects. The preparer rejects it with
`stale_subject_hash`, because the observations are not generic streams. The batch cannot reach a `rev_` ID, so
`legacy-closed-reference-acceptance` (which requires `independent_review_ref`) can never be written. The same happens
for every Stephen-resolved row.

**Impact.** Operations and migration. The accepted catalogue would lack rows that WP9.2 must implement, and adding
them later means a new catalogue identity, a new acceptance and, under M-5, possibly a new store.

**Disposition.** Owner decision: amend P-071's statement that "the command set is the note's LR-001 to LR-014".

**Proposed change.** Pick one of these and state it in note §1:
- **(a), recommended.** Add W9-path review and decision rows on W11's pattern: `RequestW9AuthorityReview`,
  `RecordW9AuthorityReview`, `ProposeW9AuthorityDecision` and a W9 `ResolveDecision` (or W9-named equivalents), one
  variant row per record kind that needs them.
  - The review subject is a pre-assigned record ID plus the exact proposed content hash. The proposed content
    already carries the pre-assigned `dec_` and `rev_` IDs, so no hash depends on itself.
  - Every Stephen-resolved LR row then gains the precondition: "the named Decision is resolved, by Stephen, as a
    `migration_authority` Decision whose subject is this record's ID and exact content hash; the named review is
    satisfied on that same hash (S-007)".
- **(b).** Use the generic W2 commands. This needs a `path:line` proof that a generic review can bind a non-generic
  subject, and that W9 preparers can read and trust generic review and decision streams. Under the cited code, a
  change to the generic preparer would be required. That is a `core/commands` change under D-4, outside P-065.

**Affected.** P-071 (command set; derivation rule); 06v D-2 and WP9.2 (more commands, so more runtime-binding rows
and a larger D-4 census change); stage A schemas, if option (a) changes what the refs name; every LR row marked "/ S".

### B-2 (Blocking). SB-Q2's per-item ownership event is registration-grained; the light path is item-grained

**Claim.** P-071 item 2 has LR-006 emit "one `legacy_owned → closed_reference` ownership event per item". Stage A's
`legacy-ownership-transitioned` schema cannot express an item, so for item-grained observations the event moves the
whole file.

**Evidence.**
- `legacy-ownership-transitioned` requires `subject_registration_ref` (a path registration) and has no selector,
  observation or item field. Its other required fields are `mapping_ref`, `paper_root_ref`, `from_mode`, `to_mode`,
  `reviewer_ref` and `decision_ref`.
- W9 §8.4 (lines 455–466) makes tracker rows, Working Notes, task logs and legacy decision entries separate light-path
  items "by a §5.5 selector, under the file's light inventory".
- W9 §14.2 (line 698) puts "result files, decision entries, tracker rows" in the first batch.
- W9 §7.3 item 4 keeps successor writers adding entries to the Computational-Log for as long as it exists.
- W9 §13.3 item 5 and §4.5's "Whole-path cutover" row tie a file's whole-file state to a final observation, a
  bijection closure and writer revocation. P-071 item 4 defers those actions to a later catalogue revision.
- LR-013 still lists "Only W9 §8.2's three transitions", which include `legacy_owned → closed_reference`, with no
  closed-reference acceptance among its preconditions (note line 78).

**Failure scenario.** The integration pilot accepts tracker row T1.3 of `.apm/tracker.md`. LR-006 emits
`legacy_owned → closed_reference` for the tracker's registration, and the projection shows the whole tracker as
`closed_reference`, with every other row still unaccepted. That is a de facto file closure, which P-071 item 4
deferred. A second batch then accepts row T1.7, and its ownership event's `from_mode: legacy_owned` no longer matches
the projection. Either the reducer refuses the event, and the batch fails for a valid item, or it accepts a no-op
duplicate, and the reducer invariant ("Only the W9 §8.2 transitions") is weakened. The Computational-Log fares worse:
accepting one legacy entry would mark a file still written by successors as `closed_reference`. Separately, an
analyst can take any registration to `closed_reference` through LR-013 without LR-006's `pilot_promotion`,
threshold and anchor preconditions.

**Impact.** Authority and evidence. The projected ownership state would be wrong for every item-grained file, and
LR-013 offers a route around the batch controls.

**Disposition.** Owner decision: amend P-071 item 2.

**Proposed change.** Replace P-071 item 2 with this text:
> LR-006 emits `E:legacy-ownership-transitioned` (`legacy_owned → closed_reference`, null mapping and root, the
> batch's review and Decision) only for an accepted observation whose selector covers the whole registered file
> (`whole_file`, or the complete family set of the file's accepted membership table), and only when the
> registration's current mode is `legacy_owned`. An inventory-item observation never changes its registration's mode.
> Its `closed_reference` status is the acceptance itself, projected per item, and the file's mode changes only
> through the deferred file-closure command. LR-013 refuses `legacy_owned → closed_reference`.

The alternative is to widen `legacy-ownership-transitioned` with an item key. That is a stage A record-schema change,
outside P-071 item 1, which covers only the catalogue-content schema.

**Affected.** P-071 item 2; LR-006, LR-013; stage A's `legacy-ownership-transitioned` (only under the alternative);
WP9.2's reducer invariants; WP9.3's acceptance preparer.

## 3. Major findings

### M-1 (Major). SB-Q3 misses two of W9 §9 item 5's triggers, and the suspension event has no payload record

**Claim.** P-071 item 3 makes suspension an event of the causing command (LR-005, LR-014). That leaves three gaps.

**Evidence and gaps.**
1. **The trigger is narrowed.** LR-005 emits `E:legacy-adoption-suspended` "for each adoption whose source blob
   changed" (note line 70). W9 §9 item 5 (line 498) says "any re-observation of the source …, any new qualifier, or
   any supersession". Qualifiers are carried only on observations (W9 §6.4), so a new qualifier arrives as a
   re-observation with the bytes unchanged: a new `open_review_finding`, a `corrected_by` entry, or a re-observation
   of an enforcement state that a `shared_enforcement_surface` change triggered (W9 §4.3). Under LR-005's wording,
   none of these suspends. The "new qualifier" trigger is therefore not covered.
2. **The use-time mismatch has no emitter.** W9 §9 item 1 (lines 488–491) and O-34 say a mismatch at use suspends a
   whole-file adoption. That check runs in the successor Task path (WP9.7, U-9), in the generic command service.
   06v WP9.2 (lines 336–338) says "No other module appends" W9 events. So no row can emit this suspension.
3. **No payload record.** P-069 item 2 accepted "no event schemas" on condition that "WP9.2 validates each event's
   payload record through the schema registry". None of stage A's 13 record kinds is a suspension record (bootstrap
   contract `families.record`). `E:legacy-adoption-suspended` would be the only W9 event with nothing to validate, so
   the condition is vacuous for it.

**Failure scenario.** Review finding A1 is recorded against an adopted Markov-rung p-value family after its
adoption. The observer re-observes the file and the bytes are unchanged. LR-005 emits no suspension, so W5 still
admits the family for its named use with the new blocking qualifier unattached to the adoption.

**Impact.** Validity. An adoption survives a qualifier that W9 says must suspend it.

**Disposition.** Fix now (gap 1). Owner decision (gaps 2 and 3).

**Proposed change.**
- LR-005: "then `E:legacy-adoption-suspended` for every active adoption whose `observation_ref` names an observation
  of the same registration, on any re-observation, whether or not the blob changed (W9 §9 item 5)."
- For gaps 2 and 3, choose one:
  - **(a)** Suspension is a projection, not an event. An adoption is suspended when a later observation of its
    source, a supersession of a record it relies on, or a recorded use-time mismatch exists. Add one W9 row,
    `RecordAdoptionUseMismatch`, with a payload record (a 14th record kind, which is a stage A schema change), for
    WP9.7's guard to request. Drop `E:legacy-adoption-suspended`.
  - **(b)** Keep the event, add a `legacy-adoption-suspension` record kind as its payload, and add the
    use-mismatch row.

**Affected.** P-071 item 3; P-069 item 2; LR-005, LR-014; O-34; WP9.4, WP9.7; stage A family (a 14th record under
either option).

### M-2 (Major). The stage B verifier has no independent expected side; §3 leaves the decisive fields unspecified

**Claim.** W11's verifier derives every catalogue row from an accepted owner annex. The note gives W9's verifier
nothing to compare the catalogue against, and §3 does not fix the fields such a comparison would need.

**Evidence.**
- `tools/verify_w11_materialization.py:539-579` reads the accepted W11 spec blob at its pinned commit, parses every
  `| OR-nnn |` row and derives the command, eligible profile, authority subject, preconditions, events, streams,
  reducer, projection and receipt. W11-T01 and W11-T03 (`test_w11_expected_catalogue.py:52-86`) compare each
  catalogue row with that independently derived row. The literal test IDs are fixed by W11's own text (W11 §4.2,
  line 478).
- Note §2 (line 52) replaces `file_observation_ref`, a hash-bound reference to an observation of the owner table,
  with free-text `source_refs`, because "W9 has no owner table".
- Note §5 (lines 134–135) lists only a count and range hash, ID uniqueness, binding-test names and fixture ranges.
- Note §3's table gives no `authority_subject`, `logical_key`, `affected_streams`, `complete_write_set`, `reducer`,
  `projection_targets` or `receipt_identity`. The paragraph below it gives a naming pattern for the last four, and
  nothing for the authority subject. W11 §4.2 calls the authority subject "the separate exact-subject grant": a
  path-only, role-only or wildcard subject never satisfies a row.

**Failure scenario.** The stage B author writes LR-006's `authority_subject` as the batch stream alone, and drops
"every item in its window" from its preconditions. The verifier passes, because count, uniqueness and test names are
unchanged, and the W9-C "negative mutation" test cannot fail because there is no expected row to diverge from. The
only control left is Stephen reading about 300 field values at acceptance. That is self-attestation by the catalogue
author.

**Impact.** Validity of the accepted contract that WP9.2 implements.

**Disposition.** Fix now, in the note's revision 2.

**Proposed change.**
- Turn note §3 into a normative owner annex. Give one parseable row per LR row with every catalogue field (or every
  field except mechanically derived names), including the exact `authority_subject`.
- Stephen's O-8 acceptance names the note's blob together with the catalogue.
- The stage B verifier derives expected rows from that blob at its pinned commit, as W11's does.
- `source_refs` becomes `owner_annex_ref`: the note's commit, blob, SHA-256 and the row line's hash, the analogue of
  `file_observation_ref`.
- `W9-C01` and `W9-C03` then compare against a real expected side.

**Affected.** P-071 item 1 (row shape); O-8 (acceptance subject); stage B verifier; WP9.2.

### M-3 (Major). Missing preconditions against their cited sources

**Claim.** Several rows omit preconditions that W9 or 06v state. The catalogue is "the accepted contract that WP9.2
implements" (note line 100), so an omission here becomes an unimplemented control.

| Row | Missing precondition | Source |
|---|---|---|
| LR-002 | Every §4.4 detector's negative control watched to fail before the first registration | W9 §4.4 lines 201–202; O-13 |
| LR-005 | §4.5's closed-reference column (Gate 7 opened; G7-A, B and C accepted; catalogue imported; detectors live). LR-006 has it; observation sits in the same §4.5 row | W9 §4.5 line 209 |
| LR-005 | The registration is in the committed registration manifest at the binding's `git_head`, so no newly registered file is invisible to rule 1 | 06v WP9.5 lines 470–473, 483–484 |
| LR-005 | Computational-Log entries are observed only from the accepted export, and `CONVENTIONS.md` locks only from blob `4b143c92`. "Handle-bound read in its window" does not apply to them | W9 §7.3 item 3; §8.3 lines 451–453 |
| LR-005 | Importer and observer are not the membership table's author. That cannot be checked at LR-003, because the importer is not yet known | W9 §5.2 line 243; §6.2; template §2 |
| LR-006 | Refuse an observation of a result affected by a later `shared_enforcement_surface` change, using the committed change list at `git_head`. Stage A has the `enforcement_change_list` field; the row does not name the rule | O-32; 06v WP9.3 lines 426–427 |
| LR-006 | Per-item `pilot_promotion` applicability proposed by the reviewer and fixed in the batch Decision, never by the producer | W9 §12.3 lines 604–605 |
| LR-006 | First batch: closed-reference items only, at most 20; after a missed threshold, no further batch | W9 §14.2, §14.3 lines 724–727; 06v L-4 |
| LR-010 | Each `adoption_ref` is an active (unsuspended) adoption for the use "evidence for the manuscript claims of paper X". Adoption is use-scoped, so an adoption "for input to T1.41" must not count | W9 §12.1 lines 565–566; §9 item 4 |
| LR-011 | The inventory is complete over the root's files at the observation commit | W9 §8.2 (W11's DAG; W11 OR-122 "Complete final-byte membership") |
| LR-013 | D-3: extractor output equals the reviewer's derivation, or the transition is blocked; the cited adoptions are still active at transition; §4.5's paper-root column enumerated, not cited as "the §4.5 column"; preconditions for `successor_owned → closed_reference` (none stated); refusal of `legacy_owned → closed_reference` (B-2) | 06v WP9.4 lines 459–461; W9 §4.5 line 212 |
| LR-014 | The replacing record is of the same kind and passed its own row; the superseded record is not already superseded | W9 §13.2; W9-T14 |
| All "/ S" rows | The Decision is resolved, by Stephen, of kind `migration_authority`, bound to this record's ID and exact content hash; the review is satisfied on the current hash (S-007) | P-005; W9 §8.5 item 5; §12.3 S-007 |

**Failure scenario.** LR-010 as written accepts a citation status whose family is adopted only for "input to T1.41".
LR-013 then transitions P01-A, and W5 admits that family as manuscript evidence: the use-scoping of W9 §9 item 4 is
bypassed.

**Impact.** Validity and operations.

**Disposition.** Fix now: add each precondition to the row, with its source. Under M-2 the verifier then pins them.

**Affected.** LR-002, 005, 006, 010, 011, 013, 014 and every Stephen-resolved row; WP9.2 to WP9.4.

### M-4 (Major). `pilot_promotion` evidence and §11.2 coverage reach only LR-006

**Claim.** W9 §12.3 assigns fixtures to adoption, supersession, paper-root transitions and result-family
observations, and W9 §8.5 item 4 requires them "for any item whose acceptance changes citability or feeds a claim".
Only LR-006 carries `pilot_promotion`.

**Evidence.**
- W9 §12.3 (lines 584–602) assigns:
  - F-015 and F-019 to adoption;
  - S-015 to every supersession;
  - F-006, F-019 and F-037 to paper-root transitions;
  - F-018 and F-037 to every result-family observation;
  - S-005 and S-007 to reviews.
- Stage A's adoption, supersession, ownership-transitioned and mapping schemas have no `pilot_promotion` field. Only
  `legacy-closed-reference-acceptance` has one.
- W9 §11.2 (lines 542–544) applies the two-family rule "at dispatch to every item in P-005's R3 set (… claim
  promotion, adoption)", and W9-D3 was accepted as recommended. 06v O-24 (line 204) and WP9.7 implement it at compute
  dispatch only. LR-007 has no coverage precondition, and nothing records the 06v narrowing as decided.

**Failure scenario.** Stephen adopts a statistical family for a claim. No F-015 (sanity-value anchoring) or F-019
(result-to-claim overreach) evidence is required, and no second-family coverage record or one-family known limit
exists. Both W9 §12.3 and W9-D3 are silently unmet.

**Impact.** Validity. The pilot-promotion bar applies to the least consequential action (closed reference) and not
to the most consequential (adoption, paper transition).

**Disposition.** Owner decision.

**Proposed change.**
- Give each catalogue row a `pilot_promotion_fixtures` field listing its §12.3 set. This also gives the verifier's
  "every fixture within F-001 to F-038 and S-001 to S-017" check (note line 135) something to check; today no
  catalogue field holds a fixture ID.
- Add a precondition to LR-007, LR-013 and LR-014: "per-item evidence or waiver refs for the row's fixtures, carried
  in the resolving Decision". The alternative is widening those stage A schemas.
- For §11.2, ask Stephen whether adoption needs a second-family coverage record (and where it lives), or whether each
  adoption records one-family review as a known limit (§11.2 "If it does not").

**Affected.** LR-005, 007, 013, 014; W9-D3; 06v O-24, O-37; stage A schemas, under the widening alternative.

### M-5 (Major). P-071 item 4's "later catalogue revision" has no route into the store

**Claim.** P-071 item 4 defers writer revocation, the bus non-import inventory, file-level closure, cutover,
retirement and manual-mode imports to "a later reviewed catalogue revision, with a new identity and a new
acceptance". Nothing in W9, 06v or the note says how that revision enters a store that already holds catalogue v1.

**Evidence.**
- W9 §5.3 item 2 provides "one independently verified genesis transaction".
- 06v WP9.2 refuses "a second genesis per store, from the replayed projection" and lists "a second genesis" among
  the genesis negatives (lines 360, 394).
- No LR row imports an accepted revision.
- O-35 and W9-T23 belong to WP9.6, and W9-T18's file closure to WP9.3 (06v §4). 06v §1's measure of done needs W9-T1
  to W9-T23 to pass.

**Failure scenario.** At L-5, catalogue v2 (with closure and cutover rows) is accepted. The genesis command refuses
it in `TDL-ARS-G7-Control`, because v1's genesis is already in the store. The deferred actions then need either a new
store, which would migrate every accepted W9 record, or an unreviewed amendment path.

**Impact.** Migration and operations.

**Disposition.** Owner decision: amend P-071 item 4. The deferral itself is sound.

**Proposed change.** Add to v1 an inert row, `ImportAcceptedW9CatalogueRevision`, with these preconditions:
- the v1 genesis is present;
- the new envelope supersedes the current identity;
- Stephen has accepted the revision;
- every v1 row is unchanged or explicitly superseded;
- the route partition is re-proved.

The alternative is to record now that the deferred actions run in a named later store, and accept the consequences.

**Affected.** P-071 item 4; W9-D10; WP9.2 (genesis guard), WP9.3, WP9.6; L-5.

### M-6 (Major). Stage B's own identities: SB-Q1 brings back the ordering problem P-069 item 1 avoided

**Claim.** SB-Q1 changes the catalogue-content schema, the generator and the stage A test inside stage B. Stage B
must also produce an envelope instance that pins all of these by `git_commit` and names a `rev_` and a `dec_`.

**Evidence.**
- Stage A's `w9-catalogue-acceptance-envelope` requires `catalogue_identity`, `schema_identities`,
  `schema_generator_identity`, `verifier_identity` and `binding_test_identities`, each with a `git_commit`. It also
  requires `independent_review_ref` (`rev_`) and `acceptance_decision_ref` (`dec_`).
- P-069 item 1 split WP9.1 because "a squash merge rewrites branch commits" and rows that pin files by commit cannot
  precede those files on main.
- Note §5 (lines 132–136) says the envelope instance and "every schema source row pinned at `5d325c5b`". A schema
  that stage B widens cannot be pinned at `5d325c5b`.
- The G7 store does not exist until L-2 (D-1), so no `rev_` or `dec_` for the catalogue acceptance can exist in
  stage B. W11 kept its accepted identity out of a repository envelope instance. `accepted_w11.py:16-30` holds the
  commit, blobs and hashes, plus the owner's acceptance as a quoted string (`owner_decision`).

**Failure scenario.** The stage B PR commits an envelope instance pinning the widened schema at its branch commit.
The squash merge rewrites that commit, and the instance on main pins a commit that is not on main. The envelope's
`rev_` and `dec_` IDs are either placeholders, which would be fabricated identities, or must be left absent, which
fails its schema.

**Impact.** Provenance of the accepted catalogue identity.

**Disposition.** Owner decision: it refines P-069 item 1's stage B content.

**Proposed change.** State in note §5:
- Stage B lands in two steps. B1 widens the catalogue-content schema, the generator, the stage A test and the
  verifier, and merges. B2 adds the catalogue, with every schema source row pinned at B1's main commit.
- The envelope instance (with its `rev_` and `dec_`) is written at L-3, in the store, or with WP9.2's
  `accepted_w9.py`, as W11 did. Stephen's O-8 acceptance names the catalogue by main commit, blob and SHA-256.

**Affected.** P-069 item 1; O-8; P-066 item 2 (`accepted_w9.py`); stage B scope.

## 4. Minor findings

- **m-1. Binding-test errors and omissions.**
  - W9-T10 is bound to LR-002. Note §3 (line 91) and 06v §4 (line 233) place T10 entirely in WP9.7, so the binding
    is unjustified. Remove it.
  - W9-T6 ("a change in a window aborts") is missing from LR-011 and LR-013, which both say "the window held", and
    from LR-007 (O-33: an adoption binding the old blob is blocked).
  - W9-T9 is missing from LR-014, which emits a suspension.
  - W9-T1 is missing from LR-007 (its negative control says "no acceptance or adoption").
  - W9-T18 is bound to LR-004, but the closure it tests is deferred (P-071 item 4). State that in v1, T18 is a
    tool-level test of the O-36 inventory and closure tool.
  - W9-T23: state that in v1 it is a unit test of WP9.6's importer with no row (06v §4 line 246), so no §17 test is
    silently unbound.
- **m-2. SB-Q6 needs a verifier rule and literal IDs.**
  - P-071 item 6 names LR-008 as "the case". The verifier must refuse any other row whose binding tests are only
    `W9-C…`. Otherwise any row can drop its W9-T binding.
  - The `W9-C` forms appear nowhere in W9. W11's forms are fixed by W11's own text (§4.2 line 478). The note must
    fix the literals, for example `W9-C01-LR-nnn`, `W9-C03-LR-nnn-owner-row-mutation` and `W9-C11-LR-nnn`.
- **m-3. The row shape is not exact.** P-071 item 1 says "19-field", and the note says "about 20". The §2 mapping
  yields 22 fields. The note does not say which are required or nullable (`requester` for O-only rows,
  `record_schema_id` for LR-001).
  - Event multiplicity needs a notation: per item (LR-006), and zero or more conditional (LR-005, LR-014).
  - "Each record kind has its own stream" (line 82) reads as one stream per kind. That conflicts with W11's per-object
    streams and with exact-subject grants (scoped authority binds `target_stream_id`, `discovery/runtime.py:240`).
    State per-record streams.
  - For rows with several roles, `eligible_actor` must name the submitter.
  - The stage A note §3 left "the kinds of the `anyRef` fields" to "stage B's catalogue rows, or WP9.2". The note
    fixes none and does not defer them by name.
- **m-4. Variant rows.** LR-009 (ordinary vs recovery root) and LR-013 (three transitions) have materially different
  preconditions. W11 splits such cases by `payload_discriminant` (OR-003/OR-011, OR-018/OR-019). Split them so each
  branch gets its own positive and negative-mutation tests.
- **m-5. Naming.** LR-012 `ProposeLegacyTransitionMapping` creates a record that already carries Stephen's
  `decision_ref` and a `reviewer_ref`. It records the accepted mapping, so name it `RecordLegacyTransitionMapping`, or
  say why "Propose" is used.
- **m-6. LR-008 and LR-009 preconditions.**
  - LR-008: `legacy_item.item_id` resolves against the accepted A-001 list or the audit, and the successor result is
    accepted, not only registered.
  - LR-009: a recovery root's predecessor is `successor_owned`; an ordinary root is created only under §12.1's
    ordering ("Papers transition last").
- **m-7. Verifier paths and boundary.** P-065's Boundary ("Docs and data files only") has been extended only by name
  (P-067; P-069 item 4). Note §5 names no verifier or test path. Name them (for example
  `tools/verify_w9_materialization.py` and its test), and record either that P-069 item 1 covers them or a named
  extension.

## 5. Info

- **I-1. Verified identities.**
  - The W11 catalogue at `5d325c5b` is blob `8d588185`, with 81 rows of 19 fields each.
  - Stage A's `OWNER_ROW` (`tools/w9_schema_gen.py:1197`) requires 9 fields, as the note says.
  - `5d325c5b` is `origin/main`, and main has not moved since.
  - The diff is docs only.
- **I-2. Record coverage.** The 13 record kinds plus genesis map one to one onto LR-001 to LR-014, apart from B-1's
  missing review and decision rows. The exclusions (the §4.4 detectors, the WP9.7 guards, the O-16 projector) agree
  with 06v §4. The P-071 item 4 deferrals are explicit. No row is unjustified on its face.
- **I-3. Actors and resolvers.** Every "/ S" row resolves to Stephen, consistent with W9 §8.6 and P-005. Adoption is
  Stephen-only, which P-005's "upgrading imported evidence" requires. Observation and light inventory carry no
  resolver, because their acceptance is LR-006. SB-Q5's `membership_author` matches template §2. The note's "every
  command refuses the Gate 6 store" is stricter than 06v, which puts the refusal in genesis. That is acceptable, if
  stated in each row's preconditions.
- **I-4. Authority.** Nothing in the note authorizes anything beyond P-065 and P-071, apart from the m-7 naming
  gap. The full-path rows (LR-009 to LR-013) are inert data. 06v O-31 puts "paper-root transitions" out of scope "for
  this plan's code", while 06v §4 assigns W9-T5, T17 and T21 to code. The note should cite the reading it relies on:
  the commands are built and refuse, and no transition runs.
- **I-5. Model family.** As in every round of this chain, this review ran on one model family (P-058 known limit).

## 6. Decision audit

| Decision | Disposition | Note |
|---|---|---|
| Note §1 derivation rule ("Decisions and reviews are not W9 commands") | **Amend** | B-1 |
| P-071 "command set is LR-001 to LR-014" | **Amend** | B-1 adds rows; M-5 adds a revision-import row |
| P-071 item 1 / SB-Q1 (W11 row shape) | **Keep, amend** | Keep the shape; add the owner-annex expected side (M-2), the exact field list (m-3), `pilot_promotion_fixtures` (M-4) and the B1/B2 sequencing (M-6) |
| P-071 item 2 / SB-Q2 (ownership event in the acceptance) | **Amend** | B-2 |
| P-071 item 3 / SB-Q3 (suspension as an event of the cause) | **Amend** | M-1 |
| P-071 item 4 / SB-Q4 (later revision) | **Keep, amend** | Keep the deferral; add an import route (M-5) |
| P-071 item 5 / SB-Q5 (`membership_author`, `requester`) | **Keep** | m-3: nullability |
| P-071 item 6 / SB-Q6 (`W9-C` minimum) | **Keep, amend** | m-2: restrict to LR-008; fix the literals |
| P-064 D-2 (Discovery-style path) | Keep | B-1 grows its command count, and so the D-4 census change |
| P-064 D-3 (extractor plus reviewer) | Keep | M-3: bind it in LR-013 |
| P-064 D-4 (re-acceptance per command-adding PR) | Keep | More rows mean larger census deltas at WP9.2 |
| P-064 D-9 / P-069 item 3 (restricted suffixes) | Keep | LR-002 and LR-005 consistent |
| P-065 (WP9.0 and WP9.1 only) | Keep | m-7 |
| P-066 item 2 (`accepted_w9.py` in WP9.2) | Keep | M-6 proposes the envelope's acceptance refs land there or at L-3 |
| P-067, P-068 (segmentation contract) | Keep | LR-004 and LR-005 cite `w9-segmentation/1.0.0` |
| P-069 item 1 (two PRs; stage B content) | **Amend** | M-6 |
| P-069 item 2 (no event schemas, two conditions) | Keep | M-1 gap 3 must be closed for the condition to hold |
| P-069 item 4 (named boundary files) | Keep | m-7 |
| P-070 (four supersession targets) | Keep | LR-014 matches |
| P-005 (Stephen-reserved transitions) | Keep | I-3 |

## 7. Consistency matrix: W9 §17 → rows

| Test | Note binds | Disposition |
|---|---|---|
| T1 | LR-005, LR-006 | Add LR-007 (m-1) |
| T2, T3 | LR-003, LR-005 | OK |
| T4 | LR-005 | OK |
| T5 | LR-013 | OK. Under B-2, LR-013's refusal of `legacy_owned → closed_reference` gets its own negative |
| T6 | LR-005, LR-006 | Add LR-007, LR-011, LR-013 (m-1) |
| T7 | none (tool) | OK (WP9.5). LR-002's precondition cites its controls (M-3) |
| T8 | LR-007 | OK (legacy side; WP9.7 guard) |
| T9 | LR-005, LR-007 | Add LR-014 (m-1). M-1's widened trigger needs an unchanged-blob negative |
| T10 | LR-002 | **Remove** (m-1); WP9.7 only |
| T11 | LR-002, LR-005 | OK |
| T12 | none (WP9.7) | OK. The adoption limb is M-4 |
| T13 | LR-005 | OK |
| T14 | LR-014 | OK |
| T15 | LR-009 | OK |
| T16 | LR-006 | OK |
| T17 | LR-010, LR-011, LR-013 | OK. M-3 adds the use-scope and D-3 preconditions |
| T18 | LR-004 | Closure is deferred; state tool-level (m-1) |
| T19 | none (tool) | OK (WP9.5) |
| T20 | LR-001 (every command) | OK |
| T21 | LR-009, LR-012, LR-013 | OK |
| T22 | LR-004 | OK |
| T23 | none (deferred) | State unit-level in WP9.6 (m-1); M-5 for the row |

## 8. Practicality

Under B-1, the command count grows from 14 to roughly 30 if review and decision rows are added per record kind, as
W11 did (each W11 authority record has five or six rows). The D-4 census change at WP9.2 grows with it. That is the
cost of W11's precedent, and it is proportionate to what it buys: each Stephen-resolved record gets an exact-hash
review and decision path.

M-2's owner annex adds little work, since §3 already holds most of each row. It removes the largest remaining
self-attestation in the chain.

M-6's two-step stage B adds one merge.

## 9. Revision plan

1. **Immediate (author, note revision 2):** M-3, m-1, m-3 to m-7. Turn §3 into the owner annex (M-2).
2. **Owner decisions (Stephen):** the B-1 route ((a) or (b)); the B-2 superseding text for P-071 item 2; M-1 gaps 2
   and 3; M-4 (fixture evidence placement, and adoption's §11.2 coverage); M-5's import row; M-6's B1/B2 split and
   envelope timing.
3. **Later-work dependencies:** WP9.2 (genesis guard and revision import; reducer invariants under B-2); WP9.4
   (adoption suspension); WP9.6 (O-35 and W9-T23, waiting on M-5); WP9.7 (the use-mismatch request, M-1).

## 10. Residual risks

- If B-1 takes option (b), a change to the generic `RequestReview` preparer is a protected-tree change under D-4
  and outside P-065.
- The note does not address the same-model-family limit (P-058), and cannot.

## 11. Commands run (read-only; no store, vault, `.apm/` or Jira access)

```text
git fetch origin
git checkout pipe/w9-wp9-1-catalogue                      # worktree beautiful-volhard-d3f62e
git diff --stat 5d325c5b..0cf8acd3
git diff 5d325c5b..0cf8acd3 -- docs/plans/agentic-research-system/03-decisions-and-open-questions.md
git log --oneline 5d325c5b..origin/main
git merge-base --is-ancestor 5d325c5b origin/main
git rev-parse 5d325c5b:.research-system/evals/expected/w11-portfolio-discovery-v1.json
git ls-tree 0cf8acd3 <note> <register>
git diff --stat 5d325c5b 0cf8acd3 -- . ':!docs'
grep -n '^#' design/09-migration-compatibility-and-pilot.md implementation/06v-w9-implementation-plan.md
sed -n '92,130p;4118,4473p' 03-decisions-and-open-questions.md
python -I -c <print w9-schema-catalogue-content.schema.json>
python -I -c <list the W11 catalogue's keys and 81 rows: command, profile, events, logical key>
python -I -c <summarise required fields of the 13 legacy-*.schema.json records>
python -I -c <print required fields of w9-catalogue-acceptance-envelope.schema.json>
python -I -c <summarise generic propose_decision, resolve_decision, request_review, record_review_verdict schemas>
cat .research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml
sed -n 1,90p research_system/discovery/commands.py
sed -n 200,240p research_system/discovery/runtime.py
sed -n 3695,3760p;4100,4180p research_system/command/service.py
sed -n 1,135p tests/research_system/contracts/test_w11_expected_catalogue.py
grep -n 'def _expected_owner_contract_rows' -A40 tools/verify_w11_materialization.py
sed -n 1,60p research_system/discovery/accepted_w11.py
grep -n '^## 2' -A25 transition/w9/w9-membership-table-template.md
grep -n 'OWNER_ROW' tools/w9_schema_gen.py
```
