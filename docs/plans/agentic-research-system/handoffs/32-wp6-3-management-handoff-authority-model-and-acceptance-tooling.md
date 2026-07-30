# WP6.3 management handoff — authority-model decision, acceptance tooling, then acceptance

**Created:** 2026-07-30
**For:** the fresh WP6.3 coordinator (management role)
**Base:** `origin/main` at `9045d78`
**Status of every state claim here:** verified against the tree/source on 2026-07-30 at the cited file:line or command — but treat it as a claim with a timestamp and re-verify before acting. This document was written by the outgoing handoff manager specifically to avoid the failure where a fresh agent stalls, or acts wrongly, because the handoff was sloppy. Read the two hard-stop reconciliations in §6 before you touch anything.

## 1. Read this first — what WP6.3 actually is right now

WP6.3 is **not** "finish authoring the pack and accept it." The three owner
decisions that were open (lane scope, reviewer capabilities, acceptance
statement) are **given** (§4). What remains is larger and different: **the
acceptance path the contract requires has no production tooling.** The control
store can hold the records and the loader can read them, but nothing writes the
multi-party records, issues the R3 acceptance grant, or runs the acceptance —
all three exist only as test doubles. And one of those gaps is not a build but a
**core-authority-model decision** that is yours to drive first.

Your job, in order: **(A) drive the authority-model decision to a resolution
with Stephen → (B) coordinate building the acceptance tooling → (C) coordinate
the multi-party orchestration and the acceptance → (D) close.** Details in §5.

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

### A. Authority-model extension — your first item, an owner decision to drive

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

So the contract requires a capability the model does not have. **Drive this to a
Stephen decision before any build:** extend the authority model to issue
post-genesis grants (a new grant-activation command emitting
`AuthorityGrantActivated` with a scoped `allowed_command_types`, its own schema,
replay handling, and a revocation story), **or** accept assurance R3 through a
different mechanism Stephen signs off. This is the true critical path — larger
than the three decisions in §4. Do not choose it yourself; surface it, with the
mechanics doc as evidence, and get a ruling.

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

## 8. Documents, in reading order

1. This handoff.
2. `reviews/wp6-3-control-store-acceptance-mechanics-2026-07-30.md` — the trace
   behind §5 (what exists, what must be built, file:line).
3. Handoff 31 (on branch `pipe/wp6-3-tdl-private-pack`) — the lane projection,
   the D-1/D-2/D-3 drafts, and the "blocker Decision 5 does not fully retire."
4. Handoff 29 (on `main`) — the W1 identity allocations, Decision 4/5, and hard
   stops. **Note its "path not open until #194" language is now stale — see §6.**
5. Handoffs 27 (implementation brief) and 28 (test baseline) for background.

## 9. Adjacent open thread (not WP6.3, but in the WP6 remit)

**KAN-64** (`command_schema_*` producer gap) has a scope analysis awaiting
Stephen's A/B decision:
`reviews/kan-64-command-schema-currency-scope-analysis-2026-07-30.md`. Independent
of WP6.3; do not fold them together.

## 10. Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
