---
name: scout-review
description: Use after Scout drops a new vault/00-Meta/Discovery/_inbox/YYYY-Www.md to triage the week's literature hits — cluster, drop noise, write a one-line relevance note per survivor, and shortlist PROMOTE candidates into _backlog.md for Assay.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---

# Scout Review

Deferred **judgment** half of Scout (Discovery & Triage Harness D5: Codex gathers,
Claude judges). Scout's weekly job is gather-only — it applies a relevance gate and
stream tags mechanically, with no viability judgment. This skill is the first human-in-
the-loop pass: it does not score viability (that is `/assay`); it decides what is worth
a `/assay` pass at all, and gets each survivor a one-line reason tied to the programme.

## When to run

Whenever you sit down and a new `vault/00-Meta/Discovery/_inbox/YYYY-Www.md` exists that
hasn't been triaged yet — i.e. the inbox note has **no `## Triage` section** (the completion
marker written in step 6). A week can be fully triaged with **zero** `_backlog.md` entries
(all hits dropped), so backlog presence is NOT the trigger. Triggered manually — there is no
scheduler for this half.

## Pre-flight self-check (re-read before emitting)

Before writing the triage output, re-confirm:

1. **Don't trust the inbox stream tags at face value.** They are produced by a
   mechanical keyword match against `scout/watchlist.yaml` (`tda_terms` gate +
   `topic_keywords` labels). Shared/generic terms can mis-tag a hit into every stream,
   or a real hit can land untagged. Judge relevance from the title/abstract yourself.
2. **The relevance gate already ran** (every hit in the inbox matched a `tda_terms`
   entry) — so "is this TDA at all" is mostly pre-filtered. Your job is "is this TDA
   relevant to *this programme*," which the gate cannot know.
3. **Programme-fit is not required for PROMOTE** (D2: viability excludes programme-fit
   on purpose) — don't drop a hit just because it doesn't extend P01–P10. Drop it only
   for noise, irrelevance to TDA-as-method, or being a known/saturated benchmark result
   with nothing new.
4. **No viability scoring here.** Do not attempt Axis-1/2/3 from the Assay rubric
   (`docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md` §5). A `triaged` entry in
   `_backlog.md` records *why it's worth assaying*, not a score.
5. **State is one-way forward.** This skill only ever produces `triaged` entries (or
   drops a hit silently with a logged reason in the triage table). It never marks
   `assayed`, `spiked`, `registered`, etc. — those are `/assay` and `/spike`.

## Procedure

1. **Locate the input.** Read the most recent inbox note with **no `## Triage` section** yet, `vault/00-Meta/Discovery/_inbox/YYYY-Www.md`
   (`Glob` does not cross the `vault/` junction — use `Read` on the known path or
   PowerShell `Get-ChildItem` to list `_inbox/`). Note the `week`, `since`, and hit count
   from the frontmatter.
2. **Read every hit.** Title, authors, year, ID, matched terms, abstract. Treat the
   bracketed `[stream, ...]` tag as a hint only, never a verdict — especially if the
   handoff or daily note for that inbox flags the tagging as not yet fixed.
3. **Cluster** hits that are near-duplicates or trivially the same finding from
   different sources; keep the strongest representative, note the rest as merged.
4. **Triage each survivor keep/drop:**
   - **Drop** (noise) when: the relevance gate false-positived on a shared generic term
     and the paper is not actually about topological methods as a research tool (e.g.
     a clinical/graph-theory paper that happens to use "segregation" or "network" in a
     non-topological sense); the abstract is empty/unusable and no other signal
     justifies a closer look; it is a marketing/preprint-mill framework paper with no
     falsifiable claim or evaluation.
   - **Keep** when: the paper uses persistent homology / persistence diagrams / Mapper /
     persistent Laplacians / topological deep learning as a genuine method, on data or
     for a question with plausible relevance to the programme's domains (longitudinal/
     panel social data, financial time series, spatial inequality, or the TDA methods
     frontier itself, per D2's "genuine breadth beyond P01–P10").
   - Every kept and dropped hit gets a **one-line reason**. For keeps, the reason ties
     the paper to the programme (which stream/paper line it could feed, or which Axis-1
     style question it raises) — not a restatement of the abstract.
5. **Shortlist PROMOTE candidates.** Among the keeps, the strongest go forward to
   `_backlog.md` as `state: triaged` — these are the ones worth spending an `/assay`
   pass on. Not every "keep" needs to be a backlog entry: a keep can be filed as
   informational (cross-link candidate for `01-Literature`) without entering the
   backlog if it's relevant-but-not-actionable (e.g. background reading, a competitor
   method to be aware of, not a candidate research direction).
6. **Write the triage output** back into the inbox note itself (append a `## Triage`
   section after `## Hits`, top of that section is fine since hits don't change) — do
   not create a separate triage file. Use the table format in Output below. **This
   `## Triage` section is the completion marker** checked by "When to run" — its presence
   means the week is triaged even if it produced zero `_backlog.md` entries.
7. **Update `_backlog.md`** — add a new top-of-page entry (reverse-chronological) per
   PROMOTE candidate, `state: triaged`, with the source inbox week and the one-line
   relevance note carried over. If `_backlog.md` does not exist yet, create it with the
   header in Output below.
8. **Vault sync.** This is triage judgment, not a `[RESULT]`/`[DECISION]` artifact — no
   Computational-Log entry is required. If the session produced a workflow lesson (e.g.
   a recurring tagging problem in Scout's gather step), note it in the daily note per
   the standard After-Session Sync convention.

## Output format

In the inbox note, append:

```markdown
## Triage — <date>, by /scout-review

| Hit | Verdict | Reason |
|---|---|---|
| Murris/Stolz/Borgwardt — "From Persistence to Survival" | KEEP — PROMOTE | Structured hypothesis testing for persistence diagrams; directly usable in P01-B. |
| Dattola et al. — EEG network density in MCI | DROP | Gate false-positived on "segregation"; clinical graph metrics, not TDA. |
```

In `_backlog.md`, each entry (top of page, reverse-chronological):

```markdown
## <slug> — <short title>

- **state:** triaged
- **source:** _inbox/2026-W25.md
- **id:** arXiv:2606.11911
- **authors:** Murris, Stolz, Borgwardt
- **relevance:** Survival-analysis framing for persistence-diagram hypothesis testing —
  candidate method extension for P01-B's structured testing problem.
- **next:** /assay
```

## Lifecycle states (reference — plan §8)

```
inbox → triaged → assayed ─(PROMOTE)→ spiked → registered → in-progress → submitted → …
                     ├─(PARK)→ parked (revisit trigger recorded)
                     └─(KILL)→ killed (reason recorded; feeds Scout)
```

This skill only ever writes `triaged`. `_backlog.md` is the single source of truth for
state — never duplicate state tracking elsewhere.

## Escalate or stop when

- The inbox frontmatter's stream tags are systematically wrong in a way that suggests
  `scout/watchlist.yaml` itself needs a fix (not just this week's noise) — flag it, do
  not silently route around a broken watchlist forever.
- A hit looks PROMOTE-worthy but you can't tell from the abstract alone whether a
  genuine metric space / falsifiable feature exists — keep it as `triaged` with that
  uncertainty named in the relevance note; let `/assay`'s Axis-1 gate resolve it. Do not
  pre-judge Axis-1 here.
- Two inbox weeks have gone untriaged — say so; backlog freshness depends on this
  running close to weekly.

## Reuse map

- Reads: `vault/00-Meta/Discovery/_inbox/*.md`, `scout/watchlist.yaml` (context only).
- Writes: the inbox note's own `## Triage` section, `vault/00-Meta/Discovery/_backlog.md`.
- Hands off to: `/assay` (scores `triaged` candidates), `01-Literature` (cross-link
  informational keeps that aren't backlog candidates).
