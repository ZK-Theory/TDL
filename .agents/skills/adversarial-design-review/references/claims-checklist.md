# Claims About Another Artefact: the Checklist

One checklist for both sides of a design document. `writing-plans-extras` uses the **Author** lines before a plan
or note states the claim; `adversarial-design-review` uses the **Reviewer** lines when it attacks the claim. Each
lesson is written once, here, with the observation that produced it.

A design's riskiest sentences describe something it does not own: a spec it reuses, a precedent it copies, a path
that "already handles" a case, a fix a reviewer prescribed. Check each one against the bytes or code that will decide
it, never against prose that describes them. Cite what you checked with `path:line`.

When a new lesson of this kind is approved, add or extend an entry here rather than adding a bullet to either skill.
Give it both lines and its source.

## Reuse or extension

"Reuses §7.5 unchanged", "extends the role enum".

- **Author:** before claiming reuse, open the materialized, accepted schema files for the reused records and check
  every field, enum and `additionalProperties` the claim depends on. Inspect one real instance of each source the
  design must address.
- **Reviewer:** do the same check yourself. Prose that looks compatible is not evidence: the schema bytes decide.
- **Source:** `2026-10-22-spec-reuse-claims-must-diff-against-materialized-schemas`. W9 claimed to reuse W11 §7.5
  unchanged; W11's accepted schemas were closed (`additionalProperties: false`, a closed role enum,
  `target_object_refs` minItems 1).

## Shared-store tenants

A new command or event family on a shared store or ledger.

- **Author:** map what the family will meet, not only the path it copies. Enumerate every reducer that replays the
  whole ledger, with the branch each takes for an unknown event type (raise, ignore, misroute to a default reducer),
  and every closed allowlist the family must join: runtime bindings, grant command types, subject-kind enums, census
  pins. Cite each with `path:line`. Settle these before marking an interface unverified, because the code often
  already answers the question. A cheap control is a test that replays a ledger holding one synthetic foreign event
  through every public replay entry point and asserts a named, intended outcome for each.
- **Reviewer:** enumerate the same reducers, unknown-type branches and closed allowlists. A new tenant is defined as
  much by the readers it must not break as by the writer it adds.
- **Source:** `2026-10-23-new-event-family-must-map-whole-ledger-replays`. The 06v plan mapped the Discovery command
  path it copied but not `projection/replay.py`, which raises on any event outside its closed predicates.

## Precedents and "handled by existing X"

- **Author:** when following a precedent for shape, list which of its rows or mechanisms the plan drops, and give a
  `path:line` for whatever takes over each dropped row's job. For "handled by existing X", read X's preparer and
  record the subject or precondition check it applies. If the plan's subject cannot pass it, X does not handle the
  case.
- **Reviewer:** diff the precedent's row set, not only its field set, and list what the design drops. For every
  "handled by existing X", read X's preparer and record the subject or precondition check it applies, with
  `path:line`.
- **Source:** `2026-10-24-design-note-routed-commands-to-a-generic-path-without-reading-its-preparer`.

## Restated rules

A document summarises another accepted document's precondition matrix.

- **Author:** point to the owning matrix as operative ("adds to, never relaxes") and restate only what this plan
  adds.
- **Reviewer:** diff every restated condition against its owning row. The safe form points to the owner as operative
  and restates only the delta.
- **Source:** `2026-10-22-gate-definition-restates-owning-matrix-narrowly`.

## Catalogue IDs

An ID is re-specified, renamed or deferred.

- **Author:** first run `git grep -l <ID> -- .research-system research_system tests tools` and record what is
  already materialized.
- **Reviewer:** run the same command and record the materialized packages, executors, pins and ID-grammar schemas
  found.
- **Source:** `2026-10-23-respec-addendum-missed-materialized-fixture`.

## Selectors and parsers

A byte-level selector or segmentation contract.

- **Author:** ship a census of each governed file and a reference script run on the real bytes in the same commit as
  the contract.
- **Reviewer:** the contract is specified only once it has run on the files it governs. Require the census (heading,
  bullet, terminator and BOM forms, with counts) and a reference script whose outputs on the real bytes are recorded.
  Re-run the script.
- **Source:** `2026-10-23-segmentation-contract-written-without-target-census`. The anchor matched 114 of 167 real
  headings.

## "In the shape of" claims

- **Author:** a claim that one artefact emits rows "in the shape of" another's schema lands with a producer-to-consumer
  binding test in the PR that lands the later artefact.
- **Reviewer:** run the producer's output through the consumer's schema. Two artefacts that claim the same shape
  without a binding test drift.
- **Source:** `2026-10-23-accepted-tool-and-schema-claim-same-shape-without-a-binding-test`. The schema rejected every
  row the reference tool emitted.

## Verifiers

- **Author:** the verifier, not the subject, names the version of the expected side: pin its blob, SHA-256 and size.
  When the owner accepts bytes, compare bytes.
- **Reviewer:** for every expected-side read, find who names its version. If the subject supplies the commit, the
  check is self-attested. Compare the gate's pass set with the identity the owner accepts: if the owner accepts bytes,
  mutate the unpinned fields and the encoding and confirm a refusal.
- **Source:** `2026-10-24-verifier-pin-chosen-by-its-subject` (a verifier read its expected side at the commit the
  subject named); `2026-10-27-gate-pass-set-wider-than-accepted-identity` (a verifier accepted byte strings other than
  the one the owner accepted).

## Negative controls

- **Author:** a control is evidence only if it fails when, and only when, its own guard is removed. Assert the
  guard's own message, and pass git only hex literals that are on `main`.
- **Reviewer:** delete the guarded line in memory and confirm the control fails, matching the guard's own message
  rather than a substring a sibling check shares. A control that resolves a branch-only commit breaks after a squash
  merge: every hex literal it passes to git must be on `main`.
- **Source:** `2026-10-24-squash-merge-strands-sha-pinned-controls`.

## Prescribed corrections

A fix a reviewer prescribed, carried into the next draft.

- **Author:** a reviewer is not an owner source. Before copying a prescribed identifier or row range into the plan,
  quote it from its owner source with `file:line`, and trace the prescribed mechanism through the code it relies on.
- **Reviewer:** your own required corrections need the same source check as your findings. Quote every identifier
  from its owner source with `file:line`, and trace a prescribed mechanism through the code path it relies on before
  prescribing it. A reviewer is not an owner source.
- **Source:** `2026-10-22-reviewer-prescribed-identifiers-copied-unverified`. It happened twice: the OR-109 to OR-115
  range, wrong by one and copied verbatim into the next draft, then `load_store_manifest`.

## Probes

- **Author:** if the chosen shape differs from the prototype a probe ran, re-run the probe on the chosen shape before
  stating its result as evidence. Every probe case asserts its message. A revision that adds or changes an encoded
  field re-runs the probe on the final payloads.
- **Reviewer:** when the chosen shape differs from the probed prototype, re-run the probe on the chosen shape, with one
  instance of every event family the claim covers, before crediting the result. A probe case that prints instead of
  asserting is not evidence. A probe result covers the revision it ran on: when a later revision adds or changes an
  encoded field, run the final revision's payloads through the seam again.
- **Source:** `2026-10-27-design-note-chose-an-unprobed-shape`;
  `2026-11-09-design-note-encoding-never-run-through-the-unchanged-assigner` (probe currency).

## Absence claims

"X omits Y", "the set lacks Y", "the accepted set includes Y".

- **Author:** check the claim against the parsed artefact (a YAML or JSON load of the row) and put the parsed list in
  the note. A cited line range runs to the end of the enclosing item.
- **Reviewer:** re-derive the set from the parsed artefact, and re-read the cited range past its stated end. A read
  that stops early turns a complete set into an apparent gap.
- **Source:** `2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it`;
  `2026-10-29-cited-a-list-from-a-truncated-read` (its author-side twin).

## Enforcement claims

"Code cannot enforce X", "X is recorded, not proved", "code cannot refuse X". These are absence claims about code
paths.

- **Author:** enumerate every path that reaches the seam before saying none of them checks, with the same
  registry-aware closure that backs a caller-inventory claim (`writing-plans-extras`, "Caller-Inventory Closure").
- **Reviewer:** require a census of every path that reaches the seam (each production constructor and the admission it
  goes through), not one function's docstring.
- **Source:** `2026-11-08-enforcement-impossibility-claim-cited-one-function`.

## Wiring claims

"X passes Y to Z".

- **Author:** cite Z's production construction sites, show that each builder holds Y, and list each of those files in
  the package boundary. Naming the receiving class is not enough.
- **Reviewer:** find where production builds Z, confirm the builder holds Y, and check that the package boundary lists
  that file.
- **Both:** a seam is wired where its object is built, not where its class is defined. For the two W9 runtimes, the
  AST construction census in `test_w9_wp9_3_censuses.py` (#420) already checks this mechanically.
- **Source:** `2026-11-09-design-note-wiring-claims-named-the-wrong-construction-site`.

## Owner points on rules

A finding or owner point asks Stephen to decide or fix a rule.

- **Author:** before an owner point asks Stephen to decide a rule, search the accepted artefacts (the catalogue, the
  annex's `derivation_rules` and `global_preconditions`, the contracts, the register) for it and cite what you find.
- **Reviewer:** search the same accepted texts before a finding or owner point asks Stephen to fix the rule, and cite
  what is there. An obligation can be open in the code and closed in the record.
- **Source:** `2026-10-28-obligation-restated-open-though-accepted-text-fixed-it`. N-2 asked for a content-hash rule
  the accepted annex already fixed.

## Carried obligations

Register sentences that name the package ("Carried to <package>", "<package> validates …").

- **Author:** run `grep -n "<package>" docs/plans/agentic-research-system/03-decisions-and-open-questions.md` and
  enter every such sentence in the obligation register with a keep or depart disposition (`writing-plans-extras`,
  "Forward-Obligation Scan" step 7). A forward obligation in the owner register is part of the next package's
  specification.
- **Reviewer:** run the same command and check that the design cites every register sentence naming its package, each
  with a keep or depart disposition.
- **Source:** `2026-10-27-note-departed-from-a-carried-owner-item-silently`.

## Shared locations

A location that several packages read or write.

- **Author:** give it its path at its first mention, or a row in the plan's table of paths.
- **Reviewer:** flag every shared location used without a path. An unnamed shared location is an interface each
  package will name differently.
- **Source:** `2026-10-28-shared-location-named-but-never-defined`. 06v named "the W9 evidence area" six times with no
  path.
