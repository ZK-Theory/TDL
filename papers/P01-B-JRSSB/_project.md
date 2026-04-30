---
paper: P01-B
title: "Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data"
status: in-progress
target-journal: "Journal of the Royal Statistical Society Series B"
submitted: null
deadline: null
priority: high
stage: 0
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, hypothesis-testing, wasserstein, zigzag, jrss-b]
---

## Status

Phase 0 scaffolding created for the JRSS-B methodology paper. This paper
combines the Markov memory ladder and diagram-level testing material from
`papers/P01-VR-PH-Core/` with the survey-design diagnostic toolkit from
`papers/P03-Zigzag/`.

Authorship fixed by programme convention: single author Stephen Dorman
(The Open University, UK).

Planned submission strategy: simultaneous JRSS-B submission, JRSS-A companion
submission, and same-day arXiv posting (`stat.ME`).

Post-audit W2 insert and repo extraction note prepared in
`papers/P01-B-JRSSB/notes/2026-04-07-post-audit-w2-insert.md` and
`papers/P01-B-JRSSB/notes/2026-04-07-post-audit-w2-repo-note.md`.

## Target

Primary: *Journal of the Royal Statistical Society Series B*

## Source Papers

- `papers/P01-VR-PH-Core/` — null hierarchy, scalar vs diagram-level testing,
  UK application results
- `papers/P03-Zigzag/` — survey-design diagnostics, pool-draw nulls,
  spanning-individual decomposition

## Open Items

- [x] Formalise the spanning-individual decomposition and pool-draw null model — completed 2026-04-30; see `papers/P01-B-JRSSB/notes/formalised-survey-toolkit.md`
- [x] Insert the post-audit W2 table and paragraph from `notes/2026-04-07-post-audit-w2-insert.md` into Section 4 of the first full draft — folded into §4.2.1–4.2.3 of v1
- [x] Update the draft text to reflect the resolved W2 audit and replay caveat — addressed in §4.2.1 of v1
- [x] Assemble v1 from P01 v8 and P03 v2+ — completed 2026-04-30; draft at `papers/P01-B-JRSSB/drafts/v1-2026-04.md`, ~9,100 words
- [ ] Keep zigzag exposition brief and explicitly subordinate to the testing framework
- [ ] Use `notes/2026-04-07-post-audit-w2-repo-note.md` when building the standalone paper repo so the `post_audit` W2 JSONs are treated as authoritative artifacts
- [ ] Prepare JRSS-B submission package and arXiv metadata
