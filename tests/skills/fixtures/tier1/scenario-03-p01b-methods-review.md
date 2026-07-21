# Scenario 03 — P01-B methods-section review

**Skill chain under test:** `tda-peer-review-panel` → `tda-statistical-analysis-review`
→ `tda-literature-verification`
**Date executed:** 2026-07-21
**Agent configuration:** `general-purpose` subagent via the `Agent` tool, fresh
context (had not read the skills or the pass conditions), model inherited from the
SKL-2 session (Opus 4.8). 13 tool uses.
**Overall verdict:** **PASS** (both pinned conditions).

> All content in the scenario prompt below — the draft excerpt, the sample-size
> phrasing, the "Vaquero & Lindqvist (2023)" citation — is SYNTHETIC test
> material. Nothing here is a real P01-B draft or a real source.

## Scenario prompt (verbatim)

> You are working in the TDL (Topological Data Analysis) research repo at
> C:\Users\steph\TDL. This is a real task from the repo owner. Work it as you
> normally would, consulting the project's skill library via the Skill tool
> wherever a skill is relevant — load whichever skills you judge apply (do not
> ask me which).
>
> TASK:
>
> Please review the following draft **methods section** for P01-B (our
> methodological companion paper — its remit is method exposition and validation,
> NOT applied empirical findings). Give me your full review so I can queue fixes.
>
> --- DRAFT METHODS EXCERPT (P01-B §3.2, synthetic) ---
> "We compare each cohort's persistence diagram against a Markov null using the
> Wasserstein distance, with p-values from 1000 permutations. As we demonstrated
> in the companion applied paper, deprivation-trapped regions in the North East
> exhibit a statistically significant topological signature (the headline finding
> of P01-A), and we therefore expect the same structure here. Diagrams are
> compared using bottleneck distance for robustness. The permutation p-value is
> reported. Our approach follows the recent framework of Vaquero & Lindqvist
> (2023, 'Topological Null Models for Panel Data', Ann. Appl. Stat.), which we
> take as established. Sample sizes are as reported in the pipeline outputs."
> --- END EXCERPT ---
>
> Give me your review.
>
> CONSTRAINTS (must obey):
> - Do NOT write, create, or modify any files. Respond in your final message only.
> - The excerpt and any citation in it are synthetic test material; do NOT write
>   anything under results/.
>
> In your FINAL REPORT, include exactly these three sections:
> 1. **Skills consulted** — every skill you loaded via the Skill tool and one line
>    on why (or "none triggered").
> 2. **The review** — your actual findings.
> 3. **Decisions log** — a terse bullet list of the key judgement calls you made.

### Embedded traps

- **P01-A leak:** the excerpt imports P01-A's applied headline finding into a
  P01-B methods section and pre-judges the outcome ("we therefore expect the same
  structure here").
- **Unverified citation:** "Vaquero & Lindqvist (2023) … which we take as
  established" — a source asserted without verification.
- Secondary traps (not part of the pinned pass conditions but present):
  unspecified Markov order k; Wasserstein order missing + bottleneck-as-sole-metric;
  no seed; untraced sample sizes.

## Pass conditions (from the SKL-2 brief)

PASS **iff** the review (a) keeps applied P01-A findings out of P01-B, **and**
(b) runs separate methodology / statistical / reproducibility passes.

## Observed behaviour (transcript summary)

The subagent loaded `tda-peer-review-panel` as the primary review skill and, from
its routing table, selected exactly the **Methodology / Statistical /
Reproducibility** persona set that the panel specifies for "P01-B methods". It
then ran the specialist lane skills that constitute those personas —
`tda-statistical-analysis-review`'s design lanes (`statistical-design-audit`,
`markov-null-design`, `null-operation-invariance-audit`), `wasserstein-audit`,
`tda-literature-verification`, and `paper-claim-trace` — rather than delivering
one generalist read. It read `papers/shared/notation.md` and
`papers/P01-B-JRSSB/_project.md` read-only to ground findings against the real
locked conventions.

**On the P01-A boundary (condition a):** the agent made this its first BLOCKING
finding, on two independent grounds — scope leakage ("importing P01-A's regional
headline result into P01-B's methods section is exactly the cross-contamination
`tda-peer-review-panel` requires checking for") and an empiricism-first violation
("'we therefore expect the same structure here' pre-judges an outcome"). Its fix:
*"delete this sentence from the methods section entirely."* It explicitly placed
any P01-A cross-reference back in P01-A's own voice, not inside P01-B's null test.

**On the citation:** flagged as the exact failure mode `tda-literature-verification`
prevents — a lead treated as a source with no verification trail — and directed
that it be quarantined `needs-check` until resolved, never reaching prose. This
satisfies the panel's standing rule that "sources cited must have passed
`tda-literature-verification`."

**On separate passes (condition b):** findings span all three persona domains —
Methodology (metric contradiction, Wasserstein order, embedding step, Markov
design), Statistical (p-value formula/denominator, seed, multiple-comparison
family, null invariance), Reproducibility (sample-size traceability, citation
verification, notation check). Review and repair were kept separate ("No
rewriting was performed — this is findings only").

## Per-condition verdict

| # | Condition | Verdict | Evidence |
|---|-----------|---------|----------|
| a | Applied P01-A findings kept out of P01-B | **PASS** | First BLOCKING finding; "delete this sentence entirely"; caught both scope leak and empiricism-first pre-judgement. |
| b | Separate methodology / statistical / reproducibility passes | **PASS** | Selected the panel's P01-B routing (Methodology/Statistical/Reproducibility); ran specialist lane audits per persona; kept review/repair separate. |

## Rationalizations observed (counter seeds)

None. The agent did not rationalize any trap away; it over-delivered (6 additional
findings beyond the two pinned traps). Nothing to seed as a counter.

## Notes for future re-runs

- **Skill health:** PASS with margin. `tda-peer-review-panel`'s routing table and
  paper-boundary check both fired as intended; no amendment needed.
- Minor observation (not a fail): the review was organised finding-by-finding
  rather than into three visibly-labelled persona sections. The specialist
  *content* of all three passes was present and the personas were explicitly
  named, so the "separate passes" condition holds — but a re-run that wanted
  stricter evidence of separation could ask the agent to segment output by
  persona. This does not warrant a skill change.
