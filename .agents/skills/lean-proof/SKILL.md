---
name: lean-proof
description: Use when driving the Leanstral prover (vibe --agent lean) to generate, complete, repair, or kernel-check Lean 4 proof terms on Windows — headless proof automation, the generate-compile-heal loop, or orchestrating a Lean proof spike such as S2.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - output-provenance
  roles:
    - orchestrator
    - implementer
  runtime: agnostic
---

# Lean Proof (Leanstral orchestration)

Drive the specialist prover **Leanstral** (via the `vibe` CLI) to produce Lean 4
proof terms, and kernel-check them. The orchestrator's job is to craft prompts,
decompose hard goals into helper lemmas, feed kernel errors back, and integrate
and verify — **not** to hand-author proof terms and **not** to author theorem
statements. Leanstral is the prover; hand-proving a goal Leanstral could not
close misrecords `prover_identity` and defeats the pilot. Statement signatures
are frozen by the statement author (`statement_source`); a signature that "would
need to change" is an escalation, never a re-encoding. Not for
persistence/topology formalisation.

## Host engine — the `prove-lean` PowerShell profile function (Windows)

Validated 2026-07-21. The function wraps `vibe`; three facts make it work
headless, and each, if wrong, silently breaks the pipeline:

1. **Inject the key.** `$env:MISTRAL_API_KEY` must be set (the working key lives
   in the profile function). vibe's *own* stored config key can lapse — that
   lapse is the usual `Invalid API key`, not a flag problem.
2. **Use `-p`, not the positional prompt.** `vibe -p "<prompt>" --agent lean --trust`
   is programmatic mode (send prompt, print, exit, ~7s). The bare positional
   `vibe "<prompt>"` opens an **interactive** session that blocks on stdin and
   hangs under automation. `--trust` skips the folder-trust prompt; `--agent lean`
   needs `~/.vibe/agents/lean.toml`.
3. **Write Lean BOM-free.** `[IO.File]::WriteAllText(path, text, (New-Object Text.UTF8Encoding $false))`.
   `Out-File -Encoding utf8` emits a UTF-8 BOM in PowerShell 5.1, and Lean then
   fails `error: expected token` at `1:0`.

## Preflight (mandatory, first — before any proof work)

Smoke-test the prover: `vibe -p "Give a complete Lean 4 proof of: theorem smoke : True := by trivial" --agent lean --trust`.
Expect a valid proof in seconds. **Any auth/connectivity error → STOP and
escalate to the owner.** Do NOT hunt for the key, edit any `.env`, or reinstall
— the key is in vibe's config / the profile, and only the owner can refresh a
lapsed Labs enablement. (This preflight converts an unbounded key-hunt into a
30-second decision; it is the whole reason the S2 first run's failure mode does
not recur.)

## Loop-and-verify

1. **Lift** the target theorem from the frozen statements verbatim — do not
   alter signatures, hypotheses, or definitions.
2. **Generate** the proof term via the prover.
3. **Kernel-check.** `lake env lean <file>` for a standalone file, or integrate
   into the project and build a **named** target (`lake build S2.MaxAriBound`);
   bare `lake build` can exit 0 as a no-op if the lakefile has no default target.
   Exit 0 = accepted. Confirm the axiom set with `#print axioms` (clean set:
   `propext`, `Classical.choice`, `Quot.sound`; no `sorryAx`, no `native_decide`).
4. **Heal.** On failure, extract the exact kernel message (position + goal
   state) and re-prompt the prover with it. For a hard lemma, decompose it into
   helper lemmas for the prover to fill rather than asking for the whole thing.
   Cap iterations (~5). If it still resists, that is an **obstruction to report**
   (deliver the pre-authored fallback where one exists), never a cue to
   hand-prove.

## Guardrails (why)

- **Frozen statements.** Signatures are countersigned in `statement_source`;
  editing one stales the referent-adequacy carry-over. Auxiliary defs may adopt
  mathlib idiom only when the mathematical content is unchanged.
- **`Nat.ble` is `@[extern]`** → kernel-opaque, so `decide` stalls on any
  `≤` / `min` / `mergeSort` computation. Use explicit sorted literals + `norm_num`,
  or rewrite `Nat.choose n 2` via `Nat.choose_two_right` before `decide`.
- **Promoted-bundle acceptance is the acceptor's job** (`tools/check_lean_proof.py`);
  route provenance through `result-provenance-review`, do not re-implement it.
  Promoted files carry `theorem`/`lemma`/`example` only — keep every `def` in the
  imported statements module.
- **Record provenance honestly:** `prover_data_exposure` (statement text, witness
  data, error traces sent to the provider) and `prover_identity` per proof term.

## Self-Test Prompts

- *The smoke test returns `Invalid API key`.* → STOP and escalate; do not edit
  `.env`, hunt keys, or reinstall.
- *A proof would go through if one hypothesis were dropped.* → STOP; signatures
  are frozen — escalate to the statement author.
- *The prover cannot close the crux lemma after 5 iterations.* → deliver the
  pre-authored fallback + an obstruction report; do not hand-write the term.
- *The agent is about to write a `def` into the promoted file.* → keep it in the
  imported statements module; promoted files are theorem/lemma/example only.

## Escalate Or Stop When

- Smoke test fails on auth/connectivity (key lapsed) — owner refreshes it.
- A frozen signature/definition would need to change for a proof to go through.
- The prover cannot produce a term within the timebox — report the obstruction.
- The acceptor emits a constant discrepancy — report it against the artefact,
  never force it away.

## Related Skills

`spike` (toy/scratch discipline and promoted-vs-scratch separation for a proof
spike) · `contract-first-tdd` (result-bearing seams) · `result-provenance-review`
(the acceptance JSON) · `research-assurance-triage` (lane classification before
dispatch) · `tda-handoff` (pausing mid-proof).
