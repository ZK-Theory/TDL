# WP9.1 stage A: the inert `ars://legacy/` schema family

**Date:** 2026-10-23<br>
**Status:** Revision 3, confirmed (`reviews/wp9-1-stage-a-confirmation-df4ec74d-2026-10-23.md`), with its one Minor
residual r-1 folded in at Stephen's request. It reconciles the review
`reviews/wp9-1-stage-a-review-b089f1fa-2026-10-23.md` and the re-review
`reviews/wp9-1-stage-a-re-review-c17c9e57-2026-10-23.md` (see `reviews/wp9-1-stage-a-reconciliation-2026-10-23.md`),
with Stephen's decisions in P-069 and P-070.<br>
**Package:** 06v WP9.1, stage A of two. Stage A is its own PR (P-069 item 1).<br>
**Implementation authority:** P-065 (WP9.0 and WP9.1 only), with P-069 item 4 naming the test and the generator.
Stage A changes no runtime Python.

## 1. What stage A materializes

| Path | Content |
|---|---|
| `.research-system/schemas/contracts/w9/*.schema.json` | 17 closed Draft 2020-12 schemas, each with `$id` `ars://legacy/<kind>`. **13 records** (W9 §5.2): path registration, field-family membership, light inventory, observation, closed-reference acceptance, adoption decision, discharge relation, paper root, paper citation status, source inventory, transition mapping, ownership transitioned, record supersession. **4 bootstrap schemas:** acceptance envelope, bootstrap contract, genesis input, catalogue content. |
| `tools/w9_schema_gen.py` | The generator of the 17 schemas (P-069 item 4). `--check` compares without writing. A non-runtime tool. |
| `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml` | The bootstrap contract. It contains: W9 (blob `ea3a8e4a`) and 06v (blob `2b40fae4`), each pinned at its reviewed commit; the Gate 6 store identity, which is refused; the accepted W11 catalogue the W9 genesis requires (blob `8d588185`, 136,229 bytes); and the D-9 restricted suffixes. Runtime activation is `forbidden`; the catalogue and the acceptance instance are `forbidden_in_stage_a`. |
| `tests/research_system/contracts/test_w9_contract_materialization.py` | 62 static controls (P-069 item 4). The test owns the expected family set, the reference-kind table and the record edge table (§2). |

**The test checks:**
- the family is closed and self-identified;
- the generator reproduces every byte;
- the 17 inlined `$defs` blocks are identical;
- the `ars://legacy/` namespace holds exactly this family;
- the family loads in the registry and is not runtime-bound;
- no stage A catalogue exists;
- the contract holds its owned values, and its pinned W9 and 06v bytes equal both their reviewed commit and `HEAD`;
- every reference field has its owned kind, and the record graph is acyclic;
- every rule in §2, through negative controls;
- the light inventory holds what the accepted reference tool `tools/w9_segmentation.py` emits, for every selector and
  for the empty file. The tool omits the selector-specific fields that do not apply (`unit_hash`, `unit_ordinal`,
  `dated`, `task_id`) and sets no row `selector_kind`. The test's `_inventory` adapter adds the inventory's selector
  kind to each row and fills the absent fields with null. WP9.3's importer does the same (re-review n-5).

Every shared definition is inlined in each file, as W11's `legacy-record-observed` does, so no schema references
another file. W11 also has a shared definitions schema, so its precedent is mixed. W9 inlines, and guards the copies
with the identical-`$defs` test.

**Effect on a store binding.** Stage A is the first change to the schema-registry inputs since M2 `4d867d85`. A store
binding computes `schema_catalogue_sha256` over every committed schema, so a binding taken at a later `HEAD` differs
from one taken at M2. That is expected (06v §2.6, D-1): the Gate 6 store is read only from M2. A Gate 6 read from a
post-merge checkout will report an integrity mismatch, and that is not corruption.

## 2. Rules the schemas enforce

- **Reference kinds** (review B-1). A W9 record is `obj_`; a W2 Decision `dec_`; a review `rev_`; an artefact `art_`;
  a task `tsk_`. Each reference field takes one named kind, listed in the test's `REF_FIELDS` table.
  - **`anyRef`**, a closed choice over those five kinds, is for a field whose kind W9 does not fix. Those fields are
    the signature record, a `pilot_promotion` evidence ref, an adoption's successor use, the inventory's independent
    reproduction, and the envelope's independent observation. Stage B's catalogue rows, or WP9.2, fix their kinds.
  - **`sourceRef`** is `anyRef` or a source locator (re-review N-2). The locator is either a repository file at a
    commit (path, commit, blob, SHA-256, size, optional line span) or a vault file (vault path, SHA-256, size,
    optional heading anchor), after W11's `sourceRef` `external` form. It is for the fields that W9 lets name a source
    ARS has not observed:
    - a qualifier's source: a review finding, an audit verdict, or a dated vault correction (§6.4);
    - conflicting records: W9-T4 imports `SUPERSEDED.md` lines 69–71 alone, naming the tier-1 file (§6.3);
    - the signed W0 revision, a repository document.

    A locator's path refuses the restricted suffixes.
- **The record graph** (review M-4; re-review N-3). Every field whose definition admits an `obj_` ID is an edge in the
  test's `RECORD_EDGES` table, with the W9 kinds that ID may name. This covers the `recordRef` fields and also the
  `anyRef` and `sourceRef` fields. An empty set means the field names no W9 record.
  - A paper root's qualifier source may name an observation. It may not name a transition, a mapping or a citation
    status.
  - Same-kind edges are declared apart: a recovery root's predecessor, a superseded citation status, and an
    observation naming another as a qualifier source or conflicting record.
  - The graph is acyclic. Two negative controls (a root naming its transition by a new field, or by a qualifier
    source) each make it cyclic.
- **Immutable records and supersession** (m-1; re-review N-4; P-070). Every record has `record_revision: 1` and
  `supersedes_revision: null`. A correction is a `legacy-record-supersession`. Its targets are W9 §13.1–13.2's four
  kinds: an observation, a closed-reference acceptance, an adoption or a mapping. P-070 records §5.2's "observation
  or mapping" row as the narrower restatement. A citation status supersedes through its own `supersedes_status_ref`.
- **Path registration:**
  - **Writers** (M-1; W9 §4.2, §4.3).
    - A legacy role takes only §4.2's three legacy classes.
    - `shared_enforcement_surface` takes exactly `ars_reviewed_pr_with_owner_note`.
    - `successor_results_root` (`results/ars/`) takes exactly `ars_reviewed_pr`, the ARS writer through merged PRs.
    - `legacy_read_only_projection` takes exactly `ars_projection_rebuild` (re-review N-1). The projection lives under
      `.research-system/projections/legacy/` (06v O-16), which is gitignored, and only `ars projection rebuild`
      writes it, from the store. It is never an authority input. It is registered `successor_owned`, at the
      repository root, as `untracked_file`.
    - Both ARS classes are the author's reading. §4.2 defines classes for legacy files only, so they are recorded here
      for Stephen to see at catalogue acceptance.
  - **`CONVENTIONS.md`** (M-2; W9 §7.3). Only `conventions_lock` may name it, at the repository root, as
    `git_tracked`. Any other role naming a `CONVENTIONS.md` path, in any letter case, is rejected, so the vault alias
    is unregistrable.
  - **Roots** (m-3). A vault root holds only `vault_file`, and `vault_file` sits only under a vault root.
    - The successor root is `results/ars/`, `successor_owned`.
    - Manuscript roots are the two P01 roots.
  - **Paths** (m-3; re-review n-1). Paths are relative and use forward slashes only. They may not contain:
    - `.`, `..` or empty segments;
    - a segment ending in `.` or a space;
    - an 8.3 short-name form (`~` and a digit);
    - a backslash, `:`, or a leading `~` or `/`;
    - trailing whitespace.

    A vault path never names `CONVENTIONS.md`, in a source identity or a source locator, so the vault alias is never
    an observation source either (confirmation r-1).

    Win32 strips a trailing dot or space and resolves short names, so those forms would alias another path. A trailing
    `/` marks a directory root. The path grammar cannot close every alias. Full alias closure belongs to the
    handle-bound read, through `physical_identity`.
- **Restricted bytes** (M-3; P-069 item 3; re-review n-2).
  - A path ending `.csv` or `.pkl`, in any case, is rejected in every non-restricted source identity and in a source
    locator.
  - Such a path is registrable only as `restricted_untracked_file`, which has no frozen-copy field.
  - The schema pattern is derived from the generator's `RESTRICTED_SUFFIXES`, which the test holds equal to the
    contract's `restricted_suffixes`.
  - The list changes with D-9.
  - WP9.7's RegisterArtefact guard (O-22) stays the store-side control.
  - D-9 matches suffixes, not content. A `.csv.gz` or a `.pickle` passes, and WP9.3's reader and WP9.7 own that
    scope.
- **Light inventory** (B-2; `w9-segmentation/1.0.0` §3 to §6).
  - **Each row carries:**
    - its selector kind and anchor-line SHA-256;
    - the unit hash and ordinal (`conventions_unit` only);
    - the dated flag (`working_note_entry` only);
    - the task ID (`tracker_task_row` only, `T`-prefixed).

    A field a selector does not emit is null.
  - **Row rules.** An item row has anchor text. A zero-length row is only the empty file's single unparseable blocker
    at byte 0.
  - **The inventory carries:**
    - its selector kind, which every row repeats (re-review n-4);
    - the heading level (`heading_section` only);
    - the covered region: declared for `heading_section`, `fixed_by_selector` for the fixed selectors, and either form
      for `computational_log_entry`;
    - the declared structural ranges and suppressed anchors (`heading_section` only);
    - read start and end times with microseconds;
    - the path form;
    - a required independent reproduction ref.
- **Observation** (m-4). Only an inventory-item selector names the segmentation contract. A conflict resolved by
  precedence names its tier, and a blocked one does not. Family names use one grammar throughout.
- **Closed-reference acceptance** (M-5; O-25, O-37).
  - Each item carries one or more `pilot_promotion` entries: a fixture ID, a disposition (`evidence` or `waiver`) and
    a ref. A waiver's ref is an owner Decision.
  - The threshold pre-registration hash is required.
  - The anchors include one for the threshold and one for the governing-record set. A `git_commit` anchor is a SHA-1,
    and an `ars_event` anchor is an `evt_` ID.
- **Ownership transitions** (W9-T5; m-2). Only W9 §8.2's three transitions are admitted. A transition to
  `successor_owned` names a mapping and a root; a transition to `closed_reference` names neither.
- **Paper root** (W9-T21). Its fields are an owned allowlist with no transition or citation-status field. The record
  graph above is acyclic. A root naming its transition, by a new field or through a qualifier source, fails the check.
- **Acceptance envelope** (M-6). Modelled on W11's, it binds:
  - the catalogue, schema, contract and generator identities;
  - the verifier and the binding-test identities;
  - an independent observation;
  - the independent review;
  - Stephen's Decision.
- **Genesis input** (m-7). It names the bootstrap contract and the envelope as file identities at exact commits. It
  also names the accepted W11 catalogue it requires.
- **Catalogue content** (m-6). Binding tests are `W9-T<n>` exactly.
- **Fixture IDs.** A fixture ID uses the eval schemas' pattern, `^[FS]-[0-9]{3}$`, with no variant suffix (P-066:
  S-017).

## 3. Decisions taken (P-069) and the work they leave

1. **Two PRs.** Stage A merges first. Stage B, which adds the catalogue rows, the envelope instance and the
   materialization verifier, pins the schema files by their commit on main. It ends with Stephen's acceptance of the
   catalogue identity.
2. **No event schemas.** W9 events fall back to `ars://core/event` 1.0.0, as W11's do (`runtime.py:588-613`). The
   conditions are binding:
   - stage B's catalogue rows name every W9 event;
   - WP9.2 validates each event's payload record through the registry.

**Left to stage B's verifier.** These are not expressible in JSON Schema:
- owner-row ID uniqueness, and `owner_row_count` equal to the number of rows;
- every binding test named in W9 §17;
- every fixture ID within the effective catalogue (F-001 to F-038, S-001 to S-017).

**Left to WP9.2 and WP9.3.** These are runtime checks:
- family-name uniqueness within a membership table or an observation, and pointer exclusivity across families (W9-T3,
  template §3 rule 3);
- one entry per fixture within an item, and one item per observation, in an acceptance (`uniqueItems` catches exact
  duplicates only);
- a recovery root that names itself, or whose paper key differs from its predecessor's (W9-T21);
- a supersession that names itself (W9-T14, WP9.6);
- a legacy role registered under `.research-system/projections/legacy/`, and an inverted locator line span
  (confirmation i-1, i-2);
- a read that ends before it starts;
- the W9 kind an `obj_` reference actually names, checked against the edge table (§2);
- the kinds of the `anyRef` fields (§2).

## 4. `accepted_w9.py` is not in WP9.1

06v WP9.1's gate, step 3, says a follow-up commit adds `research_system/legacy/accepted_w9.py`. Under P-066 item 2,
that file belongs to WP9.2, under its own later authorization. 06v's accepted bytes are unchanged (P-067 item 3). This
note, and every WP9.1 or WP9.2 dispatch brief, cites P-066 item 2. WP9.1 ends with Stephen's acceptance of the
catalogue identity, in stage B.
