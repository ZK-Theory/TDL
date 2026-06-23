---
title: P01-A and P01-B Reviewer-Response Revision to v2
---

# APM Memory Index

## Memory Notes

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
