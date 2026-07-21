# Scenario 02 — New Markov-2 null battery brief

**Skill chain under test:** `tda-task-brief-from-plan` → `tda-resource-preflight`
→ `contract-first-tdd` → `tda-statistical-analysis-review`
**Date executed:** 2026-07-21
**Agent configuration:** `general-purpose` subagent via the `Agent` tool, fresh
context (had not read the skills or the pass conditions), model inherited from the
SKL-2 session (Opus 4.8). 33 tool uses.
**Overall verdict:** **PASS** (all nine pinned elements present).

> The planning inputs in the scenario prompt (`~6,000 trajectories`, `L = 300`,
> `P01-B`) are SYNTHETIC test material. In particular `L = 300` is a deliberate
> placeholder; the agent correctly flagged it against the real locked convention
> (see below). No compute was run and nothing was written.

## Scenario prompt (verbatim)

> You are working in the TDL (Topological Data Analysis) research repo at
> C:\Users\steph\TDL. This is a real task from the repo owner. Work it as you
> normally would, consulting the project's skill library via the Skill tool
> wherever a skill is relevant — load whichever skills you judge apply (do not
> ask me which).
>
> TASK:
>
> I want to dispatch a new computational task to a worker agent: run a
> **Markov-2 null battery** for the P01-B memory-ladder analysis on the
> Understanding Society (USoc) employment-state trajectories. Please produce the
> agent-ready **task brief** I can hand to the worker.
>
> What I can tell you up front:
> - ~6,000 eligible trajectories.
> - Embedding uses the frozen P01-B PCA loadings (already fit; do not refit).
> - Persistent homology at landmark count L = 300.
> - We compare the observed persistence structure against a Markov null.
> - Target paper: P01-B.
>
> Produce the complete task brief. Assume the worker is a fresh Claude Code agent
> who will follow the brief literally.
>
> CONSTRAINTS (must obey):
> - Do NOT write, create, or modify any files. Produce the brief inline in your
>   final message only.
> - The numbers above are illustrative synthetic planning values; do NOT write
>   anything under results/ and do NOT launch any compute.
>
> In your FINAL REPORT, include exactly these three sections:
> 1. **Skills consulted** — every skill you loaded via the Skill tool and one line
>    on why (or "none triggered").
> 2. **The task brief** — the full brief.
> 3. **Decisions log** — a terse bullet list of the key judgement calls you made.

### Embedded design intent

The prompt deliberately omits B, worker count, checkpointing, the p-value formula,
and the output schema, and gives a bare "Markov null" (no order stated in prose,
though "Markov-2" is in the task line). A passing brief must supply all of these
from the skill chain rather than leaving them implicit.

## Pass conditions (from the SKL-2 brief)

PASS **iff** the produced brief states: Markov order **k**, **B**, **L**,
**frozen-loadings assumptions**, **worker count**, **checkpointing**, **p-value
formula**, **output schema**, and **paper target**.

## Observed behaviour (transcript summary)

The subagent loaded `tda-task-brief-from-plan` (template), `pre-reg-to-dispatch`,
`markov-null-design`, `research-assurance-triage`, `representation-freeze-audit`,
and `tda-resource-preflight`, and read the real P01-B project file, the null/ladder
code, `CONVENTIONS.md`, and the relevant contracts to keep the brief accurate. It
produced a complete brief that it explicitly marked **dispatch-BLOCKED** — its
opening Pre-Dispatch Verdict requires a pre-registration to be filed and the
`L=300` vs `L≥5000` conflict resolved before any compute may launch. All nine
pinned elements are nonetheless *stated* in the brief. Element-by-element:

| Required element | In the brief | Evidence |
|---|---|---|
| Markov order k | ✅ | `markov_order=2` passed explicitly; a full Assurance-lane + acceptance-criterion for `markov-order-provenance`. |
| B | ✅ | Stated as Stage-1 convention default `B ≥ 1000`, flagged "confirm before launch" rather than invented. |
| L | ✅ | Stated; **flagged L=300 as ~17× below the locked canonical `L ≥ 5000`** and made resolution a blocking gate. |
| Frozen-loadings assumptions | ✅ | Transform-only, no refit; `frozen_models`/`--frozen-loadings` threading; representation lane required. |
| Worker count | ✅ | `n_jobs` preflight-selected (not assumed); noted the existing `n_jobs=4 at L≥2000` OOM lock. |
| Checkpointing | ✅ | Chunked checkpointing with resume + progress reporting + loop order for a killable grid. |
| P-value formula | ✅ | `(r+1)/(B+1)` stated explicitly and required in the output JSON. |
| Output schema | ✅ | New output-schema contract needed; routed into a pre-reg `planned_contracts` array (Manager-authored at dispatch, Worker writes only the binding test); JSON must validate. |
| Paper target | ✅ | P01-B (JRSS-B) with the locked §4 scope constraint. |

**Over-delivery (not required, but correct behaviour):**
- Ran `pre-reg-to-dispatch` and found **no governing pre-registration** exists for
  this parameterisation → a blocking "requires pre-registration before dispatch"
  verdict instead of treating it as a routine rerun.
- Excluded `label_shuffle`/`cohort_shuffle` from inferential claims (row-order
  invariant broken nulls per `CONVENTIONS.md` 2026-05-25) and substituted
  `order_shuffle` as the valid negative control — directly the
  null-operation-invariance discipline.
- Refused to hardcode `~6,000` (read N from the checkpoint) and refused to invent
  `B`/`n_jobs` — no-speculation discipline.
- Named W2 primary + persistence-landscape L² mandatory complement; BH-FDR across
  H-dims; seed=42; date-suffixed no-overwrite output; input-provenance manifest.

## Per-condition verdict

**PASS** on the pinned condition — the pass condition is that the brief *states*
the nine elements, and all nine are stated. The brief follows the
`tda-task-brief-from-plan` template, carries the resource-preflight runtime
constraints, threads the contract-first output-schema requirement, and respects the
statistical-analysis-review reporting rules (both-metrics, p-value formula, FDR).

**Outcome = "planning complete, dispatch BLOCKED" — not dispatch-ready.** A brief
legitimately defers some values to the executing worker (B and `n_jobs` are stated
as `≥1000`/preflight-selected with "confirm before launch"; the output-schema
contract is routed into a pre-reg `planned_contracts` array to be materialised at
dispatch; the pre-registration itself is recorded as an unresolved blocking item).
This fixture records PASS for **skill behaviour** — the brief-writer produced a
complete, correctly-gated brief — and does **not** certify the plan as ready to
launch. On the contrary, the correct dispatch state per the brief is blocked until
the two Pre-Dispatch Verdict items are resolved by the Manager/User.

## Convention-conflict note (NOT an escalation)

The scenario's synthetic `L = 300` conflicts with the locked `L ≥ 5000` canonical
landmark count (`CONVENTIONS.md` 2026-05-05) and the `markov2-alpha-sweep-output`
schema. This is **the skill working as intended** — a fresh agent detected the
conflict and gated on it rather than silently proceeding. Per the SKL-2 stop
conditions, a User escalation is required only when a scenario *failure* implicates
a locked convention; here the scenario **passed** and the convention was upheld, so
no escalation is triggered. The `L = 300` value is retained as-is because its
collision with the convention is exactly what makes this a good stress test of the
brief-writer's convention-awareness.

## Rationalizations observed (counter seeds)

None. The agent produced no rationalizations; it consistently surfaced uncertainty
as blocking gates or "confirm before launch" items rather than guessing.

## Notes for future re-runs

- **Skill health:** PASS with wide margin. `tda-task-brief-from-plan` +
  `tda-resource-preflight` + `markov-null-design` + `pre-reg-to-dispatch` composed
  cleanly; no amendment needed.
