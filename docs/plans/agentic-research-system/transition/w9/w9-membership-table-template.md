# W9 field-family membership table: template and authoring guide

**Date:** 2026-10-23<br>
**Status:** Draft, revision 2, `review_pending` (WP9.0; P-065). It reconciles the review
`reviews/wp9-0-review-a427084e-2026-10-23.md` (see `reviews/wp9-0-reconciliation-2026-10-23.md`).<br>
**Authority:** W9 §5.2 (`legacy-field-family-membership`), §6.2, §8.5 item 3 and §8.6; 06v WP9.0 and §7 L-4a<br>
**Implementation authority:** None. This is a template. A real table is authored, reviewed and accepted per file under
06v §7 L-4a, and only after the W9 machinery exists.

## 1. What a membership table is

For one JSON result-file schema, a membership table assigns **every JSON pointer** in the file to exactly one named
**field family**. Any pointer it does not assign goes to `unassigned`, which blocks import (W9 §6.2; W9-T3). W9 imports a
legacy result by family, so that a superseded part of a file (for example an H₁ W₂ family) can never travel with an
authoritative part (for example an H₀ family).

**The table file and the W9 record.** The table is a file whose bytes are reviewed and accepted. It holds no review or
acceptance identity of its own, because those are written after its bytes are fixed (§4). The W9
`legacy-field-family-membership` record (W9 §5.2) is created later. It binds:
- the table's SHA-256;
- the review record that reviewed those bytes;
- Stephen's acceptance of those bytes.

## 2. Who writes it

W9 §5.2 requires the author to be "independent of the importer". The other exclusions below are this template's
additions, which are stricter than W9.
- **Author.** One ARS actor. The author must not be:
  - the importer of the file, which is W9's own exclusion;
  - the observer of the file;
  - the producer of any item that will import from it;
  - the migration analyst, who requests and proposes imports (W9 §8.6) and so must not shape the families the table
    gates.
- **Reviewer.** A different ARS actor, on a session distinct from the author's and from the migration analyst's (W9
  §8.6). The reviewer must not be the author, importer, observer, producer or migration analyst. The reviewer checks
  the table against the file's bytes and the governing records: G7-A §6.1, the audit, `SUPERSEDED.md` and the corrected
  files.
- **Acceptance.** Stephen accepts each table at an exact SHA-256 before the file's first observation (06v L-4a).

## 3. Rules

1. **Parsing.** The table's author and the importer read the file as JSON under these rules:
   - a duplicate object key anywhere is a blocker;
   - the bare tokens `NaN`, `Infinity` and `-Infinity` are accepted as number leaves (16 of 466 committed result JSONs
     hold them), and the observation records that the file holds them;
   - any other departure from RFC 8259 is a blocker.
2. **Exhaustive in both directions.** Every leaf **and** every container pointer present in the file is listed, the
   root pointer `""` included. The importer expands the table's patterns (rule 5) against the observed bytes, then:
   - every observed pointer that no expanded entry covers is `unassigned` and blocks import;
   - every table pointer that the observed bytes do not hold blocks too.
3. **Exclusive.** After expansion, each pointer is in exactly one family.
4. **Containers carry shape only.** A container pointer's membership covers only the container's own shape: an
   object's key set, or an array's length. It never covers its descendants' values. Importing a family imports the
   union of the leaf pointers listed in it, plus the shapes of the containers listed in it. So listing `/result/h1` in
   a metadata family imports none of the H₁ W₂ values beneath it.
5. **Arrays.** A pattern is an RFC 6901 pointer in which a segment that is exactly `[*]` means "every index of this
   array". `[*]` never matches an object key. RFC 6901 has no escape for `[*]`, so if a file holds an object key that
   is exactly `[*]`, the table for it uses no patterns and lists every pointer concretely.
   - An array is **homogeneous** when every element has the same set of pointers relative to the element. A
     homogeneous array may be assigned by pattern, for example `/cells/[*]/h1_w2`.
   - A heterogeneous array is assigned element by element, with concrete indices.
6. **Unprefixed keys are assigned.** Bare keys such as `t_ratio`, `d_perm` or `pvalue_null_draws` must be assigned
   (W9 §6.2). They are where silent mixing happens.
7. **Pointer form.** Concrete pointers follow RFC 6901, so `~` is written `~0` and `/` is written `~1`.
8. **Families come from records, not from names.** Each family cites, as `definition_source`, the record that
   justifies the partition: a G7-A §6.1 row, an audit verdict, a supersession entry or a corrected file. A key's name is
   never the evidence. **The table assigns no W0 class.** W0 classes come only from the signed W0 record at observation
   (O-27).
9. **One schema.** A table covers one file schema. Files that share a schema share a table only if the reviewer
   confirms that their pointer sets are identical.
10. **Bound bytes.** `applies_to` binds the exact bytes the author read: identity kind, blob (if tracked), SHA-256 and
    size. The file's first observation must match those bytes. If it does not, the observation blocks, and the table
    goes back for re-review against the new bytes.

## 4. Template

```yaml
table_id: <w9-membership/<file-schema-id>/v<n>>
file_schema_id: <stable name for the JSON shape, e.g. usoc-headline-frozen-2026-05-28>
applies_to:
  - path: <repository-relative path>
    identity_kind: <tracked_file | untracked_file | restricted_untracked_file>   # W9 §5.4
    git_blob: <blob the author read; tracked files only, else null>
    sha256: <SHA-256 of the bytes the author read>
    size_bytes: <size of those bytes>
parse_notes:
  non_finite_tokens: <true | false>   # whether NaN / Infinity / -Infinity occur (rule 1)
families:
  - name: <family name, e.g. h0_w2>
    definition_source: <record that justifies this partition, e.g. "G7-A §6.1 row T1.37">
    pointers:
      - <RFC 6901 pointer, or a pattern with [*] segments>
  - name: <next family>
    definition_source: <...>
    pointers:
      - <...>
unassigned: []        # must be empty for import
author:
  actor_id: <ARS actor; see §2 exclusions>
  session: <session reference>
# No review or acceptance fields. The W9 legacy-field-family-membership record binds this file's SHA-256 to the
# review record and to Stephen's acceptance (§1).
```

## 5. Worked example (illustrative only, not a real table)

The families W9 §6.2 names for `usoc_headline_frozen_2026-05-28.json` (T1.37) are H₀ W₂ and landscape L², which are
`authoritative`, and H₁ W₂, which is `superseded` by the 2026-07-14 corrected files.

A real table for that file would list:
- every pointer the file holds, under those three families;
- families for any provenance or metadata keys;
- the root `""` and every container, such as `/result` and `/result/h1`, each in one family.

Under rule 4, listing `/result/h1` imports only that object's key set. The H₁ W₂ values stay in their own `superseded`
family.

Whether the H₁ landscape fields belong to the landscape L² family or to the H₁ family is not settled by W9 §6.2's
T1.37 row. The real table's author decides it from G7-A §6.1, and the reviewer checks that decision. The pointers come
from reading the observed bytes, not from this example.
