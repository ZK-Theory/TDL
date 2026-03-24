---
mode: ask
description: Remove AI writing tells from academic paper drafts (TDA/social science)
---

# Academic Paper Humanizer

Remove AI writing tells from the attached or pasted text. This prompt is calibrated for TDA and quantitative social science papers.

## Instructions

1. Read the full text.
2. Identify AI tells from the pattern list below. Report as brief bullets ("What makes this obviously AI-generated?").
3. Rewrite the text with all identified patterns removed. Present the revised version.

---

## Patterns to remove

### General AI tells

- **Significance inflation**: "groundbreaking", "novel contribution", "transformative" → use specific bounded claims
- **Hedge-stacking**: "may potentially suggest" → keep one hedge per claim
- **Formulaic openers**: "In today's rapidly evolving landscape", "In recent years" → delete; start with the finding
- **Em dash overuse**: >2 em dashes per paragraph
- **Filler transitions**: "It is worth noting that", "It is important to emphasise", "We note that" → delete
- **Rule of three reflex**: First/Second/Third as structural scaffolding → merge or restructure
- **Passive evasion**: "It was found that" → rewrite with active subject
- **Copula + vague**: "This is consistent with", "This is in line with" → use causal/directional phrasing
- **Superficial -ing clauses**: "...indicating that X", "...confirming that Z" at sentence end → cut or promote to own sentence
- **Conclusion mirrors abstract**: Conclusion should interpret or project forward, not restate

### Academic-specific tells

- **Contribution inflation**: "This paper makes three novel contributions" → what you actually did, in one sentence
- **"The remainder of the paper is organised as follows"** → delete or compress to one clause
- **Formulaic abstract**: Background/Gap/Method/Results/Implications as five equal sentences → lead with the finding
- **Robustness boilerplate**: "Results are robust to alternative specifications" → say what varied and by how much
- **Literature padding**: citation cluster + one generic sentence → make a specific claim or synthesise in one sentence
- **Performative acknowledgment**: "We acknowledge that our analysis has limitations" → name the limitation and state its implication
- **Numbered-contribution template**: "First we contribute X, second Y, third Z" → rewrite as prose building from one idea to the next
- **Forward-reference filler**: "As we show below", "As discussed in §X" when within 3 paragraphs → just say it

### TDA-specific signals

- Do not say "topological features were detected" — say which features, at what persistence
- Do not say "the null was rejected" without specifying the test statistic (total persistence vs. Wasserstein)
- H₁ non-significance is a result, not a failure — frame it as bounding cyclical complexity
- Results tables should be cited by number; do not re-narrate them in full in prose
