# APM Failure Inventory → ARS-Enforceable Invariants (2026-07-17)

**Status:** input evidence for the WP6 adversarial review. WP6-agnostic: this document
presumes no outcome of that review and is usable under any outcome.
**Produced by:** standalone documentation/audit session (brief:
`.apm/memory/handoffs/2026-07-17-ars-transition-artifacts-brief.md`), read-only with
respect to code, results, and manuscripts.
**Audited commit:** `main` @ `e8890fb71331ffa3b9bdba57a55f56ffb30ed65b`
(post-PR #116 remediation, post-PR #117 restore of the #105 content).
**Companion:** `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md` (claim-level
evidence for the prose failure classes; canonical-state snapshot).

**How to read the invariants.** Every failure class below already had an
*instruction-form* countermeasure when the failures occurred — a rule in CLAUDE.md,
`.claude/rules/papers.md`, a Task Prompt, a skill, or a convention. The instruction
form failed. Each invariant is therefore phrased as a machine-checkable property of a
deliverable or a workflow gate ("a deliverable that X is rejected by gate Y before
Z"), never as an instruction to an agent. Classes are severity-ordered by realized
materiality.

---

## Class 1 — Silent solver/method substitution

**What happened.** A statistic-changing fallback executed silently, and every
downstream consumer treated its output as the intended statistic.

**Instances.**
- `trajectory_tda/topology/vectorisation.py::wasserstein_distance` fell back to a
  greedy persistence-rank matching whenever POT was absent from the venv (era
  ≤ 2026-05-29, plus a fragile 2026-05-30 → 2026-06-16 window in which POT was
  present but undeclared). H₁ W₂ inflated ~18–56×; both citable H₁ headlines were
  affected (USoc frozen H₁ obs-null 233.68 vs exact 12.68 — provably impossible as
  exact W₂ against a ~35.8 diagonal bound; BHPS p 0.019 → exact floor 0.000999 with
  d_perm +2.06 → +19.26). Full audit: WT-6, PR #94,
  `results/trajectory_tda_integration/stage1/w2_fallback_audit_2026-07-14.json`;
  vault Computational-Log 2026-07-14 entries; memo `[[w2-fallback-audit-memo-2026-07-14]]`.
- P01-A Table 1's entire H₁ column (every source greedy-era, every H₁ ρ̂ ≈ 1 — the
  greedy compression signature); two cells invert under the exact solver
  (Computational-Log 2026-07-14 audit-gap `[RESULT]`).
- The dedup-amendment "H₁ flip" (`1.006 → 1.867`) was the solver, not the dedup —
  the committed disclosure mechanism ("~139 phantom features") is misattributed
  (2026-07-14 `[RESULT]`, `dedup_amendment_comparison_corrected_2026-07-14.json`).
- The §6.2 non-overlap "H₁ rejection disappears" claim was greedy suppression;
  under exact W₂ the retained remainder object rejects (d_perm +7.48, p 0.000999) —
  pre-registered adverse fork fired (2026-07-16 `[DECISION]`).
- `markov2_alpha_sweep_summary_2026-06-16.json` W₂ means ~277 against a ~20 exact
  diagonal bound — solver-uncertifiable (no solver-identity field, no retained
  per-pair arrays); its cells are held out of P01-B Table 2 pending the
  pre-registered certified recompute (2026-07-17 pre-registration).
- A second, *benign* silent fallback exists for contrast:
  `validation/wasserstein_null_tests` falls back to scipy Hungarian on augmented
  diagrams — same estimand, different algorithm. The defect class is
  estimand-changing fallbacks, not fallbacks per se.

**Countermeasure in place.** The dual-metric mandate (W₂ + landscape L²), unit
tests, smoke canaries, per-file result schemas, CodeRabbit review, and the
"verify before relying" APM rule.

**Why it failed.** The fallback returned a plausible in-range number instead of
raising; no result file recorded solver identity, so no schema could check it; the
inflation hit obs-null and null-null *together*, so ratio-style statistics stayed
plausible; and under greedy a negative control could not fail, so the one signal
that should have looked wrong looked fine. The system's output under "not working"
was indistinguishable from "working".

**ARS invariants.**
- **I1a.** A result artifact asserting any metric statistic is rejected at ingestion
  unless it carries an in-band solver/backend identity block (solver name, version,
  `convention` tag, exactness flag) for every metric computed. Absence of the block
  is a hard reject, not a warning.
- **I1b.** A result artifact whose W₂ value exceeds its diagram-derived diagonal
  bound (`W₂(A,B) ≤ sqrt(0.5·Σpers_A² + 0.5·Σpers_B²)`) is rejected by an
  impossibility screen evaluated from retained per-pair/diagram data; artifacts
  without enough retained data to evaluate the screen are marked non-citable.
- **I1c.** Any code path that can substitute an estimand-changing algorithm is
  rejected at review time unless the substitution is opt-in, stamps `convention`
  into the output, and has a binding test proving the default path raises when the
  primary solver is unavailable. (Same-estimand fallbacks are exempt but must stamp
  the algorithm used.)
- **I1d.** A prose deliverable citing a numeric statistic is rejected unless the
  cited artifact's solver-identity block satisfies I1a — the claim→artifact binding
  (Class 3) must resolve to a *certified* artifact, not merely an existing one.

---

## Class 2 — Gates that cannot fire, never ran, or were vacuous

**What happened.** Enforcement believed to be active either never executed, could
not fail by construction, or checked a tautology.

**Instances.**
- **The contract pre-commit gate never ran (47+ days).** `core.hooksPath=.githooks`
  set 2026-04-10 (`a54a2c4`); the validator was installed to `.git/hooks/pre-commit`
  on 2026-05-27 — a directory git had been ignoring for 47 days. Every "pre-commit
  hooks ran clean" claim in that window was hollow; CodeRabbit was in practice the
  sole functioning automated check (2026-07-15 `[PIPELINE]/[NEGATIVE]`, PR #98).
- **Gate 0 (skill-tree sync) was documented in three files and existed in none** —
  and the gate restoration itself missed it because it rebuilt the gate list from
  the docs, not from the dead hook's contents (2026-07-15 `[PIPELINE]`, PR #100).
- **A vacuous convention crosscheck:** the 2026-07-12 WT-1 memo compared
  `committed_orphan_stats` against the JSON those values had been copied from one
  step earlier — trivially true, and its PASS carried the memo's inverted
  conclusion (corrected by WT-1c; the convention-gate contract now requires the
  reference side be freshly recomputed).
- **Nulls invariant to their statistic:** `_label_shuffle`/`_cohort_shuffle`
  permute rows of an already-embedded cloud; VR persistence is set-valued, so the
  "null distribution" was landmark-selection noise. Table 1's only negative
  controls could neither pass nor fail — p ≈ 0.5 read as "control passing" for the
  paper's whole life (2026-07-16 `[NEGATIVE]`;
  `[[a-null-must-perturb-the-object-the-statistic-consumes]]`).
- **Gate-4 blind spot:** 348 of 1,362 result JSONs (26%) claimed by no
  `applies_to_glob` — skipped, not validated, producing no error (2026-07-15 entry).
- Related scope defects: the stage1 `file_dispatch` over-match (a corrected-headline
  file validated against the wrong schema; 6 files affected), and binding tests
  that skipped the exact stale files they guarded (PR #31 era).

**Countermeasure in place.** The contracts framework itself, `.pre-commit-config.yaml`,
`install-git-hooks.py` (which printed success while doing nothing), documentation
of the gates in CLAUDE.md/CONVENTIONS, and Worker reports asserting hooks ran.

**Why it failed.** Passive enforcement is unverifiable enforcement: an absent hook
does not error; a skipped file does not error; a vacuous check passes. Nothing
emitted a positive liveness signal a human reads
(`[[silent-absence-is-the-failure-mode-that-produces-no-error]]` — three instances
in one week, each one level deeper: infrastructure, computation, experimental design).

**ARS invariants.**
- **I2a.** Every gate in the workflow must emit a signed, positive execution record
  (gate id, commit/artifact hash, verdict, timestamp) to a ledger the acceptance
  step reads; a deliverable whose required-gate set lacks a matching execution
  record is rejected — "no record" and "gate failed" are equivalent.
- **I2b.** Every gate must ship a negative control demonstrating it can fire (a
  known-bad input that the gate rejects), re-run on every gate change; a gate
  without a passing negative control is not counted as enforcement.
- **I2c.** Coverage is closed-world: every result artifact must be claimed by
  exactly one validation scope; an artifact claimed by zero scopes (or two) fails
  admission. Exclusions require a machine-readable reason and a pointer to the
  scope that does cover the file.
- **I2d.** A null-model specification is rejected unless it carries a
  machine-checkable invariance audit: evidence that the null operation perturbs the
  statistic's actual input object (statistic value changes on a probe draw) and
  that the observed statistic is not structurally centered in its own null.
- **I2e.** A comparison/reconciliation check is rejected if its reference side is
  not re-derived through the code path under test (data-lineage check: reference
  values may not be copied from the artifact being validated).

---

## Class 3 — Evidence-unbound prose claims

**What happened.** Methods/results text asserted procedures or evidence the record
does not support. Detection came only from the User and CodeRabbit.

**Instances** (claim-level detail and ~40 further findings: the companion claim-trace
audit).
- PR #116 CodeRabbit findings on `papers/P01-B-JRSSB/drafts/sections/`:
  §3.3 described a paired/shared-draw bootstrap while the implementation resamples
  i.i.d. flattened distance arrays (bootstrap-unit misdescription); §3.1 silently
  deviated from the spec'd L=1,000 H₂ fallback; the spanning section cited a
  constant-by-construction W₂ as cross-ε* robustness evidence. (All three
  remediated in #116 by disclosure; recorded here as the failure instances.)
- P01-A §4.3 negative-control text asserts eight label/cohort p-values as evidence
  of clean negative controls — invalid-by-construction, "none of them was ever
  evidence" (2026-07-16 `[NEGATIVE]`); still in the draft at the audited commit.
- P01-A §6.2 asserts the non-overlap H₁ disappearance (p=0.221, 0/20 subsamples) —
  falsified for the retained remainder object on 2026-07-16.
- P01-A §S6/§6.2 assert the "139 phantom features" dedup mechanism — struck by the
  2026-07-14 ruling (the flip evidence was the solver).
- P01-A `methods-w2-formal-definition.md` and `supplement-S0-null-specification.md`
  assert a permutation p-value denominator of `1 + N_pairs` (floor ≈ 0.002) as "the
  locked formula" — contradicting the 2026-05-27 `monte-carlo-permutation-p-value`
  contract lock (denominator = null draws; floor 1/1001) and every canonical result
  file (`pvalue_null_draws: 1000`).
- P01-A `methods-h0-orthogonality.md` builds two rewritten paragraphs on
  "ARI = 0.00004" — no artifact on `main` supports the value, and the §4.6 working
  file states the H₀-vs-GMM material was removed as a different object.
- P01-B §3.2 quotes the α-sweep's W₂ p-values (including a BHPS H₁ non-rejection,
  p ≈ 0.98–0.997) as empirical motivation — the source is solver-uncertifiable and
  the exact-W₂ rebuild rejects BHPS Markov-2 H₁ (p 0.0099, d_perm +27.17).

**Countermeasure in place.** `.claude/rules/papers.md` (empiricism-first, "every
number cites its source JSON" as a Task Log obligation), `/paper-claim-trace` and
`result-provenance-review` skills, Manager review, per-section User review.

**Why it failed.** The binding between a sentence and its artifact existed only in
the agent's report, not in the deliverable; nothing machine-checked that the cited
artifact (a) exists, (b) is canonical rather than superseded, (c) computes the
object the sentence names, and (d) still supports the sentence after later rulings.
Instructions to verify were followed at drafting time and silently invalidated by
subsequent supersessions — prose has no re-validation trigger.

**ARS invariants.**
- **I3a.** Every substantive claim in a manuscript deliverable must carry a
  machine-readable binding (claim id → artifact path/hash + field path + expected
  value/tolerance). A deliverable containing an unbound numeric or procedural claim
  is rejected before human review.
- **I3b.** Bindings are validated against the artifact *content* at acceptance
  time: value equality within tolerance, referent fields (estimand/comparison/
  metric selectors) equal to what the claim names, and artifact certification per
  I1a. A binding to a superseded artifact (per the supersession manifest) fails.
- **I3c.** Supersession events re-trigger validation: when an artifact is marked
  superseded/falsified, every deliverable holding a binding to it is automatically
  flagged stale and blocked from citation/assembly until re-validated. (This is
  what the record could not do for §6.2/§S6/negative-control text.)
- **I3d.** A methods sentence describing an algorithmic property (resampling unit,
  denominator, smoothing, fallback behavior) must bind to the implementing function
  (file + symbol + content hash); the binding fails when the implementation hash
  changes without prose re-validation, and fails at creation if a
  designated checker cannot confirm the description against the implementation.

---

## Class 4 — Document-register violations

**What happened.** Report-style content — process narration, tracker IDs, repo
paths, review-status blocks — recurred inside manuscript section files in "almost
every writing agent task" (User statement, 2026-07-17, recorded in the freeze
instructions).

**Instances at the audited commit** (all P01-A; the seven P01-B files were
de-scaffolded by T2.23 / PR #109 on 2026-07-17):
- `results-bhps-robustness.md`, `results-stratified-w2-subgroups.md`: HTML
  `EDITORIAL STATUS (provisional — awaiting User per-section review)` blocks with
  result-JSON paths and pending-decision notes addressed to the User.
- `supplement-S6-length-matched-dedup.md`: 39-line HTML header with commit hashes,
  PR numbers, CodeRabbit references, vault decision pointers.
- `results-ari-stability.md`: opens "This working file covers the §4.6
  normalised-ARI rewrite (reviewer issue B9)…"; body parenthetical quoting the
  reviewer response plan; closing "Provenance status" section listing JSON files.
- `results-escape-regression-foo.md`: Task IDs in body text ("(T1.29)", "(T1.15)",
  "the earlier formal-mediation analyses (T1.21/T1.22) were superseded");
  "*provisional label; final table number set at v2 assembly*" in table captions.
- `methods-h1-artefact-caveat.md`: "(cf. Bauer 2021; Reviewer 1, Issue 9)" inside
  the manuscript quote block — a banned tracker token in referee-visible text.
- `methods-w2-formal-definition.md` / `supplement-S0-null-specification.md`: repo
  paths with line numbers and Task/branch names ("T1.2, in progress on branch
  `pipe/stage1-phase-split`") in body text.
- `table1-effects-d_perm-rho-CI.md` and `results-mapper-vocabulary-audit.md` are
  structured as edit-plans/audit-notes (v1 line-number tables, "Note for v2
  assembly" sections), not as manuscript text.
- Historical: the T2.23 de-scaffold PR (#109, "zero science change") had to remove
  the same class of scaffolding from all seven P01-B files — written by earlier
  writing tasks under the same rules.

**Countermeasure in place.** `.claude/rules/papers.md` carries an explicit banned-token
list, a two-channel separation table, and a mandatory pre-delivery self-check
("delete anything a referee could not read… state in your report that you ran this
check"). Skill observation 59 records the register-inheritance mechanism.

**Why it failed.** The register rule is enforced by the same agent it constrains,
at the end of the same context window that produced the violation; the self-check
is self-attested. Nothing outside the agent parsed the deliverable for the banned
classes. Detection therefore fell to the User and CodeRabbit, post hoc.

**ARS invariants.**
- **I4a.** A manuscript-class deliverable is rejected by a register gate before
  human review if it contains any of: HTML comments; tracker/Task/issue IDs
  (T\d+\.\d+, R\d-, B\d+, C\d/M\d/H\d/L\d patterns); repo paths or result-file
  names in body text (outside a designated reproducibility statement); the tokens
  of the banned list in `.claude/rules/papers.md` ("working file", "Manager",
  "Task Prompt", "awaiting review", "provisional label", "out of scope", …);
  review-status or provenance sections.
- **I4b.** The register gate is a property of the *document class*, applied by the
  workflow to every deliverable of that class — not a step the producing agent
  runs on itself. Its verdict is recorded per I2a.
- **I4c.** Claim-provenance metadata (the I3a bindings) must live in a sidecar
  channel (annex file or structured front-matter stripped at assembly), so that
  satisfying Class 3 can never re-introduce a Class 4 violation.

---

## Class 5 — Provenance by inference instead of verification

**What happened.** Provenance assertions were derived from metadata (mtimes, dates,
lockfiles, architecture diagrams) rather than content, and were later falsified
bit-for-bit.

**Instances.**
- **B9 (2026-06-22):** "the frozen Stage-1 W₂ banks are Apr-8-rooted; no canonical
  result consumes the May-2 file" — mtime-reasoned, conflated PCA loadings with
  sequences, falsified bit-for-bit by Spike Set B (the frozen USoc cache reproduces
  *only* from the May-2 orphan; bottleneck ≈ 6.5e-309 vs 0.597). The 2026-06-23
  promotion of the recovered Apr-8 sequences is exactly what made the frozen
  headline stop reproducing from the canonical path (2026-07-12 `[DECISION]`).
- **Working-tree sha256 pins broken by line-ending checkout variance:** under
  `core.autocrlf=true`, working-tree bytes depend on how a file arrived (git
  checkout → CRLF; tool write → LF), so the input-provenance gate fired a false
  VIOLATION on `SUPERSEDED.md` — and the first analysis of the incident was itself
  wrong because it was inferred from a byte comparison instead of measured with
  `git ls-files --eol` (2026-07-15 pre-registration, incidental finding; the sound
  signature is the git blob hash).
- **Dating the solver era from the lockfile pin** would have condemned four sound
  files: a lockfile records when a dependency became *guaranteed*, not *present*
  (WT-6; the true boundary 2026-05-29/30 was established from the artifacts).
- Positive counter-instance worth preserving: the T1.23c recovery showed an
  mtime/layout signal screaming "non-reproducible" while the fail-closed content
  canary reproduced the baseline to 10 dp — metadata is suspicion, content is
  verdict.

**Countermeasure in place.** The input-provenance manifest system (R-B/R-C),
`result-provenance-review`, and the APM "verify before relying" rule.

**Why it failed.** The gates pinned the wrong signature class (mtimes, working-tree
bytes) — checkout-unstable proxies for content — and assertions made in passing
(inside an entry titled for a different object) were never surfaced to the
authoritative manifest where a later reader would re-check them.

**ARS invariants.**
- **I5a.** Provenance signatures for tracked text/data inputs are content-addressed
  and checkout-invariant (git blob hash for tracked files; content sha256 for
  untracked intermediates). A manifest pinning an mtime or working-tree byte hash
  of a tracked file fails schema validation.
- **I5b.** A claim that artifact A derives from input B is accepted only with a
  reproduction check (regenerate-and-compare within tolerance) or an explicit
  `unverified-inference` marker that blocks citation-grade use; the marker cannot
  be cleared except by a recorded reproduction.
- **I5c.** Frozen caches/banks are admissible only with a generation-time sidecar
  manifest binding cache hash → input hashes → seed policy → backend versions
  (already a CONVENTIONS lock; ARS makes the sidecar's presence and validity an
  admission predicate for any workflow consuming the cache).
- **I5d.** Environment/era claims ("solver X was active for artifact Y") must cite
  an artifact-level witness (in-band stamp, gated reproduction), never a
  repo-history event (pin, commit date).

---

## Class 6 — Merge-gate violations (merged before review concluded)

**What happened.** PRs were merged before the review gate concluded, twice
requiring corrective surgery on `main`.

**Instances.**
- **PR #54 precedent:** a local merge FF-pushed marked the PR merged-on-arrival;
  CodeRabbit bailed with "PR is closed"; remediated by revert + re-PR (recorded in
  auto-memory as the review-then-merge lock).
- **2026-07-17 revert cycle:** #105 (Table 1 H₁ exact rebuild) and #106 (dedup
  rewrite prose) merged 08:36–09:05 before their CodeRabbit reviews concluded;
  revert PRs #111/#112 merged 10:41 on top of them, removing both content sets
  from `main`; the #105 content returned via the reviewed restore PR #117 (merged
  2026-07-17 18:44); the #106 prose remains parked for the ARS lane. Cost: a full
  day of `main` in a state where the citable Table-1 H₁ artifact did not exist,
  plus this audit having to pin its baseline mid-day.

**Countermeasure in place.** The review-then-merge rule (CONVENTIONS/CLAUDE.md,
auto-memory), and the worktree-retention lock designed around reviews concluding.

**Why it failed.** The rule was procedural with no mechanical interlock: nothing
prevented a merge before the review-state check; the actor performing the merge is
the same one asserting readiness, and under time pressure the assertion substitutes
for the check.

**ARS invariants.**
- **I6a.** Publication/merge of a deliverable requires a recorded
  review-concluded event for that exact head SHA from the designated reviewer
  set; the merge action is rejected (branch protection / workflow interlock) when
  the event is absent — not flagged after the fact.
- **I6b.** A revert or re-apply of previously published content is itself a
  deliverable subject to I6a; the ledger must link supersession chains
  (publish → revert → restore) so consumers can resolve the live state
  mechanically (this audit had to reconstruct #105→#111→#117 by hand).

---

## Class 7 — Instruction non-compliance despite explicit brief text

**What happened.** Dispatched briefs stated a requirement verbatim; the deliverable
ignored it; the envelope/report asserted compliance.

**Instances.**
- **Pre-reg `planned_contracts` unmaterialised at dispatch — twice** (WT-2, Obs 68;
  MCbiF confirmatory, Obs 73), despite the pre-reg embedding the full contract spec
  precisely so dispatch would be mechanical; rescued both times by a dedicated
  extraction agent.
- **Worker-authored contracts** despite the Manager-authors-contracts split being a
  CONVENTIONS "NEVER" (T1.6 dispatch, Obs 7; caught by the User).
- **Manager dispatch prerequisites described but not created** across three
  dispatches (no worktree, no contracts, incoherent inputs) — the guide text was
  lazy-loaded and dropped out of context post-compaction (Obs 17; led to the
  PreToolUse dispatch-readiness hook, PR #52).
- **T1.38 Phase 2 Worker** wrote checkpoints worktree-side despite the two-path
  rule (Manager copied them to `PROJ_ROOT` at review) and omitted the mandatory
  vault write at completion (2026-07-16 `[RESULT]`, noted at acceptance).
- **Register rules ignored in near-every prose task** despite the banned-token list
  and mandatory self-check (Class 4; the self-check was asserted in reports while
  violations shipped).
- **Sanity-value anchoring:** a dispatch-quoted "lower bound" (ARI ≈ 0.40) was
  reproduced rather than tested; the certified answer was ≈ 0.31 (Obs 19; now an
  anti-anchoring clause in pre-registrations).

**Countermeasure in place.** The brief text itself, CONVENTIONS locks, skills
restating the rules, Manager review of reports.

**Why it failed.** Compliance was asserted by the same context that failed to
comply; instructions are context-fragile (compaction, long tasks) while the
enforcement surface (a hook, a gate) is not. Where a hook was installed
(dispatch-readiness), the failure mode stopped recurring; where enforcement stayed
prose, it recurred.

**ARS invariants.**
- **I7a.** Every brief/dispatch requirement that names a concrete artifact
  (contract file, worktree, manifest, checkpoint path, vault entry) is compiled
  into a machine-checkable obligation list; task acceptance requires each
  obligation's existence/validity check to pass, evaluated by the workflow, not
  reported by the agent.
- **I7b.** Output-location rules (two-path) are enforced by the runtime: writes of
  designated artifact classes outside their declared root fail at write time or at
  acceptance reconciliation, not at a later consumer's crash.
- **I7c.** Expected/sanity values in a brief are marked as hypotheses in the
  obligation list; an acceptance run that reproduces a quoted expected value
  without an independent-derivation record is flagged for anchoring review.
  Pre-registrations carry no expected values in decision-rule scope (the 2026-07-15
  anti-anchoring clause, generalized).

---

## Class 8 — Vault/record discipline omissions and buried rulings

**What happened.** The research record's required entries were omitted, mislocated,
or unlocatable at the point of need.

**Instances.**
- T1.38 Phase-2 Worker omitted the vault `[RESULT]` write; Manager authored it at
  review (2026-07-16 entry).
- Three of four Wave-1 experiment-changes had no change-time `[DECISION]` — the
  Tier-1 Firth broad→conditional re-spec, a B9 ARI object-swap, a B10 metric pick —
  and their reasoning was unrecoverable weeks later (Obs 14; led to the
  referent/rationale/supersession/consequence lock, CONVENTIONS 2026-06-22).
- The only prior statement on the W₂ banks' sequence vintage lived buried inside a
  §4-clustering-titled B9 entry, never surfaced to `SUPERSEDED.md` — which is why
  Spike Set B could not find it (Obs 57; 2026-07-12 `[DECISION]` discoverability
  fix).
- A result file's self-description contradicted its payload
  (`stability_se_2026-05-16.json` declared `stability_stored` canonical but
  computed `stability_from_seqs` — Obs 15; fixed by the relational-assertion lock).

**Countermeasure in place.** The prefix→file mapping, APM_RULES vault-discipline
section, `commit-log`/`vault-sync` skills, Manager review.

**Why it failed.** The record write is a trailing step with no gate behind it; a
ruling filed under the wrong title is invisible to keyword search at the point of
need; nothing checked descriptor-vs-payload consistency.

**ARS invariants.**
- **I8a.** Task/workflow closure requires a record artifact (typed: result/
  decision/negative/pipeline) validated for the required fields — referent (exact
  object computed), rationale, supersession (old→new + do-not-cite marker),
  consequence — before the closure event is accepted.
- **I8b.** Supersession/vintage rulings about artifact X must be written to X's
  authoritative manifest (machine-checked: the ruling's referent path must appear
  in the manifest updated in the same change-set), not only to a narrative log.
- **I8c.** A result artifact carrying a selector field (`use_*`, `estimand`,
  `metric`, `comparison`) must carry a `computed_on` witness equal to the selector,
  asserted by its admission schema (the 2026-06-22 lock, made an ARS admission
  predicate).

---

## Class 9 — Stale-state assertions across sessions (new; not in the minimum list)

**What happened.** Sessions asserted workflow state from stale snapshots — a prior
prompt, a local ref, an earlier draft — without checking the live state.

**Instances.**
- Manager 13 filed a "dispatch WT-1" recommendation while WT-1 had already run and
  merged (PR #85) — caught same-session on-disk (2026-07-12 entry correction;
  Obs 58).
- A Manager asserted a merge blocker from a stale local `main` without checking
  `origin/main` (2026-07-15 entry, listed among the silent-failure family).
- A handoff's inherited "blocker" shaped a plan after the blocker had dissolved
  (Obs 70).
- At the audited commit, P01-B Table 2's footnote § ("BCa … pending") is stale:
  the interval it declares pending exists on `main`
  (`w2_gap_closure_phase1_2026-07-16.json`, BCa [2.1646, 2.1832]) — prose written
  against the pre-#117 state with no re-validation trigger (also Class 3/I3c).

**Why the existing countermeasures failed.** "Check the live state" was an
instruction; the state snapshot travels inside prompts and drafts, which nothing
expires.

**ARS invariants.**
- **I9a.** Workflow-state claims consumed by a decision (blocked-by, not-yet-run,
  absent-on-main) must be resolved from the live system of record at decision time
  by the workflow runtime; a decision record citing a state claim without a
  resolution timestamp/witness is rejected.
- **I9b.** Deliverable-embedded state assertions ("pending", "in progress",
  "not yet derived") are bindings under I3a with an expiry: they re-validate on
  every assembly/citation event, so a restored artifact flips the assertion to
  stale automatically.

---

## Class 10 — Cross-document divergence on shared objects (new; not in the minimum list)

**What happened.** Two documents (or two sections) describe the same locked object
incompatibly; each was individually reviewed, and nothing compared them.

**Instances at the audited commit.**
- **Permutation p-value formula:** P01-B §3.3 carries the locked form
  (denominator = null draws); P01-A `methods-w2-formal-definition.md` and §S0.8
  assert the `1 + N_pairs` denominator as "the locked formula" — a direct
  contradiction on a contract-locked object, across two papers that share
  `papers/shared/notation.md` precisely to prevent this.
- **Markov-2 evidence:** P01-B §4.2 holds the Markov-2 cells as "unaudited;
  non-inferential" while §3.2 of the same paper quotes the same source's W₂
  p-values as empirically motivating α = 1.
- **Landscape availability for Markov-2:** §4.2's footnote says the α-sweep
  "computes W₂ only" (confirmed against the artifact) while the 2026-07-17
  pre-registration states certified Markov-2 landscape values are "already in
  hand" — one of the two is wrong, and the certified-landscape source is not
  locatable on `main` (open hole; see the companion snapshot).
- **Dual-metric rejection counting:** P01-A §6.1 counts BHPS 1940s as a rejection
  (W₂ p_adj 0.016; landscape 0.148) while P01-B Table 3 marks the analogous
  landscape-incomplete rows non-headline.
- **H₀-vs-GMM ARI:** the §4.6 working file removes the H₀-vs-GMM material as a
  different object; `methods-h0-orthogonality.md` builds two paragraphs on
  ARI = 0.00004 for exactly that comparison.

**Why the existing countermeasures failed.** `notation.md` and `/notation-check`
cover symbols, not semantic content; review was per-file; no check reads two
documents against one locked object.

**ARS invariants.**
- **I10a.** Locked methodological objects (p-value formula, metric definitions,
  smoothing constants, correction procedures) are registry entries; every document
  binding to such an object (I3a) must bind to the registry version, and a
  deliverable asserting a formula/value differing from its bound registry entry is
  rejected.
- **I10b.** Assembly of any paper re-validates all bindings to shared registry
  objects across *both* papers; a divergence between two live documents on one
  registry object blocks both until reconciled.

---

## Class 11 — Result artifacts and prose interleaved in the wrong tree (minor)

**What happened.** `table1_effects_2026-05-22.{json,md}` and
`compute_table1_effects.py` live under `papers/P01-A-JRSSA/drafts/sections/` —
computational results inside the papers tree, contra the papers rule ("results go
in `results/`, never in `papers/`"), which also exempted them from every
results-tree gate (no-overwrite hook, gate-4 globs, SUPERSEDED tracking by path).

**ARS invariant.**
- **I11a.** Document-class trees are typed: a manuscript workspace rejects
  artifacts of result/computation classes at admission; result artifacts are
  admissible only in the results store where the validation scopes (I2c) and
  supersession manifests operate.

---

## Cross-cutting synthesis

Three mechanisms generate nearly every instance above:

1. **Self-attestation** — the party producing the artifact also attests the
   property (register self-check, "hooks ran clean", envelope-described worktrees,
   convention gates comparing a value to itself). *ARS rule of thumb: no property
   of a deliverable is established by the agent that produced it.*
2. **Silent absence** — the failure state produces no signal (dead hooks, skipped
   files, invariant nulls, absent solver stamps). *Every ARS gate needs a positive
   execution record and a demonstrated ability to fire (I2a/I2b).*
3. **No re-validation trigger** — bindings between prose and evidence, or between
   session state and repo state, were checked at most once and silently rotted as
   the record moved (supersessions, restores, reverts). *ARS bindings are live:
   supersession and publication events re-trigger validation (I3c, I9b, I10b).*

The compute lane hardened over this period precisely by converting instruction-form
rules into artifacts of these three kinds (fail-loud solvers, convention gates with
negative controls, liveness-verified hooks, sidecar manifests). The prose lane
never acquired an equivalent surface — which is the transition this document's
invariants specify.
