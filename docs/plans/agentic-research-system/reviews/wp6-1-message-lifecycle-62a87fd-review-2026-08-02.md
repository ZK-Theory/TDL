# WP6.1 Message lifecycle exact-subject review - candidate `62a87fd`

Date: 2026-08-03
Reviewer role: fresh independent exact-subject reviewer
Verdict: **`rework_required`**

## Exact subject and review boundary

- Review worktree: `C:\Users\steph\.codex\worktrees\62ec\TDL`
- Review branch: `codex/wp6-1-message-c01-review-62a87fd-20260802`
- Exact candidate: `62a87fd46642ac6c9c176058949bd2d43075a326`
- Sole parent: `9deda084366cc05f473bfe12cd4000fbf6953424`
- Candidate tree: `4e7bb6308b3286c671181224ff1865cb63aae9a3`
- Candidate subject: `[PIPELINE] P00: reject orphan Message receipt before append`
- Underlying implementation base: `7275184e41fbfb149d2c91462ac872012d29a961`
- Rejected predecessor: `b4000015c65c132da272f0ca6122060a17d8c0af`, tree `21c5169ff964542a86fefc3c1bd34b9362be6d5a`
- Immutable first review: `638a12b1ffb9893fac0fd2f996995c788df95693`
- Design authority: `0e842969c770811edf5c81dcd7e4f7a647e050ad`, blob `80182047b5ad42ad8427db128e1b66b784c93177`
- First-review record blob: `4b89a507ee6ac1699600b38458f7614b386243b6`
- Parent rereview record blob: `29763b912b391163690b8bc1f300e994fb9a6f80`

The candidate has exactly these two new-subject changed paths:

1. `research_system/command/service.py`
2. `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

The worktree started detached. Detached `HEAD` and the pre-created review ref both
resolved to the exact candidate, so one deterministic switch attached the named
review branch. The candidate has the stated sole parent, tree, subject, and changed
paths. No fallback branch, branch creation, rename, commit switch, merge, rebase,
cherry-pick, integration, or remediation was performed.

Repowise bootstrap was started with the required non-interactive flags. Its wrapper
timed out while the initializer continued, the identified initializer then completed,
and `repowise status` exited zero with the indexed repository at `HEAD 62a87fd`.
No tracked setup file was rewritten. Ignored `.repowise` cache files remain setup
state and were not staged or used as semantic evidence.

## Executive decision

The candidate closes the exact C-01 orphan-receipt defect that caused rejection of
`b400001`: after fresh Message authority resolution and after canonical event-backed
missing-index recovery has had an opportunity to return or reconstruct, it rejects a
stored Message receipt that has no canonical event. The guard executes before version
observation, Message preparation, event construction, allocation, append, receipt
publication, or idempotency-index publication. The committed public-seam negative is
green, the same exact test is semantically red against `b400001`, and a stronger
independent probe with authority pre-activated proved both the domain and authority
stores unchanged.

The exact subject nevertheless has one unresolved Major parent-baseline defect. When
a canonical Message event and receipt exist, the scoped index is missing, and a retry
changes only `command_id`, event-backed recovery returns the original accepted receipt
and reconstructs the index instead of raising the required Message idempotency
conflict. This violates the already asserted changed-command-ID contract and mutates
the durable index for a submission that should be rejected. The behavior reproduces
identically at `b400001`; it was not introduced by the candidate's five-line service
change, but it remains reachable at the reviewed exact subject. An unresolved Major
finding requires `rework_required`.

## Severity-ranked finding

### PB-M-01 - Major - Event-backed missing-index recovery bypasses the Message changed-command-ID conflict

**Required contract.** Every Message row's changed command-ID/same-idempotency-key
case must conflict without mutation. The executable common-axis matrix asserts this
at `tests/research_system/integration/test_wp6_1_message_lifecycle.py:142-152`.
Valid missing-index recovery must reconstruct only an exact retry, as exercised at
`test_wp6_1_message_lifecycle.py:1716-1738`.

**Exact source evidence.** With the scoped index absent, `_load_lifecycle_authority_receipt`
returns `None` at `research_system/command/service.py:1459-1476`. Submit then calls
`_matching_committed` at `service.py:493-498`. Its `same_submission` predicate checks
payload hash, stream, and version but not command ID (`service.py:2479-2507`), so it
returns the original committed batch. Submit immediately returns through
`write_receipt(self._return_or_reconstruct(existing))` at `service.py:499-500`.
The Message retry-identity check at `service.py:1484` is only reached when a scoped
index was loaded, and the candidate's new orphan-receipt guard at `service.py:501-505`
is after the early recovery return. The reconstructed scoped index is therefore bound
to the original accepted receipt before any changed-command-ID conflict is raised.

**Independent public-seam counterexample at the candidate.** A disposable control
plane used the plain public `CommandService.submit` seam, a real pre-activated current
Message grant, the valid immutable adapter snapshot, and an accepted `PublishMessage`.
After deleting only its scoped index, the retry retained actor, grant, command type,
idempotency key, payload, target, schema, and expected version but changed the command
ID. Candidate `62a87fd` returned:

```text
Receipt: accepted
returned command_id: cmd_01978abc-7101-7000-8000-000000000618
returned_original: True
event_count: 1
index_reconstructed: 1
state_equal: False
```

The submitted changed command ID was
`cmd_01978abc-7101-7000-8000-000000000619`. No second event was appended, but the
scoped-index set changed and the changed-identity submission received accepted
evidence instead of a typed conflict.

**Parent-baseline classification.** The same probe at exact `b400001`, service blob
`5d1cad1b0e5e68b60e9806757ff7cc9f1f6e1245`, returned the original accepted receipt,
kept one event, reconstructed one index, and reported unequal before/after state.
The candidate changes only the later orphan-receipt guard, so PB-M-01 is a
parent-baseline defect still present at this candidate, not a candidate-introduced
regression or setup residue.

**Impact.** Message recovery does not preserve the distinguishing command-ID/key
contract across a legitimate event-backed missing-index state. A different command
identity can receive the original acceptance and cause durable index publication.
This is an exactly-once and evidence-identity defect on the required recovery seam.

No remediation was attempted.

## Decisive C-01 review

### Exact ordering and classification

At the candidate, the public submit order is:

1. exact active command-schema validation and command construction
   (`service.py:389-437`);
2. fresh lifecycle authority resolution, with denial returning before recovery
   (`service.py:448-478`);
3. scoped-index load and, when present, canonical replay/history reconciliation
   (`service.py:479-485`, `782-997`, `1459-1485`);
4. event-backed committed-command matching and receipt/index reconstruction
   (`service.py:493-500`, `2479-2531`);
5. the new Message-only stored-receipt guard
   (`service.py:501-505`); then
6. only if no conflict, observed version, preparation, event construction, append,
   and accepted receipt/index publication (`service.py:506-671`).

The guard raises the stable typed domain error
`ConflictError("receipt already exists: <command_id>")`. It is Message-only, so the
added predicate and receipt load are short-circuited for non-Message commands.

### Committed negative and no-mutation surface

`test_orphan_message_receipt_is_rejected_before_append_without_mutation` at
`tests/research_system/integration/test_wp6_1_message_lifecycle.py:1742-1798` uses
the public `harness.service.submit(command)` seam. It creates an accepted receipt for
the exact `PublishMessage` command, no scoped index, and no Message event. It anchors
the complete ConflictError text and verifies unchanged:

- event count and ledger tail;
- ledger batches and stream versions;
- complete receipt bytes/set and accepted-receipt set;
- complete idempotency-index bytes/set;
- committed command-ID and command-scope maps;
- replay/control-plane history; and
- external projection state.

The harness carries a valid typed immutable adapter snapshot and resolves a real
Message grant through the sibling authority ledger. To remove any ambiguity from the
test fixture's automatic grant setup, an independent public-seam probe pre-activated
the exact Message grant through the real authority command service, switched to the
plain `CommandService`, wrote the orphan receipt, and captured both stores before
submit. The candidate raised the exact ConflictError with zero domain events; domain
state, all domain receipt/index bytes, authority ledger snapshot (three existing
authority events), and authority receipt bytes were identical before and after.

### Exact parent-red evidence

A history-bearing no-hardlink clone was configured with `core.autocrlf=false` and
`core.longpaths=true`, checked out detached at exact predecessor `b400001`, tree
`21c5169ff964542a86fefc3c1bd34b9362be6d5a`, and kept the predecessor service blob
`5d1cad1b0e5e68b60e9806757ff7cc9f1f6e1245`. Only the candidate test patch was
applied; its resulting test blob was exactly candidate blob
`f2444eaa3f51c7a55c81672e9b9f2433a7762e4c`.

The exact new node raised the expected ConflictError but then failed at
`test_wp6_1_message_lifecycle.py:1787`: the Message event count changed from zero to
one. Result: `1 failed in 11.98s`, exit 1. This establishes a semantic red against
the rejected predecessor rather than a missing fixture or schema-preempted negative.

The explicitly named disposable clone remains at
`C:\Users\steph\AppData\Local\Temp\tdl-message-c01-parent-red-62a87fd-20260803-001`.
Cleanup was blocked by execution policy and, per owner direction, was not retried.
It is outside the review worktree and contains no candidate production edit.

## Mandatory prior-finding dispositions

### C-01 - closed for the exact orphan-receipt/no-event case

Fresh authority, valid and foreign scoped indexes, canonical history, project, and
unsupported-major controls remain in place. The new guard closes the exact accepted
receipt plus absent index plus absent canonical event mutation demonstrated by the
parent rereview. PB-M-01 is a separate event-backed changed-command-ID recovery
interaction and prevents overall acceptance.

### C-02 - remains closed

The Message-specific exact-schema guard remains at
`research_system/command/lifecycle.py:62-107`; replay consumes it before projection
publication. The recognized Message event under the generic schema negative remains
green. Generic Task compatibility behavior is outside the candidate delta.

### M-01 - shared non-Message retry regression remains closed

The shared `_return_scoped_receipt_or_raise` behavior at `service.py:1502-1513` is
unchanged. The new guard is Message-only. All four required unchanged non-Message
retry nodes pass. PB-M-01 concerns a Message-only event-backed missing-index early
return and does not reopen the prior shared-helper regression.

### M-02 - remains closed

All four Message event constructors still deep-copy caller payloads at
`service.py:2596-2607`. The caller-mutation/deliverability node remains green.

### M-03 - no candidate regression to the settled 13-row common-axis matrix

The catalogue and `MESSAGE_ROWS` each contain the same 13 unique exact row IDs. Pytest
collects exactly 13 common-axis nodes, one per row. Each node executes current
authority, exact retry, changed command-ID and key conflicts, an authority rejection,
row-specific decisive rejection, no-mutation checks, replay, projection, and its
applicable race or explicit publication N/A. The candidate adds the C-01 test without
changing the matrix body.

The matrix's per-row authority mutation is wrong actor. Missing authority is exercised
for each of the four Message commands, while wrong command/subject kind, wrong subject,
not-yet-effective, expired, prohibited actor, and wrong project are representative
shared-resolver tests. This is the parent review's settled coverage granularity and is
not changed by the candidate; it does not override PB-M-01's concrete cross-axis
failure.

### m-01 - remains closed

`control_plane(..., auto_authority=False, message_adapter_registry=...)` still passes
the explicit snapshot to the plain service at `tests/research_system/factories.py:462-542`.
The manually activated plain-control-plane adapter path remains green.

## Full frozen-pilot contract audit

### Catalogue, bindings, schemas, and payloads

- Exact catalogue blob `1adc66921ee9c90d8786ff173748150922f1035e` contains 13 unique
  `message.*` rows: ten publication discriminants plus delivery,
  acknowledgement, and delivery failure.
- The runtime registry contains exactly four Message command bindings and four
  producer-specific Message event bindings, all at `1.0.0`, at
  `research_system/schema_registry.py:140-183`.
- Exact Git-object parsing of both protected PublishMessage and MessagePublished
  schemas found one ten-branch discriminated union in each: assignment,
  acknowledgement, progress, input_request, escalation, report, review_request,
  review_response, decision_request, and handoff. Every branch has its literal
  discriminant, `additionalProperties: false`, and all declared properties required.
- The ten positive discriminant cases and missing/unsupported/aliased/inconsistent
  negatives remain green in the complete module.

### Authority, lifecycle, content, adapters, replay, and mutation controls

- Exact command schema identity, current scoped authority, actor, project, Message
  subject, target stream, payload hash, expected version, and canonical grant history
  are resolved before Message mutation.
- Publication binds sender, recipient set, row payload, reply/correlation linkage,
  thread, typed subject, and immutable content. Self-link and acknowledgement
  correlation negatives remain decisive.
- Delivery and failure require the service-local immutable adapter snapshot, current
  status/effectivity, project, capability, allowed actor, and non-empty evidence.
  No provider or adapter action is performed.
- Delivery binds canonical publication content and exact recipients. Acknowledgement
  additionally requires delivered state, a published recipient actor, and
  `source_position == MessagePublished.global_position`.
- `reduce_message` permits only absent-to-published-to-delivered-to-acknowledged or
  absent-to-published-to-delivery_failed. Delivery/failure and acknowledgement races
  retain one winner and a stable unchanged loser.
- Replay validates exact command/event provenance, schema identities, project, actor,
  content/linkage, source position, hash chain, transaction order, stream version, and
  legal lifecycle order before projection publication. Unknown major, recognized
  Message under generic schema, broken producer provenance, actor/lineage divergence,
  missing reducer route, and divergent terminal history fail closed.
- Rejected-path snapshots cover ledger tail/batches/versions, accepted receipts,
  idempotency indexes, committed command/scope maps, replay history, and projection.
  The exact C-01 orphan case is now unchanged. PB-M-01 is the demonstrated exception
  to the required changed-command-ID conflict/no-mutation interaction.

### Path envelope and non-goals

The linear implementation-base-to-candidate range changes exactly ten paths: the two
immutable review records plus these eight implementation/test paths:

1. `research_system/authority.py`
2. `research_system/command/lifecycle.py`
3. `research_system/command/reducers.py`
4. `research_system/command/service.py`
5. `research_system/projection/replay.py`
6. `research_system/schema_registry.py`
7. `tests/research_system/factories.py`
8. `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

Ten is below the 14-path ceiling and all paths remain inside the implementation/review
envelope frozen by the two immutable review records. The range adds no real provider
or adapter action, persistence framework, second stream, `store/ledger.py` edit,
ClaimDispatch behavior, KAN-67, WP6.4, W11, schema-byte write, catalogue change, or
protected identity change.

## Protected identities

The protected schema registries independently resolve from the candidate Git object:

| Registry | Exact tree | Files |
|---|---|---:|
| Commands | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | 87 |
| Events | `154ffc4bdde82fe903718734687e7a62797b1f69` | 86 |

SHA-256 over the exact candidate Git blob bytes produced:

| Active identity (`1.0.0`) | Bytes | Raw SHA-256 |
|---|---:|---|
| `PublishMessage` | 91,363 | `14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c` |
| `MessagePublished` | 91,354 | `f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f` |
| `RecordMessageDelivery` | 7,566 | `9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828` |
| `MessageDelivered` | 10,483 | `7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388` |
| `AcknowledgeMessage` | 7,280 | `3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d` |
| `MessageAcknowledged` | 10,221 | `576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be` |
| `RecordMessageDeliveryFailure` | 7,303 | `afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89` |
| `MessageDeliveryFailed` | 10,212 | `0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5` |

All values match the protected identities. Candidate-to-parent has no schema path.

## Independent validation evidence

All Python commands used `C:\Users\steph\TDL\.venv\Scripts\python.exe` directly with
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and
`PYTEST_ADDOPTS=''`. Pytest additionally used `-o "addopts=" -p no:cacheprovider`.
`uv` was not used.

```text
exact orphan-receipt node
  1 passed in 8.93s

complete Message module
  99 passed in 111.86s

four unchanged shared retry nodes
  4 passed in 127.68s

common-axis collection
  13 tests collected in 0.40s

pre-activated-authority exact C-01 public probe
  pass; exact ConflictError; domain events 0; domain and authority state unchanged

exact b400 parent-red node with candidate test blob
  1 failed in 11.98s at event-count no-mutation assertion, as required

candidate missing-index + changed-command-ID public probe
  returned original accepted receipt; reconstructed index; state changed

exact b400 classification probe for the same interaction
  identical accepted outcome and index mutation

ruff check over all eight implementation/test paths
  All checks passed!

ruff format --check over all eight implementation/test paths
  8 files already formatted

git diff --check parent..candidate over the two code/test paths
  exit 0

git diff --check implementation-base..candidate over all eight implementation/test paths
  exit 0
```

No package or full repository suite was run. The requested complete Message module,
shared retry nodes, static checks, exact public probes, and the decisive Major
cross-axis failure define the demonstrated dependency surface; a broader suite would
not resolve the exact identity defect.

## Current-main integration risk and hard stops

At review time both live `origin/main` and local `origin/main` resolve to the supplied
`dd67dca5ff69c1aeefb903c63f3437df357280c0`. Main and the candidate diverge at
implementation base `7275184e41fbfb149d2c91462ac872012d29a961`. Main-side changes
overlap `research_system/authority.py`, `research_system/command/service.py`,
`research_system/projection/replay.py`, `research_system/schema_registry.py`, and a
shared authority-activation integration test. This is a later conditional integration
seam, not a defect penalty on the frozen exact subject. No merge, rebase, cherry-pick,
integration, PR, Jira, CodeRabbit, owner-acceptance, provider, or external action is
authorized by this review.

## Final verdict

**`rework_required`**

The exact orphan-receipt/no-event C-01 mutation is closed at candidate `62a87fd`, and
the protected identities and focused regression evidence remain sound. Exact-subject
acceptance is blocked by PB-M-01: event-backed missing-index recovery still accepts a
changed Message command ID and publishes the reconstructed scoped index instead of
raising the required typed conflict without mutation.
