# 06k: WP6.1 Authority Source and Composite Lock Identity Design

**Date:** 2026-08-01
**Status:** design decision only; no runtime implementation or activation
**Exact design base:** `36b01dba4284d65cb7114b3849d683191942be67`
**Rejected-subject review:**
`wp6-1-durable-authority-evidence-36b01db-review-2026-08-01.md`
(`rework_required`: M-01 and M-02)

## 1. Decision

Implement one narrow mechanism with two dependency-ordered slices:

1. `CompositeWriterLock` becomes a two-phase physical-directory lock. It
   freezes every supplied root identity, reopens and holds an operating-system
   directory anchor for every distinct root and its `runtime` directory,
   creates each writer lock through the anchor's canonical final path, and
   revalidates every supplied alias before it yields control to protected work.
2. `IssueCostGrant` and `AuthorizeProviderIssue` stop accepting an arbitrary
   authority callback. They require the service-owned concrete
   `ControlStoreT2AuthorityResolver`, bind it to the authority member of the
   acquired composite-lock lease, and verify a typed source identity for every
   returned record before any event or receipt write.

This is the minimal resolution because both findings share one missing object:
an acquired, physical-root capability. The lock slice creates that capability;
the resolver slice consumes it. A path string, `Path.resolve()`, a manifest,
and resolver-reported `control_root` remain descriptive evidence, not proof of
the store that was locked or read.

The implementation should use one new correction PR with two reviewable
commits, not two sequential PRs. The lock commit is reviewed at its exact SHA
before the resolver commit is added; the combined head then receives a fresh
independent exact-subject review. Nothing is merge-eligible after the first
commit because M-01 remains open. This avoids overlapping `service.py` and T2
test changes across dependent PRs while preserving a literal review boundary.
PR #205 remains frozen until a later, separately authorized integration action.

## 2. Governing obligations and disposition

| Source | Obligation carried into this design | Disposition |
|---|---|---|
| 36b01db review M-01 | Prove that T2 authority came from the exact frozen physical store, or reject the resolver | Sections 5-7; Slice R |
| 36b01db review M-02 | Bind lock creation/use to captured directory identity and reject replacement of every multi-root member before append | Sections 4 and 6; Slice L |
| 06a / P-020 | One writer and atomic no-side-effect rejection | Invariants L-1 through L-9 and A-1 through A-9 |
| 06h | T2 is a real producer path; raw schema provenance and runtime activation are separate work | Current call graph is traced, but schema identity and activation bytes are protected non-goals |
| 06i | Authority must be replay/store-derived; direct object access is not itself an authorization decision | The new resolver is a bounded read channel only; it creates no grants or authority |
| Handoff 32 accepted authority details | Grants are ledger/replay-governed, and direct `ObjectStore.write` grant fabrication is forbidden | No grant issue, activation, migration, record admission, or owner decision is introduced |

No new owner gate, command/event identity, provider capability, or catalogue row
is minted by this design.

## 3. Verified current call graph and smallest seam changes

The following is the source-observed graph at the exact design base, not an
expected interface:

```text
CommandService.submit
  service.py:304-305 -> submit_t2 for the closed T2 family
    t2.py:1019-1020 -> _T2Command, then service._submission_lock
      service.py:590-598 -> domain root plus advertised T2 authority root
      service.py:606-622 -> CompositeWriterLock construction/acquire/release
        lock.py:76-96 -> resolve, stat, group, choose path representatives
        lock.py:99-120 -> later acquisition of path-derived WriterLocks
    t2.py:1022-1065 -> active schema validation and replay
    t2.py:1183-1189 -> Issue/Authorize semantic checks
      t2.py:215-220 -> arbitrary service.t2_authority_resolver(kind, id, rev)
      t2.py:256-285 -> subject projection lookups
    t2.py:1194-1204 -> build events, append, then write accepted receipt
```

The misleading proof is split across two sites:

- `service.py:1025-1047` freezes only `getattr(resolver, "control_root")`
  and its stat identity.
- `t2.py:215-220` later invokes the resolver callable without passing the
  acquired root or checking where the returned bytes were read.

M-02 exists because `lock.py:76-92` records identity during construction while
`lock.py:99-103` opens `root/runtime/writer.lock` later. The two operations have
no acquired directory object in common.

The smallest production API changes are:

| Path | Exact change |
|---|---|
| `research_system/store/lock.py` | Add physical `DirectoryIdentity`, held `_DirectoryAnchor`, immutable `LockedRoot`, and a lease lookup on `CompositeWriterLock`; move authoritative grouping/acquisition validation into the two-phase protocol |
| `research_system/command/service.py` | Make `_submission_lock` yield the acquired composite lock; reject unprovable T2 resolvers for the two protected commands before lock or receipt I/O; bind the typed resolver to the authority `LockedRoot` |
| `research_system/store/objects.py` | Add `read_with_identity(...) -> StoredObjectRevision`; keep `read(...)` as a compatibility wrapper returning `.value` |
| `research_system/command/t2.py` | Replace protected-command `_lookup(service, ...)` calls with a bound reader and verify each typed result; do not change command/event/schema semantics |

No schema, reducer, projection, CLI, provider adapter, catalogue, policy, or
authority activation path changes.

## 4. Composite lock: types, invariants, and acquisition protocol

### 4.1 Types

`lock.py` owns these types. They are filesystem capabilities, not persisted
records:

```python
@dataclass(frozen=True, order=True)
class DirectoryIdentity:
    scheme: Literal["windows-file-id-v1", "posix-dev-inode-v1"]
    volume_or_device: int
    file_id: bytes

@dataclass(frozen=True)
class LockedRoot:
    identity: DirectoryIdentity
    final_path: Path
    runtime_identity: DirectoryIdentity
    runtime_final_path: Path
    aliases: tuple[Path, ...]
    _lease_token: object
```

`file_id` is the 128-bit Windows `FILE_ID_INFO.FileId` on Windows. POSIX
encodes `st_ino` into bytes and uses `st_dev` as `volume_or_device`.
`final_path` is an operation path and diagnostic; it is never the equality or
deduplication key. `_lease_token` is process-local and non-serializable.

`CompositeWriterLock.locked_root(path)` is valid only while the context is
entered. It resolves the original claim to exactly one `LockedRoot` or raises
`ConflictError`. Callers cannot construct a valid lease by copying fields.

### 4.2 Lock invariants

- **L-1 Existing-root requirement.** Every supplied root and its existing
  `runtime` child must be directories before construction completes. Absence,
  a non-directory, an unreadable identity, or a reparse `runtime` child fails
  closed. Acquisition creates neither a root nor a `runtime` directory.
- **L-2 Physical equality.** Deduplication and ordering use
  `DirectoryIdentity`, never path spelling. Normal, relative, case, extended
  `\\?\`, junction, and other followed reparse aliases of one physical root
  form one member. Different identities remain different members.
- **L-3 Frozen claim.** Construction captures one physical identity per
  supplied alias. Acquisition must reopen that alias to the same identity; a
  replacement never becomes the new accepted root for that lock attempt.
- **L-4 Anchored lock location.** The writer lock is created at
  `<runtime_anchor.final_path>/writer.lock`, where the held runtime anchor was
  opened from the held root's canonical final path. It is never opened from a
  caller-supplied alias.
- **L-5 Complete member fence.** After every member lock is acquired and before
  protected code is invoked, every original alias, root anchor, runtime
  anchor, and writer-lock ownership record is revalidated. One mismatch aborts
  the complete set.
- **L-6 Stable order.** Distinct members acquire in ascending
  `DirectoryIdentity`; reversing input order produces the same order.
- **L-7 No early work.** No replay, authority read, domain append, object write,
  projection write, or receipt write occurs before L-5 passes.
- **L-8 Total cleanup.** Any acquisition, fence, or protected-body failure
  remains the primary error. Cleanup still attempts every acquired writer-lock
  release in reverse order and then every runtime/root anchor close. After all
  attempts, the first cleanup error is chained as the cause of that primary
  error. With no primary error, normal release uses the same ordering, closes
  anchors last, and raises the first cleanup error only after all attempts.
- **L-9 Retry means reacquire.** A service retry after `ConflictError` creates a
  new `CompositeWriterLock`, recaptures/reopens every identity, and receives a
  new lease token. No claim or lease survives a failed attempt.

### 4.3 Acquisition, validation, append, release

1. **Freeze claims.** For each supplied spelling, open an ephemeral directory
   observer, capture physical identity and final path, require an ordinary
   existing `runtime` child, then close it. Retain every alias claim even after
   physical deduplication.
2. **Open held roots.** In identity order, reopen each representative root and
   compare its physical identity to the frozen claim. Keep the handle/file
   descriptor open. A mismatch is `ConflictError`.
3. **Open held runtime directories.** From the held root's final path, open the
   `runtime` child, require it not to be a reparse point, capture its identity,
   and keep it open. Recheck the root identity after this path-based open.
4. **Acquire writer locks.** Create `writer.lock` under each held runtime final
   path using existing exclusive-create and identity-record semantics. Preserve
   the current conflict retry policy in `CommandService`.
5. **Final fence.** Reopen every original alias and compare it with its frozen
   root identity; re-query every held root/runtime anchor; verify the lock path
   remains under the held runtime final path and has the expected ownership
   record. Perform this for every member, not only the authority root or last
   acquired root.
6. **Publish lease.** Mint one opaque lease token and expose immutable
   `LockedRoot` members. Entering the protected body starts only here.
7. **Protected work.** Bind the T2 authority reader, validate/replay, resolve
   authority, append the domain event batch, and persist the receipt in the
   existing semantic order.
8. **Release.** Release member locks in reverse order while directory anchors
   are still held. Close runtime anchors and then root anchors even if a sibling
   release raises. Invalidate the lease token before returning.

### 4.4 Windows feasibility

The directly inspected implementation runtime is CPython 3.13.5 on Windows 11.
On this runtime `os.supports_dir_fd` is empty, `os.O_DIRECTORY` and
`os.O_NOFOLLOW` are absent, and the nominal `dir_fd` parameters on `os.open`
and `os.stat` are not supported. `pathlib.Path.is_junction` and
`os.path.samefile` are available. Therefore this design does **not** claim that
Python can create `runtime/writer.lock` atomically relative to a Windows
directory handle.

Use a narrow private Windows backend in `lock.py`, implemented with `ctypes`
and the kernel32 functions present on this host:

- `CreateFileW` with `FILE_READ_ATTRIBUTES | SYNCHRONIZE`,
  `FILE_SHARE_READ | FILE_SHARE_WRITE` (deliberately excluding
  `FILE_SHARE_DELETE`), `OPEN_EXISTING`, and
  `FILE_FLAG_BACKUP_SEMANTICS`;
- `GetFileInformationByHandleEx(FileIdInfo)` for volume serial number and the
  128-bit file ID;
- `GetFinalPathNameByHandleW` for the canonical absolute operation path; and
- `CloseHandle` on every exit path.

Do not set `FILE_FLAG_OPEN_REPARSE_POINT` for the root observer: the identity
being locked is the followed physical directory, so a junction and its target
deduplicate. The separate final fence reopens every original spelling and
detects a junction retarget before protected work. The held target and runtime
handles exclude delete sharing, preventing ordinary rename/delete replacement
of those directories while acquired. If the platform cannot return a stable
file ID/final path or cannot obtain the non-delete-shared handle, acquisition
fails; it does not fall back to lexical identity or a stat-only Windows path.

On platforms with real directory descriptors, the private backend may use
`os.open(..., O_DIRECTORY)`/`fstat` and descriptor-relative child operations.
That portable branch does not weaken the Windows rule.

## 5. Root-bound T2 authority resolution

### 5.1 Ownership and types

The root-bound T2 resolver contract is closed over exactly
`IssueCostGrant` and `AuthorizeProviderIssue`. It is not the resolver contract
for the six Scope/Task lifecycle commands. `CreateScopeDefinition`,
`AmendScopeDefinition`, `SupersedeScopeDefinition`, `CreateTask`, `AmendTask`,
and `SupersedeTask` continue to use the concrete
`LedgerAuthorityGrantResolver.resolve_command` path and its replay-derived
scoped-grant evidence. The two resolver families are not substitutes and must
not share an A-1/A-2 implementation claim.

Define the static interface and one trusted implementation in `t2.py` (a
separate module is unnecessary for this bounded seam):

```python
class RootBoundT2AuthorityResolver(Protocol):
    @property
    def control_root(self) -> Path: ...

    @property
    def frozen_root_identity(self) -> DirectoryIdentity: ...

    def bind(self, locked_root: LockedRoot) -> BoundT2AuthorityReader: ...

@final
class ControlStoreT2AuthorityResolver:
    # service-owned concrete implementation
    ...

@dataclass(frozen=True)
class T2AuthoritySourceIdentity:
    directory_identity: DirectoryIdentity
    final_root: Path
    object_kind: str
    object_id: str
    object_revision: int
    relative_path: PurePath
    object_bytes_sha256: str
    _lease_token: object

@dataclass(frozen=True)
class ResolvedT2AuthorityRecord:
    value: Mapping[str, Any]
    source: T2AuthoritySourceIdentity
```

The protocol provides type checking. It is not the trust decision. For the two
protected commands, `CommandService` requires
`type(resolver) is ControlStoreT2AuthorityResolver`; structural conformance,
subclasses, arbitrary callables, and objects that merely expose
`control_root` are unprovable and fail before lock or receipt I/O.

The concrete resolver freezes its root with the same identity observer used by
`CompositeWriterLock`. `bind()` accepts only the live `LockedRoot` selected by
the service, requires exact frozen/acquired physical identity equality, and
constructs an `ObjectStore` from `locked_root.final_path`, not from its own
path property. The bound reader cannot change roots and expires with the lease.

`ObjectStore.read_with_identity()` performs the existing exact-one-file,
canonical-JSON, and filename-hash checks and returns the actual relative path
and canonical byte SHA alongside the value. Existing `read()` delegates to it
and returns only `.value`, preserving all existing callers.

### 5.2 Service verification

For every protected-command lookup, the service—not the record and not a
resolver-supplied manifest—checks all of the following before using `value`:

1. the result's exact runtime type is `ResolvedT2AuthorityRecord`;
2. `source._lease_token` is the live composite-lock token by object identity;
3. `source.directory_identity` equals the acquired authority member identity
   and the resolver's frozen identity;
4. `source.final_root` equals the acquired member final path;
5. kind, ID, and revision equal the requested lookup exactly;
6. `relative_path` is the canonical
   `objects/<kind>/<id>/<revision>-<sha>.json` path, contains no absolute or
   parent component, and resolves below the acquired final root;
7. `sha256(canonical_bytes(value))` equals `object_bytes_sha256` and the
   filename digest; and
8. the existing T2 record-body triple and current/revoked/effectivity checks
   still pass.

Checks 2-7 establish source; check 8 establishes existing command semantics.
Self-reported `control_root`, store metadata, an inner `content_hash`, or a
matching record body cannot substitute for the acquired-root and byte checks.

Any failure of checks 1-7 is an integrity failure, not a stable business
rejection: raise before append and before writing a rejected receipt. A normal,
properly sourced record that fails an existing semantic rule retains the
existing stable rejection behavior.

### 5.3 Authority invariants

- **A-1 Protected resolver type.** `IssueCostGrant` and
  `AuthorizeProviderIssue` require the exact concrete root-bound resolver.
- **A-2 Same acquired source.** Every authority/subject lookup for one command
  uses one reader bound to the authority member of that command's live
  composite lease.
- **A-3 No alternate-store fallback.** A missing record in locked root B is
  missing even if an identical or usable record exists in root A.
- **A-4 Complete source identity.** Every returned record carries and passes
  the eight checks in section 5.2. Source identity is per record, not one
  resolver-level assertion.
- **A-5 One linearized interval.** Authority reads occur after the complete
  composite final fence and before domain append while both writer locks and
  directory anchors remain held.
- **A-6 Same-root correctness.** If authority and domain spellings identify one
  physical directory, the composite set contains one member and the resolver
  binds to that member; source checks are not skipped.
- **A-7 Fail-closed effects.** Unprovable resolver, root mismatch,
  replacement, stale lease, source mismatch, or source-byte mismatch produces
  no authority write, domain event/object/projection mutation, or receipt.
- **A-8 No authority creation.** The resolver is read-only. It cannot issue,
  activate, revoke, migrate, or admit a grant or assurance record.
- **A-9 Retry revalidation.** A stored-receipt or ledger-reconstructed retry
  reacquires the composite lease, rebinds a new `LockedRoot`, and reruns the
  current `_issue_semantics` or `_authorize_semantics` lookup path before any
  return. Revocation or record rekeying denies the retry without rewriting the
  exact accepted receipt or its canonical ledger proof.

## 6. End-to-end protected command sequence

For `IssueCostGrant` and `AuthorizeProviderIssue` the exact order is:

1. Construct the T2 command and determine that it is authority-coordinated.
2. Require the exact concrete resolver. Reject an arbitrary callable before
   acquiring a lock or touching either store.
3. Build `CompositeWriterLock(domain_root, resolver.control_root)` from frozen
   claims. Acquire and final-fence every distinct member as section 4 specifies.
4. Obtain `authority_locked_root = lock.locked_root(resolver.control_root)` and
   call `resolver.bind(authority_locked_root)`. Verify the frozen identity and
   live token.
5. Run active command-schema validation and replay, and locate any stored
   receipt or ledger-reconstructed retry candidate, but do not return it yet.
6. Pass the newly bound reader through `_issue_semantics`,
   `_authorize_semantics`, `_subject_gate`, and `_lookup` for both first
   execution and retry. A stateful retry derives the pre-command T2 projection
   from the canonical batch it is reconciling, while every authority/source
   lookup is current under the new lease.
7. If a retry passes current semantics, reconcile and return the exact stored
   receipt identity (or its existing duplicate proof) without replacing it. If
   current revocation or rekeying denies the retry, return the current denial
   without persisting over the accepted receipt.
8. For a first execution, build the unchanged event set and call
   `EventLedger.append` once. There is
   still no provider invocation.
9. Build and write the existing Receipt 2.0 accepted outcome.
10. Invalidate the bound reader, release writer locks in reverse physical order,
   and close anchors last.

`RecordProviderReceipt` remains outside the composite authority lock, as in the
reviewed subject. This design does not broaden its runtime authority or provider
behavior. It may use the concrete resolver for ordinary record provenance, but
the lease-bound requirement and new composite-root participation apply only to
the two named issuance commands. A later attempt to extend the guarantee to
receipt reconciliation requires its own authority/atomicity decision and tests.

## 7. Backward compatibility and fail-closed rules

- `WriterLock(path, identity)` and its on-disk JSON ownership record remain
  unchanged.
- `with CompositeWriterLock(...) as lock:` remains valid. `lock.paths` becomes
  authoritative only after successful entry; production has no pre-entry
  consumer. Tests that inspected provisional paths before entry must instead
  inspect acquired `LockedRoot.runtime_final_path` values.
- Existing same-root behavior remains one lock. Input-order independence and
  conflict retry remain.
- `ObjectStore.read()` retains its return type and errors.
- Non-T2 services may continue to construct `CommandService` with no T2
  resolver.
- A legacy callable may remain available only to the existing
  `RecordProviderReceipt` path during migration. If either protected command
  reaches `_submission_lock` with that callable, it raises immediately; it is
  never invoked and its advertised metadata is never used.
- The T2 test harness must seed canonical records into a real temporary
  `ObjectStore` and use `ControlStoreT2AuthorityResolver`. In-memory `Records`
  callbacks are no longer admissible positive evidence for the protected
  commands.
- Existing/absent is literal: a root or `runtime` directory that appears after
  a failed claim is not adopted on retry unless the service constructs a new
  resolver whose frozen identity intentionally names it.
- Replacement/source-integrity failures write no rejection receipt. Ordinary
  current-authority denials from a correctly bound source preserve current
  stable reason codes and receipt behavior.

## 8. Deterministic test matrix

Every failure row snapshots each physical store, root, and `runtime` directory
that exists before the action and asserts: no new ledger batch, object revision,
projection file, accepted or rejected receipt, and no authority-store mutation
unless the row explicitly tests a normal semantic rejection. L-N1 and L-N2
record absent roots or `runtime` directories as absence facts and assert those
paths remain absent; their snapshot helpers must not create the paths they are
meant to test.

### 8.1 Lock primitive

| ID | Case | Expected result |
|---|---|---|
| L-P1 | One existing root and ordinary `runtime` directory | One member; lock under anchored runtime; clean release |
| L-P2 | Two distinct existing roots, both input orders | Two members in identical physical-ID order |
| L-P3 | Normal, absolute, relative, case, and `\\?\` aliases on Windows | One physical member and one writer lock |
| L-P4 | Junction/reparse alias plus target, when fixture creation is permitted | One physical member; every alias passes final fence |
| L-P5 | Domain and authority are the same physical root | One lock, two successful lease lookups |
| L-N1 | Root absent at construction, parameterized over each multi-root position | Fail; do not create root, runtime, or lock |
| L-N2 | `runtime` absent, non-directory, or reparse target | Fail before writer-lock creation |
| L-N3 | Replace member `i` after frozen claim but before held-root open, for every `i` | Identity mismatch; no lock remains in old or replacement root |
| L-N4 | Replace/retarget member `i` after its anchor opens but before its lock opens | Windows ordinary replacement is denied by the held handle; a reparse retarget is caught by the final fence |
| L-N5 | Replace/retarget member `i` after its writer lock opens but before final fence | Complete acquisition aborts; all sibling locks are removed; no protected callback fires |
| L-N6 | Lock conflict on member 2 after member 1 acquired | Member 1 lock released and every anchor closed |
| L-N7 | Cleanup of member 2 raises while member 1 also needs release | Both releases attempted; first cleanup error raised from acquisition error |
| L-N8 | Anchor identity/final-path API unavailable or unstable | Windows fails closed; no lexical/stat fallback |

Replacement timing is deterministic. Tests wrap the private directory-anchor
factory and existing `lock_factory`, or monkeypatch the private final-fence
helper, to move `old-root` to `old-root.saved` and create/retarget the named
replacement at one exact phase. No public production callback is added. Each
service-level row runs the real `CommandService.submit` and proves the domain
append callback was never reached for both root positions.

### 8.2 Resolver/source binding

| ID | Case | Expected result |
|---|---|---|
| A-P1 | Exact resolver, distinct domain B and authority A, valid records in A | Issue accepted; all sources name A's lease and physical ID |
| A-P2 | Exact resolver, same physical root through different aliases | Issue/authorize accepted with one composite member |
| A-P3 | Issue then authorize with a concurrent cooperative authority revoker | Existing domain-wins and revocation-wins linearization controls remain green |
| A-P4 | Properly sourced but revoked/expired/wrong-scope record | Existing stable rejection; no event append |
| A-N1 | Callable advertises B but returns valid records read from A | Fail before callable invocation, locks, receipt, or append for both protected commands |
| A-N2 | Resolver froze A; acquired authority member is B | Bind fails on physical identity before lookup |
| A-N3 | A lacks a requested record while an identical valid record exists in B | No fallback; normal missing/invalid semantic outcome from A only |
| A-N4 | Forged lease token or stale reader reused after release | Integrity failure; no writes |
| A-N5 | Right record body with wrong source root identity/final root | Integrity failure; no writes |
| A-N6 | Right root with wrong relative path, requested kind/ID/revision, filename digest, or canonical byte digest | Each mutation fails independently before semantic use |
| A-N7 | Replace authority or domain root at each L-N3/L-N5 phase | Fail before resolver call/append; neither old nor replacement store changes |
| A-N8 | Resolver root absent or loses stable Windows identity | Construction/acquisition fails closed |
| A-N9 | `RecordProviderReceipt` regression | Existing domain-only lock set and no-provider-invocation canary remain unchanged |
| A-N10 | Exact stored or ledger-reconstructed retry after authority revocation or requested-record rekey | Reacquire and rebind, rerun current lookup semantics, deny without changing the accepted receipt or ledger proof |

The malicious A-N1 resolver has an invocation counter and reads A only if
called. The expected counter is zero. A path or metadata equality assertion
without that negative is insufficient.

## 9. Dependency-ordered implementation slices

### Slice L: physical composite-lock lease

**Purpose:** close M-02 and provide the only source capability Slice R may
consume.

**Allowed production paths:**

```text
research_system/store/lock.py
research_system/command/service.py
```

In `service.py`, this slice may only make `_submission_lock` yield the acquired
lock/lease and preserve retry/release behavior. It must not alter authority
resolution, T2 semantics, schemas, events, receipts, reducers, or projections.

**Allowed test paths:**

```text
tests/research_system/unit/test_store.py
tests/research_system/integration/test_wp6_1_scope_task_authority.py
tests/research_system/unit/test_wp6_2_t2_runtime.py
```

**Validation:**

```powershell
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q tests/research_system/unit/test_store.py tests/research_system/integration/test_wp6_1_scope_task_authority.py tests/research_system/unit/test_wp6_2_t2_runtime.py -o "addopts=" -p no:cacheprovider -p no:cov
C:\Users\steph\TDL\.venv\Scripts\python.exe -m ruff check research_system/store/lock.py research_system/command/service.py tests/research_system/unit/test_store.py tests/research_system/integration/test_wp6_1_scope_task_authority.py tests/research_system/unit/test_wp6_2_t2_runtime.py
git diff --check
```

**Fresh-review boundary:** commit Slice L alone. An independent reviewer pins
SHA/parent/tree, runs L-P1 through L-N8 including every member replacement, and
returns one exact verdict. Acceptance of that primitive is evidence for Slice
R; it is not acceptance or merge authority for the still-incomplete correction.

### Slice R: locked-source T2 resolver

**Dependency:** exact accepted Slice L SHA; do not reimplement or weaken its
identity/lease contract.

**Allowed production paths:**

```text
research_system/command/service.py
research_system/command/t2.py
research_system/store/objects.py
```

**Allowed test paths:**

```text
tests/research_system/unit/test_store.py
tests/research_system/unit/test_wp6_2_t2_runtime.py
tests/research_system/integration/test_wp6_1_scope_task_authority.py
```

No production CLI/factory call site currently passes
`t2_authority_resolver`; the source inventory at the design base finds that
argument only in the T2 unit harness. A newly discovered caller is a stop: add
its exact symbol and compatibility disposition to this design before editing
it.

**Validation:**

```powershell
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q tests/research_system/unit/test_store.py tests/research_system/unit/test_wp6_2_t2_runtime.py tests/research_system/integration/test_wp6_1_scope_task_authority.py -o "addopts=" -p no:cacheprovider -p no:cov
C:\Users\steph\TDL\.venv\Scripts\python.exe -m ruff check research_system/command/service.py research_system/command/t2.py research_system/store/objects.py tests/research_system/unit/test_store.py tests/research_system/unit/test_wp6_2_t2_runtime.py tests/research_system/integration/test_wp6_1_scope_task_authority.py
git diff --check
```

Run the three-file changed-behavior set once at final combined head, not after
every finding. Expand to the full `tests/research_system` tree only if the
targeted set exposes a shared API regression, a new production caller is found,
or the final integration gate explicitly requires it.

**Fresh-review boundary:** the final independent reviewer verifies both exact
Major findings against the combined exact subject, reruns A-P1 through A-N9
and the lock replacement controls, and confirms that protected schema,
contract, plan, authority-model, provider, and catalogue paths are unchanged.
Passing tests do not constitute owner acceptance or PR integration authority.

## 10. Non-goals and residual threat boundary

### Non-goals

- No provider invocation, credential access, live research, transport change,
  W11 activation, dossier admission, or catalogue expansion.
- No new command/event/schema identity; no accepted schema byte change; no
  runtime activation or historical migration.
- No grant issue/activation/revocation design, assurance-record creation,
  owner decision, or direct authority-object write.
- No change to artefact consumer policy, release publication, evaluation
  corpus, CLI, Jira, PR #205, or CodeRabbit state.
- No universal path sandbox, filesystem transaction layer, stale-lock
  reclamation framework, or defence against arbitrary code already executing
  inside the trusted process.

### Explicit residual boundary

The guarantee is against root substitution from claim capture through the
final fence and against unprovable authority sources for the two named
commands. It assumes the operating-system kernel and returned local-volume file
IDs are sound, and that cooperating writers honor `writer.lock`.

Windows root/runtime handles prevent ordinary deletion or rename of the
anchored target directories while held, and the authority reader uses the
anchor's canonical final path. Python on this host cannot perform the domain
ledger append handle-relative. An actor with sufficient filesystem rights that
retargets an unanchored ancestor/reparse spelling after the final fence but
during the protected body, deletes/replaces the writer-lock file itself, or
mutates the running process is outside this correction. Closing that stronger
threat would require rebinding every ledger/object/receipt I/O operation to
native handles or changing store layout and access control; that is a separate
filesystem architecture, not a minimal resolution of M-01/M-02.

If a configured filesystem cannot supply stable physical IDs or Windows
non-delete-shared directory handles, the supported behavior is fail closed.
The implementation must not silently downgrade to `Path.resolve()`, path
case-folding, manifest equality, or resolver self-attestation.
