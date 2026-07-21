# 05a — W5 Addendum: `lean_proof` Evidence Class

**Date:** 2026-07-07 · **Review integrated:** 2026-07-20 · **Accepted:** 2026-07-21 (Stephen)
**Status:** ACCEPTED v0.2 — packs may reference this class. Independent adversarial review completed (`../reviews/adversarial-05a-lean-proof-evidence-class-review-2026-07-20.md`, `accept_with_required_changes`); this revision applies all author-side required changes (C1, M1–M6, m1–m7). All §9 owner decisions resolved by Stephen 2026-07-21. Implementation of the acceptor-side harness and W6 fixtures remains behind their own gates (§10).
**Specification version:** 0.2 (extends W5 v0.2 via the §8.2 domain-pack interface; changes no core lifecycle, authority, or lane semantics)
**Implementation authority:** None; this document creates no packs, contracts, adapters, role profiles, or Lean artefacts
**Evidence basis:** S0 smoke test PASS (2026-07-04) — see the correction in §8 on the "local model / zero-token" premise; S1 gap survey + framing memo (2026-07-07); S2 statement-authorship document (`docs/plans/strategy/S2-statement-authorship-max-ari-bound-2026-07-07.md`); value assessment (`docs/plans/strategy/lean-integration-value-assessment-2026-07-07.md`)

## 1. Purpose and position

This addendum defines `lean_proof` as a new **evidence class** that reviewed domain packs may attach to machine-checkable proof obligations. A `lean_proof` is a Lean 4 artefact whose acceptance is established by the Lean kernel — a deterministic, fail-closed, non-LLM verifier — **re-executed by the accepting gate** (§3 C1). The kernel is independent of every producer and reviewer by construction; that independence reaches the *evidence chain* only because acceptance re-runs the kernel rather than trusting producer-supplied logs.

A `lean_proof` record is an `assurance_evidence` object under W5 §6.1 / W2 (identity `aev_…`, revision, content hash, owner, review state, supersession lineage, currency triggers), carrying the class-specific fields of §2.

Position within W5 v0.2, unchanged semantics:

- **Claim classification (§12):** a `lean_proof` discharges **D-class** assertions only — the "independently recomputable property" column, where the re-executed kernel is the independent recomputation. It contributes nothing to T, R, M, H, O, or P classes.
- **Two-key validity (§17):** a `lean_proof` is **Key A evidence only**. The statement-referent question — *does the formal statement say what the promoted claim needs?* — is a Key B obligation split into (a) **referent adequacy** (is the authored statement what the claim needs?) and (b) **drift** (does the promoted statement equal the authored one?), both in §3. No prover output discharges either.
- **Pack constraints (§8.2):** this class cannot turn `not_applicable`, `unable_to_grade`, Partial, or a failed obligation into pass; cannot lower risk floors, independence grades, or human gates; cannot override a stronger pre-registration (a governing pre-registration may impose **stricter** proof-style rules — e.g. the S3a/S3b prereg §8.4 restriction on opaque hammer proofs — and those control; m2).

## 2. Evidence-class definition

A `lean_proof` evidence record is an `assurance_evidence` object (envelope per §1) binding these class-specific fields:

| Field | Content |
|---|---|
| `statement_source` | The independently authored statement document (ID + hash) fixing the theorem signatures **and every statement-side `def`/`notation`/`macro`/`instance`/`abbrev`** — e.g. the S2 statement document. Authored before proof search per §4 |
| `statement_hash` | Hash of the **elaborated type** of each promoted theorem (`#check`/`#print`-style output produced in a controlled environment importing only the pinned mathlib + the `statement_source` definitions), diffed against `statement_source` at review. Not a source-text hash — notation capture can make source text match while the elaborated type differs (M1) |
| `referent_note` | Plain-English statement of the empirical/paper claim the theorem licenses, the exact result artefact IDs/hashes it attaches to, and where exact arithmetic ends (e.g. float-rounding boundaries). **For any instance attached to a topology-lane obligation, the note must enumerate the lane obligations NOT discharged** (§5.1; RQ4 hardening) |
| `toolchain` | `lean-toolchain` content, mathlib commit, lake manifest hash |
| `artefacts` | Promoted `.lean` files (hashes) **plus the Lean project's repository identity + commit** (the project lives outside TDL, so file hashes without a repo/commit anchor have no durable resolution path — m3), `build.log`, `axiom-audit.md`, `result.md`; scratch files listed and excluded |
| `kernel_verdict` | The **acceptor's** `lake build` exit status from its own clean re-execution (§3 C1). Producer `build.log` is advisory context only |
| `axiom_audit` | The **acceptor's** `#print axioms` output per promoted theorem, re-run at acceptance |
| `witnesses` | Non-vacuity witnesses and mutation obligations (§3.6–3.7), authored in `statement_source` (§4), with build status |
| `prover_identity` | Provider/model of the proof author (e.g. Leanstral 1.5 via `vibe`), per W3 visibility rules |
| `prover_data_exposure` | Enumeration of the content classes the prover could observe during proof search (statement file, referent note, witness data, artefact excerpts, error traces) and the provider boundary they crossed. For `TDL_private` instances the pack must either restrict exposure to minimized aggregates or record explicit approval per W5 §24 (M4) |

## 3. Acceptance contract (all machine-checkable, fail-closed)

**Acceptor re-execution (item 0, governs items 1–7 — C1).** Items 1–7 are established by the **accepting gate's own execution**, not by producer records: the acceptor (or its deterministic harness) rebuilds the hashed promoted artefact set with `lake build` in a clean environment on the pinned toolchain, re-runs the `sorry`/`admit` scan and `#print axioms` per promoted theorem, and re-derives the axiom set. Producer-supplied `build.log` / `axiom-audit.md` are advisory only. The acceptance record binds the acceptor's command transcript and the artefact hashes it ran against (W5 §14.5).

A `lean_proof` is admissible as Key A evidence only when all of the following hold under that re-execution:

1. **Kernel:** `lake build` exits 0 on the pinned toolchain recorded in `toolchain`.
2. **No holes:** no `sorry` / `admit` in promoted files (grep) and `#print axioms` on every promoted theorem shows no `sorryAx`.
3. **Axiom audit:** axiom set ⊆ {`propext`, `Classical.choice`, `Quot.sound`}. Any classical-choice use is noted in `result.md`. New axioms are prohibited.
4. **Trusted-computing base:** `native_decide` and `extern`/FFI-backed evaluation are prohibited unless the requirement explicitly approves them with rationale (they extend trust beyond the kernel to the compiler). A declaration-kind scan (see item 8) also catches this; and item 3 catches it downstream (`native_decide` introduces `Lean.ofReduceBool`, failing the ⊆-check). Defence in depth against non-kernel-checked evaluation.
5. **Constants pinned by equality, not merely bounded (M3):** for every artefact-bound constant, the promoted set includes a kernel-checked **equality evaluation** of the derived quantity (e.g. `example : greedyValue margins = 60862048 := by decide`), and the acceptance record states the comparison outcome against the artefact's recorded value. A strict-inequality-only derivation does not satisfy this item — an inequality proof succeeds for any recorded constant on the slack side and never detects an inflated/loose recorded value. A detected mismatch produces, in addition to `evidence_inadmissible`, a **discrepancy record** (W2 event referencing the artefact ID/hash and the derived value) that stales the artefact's acceptance for consumers of the affected field, per W5 §18/§19 — the finding does not evaporate.
6. **Non-vacuity witness:** for every promoted theorem **with hypotheses or quantification over a possibly-empty domain**, a kernel-checked `example` exhibits an inhabitant/instance satisfying them — on the real referent data where feasible. A theorem whose hypotheses are unsatisfiable, or whose universal is vacuous over an empty domain, proves nothing about the claim (W5 §13.3 in formal clothing).
7. **Mutation obligation:** at least one deliberately false variant (e.g. the bound tightened past a known witness) is *refuted* in-kernel, demonstrating the encoding is falsifiable. A statement family in which the false variant cannot be refuted fails the contract.
8. **Full-environment drift check (Key B(b), blocking — M1):** the diff of §3.8 covers **the full promoted statement environment**. Every `def`, `notation`, `macro`, `instance`, and `abbrev` transitively referenced by a promoted signature must originate either in the pinned mathlib commit or in `statement_source`, byte-diffed by elaborated type. Promoted files may contain, beyond these, only `theorem`/`example` declarations and their proof bodies; a declaration-kind scan of the promoted files mechanically enforces this. Signature drift of any kind — including "equivalent" re-encodings and prover-supplied auxiliary definitions/notation — stales the review.
9. **Referent adequacy (Key B(a), blocking — M2):** a reviewer independent of both the prover **and the statement author** (session-level at minimum for R2; I2 + Stephen for R3/P-005) reviews `statement_source` against the promoted claim and the `referent_note` *before proof search begins*, and re-confirms at evidence review. The drift check (item 8) does **not** discharge this item — it verifies promoted-equals-authored, never authored-equals-needed. (Grade rationale: this class *requires* these grades; it does not inherit them from W5 §6.2/§11.1, which set grades for requirement-scope review — m1.)
10. **Scratch separation:** exploratory files are excluded from the promoted set and from the evidence hashes (governing pre-registration's artefact-contract and layout sections — m7).

Failure of any item yields `evidence_inadmissible`; per W5 §17.3 no other evidence compensates.

### 3.1 W6 fixture obligations (reserved at spec time; IDs minted at the next W6 reservation gate — M6)

W5 §22 obliges packs to reserve fixture designs at spec time even when materialization is gated (the 06b precedent). One negative-control fixture per acceptance item, **negative case first** (a gate never watched to fail is an open observation, not an assurance):

| Item | Reserved fixture (must be shown to FAIL) |
|---|---|
| 0 / 1 | Forged or absent kernel verdict — producer `build.log` says exit 0 but acceptor rebuild fails — rejected |
| 2 | `sorry`/`admit`-bearing promoted file rejected |
| 3 | Disallowed axiom rejected |
| 4 | `native_decide` / FFI evaluation rejected absent explicit approval |
| 5 | Loose/inflated recorded constant surfaced by the equality-evaluation mismatch + discrepancy record emitted |
| 6 | Unsatisfiable-hypotheses (or empty-domain vacuous) statement rejected for missing witness |
| 7 | Mutation family whose false variant cannot be refuted rejected |
| 8 | Textually-identical but semantically-drifted signature (notation/definition capture) rejected; prover-authored definition in a promoted file rejected |
| 9 | A statement whose `statement_source` is adequate-looking but reviewed only by its own author (R2) rejected for missing independent adequacy review |
| §5.4 | Pack wording that counts `lean_proof` toward Key B ("kernel-verified, therefore reviewed") rejected |

## 4. Statement/prover authorship split (binding)

The critical risk is proving the wrong statement, not proving a statement wrongly. Therefore:

- The **statement author** (Claude judgment model or Stephen) fixes theorem signatures, **all statement-side definitions/notation/macros/instances**, the `referent_note`, and the non-vacuity witness and mutation obligations (§3.6–3.7) *before* proof search, in a version-controlled statement document.
- The **prover** (Leanstral or any successor) supplies proof terms and auxiliary *private lemmas* only. It may *propose* a signature or definition change; the proposal returns to the statement author and re-review — it is never self-applied. Prover-substituted witnesses, mutations, definitions, notation, or instances are drift under §3 item 8.
- The statement author and the prover must be distinct actors under W4's relationship evidence. The **referent-adequacy reviewer** (item 9) must be independent of both the prover and the statement author (session-level for R2, not R3-only — M2).
- **Where the prover is an external provider, proof search is a data-boundary crossing** (M4/§8); the `prover_data_exposure` declaration is part of the evidence. Prover proof-search transcripts are not assurance evidence and are not copied into records (W5 §24); the artefact set of §2 is the complete evidence.

## 5. Negative scope — what `lean_proof` may never be used for

Binding on packs and on W4 routing:

1. **Not topology-lane coverage.** Until a persistence stack exists in mathlib (absent per S1, re-check on any future survey against a durably stored catalogue — the S1 full catalogue currently lives in a session scratchpad; m8), no `lean_proof` may be presented as certifying a persistence computation, diagram distance, landscape norm, stability property, or landmark/approximation error. A `lean_proof` attached to a topology-lane obligation certifies only the specific finite lemma its `referent_note` names — and the note **must enumerate the lane obligations it does NOT discharge** (§2 `referent_note`; RQ4), so omission is machine-detectable rather than prose. The lane's remaining obligations (benchmarks, permutation nulls, independent recomputation) are untouched.
2. **Not code verification.** A theorem about a mathematical object does not verify any Python/R implementation. The sanctioned bridge is the **certificate pattern**: implementation emits a witness into the result artefact; the theorem certifies the witness-to-property implication; a runtime check certifies the witness. All three parts are named in the `referent_note`.
3. **Not float claims.** Statements are over ℕ/ℤ/ℚ (or exact reals where mathlib supports the claim). The `referent_note` must state where floating point enters the artefact's derived fields and why no promoted claim depends on the rounding.
4. **Not Key B.** No pack may count a `lean_proof` toward scientific review, interpretation, limitation, or claim-strength questions. (Reserved fixture, §3.1 item §5.4.)

## 6. Initial applicability

- **First target (pilot):** the S2 fixed-margin max-ARI concentration bound — statement document authored 2026-07-07, revised under adversarial review 2026-07-20. On **full two-key acceptance** (not kernel acceptance alone) it becomes a *candidate* seed fixture for W6 and *candidate* capability evidence for the future W4 `lean-prover` role profile, consumed only when those gates open (m5).
- **Pack placement:** `TDL_private` TDA pack (W5 §15.1) for referent-bearing instances; the class definition itself is `template_safe` (contains no data, paths, or TDL-private content) and may enter public templates.
- **Deferred (unchanged from scout plan §6):** W4 `lean-prover` role profile (consumes the `prover_data_exposure` field), W7 `vibe` adapter spec (must surface the C1 acceptor-side execution hooks), W6 fixture materialization (consumes the §3.1 table), S3a/S3b research-strand artefacts. None start before their own gates.

## 7. Review questions for the adversarial pass — answered 2026-07-20

The independent review (`../reviews/adversarial-05a-lean-proof-evidence-class-review-2026-07-20.md`) answered all five; the answers are folded into §3 above:

1. **Prover-authored statement masquerading as a re-encoding?** Yes as originally written — through the *environment* (prover-supplied definitions/notation), not the signature door. Closed by §3 item 8 (full-environment diff, elaborated-type hash, declaration-kind scan).
2. **Vacuously true theorem passing all checks?** Two constructions (empty-domain universal; witness on degenerate data). Closed by §3 item 6 (widened scope) + item 9 (adequacy review); M2 and the witness-authorship rule (§4) must hold together.
3. **Key B leak through pack wording?** Prohibited (§5.4) with a reserved fixture (§3.1).
4. **§5.1 erosion via topology-flavoured referent note?** Closed by making the "obligations not discharged" enumeration a required `referent_note` element (§2, §5.1).
5. **Loosely-stated claim surviving a wrong recorded constant?** Yes as originally written (inequality proof never computes the exact value). Closed by §3 item 5 (equality evaluation + discrepancy record).

## 8. Correction to the cited evidence basis (M4)

The scout plan (§§1, 2.2–2.3) and value assessment (§5) describe Leanstral as a **local** model at **zero API tokens**. The S0 vault `[RESULT]` (Computational-Log, 2026-07-04) records the opposite: **Leanstral requires a Mistral API key + Labs model enablement — it is an external API, not a local model.** It is, however, **currently free under Mistral's experimental Labs programme** (so the zero-*metered*-cost premise holds provisionally — via free hosting, not local execution, and not guaranteed to persist). This addendum's design does not depend on locality: the token-economics argument is unaffected in *relative* terms (proof search is off Claude's budget either way), but proof search is a third-party **data-boundary crossing**, which is why §2's `prover_data_exposure` field and §4's boundary sentence exist. Per the currency rule the dated scout plan and value assessment are **not** rewritten; **dated errata were filed 2026-07-21** in each (scout plan after §Scope decisions; value assessment §5) pointing at the S0 vault entry — resolving §9 decision 2.

## 9. Owner decisions (Stephen) — RESOLVED 2026-07-21

1. **Accept the amended addendum (v0.2). → ACCEPTED.** Status updated; packs may reference the class.
2. **Errata to scout plan §§1–2.3 and value assessment §5. → APPROVED and filed 2026-07-21** (§8). Refined per Stephen: Leanstral is external but **free under Mistral's experimental Labs programme for now**, not local — the "zero-token" premise holds provisionally via free hosting, and the data-boundary crossing is real regardless.
3. **R2 statement-reviewer independence rule (§3 item 9 / §4) as class standard. → CONFIRMED.** Every R2 `lean_proof` requires a referent-adequacy reviewer independent of the statement author, not just the prover.
4. **S2 pilot sequencing. → BEFORE.** The pilot proceeds under this contract; it does not block on formal re-acceptance (moot now that v0.2 is accepted, but recorded: the S2 document already meets the stricter rules).
5. **Hammer-proof rule divergence (S2 F6). → STRICTER GOVERNS.** The S3a/S3b prereg §8.4 restriction (no opaque hammer-only proofs unless short/auditable) controls its instances via §8.2 precedence; S2 §5 item 3 states this.

## 10. Later-work dependencies (unchanged gates)

W6 fixture materialization consumes the §3.1 table at its own gate; W4 `lean-prover` role profile consumes the `prover_data_exposure` field; W7 `vibe` adapter spec must surface the C1 acceptor-side execution hooks. No runtime, migration, active APM write, result reinterpretation, or paper-claim change is introduced by this addendum.
