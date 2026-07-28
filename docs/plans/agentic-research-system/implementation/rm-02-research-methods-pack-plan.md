# RM-02: Research Methods Pack v1 Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. The pack assets are
> *procedural memory* under W3 §13.2 — treat their metadata fields as
> contract-bound, not decorative. The paper being distilled is
> `TDA-Research/01-Literature/Research Papers/Gemini For Research.md`
> (Woodruff et al.); cite it by section in each asset's lineage field.

**Status:** PROPOSED — dispatch blocked on gates G-RM-2 and G-RM-3 (rm-00 §3).
Asset *acceptance* additionally blocked on G-RM-4.
**Goal:** Deliver five provider-neutral method assets with a schema-validated
manifest, registry loading, and binding tests, such that RM-03's exporter can
select assets by ID with verified hashes and review states.
**Architecture:** Assets are Markdown files with YAML frontmatter under
`.research-system/methods/`. A single manifest binds IDs to paths, SHA-256
hashes, versions, W3 §13.2 metadata, and lifecycle state. A JSON Schema
validates the manifest; a loader in `research_system` resolves and re-hashes
assets fail-closed. Nothing in this plan touches the event ledger, CLI, or
eval corpus — it is schemas, assets, one loader module, and tests.
**Tech stack:** Python 3.13, jsonschema, PyYAML, pytest, ruff.
**Owner authorization:** P-044 (pending). Asset content acceptance is G-RM-4.

## Global constraints

- All standing constraints of rm-00 §5 apply.
- Branch `pipe/rm-02-methods-pack` from approved `main`. No dependency on
  RM-01; do not rebase onto RM-01 branches.
- **Provider-neutral rule (O-RM-14):** no provider name in any file name,
  `$id`, field name, or asset body outside the lineage citation of the source
  paper. The adversarial reviewer is instructed to grep the diff for provider
  names as a review step.
- Do not modify `.research-system/packs/core-assurance.yaml` (W5 assurance
  packs are a different mechanism; methods assets deliberately live in their
  own root to avoid coupling).

## File map

**Create:**

~~~text
.research-system/methods/methods-pack.yaml                       # manifest
.research-system/methods/assets/adversarial-review-protocol.md
.research-system/methods/assets/counterexample-search-brief.md
.research-system/methods/assets/context-deidentification-transform.md
.research-system/methods/assets/theorem-retrieval-brief.md
.research-system/methods/assets/decomposition-scaffolding-template.md
.research-system/schemas/methods/methods-pack-manifest.schema.json   # $id: ars://methods/pack-manifest
research_system/methods/__init__.py
research_system/methods/pack.py                                  # loader + verification
tests/research_system/contracts/test_methods_pack_contract.py
~~~

**Modify:** none. If loading requires touching `schema_registry.py` bundling
logic, stop Partial (O-RM-10 may still be active; and registry expansion is an
RM-03 concern).

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R2-1 | W3 §13.2 | Each asset records canonical name, version+hash, source path, applicability trigger, runtime/provider compatibility (`any`), dependencies, supersession, review state | Manifest schema required fields; Task 1 |
| R2-2 | W3 §13.1 | Lifecycle `candidate -> reviewed -> accepted`; assets ship as `candidate` | Task 2; G-RM-4 flips states via manifest revision, never by editing accepted asset bytes |
| R2-3 | Paper §2.1/§3.2 | Adversarial review protocol = 3 stages: initial review → self-critique of findings for hallucinated objections → iterative refinement; findings typed, each bound to a location in the subject | Task 2 asset 1 |
| R2-4 | Paper §2.3/§9.2 | Counterexample brief mandates neutral prove-or-refute framing (anti-confirmation-bias) and minimal-instance-first search | Task 2 asset 2 |
| R2-5 | Paper §2.7 | De-identification transform strips open-problem/conjecture framing and source identity; a provenance sidecar records exactly what was stripped so the import can be re-identified | Task 2 asset 3 |
| R2-6 | Paper §2.5 | Theorem-retrieval brief requires the operator to externally verify any retrieved theorem statement before it may enter an import as `verified`; unverified retrievals import only as `unverified` leads | Task 2 asset 4; enforced by RM-03 `TheoremCitation` enum |
| R2-7 | Paper §2.1 | Decomposition template: scaffold → verifiable sub-lemmas → per-step error-correction loop | Task 2 asset 5 |
| R2-8 | D-3 / O-RM-14 | STEM-generic bodies; TDA appears only in each asset's single worked example, clearly marked as example | Task 2; review question |
| R2-9 | W2 discipline | Manifest is append-only in spirit: version bumps supersede; hashes never edited in place for an already-reviewed version | Task 1 schema (`supersedes` field) + Task 3 negative control |

## Research assurance requirements

- **Lanes:** Output/Provenance. No math/stats logic.
- **Machine-checkable claims:** manifest validates against
  `ars://methods/pack-manifest`; every asset path resolves; every recorded
  SHA-256 matches recomputed file bytes; every review state is in the closed
  lifecycle set; loader rejects (with typed errors, fail-closed) a missing
  file, hash mismatch, unknown state, duplicate ID, or unregistered asset ID.
- **Human-review-only:** are the asset bodies faithful, usable distillations of
  the cited paper sections? Is anything provider-specific? Are the prompts
  written so a non-TDA researcher could apply them? (These are G-RM-4
  questions for Stephen plus the adversarial reviewer.)
- **Partial criteria:** schema-registry modification needed; any coupling to
  W5 assurance packs; asset content requiring provider-specific instructions.

## Task 1: Manifest schema + failing contract test

- [ ] **Step 1 — Failing test.** `test_methods_pack_contract.py`: load the
  manifest via `research_system.methods.pack.load_methods_pack(root)`;
  assert five assets, all metadata fields present, hashes verified. Red
  because nothing exists yet.
- [ ] **Step 2 — Schema.** `methods-pack-manifest.schema.json`
  (`$id: ars://methods/pack-manifest`, draft 2020-12, matching the style of
  the existing `.research-system/schemas/**` families;
  `additionalProperties: false` throughout). Required per asset entry:
  `asset_id`, `name`, `version`, `path`, `sha256`, `applicability_trigger`,
  `compatibility` (const `any`), `dependencies`, `review_state`
  (enum `candidate|reviewed|accepted|rejected|stale|superseded|retired`),
  `supersedes` (nullable), `lineage` (object: `source`, `sections` array),
  `owner_acceptance` (nullable: date + reference, required non-null iff
  `review_state: accepted`).
- [ ] **Step 3 — Loader.** `pack.py`: pure function, no ledger interaction:
  parse YAML → validate against schema (reusing the existing registry *read*
  path if it can load a schema by path without modification; else validate
  directly with jsonschema) → re-hash every asset file → return frozen
  dataclasses. Typed errors from `research_system.errors` conventions.
- [ ] **Step 4 — Green.**

~~~powershell
C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -q tests/research_system/contracts/test_methods_pack_contract.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/methods tests/research_system/contracts/test_methods_pack_contract.py
~~~

- [ ] **Step 5 — Commit.** `[PIPELINE] P00: methods-pack manifest schema and fail-closed loader`.

## Task 2: Author the five assets (as `candidate`)

Each asset: YAML frontmatter mirroring its manifest entry; body sections
**Purpose / When to select (applicability) / Protocol (numbered, imperative,
operator-executable) / Output the operator must bring back (naming the RM-03
import type it feeds) / Failure modes to watch (from paper §9.2) / Worked
example (marked, may be TDA) / Lineage**.

- [ ] Asset 1 `adversarial-review-protocol` — feeds `ReviewFindingSet`.
      Protocol per R2-3; instructs the external session to grade its own
      findings for hallucination before finalizing; requires each finding to
      carry subject location + severity + falsifiable statement of the defect.
- [ ] Asset 2 `counterexample-search-brief` — feeds `CounterexampleCandidate`.
      Neutral prove-or-refute framing per R2-4; requires explicit instance,
      violated statement, and a checkable verification recipe (feeds RM-04).
- [ ] Asset 3 `context-deidentification-transform` — a *compilation* procedure
      applied when building a brief: what to strip, what the sidecar records
      (stripped identifiers, original framing, mapping), re-identification on
      import. Per R2-5.
- [ ] Asset 4 `theorem-retrieval-brief` — feeds `TheoremCitation`. Per R2-6:
      external verification of exact statements before `verified` status;
      distinguishes statement retrieval from applicability argument.
- [ ] Asset 5 `decomposition-scaffolding-template` — feeds `ExploratoryMemo`.
      Per R2-7.
- [ ] Extend the contract test: per-asset frontmatter/manifest consistency
  (same ID, version, hash), and the required body sections present.
- [ ] Commit: `[PIPELINE] P00: five candidate method assets with lineage`.

## Task 3: Negative controls

- [ ] Add red-then-green tests: (a) tampered asset byte → hash mismatch
  rejection; (b) manifest entry with `review_state: accepted` but null
  `owner_acceptance` → schema rejection; (c) unknown `asset_id` requested from
  the loader → typed error; (d) duplicate `asset_id` → rejection; (e) a
  *reviewed-version hash edit* (same version, new hash) → rejection by a
  loader rule comparing against `supersedes` discipline (version must bump).
- [ ] Commit: `[PIPELINE] P00: methods-pack negative controls`.

## Close-out

- PR with the three commits; CodeRabbit concludes; merge per house rule.
- Present assets to Stephen for G-RM-4 review → state flips land as a
  follow-up manifest-revision commit (`review_state`, `owner_acceptance`),
  not byte edits to asset bodies.
- README lane row update (O-RM-18); vault `[PIPELINE]` entry in
  Pipeline-Overview naming the pack root and lifecycle rule.
