# /paper-draft — Start or Continue a Paper Draft

Create or update a paper draft following the programme structure.

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
