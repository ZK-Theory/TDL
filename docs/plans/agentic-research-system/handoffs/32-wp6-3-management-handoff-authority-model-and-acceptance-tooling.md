# WP6.3 management handoff — authority-model decision, acceptance tooling, then acceptance

**Created:** 2026-07-30
**Updated:** 2026-07-30 after the KAN-64/runtime-schema investigation
**For:** the fresh WP6.3 coordinator (management role)
**Base:** `origin/main` at `9045d78`
**Amendment subject:** local `main` at `da6b5c04ef4e1c914277b42a2dc5250d134f74dc` before this uncommitted amendment
**Status of every state claim here:** verified against the tree/source on 2026-07-30 at the cited file:line or command — but treat it as a claim with a timestamp and re-verify before acting. This document was written by the outgoing handoff manager specifically to avoid the failure where a fresh agent stalls, or acts wrongly, because the handoff was sloppy. Read the hard stops in §6 before you touch anything.

## 0. Executive correction — stop the review loop and repair the runtime boundary

The WP6 schema work has **not disappeared and does not need to be generated
again**. The 87 command schemas and 86 event schemas (173 files) were generated,
independently checked at exact bytes, and owner-accepted under D-G6-3. That
acceptance deliberately covered the schema artefacts only. It did **not**
authorize runtime registration, migration, reducers, projections, or the rest
of WP6.1. The durable authority is
`.research-system/contracts/wp6-1-stage2-owner-acceptance-record.yaml`.

The failure was in the management and integration work around those accepted
artefacts:

1. Merging the generated files into a recursively scanned schema directory
   accidentally made them live runtime validators. No explicit activation
   decision or versioned runtime binding existed.
2. The current runtime still emits the older, small payloads and validates
   commands against the generic command schema. It cannot satisfy the richer
   accepted command/event pairs yet.
3. KAN-64 and RM-01 treated the missing `command_schema_*` fields as if they
   explained the whole red suite. They do not. The event payloads are
   independently incompatible, and the generic event schema currently forbids
   those three new fields.
4. Handoff 32 originally described KAN-64 as an independent A/B choice. That was
   wrong. Neither literal choice supplies the versioned binding and activation
   model required by the accepted WP6 design.

This is the responsibility boundary the next Manager must use:

- **Schema generation/review:** complete for the accepted 173-file D-G6-3
  subject. Preserve those exact bytes.
- **Runtime schema catalogue, version binding, activation, compatibility and
  producer integration:** incomplete and incorrectly scoped by KAN-64/RM-01.
- **Full WP6.1 behaviour:** still to be delivered as command/event vertical
  slices, including payload construction, reducers, projections and replay.
- **WP6.3:** its pack bytes are accepted, but its production writer, grant
  issuance and acceptance runner are still missing.

### The next vertical action

**Do not commission another broad review or regenerate the 173 schemas.**
Re-scope KAN-64/RM-01 into one implementation deliverable: the **versioned
runtime schema binding and activation foundation** described in §5A0. Once that
foundation passes its focused tests, use it for the WP6.3 post-genesis grant
path in §5A. This repairs the shared boundary once and then produces a real,
usable WP6.3 capability.

The KAN-64 scope investigation is a blocking correction to the old plan, not a
request for another review:
`docs/plans/agentic-research-system/reviews/kan-64-command-schema-currency-scope-analysis-2026-07-30.md`.
The resulting execution verdict for KAN-64/RM-01 as currently scoped is
**`rework_required`**.

## 1. Read this first — what WP6.3 actually is right now

WP6.3 is **not** "finish authoring the pack and accept it." The three owner
decisions that were open (lane scope, reviewer capabilities, acceptance
statement) are **given** (§4). What remains is larger and different: **the
acceptance path the contract requires has no production tooling.** The control
store can hold the records and the loader can read them, but nothing writes the
multi-party records, issues the R3 acceptance grant, or runs the acceptance —
all three exist only as test doubles. And one of those gaps is not a build but a
**core-authority-model decision** that is yours to drive after A0.

Your job, in order: **(A0) deliver the shared schema binding/activation
foundation → (A) obtain the one remaining authority-model ruling and deliver
the post-genesis grant path → (B) deliver the record writer and acceptance
runner → (C) coordinate the multi-party acceptance → (D) close.** Details in
§5. This is a delivery sequence, not permission to start another campaign-wide
analysis.

Full evidence for all of this is in
`docs/plans/agentic-research-system/reviews/wp6-3-control-store-acceptance-mechanics-2026-07-30.md`.
Read it before §5.

## 2. Verified current state (re-verify; do not trust this table)

| Fact | Value / where to check |
|---|---|
| Base | `origin/main` at `9045d78` |
| PR | **#197** open, `mergeable: MERGEABLE` but `mergeStateStatus: BLOCKED` — the required `lint-and-test` check **has never run** on the branch (`gh run list --branch pipe/wp6-3-tdl-private-pack` → empty). CodeRabbit came back **rate-limited**. It will not merge on the normal path without CI running or an admin override. |
| Branch vs main | `pipe/wp6-3-tdl-private-pack` fully contains `main`; changes only 4 files; `pack_loader.py`/`resolver.py` are byte-identical to `main` |
| Owner-accepted bytes | `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` and its schema are **byte-identical to `449b0d00`** (`git diff --stat 449b0d00 origin/pipe/wp6-3-tdl-private-pack -- <both>` is empty). **Do not edit them (§6).** |
| Decision-5 preconditions | All five hold on `main`: #194 merged (`8b9c5833`, ancestor of main); `_RECORD_ENVELOPE` = 12 classes (`pack_loader.py:69`); no generic `lifecycle_state`; resolver refuses a foreign root (`resolver.py:104`); staleness resolves the pinned relationship record and rejects a lapsed window / sub-floor grade (`pack_loader.py:444-460`) |
| Branch tests | WP6.3 contract + candidate modules: **72 passed** (run in a detached worktree with the main venv) |

## 3. Identities — 6 allocated, 5 still unallocated

**Allocated under W1 (handoffs 29 Decision 2 + Decision 4) — use these exact values, do not re-mint:**

| Field | Value |
|---|---|
| `producer_actor_id` = `prospective_producer_actor_id` | `act_019fa9de-c8a4-7ca5-9e03-8da0c2159a4b` |
| `assurance_requirement_id` (rev 1) | `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` |
| `acceptance_record_id` | `ard_019fa9de-c8a4-7978-90b1-8c73e8f1e5ed` |
| `task_id` (rev 1) | `tsk_019faddf-5d6c-7629-bc3b-b20112ad041d` |

**Still unallocated (5):** `owner_actor_id`, `author_actor_id`,
`scope_reviewer_actor_id`, `accepting_actor_id`, `prospective_producer_profile_id`.
Three (`author`, `scope_reviewer`, `acceptor`) are constrained to **differ from
the producer**. These are realised by writing real control-store records for
distinct parties — not by minting UUIDs (§6). Plus the relationship/acceptance
records carry further required fields (`scope_relationship_record_id`,
`relationship_record_id`, `subject/object_actor_id`, `grade`,
`effective_at`/`expires_at`).

**Risk classification (fixed, handoff 29 Decision 4):** `requested_risk` R3,
`w5_epistemic_risk_floor` R3, `action_semantic_risk` R3,
`requirement_relationship_grade` I2.

## 4. Owner decisions already given (Stephen, 2026-07-30) — do not re-ask

- **D-1 lane scope:** all six lanes `required`, none `not_applicable`.
- **D-2 reviewer capabilities:** signed off (for now) as drafted in handoff 31.
- **D-3 owner acceptance:** approved for assurance requirement
  `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` rev 1 — TDL_private, six lanes / 69
  obligations, R3 / W5-floor R3 / action-semantic R3 / I2; wp6-1 acceptance-record
  shape; carries `ard_019fa9de-c8a4-7978-90b1-8c73e8f1e5ed`.

These retire D-1/D-2/D-3. They do **not** unblock acceptance — §5.

## 5. The critical path

### A0. Repair the shared WP6 runtime schema boundary — first delivery item

The present `SchemaRegistry` recursively discovers every `*.schema.json`, keys
schemas by `$id` alone, discards the exact source bytes after parsing, and
rejects duplicate IDs. `EventLedger` then uses registry presence as the switch
for event-specific validation. In plain language: putting an accepted proposal
on disk accidentally turns it on, while the registry cannot retain two
versions of one schema or prove which exact bytes a producer used.

That is incompatible with the accepted WP6 rule in P-043 and W2: a stable
schema ID may have semantic versions; old and new readers must coexist where
history requires it; persisted history is never silently reinterpreted; and
the event records the exact command-schema bytes that validated its command.

Re-scope KAN-64/RM-01 so the implementation deliverable has all of these
outcomes:

1. **Catalogue is not activation.** Schema files can be materialized and
   reviewed without becoming live validators. Runtime command and event
   bindings are explicit.
2. **Version and exact identity are real.** Runtime lookup supports at least
   `(schema_id, schema_version)` and retains the raw bytes and SHA-256 used for
   validation. Validation returns that identity to the producer.
3. **The live envelope is coherent.** A newly emitted event can carry
   `command_schema_id`, `command_schema_version`, and
   `command_schema_sha256` without failing the generic event envelope. An
   activated event-specific schema must also validate; an inactive proposal
   must not.
4. **History remains readable.** Inventory the configured external control
   stores before selecting the cutover. If old records exist, retain old and
   new readers or use an explicit versioned migration; never rewrite or
   reinterpret historical records. If no records exist, record a clean-start
   decision with the evidence used.
5. **One real vertical proof passes.** The proof pair is
   `CreateTask` → `TaskCreated`. Exercise it with positive, inactive-schema,
   wrong-version, wrong-hash, and replay/legacy cases. Do not claim the whole
   86/87 runtime is implemented from this one slice.

The existing 173 accepted generated schemas are frozen inputs to this work.
Changing or regenerating them is out of scope unless an exact-byte defect is
demonstrated and Stephen separately authorizes a new schema subject.

The old RM-01 exclusion of `research_system/schema_registry.py` is therefore
withdrawn: that file is part of the defect, and a producer-only patch cannot
meet the accepted system requirements. The focused unit result to carry
forward is `tests/research_system/unit/test_command_service.py`: 10 failed,
7 passed on the investigated subject, with both missing provenance and payload
shape errors. Do not misreport those failures as one cause.

### A. Authority-model extension — second delivery item, one owner ruling

`validate_requirement` requires, at R3,
`authority_policy.permits(accepting_actor_id, "accept_r3_assurance_requirement")`
(`assurance/requirements.py:159-163`), and the production policy resolves that
from a **replayed ledger grant** (`LedgerBackedAuthorityPolicy`,
`requirements.py:43-113`). But `AuthorityGrantActivated` is emitted in exactly
one place — the `store init` bootstrap (`authority.py:782`) — which mints two
grants (`RevokeAuthorityGrant`, `PublishReleaseGateDecision`) and forbids `"*"`
(`authority.py:165, 272-277`). **No command type activates a new grant.** The
authority model can mint grants only at genesis and revoke them after; it cannot
*issue* a new, differently-scoped grant.

So the contract requires a capability the model does not have. The recommended
design is a **post-genesis, scoped grant-activation command** that emits
`AuthorityGrantActivated`, records its exact command/event schema identities,
replays deterministically, and can later be revoked. The only remaining owner
ruling should be the narrow authority question: **which existing actor or
capability may issue that command, and under what scope?** Present that
recommendation and question to Stephen once. Do not reopen D-1/D-2/D-3 and do
not offer an acceptance bypass as the easy option.

Build this path on A0 rather than adding another schema-presence special case.
If Stephen chooses a different grant mechanism, record that exact decision and
its replay/revocation consequences before implementation.

### B. Build the acceptance tooling (agent-buildable; not owner-gated once A is decided)

Three pieces, all currently test-double-only:

1. a control-store **record writer** for the external assurance/relationship
   records, usable by genuinely distinct parties (not one session);
2. the **grant-issuance** path chosen in A;
3. a production **acceptance runner** that constructs
   `ControlStoreAuthorityResolver` + `LedgerBackedAuthorityPolicy` and runs
   `validate_requirement` + `load_pack` over the real control store.

Each piece is result-bearing ARS/assurance code: run research-assurance triage,
write the binding test / negative control first, and keep enforcement mechanical.

### C. Multi-party orchestration (owner/W1) + acceptance

With the tooling built: distinct author, an **independent I2 scope reviewer**,
the acceptor (Stephen), and the agent producer — each party's record authored by
that party; the relationship-evidence record at grade I2 with a validity window;
the R3 grant issued to the accepting actor. Then run the acceptance runner
(green), author the pack candidate replacing every placeholder (report the real
`pack_git_blob`/`pack_raw_sha256`, not the placeholder-derived
`2728b135…`/`e0cb712b…`), compute the acceptance-record sha256 over canonical
bytes, complete the allocation file.

### D. Close

Independent pack review → close Gate A A7 → then (separately, not by this lane)
WP6.4 / Gate 6. A7 is not self-reviewable.

### What “done” means for this Manager

The Manager has made concrete progress only when a production path exists and
focused tests pass. A revised plan, a new issue list, or another review of the
same accepted bytes is not completion. The delivery checkpoints are:

- A0 merged as an explicit, versioned activation foundation with its focused
  compatibility tests;
- the owner’s one grant-issuer ruling durably recorded;
- the post-genesis scoped grant path, control-store writer and acceptance
  runner implemented and tested;
- the real multi-party records created by their actual parties; and
- the WP6.3 acceptance run completed or stopped on one named external action
  that only Stephen/the relevant human party can perform.

After A0, broader WP6.1 delivery continues by activating complete vertical
command/event slices — schema binding, payload production, reducer, projection,
replay and negative cases together. Do not activate all 173 schemas merely
because the catalogue can see them.

## 6. Hard stops — read these before acting

- **The "preconditions met" trap (reconciled).** #194 is merged and all five
  Decision-5 preconditions now hold. Handoff 29 said the control-store record
  path "is not open until PR #194 is on `main`" — that phrasing now reads as a
  green light. **It is not.** #194 delivered the *read* side (the resolver). The
  *write* side and the grant issuer **do not exist** (§5, mechanics doc). And
  even when built, one session must not author every party's record. "Preconditions
  met" does **not** authorize writing records or issuing the grant.
- **Do not fabricate an `authority_grant` object** by calling `ObjectStore.write`
  directly to satisfy the R3 gate. That bypasses the ledger/replay integrity the
  whole authority model rests on. The grant must be issued through the mechanism
  decided in §5A, or not at all.
- **Do not implement KAN-64 or RM-01 as currently written.** A producer-only
  provenance patch leaves both the generic-envelope contradiction and the
  payload mismatch unresolved.
- **Do not remove the generated schemas or filter them with a one-off
  `x-lifecycle` check and call WP6 fixed.** Lifecycle is part of an explicit,
  versioned runtime binding; directory discovery is not activation.
- **Do not regenerate or re-review the accepted 173 WP6.1 schemas** without a
  demonstrated exact-byte defect and a new owner-authorized subject.
- **Do not write control-store records single-session on behalf of multiple
  parties.** That is the self-attestation the pack exists to prevent — the
  externality of the store makes records *capable* of being sound; it does not
  make them sound when one party writes them all.
- **Do not edit** `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
  or `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`.
  Owner-accepted at exact bytes at `449b0d00`; editing forces a fresh independent
  review.
- **Do not mint identities** into repository YAML (the 5 in §3).
- **Do not** self-review, close Gate A A7, dispatch WP6.4, or move Gate 6.
- **No** provider calls, migrations, eligibility transitions, or live-governance
  actions. Planning authority is not runtime authority.

## 7. Environment traps (each has cost a session)

- `petls` is a **dependency group, not an extra**: `uv sync --group petls`, not
  `--all-extras`. No Windows wheel; nothing depends on it; CI covers it Linux-only.
- `uv run` inside a **linked worktree** resolves that worktree and tries to sync
  it (a `petls` build that fails on missing Boost). Use
  `C:/Users/steph/TDL/.venv/Scripts/python.exe` directly, or set
  `UV_PROJECT_ENVIRONMENT=C:/Users/steph/TDL/.venv UV_NO_SYNC=1`.
- The **pre-commit gate takes >2 min**. A 120s-timeout shell call will time out
  while the commit succeeds — check `git log` before concluding failure.
- **Git hooks live in `.githooks/`** (`core.hooksPath`); anything in `.git/hooks/`
  is silently ignored. Never `--no-verify`.
- **Multi-line commit messages go in a file** committed with `git commit -F`,
  written with the file-write tool — never a shell heredoc. PowerShell
  `Out-File -Encoding utf8` adds a BOM that breaks the repo's `prepare-commit-msg`
  prefix detection.
- **Confirm cwd and branch before any write.**
- Suite run: `C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -q
  tests/research_system -o "addopts=" -p no:cacheprovider -p no:cov`. Contracts
  alone ~11 min; the full directory (1515 tests) is very slow.

## 8. Authorities to use — read only what the next delivery needs

1. This handoff.
2. `reviews/kan-64-command-schema-currency-scope-analysis-2026-07-30.md` plus
   §5A0 above — evidence for withdrawing the old A/B fork and RM-01 scope.
3. `reviews/wp6-3-control-store-acceptance-mechanics-2026-07-30.md` — the trace
   behind §5A/§5B (what exists, what must be built, file:line).
4. Handoff 31 (on branch `pipe/wp6-3-tdl-private-pack`) — the lane projection,
   the D-1/D-2/D-3 drafts, and the "blocker Decision 5 does not fully retire."
5. Handoff 29 (on `main`) — the W1 identity allocations, Decision 4/5, and hard
   stops. **Note its "path not open until #194" language is now stale — see §6.**
6. Handoffs 27 and 28 only when their implementation detail or test baseline is
   needed. Do not replay the entire handoff chain as a prerequisite to A0.

## 9. WP6 dependency map and immediate dispatch boundary

KAN-64 is no longer an “adjacent” producer-field ticket. Its corrected A0 scope
is the shared runtime foundation on which the new WP6.3 authority command must
rely. Keep the implementation subjects bounded, but preserve this dependency:

`accepted schema artefacts (frozen)` → `A0 explicit versioned runtime binding`
→ `WP6.3 scoped grant command + writer + runner` → `multi-party acceptance`
→ `WP6.4 / Gate 6`.

The next Manager’s first dispatch is **A0 only**. It must identify the exact
base SHA, a dedicated candidate branch/worktree and write owner; permit changes
to the registry/binding layer, generic envelope versioning, producer identity
plumbing and focused tests; forbid edits to the 173 accepted generated schemas
and the two owner-accepted WP6.3 pack/schema files. Candidate acceptance is
focused behavioural evidence, not another contract-byte review. Once A0 is
accepted, dispatch §5A as the next semantic subject rather than silently
expanding the same author task.

## 10. Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
