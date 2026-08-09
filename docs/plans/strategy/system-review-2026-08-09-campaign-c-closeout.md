# System Review 2026-08-09 — Campaign C Closeout

**Campaign:** Git, hook, and review-seam liveness

**Decision:** Approved by Stephen on 2026-08-09

**Candidate branch:** `codex/system-review-2026-08-09-c-git-gates`

**Base:** `9736c900fd4f72e84b2208eeff0dcfb2a2b44106`

**Result:** 15 of 15 mapped observations resolved

## Observable change

Commit admissibility now runs the contract validator against an isolated
materialization of the Git index while retaining access to repository history.
Unrelated working-copy bytes cannot make a scoped candidate pass or fail. A
tracked pre-push hook makes local `main` read-only and routes integration through
the remote PR seam. The installer activates `core.hooksPath=.githooks` in a fresh
clone, then verifies that boundary and all tracked hook modes. The main CI job has a 45-minute budget and remains an unfiltered
post-merge composition and exact-reference currency signal.

## Observation dispositions

| Observation | Disposition | Evidence |
|---|---|---|
| 84 | ACTIONED — already compliant, made explicit | CI runs the unfiltered suite on every push to `main`; large-workflow guidance now requires affected-test execution on the composed merge result. |
| 101 | ACTIONED — already compliant | `tda-large-workflow-supervision` requires a history-bearing validation clone rather than an archive. |
| 103 | ACTIONED — already compliant | The same canonical recipe sets `core.autocrlf=false` and `core.longpaths=true` before checkout. |
| 104 | ACTIONED — already compliant | Read-only validation uses a verified external interpreter and checks residue after hooks. |
| 120 | ACTIONED — already compliant | `contract-first-tdd` names working tree, index, revision, and `HEAD` proof namespaces and requires a post-commit candidate run for `HEAD`. |
| 121 | ACTIONED — existing controls retained and extended | Installer fixtures cover missing directory, missing hook, non-executable index mode, and linked-worktree resolution; `pre-push` is now also required. |
| 122 | ACTIONED — already compliant | Hermetic mirror-tree tests cover allow, deny, Windows separators, linked prefixes, malformed input, and durable fail-open receipts. |
| 123 | ACTIONED — current merge-seam signal made explicit | The unfiltered push-to-main suite re-resolves every accepted exact-reference row against current `HEAD`; workflow guidance forbids reusing the PR-head verdict. |
| 137 | ACTIONED — already live, duration bounded | CI runs the unfiltered research-system suite on PRs and pushes to `main`; the primary job now fails after 45 minutes instead of hanging without a signal. |
| 146 | ACTIONED — already compliant | The pre-commit launcher resolves one populated interpreter and the validator runs binding tests through `sys.executable`; linked-worktree controls prove no local venv bootstrap. |
| 01KZ2SJJJ55APRV36G53DPGC40 | ACTIONED — applied in this campaign | `contract-first-tdd` now classifies controls as `remediation-red` or `preservation-green`, with different parent expectations bound to the public seam and source ordering. |
| 01KZ8F4J6W3Q2N7M9T5R0C8BHD | ACTIONED — applied in this campaign | `run_staged_contract_gate.py` materializes index bytes outside the repository and runs the candidate validator there with the real Git object database. |
| 01KZ913F8WDQPQBQ987V305D7S | ACTIONED — applied in this campaign | `.githooks/pre-push` rejects every direct update to `refs/heads/main`; feature-branch pushes remain allowed. |
| 2026-08-06-precommit-hook-exec-bit-dropped | ACTIONED — current mode verified and watched | All tracked hooks are mode `100755`; installer tests fail on a dropped index executable bit and now include `pre-push`. |
| 01KZJRRT4QK55YKM9Z7ZVX0DYV | ACTIONED — applied in this campaign | Empty-index counting uses one `awk` reduction; its fixture requires exit 0, no stderr, and exactly one zero-file template. |

## Controls and validation

- Staged-tree positive control: staged valid bytes pass even when the working
  copy contains a conflicting unrelated value; the working copy is unchanged.
- Staged-tree negative control: a staged validator failure propagates its exact
  nonzero status.
- Main-boundary negative control: a `refs/heads/main` pre-push update is rejected.
- Main-boundary positive control: a feature-branch update passes.
- Fresh-clone execution control: `--install` activates the tracked path, then a
  real feature push passes and a real `main` push is rejected by Git's hook seam.
- Empty-index control: the prepare hook emits no stderr and one zero-file count.
- Hook-liveness controls: missing hook/directory, non-executable mode, mirror
  deny/allow/fail-open receipt, and linked-worktree interpreter routing.
- Focused result: 44 tests passed across the five changed hook/gate test modules
  plus the skill-sync suite.
- Dual-tree and guide checks pass; patch hygiene is clean.

## Remaining external fact

GitHub reported no server-side branch-protection rule for `main` during this
review. The approved repository control closes direct pushes from compliant
TDL clones; server-side protection would add defence in depth but is not
silently enabled by this PR.

## Simplification disposition

The implementation reuses the existing validator, interpreter, Git index, and
CI suite. It adds one small materialization launcher and one standard Git hook;
it does not create a second contract validator, a second CI suite, or a new
review workflow.
