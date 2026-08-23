# Gate 6 STORE-1A exact-subject review — 2026-08-23

## Executive verdict

**Verdict: `rework_required`. Candidate is not ready for publication.**

Reviewed subject: `d61b971ec0205cbaf3b5fe2b7dcf9d56578673ce` on
`codex/g6-spec-store-1` in the clean linked worktree
`C:\Users\steph\.codex\worktrees\g6-spec-store-1\TDL`.

The candidate implements most of the bounded STORE-1A design and stays within
the accepted size and ownership split. One reachable Major defect remains in
the writer-lock publication boundary: if the private staging name cannot be
cleaned after the canonical lock name has already been published,
`WriterLock.__enter__` raises while leaving a lock owned by the still-running
process. The composite owner never records that lock as entered and therefore
cannot release it. Subsequent governed operations see a live lock and cannot
recover it. This violates exact-generation recovery and the stated distinction
between transient cleanup failure and canonical contention.

Gate 6 remains **INCOMPLETE**. STORE-1B, the remaining capability PRs, assembled
public SPEC execution, live binding, fresh real run, backup/restore, independent
final review, and owner closure are all outside this candidate and remain open.

## Review method and independence

The governing source was `06q` lines 216–331 and 552–576. Expected behavior was
derived from that plan before comparing the implementation. Observed behavior
came from the exact committed source, committed tests, Git diff, and a direct
failure injection against the exact SHA. Prior agent summaries and the
candidate's green-test claims were not used as semantic evidence.

For strict comparisons, expected and observed inputs were traced separately:

- lock ownership expected values originate in the caller-supplied lock identity
  plus the process-instance observation; observed values come from the
  canonical lock file and filesystem generation;
- governed-manifest expected values are persisted manifest fields; observed
  values are rebuilt from Git tree/blob objects, filtered working files, index
  flags, configured origin, and ancestry queries;
- diagnostic expectations originate in schema activation and producer
  bindings; observations come from the submitted event envelope;
- preservation expectations originate in fixture declarations and active
  schema bindings; observations come from real command/ledger/object paths.

## Decision and invariant matrix

| Requirement / decision | Enforcement observed | Direct evidence | Disposition |
|---|---|---|---|
| One verified snapshot/predecessor governs an operation | Explicitly deferred with historical binding lineage, transaction, context, commands and consumers to STORE-1B (`06q` 265–270) | No parallel binding implementation is present in this diff | **defer — correct boundary** |
| No parallel current-binding lineage | Candidate adds no binding pointer, event family, or binding command | 21-path exact diff | **keep** |
| Physical root and runtime identity are held under a live lease | `CompositeWriterLock`, physical directory anchors, `LockedRoot` lease token and final fence | `lock.py` 242–444, 1983–2234; capability/alias tests | **keep** |
| Only canonical lock contention is retryable | `WriterLockContentionError` is raised for canonical lock-name collision; command consumers catch that subclass | `lock.py` 23–24, 1932–1935, 2031–2046; `service.py` 1030–1053, 1875–1915 | **keep, subject to G6-S1A-M1** |
| Every sibling `ConflictError` propagates immediately | Both recovery and submission loops catch only the dedicated subtype | `test_command_lock_retry.py` four producer/consumer controls | **keep** |
| Immutable publication owns exact generations | Private fsynced stage, no-follow hard-link claims, identity/byte checks, anchored deletion/quarantine | `lock.py` 487–1051, 1258–1562; `objects.py` 33–535 | **keep, subject to G6-S1A-M1** |
| Post-proof substitution preserves a foreign generation | Windows opens a delete-sealing handle; POSIX renames into private dirfd quarantine and rechecks identity/bytes; final names are rechecked | `lock.py` 1376–1562; substitution tests in `test_store_publication_contract.py` | **keep** |
| `missing_ok` does not excuse identity mismatch | Absence is separately returned; changed identities still raise | `objects.py` 50–98, 133–165; two absence controls | **keep** |
| Windows no-follow publication | `os.link(..., follow_symlinks=False)` is explicit and directly observed | `lock.py` 35–38; `objects.py` 27–30; Windows positive controls | **keep** |
| POSIX deletion avoids stat/unlink race | Same-parent private 0700 quarantine and dirfd-relative rename/read/unlink | `lock.py` 1275–1502; POSIX source-contract and runtime tests | **keep; platform evidence gap noted below** |
| Manifest covers code, config, schemas, contracts and dependency locks | Registry-derived Git-tree inventory covers all `research_system/*.py`, `.research-system/**`, `.python-version`, `pyproject.toml`, `uv.lock` | `governed_code.py` 31–94, 427–489 | **keep** |
| Manifest binds committed bytes, not checkout path | Git blob OID and SHA-256 are rebuilt; clean worktree, physical paths, hidden index flags and filtered working OIDs are checked | `governed_code.py` 101–295, 491–505 | **keep** |
| Same repository subject is worktree-portable; different identity/redirect fails | Repository identity is persisted origin spelling; root redirection and origin mismatch reject | `governed_code.py` 101–205; manifest tests 152–178, 217–244 | **keep; independent origin authority remains STORE-1B** |
| Divergence is classification, not authority | Read-only `DIVERGENT` relation grants no transition; strict successor explicitly excludes first retired-binding divergence | `governed_code.py` 521–620 | **keep** |
| Documentation-only descendant changes no governed bytes | Exact descendant/main/review identity, unchanged governed inventory/catalogue, doc-only diff, regular-file and hidden-byte checks | `governed_code.py` 624–738; tests 381–496 | **keep** |
| `SpecOperatorConfig` is authority-neutral | Exact locator fields only; no origin witness/admin decision/effect permission; missing store is allowed | `config.py` 423–494; schema; config tests | **keep; verified binding/authority join remains STORE-1B** |
| Inactive/full-only schema precedes producer diagnosis | Activation is checked before unbound producer; active wrong producer remains distinct | `ledger.py` 513–545; `test_store.py` 1357–1411 | **keep** |
| S-014 known-bad binds a declared mutation; known-good stays unmutated | Calibration supplies first declared mutation only to known-bad; known-good receives the original payload | `calibration.py` 160–192; direct S-014 control | **keep** |
| Scenario-A frozen trace equals its producer | Contract is exactly two `RouteSelected` plus one `ProviderCommandIssued`; equality control executes producer | `release_snapshot.py` 45–50; `test_gate3_scenarios.py` 60–71 | **keep** |
| Release fixture uses active schemas and preserves retry semantics | Active grant/admin/command identities are derived; two services reach real filesystem contention; stricter scoped retry tests remain | `release_tranche.py` 203–295; release tests 1717–1800 | **keep** |
| Size hard stop | 21 changed files; 4,494 added lines, below 35/5,000 | `git diff --numstat d61b971^ d61b971` | **keep** |
| Public observable remains bounded | STORE-1A exposes foundations only; binding CLI, context and consumer migration are absent and explicitly deferred | Diff plus `06q` 265–270 | **defer — correct boundary; capability not runnable** |

## Required finding

### G6-S1A-M1 — Major — failed staging cleanup strands a live canonical writer lock

**Claim.** `WriterLock.__enter__` can publish `runtime/writer.lock`, fail while
deleting its private staging hard link, raise to the caller, and leave the
canonical lock owned by the current live process. The surrounding composite
owner has not yet set `lock_entered`, so its acquisition cleanup skips that
lock.

**Evidence.** `lock.py` 1922–1935 publishes the canonical link before staging
cleanup. Lines 1938–1954 treat any staging cleanup error as fatal without
removing or adopting the already-published lock. `CompositeWriterLock` sets
`lock_entered = True` only after `lock.__enter__()` returns (`lock.py`
2063–2067), while `_cleanup_members` releases only members with that flag
(`lock.py` 2114–2125).

**Concrete failure.** A sharing violation, antivirus/file-indexer handle, I/O
fault, or injected cleanup error affects the staging name after the hard link
to `writer.lock` succeeds. The submit reports failure. `inspect_lock` reports
the remaining lock as `live`, so stale-lock reclamation correctly refuses to
remove it. Every later operation in the same long-running process blocks until
manual intervention or process exit.

**Direct falsifier.** At exact SHA, replacing only
`_delete_exact_regular_file` for the private `.writer.lock.*.tmp` name with an
`OSError` produced:

```text
OSError injected cleanup failure
lock_exists True
state live
```

**Impact.** A recoverable local cleanup fault becomes an unrecoverable
same-process availability failure. It breaks the STORE-1A exact-generation and
crash/recovery invariant and misleads retry handling: the first call sees an
I/O error; later calls see genuine live contention that cannot resolve.

**Required disposition: fix now.** Once canonical publication succeeds,
`__enter__` must either (a) return an acquired lock while retaining safe cleanup
responsibility, or (b) synchronously delete the exact canonical generation
before propagating the staging-cleanup error. The composite owner must never
observe an exception with an untracked live canonical lock. Preserve foreign
generations if either name changes.

Add a red/green control that injects staging cleanup failure after canonical
publication and proves: no untracked canonical lock remains after the raised
error; a foreign substituted canonical generation is preserved; and the next
ordinary acquisition succeeds without stale/live misclassification.

**Affected work.** STORE-1A publication boundary and KAN-105. It does not alter
the STORE-1B split, authority model, public CLI, or live-store lineage.

## Minor issues and platform evidence gaps

- No nit is publication-blocking independently of G6-S1A-M1.
- The exact review ran on pinned Windows CPython 3.13.5. Two POSIX runtime tests
  in the focused publication module were skipped by platform, while the POSIX
  implementation and structural controls were inspected. A Linux execution is
  useful cross-platform evidence before STORE integration, but Windows is the
  accepted live runtime and this is not a second material finding.
- `repository_identity` is the configured origin spelling, not an independently
  authenticated origin witness. That is acceptable only because STORE-1A
  grants no binding authority and `06q` assigns the independent
  `ApprovedProjectBinding` origin-witness join to STORE-1B.

## Test and evidence record

Commands executed from the exact clean worktree:

```text
git rev-parse HEAD
git branch --show-current
git status --short
git diff --numstat d61b971^ d61b971
git diff --name-only d61b971^ d61b971
```

Focused pytest selection (343 collected) covered publication, store, typed
retry, governed manifest, operator config, calibration, Gate-3 Scenario-A,
Gate-5 release tranche, and release publication. It progressed without a
reported failure but the session was interrupted before a terminal summary;
this review therefore does **not** claim that aggregate as green. The direct
falsifier above is decisive regardless of nominal suite status.

## Revision and re-review plan

1. Repair G6-S1A-M1 at the writer-lock ownership boundary; do not change retry
   typing or introduce another recovery lineage.
2. Add the exact post-publication cleanup-failure negative and next-acquisition
   positive.
3. Run the changed publication and command-retry tests, then the frozen
   STORE-1A selection once at the new exact head.
4. Obtain a focused independent re-review of this finding's prescribed
   mechanism. Any later commit is a new exact subject.

## Residual risk and change log

Even after this repair, STORE-1A remains a foundation candidate, not an
integrated capability. STORE-1B must still supply the one historical binding
lineage, transactional recovery identity, shared verified context, public CLI,
and consumer migration. No live-store write or owner acceptance is implied.

This review added only this report. It changed no implementation, test,
planning authority, Git state, Jira record, live store, PR, or external review
state.
