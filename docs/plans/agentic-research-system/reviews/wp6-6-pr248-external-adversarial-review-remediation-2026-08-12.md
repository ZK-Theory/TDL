# WP6.6 PR #248 external-adversarial-review remediation record

Status: candidate construction record; not independent acceptance, CodeRabbit
completion, owner acceptance, merge authorization, or integration evidence.

Controlling review: owner-supplied
`wp6-6-pr248-external-adversarial-review-2026-08-12.md`, 788 lines, 59828 bytes,
SHA-256 `2dbfe5ea936c402b4064fd5e51b84bc9950c581c2cfcb961b04ae752709c41d1`.
It reviewed PR #248 commit
`5c48cc73c5f4f7706049087b4447684330d47c88`, tree
`0a565bc029d0ef5ce7c2cfe1c016a306f7fb55a5`, against live-main
`2e6bf9c92e59208c40e55f664fc48d75e481ae04`, and returned
`REWORK REQUIRED`. The review remains the continuity authority for this
remediation even when a finding overlaps a later PR inline comment.

## External-review finding ledger

| Finding | Candidate disposition | Decisive proof | Final exact-head evidence |
|---|---|---|---|
| C-1 | Reserve the accepted catalogue identity from position zero; allow only OR-140 to claim it while genesis is absent; require genesis before all authority-lane preparation. | Every executable non-OR-140 route rejects the catalogue identity on an empty store with no events or receipts, then exact genesis remains reachable; OR-101 and OR-110 fail on the explicit genesis precondition. | The exhaustive fresh-store route test, natural authority-route negatives, replay-reordering attack and exact genesis positive are in the 446-test candidate gate below. |
| M-1 | Join OR-019 and running-Spike OR-022 closure shadows to the exact same-transaction `PartialOutcomeRecorded` and `LeaseReleased` canonical operational events, re-derived from the active Attempt/Lease at the event instant. Bind holder, reason, stop cause, transaction and durable timestamp. | Fully reindexed/rehashed deletion, substitution, and transaction-split attacks reject at the closure event; complete OR-019 and running-Spike OR-022 paths replay. | Both boundary attack families and untouched OR-019/OR-022 paths are in the 446-test candidate gate below. |
| m-1 | Real TDA-scale dossier certification remains an explicit owner-machine release gate. Hosted CI is not represented as physical-root evidence and no synthetic owner path is introduced. | Stephen, acting as release operator, runs the committed certification command at the exact release-candidate head and attaches its exit/result to the owner acceptance record. | `OWNER_GATE_PENDING` |
| m-2 | The certification script probes `import pytest`; an explicit unusable `TDL_PYTHON` fails with a clear error, repository and owner virtual environments are selected only when pytest imports, and `uv run --group dev python` is the final fallback. | Invalid explicit-interpreter negative plus no-override owner-root certification. | Unusable explicit override failed with its named actionable error; exact candidate certification auto-selected `C:\Users\steph\TDL\.venv\Scripts\python.exe` and returned 38 passed, zero skips, exit 0. |
| m-3 | The exhaustive R1 matrix asserts the closed identity-fence error family rather than accepting an arbitrary `IntegrityError`; the fresh-store catalogue test separately asserts the genesis precondition. | Exact error-match negative across the public submit route matrix. | Both public route-matrix tests require the closed three-message fence family and pass in the 446-test candidate gate. |
| m-4 | Repository-owned runs use the registered `integration` marker from `pyproject.toml`. An out-of-tree reviewer harness must bind the repository configuration explicitly; a repository `conftest.py` cannot make a foreign rootdir inherit project configuration. | Run external harnesses from the repository root, or pass `--rootdir <repository-root> -c <repository-root>/pyproject.toml`; no speculative runtime change. | Documentation disposition; no capability mutation. |
| m-5 | No production classifier change: the governed generic command schema is closed, has no `row_id` or `owner_row_id`, and therefore makes the review's injected-key payload unreachable at persistence. | The schema-contract test proves `additionalProperties: false`, proves both keys absent, and proves a valid generic `ResolveDecision` transaction is not classified as Discovery. Real Discovery resolve rows remain unchanged. | `test_generic_resolve_decision_cannot_spoof_a_discovery_row_binding` passes in the 446-test candidate gate. |
| m-6 | Exercise OR-028 at both irreversible ledger boundaries using the real accepted expected-set and path authorities. | Before-publish interruption leaves exact events and receipts unchanged and retries once; after-publish interruption repairs the exact lost receipt without a second event batch. | Both OR-028 crash tests pass in the 446-test candidate gate and the 38-test strict dossier certification. |
| m-7 | Closed by M-1's direct operational closure binding; downstream revisit failure is no longer treated as the defence. | Truncated-at-boundary OR-019 and OR-022 attacks fail on the owning closure invariant. | Both truncated closure attack families pass in the 446-test candidate gate. |

## PR #248 unresolved-thread ledger at remediation start

| Thread finding | Candidate disposition | Final exact-head evidence |
|---|---|---|
| CodeRabbit: persist the exact reviewed PR #248 source identity and validation evidence | The preceding PR #247 remediation record now names commit `5c48cc73...`, tree `0a565bc0...`, subject, exact nine-module aggregate command, named decisive nodes, and reported results without pretending those historical bytes are the new remediation head. | Historical exact-source identity and its 427-pass/1-skip plus 35-pass certification evidence are now durable in that record. |
| Codex: bind `CandidateAssayLinked` to the scored Assay | Require the exact preceding same-transaction `AssayScored` event, Candidate/Assay identities and prior states. | Fully rehashed missing/split/wrong-stream attacks pass in the 446-test candidate gate. |
| Codex: bind `CandidateSpikePlanLinked` to the newly planned Spike | Require the exact preceding same-transaction `SpikePlanned` and `SpikeApprovalRequested` events, Candidate/Spike identities and prior states. | Fully rehashed missing/split/wrong-stream attacks pass in the 446-test candidate gate. |
| Codex: bind dossier materializations to the accepted manifest | Persist the full schema-valid `candidate_manifest` in `ResearchDossierAdmitted`; replay validates its accepted hash and requires exact one-to-one object, Scope and edge blueprints/content hashes plus exact relationships. A coordinated fully rehashed substitution must reject. | The coordinated object/Scope/edge/relationship substitution was observed red before the fix and passes in both final candidate gates. |
| Codex: authorize initiating commands against the aggregates they mutate | Resolve the four initiating Decision/Review commands against the existing Candidate scope; a grant only for the minted target rejects before mutation. | Candidate-scope activation and wrong-minted-target/no-mutation controls pass in the 446-test candidate gate. |

## Consolidated candidate evidence

The commit cannot contain its own commit or tree hash. The exact resulting
commit and tree are therefore recorded in the PR #248 conversation immediately
after push; this durable record binds the reviewed source above and the commands
and results used to construct that successor.

- Candidate gate:
  `C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -p no:randomly --no-cov -rs tests/research_system/contracts/test_w11_expected_catalogue.py tests/research_system/integration/test_wp6_6_discovery_authority.py tests/research_system/integration/test_wp6_6_discovery_crash_recovery.py tests/research_system/integration/test_wp6_6_discovery_runtime.py tests/research_system/integration/test_wp6_6_dossier_admission.py tests/research_system/unit/test_command_lifecycle.py tests/research_system/unit/test_discovery_dossier.py tests/research_system/unit/test_schema_registry.py tests/research_system/unit/test_wp6_6_discovery_activation.py`
  returned **446 passed in 835.94s**, exit 0.
- Exact owner-root construction certification:
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\certify_wp6_6_real_dossier.ps1`
  auto-selected `C:\Users\steph\TDL\.venv\Scripts\python.exe` and returned
  **38 passed in 68.75s**, zero skips, exit 0.
- Ruff check and format-check passed on every changed Python file; PowerShell
  parsing and `git diff --check` passed.
- The protected W11 catalogue remains Git blob
  `8d58818540e04859f929d4b04c71e4cfa0512554`, 136229 bytes, SHA-256
  `7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80`.

## Owner-machine real-dossier release gate

Owner/operator: Stephen.

At every exact candidate head proposed for WP6.6 acceptance, from that clean
checkout run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/certify_wp6_6_real_dossier.ps1
```

The command sets `TDL_REQUIRE_REAL_DOSSIER=1`; inaccessible repository, vault,
or contract roots are a collection error, not a skip. Acceptance evidence must
name the candidate commit and tree, selected pytest-capable interpreter, command,
test count, exit code, and zero real-dossier skips. A hosted CI pass does not
substitute for this physical owner-root certification.

## Closure boundary

The consolidated test evidence is recorded above. Exact commit/tree identity,
PR thread replies, and resolved-thread readback are recorded in PR #248 only
after the consolidated remediation is committed and pushed.
Stephen alone triggers or monitors CodeRabbit. The campaign remains incomplete
until Stephen reports CodeRabbit complete at the exact current PR head and
separately authorizes a fresh integration closer.
