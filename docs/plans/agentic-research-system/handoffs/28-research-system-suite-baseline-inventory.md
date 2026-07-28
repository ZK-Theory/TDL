# Baseline inventory: the first completed `tests/research_system` run

**Created:** 2026-07-28
**For:** the agent implementing Defect 3 (producer emits `command_schema_*`), and anyone needing a before-number for this suite
**Supersedes nothing.** Extends `26-research-system-suite-red-briefing.md`, which recorded that this suite had never been seen to finish.
**Status of every number below:** measured on one completed run, not inferred.

## Why this exists

Briefing 26 closed with: *"The inventory past test 74 is unknown. Nobody has seen this suite finish. Establishing the complete list is worth doing once your fix makes a full run affordable — that is arguably the biggest single benefit of the N+1 repair."*

This is that list. The suite completed in **1:12:45**.

## Provenance

| | |
|---|---|
| Tree | `97f447f` — `main` at `dd77689` plus PR #176 (Defects 1 and 2) |
| Command | `uv run --no-sync python -m pytest tests/research_system -q -o "addopts=" -p no:cacheprovider -p no:cov --no-header -rf --durations=15` |
| Interpreter | worktree `.venv`, Python 3.13.5, pytest 9.0.2 |
| `rfc3339-validator` | **absent** — the fallback checker was live, and correct (PR #176) |
| Wall clock | 4365.89s (1:12:45) |

Note the venv: briefing 26 recommends the main-repo interpreter, but that one lacks `jsonschema` and cannot run this suite. The worktree venv was provisioned with `uv sync --all-extras --no-install-package petls`, which is the procedure `pyproject.toml:120` documents and which works.

## Headline

**1515 tests — 1357 passed, 133 failed, 25 errors.**

Every one of the 158 non-passing cases is attributed below. No unexplained residue.

| Cause | Count | Share |
|---|---|---|
| Defect 3 — `command_schema_*` required but never emitted | **156** | 98.7% |
| Stale schema enumeration (`receipt-v2`) | 1 | |
| Stale signature guard (`Receipt \| T2Receipt`) | 1 | |

Attribution method: each of the 133 failure blocks and 25 error blocks was parsed from the run output and classified by whether its traceback mentions `command_schema_*`. Block count reconciles exactly with the summary line (133 = 133), so this is exhaustive, not a sample.

## Defect 3 — 156 cases

**All 25 errors** are Defect 3, all at fixture setup:

| Module | Errors |
|---|---|
| `unit/test_adapter_parity.py` | 16 |
| `integration/test_gate5_variant_execution.py` | 9 |

**131 of the 133 failures** are Defect 3:

| Module | Failures |
|---|---|
| `unit/test_release_publication.py` | 85 (84 Defect 3 + 1 signature guard) |
| `unit/test_command_service.py` | 10 |
| `integration/test_gate5_release_tranche.py` | 9 |
| `integration/test_control_plane_fixtures.py` | 8 |
| `unit/test_replay.py` | 5 |
| `unit/test_store.py` | 3 |
| `integration/test_release_event_publication.py` | 3 |
| `integration/test_release_coordinator.py` | 3 |
| `integration/test_eval_cli.py` | 3 |
| `unit/test_schema_registry.py` | 1 (**not** Defect 3 — see below) |
| `integration/test_gate5_variant_execution.py` | 1 |
| `integration/test_broken_oracle_regression.py` | 1 |
| `integration/test_authority_grant_source.py` | 1 |

The common path is `ledger.append` → `SchemaRegistry.validate` → the generated event schema. **When the producer starts emitting these fields, expect all 156 to move together.** If a subset stays red, that subset is a different defect and worth isolating early.

## The two cases that are NOT Defect 3

These will survive your change. Neither is yours; both are recorded so you can discount them.

### 1. `test_every_core_schema_declares_closed_object_contract`

`unit/test_schema_registry.py:92` asserts the contents of `.research-system/schemas/core/` equal a hand-written 13-name literal. `receipt-v2.schema.json` was added by `391a927` and never added to the literal.

```
Extra items in the left set: 'receipt-v2.schema.json'
```

The gate's signal is inverted: a correctly-added schema reads as a violation, while the property under test — that every core schema declares a closed object contract — is never evaluated for the new file. Left untouched, because the closed enumeration may be a deliberate unreviewed-schema-addition gate rather than an oversight. That is a call for whoever owns it.

### 2. `test_command_service_submit_preserves_public_signature_and_guard_metadata`

`unit/test_release_publication.py:956`:

```
assert 'Receipt | T2Receipt' == 'Receipt'
- Receipt
+ Receipt | T2Receipt
```

A signature guard pinning `CommandService.submit`'s return annotation, not updated when WP6.2 T2 widened it to a union.

**This one is close to your work.** It guards the exact method whose path you are changing, and it is currently red for an unrelated reason — so it cannot tell you whether *your* change alters that signature. Worth updating to the intended annotation before you start, so it is a live gate during your task rather than known-noise.

## Slowest tests

All fifteen slowest are in `unit/test_release_publication.py`, 48–63s each:

| Seconds | Test |
|---|---|
| 63.04 | `test_replay_rejects_release_source_and_chain_tamper[authority_id-...]` |
| 62.55 | `test_replay_rejects_release_source_and_chain_tamper[authority_hash-...]` |
| 61.47 | `test_index_first_receipt_crash_recovers_exactly_one_publication` |
| 61.13 | `test_concurrent_exact_publications_serialize_to_one_original_receipt` |
| 56.89 | `test_public_verifier_rejects_pre_serialization_producer_perturbation[applicability]` |

Each still calls `run_p0_coverage`, which builds one registry per distinct schema root and validates 40 fixture packages. That is now paid once per root rather than 40 times, but it is not free — this file remains the suite's cost centre and is the place to look if further speedup is wanted.

## Reproducing this more cheaply than I did

The N+1 fix is on `main`, so a re-run costs far less than it did to produce this. Reference point: one test in this file went **315.05s → 16.97s** (18.6×) from the caching fix alone.

Two things that cost me time and need not cost yours:

1. **A fresh worktree `.venv` is an empty stub.** `uv run` fails building `petls` (CMake cannot find Boost), and `uv run --no-sync` then silently uses a venv with no pytest. Provision with `uv sync --all-extras --no-install-package petls`.
2. **Do not pipe a long background run through `tail`.** Output is buffered until exit, so a failed run and a working one look identical — indistinguishable from a hang for as long as it lasts.
