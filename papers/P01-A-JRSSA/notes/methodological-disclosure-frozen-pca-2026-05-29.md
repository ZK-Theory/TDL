# Methodological Disclosure: Frozen PCA Markov Null Audit

Date: 2026-05-29

The Stage-1 audit separated two implementation details: the p-value denominator used in the reporting path and the scaler/PCA loadings used when embedding Markov-null trajectories. Preserved null-diagram caches were re-evaluated under the intended Monte Carlo rule, `(r+1)/(B+1)`, and the affected Stage-1 analyses were rerun with Markov-null embeddings projected through the observed scaler/PCA basis. The fresh frozen-loadings comparison indicates that the T1.2h prose direction requires revision because some comparison cells no longer reject at alpha 0.05, while the stratified Markov-1 analysis continues to support T1.3 Outcome A.
