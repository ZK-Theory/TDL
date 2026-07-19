# Adversarial WP6.5 W11 CodeRabbit remediation R6 review — 2026-07-19

## 1. Review identity and boundary

- **Reviewed PR:** #121
- **Exact reviewed subject:** `c21b366caa751265e455435f23d1232f0bb6220c`
- **Branch:** `pipe/ars-wp6-5-w11-spec`
- **Base:** `main`; current remote base `5795a18b5a35279c834719ebfe06176fbfd5810b`; merge base `4e6fd0cb26c04ff9707c3183f663461d752b53b9`
- **W11 SHA-256:** `3011de88b6826b27bbc105dbf2ce0e2f3fa095666dec082aa0e460be9cca0799`
- **W11 Git blob:** `f90729d0c42a0de98d064fac0824d1969c871c82`
- **Live-evidence register SHA-256:** `10e89442035a88753e8d0b629a1b006f8bb7f0e4dbb639f7493399d5f15949af`
- **Live-evidence register Git blob:** `92cc132a938bfd8718867ea8516a25f7f777e92c`
- **Decision-register SHA-256:** `bb57bef4acd2e051873b146389e42aae69f5715884684c4f69b575cd0cb7e922`
- **Decision-register Git blob:** `9eecbb7084fb2c9c840c4f233201d964fe08808b`

At entry and again immediately before this report was created, local `HEAD`, the local
origin-tracking ref, `git ls-remote` for the branch, `git ls-remote` for
`refs/pull/121/head`, and GitHub PR #121's `headRefOid` all equalled the exact reviewed
subject. The worktree was clean at both checks. Report creation is the only authorized
post-review write.

### Provenance-overlap disclosure

The R6 reviewer authored the R5 evidence file
`adversarial-wp6-5-w11-spec-remediation-r5-review-2026-07-19.md`. R5 is therefore
treated here only as a mechanically verified provenance artefact: its exact file/blob
identity, historical reviewed subject, additive erratum, and action-boundary statements
were checked, but its qualitative verdict is not counted as independent R6 authorship
evidence. R6 independence applies to the main-authored live-evidence clarification in
`c21b366caa751265e455435f23d1232f0bb6220c` and to the complete exact-head PR review.

## 2. Verdict

**`approved`**

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 0 |
| Minor | 0 |

Both CodeRabbit findings are closed without weakening the previously reviewed W11
contracts. This verdict is review evidence only. It does not accept W11 on Stephen's
behalf, merge PR #121, authorize implementation, approve an ownership-transition batch,
or close either D-G6-4 limb.

## 3. CodeRabbit finding disposition

### CR-M1 — conflicting legacy lifecycle-authority label

**Disposition: Closed.**

The revised dated live-evidence row now states all of the following together:

- the living backlog is a legacy source referenced by P-004/P-032;
- its authority is limited to items still marked `legacy_owned`;
- its PROMOTE/PARK/KILL labels are not W11 commands, Decisions, or successor lifecycle
  authority;
- no row is imported, adopted, transitioned, or frozen by W11;
- the recorded hash remains a dated observation only; and
- any later transition or cutover requires a fresh handle-bound observation and the
  accepted inventory/mapping contracts.

This is consistent with P-004's exclusive ownership modes and P-032's boundary: legacy
items remain vault/APM-owned until explicit transition, while the vault is not lifecycle
authority for successor-owned Discovery objects. The addendum-level prohibition on
admission, implementation, migration, ownership-transition, result, eligibility,
Decision, and claim authority remains unchanged.

### CR-m1 — inaccurate R4 owner-row range shorthand

**Disposition: Closed by additive, content-addressed erratum.**

The immutable R4 report remains byte-identical to its committed evidence:

- commit: `e68d60f4e9d41fd86495c4259cbc5bc84b77d018`;
- Git blob: `f6c2d1e4d104f0a95bc4bd99e4f01f7bd7a38748`;
- SHA-256: `5860ee1c68234411d75270afa698f8e5675b66d7bb5672deab0c67588c4468d9`.

`git diff --exit-code e68d60f4e9d41fd86495c4259cbc5bc84b77d018 -- <R4 path>`
returned no difference, and the current blob equals the blob stored at that commit. R5's
additive erratum identifies the exact six request rows as **OR-034–OR-038 and OR-040**,
explicitly excluding verdict row OR-039. It identifies CodeRabbit comment
`PRRC_kwDOQn1MU87XI78K` / `discussion_r3609444106`, states that the erratum lies outside
the original R5 review epoch, and does not rewrite or change R4's `rework_required`
verdict or findings.

## 4. Exact-head regression and adversarial disposition

The W11 and decision-register bytes are unchanged from the R5-reviewed subject
`892d1d1650cdcf71d2a886318e174a18e11d5de0`. The only post-R5 changes are the additive
R5 evidence file and the one-row live-evidence clarification. The full exact-head branch
delta was nevertheless rechecked rather than treating the small latest commit as the
entire review surface.

| Attack surface | R6 disposition |
|---|---|
| Expected/observed producer separation | Pass. Candidate content, independent byte observation, review, external acceptance, and runtime consumption remain distinct stages. |
| Hash self/back edges and SCCs | Pass. Relation preimages exclude their own, enclosing, and later hashes; the catalogue bootstrap remains externally accepted before runtime. |
| Owner multiset completeness | Pass. Exactly 81 rows: OR-001–OR-041 and OR-101–OR-140, with no gap, duplicate, extra ID, or empty normative cell. |
| Literal receipts and tests | Pass. All 81 receipts are unique; every row retains the literal positive, negative/mutation, and retry identity convention. |
| Review request/verdict split | Pass. The request rows are exactly OR-034–OR-038 and OR-040; OR-039 is an Assay-cancellation verdict row. |
| Outcome-review effects | Pass. OR-006/007/020/021/039/041 always update Review; aggregate/Candidate effects occur only on the policy-satisfying branch. |
| Negative/withdrawn recovery | Pass. Non-satisfying verdicts produce no reviewed outcome and cannot reach promotion/revisit; replacement binds the prior review and exact subject/delta relation. |
| Partial/cancellation cleanup | Pass. Retry uses fresh aggregates; Spike Partial/cancel closes attempt/lease state and cancellation supersedes an unresolved execution proposal atomically. |
| Source inventory and ownership transition | Pass. Observation is not adoption; source-only inventory precedes mapping acceptance, per-item transition, later closure, and cutover. |
| Path writer and cutover races | Pass at specification level. Handle identity, no-follow traversal, writer separation, accepted annotation epoch, re-observation under lock, atomic fence, and successor routing remain explicit. |
| Dossier admission publication | Pass at specification level. Accepted expected-set identity, independent rehashing, idempotency-before-collision ordering, exact closure, and atomic publication remain intact. |
| Legacy evidence authority | Pass. The revised row preserves only legacy-lane authority and denies successor/W11 command, Decision, and lifecycle authority. |

## 5. Invariant audit

| Invariant | R6 disposition |
|---|---|
| W11-I01 | Pass at specification level |
| W11-I02 | Pass; identities and content authorities remain acyclic |
| W11-I03 | Pass |
| W11-I04 | Pass; review satisfaction remains distinct from verdict recording |
| W11-I05 | Pass |
| W11-I06 | Pass; negative and cleanup routes remain closed |
| W11-I07 | Pass; promotion/revisit requires a policy-satisfied exact review |
| W11-I08 | Pass |
| W11-I09 | Pass |
| W11-I10 | Pass |
| W11-I11 | Pass |
| W11-I12 | Pass; all 81 owner rows and Review effects reconcile |
| W11-I13 | Pass |
| W11-I14 | Pass at design level; unavailable required Windows coverage remains Partial |
| W11-I15 | Pass |
| W11-I16 | Pass |
| W11-I17 | Pass |
| W11-I18 | Pass; epoch/fence and successor routing remain explicit |
| W11-I19 | Pass |
| W11-I20 | Pass |
| W11-I21 | Pass |
| W11-I22 | Pass |

## 6. Pre-implementation test-family audit

| Test | R6 disposition |
|---:|---|
| 1 | Pass as specified |
| 2 | Pass as specified |
| 3 | Pass as specified |
| 4 | Pass; complete verdict and replacement branches remain explicit |
| 5 | Pass |
| 6 | Pass |
| 7 | Pass; satisfaction, negative review, cleanup, and reachability remain explicit |
| 8 | Pass |
| 9 | Pass |
| 10 | Pass |
| 11 | Pass; all owner rows, Review effects, and conditional outcome effects join |
| 12 | Pass |
| 13 | Pass at design level |
| 14 | Pass at design level; unavailable required Windows coverage remains Partial |
| 15 | Pass |
| 16 | Pass |
| 17 | Pass |
| 18 | Pass |
| 19 | Pass |
| 20 | Pass |

## 7. Mechanical and external validation

- `python -B .claude/hooks/contract_binding_check.py --validate-only`: all gates passed
  against 101 contracts.
- `python -B .claude/hooks/contract_binding_check.py --no-pytest`: all gates passed
  against 101 contracts.
- `PYTHONDONTWRITEBYTECODE=1` was set; the worktree remained clean after both commands.
- `git diff --check main...c21b366caa751265e455435f23d1232f0bb6220c` passed.
- `git diff --check 892d1d1650cdcf71d2a886318e174a18e11d5de0..c21b366caa751265e455435f23d1232f0bb6220c` passed.
- Nine changed Markdown files: all code fences balanced, all local Markdown targets
  resolved, and all detected pipe-table widths consistent.
- Owner rows: 81 exact and unique; receipts: 81 unique.
- Invariants: exact `W11-I01`–`W11-I22`; test families: exact 1–20.
- PR #121 was open, draft, and mergeable at the exact head.
- Codacy Static Code Analysis completed successfully for the exact head.
- CodeRabbit's exact-head status was `Review skipped: draft pull request`; it was not
  treated as substantive review evidence and was not retriggered. The two earlier
  substantive findings were verified directly against the current bytes.

## 8. Decision and gate audit

| Decision/gate | R6 disposition |
|---|---|
| P-004/P-021 | Keep. Legacy authority is confined to `legacy_owned`; successor paths and writers remain separate. |
| P-005/P-022 | Keep. Review evidence and human Decision authority remain non-compensable and distinct. |
| P-026 | Keep. This remains specification/review evidence only. |
| P-032 | Keep. The corrected evidence language now matches its legacy/successor boundary. |
| P-034 | Keep. Transition and cutover remain one-way, accepted, content-addressed, and epoch-fenced. |
| P-036 | Keep. WP6 launch-basis constraints are unchanged. |
| D-G6-4 bounded policies | Previously accepted; no broader authority inferred. |
| D-G6-4 limb 1 | **Open pending Stephen's explicit acceptance of this exact W11 revision.** |
| D-G6-4 limb 2 | **Open pending separate approval of a content-addressed first ownership-transition batch.** |
| W11-A1 | Open/optional. |

## 9. Residual risks

- Future generated reducers must preserve the difference between an always-recorded
  Review effect and policy-conditional aggregate/Candidate effects.
- Materialized tests must cover all outcome subject/verdict/condition/replacement
  combinations and every exact owner-row identity.
- Runtime catalogue construction must preserve independent expected/observed producers
  and the external genesis envelope.
- Required Windows race tests that cannot execute on the target platform remain Partial,
  not pass.
- Every later legacy observation, mapping, transition, and cutover requires fresh exact
  bytes; the dated backlog hash is never frozen migration authority.
- W9/W10 and implementation specifications may consume but not narrow the ownership,
  path, review, or gate contracts.
- Interface conformance does not establish scientific adequacy, result acceptance,
  eligibility, or claim authority.

## 10. Review action boundary

This review created only this R6 report. It made no changes to W11, the live-evidence
register, any earlier review, the decision register, schemas, runtime, projections, or
vault state. It did not stage, commit, push, comment on or resolve a PR thread, trigger
CodeRabbit, merge, accept W11, admit or transition an item, cut over a path, approve a
transition batch, or perform any result, eligibility, or claim action. No other PR was
touched.
