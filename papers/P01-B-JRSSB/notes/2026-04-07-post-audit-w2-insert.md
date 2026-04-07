# Post-Audit W2 Battery Insert

Suggested placement: Section 4, after the Markov ladder results subsection and before the survey-design decomposition discussion.

Source artifacts:
- `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json`
- `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json`

Run settings:
- Wasserstein order: `W_2`
- Permutations: `100`
- Landmarks: `2000`
- Seed: `42`

Draft-ready table:

| Null type | USoc H0 p | USoc H1 p | BHPS H0 p | BHPS H1 p |
| --- | ---: | ---: | ---: | ---: |
| label shuffle | 0.452 | 0.538 | 0.036 | 0.330 |
| cohort shuffle | 0.458 | 0.604 | 0.034 | 0.266 |
| order shuffle | <0.001 | 0.906 | <0.001 | 0.070 |
| Markov-1 | 0.070 | 0.226 | <0.001 | 0.002 |
| Markov-2 | 0.546 | 0.078 | 0.084 | 0.010 |

Suggested caption: Diagram-level post-audit `W_2` null battery for the USoc integration checkpoint and the BHPS checkpoint. Reported values are permutation p-values for full-diagram comparisons in `H0` and `H1`.

Draft-ready paragraph:

Table X reports the post-audit diagram-level `W_2` null battery for the two archived trajectory checkpoints. In the USoc integration checkpoint, assignment-preserving perturbations do not reject at the diagram level: both label-shuffle and cohort-shuffle remain non-significant in `H0` and `H1`, while destroying within-trajectory order produces a decisive `H0` rejection (`p < 0.001`) without corresponding `H1` evidence. The Markov ladder is also weaker in this shorter-window sample: Markov-1 is not significant at conventional levels and Markov-2 is clearly non-significant in `H0`, with only borderline `H1` evidence. The BHPS checkpoint is sharper. Order-shuffle again rejects strongly in `H0`, Markov-1 rejects in both `H0` and `H1`, and Markov-2 remains non-significant in `H0` but significant in `H1`. The main caution is that BHPS label-shuffle and cohort-shuffle also produce small `H0` p-values, so they should not be written up as generic negative controls in the same way as the USoc results. Instead, the older panel appears more topologically sensitive even under assignment-preserving perturbations, which is itself part of the methodological signal that the null hierarchy needs to separate.