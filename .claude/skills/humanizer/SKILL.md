# /humanizer — Academic Writing Anti-AI Pass

Remove AI writing tells from academic paper drafts. Optimised for TDA/social science papers in this research programme.

## Usage

```
/humanizer [file or pasted text]
```

Run on a draft before submission review. Attach the draft file or paste the section.

---

## Process

1. **Read** the draft in full.
2. **Audit** — identify AI tells from the patterns below. Report as brief bullets: "What makes this obviously AI-generated?"
3. **Revise** — fix all identified patterns. Present the revised version.

---

## General AI Patterns to Remove

**1. Significance inflation**
- "groundbreaking", "revolutionary", "transformative", "novel contribution"
- Replace with specific, bounded claims.

**2. Hedge-stacking**
- "may potentially suggest", "could possibly indicate", "seems to appear"
- Keep one hedge per claim, not three.

**3. Formulaic openers**
- "In today's rapidly evolving landscape...", "In recent years..."
- Delete or start with the actual finding.

**4. Em dash overuse**
- More than 1–2 em dashes per paragraph is a tell.

**5. Filler transitions**
- "It is worth noting that", "It is important to emphasise", "We note that"
- Delete and make the point directly.

**6. Rule of three**
- "First... Second... Third..." as a structural reflex.
- Merge or restructure when the tripartite division adds no content.

**7. Passive evasion**
- "It was found that", "It can be seen that"
- Rewrite with an active subject.

**8. Copula + vague**
- "This is consistent with", "This is in line with"
- Replace with causal/directional phrasing.

**9. Superficial -ing clauses**
- "...indicating that X", "...suggesting that Y", "...confirming that Z" as sentence-ending padding.
- Promote the -ing clause to its own sentence or cut it.

**10. Conclusion mirrors abstract**
- Conclusion restates abstract point-for-point.
- Conclusion should do new work: interpret, project forward, or name what surprised you.

---

## Academic-Specific Patterns to Remove

**A1. Contribution inflation**
- "This paper makes three novel contributions to the literature."
- Replace with: what you actually did, in one direct sentence.

**A2. "The remainder of the paper is organised as follows"**
- Delete entirely, or compress to one clause if a roadmap is needed.

**A3. Formulaic abstract structure**
- Background → Gap → Method → Results → Implications as five equal-length sentences.
- Lead with the finding, not the context.

**A4. Robustness boilerplate**
- "Results are robust to alternative specifications (see Appendix X)."
- If results are robust, say what varied and by how much. If they are not, say that.

**A5. Literature padding**
- Rapid-fire citation clusters with one generic sentence per citation.
- Either make a specific claim about each cited work or group them with a single synthesis sentence.

**A6. Method ventriloquism**
- "The data suggest...", "The analysis reveals..."
- Data do not suggest — you found, or you interpret.

**A7. Performative acknowledgment**
- "We acknowledge that our analysis has limitations."
- Name the limitation specifically and say what it implies for the findings.

**A8. Significance hedging at conclusions**
- "While these findings are preliminary, they may have implications for..."
- If the implications are real, state them. If they are not, cut them.

**A9. Numbered-contribution template**
- "First, we contribute X. Second, we contribute Y. Third, we contribute Z."
- Rewrite as prose that builds from one idea to the next.

**A10. Forward-reference filler**
- "As we show below", "As discussed in §2.3", "As noted earlier"
- When the reference is within 3 paragraphs, just say it. Delete otherwise.

---

## TDA-Specific Signals

- Do not say "topological features were detected" — say which features, at what persistence.
- Do not say "the Markov null was rejected" without specifying which test statistic.
- Results tables should be cited by number, not re-narrated in full in prose.
- H₁ non-significance is a result, not a failure — frame it as bounding the complexity of cyclical dynamics.
