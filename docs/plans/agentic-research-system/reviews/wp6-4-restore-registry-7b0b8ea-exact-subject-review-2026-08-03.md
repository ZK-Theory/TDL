# WP6.4 restore-registry exact-subject review - `7b0b8ea1`

**Date:** 2026-08-03
**Pull request:** #208
**Verdict:** `accept_exact_subject` (`Critical 0`, `Major 0`, `Minor 0`)

## Exact subject

- Candidate: `7b0b8ea1e253294ceb23d70f75c549dd1af4102f`
- Tree: `bcecf6b9b1aafa6f368da165e7ded1005766af02`
- Parent: `520e0b4a7dda0fca7e6a9082002a985ee02c7488`
- Base and merge base: `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e`
- Branch: `codex/wp64-origin-witness-r11`
- Correction delta: `research_system/operations/backups.py` and
  `tests/research_system/integration/test_gate5_release_tranche.py`

At the decision point, local `HEAD`, configured upstream, the live remote
branch, and PR #208 head all resolved to the candidate. The required base is
its merge base and ancestor. The two-path correction passes `git diff --check`.

## Accepted behavior

- Registry-state normalization recursively converts `set` and `frozenset`
  values and orders their normalized elements by canonical bytes. Equivalent
  nested states therefore produce the same canonical JSON and SHA-256.
- Unsupported registry values and failures while serializing set-order keys are
  translated into typed ARS failures. Preparation rejects them before locking;
  locked revalidation raises `IntegrityError` before append. Previously accepted
  registry state retains its prior hash.
- `prepare_restore_admission_before_writer_lease` exposes the ten explicit,
  correctly typed keyword-only inputs. It forwards each once by name, requests
  bundle capture, verifies the returned type, and returns a checked
  `RestoreAdmissionBundle`. The public verifier still returns its
  `RestorePreflightResult`-compatible object unless private capture is requested.
- These changes preserve the previously accepted one-preparation, bounded
  locked-revalidation, durable origin-evidence, and ordinary/T2 retirement
  behavior.

## Validation and protected surfaces

Direct exact-head probes covered nested set/frozenset order, unsupported state,
ordering-key failure at both service boundaries, unchanged accepted-state hash,
exact wrapper forwarding, wrong-return rejection, and verifier API compatibility.
All failed paths left the ledger unchanged.

The proportional restore, ordinary/T2, recovery, origin-witness,
foundation-contract, and P-045 set passed: `109 passed in 505.40s`. Ruff check
and Ruff format check passed for both changed paths.

Relative to the base, the schema trees, contract trees, P-045 event schema,
P-045 decision, and P-045 compatibility-test identities are unchanged. The
pre-existing `.claude/CLAUDE.md` and `.repowise-workspace.yaml` setup changes
were not edited or staged.

## Boundary

This record accepts only the exact candidate above. It does not merge PR #208,
update Jira or another external service, materialize owner authority, or
authorize research execution. Any later substantive commit requires focused
re-review.
