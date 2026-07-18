# Adversarial WP6.3 assurance-contract remediation R2 review

**Review date:** 2026-07-18<br>
**Reviewer posture:** fresh distinct-authority, independent, adversarial; not the producer<br>
**Exact reviewed commit:** `d722664f54a55c59466a9923ac5706c7db010081`<br>
**Subject branch / PR:** `pipe/ars-wp6-3-tda-pack` / draft PR #123<br>
**Live PR and remote head verified:** `d722664f54a55c59466a9923ac5706c7db010081`<br>
**Review branch:** `review/ars-wp6-3-tda-pack-r2`<br>
**R1 review commit:** `fe0b8bae0a85b032fb60dc3895578ba6c638e0b8`<br>
**R1 report Git blob:** `fcd02142d2775a4dae5aaea0a258bec05fbd6ae0`<br>
**R1 report raw-blob SHA-256:** `8553e70ef68e772555ccab20b518c185e38d940840235e73bc8b2de67814a8e1`<br>
**Remediation commits:** `b44971fdd52430afdd87419b29b40a0f9c090ae7`, `d722664f54a55c59466a9923ac5706c7db010081`<br>
**Scope:** committed bytes only; R1 report plus final contract, two schemas, and binding test; no future pack implementation<br>
**Verdict:** `rework_required`<br>
**Finding count:** **1 Critical, 3 Major, 0 Minor**<br>
**Evidence accessibility:** complete; this review is **not Partial**

## 1. Executive verdict

The remediation closes important parts of R1. `TDL_private` is now only the accepted
family name; the future canonical object is a distinct `asp_<UUID7>` identity; the
closed pack schema has the TDL-specific ID
`ars://assurance/packs/tdl-private/1.0`; the legacy generic schema ID is absent; and
pack, schema, and contract content identities are declared separately. The candidate
schema is strict and `proposed`-only, contains no pack-review or pack-acceptance
surface, and the task-local future-file absence check is no longer a durable binding.
The contract also freezes exactly 12 complete reference rows, 52 complete fixture rows,
and 69 typed W5/WP6 obligation rows across all six lanes.

Those corrections are not sufficient for acceptance. The external semantic oracle
accepts a rejected assurance requirement, an assurance requirement accepted by the
future producer, a requirement accepted after the pack owner decision, foreign record
types, a review whose producer field names the wrong actor, and a role-like reviewer
alias. Exact hashes do not cure those semantic failures. The pack-subject helper also
hashes a canonical JSON serialization of an already-parsed object instead of the raw
future YAML bytes that the contract names as its Git-blob surface. Two different Git
blobs therefore receive one review/acceptance subject. The positive future-lifecycle
fixture activates both pending references while retaining them in
`current_pending_reference_ids`, and external acceptance passes that contradictory
state. Finally, three typed obligations name `paper-claim-trace` as an enforcing
reference while their lane rows omit it from the exact governing-reference relation.

These defects leave R1 C-1 materially open and leave relational parts of M-2/M-4
unclosed. Stephen must not accept this exact contract/schema revision, no
`assurance_pack` ID or future file may be materialized from it, and WP6.3/A7 remains
blocked.

## 2. Exact revision, authority, and scope

The Codex worktree started detached at the requested commit. Detached `HEAD` and the
pre-created `review/ars-wp6-3-tda-pack-r2` ref both resolved to
`d722664f54a55c59466a9923ac5706c7db010081`; one deterministic `git switch` attached
the worktree, after which the tree was clean. Draft PR #123 was read live and was still
open/draft with base `main`, head branch `pipe/ars-wp6-3-tda-pack`, and head OID equal
to the reviewed commit. `git ls-remote` independently returned the same OID.

The reviewed history above `origin/main` is:

| Commit | Role | Disposition |
|---|---|---|
| `2ae607803b4cdaef677c2699439e1e1b876856e8` | Initial upstream contract/schema/test | R1 subject; superseded by remediation |
| `2a247fe...` | In-branch copy of R1 decision | Carries the exact R1 report blob below |
| `b44971fdd52430afdd87419b29b40a0f9c090ae7` | Main R1 remediation | Reviewed in full at final bytes |
| `d722664f54a55c59466a9923ac5706c7db010081` | Git-native hash helper change | Exact final subject |

The report at R1 commit `fe0b8bae...`, the in-branch R1 decision, and final `HEAD` all
resolve the R1 report path to Git blob
`fcd02142d2775a4dae5aaea0a258bec05fbd6ae0`; no historical evidence was rewritten.
The final diff from `origin/main` adds only the contract, two schemas, R1 report, and
binding test. It makes no production, WP6.4, result, claim, live, migration,
eligibility, Gate 5, or research-state change.

## 3. Findings

### C-1 — Critical — Hash-valid external records can still fabricate acceptance authority

1. **Claim.** Candidate self-acceptance is removed, but the external acceptance oracle
   does not establish that the assurance requirement, pack review, or owner decision
   are the typed, accepted, producer-independent, temporally valid records promised by
   the contract. A content-addressed foreign or rejected record can pass.
2. **Evidence.** The contract requires six external record types, canonical resolution,
   exact subjects, I2, and distinct actors at `Contract:174-195`. The test constructs
   untyped dictionaries at `Test:497-580`; `_resolved_record` checks only ID presence
   and canonical-object SHA-256 at `Test:583-589`. The acceptance routine at
   `Test:611-700` never checks the requirement record's `record_type`, `outcome`,
   `acceptor_actor_id`, or `accepted_at`; never checks the review record's
   `record_type` or `producer_actor_id`; and never schema-validates external actor IDs.
   It checks review-before-owner time only, not requirement-before-review/owner time.
3. **Concrete failure scenario.** Fresh external probes started from the asserted-valid
   eligible fixture, mutated one semantic field, recomputed every affected record hash,
   pack subject, review hash, and owner hash, and called the same acceptance oracle.
   All of the following returned **ACCEPTED**: `outcome=rejected`; requirement
   `acceptor_actor_id=producer`; requirement acceptance dated after the owner decision;
   foreign requirement record type; foreign owner-decision record type; review
   `producer_actor_id` naming another actor; and a role-like reviewer alias.
4. **Impact.** A pack can be owner-accepted without an accepted producer-independent
   assurance requirement and without canonical typed review/decision evidence. This
   can confer invalid scientific and distribution authority and meets Critical
   severity even though no live pack exists yet.
5. **Authority violated.** W5 §§6, 11, 16, and 17 require accepted scope authority,
   canonical independence evidence, exact review subject, and non-self-attested
   two-key acceptance. R1 C-1 expressly required canonical actor/relationship/review/
   owner-decision resolution, coherent dates, and tests at the external producer seam.
6. **Required disposition.** Fix in a new contract/schema/test revision; do not accept
   `d722664f...` and do not materialize the future pack or object.
7. **Exact interface change.** Freeze strict schema IDs/versions/content addresses for
   every external record class. Validate each resolved record against its schema and
   require exact `record_type`, accepted/pass outcome, canonical actor IDs, active
   authority, producer relations, subject equality, and the full ordering
   requirement-accepted → candidate-authored → independently-reviewed → owner-accepted.
   Add coordinated valid-hash negatives for every probe above; hashes must be necessary
   but never sufficient evidence.
8. **Affected decisions/work packages.** P-005, P-022, P-023, P-029, P-036; W5 §§6,
   11, 16-17; WP6.3/A7 and every downstream consumer.

### M-1 — Major — The purported Git-blob pack identity hashes normalized JSON, not raw pack bytes

1. **Claim.** The contract names raw Git-blob UTF-8/LF bytes as the candidate identity
   surface, but the binding helper discards those bytes before hashing.
2. **Evidence.** `Contract:9` fixes `canonical_byte_surface: git_blob_utf8_lf`, and
   `Contract:145-153` requires `raw_candidate_pack_bytes` as an independent input.
   `_pack_subject(pack)` instead calls `_canonical_bytes(pack)` and hashes that JSON at
   `Test:476-484`. Commit `d722664f...` replaced a manual Git blob formula with
   `git hash-object --stdin`, but its input remains normalized JSON rather than the
   future YAML file's exact bytes.
3. **Concrete failure scenario.** Two UTF-8 YAML serializations differing only by a
   leading comment had raw Git blobs `1dcc2bb9dbbf8ee3784e84bd26a314eebd190f00`
   and `ca8001189efcaec75b0b43bbe1cd72aa94ca673c`, but both parsed objects received helper
   subject blob `fabd18728f03fbdb727f5072eab4d274c794274e`, which equalled neither raw blob.
4. **Impact.** Review and owner records can continue to validate after the repository
   bytes change, defeating exact-byte provenance and making the test oracle inconsistent
   with the declared content-addressing model.
5. **Authority violated.** R1 C-1 required identity from a defined non-self-referential
   canonical byte surface, preferably the external Git blob plus SHA-256; the remediated
   contract chose that surface explicitly.
6. **Required disposition.** Fix before owner acceptance.
7. **Exact interface change.** Make the subject builder accept raw candidate bytes,
   compute Git blob and SHA-256 directly from those exact bytes, then parse and validate
   the same bytes separately. Bind review and owner records to that raw subject. Add a
   semantically equivalent/comment/order mutation proving that every byte change changes
   the subject while unchanged bytes are portable across Git implementations.
8. **Affected decisions/work packages.** P-023, P-029, P-036; W5 §§6, 14.5, 16-17;
   WP6.3/A7.

### M-2 — Major — The positive lifecycle oracle accepts an active/pending contradiction

1. **Claim.** Current pending references correctly block acceptance, but the test that
   purports to demonstrate the later eligible lifecycle does not clear their pending
   relation and still passes external acceptance.
2. **Evidence.** The current contract lists two pending IDs at `Contract:367-379`.
   The contract schema requires `current_pending_reference_ids` to contain exactly two
   rows at `Contract schema:456-461`. `_eligible_contract` flips both referenced rows to
   `activation_state=active` and `pack_acceptance_eligible=true` but deliberately leaves
   the same two IDs in the pending list (`Test:369-382`). The pack validator gates only
   `pack_acceptance_eligible` (`Test:423-424`) and never checks equality between the
   pending list and non-eligible rows.
3. **Concrete failure scenario.** The external probe schema-validated the eligible
   contract and completed external acceptance while both active/eligible reference IDs
   remained declared current-pending. Thus the positive fixture proves acceptance of an
   internally contradictory authority object, not a feasible cleared state.
4. **Impact.** The proposed → reviewed → Stephen-accepted sequence is acyclic in prose,
   and the task-local absence test no longer self-invalidates, but the only executable
   future-state proof can launder pending dependencies. A consumer cannot determine
   which status relation is authoritative.
5. **Authority violated.** W5 exact-reference/currency rules, R1 M-2/M-4, and the OPEN
   relational-invariant review principle require exact cross-record relations, not only
   individually valid rows.
6. **Required disposition.** Amend the relation and positive lifecycle fixture before
   acceptance.
7. **Exact interface change.** Enforce
   `current_pending_reference_ids == {id | activation_state != active or
   pack_acceptance_eligible == false}`. Permit an empty exact set in a superseding
   revision, clear it in the positive fixture, schema-validate that future revision,
   and retain a negative where any disagreement blocks acceptance.
8. **Affected decisions/work packages.** P-023, P-029, P-036; W5 §§8, 11, 16; WP6.3
   and the future producer dispatch.

### M-3 — Major — Typed obligations and exact lane governing references are relationally inconsistent

1. **Claim.** The 69 obligation rows are complete and typed, but three obligations use
   an enforcing reference that their lane's exact governing-reference row omits. The
   validator freezes both sides independently without checking the relationship.
2. **Evidence.** Topology, statistical/panel, and output/provenance lane rows are at
   `Contract:215-232`, `Contract:263-281`, and `Contract:308-323`. Their interpretation,
   claim-type, and vault/claim-routing obligations respectively name
   `skill/paper-claim-trace`, but their `exact_governing_reference_ids` arrays do not.
   The reference row permits that skill in those lanes, so individual validity passes.
   `Test:440-459` validates the lane reference set and obligation set separately but
   never requires every obligation enforcer to belong to its lane's governing set.
3. **Concrete failure scenario.** The exact current candidate passes while three lane
   contracts invoke an undeclared enforcer. The committed swapped/dangling mutation
   changes the whole lane list and therefore does not expose this internally frozen
   mismatch.
4. **Impact.** Consumers deriving lane dependencies from the exact lane relation can
   omit an enforcing skill required by a typed obligation, weakening claim-boundary
   review in three lanes despite exact-set equality everywhere.
5. **Authority violated.** R1 M-2 required allowed lane usages and exact lane-reference
   resolution; the relational-invariant rule requires equality at the relationship,
   not merely validity of each member.
6. **Required disposition.** Fix the three relations and add a relation mutation.
7. **Exact interface change.** Either add `skill/paper-claim-trace` to all three exact
   governing-reference sets or define a separate, explicitly named obligation-enforcer
   relation. Enforce that every `enforcing_reference_id` exists, permits the lane, and
   is present in the governing/enforcer relation. Add one foreign-valid substitution
   and one omitted-enforcer mutation.
8. **Affected decisions/work packages.** P-023, P-029, P-036; W5 §§14.1, 14.3, 14.5,
   14.6, 15.1; WP6.3/A7.

## 4. R1 finding retest matrix

| R1 finding | Remediation retest | R2 disposition |
|---|---|---|
| C-1 — self-attested acceptance/content | Candidate is strictly `proposed`; pack review/acceptance fields are forbidden; exact external subjects, distinct actor set, owner grant, review-before-owner, and frozen hashes are present. External record type/outcome/acceptor/producer/time semantics and raw-byte identity still fail the probes above. | **Open — Critical (C-1) plus M-1.** |
| M-1 — family/object/schema identity conflation | `TDL_private`, future `asp_<UUID7>`, TDL schema ID, schema version, pack content subject, and contract content subject are separate. Both schema IDs are unique; the legacy generic ID is absent. | **Closed for identity separation.** Raw-byte realization remains M-1, not identity conflation. |
| M-2 — references/fixtures/lane relations not exact | Exactly 6 contract + 6 skill rows and 52 fixture rows are complete-row compared. Missing, duplicate, alias, kind swap, foreign-valid, and lane swap/dangling attacks reject. Pending rows block current acceptance. Pending-set and obligation-enforcer relations remain inconsistent. | **Partially closed — M-2 and M-3 remain.** |
| M-3 — incomplete free-text six-lane obligations | 69 exact typed rows cover W5 §§13-19 and WP6.3 across six lanes. Free-text additions, missing/duplicate/swapped rows reject; Partial, unable-to-grade, and failed-proof cannot become pass in the candidate policy. | **Closed for typed obligation coverage.** |
| M-4 — durable absence/status self-invalidates | Future-file absence is task-local/unbound; durable candidate state is `proposed`; review/owner state is external; the hash dependency order has no self-edge. The positive eligible fixture is nevertheless internally contradictory. | **Original absence defect closed; future-state proof requires M-2.** |

## 5. Six-lane coverage and relation matrix

| Lane | Typed obligations | Governing refs | Lane fixtures | W5/WP6 minimum coverage | Relation verdict |
|---|---:|---:|---:|---|---|
| Topology | 11 | 4 | 8 | Persistence object/construction, W2, filtration/metric/order, threshold/truncation, landmark, coefficient field, dimensions/essential classes, benchmark, scaling/direction, subject identity, interpretation limits | **Complete rows; FAIL relation:** `paper-claim-trace` enforces interpretation but is absent from lane governing refs. |
| Stochastic / null | 11 | 6 | 7 | Null hypothesis/operation, exchangeability, Markov order/strata, unit/B, RNG/seed, denominator/formula, tested-object mutation/no-op, checkpoint/resume, multiplicity, diagnostic separation | **Complete and relationally closed.** Two referenced contracts remain pending and correctly block current acceptance. |
| Statistical / panel | 12 | 4 | 5 | Estimand, population, eligibility/denominator, dependence, missingness, weights, variance, multiplicity, sensitivity, formula/software, boundary cases, claim-type limits | **Complete rows; FAIL relation:** `paper-claim-trace` enforces claim-type limits but is absent from lane governing refs. |
| Representation | 10 | 3 | 5 | Fit/transform authority, frozen model/loadings/scaler/labels, training population, recoding, windows/dimensions/vintage, fingerprint, transform-only, comparability, prohibited refit/fallback, uncertainty | **Complete and reference-relationally closed.** |
| Output / provenance | 11 | 3 | 12 | IDs/hashes, code/environment, parameters/seeds/sample, roots/date, no overwrite, schema/cache/regeneration, comparison fields, supersession, exact bytes, vault/claim routing, distribution boundaries | **Complete rows; FAIL relation:** `paper-claim-trace` enforces routing but is absent from lane governing refs. |
| Paper claim | 14 | 3 | 7 | Accepted result/evidence IDs, decision outcome, wording/type/strength/scope/uncertainty, limitations/disclosure, negative/Partial restrictions, independent review, Stephen promotion, no escalation, result/claim separation | **Complete and relationally closed.** |
| **Total** | **69** | — | **52 exact catalogue rows** | All six WP6.3 lanes and the complete W5 §15.1 TDL pack minima are represented through typed rows drawing on W5 §§13-19. | **Three lane-enforcer relation defects remain.** |

Scientific adequacy remains prospective and human-review-only. No topology, null,
statistical, representation, result, or claim outcome was evaluated or accepted here.

## 6. Identity, lifecycle, and decision matrix

| Decision / invariant | R2 disposition | Basis |
|---|---|---|
| Future path `.research-system/packs/tdl-private-assurance.yaml` | **Keep proposed; not created.** | Collision-free, Git-tree absent, and scope-correct. |
| `TDL_private` | **Keep as family/name only.** | Accepted W5 §15.1 name; no longer used as object identity. |
| Future `asp_<UUID7>` object | **Keep proposed; blocked.** | Strict pattern exists, but W1 registry has no `assurance_pack: asp` kind/object. |
| TDL schema ID `ars://assurance/packs/tdl-private/1.0` | **Keep proposed.** | Unique, TDL-specific, and non-conflated with contract/family/object IDs. |
| Schema version `1.0.0` | **Keep proposed.** | Unique and conventional; gains authority only after corrected exact review/acceptance. |
| Candidate `proposed` only | **Keep.** | Schema forbids candidate pack review/acceptance fields. |
| External requirement/review/owner lifecycle | **Amend — C-1.** | Hash resolution exists, but record semantics and canonical actor/type/time bindings are incomplete. |
| Raw candidate Git-blob + SHA-256 subject | **Amend — M-1.** | Contract is correct; executable oracle hashes normalized JSON instead. |
| Required sequence | **Keep ordering; amend positive proof — M-2.** | Contract → review → Stephen acceptance → W1 object → candidate → independent review → Stephen acceptance → consumer is acyclic, but pending relation is not cleared. |
| Exact 12 reference rows | **Keep rows; amend relations.** | Six contracts + six skills are complete and content-addressed; two pending rows block; lane-enforcer relation has M-3. |
| Exact 52 fixture rows | **Keep catalogue; strengthen executable bindings.** | Complete-row closure works, but C-1/M-1/M-2 attacks demonstrate that catalogue presence does not prove every stated mutation fails. |
| Exact 69 obligation rows | **Keep.** | Complete typed W5/WP6 coverage; only relation wiring needs M-3. |
| TDL-private consumers/distribution | **Keep.** | Exact five consumers and closed publication/path/data controls reject widening. |
| P-031 | **Keep / unaffected.** | No pilot, WP6.4, or Gate 6 credit. |
| P-032 | **Keep / unaffected.** | No W11 object, migration, or dual ownership. |
| P-033 | **Keep / unaffected.** | No live transport, profile, degraded mode, or dispatch. |
| P-034 | **Keep / unaffected.** | Consolidation remains downstream. |
| P-035 | **Keep / unaffected.** | No WP6.2 protocol, live evidence, or eligibility action. |
| P-036 | **Keep; do not overread.** | It approves the exact WP6 plan as planning authority, not this remediation contract or a future pack. |

## 7. Decision / invariant → enforcement → test matrix

| Invariant | Declared enforcement | Committed/external attack | Result |
|---|---|---|---|
| Candidate cannot self-attest acceptance | Proposed-only closed schema; no pack review/owner fields | `candidate_state=accepted`, added review hash, producer-only N/A | **PASS — rejected.** |
| External requirement is accepted and producer-independent | External record ID/hash plus actor distinctness | Rejected outcome; producer as acceptor; foreign type | **FAIL — all accepted (C-1).** |
| External review/owner records are canonical | Hash manifest, review subject, owner review hash, owner grant | Wrong review producer; reviewer alias; foreign owner type | **FAIL — all accepted (C-1).** |
| External time order is coherent | Candidate time order; review before owner | Candidate effective/expiry inversion; requirement accepted after owner | **Partial — candidate inversion rejects; late requirement accepts (C-1).** |
| Raw candidate content address is exact | Declared Git-blob UTF-8/LF + SHA-256 | Same parsed YAML, different raw comment bytes | **FAIL — one computed subject for two raw blobs (M-1).** |
| Contract/schema/family/object identities are one-to-one | Separate strict fields and schema IDs | Legacy generic ID lookup; `TDL_private` as object ID; schema subject swap | **PASS — rejected/absent.** |
| Exact reference rows | Complete-row equality + independent ID closure | Missing, duplicate/different body, alias, kind swap, foreign valid, inline copy | **PASS — rejected.** |
| Pending references block acceptance | `require_active_references` | Current contract acceptance | **PASS — blocked.** |
| Pending relation can clear coherently | Positive eligible fixture | Active/eligible rows retained in current-pending list | **FAIL — acceptance passes contradiction (M-2).** |
| Lane reference relations are exact | Exact lane set + allowed-lane check | Dangling and whole-set swap; obligation enforcer omitted from lane set | **Partial — committed attacks reject; three frozen mismatches pass (M-3).** |
| Exact fixture rows | Complete-row equality + independent ID closure | Missing, extra, duplicate/different body, attack-class swap | **PASS — rejected; 52 rows exact.** |
| Exact typed obligations | Complete-row equality + independent per-lane IDs | Missing, duplicate, cross-lane swap, free-text field | **PASS — rejected; 69 rows exact.** |
| Consumer/distribution boundary | Strict constants/exact list | Consumer widening, absent controls, contradictory public path | **PASS — rejected.** |
| Coordinated expected/observed replacement | Frozen contract oracle and external hash manifest | Coordinated contract+candidate row change; candidate+review+owner change against frozen manifest | **PASS for tested object hashes; FAIL for unvalidated semantic record changes and raw-byte equivalence.** |
| No-op, degenerate, and claim-escalation attacks | Fixture catalogue rows | Exact row presence only; no dedicated executable mutation in this file | **Coverage gap; future binding still required.** |
| Future file absence is task-local | Unbound scope test | Git tree/filesystem check | **PASS now; does not self-invalidate durable contract.** |

## 8. Validation and independent test evidence

All commands ran against the exact reviewed checkout with
`PYTHONDONTWRITEBYTECODE=1`, pytest cache disabled, coverage disabled, and an external
`COVERAGE_FILE`. Repository `.coverage`, `.pytest_cache`, and relevant `__pycache__`
paths were absent before and after; Git remained clean.

| Check | Result |
|---|---|
| `python .claude/hooks/contract_binding_check.py --validate-only` | Exit 0; `all gates passed against 101 contract(s)` |
| `python .claude/hooks/contract_binding_check.py --no-pytest` | Exit 0; `all gates passed against 101 contract(s)` |
| Focused pytest with `-q -p no:cacheprovider --no-cov` | Exit 0; **10 passed** |
| Contract-schema object closure | **40/40** object nodes closed |
| Pack-schema object closure | **25/25** object nodes closed |
| Schema registry | TDL pack ID count 1; WP6.3 contract ID count 1; legacy generic count 0; no duplicate IDs |
| Source/reference Git blob + SHA-256 checks | Passed in focused suite for every declared governing source and all 12 references |
| `git diff --check origin/main..HEAD` | Pass |
| Live PR/remote head | Both equal exact reviewed commit |
| Future pack path | Absent from filesystem and `HEAD` Git tree |
| Future object/registry kind | No `assurance_pack` / `asp` entry |
| Required public callable | No production definition; only contract/schema/test mentions, as hard-stopped |

Passing framework gates do not override the independent negative probes. The gates
exercise the committed oracle; C-1/M-1/M-2/M-3 show where that oracle does not enforce
its own stated contract.

## 9. Final subject provenance

All final subject blobs are strict UTF-8/LF Git blobs with zero CR bytes and a terminal
LF.

| Path | Git blob | Raw-blob SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `c64a093dca6d6240b27b58dffa54202a5abb61da` | `74c02d6fd470ae7f6c46400fb973ef62547ff1ef1f23fc39a9ba5911e944a39d` |
| `.research-system/schemas/assurance/assurance-pack.schema.json` | `5e9ef138abc69e2830fc6547bb2352293a0ddb43` | `c3f9b5959eb6c5efb4ead4dd30b9091759ce0450ca13d9a19983ad536229c2a1` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `e2d4eb1ab70ecf889598527a14bb73d52fd77908` | `8e70cf2d64ae177b8f94d346faa49a4043f832a3311ca64c4c0fac3a404e64f0` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `03b3065807e70e0b92e7e910306cf17d966af02f` | `67d7a0e5b277963c0c097ecbcb76d651c5280e8c2028bb8e6d6935c949e639b8` |
| R1 report | `fcd02142d2775a4dae5aaea0a258bec05fbd6ae0` | `8553e70ef68e772555ccab20b518c185e38d940840235e73bc8b2de67814a8e1` |

## 10. Required revision plan

### Immediate corrections

1. Define and bind strict external record schemas and close every C-1 record semantic,
   actor, relation, outcome, authority, and time-order mutation.
2. Hash exact raw pack bytes, not a normalized parsed object, and bind review/owner
   subjects to that byte identity.
3. Make pending IDs a derived exact relation, allow a cleared future set, and validate
   the positive lifecycle fixture against the contract schema and semantic oracle.
4. Repair the three obligation-to-lane reference relations and add relational mutation
   tests.
5. Bind catalogue-only no-op, degenerate, and claim-escalation rows to executable
   future producer/loader-seam negatives before pack acceptance.
6. Re-run both framework gates, the focused suite, raw-byte probes, external-record
   semantic probes, and a new distinct-authority review of the exact new revision.

### Owner decisions and later dependencies

- Stephen may consider the corrected exact contract/schema subjects only after a fresh
  independent review returns an acceptable verdict.
- W1 authority must separately materialize the `assurance_pack` ID kind/object after
  contract acceptance; this review does not authorize it.
- The two pending TDL contract references must become accepted/active in a superseding
  exact upstream revision before any pack owner acceptance.
- Only then may a distinct future producer author the proposed pack. The pack itself
  still requires exact-byte scientific review and Stephen acceptance.
- WP6.4, A7/Gate 6 credit, research execution, results, claims, live capability,
  migration, and eligibility remain downstream and uncredited.

## 11. Practicality and residual risk

The required changes are small relative to the authority risk: strict record-profile
validation and relation checks are deterministic; raw-byte hashing is one Git-native
operation; and the pending/enforcer crosswalks are set equalities. None requires
scientific compute or production implementation in this upstream task.

After correction, scientific adequacy, reviewer capability, interpretation limits,
consumer fitness, and paper language will remain deliberately human-gated. Those are
future pack-review risks, not reasons to weaken this upstream contract.

## 12. Hard stops and change log

| Hard stop | R2 evidence | Status |
|---|---|---|
| No future pack file | Filesystem and Git object lookup absent | **Held** |
| No future `asp_` object/registry mutation | Registry contains no assurance-pack kind | **Held** |
| No production semantic interface implementation | Required callable absent from production Python | **Held** |
| No subject-file remediation by reviewer | Only this R2 report is changed | **Held** |
| No WP6.4 / Gate 6 / A7 credit | Diff contains no such artifact or decision | **Held** |
| No result, claim, live call, migration, eligibility, or Gate 5 action | Five-file subject scope plus read-only review evidence | **Held** |
| No self-review approval | R2 verdict is `rework_required`; Stephen acceptance remains pending | **Held** |

**Files intentionally changed by this R2 task:** this report only.<br>
**Reviewed contract/schema/test/R1 bytes changed:** none.<br>
**Final verdict:** `rework_required`.
