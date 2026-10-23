# 06v reconciliation: revision 1 → revision 2

**Date:** 2026-10-23
**Author:** the 06v author session
**Review reconciled:** `reviews/06v-w9-plan-review-2a3940e2-2026-10-23.md` (`b3fe778c`). Verdict: REWORK REQUIRED (0
Blocking, 8 Major, 13 Minor, 6 Info).
**Subject after reconciliation:** 06v revision 2, in the commit that adds this file
**Runtime authority:** none. Author reconciliation is not acceptance.

**Verification before writing.** The author re-read the new seams the review cites, at `e82f9630`:
- `projection/replay.py:1125,1319-1324,1369-1381`
- `discovery/routes.py:301-319`
- `discovery/replay/driver.py:66-75,394-401`
- `discovery/runtime.py:192-198,203-208,576-582,2608-2611`
- `schema_registry.py:1547-1549`
- `create_task.schema.json:264`
- `register_artefact.schema.json:119`
- `service.py:4382,6019`
- `store/identity.py:824,857`
- `check_merge_admission.py:703-709`
- `.research-system/config/foundation.yaml`, unchanged from M2 `4d867d85` to `e82f9630`

Each cited range says what the review says it does.

## 1. Major findings

| Finding | Disposition | Change |
|---|---|---|
| **M-1** shared-ledger replay unmapped | Fixed | New §2.2 row "Shared-ledger replay", plus the writer-lock row. WP9.2 adds the legacy predicate consulted by `projection/replay.py` and `shared_event_partition`, the lazy `replay_legacy`, and the three-root `CompositeWriterLock`. It also adds the mixed-ledger replay test, whose negative control removes the predicate. U-7 asks whether the edit can be confined to a predicate; if it cannot, the package stops and returns Partial (§8). |
| **M-2** U-1 already answerable | Fixed | U-1 is removed. §2.2 now states as fact that each command needs one `ars://core/command` row and that events fall back to `ars://core/event`. §2.3 adds the consequence that every package adding a command changes the census. D-4 is now per package (option (b)), with the 06h manifest YAML named. The expected packages are listed in §5. |
| **M-3** successor-side seams unmapped | Fixed | New §2.7 table maps each successor-side test to its module, line and field: T8 to the CreateTask preparer and `source_import_refs`; T10 and T11 to the RegisterArtefact preparer and `manifest.relative_path` (the Task has no output field); T12 to the ClaimDispatch preparer; T16 to the W9 acceptance preparer; and T17's W5 clause to `research_system/assurance/`. U-5 covers the T8 refs and U-6 the W5 hook. D-2's rationale now reads "keeps the legacy commands out of the protected trees". WP9.4 and WP9.7 carry the guards. |
| **M-4** Gate 6 refusal had no identity source | Fixed | New §2.6 freezes `store_identity`, `project_id` and `origin_witness_sha256` from `foundation.yaml` at M2. WP9.2 refuses by `store_identity` through `load_store_manifest`, with its own reason code. W9-T20 now runs on a scratch store carrying the frozen identity under a valid test foundation, plus a copy at a second path. D-1 states the re-pin's consequence. |
| **M-5** §7 narrower than its owners; L-1 wrote legacy surfaces | Fixed | §7 now opens by making W9 §4.5, §8.5 and the 04-plan per-item conditions operative, and its gate column adds only what they lack. L-1's controls run on a scratch clone or a byte copy, never on `main` or the vault. New L-4a covers membership tables. L-4 adds the governing-record set and the `pilot_promotion` evidence or waiver refs; WP9.1 adds the acceptance fields and WP9.3 enforces them. L-5 adds the project-use acceptance writer condition. The batch checklist adds post-batch S-014 replay and restore. |
| **M-6** detector had no registry, and its key failed under squash | Fixed | WP9.5 reads a committed, Git-anchored registration manifest exported per batch, with a test against the store. §4.2 records are keyed by PR number plus old and new blobs, mapped from the squash commit through the existing queue derivation. Negative controls use a fixture registry in a scratch clone. W9-T7 is marked slow. |
| **M-7** register missed obligations | Fixed | Added O-32 to O-38 with packages and tests. O-38 is out of scope (W11 machinery). The "none dropped" line is replaced by the list of sources scanned. |
| **M-8** baseline export waited for full implementation | Fixed, as an owner decision | New D-7 and L-0b: the export is taken as soon as Stephen authorizes it, either as a reviewed byte copy under the segmentation contract or once WP9.3's exporter merges. The classified list then goes to him for acceptance. |

## 2. Minor findings

| Finding | Change |
|---|---|
| m-1 append-site wording | WP9.2: "its own single append site … no other module appends" |
| m-2 genesis guards omitted | Pre-lock payload check and route-registry partition check added, with the negative control "a catalogue row with no route and no recorded exclusion" |
| m-3 subject-kind enum | WP9.2 reuses existing kinds (`scope_definition`, `review`, `decision`). A new kind is out of scope. |
| m-4 citation drift | `layout.py:19,56`; `identity.py:857`; `wp6_2_t2_authority_validation.py:244-245,252-268`. §2.5 adds `materialize_context_routing_fixtures.py:215` and the F-031 oracle. §2.3 names the 06h manifest. |
| m-5 W9-T21 mapping | §4 now maps W9-T21 to WP9.1, WP9.2 and WP9.4 |
| m-6 extractor scope | D-3 and WP9.4 cover every file type in the root, including scripts. The extractor reads observed bytes, read by a non-author, and its results are projected from files to families through the membership tables and the artifact map. |
| m-7 segmentation rule | WP9.0 adds a versioned segmentation contract, and every observation records UTC time |
| m-8 D-1 operational choices | D-1 now covers the project ID (reuse), binding advance per code change, and runbook A1 to A7 as separate authorizations |
| m-9 meaning of "precedes" | An anchor is an ancestor commit of the binding's `git_head` at the first acceptance, or an ARS event at a lower global position (WP9.3) |
| m-10 gates not slated for the register | §9: Stephen's acceptance of the plan and of D-1 to D-8 is recorded as a register entry |
| m-11 fixture provenance; T7 cost | §4 adds a fixture manifest with blob re-derivation. W9-T7 clones from the local object store and is marked slow and integration. |
| m-12 U-3 fallback narrows W9-D5 | Now D-8, an owner decision, not a package fallback |
| m-13 runtime activation of `ars://legacy/` | WP9.1: the schemas are validated directly through the registry and are not runtime bindings. A test asserts no `ars://legacy/` ID in `_RUNTIME_BINDINGS`. |

## 3. Info and owner-decision dispositions

- **I-1, I-2:** noted; §2.1 states both.
- **I-3:** taken in. The W11-genesis check reads the replayed Discovery projection.
- **I-4:** taken in, through M-4's design.
- **I-5:** noted in §2.4.
- **I-6:** the P-058 known limit, noted in §9.

| Decision | Reviewer | Revision 2 |
|---|---|---|
| D-1 | Amend, then accept | Amended with the frozen identity, the re-pin consequence, the project ID, binding advance and A1 to A7 |
| D-2 | Accept with conditions | Conditions written into the decision and into WP9.2 and §2.7 |
| D-3 | Accept "both", amended | Amended per m-6 |
| D-4 | Amend | Per package, with the 06h manifest and a register entry per re-acceptance |
| D-5 | Accept, amended | A positive execution record for each run; a missed run blocks the next batch |
| D-6 | Accept | WP9.7 may split along §2.7 |
| D-7 (proposed) | For Stephen | Added |
| D-8 | — | New, from m-12 |

## 4. Not changed

The review's direction stands, as does every unflagged part of revision 1. W9 itself is not touched.
