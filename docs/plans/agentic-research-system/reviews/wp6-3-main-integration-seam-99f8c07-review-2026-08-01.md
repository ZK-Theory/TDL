# WP6.3 Main-Integration-Seam Exact-Head Review

**Date:** 2026-08-01

**Verdict:** `accept_integration_seam`

**Findings:** 0 Critical, 0 Major, 0 Minor

**Review mode:** fresh independent exact-head integration review; no
implementation remediation

## 1. Exact review subject and authority boundary

| Field | Exact value |
|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\6f50\TDL` |
| Branch | `codex/wp63-scoped-grant-revocation-seal` |
| Integration candidate | `99f8c0753681e4d848d6fc7d1e0e4f0a448438f5` |
| Candidate first parent | `8bb891e2f47bd07919f968408164fa0806a6f685` |
| Candidate second parent | `a464eb5aefed2645da48e4495efa61a27f0e3954` |
| Accepted technical subject | `10759ecaf53d865a801fe5cedaaf15412b36b91e` |
| Independent exact-subject review | `8bb891e2f47bd07919f968408164fa0806a6f685` |
| Live `origin/main` | `a464eb5aefed2645da48e4495efa61a27f0e3954` |
| Common merge base | `6dcdbe85bdbadbbc5c66d0e3cdedd1080d8411b6` |
| Entry worktree state | only preserved Repowise setup changes: `M .claude/CLAUDE.md`, `M .repowise-workspace.yaml` |
| Review-owned path | this report only |

`git rev-list --parents -n 1` identifies the two candidate parents exactly as
the accepted review commit and current main. Both local `origin/main` and a
fresh `git ls-remote origin refs/heads/main` resolved to `a464eb5...`.
No remote branch or open pull request existed for the integration branch at
review time; the path-count evidence below is therefore the exact local
three-dot delta that would be presented to a pull request. Nothing was pushed,
opened, or merged by this review.

This review accepts only the integration seam at `99f8c075...`. It does not
re-review the accepted WP6.3 runtime semantics, change an owner decision, or
infer owner acceptance from the prior independent verdict.

## 2. Ancestry and final path surface

Each required ancestry check exited 0:

- `10759ec...` is an ancestor of `8bb891e...`;
- `8bb891e...` is an ancestor and the first parent of `99f8c075...`;
- `a464eb5...` is an ancestor and the second parent of `99f8c075...`; and
- `10759ec...` is therefore also an ancestor of `99f8c075...`.

The reviewed candidate delta from current main contains exactly 24 paths:
7 WP6.3 authority schemas, 9 production modules, 4 tests, 3 prior review
records, and the shared decision register. This review record makes the final
review-bearing branch delta exactly 25 paths, below the required 100-path
ceiling.

The current-main divergence from the common merge base contains 23 paths, all
under `docs/plans/agentic-research-system/`. Main changed no production,
schema, contract, or test path. Among the 24 accepted WP6.3 paths, the merge
changed only
`docs/plans/agentic-research-system/03-decisions-and-open-questions.md`.
There is consequently no production or dependency overlap that could create a
new runtime incompatibility.

## 3. Accepted WP6.3 blob preservation

For every production, schema, test, and prior-review path in the accepted
branch delta, `git rev-parse 8bb891e:<path>` and
`git rev-parse 99f8c075:<path>` returned the same blob. The complete protected
comparison is:

| Class | Path | Unchanged Git blob |
|---|---|---|
| Schema | `.research-system/schemas/wp6-3-authority/accept-r3-assurance-requirement-policy-action.schema.json` | `84d30db5102ce9c052d31e74dd6c2bdafda0bf8d` |
| Schema | `.research-system/schemas/wp6-3-authority/activate-authority-grant-command.schema.json` | `3e26da4221604369a09ca2818e1f0fe179d61a3d` |
| Schema | `.research-system/schemas/wp6-3-authority/issued-authority-grant-revoked-event.schema.json` | `6a960732ad280b3326f48d8400eb0d422ecfd615` |
| Schema | `.research-system/schemas/wp6-3-authority/owner-authority-administration-decision.schema.json` | `483d9e8352995691dd3499b449f6c45671387afa` |
| Schema | `.research-system/schemas/wp6-3-authority/revoke-issued-authority-grant-command.schema.json` | `37240e4e16534e5544b1c666eb9dfab44feeefb0` |
| Schema | `.research-system/schemas/wp6-3-authority/scoped-authority-grant-activated-event.schema.json` | `926245aba3821e17d1245c3eb64cf5177c69c0cf` |
| Schema | `.research-system/schemas/wp6-3-authority/scoped-authority-grant.schema.json` | `e0338b83c1f03449d65ffc73ab7c6d47a2d39157` |
| Production | `research_system/assurance/requirements.py` | `35b99791671fa08c6b5457ec1f3c8818ee922c76` |
| Production | `research_system/authority.py` | `c564bfdc7db01b7ff1c2f47b67f144ee14984a5c` |
| Production | `research_system/cli.py` | `0e1e35e5615f8c8b936efca507b942d8dbba8be3` |
| Production | `research_system/command/service.py` | `008393a78973bf6cee04dd798f9377355b7fa339` |
| Production | `research_system/command/t2.py` | `01c839ca6a9fb9f415d394c9ef75ed2af00f62e3` |
| Production | `research_system/operations/backups.py` | `0980b3d9200e36635ec1db9e98e942b3292340ff` |
| Production | `research_system/projection/replay.py` | `58005e5e6e7340a75e75699ba1ce0b55e1ecaf3a` |
| Production | `research_system/schema_registry.py` | `740e2d9f26836bfa43699d6cf8ebc7c9ac027edb` |
| Production | `research_system/store/ledger.py` | `8e53a707c8eb271434f10d94f95878b64f688573` |
| Test | `tests/research_system/integration/test_scoped_authority_grant_activation.py` | `2dba47b8ba617f60f21bb4ed77386569706a54b2` |
| Test | `tests/research_system/unit/test_assurance_requirements.py` | `cf85cd74f376806dbaa97faca19f5bc6d6842ff1` |
| Test | `tests/research_system/unit/test_schema_registry.py` | `2aa7258d573667d81110587343e7ea424149d1b5` |
| Test | `tests/research_system/unit/test_scoped_authority_grants.py` | `fbfa3daa2afae51a767f9f73ab201c4842187bb2` |
| Review | `docs/plans/agentic-research-system/reviews/adversarial-wp6-3-scoped-authority-10759ec-revocation-seal-exact-subject-review-2026-08-01.md` | `e097bd494401b0e7c86bce3669f18baddcae04c0` |
| Review | `docs/plans/agentic-research-system/reviews/adversarial-wp6-3-scoped-authority-13c479d-remediation-exact-subject-review-2026-08-01.md` | `46d53c9265563298439f687b2f53411bf356171a` |
| Review | `docs/plans/agentic-research-system/reviews/adversarial-wp6-3-scoped-authority-255f607-exact-subject-review-2026-07-31.md` | `b76daa8aa96b9f2d5c55dcd0a084be006bf08954` |

No accepted production, schema, test, or review blob was altered by the main
integration.

## 4. Decision-register automatic merge

The decision register is the sole shared accepted path. Its relevant blob
identities are:

| Revision | Git blob |
|---|---|
| Common merge base | `bf3181961d229d5e8f92987203770c7eb3df317b` |
| Accepted WP6.3 parent | `90b3436469e2012168499f475a90177922b92d65` |
| Current-main parent | `a8a4cdcc65bd7f8445d78af94c635565375a3863` |
| Integration candidate | `552183b39e70cf4b105346bdd7f747496a792e85` |

The candidate-to-parent diffs prove a non-deleting semantic union:

- accepted WP6.3 parent to candidate is exactly 31 insertions and 0 deletions,
  comprising the accepted P-044 06i/06j amendment from main; and
- current-main parent to candidate is exactly 65 insertions and 0 deletions,
  comprising P-046 from the accepted WP6.3 parent.

`git merge-tree 6dcdbe8... 8bb891e... a464eb5...` exited 0 with no conflict
marker line. The candidate contains exactly one P-044 heading at line 818, one
P-044 amendment heading at line 875, P-045 between the decisions, and exactly
one P-046 heading at line 942. P-044's bounded Stage-A/gate limits remain
unchanged, while P-046's owner-bound admission, raw-append prohibition,
closed scope, human-owner rule, and no-owner-acceptance boundary remain
unchanged. The seven directly named P-044/P-046 plan, handoff, and review
targets all resolve at the candidate.

No authority, lifecycle, scope, or gate meaning from either decision was
deleted, narrowed, widened, or combined with the other decision.

## 5. Protected accepted contract and schema identities

The protected tree and artifact identities are equal at the technical subject,
independent review, current-main parent, and integration candidate:

| Protected object | Exact identity |
|---|---|
| `.research-system/schemas/core` tree | `831ed486736d74df7c2d3a10d1ba70c2940e18d2` |
| `.research-system/contracts` tree | `27f1e12e8ecfb5c6fb33377981a96410555cbd56` |
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` blob | `7298b994ca80fb43364ec53964b735f1c7e3929a` |
| Assurance-pack raw SHA-256 | `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` blob | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` |
| Assurance-pack-schema raw SHA-256 | `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` |

The two protected files are explicitly `text eol=lf`; their current
working-tree raw bytes hash to the recorded accepted SHA-256 values and their
unfiltered working-tree blob IDs equal the candidate Git blobs.

## 6. Diff, encoding, and compatibility evidence

- `git diff --check a464eb5... 99f8c075...` exited 0.
- All 24 candidate-delta Git blobs decode as strict UTF-8, have no UTF-8 BOM,
  NUL, replacement character, recognised mojibake sequence, CRLF, missing final
  LF, or conflict marker.
- The Windows checkout has `core.autocrlf=true`; 12 ordinary text files are
  therefore materialised with CRLF but are filter-clean. This does not alter
  their Git blobs. The protected hash-bound contract and schema remain LF and
  byte-exact in the working tree.
- The only pre-existing worktree changes remain the two Repowise setup files;
  neither is in the candidate delta or touched by this review.
- Main's post-base changes are documentation-only. No runtime, schema,
  contract, test, or caller/dependency path overlaps the accepted WP6.3 code.

No runtime suite was rerun. The explicit expansion trigger was absent: main
introduced no code overlap, and every accepted production/schema/test blob is
identical to the independently reviewed parent. Re-running the scoped-authority
or full runtime suite would test unchanged bytes rather than this integration
seam.

## 7. Findings, residual boundary, and verdict

No Critical, Major, or Minor integration finding was established. The only
shared-path merge is a clean, non-deleting decision-register union; all
accepted semantic blobs and protected hashes are preserved; the final path
surface remains below 100; and no actual current-main incompatibility is
present.

This decision grants no push, pull-request creation, merge, dispatch, Gate 6,
live grant, live owner decision, result, or claim authority. The review-record
commit is a provenance-only descendant and does not extend the verdict to a
later implementation, schema, contract, test, or decision change.

**Final exact-head verdict: `accept_integration_seam`.**
