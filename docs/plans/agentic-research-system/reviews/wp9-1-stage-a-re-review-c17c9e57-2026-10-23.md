# Independent re-review of W9 WP9.1 stage A, revision 2 (`c17c9e57`)

**Date:** 2026-10-23<br>
**Reviewer:** the session that wrote the review of `b089f1fa` (`d9a7d22b`). It did not author revision 2, the
reconciliation, P-069, the generator or the test.<br>
**Skill:** `adversarial-design-review` (remediation re-review)<br>
**Verdict:** **REWORK REQUIRED (narrow).** 0 Blocking, 4 Major, 5 Minor, 8 Info. Every finding of the first review is
closed or correctly carried; the four Majors come from the three interpretations the reconciliation (§3) asked me to
test, and each needs a small schema or test-table change.<br>
**Known limit (P-058):** every review in this chain, this one included, ran on one model family. This is recorded as a
known limit, not as a finding.

## 1. Subject

Commit `c17c9e57` on `pipe/w9-wp9-1-schemas`. Its parent is my review commit `d9a7d22b`; revision 2 changes 23 files
(`git diff --name-only d9a7d22b..c17c9e57`) and does not touch the review. New or changed:

- `tools/w9_schema_gen.py` (new; P-069 item 4) and the 17 regenerated schemas;
- the bootstrap contract (adds `required_w11_catalogue`, `restricted_suffixes` and four verification rules);
- `tests/research_system/contracts/test_w9_contract_materialization.py` (57 tests);
- the stage note (revision 2), the reconciliation `reviews/wp9-1-stage-a-reconciliation-2026-10-23.md` and register
  entry P-069.

## 2. Method

- Read P-069, the reconciliation, the note, the generator (all 1,254 lines) and the test (all 888 lines).
- For each first-review finding, bound the reconciliation's stated fix to the generator line that implements it and the
  test that controls it (§4).
- Attacked the three interpretations in reconciliation §3 with synthetic instances against the committed schemas, using
  the registry's `FORMAT_CHECKER`.
- Ran an independent in-memory mutation probe: seven guards weakened one at a time by replacing the test module's
  `_schema` loader in memory, never on disk.
- Ran `tools/w9_schema_gen.py --check`, ruff, a CR/BOM byte check and the first review's command-9 suites plus the
  segmentation vectors.
- W9 and 06v are as pinned in the first review (unchanged on the branch).

All probes are read-only and run with `python -I` from the session scratchpad. §7 lists the commands.

## 3. Findings

### 3.1 Blocking

None.

### 3.2 Major

#### N-1 — `ars_reviewed_pr` cannot be the writer of the read-only projection. Interpretation 1 holds for one role only.

**Location:** `tools/w9_schema_gen.py:270, 275, 401-404`; test `:728-729`; note §2 "Writers"; reconciliation §3 item 1.

**Claim.** Revision 2 makes `["ars_reviewed_pr"]` the exact writer set of both ARS-owned roles. That fits
`successor_results_root` (`results/ars/`), whose changes reach `main` through merged PRs (W9 §4.4's detector treats
`results/ars/` as the registered successor root). It does not fit `legacy_read_only_projection`:
- 06v O-16 (line 196) and WP9.6 (line 518) put the projection under `.research-system/projections/legacy/`;
- that directory is gitignored (`.gitignore:219-220`; 06v §2.2 line 69), so no PR can ever write it;
- it is written by `ars projection rebuild` (06v §2.2, `cli.py:1507-1547`), a rebuild from the ledger.

**Evidence.** Probe P1: the projection at its 06v path with `writer_classes: ["ars_reviewed_pr"]` is VALID; P2: the same
with `[]` is REJECTED (`['ars_reviewed_pr'] was expected`). Nothing else about the role is constrained: P3
(`legacy_owned`), P4 (`closed_reference`) and P5 (at a `vault_root`) are all VALID, although W9 §7.2 (line 376) says the
projection is "published under a registered ARS namespace". The test's own positive fixture registers the projection as
`legacy_owned` (`:728`).

**Failure scenario.** WP9.6 registers the projection as the schema requires, with writer `ars_reviewed_pr`. Its actual
writer, the projector, is then a writer the registration does not admit. Either WP9.5's writer check flags every
rebuild, or the check is relaxed for this path by special case, which is the weakening the writer registry exists to
prevent. And a projection registered `legacy_owned` reads as a legacy file under §4.2.

**Impact.** Validity of the writer registry; operations for WP9.5 and WP9.6.

**Required change.** For `legacy_read_only_projection`:
- `ownership_mode: successor_owned`, `root_kind: repository_root`, and a path under
  `.research-system/projections/legacy/` (06v O-16), as `untracked_file`;
- a writer class that names the actual writer, for example `ars_projection_rebuild` ("written only by
  `ars projection rebuild` from the store; never an authority input"), in place of `ars_reviewed_pr`.

Keep `ars_reviewed_pr` for `successor_results_root`. Correct the test fixture at `:728`, and add P2 to P5 as controls.
The reconciliation calls this an interpretation of W9 §5.2, so record the new class in the note as the author's reading
for Stephen to see at catalogue acceptance.

**Affects:** W9 §7.2, W9-D8b; O-16; WP9.5, WP9.6.

#### N-2 — `anyRef` is closed over ARS IDs, so W9's qualifier and conflict sources cannot be cited unless already observed.

**Location:** `tools/w9_schema_gen.py:182, 223, 705-716`; note §2 "Reference kinds"; reconciliation §3 item 2.

**Claim.** `anyRef` is a `oneOf` over `obj_`, `dec_`, `rev_`, `art_` and `tsk_` refs. By W9's text, three of the
`anyRef` fields must be able to cite sources that are legacy or repository files, not ARS records:
- `qualifier.source_ref`: W9 §6.4's sources are a review finding (A1 to A4 in G7-A), a claim-trace audit verdict, a
  stronger record (`stale_projection_of`), and a dated correction entry in the vault Computational-Log (`corrected_by`,
  the 2026-10-22 T1.20 correction);
- `conflicts[].conflicting_record_refs[]`: W9 §6.3 records lines 69–71 of `SUPERSEDED.md` "with the conflict naming both
  records", the other being the T1.38 Phase 1 `[RESULT]` and `w2_gap_closure_phase1_2026-07-16.json`;
- `families[].signed_w0_revision_ref`: the W0 manifest revision Stephen signed, which is a repository document at a
  commit.

**Evidence.** Probe R1: a conflict naming the tier-1 JSON by Git file identity is REJECTED. R2: the same as a W11-style
`sourceRef` (`ref_kind: external`, with a locator) is REJECTED. R3: a `corrected_by` qualifier citing the vault entry by
path and hash is REJECTED. W11's precedent has exactly that branch: `w11-common-definitions.schema.json` `sourceRef` with
`ref_kind` in `record | artefact | external` and a `locator`. W9-T4's negative control is "Import them [lines 69–71]
alone; the summary's W₂ family is `unverified`", which means the stronger record need not be observed first.

**Failure scenario.** The W9-T4 import of lines 69–71 alone must record the conflict and its tier-1 resolution. The
schema admits only ARS IDs, so either the tier-1 record is observed first (contradicting "alone"), or the conflict is
recorded with one side missing, or a fabricated `art_` stands in for a file. The note says stage B or WP9.2 "fix" these
kinds, but a closed `oneOf` pinned by the catalogue can only narrow, never admit a file identity, without a new schema
identity.

**Impact.** Validity; W9-T4 and W9-T13 cannot be represented as W9 specifies them.

**Required change.** Add a source-locator branch to `anyRef`, or a separate `sourceRef` for these fields only: a Git
file identity (path, commit, blob, SHA-256, size, optional line span) and a vault identity (vault path, SHA-256, size,
optional heading anchor), following W11's `sourceRef` `external` form. Use it for `qualifier.source_ref`,
`conflicting_record_refs` and `signed_w0_revision_ref`. Add R1 and R3 as positive controls. If the author reads W9 as
requiring every source to be observed first, that reverses W9-T4's "alone" and is Stephen's decision, not an
interpretation.

**Affects:** W9 §6.3, §6.4; W9-T4, W9-T13; O-27; WP9.3.

#### N-3 — The edge table omits the `anyRef` fields, whose `obj_` branch lets a paper root name its own transition.

**Location:** test `:146-168, 418-426`; `tools/w9_schema_gen.py:858` (`legacy-paper-root.qualifiers`).

**Claim.** `test_record_reference_graph_is_closed_and_acyclic` requires `RECORD_EDGES` to equal the fields whose kind is
`recordRef` or `nullableRecordRef` (`:419`). The eight `anyRef` and `nullableAnyRef` fields in `REF_FIELDS` (the note's
seven items) also admit an `obj_` ID, so they can name any W9 record, and they are outside both the table and the cycle
check.

**Evidence.** Probe R4: a `legacy-paper-root` whose qualifier `source_ref` is an `obj_` ref is VALID; nothing records which
W9 kinds that ref may name. If it names the root's `legacy-ownership-transitioned` record, the graph has
root → transition → root, which is W9-T21's first negative control ("A `legacy-paper-root` that names its transition
event"). The paper-root allowlist test passes, because the field is `qualifiers`, which is allowed.

**Failure scenario.** WP9.2 reads the edge table as the declared graph (as the note invites: "The test's edge table
shows the record graph is acyclic"). A qualifier sourced from the transition record enters a root and passes every
stage A check.

**Impact.** The closure the first review's M-4 asked for ("assert it equals the table's key set … so a new ref field
fails until it is classified") is met for one ref family but not for every field that can carry a W9 record ID.

**Required change.** Make the closure "every field whose definition admits `objId`": include the `anyRef` and
`nullableAnyRef` fields in `RECORD_EDGES`, with the W9 kinds their `obj_` branch may name (an empty tuple where none
may). For `legacy-paper-root.qualifiers[].source_ref`, exclude `legacy-ownership-transitioned`,
`legacy-transition-mapping` and `legacy-paper-citation-status`. Add R4, with a transition target, as a negative control
on the graph.

**Affects:** W9-T21, O-29; M-4 of the first review.

#### N-4 — Supersession is declared for observations and mappings only. W9 §13.1 and §13.2 also supersede acceptances and adoptions.

**Location:** test `:166-167`; reconciliation §3 item 3; note §2 "Immutable records".

**Claim.** Revision 2 reads W9 §5.2's row (line 252: "Corrects an erroneous accepted observation or mapping") as the
target set. W9 restates the rule twice, more widely:
- §13.2 (line 635): "An accepted observation, closed-reference acceptance, adoption or mapping found wrong is superseded
  by a new record";
- §13.1 (line 612), the rollback route: "After commit, closed-reference item: the accepted record is superseded by
  `legacy-record-supersession`". The accepted record there is the `legacy-closed-reference-acceptance`.

**Evidence.** The schema itself does not restrict targets (probe S1: any `obj_` validates), so the narrowing lives in the
edge table and the note, which are the declarations WP9.2 and WP9.6 will build from. Revision 2 also fixes every
record at `record_revision: 1` (m-1). With both changes, an erroneous closed-reference acceptance or adoption has no
correction route at all.

**Failure scenario.** WP9.6 builds the rollback harness from the edge table. The §13.1 route for a committed
closed-reference item, which O-17 requires to be "exercised once on a scratch store before the item's batch", cannot be
expressed, so either the batch is blocked or the harness invents an unreviewed route.

**Impact.** Rollback and recovery (W9-D4, W9-T14, O-17).

**Required change.** Make the supersession targets W9 §13.2's four kinds: `legacy-observation`,
`legacy-closed-reference-acceptance`, `legacy-adoption-decision` and `legacy-transition-mapping`. The graph stays
acyclic, since no record names a supersession. Record in the note that §5.2's row is the narrower restatement and that
§13.1–13.2 govern. Stephen may want a one-line erratum reading, as P-066 item 3 did for §12.3.

**Affects:** W9 §5.2, §13.1, §13.2; W9-T14; O-17; WP9.6.

### 3.3 Minor

**n-1 — Windows-normalized aliases still pass the path guards.** The relative-path grammar rejects `./`, `..`, `//`,
backslashes, `:` and trailing whitespace, but not a segment ending in `.` or a space, or an 8.3 short name. Win32 strips
trailing dots and spaces, and NTFS resolves short names. Probes: `CONVENTIONS.md.` and `CONVEN~1.MD` registered under
`legacy_decision_log_entry` at a vault root are VALID (Q1); `x/null_cache.pkl.` as `untracked_file` is VALID, in a
registration (Q2) and in an observation with a frozen copy (Q3). The note says the vault alias "is unregistrable". Fix:
reject any segment ending in `.` or a space, and segments matching `~[0-9]`; and state in the note that full alias
closure is the handle-bound read's (`physical_identity`), not the path grammar's.

**n-2 — The contract's suffix list is not bound to the schema's regex.** The test checks `restricted_suffixes` against
its own constant `D9_SUFFIXES` (`:81, 310`); the schema regex is a separate literal (`w9_schema_gen.py:32`). If D-9's
list grows, the contract and the constant can change while the schemas do not, and every test passes. Fix: derive
`RESTRICTED_SUFFIX` from a list in the generator, assert that list equals the contract's, and test each suffix, upper
and lower case, against every non-restricted branch.

**n-3 — "Byte for byte" is checked as decoded text.** The contract rule says the generator reproduces every schema "byte
for byte"; the test (`:268`) and `--check` (`w9_schema_gen.py:1243`) compare `read_text()`, which translates CRLF. With
`eol=lf` this is latent, but it is the CRLF case the skill's fixture lessons warn about. Fix: compare `read_bytes()` with
`render(schema).encode("utf-8")`.

**n-4 — A row's `selector_kind` is not bound to its inventory's.** Probe U1: a `heading_section` inventory whose rows say
`computational_log_entry` is VALID (T1, a mismatch that also changes the per-selector fields, is rejected). Fix: one
`allOf` branch per selector kind requiring `rows[].selector_kind` to equal it.

**n-5 — The adapter between the tool and the schema is the test's.** The tool omits the four selector-specific keys
when they do not apply; the test's `_inventory` (`:803-811`) fills them with null before validating. That is a sound
reading, but the note's "the light inventory holds what the accepted reference tool … emits" holds through this
adapter. Fix: say in the note that WP9.3's importer fills absent selector fields with null, and cite the adapter.

### 3.4 Info

**i-1 — First-review findings: all addressed.** §4 maps each to its line and test. B-1, B-2, M-1 to M-6, m-1 to m-4 and
m-6 to m-12 are fixed; M-7 and m-12 are settled by P-069; m-5, I-3 and I-8 are carried to named later work in note §3.

**i-2 — P-069 matches the options the review offered.** Two PRs as a named exception to D-6; deviation 2 accepted with
both conditions binding; M-3 option 1; the test and generator named in the boundary.

**i-3 — Independent mutation probe.** Seven guards weakened in memory, each caught by a named test: the ARS-role writer
rule, the legacy-role writer rule, `vault_root ⇔ vault_file`, the restricted guard in the `git_tracked` branch, `anyRef`
widened, the `heading_section` region rule, and `superseded_ref` retyped (caught by the reference-kind walk). The
unmutated baseline passes every test.

**i-4 — The tool-to-schema binding holds beyond the test's inputs.** Eight further synthetic inputs (structural log
blocks, duplicate anchors in the log and in Working Notes, a stage log without frontmatter and one unterminated,
conventions continuations, an unaddressed heading-section region, a tracker row with an escaped `\|` and an invalid
byte) all validate (T2).

**i-5 — No tracked `.csv` or `.pkl` exists** (`git ls-files` returns none), so the `git_tracked` branch's suffix guard
excludes nothing today.

**i-6 — D-9's list is narrower than W9 §5.4's classes.** `x/table.csv.gz` and `x/cache.pickle` pass as `untracked_file`
(Q2). W9 §5.4 names null caches and embeddings by content, not suffix. D-9's list is Stephen's (P-064 item 9), so this
is a scope note for WP9.3's reader and WP9.7, not a schema defect.

**i-7 — Runtime-only conditions remain runtime-only.** A read that ends before it starts (U2), a supersession naming
itself (S2) and a recovery root naming itself are not expressible; note §3 assigns them correctly, except S2, which
belongs with W9-T14 in WP9.6.

**i-8 — Clean checks.** The generator `--check` passes; ruff `check` and `format --check` pass on the generator and the
test; no W9 schema has CR bytes or a BOM. No file under `research_system/` changes.

## 4. First-review findings: disposition check

| Finding | Reconciliation's fix | Bound to | Status |
|---|---|---|---|
| B-1 | Typed refs; `REF_FIELDS` equals a schema walk | `w9_schema_gen.py:198-225`; test `:368-393` | Closed. Residual: N-2, N-3 |
| B-2 | Contract fields; tool-to-schema test | `:476-660`; test `:836-888` | Closed. Residual: n-4, n-5 |
| M-1 | Writer classes by role | `:391-404`; test `:716-729` | Closed for legacy roles and the shared surface. Residual: N-1 |
| M-2 | Only `conventions_lock` names `CONVENTIONS.md` | `:375-385`; test `:732-741` | Closed for spelling and case. Residual: n-1 |
| M-3 | Suffix guard (option 1) | `:94-140, 412-419`; test `:520-536, 750-765` | Closed. Residual: n-1, n-2, i-6 |
| M-4 | Edge table, acyclicity, allowlist | test `:146-173, 418-431` | Closed for `recordRef` fields. Residual: N-3, N-4 |
| M-5 | Per-fixture entries, anchors keyed | `:758-811`; test `:601-633` | Closed |
| M-6 | Verifier, tests, generator, observation bound | `:1050-1091` | Closed |
| M-7 | P-069 items 1 and 2 | Register; note §3 | Settled by owner |
| m-1 | Revision const 1 | `:279-307`; test `:452` | Closed. Interacts with N-4 |
| m-2 | Null refs on closed-reference transitions | `:983-1002`; test `:479-481` | Closed |
| m-3 | Path grammar; root/identity coherence | `:36, 405-411`; test `:698-713, 750-755` | Closed. Residual: n-1 |
| m-4 | Observation bindings; one family grammar | `:747-754, 720-727`; test `:550-574` | Closed |
| m-5 | Carried to WP9.3 | Note §3 | Correctly carried |
| m-6 | `^W9-T[0-9]+$`; verifier checks in stage B | `:1145`; note §3 | Closed |
| m-7 | File identities; W11 catalogue named | `:1093-1120`; test `:330-333` | Closed. The W11 identity matches `HEAD` |
| m-8 | Prerequisite sentence | Contract; test `:311` | Closed |
| m-9 | Namespace test; `HEAD` tuples; both W0 refs; format checker | Test `:276-283, 314-327, 539-547, 220-222` | Closed |
| m-10 | Generator committed; identical `$defs` | Test `:264-273` | Closed. Residual: n-3 |
| m-11 | Note editorial | Note revision 2 | Closed |
| m-12 | P-069 item 4 | Register | Settled by owner |
| I-1 to I-9 | Recorded | — | No change needed; I-5 is now in note §1 |

## 5. Decision audit

| Decision or rule | Disposition | Reason |
|---|---|---|
| P-069 item 1 (two PRs) | Keep | Matches W11's precedent; recorded as a named exception |
| P-069 item 2 (no event schemas, two conditions) | Keep | Conditions are carried in note §3 |
| P-069 item 3 (restricted-path guard) | Keep; tighten | n-1, n-2 |
| P-069 item 4 (named boundary) | Keep | The generator writes only its 17 files; `--check` writes nothing |
| P-068 item 2 (segmentation contract) | Keep | The inventory now holds the tool's rows (i-4); n-4, n-5 |
| P-064 D-9 | Keep | Scope note i-6 |
| W9 §5.2 vs §13.1–13.2 (supersession targets) | Amend the reading | N-4; Stephen may want an erratum reading |
| W9 §6.3, §6.4, W9-T4 (sources of conflicts and qualifiers) | Keep W9; amend the schema | N-2 |
| W9 §7.2, 06v O-16 (projection) | Keep; amend the schema | N-1 |
| W9-T21 (paper-root acyclicity) | Keep; extend the closure | N-3 |

## 6. Revision plan

**Author (revision 3).** N-1 to N-4 and n-1 to n-5. All are generator, test-table or note edits; none needs a new owner
decision unless the author disagrees with N-2's reading of W9-T4 or with N-4's reading of §13.

**Owner (Stephen), optional.** An erratum reading that W9 §13.1–13.2, not §5.2's row, fix the supersession targets
(N-4).

**Later work.** Unchanged from note §3, plus i-6 for WP9.3's reader and S2 (i-7) for WP9.6.

**Residual risk.** The same as the first review: once the catalogue pins these bytes, every change is a new identity
and a new acceptance. All four Majors are cheap now and expensive after stage B.

## 7. Change log and commands

**Files edited:** this file only. No subject file, vault, `.apm/`, store, Jira or `papers/` write.

**Commands** (from the worktree unless noted; probes from the scratchpad, `python -I`):
1. `git checkout -q pipe/w9-wp9-1-schemas`; `git log --oneline d660f091..HEAD`; `git diff --stat b089f1fa..HEAD`;
   `git diff --name-only d9a7d22b..c17c9e57` (the review file is not among them).
2. `git diff d9a7d22b..c17c9e57 -- docs/plans/agentic-research-system/03-decisions-and-open-questions.md` (P-069).
3. `sed -n 215,222p .gitignore`; `grep -n projections` over 06v; `git ls-files '*.csv' '*.pkl'` (none).
4. `python -I probe_rereview.py <worktree>`: sections P (interpretation 1), Q (aliases), R (interpretation 2), S
   (interpretation 3), T (tool outputs through the schema).
5. `python -I probe_rowsel.py <worktree>`: U1, U2.
6. `python -I probe_mutation.py <worktree>`: seven in-memory mutations against the stage A test functions.
7. `python -I tools/w9_schema_gen.py --check`: exit 0; `git status --porcelain` clean afterwards.
8. `python -m ruff check --no-cache` and `ruff format --no-cache --check` on the generator and the test: clean.
9. A `python -I -c` CR/BOM byte check over the 17 schemas: none.
10. `python -m pytest -p no:cacheprovider --no-cov -o addopts="" -q` over the first review's command-9 set plus
    `tests/tools/test_w9_segmentation.py`, with `PYTHONDONTWRITEBYTECODE=1`: **552 passed in 241.24 s**, none
    skipped (the reconciliation reported 551 passed and 1 skipped on the author's machine; the difference is one
    environment-dependent skip, not a failure). `--collect-only` on the W9 test: 57 tests.
