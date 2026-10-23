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

## 5. Revision 3: the re-review's findings

The re-review (`reviews/06v-w9-plan-re-review-db92045f-2026-10-23.md`, `d7f149ff`) returned REWORK REQUIRED (narrow),
with 0 Blocking, 2 Major, 5 Minor and 4 Info. Every revision 1 finding is closed in substance.

**Verification before writing (as Stephen asked).** The author re-read each mechanism the re-review prescribes, at
`e82f9630`:
- `identity.py:333-362` (`build_store_origin_witness`, `persist_store_origin_witness`)
- `identity.py:607-651` (`_validate_manifest_identity`, `load_store_manifest_unbound`)
- `identity.py:818-829` (`initialize_control_store`'s 1.0.0 manifest)
- `identity.py:857-875` (`load_store_manifest`)
- `register_artefact.schema.json:113-122`
- `use_resolver.py:308-318`
- `spec_source.py:268-271,302-305`
- `discovery/spec.py:343-352` (root tokens)
- `artefacts/runtime.py:31-50` (the content reader)
- `driver.py:379-408,665-670`
- every `shared_event_partition` caller

**What the verification changed.**
- **N-2's prescription holds only in part.** `load_store_manifest_unbound` reads without the control-root path check,
  as the re-review says. But its identity validation is version-dependent:
  - for a **1.1.0** manifest it requires `store_identity` to equal a SHA-256 over `store_nonce`, `project_id` and
    `bootstrap_manifest_sha256` (`:623-633`);
  - only the **1.0.0** form accepts an arbitrary 64-hex identity.
  
  A W9-T20 fixture can therefore carry the frozen Gate 6 identity only in the 1.0.0 form. Revision 3 says so, and
  explains it in §2.6.
- **N-1's "resolve `root_id` to its registered physical root" has two consequences.**
  - The only artefact content reader accepts `root_id == "control"` alone (`artefacts/runtime.py:38-50`), so how
    successor results in the repository's `results/ars/` are registered and read is open. This is now **U-8**.
  - Rule (e), refusing an unresolvable root, is needed for the guard not to be bypassable, so it goes to D-9 with
    rule (d).
- **n-1's consumer list.** `spec_assay.py:84` is the import; the consumer is `spec_assay.py:1133`. Revision 3 cites
  `:1133`.

| Finding | Change in revision 3 |
|---|---|
| **N-1** RegisterArtefact guard too broad and bypassable | WP9.7 and §2.7 now resolve `root_id` through the binding's root tokens and normalize the joined path, refusing `..`, absolute and alias forms. The rules are: (a) a registered legacy file; (b) the `repo` root under `results/` outside `results/ars/`; (c) a registered restricted identity or `PROJ_ROOT`'s restricted area; (d) a D-9 suffix on every root; (e) an unresolvable `root_id`. "Null caches" go through rule (c). Negative controls are added: a root inside `results/`, a `..` path, an alias form, an unresolvable root, and a non-`results/` path under a non-code root (must not fire). New **D-9** and **U-8**. |
| **N-2** W9-T20 copy case refused before the W9 guard | WP9.2's guard reads with `load_store_manifest_unbound` first, refuses on the frozen identity, and only then binds. W9-T20's fixture writes a 1.0.0-form manifest and witness through `build_store_origin_witness` and `persist_store_origin_witness`. Its original-path and copy cases both assert the W9 reason code, and a different-identity case passes the guard. |
| n-1 U-7 confinement | U-7 and WP9.2 now name three sites: the `projection/replay.py` predicate, a **new** `legacy` partition value in `shared_event_partition`, and one `continue` branch in `driver.py`. Reusing an existing value is forbidden. A consumer test covers `runtime.py:2214,2254`, `spec.py:284` and `spec_assay.py:1133`. The §8 stop rule is updated to match. |
| n-2 D-4 workability | Command-adding packages merge one at a time. Re-acceptance is of the bytes in the merge-queue entry, and a rebase needs a re-look. The T2 validator expectations and their seal are added to the byte list. |
| n-3 D-7 and L-0b timing | The segmentation contract is reviewed and accepted together with the export, ahead of the rest of WP9.0, so L-0b waits for no code package. WP9.3's exporter later reproduces the hashes. |
| n-4 O-34 seam | New §2.7 row and **U-9** cover the use-time re-hash path for an adopted restricted input, which cannot travel as an artefact under rule (d) |
| n-5 detector rule 3 | The detector fails only on a shared-surface change **without** the §4.3 note. Every change is appended to a committed change list, and WP9.3's acceptance preparer reads that list at the binding's `git_head`. |
| I-1, I-2, I-4 | Noted |
| I-3 manifest lag | Taken in: the registration manifest is exported in the same batch, before its first observation |

**Owner decisions after revision 3:** D-1 to D-9. D-9 is new: the reach of the RegisterArtefact guard over every
producer in the Gate 7 store, and the exact restricted-suffix list.
