# Fable 5 Brief — Next-Wave Research Portfolio Rebalance

*Prepared 2026-07-03. Paste as the opening prompt for a tool-enabled Fable 5 session with Read/Grep/vault access to the TDL repo and the TDA-Research vault.*

---

You are acting as strategic research director for **TDL (Topological Data Lab)** — a
programme applying topological data analysis, topological deep learning, and geometric
deep learning to produce novel academic research. Work in your systematic mode:
plan in explicit stages, delegate self-contained sub-tasks to sub-agents, and verify
each stage before moving on. Take your time; correctness and insight matter more than speed.

## Givens — settled, do NOT re-open

Treat the following as delivered and out of scope. Do not audit, re-plan, or second-guess them:

- The **Agentic Research System (ARS)** will be completed and available as research
  infrastructure. Read enough to understand what it will provide; do not redesign it.
- Papers **P01-A, P01-B, and P04** will reach submission. They are shipping. Do not
  re-plan them.

Your remit begins **where these leave off**.

## Mission

Produce a **portfolio review and rebalance of the *future* research programme** — the
next wave, ~**6–18 month** horizon — that jointly optimises for **novel research frontier**
and **insight capability**. The rebalance allocates the two scarce resources (Stephen's
attention and agent compute) across a **three-track** portfolio:

- **Track A — Adjacent, edge-leveraging.** Directions where TDL's existing edge transfers:
  panel/longitudinal + large-N methods, UK microdata access (BHPS/UKHLS), the
  Wasserstein-2 / persistence-landscape / Morse-Smale / multiparameter machinery. Faster,
  more fundable, lower-risk (e.g. health inequality, demography, mobility, econ history).
- **Track B — Bold, method-led, domain-agnostic.** Follow the topology, not the domain:
  any field where TDA is genuinely underused *and* the machinery gives an edge —
  neuroscience, ecology, climate, genomics, materials — judged on fit, not familiarity.
- **Track C — Frontier mathematics.** The methodological frontier of the method itself,
  applied to data TDL could already reach: multiparameter persistence, topological deep
  learning, sheaves/cellular sheaf theory, quiver representations, and related advanced
  machinery. Judge each on what genuinely new question it lets TDL ask, not novelty for
  its own sake.

This third track is **deliberately exploratory** — kept open to preserve optionality.
The portfolio may narrow to two tracks at a later point; for now, carry all three.

**Cap: at most 3 candidate directions per track.** Commit; do not sprawl.

## The two operating engines the portfolio must be wired around

These are not line items — they are the machinery the whole portfolio runs on. Every
recommended direction must say how it uses them:

1. **Scout** — the literature/discovery engine that surfaces new research directions.
   It is your *starting signal* (see method below).
2. **Live TTK / ParaView** — topological visualisation as a *mid-analysis instrument*,
   not an end-of-pipeline afterthought. **Caveat:** the current TTK setup docs are partly
   stale. There was a Python conflict with the locked 3.13 venv that now has an effective
   workaround; TTK likely needs setting up again, but the process is known and should be
   **planned for and delegated to an implementation agent** — not solved by you. Reason
   about TTK's *strategic value* (what seeing the topology live changes about which
   directions are worth pursuing), and treat its re-establishment as a delegated work item.

## Stance on the existing slate

The current later programme (P05–P10, FIN-01 in the Meta-Research-Plan) is **reference
only** — evidence of Stephen's interests. You are free to supersede any of it. Propose the
ideal next-wave portfolio from a clean slate.

## Read first (you are tool-enabled — read these yourself)

**Vision & existing slate (reference only):**
- `docs/plans/strategy/Meta-Research-Plan-23-03-2026.md`

**Discovery engine (Scout):**
- `scout/scout-weekly-job.md`
- `docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md`
- the vault Discovery backlog (`vault/00-Meta/Discovery/_backlog.md` and `_inbox/`)

**Insight engine (TTK — treat as strategic context, docs partly stale):**
- `docs/TTK_SETUP.md`, `docs/TTK_ENHANCED_INTEGRATION.md`
- `shared/ttk_visualization/README.md`, the domain `*/viz/paraview_*` directories

**ARS — rough understanding only:**
- `docs/plans/agentic-research-system/00-master-transition-plan.md`
- `docs/plans/agentic-research-system/design/README.md`

**Constraints, method arsenal & edge:**
- `CLAUDE.md`, `CONVENTIONS.md` (locked methodological mandates)
- current paper `_project.md` files under `papers/`

**Data — note on scope:** identifying the right datasets is itself one of the tasks, not a
given. Do **not** treat any existing data holding as the boundary. The only hard constraint
is **publicly available / open data**; within that the option space is very large and
Stephen will fetch sources as needed. Orient each candidate direction around what open data
would suit it, and name concrete open datasets where you can.

## Method (stages — verify each before proceeding)

1. **Inventory & edge.** Extract TDL's genuine edge: methods, data access, and realistic
   capacity (solo researcher + agent workforce). State it plainly — everything downstream
   is judged against it.
2. **Three-track frontier scan.** *Start inside the Scout signal* (backlog + inbox). Apply a
   **forceful filter** so only strong-signal candidates survive. **Then roam outward** from
   those survivors — external literature and method-led reasoning — to complete each track.
   Do not skip the hard filter; the Scout seed is the discipline that keeps the scan grounded.
   For Track C the seed may be thinner in Scout — supplement from the methodological
   literature, but hold it to the same "what new question does it enable" bar.
3. **Insight-capability audit.** For the surviving candidates, ask what live TTK/ParaView
   could actually *show* that changes their value, and how to make visualisation
   mid-analysis. Fold TTK re-establishment in as a delegated work item.
4. **Score & rebalance.** Assay-style scorecards per candidate: novelty, data feasibility
   (verified, not assumed), "topology-earns-its-keep", effort. Allocate attention/compute
   across the surviving portfolio.
5. **Synthesise** the rebalanced portfolio into the deliverable below.

## Deliverable

Write a single document to
`docs/plans/strategy/next-wave-portfolio-rebalance-2026-07-03.md` containing:

- **(a) Executive rebalance** — the recommended allocation of attention/compute across the
  next wave, in a sentence or two plus a simple table.
- **(b) Three-track shortlist** — ≤3 candidates per track (A, B, C), each with an
  assay-style scorecard.
- **(c) Recommended portfolio + sequencing** over the 6–18 month horizon.
- **(d) Operating engines** — concretely how Scout and live TTK feed and shape the
  portfolio, including the delegated TTK re-establishment task.
- **(e) Risks, park/kill criteria, and explicit User-decision points** — the judgement
  calls that are Stephen's to make, surfaced, not guessed.

## Guardrails

- Respect the locked TDA mandates: Wasserstein-2 is primary (landscape L² its mandatory
  complement); never run PH on raw trajectories (embed first); never assume BHPS and
  Understanding Society share coding; topology must demonstrably earn its keep.
- **Verify feasibility — do not assume it.** Whether suitable *open* data plausibly exists,
  and whether topology adds signal, are checkable; check before recommending. Flag anything
  unverifiable as a User-decision.
- Surface judgement calls and outcome-contingent forks as explicit User-decision points.
  Do not present speculative directions as settled.
- Delegate self-contained work (TTK setup planning, deep literature dives per candidate)
  to sub-agents; keep your own context for synthesis.

## Kickoff

Begin by reading the pointers above and drafting your staged plan for approval before you
run the frontier scan. Show me the plan first.
