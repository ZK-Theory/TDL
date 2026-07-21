# Adversarial Review — 05a `lean_proof` Evidence-Class Addendum

**Date:** 2026-07-20
**Reviewed document:** `docs/plans/agentic-research-system/design/05a-lean-proof-evidence-class-addendum-2026-07-07.md` (v0.1, DRAFT `review_pending`)
**Reviewer:** Claude (Fable 5), fresh session — satisfies the independence requirement in the addendum's status line and scout plan §7 ("Adversarial review of the W5 addendum | Fable (independent session) or Opus").
**Method:** Direct-evidence review per `adversarial-design-review`. Every cited source was opened and checked: W5 v0.2 (`05-research-assurance-and-independent-review.md`), scout plan (`lean-prover-integration-scout-plan-2026-07-04.md`), S1 framing memo (`S1-framing-decision-memo-2026-07-07.md`), S2 statement document (`S2-statement-authorship-max-ari-bound-2026-07-07.md`), value assessment (`lean-integration-value-assessment-2026-07-07.md`), S3a/S3b pre-registration skeleton, the T1.23d result JSON (`results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-24.json`), `trajectory_tda/analysis/panel/fixed_margin_max_ari.py`, and the vault Computational-Log S0/S1 `[RESULT]` entries (2026-07-04).
**Independent recomputation performed:** the S2 witness table's row/column margins, its pair count (59,684,973), the greedy concentration bound (row relaxation 121,751,376; column relaxation 128,779,812; ⌊(min − 27,280)/2⌋ = 60,862,048), and the normalised bracket [0.30346238…, 0.31105252…] were all re-derived from scratch in this session and match the S2 document and the result JSON exactly. The witness table equals the JSON's `achieving_table`. The pilot's arithmetic substrate is sound.

---

## Executive verdict

**`accept_with_required_changes`**

The class design is correctly positioned: D-class/Key-A-only scoping, the statement/prover authorship split, the negative scope (§5), and the anti-anchoring stance are all faithful to W5 v0.2 and to the failure history that motivates them (the T1.23d predecessor bound *was* wrong, and no runtime check could have caught it). No finding here reverses the direction.

But the acceptance contract as written certifies **recorded properties, not performed checks**, and its drift defence covers **signatures, not the environment that gives signatures meaning**. Both are the exact self-attestation / vehicle-level patterns this project's own failure inventory identifies. One Critical and six Major findings follow; all are contract-text additions, none is architectural rework.

---

## Critical findings

### C1 — The acceptance contract admits producer-attested verification: no item requires the acceptor to re-execute anything

**Claim:** Every §3 acceptance item is phrased as a property of the evidence ("`lake build` exits 0 on the pinned toolchain **recorded in the evidence**", "`#print axioms` … shows no `sorryAx`", "axiom set ⊆ …"), and §2 defines `kernel_verdict` as "`lake build` exit status" and `axiom_audit` as "`#print axioms` output" — i.e. **records supplied inside the evidence bundle**. No clause states who executes the checks at acceptance time, or that the acceptor must re-run them against the hashed artefact bytes.

**Evidence:** 05a §2 rows `kernel_verdict`, `axiom_audit`, `artefacts` (includes producer's `build.log`, `axiom-audit.md`); §3 items 1–3 and the closing sentence "Failure of any item yields `evidence_inadmissible`". Contrast W5 §1 decision 7 ("producer-emitted pass flags and sanity targets are not proof"), W5 §14.5 ("evidence that validation ran against the exact accepted bytes"), and the WP-review precedent of 2026-07-07 (release gate certifying producer-supplied verdicts).

**Failure scenario:** The proof-loop orchestrator (a Sonnet task at low reasoning, per scout plan §7) submits an evidence bundle whose `build.log` records exit 0 and whose `axiom-audit.md` shows the clean axiom set, but the build actually failed, ran on a different toolchain, or the audit was pasted from an earlier run. Every §3 item, read literally, is satisfied by the records; the artefact is admitted as Key A evidence with a broken or unverified proof.

**Impact:** Invalid acceptance of the strongest-rated evidence class in the system. The §1 claim that the kernel is "independent of every producer and reviewer … *by construction*" is true of the kernel but **false of the evidence chain as specified** — independence only obtains if acceptance re-runs the kernel.

**Disposition:** Fix now (contract text).

**Proposed text (new §3 item 0, or a preamble sentence):**
> "Items 1–7 are established by the **accepting gate's own execution**, not by producer records: the acceptor (or its deterministic harness) rebuilds the hashed promoted artefact set with `lake build` in a clean environment on the pinned toolchain, re-runs the `sorry`/`admit` scan and `#print axioms` per promoted theorem, and re-derives the axiom set. Producer-supplied `build.log` / `axiom-audit.md` are advisory context only. The acceptance record binds the acceptor's command transcript and the artefact hashes it ran against (W5 §14.5)."

**Affected:** §2 field semantics (`kernel_verdict`, `axiom_audit` become acceptor-produced), §3 items 1–3, 6–7; W6 fixture obligations (see M6); the S2 pilot's §5 contract instantiation.

---

## Major findings

### M1 — The drift defence covers theorem signatures but not the definitions, notation, or macros they elaborate against; a prover-authored statement can pass a byte-identical signature diff (answers review question 1: **yes, the §3.8 defence as written is defeatable**)

**Claim:** §2 `statement_hash` hashes "the exact promoted `theorem` signatures as built" and §3.8 diffs "the promoted signatures" against `statement_source`. But a Lean signature's meaning is a function of every definition, instance, notation, and macro in scope. §4 restricts the prover to "proof terms and auxiliary private lemmas only" — it says nothing about auxiliary *definitions*, `notation`/`macro` declarations, or instance declarations, and no machine check enforces even the lemmas-only rule.

**Evidence:** 05a §2 (`statement_hash` row), §3.8, §4 bullet 2. In the S2 pilot the load-bearing objects `greedyFill`, `omCounts`, `gmmCounts`, `b9Table` are **definitions**, authored in the statement document (S2 §3) — the signatures of T1–T4 are meaningless without them. The addendum's contract never requires those definitions to be inside the diff scope.

**Failure scenario:** The prover supplies an auxiliary file defining its own `greedyFill` (say, `max` instead of `min` in the recursion, making T1 trivially provable), or a `notation` that re-binds a symbol used in the signature. The promoted signature text is byte-identical to `statement_source`; the textual diff passes; every machine check passes; the theorem proved is not the theorem authored. A compliant-by-the-letter §3.8 review misses it because the contract scopes the review to signatures.

**Impact:** Defeats the single control the addendum names as the defence against its own top-ranked risk ("proving the wrong statement"). Requires reviewer initiative beyond the contract to catch.

**Disposition:** Fix now (contract text).

**Proposed change:** (a) Extend §3.8: the diff covers **the full promoted statement environment** — every `def`, `notation`, `macro`, `instance`, and `abbrev` transitively referenced by a promoted signature must originate either in the pinned mathlib commit or in `statement_source`, byte-diffed; promoted files may contain, beyond these, only `theorem`/`example` declarations and their proof bodies, and a machine check (a declaration-kind scan of the promoted files) enforces this. (b) Define the `statement_hash` extraction procedure — currently unspecified, hence untestable: hash the **elaborated type** of each promoted theorem (e.g. `#check`/`#print` output in a controlled environment importing only mathlib + statement-source definitions), not source text, so notation capture cannot produce a false textual match. (c) In §4, change "auxiliary private lemmas only" to "auxiliary private lemmas only; auxiliary definitions, notation, macros, and instances are statement-side objects and follow the proposal-return loop".

**Affected:** §2, §3.8, §4; S2 §5 item 5.

### M2 — The contract's only Key B item verifies promoted-equals-authored, not authored-equals-needed; at R2 the statement author can self-define the bar unreviewed

**Claim:** §1 promises that the statement-referent question — "*does the formal statement say what the promoted claim needs?*" — is a blocking Key B obligation. But the contract's sole Key B item (§3.8) is a **drift diff** against `statement_source`. Nothing in §3 requires anyone to review the *adequacy* of `statement_source` itself, and §3.8/§4 require the reviewer to be independent of the **prover** only — for R2, independence from the **statement author** is explicitly not required (§4: "must *additionally* be independent of the statement author's session **for R3 work**"). So at R2 the statement author may author the statement, the referent note, and then perform the diff review of their own authored objects.

**Evidence:** 05a §1 bullet 2, §3.8, §4 bullet 3. Contrast W5 §6.2/§11.1 (the bar-setter must be producer-independent — self-*definition* of the bar is the guarded object) and the W4/W5 review history (the 2026-06-30 round's deepest finding was exactly an unguarded bar-seeding requirement). Note the S2 pilot is **stricter than the class contract**: S2's header mandates an independent statement reviewer ("Stephen, or a fresh Fable/Opus session — NOT this session's continuation") with no R2/R3 qualifier. The pilot's discipline should be the class rule, not a per-document courtesy.

**Failure scenario:** An R2 instance: a Claude session authors a subtly-wrong statement (quantifier scoped to the wrong object; a hypothesis stronger than the artefact satisfies), authors the referent note that papers over it, and reviews its own diff. All machine checks pass; kernel-perfect proof of the wrong statement is admitted, which is the precise failure §1 promises W5 prevents.

**Impact:** The foundational bypass (self-definition of the acceptance bar) survives in the R2 tier, which will be the *common* tier for this class.

**Disposition:** Fix now (contract text).

**Proposed change:** Add a §3 item: "**Referent adequacy (Key B, blocking):** a reviewer independent of both the prover **and the statement author** (session-level at minimum for R2; I2 + Stephen for R3/P-005) reviews `statement_source` against the promoted claim and the referent note *before proof search begins* (matching the S2 precedent), and re-confirms at evidence review. The §3.8 drift diff does not discharge this item." Amend §4 bullet 3 to drop the R3-only qualifier on author-independence.

**Affected:** §1, §3 (new item), §3.8, §4; consistency with S2 header.

### M3 — The "constants derived, not asserted" rule is unenforceable for inequality-shaped statements: a loose-but-wrong recorded constant is never detected, and the "finding against the artefact" channel has no record type (answers review question 5: **no, §3.5 does not handle it**)

**Claim:** §3.5 requires every artefact-bound constant to be "derived in-proof by computation" with a mismatch "submitted as a finding against the artefact". Two failures: (a) for an upper-bound theorem (`… ≤ 60862048`), the proof only ever establishes the inequality — if the artefact's recorded constant is *loose* because of an upstream bug (recorded 61,000,000; true greedy value 60,862,048), the proof succeeds, no exact value is ever computed or compared, and the mismatch path never fires; (b) when a mismatch *is* detected, §3's only defined outcome is `evidence_inadmissible` — there is no defined record type, routing, or staleness consequence for the artefact under challenge, so the "finding" evaporates (silent-absence pattern).

**Evidence:** 05a §3.5, §3 closing sentence; W5 §13.2. S2 partially closes (a) for the pilot by hand: the witness count is pinned with an equality (`example : … = 59684973 := by decide`, S2 §3 W) and the proof shape prescribes "in-kernel evaluation of the greedy value" — but the class contract does not require the equality form, so nothing generalises this.

**Failure scenario:** A future certificate JSON records a bound inflated by an implementation bug. The statement author copies the recorded constant (per §3.5's own instruction that statement constants mirror artefact values). Leanstral proves the loose bound easily; kernel accepts; the wrong recorded constant is now *reinforced* by a kernel-verified artefact — the exact anchoring inversion §13.2 exists to prevent.

**Impact:** The class's flagship guarantee for its pilot use-case (certified brackets) silently degrades to "certified ≥/≤ of whatever was recorded".

**Disposition:** Fix now (contract text).

**Proposed change:** Replace §3.5's derivation clause with: "for every artefact-bound constant, the promoted set includes a kernel-checked **equality evaluation** of the derived quantity (e.g. `example : greedyValue margins = 60862048 := by decide`), and the acceptance record states the comparison outcome against the artefact's recorded value. A strict-inequality-only derivation does not satisfy this item." For (b): "a detected mismatch produces, in addition to `evidence_inadmissible`, a **discrepancy record** (W2 event referencing the artefact ID/hash and the derived value) that stales the artefact's acceptance for consumers of the affected field, per W5 §18/§19."

**Affected:** §3.5; W2 record binding (see m3); S2 §5 item 4 (make its equality-evaluation practice normative).

### M4 — The prover is an external metered API, not a local model; the evidence basis inherits the falsified "local" premise and the contract declares no prover data-exposure boundary

**Claim:** The addendum's evidence basis cites "S0 smoke test PASS (2026-07-04)" and the value assessment. The vault S0 `[RESULT]` entry (Computational-Log, 2026-07-04) records: "**Leanstral requires Mistral API key + Labs model enablement (not a local model, despite phrasing in scout plan)**". The scout plan (§1 "locally installed specialist model", §2.3 "zero API tokens", §2.2 "run locally") and the value assessment (§5 "proof search is local Leanstral") state the opposite; neither was corrected. The addendum's §2 `prover_identity` field discloses *who* the prover is, but no field or rule declares *what the prover was shown* — and with an external API, every statement file, referent note, witness table, and error trace sent during proof search leaves the machine to a third party.

**Evidence:** vault `04-Methods/Computational-Log.md` S0 entry ("Configuration learned" bullet 1); scout plan §§1, 2.2–2.3; value assessment §5; 05a header "Evidence basis" + §2 `prover_identity` + §6 pack placement ("`TDL_private` … for referent-bearing instances"). W5 §24 requires packs to declare distribution scope, permitted consumers, and "any path/data restrictions".

**Failure scenario:** A TDL_private referent-bearing instance embeds a non-vacuity witness "on the real referent data" (§3.6). The proof loop ships that data to the Mistral API across dozens of iterations. Nothing in the evidence record or the pack registers the exposure; an audit cannot reconstruct what restricted-adjacent content left the boundary. (For the S2 pilot specifically the exposure is benign — cluster-size margins and an aggregate contingency table are heavily minimized aggregates — but the *class* rule must not rely on the pilot's benignity.)

**Impact:** (a) Evidence-fidelity: the addendum's cited basis contains a corrected-in-vault-but-not-in-source factual error — Lane 1 requires the addendum not to inherit it silently. (b) A missing privacy/data-boundary control on the strongest evidence class, in a system whose W5 §24 obligations are explicit. (c) The token-economics framing ("zero metered cost") in the cited basis is stale; Mistral Labs API calls are metered, even if cheap.

**Disposition:** Fix now (addendum) + propose dated corrections upstream (owner action; do not rewrite the dated scout plan/value assessment — per currency rules, a one-line dated erratum in each, or a pointer to the S0 vault entry).

**Proposed change:** Add a §2 field `prover_data_exposure`: "enumeration of the content classes the prover could observe during proof search (statement file, referent note, witness data, artefact excerpts, error traces) and the provider boundary they crossed. For `TDL_private` instances the pack must either restrict exposure to minimized aggregates or record explicit approval per W5 §24." Add one sentence to §4: "Where the prover is an external provider, proof search is a data-boundary crossing; the exposure declaration is part of the evidence."

**Affected:** §2, §4, §6; scout plan §§1–2.3 and value assessment §5 (proposed errata, owner's call).

### M5 — Witness and mutation obligations have no required author, and §3.6's "where feasible" is an unrecorded escape hatch (partially answers review question 2)

**Claim:** §3.7 requires "at least one deliberately false variant … refuted in-kernel" but never says who authors it. If the prover (or the proof-loop orchestrator) authors the mutation, it can select a variant that is trivially refutable while orthogonal to the encoding's actual weakness — producer-defined falsification bar. §3.6 requires the witness "on the real referent data where feasible" with no obligation to record who judged feasibility or why, and no fallback requirement.

**Evidence:** 05a §3.6–3.7, §2 `witnesses` row. The S2 precedent again does it right: both W and M are authored in the statement document (S2 §3), fixed before proof search. The class contract does not require this.

**Failure scenario:** For a statement family where the honest mutation (bound tightened past the witness) is hard to refute, the orchestrator substitutes an easy mutation (e.g. margins perturbed so hypotheses contradict), which refutes vacuously via the hypothesis contradiction — the §3.7 checkbox passes while the encoding's falsifiability is untested. Separately, a witness on synthetic degenerate data disjoint from the referent satisfies §3.6's letter whenever "feasible" is quietly judged false.

**Impact:** The two vacuity/encoding guards — the addendum's own §13.3-in-formal-clothing — become producer-controlled.

**Disposition:** Fix now (contract text).

**Proposed change:** In §3.6–3.7: "Witness and mutation obligations are fixed in `statement_source` by the statement author (or enter through the §4 proposal-return loop); prover-substituted variants are drift under §3.8. Where the real-referent witness is judged infeasible, the evidence records the judging authority and rationale, and the referent note states what the substitute witness does and does not establish."

**Affected:** §2 `witnesses`, §3.6, §3.7, §4.

### M6 — A new evidence class with zero W6 fixture obligations: every §3 invariant currently has no test

**Claim:** W5 §22 obliges packs to supply "pack-specific counterexamples, degenerate mutations, benchmarks, and Partial/negative/claim cases", and the accepted pattern (addendum 06b) is to *reserve* fixture designs at spec time even when materialization is gated. 05a defers W6 materialization (§6, correctly) but reserves nothing and enumerates no fixture obligations. The consistency matrix below shows every §3 item currently maps to "no test".

**Evidence:** 05a §6; W5 §22; `06b-w4-w5-routing-assurance-fixture-addendum-2026-06-30.md` precedent (F-031–F-038 reserved at spec time).

**Failure scenario:** The class reaches first real use with no negative controls; the C1/M1/M3 failure modes above are exactly the ones a fixture battery would have to demonstrate can *fail* (a forged `build.log`, a notation-captured signature, a loose constant) — per the project's own gate-liveness principle, a gate that has never been watched to fail is an open GATE observation, not an assurance.

**Impact:** Untestable interface; violates the invariant→enforcement→test closure the review ladder requires.

**Disposition:** Fix now (add a fixture-obligation table to the addendum; IDs reserved at the next W6 reservation gate — do not mint IDs in the addendum itself).

**Proposed fixture obligations (one row per §3 item, negative case first):** forged/absent kernel verdict rejected; `sorry`-bearing promoted file rejected; disallowed axiom rejected; `native_decide` rejected absent approval; loose-constant equality-evaluation mismatch surfaced; unsatisfiable-hypotheses statement rejected for missing witness; unrefutable mutation family rejected; textual-identical/semantically-drifted signature (notation capture) rejected; prover-authored definition in promoted file rejected; pack wording counting `lean_proof` toward Key B rejected (review question 3's case).

**Affected:** §3 (all items), §6, W6 interface.

---

## Minor findings and editorial corrections

- **m1 (miscitation of grade authority).** §3.8 cites "≥ I1 for R2; I2 + Stephen for R3/P-005 per W5 §6.2/§11.1". Those sections set grades for **requirement-scope review** (floor/lane-scope acceptance), not evidence-stage review; evidence-review grades are requirement-bound via W5 §16/§17.2. The chosen grades are sensible — state them as this addendum's own requirement ("this class requires…") rather than as a W5 §6.2 mandate. Fix now.
- **m2 (cross-document divergence on hammer proofs).** 05a §3.4 accepts opaque hammer output whenever kernel-checked; the S3a/S3b prereg §8 item 4 forbids "opaque hammer-only proof unless the proof is short and auditable". §8.2's "cannot override a stronger pre-registration" resolves precedence, but the addendum's blanket prose invites misuse in instances (like S2) whose contract instantiation doesn't restate the restriction. Add a cross-reference: "a governing pre-registration may impose stricter proof-style rules; they control."
- **m3 (missing object envelope and W2 binding).** The §2 record defines domain fields but not the W5 §6.1 mandatory envelope (identity `aev_…`, revision, content hash, owner, review state, supersession lineage, currency triggers) nor which W2 record type carries it. One sentence ("a `lean_proof` record is an `assurance_evidence` object under W5 §6.1/W2 with the following class-specific fields") closes it. Also bind artefact **repository identity + commit** in `artefacts` — the Lean project lives outside TDL (`F:\Projects\lean\TDA`, per the S1 vault entry; no `lean-tda-spikes/` exists in this repo), so file hashes without a repo/commit anchor have no durable resolution path. Fix now.
- **m4 (vacuity scope narrowing).** §3.6 keys the witness on "every promoted theorem **with hypotheses**". A `∀ x : T, P x` over an empty/degenerate `T` is vacuous with no grammatical hypotheses. Rephrase: "with hypotheses or quantification over a possibly-empty domain, a kernel-checked `example` exhibits an inhabitant/instance…". Fix now.
- **m5 (pilot promotion wording).** §6: "on kernel acceptance it becomes the seed fixture for W6 and the capability evidence for the future W4 `lean-prover` role profile". Kernel acceptance is Key A only; seeding capability evidence from an artefact whose Key B review may be incomplete contradicts §1, and the same paragraph defers W6/W4 work behind their own gates. Reword: "on **full two-key acceptance** it becomes a *candidate* seed fixture and *candidate* capability evidence, consumed only when those gates open." Fix now.
- **m6 (self-undermining parenthetical).** §3.4 "(it always is)" makes its own condition vacuous; if the condition can never fail, drop it or state why it is worth asserting (defence in depth against non-kernel-checked hammer paths). Editorial.
- **m7 (prereg citation scope).** §3.9 cites "prereg §9 layout"; the only prereg is the **S3a/S3b** skeleton whose §9 layout enumerates `S3a/`/`S3b/` directories only — nothing governs S2 or future instances by that citation. Cite generically: "the governing pre-registration's artefact-contract and layout sections". Fix now.
- **m8 (ephemeral S1 detail).** The S1 full catalogue lives in a session scratchpad (`s1_catalogue.md`, per the vault entry); the durable evidence is the vault summary. The addendum's §5.1 "absent per S1" is adequately supported by the vault entry and the framing memo, but future "re-check on any future survey" events should target a durably stored catalogue. Note only.

---

## Answers to the addendum's §7 review questions

1. **Prover-authored statement masquerading as re-encoding?** Yes — not through the re-encoding door §3.8 guards, but through the **environment**: prover-supplied definitions, notation, or macros give a byte-identical signature different semantics (M1). Fix: full-environment diff scope + elaborated-type hashing + declaration-kind machine check.
2. **Vacuously true theorem passing all machine checks?** Two constructions: (a) `∀` over an empty domain has no "hypotheses", escaping §3.6's trigger (m4); (b) for statements quantifying over instance data, a witness on degenerate data disjoint from the referent satisfies §3.6's letter under the unrecorded "where feasible" escape (M5). Residual risk after both fixes is carried by the referent-adequacy review (M2) — which is currently the contract's weakest point, so M2 and M5 must land together.
3. **Key B leak through pack wording?** The prohibition (§5.4, W5 §8.2) is sound but its only enforcement is pack review, and no fixture tests it. M6 reserves the "kernel-verified, therefore reviewed" fixture case.
4. **§5.1 erosion via topology-flavoured referent note?** Possible; the binding object is the referent note, which the statement author writes. Defences after this review: the M2 adequacy review plus a field-level hardening — make §5.1's final sentence a **required `referent_note` element** ("for any instance attached to a topology-lane obligation, the note must enumerate the lane obligations *not* discharged"), so omission is machine-detectable rather than prose.
5. **Loosely-stated claim surviving a wrong recorded constant?** Yes, as written — the inequality-shaped proof never computes the exact value, so the mismatch path never fires (M3). Fixed by the equality-evaluation obligation.

---

## Consistency matrix (invariant → enforcement → test)

| # | Invariant (05a) | Enforcement point as written | Test | Status |
|---|---|---|---|---|
| §3.1 | Kernel accepts on pinned toolchain | Producer-recorded `kernel_verdict` | none | **C1**: acceptor must re-execute; fixture per M6 |
| §3.2 | No `sorry`/`admit`/`sorryAx` | grep + `#print axioms` (executor unspecified) | none | C1 executor fix; fixture per M6 |
| §3.3 | Axiom set ⊆ standard three | `#print axioms` (executor unspecified) | none | C1 executor fix; fixture per M6 |
| §3.4 | No `native_decide`/FFI without approval | unstated scan | none | Fold into C1's declaration scan; fixture per M6 |
| §3.5 | Constants derived, mismatch = finding | in-proof derivation (shape unspecified) | none | **M3**: equality-evaluation + discrepancy record; fixture per M6 |
| §3.6 | Non-vacuity witness | kernel-checked `example` | none | m4 scope fix; M5 authorship; fixture per M6 |
| §3.7 | Mutation refuted in-kernel | kernel-checked refutation | none | M5 authorship; fixture per M6 |
| §3.8 | No signature drift | reviewer diff vs `statement_source` | none | **M1** scope + hash procedure; **M2** adequacy review; fixture per M6 |
| §3.9 | Scratch separation | prereg layout citation | none | m7 citation fix |
| §4 | Statement/prover split | actor-relationship evidence (W4) | none | M1 (definitions), M2 (R2 reviewer independence) |
| §5.1–5.4 | Negative scope | pack review | none | RQ3/RQ4 fixtures per M6; referent-note field hardening |

Dimensional consistency: all constants in the pilot chain were re-derived and match (see header); no unit/tokenizer-mismatch issues arise in this addendum.

## Decision audit

| Decision / element | Disposition |
|---|---|
| §1 D-class-only scoping | **Keep** — faithful to W5 §12 |
| §1 Key-A-only, statement-referent as Key B | **Keep**, with M2 making the Key B promise enforceable |
| §1 pack-constraint restatement | **Keep** — matches W5 §8.2 (wording "risk floors" ≈ W5's "risk/independence evidence"; no material drift) |
| §2 evidence-record fields | **Amend** — C1 (verdict provenance), M1 (hash procedure), M4 (`prover_data_exposure`), m3 (envelope/W2/repo binding) |
| §3 items 1–4 | **Amend** — C1 executor; m6 editorial |
| §3.5 | **Amend** — M3 |
| §3.6–3.7 | **Amend** — M5, m4 |
| §3.8 | **Amend** — M1, M2, m1 |
| §3.9 | **Keep** with m7 citation fix |
| §4 authorship split | **Keep**, amend per M1/M2/M4 |
| §5 negative scope (all four items) | **Keep** — the strongest section of the document; add RQ4 field hardening |
| §6 pilot / pack placement / deferrals | **Keep**, amend per m5; `template_safe` class-definition claim verified (the addendum text itself contains no data or private paths) |
| Owner-approved upstream decisions (scout plan scope, S1 framing = B, S2-as-pilot) | **Not challenged** — no contrary evidence; the S1 framing memo's mathlib-gap findings are consistent with the vault S1 entry |

## Coverage and fixture gaps

Entirely covered by M6 — the addendum currently reserves no fixtures. The ten proposed obligations there are the minimum negative-control set.

## Practicality assessment

The contract is proportionate. Items 1–7 are cheap deterministic operations (a rebuild, two scans, an axiom print, small `decide` evaluations); the C1 fix adds one clean-environment rebuild per acceptance, which for statements of this class is minutes. The expensive controls (statement authorship, adequacy review) sit exactly at the highest-risk step, consistent with the scout plan's routing table. The one bypass-pressure point is §3.8's "drift of any kind stales the review" colliding with mathlib idiom churn; S2's "encoding freedom … provided the final signatures come back through re-review" is the right valve and should be referenced from the addendum so instances don't invent looser ones. No finding recommends removing any control.

## Revision plan

**Immediate corrections (author, before acceptance):** C1, M1, M2, M3, M5, M6 contract text; m1, m3, m4, m5, m6, m7 line edits; M4's `prover_data_exposure` field.

**Owner decisions (Stephen):** (a) accept the amended addendum; (b) approve one-line dated errata to the scout plan §§1–2.3 and value assessment §5 correcting the "local model / zero API tokens" premise against the S0 vault record (currency rule: erratum, not rewrite — both are dated snapshots); (c) confirm the R2 statement-reviewer independence rule (M2) as the class standard, since it slightly raises the review cost of every future R2 instance; (d) decide whether the S2 pilot proceeds under the amended contract before or after formal re-acceptance of the addendum (the pilot's own document already meets the stricter rules, so it need not block).

**Later-work dependencies (unchanged gates):** W6 fixture materialization consumes the M6 table at its own gate; W4 `lean-prover` role profile consumes M4's exposure field; W7 `vibe` adapter spec must surface the C1 acceptor-side execution hooks.

## Residual risks

- The referent-adequacy question (authored == needed) is irreducibly Key B; after M2 it is reviewed, not proven. A correlated statement-author/reviewer error remains possible at R2 (single model family); the R3 cross-family rule is the ceiling the system offers.
- The kernel and toolchain are trusted (standard for the field); toolchain pinning covers version identity, not a compromised toolchain distribution. Accepted risk, not worth a control at this scale.
- The S2 arithmetic verified here confirms the *statement document*; the eventual Lean artefact remains subject to the full (amended) contract.

## Change log

- Created this report. **No other file was created or modified**; the reviewed addendum, its cited sources, and the working tree's pre-existing modifications (`.claude/CLAUDE.md`, `.repowise-workspace.yaml`, `uv.lock` — unrelated to this review) are untouched.
- Verification evidence for the independent recomputations is quoted in the header (all reproduced exactly; commands run in-session against the committed JSON and the S2 text).
