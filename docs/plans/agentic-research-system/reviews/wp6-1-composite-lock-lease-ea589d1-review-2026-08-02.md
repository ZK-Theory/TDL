# WP6.1 Composite-Lock Lease Cleanup Exact-Subject Review

**Date:** 2026-08-02

**Verdict:** `accept_exact_subject`

**Findings:** 0 Critical, 0 Major, 0 Minor

**Review mode:** fresh independent exact-subject remediation review; candidate
code and tests were read-only; this record is the only review-owned file.

## 1. Exact subject and authority boundary

| Field | Exact value |
|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\d08e\TDL` |
| Branch | `codex/wp61-composite-lock-ea589d1-review` |
| Parent | `1946cd6ec59ae64861b902805934f5c3e37de8ce` |
| Candidate | `ea589d1a0b450828a7b6d013e2334dfccdca5ee5` |
| Candidate tree | `2baa95d713fd3d48deab386e4f35a7af81397218` |
| Fully qualified remote head | `refs/remotes/origin/codex/wp61-composite-lock-ea589d1-review` = `ea589d1a0b450828a7b6d013e2334dfccdca5ee5` |
| Parent ancestry | `git merge-base --is-ancestor parent candidate` exited 0 |
| Entry state | detached `HEAD` at the candidate; named local branch ref also at the candidate; clean |
| Branch attachment | exactly one deterministic `git switch --no-guess codex/wp61-composite-lock-ea589d1-review` |
| Candidate delta | exactly `research_system/store/lock.py` and `tests/research_system/unit/test_store.py` |
| Review-owned path | this report only |

The candidate and remote head were rechecked after branch attachment. No PR,
Jira, CodeRabbit, provider, credential, merge, or external-party action was
taken. This verdict applies only to `ea589d1a...` and does not authorize a
later commit, integration, or merge.

## 2. Review question and governing contract

The exact question was whether the Slice L correction closes the Windows
directory-anchor cleanup defect: a failed close of one acquired handle must not
prevent attempts on other acquired handles, and cleanup must not replace an
active identity, fence, or acquisition error.

The governing design is
`docs/plans/agentic-research-system/implementation/06k-wp6-1-authority-source-and-lock-identity-design.md`:

- §4.2 L-8 requires reverse-order release, attempted cleanup of every member,
  first cleanup error chained beneath the original acquisition error, and
  anchors closed last on normal release as well;
- §4.3 steps 5 and 8 require the complete final fence before protected work and
  lock release before runtime/root-anchor closure; and
- §10 leaves stronger handle-relative store I/O and hostile privileged
  filesystem actors outside this narrow correction.

The runtime lifecycle plan
`docs/plans/agentic-research-system/implementation/06a-wp6-1-runtime-task-lifecycle-plan.md`
was also read in full. No lifecycle, schema, contract, event, receipt, or
authority meaning is changed by this candidate delta.

## 3. Invariant-by-invariant disposition

### 3.1 Every acquired Windows handle receives a close attempt

`_open_windows_anchor` retains `probe` and `handle` until their close succeeds
and iterates both in its `finally` block (`research_system/store/lock.py:279-372`).
The `first_close_error` value is recorded but does not short-circuit the loop.
Composite cleanup similarly releases every entered writer lock and then visits
every runtime/root anchor in reverse member order while retaining the first
error (`research_system/store/lock.py:707-735`).

The candidate’s Windows controls exercise the primary-error case at
`tests/research_system/unit/test_store.py:280-346` and the no-primary case at
`:349-407`. The first records both `probe` and `followed` attempts; the second
records `probe`, its retry, and `followed` after the first close fails.

An additional disposable probe used the real Windows anchor backend, three real
temporary roots, and an actual `WriterLock` conflict on the last member. One
injected anchor-close failure still produced six anchor-close attempts (two per
acquired member, including the partially prepared conflicting member); the
raised `ConflictError` remained primary and its `RuntimeError` cleanup failure
was exposed as `__cause__`.

**Disposition:** satisfied; no finding.

### 3.2 Primary identity, fence, acquisition, and body errors remain primary

`_raise_primary_with_cleanup` explicitly raises the primary error from the
cleanup error (`research_system/store/lock.py:112-118`). The Windows anchor
path stores primary `ConflictError`, wrapped directory `OSError`, or other
`BaseException` values and raises them only after all tracked handles have been
attempted (`:350-372`). The final-fence observer does the same for fence errors
(`research_system/store/lock.py:670-689`). Composite acquisition chains cleanup
under the acquisition error (`:768-784`), and normal `__exit__` chains cleanup
under a body exception (`:811-835`).

The Windows primary-error control changes the followed identity, makes its close
fail, and asserts the raised error is the identity `ConflictError` with the
close failure as its cause (`tests/research_system/unit/test_store.py:295-346`).
The real public probe separately passed a body `ValueError` through
`CompositeWriterLock.__exit__`; it remained the raised exception with the
injected close failure as its cause.

**Disposition:** satisfied; no finding.

### 3.3 With no primary error, the first cleanup failure surfaces after all attempts

The no-primary Windows control expects the first probe close error while still
asserting the later followed-handle attempt (`tests/research_system/unit/test_store.py:349-407`).
The public no-primary probe entered a real composite lock, injected one failure
at release, observed both runtime/root anchor attempts, and raised only after
both attempts with the first cleanup error.

**Disposition:** satisfied; no finding.

### 3.4 Failed close does not mark a live handle released

`_DirectoryAnchor.close` sets `_closed` only after `_close_impl` returns
successfully (`research_system/store/lock.py:105-109`). The dedicated control
asserts `_closed is False` after the first failed close, retries the same
handle, then observes `_closed is True` only after success
(`tests/research_system/unit/test_store.py:409-441`). The Windows primary
control likewise leaves the failed followed handle live at `:342-346`.

**Disposition:** satisfied; no finding.

### 3.5 Preserved normal, sibling, lease, ordering, and replacement behavior

- Normal one-root success, lease lookup, invalidation after release, and retry
  token separation remain covered at
  `tests/research_system/unit/test_store.py:89-156`.
- Sibling-wide cleanup retains reverse release order and visits every runtime
  and root anchor even when one sibling release fails at
  `tests/research_system/unit/test_store.py:457-518`.
- The integration seam confirms one physical lock for duplicate roots,
  complete cleanup after a later-member conflict, stable physical-ID order for
  reversed input, and contention behavior at
  `tests/research_system/integration/test_wp6_1_scope_task_authority.py:1012-1094`.
- Windows normal/case/relative/extended-path aliases and reparse aliases remain
  covered at `:1097-1139`; per-member replacement and final-fence cleanup remain
  covered at `:1141-1243`; held root/runtime replacement protection and the
  acquired submission lease remain covered at `:1246-1301`.

**Disposition:** satisfied; no finding.

### 3.6 Protected identities and negative-case quality

The candidate-to-parent path surface is exactly the two authorized paths; no
schema, contract, design, event, receipt, provider, or `service.py` path moved.
The exact Git-blob comparison of the `WriterLock` class body is equal on both
subjects (SHA-256
`8cf30521384993fda7e696e0384b9e978c0d53ef9e09771e61f27e77ca712694`). The
following protected identities are also equal on parent and candidate:

| Protected object | Parent/candidate identity |
|---|---|
| 06k design blob | `04ebe53e1d88377a4e73c97cf71575c84d098113` |
| 06a lifecycle-plan blob | `052100192a1e488d1627d58592ecda0f86704dbd` |
| `.research-system/schemas` tree | `a1728d331f03aa8ecf09d4a3e739b55c18263a86` |
| `.research-system/contracts` tree | `27f1e12e8ecfb5c6fb33377981a96410555cbd56` |

The decisive negatives are not limited to schema rejection or a private mock:
the full Windows-gated unit file ran on this Windows host, the complete
WP6.1 authority integration file ran with real temporary stores and locks, and
the disposable cleanup probes traversed the public `CompositeWriterLock` API
with real OS directory anchors and an actual writer-lock conflict. Private
handle fakes are used only to deterministically induce `CloseHandle` failure.

**Disposition:** satisfied; no finding.

## 4. Validation evidence

All commands below ran from the exact candidate branch with repository coverage
and cache plugins disabled for read-only review runs.

| Validation | Result |
|---|---|
| `python -m pytest -q tests/research_system/unit/test_store.py -o "addopts=" -p no:cacheprovider -p no:cov` | `37 passed` in `99.39s` |
| `python -m pytest -q tests/research_system/integration/test_wp6_1_scope_task_authority.py -o "addopts=" -p no:cacheprovider -p no:cov` | `32 passed` in `43.53s` |
| `python -m pytest -q tests/research_system/unit/test_wp6_2_t2_runtime.py -k "authority_lock or requires_existing_control_root" -o "addopts=" -p no:cacheprovider -p no:cov` | `6 passed, 38 deselected` in `12.47s` |
| `python -m pytest -q tests/research_system/unit/test_wp6_2_t2_runtime.py -o "addopts=" -p no:cacheprovider -p no:cov` | `44 passed` in `55.98s` |
| `python -m ruff check research_system/store/lock.py tests/research_system/unit/test_store.py` | passed |
| `git diff --check 1946cd6ec59ae64861b902805934f5c3e37de8ce..HEAD` | passed |

The first combined three-file invocation was bounded at 120 seconds and timed
out without a test result while other worktree test processes were active. It
was decomposed into the bounded unit, integration, and T2 surfaces above; no
pass or failure was inferred from that timeout, and no full repository suite
was run.

## 5. Residual risk

No Critical, Major, or Minor finding remains for this exact cleanup correction.
The explicit residual boundary in 06k §10 remains: Python does not make the
ledger/object/receipt append handle-relative on Windows; an actor with
sufficient rights to retarget an unanchored ancestor after the final fence,
replace the writer-lock file itself, or mutate the running process remains
outside this narrow guarantee. Closing that stronger threat requires a separate
filesystem architecture decision and is not implied by this verdict.

The OS-level `CloseHandle` failures are deterministically injected in the
Windows controls; the real public probes verify the surrounding acquisition and
release path with actual anchors and locks. This is sufficient evidence for the
specified failure-ordering correction, not evidence that arbitrary kernel faults
are recoverable.

## 6. One next action

Record the owner decision for the exact candidate
`ea589d1a0b450828a7b6d013e2334dfccdca5ee5` as accepted for Slice L, then keep
any integration or merge action behind its separately authorized gate; this
review grants no merge or dispatch authority.

**Final exact-subject verdict:** `accept_exact_subject`.
