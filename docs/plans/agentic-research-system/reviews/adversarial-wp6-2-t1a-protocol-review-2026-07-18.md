# Adversarial review — WP6.2 T1a live-grader calibration protocol

**Review date:** 2026-07-18
**Review authority:** distinct-authority statistical/assurance review; the reviewer did not author the subject
**Exact reviewed commit:** `fe2962fa9e10eb290dec0b9e53c3b81bd3ac6491`
**Subject branch / PR:** `pipe/ars-wp6-2-threshold-protocol`; draft PR #122
**Parent / `origin/main`:** `4e6fd0cb26c04ff9707c3183f663461d752b53b9`
**Approved normative plan revision:** `fe5f1d40bc8f05f061317c677b5891cea0711249`
**Review completeness:** Complete. All cited repository authorities and all 15 immutable fixture packages were directly accessible. No conclusion from the subject or the earlier R5 plan review was adopted without recomputation.

## Executive verdict

**Verdict: `rework_required`.**

There are no Critical findings. There are four Major findings and one Minor finding. The current committed protocol is prospective, preserves the approved execution graph, pins the correct authorities and fixture vintage, and contains the correct current model/human obligation and case sets. Those positive results do not make the protocol acceptable:

1. its public schema/test seam accepts obligation relabeling, case relabeling, cross-fixture reference swaps, open transformation aliases, and foreign-but-valid substitutions after the subject-controlled hashes are recomputed;
2. the case descriptors do not freeze executable transformed subjects, independent oracles, or the prospective case-to-obligation/producer/grader allocation needed to prevent post-review case construction and expected-outcome leakage;
3. the named finite frozen target census is inconsistent with the binomial and bootstrap inferential procedures used for acceptance; and
4. the focused subject test fails in this standard Windows checkout because the content-addressed LF bytes are not protected by Git attributes.

`D-G6-2` therefore remains open. This review is neither protocol acceptance nor live evidence. The subject must be revised, re-content-addressed, independently re-reviewed, and then separately accepted by Stephen before T2.

## Review basis and independent recomputation

### Subject and authority identity

- The worktree was attached to `review/ars-wp6-2-threshold-protocol-r1` only after detached `HEAD` and the pre-created branch ref both resolved to the exact subject commit. The subject is one commit directly above `origin/main`; its parent and merge base are the stated base commit.
- At delivery-time review, draft PR #122 was open against `main`, and both its head OID and `origin/pipe/ars-wp6-2-threshold-protocol` resolved to the exact reviewed commit.
- The subject changes exactly five files: the protocol, protocol-scoped identity manifest, their two schemas, and the focused unit test. No protocol-external result, Gate 5, fixture, or p0 file is changed.
- Every authority row in `.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:11-56` was independently resolved at its declared revision. All nine repository paths, Git blobs, and canonical SHA-256 values match. The prior R5 report accepts only the exact plan suite and explicitly leaves the future T1a/T1b evidence gates open (`docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-remediation-r5-review-2026-07-17.md:284-289`); it is not evidence that this protocol is acceptable.

### Exact obligation and fixture closure

The obligation set was recomputed in two independent ways: from the 51 literal predecessor/successor rows in approved 06e and from the accepted production `load_p0_coverage` plus `load_gate5_variant_rows` outputs and immutable fixture `required_graders`. Both derivations produce exactly 31 unique M and 20 unique H tuples, and those full tuples exactly equal the protocol bindings. There are no missing, extra, duplicate, stale, cross-class, or incompatible current bindings. This agrees with the governing target population (`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:57-74`) and 06e, not merely with a subject-owned expected set.

The complete corpus is the 15 declared revisions `F-005`, `F-009`, `F-012`, `F-014`, `F-020`, `F-021`, `F-022`, `F-025`, `F-026`, `F-031`, `F-032`, `F-033`, `F-035`, `F-036`, and `S-016`. The base fixture tree, all 15 package tree/blob identities, and the protocol corpus manifest hash match. All 120 required package files were present; each package contained exactly its eight required files. All YAML/JSON parsed, the declared source/stimulus/pre-control/post-control hashes matched their raw immutable files, and `required_graders` agreed between `fixture.yaml` and `graders/required.json`.

### Independent calibration-case closure

The case IDs were derived from immutable fixture mutation IDs, known-good post-control references, safe-variation IDs, the declared F-022 ambiguity case, and the declared F-022/F-033/F-035 producer-correlation cases. The independently derived sets exactly equal the protocol sets:

| Class | Negative | Positive | Safe variation | Ambiguous | Producer-correlated | Total | Fixture clusters |
|---|---:|---:|---:|---:|---:|---:|---:|
| M | 13 | 11 | 11 | 1 | 3 | 39 | 11 |
| H | 8 | 8 | 8 | 1 | 3 | 28 | 8 |

There are no missing, extra, or duplicate current case IDs. All case and aggregate set hashes recompute. This is a current-byte closure result only; Findings R1-M1 and R1-M2 explain why the public contract cannot preserve that result and why the frozen descriptors are not yet executable cases.

### Content addressing and status

- Protocol Git blob: `3800358b52f87bf2b50b0e98070c2bb2154e7187`; canonical SHA-256: `655b2a94d4cb798f11fea3757747a42410d8a98d70e859edd306873ed1ed7bef`.
- Protocol schema Git blob: `66f363d9a2c36cc7b0ad88cfc462468e4f4911ab`; canonical SHA-256: `4ba371b2f26f623a9a2d79e4c9bdbb1465c095af3bccf36cfdb91b18c8a5ff3e`.
- The committed Git blobs are UTF-8/LF and match the protocol-scoped identity manifest. The manifest scope is correctly limited to `wp6-2-t1a-live-grader-calibration-protocol-only`.
- The subject remains `preregistered_pending_independent_review_and_stephen_acceptance`, makes `no_observed_calibration_claim`, and preserves `T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8` (`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:1-10`). No predicted outcome was treated as an observation.

## Findings

### R1-M1 — Major — The public contract does not enforce the exact relational identities it claims to freeze

**Claim.** The strict schema closes object shape, cardinality, enums, and many constants, but it does not bind the relations that make an obligation or calibration case the accepted one. Subject-controlled per-row and aggregate hashes do not create an independent expected authority when a candidate may change the row and recompute the same hashes.

**Evidence.** Target bindings are generic `uniqueItems` arrays in `.research-system/schemas/contracts/wp6-2-live-grader-calibration-protocol.schema.json:304-474`; calibration cases are cardinality/kind-constrained arrays at `:478-744`; and the reusable case definition permits open `transformation_id` strings and independently well-formed references at `:1204-1267`. The exact-target test deliberately drops `obligation_id` from its comparison tuple (`tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py:86-95`) and from each binding hash (`:165-170`). The case test proves only that the fixture ID occurs somewhere in the corpus, the candidate's own case hash recomputes, and the kind agrees with its decision (`:173-225`). The advertised bypass test (`:295-382`) checks coarse wrong-type, omission, cardinality, stale-constant, and cross-class mutations, not valid same-class swaps or cross-record relations.

Direct candidate-seam attacks were run in memory through `SchemaRegistry.validate`, recomputing every affected candidate-owned hash. The public schema accepted all of the following: swapping two obligation IDs; swapping two case IDs; putting a valid H-only fixture reference into the M set while retaining a schema-valid M record; swapping a reference across fixtures; and replacing a transformation with an unregistered alias. The unchanged committed subject is correct, but the claimed machine-checkable exactness at `.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:1640-1643` is false.

**Concrete failure scenario.** A revision relabels two obligations, substitutes a foreign-but-valid case, or points a case at another fixture's valid 64-hex reference, then recomputes `binding_sha256`, `case_sha256`, and the aggregate set hash. Schema validation and the current focused tests pass even though the accepted 06e row identity or immutable fixture semantics no longer match.

**Impact.** This permits invalid protocol acceptance at the exact public seam intended to reject missing/extra/duplicate/alias/swap/cross-family substitutions. It also makes coordinated expected/candidate corruption indistinguishable from correct closure. Human review could still catch the defect, but the protocol explicitly claims machine-checkable exactness and owner acceptance is expected to rely on the content-addressed contract.

**Disposition.** Fix now; do not defer to T1b. This is a T1a acceptance control.

**Required interface change.** Add a protocol-specific independent semantic validator or literal closed schema projection that compares each ordered complete record to accepted external authorities. The target comparison must include `obligation_id` plus the full predecessor/successor tuple and reject reordered, relabeled, missing, extra, duplicate, and cross-class rows. The case comparison must bind `case_id`, class, kind, fixture ID/revision/tree, exact reference role/hash, registered transformation identity, expected decision, blinding identity, and case hash to an independently produced and accepted manifest. A literal JSON Schema may use exact `prefixItems` plus `items: false`; an executable validator is also acceptable if its expected projection is derived from immutable accepted sources rather than this candidate. Add one-at-a-time public-seam tests for obligation swap, case swap, duplicate alias, cross-fixture reference, cross-family/foreign-valid substitution, relabeling, repeat collapse, and coordinated candidate/hash changes.

**Affected decisions/work packages.** P-035, P-036 exact-revision boundary, D-G6-2, WP6.2 T1a, future T1b-M/T1b-H evidence, and the W5 independent-property rule (`docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md:315-320`).

### R1-M2 — Major — Descriptor hashes do not freeze executable blinded cases or their prospective allocation

**Claim.** The 39 M and 28 H descriptor lists and the human rubric are separately hashed, but the protocol does not freeze the exact transformed subject, transformation implementation/specification, independent oracle, or case-to-obligation/producer/grader allocation that T1b must execute. Consequently, the reviewed expected authority and later observed authority are not yet structurally independent at the execution seam.

**Evidence.** Case rows contain a source reference hash and a free-form transformation label (`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:757-1435`); repeated labels such as `known-good-post-control`, `identifier-renaming`, `withhold-reviewer-relationship-and-authority-attribution`, and `substitute-same-family-or-same-context-nominal-reviewer` do not identify content-addressed transformation code or materialized case bytes. Repository-wide direct search found the safe/ambiguous/producer-correlated transformation labels only in this protocol or as fixture-declared IDs, not as an executable, versioned transformation authority. The future evidence list requires `target_obligation_id`, subject hashes, producer/grader identities, and contexts (`:1522-1596`), but no current case record or allocation rule determines which of 31/20 obligations receives each of 39/28 cases, which producer family/context creates it, which independent grader receives it, or how two repetitions relate to the two human initial graders.

The rubric itself is separately bound and contains sensible authority, blinding, disagreement, adjudication, and revision rules (`:1436-1461`). Yet initial graders are denied producer identity (`:1446-1452`) while producer-correlated cases are meant to test same-family/context blind spots, and no frozen subject/allocation record shows what evidence remains visible for that test. W6 requires blinded positive, negative, ambiguous, and producer-correlated examples (`docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md:315-327`); W5 requires an independent oracle/recomputation and positive, negative, boundary, mutation, and no-op cases (`docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md:315-320`). Descriptor labels alone do not satisfy those requirements.

**Concrete failure scenario.** After T1a acceptance, a T1b implementer chooses how `identifier-renaming` modifies a subject, assigns only easy cases to one model family, omits a difficult obligation-to-case pairing, or reveals the expected decision through the transformed payload. The result can bind the approved descriptor hash while evaluating a subject, oracle, or producer/grader relation that was never reviewed. A producer could also construct both the transformed expected view and the observed grading input after acceptance, defeating prospective separation without changing a frozen descriptor.

**Impact.** Calibration results would be underidentified and non-reproducible. Exact-set closure could be asserted for records that do not represent the reviewed cases; blinding and producer-correlation claims could not be independently audited; predicted outcomes could leak into observations; and the non-compensable M/H policy would lack a deterministic execution plan.

**Disposition.** Fix now in a new T1a protocol revision. This cannot be repaired retrospectively by T1b evidence.

**Required interface change.** Freeze separate content-addressed M-case, H-case, and human-rubric manifests. Each executable case must bind: exact materialized subject path/blob/SHA-256 (or a deterministic transformation spec ID/version/blob/SHA-256 plus immutable input); independent oracle ID/blob/SHA-256 and reference role; target obligation ID; case class/kind; producer actor/family/context allocation; grader class/family/context eligibility; repetition and human-grader allocation; the initial blinded view; adjudicator-only view; expected decision; and expiry/amendment identity. Define a public result schema that enforces those relations and rejects expected-decision-to-observation copying. The expected manifests must be produced/reviewed independently of later observed evidence and accepted by exact identity before any provider call.

**Affected decisions/work packages.** P-035, D-G6-2, WP6.2 T1a and T1b-M/T1b-H, T3/T4 protected producers, W5 assurance, W6 calibration, and the 06b requirement that T1b-H execute a separately frozen blinded case set (`docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md:91-107`).

### R1-M3 — Major — The inferential uncertainty model does not identify the stated finite-population estimand

**Claim.** The protocol fully enumerates a frozen finite target scope but applies Clopper-Pearson binomial bounds and a fixture bootstrap without defining a sampling process, exchangeable superpopulation, or generalization target. The acceptance uncertainty therefore does not estimate the stated object.

**Evidence.** The population is explicitly “the exact 31 M and 20 H ... obligations ... for the 15 named fixture revisions” (`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:57-74`). The estimand is a fixture-cluster probability “over the frozen target scope,” with all 11 M and 8 H fixture clusters enumerated (`:1472-1484`). There is no random sampling of fixture revisions. The cases are purposively selected from required bad/good/safe/ambiguous/correlated views. Nevertheless, acceptance uses a one-sided 95% Clopper-Pearson binomial upper bound and diagnostic percentile bootstrap (`:1480-1483`). Neither the protocol nor its controlling sources state an IID/exchangeable cluster model, a target superpopulation, a sampling frame, selection probabilities, or why a bootstrap of eight or eleven purposive fixture clusters represents future execution uncertainty.

The arithmetic is internally correct: with zero erroneous clusters, the one-sided 95% upper bounds are `0.2384041903808527` for 11 and `0.31234397806636793` for 8, below the preregistered `0.25` and `0.32` limits (`:1492-1507`). Repeat nesting and the “any adverse case/repetition makes the fixture cluster erroneous” rule correctly avoid pseudo-replication (`:1476-1479`). But zero false-pass and zero false-block counts are already separately mandatory. Thus, for the enumerated census, acceptance is an exact descriptive all-clusters rule; the binomial bound adds an unsupported superpopulation interpretation, and its threshold cannot change the decision while the zero-count rule remains.

**Concrete failure scenario.** T1b observes zero errors across all purposively chosen clusters and reports a 95% statement about an apparent fixture-error probability. Consumers interpret that as uncertainty for future fixtures, models, or human reviews, although no probability sample or exchangeability model links the frozen census to those consumers. A percentile bootstrap of all-zero cluster indicators can further report degenerate apparent certainty despite the small, selected corpus.

**Impact.** The statistical claim would overstate generalizability and could support an eligibility decision with uncertainty evidence that is not identified by the design. Conversely, the added calculations create process cost without altering the exact zero-error acceptance rule.

**Disposition.** Amend the statistical design before acceptance. Owner/statistical authority must choose the intended target; do not infer one during execution.

**Required text/interface change.** Choose one of two coherent designs. For a finite frozen census, define class-specific false-pass/false-block proportions over the exact 11/8 clusters as descriptive quantities, retain zero-error exact closure as the acceptance rule, and label any resampling as non-acceptance sensitivity with no confidence interpretation. For a superpopulation/repeated-use reliability estimand, define that population, fixture selection mechanism, exchangeability/dependence assumptions, execution unit, producer/model/human sources of variation, and an uncertainty method justified for the design; then provide prospective operating-characteristic/power rationale for the denominators and tolerable error bounds. In either design, explain the decision utility of the `0.25`/`0.32` limits and whether they are intentionally redundant with the zero-count rule.

**Affected decisions/work packages.** P-035 statistical review gate, D-G6-2, WP6.2 T1a/T1b-M/T1b-H, W6 threshold-policy ownership (`docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md:543-557`), and the accepted addendum requirement to preregister repeats, uncertainty, false-accept/false-reject evidence, and expiry (`docs/plans/agentic-research-system/design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md:48-52`).

### R1-M4 — Major — The content-addressed contract is not portable to the repository's standard Windows checkout

**Claim.** The committed protocol and schema blobs are correctly LF-normalized, but the repository does not declare an LF worktree rule for them. With repository `core.autocrlf=true`, the focused identity test reads CRLF checkout bytes and fails before comparing the declared identities.

**Evidence.** `git check-attr text eol working-tree-encoding` reports no applicable attributes for the protocol or schema. Direct byte inspection finds CRLF in the checkout while the Git blobs contain LF only. The focused test explicitly rejects any carriage return and hashes worktree bytes (`tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py:98-125`). In this exact clean review worktree, `python -m pytest -q tests/research_system/unit/test_wp6_2_live_grader_calibration_protocol.py` collected 21 tests, passed 20, and failed that test at line 120. Both broader contract-binding gates nevertheless passed, demonstrating that the failure is specific to the content-addressed checkout seam rather than corrupt committed identities.

**Concrete failure scenario.** Stephen or a hook runner checks out the accepted revision on standard Windows settings. Git silently materializes CRLF while `git status` remains clean. The required protocol test fails, or a consumer hashes worktree bytes and obtains an identity different from the accepted canonical SHA-256.

**Impact.** The owner cannot reproduce the acceptance check consistently across supported worktrees, and content-addressed identity depends on checkout configuration. That is a material operational blocker for an exact-hash owner gate.

**Disposition.** Fix now and revalidate in both Git-blob and actual Windows-worktree representations.

**Required interface change.** Add a repository-authoritative `text eol=lf` rule covering the protocol, its schema, and the scoped identity manifest/schema, then renormalize and verify the files. Alternatively, make Git blob bytes the explicitly authoritative validation input and separately enforce checkout normalization before any consumer reads worktree bytes. The revised focused test must pass in a fresh Windows worktree with the repository's actual configuration and on the owner’s canonical tree.

**Affected decisions/work packages.** P-035 exact-hash acceptance, D-G6-2, WP6.2 T1a, protocol identity manifest, and future T1b evidence consumers.

### R1-m1 — Minor — “first 31 bits” does not specify the implemented seed extraction

**Claim/evidence.** SHA-256 of the declared seed material is `0cf7de1a64e8f19bd027189ba18186a0b85d6dd539d37861c22e3bdad67bdf8a`. The declared seed `217570842` equals the first 32-bit big-endian word (`0x0cf7de1a`) masked to a non-negative 31-bit integer. A literal first-31-most-significant-bit prefix is `108785421`. The current rationale says only `first_31_bits` (`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:1462-1470`).

**Failure scenario and impact.** An independent implementation uses the literal 31-bit prefix and generates a different order/bootstrap stream. This is a local reproducibility ambiguity; the current frozen seed itself is unambiguous and was not derived from observations.

**Disposition and required text.** Fix now by stating an exact language-neutral algorithm, for example: `uint32_be(sha256(seed_material)[0:4]) & 0x7fffffff`, with a test vector containing the digest and expected integer. Affected scope: T1a randomness, future T1b execution, and diagnostic resampling.

## Statistical estimand and uncertainty disposition

| Dimension | Disposition | Basis |
|---|---|---|
| Target population | PASS for finite scope | Exact 31 M / 20 H obligations and exact 15 revisions independently reproduced. |
| Estimand definition | CONCERN | Class, adverse direction, and cluster rule are explicit, but “probability ... over the frozen target scope” conflates a finite census proportion with a stochastic probability. |
| Sampling/selection | FAIL | Complete purposive census; no random sample, sampling frame, selection probability, or superpopulation is specified. |
| Experimental unit | PASS | Case and repetition are nested in fixture revision; repeats do not inflate denominators. |
| Dependence handling | PASS for the descriptive gate | Any adverse case/repetition marks its fixture cluster; 11/8 denominators are correct. Cross-fixture exchangeability needed for inference is not established. |
| Repeats/randomness | CONCERN | Two literal repetitions and a prospective seed are frozen; seed extraction wording is ambiguous and two runs do not characterize future provider/human variation. |
| Uncertainty | FAIL | Clopper-Pearson and bootstrap lack a design-supported probability target; percentile bootstrap is only labeled diagnostic but remains uninterpretable without a sampling model. |
| Bounds/decision rule | CONCERN | Numerical zero-error bounds are correct, non-compensable, and prospective. They are redundant with mandatory zero errors, and no risk/power rationale supports `0.25`/`0.32`. |
| Multiplicity/non-compensation | PASS | FP/FB and M/H remain separate; no weighted aggregate repairs a failure. |
| Missingness/omissions | PASS in prose | Any required omission blocks the affected class and composite gate (`.research-system/contracts/wp6-2-live-grader-calibration-protocol.yaml:1614-1625`). Execution-schema enforcement remains part of R1-M1/R1-M2. |

## Decision audit

| Decision/gate | Disposition | Review result |
|---|---|---|
| P-031 — Gate 6 pilot definition | Keep | This protocol does not alter the SCALE-01 pilot occupant or promotion criteria (`docs/plans/agentic-research-system/03-decisions-and-open-questions.md:388-399`). |
| P-032 — portfolio/Discovery integration | Keep | No portfolio integration or migration is performed (`:400-410`). |
| P-033 — full live capability before research dispatch | Keep | No interim operator mode, eligibility transition, or research dispatch is authorized (`:411-421`). |
| P-034 — consolidation/sunset sequencing | Keep | No consolidation or legacy sunset work is performed (`:422-431`). |
| P-035 — staged calibration/composite evidence | Keep sequencing; T1a evidence rejected pending revision | The graph and non-compensable T1b-M/T1b-H composition remain governing. Findings require a new T1a version; they do not supersede P-035 (`:432-535`). |
| P-036 — exact plan-suite revision | Keep | The normative revision is correctly pinned. P-036 approved the plan revision, not this later protocol (`:536-559`). |
| D-G6-2 | Defer/open | Exact T1a acceptance is not earned. T2-T4 remain blocked; T1b and T5-T8 are downstream (`implementation/06-wp6-gate6-readiness-and-integration-plan.md:218-220,297-303`). |
| D-G6-3 plan-revision limb | Keep closed | No change to the accepted plan-revision limb or later manifest acceptances. |

## Complete protocol invariant disposition

| Protocol section/invariant | Disposition | Evidence/result |
|---|---|---|
| Schema/protocol identity and status | PASS on committed bytes | IDs/versions/status are exact; not acceptance or observed evidence. Windows checkout portability fails under R1-M4. |
| Authority sources | PASS | Nine path/revision/blob/SHA identities independently verified (`protocol:11-56`). |
| Scope/exclusions | PASS | M/H-only exact finite scope; D/T/R/O/P, P1 F-037/F-038, research results/claims excluded (`:57-74`). |
| Corpus/vintage | PASS | Exact 15 packages, tree identities, 120 files, declared hashes, revisions, graders, and aggregate hash independently verified (`:75-285`). |
| Target expected sets | PASS current bytes / FAIL enforcement | Exact 31/20 current tuples; no omissions or duplicates. Obligation-ID/relational attacks accepted (R1-M1). |
| Calibration expected sets | PASS current ID closure / FAIL execution identity | Exact 39/28 IDs and kind counts; transformed subjects/oracles/allocation not frozen (R1-M1/R1-M2). |
| Human rubric/blinding | PASS separate hash / CONCERN operability | Rubric has separate identity, authority, blinding, disagreement/adjudication and amendment rules. Producer-correlation visibility/allocation is unresolved (R1-M2). |
| Repetition/randomness | PASS core design / Minor wording | Two repetitions, prospective seed, within-fixture dependence, no denominator inflation; seed algorithm wording needs correction (R1-m1). |
| Estimand/uncertainty | FAIL | Correct finite denominators and clustering, unsupported binomial/bootstrap inference (R1-M3). |
| Agreement/adjudication | PASS prose / CONCERN schema | Nonagreement blocks model class; human decisions captured before distinct adjudication. Future record types/relations are not schema-bound (R1-M2). |
| Prospective criteria | PASS non-compensation / CONCERN inference | Zero errors, exact closure, separate bounds, no M/H repair. Bound interpretation/rationale fails R1-M3. |
| Expected/observed independence | PASS governance / FAIL structural completion | Author is prohibited from grading and observed side cannot amend expected sets (`:1509-1521`), but later case materialization/allocation is not independently frozen (R1-M2). |
| Future result/evidence fields | PASS inventory / FAIL executable contract | Required identities are listed, including subject, actor/context, receipts, rubric and review fields; no strict result schema or relational allocation enforces them (R1-M2). |
| Currentness/expiry/suspension/amendment | PASS | 90-day expiry, identity drift, adverse/error triggers, omissions, no grandfathering, and new-version/review/owner acceptance are explicit (`:1597-1625`). |
| Outcome permissions | PASS | Acceptance would permit only T2 then T3/T4; Partial/rejection block; no eligibility/T5-T8/result/claim (`:1626-1630`). |
| Assurance lanes/claim boundary | PASS | Statistical, stochastic, and provenance lanes are declared; no topology/representation/paper claim; no cache/result output (`:1631-1646`). |
| Hard stops | PASS and observed | All listed prohibitions remain intact (`:1647-1655`). |

## Test-catalogue disposition

| Subject test | Disposition | Gap/attack result |
|---|---|---|
| `test_protocol_and_scoped_identity_manifest_are_strict_content_addressed_contracts` | FAIL in current Windows checkout | Correct committed identities, but CRLF worktree bytes fail line 120 (R1-M4). |
| `test_contract_schemas_have_no_defaults_and_close_every_object` (two schema cases) | PASS | Recursive audit confirms every object is closed and requires all properties; shape closure does not establish relational semantics. |
| `test_expected_sets_bind_exact_approved_06e_model_and_human_rows` | PASS current tuple projection / incomplete | Correct 31/20 projection; excludes obligation IDs and hashes candidate bindings without them (R1-M1). |
| `test_corpus_and_case_hashes_bind_the_accepted_immutable_fixture_tree` | PASS current corpus / incomplete | Current packages/hashes/case counts pass. Case-to-package reference role, registered transformation, and exact accepted case record are not compared (R1-M1/R1-M2). |
| `test_human_rubric_and_prospective_bounds_are_internally_bound` | PASS arithmetic / statistical concern | Rubric hash and zero-error formulas pass; inference lacks a sampling model (R1-M3). |
| `test_future_evidence_and_assurance_dispositions_are_complete` | PASS field presence / incomplete | Presence does not create types, cross-record relations, or an execution allocation (R1-M2). |
| `test_public_schema_seam_rejects_protocol_bypasses` (14 mutations) | PASS supplied mutations / FAIL required attack coverage | Missing/wrong/extra/coarse cross-class/stale/denominator attacks reject, but valid swaps, aliases, foreign references, obligation relabels, and coordinated rehashes accept (R1-M1). |

Focused result: **21 collected, 20 passed, 1 failed**. The test failure is not waived.

## Consistency matrix

| Governing invariant | Protocol point | Enforcement point | Test/evidence | Disposition |
|---|---|---|---|---|
| T1a precedes T2; T3/T4 parallel after T2; T1b follows both; then T5-T8 | `protocol:10,1626-1630`; master `implementation/06-wp6-gate6-readiness-and-integration-plan.md:200-205`; 06b `:168-190` | Exact schema constant and hard stops | Subject schema + direct text comparison | PASS |
| T1a is prospective and makes no observed claim | `protocol:5,9,1492-1493,1647-1655`; 06b `:49-65,519-530` | Status/claim constants; outcome/hard stops | Schema, diff, no generated result files | PASS |
| Exact M31/H20 unavailable obligations | `protocol:69,286-756`; 06b `:345-426`; approved 06e complete table | Candidate hashes plus generic arrays | Independent 06e and production-loader recomputation | PASS bytes / FAIL semantic enforcement (R1-M1) |
| Exact blinded case closure and independent oracle | `protocol:757-1461`; W5 `design/05-research-assurance-and-independent-review.md:315-320`; W6 `design/06-evaluation-observability-and-audit.md:315-327` | Descriptor hashes only | Independent ID-set derivation; no executable transform/oracle authority | FAIL (R1-M2) |
| M/H non-compensation | `protocol:756,1484,1507-1508`; P-035 | Constants and array class constraints | Cross-class supplied mutations reject | PASS current rule; exact relation fixes still required |
| Producer/grader independence | `protocol:1509-1521`; W5 `:301-307` | Prose constants; future field names | Coarse same-family mutation rejects | CONCERN/FAIL allocation (R1-M2) |
| Repeats and fixture dependence | `protocol:1462-1484`; addendum `design/06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md:48-52` | Exact schema constants | Internal tests and independent recomputation | PASS except R1-m1 |
| Valid statistical uncertainty | `protocol:1472-1507`; W5 `:269-272`; W6 `:543-557` | Exact method/threshold constants | Formula recomputation only | FAIL design identification (R1-M3) |
| Immutable portable content identity | scoped manifest; focused test `:98-125` | Git blob/SHA constants; checkout-byte assertions | Git-object hashes pass; Windows focused test fails | FAIL (R1-M4) |
| Expiry, suspension, omissions, amendment | `protocol:1597-1625` | Closed constants | Schema mutations; direct review | PASS design; future result schema dependency remains |
| No Gate 5/p0/result/claim mutation | `protocol:1630,1644-1653`; P-033/P-035 | Scope/hard-stop constants and review diff | Exact changed-file inventory | PASS |

## Coverage and fixture gaps

| Required attack | Current-byte result | Validation-seam result |
|---|---|---|
| Missing / extra / duplicate | None in current obligations or cases | Cardinality/`uniqueItems` catches simple changes; coordinated valid replacement remains possible. |
| Alias / relabel | No current alias found | Open transformation alias and obligation/case relabel accepted. |
| Swap / cross-family | Current M/H sets disjoint and correct | Same-class swaps/relabels and foreign-valid semantic substitutions accepted; coarse direct M/H row replacement rejects. |
| Cross-fixture reference | All current references agree with independently derived immutable fixture semantics | A well-formed foreign fixture reference can validate after rehash. |
| Denominator drift / repeat collapse | Current 11/8 denominators and two repeats exact | Supplied mutations reject simple drift/collapse; statistical interpretation still fails R1-M3. |
| Predicted outcome promoted to observation | No observed evidence exists; expected outcomes remain prospective | No executable result schema proves future observed values originate independently (R1-M2). |
| Human positive/negative/ambiguous/producer-correlated separation | Separate H descriptor set and rubric hashes exist; current H composition is exact | Actual blinded views, transformation bytes, oracle, and allocation are not separately materialized/frozen. |

## Practicality assessment

The smallest adequate remediation is not a new registry or broad runtime build. It is a protocol-scoped semantic closure layer plus executable case manifests and one coherent statistical target. Exact literal manifests are proportionate here: 51 target obligations and 67 cases are small, already enumerated, and owner acceptance is exact-hash based. Public-seam mutation tests add low mechanical cost and directly protect the high-risk acceptance boundary. A finite-census statistical rule would reduce rather than increase execution overhead. LF attributes are a one-time repository control.

No later-work dependency can safely absorb R1-M1 through R1-M4 because each defect changes what Stephen would be asked to accept at T1a. Provider-specific command/receipt implementation, actual calibration evidence, T1b result aggregation, eligibility transition, and P1 activation remain correctly deferred.

## Revision plan

### Immediate corrections required in the subject revision

1. Add an independent protocol-specific exact-record validator/manifest and the missing public-seam mutation tests described in R1-M1.
2. Materialize and content-address executable M/H cases, or bind deterministic transformation specs and exact independent oracles; freeze prospective case/obligation/producer/grader/repetition/blinding allocation and a strict future result schema as described in R1-M2.
3. Resolve the finite-census versus superpopulation estimand and rewrite the uncertainty/threshold rationale and tests accordingly (R1-M3).
4. Enforce LF portability and make the focused identity test pass in both Git-object and standard Windows-worktree validation (R1-M4).
5. Specify the exact seed extraction algorithm and test vector (R1-m1).
6. Recompute every affected Git blob, canonical SHA-256, row/case/aggregate hash, scoped identity-manifest identity, and protocol version; run the entire focused suite and both contract gates with cache/coverage outputs external or disabled.

### Owner decisions

- Stephen/statistical authority must choose whether acceptance is for the exact finite census or a defined reliability superpopulation and approve any tolerable error bound rationale.
- Stephen must accept only the exact revised protocol hash after a new distinct-authority review. This report does not supply that acceptance.

### Later-work dependencies that remain deferred

- T2 credential/cost/lease controls; T3 Claude and T4 Codex protected canaries; empirical T1b-M and T1b-H results and their separate reviews; the composite T1b evidence policy; T5-T8; eligibility changes; and any result/research/claim work.
- None may be started to “validate” or repair this rejected protocol revision.

## Residual risks after required changes

- A literal finite corpus can establish behavior only on its frozen scope. Any claim about new fixtures, provider revisions, model revisions, human populations, or future operating conditions requires an explicit generalization design or remains a limitation.
- Two provider repetitions detect immediate nondeterminism but do not estimate long-run drift; the existing expiry/suspension rules must remain and provider/model/adapter changes must stale evidence.
- Human blinding can conflict with the information required to grade producer-correlation. The revised manifest should explicitly prove what is hidden, what relationship evidence remains visible, and why it does not leak the expected decision.
- Exact manifests reduce but do not eliminate correlated-author risk. Expected-case production, observed execution, independent review, and Stephen's acceptance must remain distinct authorities.

## Verification and change log

### Validation executed

- `python .claude/hooks/contract_binding_check.py --validate-only` with bytecode/cache/coverage disabled or external: **PASS**, all gates passed for 101 contracts.
- `python .claude/hooks/contract_binding_check.py --no-pytest` under the same controls: **PASS**, all gates passed for 101 contracts.
- Focused subject pytest with `-p no:cacheprovider --no-cov`, external `PYTHONPYCACHEPREFIX`, and external `COVERAGE_FILE`: **FAIL**, 20 passed / 1 failed at the CRLF assertion described in R1-M4.
- Recursive schema audit: **PASS** for strict required fields, `additionalProperties: false`, absence of defaults, schema IDs/versions, and protocol-scoped manifest.
- Independent production-loader and approved-06e closure: **PASS**, exact unique 31 M / 20 H with no missing or extra tuples.
- Immutable corpus/package/hash closure: **PASS**, exact 15 packages and 120 required files.
- Independent case-set closure: **PASS current IDs**, exact M39/H28 composition and no missing/extra/duplicate IDs.
- Public-schema adversarial candidates: **FAIL contract assurance**, five relational/alias/swap substitutions accepted after candidate-owned hashes were recomputed.
- Git status was checked after validation. A pytest-created ignored `research_system/__pycache__` containing three disposable bytecode files was removed after exact-path verification; no cache, coverage, result, or evidence output remains in the worktree.

### Files changed by this review

- Added only `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t1a-protocol-review-2026-07-18.md`.
- No reviewed protocol, schema, manifest, test, plan, fixture, Gate 5 evidence, p0 coverage, result, research, or claim file was edited.

### Hard-stop confirmation

No credentials were resolved; no provider or live call was made; no observed-calibration claim was created; no T2-T8 implementation or dispatch occurred; no M/H eligibility transition occurred; no Gate 5, p0, fixture, evidence, result, research, vault, or claim state was mutated; no PR was opened or merged. The report records a review verdict only.
