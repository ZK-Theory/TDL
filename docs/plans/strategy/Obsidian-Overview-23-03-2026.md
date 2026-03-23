This is a case where the setup decisions made now will save significant pain over a multi-year programme. Here is a recommended architecture that handles the separation concerns cleanly while keeping integration friction low.

## Core Architecture Decision: Two Separate Vaults

The strongest approach is **one Obsidian vault per research project**, not a single vault with project folders. The reasons are specific to your situation:

- Zotero Integration (the mgmeyers plugin) is configured *per-vault* — it points to a specific Zotero library or collection and uses a template from within that vault. Two vaults means two completely independent configurations with no risk of citation bleed [girlinbluemusic](https://girlinbluemusic.com/how-to-connect-zotero-and-obsidian-for-the-ultimate-phd-workflow/)
- Plugin settings, hotkeys, and CSS themes are vault-level — the TDA project may eventually want different tooling (e.g., heavier Dataview queries, code block rendering) than a book project
- Each vault can have its own Git repo, completely separate from your code repository

The downside — you cannot link notes *between* vaults — is not a real constraint here since the two projects are substantively independent.

## Zotero Library Separation

Zotero handles this natively. The cleanest approach is **two separate Zotero Group Libraries** (even if you are the only member of each group), because:

- Group libraries have completely independent sync settings — you can sync one to Zotero cloud and keep the other local-only if desired [youtube](https://www.youtube.com/watch?v=ScXGpZRZ7Ck)
- Better BibTex can auto-export a `.bib` file *per library*, with a stable export path, which each vault reads independently
- The Zotero Integration plugin in each Obsidian vault is then pointed at its own library — there is no possibility of the TDA Zotero notes appearing in the book vault

**Better BibTex setup per library:**
In Zotero → each library → Edit → Better BibTex → Auto-export → set the export path to `[VaultRoot]/00-Meta/references.bib` for each respective vault. Each vault then has its own self-updating `.bib` file.

## TDA Vault Structure

Given the 10-paper programme with distinct computational, methodological, and substantive components, a modified PARA structure works well:

```
TDA-Research-Vault/
│
├── 00-Meta/
│   ├── references.bib          ← Better BibTex auto-export lands here
│   ├── Templates/              ← Templater templates
│   │   ├── literature-note.md
│   │   ├── paper-project.md
│   │   └── meeting-log.md
│   └── MOC-Research-Programme.md  ← Master map of content
│
├── 01-Literature/
│   ├── TDA-Methods/
│   ├── Social-Stratification/
│   ├── Geometric-Deep-Learning/
│   └── Welfare-State-Comparative/
│
├── 02-Papers/                  ← One subfolder per paper project
│   ├── P01-Core-VR-PH/
│   │   ├── _project.md         ← Status, target journal, deadline
│   │   ├── drafts-log.md
│   │   └── reviewer-responses.md
│   ├── P02-Mapper/
│   ├── P03-Zigzag/
│   ├── P04-Multipers/
│   └── ...
│
├── 03-Methods-Pipeline/
│   ├── Markov-Memory-Ladder.md
│   ├── Embedding-Pipeline.md
│   ├── Computational-Notes.md  ← Benchmarks, RAM limits, timing logs
│   └── Datasets/
│       ├── USoc-Notes.md
│       ├── BHPS-Notes.md
│       └── SOEP-PSID-Access.md ← Data access status per country
│
├── 04-Ideas/
│   ├── Daily/                  ← Daily notes (auto-created by Templater)
│   └── Permanent/              ← Developed atomic notes
│
├── 05-Admin/
│   ├── Submissions-Tracker.md  ← Dataview-queryable submission log
│   ├── Conferences.md
│   └── Compute-Budget.md       ← Cloud credit tracking
│
└── 06-Assets/
    └── Figures/                ← Exported PD diagrams, Mapper graphs
```

The `_project.md` file in each Paper folder is the key futureproofing element. Use consistent YAML frontmatter so Dataview can query across all papers:

```yaml
---
paper: P02
title: "Mapper for Interior Trajectory Structure"
status: in-progress      # idea | in-progress | submitted | published
target-journal: "Sociological Methods & Research"
deadline: 2026-09-01
tags: [paper, mapper, tda]
---
```

This lets you maintain a live dashboard note with a Dataview query showing all paper statuses at a glance.

## VSCode and GitHub Integration

The key principle is **keep the vault repo and the code repo completely separate**. Do not put the Obsidian vault inside the code repository or vice versa.

```
~/Research/
├── tda-trajectories/           ← GitHub code repo (existing)
│   ├── src/
│   ├── data/
│   ├── notebooks/
│   └── .git/
│
└── tda-vault/                  ← Separate Git repo for the vault
    ├── 00-Meta/
    ├── 01-Literature/
    └── .git/                   ← Managed by Obsidian Git plugin
```

Cross-reference between vault and code repo using relative file links or noting the path explicitly in computational notes — VSCode's terminal and the vault's `03-Methods-Pipeline/` notes stay in sync by discipline rather than by tooling.

The **Obsidian Git** plugin handles vault version control automatically on a schedule (commit every 30 minutes, push on vault close). This gives you a full history of your thinking alongside the code history — useful when revisiting why a methodological decision was made months earlier. [drlakshan.substack](https://drlakshan.substack.com/p/using-obsidian-and-git-missing-link)

## Recommended Plugin Stack for This Vault

| Plugin | Purpose | Priority |
|---|---|---|
| **Zotero Integration** (mgmeyers) | Literature note import from Zotero | Essential |
| **Better BibTex** (Zotero-side) | Stable citekeys, auto `.bib` export | Essential |
| **Obsidian Git** | Vault version control | Essential |
| **Templater** | Consistent paper/literature note templates | Essential |
| **Dataview** | Live paper status dashboard, literature queries | High |
| **Pandoc Reference List** | Live bibliography while drafting in vault | High |
| **Excalidraw** | Research programme diagrams, manifold sketches | High |
| **Projects** | Kanban board for paper pipeline | Medium |
| **Canvas** (built-in) | Visual map of programme structure | Medium |
| **Longform** | Drafting paper sections directly in vault | Optional |

Avoid installing more than you actively use — Obsidian vaults degrade in startup speed with large community plugin stacks.

## Additional Tools Worth Considering

**Quarto** is the most significant addition to consider beyond Obsidian. It renders `.qmd` files (Markdown + Python/R code blocks + Zotero citations via `.bib`) directly to PDF, Word, or HTML — meaning you can draft paper sections in VSCode with live code execution and citation rendering, then export to submission format without a LaTeX build chain. It integrates naturally with the VSCode workflow you already use and reads the same `.bib` file that Better BibTex exports to your vault. For a computationally intensive programme producing 10 papers, this eliminates significant formatting overhead. [forum.obsidian](https://forum.obsidian.md/t/science-research-vault-a-structured-workflow-for-academics/95589)

**DVC (Data Version Control)** is worth adding to the code repository once you move into Stage 2 (cross-national data, multi-parameter persistence). It tracks large data files and model outputs in Git-compatible fashion without bloating the repo — particularly useful when USoc/BHPS data access agreements require you not to push raw data to GitHub.




Here is a complete, opinionated structure designed specifically for this research programme — not a generic academic template. It fuses PARA (action-oriented project tracking) with a lightweight Zettelkasten (idea-building) and is designed so every folder has a clear reason to exist. [forum.obsidian](https://forum.obsidian.md/t/share-on-applying-para-in-zettelkasten-system/98203)

## The Core Philosophy First

The most experienced Obsidian academics converge on a key insight: **folders organise processes, links organise ideas**. Resist the urge to mirror your topic structure in folders — that is what tags and links are for. Keep the folder count low and stable; let the graph grow organically. [forum.obsidian](https://forum.obsidian.md/t/provide-structure-how-do-you-use-zettelkasten-in-obsidian/35008)

For this programme you have two distinct workflows running simultaneously:
- **Production workflow** — moving papers from idea → draft → submitted → published
- **Knowledge workflow** — connecting methods, findings, and theory across papers

The structure below serves both without conflating them.

***

## Full Vault Structure

```
TDA-Research-Vault/
│
├── 🗂 00-Meta/
│   ├── Home.md                      ← Dashboard note (pinned)
│   ├── Programme-Map.md             ← Visual overview of all 10 papers
│   ├── references.bib               ← Better BibTex auto-export target
│   └── _Templates/
│       ├── tpl-literature-note.md
│       ├── tpl-paper-project.md
│       ├── tpl-meeting.md
│       ├── tpl-method-note.md
│       └── tpl-daily.md
│
├── 📚 01-Literature/
│   ├── _MOC-TDA-Methods.md          ← Map of content: all TDA method notes
│   ├── _MOC-Social-Stratification.md
│   ├── _MOC-Geometric-Deep-Learning.md
│   └── _MOC-Comparative-Welfare.md
│   (individual literature notes live here, flat — not in subfolders)
│
├── 🧠 02-Notes/
│   ├── Fleeting/                    ← Inbox: rough ideas, jotted thoughts
│   └── Permanent/                   ← Developed atomic notes
│
├── 📄 03-Papers/
│   ├── P01-VR-PH-Core/
│   ├── P02-Mapper/
│   ├── P03-Zigzag/
│   ├── P04-Multipers/
│   ├── P05-Cross-National/
│   ├── P06-Intergenerational/
│   ├── P07-Geometric-Forecasting/
│   ├── P08-GNN-Households/
│   ├── P09-CCNN-Multilevel/
│   └── P10-Topological-Fairness/
│
├── 🔬 04-Methods/
│   ├── Pipeline-Overview.md
│   ├── Computational-Log.md
│   └── Datasets/
│       ├── USoc.md
│       ├── BHPS.md
│       ├── SOEP.md
│       ├── PSID.md
│       └── Access-Status.md
│
├── 📅 05-Daily/
│   └── (auto-created dated notes)
│
└── 🗃 06-Archive/
    └── (completed papers, old drafts, superseded notes)
```

***

## Key Files in Detail

### `00-Meta/Home.md` — The Dashboard

This is the only note you open every day. It uses Dataview to pull live status from every paper project automatically, so you never manually maintain a tracker:

````markdown
# TDA Research Programme

## 📊 Paper Pipeline
```dataview
TABLE status, target-journal, deadline
FROM "03-Papers"
WHERE file.name = "_project"
SORT status ASC
```

## 📝 Recent Notes
```dataview
LIST FROM "02-Notes/Permanent"
SORT file.mtime DESC
LIMIT 8
```

## 📅 This Week
```dataview
TASK FROM "05-Daily"
WHERE !completed
SORT file.day DESC
LIMIT 20
```
````

***

### `03-Papers/P01-VR-PH-Core/` — A Paper Folder in Full

Each paper folder has a consistent internal structure:

```
P01-VR-PH-Core/
├── _project.md          ← Status, journal, deadlines (Dataview source)
├── _outline.md          ← Current argument structure
├── _reviewer-log.md     ← Reviewer comments & responses
├── drafts/
│   ├── v1-2025-01.md
│   └── v4-2026-03.md    ← Or link to external Quarto/LaTeX file
├── figures/
│   └── (PD diagrams, Mapper graphs as PNGs)
└── notes/
    └── (paper-specific scratch notes that haven't become permanent)
```

The `_project.md` frontmatter is the key — consistent YAML that the Home dashboard queries:

```yaml
---
paper: P01
title: "Persistent Homology of UK Socioeconomic Trajectories"
status: under-review
target-journal: Sociological Methodology
submitted: 2026-04-15
deadline: null
priority: high
tags: [paper, tda, markov-ladder, core]
---
```

**Status vocabulary** (keep it to 5 values for clean Dataview filtering):
`idea` → `in-progress` → `submitted` → `under-review` → `published`

***

### `01-Literature/` — Flat with MOCs, Not Subfolders

Literature notes all live in one flat folder. This is counterintuitive but correct — a paper on zigzag persistence that is also relevant to business cycles should not have to live in one subdirectory or the other. Instead, it links to both `_MOC-TDA-Methods.md` and whatever paper project needs it. The MOCs serve as the navigation layer. [emilevankrieken](https://www.emilevankrieken.com/blog/2025/academic-obsidian/)

A literature note created via Zotero Integration looks like:

```yaml
---
citekey: carlsson2009topology
authors: Carlsson, Gunnar
year: 2009
journal: Bulletin of the AMS
tags: [literature, tda, persistent-homology, foundational]
related-papers: [P01, P03]
---

## Summary
<!-- 3–5 sentence summary in your own words -->

## Key Claims
-

## Methods Relevance
<!-- How does this connect to the pipeline? -->

## Connections
<!-- [[note-title]], [[note-title]] -->
```

The `related-papers` field lets you run a Dataview query inside any `_project.md` to pull all literature relevant to that paper automatically.

***

### `02-Notes/` — The Thinking Layer

This is the Zettelkasten component. **Fleeting** notes are rough captures — anything worth remembering from a computation run, a paper, or a shower thought. **Permanent** notes are atomic, rewritten in your own words, heavily linked.

A permanent note has a title that makes a *claim*, not a label:

- ❌ `Markov-chain-nulls.md`
- ✅ `Over-constraint-below-Markov-means-absorbing-states-not-cycles.md`

This distinction matters because when you write Paper 5 (cross-national comparison) a year from now, a note titled with a claim surfaces immediately as relevant; a topic label does not.

***

### `04-Methods/Computational-Log.md`

This note is under-rated and often omitted. For a computationally intensive programme it is essential — a running record of benchmark results, RAM usage, timing, and parameter choices that explains *why* the pipeline is configured the way it is. Six months from now you will not remember why `L=5000` landmarks was chosen over `L=8000`:

```markdown
## 2026-03-18 — Ripser L=5000 benchmark
- Hardware: i7, 32GB RAM, no GPU
- Runtime: 158s for primary USoc sample
- L=8000 test: 347s, qualitatively identical p-values
- Decision: L=5000 retained (Section 3.3)

## 2026-04-02 — Multipers first run
- Library: multipers 0.x, gudhi backend
- Input: PCA-20D, 3000 landmarks, income as second parameter
- RAM peak: 18.4GB
- Runtime: 42 min
- Notes: Full L=5000 bifiltration estimated ~28GB → cloud run needed
```

***

## Tags vs Folders vs Links

The three organising tools serve distinct purposes in this vault: [forum.obsidian](https://forum.obsidian.md/t/provide-structure-how-do-you-use-zettelkasten-in-obsidian/35008)

| Tool | Use for | Example |
|---|---|---|
| **Folders** | Note *type* (literature, paper, method, daily) | `03-Papers/P02-Mapper/` |
| **Tags** | Cross-cutting *attributes* | `#tda`, `#submitted`, `#computational-heavy` |
| **Links** | Conceptual *relationships* | `[[Markov-memory-ladder]]` → `[[absorbing-states]]` |

Avoid duplicating the folder hierarchy in tags — `#tda/mapper` adds no information if the note already lives in `03-Papers/P02-Mapper/`.

***

## The Minimum Viable Setup

If the full structure feels like too much upfront, the three things that matter most are: [forum.obsidian](https://forum.obsidian.md/t/how-do-you-organize-academic-work-in-obsidian-heres-my-approach-after-4-years/100587)

1. The `_project.md` file with consistent frontmatter in each paper folder — this is what enables the dashboard and makes the vault queryable
2. The flat literature folder with MOC files — this prevents the "where does this paper go?" paralysis that stalls most academic vaults
3. The `Computational-Log.md` — this has no substitute and cannot be reconstructed retroactively

Everything else can be added incrementally as the programme grows.