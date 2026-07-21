---
name: paper-draft
description: Use when starting or continuing a paper draft — loads _project.md status and open items, reads the current draft, and enforces the versioned vN-YYYY-MM draft convention (never overwrite a previous draft).
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - paper-claim
  roles:
    - implementer
    - claim-reviewer
  runtime: agnostic
---

# /paper-draft — Start or Continue a Paper Draft

Create or update a paper draft following the programme structure.

## Audience and register (governs everything below)

**You are writing manuscript text for a journal referee who has never seen this
repository, this Task, the reviewer-response plan, or Stephen.** P01-A → JRSS-A;
P01-B → JRSS-B; P04 → AoAS. They cannot see your instructions and will never read
your Task report.

**Separation of channels — a prose Task has two outputs with two readers:**
- **The draft/section file:** only text that could appear in the submitted PDF.
- **The Task Log / bus report:** *everything* else — traceability evidence, open
  items, gaps, provisionality, review status, Task/ISSUE IDs, anything addressed to
  the Manager or User, "out of scope for this Task".

**The test:** *would a referee reading the submitted PDF see this?* If no, it goes
in the report — which is the correct channel, not a lesser one.

**Banned in draft/section files:** `this working file` · `Task Prompt` · `Manager` ·
`ISSUE <ID>` · `response plan` · `v2 assembly` · `provisional label` ·
`awaiting review` · `out of scope for this Task` · `## Issues (for Manager review)` ·
HTML editorial-status comments · result-JSON filenames or repo paths in body text ·
Task/Stage numbers. Internal tracker IDs are scaffolding to dissolve, not structure
to mirror — a heading is `## Ground metric`, never `## Ground metric (corrects ISSUE H1)`.

**Provenance:** number-to-file traceability is satisfied in the Task Log, never
advertised in the prose. The manuscript cites methods, data, and results — not repo
paths. (Exception: a reproducibility/data-availability statement, a real paper
artifact written in the paper's voice.)

**Gaps** are either a genuine paper limitation (write it in the paper's voice) or a
workflow item (report only — it does not appear in the file). Never both.

**Pre-delivery self-check (do not skip):** re-read and delete anything a referee
could not read — banned tokens, self-referential preamble, `## Issues` sections,
tracker IDs in headings, repo paths, provisionality. Note in your report that you
ran it. `/humanizer` will **not** catch these: it targets AI tells, and workflow
scaffolding in a manuscript is a wrong-artifact problem.

Full rule: `.claude/rules/papers.md` § Prose work.

## Usage

```
/paper-draft PXX [draft|update|outline]
```

Examples:
- `/paper-draft P02 draft` — start first draft for P02
- `/paper-draft P01 update` — update/revise current draft
- `/paper-draft P02 outline` — create/update `_outline.md`

---

## Pre-flight checklist (always run first)

1. Read `papers/PXX/_project.md` — status, current draft path, open items.
2. Read the current draft (`drafts/vN-YYYY-MM.md`) if updating.
3. Read `docs/plans/strategy/Meta-Research-Plan-23-03-2026.md` §PXX — paper's planned contribution and framing.
4. Check `results/` for any new computation results to integrate.

## Output location

New drafts go to: `papers/PXX/drafts/vN+1-YYYY-MM.md`
- Increment version number from the current highest draft.
- Date = current month (YYYY-MM).
- **Never overwrite a previous draft.**

## After writing

1. Update `papers/PXX/_project.md`:
   - Increment the version in "Current draft" line.
   - Update open items (check off completed, add new ones).
   - Update `status` field if it changed.
2. Run `/humanizer` on the new draft before marking ready for submission.

## Structure for trajectory TDA papers (P01–P10)

Standard section order (adapt as needed per paper):
1. Abstract (250 words max, lead with the finding)
2. Introduction (motivation → gap → specific contribution → roadmap in ≤1 sentence)
3. Literature Review (OM/sequence analysis, TDA foundations, domain-specific background)
4. Data and Methods (data sources → embedding → PH → null models)
5. Results (ordered: descriptive → topological → null validation → regimes/clustering → stratification)
6. Discussion (what TDA adds, interpretation of key results, limitations)
7. Conclusion (not a summary — do new interpretive work)
8. References

## Keywords to include (vary by paper)

persistent homology, topological data analysis, Wasserstein distance, Markov memory ladder, [domain keywords]
