# 05a — W5 Addendum: `lean_proof` Evidence Class

**Date:** 2026-07-07
**Status:** DRAFT — `review_pending`; requires independent adversarial review (fresh session, per scout plan §7) and Stephen's acceptance before any pack references it
**Specification version:** 0.1 (extends W5 v0.2 via the §8.2 domain-pack interface; changes no core lifecycle, authority, or lane semantics)
**Implementation authority:** None; this document creates no packs, contracts, adapters, role profiles, or Lean artefacts
**Evidence basis:** S0 smoke test PASS (2026-07-04), S1 gap survey + framing memo (2026-07-07), S2 statement-authorship document (`docs/plans/strategy/S2-statement-authorship-max-ari-bound-2026-07-07.md`), value assessment (`docs/plans/strategy/lean-integration-value-assessment-2026-07-07.md`)

## 1. Purpose and position

This addendum defines `lean_proof` as a new **evidence class** that reviewed domain packs may attach to machine-checkable proof obligations. A `lean_proof` is a Lean 4 artefact whose acceptance is established by the Lean kernel — a deterministic, fail-closed, non-LLM verifier that is independent of every producer and reviewer in the system *by construction*.

Position within W5 v0.2, unchanged semantics:

- **Claim classification (§12):** a `lean_proof` discharges **D-class** assertions only — the "independently recomputable property" column, where the kernel is the independent recomputation. It contributes nothing to T, R, M, H, O, or P classes.
- **Two-key validity (§17):** a `lean_proof` is **Key A evidence only**. The statement-referent question — *does the formal statement say what the promoted claim needs?* — is a Key B obligation (R-class review plus, where the pack requires, H-class human sign-off) that no prover output can discharge. A kernel-accepted proof of the wrong statement fails assurance exactly as W5 requires.
- **Pack constraints (§8.2):** this class cannot turn `not_applicable`, `unable_to_grade`, Partial, or a failed obligation into pass; cannot lower risk floors, independence grades, or human gates; cannot override a stronger pre-registration.

## 2. Evidence-class definition

A `lean_proof` evidence record binds:

| Field | Content |
|---|---|
| `statement_source` | The independently authored statement document (ID + hash) fixing the theorem signatures — e.g. the S2 statement document. Authored before proof search per §4 |
| `statement_hash` | Hash of the exact promoted `theorem` signatures as built (post-proof), diffed against `statement_source` at review |
| `referent_note` | Plain-English statement of the empirical/paper claim the theorem licenses, including the exact result artefact IDs/hashes it attaches to and where exact arithmetic ends (e.g. float rounding boundaries) |
| `toolchain` | `lean-toolchain` content, mathlib commit, lake manifest hash |
| `artefacts` | Promoted `.lean` files (hashes), `build.log`, `axiom-audit.md`, `result.md`; scratch files listed and excluded |
| `kernel_verdict` | `lake build` exit status on the pinned toolchain |
| `axiom_audit` | `#print axioms` output per promoted theorem |
| `witnesses` | Non-vacuity witnesses and mutation obligations (§3.5–3.6) with their build status |
| `prover_identity` | Provider/model of the proof author (e.g. Leanstral 1.5 via `vibe`), per W3 visibility rules |

## 3. Acceptance contract (all machine-checkable, fail-closed)

A `lean_proof` is admissible as Key A evidence only when all of the following hold:

1. **Kernel:** `lake build` exits 0 on the pinned toolchain recorded in the evidence.
2. **No holes:** no `sorry` / `admit` in promoted files (grep) and `#print axioms` on every promoted theorem shows no `sorryAx`.
3. **Axiom audit:** axiom set ⊆ {`propext`, `Classical.choice`, `Quot.sound`}. Any classical-choice use is noted in `result.md`. New axioms are prohibited.
4. **Trusted-computing base:** `native_decide` and `extern`/FFI-backed evaluation are prohibited unless the requirement explicitly approves them with rationale (they extend trust beyond the kernel to the compiler). Opaque hammer output is acceptable only where the resulting proof term is kernel-checked (it always is) — but the *statement* may never be produced by the prover (§4).
5. **Constants derived, not asserted:** every numeric constant appearing in a promoted statement that also appears in a result artefact is derived in-proof by computation. If the derived constant differs from the artefact's recorded value, the evidence is submitted as a **finding against the artefact**, never adjusted to match (anti-anchoring, W5 §13.2).
6. **Non-vacuity witness:** for every promoted theorem with hypotheses, a kernel-checked `example` exhibits an instance satisfying them — on the real referent data where feasible. A theorem whose hypotheses are unsatisfiable proves nothing about the claim; this is the degenerate-path guard of W5 §13.3 in formal clothing.
7. **Mutation obligation:** at least one deliberately false variant (e.g. the bound tightened past a known witness) is *refuted* in-kernel, demonstrating the encoding is falsifiable. A statement family in which the false variant cannot be refuted fails the contract.
8. **Statement-referent review (Key B, blocking):** the promoted signatures are diffed against `statement_source` by a reviewer independent of the prover at the grade the requirement demands (≥ I1 for R2; I2 + Stephen for R3/P-005 per W5 §6.2/§11.1). Signature drift of any kind — including "equivalent" re-encodings — stales the review.
9. **Scratch separation:** exploratory files are excluded from the promoted set and from the evidence hashes (prereg §9 layout).

Failure of any item yields `evidence_inadmissible`; per W5 §17.3 no other evidence compensates.

## 4. Statement/prover authorship split (binding)

The critical risk is proving the wrong statement, not proving a statement wrongly. Therefore:

- The **statement author** (Claude judgment model or Stephen) fixes theorem signatures and the referent note *before* proof search, in a statement document under version control.
- The **prover** (Leanstral or any successor) supplies proof terms and auxiliary private lemmas only. It may *propose* signature changes; a proposal returns to the statement author and re-review — it is never self-applied.
- The statement author and the prover must be distinct actors under W4's relationship evidence; the statement reviewer (§3.8) must additionally be independent of the statement author's *session* for R3 work.
- Prover proof-search transcripts are not assurance evidence and are not copied into records (W5 §24); the artefact set of §2 is the complete evidence.

## 5. Negative scope — what `lean_proof` may never be used for

Binding on packs and on W4 routing:

1. **Not topology-lane coverage.** Until a persistence stack exists in mathlib (absent per S1, re-check on any future survey), no `lean_proof` may be presented as certifying a persistence computation, diagram distance, landscape norm, stability property, or landmark/approximation error. A `lean_proof` attached to a topology-lane obligation certifies only the specific finite lemma its referent note names; the lane's remaining obligations (benchmarks, permutation nulls, independent recomputation) are untouched.
2. **Not code verification.** A theorem about a mathematical object does not verify any Python/R implementation. The sanctioned bridge is the **certificate pattern**: implementation emits a witness into the result artefact; the theorem certifies the witness-to-property implication; a runtime check certifies the witness. All three parts are named in the referent note.
3. **Not float claims.** Statements are over ℕ/ℤ/ℚ (or exact reals where mathlib supports the claim). The referent note must state where floating point enters the artefact's derived fields and why no promoted claim depends on the rounding.
4. **Not Key B.** No pack may count a `lean_proof` toward scientific review, interpretation, limitation, or claim-strength questions.

## 6. Initial applicability

- **First target (pilot):** the S2 fixed-margin max-ARI concentration bound — statement document authored 2026-07-07; on kernel acceptance it becomes the seed fixture for W6 and the capability evidence for the future W4 `lean-prover` role profile.
- **Pack placement:** `TDL_private` TDA pack (W5 §15.1) for referent-bearing instances; the class definition itself is `template_safe` (contains no data, paths, or TDL-private content) and may enter public templates.
- **Deferred (unchanged from scout plan §6):** W4 `lean-prover` role profile, W7 `vibe` adapter spec, W6 fixture materialization, S3a/S3b research-strand artefacts. None start before their own gates.

## 7. Review questions for the adversarial pass

1. Can a prover-authored statement reach promotion by masquerading as a re-encoding of the authored statement? (§3.8 drift rule is the defence — attack it.)
2. Can a vacuously true theorem (unsatisfiable hypotheses) pass all machine checks? (§3.6 — construct a case the witness requirement misses, e.g. witness satisfies hypotheses but on degenerate data disjoint from the referent.)
3. Can `lean_proof` evidence leak into Key B through pack wording ("kernel-verified, therefore reviewed")?
4. Can the negative scope of §5.1 be eroded by a pack that names a persistence-adjacent lemma with a topology-flavoured referent note?
5. Does §3.5 handle the case where the artefact's recorded constant is wrong but the *claim* consuming it was stated loosely enough to survive? (Interaction with paper-claim lane.)
