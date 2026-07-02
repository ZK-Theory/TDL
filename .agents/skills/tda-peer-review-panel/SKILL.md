---
name: tda-peer-review-panel
description: Use when reviewing a paper section, methods description, abstract, introduction, pre-registration text, computational-log entry, result interpretation, or response-to-reviewer — to run separate specialist review passes instead of one generalist read.
---

# TDA Peer Review Panel

Structured multi-persona review of research prose and claims. **Review and
repair stay separate**: reviewers find, cite, and rank; fixing happens in a
later pass, never mid-review. Not for design/spec documents
(`adversarial-design-review`) and not a substitute for the statistical lane
audits — the Statistical persona *runs* them.

## Personas

- **Methodology** — TDA and method validity: embedding choices, filtration,
  metric choices, null design, benchmark grounding.
- **Statistical** — inference and reporting; runs
  `tda-statistical-analysis-review` as its checklist.
- **Empirical** — social-science plausibility of applied findings, data
  limitations, BHPS/USoc coding pitfalls, panel-attrition caveats.
- **Reproducibility** — could a stranger regenerate this from the committed
  artifacts; `reproducibility-package-review` is the deep pass.
- **Prose** — clarity, structure, journal register; `humanizer` for the
  AI-tell pass at draft completion.

## Default Routing

| Target | Personas |
|---|---|
| P01-A applied findings | Methodology, Empirical, Reproducibility or Prose |
| P01-B methods | Methodology, Statistical, Reproducibility |
| P04 multiparameter | Methodology, Statistical, Reproducibility |
| Website / cross-project text | Prose, Methodology (as communication) |

## Procedure

1. Identify the paper, section, and intended venue; gather the result
   artifacts the text depends on.
2. Select 2–3 personas. Run each **separately** — a combined generalist
   review is not a substitute for specialist passes.
3. Every finding cites a specific passage or claim — no finding without a
   location.
4. Rank findings: blocking / major / minor / style.
5. Cross-reference overlapping concerns across personas — convergence is
   signal.
6. Convert findings into a fix queue with required evidence per item. Do not
   rewrite during the review pass.
7. Paper-boundary check is always on: applied P01-A content must not leak
   into P01-B methods sections and vice versa (P01-B §4 strict scope rule);
   sources cited must have passed `tda-literature-verification`.

## Completion Checklist

- [ ] Paper, section, and venue identified.
- [ ] 2–3 personas selected and run separately.
- [ ] Every finding located to a passage or claim.
- [ ] Findings ranked by severity; overlaps identified.
- [ ] Required evidence listed per finding.
- [ ] Fix queue created; no rewriting performed in-pass.
- [ ] Paper-boundary and citation-verification checks run.

## Escalate Or Stop When

- A finding invalidates a headline result — route to
  `tda-diagnosing-computational-defects` and the lane audits before any
  prose fix.
- A blocking finding requires a methodological judgement call — surface as a
  User decision with the options laid out.

## Related Skills

`adversarial-design-review` (design docs, not prose) ·
`tda-statistical-analysis-review` · `notation-check` · `humanizer` ·
`paper-claim-trace` · `reproducibility-package-review` ·
`tda-literature-verification` · `tda-visualisation-and-diagramming`
(figure classes and caption-claim checks for reviewed figures).
