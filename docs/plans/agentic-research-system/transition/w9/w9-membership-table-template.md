# W9 field-family membership table: template and authoring guide

**Date:** 2026-10-23<br>
**Status:** Draft, revision 1, `review_pending` (WP9.0; P-065)<br>
**Authority:** W9 §5.2 (`legacy-field-family-membership`), §6.2 and §8.5 item 3; 06v WP9.0 and §7 L-4a<br>
**Implementation authority:** None. This is a template. A real table is authored, reviewed and accepted per file under
06v §7 L-4a, and only after the W9 machinery exists.

## 1. What a membership table is

For one JSON result-file schema, a membership table assigns **every JSON pointer** in the file to exactly one named
**field family**. Any pointer it does not assign goes to `unassigned`, which blocks import (W9 §6.2; W9-T3). W9 imports a
legacy result by family, so that a superseded part of a file (for example an H₁ W₂ family) can never travel with an
authoritative part (for example an H₀ family).

## 2. Who writes it

- **Author.** A non-author, independent ARS actor. It must not be the importer or the observer of the same file, and it
  must not be the item's producer (W9 §5.2: "author identity (independent of the importer)").
- **Reviewer.** A different independent actor, who checks the table against the file's bytes and the governing
  records (G7-A §6.1, the audit, `SUPERSEDED.md`, the corrected files).
- **Acceptance.** Stephen accepts each table at an exact hash before the file's first observation (06v L-4a).

## 3. Rules

1. **Exhaustive.** Every leaf **and** every container pointer present in the file is listed. List the containers
   (objects and arrays) explicitly, so that an added key under a container is caught.
2. **Exclusive.** Each pointer is in exactly one family.
3. **Unprefixed keys are assigned.** Bare keys such as `t_ratio`, `d_perm` or `pvalue_null_draws` must be assigned
   (W9 §6.2). They are where silent mixing happens.
4. **Arrays.** An array of homogeneous records is assigned as a whole, with its pointer pattern
   (`/cells/*/h1_w2`). An array of heterogeneous records is assigned element by element.
5. **Pointer form.** Pointers follow RFC 6901, so `~` is written `~0` and `/` is written `~1`.
6. **Families come from records, not from names.** Each family cites the record that defines its class: a G7-A §6.1
   row, an audit verdict, a supersession entry or a corrected file. A key's name is never the evidence.
7. **One schema.** A table covers one file schema. Files that share a schema share a table only if the reviewer
   confirms that their pointer sets are identical.

## 4. Template

```yaml
table_id: <w9-membership/<file-schema-id>/v<n>>
segmentation_contract: n/a  # JSON tables use pointers, not segmentation
file_schema_id: <stable name for the JSON shape, e.g. usoc-headline-frozen-2026-05-28>
applies_to:
  - path: <repository-relative path>
    git_blob: <blob at the observation commit>
families:
  - name: <family name, e.g. h0_w2>
    class_source: <record that sets this family's W0 class, e.g. "G7-A §6.1 row T1.37">
    pointers:
      - <RFC 6901 pointer or pointer pattern>
  - name: <next family>
    class_source: <...>
    pointers:
      - <...>
unassigned: []        # must be empty for import
author:
  actor_id: <independent ARS actor>
  session: <session reference>
review:
  reviewer_actor_id: <different independent actor>
  verdict_ref: <review record path and commit>
acceptance:
  decision_ref: <Stephen's acceptance record>
  table_sha256: <hash of this file's bytes at acceptance>
```

## 5. Worked example (illustrative only, not a real table)

The families W9 §6.2 names for `usoc_headline_frozen_2026-05-28.json` (T1.37) are H₀ W₂ and landscape L², which are
`authoritative`, and H₁ W₂, which is `superseded` by the 2026-07-14 corrected files. A real table for that file would
list every pointer the file holds under those three families, plus families for any provenance or metadata keys. The
pointers come from reading the observed bytes, not from this example.
