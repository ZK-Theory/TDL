# WP9.5 owner-decision amendments (2026-11-24)

| Field | Value |
|---|---|
| Date | 2026-11-24 |
| Status | **Accepted by Stephen, 2026-11-24** (P-090 item 6), after an independent review and a re-review (`reviews/wp9-5-amendments-review-2026-11-24.md`, `reviews/wp9-5-amendments-re-review-2026-11-24.md`). Each amendment takes effect when the WP9.5 code PR that implements it merges. |
| Amends | §1: the WP9.3 gates (the WP9.3 design note §10.4 and §11.1, and the formats in `research_system/legacy/evidence.py`). §2: W9 §4.2 (`design/09-migration-compatibility-and-pilot.md`). §3: two paragraphs of the `CONVENTIONS.md` bullet at lines 713 to 758, and one sentence of the next. §4: `implementation/06v-addendum-2026-11-10-w9-paths.md`. |
| Authority | P-090 items 2 and 3 (Stephen's owner-point decisions on the WP9.5 design note, 2026-11-23), and P-090's widened boundary. |
| Design source | `transition/w9/wp9-5-design-note.md` at revision 8, with the gate results recorded at `79d8a684`: §5.3, §6.5 (Rule 3), §8.4, §16.1, §16.3, §16.5, §16.6, §16.9, §16.10. |
| Code base read | `dbd54fe3`. Line numbers below are at that commit. |

This file writes out the text each P-090 decision changes, in one place, so each change can be reviewed and accepted
before code relies on it. It decides nothing that P-090 does not. Where the design note leaves a detail to the code
task, this file says so and does not fill it in.

## 1. WP9.3 gate amendment (Options A1, D3, E1 and J1)

These four options change accepted WP9.3 code under `research_system/legacy/`. P-090's boundary allows exactly these
changes, in `evidence.py`, `acceptance.py`, `preparers.py` and `accepted_w9.py`, and the test builders A1 names.
The tests these options change are covered by P-089's boundary ("its tests"), and the note lists D3's under
"Records" (§16.5). P-090 itself names only A1's test builders. **Stephen to confirm** that D3's and E1's test changes
are inside the boundary.

None of these files is a D-4-protected identity. The protected identities are listed in note §2.2:
`schema_registry.py`, `authority.py`, the 06h manifest and its smoke test, `tools/w9_segmentation.py`, `IMPORTER_MODULES`, and the census
and T2 identities. No D-4 is expected. The code PR re-checks the 275-row census anyway.

**WP9.4's recorded counts** (P-090 item 2, A). The code PR re-runs both WP9.4 integration files after the change. It
also re-runs the unit and WP9.3 files the WP9.4-1 record cites (`wp9-4-1-record.md:110,127-130`), which A1, D3 and E1
change. It then appends a dated re-record to `wp9-4-1-record.md` and `wp9-4-2-record.md`, keeping the original counts.
WP9.4's production code is untouched.

### 1.1 A1: the registration manifest becomes `/2`

**Now.** `REGISTRATION_MANIFEST_FORMAT = "w9-registration-manifest/1"` (`evidence.py:40`). `require_registered`
(`evidence.py:114-131`) requires a closed body `{format, registrations}` and closed entries
`{root_kind, root_id, normalized_path}`, and it refuses unless the registration's three identity values appear as an
entry. LR-015 calls it (`preparers.py:1215-1218`).

**After.**
- `REGISTRATION_MANIFEST_FORMAT = "w9-registration-manifest/2"`.
- Each entry is closed on five keys: `root_kind`, `root_id`, `normalized_path`, `role` and `source_identity_kind`.
- `role` and `source_identity_kind` take the enums of `legacy-path-registration.schema.json`, which a registration
  record already carries as top-level fields (lines 70 to 94).
- `require_registered` finds the entry whose three identity keys equal the registration's. More than one such entry
  is refused as malformed. The entry's `role` and `source_identity_kind` must then equal the registration's, or the
  call refuses with "W9 registration manifest entry does not match the registration".
- Two of these rules are deliberately stricter than the note, which checks the two fields "when present" and puts
  uniqueness at export time (§5.3 item 3):
  - the equality is unconditional, because the schema requires both fields;
  - a duplicated triple is refused at LR-015 too, because the store already forbids two registrations on one triple
    (`reducers.py:540-585`).
- Membership is still decided by the three identity keys. LR-015 now also refuses an entry with the right triple but
  the wrong role or kind. The two new keys let the detector exclude registrations it must not judge (note §6.5
  Rule 1).

**Unchanged.** The file's path, that it is read at the binding's `git_head`, and LR-015's place in
`prepare_observation`.

**Tests and records.**
- `tests/research_system/unit/test_w9_evidence.py`: the `REGISTRATION` and `MANIFEST` constants (lines 28 and 29),
  the positive case at line 34, and the refusal cases at lines 60 and 62.
- The three test builders that create `/1` manifests: `tests/research_system/integration/w9_runtime_harness.py:450-466`,
  `test_w9_wp9_4_1_runtime.py:92-109` and `test_w9_wp9_4_2_runtime.py:80-100`. They key entries on the path alone. The
  builder must take role and kind from the registration it serves, which each `register(path, role=, kind=)` call
  already supplies (`w9_runtime_harness.py:142-166`).
- New negative controls: a role mismatch, a kind mismatch, and a duplicated triple.
- These tests certify the gate, not the exporter. The exporter's `--check` is the store-equals-manifest check.
- The WP9.4 re-record is in the preamble above.

### 1.2 D3: the shared-surface change list becomes `/2`, blob-keyed

**Now.** `SHARED_SURFACE_CHANGES_FORMAT = "w9-shared-surface-changes/1"` (`evidence.py:42`). Entries are closed on
`{merge_commit, surface, affected_registrations}` (`_change_entries`, `evidence.py:231-252`). `check_change_list`
(`acceptance.py:121-136`) refuses an affected item unless the entry's `merge_commit` is an ancestor of the
observation's `git_commit`. Under the squash merge queue, the PR that adds an entry cannot know its own merge
commit: this is O-32.

**After.**
- `SHARED_SURFACE_CHANGES_FORMAT = "w9-shared-surface-changes/2"`.
- Entries are closed on `pr_number`, `surface`, `old_blob`, `new_blob` and `affected_registrations`:
  - `pr_number` is a positive integer or `null`, never a `bool` (as `require_cl_export` already checks,
    `evidence.py:301`). The gate accepts either. Whether a `null` entry backs a Rule 3 acknowledgement for an unmapped
    commit is the detector's check, not the gate's (note §6.2.2 item 3.4);
  - `surface` is a canonical repository-relative path (`_is_canonical_relpath`, `evidence.py:446`), since it is now
    used as `f"{commit}:{surface}"` (`evidence.py:184`). Today's fixtures use the placeholder `"a shared surface"`
    (`test_w9_evidence_acceptance.py:60`, `test_w9_wp9_3_2_runtime.py:377`), so they change;
  - `old_blob` and `new_blob` are 40-hex blob ids. A surface the change creates has the all-zero id as `old_blob`. A
    surface it deletes has the all-zero id as `new_blob`, and such an entry never admits an affected item;
  - `affected_registrations` keeps its present member rule (non-empty strings, `evidence.py:243-249`).
- `check_change_list` keeps the `git_tracked` requirement (`acceptance.py:133-134`) and replaces the ancestry test
  with a tree-state test. For each entry that affects the item, let `b = blob_at(repository_root, <the observation's
  git_commit>, entry["surface"])` (`evidence.py:179-188`). The item passes that entry only if `b` is in
  `Accept(entry)`.
  - `Accept(entry)` holds the entry's `new_blob`, plus the `new_blob` of every entry for the same surface reachable
    from it by following links: an entry links to the next when that entry's `old_blob` equals its `new_blob`.
    Links are never followed through the all-zero id. A deletion ends a chain, and a later re-creation starts a new
    one, so an item observed before a deletion cannot pass by way of a later re-creation (re-review R-m1).
  - Link-following stops at a blob already collected, so a cycle terminates. An entry that no other entry's
    `old_blob` matches has `Accept = {new_blob}`.
  - **List position is never used.** A Rule 3 late entry is appended after the entries for later changes (Rule 0.2
    keeps the list append-only), so "later in the list" is not "later in time" (review A-M1).
  - A surface absent at the observation commit (`b` is `None`) refuses.
  - Otherwise it refuses with "W9 acceptance item predates a shared-surface change that affects it".
- `require_change_list` (`evidence.py:190-218`) is unchanged apart from its docstring's format line. The declared
  ref is still checked against the list at `git_head`.

**Known limit (note HR-2).** A tree-state test cannot tell a surface reverted to an earlier blob (`A -> B -> A`)
from one never changed. An observation taken at the first `A` then passes. The note records this as human-review
only, together with the completeness of `affected_registrations`, which the reviewer derives (W9 §4.3).

**Tests and records.** `tests/research_system/unit/test_w9_evidence_acceptance.py` and
`tests/research_system/integration/test_w9_wp9_3_2_runtime.py` (the O-32 cases), with these new cases:
- the late-entry scenario. PR 10 changes S from A to B with no entry, PR 11 changes it from B to C with entry
  `e2 = (B, C)`, and the late entry `e3 = (A, B)` is appended after it. An item observed with S at B is refused by
  `e2` and passes `e3`;
- an entry listed earlier does not admit an item for a later change;
- a revert `A -> B -> A` still passes (the limit below, kept);
- a cycle of entries terminates;
- a surface absent at the observation commit refuses;
- a deletion entry admits nothing;
- a surface deleted and re-created twice, `[(A,0), (0,X), (X,0), (0,Y)]`: an item observed at X before the second
  deletion is refused.

Plus the row in §4.

### 1.3 E1: the D-5 cadence is enforced at batch start and acceptance

**Now.** D-5 (06v line 567) requires a weekly vault-detector run, and a pre-batch run, but no gate checks it.

**After.**
- **A new evidence file.** `VAULT_DETECTOR_RUNS = f"{EVIDENCE_DIRECTORY}/vault-detector-runs.json"`, in format
  `w9-vault-detector-runs/1`. It holds append-only entries of two kinds:
  - `run`: `run_at`, `export_git_blob`, `classified_list_git_blob`, `live_file_sha256`, `output_sha256` and
    `status`;
  - `owner_cadence_reset`: `reset_at`, `decision_ref` and `reason`.

  The file is closed on `{format, entries}`. Each entry is closed on `kind` plus its kind's keys above. Timestamps are
  ISO-8601 UTC strings, as `_utc()` parses them (`evidence.py:259`), and the blob and hash fields are 40-hex and
  64-hex. **Only `status == "ok"` is admitted**: a failed run is not recorded, so it cannot bridge a gap.
- **A new check,** `require_vault_detector_cadence(reader, now)`, in `evidence.py`, with `now` timezone-aware.
  - **When it applies.** It does nothing while `reader.accepted_cl_export` is empty (`reader.py:218,237`), so it is
    inert before L-0b and in today's tests. That test comes before any file read, inside the function. Following the
    existing `require_x(read_evidence(...))` pattern would raise on the absent file and fail every WP9.3 and WP9.4
    test. Once the export is non-empty, the file must be present at `git_head`. Its absence refuses; deleting the
    file never disables the check.
  - **A malformed `accepted_cl_export` entry** refuses with `EvidenceRefused`, not `KeyError`. A shape test covers
    populated `ACCEPTED_CL_EXPORT` and `ACCEPTED_CONVENTIONS_CLASSIFICATION` entries: today nothing enforces either
    constant's shape (the reader and replay read only `retained_copy`, `reader.py:309`, `reducers.py:631-634`).
  - **The rule** (note §8.4 item 3):
    - timestamps never decrease;
    - the last entry is a `run` whose blobs are the accepted export's `export` and `classified_list` blobs, with
      `0 <= now - run_at <= 7 days`;
    - since the latest `owner_cadence_reset`, no two consecutive `run` entries are more than 7 days apart.
  - The module docstring's rule that "a row whose file is absent refuses" (`evidence.py:6`) gets this file's
    exception before L-0b.
- **Where it is called.** The callers already have the reader and `now`:
  - LR-003, in `prepare_proposal`'s registration branch, beside `require_detector_controls`
    (`preparers.py:686-690`);
  - LR-015, in `prepare_observation`, beside `require_registered` (`preparers.py:1215-1218`);
  - LR-016 and LR-020, in `check_environment`, beside `require_detector_controls` (`acceptance.py:147-152`).
    `check_environment(environment, legacy, record)` has no `now` today (`acceptance.py:139-141`). Its signature gains
    `now`, and its two callers pass it (`preparers.py:706`, LR-016; `:1029`, LR-020).
- **A missed weekly run** blocks the next batch until a reviewed PR adds an `owner_cadence_reset`, followed by a fresh
  `run`. No code checks the reset's `decision_ref`. What makes it Stephen's reset is his code-owner merge under I1.

**Cost Stephen accepted (P-090 item 2, E).** A weekly PR recording the run, merged by Stephen under I1, and an
`ars store advance-binding` before the next store command reads it. The run is self-attested on the operator
machine (note HR-4).

**Tests and records.** New unit cases in `test_w9_evidence.py`:
- inert when `accepted_cl_export` is empty;
- absent file refused once it is non-empty;
- stale last run refused;
- a gap without a reset refused;
- a reset followed by a fresh run passes.

Integration cases at each of the four call sites, and the row in §4.

### 1.4 J1: a pinned `CONVENTIONS.md` classification, and the classified-list format

**Now.** `ACCEPTED_CL_EXPORT` (`accepted_w9.py:86-88`) is empty. Its entries name a `classified_list` file by
`{repository_path, git_commit, git_blob, sha256, byte_length}`, but no format for that file's contents is fixed.
There is no pinned `CONVENTIONS.md` classification.

**After.**
- WP9.5 adds a separate `require_cl_classified_list(classified, export)`, which validates the classified list against
  `w9-cl-classified-list/1`. Each list entry's `ordinal` is 1-based and equals the export row's `row_ordinal`
  (`evidence.py:347-358`, `segmentation.py:408`). `require_cl_export` is unchanged, because its callers
  (`export_recheck.py:46`, `cli.py:1850`) are outside P-090's boundary. Whether the new function lives in
  `evidence.py` or `tools/_w9_detector_evidence.py` is the code task's choice (note §8.3); the second needs no WP9.3
  change.
- `accepted_w9.py` gains `ACCEPTED_CONVENTIONS_CLASSIFICATION: tuple[MappingProxyType[str, Any], ...] = ()`. Each
  entry is one flat descriptor, `{repository_path, git_commit, git_blob, sha256, byte_length}` (note §7.3). That
  differs from an `ACCEPTED_CL_EXPORT` entry, which holds three such descriptors. The descriptor names a
  `w9-conventions-classified-locks/1` file keyed by `(anchor_text, unit_hash)` (`segmentation.py:391-402`).
- Both constants stay empty until L-0b. Until then the `CONVENTIONS.md` check uses the conservative 9-section,
  68-unit partition (note §7.3).
- The L-0b PR that fills either constant is paired with a detector pin advance (note §6.1, §8.3).

**Unchanged.** `IMPORTER_MODULES` (`reader.py:42`). `accepted_w9.py` holds no D-4 identity. Under I1 it becomes
code-owned (§3).

## 2. W9 §4.2 amendment (Option H1)

**Now** (W9 §4.2 item 1): a registered legacy file may be written only under (a) a legacy-lane commit the freeze
permits, (b) a repository-wide change with Stephen's attributed note and an independent semantic-equivalence review,
or (c) an explicit owner ruling. `.apm/tracker.md` is registered (role `legacy_coordination`), and routine PRs
append Working Notes to it.

**After.** Add to item 1:

> (d) an append to `.apm/tracker.md`'s `## Working Notes` section, made through a reviewed pull request, when both
> segmenters (`research_system/legacy/segmentation.py` and `tools/w9_segmentation.py`, which must agree) show that the
> earlier and later files differ only by appended notes:
>
> - every `tracker_task_row` is byte-identical;
> - every byte outside `## Working Notes` is unchanged;
> - every earlier `working_note_entry` is preserved verbatim and in order;
> - the only other change is a blank separator matching `[ \t]*\n` inside the section;
> - neither file has a blocker.
>
> The post-merge detector checks the segmenter conditions, and that the commit maps to a merged PR. A qualifying
> append with no mapped PR fails, as it does under every other Rule 1 branch. Whether the PR was actually reviewed is
> a human check, not the detector's (note §6.5 Rule 1, which the code task brings into line with this). An append that
> fails any condition needs (b) or (c).

**Unchanged.** Items 2 and 3. A blob change to `.apm/tracker.md` still re-triggers its observation (item 3): (d)
waives the authorization record, not the re-observation. (d) is a detector-side carve-out. It adds no writer class
to the registration schema's closed `writer_classes` enum (`tools/w9_schema_gen.py:327,452`; W9 §5.2), so no pinned
W9 schema changes and there is no D-4 consequence.

**When (d) ends (review A-m8). Decided by Stephen, 2026-11-24 (P-090 item 5): it ends at the writer revocation, as
below.** W9 §13.3 item 4 plans a Stephen-recorded writer revocation,
after which sessions stop writing Working Notes to `.apm/tracker.md` and the §4.4 detector watches the path. After
that revocation, (d) would still pass a qualifying append, and the detector would be blind on the path. P-090 H set no
end. The revocation record ends (d), by a code constant that a pin advance flips. **The revocation and that pin
advance land in the same PR**, so there is no window in which the revocation is recorded but the pinned detector still
grants (d). A revocation record that arrives without the pin advance does not end (d) (CodeRabbit on #449, comment
`4674677014`).

**Evidence.** The rule was tested on the three real tracker commits after the freeze (#368 `452352ff`, #388
`e3519ba7`, #433 `a6a98966`): each added one note entry, with zero blockers and every task row identical
(`reviews/wp9-5-note-r2-review-2026-11-21.md` §5).

## 3. `CONVENTIONS.md` amendment (Option I1)

This modifies paragraphs 1 and 3 of the bullet that starts at line 713 (it runs to line 758), and one sentence of
the next bullet (lines 759 to 771), in `## ARS Foundation Governance`. That is a successor
section (lines 614 to 783), so no legacy unit changes and the legacy-lock check is unaffected. **It is applied in the
WP9.5 code PR**, in the same commit as the `.github/CODEOWNERS` and `tests/tools/test_ci_platform_policy.py` changes,
because the bullet describes what that test enforces.

**Now** (first sentence and the third paragraph):

> **The merge-admission gate's own files change only through a deliberate admin bypass.** `.github/CODEOWNERS` owns
> the gate: […]
>
> A new file the gate depends on must be added to both CODEOWNERS and `GATE_FILES` in
> `tests/tools/test_ci_platform_policy.py`. That test fails if a gate file lacks an owner, or if CODEOWNERS reaches
> beyond the gate.

**After:**

> **The merge-admission gate's own files, and the W9 detector's, change only through a deliberate admin bypass.**
> `.github/CODEOWNERS` owns the gate: […, unchanged]. Since P-090 (2026-11-23) it also owns the W9 detector surface:
> - its workflow and tools;
> - its helper and its tripwire test;
> - `research_system/legacy/accepted_w9.py` and `tools/w9_segmentation.py`;
> - the evidence directory `.research-system/evidence/w9/`.
>
> For the owned files, a PR could otherwise change the detector that judges it, or the evidence it reads. The other
> modules in the detector's import closure are pinned, not owned (P-090 item 1), and the pinned post-merge run is the
> independent check for them. The full list is in CODEOWNERS.
>
> A new file the gate depends on must be added to both CODEOWNERS and `GATE_FILES` in
> `tests/tools/test_ci_platform_policy.py`. A new `tools/` file in the detector's import closure must be added to
> CODEOWNERS and to the test's detector list (`test_derived_closure_tools_and_accepted_w9_are_codeowned`). The tests
> fail if a gate or detector file lacks an owner, or if CODEOWNERS reaches beyond the gate and the detector. Amended
> by P-090 item 2 (Option I1), applied <the code PR's date>.

And in the next bullet (lines 759 to 771), the sentence "While bypasses stay the exception, rule insights can single
one out, which the bullet above relies on." becomes:

> W9 evidence PRs are expected bypasses, each carrying a `Bypass reason:` line. Apart from them, bypasses stay the
> exception, so rule insights can single one out, which the bullet above relies on; the weekly bypass review reads
> the W9 ones by their stated reason.

The CODEOWNERS header (lines 1 to 12) gets the matching sentence. Under I1 these files are code-owned:
- `/.github/workflows/legacy-write-detector.yml`;
- the seven `tools/` files (`check_legacy_writes.py`, `check_conventions_legacy_locks.py`,
  `check_legacy_log_baseline.py`, `run_w9_detector_controls.py`, `run_w9_pinned_detectors.py`,
  `export_w9_registration_manifest.py`, `_w9_detector_evidence.py`);
- `/tests/tools/test_w9_detectors.py`;
- `/research_system/legacy/accepted_w9.py`;
- `/tools/w9_segmentation.py` (I1-include-seg);
- `/.research-system/evidence/w9/`.

The file list, the directory-pattern handling in the two policy tests (`test_ci_platform_policy.py:364-374`), and
the order in which the new files land are code-task detail (note §16.1, §15.3).

**What Stephen accepted.** This reverses the 2026-09-11 rule that CODEOWNERS covers only the merge-admission gate.
Each of these then needs his own merge, normally by bypass with a `Bypass reason:` line
(`tools/check_bypass_merges.py:41,135`):
- every pin advance;
- every evidence PR, including each PR that changes a shared surface, since it must edit the code-owned change list;
- every weekly vault-run PR.

## 4. `06v-addendum-2026-11-10-w9-paths.md` rows

The addendum's rule is that "a package that adds a shared location adds a row here in the same PR". So **these rows
are added by the WP9.5 code PR**, and are listed here only so the review sees them with the decisions.

| File | Path | Producer | Reader | Format |
|---|---|---|---|---|
| Registration manifest (row changed) | `.research-system/evidence/w9/registration-manifest.json` | WP9.5, per batch | WP9.3, LR-015; the WP9.5 detector | `w9-registration-manifest/2` (§1.1) |
| Shared-surface change list (row changed) | `.research-system/evidence/w9/shared-surface-changes.json` | each PR that changes a shared surface | WP9.3, LR-016 and LR-020; the WP9.5 detector, Rule 3 | `w9-shared-surface-changes/2` (§1.2) |
| Walk baseline (new) | `.research-system/evidence/w9/walk-baseline.json` | Stephen's pin-advance PRs, from L-1 | the WP9.5 detector and its wrapper | `w9-walk-baseline/1` (note §6.2.2) |
| Legacy-write records (new) | `.research-system/evidence/w9/legacy-write-records.json` | the PR making a W9 §4.2(b) write | the WP9.5 detector, Rule 2 | `w9-legacy-write-records/1` (note §6.4) |
| Vault-detector runs (new) | `.research-system/evidence/w9/vault-detector-runs.json` | the weekly and pre-batch operator runs | WP9.3, LR-003, LR-015, LR-016 and LR-020 | `w9-vault-detector-runs/1` (§1.3) |
| `CONVENTIONS.md` classification (new) | in the evidence area; file name fixed at L-0b | L-0b | the `CONVENTIONS.md` check, at its pinned commit | `w9-conventions-classified-locks/1` (§1.4) |
| Computational-Log export, retained copy and classified list (row 29 changed) | in the evidence area; the three paths fixed at L-0b (note §8.3) | export and retained copy: `tools/w9_segmentation.py` at L-0b; classified list: the baseline observer, accepted by Stephen (W9 §7.3 item 1) | WP9.3, LR-011 and LR-015; WP9.3-2's recheck; the vault detector | `w9-cl-export/1`, plus `w9-cl-classified-list/1` for the classified list (§1.4) |

Add one note under the table: W9-T7 runs in the unit lane (`admission-controls`), not the "integration, slow" lane
of 06v line 230 (P-090 item 2, F).

The code PR also does the following (review A-m10):
- keeps the addendum's "06v reference" column (O-9, O-32, D-5, M-6), which this table drops;
- amends the addendum's header cells "changes no requirement of 06v" and "Amends: Nothing", since the W9-T7 lane note
  changes 06v line 230;
- for each changed row, adds a dated "Amendments" entry recording the old cells, as the addendum already does, and
  re-cites any `evidence.py` line numbers that move.

## 5. Review and acceptance

1. One independent review attacks §1 to §4 against the code at `dbd54fe3`, the design note and P-090. It gives each
   section its own disposition.
2. Stephen accepts or returns each section, in a register entry.
3. The WP9.5 code brief cites the accepted sections. The code PR implements §1, applies §2's text to W9 §4.2,
   applies §3's text to `CONVENTIONS.md` and CODEOWNERS, and adds §4's rows.
