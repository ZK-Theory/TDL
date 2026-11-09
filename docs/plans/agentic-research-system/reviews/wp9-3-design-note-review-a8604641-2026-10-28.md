# Independent review: WP9.3 design note, revision 1 (`a8604641`)

**Date:** 2026-10-28 (finished 2026-10-29)<br>
**Subject:** `docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md`, revision 1, at `a8604641` on
`pipe/w9-wp9-3-design-note`. The commit adds only that file to `main` at `1f0d8281` (`git diff --stat 1f0d8281
a8604641`: one file, 911 lines).<br>
**Reviewer:** a fresh session, not the note's author. It did not read the author session's transcript or notes. It
read the observation log, which the author's session also writes to, and treated those entries as claims to check.<br>
**Branch:** `review/w9-wp9-3-note`, cut from `a8604641`. The note is not edited.<br>
**Method:** `research-observer`, then `research-assurance-triage`, then `adversarial-design-review`. Every `path:line`
below was read at `a8604641`. The probes are pytest cases on in-memory registries, reducers and payloads. They open no
store and write nothing to the repository. The file is kept in the session notes as `wp9-3-note-review-probes.py`
(SHA-256 `9f9e43c3…0abb`). It ran 22 passed, and every case asserts its outcome.<br>
**Known limit:** the author and the reviewer are the same model family (P-058).

## Verdict

**Accept with required changes.**

The note's structure holds. The rows and commands, the split, the content-hash rule, the replay-versus-preparer
division and the census delta are sound, and the census delta reproduces. One finding blocks: §10.2 and owner point K
misread the accepted LR-020 fixture set. As written, Stephen would decide K on a false premise, and the code would
enforce less than the accepted catalogue requires. Four Major findings need note changes before Stephen decides the
owner points. Two of them (M-3, M-4) change what he is asked.

| Severity | Count | IDs |
|---|---|---|
| Blocking | 1 | B-1 |
| Major | 4 | M-1 to M-4 |
| Minor | 10 | m-1 to m-10 |
| Info | 6 | i-1 to i-6 |

## Research-assurance triage

- **Stage.** A design note (a plan), not a result. It gets design and dispatch scrutiny, not result provenance.
- **Lanes touched.** Output and provenance: content hashes, pre-assigned refs, anchors, the export and its recheck,
  fixture manifests. Paper claim, indirectly: W0 classes, precedence and `pilot_promotion` decide what can later be
  cited. Topology, null-model, statistical and representation: none. The note says the same (§18).
- **Governing records.** P-080 (authority), P-068 (segmentation contract and its independence clause), P-072 and P-073
  (routes, ownership, W9-C20 to W9-C25), P-075 (O-8: the catalogue and annex at `7979e85a`), P-077 to P-079 (WP9.2),
  06v WP9.3, D-4, D-6 and D-7, and W9 §12.3.
- **Machine-checkable claims.** The census delta, row routing, the content-hash rule, the pre-assigned ref rule, the
  ownership derivation, the W2 payload encodings and JSON parsing. Each was probed here (§2).
- **Human-review-only claims.** W0 class correctness, precedence tiers, `pilot_promotion` sufficiency, the governing-
  record set's completeness, and session independence. §5 of this report audits that split.

## 1. Findings

### B-1 (Blocking). The accepted LR-020 fixture set has seven fixtures, not three. Owner point K's gap does not exist

**Claim.** §10.2 says LR-020's catalogue set is "F-017 (when the item is a sensitivity or comparison file), F-018 and
F-023", citing `wp9-1-catalogue-owner-annex.yaml:729-735`. It concludes that the set "omits" F-037, S-005 and F-038, and
asks Stephen to decide owner point K on that basis.

**Evidence.** The cited range stops early. The row continues to line 743. At the accepted annex blob
`d8fbda416b016f5e19c03689f336caff3166d0d9` (`ACCEPTED["annex_blob"]`, `research_system/legacy/accepted_w9.py:25`),
`wp9-1-catalogue-owner-annex.yaml:729-743` (the field at line 729, its seven entries at lines 730-743) lists:

| Fixture | `when` |
|---|---|
| F-017 | an item is a sensitivity or comparison file |
| F-018 | null |
| F-023 | null |
| F-037 | null |
| S-005 | two results compete for one object |
| S-014 | null |
| F-038 | an item uses the TDA pack's lanes |

The accepted catalogue (`.research-system/evals/expected/w9-legacy-integration-v1.json`, LR-020's
`pilot_promotion_fixtures`) holds the same seven entries. W9 §12.3 (`design/09-migration-compatibility-and-pilot.md:579`
onward) assigns each one to the batch the same way. S-014 reads "re-run after each W9 batch".

**Failure scenario.** The code follows §10.2 and the O-37 controls in §17 ("a missing F-018 or F-023"). A batch whose
items carry only F-018 and F-023 is then accepted, although the accepted LR-020 row requires F-037 and S-014 on every
item. Stephen would also be asked to "record the gap for the next catalogue revision", a revision that is not needed.

**Impact.** The code would depart from an accepted text (P-075). An owner decision would rest on a misreading. The
§17 test table and the §18 machine-checkable list also inherit the three-fixture set.

**A second issue the corrected reading exposes.** S-014's assignment is "re-run after each W9 batch". The batch's
evidence must be present at LR-016 and LR-020, which come before the batch is accepted. A per-item S-014 ref can
therefore name only an earlier restore run, or a waiver. The note has to say which. This ordering question is Stephen's
(see owner point K′ in §4).

**Disposition.** Fix now.

**Proposed text for §10.2.** "LR-020's catalogue set (`wp9-1-catalogue-owner-annex.yaml:729-743`) is F-018, F-023,
F-037 and S-014 on every item, plus F-017, S-005 and F-038 when their conditions hold. The preparer and replay require
the four unconditional fixtures on every item. The reviewer marks each conditional fixture's applicability, and
Stephen's batch Decision fixes it (W9 §12.3). Code cannot decide a `when` condition." Withdraw owner point K. Add K′
on S-014's timing. Extend the O-37 tests in §17 to a missing F-037 and a missing S-014.

**Affects:** §10.2, §17 (O-37), §18, §21 K; WP9.3-2.

### M-1 (Major). Two open batch proposals can both be resolved: one item accepted twice, and a second batch without the pilot Decision

**Claim.** §10.1 checks at LR-016 that each item's observation is "accepted by no earlier batch", and that the batch is
the first, because "no acceptance is recorded yet". §6.2's LR-020 row re-checks G5, the ownership list, the window,
the anchors and the change list. It does not re-check either batch rule.

**Failure scenario.** The analyst proposes batch A (LR-016). Before A resolves, the analyst proposes batch B with an
overlapping item O. Both pass LR-016, because neither is recorded. Both get reviews and Decisions. Stephen resolves A,
then B. O is now accepted twice. B is a second batch, admitted without the integration-pilot outcome Decision that the
annex requires: "a batch after the first requires the integration-pilot outcome Decision resolved as passed"
(`wp9-1-catalogue-owner-annex.yaml`, LR-016 preconditions). LR-022 is not even routed (§2.1).

**Impact.** This permits an acceptance the accepted row forbids. Stephen's resolution is a human check, but the note's
own rule (§6, "replay checks everything the ledger determines") puts this check in code.

**Disposition.** Fix now. Add to §6.2's LR-020 replay column: "every item's observation is accepted by no recorded
batch, and no acceptance is recorded (first batch only), both re-checked at this position". Add to LR-016: "no other
acceptance proposal is open and unexpired" (one open batch at a time). Add a test with two open proposals sharing an
item, where the second resolution is refused at replay.

**Affects:** §6.2, §10.1, §17; WP9.3-2.

### M-2 (Major). The §5.2 encodings leave required fields of the closed W2 payloads unnamed and unchecked, some of them authority-bearing

**Claim.** §5.2 fixes some fields per payload and says replay "does not check the other fields (questions, lanes,
deadlines), which the preparer fills from the payload or from constants".

**Evidence.** Probe `test_probe_3_required_w2_fields_the_note_leaves_unnamed` compares §5.2's named fields with each
payload's `required` list (`.research-system/schemas/core/events/*.schema.json`, `$defs.payload`):
- `ReviewVerdictRecorded`: `computed_independence_grade`, `conditions`, `context_manifest_id`,
  `context_manifest_sha256`, `findings`, `limitations`, `producing_attempt_id`, `required_evidence_refs`,
  `reviewer_profile`, `trace_visibility_evidence_refs`, and `verdict` itself;
- `DecisionResolved`: `conditions`, `decision_revision`, `effective_at`, `effective_scope`, `permitted_commands`,
  `revisit_triggers`, `superseded_decision_ids`;
- `DecisionProposed`: `expires_at` among others, which §5.2 relies on ("the preparer refuses a resolution after the
  proposal's `expires_at`").

The probes show that the six fields §5.2 names for `DecisionResolved` do not form a valid payload. Discovery refuses a
verdict whose `computed_independence_grade` differs from the request's `required_independence_grade`
(`research_system/discovery/runtime.py:2487`). W11 fixes `context_manifest_id` and `producing_attempt_id` as constants
(`discovery/runtime.py:1130`, `:1162-1167`).

**Failure scenario.** A forged or faulty ledger records a W9 verdict `approve` with `computed_independence_grade:
"self"`, or a `DecisionResolved` with non-empty `conditions` or `permitted_commands`. Replay accepts it, because §5.2
does not check those fields. §5.4 then calls the review "satisfied", and the record is written under a Decision whose
conditions nothing discharges.

**Impact.** These bytes are stored. Leaving them to "constants" in the code PR fixes stored bytes outside the reviewed
note, which is what §4.2 itself says belongs in the note.

**Disposition.** Fix now. Give a full table for each of the four payloads: every required field, its source (command
payload, constant, or derived) and whether replay checks it. At least: `computed_independence_grade` equals
`required_independence_grade` (`independent`); `conditions` is `[]` on the verdict and on the resolution;
`permitted_commands`, `superseded_decision_ids` and `revisit_triggers` are fixed values; `decision_revision` is 1; and
`context_manifest_id` and `producing_attempt_id` follow a stated rule. Add one forged-ledger control per checked field.

**Affects:** §5.1, §5.2, §5.4, §14, §17.

### M-3 (Major). §5.5 relaxes W9-C20's session limb from "refused" to "recorded, not proved", without citing W9-C20 or P-073

**Claim.** §5.5 lists "a different session from the analyst (W9 §8.6)" under "Recorded, not proved", as the operator's
attestation. Owner point H calls it "a known limit".

**Evidence.** The accepted annex `catalogue_tests` define W9-C20 as "a reviewer who produced the item, **shares the
analyst's session**, or is not the eligible session **is refused**" (`wp9-1-catalogue-owner-annex.yaml`, `W9-C20`). P-073
item 1 records it as a closed family of negative controls, and says "each is refused". The preconditions of LR-007,
LR-012 and LR-017 require the session distinction, and their `binding_tests` include W9-C20. Neither §5.5 nor owner
point H cites W9-C20 or P-073.

The closed `ReviewRequested` payload has no session field. The verdict carries `reviewer_session` (a required string).
So a full proof is not available, but a partial check is: the request can carry the analyst's session string in a
field the note already uses for encodings (for example a `w9-analyst-session:<session>` entry in
`required_evidence_refs`). Replay can then refuse a verdict whose `reviewer_session` equals it. Both strings are still
attested, but the check catches the honest same-session mistake that W9-C20 names.

**Failure scenario.** The code PR implements §5.5. W9-C20-LR-007, -LR-012 and -LR-017 then have no session case. A
review recorded from the analyst's own session passes, and the accepted test's text is not met. No one is told that an
accepted test was narrowed.

**Disposition.** Amend the decision; this is Stephen's call. Rewrite owner point H to cite W9-C20 and P-073 item 1,
and offer: (a) encode the analyst's session and refuse equality at replay, recording that both strings are attested
(recommended); or (b) record the session limb as a known limit that narrows W9-C20, as P-058 did for model families.

**Affects:** §5.5, §17 (W9-C20), §18, §21 H; P-073 item 1.

### M-4 (Major). The note makes WP9.3's exporter the D-7 producer and also its checker, which removes the independent recheck

**Claim.** The §11.1 table names "WP9.3's exporter, at L-0b" as the producer of the Computational-Log export. §12.2
gives the same exporter a recheck mode that "re-segments the retained copy and compares it with a committed export".

**Evidence.** Segmentation contract §6.1: "The export may be taken before WP9.3's handle-bound reader exists. It is
read by the reference implementation (§7) from bytes copied once from the live page." §6.3: "WP9.3's reader later
re-segments the retained copy and must reproduce every row. A mismatch voids the export." 06v D-7: "WP9.3's exporter
later reproduces the same hashes as a check." In the accepted design, the export comes from the reference
implementation, `tools/w9_segmentation.py` (blob `43e1454d`, P-068), and WP9.3's runtime segmenter rechecks it. That
makes two implementations. Under the note, one module produces the export and certifies it.

**Failure scenario.** A defect in `research_system/legacy/segmentation.py`, say in CRLF terminator handling, produces
wrong row hashes at L-0b. The recheck runs the same code over the same retained copy and reproduces the wrong hashes,
so the export is "valid". The detector then compares the live log against wrong baselines.

**Impact.** Self-attestation in a provenance check, the failure class the project's record names first. The
differential test in §8.1 runs on generated inputs, not on the export's bytes.

**Disposition.** Fix now. State that the export is produced by the reference implementation, as contract §6.1 reads,
and rechecked by the runtime segmenter. Alternatively, if WP9.3's export mode is kept, its recheck must run the other
implementation. Either way, say which implementation produced each committed export, and record it in the export.

**Affects:** §11.1, §12.2, §17 (exporter); D-7; L-0b's brief.

### m-1 (Minor). §2.2 miscounts the W9 commands still unbound after WP9.3: four, not three

`ImportAcceptedW9CatalogueRevision` (LR-002) has no binding row either. Only genesis is bound
(`research_system/schema_registry.py:268`). Probe `test_probe_1b_…` lists the four unbound commands after the note's
eleven rows: `CreateLegacyPaperRoot`, `ImportAcceptedW9CatalogueRevision`, `RecordAdoptionUseMismatch` and
`RecordPaperCitationStatus`. **Fix:** correct the sentence. A catalogue revision's package also adds a census row,
under D-4.

### m-2 (Minor). The ownership derivation maps two whole-file items of one registration to one ID

§10.5 derives one record "per item whose observation covers the whole file", with ID domain
`w9-ownership:<acceptance ID>:<registration ID>`. A batch may hold a `whole_file` observation and a complete-family-set
observation of the same JSON registration: §10.1's "the latest for its source and selector" allows both, because their
selectors differ. Probe `test_probe_5_two_whole_file_items_…` shows that both items derive the same ID. Probe
`test_probe_5_and_the_second_transition_…` shows that the existing `_apply_ownership` refuses the second transition
(`replay/reducers.py:297-298`). The failure is closed: the batch cannot be accepted. But the annex's wording ("one per
accepted whole-file observation") and the derivation disagree. **Fix:** derive one record per registration with any
whole-file item, or refuse two whole-file items of one registration at LR-016. Say which in owner point E. The
derivation is otherwise deterministic and distinct across batches (`test_probe_5_derivation_…`).

### m-3 (Minor). The pre-assigned ref rule does not say which record ID an LR-020 ownership record's copied refs are checked against

§4.2 ties a pre-assigned ref's hash to "the proposal's record ID", and replay "recomputes it and refuses any other
value". §10.6 copies the acceptance's `independent_review_ref` and `decision_ref` into each ownership record,
"pre-assigned hashes included". A replay check that recomputes each ref against the record that carries it refuses
every ownership record (`test_probe_8_an_ownership_record_…`). **Fix:** say that the copied refs are checked against
the acceptance's record ID. The rule is otherwise free of circularity (`test_probe_8_rule_depends_on_neither_hash`).

### m-4 (Minor). Existing WP9.2-2 negative controls lose their vehicle once the rows are in production

`test_c1_a_w9_command_without_its_binding_row_is_refused` (`tests/research_system/integration/test_w9_legacy_replay.py:228-233`)
relies on `ObserveLegacyRecord` having no binding row. `test_c2_a_w2_typed_event_without_its_producer_binding_is_refused`
(`:244-253`) relies on `ReviewRequested` having no `RequestW9AuthorityReview` producer row. WP9.3-1 makes both rows
production rows (`test_probe_1c_…`). Both tests would then fail, and fixing them by deleting the expectation would
leave C1 and C2 untested. The registry de-duplicates the harness's own rows (277 active rows when the harness adds its
twelve over the note's eleven), so the rest of the harness keeps working. **Fix:** list both controls in §17, and
re-point each to a command or producer that WP9.3 leaves unbound, or remove the row by monkeypatch inside the test.

### m-5 (Minor). Python's `json` departs from template §3 rule 1 in ways the note does not name

§20 item 9 asks whether Python's JSON parsing can meet rule 1 exactly. Not without checks the note does not specify.
The probes show:
- `json.loads` keeps the last duplicate key silently; an `object_pairs_hook` is needed (`test_probe_9_default_…`);
- `1e400`, a valid RFC 8259 number, parses to `inf`, the same value as the token `Infinity`, and `parse_constant` never
  sees it. A value-level non-finite check would misreport it (`test_probe_9_an_overflowing_…`);
- `json.loads` on bytes accepts a UTF-8 BOM and UTF-16 input, and it accepts a lone-surrogate escape
  (`test_probe_9_departures_…`).

**Fix:** §8.2 should name the reader's checks: bytes decoded strictly as UTF-8 with no BOM; duplicate keys refused
through the hook; non-finite tokens detected with `parse_constant` (token level), with an overflowing literal blocked
or recorded separately; and lone surrogates either blocked or recorded. Each check needs a vector.

### m-6 (Minor). The shadow run needs driver checks that the reducers do not make, but §14 says `driver.py` does not change

§6 says the preparer runs the prepared transaction "through the same reducers on a copy of the projection". The schema
check, C3 and the row-shape check run in `replay_legacy`'s loop (`replay/driver.py:139-149`), not in `REDUCERS`.
Probe `test_probe_4_reducers_alone_…` shows that a schema-invalid payload naming `OR-101` passes the reducer alone.
Probe `test_probe_4_review_request_rows_…` shows that `assign_row`'s `review_request_rows` can be rebuilt from the
projection, so no second whole-ledger replay is needed (§20 item 4 holds). **Fix:** say the shadow step is the
driver's per-transaction step (assignment, routed check, shape, C3, payload schema, reducer), factored out of the loop.
Then drop `replay/driver.py` from §14's "do not change" list, or say how the preparer reuses those checks.

### m-7 (Minor). §11.2 and §13 name different binding paths, and neither yields what the other needs

§11.2 loads the binding through `load_current_binding` (`store/current_binding.py:801`) for its `git_head`. §13 binds
through `_verified_ledger(control_root, read_only=False)` (`cli.py:1452-1484`), which returns no `git_head`.
`load_current_binding` also requires a clean worktree including untracked files (`:852-853`), HEAD at `git_head` unless
the binding is schema 1.2.0 (`:847-851`), and a foundation that names the target store (`:822-827`). Today's foundation
pins the Gate 6 store (`.research-system/config/foundation.yaml:4-6`), so this waits for D-1's re-pin (06v §2.6).
**Fix:** name one binding sequence in §13: the refusal first, then `load_current_binding`, then the ledger built from
it. Name the W9 receipt root the CLI passes to `LegacyRuntime`, which §13 step 1 refuses but never names. Record the
D-1 dependency.

### m-8 (Minor). §15's genesis re-verification consequence is stated for WP9.3-1 only

WP9.3-2 changes `LEGACY_ROUTED_ROWS` again (14/47 to 19/42), which is genesis guard 8's input. **Fix:** apply §15's
consequence to both PRs. The L-3 checklist records the review that verified genesis at the checkout L-3 runs from,
whichever PR that is.

### m-9 (Minor). Owner point G's rationale is wrong: an ARS event can already anchor a hash

§10.3 refuses `ars_event` anchors because "no W9 event carries a threshold hash, so the anchor would need a new event
family". But an `ArtefactRegistered` event carries `content_sha256`
(`.research-system/schemas/core/events/artefact_registered.schema.json`), at a global position, under the generic
`RegisterArtefact` path that §7.3 already uses for frozen copies. 06v WP9.3 accepts "an ARS event at a lower global
position" (m-9). **Fix:** correct the rationale. If `git_commit` only is still recommended, the reason is simplicity:
one anchor kind, one test. The alternative is an `ars_event` anchor that names an `ArtefactRegistered` event whose
`content_sha256` equals the anchored hash, at a lower global position.

### m-10 (Minor). Three carried items are disposed of in the note only, or not at all

- **Superseding a missing record at the preparer** (P-080 item 3). §3 row 5 moves it to WP9.6's brief "by name", but
  the brief does not exist yet and nothing in the register carries it. **Fix:** ask Stephen's decision entry for the
  note to record the carry, as P-080 item 3 itself was recorded.
- **06v WP9.3: "The `CONVENTIONS.md` vault alias is refused."** §7.1 refuses other sources for a `conventions_lock`
  registration. It does not refuse a `vault_file` registration of the vault's `CONVENTIONS.md`, which is a symlink to
  the repository file (CLAUDE.md). **Fix:** state the refusal and test it.
- **G4 for proposal rows.** §5.3 says "the hash half of each row's `authority_subject` is a replay and preparer
  check". For LR-003, LR-006, LR-011 and LR-016 the annex's subject is "pre-assigned record ID + exact proposed content
  hash", but at a proposal there is no earlier hash to compare against. The grant authorizes any content under the ID,
  and the review and Decision bind the hash later. That is a reading of an accepted global precondition, so it is
  Stephen's (owner point L in §4).

### i-1 (Info). The census delta reproduces: 262 to 273

Probe `test_probe_1_census_grows_by_exactly_eleven` built the registry with the note's seven command rows and four
producer rows: 273 active rows, all distinct. Without a producer row, each W2 event under its W9 command has no
binding, and the family is producer-bound, so the append is refused. §20 item 1 holds. The digest is the code PR's to
compute.

### i-2 (Info). The §5.2 encodings route as claimed

`ReviewRequested` built per §5.2 validates against its closed payload schema and routes to LR-007. `w9_row_ref`,
`assign_row` and `_refuse_w11_row` accept the `DecisionProposed` refs unchanged, and route them to LR-009. A second
`W9:`-prefixed ref is refused, so the lower-case `w9-subject:` prefixes matter (`test_probe_3_…`). §20 item 3 holds
for the named fields. M-2 covers the rest.

### i-3 (Info). A bound command reaches 37 rows of other packages

The seven commands also execute 37 rows tagged WP9.4, WP9.6 or WP9.7 (`test_probe_7_…`). Replay assigns a
`ProposeLegacyRecord` for an adoption decision to LR-023 and refuses it as deferred. The runtime refuses too, because
it gates on `routed_rows`. §20 item 7 holds, provided the runtime assigns rows with `assign_row`, as §2.2 says, rather
than `_COMMAND_ROWS` (`legacy/runtime.py:68`, `:418-421`).

### i-4 (Info). The line-ending claim holds at both checkouts

At this checkout `git ls-files --eol` gives 3,631 `i/lf w/lf` (the note's 3,630, plus the note itself), with two
`i/crlf` files (`.repowise-workspace.yaml` and a 06s doc), neither under `results/`, `.apm/` or `papers/`. At the
canonical `C:\Users\steph\TDL` (`main` at `779fc8bc`), every text file under those three directories is `i/lf w/lf`
(682). §20 item 10 holds.

### i-5 (Info). §20 items 2 and 6 were checked by reading, not by running

- **Item 2, the frozen-copy seam.** No probe ran it, because it needs a real scratch store, a grant and a generic
  `RegisterArtefact`. From the code: `ControlRootArtefactContentReader` reads only `root_id: "control"` inside the
  selected control root (`artefacts/runtime.py:32-51`), and `RegisterArtefact`'s subject kind is `artefact`
  (`authority.py:306`). `LegacyRuntime._replay` discards the generic projection (`legacy/runtime.py:283`), so the
  LR-015 preparer needs that function changed to resolve the artefact. The code PR's frozen-copy test should run this
  seam end to end with a non-owner observer. No live untracked or vault observation should run before WP9.7's
  `RegisterArtefact` guard (O-22) lands.
- **Item 6.** `_verified_ledger(read_only=False)` writes only inside the control root, when it builds the
  `EventLedger` with `create_directories=True` (`cli.py:1474`). `load_store_manifest`, the approved binding and
  the resolver's constructor only read. Under §13's order, the refusal comes first, so the claim holds.

### i-6 (Info). Two smaller reading notes

- The annex's "CONVENTIONS.md locks only from blob 4b143c92" (LR-015) names a commit. The note correctly reads it as
  blob `4620c716…` at commit `4b143c92`, as segmentation contract line 87 does (`git ls-tree 4b143c92 CONVENTIONS.md`).
- §9.1 adds `ACCEPTED_W0_SIGNATURES` "append-only", and W9-C25 refuses a pinned ID as pre-assigned. A ledger that
  pre-assigned the ID before the pin would stop replaying after it. The IDs are derived from a register-entry domain,
  so the case is remote. It is the same determinism concern §7.5 raises for the importer identity.

## 2. The §20 claims, probed

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | The census grows by exactly 11 | **Holds** | i-1 |
| 2 | The frozen-copy seam | **Not run**; read only | i-5 |
| 3 | The §5.2 encodings pass routing and the W2 schemas | **Holds for the named fields**; the payloads need more | i-2, M-2 |
| 4 | A shadow run without a second whole-ledger replay | **Holds**, with the driver step factored out | m-6 |
| 5 | The ownership derivation is deterministic and collision-free | **Deterministic, and distinct across batches; collides within a batch** | m-2 |
| 6 | `_verified_ledger(read_only=False)` writes nothing outside the control root | **Holds** (read) | i-5 |
| 7 | A bound `ProposeLegacyRecord` cannot reach a deferred row | **Holds** at replay; the runtime must use `assign_row` | i-3 |
| 8 | The pre-assigned ref rule has no circularity | **Holds**; the copied-ref check needs a rule | m-3 |
| 9 | Python's JSON can meet template §3 rule 1 exactly | **Only with checks the note does not name** | m-5 |
| 10 | The line-ending claim | **Holds** at both checkouts | i-4 |

## 3. Consistency matrix (the parts the findings touch)

| Invariant | Enforcement point in the note | Test in §17 | Gap |
|---|---|---|---|
| LR-020's seven fixtures on each item | §10.2 (three) | O-37 (F-018, F-023 only) | B-1 |
| One batch at a time; an item accepted once | LR-016 only | none | M-1 |
| A verdict's independence grade; no conditions | none | none | M-2 |
| W9-C20's session limb | "recorded, not proved" | none | M-3 |
| Export produced and rechecked by different code | none | exporter self-recheck | M-4 |
| One ownership record per registration | §10.5 per item | E controls | m-2 |
| C1 and C2 refusals | WP9.2-2 tests | not listed | m-4 |
| Rule 1 parsing | §8.2 | W9-T2, W9-T3 | m-5 |
| Shadow step equals replay | §6 | none named | m-6 |
| Genesis guard 8 after each routed-set change | §15 (WP9.3-1) | genesis tests | m-8 |
| The `CONVENTIONS.md` vault alias refused | none | none | m-10 |

## 4. Owner points: dispositions

| # | Needs Stephen? | Recommendation sound? | Disposition |
|---|---|---|---|
| A, the split | Yes (P-080 item 1; D-6) | **Yes.** This review asks for the split, in the note's shape: WP9.3-1 (LR-003 to LR-015, all bindings, D-4), then WP9.3-2 | Keep. Apply §15's consequence to both PRs (m-8) |
| B, approve only | Yes: it extends WP9.2-2's LR-014 reading to every W9 review | **Yes.** It matches W11's `allowed_verdicts` and the absence of a condition-discharge row | Keep. Fix `conditions: []` in the encodings (M-2) |
| C, accepted identities as frozen constants | Yes | **Yes** | Keep |
| D, the evidence area | Yes: 06v never names the path | **Yes.** `.research-system/evidence/w9/` is tracked and unignored (`git check-ignore` exits 1). The path will also hold D-9's suffix list (06v D-9) and D-5's weekly output | Keep. Record the path once, for WP9.5 and WP9.7 as well (in 06v or `CONVENTIONS.md`) |
| E, the ownership list derived, not listed | Yes: it is a reading of accepted text (`annex:567`) | **Mostly.** The derived list is fixed by the acceptance's content and the ledger prefix at LR-016, so Stephen's Decision fixes it. An alternative the note omits: list each derived ownership record's ID and hash among the LR-017 review subjects, so the hashed bytes the reviewer and Stephen act on contain the list | Keep, with m-2's rule (one per registration) and the alternative shown |
| F, genesis guard 8 generalized | Yes | **Yes** | Keep. Extend to WP9.3-2 (m-8) |
| G, `git_commit` anchors only | Yes: it narrows 06v m-9 | **The rationale is wrong** (m-9). The recommendation is defensible on simplicity | Amend the rationale, and show the `ArtefactRegistered` alternative |
| H, roles and independence | Yes | **No, as written.** It narrows W9-C20 without citing it (M-3) | Amend: cite W9-C20 and P-073 item 1, and offer the session-equality check |
| I, a runtime segmenter, and the reviewer re-implements | Yes (P-068; contract §7) | **Yes, with two additions.** The reviewer must also be shown independent of the contract's author, not only of the implementer. The re-implementation's vector results must be recorded where the acceptance can cite them. And see M-4 for the export | Keep, with the additions |
| J, the boundary extended to `authority.py` and `cli.py` | Yes (P-080's Boundary line) | **Yes** | Keep |
| K, LR-020's fixtures | **No.** The premise is false (B-1) | — | **Withdraw** |

**Missing owner points.**

| # | Point | Why it is Stephen's | Recommendation |
|---|---|---|---|
| K′ | S-014's timing: "re-run after each W9 batch" against evidence required before the batch is accepted | It reads an accepted row against W9 §12.3's timing | Let the S-014 ref name the latest restore run before LR-020, and require a post-batch re-run on the L-4 checklist |
| L | G4 at the four proposal rows: the grant binds the ID only, and the hash half has nothing to compare against until the review | It reads accepted global precondition G4 | Record it as a reading: the proposal grant is ID-exact, and the content hash is bound at the review and the Decision (m-10) |
| M | §4.2's pre-assigned ref hash is a synthetic value in a field the schemas call `content_hash` | It fixes stored bytes under a reading of accepted schemas, which the note itself says belongs in the note | Accept the rule as written, with m-3's clarification, and record it as a reading |

## 5. The research-assurance split (§18)

- **Machine-checkable list.** It is right in kind, but incomplete. Add: the seven-fixture set (B-1); one open batch,
  and no item accepted twice (M-1); the verdict's independence grade and empty conditions (M-2); the session-equality
  check if H(a) is chosen (M-3); the export and recheck by different implementations (M-4).
- **Human-review-only list.** Remove "session independence: the operator's attestation" as a whole. Under W9-C20 the
  same-session case is a refusal test (M-3). What stays human-only is whether the attested session strings are true.
  Add: "Does each item's S-014, F-037 and F-018 evidence actually evidence its fixture?" to the `pilot_promotion`
  question.
- The other human-only questions (W0 class, precedence and canonical source, the governing-record set, membership
  families) are correctly placed, and each states its question.

## 6. Revision plan

**Immediate corrections (revision 2):** B-1, M-1, M-2, M-4, m-1 to m-9, and m-10's first two items.

**Owner decisions:** A to J as disposed in §4; K withdrawn; K′, L and M added; H rewritten (M-3).

**Later-work dependencies:** D-1's foundation re-pin before any CLI binding of a non-Gate-6 store (m-7); WP9.7's
`RegisterArtefact` guard before any live frozen-copy observation (i-5); the WP9.6 brief for the supersession preparer
refusal (m-10).

**Residual risks:** the single model family (P-058); session and producer independence rest on attested strings
however M-3 is decided; §20 item 2 is unprobed until the code PR's end-to-end test.

## 7. Change log and verification

- **This review** adds one file, this report, on `review/w9-wp9-3-note`. The note and every other file are unchanged.
- **Probes.** `wp9-3-note-review-probes.py` in the session notes (SHA-256
  `9f9e43c32caf89766ad9e36f3fa72f60e50d736f572f043a60f395c5cc4d0abb`), run from this worktree with `uv run --extra dev
  python -m pytest --no-cov -q -p no:cacheprovider <file>`: 22 passed. One case at first only printed its schema
  result, and one asserted a wrong row count (277, from the registry's de-duplication). Both were corrected to assert,
  then re-run.
- **Process deviation.** Three read-only one-liners ran through `python -c`, against the brief's rule: printing
  LR-020's fixtures from the catalogue JSON, an import check, and a JSON field listing. None wrote a file, and each
  result was re-derived through the probe file or `git`. Later reads used scripts written with the Write tool.
- **Environment.** The worktree's `.venv` was created with `uv sync --frozen --extra dev`. It is gitignored. No store
  was opened, and no ARS store, legacy file, `.apm/` state, P01 paper or vault backlog was touched.
