# Confirmation of W9 WP9.1 stage A, revision 3 (`df4ec74d`)

**Date:** 2026-10-23<br>
**Reviewer:** the session that wrote the review (`d9a7d22b`) and the re-review (`e65abca1`). It did not author revision
3, P-070 or the reconciliation.<br>
**Skill:** `adversarial-design-review` (remediation confirmation)<br>
**Verdict:** **CONFIRMED, with one Minor residual and three Info notes.** N-1 to N-4 and n-1 to n-5 are closed. No
Blocking or Major finding remains.<br>
**Known limit (P-058):** every review in this chain ran on one model family. This is a known limit, not a finding.

## 1. Subject

`df4ec74d` on `pipe/w9-wp9-1-schemas`, one commit on `e65abca1`. It changes the generator, the 17 schemas, the test
(61 tests), the note, the reconciliation (§5) and the register (P-070). Neither earlier review file is touched.

## 2. Re-review findings: confirmed closed

| Finding | Check | Result |
|---|---|---|
| N-1 projection writer | `w9_schema_gen.py:456-469`; probes P1 to P5 and P8 | Closed. Only `["ars_projection_rebuild"]`, `successor_owned`, `repository_root`, `untracked_file`, under `.research-system/projections/legacy/`, is admitted. `ars_reviewed_pr` is refused for the projection, and `ars_projection_rebuild` for `results/ars/` |
| N-2 unobserved sources | `sourceLocator` and `sourceRef` (`:236-275`); used at `:192, 775, 786` | Closed. The W9-T4 shape (lines 69–71 plus the tier-1 file) and the `corrected_by` vault entry validate in the test. A restricted suffix is refused in a locator (probe L2) |
| N-3 edge-table closure | Test `:156-203, 477-488` | Closed. The walk follows qualifiers and source identities into each host schema. `RECORD_EDGES` must equal every field whose definition admits `obj_`. A paper root's qualifier source is declared observation-only, and the transition-target negative control fires |
| N-4 supersession targets | P-070; test `:150-155, 191-193, 491-500` | Closed. The four W9 §13.1–13.2 kinds are declared, and no record targets a supersession |
| n-1 aliases | `REL_PATH_PATTERN` (`:41-46`); probes Q1 and Q3 | Closed. `CONVENTIONS.md.`, `CONVEN~1.MD`, `CONVENTIONS.md /`, `CONVENTIONS.md..` and `x/null_cache.pkl.` are all refused. No tracked path is excluded by the new rule (`git ls-files` finds none) |
| n-2 suffix list | `RESTRICTED_SUFFIXES` derives the pattern (`:31-40`); the test binds it to the contract | Closed |
| n-3 bytes | `--check` and the test compare bytes | Closed. `--check` exits 0 |
| n-4 row selector | One `allOf` branch per selector (`:723-727`); test | Closed |
| n-5 adapter | Note §1 | Closed |

My earlier mutation probe was independent of the author's. For revision 3 I relied on the author's probe for the four
new guards, and checked each guard by the direct probes above.

## 3. Residuals

**r-1 (Minor) — The vault alias of `CONVENTIONS.md` still passes as an observation's source and as a locator.** W9 §7.3
(line 417) says "the vault alias is a prohibited read path for observations". The registration refuses the alias (M-2,
n-1). But:
- probe V1: an observation whose `source_identity` is `vault_file` with `vault_path: CONVENTIONS.md` is VALID;
- probe L1: a qualifier source given as a `vault_file` locator for `CONVENTIONS.md` is VALID.

At runtime the observation must also name a registration (`registration_ref`), and WP9.3's reader will join the two. So
the binding control exists downstream, and this is a cheap schema hardening, not a gap in authority.

Fix: add `{"not": {"pattern": CONVENTIONS_NAME}}` to `vault_path` in the `vault_file` branches of `sourceIdentity` and
`sourceLocator`, with V1 and L1 as negative controls. If the author prefers, it can be carried instead as a WP9.3
check that an observation's source matches its registration's path and root.

**Info.**
- **i-1.** A `legacy_research_result` can be registered under `.research-system/projections/legacy/` (probe P7). The
  directory is gitignored and ARS-owned, so such a registration is nonsensical rather than harmful. WP9.3 can refuse
  it.
- **i-2.** A Git locator's `line_span` may be inverted (probe L3, 71 to 69). This is not expressible in JSON Schema, so
  it is the reader's check.
- **i-3.** The two same-kind observation edges (qualifier source, conflicting record) are excluded from the cycle
  check. A content-addressed reference pins the target's hash, so two observations cannot name each other. The
  exclusion is safe.

## 4. Verification

- **Probes.** `probe_r3.py` and `probe_r3b.py`, from the session scratchpad with `python -I`: sections P, Q, L and V
  above.
- **Generator.** `python -I tools/w9_schema_gen.py --check`: exit 0. `git status --porcelain` is clean afterwards.
- **Lint.** `ruff check --no-cache` and `ruff format --no-cache --check` pass on the generator and the test.
- **Tests.** `pytest -p no:cacheprovider --no-cov -o addopts=""` with `PYTHONDONTWRITEBYTECODE=1`, over the first
  review's command-9 set plus `tests/tools/test_w9_segmentation.py`: **556 passed in 499.20 s**, none skipped. The
  author's 555 passed and 1 skipped is the same environment-dependent skip as before.
- **Files edited.** This file only. No subject file, vault, `.apm/`, store, Jira or `papers/` write.
