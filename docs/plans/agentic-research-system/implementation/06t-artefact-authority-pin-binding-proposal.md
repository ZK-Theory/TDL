# 06t — Path-bound vs symbol-bound pins in `artefact-authority-interface.v1`

**Date:** 2026-09-08
**Status:** PROPOSAL — decision requested from Stephen. **No contract change has
been made.** `artefact-authority-interface.v1.yaml`, its identity manifests, and
`test_06i_stage_a_candidate.py` are untouched by this document.
**Origin:** research-observer observation `2026-08-12-file-map-frozen-since-wp1`
(PROCESS lane), second limb: *"contract pins that bind behaviour to a
`source_path` should be reviewed for whether path-binding or symbol-binding is
intended."*
**Subject:** `.research-system/contracts/artefact-authority-interface.v1.yaml`
at `ced524b` (`candidate_state: proposed`), and its sole enforcement artifact
`tests/research_system/contracts/test_06i_stage_a_candidate.py`.
**Authorizes nothing.** Adopting any option below is a contract amendment plus
an identity-manifest regeneration; both require Stephen's sign-off.

---

## 1. What is actually pinned

The contract carries **47 pins across 9 source files**. They are not one
mechanism; they are four, with materially different coupling:

| # | Pin class | Count | Identity form | How the test uses it |
|---|---|---|---|---|
| 1 | `consumer_inventory[].dispatch_bindings` | 11 | `path::owner.qualname::method` (one string) | **Discovered.** Whole-tree AST scan of `research_system/**/*.py` builds the same strings; asserted **set-equal** to the declared list. |
| 2 | `consumer_inventory[].transitive_root_bindings` | 25 | `source_path` + `qualified_symbol` + `required_calls` | **Declared, then verified.** The path is a lookup key: the test parses that file, finds that symbol, asserts `required_calls ⊆ reachable calls`. |
| 3 | `public_entrypoint_bindings` | 6 (1 console_script, 3 cli_handler, 2 public_export) | mixed | console_script resolves through `pyproject.toml` (already module-bound, not path-bound); cli_handler names a handler symbol only; public_export uses `source_path` + `symbol`. |
| 4 | `direct_storage_inventory` (4) + `dynamic_object_store_kind_exclusions` (5) | 9 | `path` + `owner` (+ operation, kind) | **Discovered.** Whole-tree AST scan of object-store call sites; asserted **set-equal**. |

The nine pinned files, with current size:

```
  7198  research_system/command/service.py
  2124  research_system/cli.py
  1013  research_system/assurance/external_records.py
   668  research_system/artefacts/use_resolver.py
   650  research_system/session_exchange/exchange.py
   410  research_system/evals/release_publication.py
   247  research_system/methods/brief.py
     -  research_system/methods/__init__.py          (re-export only)
     -  research_system/session_exchange/__init__.py (re-export only)
```

Two observations that should be on the record before any judgement:

- **The checks are fail-loud, not silent.** `_function_calls` ends in
  `raise AssertionError(f"missing declared production root: {path}:{symbol}")`.
  A pin whose file or symbol disappears produces a named failure, not a vacuous
  pass. This is *not* an instance of the silent-absence failure mode.
- **The exhaustiveness guarantee comes from the scan, not from the path.** Pin
  classes 1 and 4 are strong precisely because the scan is whole-tree: a new
  artefact consumer or a new object-store write added *anywhere* under
  `research_system/` fails the set-equality assertion. That property is
  independent of whether the recorded identity contains a file path.

## 2. The cost that has already accrued

Modularising `research_system/command/service.py` (7,198 lines) is the concrete
case. Three of its symbols are pinned:
`CommandService._prepare_release_publication`,
`CommandService._ensure_artefact_materialized`, and
`CommandService._reconcile_scoped_activation_marker` /
`_reconcile_scoped_activation_receipt`.

A pure move — same code, same call graph, different module — currently requires:

1. editing `artefact-authority-interface.v1.yaml` (the recorded strings change);
2. regenerating **two** identity manifests, at
   `.research-system/contracts/candidates/06i-artefact-authority-v1/identity-manifest.yaml`
   and `.research-system/contracts/artefact-authority-v1/identity-manifest.yaml`,
   which pin the interface by `git_blob 728b9ed7…` and
   `canonical_sha256 dd085c86…` and must stay in lockstep;
3. presenting the resulting new candidate identity for review.

So the WP1 layout decision is now enforced by a content-addressed contract. That
is the accretion the observation names: nobody decided that
`_prepare_release_publication` must live in `command/service.py`; WP1 named the
file, five work packages grew capability into it, and 06i later pinned symbols
to it by path.

**The amendment window is open now and closes on acceptance.** The candidate is
`candidate_state: proposed`. No owner acceptance record binds the interface
digest — `wp6-1-stage2-owner-acceptance-record.yaml` does not reference
`dd085c86…`. Amending before the candidate is accepted costs one review of an
unaccepted proposal. Amending afterwards costs a supersession of an
owner-accepted authority object.

## 3. The case *for* keeping path-binding

This should not be waved past. Path-binding buys three things:

- **A privilege surface is a module boundary in practice.** `direct_storage_inventory`
  does not merely record that `_ensure_artefact_materialized` writes artefact
  objects; its `classification: registration_storage_mechanics` asserts *which
  component* is allowed that privilege. If artefact-object writes migrated into
  a new module under the same symbol name, a symbol-only identity would not
  notice. For a privilege boundary, "which module holds this power" is arguably
  the fact under review.
- **Diff legibility.** A reviewer reading the YAML sees where each pinned
  behaviour lives without resolving anything.
- **Forcing function.** The current cost is real, but it does force a
  large-module refactor through owner review rather than letting it happen
  silently. Removing the coupling removes that prompt.

The counter-argument is narrower than "path-binding is brittle": for pin classes
1, 2, and the `public_export` half of 3, the path contributes **nothing to
authority**. Those pins record call-graph facts — who dispatches
`resolve_for_*`, which roots reach which calls, which symbol is re-exported. The
authority question is *which symbol does this*, and the file it sits in is an
incidental fact of the current layout.

## 4. Options

### Option A — No change

Keep all 47 pins path-bound. Accept that module layout under `research_system/`
is a contract-amendment surface.

*For:* zero work; maximum forcing function; preserves the privilege-boundary
reading uniformly.
*Against:* `service.py` at 7,198 lines is a maintainability problem the health
index already flags, and its decomposition now carries contract-amendment cost
on top of refactor cost. The forcing function fires on moves that change no
behaviour at all, which is the definition of a false positive; a gate that fires
on non-events trains people to route around it.

### Option B — Symbol-bind everything

Replace every `source_path` with a module-agnostic symbol identity and resolve
by import or by qualname lookup across the tree.

*For:* refactor-transparent.
*Against:* **do not adopt this.** Import-time resolution executes production code
inside a contract check, which is unacceptable for an authority artifact. And
uniform symbol-binding erases the privilege-boundary property in §3 for the nine
storage pins, where it is the point.

### Option C — Split by what the pin asserts (recommended)

Bind by symbol where the pin records a **call-graph fact**; keep path-binding
where the pin records a **privilege boundary**.

| Pin class | Treatment | Rationale |
|---|---|---|
| 1 `dispatch_bindings` (11) | **Symbol-bound.** Recorded identity becomes `owner.qualname::method`. Keep the whole-tree scan; demote the discovered path to a non-normative `observed_in` field the test does **not** compare. | Records who calls `resolve_for_*`. The module is incidental. |
| 2 `transitive_root_bindings` (25) | **Symbol-bound.** Resolve `qualified_symbol` by scanning the tree for a unique definition instead of opening a declared `source_path`. Keep `observed_in` as non-normative. | Records reachability from a root. The module is incidental. |
| 3 `public_export` (2) | **Symbol-bound** against the declared package `__init__`. `console_script` and `cli_handler` already are. | Already nearly symbol-bound. |
| 4 `direct_storage_inventory` + `dynamic_object_store_kind_exclusions` (9) | **Keep path-bound.** | These *are* the privilege boundary. Moving an artefact-object writer into a different component is exactly the event the owner should review. |

Result: 38 pins become refactor-transparent; 9 stay as a deliberate,
documented forcing function.

**Required control, without which Option C is unsafe.** Demoting the path makes
`owner.qualname` the identity, so the contract must prove that identity is
unique. Add an invariant to the same test: **every pinned `owner.qualname` has
exactly one definition site under `research_system/`.** Without it, moving a
consumer into a module that already defines the same qualname becomes invisible.
The negative control writes a second definition of a pinned qualname into a
`tmp_path` fixture module and asserts the uniqueness check fails — this must
ship in the same change, per the gate rule that every new check arrives with a
watched failure.

Exhaustiveness is unaffected: the scan still walks the whole tree, so a new
consumer or a new object-store write anywhere still breaks set-equality. Only
the *recorded* identity loses its path component.

### Option D — Defer to Gate 7

Record the coupling as known and revisit when the candidate is accepted.

*Against:* this is Option A with the amendment window closed. Deferral converts
a proposal-stage edit into a supersession of an accepted authority object.

## 5. Recommendation

**Option C**, decided before the 06i candidate moves out of
`candidate_state: proposed`.

The reasoning is that the two limbs of the contract are doing different jobs and
have been given one mechanism. Pin classes 1–3 answer "does this symbol still do
this?"; the path is not part of that question and its presence converts every
layout change into an owner decision. Pin class 4 answers "is this component
still the only one with this privilege?"; there the path *is* the question. The
split costs one focused change to a single test module plus one contract edit,
and it retires the coupling from 38 of 47 pins without weakening any check —
provided the qualname-uniqueness invariant and its negative control ship in the
same change.

Estimated cost: one bounded session — the changes are confined to
`test_06i_stage_a_candidate.py` (five helper functions and three test bodies),
the interface YAML, and both identity manifests. No `research_system/` change.

**If Option C is approved,** the change should be scheduled as a standalone slice
and must not be folded into 06s's Gate 6 delivery phases: 06s Phase 0 is
explicitly `no research_system/ change, no test additions`, and the later phases
own their own review budget.

## 6. Adjacent finding (not part of this decision)

While tracing the enforcement path, one assertion in the same test appears
close to vacuous. `_cli_handlers_and_tokens` collects `tokens` as *every string
constant anywhere in `cli.py`*, so:

```python
assert set(binding["command_tokens"]) <= tokens
```

passes for any command token string that appears anywhere in a 2,124-line
module, including in an unrelated docstring or error message. It does not
establish that the tokens form a registered command path. This is a separate
GATE-lane item, logged independently; it is not resolved by any option above and
should not be bundled into this decision.

## 7. Decision requested

- [ ] **A** — no change; accept module layout as a contract-amendment surface.
- [ ] **C** — split by pin semantics (recommended); schedule as a standalone
      slice with the qualname-uniqueness invariant and its negative control.
- [ ] **D** — defer; accept that the amendment window closes on candidate
      acceptance.

Option B is listed for completeness and is not recommended.

## 8. Verification sources

- Contract: `.research-system/contracts/artefact-authority-interface.v1.yaml`
  (identical bytes to the candidate copy under
  `.research-system/contracts/candidates/06i-artefact-authority-v1/`).
- Enforcement: `tests/research_system/contracts/test_06i_stage_a_candidate.py`,
  in particular `_production_dispatch_bindings`, `_object_store_boundary_calls`,
  `_function_calls`, `_module_exports`, `_cli_handlers_and_tokens`, and
  `test_consumer_inventory_is_exactly_closed_over_policy_and_production_dispatch`.
- Identity: `identity-manifest.yaml` under both
  `.research-system/contracts/candidates/06i-artefact-authority-v1/` and
  `.research-system/contracts/artefact-authority-v1/`.
- Plan of origin: [06i](06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md).
- WP1 file map: [01](01-control-plane-and-replay-plan.md).
