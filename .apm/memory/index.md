---
title: P01-A and P01-B Reviewer-Response Revision to v2
---

# APM Memory Index

## Memory Notes

- **P01-A §6.1/§6.2 stratified prose (T2.7) is UNBLOCKED with a mandatory power caveat.** T1.28's per-subgroup Markov-1 W₂ + BH-FDR gave USoc 12/12 reject, BHPS 9/11. The §6.1 outcome-contingency was checked + locked ([DECISION], Computational-Log 2026-07-09): v1 §6.1's heterogeneity claims are all USoc-based → USoc 12/12 ⇒ no claim overturned. The only two non-rejections are the two smallest BHPS strata (`nssec/Professional-Managerial` n=335; `cohort/1980s` n=223), pre-registered underpowered — v2 must report them with an explicit power caveat, never as evidence against heterogeneity. Combined-23-subgroup-table vs §6.1-USoc/§6.2-BHPS structure is a T2.7 prose choice under per-section User review.
- **T1.20 BHPS regression may have consumed parental NS-SEC = all-NaN before the T1.28 extractor fix — audit open.** `covariate_extractor.py` hardcoded BHPS parental NS-SEC to NaN until T1.28's `[DATA]` fix (`ba_panssec8_dv` pa-fillna-ma, 89.7% coverage). Any *earlier* committed BHPS analysis that read parental class (T1.20 tier regression the likely candidate) may have run with that column empty. The GitNexus impact-flag requested in the T1.28 follow-up was not explicitly closed, and the GitNexus MCP is now disconnected → run this as a separate audit. Committed result JSONs are frozen (not retroactively changed); the question is whether a paper claim rests on an affected number.
- **All citable Stage-1 headline numbers are the frozen 2026-05-28/29 embedding set.** A per-call-PCA bug (fixed in T1.36/T1.37) refit loadings per null in the provisional era; freezing flipped BHPS H1 and ~20 cells. Provisional-era JSONs are marked superseded (`results/.../stage1/SUPERSEDED.md`) and retained only as regenerable provenance inputs — never cite them. Physical archival is deferred to the paper repo-split.
- **P01-B §4.2.3 / §6.2 credibility prose: the BHPS Markov-1 null is anti-conservative (T1.6 verdict SUSPECT).** The calibration double-null was non-uniform → the Markov-1 null is insufficiently stringent for BHPS H0; any result using it carries this caveat. NB the T1.6 *code* review by CodeRabbit is still outstanding (accepted as-is by the User; a review-only PR was the plan) — the result is trusted, the review is a hygiene loose end.
- **P01-B §5 cross-machine reproducibility upgrade is gated on T0.3.** The §5 reproducibility statement (T2.18) deliberately asserts only *single-machine* determinism (locked env, seed propagation, `canary_rng.py`); the cross-machine bit-for-bit claim is NOT made. When T0.3 (two-machine repro) completes with the User's `canary_machine2` file, upgrade §5 to response-plan wording. Until then the honesty constraint holds — do not assert cross-machine reproducibility. (2.18-A)
- **P01-B §4.3 carries a pending matched/age-stratified Betti confirmation.** The spanning-identification headline (T2.17, T1.9b `newcomers_robust`) is drafted with a *pending robustness check*: a low-priority TDA-agent rerun of matched/age-stratified Betti against `balance_2026-05-14.json` + `matched_subset_2026-05-14.json`. Not blocking the prose; promote from "pending" to confirmed once that rerun lands. (2.17-A)

## Stage Summaries

### Stage 2 — Reviewer-Response Prose (P01-A / P01-B)

All eight Stage-2 prose Tasks are Done and merged to `main`. The stage rewrote the P01-A/P01-B response-to-reviewers sections against *committed canonical result files only* (empiricism-first: no prose drafted ahead of a landed `results/...` artifact). Sole agent: **academic-writing-agent**. Tasks 2.1/2.2/2.3 merged early (commits 0a91d94, 46d591e); 2.4/2.6/2.17/2.18 were drafted in the Wave-1 batch (commits fbb01e1, a1bf37e, ff8842b, 1534c9c) and accepted "STANDS" by Manager 11; 2.5 was the long pole — held **Partial** behind two missing canonical files (B9 normalised ARI, B10 stored-metric SE). Manager 12 merged those files (PR #53), dispatched the 2.5 finalisation, verified it number-by-number against the two JSONs on disk, and — after User per-section approval — merged the whole Wave-1 branch as a batch (merge `c7489c0`), then collapsed the stage.

Notable findings and patterns:
- **§4.6 (B9) moved 0.40→0.31 on a sanity-check.** A Manager "≈0.40" sanity number (sorted-NW-corner construction, quoted as a lower bound) was *not* optimal; the certified fixed-margin maximum is ~0.84 (bracket [0.8397, 0.8607]), so normalised ARI is ~0.31, not ~0.40. Lesson logged: a value quoted as a "lower bound" is a number to beat, not anchor on. §4.6 reports the achievable max as a certified bracket (NP-hard, no exact solver) — never an exact value.
- **§4.5 (2.4-A) provenance correction.** Prior draft cited superseded `tier1_clustered_firth_2026-05-13.json`; canonical is the 2026-05-16 conditional-Firth (n=6,173) → §4.5 no longer reports a significant broad-sample parental-class effect.
- **§5 Mapper audit (2.6-A) honest caveat.** Node count is strongly threshold-dependent; per-regime local FDR leaves only R0/R1 significant — stated at evidence level, not over-claimed.
- Two forward-looking contingencies (2.17-A, 2.18-A) are carried as Memory notes above; both depend on other-stage tasks (TDA rerun / T0.3) and are not Stage-2 blockers.

**Task Logs:**
- task-02-01.log.md, task-02-02.log.md, task-02-03.log.md
- task-02-04.log.md, task-02-05.log.md, task-02-06.log.md
- task-02-17.log.md, task-02-18.log.md

### Stage 1 — Computational Battery (P01-A / P01-B reviewer-response results)

All Stage-1 compute Tasks are Done and merged to `main`. The stage regenerated and hardened every computational result the P01-A/P01-B v2 response depends on, under a corrected frozen-embedding pipeline, with per-result pre-registrations, dual-metric testing (W₂ primary + landscape-L² mandatory complement), permutation nulls, and BH-FDR. Agents: **tda-agent** (instances 2–4), **panel-statistics-agent**, **reproducibility-agent**; coordinated across **Managers 10, 11, 12**. T1.28 (stratified per-subgroup Markov-1 W₂ FDR) was the long pole, landing 2026-07-09 (PR #72, merge `703101d`) *after* Stage-2 prose had already closed — the empiricism-first inversion: prose that could bind to already-landed results went first, the last heavy compute closed the stage.

**Foundation.** The **frozen-loadings correction (T1.36/T1.37)** underpins every headline number: a per-call-PCA bug refit embeddings per null, and freezing the loadings flipped BHPS H1 (W₂ 0.99→0.019) plus ~20 other battery cells. All citable Stage-1 numbers are the frozen 2026-05-28/29 set; provisional-era JSONs are superseded (`results/.../stage1/SUPERSEDED.md`), retained only as regenerable provenance.

**Headline results & locks.**
- **Core battery (T1.1–1.3):** regime structure rejects order-shuffle and Markov-1 nulls under W₂; **Outcome A** (USoc 5/7, BHPS 8/8 regimes BH-significant).
- **T1.2 family + T1.7:** headline + landmark/landscape/length-matched sensitivity. The BHPS-vs-USoc H1 asymmetry survives length-matching both ways (dedup amendment) → **not a horizon artefact** (Outcome A, 2026-05-31); §4/§6.2 direction locked.
- **T1.4:** intrinsic dimensionality over-dimensional for both datasets → no D-sweep.
- **T1.5 (H2 higher-homology):** the stage's longest investigation — an apparent H2 rejection diagnosed as a cloud-dispersion artefact (H0/H1 signal re-expressed) plus a fragile normalizer-magnitude-dependent residual. **Restriction stands + honest disclosure** (User) — no dedicated higher-homology section. PR #50.
- **T1.6 (BHPS Markov-1 credibility):** verdict **SUSPECT / anti-conservative** (non-uniform calibration double-null) → locks P01-B §4.2.3 (Markov-1 null insufficiently stringent for BHPS H0; dependent results carry the caveat). Memory-bandwidth-bound exact-W₂; 4 attempts, serial in-process fastest.
- **T1.8:** Markov-2 α-sweep — W₂ rejection directions stable across α∈{0,0.5,1,5}; canonical α=1. PR #47.
- **T1.9b:** spanning/Betti — `newcomers_robust` (windowed β₀-AUC, inferential; resolves the T1.9 divergence). §6/§3.4.2 locked. PR #51.
- **T1.10/1.11:** sub-regime heterogeneity (358 nodes) + a recovered live density-peak inversion bug fix. PR #40.
- **T1.23/1.24 (B9/B10):** OM-vs-GMM normalised ARI ≈**0.31** (certified fixed-margin bracket, not the vacuous 1.0) + stored-metric stability SE. PR #53.
- **T1.26/1.26b:** BHPS non-overlap → §6.2 size/landmark-fraction artefact confirmed (dual-metric). PR #45.
- **T1.27:** 10-of-14 GMM subsample. PR #41. **T1.34/1.35:** escape regression via the pre-registered svyglm fallback (WeMix/glmmTMB withdrawn).
- **T1.28:** stratified per-subgroup Markov-1 W₂ + per-family BH-FDR — **USoc 12/12 reject, BHPS 9/11** (two smallest BHPS strata underpowered per pre-registration). §6.1 contingency checked/locked; §6.1/§6.2 prose (T2.7) unblocked with a power caveat. PR #72.

**Patterns for future Managers.**
- **Research-assurance over software-tests was repeatedly decisive** — tests/lint/smoke passed while the math/null/provenance failed: B9's vacuous 1.0 normalisation, H2's dispersion-artefact rejection, the T1.11 density-peak inversion *live on main*, the `stability_se` latent metric bug, and the T1.28 §6.1 contingency were all caught by RA review against on-disk artifacts, not by tests.
- **Worker files [RESULT]; Manager files the outcome-contingent [DECISION] after independent verification.** Outcome forks (H2 restriction, Pre-reg #5 B|C, spanning characterize-vs-disclose, T1.28 §6.1) were routed to the User, not auto-resolved.
- **Governance built mid-stage:** input-provenance manifest + `manager_predispatch_check` (after the B9 vintage-coherence incident), the dispatch-readiness PreToolUse hook (compaction-proofing), CONVENTIONS single-source hardlink, R1/R3 provenance-recording locks.
- **Compute-feasibility discipline:** exact W₂ on ~5000-pt H0 diagrams is memory-bandwidth-bound and does not parallelise; a giotto-tda backend spike was falsified by a production-scale canary; cost-model gate added (benchmark the real statistic at realistic scale).
- **CodeRabbit review-then-merge is the gate:** a premature FF-merge of T1.6 (PR #54) marked it merged-on-arrival so CodeRabbit never reviewed → remediated by revert + re-PR; T1.28 (PR #72) held the gate correctly.

**Open threads (carried into Memory notes):** T1.6 CodeRabbit code review outstanding (result accepted as-is); T1.20 parental-NS-SEC = NaN audit pending.

**Task Logs:**
- task-01-01, task-01-02a…02g, task-01-04, task-01-05/05d/05e/05f, task-01-06, task-01-08, task-01-09/09b, task-01-10, task-01-11, task-01-12 … task-01-21, task-01-23/23b/23c/23d, task-01-24/24b, task-01-25/26/26b/27, task-01-28, task-01-29 … task-01-33, task-01-34/34a/34a-redo/34-35-coderabbit-fix, task-01-35/35-redo, task-01-36, task-01-37 (`.apm/memory/stage-01/`)
