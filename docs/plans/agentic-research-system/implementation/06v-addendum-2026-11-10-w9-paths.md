# 06v addendum (2026-11-10): W9 paths

| Field | Value |
|---|---|
| Date | 2026-11-10 |
| Status | Dated addendum. It records paths that are already decided and changes no requirement of 06v |
| Amends | Nothing. `06v-w9-implementation-plan.md` stays as accepted at revision 4 (`7b19e40b`, P-064). This file gives a path to each place 06v names without one |
| Authority | P-081 item 4 (owner point D, accepted 2026-10-29): "The W9 evidence area (D) is `.research-system/evidence/w9/`". WP9.3 design note §11.1 (revision 14, `2d9aeddc`). Written on Stephen's approval of the 2026-11-10 system review, Group C2 |
| Code base read | origin/main `0e54de75` |
| Observation | `2026-10-28-shared-location-named-but-never-defined` |

06v names "the W9 evidence area" six times (lines 212, 434, 471, 495, 567 and 570), as the home of files that three
packages write or read, and never gives its path. WP9.3 had to propose one as an owner point. This table is the one place
a W9 package looks up a shared location. A package that adds a shared location adds a row here in the same PR.

## The W9 evidence area

**Path:** `.research-system/evidence/w9/` (P-081 item 4). In code: `EVIDENCE_DIRECTORY` in
`research_system/legacy/evidence.py:28`. The directory is tracked. Readers take each file from Git at the store
binding's `git_head` (`git show <git_head>:<path>`), never from the working tree, and a row whose file is absent
refuses (note §11.1).

| File | 06v reference | Path | Producer | Reader | Format fixed by |
|---|---|---|---|---|---|
| Registration manifest | M-6 (lines 470 and 471) | `.research-system/evidence/w9/registration-manifest.json` (`REGISTRATION_MANIFEST`, `evidence.py:29`) | WP9.5, per batch | WP9.3, LR-015 | WP9.3: `w9-registration-manifest/1` (`evidence.py:31`) |
| Detector control-output hashes | D-5, O-13 (lines 495, 567) | `.research-system/evidence/w9/detector-controls.json` (`DETECTOR_CONTROLS`, `evidence.py:30`) | WP9.5 | WP9.3, LR-003 | WP9.3: `w9-detector-controls/1` (`evidence.py:32`) |
| Shared-surface change list | O-32 (line 212) | in the evidence area; file name not yet fixed | each PR that changes a shared surface | WP9.3, LR-016 and LR-020 | WP9.3-2 |
| Computational-Log export and its retained copy | D-7 (line 434) | in the evidence area; file name not yet fixed | `tools/w9_segmentation.py` at L-0b (segmentation contract §6.1) | WP9.3, LR-011 and LR-015 | the segmentation contract (P-068) and note §11.3 |
| D-9 restricted-suffix list and exemptions | D-9 (line 570) | in the evidence area; file name not yet fixed | WP9.7 | the RegisterArtefact guard, at the binding's `git_head` | WP9.7 |

**Open rows.** Three file names are not fixed on `main`. The package named in the last column fixes each one, and the
PR that does so updates its row here. Until then, each of those packages reads this table, not 06v's prose, for the
directory.

## Other shared W9 locations

| Location | Path | Source |
|---|---|---|
| W9 schema family (`ars://legacy/`) | `.research-system/schemas/contracts/w9/`, exactly its owned files | `SCHEMA_ROOT` and `test_schema_files_are_exactly_the_owned_family` in `tests/research_system/contracts/test_w9_contract_materialization.py:31` and `:316-318` (note §11.1) |
| W9 transition records | `docs/plans/agentic-research-system/transition/w9/` | the WP9.x design notes and records |
| Gate 7+ intake list | `docs/plans/agentic-research-system/implementation/gate7-intake-deferrals.md` | PR #419 |
