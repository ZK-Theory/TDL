# WP6.1 Slice L exact-subject review

Date: 2026-08-01

Reviewed candidate: 1946cd6ec59ae64861b902805934f5c3e37de8ce

Approved design base: acaaa7056c033cb1b716c6ff42f7235607fa3282

Expected parent: 177419bc8341ec76130a1cb207913a7710719dcb

Expected tree: ab178b1e10e9e913df5df5c0d34e3afc7bb5e681

Review branch: codex/review-wp61-composite-lock-1946cd6

Verdict: rework_required

Finding counts: Critical 0, Major 1, Minor 0

## Executive decision

The candidate implements the intended physical-identity and two-phase lock
mechanisms, and the decisive ordinary-Windows and alias controls pass. It is
not exact-subject acceptable because a reachable close-failure path leaks an
acquired native handle and masks the primary identity/fence error without
chaining it. This violates the design's L-8 complete-cleanup and first-error
preservation requirement. The required disposition is a narrow Slice L fix to
close-state handling and error chaining; no Slice R, T2 resolver/schema/event,
receipt, catalogue, provider, or design change is required.

## Exact subject and scope

The starting checkout was a detached exact candidate. After verifying the
detached commit and branch ref were equal, exactly one deterministic switch was
made to codex/review-wp61-composite-lock-1946cd6. The post-switch checkout was
complete and clean: 3,424 tracked paths were materialized, with no
skip-worktree entries, working-tree differences, or index differences. HEAD,
the review branch ref, the expected parent, expected tree, ancestry, and
origin/codex/wp61-composite-lock-lease-r7 all resolved to the required
candidate state.

The complete range from acaaa7056c033cb1b716c6ff42f7235607fa3282 through the
candidate contains only these paths:

    research_system/store/lock.py
    research_system/command/service.py
    tests/research_system/integration/test_wp6_1_scope_task_authority.py
    tests/research_system/unit/test_store.py

The range consists of the expected parent commit
177419bc8341ec76130a1cb207913a7710719dcb and the candidate remediation commit.
No other Slice L or downstream path was included.

## Finding

### M-1 — Major — anchor close failure is not retryable and masks the primary error

Evidence in the current candidate:

* In research_system/store/lock.py, _DirectoryAnchor.close marks
  self._closed = True before calling self._close_impl(self._handle). If the
  native close operation raises, the handle can remain live while the anchor
  permanently refuses every later close attempt.
* _windows_close_handle raises the raw close failure when CloseHandle returns
  false.
* _open_windows_anchor performs the probe/followed-handle cleanup in a
  finally block and raises first_close_error after the primary acquisition,
  identity, or final-path failure has already been raised. A raise from that
  finally block replaces the primary exception and does not preserve it as
  __cause__.
* The analogous POSIX failure cleanup directly calls os.close in an exception
  path; a close exception can likewise replace the original failure.
* The final-fence observer is closed in a finally block, and composite cleanup
  aggregates close failures but cannot retry an anchor whose closed flag was
  set before a failed close.

The precise failure is reachable in the current production path. A direct
Windows-path control allowed the no-follow probe to acquire successfully,
forced the followed identity read to raise OSError("identity unavailable"),
and made the native close operation raise RuntimeError("close failure").
The observed result was:

    RuntimeError close failure cause= None
    handle_states= [('probe', True), ('followed', False)]

Thus the original identity failure was masked, no cause was chained, and the
followed handle remained unclosed. This is not a claim inferred from a
synthetic assertion: it exercises the candidate's actual _open_windows_anchor
exception/finally and _DirectoryAnchor.close paths. The subject's existing
close-failure test also records that a permanently failing followed handle
remains not closed after all cleanup attempts, so the leak is currently
accepted by the test rather than closed or retried.

Impact: a failed acquisition or final fence can leave a root/runtime native
handle live. On Windows that can retain the directory and block subsequent
rename/delete operations or consume handle resources. Replacing the identity
or fence reason with an unrelated cleanup exception also removes the evidence
needed to diagnose the failed protection boundary. The ordinary successful
path remains fail-closed; this finding concerns deterministic failure handling
and cleanup integrity.

Disposition: fix now within Slice L. An anchor must remain retryable until its
close succeeds, while cleanup still attempts every sibling. Failure paths must
preserve the primary acquisition/fence exception and attach or chain cleanup
failures rather than allowing a finally block to replace the primary error.
Add a control covering primary identity/fence failure plus close failure, and a
control proving a failed close can be retried or otherwise reaches a closed
state. Preserve the existing first-cleanup-error ordering and sibling cleanup
attempts. Do not broaden this disposition into unsupported handle-relative
child creation or stale-lock ABA redesign.

## Mechanism decision audit

* L-1 existing directory root/runtime validation: pass. Missing,
  non-directory, unavailable, and unstable identities fail closed without
  creating lock state.
* L-2 physical identity: pass. Native Windows file identity is used, and
  normal, relative, case-swapped, extended-path, and junction aliases
  deduplicate to one member on this host.
* L-3 frozen identity claim: pass for the successful path. The no-follow
  probe remains live through the followed open, followed identity is checked,
  and the DELETE-access protected handle is reopened by the observed final
  path and rechecked.
* L-4 anchored lock location: pass. The lock location is tied to the
  physically observed directory and protected handle.
* L-5 complete member fence: pass for replacement controls before, between,
  and after acquisition phases; replacement is rejected before the protected
  callback.
* L-6 stable acquisition order: pass. Composite members are deduplicated and
  sorted by physical DirectoryIdentity rather than caller input order. Reverse
  input order produced the same acquisition/cleanup order in the direct
  control.
* L-7 no early protected work: pass. The service seam observed
  final_fence_start, final_fence_end, protected_body; the body did not run
  before the complete final fence and _submission_lock yields the acquired
  CompositeWriterLock.
* L-8 total cleanup and first-error preservation: fail, M-1. The normal
  composite cleanup attempts all locks and anchors and preserves its first
  recorded error, but an individual anchor close failure is made
  non-retryable and a primary Windows acquisition error can be masked.
* L-9 lease capability lifecycle: pass. Normal public construction and
  foreign tokens reject; retained, shallow-copied, and field-copied leases
  share invalidatable state; release and acquisition failure invalidate the
  state; retry creates distinct state; validation binds one active member and
  current lock-owned state.

The design's explicit residual boundary is preserved. This review does not
demand CPython handle-relative child creation, a stale-lock ABA redesign, or
arbitrary untrusted-process actor isolation.

## Validation evidence

All validation used C:/Users/steph/TDL/.venv/Scripts/python.exe directly, with
PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, pytest cache
disabled, and coverage disabled.

* The complete changed-behavior selection passed: 111 passed in 115.23s:
  tests/research_system/unit/test_store.py,
  tests/research_system/integration/test_wp6_1_scope_task_authority.py, and
  tests/research_system/unit/test_wp6_2_t2_runtime.py.
* Focused composite/anchor/WriterLock unit tests passed: 9 passed, 26
  deselected.
* Focused composite/service integration tests passed: 12 passed, 20
  deselected.
* Ruff check passed for all four changed paths; format check reported all four
  already formatted; git diff --check passed.
* The native host control ran on Windows 11 with Python 3.13.5. A held
  ordinary directory root and runtime both rejected rename and delete with
  WinError 32 under the DELETE-protected anchor.
* Alias controls covered normal, absolute, relative, case-swapped, extended,
  and junction paths and observed one physical member and one lock.
  Reparse/junction runtime aliases were rejected as required.
* Replacement controls covered pre-acquisition, between anchor and lock, and
  final-fence swaps, including both multi-root positions. Later-member
  conflict released earlier members/anchors.
* WriterLock raw bytes and AST for WriterLock, __init__, __enter__, and
  __exit__ were equal between the approved base and candidate. Its on-disk
  format and retry behavior therefore remain unchanged.
* Protected WP6.1 schema/contract identities, WP6.2 T2 contract identities,
  core schema tree, T2 schema tree, the 06k design, and the 06h/06i plans
  were byte-identical between the approved base and candidate. No Slice R or
  T2 authority behavior changed.

Producer tests are reproduction claims, not acceptance. The decision above
rests on current source inspection plus the native host controls and the
direct failure-path probe.

## Final decision

rework_required

Counts: Critical 0, Major 1, Minor 0.

Only this review record is authored by this review task. No production code,
test, design, PR, Jira, merge, CodeRabbit, or other external review state was
changed.
