# Review of the WP9.4 design note, revision 7, and its addendum edits

| Field | Value |
|---|---|
| Date | 2026-11-20 |
| Subject | `transition/w9/wp9-4-design-note.md` at `a7485bef` (revision 7, PR #437, unmerged); that commit's edits to `implementation/06v-addendum-2026-11-10-w9-paths.md` |
| Diff reviewed | `git diff 642c56d3 a7485bef` |
| Judged against | the rest of the note; the code at `a7485bef`; W11 §7.2 and §7.3 (`design/11-portfolio-and-discovery-lifecycle.md:1150-1200`); W9 §3.1; P-085; P-086; the review of revision 6 (`7a0c6b11`) |
| Method | `adversarial-design-review`. Every code claim was run, on Windows (`win32`, Python 3.13.5, NTFS), in scratch directories under a temporary directory, with in-memory replay state. The R6 probes were read as references; the R7 probes were written from revision 7's text |
| Branch | `claude/review-w9-wp9-4-note-r7-b531b4` |
| Artifacts | `reviews/wp9-4-note-r7-review-artifacts/`: `r7_collision_probe.py` and its output; `r7_extractor.py` and its output |

## 1. Verdict

**accept_with_required_changes.** 0 Blocking, 2 Major, 4 Minor, 4 Info.

Revision 7 fixes what the review of revision 6 asked for, and the fixes work when run. The case-folded path check
refuses every case variant of a member path in both directions, against recorded registrations and open proposals,
and admits the `P01-A-JRSSA-old` sibling and a `vault_root` path that begins `papers/P01-A-JRSSA/`. The
`(volume_serial_number, stable_file_id)` comparison refuses one file registered twice in two letter cases, and falsely
refuses nothing I could build: not a `legacy_decision_log_entry` registration, not a vault file, and not a later file
after deletes (NTFS reused no file ID in 3,000 cycles). The §11.1 rule, rebuilt from revision 7, gives P01-A's drafts
23 cited files and four ambiguous names, and P01-B's two cited files and none.

Two gaps remain in the collision checks. Neither is in the parts revision 7 changed; both are in what it relies on.

- **R7-M1.** The target prefix is called sound "while every registration is made under one binding's repository
  root, which v1 assumes". The code does not assume it: a v1.2 `AdvanceStoreBinding` and a `RepairStoreBinding` both
  rebind a store to another checkout. The path half is scoped by `root_id`, which is a free string that no preparer or
  replay check pins. After a rebind, a member registered under another `root_id` passes all three checks.
- **R7-M2.** W11 §7.2's case-folded collision is still open at LR-003's other prefix test. `_check_registration`
  refuses a legacy role under `.research-system/projections/legacy/` by a case-sensitive `startswith`, and
  `.Research-System/Projections/Legacy/p.json` is read by the preparer and admitted by replay.

The Minors are test and wording defects. The most important is R7-m1: §15's test for R6-M2's fix cannot fail on a
plausible wrong implementation, the one that still trusts the declared `canonical_target`. Nothing here blocks WP9.4-1.
R7-M1, R7-m1 to R7-m4 belong in WP9.4-2's note before its code. R7-M2 needs Stephen's scope call, as R6-M2 did.

No finding reopens an owner point. One claim is not credited to a review but turns a review's residual risk into an
unsupported assumption ("which v1 assumes"; R7-M1). Every other credit in §25, §17 claim 15 and §10.2 matches the
committed r6 report.

## 2. Major findings

### R7-M1 (Major). The target prefix's soundness condition is false in v1's code, and the path half's `root_id` scope is unpinned

**Note sections.** §10.2 "Prefix collisions" (lines 960-967): the path half "within one `(root_kind, root_id)`"; the
target half "is sound while every registration is made under one binding's repository root, which v1 assumes".
§10.2 "The equality half" (lines 973-980): "`normalized_path` case-folded", for every role. §17 claim 15.

**Evidence.**
- The binding's repository root can change. `_validate_binding_transition` (`store/current_binding.py:361-386`) keeps
  `code_roots` among the `stable_fields` for older bindings, but its v1.2.0 branch checks only `identity_fields`
  (`:378-386`), which do not include `code_roots`. `AdvanceStoreBinding` writes `intended_manifest["code_roots"] =
  [str(candidate.root)]` (`store/binding_service.py:1670`) with no check that the candidate is the predecessor's root.
  It only refuses a disposable checkout (`:484`; `config.py:97-113`). `RepairStoreBinding` moves a stale store to a new
  root by design (`binding_service.py:970-1005`). The W9 commands then run from that root:
  `_legacy_current_binding` takes the repository root from the running checkout (`cli.py:1677-1684`), and
  `load_current_binding` requires `code_roots` to equal it (`current_binding.py:842`).
- `root_id` is a free string. The schema gives `{"type": "string", "minLength": 1}`. LR-003's preparer ignores it:
  `_root` chooses the directory by `root_kind` alone (`legacy/preparers.py:135-140`). No replay check reads it except
  as part of the equality key (`replay/reducers.py:403-406`). Nothing in `legacy/accepted_w9.py` pins it.
- The review of revision 6 named the condition as a residual risk: "The physical-prefix form in R6-M1 is sound only
  while every registration is made under one binding; the case-folded path form does not depend on that" (r6 §8).
  Revision 7 turned that into "which v1 assumes", with no citation. The second half of the r6 sentence is also not
  quite right: the path form depends on the registrant using the same `root_id`.
- Probe (`r7_collision_probe_output.txt`):
  - [4], same binding, `root_id='tdl-2'`: path half `False`, target half `True`. The target half covers for the
    unpinned `root_id`.
  - [5], root registered at checkout A, then the binding moves to checkout B: with `root_id='tdl'`, the path half is
    `True` and the target half `False`; with `root_id='tdl-2'`, **every check is `False`**, including today's
    `_registration_conflicts`.

**Failure scenario.** The P01-A root is recorded while the store is bound to one clone. Stephen later advances the
binding to another durable clone. A registration manifest then lists `papers/P01-A-JRSSA/_project.md` as
`legacy_coordination` under `root_id: "repo"` instead of `"tdl"`. LR-003 reads it in the new clone, and replay admits it.
Only Stephen's LR-004 Decision stands between the file and two writer sets, which is the outcome R5-M1 was raised to
prevent. The same move defeats R6-M2's every-role equality: a duplicate registration of any file under a new `root_id`
has a new file ID and a new target.

**Impact.** Validity of the ownership state. §10.2 calls option 1's "no member has a registration" a replay invariant;
it holds only while the binding never moves or every registrant reuses one `root_id`.

**Disposition.** Fix in WP9.4-2's note, within O (it refines O's check; it reopens nothing).

**Proposed text** (§10.2, replacing the last sentence of the target bullet and adding one bullet before it):
- "**`root_id` is pinned.** Replay's LR-003 check refuses a registration whose `root_id` differs from the `root_id` of
  any recorded or open-proposed registration of the same `root_kind`. So one `root_kind` has one `root_id` for the
  store's life, and the path half's scope cannot be escaped by a new spelling."
- "The target half compares absolute paths, so it holds only between registrations made under one binding's
  repository root. A v1.2 `AdvanceStoreBinding` or a `RepairStoreBinding` can move that root
  (`current_binding.py:378-386`, `binding_service.py:970-1005`, `:1670`). Across a move the path half, with `root_id`
  pinned, is the check that holds."
- In the equality half, say that the folded-path key stays `(root_kind, root_id, folded normalized_path)`.

Add to §15's prefix row: "a member proposed under another `root_id` of the same `root_kind` is refused; a
registration whose `canonical_target` lies under another checkout's root, with the root's `root_id`, is refused by the
path half". Alternatively, if Stephen prefers not to pin `root_id`, scope both path comparisons by `root_kind` alone.
That is the same protection, with no new refusal.

**Affected.** Owner point O (P-086 item 15); R6-M2's every-role correction; WP9.4-2; §17 claim 15; §18.

### R7-M2 (Major). A case-folded collision W11 §7.2 lists is still open at LR-003's projection-prefix test

**Note sections.** §10.2 "Letter case survives to LR-003" (lines 948-956): "The other aliases W11 names are closed by
the read already"; §17 claim 15: "close every alias W11 §7.2 lists on Windows".

**Evidence.**
- `_check_registration` (`replay/reducers.py:428-429`) refuses a non-projection role when
  `path.startswith(".research-system/projections/legacy/")`. That test is case-sensitive. (`_CONVENTIONS` beside it
  is compiled with `re.IGNORECASE`, `:132`.)
- The preparer reads a parent spelled in another case on Windows (`reader.py:161` compares with `os.path.normcase`).
- Probe [9]: `.research-system/projections/legacy/p.json` as `legacy_coordination` is read and refused by replay;
  `.Research-System/Projections/Legacy/p.json` is read and **admitted** by replay.
- The r6 review's site table (r6 §3) looked at this test only for a root ("the root's path is fixed by the schema"),
  which is right for the question it asked. The case question is new.

**Failure scenario.** A `legacy_owned` registration of a file under the legacy projection directory, which is
`successor_owned` and written by `ars_projection_rebuild` (schema `allOf`, role `legacy_read_only_projection`). The
rebuild and a legacy writer then share one file. LR-004's Decision is the only stop. This is WP9.3's accepted check,
not revision 7's text. Revision 7 makes it relevant because it claims the W11 alias list is closed.

**Impact.** The same class as R6-M1, at a second site.

**Disposition.** Owner decision on scope, as for R6-M2. I recommend folding it into the 2026-11-20 every-role
correction in WP9.4-2: the projection test compares `path.casefold()` against the prefix (already lower case), with a
forged-ledger test of the case variant. Until then, amend §10.2's "The other aliases W11 names are closed" to name this
exception.

**Affected.** WP9.3's LR-003 (P-081, P-084); Stephen's 2026-11-20 decision; WP9.4-2.

## 3. Minor findings

### R7-m1 (Minor). §15's test of R6-M2's fix cannot fail on the plausible wrong implementation

**Note section.** §15 row "One file registered twice" (line 1333): "one file registered at two paths that differ in
case, the second declaring its `canonical_target` in another case, is refused by the `(volume_serial_number,
stable_file_id)` comparison even with the path half disabled in the test; two distinct files at two distinct paths are
admitted".

**Evidence.** Probe [6]:
- The decided check refuses the pair, with or without its folded-path part (`True`, `True`). Today's code does not
  (`False`). So the test fails when the check is wholly absent.
- But an implementation that only case-folds today's key, `(canonical_target.casefold(), stable_file_id)`, also
  refuses it with the path part disabled (`True`). That implementation still treats the declared target as an
  identity and still ignores the volume, which §10.2 says the fix removes. The test cannot tell them apart.
- A discriminating fixture exists and needs nothing disabled: same `(volume, file id)`, unrelated path and unrelated
  declared target. The decided check refuses it (`True`); the wrong one admits it (`False`).
- "With the path half disabled in the test" needs a seam in a replay reducer, a flag or a monkeypatch on a private
  function, to make the test meaningful. "The path half" also names §10.2's root-scoped prefix check, which a non-root
  pair never reaches, so the wording points at the wrong comparison.

**Disposition.** Fix in WP9.4-2's note. **Proposed text:** "For any role, on a forged ledger: a registration with the
same `(volume_serial_number, stable_file_id)` as a recorded one, at an unrelated path with an unrelated declared
`canonical_target`, is refused. The same file ID on another `volume_serial_number` is admitted. One file at two
case-variant paths is refused. Two distinct files are admitted."

### R7-m2 (Minor). The target half does not say "component boundary", and the plain string reading refuses the sibling

**Note sections.** §10.2 target bullet (lines 965-967); §15 prefix row: "`papers/P01-A-JRSSA-old/x.md` is not under
the root (component boundary)".

**Evidence.** `canonical_target` carries no trailing `/` (`canonical_target(final)`, `reader.py:114-121`; probe [1]).
The path half says "at a path-component boundary"; the target half says "lies strictly under". Probe [2]: under a
plain `startswith` on the folded targets, `papers/P01-A-JRSSA-old/x.md` is refused in both directions
(`target_plain_string=True`); with a `/` appended, it is not. §15's sibling control does not say which half it tests,
so an implementation that refuses the sibling through the target half fails the control without the note saying why.

**Disposition.** Fix now. **Proposed text:** "… case-folded with `/` separators, compared at a path-component boundary
(the root's folded target with `/` appended)." In §15: "the sibling is admitted by the path half and by the target
half".

### R7-m3 (Minor). "Tail" has two definitions that disagree, and item 3's table was not updated

**Note section.** §11.1 item 1 (line 1093) and the paragraph "A tail is never a cited file by itself" (lines
1116-1123); item 3's class table (lines 1100-1105).

**Evidence.**
- The note says a tail is "a token produced by a brace split, and so begins with `/`". A brace split can produce a
  token that does not begin with `/` whenever a placeholder sits inside a component: `table1_effects_{date_suffix}.json`
  gives `.json`, and `results/trajectory_tda_{survey}_nulls.json` gives `_nulls.json`. And a token can begin with `/`
  without a brace split, as an absolute path does.
- `r7_extractor.py` implements both readings (`tail_mode=provenance`, `tail_mode=slash`):

| Token | Provenance reading | `/` reading |
|---|---|---|
| `_nulls.json`, from `results/trajectory_tda_{survey}_nulls.json` with `results/trajectory_tda_bhps_nulls.json` registered | `not_a_file` | **`unregistered`**, a blocker nothing can clear |
| `/home/u/TDL/results/a/unique.json`, an absolute path | cited | **`not_a_file`**, a real citation dropped from the set |

- Under the `/` reading, the first row is R4-m4's unclearable blocker again. Under the provenance reading, "ends in" is
  applied to `_nulls.json` at a component boundary, so a template that does mean a registered file is reported, not
  blocked. The note's reasoning that "a row can always clear it" assumes the tail starts with `/`.
- Item 3's table still classes `/a.json` as a cited file by its third clause ("a token with a directory part, no
  `results/`, … a suffix of exactly one registered path"). The override lives only in the later paragraph. A reader
  implementing the table, which is the de facto rule, gets revision 6's behaviour.
- On the real roots neither reading changes anything today: the only brace-split candidates are `.json` (P01-A drafts
  and notes, P01-B notes), and no token begins with `/` (`r7_extractor_output.txt`).

**Disposition.** Fix in WP9.4-2's note. **Proposed text:** "A tail is a token that immediately follows `}` in the
text. Item 3's first row reads: '`ambiguous` or `not_a_file` (a tail, tested before every other class): a tail is
`ambiguous` when any registered path ends in it as a string, and a disambiguation row names its set; otherwise it is
`not_a_file`.'" Drop "and so begins with `/`". Add the two probe tokens to §15.

### R7-m4 (Minor). §15's "a tail no registered path ends in, reported as `not_a_file`" fails as written

**Note sections.** §15 extractor row; §11.1 item 2; "Nothing is dropped silently" (line 1129).

**Evidence.** Item 2 makes a token a candidate only if it contains `results/`, ends in a registered result's basename,
or is a bare name with a result extension. A tail such as `/b.json` has a `/`, no `results/`, and a basename nobody
registered, so it is not a candidate. It is never classed or reported. `r7_extractor_output.txt`: the fixture
`results/x_{survey}/b.json` gives only `results/x_`, and `/b.json` is absent ("FAIL … AS WRITTEN"). The fixture
passes only when the tail's basename is registered elsewhere (`/post/a.json` with `results/y/a.json`). "Nothing is
dropped silently" is true of candidates. A template whose tail names an unregistered file is dropped silently.

**Disposition.** Fix now. Either add to item 2 "or is a tail (item 3)" so that every tail is classed (recommended:
the reviewer then sees every template), or rewrite the fixture as `/post/a.json` with `results/y/a.json` registered.

## 4. Info

### R7-i1 (Info). §19 O says "within O's decided scope" over a change P-086 scopes out

§19 O (line 1463): "Revisions 6 and 7 add, within O's decided scope: … and, by Stephen's 2026-11-20 scope decision,
LR-003's equality half compares `(volume_serial_number, stable_file_id)` for every role". P-086 item 15 reads "For
role `legacy_manuscript_root` only". §10.2 and §25 state correctly that the every-role change is Stephen's extension.
**Disposition:** reword to "…; and, outside O's decided role scope by Stephen's 2026-11-20 decision, …". The register
entry at WP9.4-2's dispatch (R6-i3) should quote both the extension and R7-M2's outcome.

### R7-i2 (Info). The addendum's header still says the file covers only places 06v names

R6-i5 quoted the header: "This file gives a path to each place 06v names without one". That sentence is in the header
table's **Amends** row (addendum line 7), which `a7485bef` did not change. The commit added the clause to the intro
paragraph instead (line 15), so the header and the intro now disagree. Everything else in R6-i5 is fixed. The open-item
row's readers (LR-030, LR-033, LR-034, LR-053, LR-054) match §8's preparer column (lines 722-726) and §5.4 item 3
(line 429). The disambiguation row's readers match §11.1 items 5 and 6 and LR-054's re-run (lines 1038, 1247). The
dated entry's account of P-086 item 8 (LR-034 and LR-054) against the note (LR-033 and LR-053) matches the register.
**Disposition:** append the intro's clause to the Amends row at the next addendum edit.

### R7-i3 (Info). The directory identity: one leftover "`fstat`" and a Windows-only conversion

Confirmed by probe [0], as the note says: `os.open` on a directory is refused (PermissionError); the anchor's
`volume_or_device` equals `st_dev`, and `int.from_bytes(file_id, "little")` equals `st_ino`; a directory's `st_nlink`
stays 1 after adding a subdirectory and a file. Line cites hold: `DirectoryIdentity` at `store/anchor.py:406-410`,
`_windows_handle_matches_stat` at `:1561-1573`, `_same_physical_identity` at `preparers.py:143-148`. Two residues:
- §15's root identity row still says "records a directory identity, in the reader's `fstat` encoding". Say "in the
  reader's decimal-string encoding, from the bound anchor".
- The little-endian conversion is right for `windows-file-id-v1` only. The `posix-dev-inode-v1` anchor stores `st_ino`
  as 16 big-endian bytes (`anchor.py:1825`). All CI runs on `windows-latest` (14 jobs in `.github/workflows/`), so this
  matters only if replay is meant to give "one answer on every platform" for identities too. Add "by scheme: little
  endian for `windows-file-id-v1`, big endian for `posix-dev-inode-v1`".

### R7-i4 (Info). `str.casefold` against NTFS: over-folds, never under-folds here (accept risk)

Probe [8] created each pair on NTFS:

| Pair | NTFS treats as one name | `casefold` equal | `os.path.normcase` equal |
|---|---|---|---|
| `A.md` / `a.md` | yes | yes | yes |
| `straße.md` / `strasse.md` | no | **yes** | no |
| Kelvin sign `K.md` / `k.md` | no | **yes** | no |
| long s `ſ.md` / `s.md` | no | **yes** | no |
| final sigma `ς.md` / `σ.md` | no | **yes** | no |
| dotless `ı.md` / `i.md` | no | no | no |
| `İ.md` / `i.md` | no | no | no |
| NFC / NFD `é.md` | no | no | no |

So `casefold` can falsely refuse two distinct files (`straße`/`strasse`), and I found no pair that NTFS treats as one
name and `casefold` keeps apart. For a parent directory the read is the narrower gate: `reader.py:161`'s
`os.path.normcase` (Python 3.13 uses `LCMapStringEx`) refuses `paperſ/…` ("a parent of the registered path is
unavailable"). The paper roots are ASCII. NTFS reused no file ID across 3,000 create/delete cycles (probe [7]), so the
file-ID comparison against historical registrations does not falsely refuse a later file on NTFS. An atomic replace,
as Obsidian and `git checkout` write, changes the ID, which is LR-005's concern, not LR-003's. On a POSIX filesystem
inode numbers are reused, so the every-role file-ID comparison could falsely refuse a later registration there.
**Disposition:** accept the risk for v1 (Windows-only CI); one sentence in §10.2 if POSIX is ever a target.

## 5. Focus 1, the collision checks, run (`r7_collision_probe_output.txt`)

| Question | Result |
|---|---|
| Case-folded path, component boundary, one `(root_kind, root_id)`: every case variant refused, both directions? | **Yes.** `papers/p01-a-jrssa/_project.md`, `PAPERS/P01-A-JRSSA/_PROJECT.MD`, `papers/P01-a-JrSsA/drafts/A.TEX`: path `True` with the root recorded, and with each member recorded or open-proposed before the root ([2]). Today's check: `False` for all |
| Case-folded target prefix: refuses what it should and nothing else? | **Yes, at a component boundary.** The variants are refused; the `-old` sibling and the vault note are not ([2], [3]). Under a plain string reading the sibling is refused (R7-m2). Across a binding move it refuses nothing (R7-M1) |
| `vault_root` path beginning `papers/P01-A-JRSSA/` | Not refused by any half ([3]) |
| "Sound while … one binding's repository root, which v1 assumes": true in v1's code? | **No** (R7-M1) |
| `(volume, file id)` for every role refuses one file registered twice in two cases? | **Yes** ([6]); today's check does not |
| False refusals: `legacy_decision_log_entry`, vault file, re-registration after supersession? | **None.** The CL page beside the root and a vault note is admitted ([3]). Supersession cannot occur: the schema fixes `record_revision` to 1 and `supersedes_revision` to null, and a second registration of one path is already refused by today's path equality. No file-ID reuse on NTFS ([7]) |
| `casefold` against NTFS and `normcase` | Over-folds, never under-folds for these roots (R7-i4) |
| Anything W11 §7.2 lists still open? | Exact: open across `root_id` spellings (R7-M1). Case-folded: open at the projection prefix (R7-M2). Unicode-normalized: NTFS keeps NFC and NFD distinct, so no single physical target ([8]). 8.3: `relPath` refuses `~<digit>`. Symlink and reparse point: refused by the read (`reader.py:161`, `:165`). Resolved prefix: within one binding only (R7-M1) |

## 6. Focus 2, R6-M2's scope

§10.2 states Stephen's 2026-11-20 decision accurately: built in WP9.4-2, as an extension of O to every role, recorded
as a correction to WP9.3's accepted LR-003 replay check, entering the register at WP9.4-2's dispatch. The change sits
inside P-085's boundary ("WP9.4's code under `research_system/legacy/`"), since `_registration_conflicts` is in
`research_system/legacy/replay/reducers.py`. §15's row is testable but does not bind the mechanism (R7-m1). §19 O's
wording conflicts with P-086 item 15 (R7-i1). The statement "No real store exists before WP9.4-2" matches P-086's "Not
authorized" list.

## 7. Focus 3 and 4, revision 6's findings re-checked

| r6 finding | §25 says | Re-check |
|---|---|---|
| R6-M1 | Fixed | **Fixed** for case variants within one binding and one `root_id` (probe [2]). The stated soundness condition is false (R7-M1); the target half needs "component boundary" (R7-m2) |
| R6-M2 | Fixed, WP9.4-2 under O | **Fixed in text** (probe [6]); the test does not bind it (R7-m1); §19 wording (R7-i1) |
| R6-m1 | Fixed | **Fixed.** The `git_tracked` rule is in replay and the preparer (lines 851-856, §15 line 1331). `_check_registration` (`reducers.py:423-433`) sees both fields, as the note says |
| R6-m2 | Fixed | **Fixed in substance**; definition and table defects (R7-m3, R7-m4) |
| R6-m3 | Fixed | **Fixed.** The "Why templates" paragraph matches the extractor: `.json` and `level1_comparison_YYYYMMDD.json` as `not_a_file`, and no ladder brace piece except `.json` is a candidate |
| R6-i1 | Fixed | **Fixed**; line cites hold; one "`fstat`" residue in §15 (R7-i3) |
| R6-i2 | Fixed | **Fixed.** §10.2 names the observation schema's refusal; §15 asserts the preparer's message |
| R6-i3 | Recorded | **Recorded** in §19 O |
| R6-i4 | Fixed | **Fixed.** §24 now calls them points of the code and attributes them to the author's draft |
| R6-i5 | Fixed | **Fixed except the header's Amends row** (R7-i2) |
| R6-i6 | Carried | **Carried** as §3 row 17; `_relative` at `reader.py:105-111` refuses the trailing `/` as stated |

**§11.1 re-run** (`r7_extractor.py`, written from revision 7's text, registration set the 506 tracked files under
`results/` at `a7485bef`, roots read through `git show a7485bef:<path>`):

| Drafts only, revision 7 | P01-A | P01-B |
|---|---|---|
| Files / not text | 33 / 0 | 22 / 0 |
| Cited files | 23 | 2 |
| `ambiguous` | 4: `04_nulls_wasserstein_w2_20260407.json`, `04_nulls_wasserstein_w2_L5000_20260502.json`, `05_analysis.json`, `stratified_markov1_W2_L5000_20260502.json` | none |
| `unregistered` / no class | none / none | none / none |
| `not_a_file` | 4 directory paths and `.json` | 2 directory paths |

The same counts come out under both tail readings. **Confirmed:** four ambiguous names in P01-A's drafts and none in
P01-B's. §15's extractor fixtures, as revision 7 words them: 29 of the 30 cases I built come out as written, under
both tail readings. The exception is "a tail no registered path ends in, reported as `not_a_file`" (R7-m4). (One of my
own fixtures first failed because I built it on a suffix of a registered path. It was corrected before the final run.)

## 8. Change-log and attribution audit

Checked against the committed r6 report (`7a0c6b11`) and its artifacts:
- §25's summary of r6 (counts, roots, 22 fixtures, addendum against note and P-086): matches r6 §1, §5, §6.
- §17 claim 15, "The review of revision 6 walked every site … (its §3) and found LR-003's conflict check the only one
  that needs a prefix form": matches r6 §3.
- §10.2, "The review of revision 6 ran this: the variant passes today's `_registration_conflicts` and revision 6's
  prefix rule alike": matches r6 probe [3].
- §10.2, "the review's probe found both equal `st_dev` and `st_ino`": matches `r6_dir_identity_probe_output.txt`.
- §10.2, "the review's probe gave `False` for that pair and `True` for its control": matches r6 probe [4].
- §25's re-read line cites (`preparers.py:143-148`, `reader.py:161`, `reducers.py:409-413`, W11 `:1174`, `:1193`,
  `:1196`): all hold at `a7485bef`.
- R6-m2's "(a token that begins with `/`)" came from the r6 review's proposed text. Revision 7 kept it and added "a
  token produced by a brace split" (R7-m3).
- "which v1 assumes" is not credited to anyone and is not supported (R7-M1).

No claim is credited to a review that the review did not make.

## 9. Owner points

No new text reopens or contradicts a P-086 point. O's added checks refine O's reading. The every-role equality is
Stephen's recorded extension (R7-i1 for wording). K, item 11 ("No accepted byte changes"), still holds: no schema byte
changes. R7-M1's `root_id` pin is a new replay refusal inside O. R7-M2 widens the 2026-11-20 extension and is
Stephen's to decide.

## 10. Revision plan

- **Before WP9.4-2's code (in its note):** R7-M1 (pin `root_id` per `root_kind`, or scope by `root_kind`; correct the
  soundness sentence); R7-m1 (discriminating fixture); R7-m2; R7-m3; R7-m4.
- **Stephen:** R7-M2's scope (fold into the 2026-11-20 every-role correction, recommended, or a WP9.3 follow-up);
  record R7-i1's wording with R6-i3 at WP9.4-2's dispatch.
- **Optional, any time:** R7-i2 (addendum Amends row), R7-i3, R7-i4.
- **WP9.4-1:** nothing here blocks it.

## 11. Residual risks

- The reviewer is the author's model family (P-058).
- The probes ran on Windows NTFS only. R7-i3 and R7-i4 note what differs on POSIX.
- The probes implement revision 7's rules from its text; they are not WP9.4-2's code. Each finding names the reading
  it depends on.
- Replay sees declared identities only, so a forged ledger can lie about `stable_file_id` itself. Replay's checks are
  consistency checks, and the preparer's handle-bound read is the physical check. Every registration still needs
  Stephen's LR-004 Decision, a human stop the probes do not model.

## 12. Files

Written: this report and `reviews/wp9-4-note-r7-review-artifacts/`:
- `r7_collision_probe.py`, `r7_collision_probe_output.txt` (§5; R7-M1, R7-M2, R7-m1, R7-m2, R7-i3, R7-i4);
- `r7_extractor.py`, `r7_extractor_output.txt` (§7; R7-m3, R7-m4). Its exit status is 1 because of the one as-written
  §15 fixture that fails (R7-m4).

Not edited: the note, the addendum, the register, any store, `.apm/`, `papers/`, `results/` or the vault. The probes
wrote only under a temporary directory.
