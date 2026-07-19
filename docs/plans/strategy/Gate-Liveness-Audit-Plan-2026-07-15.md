# Gate Liveness Audit — Plan

**Date:** 2026-07-15 (approved and amended 2026-07-16)
**Author:** Manager 14 (APM)
**Status:** **APPROVED** — §7 recommendations accepted by the User 2026-07-16
**Trigger:** User, 2026-07-15: *"Every single gate is now suspected of silent
failure unless there is evidence otherwise."*
**Governing question:** **Has anyone ever watched it fail?**

## 0. Approved decisions (User, 2026-07-16)

1. **Phase A + B dispatch as one batch** to `reproducibility-agent`, reporting at
   the phase boundary.
2. **Phase C runs after** the User's §4.2/§6.2 review — it needs judgement, not
   compute, and must not compete for attention.
3. **CodeRabbit and Codacy are OUT OF SCOPE.** External to the repo and not
   negative-controllable by this method. Removed from §2 rather than carried as
   `UNVERIFIABLE` — the register should not list what it cannot test. The
   standing fact remains worth stating once and not re-litigating:
   review-then-merge is enforced by the User's habit, not by a mechanism, and it
   was the only automated verification provably running during the 47-day
   outage.
4. **Phase D strictly after A–C report**, with **one exception**: the
   working-tree-sha256 signature rule is a known-unsound *live* rule and is
   dispatched now as **Task G1**, ahead of the audit.

**Amendment 2026-07-16 — the Mode-3 mechanism in §1 was stated wrongly on
2026-07-15 and is corrected below.** The original claim was inferred from a byte
comparison of two working copies instead of measured with `git ls-files --eol`.
The corrected finding is **broader**, and it changes the fix.

---

## 1. Why this exists

Three months of "pre-commit hooks ran clean" were hollow. The contract validator
was installed to `.git/hooks/` on 2026-05-27 while `core.hooksPath=.githooks`
had been in force since 2026-04-10 — it never executed once. Fixing that
surfaced a second dead gate: **Gate 0** (dual-tree skill sync) was described as
"pre-commit Gate 0" in `CONVENTIONS.md` and two `SKILL.md` files, and
implemented in none of them — it existed only inside the zombie hook the fix was
replacing. The restoration rebuilt the gate list *from the documentation* and so
inherited the documentation's blind spot exactly.

That is the whole thesis: **a documented gate is evidence of intent, not
existence.** The permanent note
[[silent-absence-is-the-failure-mode-that-produces-no-error]] now records six
instances. A check that is missing returns the same thing as a check that
passed.

### The three failure modes (not two)

Manager 13 identified two axes. Building T1.38's input-provenance manifest today
surfaced a third, which changes what the audit must measure.

| # | Mode | Signature | Found |
|---|---|---|---|
| **1** | **Uncovered object** — the gate runs, but nothing claims the artifact | Skipping produces no error. 348/1,362 result JSONs (26%) are claimed by no contract; gate 4 never looks at them. | Manager 13, 2026-07-15 |
| **2** | **Dead enforcement path** — the contract/rule exists, nothing executes it | The gate reports success by not running. Contract validator (47 days); Gate 0 (never). | Manager 13, 2026-07-15 |
| **3** | **False-positive gate** — it fires, but for the wrong reason | Trains the operator to override. `SUPERSEDED.md` VIOLATION under `core.autocrlf=true`: its working-tree sha256 differs by checkout (9,041 B / 0 CRLF at PROJ_ROOT vs 9,179 B / 138 CRLF in the worktree) though the git blob is identical and clean in both. | Manager 14, 2026-07-15 |

Mode 3 matters more than it looks. A gate that cannot fire is inert; a gate that
fires spuriously is **corrosive** — it manufactures the override reflex that will
later wave a true positive through.

### Mode 3, correctly stated (amended 2026-07-16)

The 2026-07-15 draft said the JSON inputs were safe "because their blobs already
store CRLF, so checkout is a no-op". **That was wrong.** It was inferred from
comparing two working copies rather than measured. `git ls-files --eol` gives the
actual state:

```
i/lf  w/crlf   results/trajectory_tda_integration/05_analysis.json
i/lf  w/crlf   results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json
i/lf  w/crlf   contracts/manifests/input-provenance/b9-om-gmm-inputs.yaml
i/lf  w/lf     results/trajectory_tda_integration/stage1/SUPERSEDED.md
```

`.gitattributes` normalises only `.research-system/evals/fixtures/**`. **Every**
text blob is LF. So working-tree bytes depend on **how the file arrived**, not on
its blob:

- **checked out by git** → CRLF
- **written in place by a tool** (`Write`, `Edit`, a regenerating script) → LF

`SUPERSEDED.md` is `w/lf` at PROJ_ROOT because a tool wrote it, and `w/crlf` in
the worktree because git checked it out. Same blob, clean in both, different
sha256.

**The corrected finding is broader, not narrower.** The exposure is not one `.md`
file — it is **every text input any manifest signs**. The committed JSONs are
pinned safely only because both copies happened to be checked out. They are one
in-place rewrite away from the same false VIOLATION, and `b9-om-gmm-inputs`'s
`05_analysis.json` pin (`82afc3b5..`, computed over CRLF bytes) sits on exactly
that footing. Nothing is firing today. **That is luck, not design** — which was
the right conclusion for the wrong reason.

**The obvious fix is the dangerous one.** Adding `* text=auto` normalisation
would leave blobs unchanged (already LF) but rewrite every checked-out working
copy CRLF→LF, **invalidating every existing working-tree sha256 pin at once** —
a fresh Mode-3 false positive across every manifest simultaneously. The sound
repair is to sign the **git blob hash** (`git rev-parse HEAD:<path>` /
`git hash-object`), which is checkout-invariant by construction and is what "the
git-stable signature" was always reaching for. **This is why the exception is
dispatched as its own Task with its own negative control, and not applied as a
one-line config change.**

The `apm-outputs` rule "`root: worktree` → content sha256 is the git-stable
signature" correctly rejected mtimes as checkout-unstable, then substituted
another checkout-unstable signature and stopped.

### The measurement gap

The 26% figure counts **files without contracts**. It cannot see **contracts
without a live enforcement path**, and it cannot see **checks that fire
wrongly**. Zero violations across 97 contracts is not an all-clear; it is the
output of a system that has never been shown capable of producing a non-zero.

---

## 2. Scope

**In scope — every mechanism the project relies on to say "no".**

| Family | Members |
|---|---|
| Git hooks (`.githooks/`) | Gate 0 skill-sync · ruff lint · ruff format · contract validator · `commit-msg` · `prepare-commit-msg` |
| Contract framework | gates 1b, 1c, 2b · gate 4 (`output_validation`) · pending-debt gate · meta-schema validation |
| APM dispatch | `manager_dispatch_check` (worktree / `.env` / report-bus / contracts / `hook-gate` / input-provenance) · `manager_predispatch_check` (R-B) · `input-provenance-manifest-coherence` (R-C) |
| Claude Code harness hooks | `notation-guard` · `results-no-overwrite` · `dispatch-readiness-guard` · `research-context-check` · `results-vault-reminder` · `git-commit-msg` |
| Test-suite gates | `validation` marker (mathematical correctness) · `integration` marker · binding tests |

**Out of scope:**

- **CodeRabbit and Codacy** (User, 2026-07-16). External to the repo; a
  deliberate violation cannot be introduced and reverted the way §3 requires, so
  they cannot meet the standard of evidence. Excluded outright rather than
  carried as `UNVERIFIABLE` — a register should list what it can test. Recorded
  once, not re-litigated: **review-then-merge is enforced by the User's habit,
  not by a mechanism**, and it was the only automated verification provably
  running during the 47-day outage.
- Designing new gates; the T1.38 compute; any prose Task.

This audit establishes *evidence about existing gates*. New enforcement is an
output of Phase D, not an assumption of Phase A.

**Non-negotiable constraint:** this audit must not itself become a documented
gate that nobody ran. Its deliverable is **observed evidence**, not a register of
intentions.

---

## 3. The standard of evidence

A gate is **LIVE** only if all four hold. Anything less is a finding.

1. **Exists** — the check is implemented in code, and the code is identified by
   path and line.
2. **Wired** — it is bound to a trigger that actually executes (correct
   `hooksPath`, registered in `settings.json`, collected by pytest, invoked by
   the dispatch path). *Verified by execution, never by reading config.*
3. **Fires** — **someone has watched it fail.** A deliberate violation was
   introduced, the gate returned non-zero with a diagnostic naming the
   violation, and the violation was restored. **This is the load-bearing
   criterion and the reason the audit exists.**
4. **Fires only when it should** — a known-good input passes. A gate failing
   this is Mode 3 and is reported at the same severity as a dead one.

Recorded verdicts: `LIVE` · `DEAD` (fails 1 or 2) · `INERT` (exists and wired,
never observed to fire) · `NOISY` (fails 4) · `UNCOVERED` (live but claims
nothing) · `UNVERIFIABLE` (no artifact can decide — record it, do not infer).

**The precedent already exists.** Manager 13 proved Gate 0 by diverging a
`SKILL.md`, watching exit 1 with "skill trees diverged — commit blocked", and
restoring. The W2 audit proved the greedy replica by reproducing a committed
value bit-for-bit. T1.38's three contracts each require a binding test carrying a
**negative control that proves the screen can fire**. This plan does not invent a
method; it **promotes an existing one from ad-hoc to systematic**.

---

## 4. Phases

### Phase A — Inventory and liveness triage (read-only, ~1 Task)

Enumerate every gate in scope. For each record: path, trigger, what it claims to
enforce, where that claim is *documented*, and — separately — where it is
*implemented*. **Diff those two columns.** Gate 0 lived in the gap between them,
and the gap is the finding.

Two specific sweeps, because both known dead gates would have been caught by one
of them:

- **Documentation→implementation:** every gate named in `CONVENTIONS.md`,
  `CLAUDE.md`, `README.md`, any `SKILL.md`, or an APM guide → resolve to the
  line that implements it. An unresolvable claim is a Mode-2 finding.
- **Zombie sweep:** every file that *looks* like an installed hook but sits
  outside the active path (`.git/hooks/`, stale copies, orphaned worktree
  hooks). **Diff the corpse before burying it** — the zombie was Gate 0's sole
  implementation.

**Output:** `results/governance/gate_register_<date>.json` + a table.
Verdicts limited to `DEAD` / `UNCOVERED` / "candidate LIVE (unproven)".
**No gate may be marked LIVE in Phase A** — Phase A cannot satisfy criterion 3.

### Phase B — The negative-control battery (the core, ~1–2 Tasks)

For every candidate-LIVE gate: introduce a deliberate, minimal, reverted
violation; observe the failure; restore; record the evidence.

Per gate, record: the violation, the exact command, the observed exit code, the
**verbatim diagnostic**, restoration confirmation, and a clean-tree pass
(criterion 4).

Design constraints, each earned:

- **Violations are surgical and reverted in the same step.** Never leave a
  violated tree.
- **Never on `main`.** Dedicated branch/worktree.
- **A gate that cannot be violated without destructive side effects is itself a
  finding** — record it `UNVERIFIABLE` and propose a testable seam. Do not force
  it.
- **`results/` stays real.** No synthetic or toy artifact is written to
  `results/` — an autonomous agent once committed toy p-values there under
  date-suffixed names. Fixtures live in `tests/fixtures/` or a scratch path.
- **The battery must run in a worktree**, because two of the three known failure
  modes (`hooksPath` resolution, autocrlf sha drift) *only manifest* in a linked
  worktree. Testing at `PROJ_ROOT` alone would have missed both.

**Output:** `results/governance/gate_liveness_evidence_<date>.json` — one
observed-failure record per gate. **This file is the deliverable.** Everything
else is scaffolding.

### Phase C — Coverage triage (User decision, folds in the existing item)

Manager 13's gate-4 backlog item belongs here as **Mode 1 for one gate**, not as
a separate workstream. Reproduce the measurement (glob `results/**/*.json`
against every `output_validation.applies_to_glob`), then triage the four
*result* directories — 16 in `trajectory_tda_integration/`, 16 in `post_audit/`,
12 in `trajectory_tda_bhps/`, 9 in `h2_check/`.

**Per directory, a User call:** citable ⇒ needs an `output_validation` contract;
intermediate ⇒ legitimately does not. Most of the 348 are genuinely intermediate
(62 are spanning-inference checkpoints). **Do not close on the 0-violations
number.**

Generalise the sweep to every gate with a claim surface, not just gate 4: for
each, what does it claim to cover, and what does it actually reach?

### Phase D — Standing enforcement (design only; dispatch after A–C report)

Convert one-shot evidence into a property that cannot silently lapse. Candidates,
**to be chosen on Phase A–C findings rather than committed to now**:

1. **Liveness canary in CI** — a job that violates each gate and asserts
   non-zero. A gate going dead then breaks a build instead of going quiet.
   Directly answers "has anyone watched it fail?" on every run.
2. **`hook-gate` generalisation** — `manager_dispatch_check` already asserts the
   pre-commit hook is live and a Manager reads it at every dispatch. That works
   *because it is read*. R-C failed because it was passive. Extend the same
   read-path assertion to the other gates.
3. **Fix Mode 3 at the root** — add `.gitattributes` normalisation, or change
   the manifest rule to sign text inputs by **git blob hash** rather than
   working-tree sha256. The current rule is unsound and only luck has hidden it.
4. **Ship every new gate with its negative control** — promote the T1.38 contract
   pattern (binding tests must prove the screen fires) into the contract
   meta-schema so an un-negative-controlled gate cannot be registered.

**Recommendation:** (3) first — it is a live, known-unsound rule with a bounded
fix — then (1). (4) is the durable one but should be shaped by what A–C actually
find.

---

## 5. Sequencing, cost, risk

| Phase | Agent | Cost | Gate |
|---|---|---|---|
| A | reproducibility-agent | Low — read-only sweep | — |
| B | reproducibility-agent | Medium — many small violate/observe/restore cycles | Needs A's register |
| C | Manager + **User decision** per directory | Low compute; the cost is judgement | Independent of A/B |
| D | TBD | TBD | **Do not scope until A–C report** |

**Concurrency:** A/B are governance-only and touch no paper artifact, so they run
alongside T1.38 and the prose Tasks without contention. C needs your attention,
which is the scarce input — it should not land while you are reviewing §4.2.

**Risks.**

- *The audit becomes theatre.* The whole failure class is documented-but-unrun.
  Mitigation: Phase B's evidence file is the deliverable; a register without
  observed failures is an explicit non-completion.
- *A violation escapes.* Mitigation: dedicated worktree, surgical reverts,
  never `main`, clean-tree confirmation per gate.
- *Findings cascade into the paper.* If a gate is found dead, artifacts it was
  believed to cover become unverified — exactly the T1.38 shape. Mitigation:
  record the exposure, **do not** auto-condemn. Where an artifact survives,
  decide by artifact; where none does, record `UNVERIFIABLE`. **Never date an
  environment from a lockfile** — a pin records when something became
  *guaranteed*, never when it became *present*.
- *Scope explosion.* Every gate invites a redesign. Mitigation: A–C establish
  evidence only; design is deferred to D by construction.

---

## 6. What this plan refuses to do

- **Assert any gate is live without watching it fail.** That is the error under
  audit, and repeating it in the audit itself would be the funniest possible
  outcome.
- **Rebuild a gate from its documentation.** Every restoration reads the
  implementation — including dead implementations — first.
- **Close Mode 1 on a zero.** A file no contract claims is *skipped*, not
  validated, and skipping is silent.
- **Treat a passing test suite as evidence.** Lint, unit tests and smoke runs all
  passed throughout the 47-day outage and throughout the greedy-W₂ affair. They
  prove the code does what it does, never what it was promised to do.

---

## 7. Open questions for the User

1. **Phase A+B as one dispatch or two?** They are one intellectual act
   (enumerate, then prove); splitting adds a round trip, batching risks a large
   Task. **Recommendation: one batch, `reproducibility-agent`, phase-boundary
   report** — the same shape as T1.38.
2. **Phase C timing** — it needs your judgement per directory. **Recommendation:
   after your §4.2/§6.2 review**, so it is not competing for attention.
3. **Does the audit cover CodeRabbit/Codacy?** They are the only automated
   verification that provably ran for three months. They are also outside the
   repo and cannot be negative-controlled the same way. **Recommendation:
   inventory them in A, mark `UNVERIFIABLE` by this method, and note that
   review-then-merge is enforced by your habit rather than by a mechanism — which
   is itself worth knowing.**
4. **Appetite for Phase D now, or strictly after A–C report?**
   **Recommendation: strictly after**, with the single exception of the autocrlf
   fix, which is a known-unsound live rule and should not wait.
