# WP6.1 authority linearization third-remediation exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 0 Critical, 2 Major, 0 Minor.

This is a fresh, independent, read-only review of the exact corrective
subject. It is not owner acceptance, PR or merge evidence, completion of the
remaining WP6.1 catalogue, or Gate 6 closure.

## Exact review identity

- Producer task: `019fbeb6-2147-72c2-9de0-1d49b55c0bf5`
- Independent reviewer task: `019fbec9-d11a-7b33-bf7b-e54d581794f5`
- Subject: `36b01dba4284d65cb7114b3849d683191942be67`
- Parent: `942c834af92b928e403459df2951999d97724f74`
- Tree: `9d768784cc9f3759a7c99330d792c315c3074970`
- Producer remote: `origin/codex/wp61-authority-linearization-r4`
- Exact corrective delta: 5 paths
  - `research_system/command/service.py`
  - `research_system/store/lock.py`
  - `tests/research_system/integration/test_wp6_1_scope_task_authority.py`
  - `tests/research_system/unit/test_store.py`
  - `tests/research_system/unit/test_wp6_2_t2_runtime.py`
- PR #205 remained open and unchanged at
  `bf2649c6a6fbc02bbd66e1b16403f564e1a22029` during review.

The reviewer confirmed the exact subject, parent, tree, five-path boundary,
clean tracked state, and equality of the producer branch and live remote. The
protected schema, contract, plan, authority, and active-binding paths were
unchanged.

## Executive disposition

The subject closes the prior extended-path double-lock, exceptional sibling
cleanup, and two T2 revocation-interleaving findings. It also preserves the
seven substantive PR #205 CodeRabbit closures already established in its
parent lineage.

Two material seams remain. The T2 service proves only the root advertised by
the resolver object, not the store actually read by the supplied resolver
callable. Separately, composite-lock grouping records directory identity and
then opens lock paths later; replacing a root directory in that interval can
move the protected append into an unlocked replacement.

The subject remains quarantined. PR #205 must not fast-forward to this SHA.
Any later correction is a new exact subject requiring fresh independent
review and current-head external review.

## M-01 - resolver reads are not bound to the frozen authority store

The submission path validates the resolver's advertised `control_root`, while
the T2 authority projection is still obtained by invoking an arbitrary
callable. Nothing proves that callable read the frozen physical store. A
resolver can advertise and lock root B, read a valid authority projection
from root A, and authorize `IssueCostGrant` into the domain store while A is
unlocked. The same seam applies to `AuthorizeProviderIssue`.

The next correction must bind authority resolution to the exact frozen
physical store used by the composite lock, or reject resolver forms for which
that binding cannot be proven. The control must demonstrate that advertising
one root while reading another fails closed without domain or authority
writes.

## M-02 - root replacement between grouping and lock acquisition escapes the lock

Composite-lock construction groups and stats existing roots before it later
opens each root's lock path. The directory identity captured during grouping
is not atomically bound to, or revalidated at, acquisition. Replacing the
domain root in that interval allows the command to acquire a lock associated
with the old identity and then append into the unlocked replacement root.

The next correction must bind lock-file creation and use to the captured
directory identity, and fail closed if the path resolves to a replacement at
any point before the protected operation begins. Deterministic controls must
cover replacement of each member of a multi-root lock set and prove no append
occurs in either the original or replacement store.

## Preserved closures and validation

The producer first demonstrated eight expected red controls plus one
platform-positive control, then reported all nine new controls green. The
combined three-file changed-behaviour selection completed as:

```text
93 passed in 37.48s
Focused Ruff and git diff --check: passed
Protected schema and contract bytes: unchanged
Local branch, tracking branch, and live remote: exact-subject equal
```

The fresh reviewer independently reported:

```text
Nine decisive controls: 9 passed in 7.10s
Exact changed-behaviour selection: 93 passed in 39.43s
Focused Ruff and git diff --check: passed
Tracked review state: clean
```

Independent attack also confirmed that late resolver-root mutation fails
closed, multi-error cleanup attempts every sibling release while preserving
the first error, `RecordProviderReceipt` remains domain-only, and both T2
issuance commands use the composite authority/domain lock. Those closures do
not establish either missing binding above.

CodeRabbit's completed review remains pinned to PR #205 head
`bf2649c6a6fbc02bbd66e1b16403f564e1a22029`. Its seven substantive findings
are corrected in this descendant lineage, but that does not supply external
review of this later exact subject and does not override the two major
findings.
