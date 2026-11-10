# Issue #415 findings: refusing writes from pre-pin code after a later W0 signature pin

**Status:** investigation and proposal only. No code changed. For Stephen's decision.
**Issue:** ZK-Theory/TDL#415. **Governing text:** the WP9.3 design note, revision 5 (PR ZK-Theory/TDL#411, head
`97dc7cbb`), §9.1 "When the ID becomes reserved", §4.3 and §18.
**Code read at:** `main` `44b6f2b5`. Line numbers below are at that commit.
**Date:** 2026-11-08.

## 1. Summary

The issue asks whether code can refuse a W9 or W11 writer still on pre-pin code once a store has passed a later W0
signature pin. The note says it cannot (§9.1, last freeze bullet; §18, last human-review item), because
`validate_persisted_governed_code_manifest` never compares the recorded commit with the physical `HEAD`
(`store/governed_code.py:551-553`).

That premise is narrower than the code. The function the note cites validates **historical** binding links. The
function every production writer admits through, `load_current_binding`, **does** compare the checkout's `HEAD` with the
store's bound commit, on every operation (`store/current_binding.py:847-853`, `:913-921`). A store's current binding
therefore already decides which code may write to it.

**Recommendation (option C below):** make "release" of a later pin, for each W9 store, the existing owner operation
`AdvanceStoreBinding` to a `main` commit that holds the pin. From that advance, a writer on pre-pin code is refused by
the binding loader before it can replay, prepare or append, on the W9 path (once the note's §13 `ars legacy submit`
lands) and on the W11 SPEC path today. No new store event, schema, command or per-write cost is needed. The freeze
shrinks to the window between the final pre-pin check and the advance, and a claim made in that window fails closed at
the first post-advance replay instead of passing silently.

The two options the issue names both work mechanically, and the probes confirm it, but each needs new code and a store
write per pin, and each is redundant once the binding is used.

## 2. Question 1: a store-side marker

**Does `replay_legacy` fail closed on an event type it does not recognise?** Not by itself. It reduces only W9
transactions and skips every transaction whose command type is not a W9 command (`legacy/replay/driver.py:84-86`;
the predicate is `legacy/commands.py:34-44`). It refuses an unknown event type only inside a W9 transaction
(`driver.py:143`), and a W9 event type under a non-W9 command (`driver.py:121-123`).

**But both runtimes run the generic replay first, and that does fail closed.** `LegacyRuntime._replay` calls
`replay_shared`, then `replay_discovery`, then `replay_legacy`, before any preparation or append
(`legacy/runtime.py:279-293`, called at `:373-374`). `DiscoveryRuntime._submit_authorized` calls `replay_discovery`
(`discovery/runtime.py:474-484`), which runs the same generic `_replay` over the whole ledger
(`discovery/replay/driver.py:68-75`, `projection/replay.py:1184-1201`). The generic replay refuses a marker the running
code does not know at one of three points:

- a command schema identity the registry does not hold: `projection/replay.py:1251-1260` ("command schema identity
  mismatch");
- a known command schema but an unknown event type: `apply_event`'s last branch, `projection/replay.py:1124-1125`
  ("unsupported event type");
- on the W11 path, a command type with no active binding row: `discovery/ledger_integrity.py:84-99`, raised at `:136`.

So a marker event appended at a pin's release would make pre-marker code refuse every W9 and W11 command on that store.
Probes M1 and M2 (§6) show it for both marker shapes and both paths.

**Would it break replay of earlier ledgers?** No. A ledger without the marker replays unchanged (probe M0), and a prefix
ending before the marker still replays on pre-marker code (probe M3). Pre-marker code refuses only a ledger that holds
the marker, which is the intent. Read-only tools on pre-marker code (`ars legacy status`, `cli.py:1513-1524`) refuse it
too.

**The limits.** A marker type refuses only code that predates the type. The second later pin's marker has the same type
as the first, so code holding the first pin already knows it and would not refuse. A marker is therefore one-shot
unless its replay also compares the pin set it records with the code's own pin set, which is option B. It also needs a
new command, schemas, a binding row, a grant kind, a reducer branch in the generic replay and a W11 partition rule, a
new append site in the 06h manifest (`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`) and the
runtime-binding census, and a live store write at every pin.

## 3. Question 2: comparing pin sets, and what the binding already enforces

**A pin-set comparison does not touch the governed-code rule.** The preparer would compare a module constant
(`ACCEPTED_W0_SIGNATURES`, which WP9.3 adds; it is not on `main` yet) with a pin set read from the store. It reads no Git
object and no `HEAD`, so `validate_persisted_governed_code_manifest` is unaffected. Two limits:

- the store needs somewhere to record its pin set, which is option A's marker or an equivalent record, with the same
  costs;
- it refuses only code that already contains the comparison. Code before the comparison ships has nothing to compare.

**The binding already compares `HEAD`.** The note's premise cites the persisted validator, whose docstring says it never
compares with `HEAD` (`governed_code.py:549-553`). That is the check for historical links in the binding chain
(`current_binding.py:908-912`). The admission of the current binding does more:

- `HEAD` and its tree must equal the binding's `git_head` and `git_tree`, unless the binding is schema 1.2.0
  (`current_binding.py:847-851`);
- the worktree must be clean, untracked files included (`:852-853`), so the imported modules are the committed bytes;
- for a 1.2.0 binding whose subject is not exact, the checkout must be a reviewed, documentation-only descendant of the
  bound commit that equals `refs/heads/main` (`:913-921`; `governed_code.py:751-801`, the descendant test at `:784-785`
  and the governed-file equality at `:791-792`). Otherwise `validate_governed_code_manifest` requires `HEAD` to equal
  the bound commit (`governed_code.py:526-540`, the comparison at `:535`);
- the binding names exactly one code root (`current_binding.py:842`), and the CLI derives that root from the running
  package's own location (`cli.py:121-136`, `config.py:534-536`). So the `HEAD` checked is the `HEAD` of the checkout
  the running code was imported from.

A pin PR changes `research_system/legacy/accepted_w9.py`, a governed file (`governed_code.py:75-77`). So once a store's
binding is advanced to the pin commit C1, a checkout at C0 is neither C1 nor a descendant of it, and is refused. Before
the advance, a checkout at C1 changes governed code relative to C0 and is refused too. Probes B1 to B4 (§6) show both
directions and the documentation-only control.

**Which writers pass through it.**

- W11: the only production construction of `DiscoveryRuntime` is `SpecCoordinator._discovery`
  (`discovery/spec.py:339-351`). `SpecCoordinator` admits through the binding at construction (`spec.py:213`) and
  re-validates it in its operations (`:331`, `:355`, `:699`, `:779`, `:821`, `:917`). A changed binding gives
  `ConflictError` (`current_binding.py:833-834`), so a long-running coordinator started before an advance cannot write
  after it.
- W9: today no production command writes W9 records; the `ars legacy` CLI is read-only (`cli.py:1513-1524`). The note's
  §13 makes `ars legacy submit` the one mutating subcommand and has it load the binding through `load_current_binding`
  before building `LegacyRuntime`. Once that lands, the W9 write path is checked the same way.
- Not covered: anything that builds `LegacyRuntime` or `DiscoveryRuntime` directly (tests, scripts), and local
  administration through `--config` (`cli.py:161-166`). These are not the dispatch path, and the authority-administration
  writers do not claim W9 or W11 record IDs.

## 4. Question 3: cost per write, and W11

| Option | Marginal cost per write | New code | Store writes per pin | Refuses pre-pin W9 | Refuses pre-pin W11 | Repeatable across pins |
|---|---|---|---|---|---|---|
| A. Marker event of a new type | None measurable: one more event in the full replay every command already runs | Command, schemas, binding row, grant kind, reducer and partition branches, 06h and census entries, tests | One marker per store | Yes (M1) | Yes (M2) | No, one-shot per type |
| B. Pin-set comparison against a store record | O(markers) inside the same replay | A plus the comparison in both preparers | One record per store | Only code that already has the check | Same | Yes |
| C. Release by advancing the store binding | None: the loader already runs on every SPEC operation and will run on every `ars legacy submit` | None required; one optional guard test (§5) | The existing `AdvanceStoreBinding` | Yes, once §13 lands (B2) | Yes, today (B2) | Yes: every later pin is a new commit |

The loader's own cost (Git subprocesses for `HEAD`, status and the governed manifest) is already paid by every W11 SPEC
operation and is built into §13's design. I did not time it on the real repository; option C adds nothing to it.

**W11 needs it as well as W9.** §4.3 notes that W11's admissible-target check reads only Discovery's projection, so
WP9.3-1 adds a check against W9's fixed identities, the pinned W0 refs among them, read from code constants. A W11
writer on pre-pin code holds the old constants and would admit a W11 command that takes the newly pinned ref, for
example as a `new_review_id`. Option C covers W11 automatically, because the binding is per store and per code subject,
not per command family. Option A gets W11 coverage for free, because the generic replay both runtimes run refuses the
marker (M2). Option B would need its comparison written into the W11 preparer as well as the W9 one.

## 5. Recommendation and what it changes

1. **Release a later pin by advancing each W9 store's binding** (`AdvanceStoreBinding`, owner action
   `advance-clean-descendant-store-binding`, `store/binding_service.py:170-232`) to a `main` commit that holds the pin.
   Every later `main` commit also holds it, because the pin tuple is append-only (§9.1). This is not a new operation:
   any merge that changes `research_system/` already needs an advance before writers on the new code can write.
2. **The §9.1 freeze becomes narrower and partly mechanical.** Before the advance, only pre-pin code can write (B3), so
   the freeze still matters from the final check to the advance, and the ledger-head re-read still belongs in the
   checklist. After the advance, pre-pin code cannot write (B2). If a pre-pin writer did claim the ID in the window, the
   first replay on the pinned code refuses the ledger (the note's cross-pin control), so the failure is a store that
   refuses writes, not a silently corrupted one. Recovering from it (re-deriving with `#<n>` after release) needs an
   owner ruling, because the note's replace-before-release rule no longer applies.
3. **The §18 item changes from recorded to checked.** "Does every writer of the store run the pinned commit?" becomes
   "is the store's current binding at a commit that holds the pin?", which the store's current-binding pointer answers.
4. **One enforcement artifact is worth adding, with your go:** a census test that the only non-test constructions of
   `LegacyRuntime` and `DiscoveryRuntime` are behind `load_current_binding` (`spec.py:341` and §13's CLI), with a
   negative control that adds an unbound construction and watches it fail. Without it, the property depends on nobody
   building a runtime elsewhere. A stronger form, passing a `VerifiedCurrentBinding` into each runtime and re-validating
   under the writer lock, touches every runtime test and is not recommended now.

**Text this would change, all yours to decide.** §9.1's last freeze bullet and §18's last human-review item state that
code cannot refuse an old writer after release. If you accept option C, both need revising, either in a revision 6 of
PR #411 before merge or in a follow-up after it. I have not edited the note or the decisions register.

**If you prefer not to rely on the binding,** option A plus B is the fallback: it works (M1, M2) and does not touch the
governed-code rule, but it costs a new command family, a store write per pin, and the comparison in both preparers.
Neither option is needed for the first pin, which lands before W9 genesis on any store (§9.1).

## 6. Probes

A throwaway pytest file, outside the repository in the session notes folder as
`issue-415-writer-version-probes.py`. It opens only stores and Git repositories that pytest creates under `tmp_path`,
using the existing fixtures `_store`/`_genesis_command` (W9 runtime tests), `_bound_fixture` (current-binding tests) and
`governed_repository` (governed-code tests). Run from this worktree with
`.venv/Scripts/python.exe -m pytest --no-cov -q -s -p no:cacheprovider --rootdir . -c pyproject.toml <file>`.
Result: 10 passed in 49 s.

| Probe | What it shows | Outcome |
|---|---|---|
| M0 | Control: a ledger with W11 and W9 genesis replays on the W9 and W11 preparer paths | Passes |
| M1 (two shapes) | `LegacyRuntime._replay` on that ledger plus a forged marker refuses it | Unknown command schema: "command schema identity mismatch at 3". Known command schema, new types: "unsupported event type: W0SignaturePinRecorded" |
| M2 (two shapes) | `replay_discovery` (the W11 preparer's replay) refuses the same ledgers | "command schema identity mismatch at 3"; "Discovery persisted schema provenance mismatch at 3" |
| M3 | The prefix before the marker still replays on pre-marker code | Passes |
| B1 | The full loader on a bound scratch store refuses once a pin commit moves `HEAD` off `git_head` | "Git subject changed" |
| B2 | A 1.2.0 binding advanced to pin commit C1, checkout at C0: the exact check and the documentation-successor check both refuse, with `main` at C1 or rewound to C0 | "differs from the candidate head"; "not a descendant" |
| B3 | Binding still at C0, checkout at C1: pinned code is refused before the advance | "differs from the candidate head"; "changes governed code" |
| B4 | Control: the bound commit, and a documentation-only descendant on `main`, are admitted | Passes |

**Not verified.** B2 and B3 call the governed-code validators directly rather than running a real `AdvanceStoreBinding`
through `load_current_binding`; the loader's branch to those validators is read from `current_binding.py:896-921`, not
executed with a 1.2.0 binding. The loader's cost on the real repository is not measured. §13's CLI does not exist yet,
so the W9 half of option C is a property of the design note, not of `main`.
