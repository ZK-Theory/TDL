# RM-02: Research Methods Pack v1 Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. The pack assets are
> *procedural memory* under W3 §13.2 — treat their metadata fields as
> contract-bound, not decorative. The paper being distilled is
> `TDA-Research/01-Literature/Research Papers/Gemini For Research.md`
> (Woodruff et al.), SHA-256
> `43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24`; cite it by
> section in each asset's lineage field, and **verify each cited section exists
> before writing the citation** — revision 1 cited a §2.5 the document does not
> contain.

**Status:** REVISED 2026-07-29 (revision 2). The adversarial review returned
`reject` on revision 1 for one Critical (C-2, an impossible self-referential
asset hash) and three Majors (M-3 lifecycle authority, M-10 sidecar
recoverability, M-11 unsupported citations). Dispatch blocked on **G-RM-3**
(fresh review of the revised suite). Asset *acceptance* additionally blocked on
**G-RM-4**.
**Goal:** Deliver five provider-neutral method assets with a schema-validated
manifest, an append-only revision history, checkout-stable identity, fail-closed
loading, and binding tests, such that RM-03's exporter can select assets by ID
with verified identity and authorized review states.
**Owner authorization:** P-044 (accepted 2026-07-28; G-RM-3 and plan-specific
dependencies remain open). Asset content acceptance is G-RM-4.

## What changed in revision 2, and why

| Revision 1 | Revision 2 | Driver |
|---|---|---|
| Asset frontmatter "mirrors its manifest entry"; contract test asserts "same ID, version, hash" | Frontmatter repeats non-hash fields only and **never carries its own content hash** | **C-2**: a file's own SHA-256 cannot live inside the bytes it digests. Writing `h` changes the bytes; rewriting changes them again. The task was unsatisfiable except by finding a SHA-256 fixed point |
| Raw checkout-byte hashing of tracked Markdown | Git-blob identity (or a declared LF-canonical byte hash), stated explicitly | **M-3**: raw checkout bytes are not stable across Windows/EOL settings, so the same asset hashes differently on different machines |
| Loader compares the current manifest against itself | Append-only **revision history** persists prior identities | **M-3**: a loader seeing only the current manifest cannot detect an in-place same-version replacement — every listed test would pass while a reviewed asset's bytes changed |
| `owner_acceptance` written directly into YAML | Lifecycle state resolves against an **exact external accepted-decision reference** | **M-3**: a self-written YAML field records an assertion, not an acceptance. Any agent could write it |
| W3 §13.2 metadata partially rendered | Adds `permissions` and `observer_overlays` | **M-3**: both are required by W3 §13.2 and were absent |
| De-identification sidecar = `{stripped, mapping_sha256}` | Sidecar is an immutable object with ID, revision, hash, subject set, transform version, sensitivity/retention class, authorized consumers | **M-10**: a digest alone neither locates nor authorizes the mapping, so re-identification was impossible and two same-shaped briefs could join the wrong mapping |
| "minimal-instance-first" attributed to the paper; theorem retrieval to §2.5 | Minimal-instance-first demoted to a labelled ARS-added heuristic; theorem retrieval cited to §§2.2-2.3 | **M-11**: the pinned paper supports neither attribution |
| `P-044 (pending)` | `accepted 2026-07-28` | **m-1** |
| O-RM-10 "may still be active" | Registry expansion is outside this plan's accepted file map | **m-2** |
| "Full quality gates" | Exact command set below | **m-3** |

## Global constraints

- All standing constraints of rm-00 §5 apply.
- Branch `pipe/rm-02-methods-pack` from approved `main`. No dependency on 06h or
  RM-01; do not rebase onto their branches. Copy `.env` into the worktree.
- **Provider-neutral rule (O-RM-14):** no provider name in any file name,
  `$id`, field name, or asset body outside the lineage citation of the source
  paper. The adversarial reviewer is instructed to grep the diff for provider
  names as a review step.
- Do not modify `.research-system/packs/core-assurance.yaml` (W5 assurance
  packs are a different mechanism; methods assets live in their own root
  deliberately, to avoid coupling).
- **Modify: none.** If loading appears to require touching
  `schema_registry.py`, stop Partial: **registry expansion is outside this
  plan's accepted file map and requires a reviewed cross-family plan** (06h
  owns the only sanctioned registry edit, under G-RM-9).

## File map

**Create:**

~~~text
.research-system/methods/methods-pack.yaml                            # manifest (current state)
.research-system/methods/methods-pack-revisions.yaml                  # append-only revision history
.research-system/methods/assets/adversarial-review-protocol.md
.research-system/methods/assets/counterexample-search-brief.md
.research-system/methods/assets/context-deidentification-transform.md
.research-system/methods/assets/theorem-retrieval-brief.md
.research-system/methods/assets/decomposition-scaffolding-template.md
.research-system/schemas/methods/methods-pack-manifest.schema.json    # $id: ars://methods/pack-manifest
.research-system/schemas/methods/methods-pack-revisions.schema.json   # $id: ars://methods/pack-revisions
research_system/methods/__init__.py
research_system/methods/pack.py                                       # loader + verification
tests/research_system/contracts/test_methods_pack_contract.py
~~~

## Architecture

Assets are Markdown files with YAML frontmatter under
`.research-system/methods/assets/`. Two manifests bind them:

- **`methods-pack.yaml`** — current state: for each asset, its identity,
  W3 §13.2 metadata and lifecycle state.
- **`methods-pack-revisions.yaml`** — append-only history: every identity an
  asset has ever had, with the revision that introduced it. **This is what
  makes tamper detection possible.** Without it, a same-version byte
  replacement leaves a perfectly self-consistent current manifest.

**Identity is external and checkout-stable (M-3).** The recorded identity is the
Git blob SHA-1 of the tracked file (`git hash-object --path=<path> <path>`,
which is also what the repo's input-provenance manifests use), *or* a SHA-256
over LF-canonicalized bytes if the implementer prefers — the choice is recorded
in the manifest as a `identity_scheme` field and tested both ways. **No asset
ever records its own identity in its own frontmatter (C-2).** Frontmatter
repeats `asset_id`, `name`, `version`, lineage and applicability metadata; the
external manifest alone records identity, and the binding test compares all
duplicated non-hash fields while recomputing the external identity
independently.

**Lifecycle transitions are externally authorized (M-3).** `review_state` may
only be `accepted` when `owner_acceptance` names an exact external accepted
decision (register entry ID plus its blob identity), and the loader resolves
that reference rather than trusting the field. A hand-written
`owner_acceptance` that resolves to nothing is rejected.

Nothing in this plan touches the event ledger, CLI, or eval corpus.

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R2-1 | W3 §13.2 | Each asset records canonical name, version, external identity, source path, applicability trigger, runtime/provider compatibility (`any`), dependencies, supersession, review state, **permissions**, **applicable observer overlays** | Manifest schema required fields; Task 1 |
| R2-2 | W3 §13.1 | Lifecycle `candidate -> reviewed -> accepted`; assets ship as `candidate`; every other transition enumerated as legal or forbidden and tested | Task 2, Task 3 |
| R2-3 | Paper §§2.1, 3.2 | Adversarial review protocol = 3 stages: initial review → self-critique of findings for hallucinated objections → iterative refinement; findings typed, each bound to a location in the subject | Task 2 asset 1 |
| R2-4 | Paper §9.2 | Counterexample brief mandates neutral prove-or-refute framing (anti-confirmation-bias) | Task 2 asset 2. **"Minimal-instance-first" is removed as a sourced requirement** (M-11); it may appear only as an explicitly labelled ARS-added heuristic |
| R2-5 | Paper §2.7 + W3 provenance | De-identification transform strips open-problem/conjecture framing and source identity; an **immutable ARS-side sidecar object** records what was stripped, with identity and authorization, so the import can be re-identified | Task 2 asset 3; interface consumed by RM-03 |
| R2-6 | Paper §§2.2-2.3 | Theorem-retrieval brief requires the operator to externally verify any retrieved statement before it may enter an import as verified; unverified retrievals import as leads only | Task 2 asset 4; enforced by RM-03's separate attributed verification record |
| R2-7 | Paper §2.1 | Decomposition template: scaffold → verifiable sub-lemmas → per-step error-correction loop | Task 2 asset 5 |
| R2-8 | D-3 / O-RM-14 | STEM-generic bodies; TDA appears only in each asset's single worked example, clearly marked | Task 2; review question |
| R2-9 | W2 discipline + M-3 | Identity history is append-only; a reviewed version's identity is never replaced in place | Task 1 revision-history schema; Task 3 negative controls |
| R2-10 | M-3 | Lifecycle state resolves against an exact external accepted-decision reference, never a self-written field | Task 1 loader rule; Task 3 forged-acceptance control |
| R2-11 | M-3 | Identity must be stable across checkouts and EOL settings | `identity_scheme`; Task 3 EOL-variant control |

## Research assurance requirements

- **Lanes:** Output/Provenance. No mathematical, statistical, topological or
  representation logic.
- **Machine-checkable claims:** manifest validates against
  `ars://methods/pack-manifest` and the history against
  `ars://methods/pack-revisions`; every asset path resolves; every recorded
  identity matches an independently recomputed one under the declared
  `identity_scheme`; every review state is in the closed lifecycle set; every
  `accepted` state resolves to an external decision reference; the loader
  rejects — fail-closed, with typed errors — a missing file, identity mismatch,
  unknown state, duplicate ID, unregistered asset ID, same-version identity
  replacement, removed history entry, forbidden transition, forged acceptance
  reference, and any manifest shape carrying a self-hash field.
- **Human-review-only:** are the asset bodies faithful, usable distillations of
  the cited sections? Is anything provider-specific? Could a non-TDA researcher
  apply them? (G-RM-4 questions for Stephen plus the reviewer.)
- **Partial criteria:** schema-registry modification appears necessary; any
  coupling to W5 assurance packs; asset content requiring provider-specific
  instructions; the sidecar interface cannot be specified without an ARS-side
  object store this plan does not own (report; do not improvise storage).

## Task 1: Manifest and revision-history schemas + failing contract test

- [ ] **Step 1 — Failing test.** `test_methods_pack_contract.py`: load via
  `research_system.methods.pack.load_methods_pack(root)`; assert five assets,
  all W3 §13.2 metadata present, identities verified against independent
  recomputation, history consistent. Red — nothing exists yet.
- [ ] **Step 2 — Manifest schema.** `methods-pack-manifest.schema.json`
  (`$id: ars://methods/pack-manifest`, draft 2020-12, matching the style of
  `.research-system/schemas/**`, `additionalProperties: false` throughout).
  Required per asset entry: `asset_id`, `name`, `version`, `path`,
  `identity_scheme` (enum `git_blob_sha1 | lf_canonical_sha256`), `identity`,
  `applicability_trigger`, `compatibility` (const `any`), `dependencies`,
  `permissions`, `observer_overlays`, `review_state`
  (enum `candidate|reviewed|accepted|rejected|stale|superseded|retired`),
  `supersedes` (nullable), `lineage` (`{source, source_sha256, sections[]}`),
  `owner_acceptance` (nullable object `{decision_id, decision_blob,
  accepted_on}`; required non-null **iff** `review_state: accepted`).
  **The schema must forbid any per-asset property that would hold the asset's
  own content hash** — this is C-2's structural fix, not a convention.
- [ ] **Step 3 — Revision-history schema.** `methods-pack-revisions.schema.json`
  (`$id: ars://methods/pack-revisions`): an append-only array of
  `{asset_id, version, identity, identity_scheme, recorded_at, revision_reason,
  supersedes_identity (nullable)}`. Entries are never edited or removed.
- [ ] **Step 4 — Loader.** `pack.py`: a pure function with no ledger
  interaction — parse both YAML files → validate each against its schema →
  recompute every asset identity under its declared scheme → check the current
  identity against the history (a `(asset_id, version)` pair whose identity
  differs from its history entry is a same-version replacement and is rejected)
  → resolve every `owner_acceptance` reference → return frozen dataclasses.
  Typed errors per `research_system.errors` conventions.
- [ ] **Step 5 — Green.**

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/contracts/test_methods_pack_contract.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/methods tests/research_system/contracts/test_methods_pack_contract.py
~~~

- [ ] **Step 6 — Commit.** `[PIPELINE] P00: methods-pack manifest, revision history, and fail-closed loader`.

## Task 2: Author the five assets (as `candidate`)

Each asset: YAML frontmatter repeating `asset_id`, `name`, `version`, lineage
and applicability metadata — **and never its own content hash (C-2)**. Body
sections: **Purpose / When to select (applicability) / Protocol (numbered,
imperative, operator-executable) / Output the operator must bring back (naming
the RM-03 import type it feeds) / Failure modes to watch (paper §9.2) / Worked
example (marked as an example; may be TDA) / Lineage**.

Before writing any lineage citation, open the pinned paper and confirm the
section exists and says what the citation claims. Revision 1 failed this on two
of five assets.

- [ ] Asset 1 `adversarial-review-protocol` — feeds `ReviewFindingSet`.
      Protocol per R2-3 (paper §§2.1, 3.2); instructs the external session to
      grade its own findings for hallucination before finalizing; requires each
      finding to carry subject location, severity, and a falsifiable statement
      of the defect.
- [ ] Asset 2 `counterexample-search-brief` — feeds `CounterexampleCandidate`.
      Neutral prove-or-refute framing per R2-4 (paper §9.2); requires an
      explicit instance, the violated statement, and a checkable verification
      recipe. **If minimal-instance-first is retained, it appears under an
      explicit "ARS-added heuristic (not from the source paper)" heading.**
      Note in the asset that the recipe is *recorded, not executed* — execution
      is deferred under G-RM-11.
- [ ] Asset 3 `context-deidentification-transform` — a *compilation* procedure
      applied when building a brief: what to strip, and the **sidecar object**
      it must produce. Specify the sidecar as an immutable ARS-side record with
      `{sidecar_id, revision, content_hash, subject_set, transform_version,
      sensitivity_class, retention_class, authorized_consumers}`. The
      operator-facing brief carries only the opaque `sidecar_id` and hash —
      never the mapping. Per R2-5 and O-RM-21.
- [ ] Asset 4 `theorem-retrieval-brief` — feeds `TheoremCitation`. Per R2-6
      (paper §§2.2-2.3): the operator externally verifies exact statements, and
      that verification is a **separate attributed record**, not a value the
      returned document asserts about itself. Distinguishes statement retrieval
      from applicability argument.
- [ ] Asset 5 `decomposition-scaffolding-template` — feeds `ExploratoryMemo`.
      Per R2-7 (paper §2.1).
- [ ] Extend the contract test: per-asset frontmatter/manifest consistency on
      **all duplicated non-hash fields**, required body sections present, and
      every lineage `sections[]` entry resolvable in the pinned source.
- [ ] Commit: `[PIPELINE] P00: five candidate method assets with verified lineage`.

## Task 3: Negative controls (each red first)

- [ ] (a) Tampered asset byte → identity mismatch rejection.
- [ ] (b) `review_state: accepted` with null `owner_acceptance` → schema
      rejection.
- [ ] (c) `owner_acceptance` naming a decision that does not resolve → loader
      rejection (**forged acceptance**, M-3).
- [ ] (d) Unknown `asset_id` requested from the loader → typed error.
- [ ] (e) Duplicate `asset_id` → rejection.
- [ ] (f) **Same-version identity replacement** (version unchanged, bytes and
      identity changed) → rejection via the revision history.
- [ ] (g) **History entry removed** → rejection (append-only violation).
- [ ] (h) **Self-hash shape:** a manifest or frontmatter carrying a field that
      holds the asset's own content hash → schema rejection. This is C-2's
      negative control and must exist even though nothing produces such a file.
- [ ] (i) **EOL variant:** the same asset checked out with CRLF endings yields
      the same identity under the declared scheme.
- [ ] (j) Every **forbidden lifecycle transition** enumerated in Task 1 →
      rejection; every legal one → accepted. Prove all transitions, not one
      example.
- [ ] Commit: `[PIPELINE] P00: methods-pack negative controls`.

## Close-out

- Exact verification commands (m-3):

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/contracts/test_methods_pack_contract.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/methods tests/research_system/contracts
~~~

  Broader validation triggers only if the loader is later imported by another
  module — it is not, in this plan.
- PR with the three commits; CodeRabbit concludes; merge per house rule.
- Present assets to Stephen for **G-RM-4**. State flips land as a follow-up
  commit that appends to the revision history and updates `review_state` and
  `owner_acceptance` — never as byte edits to accepted asset bodies.
- README lane row update (O-RM-18); vault `[PIPELINE]` entry in
  Pipeline-Overview naming the pack root, the identity scheme, and the
  lifecycle authorization rule.
