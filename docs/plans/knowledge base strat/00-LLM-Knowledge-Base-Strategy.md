# LLM Knowledge Base Strategy for Counting Lives & TDA Research

**Date:** 2026-04-05
**Sources:** Karpathy's LLM Knowledge Base architecture; Forsythe's 10 Claude Code Principles
**Purpose:** Map evidence-based practices onto the existing two-vault, two-Cowork-project research setup

---

## Current Architecture

```
Counting Lives vault (Obsidian)          TDA-Research vault (Obsidian)
├── 01 - Manuscript/                     ├── 01-Literature/
│   └── [Part]/[Ch]/                     │   └── Perplexity-Captures/
│       ├── ChXX - Title.md              ├── 02-Notes/
│       ├── Index.md  ← Longform         │   └── Permanent/
│       ├── sections/                    ├── 03-Papers/
│       └── notes/                       │   └── [paper-id]/
├── 02 - Sources/                        │       ├── _project.md
│   └── literature-notes/                │       └── _outline.md
├── 03 - Research/                       ├── 04-Methods/
├── 05 - AI Sessions/                    │   ├── Computational-Log.md
└── 07 - Templates/                      │   ├── Pipeline-Overview.md
                                         │   └── Datasets/
                                         ├── 05-Daily/
                                         └── MOCs/

Skills (Cowork/claude.ai)               Code Repository
├── chapter-session                      C:\Projects\TDL\
├── counting-lives-humanizer             ├── papers/P01-P10/
├── perplexity-capture                   ├── core/
├── tda-session                          ├── data/
├── tda-perplexity-capture               └── notebooks/
└── tda-repo-bridge

Website: zktheory.org (Astro 5.x, React 19, Tailwind 4, MDX)
└── PRD v1.1 speccing learning paths, Two Lenses UI, Zotero integration
```

---

## Gap Analysis: What Karpathy's Architecture Adds

### What's already in place

| Karpathy element | Your equivalent | Status |
|---|---|---|
| `raw/` directory for ingestion | Perplexity captures, Zotero imports, Obsidian Web Clipper | ✅ Working |
| Compiled wiki with backlinks | Both Obsidian vaults with structured notes | ✅ Working |
| LLM as compiler/librarian | Custom skills (session openers, captures, repo bridge) | ✅ Working |
| Incremental compilation | Perplexity capture → verify → Zotero → lit note → prose | ✅ Working |
| Domain-specific structure | Paper pipeline (P01–P10), chapter structure (Ch00–Ch18) | ✅ Working |

### What's missing or underused

| Karpathy element | Gap | Priority |
|---|---|---|
| Auto-maintained INDEX.md | Longform-generated indexes exist but aren't refreshed by LLM | 🔴 High |
| Health check / linting passes | No systematic scan for orphans, stale items, cross-vault links | 🔴 High |
| Filing outputs back into wiki | Conversation synthesis stays in chat history, not vaults | 🔴 High |
| Ephemeral mini-knowledge-bases | No mechanism to spawn focused research contexts from vault subsets | 🟡 Medium |
| Custom search over wiki | No CLI or search tool beyond Obsidian's built-in search | 🟡 Medium |

---

## Gap Analysis: What the 10 Principles Add

| Principle | Current state | Recommendation | Priority |
|---|---|---|---|
| 1. Hardening | Skills mix deterministic + fuzzy steps | Extract deterministic vault operations into scripts | 🟡 Medium |
| 2. Context Hygiene | Skills are moderate length (5–7 steps) | Good — but watch for growth past ~19 requirements | 🟢 OK |
| 3. Living Documentation | No freshness checks on vault docs | Add to health check skill | 🔴 High |
| 4. Disposable Blueprint | PRD exists but no per-feature implementation plans | Adopt for website build; template provided | 🟡 Medium |
| 5. Institutional Memory | No CONVENTIONS.md or always/never lists | Create for both vaults | 🔴 High |
| 6. Specialist Review | Single generalist review in conversations | Define specialist review personas | 🟡 Medium |
| 7. Observability | Session logs exist but are optional | Make session capture default, not opt-in | 🔴 High |
| 8. Strategic Human Gates | Perplexity verification is a gate; others informal | Formalise gates at paper draft and website deploy | 🟡 Medium |
| 9. Token Economy | Not currently tracked | Consider for heavy multi-step workflows | 🟢 Low |
| 10. Toolkit | Skills exist but no meta-maintenance | Health check skill covers this | 🔴 High |

---

## Implementation Plan

### Phase 1: Immediately Useful (This Session)

**1.1 Session Capture Skill** → `session-capture/SKILL.md`
- Invoked at end of any substantive conversation
- Extracts decisions, formulations, open questions
- Files into appropriate vault location
- Closes the "conversation output → vault" loop

**1.2 Index Regeneration Amendments** → patches to `tda-session` and `chapter-session`
- Add a Step 0 that reads and refreshes INDEX.md
- Add a closing step that regenerates INDEX.md after work
- Leverages existing Longform-generated indexes as the starting point

**1.3 CONVENTIONS.md for TDA-Research** → `CONVENTIONS.md` at vault root
- Codifies methodological decisions from the Markov memory ladder work
- Always/never rules with reasons (the strongest prompting pattern per CHI 2023)
- Seeded from known decisions; designed for incremental growth

**1.4 CONVENTIONS.md for Counting Lives** → `CONVENTIONS.md` at vault root
- Codifies book register, citation practices, verification protocol
- Connects to the humanizer skill's anti-patterns

### Phase 2: Structural Improvements (Next Sessions)

**2.1 Vault Health Check Skill** → `vault-health-check/SKILL.md`
- Scans for orphan notes, stale TODOs, unverified captures
- Checks Zotero alignment
- Identifies cross-vault connection opportunities (Two Lenses seeding)
- Runs weekly or on-demand

**2.2 Specialist Review Personas** → `review-personas.md` reference file
- Brief (<50 token) specialist identities for TDA paper review
- Separate personas for: mathematical methodology, social policy claims,
  journal style, computational reproducibility
- Can be loaded by any skill that needs review

**2.3 Disposable Blueprint Template** → `implementation-blueprint.md` template
- For website feature implementation against the PRD
- Versioned plan → implement → discard code if needed → refine plan

### Phase 3: Advanced Integration (Future)

**3.1 Cross-Vault Linker** — identify concepts that appear in both vaults
and should have explicit connections (e.g., persistent homology methodology
in TDA vault ↔ mathematical tools discussion in Counting Lives Ch17)

**3.2 Ephemeral Research Contexts** — ability to extract a focused subset
of vault notes into a temporary context for deep Q&A on a specific topic
(the Lex Fridman "mini-knowledge-base" pattern)

**3.3 Website Content Pipeline** — vault INDEX.md files feed learning path
generation at Astro build time, similar to the Zotero integration already specced

**3.4 Synthetic Data / Fine-Tuning** — Karpathy's longer-term vision of
training a model on the compiled wiki. Premature now but worth noting as
the vaults grow past the ~400K word threshold where context-window approaches
start to strain.

---

## Principles Applied to Skill Design

When creating or modifying skills, apply these constraints:

1. **Keep each skill under 19 distinct requirements** (Context Hygiene)
2. **Use real job titles, not flattery, for any persona** (Specialist Review)
3. **Separate deterministic steps from fuzzy reasoning** (Hardening)
4. **Every skill that modifies the vault should update INDEX.md** (Living Documentation)
5. **Every skill should log what it changed** (Observability)
6. **Mistakes found during sessions → CONVENTIONS.md, not just corrections** (Institutional Memory)
7. **Plans go in files, not just conversation** (Disposable Blueprint)

---

## Files Produced

| File | Purpose | Install location |
|---|---|---|
| `session-capture/SKILL.md` | New skill: file conversation outputs back to vaults | Cowork skill |
| `vault-health-check/SKILL.md` | New skill: lint and audit both vaults | Cowork skill |
| `CONVENTIONS-TDA.md` | Always/never rules for TDA research | TDA vault root |
| `CONVENTIONS-CL.md` | Always/never rules for Counting Lives | CL vault root |
| `review-personas.md` | Specialist review identities | Shared reference |
| `implementation-blueprint-template.md` | Disposable blueprint for website features | Website project |
| `tda-session-amendments.md` | Patches to add index regeneration | Applied to existing skill |
| `chapter-session-amendments.md` | Patches to add index regeneration | Applied to existing skill |
