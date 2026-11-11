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
`research_system/legacy/evidence.py:36` (line numbers as of WP9.3-2). The directory is tracked. Readers take each
file from Git at the store binding's `git_head` (`git show <git_head>:<path>`), never from the working tree, and a row
whose file is absent refuses (note §11.1).

| File | 06v reference | Path | Producer | Reader | Format fixed by |
|---|---|---|---|---|---|
| Registration manifest | M-6 (lines 470 and 471) | `.research-system/evidence/w9/registration-manifest.json` (`REGISTRATION_MANIFEST`, `evidence.py:37`) | WP9.5, per batch | WP9.3, LR-015 | WP9.3: `w9-registration-manifest/1` (`evidence.py:40`) |
| Detector control-output hashes | D-5, O-13 (lines 495, 567) | `.research-system/evidence/w9/detector-controls.json` (`DETECTOR_CONTROLS`, `evidence.py:38`) | WP9.5 | WP9.3, LR-003 | WP9.3: `w9-detector-controls/1` (`evidence.py:41`) |
| Shared-surface change list | O-32 (line 212) | `.research-system/evidence/w9/shared-surface-changes.json` (`SHARED_SURFACE_CHANGES`, `evidence.py:39`; fixed by WP9.3-2) | each PR that changes a shared surface | WP9.3, LR-016 and LR-020 | WP9.3-2: `w9-shared-surface-changes/1` (`evidence.py:42`) |
| Computational-Log export and its retained copy | D-7 (line 434) | in the evidence area; file name not yet fixed. Each accepted export's paths are pinned in its `ACCEPTED_CL_EXPORT` entry (note §11.3) | `tools/w9_segmentation.py` at L-0b (segmentation contract §6.1) | WP9.3, LR-011 and LR-015; WP9.3-2's recheck | the segmentation contract (P-068), note §11.3, and WP9.3-2's `w9-cl-export/1` (`evidence.py:43`; amended 2026-11-11, below) |
| D-9 restricted-suffix list and exemptions | D-9 (line 570) | in the evidence area; file name not yet fixed | WP9.7 | the RegisterArtefact guard, at the binding's `git_head` | WP9.7 |

**Open rows.** Two file names are not fixed on `main`: the export's and the D-9 list's. (WP9.3-2 fixed the change
list's, the third.) The package named in the last column fixes each one, and the PR that does so updates its row
here. Until then, each of those packages reads this table, not 06v's prose, for the directory.

## Other shared W9 locations

| Location | Path | Source |
|---|---|---|
| W9 schema family (`ars://legacy/`) | `.research-system/schemas/contracts/w9/`, exactly its owned files | `SCHEMA_ROOT` and `test_schema_files_are_exactly_the_owned_family` in `tests/research_system/contracts/test_w9_contract_materialization.py:31` and `:316-318` (note §11.1) |
| W9 transition records | `docs/plans/agentic-research-system/transition/w9/` | the WP9.x design notes and records |
| Gate 7+ intake list | `docs/plans/agentic-research-system/implementation/gate7-intake-deferrals.md` | PR #419 |

## Amendments

**2026-11-11, WP9.3-2.**
- **Row "Shared-surface change list".** The file name is fixed as the row's last column asked. The old cells read "in
  the evidence area; file name not yet fixed" and "WP9.3-2". No owner decision was needed: the row named WP9.3-2 as
  the package that fixes it.
- **Row "Computational-Log export and its retained copy", last column.** Its old wording was "the segmentation
  contract (P-068) and note §11.3". Note §12.2 says WP9.3 "fixes the export's format", in
  `research_system/legacy/evidence.py`, so the column now also cites WP9.3-2's `w9-cl-export/1`. The file name stays open. Authority: Stephen, in chat,
  2026-11-11, answering the WP9.3-2 plan's Q3 ("Yes, as recommended", relayed by the Gate 7 handover session). This
  changes an addendum's text, so the WP9.3-2 record lists it as a departure for the merge entry.
- **Line references.** The `evidence.py` line numbers in the table moved when WP9.3-2 added its constants. They are
  re-cited at WP9.3-2's head.
