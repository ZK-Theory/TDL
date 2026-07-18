# Post-WT-1 decision brief — what happens after the headline-vintage materiality memo lands

**Audience: Stephen (Manager/User). Not an agent handoff.**
Companion to `.apm/memory/handoffs/2026-07-12-headline-vintage-materiality-brief.md`.
Purpose: fix the decision procedure — including the materiality rule — *before*
the memo returns, and specify exactly what the re-run pre-registration must
contain if one is needed.

> **Update 2026-07-12 (Manager reconciliation).** A prior ruling on the banks'
> vintage was found: the B9 2026-06-22 audit asserted the frozen banks were
> "Apr-8-rooted" and that "no canonical result consumes" the May-2 file — an
> mtime-based inference falsified bit-for-bit by Spike Set B (loadings vs
> sequences conflation; T1.23c's own promotion of Apr-8 is what broke
> reproduction of the orphan-derived headline). The reconciliation
> `[DECISION]` is in the Computational-Log (2026-07-12), cross-linked with
> `PROVENANCE-FINDING-orphan-reference.md`. The WT-1 brief was amended: the
> memo must quote and record supersession of the B9 assertion. Everything
> below stands; where a branch writes a `[DECISION]` or amends
> `SUPERSEDED.md`, it must reference the full superseding chain (B9 assertion
> → Spike Set B falsification → WT-1 memo → your ruling), not just the memo.

---

## 1. What WT-1 will hand you

Three artifacts:

1. **Decision memo** (`vault/00-Meta/Discovery/headline-vintage-materiality-memo-2026-07-12.md`)
   with a recommendation: **(a)** headline stands with a vintage caveat,
   **(b)** full B=1000 re-run on the Apr-8 sequences needed before Stage-2
   prose, or **(c)** mixed per dataset.
2. **Result JSON** (`results/trajectory_tda_integration/stage1/headline_vintage_materiality_2026-07-12.json`):
   the side-by-side p-value/d_perm table (orphan vs Apr-8 vintage for USoc),
   per-bank BHPS reproduction verdicts, diagram cardinalities and bottlenecks.
3. **Sidecar provenance manifests** (`<cache>.provenance.json`) for every
   frozen `.npz` bank — the first authoritative source-vintage record for the
   Stage-1 cache layer.

The memo *recommends*; you decide. The recommendation is advisory precisely
because materiality is a judgement about what Stage-2 prose will lean on.

## 2. Lock the materiality rule NOW (before reading the numbers)

Reading the deltas first and deciding afterwards is outcome-driven judgement —
the same failure mode pre-registration exists to prevent. Proposed rule, to
adopt (or amend) before the memo arrives:

**Branch (a) — headline stands** iff ALL of:
- The BH-FDR survivor set across the headline family is **identical** on both
  vintages.
- No primary headline p-value crosses α = 0.05 in either direction.
- No d_perm changes sign, and no headline statistic changes its qualitative
  reading (e.g. "signal at Markov-1" stays "signal at Markov-1").

**Branch (b) — re-run required** iff ANY of:
- Survivor-set change, threshold crossing, or sign flip on any statistic that
  Stage-2 prose is planned to cite.
- Any BHPS bank that Stage-2 prose depends on is UNRESOLVED (no on-disk build
  reproduces it) — an unreproducible provenance chain cannot be caveated,
  only replaced.

**Grey zone** (moves without crossing): if a cited p-value shifts by more than
a factor of ~2, or crosses a conventional reporting band (0.01 / 0.10) without
crossing α — default to (a) **plus a mandatory sensitivity sentence in any
prose that cites it**, escalating to (b) only if the statistic is
load-bearing for a headline claim rather than supporting.

**Branch (c) — mixed**: apply the rule per dataset. The likely shape: BHPS
banks reproduce from the canonical build (the orphan event was observed on the
integration sequences file; BHPS may be unaffected) → USoc-only handling.

Write your adopted rule (even one line: "rule as proposed in the post-WT-1
brief, adopted unamended") into the vault *before* opening the memo — a
pre-registration entry in spirit, timestamped.

## 3. Reviewing the memo — checklist

- [ ] Sanity cross-check passed: orphan-vintage p-values re-derived from
      committed data match `usoc_headline_frozen_2026-05-28.json` exactly. If
      this failed, nothing else in the memo is interpretable — send it back.
- [ ] Every BHPS bank has an explicit reproduced / not-reproduced / UNRESOLVED
      verdict with bottleneck + cardinality values.
- [ ] The comparison table covers **every** statistic in the committed
      headline JSON, not a selection.
- [ ] Manifest count equals frozen-cache count; spot-check one manifest.
- [ ] The agent's (a)/(b)/(c) recommendation is argued from the table, not
      from effect-size aesthetics ("only 0.7%" is not an argument; survivor-set
      stability is).

## 4. Actions per branch

### Branch (a) — headline stands

1. **`[DECISION]` entry** in `04-Methods/Computational-Log.md`: the adopted
   materiality rule, the observed deltas, the ruling, and the referent
   (memo + result JSON). This is the entry Stage-2 prose cites for permission
   to use the frozen headline.
2. **`SUPERSEDED.md` amendment** (`results/trajectory_tda_integration/stage1/`):
   a new *sequence-vintage* section — distinct from the existing PCA-refit
   supersession — recording that the frozen 2026-05-28 headline and banks were
   computed on the May-2 orphan sequences, judged non-material per the
   `[DECISION]`, with the manifest files as the machine-readable record.
3. **Prose caveat rule**: any Stage-2 paragraph citing the frozen headline
   carries (at minimum, once per paper) the vintage note. Add this to the
   P01-B `_project.md` open-items so it survives until drafting.
4. **Unblock**: Stage-2 prose tasks that cite the headline may dispatch.

### Branch (b) — re-run required

1. **`[DECISION]` entry** recording the ruling and the rule it followed.
2. **Author the re-run pre-registration** (§5 below) — you and a planning
   session author it; it is *not* delegated to the run agent.
3. **Dispatch preconditions**: WT-5 (compute_profile) merged first — the
   re-run should be the first fully instrumented, manifest-stamped battery;
   blast-radius audit (§6) completed and folded into the pre-reg.
4. **Stage-2 prose citing the headline stays blocked** until the re-run lands
   and its own `[RESULT]` is on file. Prose not citing the headline is
   unaffected.

### Branch (c) — mixed

Run (a)'s actions for the clean dataset, (b)'s for the affected one. The
re-run pre-reg then scopes to the affected dataset only — do not "re-run both
for symmetry"; the clean dataset's re-run would be uninformative compute.

### UNRESOLVED banks (either branch)

A bank no on-disk build reproduces: mark it **do-not-reuse** in its manifest
(`"reuse": "forbidden"`), and decide per bank whether anything planned still
consumes it. Consumed downstream → that consumption inherits branch (b).
Historical-only → record and move on. A short forensic pass (backup drives,
`git log` on adjacent committed files for reconstruction hints) is optional
and cheap; cap it at an hour.

## 5. The re-run pre-registration (branch b) — required contents

This is a **re-execution pre-reg**, not a new hypothesis. Its discipline is
faithfulness: same decision rules, new input vintage, both results retained.

**Placement**: JSON in `results/trajectory_tda_integration/stage1/`
(`pre_registrations_<date>.json` pattern) + vault pre-registration entry
written before compute, per APM rules.

**Must contain:**

1. **Inherited decision rules, by reference**: name the governing original
   pre-registration file(s) for the frozen headline (the 2026-05-25 era
   entries) and state that all decision rules, statistics, α, and the BH-FDR
   family are inherited **verbatim** — no new outcome-contingency.
2. **The one new rule — discrepancy reporting**: how orphan-vintage vs
   Apr-8-vintage results are compared and reported. Both retained; new
   date-suffixed files; the old headline marked superseded in
   `SUPERSEDED.md`, never deleted. State up front which result becomes
   canonical-citable (the new one, unconditionally — do not leave room for
   picking the preferred vintage after seeing both).
3. **Pinned inputs**: Apr-8 sequences sha256 `7a486917…` (full hash);
   frozen PCA loadings (no refit — representation-freeze audit in the run);
   L=5000 maxmin, seed 42.
4. **Threshold policy — decide explicitly**: the frozen run's threshold
   (16.91) was the p75 *of the orphan cloud*. Faithful re-execution means
   **re-deriving p75 by the same rule on the Apr-8 cloud** and reporting the
   numeric delta — not pinning 16.91. Pinning the number would mix vintages.
   State this choice in the pre-reg either way; it is exactly the kind of
   silent divergence the provenance audit exists to catch.
5. **Null ladder**: identical to the original frozen battery (whatever
   `run_headline` ran — enumerate the rungs from the committed headline JSON,
   don't reconstruct from memory). B=1000; per-draw seed policy 42+i+1.
   Note: new vintage → new null clouds by construction; common random numbers
   preserves the *seed policy*, not bit-identity with the old banks.
6. **p-value convention**: per `pvalue_denominator_cleanup_2026-05-28.json`,
   named in the pre-reg.
7. **New caches**: date-suffixed `.npz` + sidecar provenance manifest written
   **at generation time** (WT-1's schema); 2026-05-28 banks untouched.
8. **Instrumentation**: compute_profile per cell (WT-5) — gives the first
   per-phase cost record of the full battery, closing the gap Set B exposed.
9. **Blast radius annex** (§6): the enumerated consumer list with each
   consumer's disposition (re-derive / vintage-caveat / moot).
10. **Runtime plan**: ≥4 process-based workers, checkpoint every 25 draws,
    wall-time flag, benchmark before launch. Rough envelope from T1.6 + WT-1
    profiling: PH on ~1000 null clouds parallelises well; the W₂ bill
    (obs-null ~1000 pairs + null-null ~500 pairs, ×2 dims, at ~5–8 s/pair)
    is ~5–6 h serial per dataset → a half-day to day-scale job with process
    parallelism. If WT-1's measured numbers say materially worse, revisit
    before dispatch.
11. **Worktree/model**: branch `run/headline-rerun-apr8`, Opus 4.8 / high —
    faithful re-execution of locked rules; the judgement lives in this
    pre-reg, not in the run.

## 6. Blast-radius audit (feeds the pre-reg; cheap, do before authoring)

The frozen banks were "reused across Stage-1". Enumerate consumers before
scoping the re-run:

- **Source of truth**: WT-1's manifests list the banks; a Grep over
  `trajectory_tda/scripts/` and `results/.../stage1/*.json` for the cache
  filenames yields the consumers (lm_sensitivity frozen runs, landscape
  sensitivity, dedup-amendment comparisons, length-matched/nonoverlap
  variants, anything T1.9b-adjacent).
- **Disposition per consumer**: (i) *re-derive* — it feeds a live Stage-2
  claim; (ii) *vintage-caveat* — historical/sensitivity value only; (iii)
  *moot* — superseded already. Expect most sensitivity analyses to be (ii):
  their purpose was robustness of the design, and design robustness on the
  orphan vintage still evidences design robustness.
- The subgroup/stratified batteries (T1.28 line) have their own checkpoint
  provenance — check whether they consumed the frozen banks or built their
  own nulls before assuming they're in scope.

## 7. Sequencing and what's blocked meanwhile

- **Blocked until the `[DECISION]` is on file**: any Stage-2 prose citing the
  USoc/BHPS W₂ headline. Nothing else.
- **Not blocked**: WT-2/3/4 (they consume the Apr-8 sequences directly), WT-5,
  P01-A work.
- **Spike set C** (W₂-economy: diagram pruning before W₂, parallel/approx W₂,
  landscape-L² as primary economical statistic) plans **after** the decision.
  If branch (b) runs, do NOT fold economy levers into the re-run — it must be
  methodology-faithful; economy work calibrates against it afterwards, and
  gets a cleaner reference out of it.

## 8. Standing locks regardless of branch

1. **CONVENTIONS.md addition (propose at decision time)**: every frozen
   diagram/null cache carries a sidecar provenance manifest naming its
   source-input sha256s, written at generation time — closes skill
   observation #53 properly (WT-1 retrofits; this makes it forward-binding).
2. **CONVENTIONS.md addition**: spike branches/worktrees are retained until
   their scratch reference code has been promoted by the consuming dispatch
   (or the line is formally PARKed) — today's branch-restore incident is the
   precedent. Anything escalated to User/Manager must be promoted out of
   scratch immediately (the provenance note briefly existed only in a
   gitignored worktree scratch).
3. Close observation #53 in the skill-observations log once (1) is locked.
