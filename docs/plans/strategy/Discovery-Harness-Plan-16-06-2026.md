# TDA Discovery & Triage Harness — Plan

> **Created 2026-06-16.** Companion to the static
> [`Meta-Research-Plan-23-03-2026.md`](./Meta-Research-Plan-23-03-2026.md) and
> [`vault/00-Meta/Programme-Map.md`](../../../vault/00-Meta/Programme-Map.md).
> Those two documents are *outputs* of a one-shot topic-selection exercise; this
> document specifies the **living, repeatable harness** that should produce and
> triage candidate topics from now on.
>
> **Status:** design locked, not yet built. Vault companion:
> `vault/00-Meta/Discovery-Harness.md`.

---

## 1. The gap this addresses

The current harness is a mature **execution + assurance backend**:

- ~14 execution/paper skills (`new-analysis`, `tda-experiment`, `markov-null-design`,
  `tda-figure-spec`, `paper-draft`, `paper-repo-extract`, …).
- ~14 assurance skills (`research-assurance-triage`, `statistical-design-audit`,
  `topology-benchmark-review`, `validate-topology`, the freeze/provenance/claim-trace
  audits, `schema-contract-design`) backed by `contracts/` + `contract_binding_check.py`.
- APM orchestration (planner/manager/worker, file-based bus, worktrees, tracker).
- 6 enforcement hooks (notation-guard, results-no-overwrite, research-context-check,
  vault reminders, commit-msg).

Every one of those sits **downstream of "we have decided to write paper PXX."** The
only topic-selection artifacts are the two static documents above. The live vault has
**no home** for candidate ideas at all (top level is `00-Meta, 01-Literature, 02-Notes,
03-Papers, 04-Methods, …` — there is no `04-Ideas/`; that was a *proposed* tree in
`Obsidian-Overview-23-03-2026.md` that was never created).

Two structural observations:

1. The 14-skill **assurance explosion is itself a symptom** — it is compensation for
   APM not natively enforcing research validity. The new layer must **reuse** it, not
   regrow a parallel set.
2. Multi-tool portability (Codex) is feasible **because APM coordination is already
   file-based** (the bus, not API calls). The durable artifacts are plain files; the
   skills are merely Claude's convenience wrapper over them.

## 2. Design decisions locked (2026-06-16 session)

| # | Decision | Rationale |
|---|---|---|
| D1 | Build the **full idea→execution→assurance→publish loop**, phased delivery. | One coherent system, value delivered early (Phase A). |
| D2 | Viability = **topology-earns-its-keep + data-feasibility + novelty**. *Programme-fit deliberately excluded.* | Wants genuine breadth beyond P01–P10; the rubric must not reward "extends the existing pipeline." |
| D3 | Durable artifacts are **tool-agnostic files**; build & validate **Claude-first**. | Lets Codex CLI join later with zero rework. |
| D4 | Intake = **standing surveillance** (auto drip into an inbox). | Not on-demand-only; not manual-only. |
| D5 | Scout runner = **cron fetch (free, no LLM) + deferred `/scout-review` triage**. | No API; stays within subscription; user stays in the loop. Promotable to a scheduled cloud routine after a tier upgrade. |
| D6 | This session produces a **durable plan doc + vault entry only** — no building yet. | Review the whole design before committing code. |

## 2a. Update — 2026-06-16 (evening): open questions resolved

- **OQ1 (PROMOTE rule):** approved as proposed, for pressure-test — Axis‑1 gate must pass;
  Axes 2–3 each 0–3; PROMOTE iff gate‑pass **and** (Axis2 + Axis3) ≥ 4 with neither = 0.
- **OQ3 (finance):** **FIN‑01 seeds a full finance TDA stream** (not a single paper).
  `q-fin.*` is a first-class Scout stream.
- **OQ4 (cadence):** weekly, **~20:00 local** (PC reliably on), **8‑day lookback**
  (1‑day overlap so the weekly boundary never drops a day).
- **OQ5 (Codex):** **Codex CLI 0.140.0 is installed**
  (`C:\Users\steph\AppData\Local\Programs\OpenAI\Codex\bin\codex.exe`; non-interactive
  `codex exec`; TDL is a *trusted* Codex project). Codex becomes the **Scout runner** — a
  clean two-agent split: **Codex owns the weekly gather** (fetch → extract → dedupe →
  inbox), **Claude owns the judgment** (`/scout-review`, `/assay`, `/spike`). This pulls
  the Phase C portability goal forward into Phase A.

**Phase A artifacts seeded this session:** `scout/watchlist.yaml` (5 streams; query
templates from the user's proven schedule-job prompts), `scout/scout-weekly-job.md` (the
Codex gather prompt — gather only, no triage), `scout/run-scout.ps1` (Task Scheduler
wrapper). **Not yet scheduled** — pending one interactive test run to confirm network
access under `codex exec -s workspace-write`. Scout intake is **gather-only**: Codex
collects and extracts; Claude's `/scout-review` does all triage/judgment.

## 3. The integrated loop

```
┌─ NEW: Discovery & Triage layer ─────────────────┐   ┌─ EXISTS: APM execution + assurance ─┐
                                                  │   │
 SCOUT          ASSAY             SPIKE            │   │  EXECUTION → ASSURANCE → PAPER
 surveillance   viability score   feasibility +   │   │  (worker/    (14 audit   (paper-
 → inbox        → ranked backlog  pre-registration│   │   bus/        skills +    draft,
                + kill criteria   (time-boxed)     │   │   worktrees)  contracts)  repo-extract)
                                                  │   │
└──────────────────────────────────────────────────┘   └─────────────────────────────────────┘
        ▲                                                              │
        └──────── feedback: [NEGATIVE] results + open questions ───────┘
```

New stages = **Scout / Assay / Spike** (prospecting labels). The **seam into APM is an
artifact APM already requires: the pre-registration.** The funnel hands the backend
vetted, pre-registered candidates; the backend is untouched.

## 4. SCOUT — standing surveillance → inbox

**Goal:** new, relevant papers drip into an inbox with no manual searching, at zero API cost.

**Watchlist config** (`scout/watchlist.yaml`, repo):
- arXiv categories: `math.AT` (alg. topology), `q-fin.*` (finance TDA), `stat.AP`,
  `stat.ME`, `cs.LG`, `cs.SI` (computational social science).
- Key authors (seed): Carlsson, Bubenik, Gidea, Katz, Perea, Mémoli, Bauer, Lapous (multipers),
  Bronstein (geometric DL) — refine in Open Question OQ2.
- Venues / journals to watch (JRSS, AoAS, JASA, AJS, BJS, JMLR, NeurIPS, FAccT, Physica A).
- Keyword set (persistent homology + social/longitudinal/panel/mobility/regime/inequality;
  zigzag; mapper; multiparameter; topological deep learning; CCNN; persistence landscape).

**Free sources (no LLM, no paid key):** arXiv API (no auth), OpenAlex (free, polite-pool
email), Semantic Scholar (free tier). These cover fetch + metadata + abstracts.

**Two-step split (forced by the no-API constraint):**

- **Fetch (free, automated):** a Python script (`scout/fetch.py`, run via
  `uv run --env-file .env`) pulls entries since the last run, **dedupes against
  `01-Literature`** and the previous inbox, and writes raw hits to a weekly inbox note.
  Triggered by **Windows Task Scheduler** on a weekly cron — no model involved.
- **Triage-prep (model, deferred):** a new **`/scout-review`** skill, run when you next
  sit down, clusters the week's hits, drops obvious noise, and drafts a one-line
  "why this might matter to TDL" per surviving cluster. Promotes the strongest into Assay.

**Inbox format:** `vault/00-Meta/Discovery/_inbox/YYYY-Www.md` — reverse-chronological,
one block per hit (title, authors, arXiv/DOI link, abstract, matched watchlist terms,
dedupe status). Cross-links into `01-Literature` when a hit is retained.

**Feedback loop:** finished papers' `[NEGATIVE]` results and recorded open questions
re-seed the watchlist keyword/author set — the funnel learns from what the programme
has already ruled in or out.

## 5. ASSAY — viability scoring → ranked backlog

**Goal:** decide, cheaply and before any compute, whether a candidate deserves a Spike.

A new **`/assay`** skill produces a **scorecard** per candidate
(`vault/00-Meta/Discovery/<slug>.md` + machine-readable block validated against a schema
in `contracts/`). Three axes, with the hard one run **first as a gate**:

### Axis 1 — Topology earns its keep (GATE; pass/fail, not scored)
Run adversarially — argue the *null* ("why TDA is **not** needed here") and require the
candidate to survive:
- Is there a genuine **metric space without an arbitrary embedding choice**? (Raw
  trajectories are not a metric space — embed first; see `CONVENTIONS.md`.)
- Does a **specific** topological feature (an H₁ loop, H₀ component count, a persistence
  signature) map to a **substantive, falsifiable claim**?
- Or is the claim **reducible** to clustering / PCA / a GMM a reviewer reaches for anyway?
- Is there a **named baseline** that TDA must beat?

Fail any → **KILL** here, at zero compute cost. This is the single most valuable filter,
and it is exactly the test most published TDA-in-social-science work fails.

### Axis 2 — Data feasibility (scored 0–3)
Metric space realisable on panels you have (USoc/BHPS) or can get (SOEP/PSID/CNEF — note
lead times); n large enough for a **permutation null**; embedding choice defensible;
BHPS↔USoc coding checked where relevant (`/bhps-wave-crosswalk`).

### Axis 3 — Novelty & publishability (scored 0–3)
Clear gap in the Scout-pulled literature; identifiable target venue; distinct from
existing work; not already a known benchmark (`/topology-benchmark-review`).

**Output:** `PROMOTE / PARK / KILL`. `PROMOTE` is surfaced as an explicit
**User-decision point** (per APM_RULES — the harness recommends, you decide). Promoted
candidates land in the living **`_backlog.md`** (ranked) — the dynamic replacement for
the static Programme-Map idea table.

**Kill-criteria / red-flag checklist** (any one is a strong KILL signal): no metric space
without arbitrary embedding; n too small for a null; claim reducible to clustering; no
baseline; the topological feature has no substantive interpretation; already published
as a benchmark; data inaccessible within the horizon.

## 6. SPIKE — feasibility probe → pre-registration

**Goal:** enforce "no speculative paths" *at the front door* — before a worktree exists.

A **time-boxed** feasibility probe (a new **`/spike`** skill; e.g. ≤ a few hours of
compute) on a promoted candidate:
- smallest-possible data pull + **toy-scale** topological computation
  (reuses `/new-analysis`, `/tda-experiment` at reduced scale);
- confirms the **metric space exists**, a **signal is detectable** at toy scale, and the
  **null is well-defined** (reuses `/null-operation-invariance-audit`,
  `/statistical-design-audit`, `/representation-freeze-audit`).

On success it **emits the pre-registration** (parameters, decision rule,
prose-direction-per-outcome, planned contracts) consumed by `/pre-reg-to-dispatch` — the
clean handoff into the APM Manager. On failure it writes a `[NEGATIVE]` note and the
candidate returns to PARK/KILL with reasons (feeding the Scout loop).

## 7. Reuse map (extend, don't regrow)

| New stage | Leans on existing |
|---|---|
| Scout | `01-Literature`, `[NEGATIVE]` prefix + open-questions feedback |
| Assay | `research-assurance-triage` (lightweight front version), `topology-benchmark-review`, `bhps-wave-crosswalk`, `contracts/` + `schema-contract-design` + `contract_binding_check.py` for the scorecard schema |
| Spike | `new-analysis`, `tda-experiment`, `null-operation-invariance-audit`, `statistical-design-audit`, `representation-freeze-audit`, `validate-topology`, `pre-reg-to-dispatch`; hooks: `results-no-overwrite`, `research-context-check` |
| Seam → APM | the pre-registration artifact → `apm-2-initiate-manager` and the existing worker/bus/worktree flow |

The only genuinely new enforcement artifact is the **scorecard schema** in `contracts/`
with its binding test — authored via the existing `schema-contract-design` skill.

## 8. Lifecycle status model

Extend the existing `idea → in-progress → submitted → under-review → published` with
front-of-funnel states; the **`_backlog.md` table is the single source of truth**:

```
inbox → triaged → assayed ─(PROMOTE)→ spiked → registered → in-progress → submitted → …
                     ├─(PARK)→ parked (revisit trigger recorded)
                     └─(KILL)→ killed (reason recorded; feeds Scout)
```

## 9. Portability seam (Codex-later)

Durable, tool-agnostic artifacts (no Claude-specific dependency):
- `scout/watchlist.yaml`, `scout/fetch.py` (plain Python)
- scorecard **JSON schema** in `contracts/` (+ binding test)
- `_backlog.md`, scorecard notes, inbox notes (plain markdown)
- pre-registration template + JSON (already tool-agnostic)
- APM **bus message format** (already file-based)

To let **Codex CLI** join (Phase C): add an **agent-neutral task contract** (a JSON/MD
spec a worker of any kind reads from `.apm/bus/`, executes, and writes results back) plus
a **plain-markdown playbook** mirroring each skill's procedure, so a Codex worker follows
the same steps without the Claude skill wrapper. Coordination stays filesystem-based;
never API. No Codex instance is needed to *design* this.

## 10. Artifact locations

- **Repo** (code): `scout/` (watchlist, fetch script), scorecard schema in `contracts/`,
  the new skills (`scout-review`, `assay`, `spike`), Codex playbooks (Phase C).
- **Vault** (research record): new **`00-Meta/Discovery/`** folder — `_inbox/`,
  per-candidate scorecards, `_backlog.md`. Keeps the low-folder-count vault philosophy
  (it is programme-meta, sitting beside `Programme-Map.md`). Surveillance hits cross-link
  into `01-Literature`.

## 11. Phasing & acceptance

| Phase | Deliverables | Done when |
|---|---|---|
| **A** (cheap, Claude-only, 0 API) | `scout/watchlist.yaml`, `scout/fetch.py` + Task Scheduler entry, `00-Meta/Discovery/` + inbox, `/scout-review`, `/assay` + scorecard schema/contract, `_backlog.md` | A real week's arXiv/OpenAlex hits land in the inbox automatically; `/scout-review` triages them; one candidate carried through `/assay` to a PROMOTE/PARK/KILL with a scorecard. |
| **B** | `/spike` skill + pre-reg seam; topology-earns-keep wired as a hard front gate | A promoted candidate runs a toy-scale Spike and emits a valid pre-reg that `/pre-reg-to-dispatch` accepts. |
| **C** | agent-neutral task contract + Codex playbooks; optional promotion of Scout to a scheduled cloud routine | A documented contract a non-Claude worker can execute against the bus; (optional) Scout runs unattended on cron in the cloud. |

## 12. Open questions (resolve before / during Phase A)

- **OQ1 — Rubric thresholds.** Numeric PROMOTE rule. Proposed: Axis-1 gate **must pass**;
  Axes 2–3 each 0–3; PROMOTE if gate-pass **and** (Axis2 + Axis3) ≥ 4 with neither = 0.
- **OQ2 — Seed watchlist.** Confirm/extend the arXiv categories, author list, venues, and
  keyword set in §4.
- **OQ3 — Finance TDA stream.** Is FIN-01 the seed of a *full finance funnel* or does it
  stay a single paper? (Scout covers `q-fin.*` either way.)
- **OQ4 — Cron cadence.** Weekly fetch assumed; confirm. Define the trigger for promoting
  Scout to a scheduled cloud routine (likely: after tier upgrade).
- **OQ5 — Codex timing.** When does Codex CLI actually arrive? Gates Phase C.

## 13. Risks & mitigations

- **Surveillance noise → triage fatigue.** Tight watchlist + dedupe + clustering + a weekly
  cap on hits surfaced.
- **Topology-earns-keep gate gamed by optimistic scoring.** Make it adversarial (argue why
  TDA is *not* needed); require a named baseline and a falsifiable mechanism.
- **Scorecard drift across sessions.** Schema + contract binding test + rubric pinned in the
  skill (the Pre-Flight principle: the skill re-reads its rubric before emitting).
- **Front-loaded work duplicating APM.** The seam is the pre-reg; Spike is strictly
  time-boxed and kills fast.
- **Breadth → scope sprawl** (programme-fit was dropped). Backlog WIP limit; PROMOTE is a
  user decision, not automatic.
