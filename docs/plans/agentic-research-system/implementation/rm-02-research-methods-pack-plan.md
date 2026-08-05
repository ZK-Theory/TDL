# RM-02: Research Methods Pack v1 Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. The assets are W3
> section 13.2 procedural memory. Verify every cited section in the pinned
> Woodruff et al. source before writing it.

**Integrated owner:** WP6.4 / KAN-57 under P-047. The pack is part of the
owner-operated external-session capability, not a separately completed lane and
not WP6.3 assurance-pack content.

**Status:** REVISED 2026-08-05. G-RM-3 is already closed for the accepted plan
bytes. Candidate implementation remains absent; canonical asset use still
requires the accepted 06i path and exact-scope G-RM-4. Candidate authorship is
file-level independent of 06h/06i and is no longer blocked by G-RM-3.
Canonical acceptance and export require accepted 06i plus G-RM-4.

**Goal:** deliver five provider-neutral candidate assets with stable external
identity, complete W3 metadata, an independently Git-anchored append history,
and fail-closed current-byte loading. The repository pack never writes its own
acceptance.

## Architecture

Three distinct objects must not be collapsed:

1. `methods-pack.yaml` describes current candidate bytes and W3 metadata.
2. `methods-pack-revisions.yaml` is the proposed append chain.
3. an **independently supplied history anchor** establishes what the accepted
   base actually contained.

The current manifest/history pair cannot prove append-only behavior by agreeing
with each other. The review/CI history gate runs in a history-bearing clone and
receives the base ref from the PR/acceptance runner, not from either candidate
file. It resolves:

~~~text
repository identity, base commit, current commit, history path,
base history Git blob or proved path absence, current history Git blob,
merge-base ancestry, prior accepted asset identities
~~~

For genesis, the independently supplied base commit must prove that the history
path is absent. For later revisions, it must resolve the exact prior accepted
history blob and require the current history to retain that complete prefix in
order. The gate rejects a candidate-selected base ref.

The runtime loader verifies current files and identity but does **not** claim
Git history authority. Canonical acceptance occurs after 06i: each asset is
registered as an artefact at forced `candidate`, then Stephen's G-RM-4 action
uses the production `SetArtefactUseAuthority` path. RM-03 resolves that
replay-derived state through `ArtefactUseResolver`. No
`methods_asset_owner_acceptance` body is written into YAML or directly into the
object store.

## Global constraints

- Branch `pipe/rm-02-methods-pack` from approved main; disjoint from 06h.
- Provider-neutral production names; source paper appears only in lineage.
- Do not modify core schemas, schema registry, W5 packs, ledger, CLI, or evals.
- Assets ship candidate. The RM-02 Worker cannot perform G-RM-4.

## File map

~~~text
.research-system/methods/methods-pack.yaml
.research-system/methods/methods-pack-revisions.yaml
.research-system/methods/assets/adversarial-review-protocol.md
.research-system/methods/assets/counterexample-search-brief.md
.research-system/methods/assets/context-deidentification-transform.md
.research-system/methods/assets/theorem-retrieval-brief.md
.research-system/methods/assets/decomposition-scaffolding-template.md
.research-system/schemas/methods/methods-pack-manifest.schema.json
.research-system/schemas/methods/methods-pack-revisions.schema.json
research_system/methods/__init__.py
research_system/methods/pack.py
tests/research_system/contracts/test_methods_pack_contract.py
tests/research_system/contracts/test_methods_pack_history.py
~~~

`test_methods_pack_history.py` is the history-bearing Git gate. It accepts base
and subject commits from the gate runner. The candidate files do not provide
them.

## Data contracts

Each manifest asset requires:

~~~text
asset_id, name, version, path,
identity_scheme: git_blob_sha1 | lf_canonical_sha256,
identity, applicability_trigger, compatibility: any,
dependencies, permissions, observer_overlays,
declared_review_state: candidate | reviewed,
supersedes, lineage
~~~

There is no `accepted` repository state and no `owner_acceptance` body. The
manifest is descriptive candidate metadata; replay-derived 06i authority is
the only acceptance-for-use source.

The revision file contains ordered entries:

~~~text
asset_id, version, identity_scheme, identity, recorded_at,
revision_reason, supersedes_identity, previous_history_blob
~~~

`previous_history_blob` strengthens the chain but is not trusted by itself. The
independent base-ref gate resolves and compares it.

No asset stores its own hash in frontmatter. Identity is Git-blob SHA-1 or
explicit LF-canonical SHA-256, declared once and independently recomputed.

The de-identification sidecar specification contains:

~~~text
sidecar_artefact_id, revision, content_sha256, subject_set,
transform_version, sensitivity_class, retention_class
~~~

It contains no `authorized_consumers`. Access is independently expressed by
06i replay-derived authority for `consumer_kind: sensitive_sidecar`. The
operator brief receives only opaque ID/revision/hash.

## Obligations

| ID | Obligation | Enforcement |
|---|---|---|
| R2-1 | complete W3 section 13.2 fields | schema/loader |
| R2-2 | candidate/reviewed local metadata never equals acceptance | schema forbids accepted; 06i/G-RM-4 |
| R2-3 | three-stage adversarial review protocol | asset 1; source sections 2.1/3.2 |
| R2-4 | neutral prove-or-refute counterexample framing | asset 2; source 9.2; minimal-first labelled ARS heuristic only |
| R2-5 | reversible de-identification with independent access | asset 3 sidecar + 06i |
| R2-6 | theorem retrieval and external verification are separate | asset 4; source 2.2-2.3 |
| R2-7 | decomposition scaffold | asset 5; source 2.1 |
| R2-8 | provider-neutral bodies; TDA example only | content review |
| R2-9 | coordinated asset/manifest/history rewrite still fails | independent Git anchor gate |
| R2-10 | acceptance not self-written | schema + 06i |
| R2-11 | checkout-stable identity | both schemes/EOL controls |

## Research assurance

- **Lanes:** Output/Provenance.
- **Machine-checkable:** schema closure; exact current identities; independently
  supplied base/subject ancestry; prior history prefix; Git blobs; no
  candidate-selected base; no self-hash; no accepted local state; sidecar
  identity; lineage section existence.
- **Human review:** source fidelity, cross-domain usability, permissions,
  observer overlays, and G-RM-4 asset choice.
- **Partial:** history-bearing base unavailable; prior accepted blob ambiguous;
  schema-registry/core change required; sidecar requires self-declared access;
  provider-specific content.

## Task 1: schemas, loader and history gate

1. Write closed manifest/revision schemas.
2. Implement `load_methods_pack` to validate current YAML and asset bytes,
   recompute identity, reject duplicates/unknowns/self-hash shapes, and return
   frozen candidate records. It does not return “accepted”.
3. Implement the history gate using exact base/subject refs supplied by the
   caller. Verify ancestry, base blob/absence, current blob, retained ordered
   prefix, per-entry identity, and previous-blob links.
4. Prove the gate cannot take base/expected values from candidate YAML.

## Task 2: author five candidate assets

Every asset contains Purpose, Applicability, numbered operator protocol,
required RM-03 output, failure modes, marked worked example, and verified
lineage. Frontmatter repeats only non-hash binding fields.

- adversarial review protocol -> `ReviewFindingSet`;
- counterexample search -> `CounterexampleCandidate`, recipe recorded only;
- context de-identification -> sidecar contract above;
- theorem retrieval -> `TheoremCitation`, operator verification separate;
- decomposition scaffold -> `ExploratoryMemo`.

## Task 3: required controls

- tampered bytes;
- duplicate/unknown asset;
- same-version replacement;
- deletion/reorder/duplication/extra history entry;
- candidate-selected foreign base;
- coordinated asset + manifest + complete current-history replacement;
- wrong/non-ancestor base, wrong prior blob, changed previous link;
- self-hash field;
- CRLF/LF checkout equivalence;
- local `accepted`/owner-acceptance field;
- sidecar self-declared authorized consumers;
- nonexistent lineage section.

The coordinated rewrite must fail even though the two current YAML files are
mutually consistent.

## Close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/contracts/test_methods_pack_contract.py tests/research_system/contracts/test_methods_pack_history.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system/methods tests/research_system/contracts/test_methods_pack_contract.py tests/research_system/contracts/test_methods_pack_history.py
~~~

Present candidate assets to Stephen only after 06i provides the production
registration/use-authority writer. G-RM-4 follow-up registers exact asset
bytes and transitions accepted scope; it does not edit asset bodies or claim
that `methods-pack.yaml` is authority. Update `implementation/README.md` and
Pipeline-Overview with the identity scheme and exact Git anchor.
