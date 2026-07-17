<!--
Target location in v2: §4.2, appended to the H₁ persistence paragraph
(v1-2026-04.md line 102 — "Loops are numerous but not deeply persistent…").

Evidence sources verified during drafting:
  • v1 §4.2 H₁ paragraph quoting 5,962 features and maximum H₁ persistence
    3.21 against maximum H₀ 15.81 (v1-2026-04.md line 102).
  • `papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md`
    Reviewer 1 issue R1-10.5 — short-bar H₁ features in high-dimensional
    Vietoris-Rips complexes can be sampling and projection artefacts.

Cross-references to §4.3 (Markov-memory ladder p-values) and §6.2 (BHPS
length-matched comparison) are stated only by section number. The actual
H₁ result wording in those sections is gated and not authored in this Task.
-->

## §4.2 H₁ caveat addendum

Append the following two sentences immediately after the v1 §4.2 H₁
paragraph (which ends "…roughly a fifth of maximum H₀ (15.81)."):

> In 20-dimensional Vietoris–Rips complexes built on maxmin landmark subsets,
> low-persistence $H_1$ features can arise from sampling fluctuations of the
> landmark set and from the loss of metric exactness under PCA projection from
> the full $90$-dimensional unigram-bigram feature space (cf. Bauer 2021;
> Reviewer 1, Issue 9). The substantive $H_1$ analysis is therefore the
> null-comparison reported in §4.3 — which evaluates whether the observed $H_1$
> diagram is more distant from null diagrams than null diagrams are from each
> other — and the BHPS length-matched comparison in §6.2.

## Note for v2 assembly

The section references "§4.3" and "§6.2" mirror the v1 numbering and should
be left as written unless the v2 outline renumbers either section. The text
makes no claim about the *outcome* of those analyses, only their location;
both result paragraphs are gated and authored separately.
