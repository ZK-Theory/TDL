# §5 Reproducibility (replaces the §4.2.1 / §5.3 replay-drift disclosure)

This working file replaces the v1 replay-drift disclosure (v1 §4.2.1 note and the §5.3
"Exact $W_2$ replay" limitation) with a positive reproducibility statement grounded in the
locked environment, lockfile, and deterministic seed propagation. The legacy
replay-provenance material is moved to the supplement (see end of file). The main-text
reproducibility framing below contains no "drift", "discrepancy", or "may not exactly
reproduce" language.

## §5.x Reproducibility

All numerical results in this paper are computed under a single locked software
environment. Python 3.13 and the complete set of package versions — including the
persistent-homology and optimal-transport dependencies (`gudhi`, `ripser`,
`scikit-learn`) — are pinned in the committed lockfile `uv.lock`, which is distributed with
the paper's reproducibility repository. A reviewer or replicator obtains the exact
dependency set from the lockfile alone, with no version resolution left to the local
machine.

Stochastic components are governed by deterministic seed propagation from a single master
seed. The master seed flows to every downstream random-number generator in the
pipeline — landmark selection, surrogate-trajectory generation, null and null–null pair
sampling, mixture-model initialisation, and imputation iterations — and every result file
records the seed used. Run-to-run determinism under this scheme is verified directly: the
canary check `trajectory_tda/scripts/canary_rng.py` executes the Markov-1 $W_2$ pipeline
twice on a fixed master seed and confirms that the two runs produce bit-identical outputs.
Within a fixed environment, therefore, the headline numbers are exactly reproducible from
the stated inputs and seed.

The locked environment, the committed lockfile, and the audited seed propagation are the
foundation on which cross-machine reproducibility rests: pinning the interpreter, the
dependency tree, and the RNG seeding removes the principal sources of numerical divergence
between machines. A formal two-machine bit-for-bit confirmation — re-executing the locked
pipeline on a second, independently provisioned machine and verifying identical numerical
outputs — is the appropriate final check and is in progress; it is not claimed as
completed here. Where a future cross-machine run reveals residual platform-level variation
(for example, BLAS threading or floating-point summation order), the established procedure
is to pin the implicated settings (`MKL_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, or
equivalent) and record the resolution. The single-machine reproducibility guarantee above
does not depend on that pending check.

> **[DRAFTING NOTE — honesty constraint vs response plan, surfaced for review.]** The
> P01-B response plan §5.4(5) drafts the new §4.2.1 to assert that "two independent runs
> on different machines yielded identical numerical values." That assertion **cannot be
> made**: the two-machine bit-for-bit determinism check (Stage-0 T0.3) is paused pending a
> second-machine canary (Spec §"Reproducibility Framework" and the live
> `pipe/two-machine-check` worktree). The statement above is therefore deliberately
> **weaker than the response plan assumes** — it claims locked-environment + lockfile +
> seed-controlled single-machine reproducibility (verified by `canary_rng.py`), and frames
> cross-machine reproducibility as achievable-and-in-progress rather than verified. This
> is flagged per the Task Prompt instruction to report, rather than assert, the stronger
> claim. When T0.3 completes, this paragraph can be upgraded to the response-plan wording.

## Supplement (S) — Legacy replay-provenance note (moved out of the main text)

For the historical record, the pre-lockfile computation exhibited an exact-replay gap on
the archived $W_2$ null-battery values: a deterministic replay of the stored P01
integration order-shuffle null under the then-current $W_2$ code path did not reproduce the
archived $H_0$ obs–null mean (12.6766 stored versus 11.2172 on replay). A control replay
under an explicit order-1 Wasserstein (1-Wasserstein) monkeypatch produced values orders
of magnitude away (≈498.64 versus 11.22), ruling out an order-1 origin and confirming the
archived values as $W_2$-era outputs. This exact-replay gap was a provenance artefact of
pre-lockfile code and environment evolution; it is resolved structurally by the locked
environment described above, under which all v2 headline numbers are regenerated. The
archived `post_audit` JSON files (`results/trajectory_tda_integration/post_audit/`,
`results/trajectory_tda_bhps/post_audit/`) are retained as historical artefacts; any
replication writes to new date-suffixed result files rather than overwriting them.
