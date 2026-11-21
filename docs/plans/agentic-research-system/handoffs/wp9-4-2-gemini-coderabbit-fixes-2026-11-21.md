# Follow-up 3: WP9.4-2, the CodeRabbit fixes on PR #443

CodeRabbit reviewed PR #443 at `e1fd58eb` (review `6003745058`). It left 19 inline findings, 2 outside the diff, 1
nitpick, and 1 that it marked unverified. The reviewer checked each one against the code, the note and the accepted
WP9.3 and WP9.4-1 code. Seventeen need a change, in fixes F1 to F7, T1 to T6, R1 and R2 below (F4 and T5 each cover
two findings). Six need none, and the reasons are at the end. Do not reply on the PR; replies are posted separately.

Same branch, same worktree, same rules as before:
- commits written with `git commit -F <file>`, the file UTF-8 without a BOM;
- never `--no-verify`, no push, no PR, no merge;
- the handover's §4 boundary, with `reader.py`'s `member_path` and the two extra `authority.py` lines allowed. None of
  these fixes touches `reader.py`, `authority.py`, `schema_registry.py` or a D-4 file. If one turns out to need that,
  stop and report.

## Where you are

- Worktree: `C:\Users\steph\TDL\.apm\worktrees\wp9-4-2`
- Branch: `pipe/w9-wp9-4-2-full-path`, head `e1fd58eb`, pushed as PR #443

Before any write, confirm the branch, that HEAD is `e1fd58eb`, and that `git status --short` is clean.

## Code fixes

### F1. LR-011 must not admit a manuscript root (CodeRabbit's outside-diff Major, `preparers.py:751`)

K reading 1 (note §10.2 item 1) is **LR-015's** path rule. You put it in `_source_matches_registration`
(`replay/reducers.py:622-663`), which LR-011's `_check_inventory` (`:667`) also calls. So replay now admits a light
inventory whose registration is a `legacy_manuscript_root` and whose source is a member path. The preparer refuses it
only by accident: `_read_source` (`preparers.py:742-760`) calls `read(registration)`, and the reader refuses a root
without a member path.

CodeRabbit suggests passing the member path in `_read_source`. **Do not do that**: it would open the light path to
paper roots, which take the full path (W9 §8.4). Instead:
- in replay, make LR-011 refuse a `legacy_manuscript_root` registration with its own message, before the source check.
  Every other role keeps WP9.3's check unchanged;
- at the preparer, refuse it at LR-011 too (`preparers.py:696-699`), with its own message, before `_read_source`. Also
  check `RecordLegacyLightInventory` (LR-014, `:1159-1175`): its proposal cannot exist once LR-011 refuses, so say in
  the record whether it needs its own refusal;
- add one replay control and one preparer control, each asserting its own message, and a mutation for each guard.

### F2. Per-path suspension for family adoptions of a root member (inline, reported on `replay/reducers.py:645`)

The comment's code is in `research_system/legacy/projection_read.py:118-122`. For a `legacy_manuscript_root`, the
`families` branch suspends an adoption when any later `json_family_set` observation of the registration names an
adopted family, even one that reads another member. The `whole_file` branch above it (`:112-117`) already compares the
source path. That is K reading 3 (per source path for a root), so apply it to the `families` branch too. Keep the
current rule for every other role. Update the docstring CodeRabbit names (`projection_read.py:48-51`) to match. Add a
control in which observing `root/b.json` with a shared family name leaves the adoption of `root/a.json` active, plus
the non-root control, and a mutation.

### F3. LR-039's replay must check each family against its observation (inline, `replay/reducers.py:1345`)

`_check_citation_status_lr039` (`:1338-1361`) never checks that `family_name` belongs to the cited observation, so a
forged unadopted entry with an unknown name replays clean. The preparer refuses it only because it compares the set
with the extractor's. Use the extractor's own rule (`citations.py`, `registered_result_projections`):
- `family_name == "whole_file"` only when the observation's selector is `whole_file`;
- otherwise the selector is `json_family_set` and `family_name` is in its `family_names`.

Refuse anything else with its own message, for adopted and unadopted entries alike. Add a replay control that changes
only the family name and recomputes both hashes and the record ID, and a mutation.

### F4. Catch the JSON nesting limit (inline `citations.py:90`; outside-diff `evidence.py:88`)

`json.loads` raises `RecursionError` on deeply nested input, and neither site catches it:
- `citations.py:86-91`: treat it like a parse failure, so the file keeps its raw-text tokens;
- `evidence.py` (around `:88`): raise `EvidenceRefused`, as for other malformed JSON.

Add a control for each.

### F5. A failed results listing must refuse (inline, `citations.py:427`)

`_git_result_directories` (`citations.py:422-426`) returns an empty set when `ls-tree` fails, so every real result
directory becomes a false `unregistered` blocker. Raise a domain error instead (`IntegrityError`, or `EvidenceRefused`
if that is what its callers handle). A successful empty listing still returns an empty set. Add a control.

### F6. `cited-families` prints no grant subject for an ineligible extraction (inline, `cli.py:2024`)

When the extractor reports blockers, or the cited-family set is empty, LR-039's preparer refuses, so no record can
have the printed ID. In those two cases print the report without `derived_record_id`. Keep printing it for a non-empty,
blocker-free set even when the two derivation hashes differ. Add a CLI control.

### F7. Type the disambiguation default (CodeRabbit's unverified "additional comment", `citations.py:300`)

`disambiguation: Mapping[...] = ()` should default to `None` and be normalised to an empty mapping. No behaviour
change.

## Test fixes

### T1. The second-registration test isolates each prefix guard (inline, `test_w9_wp9_4_2_replay.py:1223`)

This is the gap your M16 and M17 runs found. In `test_p087_item6_second_registration_refused_with_active_whole_file_adoption`,
replace the third form with two: one whose path is under the recorded root and whose target is not, and one whose
target is under the root's target and whose path is not. Rerun M16 and M17 against that test alone and record both as
caught. Update record §6.2's P-087 item 6 line.

### T2. Replay records the reference edges (inline, `test_w9_wp9_4_2_replay.py:1036`)

`test_w9_t21_graph_cycles_among_root_inventory_mapping_status_and_transition` calls `_add_edges` directly, so it does
not show that replay records edges. Keep it, and in a replay flow that already records a root, inventory, mapping,
citation status and transition, assert `state["reference_edges"]` holds each one's expected edges. Add a mutation that
drops one replay row's `_add_edges` call and report it caught.

### T3. The commit-time window re-read at LR-044, LR-054 and LR-055 (inline, `test_w9_wp9_4_2_runtime.py:824`)

Each window test changes `main.tex` before `submit`, so the preparer's first check refuses, and no test fails if the
commit-time re-read is removed. WP9.3-2 and WP9.4-1 both test it. Follow their pattern
(`test_w9_wp9_3_2_runtime.py:179-200`, and `test_w9_wp9_4_1_runtime.py:895` onwards): change the source after the
first read and before the commit re-read, assert the refusal and an unchanged snapshot, and keep the no-edit run as the
positive control. Run a mutation that removes only the commit re-read for each of the three rows, and report it caught.

### T4. Retry every recorded full-path step (inline, `test_w9_wp9_4_2_runtime.py:1206`)

The idempotency check retries only the first and last step of each list. Retry every step and compare each retry with
its original receipt.

### T5. Name each guard's message (inline: `test_w9_citations.py:339`, `test_w9_reader.py:286`)

- In the malformed-disambiguation cases, pair each payload with its guard's own `EvidenceRefused` message, and keep the
  other fields, `citing_path` included, valid.
- In the reader's member-path cases, give each one its expected `ReadRefused` message. The sibling
  `papers/P01-A-JRSSA-extra/trap.md` expects "member path is not strictly under the registered root".

### T6. A stale citation-status reference (nitpick, `test_w9_wp9_4_2_replay.py:214`)

Add the missing case: a new status whose `supersedes_status_ref` names the older status after its successor is
current, with revision and hash equal to the current status's, so only the ID differs.

## Record fixes

### R1. State exactly what blocks LR-055 (inline, record `:133` and `:295`)

"Any change under the root" overstates it. LR-055 refuses when the tracked file set under the root changes, when a
mapped inventory row's blob changes, or when the root's physical identity changes. An untracked file does not block.
Also say that WP9.6 must make LR-055 resolve the replacement inventory, because `_prior_lr054_inventory_for_registration`
follows the original LR-054 mapping; superseding the inventory is not enough on its own. Change §3.1 item 5 and §7
together.

### R2. M04 (inline, record `:213`)

M04 is recorded as "bypass `_evidence_git` (`_git` without `--no-replace-objects`)", but `reader._git` has added the
flag itself since `707cbe0d`, so that substitution leaves Git's behaviour unchanged. Rerun M04 at the current head
exactly as recorded and report the result. If it survives, mark it as an equivalent mutation, and add one that does
remove the flag from the disambiguation read (for example, both `_evidence_git`'s and `reader._git`'s flag).

### R3. The rest of the record

Add every new guard, control and mutation to §1.2 to §1.5 and §6.2 as before, and add a §8 listing these findings, the
fix for each, and the six not taken, with the reasons below.

## Not taken (no change)

- **The empty family set** (inline, `preparers.py:1119`). The citation-status schema requires `families` to have at
  least one item (`legacy-paper-citation-status.schema.json`, `minItems: 1`), so the preparer's refusal matches the
  schema.
- **Revalidate the binding in `cited-families`** (inline, `cli.py:2032`). The preview is advisory. LR-039's preparer
  re-runs the extractor and re-derives the ID under the binding in force at submit, so a stale preview is refused, not
  admitted.
- **Escaped JSON strings in the raw-text scan** (inline, `citations.py:94`). Note §11.1 item 1 scans decoded string
  values "as well" as the raw text, so the code follows the note. The effect is a false blocker, which refuses rather
  than admitting a wrong status. Record it in §7 as a known limit of the note's rule.
- **Close every anchor** (inline, `preparers.py:241`). It is the same pattern as WP9.3's accepted reader
  (`reader.py:199-205`). A change belongs with both.
- **Binary mode for `ls-tree`** (inline, `preparers.py:539`). A name containing `\r` cannot exist on Windows, the
  `_git` text mode is the reader's shared helper, and the effect refuses.
- **The authority root in the no-write snapshot** (inline, `test_w9_wp9_4_2_runtime.py:56`). It is the same
  `_snapshot` as WP9.4-1's accepted tests (`test_w9_wp9_4_1_runtime.py:73`). A change belongs with both.

## Verification

- `ruff check` and `ruff format --check` on every changed `.py` file.
- Each new mutation, run and restored as before.
- Serial `--no-cov` runs, one file per command, of every test file you change, with their wall times. Report them
  against the budget. The branch now adds 183s of the 300s, so these fixes may add at most 117s. If they would go over,
  stop and report before cutting any test.
- `test_w9_legacy_replay.py`, `test_w9_wp9_3_replay.py` and `test_w9_wp9_3_2_runtime.py` after F1, because F1 changes
  LR-011.

## What to hand back

1. Status first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`.
2. The new head, and `git log --oneline e1fd58eb..HEAD`.
3. For each of F1 to F7, T1 to T6 and R1 to R3: what changed, with `path:line`.
4. Each new mutation and its result, and M04's rerun.
5. The test times against the budget.

Do not describe the work as reviewed, accepted or ready to merge.
