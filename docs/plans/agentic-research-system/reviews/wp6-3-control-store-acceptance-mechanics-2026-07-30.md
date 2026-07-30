# WP6.3 control-store acceptance mechanics — what exists, what must be built

**Created:** 2026-07-30
**For:** the fresh WP6.3 management handoff (coordinator)
**Base traced:** `origin/main` at `9045d78`
**Status of every claim:** read from source at the cited file:line, not inferred.

## Bottom line

Handoffs 29 and 31 describe completing WP6.3 acceptance as an owner/W1 *action* —
"allocate the remaining identities by writing the records into the external
control store," and "R3 acceptance is complete when a grant authorising your
actor to take `accept_r3_assurance_requirement` exists in the store and replays
cleanly." Traced to source, **that step has no production tooling.** The control
store can *hold* these records and the loader can *read* them, but nothing in
`research_system/` or `scripts/` *writes* the multi-party records, *issues* the
acceptance grant, or *runs* the acceptance over the real store. All three exist
only as test doubles.

So WP6.3 acceptance is not gated on a few owner keystrokes. It is gated on
building the acceptance tooling first — and one leg of that touches the core
authority model, which today can only mint grants at genesis.

## What exists (verified)

- **Externality + immutable content-addressed store.** `ObjectStore.write(kind,
  object_id, revision, value)` persists an immutable revision whose filename is
  the SHA-256 of its canonical bytes (`store/objects.py:208, 138-201`);
  `require_control_root_disjoint_from_code_roots` keeps the store outside every
  code root (asserted on every resolver bind, `assurance/resolver.py:74-79`).
- **The read side (PR #194).** `ControlStoreAuthorityResolver.resolve` reads an
  external record from kind `assurance_record`, latest revision, and refuses a
  foreign authority root (`assurance/resolver.py:81-112`, root check at :104).
- **Grant replay.** `LedgerAuthorityGrantResolver` replays the ledger to resolve
  a grant's actor, allowed commands, risk ceiling, and validity window
  (`authority.py`, grant model at :109-191).
- **The acceptance rule.** `validate_requirement` requires, at effective R3,
  `authority_policy.permits(accepting_actor_id, "accept_r3_assurance_requirement")`
  to return true (`assurance/requirements.py:159-163`), and the production policy
  is `LedgerBackedAuthorityPolicy`, which derives that from a replayed grant
  (`requirements.py:43-113`).
- **Bootstrap grants.** `store init` mints exactly two grants — a root grant
  scoped to `RevokeAuthorityGrant` and a publication grant scoped to
  `PublishReleaseGateDecision` (`authority.py:742-793`, scopes asserted at
  :272-279).

## What does not exist — the three gaps

**Gap 1 — no writer for the external multi-party records.** Nothing writes
`assurance_record`/`relationship_record` objects except three test files
(`test_external_record_envelope_and_resolver.py`,
`test_assurance_requirements.py`, `test_authority_grant_source.py`). No CLI
subcommand, no `scripts/` entry, no production caller of `ObjectStore.write` for
this kind. The `ars` CLI exposes `store init`, `command submit`, `replay verify`,
`projection rebuild`, and the `eval` family — none writes an assurance record
(`cli.py:577-640`).

**Gap 2 — no path to issue an `accept_r3_assurance_requirement` grant.**
`AuthorityGrantActivated` is emitted in exactly one place: the `store init`
bootstrap (`authority.py:782`). No command type in `CommandService._build_event`
produces it (`command/service.py:831-893` emits only TaskCreated, DispatchClaimed,
TaskSuperseded, EvidenceDeletionVerified, AuthorityGrantRevoked,
ReleaseGateDecisionPublished). The bootstrap manifest's fields are exact — it can
carry only the root and publication grants (`authority.py:242-282`) — and
`AuthorityGrant.from_dict` forbids a `"*"` wildcard command (`authority.py:165`).
So there is no way, genesis or later, to activate a grant whose
`allowed_command_types` includes `accept_r3_assurance_requirement`. **Grants are
issuable only at genesis, and only the two hardcoded ones.**

**Gap 3 — no production acceptance runner.** `ControlStoreAuthorityResolver(` and
`LedgerBackedAuthorityPolicy(` are constructed nowhere in `research_system` —
only in tests. Nothing wires the pack loader / `validate_requirement` to the real
control store. Even with records and a grant in place, no production entry point
runs the acceptance.

## What this means for unblocking WP6.3

The real sequence is **build, then orchestrate, then accept** — not "write and
issue."

1. **Build the acceptance tooling (agent-buildable engineering — not owner-gated,
   but sizeable and partly architectural):**
   - a control-store *record writer* for the external assurance/relationship
     records, usable by genuinely distinct parties (so it is not single-session);
   - an *authority-grant issuance* path for `accept_r3_assurance_requirement` —
     this is the deep one: it means extending the authority model beyond
     genesis-only grants (a new grant-activation command emitting
     `AuthorityGrantActivated` with a scoped `allowed_command_types`, its own
     schema, replay handling, and revocation story), or an equivalent design
     Stephen signs off;
   - a production *acceptance runner* constructing the resolver + ledger-backed
     policy and running `validate_requirement` + `load_pack` over the real store.
2. **Orchestrate the multi-party structure (owner/W1):** distinct author, an
   independent I2 scope reviewer, the acceptor (Stephen), and the agent producer
   — each party's record written by that party, the relationship-evidence record
   at grade I2 with a validity window, the R3 grant issued to the accepting
   actor.
3. **Accept and close:** run acceptance green, then the pack candidate, then the
   independent pack review, then Gate A A7.

## The architectural question underneath Gap 2

The authority model as built issues grants only at genesis and only supports
*revoking* them thereafter (`RevokeAuthorityGrant` is the root grant's sole
power). The WP6.3 assurance contract requires *issuing* a new, differently-scoped
grant (`accept_r3_assurance_requirement`) — a capability the model does not have.
This is the same shape as KAN-64: a contract/spec landed ahead of the runtime
that must satisfy it. Whether to extend the authority model to issue post-genesis
grants, or to accept assurance R3 through a different mechanism, is an owner
decision, and it is the true critical path for WP6.3 — larger than the three
decisions already given.

## Owner decisions captured 2026-07-30 (Stephen)

- **D-1 lane scope:** all six lanes `required`, none `not_applicable`.
- **D-2 reviewer capabilities:** signed off (for now) as drafted in handoff 31.
- **D-3 owner acceptance:** approved for assurance requirement
  `asr_019fa9de-c8a4-7ded-a0e8-41407ec0df34` rev 1 — TDL_private, six lanes / 69
  obligations, R3 / W5-floor R3 / action-semantic R3 / I2; wp6-1 acceptance-record
  shape; carries `ard_019fa9de-c8a4-7978-90b1-8c73e8f1e5ed`.

These retire D-1/D-2/D-3. They do **not** retire Gap 2's architectural question or
the build in step 1 — the acceptance still cannot be performed until the tooling
exists.

## What I did not pin

The exact id-kind prefixes for the external record ids (the registry that
PR #194 extended for `assurance_record`/`relationship_record`) were not located
to source in this trace; confirm them before authoring record ids.

## Sensitive information

No credentials, tokens, provider session data, or private research data included.
