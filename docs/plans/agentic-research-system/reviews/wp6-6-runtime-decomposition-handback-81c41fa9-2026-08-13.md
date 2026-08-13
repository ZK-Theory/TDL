# WP6.6 `discovery/runtime.py` decomposition — handback to the owning manager

Date: 2026-08-13
For: the WP6.6 / KAN-59 owning manager agent
Producer: implementing session (Claude Code, Windows)
Assignment: WP6.6 external adversarial architecture review **and remediation** of
PR #248, with authority to implement the refactor if the frozen assessment
warranted it.

**Capability status: INCOMPLETE — WP6.6 is not INTEGRATED.** The exact functional
gap is owner-controlled CodeRabbit completion at the new PR head plus separate
owner authorization to integrate. The remaining *architectural* gap is the
preparation split: `DiscoveryRuntime` is still a 2,802-line owner of the
`_prepare_*` family and a 287-line `_submit_authorized`.

This is a construction handback, not an independent approval. The same session
froze the assessment and implemented the remediation, so the exact head remains
subject to external review and owner acceptance.

---

## 1. What you are receiving

| Item | Value |
|---|---|
| PR | #248, `codex/wp6-6-adversarial-full-review`, OPEN |
| Previous head (reviewed subject) | `cf4ea2e48b0564c4e21e63af40846274bf26a039`, tree `4573e3c2970002851b669e5341161028698b41f7` |
| **New head** | `81c41fa9b105441a1b02c1fc29e6ee666257561d` |
| **New tree** | `2dee24e186a2a13e3c0282ca5e566bf8282dd0df` |
| Push type | fast-forward `cf4ea2e..81c41fa`; remote head re-verified as `cf4ea2e` immediately before pushing |
| PR record comment | https://github.com/stephendor/TDL/pull/248#issuecomment-5274099073 |
| Base / live main | `2e6bf9c92e59208c40e55f664fc48d75e481ae04` — verified ancestor of the new head |

Seven commits were added on top of the reviewed subject:

| Commit | Purpose |
|---|---|
| `bcafb9d` | Frozen pre-edit adversarial assessment (**committed before any production edit**) |
| `6f5a4a0` | Leaf extraction: `accepted_w11`, `routes`, `rules`, `ledger_integrity` |
| `fd1f9e0` | `replay_discovery` split into owned lifecycle reducers + architectural controls |
| `2f74bc8` | Assay Partial binding rule de-duplicated |
| `57a2169` | Responsibility and dependency maps, remediation record |
| `60eeeb8` | Canonical LF bytes restored (self-inflicted CRLF regression) |
| `81c41fa` | Formatter-disagreement fix in the architecture control |

---

## 2. The decision you are being asked to accept

**SUBSTANTIAL DECOMPOSITION**, frozen at `bcafb9d` before editing, and then
implemented.

KEEP AS-IS was refused against the assignment's mandatory decision rule. The
governing evidence was not line count:

- Verifying one lifecycle transition (OR-005 `RecordAssayPartial`) required
  reading ten regions spread over ~5,800 lines of one file, with the two halves
  of a duplicated rule 3,700 lines apart.
- The file had five commits, **four of them review remediation**, and grew
  5,690 → 6,481 lines entirely through defect correction.
- Decisively: the hunk spread *within a single remediation round*. `cf4ea2e`
  alone required coordinated edits in the replay reducer (lines 2030–3470),
  receipt recovery inside `_submit_authorized` (4020–4191), and Assay-bar
  authority preparation (4952–4962). No reviewer reading any one region could
  have seen that round's findings whole.

Full argument and the ten required answers: `wp6-6-runtime-architecture-adversarial-assessment-2026-08-12.md`.

---

## 3. Relationship to the concurrent large-file review — please read this first

The reviews directory also contains
`large-file-suitability-and-modularisation-review-2e6bf9c9-2026-08-12.md`, whose
disposition is *"the modularisation question itself resolves to **mostly no**"*
and which states *"one Critical defect must be closed before any modularisation
work begins."*

**There is no contradiction, and the gating clause does not reach this work.**
Verified, not assumed:

1. That review's subject is the 40 large files **on `main` at `2e6bf9c9`**. At
   that commit `research_system/discovery/` **does not exist at all**. The review
   says so itself, in finding m-4: *"`research_system/discovery/` does not exist
   at `2e6bf9c9` — those consumers are in unmerged PRs #247/#248."* It therefore
   never assessed `discovery/runtime.py` and its "mostly no" does not cover it.
2. Its Critical C-1 is that `.github/workflows/ci.yml` is `disabled_manually` and
   that `tests/research_system/contracts/test_06i_stage_a_candidate.py` is red on
   a byte-clean `origin/main`, because the artefact-write authority moved from
   `prepare_session_brief` to `record_session_evidence` in
   `research_system/session_exchange/exchange.py` without the contract or the
   test's expected set being updated.

I reproduced C-1 at my candidate head to establish its status factually:

```
tests/research_system/contracts/test_06i_stage_a_candidate.py
1 failed, 8 passed in 4.82s
FAILED ...::test_direct_artefact_storage_boundary_is_exact_including_history_and_content_reads
E  Extra items in the right set:
E  ('research_system/session_exchange/exchange.py', 'prepare_session_brief', 'write', 'artefact')
```

Identical failure, identical message. It is **pre-existing on `main`, inherited
by PR #248, neither caused nor fixed by this work**, and outside the WP6.6
nine-module gate. My change surface touches zero files in that area:
`git diff --name-only cf4ea2e..81c41fa -- research_system/session_exchange/ .research-system/ contracts/ tests/research_system/contracts/`
returns nothing.

**Manager action required:** decide whether C-1 blocks acceptance of this PR. My
reading is that it should be tracked as a separate `main`-scoped defect (it
predates the branch and lives in an unrelated module), but that call is yours,
and if you rule that C-1 must close first, this candidate should wait.

**Disambiguation of one phrase you will see in my evidence.** The pre-commit
output `Contract framework: all gates passed against 103 contract(s)` refers to
the `.githooks/pre-commit` contract-framework validator. It is **not** the same
gate as `test_06i_stage_a_candidate.py`, and it does not contradict C-1.

---

## 4. What changed structurally

`research_system/discovery/runtime.py`: **6,481 → 2,802 lines**.
`replay_discovery`: **2,072 → 728 lines**, and it now owns no lifecycle policy.
The 54-branch `event_type` chain (1,385 lines) became 54 reducer functions across
seven lifecycle modules behind an explicit registry.

| Module | Lines | Owns exactly |
|---|---:|---|
| `accepted_w11.py` | 49 | Protected accepted-W11 envelope identity; the one-time genesis payload |
| `routes.py` | 352 | Immutable row→command/event registry (59 executable rows), its accepted-catalogue partition proof, the shared-ledger partition, the global immutable-identity contract |
| `rules.py` | 1,172 | Shared lifecycle predicates — one definition per rule, reached by both preparation and replay |
| `ledger_integrity.py` | 168 | Hash-chain and persisted-envelope validation |
| `replay/scope.py` | 40 | The complete set of names a reducer may read |
| `replay/driver.py` | 760 | Ledger preconditions, projection init, transaction-join closures, shared-ledger partition, authority shadow lane. **No lifecycle policy** |
| `replay/registry.py` | 84 | 66 event types → exactly one owning reducer |
| `replay/genesis.py` | 31 | `W11CatalogueGenesisImported` |
| `replay/scout_candidate.py` | 186 | Scout ingestion, Candidate registration and supersession |
| `replay/assay.py` | 475 | Assay request, score, partial, cancellation and Candidate links |
| `replay/spike.py` | 649 | Spike plan, authorization, start, verdict, partial, review, cancellation, operational closure shadows |
| `replay/review_decision.py` | 354 | Review/Decision relations, revisit and retry across both lifecycles |
| `replay/promotion.py` | 123 | Candidate promotion request and application |
| `replay/dossier.py` | 130 | Dossier admission and object/Scope materialisation |
| `runtime.py` | 2,802 | `DiscoveryRuntime` façade: authority resolution, identity fencing, receipt/idempotency recovery, route dispatch, schema/producer binding, event construction, ledger append |

Dependency direction, enforced by test, runs leaf → replay → façade and never
back:

```
accepted_w11 → routes → rules ─┐
                ledger_integrity ┤
                    replay.scope ┤
        replay.{7 lifecycle modules} → replay.registry → replay.driver → runtime
```

---

## 5. Why you can believe behaviour is preserved

The transformation was mechanical and self-checking, not hand-edited:

- **Leaf extraction.** The script asserted that kept + removed lines
  reconstitute the original file exactly. The extracted route registry was
  proven field-identical to the original for all 59 rows (the naive `==`
  comparison fails only because `DiscoveryRowRoute` became a distinct class;
  field-by-field comparison and a canonical-JSON comparison both match).
- **Reducer split.** Each reducer body is the original branch body dedented by
  exactly 8 columns — asserted, then re-parsed. Each reducer's prologue rebinds,
  under their original names, only the shared-scope names its body actually
  reads, derived by AST rather than guessed.
- **Fail-loud property.** The reducer modules' global scope contains no `state`,
  `event`, or `payload`. A missed binding therefore raises `NameError` rather
  than silently altering a rejection. This is the property that makes the
  transformation safe to trust at this scale.
- The `else: raise IntegrityError(f"unsupported Discovery event: {event_type}")`
  terminator is preserved exactly as the registry miss.

**Preserved seams.** `DiscoveryRuntime`, `DiscoveryRuntime.submit` and
`replay_discovery` all still resolve from `research_system.discovery.runtime`.
`runtime.replay_discovery` remains a module global, so the crash-recovery tests'
`monkeypatch.setattr(discovery_runtime_module, "replay_discovery", …)` still
intercepts it. `research_system/projection/replay.py`'s deferred import is
unchanged. No command, event, schema or producer identity changed; no durable
event or receipt format changed; OR-030 remains deliberately inactive and
fail-closed.

**Contract path-pin check.** Prompted by the OPEN research-observer observation
that contract pins bind behaviour to `source_path`, I verified no contract pins
reference `research_system/discovery/` at all — so this move breaks no path
binding. That is why the contract framework stays green across the move.

---

## 6. Validation at the exact head `81c41fa`

| Gate | Result |
|---|---|
| Pre-refactor baseline at `cf4ea2e` (nine-module gate) | **459 passed**, exit 0, 1292s |
| Nine-module gate + 10 architectural controls at `81c41fa` | **469 passed**, exit 0, 847s |
| Strict real-owner dossier certification (`tools/certify_wp6_6_real_dossier.ps1`) | **38 passed**, zero skips, exit 0 |
| `ruff check` (`research_system/`, `tests/research_system/`) | passed |
| `ruff format --check` (all 19 changed `.py`) | passed |
| `git diff --check cf4ea2e..81c41fa` | clean |
| W11 catalogue blob / bytes / SHA-256 | `8d58818540e04859f929d4b04c71e4cfa0512554` / 136229 / `7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80` — unchanged |
| `git diff cf4ea2e..81c41fa -- .research-system/ contracts/` | empty |
| `2e6bf9c` (live main) ancestor of head | yes |
| `cf4ea2e` (reviewed subject) ancestor of head | yes |

469 = the 459-test baseline plus the 10 new architectural controls. **No test was
deleted, skipped, weakened, or xfailed.** The intermediate structure was also
validated independently: 130 heavy integration tests on a pinned worktree at
`6f5a4a0`, and 90 adversarial replay tests after the reducer split.

The command used for the gate is the same nine-module aggregate recorded in the
prior WP6.6 remediation records, plus
`tests/research_system/unit/test_wp6_6_discovery_architecture.py`.

---

## 7. Findings, including one against myself

**F-1 — a real import cycle, watched red then fixed.** `replay/registry.py`
imported the `replay` package while `replay/__init__.py` eagerly imported
`driver`, placing the package initialiser inside its own dependency chain. It
functioned only because Python tolerates partially-initialised parents. The new
control failed on it before it passed:

```
AssertionError: import cycle: __init__ -> runtime -> replay -> replay.driver -> replay.registry -> replay
```

Fixed by emptying `replay/__init__.py` and importing `replay.driver` directly —
**not** by relaxing the test. That failure is this gate's negative control.

**F-2 — the Assay Partial duplication, and a correction to my own frozen
assessment.** The assessment (§3.1) called the two copies "already diverged" and
filed it under defects. That overstates it and I am correcting it on the record:
**the divergence is not exploitable.** Replay's `_current_assay_bar_matches`
subsumes both of preparation's bar comparisons and additionally binds the
producer relation and actor, so replay is at least as strong as preparation on
every input; no ledger replay would accept could have been refused at
preparation. **No red behavioural proof is claimed, because the divergence does
not admit one.** What was real is the maintainability defect: seven reference
comparisons written twice, 3,700 lines apart, with nothing forcing agreement.
They now have one definition, `rules._assay_partial_bindings_match`, reached by
both paths, with each side keeping only the checks its own context can make.
Rejection behaviour on both paths is unchanged.

**F-3 — a CRLF byte-surface regression I introduced and then fixed.** The
extraction scripts used `pathlib.Path.write_text`, which translates newlines on
Windows, so twelve modules were committed as CRLF against a repository whose
blobs are LF. `.gitattributes` declares the contract system's
`canonical_byte_surface: git_blob_utf8_lf` and warns in its own comment that
validators hash working-tree bytes against it. **Ruff, the pre-commit hooks and
all 103 contract-framework gates passed anyway, across two separate commits.**
Only `git diff --check` caught it, and only because the assignment happened to
list it. Fixed in `60eeeb8`; `git diff --check` over the full range is clean.
Logged as an OPEN GATE-lane research-observer observation
(`2026-08-13-crlf-byte-surface-unenforced`) recommending a pre-commit byte-level
check shipped with its own negative control.

---

## 8. PR thread dispositions

**None.** PR #248 had **zero unresolved review threads** at `cf4ea2e` when this
work began, confirmed via the GraphQL `reviewThreads` query, and this work
addressed and resolved none. Nothing here disposes of a prior finding, and no
prior finding was reopened.

---

## 9. Residual risks — what still requires reading across modules

1. **The façade is still 2,802 lines and the preparation split is not done.**
   `DiscoveryRuntime` retains the `_prepare_*` family and a 287-line
   `_submit_authorized` that still fuses receipt/idempotency recovery with route
   dispatch, schema binding and append. Establishing preparation/replay
   equivalence for one row now requires reading `runtime.py` plus the owning
   reducer module — two files instead of ten regions of one, which is better but
   is not "one file". This is the single largest remaining item and is an
   explicit scope decision for you.
2. **Three accepted catalogue tokens normalise to names the runtime does not
   emit**: `AssayReviewRequested` vs `AssayOutcomeReviewRequested`, and
   `CandidateRevisitRequested/assay` and `/spike` vs
   `CandidateAssayRevisitRequested` / `CandidateSpikeRevisitRequested`. These are
   pre-existing at the frozen subject and were deliberately left alone, because
   the event identities are durable. The consequence for review: registry
   coverage is proven **structurally** (one owner per event, no orphans, no
   duplicate ownership) rather than by catalogue-name equality, so a reviewer
   cannot verify coverage by string-diffing the registry against the catalogue.
3. **Nine authority-lane event types are reduced by the driver, not the
   registry**, through the `authority_event_type` shadow branch. That lane is
   cohesive but is a second dispatch mechanism a reviewer must know exists.
4. **`spike.py` (649) and `assay.py` (475)** remain the largest reducer modules
   and could be split further by transition family if a later review finds them
   hard to reason about.
5. **C-1 is inherited and unresolved** (see §3).

---

## 10. Exact owner / manager actions

1. **Decide the C-1 interaction** (§3): does the disabled CI workflow and the red
   `test_06i_stage_a_candidate.py` on `main` block acceptance of this PR, or is
   it tracked separately as a `main`-scoped defect?
2. **Trigger and monitor CodeRabbit at `81c41fa9b105441a1b02c1fc29e6ee666257561d`.**
   Any earlier CodeRabbit evidence for PR #248 is void — this is a new head. I
   did not trigger, poll, schedule, simulate, or infer CodeRabbit completion.
3. **Run the release-gate certification from your own clean checkout at this
   head**, since hosted CI does not substitute for physical owner-root evidence:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File tools/certify_wp6_6_real_dossier.ps1
   ```
4. **Decide the scope of the remaining preparation split** (residual risk 1):
   this PR, or a successor subject.
5. **Authorize integration separately.** Nothing in this handback is merge
   authorization.

## 11. Boundaries observed

Did not merge; did not push `main`; did not mark KAN-59 or KAN-85–91 Done; did
not claim INTEGRATED; did not trigger or poll CodeRabbit; did not modify
protected W11 catalogue, schema, or accepted-design bytes; did not open a second
PR. Provider execution, pilot dispatch, migration/cutover and KAN-69 remained out
of scope. Unrelated worktree setup changes (`.claude/CLAUDE.md`,
`.repowise-workspace.yaml`) were left modified-but-unstaged and were never
committed.

Work was performed in a fresh detached worktree at the required subject, on the
temporary branch `codex/wp6-6-runtime-decomposition`, and pushed to the PR branch
only after re-fetching and confirming the remote head still equalled `cf4ea2e`.
