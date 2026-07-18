# Adversarial WP6.3 TDL-private assurance-contract review

**Review date:** 2026-07-18<br>
**Reviewer posture:** distinct-authority, independent, adversarial; not the author<br>
**Subject commit:** `2ae607803b4cdaef677c2699439e1e1b876856e8`<br>
**Subject parent / `origin/main`:** `4e6fd0cb26c04ff9707c3183f663461d752b53b9`<br>
**Subject branch / PR:** `pipe/ars-wp6-3-tda-pack` / draft PR #123<br>
**Review branch:** `review/ars-wp6-3-tda-pack-r1`<br>
**Approved normative WP6 revision:** `fe5f1d40bc8f05f061317c677b5891cea0711249`<br>
**Review scope:** committed bytes only; four added subject files; no future pack implementation<br>
**Verdict:** `rework_required`<br>
**Finding count:** **1 Critical, 4 Major, 0 Minor**

## 1. Executive verdict

The proposed future path `.research-system/packs/tdl-private-assurance.yaml` is
currently collision-free and follows the existing lower-kebab-case pack-path
convention. The label `TDL_private` is the accepted W5 name for the first TDA pack
(`W5:417-425`), and version
`1.0.0` is repository-conventional. Those three choices can be retained.

The complete proposed identity is **not safe to accept yet**. The generic schema ID
`ars://assurance/assurance-pack` names a schema that hard-codes one TDL-private pack,
while the schema omits W5's canonical `asp_...` assurance-pack object identity. More
importantly, a candidate can claim `accepted` using invented actor labels, arbitrary
and mutually inconsistent review/acceptance hashes, an unbound content hash,
foreign/aliased references, widened consumers, weak free-text restrictions, and an
invalid time order, and still pass the only semantic validator. That validator exists
only as a private helper in the test module, not at a producing or consuming boundary.

The subject correctly remains prospective: its contract status is
`pending_independent_review`, the future pack is absent, and the four-file diff makes
no research result, claim, live call, migration, eligibility, Gate 5, P0, WP6.4, or
Gate 6 mutation. Those hard stops do not compensate for the contract defects. The
upstream contract/schema/test set needs a new exact revision and fresh review before
Stephen can accept its identity or a distinct future producer may author the pack.

Direct controlling evidence was accessible. This review is therefore **not Partial**.

## 2. Revision, authority, and scope evidence

The checkout was initially detached. Detached `HEAD` and
`refs/heads/review/ars-wp6-3-tda-pack-r1` both resolved to the exact subject commit;
one deterministic switch attached the worktree to the assigned branch. The resolved
worktree is the declared writable root. `origin/main` and the merge base both resolved
to the stated parent, and the pre-review tree was clean.

Exact evidence-path aliases used below are:

- `W5` = `docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md`
- `WP6` = commit `fe5f1d40bc8f05f061317c677b5891cea0711249` path
  `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md`
- `Decisions` = `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
- `R5` = `docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r5-review-2026-07-17.md`
- `Contract` = `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`
- `Pack schema` = `.research-system/schemas/assurance/assurance-pack.schema.json`
- `Contract schema` = `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`
- `Test` = `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py`

Authority was classified as follows:

- W5 v0.2 is accepted normative design but creates no pack or runtime
  (`W5:3-17,702-727`).
- The literal WP6 plan bytes at `fe5f1d40bc8f05f061317c677b5891cea0711249`
  were reviewed by R5 and then made
  authoritative for launch/dispatch planning by P-036
  (`Decisions:536-560`; `R5:3-10,330-342`). P-036 does not
  accept this subject contract or any future pack.
- Exact WP6.3 requires one `TDL_private` pack covering six lanes and the listed TDA/
  panel obligations with versioned references, producer-distinct scope authority,
  and standard adversarial review (`WP6:110-120`). Pack adequacy for the scientific
  lanes is human-review-only, not something a schema may self-certify (`WP6:221-257`).
- The subject contract and its proposed path/schema/version remain only proposed
  (`Contract:1-5,60-72,259-282`). `.research-system/packs/core-assurance.yaml` and
  the existing assurance-requirement schema are explicitly labelled observed
  baselines, not new normative authority (`Contract:48-59`).
- A7 clears only when the future pack itself is accepted with distinct-authority
  review (`WP6:287-325`). Contract/schema approval cannot claim
  WP6.3, WP6.4, Gate 6, or pilot credit.

## 3. Findings

### C-1 — Critical — Accepted-pack authority and content can be self-attested

1. **Claim.** The proposed schema plus its only semantic validator do not bind an
   `accepted` pack to canonical actor/relationship records, the independently accepted
   upstream contract identity, review and owner-decision records, actual pack bytes,
   coherent dates, or non-widened TDL-private consumers. Shape-valid self-attestation
   can therefore pass as accepted authority.
2. **Evidence.** The pack schema treats content, relationship, review, and decision
   hashes as syntactic hex (`Pack schema:27-40,86-137,233-259`). Its actor pattern
   accepts role-like aliases at `Pack schema:79`, unlike canonical UUID7 actor IDs in
   `.research-system/schemas/core/command.schema.json:12-13` and
   `.research-system/schemas/core/authority-grant.schema.json:10`. The only relational
   code is the private `_validate_candidate_pack` helper (`Test:283-324`). It requires
   merely four selected distinct strings and non-null hashes for `accepted`
   (`Test:296-308`); it does not resolve authority records, include the
   requirement/contract author in the full separation relation, compare decision
   hashes, recompute `pack_content_sha256`, validate permitted-consumer semantics, or
   check effective/expiry order. Repository-wide search finds no production pack
   loader, writer, CLI, or semantic-validator call.
3. **Concrete failure scenario.** Starting from the asserted-valid candidate, in-memory
   probes changed the content hash without changing bytes, supplied mutually different
   upstream/review/acceptance hashes, widened `permitted_consumers` to
   `public_template_exporter`, replaced path/data restrictions with `allow all`, made
   the requirement author equal the future producer, and made `effective_at` later than
   `expires_at`. Every candidate was accepted. A malformed `effective_at` is also
   accepted because `SchemaRegistry` does not install a JSON Schema `FormatChecker`
   (`research_system/schema_registry.py:49-70`).
4. **Impact.** Invalid acceptance, producer self-certification, and restricted-pack
   distribution widening are possible while all committed checks remain green. This
   crosses the authority and privacy boundaries and therefore meets Critical severity.
5. **Authority violated.** W5 requires immutable identity/lifecycle and producer-
   independent requirement acceptance (`W5:144-183`), canonical separation and
   independent activation (`W5:291-320`), non-self-attested review evidence
   (`W5:431-456`), non-compensable two-key validity (`W5:458-482`), and TDL-private
   consumer/publication/path/data restrictions (`W5:647-654`). P-022 makes
   independence evidence, not a role label (`Decisions:274-281`).
6. **Required disposition.** Fix in a new upstream-contract revision; do not accept this
   revision and do not author the future pack.
7. **Required interface change.** Name one production/public semantic validation seam
   under `research_system.assurance`, invoked by pack loading and acceptance. It must
   take independently frozen expected identities, resolve actor/relationship/review/
   owner-decision records, enforce every mandated distinct pair and minimum grade,
   bind all acceptance hashes to the same decision, validate time ordering, close
   permitted consumer classes against TDL-private policy, and verify pack identity from
   a defined non-self-referential canonical byte surface (prefer external Git blob plus
   SHA-256). Tests must call that public seam and perturb its producer/loader inputs,
   not post-produced dictionaries.
8. **Affected decisions/work packages.** P-022, P-023, P-029, P-036; W5 §§6, 11, 16,
   17, 24; WP6.3/A7 and downstream WP6.4/Gate 6.

### M-1 — Major — The proposed identity conflates pack name, object identity, and schema family

1. **Claim.** The path and human-facing pack name are collision-free, but the full
   identity is not repository-consistent or safely extensible.
2. **Evidence.** W5 defines canonical `assurance_pack_id  asp_...` and requires every
   object to have revision/hash/lineage (`W5:144-159`), while naming the TDA pack
   `TDL_private` at `W5:417-425`. The subject uses `pack_id: TDL_private` without an
   `assurance_pack_id` (`Pack schema:6-33`). The current ID-kind registry
   has no `assurance_pack: asp` entry (`.research-system/config/id-kind-registry.yaml:
   2-27`). The generic `$id` `ars://assurance/assurance-pack` hard-codes the TDL-private
   pack name, path, and scope (`Pack schema:3-4,27-33`) even though W5 defines TDA,
   statistical/social, and qualitative pack families (`W5:417-429`).
3. **Concrete failure scenario.** A later template-safe statistical pack either reuses
   the generic schema ID and collides with TDL-specific constants or invents a parallel
   convention. Meanwhile `TDL_private` is used as both family label and canonical
   object identity, leaving no W5 `asp_...` identity to bind revisions and decisions.
4. **Impact.** Material identity ambiguity and predictable schema-family collision as
   the accepted multi-pack design is implemented.
5. **Required disposition.** Amend before upstream acceptance.
6. **Exact change.** Retain `TDL_private` as a registered family/name and retain the
   proposed file path, but add the canonical `assurance_pack_id` dependency and its
   registry/materialization gate. Either make `ars://assurance/assurance-pack` genuinely
   generic by removing TDL-specific constants and composing a TDL-specific profile, or
   give the closed TDL schema a pack-specific ID such as
   `ars://assurance/packs/tdl-private/1.0`. Freeze the chosen ID/version/path/blob/SHA in
   the next independent review.
7. **Alternatives rejected.** The observed `core-assurance.yaml` slug is not sufficient
   authority to override accepted W5 identity semantics; the subject itself labels it
   only an observed baseline (`Contract:48-53`).
8. **Affected decisions/work packages.** P-029/P-036; W1 identity registry, W5 §§6/8/
   15, WP6.3, and future W10 pack distribution.

### M-2 — Major — Required reference, fixture, and lane-reference sets are not exact or independently bound

1. **Claim.** The contract names exact capability/skill/fixture obligations, but the
   candidate schema and validator accept missing, foreign, aliased, duplicated, swapped,
   pending, and dangling references.
2. **Evidence.** The contract lists six contract capabilities and six skill IDs
   (`Contract:200-217`) and fourteen fixture cases plus producer-seam requirements
   (`Contract:218-236`). The pack schema instead accepts at least one
   contract reference, five skills, and ten arbitrary fixture objects
   (`Pack schema:61-65,166-198,448-459`). Both reference arrays share one
   type whose `reference_kind` is merely an enum, so array kinds can be swapped. The
   asserted-valid candidate contains one invented `null-operation-contract`, only five
   skills (omitting `research-assurance-triage`), ten generic fixtures, and dangling lane
   reference `accepted-w5-v0.2`
   (`Test:63-97,178-188,228-244`). The semantic helper never checks reference or
   fixture closure (`Test:283-324`).
3. **Concrete failure scenario.** In-memory probes accepted contract/skill kind swaps,
   a duplicate `reference_id` with different version/hash, foreign lane references, and
   replacement of the contract's required capability, skill, fixture, and bound-test
   lists with a single foreign string. The contract schema also accepted a seventh
   source alias and a topology-key record whose `lane_id` was changed to `paper_claim`
   because all keys use one generic lane schema (`Contract schema:121-131,276-287`).
4. **Registry status.** All named files exist, but
   `contracts/topology-invariants/null-operation-changes-ph-input.yaml:1-3,40-48` and
   `contracts/stochastic-tests/markov-order-provenance.yaml:1-3,34-41` are still
   `pending: true`; their declared binding test files are absent. The pack schema carries
   no activation/acceptance status or exact registry resolution.
5. **Impact.** A future pack can omit required assurance mechanisms or fixtures, bind
   the wrong artifact kind/path/hash, reference an inactive contract, and still pass.
6. **Required disposition.** Fix now in the upstream contract/schema and public semantic
   seam; do not defer exact closure to future pack prose.
7. **Exact change.** Bind one independently frozen multiset of complete reference rows:
   kind, exact ID, canonical registry path, Git blob, SHA-256, activation/acceptance
   status, and allowed lane usages. Require exact equality for the six contract and six
   skill IDs; resolve every lane `governing_reference_id`; exact-set bind all fourteen
   fixtures and their attack classes. Reject missing, extra, duplicate-ID/different-body,
   alias, swap, foreign-valid, pending, stale, and coordinated expected/observed
   replacement cases.
8. **Affected decisions/work packages.** P-023/P-029; W5 §§7-8, 11, 13-15, 22; WP6.3.

### M-3 — Major — The closed six-lane schema narrows accepted W5 obligations into incomplete free-text slots

1. **Claim.** All six lane keys are present, but the closed obligation objects omit
   material W5 minima and permit one generic sentence to satisfy every field. This is an
   expressivity and reviewability failure, not a demand that schema validation replace
   human scientific judgment.
2. **Evidence.** The subject inventories at `Contract:84-170` are reproduced as strict
   objects of nonempty string arrays at `Pack schema:261-344`. The valid
   fixture supplies the same `Explicit prospective obligation.` string everywhere and
   passes (`Test:100-177,368-372`). The contract's W5 section list (`Contract:30-35`)
   omits accepted W5 §§18-23 and §28 even though the contract purports
   to govern Partial/negative restrictions, result/claim bindings, execution/failure,
   audit, fixtures, and acceptance.
3. **Concrete failure scenario.** A future pack fills every required string array with
   generic prose, omits W5's unrepresented minima, and is structurally complete. Because
   `additionalProperties: false`, a producer cannot add the missing typed fields without
   changing the accepted schema.
4. **Impact.** Human reviewers receive no exact obligation identity or typed source
   binding for material scientific boundaries; omissions can be mistaken for a complete
   W5 transcription.
5. **Required disposition.** Amend the upstream schema before acceptance.
6. **Exact change.** Represent lane obligations as exact, versioned requirement rows
   (stable obligation ID, exact W5/WP6 source identity/section, applicability, enforcing
   artifact or human-review question, evidence output, consumer restriction, failure/
   Partial/claim consequence). Exact-set bind the accepted minimum IDs below while
   leaving the scientific answers for the future distinct producer and human review.
   Do not copy mutable contract/skill bodies inline.
7. **No weakened obligation rule.** The next schema must also explicitly preserve W5's
   prohibition on turning `not_applicable`, `unable_to_grade`, Partial, or failed proof
   into pass (`W5:232-238`) and its non-compensable key-A/key-B rule (`W5:458-476`).
   Current `failure_consequence` and `cross_lane_compensation` constants do
   not model those states and authorities.
8. **Affected decisions/work packages.** P-029/P-036; every W5 lane; WP6.3/A7 and paper-
   claim consumers.

### M-4 — Major — The durable upstream contract is self-invalidating at the future-pack transition

1. **Claim.** Task-local absence and pending-review assertions are bound as permanent
   contract tests, but the contract's own acceptance order requires the future pack to
   be authored later. No immutable external lifecycle record resolves the transition.
2. **Evidence.** The contract and its schema fix status to
   `pending_independent_review` (`Contract:1-5`; `Contract schema:22-26`). The bound
   test list includes `test_upstream_contract_is_strict_pending_and_content_addressed`
   (`Contract:249-257`), which unconditionally asserts the future path does not exist
   (`Test:327-350`). Yet the same contract orders independent review,
   Stephen acceptance, distinct producer assignment, and future pack authorship
   (`Contract:259-282`).
3. **Concrete failure scenario.** After legitimate owner acceptance, the distinct future
   producer creates the pack. The accepted upstream test immediately fails. Removing or
   weakening the absence/status assertion changes the exact test/contract identity that
   was accepted; leaving it unchanged prevents implementation. Alternatively, consumers
   treat an externally accepted contract still labelled pending as accepted, laundering
   lifecycle state outside any defined binding.
4. **Impact.** The approved contract cannot remain both immutable and executable through
   the transition it governs. This forces bypass, byte drift, or contradictory status.
5. **Authority context.** Future-pack absence is a valid hard stop for this authoring
   task, but it is not WP6.3 completion authority. The approved master requires the
   eventual pack and clears A7 only after pack acceptance
   (`WP6:110-120,325`).
6. **Required disposition.** Separate the task-local hard-stop test from durable
   validation bindings before contract acceptance.
7. **Exact change.** Keep the authored contract bytes immutable and put review/owner
   acceptance, supersession, and future-pack authorization in external, content-
   addressed lifecycle records bound to the exact contract blob/SHA. The durable
   validator should accept the future path only when those records and a distinct
   producer are valid. The current task may retain a separate unbound scope test that
   proves the pack was absent at subject commit `2ae6078`.
8. **Affected decisions/work packages.** P-029/P-036; W5 §§6/8/16; WP6.3 and its later
   producer dispatch.

## 4. Six-lane coverage matrix

| Lane | Accepted W5 minimum | Subject surface | Disposition |
|---|---|---|---|
| Topology | Object/filtration/homology; coefficient field; metric/order; thresholds/truncation; landmark and essential-class rules; benchmark/scaling/direction; subject identity and topology/geometry/association/causal limits (`W5:373-379`) | `persistence_construction`, `filtration`, `coefficient_field`, `homology_dimensions`, `benchmark_validation`, `interpretation_boundaries` (`Contract:92-103`; `Pack schema:261-272`) | **Incomplete.** Metric/order, threshold/truncation, landmark, essential-class, scaling/direction, and subject identity are not addressable as exact typed obligations. |
| Stochastic / null | Hypothesis/operation; exchangeability/conditioning; Markov order/strata; sampling unit; B; RNG/seed; denominator/formula; tested-object mutation; checkpoint/resume; multiplicity; diagnostic/inferential separation (`W5:381-386`) | Eight broad fields (`Contract:104-117`; `Pack schema:274-287`) | **Incomplete.** No exact B, sampling-unit, conditioning/strata, checkpoint/resume, multiplicity, or diagnostic-separation obligation IDs. |
| Statistical / panel | Estimand/population/eligibility/denominator; dependence; missingness; weights/trimming; variance; multiplicity/sensitivity; governed formula/software; boundary/sparse/separation cases; claim-type limits (`W5:388-393`) | Nine broad fields (`Contract:118-132`; `Pack schema:289-303`) | **Incomplete.** Weights/trimming, formula/software, boundary/sparse/separation, and claim-type distinctions are absent; `uncertainty` is not an exact variance contract. |
| Representation | Fit/transform authority; frozen model/loadings/scaler/labels; training population; recoding/windows/dimensions/vintage; fingerprint; comparability/prohibited refit; uncertainty/sensitivity (`W5:395-400`) | Six broad fields (`Contract:133-144`; `Pack schema:305-316`) | **Incomplete.** Training population, scaler/labels, windows/dimensions, fingerprint, and uncertainty/sensitivity are absent. |
| Output / provenance | Immutable IDs/hashes; code/environment; parameters/seeds/sample restrictions/roots/date; no overwrite; schema/cache lineage/regenerability; consumer comparison fields; exact-byte validation; separately authorized vault/claim routing (`W5:402-407`) | Nine broad fields (`Contract:145-159`; `Pack schema:318-332`) | **Incomplete.** Code/environment, parameters/seeds/sample, roots/date, cache/regenerability, comparison fields, and exact-byte run identity are absent. |
| Paper claim | Exact result/evidence IDs; decision rule/outcome; wording/type/strength/population/domain/uncertainty/limitations/disclosure; independent review and Stephen promotion; no unsupported causal/novelty/generality escalation (`W5:409-415`) | Five broad fields (`Contract:160-170`; `Pack schema:334-344`) | **Incomplete.** Exact result identity, decision-rule outcome, wording/type/strength/scope/uncertainty/disclosure, and attributed Stephen decision are not exact fields. |

Every lane must also expose exact governing sources, inputs/identities, enforcing
artifacts, review questions/capability, counterexamples, evidence outputs/consumer
restrictions, and Partial/failure/claim consequence (`W5:185-220`). The
current generic arrays do not supply that complete relational contract.

## 5. Proposed identity disposition

| Element | Disposition | Basis |
|---|---|---|
| `.research-system/packs/tdl-private-assurance.yaml` | **Keep proposed** | Absent at base/subject; no path collision; follows existing pack directory and lower-kebab filename convention. It remains future-only. |
| `TDL_private` | **Keep as pack family/name; amend as canonical object ID** | Exact accepted W5 name (`W5:419-421`), but W5 separately requires `assurance_pack_id asp_...` (`W5:144-159`). |
| `ars://assurance/assurance-pack` | **Amend** | Currently unique and discoverable, but generic ID hard-codes one TDL-private schema and conflicts with the accepted multi-pack design. |
| `1.0.0` | **Keep proposed** | Conventional and collision-free; gains authority only with the corrected exact schema revision. |
| `distribution_scope = TDL_private` | **Keep** | Required by W5 §§15.1/24; consumer/path/data semantics still require the C-1 binding. |
| minimum independence `I2` | **Keep as proposed strengthening** | P-029 permits a pack to raise R2 from I1 to I2 (`Decisions:344-350`); it must be enforced, not merely declared. |

## 6. Decision disposition

| Decision | Disposition for this subject |
|---|---|
| P-031 | **Keep / unaffected.** Only pilot occupant changes; no pilot or WP6.4 credit is earned (`Decisions:388-398`). |
| P-032 | **Keep / unaffected.** No W11 object, path transition, dual ownership, or migration is created (`Decisions:400-409`). |
| P-033 | **Keep / unaffected.** No live transport, degraded/operator bypass, profile, or R2 dispatch is opened (`Decisions:411-420`). |
| P-034 | **Keep / unaffected.** Consolidation remains downstream and transition-gated (`Decisions:422-430`). |
| P-035 | **Keep / unaffected.** This governs WP6.2 sequencing/composition, not WP6.3 acceptance; no future protocol, manifest, live result, eligibility, migration, preflight, or claim is inferred (`Decisions:432-534`). |
| P-036 | **Keep; do not overread.** It approves exact plan revision `fe5f1d40bc8f05f061317c677b5891cea0711249` as planning authority only, not subject `2ae607803b4cdaef677c2699439e1e1b876856e8`, its proposed identity, or a future pack (`Decisions:536-560`). |

Subject-contract decisions are disposed as follows: upstream-contract-first is a
reasonable response to missing accepted schema/path/version authority; the I2 floor,
exact-version-reference rule, no-copy rule, six-lane non-compensation, TDL-private
distribution, and no-core-authority-mutation boundaries are retained. The current
identity schema, semantic binding, exact-set definitions, lane transcription, and
task-local/durable lifecycle composition require amendment under C-1/M-1–M-4.

## 7. Invariant → enforcement → test consistency matrix

| Invariant | Authority | Subject enforcement | Adversarial test | Result |
|---|---|---|---|---|
| Exact six lane keys, no extras | W5 §§7-8; WP6.3 | Closed keyed schema (`Pack schema:41-59`) plus helper set equality (`Test:290-292`) | Missing/extra lane | **Pass for keys only** |
| Full W5 obligation fidelity | W5 §§7-8, 14-15 | Closed free-text obligation objects (`Pack schema:261-344`) | Generic sentence accepted in every field | **Fail — M-3** |
| Independent requirement scope / I2 | P-022/P-029; W5 §§6/11 | Shape-only actor IDs; partial four-string distinctness (`Test:296-315`) | Same selected reviewer; producer-only N/A | **Fail — C-1; author, grade, record resolution unbound** |
| Exact upstream contract identity | W5 §§6/16 | Caller-supplied expected blob/SHA defaults (`Test:283-318`) | One-sided stale SHA | **Fail — defaults are fictional; no public external binding** |
| Pack content address | W5 §§6/14 | 64-hex shape only (`Pack schema:31`) | None committed; in-memory changed hash accepted | **Fail — C-1** |
| Exact six contract + six skill refs | WP6.3; `Contract:200-217` | ≥1 contract, ≥5 skills; generic row (`Pack schema:166-198`) | Missing version / inline body only | **Fail — M-2** |
| Active, non-copied versioned semantics | W5 §§8/11/15.1 | Git-blob-shaped row; no registry/activation resolution | Inline-body mutation only | **Fail — M-2; two required contracts pending** |
| Exact fourteen fixture cases / producer seam | W5 §§11/13/22; `Contract:218-236` | ≥10 arbitrary fixtures (`Pack schema:61-65`) | Ten synthetic post-production rows | **Fail — M-2** |
| TDL-private consumer/publication/path/data boundary | W5 §24 | Const scope/export plus arbitrary nonempty consumer/restriction strings (`Pack schema:200-231`) | Missing fields only | **Fail — C-1; widening/contradiction accepted** |
| Accepted review/owner decision and no status laundering | W5 §§8/16-17 | Non-null arbitrary hashes (`Test:305-308`) | No committed status/hash-coherence attack | **Fail — C-1/M-4** |
| Immutable transition to future pack | W5 §§6/8 | Pending const plus permanent absence assertion | No future-state test | **Fail — M-4** |
| Schema discovery / duplicate ID rejection | W1 registry; current implementation | Recursive `*.schema.json` registration and duplicate `$id` rejection (`research_system/schema_registry.py:27-47`) | Focused registration assertions (`Test:327-365`) | **Pass for current IDs** |
| UTF-8/LF source blob provenance | `Contract:7-13,21-59` | Git `rev-parse`/`cat-file`, SHA-256, CR rejection (`Test:350-359`) | All six sources | **Pass for pinned governing sources** |
| No future pack or prohibited work in subject | Task hard stop; P-036 boundary | Four-file diff; absence assertion | Git tree/diff inspection | **Pass at subject commit** |

## 8. Bound test and fixture disposition

All six declared test functions exist and passed:

| Bound test | Disposition |
|---|---|
| `test_upstream_contract_is_strict_pending_and_content_addressed` | **Pass for current pending task**, but its durable pack-absence binding causes M-4. Source blob checks and schema closure are sound. |
| `test_candidate_pack_accepts_complete_six_lane_shape` | **Pass mechanically; invalid oracle.** The candidate is not complete against the contract's exact refs/fixtures or W5 minima. |
| `test_candidate_pack_rejects_lane_closure_and_distribution_mutations` | **Partial coverage.** Missing/extra lane and wrong top-level scope reject; consumer widening and contradictory restrictions pass. |
| `test_candidate_pack_rejects_authority_and_not_applicable_bypasses` | **Partial coverage.** One missing role and two same-actor cases reject; canonical records, minimum I2, author/producer separation, Stephen authority, and hash linkage are untested. |
| `test_candidate_pack_rejects_reference_and_boundary_bypasses` | **Partial coverage.** Missing version, inline body, and missing boundary fields reject; wrong kind, foreign/alias/duplicate/swap/pending/dangling references pass. |
| `test_candidate_pack_rejects_stale_identity_currency_and_cross_lane_compensation` | **Partial coverage.** One-sided stale values reject; content hash, coordinated replacement, decision-hash coherence, effective/expiry order, and public seam are untested. |

The fourteen contract-named cases—missing/extra lane, wrong distribution scope, missing
authority separation, producer-only N/A, unversioned/copy reference, four missing
distribution boundaries, stale identity, expired currency, and cross-lane compensation—
are each represented by a post-produced dictionary mutation. None perturbs a future
pack producer, loader, registry resolver, or public acceptance seam. There are no
committed duplicate-ID, alias, swap, foreign-valid, consumer-widening, status-laundering,
self-acceptance, content-preimage, coordinated expected/observed replacement, or
effective/expiry-order fixtures.

## 9. Validation evidence

| Check | Result |
|---|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` with `PYTHONDONTWRITEBYTECODE=1` | Exit 0; `all gates passed against 101 contract(s)` |
| `python .claude/hooks/contract_binding_check.py --no-pytest` with `PYTHONDONTWRITEBYTECODE=1` | Exit 0; `all gates passed against 101 contract(s)` |
| `python -m pytest tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -q -p no:cacheprovider --no-cov` with bytecode disabled and external `COVERAGE_FILE` | Exit 0; **6 passed** |
| Ignored runner-artifact inventory before/after | `.coverage`, `.pytest_cache`, subject-test `__pycache__`, and package `__pycache__` absent before and after |
| `git diff --check` on subject diff | Pass |
| Schema object closure | Contract schema 23/23 explicit object nodes closed; pack schema 27/27 closed |
| Governing source identities | All six declared commit/path/blob/SHA triples independently resolved; strict UTF-8/LF Git blobs, zero CR, terminal LF |
| Current schema registry | Both new IDs discoverable; no duplicate among the subject's registered schemas |
| Future pack | Absent from filesystem and `HEAD` Git tree |

Subject added-blob provenance:

| Path | Git blob | Canonical raw-blob SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7e8785926acb2491c9df5b0ee4513f4f0dc60599` | `79db7d232692dc8cce89d9bae4b049c98c364c7a056784eada9511e73cdfb484` |
| `.research-system/schemas/assurance/assurance-pack.schema.json` | `7ebfabd178b5396432a82dad33fe6deed5e8d4ae` | `eeabd889e5649fc3a2310fccf3df51dc91c3fc70046eefb6ab2186fc0430a183` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `993bade530c38237fb3e3c653b0fb64ca7e70525` | `e78b4444446230d61d34b5eca3ea92cadbf944b6fa6683f39de9b31ec8a02bb5` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `416abc5d1d10970497a1209aa77bff1bf4e89cbe` | `5b0d744587480bf01b7a27f9786cbc2f85a7c7f3c0ba4606216923c5ac81996d` |

## 10. Revision plan

### Immediate upstream corrections

1. Resolve M-1's identity split and schema ID before any registry or future-pack work.
2. Add the public semantic binding required by C-1, using independently frozen external
   authority and contract identities plus a defined canonical pack digest surface.
3. Exact-set bind complete references, active status, lane-reference resolution, and
   all fourteen fixture rows; add the M-2 negative matrix.
4. Replace generic lane strings with the exact versioned obligation-row closure in the
   six-lane matrix, preserving human-review-only scientific judgments and no-copy rules.
5. Separate task-local absence proof from immutable contract lifecycle/acceptance and
   future-pack authorization records.
6. Re-run both contract gates, the focused test, public-seam mutation tests, strict Git-
   blob hash checks, then obtain a new distinct-authority review of the exact revision.

### Owner decisions

- Stephen must accept the corrected exact contract/schema identity after fresh review.
- If the generic-vs-TDL-specific schema-ID choice changes direction, record that choice
  explicitly because accepted authority did not pre-fix it.
- Any required currently pending TDL contract must be activated under its own authority
  or explicitly blocked/deferred; a pack cannot silently treat `pending` as accepted.

### Later-work dependencies

- Only after corrected contract acceptance may a distinct future producer author the
  pack in a new task.
- The future pack then receives its own exact-byte validation, scientific lane review,
  owner acceptance, consumer restrictions, and A7 disposition.
- WP6.4, Gate 6 preflight, research dispatch, result/claim work, and migration remain
  downstream and uncredited.

## 11. Practicality and residual risks

The required corrections are proportionate. Exact-set and cross-field checks execute
once at pack load/review and do not add scientific compute. One typed obligation table
is smaller and more reviewable than duplicating mutable contract/skill bodies. External
Git-blob identity avoids Windows checkout EOL ambiguity and avoids a self-referential
embedded content hash.

After correction, residual risks will remain deliberately human-gated: scientific
adequacy of each lane, reviewer capability, interpretation limits, exact consumer
fitness, and paper-claim language. Two referenced current contracts are pending, the ID
registry does not yet materialize `asp_...`, and the future pack/review/owner decision do
not exist. Those are later blocking dependencies, not evidence that this revision is
acceptable.

## 12. Hard-stop confirmation and change log

The complete subject diff adds exactly the upstream contract, two schemas, and one test.
The future pack file is absent. No pack implementation, WP6.4 credit, research
computation, result, claim, live provider call, migration, eligibility transition,
Gate 5 mutation, P0 mutation, results-path write, credential access, environment-content
access, or self-review approval occurred.

**Files intentionally changed by this review task:** this review report only.<br>
**Reviewed contract/schema/test files changed:** none.<br>
**Verdict:** `rework_required`.
