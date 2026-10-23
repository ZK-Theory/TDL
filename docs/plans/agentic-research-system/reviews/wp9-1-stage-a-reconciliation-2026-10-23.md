# WP9.1 stage A reconciliation: revision 2 against the review of `b089f1fa`

**Date:** 2026-10-23<br>
**Author:** the WP9.1 author session<br>
**Review:** `reviews/wp9-1-stage-a-review-b089f1fa-2026-10-23.md` (commit `d9a7d22b`). Verdict REWORK REQUIRED:
2 Blocking, 7 Major, 12 Minor, 9 Info.<br>
**Owner decisions:** P-069. Stephen chose the recommended option on all four:
- two PRs;
- no event schemas, under conditions;
- a schema guard for restricted paths (M-3 option 1);
- the test and the generator named in the boundary (m-12, m-10).

**Status:** Revision 2 is ready for re-review. It is not accepted.

## 1. Files in revision 2

| File | Change |
|---|---|
| `tools/w9_schema_gen.py` | New and committed (P-069 item 4). The generator, with every schema fix below. `--check` compares without writing |
| `.research-system/schemas/contracts/w9/*.schema.json` | All 17 regenerated |
| `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml` | Adds the required W11 catalogue identity, the D-9 suffix list and four verification rules (m-8, m-9, P-069) |
| `tests/research_system/contracts/test_w9_contract_materialization.py` | Rewritten: 57 tests (was 33) |
| `docs/plans/agentic-research-system/transition/w9/wp9-1-stage-a-note.md` | Revision 2 |
| `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` | P-069 |
| this file | New |

## 2. Dispositions

| Finding | Disposition | Where |
|---|---|---|
| **B-1** every ref is `obj_` only | Fixed. Typed definitions: `recordRef` (`obj_`), `decisionRef` (`dec_`), `reviewRef` (`rev_`), `artefactRef` (`art_`), `taskRef` (`tsk_`), and `anyRef`, a closed `oneOf` over them. Each field takes one, per the test's `REF_FIELDS` table. A walk of every schema must find exactly that table. Negative controls reject a wrong prefix for each typed ref | Generator `DEFS`; test `REF_FIELDS`, `test_every_reference_field_has_its_owned_kind`, `test_typed_references_accept_only_their_kind`; note §2 |
| **B-2** inventory versus the accepted contract | Fixed. Each row gains `anchor_line_sha256`, `unit_ordinal`, `dated` and `task_id`, with per-selector conditions. The zero-length empty-file blocker is admitted, and nothing else at zero length. The inventory gains the selector kind, heading level, covered region (three forms), structural ranges, suppressed anchors, read start and end times with microseconds, path form and a required reproduction ref. A test runs `tools/w9_segmentation.segment()` on synthetic bytes for all six selectors, and on the empty file, and validates the wrapped result | `legacy-light-inventory`; tests `test_inventory_holds_what_the_reference_tool_emits`, `…_empty_file_blocker_row`, `…_binds_selector_fields_region_and_read_record` |
| **M-1** writers not bound to role | Fixed. Legacy roles take only §4.2's three classes. `shared_enforcement_surface` takes exactly `ars_reviewed_pr_with_owner_note`. The two ARS-owned roles take exactly a new class, `ars_reviewed_pr`. The review's A1, A7 and A8 are negative controls | `legacy-path-registration`; `test_registration_writer_classes_follow_the_role` |
| **M-2** the vault alias of `CONVENTIONS.md` | Fixed. Only `conventions_lock` names `CONVENTIONS.md`, at the repository root, as `git_tracked`. Any other role naming a `CONVENTIONS.md` path in any case is rejected. A2, A2b and A2c are tested, plus the manuscript-root branch. The note lists only what is tested | `test_conventions_is_registrable_only_as_the_lock_at_its_repository_path`, `test_manuscript_roots_are_the_two_p01_roots` |
| **M-3** restricted bytes by self-label | Fixed by option 1 (P-069 item 3). Every non-restricted source identity rejects a `.csv` or `.pkl` path in any case. A registration with that suffix must be `restricted_untracked_file`. B1, B1b and A6 are negative controls. The contract carries the D-9 list | `SOURCE_IDENTITY`; `test_restricted_bytes_never_carry_a_frozen_copy`, `test_registration_root_and_identity_kinds_cohere` |
| **M-4** no acyclicity test; hollow T21 test | Fixed. The test owns an edge table (`RECORD_EDGES`) whose keys must equal every W9-record reference field. The graph must be acyclic apart from two declared lineage edges, and a negative control inserts a root-to-transition edge. The paper root's fields are an owned allowlist | `test_record_reference_graph_is_closed_and_acyclic`, `test_paper_root_fields_are_an_owned_allowlist` |
| **M-5** `pilot_promotion` shape | Fixed. Per-fixture entries `{fixture_id, disposition, ref}`, and a waiver's ref is a Decision. Each item needs at least one entry, and items are unique. The parallel `observation_refs` list is dropped. The threshold hash is required. The anchors are keyed by what they anchor, and both must be present; a `git_commit` value is a SHA-1 and an `ars_event` value an `evt_` ID | `legacy-closed-reference-acceptance`; two tests |
| **M-6** the envelope drops W11's bindings | Fixed. It adds the verifier identity, the binding-test identities, an independent-observation ref and the generator identity. The catalogue and contract are file identities | `w9-catalogue-acceptance-envelope` |
| **M-7** one PR or two; deviation 2 | Owner decisions taken (P-069 items 1 and 2). Two PRs as a named exception to D-6. No event schemas, under two binding conditions. The note cites both | P-069; note §3 |
| **m-1** revisions in place | Fixed: `record_revision: 1` and `supersedes_revision: null` on every record. Correction is by supersession | Generator `header`; paper-root test |
| **m-2** closed-reference transitions with refs | Fixed: they require a null mapping and root | `legacy-ownership-transitioned`; transition test |
| **m-3** path normalization; root and identity coherence | Fixed. The path grammar rejects backslashes, `:`, `.` / `..` / empty segments, a leading `~` or `/`, and trailing whitespace. `vault_root` ⇔ `vault_file`, and `conventions_lock` ⇒ `git_tracked` | `relPath`; two tests |
| **m-4** observation internals | Fixed. The segmentation contract is non-null only for an inventory-item selector. A tier is required for `resolved_by_precedence` and null otherwise. Conflicting refs must be unique. One family-name grammar is used everywhere | `legacy-observation`; test |
| **m-5** membership family names may repeat | Recorded as a WP9.3 check, together with pointer exclusivity (template §3 rule 3). Neither is expressible in JSON Schema | Note §3 |
| **m-6** binding-test grammar | Fixed: `^W9-T[0-9]+$`. Row-ID uniqueness, the count and §17 membership are stage B verifier checks | `w9-schema-catalogue-content`; note §3 |
| **m-7** genesis refs | Fixed. The contract and envelope are file identities, and the required W11 catalogue identity is named. It was verified against `HEAD`: blob `8d588185`, 136,229 bytes, SHA-256 `7e36b39a…5860b80`. This matches the W11 PR #248 review's direct read | `import-accepted-w9-catalogue-genesis`; contract; test |
| **m-8** the prerequisite sentence | Added as a verification rule, and the test asserts it | Contract; test |
| **m-9** test weaknesses | Fixed: a registry-wide namespace test, the source tuples compared at `HEAD`, a negative control for `signed_w0_revision_ref`, and `FORMAT_CHECKER` in every validation (with a `notadateZ` control) | Test |
| **m-10** generator and 17 copies | Fixed. The generator is committed (P-069 item 4), and tests assert byte reproduction and identical `$defs` | Two tests |
| **m-11** note editorial | Fixed in revision 2 of the note | Note |
| **m-12** test within P-065 | Settled by P-069 item 4 | P-069 |
| I-1, I-2, I-6, I-7, I-9 | Recorded; no change | — |
| **I-3** catalogue range | A stage B verifier check | Note §3 |
| **I-4** no runtime activation | Still true: no file under `research_system/` changes | — |
| **I-5** schema catalogue hash | Stated in the note | Note §1 |
| **I-8** runtime-only T21 conditions | WP9.2's | Note §3 |

## 3. Interpretations for the re-reviewer to check

1. **`ars_reviewed_pr`.** W9 §5.2 says writer classes come from §4.2, which defines classes for legacy files only.
   The two ARS-owned roles needed a writer, so this revision adds `ars_reviewed_pr` and gives it to those roles
   exclusively.
2. **`anyRef` fields.** W9 does not fix the target kind of seven fields (note §2). They take a closed choice of five
   kinds, not a free string, and the note names who fixes them.
3. **Supersession targets.** `legacy-record-supersession` may name an observation or a mapping, which is W9 §13.2's
   "erroneous accepted observation or mapping". The edge table records both.

## 4. Verification

- **Stage A test:** 57 passed.
- **Mutation probe.** The probe removed nine of the new guards one at a time: the legacy writer rule, the
  `CONVENTIONS.md` rule, the restricted-suffix registration rule, the restricted path in `untracked_file`, the
  observation selector binding, the zero-length row rule, the heading-section region rule, the anchor coverage and the
  closed-reference null refs. Each time, the owning test failed. Afterwards the schemas were restored and
  `--check` passes.
- **Related suites.** The reviewer's command 9 set, plus the segmentation vectors, was re-run: 551 passed and 1
  skipped, in 510.87 s.
- **Lint.** `ruff check` and `ruff format` are clean on the generator and the test.

## 5. Not done

- Stage B: the catalogue, the envelope instance and the verifier.
- No push, no store, no legacy write.
