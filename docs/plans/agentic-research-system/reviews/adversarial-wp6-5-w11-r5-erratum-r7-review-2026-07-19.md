# Adversarial WP6.5 W11 R5-erratum R7 review — 2026-07-19

## 1. Review identity and independence

- **Reviewed PR:** #121
- **Exact reviewed subject:** `4e7ec91a7815b808ae0ee8af3421eab20840094e`
- **Remote branch:** `pipe/ars-wp6-5-w11-spec`
- **Local review branch:** `codex/wp6-5-w11-r3-remediation`
- **Base:** `main`; observed base tip `5795a18b5a35279c834719ebfe06176fbfd5810b`
- **Merge base:** `4e6fd0cb26c04ff9707c3183f663461d752b53b9`
- **Primary remediation under review:** additive R5 erratum in commit
  `4e7ec91a7815b808ae0ee8af3421eab20840094e`
- **CodeRabbit trigger:** review `4729612870`, submitted against
  `ef300900476a7479e7926fc345279bb09800447c`
- **CodeRabbit comments:** `PRRC_kwDOQn1MU87XJRLV` / `discussion_r3609531093`
  and `PRRC_kwDOQn1MU87XJRLW` / `discussion_r3609531094`
- **Review mode:** fresh independent exact-head adversarial review. Earlier R5/R6
  conclusions were treated as provenance claims and checked against current files,
  Git identities, the live PR, and the originating CodeRabbit comments.

At entry and immediately before this report was created, the working directory was
`C:\Users\steph\.codex\worktrees\cfe3\TDL`, the symbolic branch was
`codex/wp6-5-w11-r3-remediation`, and local `HEAD`, the local origin-tracking ref,
`git ls-remote` for `refs/heads/pipe/ars-wp6-5-w11-spec`, `git ls-remote` for
`refs/pull/121/head`, and GitHub PR #121's `headRefOid` all equalled the exact reviewed
subject. The worktree was clean. The report is the only authorized post-review write.

## 2. Verdict

**`approved`**

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 0 |
| Minor | 0 |

The additive erratum closes both exact CodeRabbit findings without changing the
immutable R5 report or any normative W11, decision, evidence-authority, implementation,
acceptance, transition, or claim boundary. No open finding remains in the exact-head PR
delta.

This is review evidence only. It does not accept W11 for Stephen, merge PR #121,
authorize implementation, approve a first ownership-transition batch, or close either
D-G6-4 limb.

## 3. Exact CodeRabbit finding disposition

### `PRRC_kwDOQn1MU87XJRLV` — malformed R3-M2 label

**Disposition: Closed additively.**

The originating comment asked that R5 line 110's historical catalogue label say the
bootstrap “required **a** prohibited runtime” while retaining its ID, status and
explanation. Erratum §2 identifies the exact original text and supplies exactly that
corrected label. It expressly limits the defect to the omitted article and preserves
R3-M2's ID, `Closed` disposition, explanation, R3 evidence and R5 verdict. R5 itself is
unchanged.

### `PRRC_kwDOQn1MU87XJRLW` — action-boundary provenance and PR identity

**Disposition: Closed additively.**

Erratum §3 replaces the later interpretation of R5 §15 with an epoch-aware chronology:

1. R5 reviewed exact subject `892d1d1650cdcf71d2a886318e174a18e11d5de0`
   read-only through its exit checks.
2. Creating and provenance-tightening the R5 evidence file was the reviewer's sole
   authorized post-review file write; the reviewer did not stage, commit or push it.
3. The main agent recorded only that report in commit
   `07d2d1315accb211d4c257cc7ea28985871dc4f1`, whose parent is the exact R5 subject.
4. The reviewed PR is correctly identified as #121. PR #124 is explicitly described as
   an untouched cross-PR boundary, not as the reviewed PR.
5. Apart from report creation, no reviewed artefact, branch, authority, acceptance,
   migration or claim state changed.

This is consistent with the Git sequence and prior evidence. Commit `07d2d131...` adds
only the R5 report; `c21b366caa751265e455435f23d1232f0bb6220c` changes only the dated
live-evidence row; `ef300900476a7479e7926fc345279bb09800447c` adds only R6; and
`4e7ec91...` adds only the erratum. R6 discloses that its reviewer authored the R5
evidence file and treats that file only as mechanically checked provenance, not as
independent R6 qualitative evidence. GitHub identifies #121 as the open PR for branch
`pipe/ars-wp6-5-w11-spec`; the read-only #124 check showed its separate
`pipe/ars-wp6-1-task-lifecycle` branch and an `updatedAt` preceding the R5/erratum epoch.
No contrary PR #124 action evidence was found.

## 4. Immutable evidence identities

### R5 report

The current R5 file remains byte-identical to the evidence first recorded in commit
`07d2d1315accb211d4c257cc7ea28985871dc4f1`:

- path: `adversarial-wp6-5-w11-spec-remediation-r5-review-2026-07-19.md`;
- commit blob: `057789ec492db7e12560b0ec22aea439af569aad`;
- current Git blob: `057789ec492db7e12560b0ec22aea439af569aad`;
- current file SHA-256:
  `f7c5d37736661d7c62b7ee94420e185eb93f73796b0347ea7ed439e46cee83b2`;
- `git diff --exit-code 07d2d1315accb211d4c257cc7ea28985871dc4f1 -- <R5 path>`:
  no difference.

The two CodeRabbit corrections therefore do not rewrite historical evidence. The
erratum is a later, separately content-addressed interpretation record:

- erratum Git blob: `a6f7321353583b94a7735671af3c2479f4c15f00`;
- erratum SHA-256:
  `ad8037f913518ee39aae8f41374717abc0c7ace2ec0639f78147d1275a20651f`.

### Normative and prior-review surfaces

- W11 Git blob: `f90729d0c42a0de98d064fac0824d1969c871c82`;
  SHA-256 `3011de88b6826b27bbc105dbf2ce0e2f3fa095666dec082aa0e460be9cca0799`.
- Decision-register Git blob: `9eecbb7084fb2c9c840c4f233201d964fe08808b`;
  SHA-256 `bb57bef4acd2e051873b146389e42aae69f5715884684c4f69b575cd0cb7e922`.
- Live-evidence-register Git blob:
  `92cc132a938bfd8718867ea8516a25f7f777e92c`.
- R6 Git blob: `f105a4f8566585622fad976c0cc37d15406d8d22`;
  SHA-256 `8cbe0f88a4e5fb0813e2815625a82c0e8bba5eb180dc26bf85fd0a78d6a6c7c9`.

W11 and the decision register have no difference from the R5-reviewed subject
`892d1d1650cdcf71d2a886318e174a18e11d5de0`; R6 has no difference from its recording
commit `ef300900...`. The erratum changes none of these identities and does not alter
R5's or R6's `approved` verdict or zero-finding counts.

## 5. Full exact-head regression and adversarial disposition

The full PR delta was rechecked rather than treating the one-file latest commit as the
entire review surface.

| Attack surface | R7 disposition |
|---|---|
| Evidence fidelity and producer separation | Pass. Content candidates, independent byte observations, reviews, external owner acceptance and later runtime consumption remain separate. The erratum adds no authority-bearing input. |
| Hash dependency DAG | Pass. Content cannot contain its own storage/review/acceptance; relation preimages exclude self, enclosing and later hashes; the external catalogue envelope precedes runtime and OR-140 genesis. |
| Owner catalogue closure | Pass. Exactly 81 rows, OR-001–OR-041 and OR-101–OR-140, with no missing, duplicate or extra ID and no absent command, receipt, reducer or projection tag. |
| Receipt/test identity closure | Pass. All 81 receipts are unique; the literal positive, mutation and retry identities remain bound by owner-row number. |
| W4/owner-row join | Pass. The six review-request discriminants are exactly OR-034–OR-038 and OR-040 and remain in the Portfolio Steward allowlist. OR-039 is a verdict row. |
| Verdict/gate separation | Pass. OR-006/007/020/021/039/041 always update Review, while only policy `satisfied` emits aggregate/Candidate reviewed effects. |
| Negative/withdrawn recovery | Pass. Non-satisfying verdicts cannot reach promotion/revisit; replacement binds prior request/verdict and exact new subject or bounded delta. |
| Partial/cancellation overlays | Pass. Spike Partial/cancellation closes attempts and leases; cancellation atomically supersedes an unresolved execution proposal before review/revisit. |
| Dossier exact closure | Pass at specification level. The accepted six-family expected set precedes candidate observation; independently reopened bytes and atomic zero-publication failure remain required. |
| Ownership transition | Pass. Source observation, source-only inventory, mapping acceptance, transition and later cutover closure remain acyclic and one-way. |
| Path/writer and annotation races | Pass at specification level. Legacy/successor writers are disjoint; the accepted legacy annotation epoch is re-observed under lock, atomically fenced and followed by successor routing. |
| Authority and acceptance boundaries | Pass. The erratum explicitly denies acceptance, implementation, transition, cutover, result, eligibility and claim actions. It does not narrow P-004/P-021/P-032/P-034. |
| Immutable-review handling | Pass. R5 is preserved byte-for-byte; both corrections are additive and tied to exact comment, review, commit, blob and file identities. |

The strongest new attack was whether the chronology correction could make the R5 file
part of its own reviewed subject or claim that R5 independently reviewed its later
evidence write. Erratum §3 explicitly denies both constructions. The Git parent chain
also makes the order constructible: reviewed subject first, R5 provenance commit next,
normative evidence clarification next, R6 evidence next, CodeRabbit finding next, and
the additive erratum last.

## 6. Complete invariant disposition

| Invariant | R7 disposition |
|---|---|
| W11-I01 | Pass at specification level; immutable state-free definitions unchanged. |
| W11-I02 | Pass; exact identities and relation preimages remain acyclic. |
| W11-I03 | Pass; required dependency/block graph remains acyclic. |
| W11-I04 | Pass; Assay authority and reviewed recovery remain exact. |
| W11-I05 | Pass; Assay/Spike evidence cannot resolve promotion. |
| W11-I06 | Pass; Partial/cancellation review and resource cleanup remain closed. |
| W11-I07 | Pass; promotion requires exact policy-satisfied review and human authority. |
| W11-I08 | Pass; PROMOTE remains limited to one named next design step. |
| W11-I09 | Pass; dossier expected-set content remains literal, external and acyclic. |
| W11-I10 | Pass; dossier exact closure remains independently re-resolved. |
| W11-I11 | Pass; dossier publication remains atomic. |
| W11-I12 | Pass; all 81 owner rows, W4 joins, receipts and tests reconcile. |
| W11-I13 | Pass; generated views remain non-authoritative. |
| W11-I14 | Pass at design level; required unavailable Windows races remain Partial. |
| W11-I15 | Pass; annotations remain evidence until separately acted upon. |
| W11-I16 | Pass; one owner and one accepted source-to-target relation remain required. |
| W11-I17 | Pass; partial transition never repurposes the legacy path. |
| W11-I18 | Pass; cutover requires complete closure, accepted epoch and atomic fence. |
| W11-I19 | Pass; whole-path cutover remains one-way. |
| W11-I20 | Pass; projection rebuild remains deterministic and authority-neutral. |
| W11-I21 | Pass; Portfolio Claim cannot compensate for W5 claim authority. |
| W11-I22 | Pass; replay fails closed and genesis consumes only external acceptance. |

## 7. Complete pre-implementation test-family disposition

| Test | R7 disposition |
|---:|---|
| 1 | Pass as specified; schema, DAG and complete owner-row surface unchanged. |
| 2 | Pass as specified. |
| 3 | Pass; complete-row equality and coordinated expected/runtime attacks retained. |
| 4 | Pass; all outcome verdict, condition, replacement and recovery branches retained. |
| 5 | Pass; foreign-valid relation substitutions retained. |
| 6 | Pass as specified. |
| 7 | Pass; only policy satisfaction emits reviewed effects; cleanup/recovery retained. |
| 8 | Pass; exact human option authority retained. |
| 9 | Pass; acyclic expected set and six-family negative closure retained. |
| 10 | Pass; zero-publication failure injection retained. |
| 11 | Pass; all 81 owner-row retries, W4 joins and effect projections retained. |
| 12 | Pass; Scout source/judgment boundary retained. |
| 13 | Pass; annotation and pre-/post-fence race cases retained. |
| 14 | Pass at design level; unavailable required Windows coverage remains Partial. |
| 15 | Pass; source/inventory/mapping/target relational substitutions retained. |
| 16 | Pass; partial-transition ownership/path separation retained. |
| 17 | Pass; projection deletion/rebuild neutrality retained. |
| 18 | Pass; whole-path closure, epoch fence and race attacks retained. |
| 19 | Pass; external-envelope bootstrap and conflicting-genesis tests retained. |
| 20 | Pass; portfolio prose/Claim cannot satisfy result or claim authority. |

## 8. Decision, gate and assurance boundary

| Decision/gate | R7 disposition |
|---|---|
| P-004/P-021 | Keep. Exclusive legacy/successor ownership and physical writer separation are unchanged. |
| P-005/P-022 | Keep. Independent review and Stephen's reserved Decisions remain distinct and non-compensable. |
| P-026 | Keep. This remains specification and review evidence only. |
| P-032 | Keep. W11's canonical successor boundary is unchanged. |
| P-034 | Keep. Transition and cutover remain content-addressed, one-way and epoch-fenced. |
| P-036 | Keep. WP6 launch-basis controls are unchanged. |
| D-G6-4 bounded policies | Previously accepted; the erratum neither reopens nor broadens them. |
| D-G6-4 limb 1 | Open pending Stephen's explicit exact-revision acceptance. |
| D-G6-4 limb 2 | Open pending separate approval of the first content-addressed ownership-transition batch. |
| W11-A1 | Open/optional; omission remains conforming. |

All six assurance lanes remain dispositioned as design/specification controls. This
review establishes interface and provenance consistency only; it does not establish
scientific adequacy, result validity, eligibility or claim authority.

## 9. Mechanical and external validation evidence

- `python -B .claude/hooks/contract_binding_check.py --validate-only`:
  all gates passed against **101 contracts**.
- `python -B .claude/hooks/contract_binding_check.py --no-pytest`:
  all gates passed against **101 contracts**.
- `PYTHONDONTWRITEBYTECODE=1` was set for both commands.
- Owner rows: **81**, exact ranges OR-001–OR-041 and OR-101–OR-140; no missing,
  duplicate or extra ID.
- Receipts: **81**, all unique; every owner row contains command, receipt, reducer and
  projection tags.
- Invariants: exact `W11-I01`–`W11-I22`.
- Pre-implementation tests: exact sequence 1–20.
- Eleven changed Markdown files: zero table-width mismatches, zero unbalanced code
  fences, and zero missing local Markdown link targets.
- `git diff --check main...4e7ec91a7815b808ae0ee8af3421eab20840094e`:
  passed.
- Codacy Static Code Analysis check run `88141907271` completed `success` at the exact
  head with **zero annotations**.
- PR #121 was open, non-draft and mergeable at the exact head.
- No CodeRabbit review was triggered by R7.

## 10. Residual risks

- The erratum remains a separate interpretation record; consumers must resolve it with
  the pinned immutable R5 identity rather than quote the superseded R5 lines alone.
- Future generated reducers must preserve the difference between an always-recorded W2
  Review verdict and policy-conditional aggregate/Candidate effects.
- Future catalogue/schema/runtime work must keep expected and observed producers
  separate and preserve the external acceptance envelope before genesis.
- Required Windows filesystem race cases that cannot execute on the target platform
  remain Partial rather than pass.
- Every later legacy observation, mapping, transition and cutover requires fresh exact
  bytes; the dated evidence register is not migration authority.
- W9/W10 and implementation specifications may consume but not narrow W11's ownership,
  path, review or gate controls.
- Interface conformance does not establish scientific adequacy, result acceptance,
  eligibility or claim authority.

## 11. Change log and action boundary

This review created only
`adversarial-wp6-5-w11-r5-erratum-r7-review-2026-07-19.md` after the clean exit check.
It did not modify the erratum, R5, R6, W11, the evidence register, the decision
register, schemas, runtime, projections or vault state. It did not stage, commit, push,
comment on or resolve a PR thread, trigger CodeRabbit, merge, accept W11, authorize
implementation, admit or transition an item, cut over a path, approve a transition
batch, or perform any result, eligibility or claim action. No other PR was mutated.
