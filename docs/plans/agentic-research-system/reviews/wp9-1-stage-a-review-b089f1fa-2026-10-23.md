# Independent adversarial review of W9 WP9.1 stage A (`b089f1fa`)

**Date:** 2026-10-23<br>
**Reviewer:** an independent Claude Code session (Opus 5.5). It did not author the stage A schemas, the bootstrap
contract, the test, the stage note, 06v, W9 or the WP9.0 documents.<br>
**Skill:** `adversarial-design-review` (implementation-conformance mode)<br>
**Verdict:** **REWORK REQUIRED.** 2 Blocking, 7 Major, 12 Minor, 9 Info.<br>
**Known limit (P-058):** every review in this chain, this one included, ran on one model family. This is recorded as a
known limit, not as a finding.

## 1. Subject

Branch `pipe/w9-wp9-1-schemas` at `b089f1fa`, reviewed as a whole over `d660f091..b089f1fa` (three commits on main
`d660f091`). The first commit, `799fba5f`, is labelled "[EXPLORE] … not for review"; its content is part of the subject
because the later commits build on it.

| Path | Content |
|---|---|
| `.research-system/schemas/contracts/w9/*.schema.json` | 17 schemas, `$id` `ars://legacy/<kind>`: 13 records, 4 bootstrap |
| `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml` | The bootstrap contract |
| `tests/research_system/contracts/test_w9_contract_materialization.py` | 33 collected tests |
| `docs/plans/agentic-research-system/transition/w9/wp9-1-stage-a-note.md` | The stage A note |

The schemas were produced by an uncommitted generator. This review covers the committed JSON only.

## 2. Method

**Governing texts read** (paths under `docs/plans/agentic-research-system/` unless stated):
- 06v at `d660f091`: §§2.1, 2.2, 2.3, 2.6, 3 (O-1 to O-38), 4, 5 (WP9.0, WP9.1, WP9.2) and 6 (D-1 to D-9);
- W9 at `d660f091`: §§1, 4, 5.1 to 5.5, 6, 7.3, 8, 12, 13.1, 13.2 and 17;
- register entries P-064 to P-068, including both post-acceptance corrections;
- the accepted WP9.0 documents: `transition/w9/w9-membership-table-template.md`,
  `transition/w9/w9-segmentation-contract-v1.md` and its reference implementation `tools/w9_segmentation.py`;
- the W11 precedent: `.research-system/contracts/w11/w11-materialization-bootstrap-contract.yaml`, the 62 W11 schemas
  (including `w11-common-definitions`, `legacy-record-observed`, the genesis input and the acceptance envelope) and
  `tests/research_system/contracts/test_w11_contract_materialization.py`;
- the core ID grammars in `.research-system/schemas/core/` and the eval `fixture_id` pattern;
- `research_system/schema_registry.py` (registry loading, format checking), `research_system/store/current_binding.py`
  (schema catalogue hash) and `research_system/discovery/runtime.py:586-613` (event schema fallback).

**Log observations applied** (OPEN, tagged to this skill): verify reuse claims against materialized bytes, not prose
(`2026-10-22-spec-reuse-claims-must-diff-against-materialized-schemas`); quote every identifier in a proposed
correction from its owner source (`2026-10-22-reviewer-prescribed-identifiers-copied-unverified`); run a rule on the
bytes it governs (`2026-10-23-segmentation-contract-written-without-target-census`). The last one is why §3.1 B-2 runs
the accepted reference tool's output through the schema it claims to match.

**Probes.** All probes are read-only Python scripts run with `python -I` from the session scratchpad. They construct
synthetic instances in memory and validate them. Nothing was written to the repository, the vault, `.apm/`, any store
or `papers/`. The commands are listed in §8.

## 3. Findings

### 3.1 Blocking

#### B-1 — Every reference field accepts only `obj_` IDs, so no W9 record can cite a W2 Decision, review or artefact.

**Location:** `$defs/recordRef` and `$defs/objId`, inlined identically in all 17 schemas (for example
`legacy-closed-reference-acceptance.schema.json:187-190, 209-226`); `nullableRecordRef` wraps the same definition.

**Claim.** `recordRef.id` is `{"$ref": "#/$defs/objId"}`, and `objId` is
`^obj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`. Every `*_ref` field in the family uses it:
`decision_ref`, `registration_decision_ref`, `acceptance_decision_ref`, `recovery_decision_ref`, `review_ref`,
`reviewer_ref`, `independent_review_ref`, `frozen_copy_ref`, `evidence_refs`, `waiver_ref`, `successor_result_ref`,
`intended_use.successor_ref` and the rest.

**Evidence.**
- W2 Decisions are `dec_` IDs (`core/commands/propose_decision.schema.json`, `new_decision_id` pattern `^dec_…`). W2
  reviews are `rev_` IDs (`core/commands/record_review_verdict.schema.json`, `review_id`). Artefacts are `art_`, events
  `evt_`, tasks `tsk_`. Across `.research-system/schemas/core/`, `^obj_` occurs 16 times, only in the scope-definition,
  task and artefact-registration commands and events.
- Probe `probe_refs.py`: a `recordRef` with an `obj_` ID validates; the same ref with `dec_`, `rev_`, `art_`, `evt_`
  or `tsk_` is **rejected**.
- W11, which the note cites as precedent, types `recordRef.id` as `{"type": "string", "minLength": 1}`
  (`w11-common-definitions.schema.json`, and inlined in `relation-assay-bar-acceptance.schema.json`) and defines
  separate `decId`, `artId`, `asyId` and `spkId` grammars. Its `relation-assay-bar-acceptance` carries a `decision_ref`
  through that untyped ref. W9 narrowed the type without saying so.
- Every test fixture uses `_OBJ = "obj_…"` for every ref, decision refs included (`test_w9_contract_materialization.py:71,
  75-76`), so no test can see the mismatch.

**Failure scenario.** Stage B pins these schema bytes, and Stephen accepts the catalogue. WP9.3's acceptance preparer
must write a `legacy-closed-reference-acceptance` whose `decision_ref` names Stephen's batch Decision `dec_…`
(W9 §8.1 item 3). Validation through the registry rejects it. Either the implementer invents an `obj_` wrapper for
Decisions that no specification defines, or the schema must change after acceptance, which needs a new catalogue
identity and a new owner acceptance.

**Impact.** Validity and migration. The authority links W9 exists to record (Stephen's Decisions, independent reviews,
frozen copies) are unrepresentable with real identifiers.

**Required change.** Before stage B pins anything:
1. Define typed reference grammars and use one per field: for example `decisionRef` (`^dec_`), `reviewRef` (`^rev_`),
   `artefactRef` (`^art_`), `recordRef` (`^obj_`) for W9 records. Record the field-to-ID-kind table in the stage note.
   If a field may name more than one kind, use a `oneOf` over the named grammars, never a free string.
2. Or adopt W11's untyped `minLength: 1` ID and fix each field's kind in the stage B catalogue rows. This is weaker;
   the typed form is recommended.
3. Change the test fixtures to use each field's real prefix, and add one negative control per typed ref (a `dec_` ID
   in an `obj_` field is rejected).

**Affects:** O-7, O-8; every record schema; WP9.2 to WP9.4.

#### B-2 — `legacy-light-inventory` cannot hold the records the accepted segmentation contract requires.

**Location:** `legacy-light-inventory.schema.json:75-194` (`rows` and the top-level properties).

**Claim.** The contract `w9-segmentation/1.0.0` (accepted at exact bytes, P-068 item 2) says its reference tool
"returns rows in the shape of `legacy-light-inventory` rows" (contract §7, line 197), and that where the tool and the
contract disagree, the contract governs. The closed row schema rejects every row the tool emits, and it has no field
for several records the contract requires.

**Evidence.** Probe `probe_attacks.py`, section H, feeds `tools/w9_segmentation.segment()` output on synthetic bytes
through the schema (with `selector_kind` added per row):

| Selector | As emitted | Schema-unknown keys dropped |
|---|---|---|
| `heading_section` | REJECT: `anchor_line_sha256` | valid |
| `tracker_task_row` | REJECT: `anchor_line_sha256`, `task_id` | valid |
| `working_note_entry` | REJECT: `anchor_line_sha256`, `dated` | valid |
| `conventions_unit` | REJECT: `anchor_line_sha256`, `unit_ordinal` | valid |
| `log_frontmatter`, empty file | REJECT: `line_count` 0 < minimum 1, and `anchor_line_sha256` | REJECT: `line_count` 0 |

What the contract requires and the schema cannot hold:
- **The anchor-line SHA-256 per row.** It is the only identity of a structural or blocker row: "It is identified by
  its anchor-line SHA-256" (contract §6.4, line 187). It is also how an inventory checks its declared region (§3).
  Without it, the L-0b export's structural and blocker rows have no identity, and the vault detector cannot locate
  them (§6.5).
- **The empty-file blocker row** (contract §4.5, line 156): "one zero-length blocker row at byte 0". The tool emits
  `line_count: 0`; the schema requires `minimum: 1` (`:142`).
- **The covered-region declaration** (§3, line 64: "Every inventory declares its covered region"), the heading level k
  for `heading_section`, and the **suppressed anchors** with their line, anchor-line SHA-256 and heading text (§3).
- **The unit ordinal** for `conventions_unit` ("recorded, never identity", §3 table), the **dated flag** for
  `working_note_entry` ("The flag is recorded", §3 table), and the task ID.
- **Start and end read times with microseconds** (§5.1, line 160) and the **path form** (§5.2). The schema has one
  `observed_at`, whose `utc` grammar is only `format: date-time` plus `Z$`.

Secondary gaps in the same schema: `independent_reproduction_ref` is nullable although W9 §5.2 lists "an independent
reproduction ref" as a key field; `unit_hash` is not bound to `conventions_unit`; `anchor_text` may be null on an item
row.

**Failure scenario.** The L-0b export (D-7) is taken under the accepted contract and filed as a light inventory. The
anchor-line hashes are dropped to pass validation. The vault detector then cannot identify the legacy region's
structural rows (contract §6.4), so an edit to the page title block goes unflagged. Or an empty stage log's mandated
blocker row is omitted, and W9-T18's closure bijection is computed over an inventory that silently lacks a row.

**Impact.** Validity and migration. A schema Stephen will accept as part of the catalogue contradicts an accepted
contract (P-068). The producer and the consumer of the same record shape are not bound to each other.

**Required change.**
1. Add to each row: `anchor_line_sha256` (`sha256`, or null only for the zero-length row), `unit_ordinal` (integer,
   required for `conventions_unit`, else null), `dated` (boolean, required for `working_note_entry`, else null) and
   `task_id` (required for `tracker_task_row`, else null). Allow `line_count: 0` only when `byte_length` is 0 and
   `blocker_reason` is `unparseable_anchor`.
2. Add to the inventory: the covered-region declaration (one of the two §3 forms, with its resolved line range), the
   heading level, `suppressed_anchors` (line, anchor-line SHA-256, heading text), read start and end times, and the path
   form. Require `independent_reproduction_ref` non-null, or document that the field is filled at a later revision and
   name the command that fills it.
3. Add a test that runs `tools/w9_segmentation.segment()` over the contract's own synthetic vectors (or a subset
   covering every selector and the empty file) and validates the result, wrapped in an inventory, against the schema.
   That test binds the two accepted artefacts. It reads no legacy bytes, so it stays within 06v §4's fixtures rule.

**Affects:** P-068 item 2; D-7 (L-0b); O-20, O-21; W9-T18, W9-T19, W9-T22; WP9.3.

### 3.2 Major

#### M-1 — `writer_classes` is not bound to role or ownership. A legacy file can be registered with a successor writer.

**Location:** `legacy-path-registration.schema.json:107-117`; the `allOf` from `:132` constrains only root kind, path
and mode.

**Claim.** W9 §4.2 item 2 (line 178) prohibits "any successor writer" on a registered legacy file. W9 §4.3 (line 186)
gives a `shared_enforcement_surface` the writer set "ARS reviewed PRs **plus** a §4.2(b) owner note". The schema lets
any role carry any subset of the four writer classes, including none.

**Evidence.** Probe section A, all VALID:
- A1: `role: legacy_research_result`, `writer_classes: [ars_reviewed_pr_with_owner_note]`;
- A7: `role: shared_enforcement_surface`, `writer_classes: [owner_ruling]` (no ARS writer);
- A8: `role: successor_results_root`, `writer_classes: [legacy_lane_commit]`.

**Failure scenario.** WP9.5's first-parent detector (O-9) reads the committed registration manifest to decide which
writes are allowed. A registration admitted by the schema with `ars_reviewed_pr_with_owner_note` on a legacy result
makes a successor PR to that result look permitted.

**Impact.** Validity of the writer registry the detectors rely on.

**Required change.** Add `allOf` branches: `ars_reviewed_pr_with_owner_note` is allowed only for
`shared_enforcement_surface`, and is required there; `successor_results_root` and `legacy_read_only_projection` carry
no legacy writer class (or define a successor writer class for them). Add a test with A1, A7 and A8 as negative
controls.

**Affects:** W9-D5, O-9, O-32; WP9.5.

#### M-2 — The vault alias of `CONVENTIONS.md` is registrable. The note says it is not, and no test covers either claim.

**Location:** note line 64 ("the vault alias is unregistrable"); note §1 line 15 ("plus … the registration bindings");
`legacy-path-registration.schema.json:155-175` (the `conventions_lock` branch); test `:394-405`.

**Claim.** The `conventions_lock` branch forces `repository_root` and `CONVENTIONS.md` only when the role is
`conventions_lock`. Any other role may register `CONVENTIONS.md` at `vault_root`. W9 §7.3 (line 417): "It is
registered at its repository path only; the vault alias is a prohibited read path for observations."

**Evidence.** Probe A2 (`legacy_decision_log_entry`, `vault_root`, `CONVENTIONS.md`) and A2b (`legacy_contract`, same)
are VALID. A2c (`conventions_lock` at `vault_root`) is rejected. The test's only registration test
(`test_registration_binds_the_successor_root_and_rejects_traversal`) exercises `successor_results_root` and two
traversal paths. Neither the `conventions_lock` branch nor the `legacy_manuscript_root` branch is exercised by any
test, although note §1 says the test checks "the registration bindings".

**Failure scenario.** An analyst registers the vault symlink as a `legacy_decision_log_entry`. Observations then read
`CONVENTIONS.md` through the vault alias, which W9 forbids, and the repository check against `4b143c92` (O-12) never
sees those reads.

**Impact.** Validity; and a claimed control with no test (implementation-conformance gap).

**Required change.** Forbid `normalized_path: CONVENTIONS.md` (case-insensitively, given Windows) under `vault_root`
for every role, or forbid any role but `conventions_lock` from naming it. Add tests for A2, A2b and A2c, and for the
manuscript-root branch (a third `papers/` path rejected; each P01 path accepted). Correct note line 15 to list only
what is tested.

**Affects:** W9 §7.3, O-12; the note.

#### M-3 — The W9-T11 "schema half" rests on a self-declared identity kind. W9-T11's own negative control passes.

**Location:** note lines 34-36; `$defs/sourceIdentity` (for example `legacy-observation.schema.json:397-516`);
`legacy-path-registration.schema.json` `source_identity_kind`.

**Claim.** Only the `restricted_untracked_file` branch lacks `frozen_copy_ref`. Nothing ties a restricted file to that
branch. W9-T11's negative control is "observe one [a `*.pkl` or null cache] with a frozen copy in the store; …
rejected".

**Evidence.** Probe B1: `identity_kind: untracked_file`, `path: x/null_cache.pkl`, with `frozen_copy_ref` — VALID.
B1b: a `*.csv` as `vault_file` with a frozen copy — VALID. A6: a `*.pkl` registered as `untracked_file` — VALID. The
test (`:240-248`) only checks the honestly labelled case. P-064 item 9 has accepted the suffix list (`*.csv`, `*.pkl`)
for the store guard (D-9).

**Failure scenario.** An importer, or a careless analyst, labels a null cache `untracked_file`. Every schema check
passes, and the frozen copy lands in the ARS evidence store, which W9 §5.4 forbids.

**Impact.** Restricted-data containment (UKDA terms). The note overstates the protection the schema gives.

**Required change.** Either:
1. add to each non-restricted `sourceIdentity` branch, and to the registration, a `not` over a case-insensitive
   `\.(csv|pkl)$` path pattern, with B1, B1b and A6 as negative controls, and record that the schema copy of the D-9
   list must change with it; or
2. narrow the note's claim to "honestly labelled sources" and add an O-22 obligation row: WP9.3's reader classifies by
   the D-9 list at the store binding's `git_head` and refuses a mismatch, with B1 as its test.

Option 1 is recommended because it is cheap and fails closed; option 2 is the minimum.

**Affects:** W9-T11, O-22, D-9; WP9.3, WP9.7.

#### M-4 — 06v's required acyclicity test is missing, and the W9-T21 test is hollow.

**Location:** 06v WP9.1 Tests, line 325 ("The reference graph between record kinds is acyclic"); test `:185-191`.

**Claim.** No test builds or checks a reference graph. The W9-T21 test asserts that three guessed property names
(`transition_ref`, `citation_status`, `citation_status_ref`) are rejected, which `additionalProperties: false` already
guarantees (and `:127` already tests).

**Evidence.** The references are untyped (W11 precedent, B-1 aside), so no machine-readable kind graph exists in stage
A. A paper root with an added `transition_event_ref` property would pass the T21 test if the schema allowed it, since
the test never enumerates the property set. The note does not list the acyclicity test as deferred to stage B.

**Failure scenario.** A later schema revision adds `legacy-paper-root.transition_event_ref` "for convenience". Every
stage A test still passes, and the W9-T21 cycle (root → transition → mapping → root) becomes expressible.

**Impact.** A planned control is absent; a claimed control is vacuous.

**Required change.** In the test, own an edge table: every ref-bearing field of every record schema → its target
record kind(s). Derive the field set by walking the schemas, and assert it equals the table's key set (closure, so a
new ref field fails until it is classified). Assert the kind graph is acyclic, excluding only the declared same-kind
lineage edges (`recovery.predecessor_root_ref`, supersession), and add a negative control that inserts a
`legacy-paper-root → legacy-ownership-transitioned` edge and expects failure. Also assert `legacy-paper-root`'s property
set equals an owned allowlist.

**Affects:** O-29, W9-T21; 06v WP9.1 Tests.

#### M-5 — `pilot_promotion` cannot express "evidence or waiver" per fixture, so O-37 cannot be checked from the record.

**Location:** `legacy-closed-reference-acceptance.schema.json:71-115`; `threshold_preregistration_sha256` and
`anchors` at `:116-152`.

**Claim.** `fixture_ids`, `evidence_refs` and `waiver_ref` are three unrelated lists. O-37 (06v line 217) requires
"per-item `pilot_promotion` evidence or waiver, with fixture IDs"; W9 §12.3 says an exclusion is "an owner-accepted
record", per fixture.

**Evidence.** Probe E1: fixtures `F-018`, `S-017`, no evidence, no waiver — VALID. E2: the same observation twice in
`items`, with different `pilot_promotion` blocks — VALID. In E1, `threshold_preregistration_sha256` is null and an
anchor's `value` is `not-a-commit` with `anchor_kind: git_commit` — VALID. Anchors are not tied to which hash they
anchor (O-25 needs both the threshold and the governing-record set anchored).

**Failure scenario.** A batch lists three fixtures and one evidence ref. WP9.3 cannot tell which fixture is evidenced
and which is waived, because the record does not say. Or a batch is accepted with a null threshold hash, defeating
W9-T16.

**Impact.** Validity of acceptance; O-25, O-37 and W9-T16 lose their record-level hook.

**Required change.** Replace `pilot_promotion` with an array of `{fixture_id, disposition: evidence | waiver, ref}`
entries, unique by `fixture_id`. Make `items` unique by `observation_ref`, and drop either `items` or the parallel
`observation_refs` list (or test that they hold the same set). Key `anchors` by what they anchor (`threshold`,
`governing_record_set`), and give `git_commit` anchors the `sha1` grammar. State in the note when
`threshold_preregistration_sha256` may be null, or make it required.

**Affects:** O-25, O-37, W9-T16; WP9.3.

#### M-6 — The acceptance envelope drops W11's verifier and test bindings. "Independently verified" is not bound.

**Location:** `w9-catalogue-acceptance-envelope.schema.json:5-19` (required set).

**Claim.** 06v WP9.1 (lines 317-319) says the envelope and contract are "modelled on W11's". W11's envelope requires
`bootstrap_command_schema_identity`, `bootstrap_validator_schema_identity`, `bootstrap_test_identities`,
`independent_observation_ref` and `review_report_ref`. W9's requires none of these; it adds
`bootstrap_contract_identity` and `plan_identity`. W9 §5.3 item 2 (line 262) requires "one independently verified
genesis transaction".

**Evidence.** Required sets read from both schemas (§8, command 7). The note says stage B adds "a materialization
verifier", but the envelope schema stage A fixes has no field that could name it.

**Failure scenario.** Stephen accepts an envelope that binds the catalogue and schemas but not which verifier and which
tests produced the verification. A later change to the verifier leaves the accepted envelope apparently intact.

**Impact.** Provenance of the acceptance; O-3.

**Required change.** Add the verifier identity and the binding-test identities (file identities at exact commit and
blob), plus an independent-observation ref, or record in the note why W9 departs from W11 here. Do it before stage B
pins the envelope schema.

**Affects:** O-3, O-8; stage B.

#### M-7 — The note's "one PR or two (D-6)" misstates the owner authority; deviation 2 needs Stephen's acceptance.

**Location:** note line 26; 06v D-6 (line 568); P-065 item 3 (register line 4229).

**Claim.** The note says "Stages A and B can land as one PR or as two (D-6)". D-6 is "One PR per package. WP9.3 may
split …, and WP9.7 …". It names no split for WP9.1. P-065 item 3: "Each package is one PR".

**Evidence.** Quoted above. Deviation 2 (no event schemas) likewise departs from accepted 06v text ("one … schema per
W9 §5.2 record and per emitted event", 06v WP9.1). The note offers it "for review"; a reviewer cannot amend an accepted
plan.

**Failure scenario.** Stage A merges as its own PR on the strength of the note. That is a second PR for one package
without an owner decision, in a programme where authority boundaries are recorded per decision.

**Impact.** Authority.

**Required change.** Strike "or as two (D-6)", or obtain Stephen's decision and cite it. Ask Stephen to accept
deviation 2 explicitly (the reviewer's view is in §4). Record both in the register or the note.

**Affects:** P-065 item 3, D-6; 06v WP9.1.

### 3.3 Minor

**m-1 — Revision fields let "immutable" records be revised in place.** Every record carries `record_revision` and
`supersedes_revision`. Probe D1: a `legacy-paper-root` at revision 2 superseding 1 is VALID, although W9 §5.2 (line
250) says "the root is never revised", and W9 §13.2 corrects accepted records only by `legacy-record-supersession`
with reviewer and Decision. W11's `legacy-record-observed` has no revision fields. Fix: `record_revision: const 1` and
`supersedes_revision: const null` on records W9 corrects only by supersession, or name the WP9.2 guard that refuses a
revision. Affects §13.2, W9-T14, W9-T21.

**m-2 — Closed-reference transitions may carry mapping and paper-root refs.** Probe C1: `legacy_owned →
closed_reference` with non-null `mapping_ref` and `paper_root_ref` is VALID
(`legacy-ownership-transitioned.schema.json:85-130`). Fix: require both null in branches 2 and 3, or state why not.

**m-3 — `normalized_path` is not normalized; root kind and identity kind are not coherent.** Probe A5 accepts
`results\x.json`, `./CONVENTIONS.md`, `results//x.json`, `results/./x.json`, a trailing space and `~/x`
(`$defs/relPath`, `legacy-path-registration.schema.json:232-236`). A3: `conventions_lock` with
`source_identity_kind: vault_file`; A4: `vault_root` with `git_tracked` — both VALID. Fix: forbid backslashes, `.` and
empty segments and trailing whitespace; bind `vault_root ⇔ vault_file` and `conventions_lock ⇒ git_tracked`.

**m-4 — Observation internals are unbound.** B2: an `inventory_item` selector with `segmentation_contract: null`; B3: a
whole-file JSON observation naming the contract; B5: `resolved_by_precedence` with a null tier and two identical refs;
B6: one family name twice with two W0 classes — all VALID. `families[].family_name` has no grammar, while
`selector.family_names` uses `^[a-z0-9_]+$`; `legacy-paper-citation-status` repeats the inconsistency. Fix: bind each
pair with `if`/`then`; give every family-name field one grammar.

**m-5 — Membership family names may repeat.** Probe F1: two families named `h0` — VALID. Pointer exclusivity across
families (template §3 rule 3) is not expressible in JSON Schema and is W9-T3's runtime job; name uniqueness is cheap to
test. Fix: a test-side or verifier-side uniqueness check now, and note rule 3 as WP9.3's.

**m-6 — Catalogue binding-test grammar is unanchored.** `w9-schema-catalogue-content.schema.json:242` is
`^W9-T[0-9]+`; `W9-T5-not-a-test` and `W9-T99` validate. Duplicate `owner_row_id`s pass when the rows differ, and
`owner_row_count` is not tied to the row array. Fix: `^W9-T[0-9]+$`, and let the stage B verifier check row-ID
uniqueness, the count and that each named test exists in W9 §17.

**m-7 — The genesis input references files and an envelope as `obj_` records.** `bootstrap_contract_ref` and
`external_envelope_ref` (`import-accepted-w9-catalogue-genesis.schema.json:24-29`) are `recordRef`s, but the bootstrap
contract YAML and the envelope have no `record_id` or revision. `requires_w11_genesis_in_store: true` names no W11
identity. Fix: use file identities (path, commit, blob, SHA-256, size), as the envelope does, and name the accepted
W11 catalogue identity.

**m-8 — The contract lacks a statement 06v requires.** 06v WP9.1 (lines 319-320): "The contract states that the W9
runtime cannot produce or accept its own prerequisite." The YAML's `verification_rules` and `forbidden` lists do not
say it. Fix: add that sentence as a verification rule.

**m-9 — Test weaknesses beyond M-2 and M-4.**
- `:136` asserts that the test's own constant starts with `ars://legacy/`; it can never fail. Assert instead that no
  registry ID outside the W9 directory starts with `ars://legacy/`, and that no W9 file's ID starts with
  `ars://portfolio/` or `ars://core/`.
- `:159-171` re-derives each tuple at its pinned commit, so a later edit to W9 or 06v on main goes unseen. Contract
  rule 1 and note line 15 say "against main". Either compare with `HEAD` (or `origin/main`) as well, or drop "main"
  from both texts.
- `:262` deletes only `signature_record_ref`; `signed_w0_revision_ref` has no negative control.
- The fixtures validate without `FORMAT_CHECKER`, while the runtime registry uses it (`schema_registry.py:1496`). Probe
  B4: `created_at: notadateZ` passes the test-style validator and fails the registry's.

**m-10 — The generator is not committed, and the shared definitions are inlined 17 times.** Today all 17 `$defs`
blocks are identical (probe, one distinct block). Every fix to B-1, B-2 or M-3 touches all 17. Fix: a test asserting
the `$defs` blocks are byte-identical across the family, or commit the generator under a named boundary extension (as
P-067 did for WP9.0's tool).

**m-11 — Note editorial.** Line 15 says 32 tests; 33 are collected. The "Registration bindings" bullet (lines 62-66)
sits under §4 (`accepted_w9.py`) instead of §3. Line 18 says the inlining follows "W11's `legacy-record-observed`";
W11 also has a shared `w11-common-definitions` schema, so the precedent is mixed.

**m-12 — Is the test file inside P-065's boundary?** P-065's Boundary line is "Docs and data files only". P-067 had to
extend it by name to a WP9.0 tool and its test. 06v WP9.1 does list "Tests" inside the package P-065 item 2
authorizes, so the file is probably in scope, but the register does not say so. Owner confirmation, one line.

### 3.4 Info

**I-1 — Pinned identities hold.** W9 at `50371fac`: blob `ea3a8e4a…`, 68,637 bytes, SHA-256 `cf5ce671…fac2`. 06v at
`4999111c`: blob `2b40fae4…`, 58,809 bytes, SHA-256 `95e3307a…630`. Both match the contract and are unchanged on
`d660f091`, `b089f1fa` and `origin/main`. Blob `2b40fae4` differs from P-064's accepted revision-4 blob `531348e0` by
exactly the status row, the §9 checkbox and the five lines of P-064's post-acceptance correction (diff, §8 command 5),
so pinning main's bytes is correct. The refused store identity `5e3b95a9…8d69` equals 06v §2.6 and
`.research-system/config/foundation.yaml` at M2 `4d867d85` and at `d660f091`.

**I-2 — Enumerations are W9's exact sets.** Roles: the 13 of W9 §5.2. Identity kinds: the 4 of §5.4. Selector kinds:
the 6 of the segmentation contract §3, plus `whole_file` and `json_family_set`. W0 classes: the 10 of §6.1
("authoritative, qualified" is a qualifier, not a class). Qualifiers: the 4 of §6.4. Transitions: the 3 of §8.2. The
record set is exactly W9 §5.2's 13 records. W9-T5's schema half holds: probe C2 rejects all five illegal pairs.

**I-3 — Fixture IDs match the eval schemas.** `^[FS]-[0-9]{3}$` is the pattern in five eval schemas
(`evaluation-run`, `fixture-definition`, `fixture-grader-manifest`, `fixture-oracle`, `fixture-source-manifest`). The
test uses S-017 and rejects `S-016/OM` (P-066 item 1). The pattern admits IDs outside the effective catalogue (F-001
to F-038, S-001 to S-017; probe E3: `S-999`, `F-000`), which the stage B verifier or WP9.3 should close.

**I-4 — No runtime activation.** The diff touches no file under `research_system/`. No `ars://legacy/` ID is in
`_RUNTIME_BINDINGS`; the 06h census, the T2 protected-tree tests, the W11 materialization and expected-catalogue tests
and the Discovery activation partition all pass (491 passed, §8 command 9). The registry loads the W9 schemas
(`schema_registry.py:1344` globs every `*.schema.json`), which is how 06v m-13 intends W9 to validate content.

**I-5 — This is the first schema-registry input change since M2.** `git diff 4d867d85 d660f091 --
.research-system/schemas` is empty. Stage A therefore changes the `schema_catalogue_sha256` that a store binding
computes at a later `HEAD` (`current_binding.py:201-255, 854-856`). That is expected under 06v §2.6 and D-1 (the Gate 6
store is read only from M2 after the re-pin), but the note should say it, so nobody runs a Gate 6 read from a post-merge
checkout and mistakes the integrity error for corruption.

**I-6 — Deviation 2's evidence is accurate.** W11's contract families are content, relation, artefact and bootstrap,
with no event family, and none of the 62 W11 schemas is an event schema. `discovery/runtime.py:588-613` falls back to
`ars://core/event` 1.0.0 when an event has no producer binding.

**I-7 — The `accepted_w9.py` pointer is in place.** Note §4 cites P-066 item 2, as P-067 item 3 requires.

**I-8 — Some W9-T21 conditions are runtime-only.** A recovery root naming itself as predecessor (probe D3, VALID) and
a recovery root whose `paper_key` differs from its predecessor's cannot be expressed in JSON Schema. They belong to
WP9.2's reducer and WP9.6, as 06v §4 assigns W9-T21.

**I-9 — Bytes and lint are clean.** No W9 schema or the contract has CR bytes or a BOM; `.gitattributes` gives them
`eol=lf`. `ruff check` and `ruff format --check` pass on the test.

## 4. Decision audit

| Decision or rule | Disposition | Reason |
|---|---|---|
| P-064 D-1 (new store; Gate 6 refused) | Keep | The refused identity is correct (I-1) |
| P-064 D-2 (Discovery-style command path) | Keep | Consistent with deviation 2 (I-6) |
| P-064 D-4 (P-059 re-acceptance) | Not engaged | Stage A changes no census row or protected tree (I-4) |
| P-064 D-6 (one PR per package) | Keep; amend the note | M-7 |
| P-064 D-9 (restricted suffix list) | Keep | The schema does not use it (M-3) |
| P-064 D-3, D-5, D-7, D-8 | Not engaged by stage A | D-7's export depends on B-2 |
| P-065 item 2 (WP9.1 scope: data only) | Keep | No runtime code (I-4); boundary wording for the test needs one line (m-12) |
| P-065 item 3 (one PR, review, CodeRabbit, Stephen merges) | Keep | M-7 |
| P-066 item 1 (S-017) | Satisfied | I-3 |
| P-066 item 2 (`accepted_w9.py` in WP9.2) | Satisfied | I-7 |
| P-066 item 3 (W9 §12.3 erratum) | Not engaged | — |
| P-067 item 3 (note cites P-066 item 2) | Satisfied | I-7 |
| P-068 item 2 (`w9-segmentation/1.0.0` accepted) | Keep the contract; amend the schema to it | B-2 |
| 06v WP9.1 deviation 1 (two stages) | Accept, with a condition | W11's `forbidden_in_pr1` precedent is real, and a catalogue that pins schema files by commit cannot precede them. Condition: every schema fix in this review lands before stage B pins any schema, and the package still lands as one PR unless Stephen decides otherwise (M-7) |
| 06v WP9.1 deviation 2 (no event schemas) | Recommend acceptance; owner decision | The evidence holds (I-6). Condition: stage B's rows name every emitted event, and WP9.2 validates each event's payload record through the registry. Stephen must accept the departure from 06v's text (M-7) |
| O-3 (bootstrap contract; verified genesis) | Partly met | M-6, m-7, m-8 |
| O-7 (exact JSON shapes) | Not met yet | B-1, B-2, M-5 |
| O-8 (catalogue accepted at exact identity) | Pending stage B | Blocked by B-1 and B-2 |
| O-22 (restricted bytes) | Overclaimed | M-3 |
| O-25 (thresholds anchored) | Partly met | M-5 |
| O-29 (paper root acyclic) | Partly met | M-4, I-8 |
| O-37 (pilot_promotion evidence or waiver) | Shape inadequate | M-5 |

## 5. Consistency matrix

| Invariant | Enforcement point | Test | Status |
|---|---|---|---|
| The family is exactly W9 §5.2's records | Schema directory | `test_schema_files_are_exactly_the_owned_family` | Holds |
| Schemas are closed and self-identified | Top-level `additionalProperties`, `schema_id` const | parametrized closure test | Holds at the top level; nested `if`/`then` branches are constraints, not open objects |
| W9's enumerations are exact | Enums | none directly | Holds by inspection (I-2); no test pins the enum sets |
| W9 records can cite Decisions, reviews and artefacts | `recordRef` | none | Fails (B-1) |
| Inventory rows carry what the contract records | `legacy-light-inventory` | inventory test with a hand-built row | Fails (B-2) |
| No successor writer on a legacy file | `writer_classes` | none | Not enforced (M-1) |
| `CONVENTIONS.md` registered at its repository path only | `conventions_lock` branch | none | Not enforced for other roles (M-2) |
| No frozen copy of restricted bytes | `sourceIdentity` branches | restricted test, honest label only | Bypassed by labelling (M-3) |
| No return to `legacy_owned` (W9-T5) | `from_mode`/`to_mode` enums and `oneOf` | transition test | Holds (I-2) |
| Paper-root graph acyclic (W9-T21) | Absence of fields | T21 test | Vacuous test; no graph test (M-4) |
| Per-fixture evidence or waiver (O-37) | `pilot_promotion` | closed-reference test | Shape cannot express it (M-5) |
| Thresholds precede the batch (W9-T16) | `threshold_preregistration_sha256`, `anchors` | none | Nullable and unkeyed (M-5) |
| Independently verified genesis (W9 §5.3 item 2) | Envelope | none | Verifier not bound (M-6) |
| Gate 6 store refused (W9-T20) | Contract `refused_store_identities` | contract test | Identity correct (I-1); the guard is WP9.2's |
| Pinned W9 and 06v bytes | Contract `source_spec`, `source_plan` | source-tuple test | Correct at the pinned commits; not compared with main (m-9) |
| No `ars://legacy/` runtime binding | `_RUNTIME_BINDINGS` | activation test | Holds (I-4) |
| W11 tree unchanged | W11 tests | `test_w11_*` | Holds (I-4) |
| Membership binds the accepted table bytes | `applies_to`, `table_sha256` | membership test | Holds for the template's fields; family-name uniqueness open (m-5) |

## 6. Revision plan

**Immediate corrections (author, before stage B pins any schema).**
- B-1: typed reference grammars, real-prefix fixtures and negative controls.
- B-2: the inventory and row fields, and the tool-to-schema binding test.
- M-1 to M-6: the schema branches, the tests and the note corrections named in each finding.
- m-1 to m-11 as listed. m-10's identical-`$defs` test is the cheapest guard for the 17-copy edits these fixes need.

**Owner decisions (Stephen).**
- M-7: confirm one PR for WP9.1, or decide a two-PR split; accept or reject deviation 2.
- M-3: option 1 (schema guard) or option 2 (note plus WP9.3 obligation).
- m-12: confirm that the test file is within P-065.

**Later-work dependencies.**
- Stage B: the catalogue rows name every W9 event (deviation 2's condition); the verifier checks m-6's row rules and
  I-3's catalogue range; the envelope binds the verifier (M-6).
- WP9.2: refusal of record revisions if m-1 is not fixed in the schema; the W9-T21 reducer conditions (I-8).
- WP9.3: W9-T3 exclusivity (m-5), O-37 refusal on the new `pilot_promotion` shape (M-5), and the restricted-file
  classification if M-3 takes option 2.

**Residual risks.**
- The schemas are inert today, so none of these defects can corrupt evidence yet. The risk is acceptance: once
  Stephen accepts a catalogue that pins these bytes, every fix becomes a new catalogue identity and a new acceptance.
- Untyped kind relations (which record a ref names) stay a runtime and catalogue concern even after B-1, as in W11.
  M-4's edge table is the stage A substitute.

## 7. Change log and files edited

- This file only: `docs/plans/agentic-research-system/reviews/wp9-1-stage-a-review-b089f1fa-2026-10-23.md`.
- No subject file was edited.
- No vault, `.apm/`, store, Jira or `papers/` write was made. `git status --ignored` was read on the main checkout's two
  P01 roots (no untracked files); nothing there was opened.

## 8. Commands run

All from the worktree `C:\Users\steph\TDL\.claude\worktrees\nifty-jepsen-515bb4` unless noted. Probe scripts live in
the session scratchpad and were run with `python -I`.

1. `git fetch origin -q`; `git log --oneline d660f091..b089f1fa`; `git worktree list`; `git checkout -q
   pipe/w9-wp9-1-schemas`; `git diff --stat d660f091..b089f1fa`.
2. `git rev-parse <c>:<W9 path>` and `<c>:<06v path>` for `c` in `50371fac 4999111c d660f091 b089f1fa origin/main`.
3. `python -I -c` hashing `git cat-file blob d660f091:<path>` for W9 and 06v (SHA-256 and size).
4. `git show 4d867d85:.research-system/config/foundation.yaml` and `git show d660f091:…/foundation.yaml`, grep for
   `store_identity`.
5. `git diff -U0 531348e0… 2b40fae4…` (P-064's accepted 06v blob against main's).
6. `python -I probe_summary.py <worktree>` (enums, consts, patterns, open nested objects per schema).
7. `python -I probe_defs.py <worktree> <schemas…>` (shared `$defs` identity, used defs, full schema dumps), and a
   `python -I -c` dump of the W11 genesis input and envelope required sets and of W11 `recordRef`.
8. `python -I probe_attacks.py <worktree>` with the repository venv's interpreter (sections A to H above; H imports
   `tools/w9_segmentation.py` by file path and segments synthetic bytes only); `python -I probe_refs.py <worktree>`.
9. `python -m pytest -p no:cacheprovider --no-cov -o addopts="" -q` over
   `tests/research_system/contracts/test_w9_contract_materialization.py`,
   `test_w11_contract_materialization.py`, `test_w11_expected_catalogue.py`, `test_wp6_2_t2_authority_contract.py`,
   `tests/research_system/unit/test_schema_registry.py`, `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`
   and `tests/research_system/unit/test_wp6_6_discovery_activation.py`, with `PYTHONDONTWRITEBYTECODE=1`:
   **491 passed in 238.22 s**. `--collect-only` on the W9 test: 33 tests.
10. `python -m ruff check --no-cache` and `ruff format --no-cache --check` on the test file: clean.
11. A `python -I -c` byte check for CR and BOM over the W9 schemas and the contract; `git check-attr -a` on one schema.
12. `git diff --stat 4d867d85 d660f091 -- .research-system/schemas` (empty);
    `git status --ignored --porcelain=v1 -- papers/P01-A-JRSSA papers/P01-B-JRSSB` on the main checkout (empty).
13. Read-only `grep`/`sed` over the governing texts, the W11 schemas, `research_system/schema_registry.py`,
    `research_system/store/current_binding.py`, `research_system/discovery/runtime.py`, the core command schemas and
    the eval schemas, for the line citations above.
