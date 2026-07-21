# Task Brief: S2-PROOF-v2 — Complete the S2 Lean proof via Leanstral orchestration

**Date:** 2026-07-21
**Model / effort:** **Opus 4.8, High** (rationale in §Model note — this is a hard-proof orchestration + fragile-setup-recovery task, not mechanical loop-running; the prior Sonnet run failed on both).
**Supersedes:** the busted first attempt on TDL branch `run/s2-lean-proof` (commit 173e554, Sonnet) — see §Why the first run failed. Reuse its Lean project and partial proofs; do not restart cold.
**Status:** ready to dispatch once PR #144 (C1) is merged (§Blocking preconditions).

---

## Model note — why Opus High, not Sonnet

The original routing put this at Sonnet/medium on the theory that "the kernel is the verifier, the driver just manages the loop." The first run disproved that theory for *this* task: the setup is fragile (external prover, non-obvious auth location) and the remaining proof (T1) is genuinely hard (exchange induction needing coordinated sub-lemmas). Sonnet rabbit-holed on access, then abandoned the prover and hand-proved only the two trivial theorems. Opus High is chosen because the orchestrator's real value here is (a) not rabbit-holing on setup, (b) *decomposing* T1 into helper lemmas Leanstral can fill, (c) crafting effective `vibe` prompts and iterating on kernel errors, and (d) recognising statement drift. None of that is mechanical.

**This does not change the division of labour: Leanstral is the prover; the orchestrator does NOT hand-author proof terms.** The first run's central error was the orchestrator proving theorems itself. See §Hard rules.

## Target paper / project

P01-A (the certified bound backs the reviewer-B9 normalisation) + ARS infrastructure (the `lean_proof` evidence-class pilot, 05a).

## Goal

Complete the S2 fixed-margin max-ARI Lean proof so the promoted bundle passes the acceptor harness with a clean axiom set — **either** the full tight bound (T1→T2→T4→T5 at pair-overlap ≤ 60,862,048) **or**, if T1 resists the timebox, the pre-authored coarse fallback (T4-coarse at ≤ 65,560,990) as an honest Partial. Every proof term is produced by **Leanstral**, driven by the orchestrator.

## Non-goals (hard stops)

- **Do NOT author, weaken, or "re-encode" any theorem signature, definition, notation, or constant.** The statement set is frozen and countersigned (see §Statement source). Signature drift → STOP and escalate (§Stop conditions).
- **Do NOT hand-prove to bypass Leanstral.** If Leanstral cannot produce a proof, that is an obstruction to report, not a cue to write the proof yourself. `prover_identity` in the bundle must honestly name who produced each proof term.
- **Do NOT re-prove what is already clean** (T3, T6, all G-obligations, C1, W, M — §State).
- **Do NOT hunt for or provision a `MISTRAL_API_KEY`, and do NOT touch TDL's `.env`.** The key is in vibe's own config and already works (§Leanstral access). A missing key → STOP and escalate, never hunt.
- No persistence/topology formalisation; no paper-claim promotion (that step is separately R3, out of scope); no toy/synthetic artefacts in `results/`.

## Blocking preconditions (verify before any proof work)

1. **PR #144 merged.** `statement_source` pins to the post-C1 S2 blob; the referent-adequacy review's zero-re-review carry-over is keyed to those exact bytes. If #144 is unmerged, STOP.
2. **Leanstral smoke test passes** (§Leanstral access step 3). If it fails, STOP and escalate — do not attempt to fix auth.
3. **The Lean project builds** (`lake build` exit 0 from the existing project, §Lean access). It already did at 68b996c; a fresh failure is a toolchain problem to report, not to debug indefinitely.

## Leanstral access (READ THIS — it is where the last run lost hours)

The prover is **Leanstral 1.5** (Mistral Labs specialist model), driven through the `vibe` CLI. It is **already installed and configured** — S0 (vault Computational-Log 2026-07-04) proved it functional.

1. **Binary:** `vibe` is on PATH at `~/.local/bin/vibe` (Windows: `C:\Users\steph\.local\bin\vibe`). Confirm with `vibe --version`.
2. **Invocation (programmatic mode, ~20–30 s/request):**
   ```
   vibe -p "<your prompt to Leanstral>" --agent lean
   ```
   Leanstral returns Lean 4 code; you integrate it into `MaxAriBound.lean` and kernel-check with `lake build`.
3. **MANDATORY first step — smoke test:** reproduce an S0-style proof, e.g.
   ```
   vibe -p "Give a complete Lean 4 proof of: theorem smoke : True := by trivial" --agent lean
   ```
   Confirm Leanstral responds with a valid proof. **If `vibe` errors on auth/connectivity, STOP and escalate to Stephen.** Do NOT look for the API key, do NOT edit `.env`, do NOT install anything — the key lives in vibe's own configuration (NOT TDL's `.env`; that is the dead end the last run searched), and if it has lapsed only Stephen can refresh the Labs enablement.
4. **Prover role:** Leanstral produces proof terms and auxiliary **private lemmas** (05a §4). You may craft strategic prompts (suggest the proof route, supply the `Nat.ble` workaround below, feed back kernel errors) and decompose T1 into helper lemmas for Leanstral to fill — but the proof terms are Leanstral's output, integrated and kernel-checked by you.

## Lean access (also a time-sink last run — it is all already set up)

- **Toolchain installed:** elan 2.10.4, Lean `leanprover/lean4:v4.32.0`, Mathlib4 `v4.32.0`. Do NOT reinstall.
- **The project already exists and is built** at `C:\Users\steph\lean-tda-spikes` (a git repo, HEAD `68b996c`). `.lake/` is populated — **do NOT run `lake exe cache get` from scratch or re-fetch mathlib.** Just `lake build` (incremental) from the project root.
- **Files:**
  - `S2/Statements.lean` — statement-side defs + the frozen theorem signatures (derived from `statement_source`). **Do NOT edit signatures/defs here.**
  - `S2/MaxAriBound.lean` — the proofs. **This is where you work.**
- **Continue the Lean project from `68b996c`** with new commits in `lean-tda-spikes`; the TDL side gets a fresh branch off `main` (§Outputs).

## Carry-forward engineering discovery (from the first run — saves hours)

`Nat.ble` is `@[extern]` in Lean 4 → **kernel-opaque**, so `decide` stalls on any `≤` / `min` / `mergeSort` computation. Workarounds already proven in this project:
- For the greedy upper value, use the literal `sortedGmmCounts` (already defined in `Statements.lean`) instead of `gmmCounts.mergeSort`, then `norm_num` (NOT `decide`).
- `Nat.choose_two_right` rewrites `Nat.choose n 2` to multiplication before `decide`/`norm_num` evaluates the GMP arithmetic — use it for pair-count evaluations (it is how `b9_pair_sum_witness` = 59,684,973 was proved).

## State — what is already proved (do NOT touch) vs what remains

**Proved and kernel-clean (axiom set `{propext, Classical.choice, Quot.sound}`) — leave alone, do not re-prove:**
- **T3** (`ari_mono`), **T6** (`normalised_lower`).
- All **G-obligations**: `greedySumSqUpper_eq` (=121,751,376), `pairBoundDerived_eq` (=60,862,048), `rpQ_pins`, `cpQ_pins`, `tpQ_pins`, and **C1**: `omCounts_sum_eq` / `gmmCounts_sum_eq` (=27,280).
- **W**: `b9_pair_sum_witness` (=59,684,973) + the three margin-check examples.
- **M**: falsifiability `¬ (…) ≤ 59,684,972` (by `omega`).

**Remaining work (drive Leanstral to prove, in this order):**
1. **T4-coarse** (`b9_pair_overlap_le_coarse` ≤ 65,560,990) — **do this FIRST to secure a deliverable.** Route is *known*: column-convexity (cpQ = 64,376,266 ≤ 65,560,990) with `Nat.choose_two_right` floor-division. This guarantees at least a coarse-scope Partial even if T1 never lands.
2. **T1** (`sumSq_le_greedyFill`) — **the crux.** Exchange induction over the sorted capacity list; the first run judged it needs 3+ coordinated helper lemmas. This is exactly the token-heavy tactic search Leanstral exists to do — decompose it and drive Leanstral hard here.
3. **T2** (`matrix_sumSq_le_rowConcentration`) — row-wise application of T1.
4. **T4** (`b9_pair_overlap_le` ≤ 60,862,048) — T2 (direct, c = gmmCounts) + the G value.
5. **T5** (`b9_ari_le`) — already *structurally* proved (T3 + T4 via `exact_mod_cast`); once T4 is clean, remove the `sorry` contamination. No new proof search.

## Assurance-lane disposition

- **Output/Provenance — REQUIRED now.** Evidence = the promoted bundle; acceptance = `tools/check_lean_proof.py` passes (§Acceptance). This is the `lean_proof` Key-A machine half.
- **Paper Claim — DEFERRED**, owner Stephen, gate = R3 promotion of the normalised bracket into P01-A prose (separate; out of scope).
- **Topology / Stochastic-Null / Statistical-Panel / Representation — NOT APPLICABLE:** this task certifies a finite counting/algebra bound; it touches no persistence, null, estimand, or representation object.
- **Key B(a) referent adequacy** is already satisfied (`reviews/referent-adequacy-S2-max-ari-2026-07-21.md`, `adequate_with_conditions`, C1 applied + acknowledged). This run supplies Key A only; both feed the eventual acceptance record.

## Required upstream contracts

- **Existing / accepted:** 05a `lean_proof` acceptance contract (v0.2, ACCEPTED); the acceptor harness `tools/check_lean_proof.py` (PR #143). Nothing new needs authoring.

## Inputs (by path)

- `C:\Users\steph\lean-tda-spikes` @ `68b996c` — the Lean project (S2/Statements.lean, S2/MaxAriBound.lean, bundle/).
- `docs/plans/strategy/S2-statement-authorship-max-ari-bound-2026-07-07.md` — **`statement_source`** (post-#144). Signatures here are frozen.
- `docs/plans/agentic-research-system/design/05a-lean-proof-evidence-class-addendum-2026-07-07.md` §3–§4 — acceptance contract + authorship split.
- `docs/plans/agentic-research-system/reviews/referent-adequacy-S2-max-ari-2026-07-21.md` — Key B(a) evidence.
- `results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-24.json` — the T1.23d artefact certified.
- Vault S0 entry (`vault/04-Methods/Computational-Log.md`, 2026-07-04) — the proven Leanstral/Lean setup.
- `tools/check_lean_proof.py` — the acceptor harness.

## Expected outputs (by path)

- Updated `C:\Users\steph\lean-tda-spikes\S2\MaxAriBound.lean` (proofs completed), committed in the `lean-tda-spikes` repo (new HEAD).
- Promoted `bundle/` (MaxAriBound.lean, Statements.lean, build.log, axiom-audit.md, `result.md` with `prover_data_exposure` + the lean-repo commit anchor).
- **New date-suffixed** acceptor output `results/panel_methodology/ari/lean_proof_s2_acceptance_<YYYY-MM-DD>.json` (no overwrite; supersedes the 6/8 file from the busted run).
- Vault `[RESULT]` entry (top-of-page, `vault/04-Methods/Computational-Log.md`) referencing this brief, the statement doc, and the T1.23d JSON, carrying the §1 referent line **at the scope actually proved**.
- TDL branch `run/s2-lean-proof-v2` (off `main`, post-#144), PR opened; CodeRabbit before merge.

## Acceptance criteria (machine-checkable)

Run the acceptor and read its JSON:
```
uv run --env-file .env python tools/check_lean_proof.py \
    --bundle "C:\Users\steph\lean-tda-spikes\bundle\s2-lean-proof" \
    --repo-commit <new lean-tda-spikes HEAD> \
    --project-dir "C:\Users\steph\lean-tda-spikes" \
    --json-out results/panel_methodology/ari/lean_proof_s2_acceptance_<YYYY-MM-DD>.json \
    --emit-discrepancies results/panel_methodology/ari/lean_proof_s2_discrepancies_<YYYY-MM-DD>.json
```
- **Full success:** all 8 checks PASS — `kernel-build` exit 0, `no-holes` (no `sorry`/`admit`), `axiom-audit` (⊆ {propext, Classical.choice, Quot.sound}; no `sorryAx`), `trusted-computing-base` (no `native_decide`), `declaration-kind`, `constant-equality`, `non-vacuity-witness`, `file-integrity` — with **T1–T6 all clean**.
- **Acceptable Partial:** T4-coarse clean, T5 re-instantiated at 65,560,990, T1/T2/T4 documented as obstructed; acceptor passes for the **coarse-scope bundle** (no `sorry` in the *promoted* set — the tight-bound theorems are excluded from the promoted bundle, not left as stubs in it), with an obstruction report on T1.
- A discrepancy record emitted by the acceptor (a G constant not matching the artefact) is a **finding to report**, never to force away.

## Validation commands

- Lean: `lake build` (from `C:\Users\steph\lean-tda-spikes`) exit 0.
- Axioms: `#print axioms` on every promoted theorem shows the clean set only.
- Acceptor: the command above, exit 0 for the delivered scope.

## Provenance requirements

- `prover_data_exposure` recorded (statement text, witness data, error traces sent to Leanstral; provider = Mistral Labs API). B9 margins are minimized aggregates — benign, but record it.
- Lean-project **repo identity + commit** bound in `result.md` (05a m3) — the project is outside TDL, so a bare file hash has no durable anchor.
- Acceptor output is date-suffixed, no-overwrite (the 2026-07-21 6/8 file stands as history).

## Runtime constraints

- Timebox: 1 working day of orchestration (Leanstral does the iteration; latency ~20–30 s/request). No heavy TDL compute; no worker/checkpoint machinery needed.
- `lake build` is incremental off the existing `.lake/` — do not clean-rebuild.

## Paper-claim constraints

- **Allowed:** the bundle certifies the pair-count bound (and, at full success, the ARI upper bound + normalised transfer) for the exact B9 margins. Target: none in prose this run — this produces evidence, not paper text.
- **Prohibited:** presenting the certificate as promoting the P01-A claim (that is the separate R3 step). **If the coarse fallback is delivered, the `[RESULT]` must state the coarse scope and must NOT present the published normalised bracket floor 0.30346 as certified** — under the fallback the certified floor is ≈ 0.2765 and 0.30346 stays on runtime assurance (referent-adequacy review §2 item 5).

## Suggested skills

`spike` (toy/scratch discipline; promoted vs scratch separation), `commit-log` + `vault-sync` (close-out), `result-provenance-review` (the acceptance JSON).

## Stop conditions (blocking)

1. **Leanstral smoke test fails** → STOP, escalate to Stephen. Do not hunt keys, edit `.env`, or install anything.
2. **A frozen signature/definition would need to change** to make a proof go through → STOP, escalate to the statement author; do not author it (that stales the countersigned statement set and the referent-adequacy carry-over).
3. **T1 resists after the timebox** → do NOT hand-prove it; deliver the T4-coarse Partial with an obstruction report (this is a success outcome, not a failure).
4. **PR #144 not merged** → STOP (statement_source pin).
5. **The orchestrator finds itself writing proof terms Leanstral could not produce** → STOP and report; hand-proving defeats the pilot's purpose and misrecords `prover_identity`.

## Why the first run failed (context, not blame)

Sonnet (branch `run/s2-lean-proof`, 173e554): (a) searched TDL's `.env` for `MISTRAL_API_KEY` — it was never there (it is in vibe's config), so the hunt was unbounded; (b) did not have the `vibe -p … --agent lean` pattern to hand; (c) after losing time on access, abandoned Leanstral and hand-proved T3 and T6 (the two trivial theorems), leaving T1 (the crux) and all its dependents as `sorry`. Net: 2/6 theorems, and the two proved were the two that never needed a specialist prover. This brief front-loads access, points at the existing built project, carries the `Nat.ble` discovery forward, secures the coarse fallback first, and forbids hand-proving — so the effort lands where it belongs: driving Leanstral through T1.
