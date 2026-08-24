# Gate 6 agent-transfer current state

**Recorded:** 2026-08-24

**Capability status:** `INCOMPLETE / OWNER-BLOCKED` — the historical real
SPEC run is proven and the STORE prerequisites through PR #267 are on `main`,
but PR #268 is not integrated and the SOURCE, AUTHORITY, TASK, MODEL, and EXEC
slices do not yet exist on `main`.

**Current `origin/main`:**
`e13b77b3e3521e41d9d6438fc25c9b785b2146fd`

**Active implementation candidate:** [PR #268](https://github.com/ZK-Theory/TDL/pull/268)
at `87af6689692dd2a1729e9040b7347da9e42e8be5`

**Governing plan:**
[06q — Gate 6 Recovery and Closure Plan](../implementation/06q-gate6-spec-real-run-integration-and-follow-up.md)

**Workflow:** standalone agent transfer

## 1. Purpose and authority of this record

This is a factual transfer snapshot for a new agent set. It is deliberately
not a replacement plan. The existing 06q plan remains the sole Gate 6 recovery
and closure authority, and 06r remains the historical PR #258 review record.

This handoff was created as a new file. It does not modify 06q, 06r, the
roadmap, decisions, result handoff, `agent_docs`, Jira, runtime code, schemas,
the live store, or any existing worktree. Current facts that have moved ahead
of the copy of 06q on `main` are recorded here so that the original planning
documents can remain untouched for transfer.

This record grants no authority to:

- merge or queue PR #268;
- mutate the live control store or issue a successor binding;
- invoke a provider, spend money, or start the fresh real run;
- accept a review on Stephen's behalf; or
- make the final Gate 6 closure decision.

Those remain explicit Stephen owner actions.

## 2. Plain-English position

A real SPEC-01/SPEC-02 suitability exercise has already run and produced
durable evidence. It assessed the Damrich-Berens-Kobak method, executed the
frozen 126-configuration design with 42 deterministic reruns, and ended at
`PARK`. That means the method remains an experimental or benchmark candidate;
it is not the default empirical method and the run made no scientific claim.

That result proves the historical route, not the current implementation. The
large implementation that produced it was never merged. The recovery campaign
has since integrated several STORE foundations, but it has not yet assembled
the public SPEC path. Gate 6 is therefore neither runnable nor integrated from
current `main`.

The immediate blocker is narrow: PR #268 is open, mergeable, green on the two
required repository checks, and not queued or merge-authorized. Until it is
merged and verified, STORE is not complete and SOURCE remains blocked behind
it.

## 3. Durable historical result

The authoritative human result is
[01M0454KCTYV0E8PB016CP3F6J — Gate 6 SPEC real-run result](01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md),
with its adjacent
[machine-readable evidence manifest](01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-evidence-manifest.json).

Key result facts already recorded there are:

- terminal research disposition: `PARK`;
- terminal historical SPEC state: `PROVEN/spec_02_owner_decided`;
- frozen computation: 126 configurations and 42 deterministic reruns;
- historical run-closure anchor: ledger position 444,
  `ResourcesReleased`;
- source correction: GitHub locator `neurips2024` is a real lightweight tag at
  commit `145efcde673f1a1897eff250b77221d26c34c479`;
- seven registered result, source, check, summary, return, correction, and
  approval artefacts were re-read and matched their registered SHA-256 values;
  and
- the result is a project-suitability decision, not a scientific finding.

The historical implementation and evidence worktree is clean and retained at:

```text
C:/Users/steph/.codex/worktrees/gate6-spec-real-run/TDL
branch: codex/gate6-spec01-spec02-real-run
HEAD:   94f8bc1fc92bdc5259acab02e73a3958202ab2e4
```

Do not treat that branch as a merge candidate. Do not rewrite its ledger or
artefact history.

## 4. Git and pull-request history

The following is the live GitHub state read on 2026-08-24. Additions and
deletions are GitHub's gross PR counts, not unique capability code.

| PR | State | Exact candidate / merge | Scope and disposition |
|---|---|---|---|
| [#257](https://github.com/ZK-Theory/TDL/pull/257) | Closed unmerged | `dea803490eaea8d7381e73cdab33d5510a6079bb` | Obsolete SCALE-01 eligibility-envelope attempt. Retained only as history. |
| [#258](https://github.com/ZK-Theory/TDL/pull/258) | Closed unmerged | `94f8bc1fc92bdc5259acab02e73a3958202ab2e4` | First monolithic real-SPEC integration attempt: 155 files, +39,065/-821, 58 commits. Historical evidence only. |
| [#259](https://github.com/ZK-Theory/TDL/pull/259) | Merged | `d65d74912e2edf385702f67c85c4df340c900651` | Recovery control reset and replacement decision. |
| [#260](https://github.com/ZK-Theory/TDL/pull/260) | Closed unmerged | `53beb174cc90455e31f8091fbe1b4a7424a4db0d` | First SOURCE attempt. Retired after a second material review cycle exposed the missing shared STORE boundary. Evidence may be re-derived; do not cherry-pick wholesale. |
| [#261](https://github.com/ZK-Theory/TDL/pull/261) | Merged | `02e4b2baf8e2e85052fdbdda8f4d35e27fa0cc30` | Durable decision to put STORE before SOURCE. |
| [#262](https://github.com/ZK-Theory/TDL/pull/262) | Merged | candidate `af680b81f10df2bf0f0803a475e34656a926f766`; merge `121e20ff50e11ecce9da93401dca543cd704f519` | Physical publication boundary. |
| [#263](https://github.com/ZK-Theory/TDL/pull/263) | Closed unmerged | `b59b9de5bceb9b65d90c7b8654f3f8f0dcfe0dae` | Failed post-merge lock repair. Retired rather than repeatedly remediated. |
| [#264](https://github.com/ZK-Theory/TDL/pull/264) | Merged | candidate `9c267da575f5697764e28df67b2e53103058e8ea`; merge `161976a59ca6d8eb2e0915ec3113a8ff32f40fe6` | Physical directory transaction and immutable `ObjectStore` ownership. |
| [#265](https://github.com/ZK-Theory/TDL/pull/265) | Merged | candidate `34d208482b1a9c2580b835dca0309aa9bbfbd8a9`; merge `571236ed69be719aa6fe7b7f48dfd9935d195538` | Read-only admission of the exact current store binding and append-only historical binding identity. |
| [#266](https://github.com/ZK-Theory/TDL/pull/266) | Merged | candidate `dfef3a11d2eb8237c9799f07c55e467c125c3752`; merge `c28a6b674623b8fd4c485f5c0149a0afaf8577f0` | Governed-code manifest and reviewed code/documentation successor rules. |
| [#267](https://github.com/ZK-Theory/TDL/pull/267) | Merged | candidate `e33df9fda0dc269889b4ea2adea0abb3449d81cf`; merge `e13b77b3e3521e41d9d6438fc25c9b785b2146fd` | STORE writer/release ownership and mutable-replacement recovery. Candidate and merge trees both equal `9edec7af25bbe711bdbf4d515bbaadd7b0f4f9a1`. |
| [#268](https://github.com/ZK-Theory/TDL/pull/268) | Open | code `ff5de006e81e93758f00b744de9a8b2e8bc1bd6b`; current head `87af6689692dd2a1729e9040b7347da9e42e8be5` | Public verified binding continuation and shared Gate 6 store admission. Awaiting Stephen's merge/queue decision. |

PRs #262-#268, including retired #263, represent approximately 21,860 gross
additions, 4,880 gross deletions, and 33 commits. This is churn, not a measure
of capability completion.

## 5. Integrated STORE path on current `main`

At `origin/main == e13b77b3e3521e41d9d6438fc25c9b785b2146fd`,
the repository contains these STORE prerequisites:

1. physically anchored directory transactions and immutable object
   publication;
2. retained physical owners for object effects and release recovery;
3. read-only verification of one current store binding and historical binding
   replay;
4. governed-code inventory and reviewed documentation-successor rules; and
5. writer/release and mutable-replacement recovery.

The merged PR #267 evidence was:

- Windows changed-path STORE selection: 68 passed, 14 platform skips;
- WSL guarded-unlink and race packet: 6 passed;
- independent exact-diff lifecycle review: pass;
- required repository checks: pass; and
- reviewed candidate tree exactly equal to the squash-merge tree.

This does not make Gate 6 runnable. Current `main` still lacks the public
binding continuation supplied by PR #268 and all later SPEC slices.

## 6. Active candidate: PR #268

Current live state on 2026-08-24:

- base: `e13b77b3e3521e41d9d6438fc25c9b785b2146fd`;
- reviewed governed-code commit:
  `ff5de006e81e93758f00b744de9a8b2e8bc1bd6b`;
- current PR head:
  `87af6689692dd2a1729e9040b7347da9e42e8be5`;
- current head is a direct documentation-only child of the reviewed code
  commit and changes only 06q;
- worktree is clean;
- GitHub state: open, mergeable, `BLOCKED`, no review decision, no merge-queue
  or auto-merge request;
- `contract-and-session-currency`: success;
- `require-active-currency-workflow`: success; and
- CodeRabbit status: success.

The candidate adds the thinnest current continuation expected from STORE:

- strict, authority-neutral `SpecOperatorConfig@1.0.0`;
- public `ars store repair-binding --intent PATH` and
  `ars store advance-binding --intent PATH` commands;
- append-only v1.2 repair/advance schemas and governed-code references;
- one lock-held predecessor and snapshot for repair/advance;
- prevalidated deterministic outputs and idempotent recovery of object, event,
  receipt, current pointer, and transaction marker effects;
- historical-manifest validation at the recorded commit while admitting only
  exact current code or a reviewed documentation-only descendant; and
- shared verified binding admission for governed backup, restore verification,
  replay verification, and projection rebuild.

Exact reviewed-code evidence already produced:

- compact assembled public/binding packet: 38 passed;
- bounded closure review: pass, including 5 crash-recovery and
  history/documentation-successor tests;
- direct missing-generic-receipt recovery: 1 passed;
- CLI/config packet: 53 passed;
- historical fixture/current-binding packet: 86 passed; and
- Ruff, Ruff format, `py_compile`, and `git diff --check`: passed.

The candidate performed no live-store write, binding transition, provider
call, Task closure, or Gate 6 decision. Do not infer merge authority from its
green checks or prior review. Stephen must explicitly authorize the exact
merge action.

Active candidate worktree:

```text
C:/Users/steph/.codex/worktrees/g6-spec-store-binding-v1/TDL
branch: codex/g6-spec-store-binding-v1
HEAD:   87af6689692dd2a1729e9040b7347da9e42e8be5
status: clean at this snapshot
```

## 7. Planning-document freshness

The copy of 06q on `main` remains the governing plan but its factual progress
section stops at PR #266. PR #268's documentation-only tail records PR #267 as
integrated and #268 as active. Because PR #268 has not merged, that update is
not on `main`.

This handoff records the current facts without editing either plan:

- [06q](../implementation/06q-gate6-spec-real-run-integration-and-follow-up.md)
  remains the sole active recovery and closure plan;
- [06r](../implementation/06r-gate6-pr258-review-convergence-plan.md) remains
  the retired PR #258 convergence record; and
- no 06s or competing master plan should be created.

Any future agent must distinguish plan authority from a stale progress
paragraph. It must refresh GitHub, `origin/main`, Jira, and the live store
before mutating anything.

## 8. Jira control state

The following was read back from Jira on 2026-08-24. No Jira field was changed
by this handoff.

| Issue | Current status | Meaning |
|---|---|---|
| [KAN-12](https://nexusstephen.atlassian.net/browse/KAN-12) | In Progress | Gate 6 control/capability issue. |
| [KAN-103](https://nexusstephen.atlassian.net/browse/KAN-103) | In Progress | Gate 6 recovery and integration capability, parent KAN-12. |
| [KAN-104](https://nexusstephen.atlassian.net/browse/KAN-104) | To Do | SOURCE; labelled `blocked-by-store`. |
| [KAN-105](https://nexusstephen.atlassian.net/browse/KAN-105) | To Do | STORE; labelled `owner-action-required`; remains open for PR #268 integration. |
| [KAN-106](https://nexusstephen.atlassian.net/browse/KAN-106) | To Do | AUTHORITY. |
| [KAN-107](https://nexusstephen.atlassian.net/browse/KAN-107) | To Do | TASK. |
| [KAN-108](https://nexusstephen.atlassian.net/browse/KAN-108) | To Do | MODEL. |
| [KAN-109](https://nexusstephen.atlassian.net/browse/KAN-109) | To Do | EXEC. |

All six slice jobs are children of KAN-12. KAN-105 blocks KAN-104, KAN-106,
and KAN-103 in the current link graph; the later jobs carry the remaining
sequence. A successor must read back descriptions, status, parent, and both
ends of dependency links before changing them. Jira comments are evidence, not
the technical authority.

## 9. Worktrees and preservation boundaries

Do not continue Gate 6 implementation in the main checkout:

```text
C:/Users/steph/TDL
branch: codex/gate6-eligibility-envelope
HEAD:   dea803490eaea8d7381e73cdab33d5510a6079bb
status: dirty, preserved historical/user work
```

Its ten dirty entries at this snapshot are:

```text
M  .claude/CLAUDE.md
M  .repowise-workspace.yaml
M  docs/plans/agentic-research-system/implementation/06p-gate6-control-model-proposal.md
M  research_system/cli.py
M  research_system/config.py
M  research_system/store/identity.py
M  research_system/store/schema_binding.py
M  tests/research_system/integration/test_command_cli.py
M  tests/research_system/integration/test_restore_recovery_origin_witness.py
?? docs/plans/agentic-research-system/handoffs/01KZZ1YVPV5SMAHWZGDWZWBK9J-gate6-real-run-reset.md
```

Do not clean, reset, stage, restore, merge into, or use those files as current
implementation evidence.

Other retained evidence worktrees:

```text
C:/Users/steph/.codex/worktrees/gate6-spec-source-1/TDL
branch: codex/g6-spec-source-1
HEAD:   53beb174cc90455e31f8091fbe1b4a7424a4db0d
status: clean; retired SOURCE evidence only

C:/Users/steph/.codex/worktrees/gate6-spec-real-run/TDL
branch: codex/gate6-spec01-spec02-real-run
HEAD:   94f8bc1fc92bdc5259acab02e73a3958202ab2e4
status: clean; retired implementation and historical run evidence only
```

For each new slice, create a clean linked worktree from refreshed
`origin/main`, attach one unique `codex/` task branch, verify ancestry and
status, and make no first write until those checks pass. Do not recycle a
retired branch into a new candidate.

## 10. Live-store boundary

The historical control store is at:

```text
C:/Users/steph/TDL-ARS-WP64-Control
```

Historical evidence recorded its store identity as
`2df87684ef33136d85adff91d58a8e91fc31a061a53ced6932988df4e687cd7a`
and its prior governed-code subject as
`cf8faf48d3cd682bf7d8fe7b9202b0054249442c`. These are handoff anchors, not
permission to write. Re-read and verify the physical root, project identity,
store identity, ledger tail, current binding, authority roots, and origin
witness before any future live action.

No live control-store write occurred during the recovery construction through
PR #268. In particular:

- no successor binding has been issued;
- the historical auxiliary Task has not been append-only closed by this
  recovery campaign;
- no recovery provider or paid call has been made;
- no fresh SPEC run has started; and
- no final backup/export has been made at a new closure tail.

The historical operational Task is
`tsk_60c5549e-d11f-7d17-8145-d80e144aa537`. Earlier replay projected it as
`in_progress` despite its completed attempt and released resources. Treat that
as a required historical closure check, but refresh the live projection before
asserting its current state. Its history must be extended only through the
existing governed `SubmitForReview` then `AcceptTask` contracts; never infer
Task acceptance from attempt completion or resource release.

The reserved same-disk closure locations are:

```text
C:/Users/steph/TDL-ARS-WP64-Backups
C:/Users/steph/TDL-ARS-WP64-Restore-Verification
```

They satisfy only logical independence and restore verification. Encrypted
off-disk machine-loss resilience remains a separate deferred operational gap.

## 11. Remaining implementation sequence

The sequence below restates 06q for navigation; it does not amend it.

1. **STORE integration.** After explicit owner authorization, merge PR #268
   through the protected route. Verify exact merged `main`, the composed tree,
   the public repair/advance commands, and one governed backup/replay admission
   path. Then update KAN-105 from live evidence.
2. **SOURCE — KAN-104.** Implement exact Git locator resolution, exact source
   bytes, causal-prefix source observations, append-only source corrections,
   and physically anchored registered-content recovery through the STORE-owned
   verified context.
3. **AUTHORITY — KAN-106.** Implement actor sessions, session-contained grants,
   exact role separation, and exact-retry behavior after expiry.
4. **TASK — KAN-107.** Close eligible auxiliary Tasks only through
   `SubmitForReview` then `AcceptTask`; keep incomplete, failed, partial, or
   unsatisfied-review cases non-accepted.
5. **MODEL — KAN-108.** Implement one registry-derived SPEC action state model,
   `ProjectUseDecision`, and the human-readable `ars discovery spec result`
   surface.
6. **EXEC — KAN-109.** Implement semantic intent preparation, one-snapshot
   evaluation, transactional publication/recovery, owner context, separate
   SPEC-02 approval after PARK, and the full public SPEC status/advance path.
7. **Assembled proof.** On exact integrated `main`, run the final bounded
   regression selection and an independent boundary review once.
8. **Owner-gated live proof.** Issue one reviewed successor binding, close the
   historical Task, register the historical project-use decision, obtain a new
   owner approval, and execute one fresh bounded real SPEC-01/SPEC-02 run with
   separate producer, reviewer, and operator sessions.
9. **Closure evidence.** Close the fresh Task, register and render its
   `ProjectUseDecision`, replay historical and fresh results, create the
   governed backup, restore to a fresh root, verify bytes and hashes, obtain
   independent final evidence review, and obtain Stephen's explicit closure
   decision.
10. **Final reconciliation.** Merge the result/documentation record, verify it
    is a documentation-only governed-code descendant, reconcile `agent_docs`
    and Jira, and only then close KAN-103 and KAN-12.

Gate 6 becomes `INTEGRATED` only after the connected public path, live result,
Task closure, replay, backup/restore, independent evidence review, and owner
decision all exist. Merged STORE parts do not qualify.

## 12. SOURCE preparation already completed

Read-only investigation of retired PR #260 found reusable evidence, but no
SOURCE implementation was ported to current `main`.

Useful semantic references in the retired branch are:

- `research_system/discovery/git_reference.py`;
- `research_system/discovery/source_observation.py`;
- `research_system/discovery/source_correction.py`;
- `research_system/store/registered_content.py`;
- `tests/research_system/unit/test_git_reference.py`;
- `tests/research_system/unit/test_source_observation.py`;
- `tests/research_system/unit/test_source_correction.py`; and
- selected SOURCE integration cases in
  `tests/research_system/integration/test_wp6_6_discovery_runtime.py`.

Use those as evidence and design references only. Re-derive the smallest SOURCE
slice on top of the merged STORE surface. Do not copy PR #260's unrelated
STORE, lock, replay, route-package, or projection changes.

The current STORE-owned boundary is the verified binding context in
`research_system/store/binding_service.py`. SOURCE must use that single
verified context for registration, replay, projection, backup, and restore. Do
not introduce optional arbitrary resolver callbacks: that was the production
bypass identified in PR #260.

`EventLedger.raw_prefix_sha256()` already exists in
`research_system/store/ledger.py`; use it rather than adding another prefix
hash implementation.

One contract question must be resolved explicitly before SOURCE writes:

- 06q's action table names `spec_01_source_correction@1.0.0`;
- retired PR #260's exact causal-prefix correction uses version `2.0.0`.

Do not silently replace historical v1 bytes. Preserve v1 for historical replay
and add/use v2 for the exact causal correction, unless Stephen explicitly
changes the governing contract.

The smallest useful SOURCE acceptance packet is:

- the `neurips2024` regression plus head, lightweight/annotated tag, direct
  OID, slash ref, subpath, ambiguity, unavailable transport, and malformed
  locator behavior;
- exact source bytes and causal ledger prefix;
- append-only correction bound to exact earlier evidence;
- anchored registration recovery with no publication on failure;
- one real registration/runtime/replay positive path; and
- decisive no-context, wrong-artefact, stale-prefix, and substitution
  negatives.

Run one downstream backup/restore check only after that public path works. Do
not duplicate the complete STORE assurance suite inside SOURCE.

## 13. What went wrong in the current delivery process

This transfer is being made because the current agent process repeatedly
failed to control scope and review churn despite explicit owner instructions.
This is the third Gate 6 implementation attempt. PR #258 became a 155-file,
58-commit monolith. The recovery then expanded one STORE phase across PRs
#262-#268, including a retired repair PR, with approximately 21,860 gross
additions, 4,880 gross deletions, and 33 commits. The current goal timer
recorded 69,663 seconds, about 19 hours 21 minutes; that includes tests,
reviews, waits, and administration rather than pure coding time.

The practical failure was not lack of a plan. The plan and repeated owner
instructions already required bounded slices, necessary review, targeted
tests, and no speculative hardening. The agent nevertheless treated possible
edge cases and review observations as reasons to reconstruct increasingly
broad storage machinery. Each remediation enlarged the review surface and
created more opportunities for new findings. Work on the end-to-end SPEC
capability stalled while assurance and transaction detail consumed most of the
campaign.

The integrated STORE code must now be treated as inherited production state,
not as a template for further elaboration. A successor should not reopen it
without a demonstrated failure on the required Gate 6 path.

## 14. Transfer operating constraints

The new agent set should apply these constraints literally:

- Deliver the smallest vertical production path for the current named slice.
  Start with the public positive path, then add only decisive failure cases.
- A review comment is evidence to investigate, not an automatic instruction to
  add code. Fix reachable correctness, corruption, replay, authority, or public
  contract defects. Record and decline speculative, unreachable, style-only,
  or tail-risk expansion.
- Do not add general-purpose infrastructure unless the current positive path
  cannot work without it and the dependency is demonstrated by a failing
  direct test.
- Do not create another Gate 6 plan, successor plan, assurance plan, review
  convergence plan, or mechanics-only work package. Use 06q and the Jira jobs.
- Do not port `spec_flow.py` or its retired monolithic test module wholesale.
- Use one targeted changed-path packet during construction. Expand only when a
  shared seam is actually changed or a narrower test exposes the need. Run one
  final bounded regression selection at the frozen candidate head.
- Use one independent boundary review where 06q requires it. Do not poll or
  retrigger CodeRabbit; Stephen controls that service.
- Stop after the slice's observable result and closure evidence pass. Do not
  pursue adjacent improvements merely because they are visible.
- Never call a merged foundation, green test packet, review, or PR "Gate 6
  complete." Report capability truth first.
- Preserve all owner gates. No green status, prior instruction, or handoff text
  substitutes for Stephen's exact merge, live-write, paid-run, or final-closure
  authorization.

If an agent cannot remain within these constraints, it should return a bounded
diagnosis and hand the implementation to a different executor rather than
expanding the scope.

## 15. Exact next production action

There is no further authorized coding action before PR #268 is dispositioned.
The next action is Stephen's explicit decision whether to queue and merge the
current exact PR #268 head. A new agent should first refresh:

```powershell
git fetch origin main
git rev-parse origin/main
gh pr view 268 --repo ZK-Theory/TDL `
  --json state,headRefOid,baseRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,autoMergeRequest
git -C C:/Users/steph/.codex/worktrees/g6-spec-store-binding-v1/TDL status --short
```

If Stephen explicitly authorizes the merge and the exact candidate remains
unchanged, merge through the protected route and verify the merged public STORE
path once. If the head, base, checks, review state, or worktree has changed,
stop and report the exact delta before acting. After verified STORE integration,
start SOURCE from a new clean worktree at refreshed `origin/main`.

## 16. Transfer checklist

- [ ] Refresh `origin/main`, PR #268, Jira, and the live binding before relying
  on this dated snapshot.
- [ ] Preserve the dirty main checkout and all retired evidence branches.
- [ ] Obtain explicit Stephen authorization before any merge or live action.
- [ ] Merge and verify PR #268, or record its retirement if Stephen rejects it.
- [ ] Complete SOURCE, AUTHORITY, TASK, MODEL, and EXEC in the 06q order.
- [ ] Exercise the assembled public path before adding assurance around it.
- [ ] Run one fresh owner-approved real SPEC proof with separate identities.
- [ ] Close both historical and fresh Tasks through governed contracts.
- [ ] Render both project-use decisions through the public result surface.
- [ ] Back up, restore to a fresh root, replay, and compare exact bytes/hashes.
- [ ] Obtain independent final evidence review and Stephen's closure decision.
- [ ] Reconcile the final tracked docs, `agent_docs`, and Jira only after the
  underlying truth changes.

No credentials, provider secrets, access tokens, or private artefact contents
are contained in this handoff.
