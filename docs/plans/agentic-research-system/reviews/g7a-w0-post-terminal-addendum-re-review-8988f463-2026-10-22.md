---
document: G7-A focused independent re-review (revision 2)
date: 2026-10-22
subject: transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md
subject_commit: 8988f463
subject_blob: 9b159e87f1275ff38203cc5e5f8a8a5b4af8f38e
reconciliation_record: reviews/g7a-w0-post-terminal-addendum-reconciliation-2026-10-22.md (same commit)
prior_review: reviews/g7a-w0-post-terminal-addendum-delta-review-77388ec9-2026-10-22.md (committed 73d73357)
verified_against: origin/main 3fa437a160ab75c5fa0083fd35176006b1ee19a4
verdict: REWORK REQUIRED (narrow)
reviewer: the same independent session that wrote the prior review (distinct from the author session)
implementation_authority: none
---

# G7-A re-review: revision 2 (8988f463)

## 1. Subject and basis

| Item | Value |
|---|---|
| File | `docs/plans/agentic-research-system/transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md` |
| Commit | `8988f463` (read with `git show 8988f463:<path>`) |
| Blob | `9b159e87f1275ff38203cc5e5f8a8a5b4af8f38e` (36,086 bytes) |
| Verified against | origin/main `3fa437a1`. After `git fetch origin` on 2026-10-22, origin/main has not moved. |
| Scope | As set by the prior review's §8.4: the six Majors, the minors' closure, and what is new in revision 2. New identities are verified. Unchanged identities were checked in the prior review and are not re-run. |

## 2. Verdict

**REWORK REQUIRED (narrow).** Revision 2 fixes most of what the first review found. M1, M2, M4, M5 and M6 are closed,
as are all twelve minors and the five infos. The #215 round-trip claim is correct in substance: every rewritten blob is
restored. The T1.3 class change follows from its evidence.

Two Majors remain. Both are text fixes and need no new analysis from the author:

- **R1, the residual of M3.** The A-001 list in §10 ends with "No Stage 1 computational or assurance requirement
  exists other than those listed above." That sentence is still false at `3fa437a1`. The list omits:
  - review finding A4, a class A finding with a compute action;
  - hole H9;
  - any remediation for T1.8's W₂ α-stability conclusion, which §6.1 itself now classes `unverified`.
- **R2, new.** The T1.20 note in §6.1 surfaces a conflict between two governing records, and the addendum does not
  record it. The §4.5 NS-SEC odds ratios that the 2026-07-11 T1.20 closure "verified" exist only in a Tier 1 file
  that the claim-trace audit says not to cite. In the canonical file the same terms are non-significant.

Counts for new findings in this re-review: **Blocking 0 · Major 2 · Minor 3 · Info 4.**

## 3. Closure of the prior findings

| Finding | Status | Evidence |
|---|---|---|
| **M1** §5.2 classes left standing | **Closed** | §6.1 has a row for every manifest §5.2 row. The rows are T1.1, T1.2/2a–f, T1.2g+T1.7, T1.2h, T1.3, T1.4, T1.5, T1.6, T1.8, T1.9, T1.9b, T1.10–T1.20, T1.21, T1.22, T1.23, T1.24, T1.25, T1.26/26b, T1.27, T1.29–T1.32, T1.33, T1.34/34a, T1.35, T1.36 and T1.37. I compared them with manifest lines 128–154. The four class changes follow from their evidence: see §4.1 (T1.3) and §4.2 (T1.8, T1.26/26b, T1.37). Two notes need correction (R2, I2). §13 row 3 now reads "Open until the signatory confirms §6.1". |
| **M2** soundness record missing | **Closed** | §7 records #131 (`7cdba0d0`), which added `shared/math_invariants.py` and `tests/shared/test_math_invariants.py` (verified with `git diff --name-only`). It records #132 (`0e906ad6`) and its A1–A4, which match review §1 headings A1–A4. It records holes H1–H9 with H6 resolved by #129 (`5795a18b`). The A2 caveat on T1.28 is in §4. The dispatch bar on the Markov-2 pre-registration is in §6.2 and §17. |
| **M3** A-001 asserted an unchecked closure | **Partly closed** | The list format, the dropped `prepared` and the qualified closing sentence fix the form. The list is still incomplete, so the closing sentence is still false. See R1. |
| **M4** `SUPERSEDED.md` does not hold the boundary | **Closed** | §8 attributes the UNVERIFIABLE classification correctly. `w2_gap_closure_phase1_2026-07-16.json` has `phase1.markov2_alpha_sweep.classification = "UNVERIFIABLE"`, which I verified. §8 records line 69 as a `stale_projection` and names it as an import-time conflict for G7-B. |
| **M5** merged drafts without audit verdicts | **Closed** | The qualifiers in §9 match the audit: A24 is UNSUPPORTED/falsified, A21 struck, A19 MISDESCRIBED, A26 "MISDESCRIBED (major)" and A32 "MISDESCRIBED (consistency, minor)"; the negative-control file is "entire file invalid" and the Table 1 effects family "all cells unciteable". A-002 is restated with the audit and the HOLD. The stage-02 logs are read. See R2 for one qualifier the record does not yet carry, and I3 for a mislabelled source. |
| **M6** `deferred` for undisposed tasks | **Closed** | T2.9–T2.11 and T2.19–T2.22 are now `blocked`, with named blockers. `deferred` is kept only for T1.41 and Markov-2. §5 trigger 3 ("No; the freeze blocks them") is now consistent. |
| m1 | Closed | §8: only the integration `SUPERSEDED.md` changed. The BHPS file is unchanged since `a67ca4c7`. |
| m2 | Closed | T2.24 is `superseded` on main, and its tracker row is listed separately in §15. |
| m3 | Closed | §11 names F401 (`numpy`, `NDArray`, `typing.Dict`) and E741, and drops the F841 citation. |
| m4 | Closed, with corrections | #368 and `1af52f6d` are recorded. The new #215 entry misattributes its writer (N1), and the contracts surface is still missing (N2). |
| m5 | Closed | §3 keeps the manifest's sealing authority. The addendum's own states are added with owners. W0-D1 is widened to all eight §14 items. |
| m6 | Closed | §15 clash 4 adopts P-026 and P-034. |
| m7 | Closed | §15 clash 1 records the "active" limb as ambiguous. |
| m8 | Closed | All nine records named in the prior review are in §15's table, along with five others. |
| m9 | Closed | §6.2 says both T1.38 phases went through #105, #111 and #117. T1.40 is `unverified`, with its Partial log recorded. |
| m10 | Closed | §12 now gives "inferred from that scope". |
| m11 | Closed as an owner decision | §14 and W0-D4 propose the deviation. My opinion is in §6. |
| m12 | Closed | The §5 trigger rows cite the freeze, the 2026-07-15 pre-registration and `9ca20884`. |
| i1–i5 | Closed | Adopted as listed. `under_review` is now a value in §3's vocabulary. |

## 4. Checks the author asked for

### 4.1 T1.3, the new class change

- **The claim.** T1.3's H₁ W₂ is `unverified`, because its source
  `stratified_markov/stratified_markov1_W2_L5000_frozen_2026-05-29.json` is not classified by WT-6 and carries the date
  on which WT-6 proved a sibling file greedy.
- **Evidence:**
  - I searched the WT-6 audit JSON (`w2_fallback_audit_2026-07-14.json`) for the file. Its `audit_table` and
    `non_compute_classified` name `stratified_markov1_battery_2026-05-13.json` (H₁ SUSPECT-UNVERIFIABLE) and not the
    2026-05-29 frozen file.
  - WT-6's `era_boundary.empirical_boundary_natural_experiment` classifies
    `bhps_length_matched_truncate_frozen_2026-05-29.json` as greedy ("GREEDY — the greedy replica reproduces the
    committed value bit-for-bit"). It concludes that POT "entered the venv between 2026-05-29 and 2026-05-30".
  - Commit times bracket the T1.3 source. The greedy 2026-05-29 truncate file landed in `501312c1` (05-29 07:55).
    The T1.3 source landed in `6d209987` (05-29 18:52). The exact 2026-05-30 truncate file landed in `3a2971ba` (05-30
    17:17). So the date alone cannot place the source.
- **Content screen (additional evidence the author did not cite):**
  - The source's H₁ cells show t-ratios (ρ̂) of 0.80–1.13 in 14 of 15 regimes. The one exception is USoc R2, at 8.42.
  - Its H₁ mean obs-null distances run from 17.7 to 184.2. Several of them (for example USoc R0 at 115.6 and R2 at
    184.2) sit in the range `SUPERSEDED.md` calls "the greedy compression signature" (ρ̂ ≈ 1, H₁ means 130–306
    against an exact diagonal bound of ~20).
  - That points towards greedy. Without a per-cloud diagonal bound it is not proof, so `unverified` is the right
    conservative class.
- **Disposition: confirmed.** Info I1 settles the question the row leaves open.

### 4.2 The other three class changes

- **T1.8.** Supported. The tracker row bases T1.8 on the summary, and the summary is UNVERIFIABLE (verified, §3 M4).
  Citing the α=1 landscape cells as citable is supported by `1af52f6d`'s `SUPERSEDED.md` entry. See R1 for the
  missing remediation.
- **T1.26/26b.** Supported by the 2026-07-16 `[DECISION]` and `SUPERSEDED.md`, as the prior review established.
- **T1.37.** Supported by `a9dcccbf`'s `SUPERSEDED.md` table. The WT-6 `non_compute_classified` entry for
  `lm_sensitivity_*` reads "h0: IMMUNE; h1: SUSPECT-UNVERIFIABLE", which matches the row.

### 4.3 The T1.20 note

The note's first sentence is correct. The 2026-07-11 `[DECISION]` traces "every §4.5 parental-NS-SEC number (Tier 1 OR
0.8351/0.8949 p 0.0008/0.0466; Tier 2 1.0487/1.2324; svyglm headline 1.0954/1.1126)" to
`tier1_clustered_firth_2026-05-13.json`, `tier2_glmm_firth_2026-05-14.json` and `tier2_svyglm_headline_2026-06-03.json`.

The note's second sentence overstates. Audit §3.2's "(NOT 05-13/05-14)" is attached to `tier1_clustered_firth_*`. On
main there are Tier 1 files dated 05-13, 05-14 and 05-16, and one Tier 2 GLMM file,
`tier2_glmm_firth_2026-05-14.json`. Audit A41 cites `tier2_glmm_*` as canonical. So only the Tier 1 trace is to a
do-not-cite file. The Tier 2 05-14 file is not one.

I checked what the note left "not re-checked", with this outcome:

- **The exposure argument holds for the canonical file.** `tier1_clustered_firth_2026-05-16.json` sources
  `nssec_proxy` from "pasoc90_cc falling back to masoc90_cc", the `xwavedat` path that does not use
  `covariate_extractor.py`. So T1.20's closure (no NaN exposure) stands, and the note can say so.
- **The numbers do not hold.** The values 0.8351 and 0.8949 appear only in the 05-13 file. The 05-14 and 05-16 files
  do not contain them. The 05-16 file has `nssec_proxyM` OR 1.0455 (p_firth 0.81056) and `nssec_proxyL` OR 1.2161
  (p_firth 0.30726). It also uses a different escape definition: window-based, n_complete_case 6,173, escape rate
  0.0488. The 05-13 file has n_analytical 27,280 and escape rate 0.7172. See R2.

### 4.4 The #215 claim

Correct in substance, with one wrong identity (N1).

- `git diff -w --ignore-cr-at-eol a426b731 5df0c001 -- results/` is empty. The plain diff shows 7 files with
  373,065 insertions and 373,065 deletions, so the rewrite was line endings only.
- For each of the seven files, the blob at `3fa437a1` equals its blob just before the rewrite and, where the file
  existed then, its blob at `33ab053e`. For example, `bhps_nonoverlap_reanalysis_2026-06-09.json` goes `6137c523` →
  `435c2e0b` → `6137c523`.
- `3bfb279c` is the restoring commit. The GitHub API associates it with #219 (merged 2026-08-08T21:23Z). The net
  effect is nil, as stated.

### 4.5 The §3 state tables, W0-D1 and W0-D4

The §3 tables meet KAN-20's ask: one sequence for the series and one for the document, each state with evidence and
an owner. The manifest's sealing authority is preserved, and the change to it is routed through W0-D1 and G7-C. The
`rework_required` → `under_review` transition is implicit ("the author reconciles and resubmits"). That is
acceptable. My opinions on W0-D1 and W0-D4 are in §6.

## 5. New findings

### Major

#### R1. The A-001 list is still incomplete, so its closing sentence is still false (residual of M3)

- **Claim (§10):** eight items, then "No Stage 1 computational or assurance requirement exists other than those
  listed above."
- **Evidence:**
  1. **Review A4** (`P01-Adversarial-Mathematical-Review-2026-07-18.md` §1 A4 and the §5 priority map). The finding
     is per-cloud α_max truncation. It blocks "All witness-complex cells". The action it sets is "Pin α_max per
     cell; one-cell sensitivity triage first". That is a computational assurance requirement. §7 records A4, but §10
     omits it.
  2. **Hole H9** (audit §3.3). "ARI 0.00004 (H₀-tree-cut vs GMM) — no artifact… Re-derive with referent recorded, or
     drop the numeric anchor". §7 lists it as "Open; re-derive or drop". §10 omits it.
  3. **T1.8's W₂ α-stability conclusion.** §6.1 now classes it `unverified`. The Markov-2 recompute in item 2 is
     α=1 only (the H6 `[DECISION]` scopes it "W₂ only" at α=1). Nothing in the list re-establishes or retires the
     claim that W₂ is stable across α∈{0, 0.5, 1, 5}. Item 6 (H7) does not cover it: the summary is UNVERIFIABLE,
     meaning it has no cache to gate, so a gate cannot settle it.
  4. Lower-tier, for the signatory to scope: review B1–B7 ("Per-finding one-shot sensitivities + wording"). These may
     or may not count as requirements. The list should say which.
- **Failure:** The signatory confirms the list as complete, as §10 asks. A-001 is then confirmed while A4's triage,
  H9's re-derivation and T1.8's α-sweep question are open. That is the same failure as M3, on a smaller surface.
- **Required correction:**
  - Add three items: A4 (pinned-α_max sensitivity triage); H9 (re-derive with referent, or drop the anchor); and
    T1.8's W₂ α-stability (an exact α-sweep, or drop the claim).
  - Either add B1–B7 as one scoped item ("the signatory decides which B findings are requirements") or say why they
    are excluded.
  - Add R2's trace conflict, or route it to A-002 (see R2).
  - Keep the closing sentence only after these are added.

#### R2. Two governing records disagree on the §4.5 NS-SEC numbers, and the addendum does not record it

- **Claim (§6.1, T1.10–T1.20 row):** the note records that T1.20 traced §4.5 to non-canonical files, says the trace
  "was not repeated", and leaves the row "unchanged, with a note". §9 carries T2.1–T2.6 (§4.5 belongs to T2.4) as
  `merged_draft` "subject to the audit's per-file verdicts". For §4.5 the audit gives A41 VERIFIED\*, with
  `tier1_clustered_firth_2026-05-16.json` as canonical.
- **Evidence (§4.3 above):**
  - The 2026-07-11 `[DECISION]` says the §4.5 Tier 1 NS-SEC ORs are 0.8351 and 0.8949 (p 0.0008 and 0.0466). Those
    values exist only in `tier1_clustered_firth_2026-05-13.json`.
  - The canonical 05-16 file gives 1.0455 (p 0.81) and 1.2161 (p 0.31), under a different escape definition.
- **Failure.** One of the two records is wrong, and either way it matters:
  - If §4.5 carries 0.8351/0.8949, a merged draft states a significant protective NS-SEC effect from a do-not-cite
    file, next to a headline (Firth OR 18.5954, n 6,173) drawn from the 05-16 file. Under the canonical model that
    effect is non-significant. Audit A41's VERIFIED\* did not catch it, and no hole lists it.
  - If §4.5 carries the 05-16 values, then T1.20's "verified: every §4.5 … number traces to" sentence verified
    against the wrong file. Its exposure conclusion still stands, per §4.3 above.
  - The addendum is the record that should surface this. As written, a successor reads §4.5 as VERIFIED\*.
  - I did not read the §4.5 draft (out of bounds), so I cannot say which record is wrong.
- **Required correction:**
  - Correct the §6.1 note. Only the Tier 1 trace is to a do-not-cite file; the Tier 2 05-14 file is canonical. The
    exposure argument is confirmed for the 05-16 file (both use `nssec_proxy` from `xwavedat`).
  - Record the numeric conflict as a candidate audit hole (for example "H10, candidate"). Add it to §7's hole table
    and to the §9 qualifier for §4.5/T2.4. Its resolution is a read of §4.5 by a session permitted to read the drafts.
  - Name it in the A-001 list (R1) or in the A-002 qualifiers, and add it to §17's triggers as "a decision on H10".

### Minor

#### N1. The writer of the #215 rewrite is misidentified

- **Claim (§11):** "#215 (`5df0c001`, 2026-08-05, an ARS WP6.4 PR) rewrote seven legacy result files".
- **Evidence:**
  - GitHub records #215's merge commit as `a426b731` (2026-08-05T04:44+01:00, two parents). `git diff b21640de
    a426b731` touches no `results/`, `papers/` or `.apm/` path.
  - `5df0c001` (05:32+01:00) is a separate commit with a single parent (`a426b731`). It reuses #215's merge message.
  - The GitHub API associates `5df0c001` with no pull request. It was pushed directly to main.
  - The same is true of `811d5a2b` (2026-08-07), which also has no associated PR (N2).
- **Correction:** Use "`5df0c001`, a direct push to main with no PR, reusing #215's merge message (#215 itself merged
  as `a426b731` and touched no legacy path), rewrote seven legacy result files, line endings only; `3bfb279c` (#219)
  restored them". For G7-B's writer registry, the material fact is that a no-PR writer reached `legacy_owned` result
  paths.

#### N2. §11 omits the contracts surface

- **Claim (§11 and §14):** the delta covers "the legacy surfaces the manifest's §2.1 and §8 name". Manifest §8.1
  names "`contracts/**/*.yaml` plus binding tests" as legacy research authority, to be imported with "pending/active
  state".
- **Evidence (`git log 4b143c92..origin/main -- contracts/`):**
  - `f523b1e5`, `b18a5222`, `f5c449ad` and `73d58759` (2026-07-26, "P01-A: activate WP6.3 prerequisite contracts")
    took `null-operation-changes-ph-input` and `markov-order-provenance` from `pending: true` to active. They edited
    `monte-carlo-permutation-p-value` and `research-assurance.yaml`, and added
    `markov-order-provenance-json-validation` (applies to `results/trajectory_tda_integration/stage1/matched_w2_battery_*.json`).
  - `811d5a2b` (2026-08-07, no PR) rewrote three legacy input-provenance manifests: `t128-inputs.yaml`,
    `t138-w2-gap-closure-inputs.yaml` and `b9-om-gmm-inputs.yaml`. `3bfb279c` restored them, and
    `git diff 4b143c92 origin/main -- contracts/manifests/input-provenance/` is empty.
  - `eba3fe69` (#334) added `retired-plan-imperatives-quoted.yaml`.
- **Correction:** Add a "Contracts" bullet to §11:
  - the WP6.3 activations, which change the enforcement state of contracts the legacy results are read under;
  - the `811d5a2b`/`3bfb279c` round trip on T1.28's and T1.38's input-provenance manifests (net nil, no PR);
  - #334.

  Each goes to G7-B's registry. No class changes.

#### N3. §4's T1.28 headline omits audit A32

- **Evidence:** Audit A32 says "nine of eleven BHPS subgroups reject" counts the 1940s cohort (W₂ p_adj 0.016;
  landscape p 0.148, non-reject) as a rejection, while P01-B Table 3 treats such rows as non-headline under the
  dual-metric mandate. Verdict: "MISDESCRIBED (consistency, minor)".
- **Correction:** Add to §4: "BHPS 9/11 counts the W₂-only 1940s cohort. Under the dual-metric reading used by P01-B
  Table 3 it is 8/11 (audit A32)."

### Info

- **I1. T1.3: Outcome A rests on H₀ alone.** In the T1.3 source, `per_dataset.*.significant_regimes` equals the set of
  H₀-rejecting regimes exactly:
  - USoc: R0, R2, R3, R4, R5, R6 (6/7);
  - BHPS: R0, R2, R4, R5 (4/8);
  - every H₁-rejecting regime also rejects at H₀ (USoc R0, R2, R5; BHPS R0).

  The rule `frac_significant ≥ 0.5 in ≥1 dataset` gives Outcome A from USoc's H₀ cells alone (0.857). WT-6 holds H₀
  W₂ to be solver-immune. So §6.1's sentence "Whether Outcome A holds on its H₀ and landscape cells alone is not
  established here" can become "Outcome A holds on its H₀ W₂ cells alone (per the file's own `per_dataset`); the
  A1–A4 caveats apply". The tracker's "USoc 9/14" is 6 H₀ + 3 H₁ tests, which is a different count from the rule's
  per-regime fraction.
- **I2. T1.2g and T1.7: stronger evidence is available.** For the truncate arm, the WT-6 natural experiment verifies
  more than "the exact side". Its committed H₁ mean of 6.6314 matches an exact 12-pair subsample (6.6695), not the
  greedy one (203.22). The first13 arm rests on the day-level boundary only. The row can say so.
- **I3. §9 mislabels one source.** The list headed "Claim-trace audit verdicts" includes `methods-3-2-ladder-markov.md`
  "(review A1)". That verdict comes from the adversarial review, not the audit. Move it, or relabel the heading.
- **I4. #219.** `3bfb279c` came through #219. Cite the PR in §11 so the restorer is identified as well as the
  rewriter.

## 6. Owner decisions (reviewer opinion)

These are my opinions as reviewer. They are not dispositions.

- **W0-D1 (who signs all eight §14 items).** I agree: Stephen signs. The independent check should cover §6.1, §7 and
  §10 after R1 and R2 are fixed. I would also ask that the signatory explicitly scope the B1–B7 items (R1). The
  routing through G7-C's register entry is right.
- **W0-D2 (Stage 2 scope decision at 06l Step 3).** I agree. With M6 closed, the deferral is consistent. The fifteen
  rows are named.
- **W0-D3 (accept §3's state sequences).** Accept. Both tables meet KAN-20. The current state, `under_review`, is
  consistent with the frontmatter.
- **W0-D4 (Discovery boundary excluded, assigned to G7-B against W11).** Accept, with one condition. The 06l Step 2
  amendment that G7-C carries should state that no Discovery item may take a Step 3 or later action until G7-B's
  Discovery inventory is accepted. Otherwise the exclusion leaves Discovery items with no W0-level closeout record at
  the point where 06l expects one.

## 7. What revision 3 needs

1. R1: add A4, H9 and T1.8's α-stability to the §10 list, scope B1–B7, and add R2's item. Then keep the closing
   sentence.
2. R2: correct the T1.20 note; record H10 (candidate) in §7, in §9's qualifiers for §4.5, and in §17's triggers.
3. N1, N2 and N3; I1 to I4 are optional.

A re-check of §6.1's T1.20 row, §7, §9's §4.5 qualifier, §10 and §11 is enough. Nothing else needs re-review.

## 8. Limits

- **Same model family.** I ran on Claude Opus 5.5, the same model family as the author. I am also the session that
  wrote the prior review, so this re-review checks its own earlier findings for closure. The independence from the
  author is session independence only (a P-058 known limit).
- **Paper drafts.** I did not read them. R2's conflict is established between two records, the 2026-07-11
  `[DECISION]` and audit §3.2/A41, plus the committed JSONs. Which record is wrong needs a read of §4.5.
- **Not re-run.** The unchanged identities from the prior review's §4. B1–B7 were not evaluated beyond the review's
  priority map.
- **Sources read in part.** The Computational-Log at the T1.20 and 2026-07-16/18 entries only. The WT-6 audit at the
  keys cited. The T1.3 source's `per_dataset`, `fdr_tests` and H₁ blocks.
- **No edits.** I wrote only this file. I committed nothing, and I wrote nothing to `.apm/`, the vault, any ARS store
  or Jira.
