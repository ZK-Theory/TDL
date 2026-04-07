# Post-Audit W2 Repo Note

For any future standalone paper repo or `repo-manifest.yaml`, treat the following files as the authoritative null-battery artifacts:

- `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json`
- `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json`

Extraction rule:
- Package the two `post_audit` JSON files as the forward-looking `W_2` results used for JRSS draft assembly and reproducibility.
- Do not silently replace or rename the legacy `results/trajectory_tda_integration/04_nulls_wasserstein.json` and `results/trajectory_tda_bhps/04_nulls_wasserstein.json` files.
- If the legacy JSONs are retained in any extracted repo, label them explicitly as historical manuscript-era artifacts and not as the authoritative post-audit outputs.

Metadata that should travel with the archived artifacts:
- Wasserstein order: `W_2`
- Permutations: `100`
- Landmarks: `2000`
- Seed: `42`
- Run date: `2026-04-07`

Implementation note:
- `trajectory_tda/scripts/run_wasserstein_battery.py` now supports `--output-name` and `--overwrite-output`, so future archival reruns can be written to new result files without overwriting historical artifacts.
- `trajectory_tda/topology/permutation_nulls.py` now normalises missing cohort labels to `"unknown"`, which is required for stable `cohort_shuffle` reruns on repaired legacy checkpoints.