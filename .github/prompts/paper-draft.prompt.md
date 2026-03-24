---
mode: agent
description: Start or continue a paper draft for the TDA research programme
---

# Paper Draft Agent

Start or update a paper draft following the programme's structure conventions.

## Pre-flight (always do first)

1. Read `papers/PXX/_project.md` — status, current draft path, open items.
2. Read the current draft at `papers/PXX/drafts/vN-YYYY-MM.md`.
3. Check `docs/plans/strategy/Meta-Research-Plan-23-03-2026.md` for the paper's planned framing.
4. Check `results/` for computation outputs to integrate.

## Output

Write new draft to: `papers/PXX/drafts/vN+1-YYYY-MM.md`
- Increment version number.
- Date = current month (YYYY-MM).
- Never overwrite an existing draft.

After writing:
- Update `_project.md` current draft path and open items.
- Note any remaining open items.

## Paper structure (trajectory TDA papers)

1. Abstract — lead with the finding (not background)
2. Introduction — motivation → gap → specific contribution → roadmap in ≤1 sentence
3. Literature — OM/sequence analysis | TDA foundations | domain background
4. Data and Methods — data sources → embedding → PH → null models (Markov memory ladder)
5. Results — descriptive → topological → null validation → regimes → stratification → validation
6. Discussion — TDA vs baseline, key finding interpretation, limitations with implications
7. Conclusion — new interpretive work; not a summary of the abstract
8. References

## After completing a draft

Run the paper-humanizer prompt on the final draft before marking it ready for submission review.
