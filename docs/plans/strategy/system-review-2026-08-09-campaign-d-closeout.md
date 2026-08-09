# System Review 2026-08-09 — Campaign D Closeout

**Campaign:** Contract and runtime semantic coverage

**Decision:** Approved by Stephen on 2026-08-09

**Candidate branch:** `codex/system-review-2026-08-09-d-contract-semantics`

**Base:** `9736c900fd4f72e84b2208eeff0dcfb2a2b44106`

**Result:** 16 of 16 mapped observations resolved

## Observable change

The reusable author/reviewer workflow now derives coverage from the governed
set instead of accepting hand-maintained subsets. It requires kernel equality
coverage for recorded constants, executable semantic boundaries, independent
discovery of durable enforcement surfaces, explicit catalogue-versus-runtime
activation, lifecycle adjacency, non-unit command/event cardinalities,
command-bound recovery, and event-first authority materialization. The stale
core-schema filename/count snapshots were removed; closed-object properties now
run over every schema actually present in the catalogue directories.

## Observation dispositions

| Observation | Disposition | Evidence |
|---|---|---|
| 86 | ACTIONED — already enforced, generalized in review guidance | Lean acceptor controls reject inequality-only pins and surface the recorded/derived discrepancy; adversarial review now requires a derived-LHS kernel equality. |
| 87 | ACTIONED — already enforced, generalized in review guidance | The Lean acceptor machine-checks the complete `artefact_constants` set; review guidance now diffs the contract pin list against derived equalities. |
| 111 | ACTIONED — already enforced, generalized in contract guidance | T2/live-issue contracts carry exact relational boundary witnesses and mutation controls; schema design now requires a positive witness through coupled representations and a decisive type/range negative. |
| 117 | ACTIONED — already implemented | The live-issue binding fixes canonical bundle, projection, normalized operation, provider-native selector, exact argv profile, timeout, and response accounting, with mismatch controls. |
| 128 | ACTIONED — already implemented, generalized at finding closure | WP6.3 review provenance iterates the contract-declared record types; adversarial review now dispositions every sibling governed by the same clause. |
| 129 | ACTIONED — already implemented, generalized in contract guidance | Provider/model/argv constraints are authority-bound and tested relationally; narrower environment literals now require authority rationale and inside/outside fixtures. |
| 131 | ACTIONED — already implemented, generalized in contract guidance | Executable tests consume declared governed sets and close the durable test surface; the authoring skill now requires a mutation proving a newly declared member is enforced. |
| 138 | ACTIONED — simplified in this campaign | Removed exact filename and `len == 96` snapshots from closed-object tests; the property derives from the full directory glob and still fails on any malformed sibling. |
| 139 | ACTIONED — already implemented | Durable test closure is exact while retired task-local names may disappear; missing durable, undeclared, and overlapping names fail. |
| 147 | ACTIONED — already implemented, generalized in contract guidance | Runtime registries activate only explicit accepted `SchemaBinding` rows; inert catalogue schemas fail `validate_active`, and producer bindings are tested by family. |
| 01KYV4AHVH5DRSGZMXD8YPR0GN | ACTIONED — existing lifecycle matrices retained, generalized in TDD | C1 and Message integration suites compose active transitions and assert full no-mutation state; TDD now derives sequences from the accepted adjacency matrix. |
| 01KYXYHVJQZ3DAVF8GQG67V10D | ACTIONED — already implemented | All twelve accepted external record classes run through writer and resolver, including nested references, invalid date-time, and revision-gap controls. |
| 01KYYDXV2C93X7S3P8R3WDNBPV | ACTIONED — already implemented, generalized in TDD | Runtime binding tests cover ClaimDispatch's ordered two-event atomic batch and complete catalogue rows; TDD now requires many-to-one and one-to-many mutations. |
| 01KYZ4VJAG6JVF1T3ZX5JRE2NM | ACTIONED — already implemented, generalized at review closure | W11 custom/no-op callback controls attack downstream numeric-domain shapes; adversarial review now traces every consumer-read field and shape class. |
| 01KZ2FR7BMBDNHJVBEAYJPD4P6 | ACTIONED — already implemented, generalized in TDD | Message and C1 public-seam tests reject changed command identities before repairing missing index/receipt state and prove exact retry recovery. |
| 01KZ5BSJV5B79JTMSMSRNX0N9X | ACTIONED — already implemented, generalized in TDD | ResourceGrant materialization appends the authorizing event first; event-only interruption repairs without a second event and invalid/orphan objects remain unusable. |

## Controls and validation

- Lean constant controls: inflated equality discrepancy, inequality-only
  rejection, and accepted kernel equality.
- Live-issue semantic set: complete schema identities, canonical preimages,
  argv/model/timeout/accounting joins, relational near-misses, zero-effect
  rejection, replay, and accepted successor overlay.
- External records: exact twelve-class writer/resolver coverage, date-time
  format checking, nested references, and contiguous revision history.
- Lifecycle controls: changed-command missing-index rejection, ClaimDispatch
  residue recovery, and event-only ResourceGrant repair.
- Downstream consumer controls: W11 custom and no-op callback malformed-domain
  matrices.
- Candidate-focused result: 124 passed (97 in the live-issue/Lean partition and
  27 across records, registry, lifecycle, recovery, and downstream consumers).
- Dual-tree skill sync, guide checks, and patch hygiene pass.

## Baseline reds kept separate

The broad semantic selection exposed two failures already present at exact base
`9736c900` and unrelated to this candidate's files:

1. `test_accepted_t2_wp6_1_t1a_bytes_remain_exact` reports the protected
   identity for `wp6_2_t2_authority_validation.py` is stale (`a9211047...`
   expected, `607a6f9...` at `HEAD`).
2. The WP6.3 governed-set mutation test reaches the existing canonical-checkout
   reference drift first: all six pinned contract files and all six pinned skill
   files hash differently from their accepted rows when resolved from current
   working-tree bytes, while their `HEAD:path` blobs remain the accepted blobs.

These reds are evidence that the existing exact-reference controls are live;
they are not rewritten or waived by Campaign D.

## Simplification disposition

No second runtime registry, lifecycle harness, or contract catalogue was added.
Two stale hand-maintained schema counts were removed, and the general rules were
consolidated into three existing skills that already own design, review, and
implementation behavior.
