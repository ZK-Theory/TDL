# WP6.4 restore-recovery exact-subject review — `5b9e3d3`

**Date:** 2026-08-02
**Reviewer role:** fresh independent exact-subject reviewer; no remediation performed
**Workflow / phase:** standalone / deliver
**Verdict:** `rework_required`

## Exact subject

| Item | Verified value |
|---|---|
| Review branch | `codex/wp64-restore-recovery-r10-review` |
| Candidate | `5b9e3d389f59e861b024d0a7ae92d335ec51d29c` |
| Candidate tree | `f5d4007ed58326d04ab0c6c17093c03ad7531ab9` |
| Required / sole parent | `0b0ee6c11381cf8e000858b13526d62110ec26d4` |
| Expected candidate delta | 8 paths |

The worktree began detached at the candidate. Before any task write, detached
`HEAD`, the local review ref, remote-tracking review ref, and live remote review
ref all resolved to the candidate. One deterministic
`git switch codex/wp64-restore-recovery-r10-review` attached the worktree. No
fallback branch, rename, detached commit, history rewrite, or Repowise setup
write was used.

The resumed write gate returned:

```json
{"cwd":"C:\\Users\\steph\\.codex\\worktrees\\3942\\TDL","branch":"codex/wp64-restore-recovery-r10-review","head":"5b9e3d389f59e861b024d0a7ae92d335ec51d29c","tree":"f5d4007ed58326d04ab0c6c17093c03ad7531ab9","clean":true,"record_exists":false,"write_gate":true}
```

`git merge-base --is-ancestor 0b0ee6c11381cf8e000858b13526d62110ec26d4 HEAD`
exited zero. The complete parent-to-candidate name range contained exactly:

1. `research_system/authority.py`
2. `research_system/cli.py`
3. `research_system/operations/backups.py`
4. `research_system/store/identity.py`
5. `tests/research_system/integration/test_external_assurance_record_cli.py`
6. `tests/research_system/integration/test_gate5_release_tranche.py`
7. `tests/research_system/unit/test_replay.py`
8. `tests/research_system/unit/test_store.py`

Therefore the candidate did not change schemas, contracts, catalogues, the
WP6.4 design, prior reviews, provider or foundation material, or Jira records.

## Authority and review method

I read the prior `eef403e` review, the WP6.4 state-machine design, P-020,
06g, the WP6/Gate 6 plan, and the WP6.4/store-identity authority sources. I
then inspected the complete eight-path diff and traced the real initialization,
loader, CLI, command-service, retry, cleanup, admission, and rollback paths.
Producer history and green-test counts were not used as acceptance evidence.

The resumed review was stopped after a decisive provenance/data-integrity
failure. Per the bounded stop instruction, no further adversarial probes or
broad validation were run, and unfinished checks below are reported as
unproven rather than assigned invented results.

## Finding counts

| Severity | Count |
|---|---:|
| Critical | 1 |
| Major | 0 |
| Minor | 0 |

## Critical finding

### C-02 remains open: the origin discriminator is locally replaceable self-attestation

**Claim under review.** Both initialization paths were required to write an
independently verifiable immutable origin such that missing, forged,
source/target-conflicting, downgraded, copied, or stripped provenance fails
closed and a rebound store can never be classified as an ordinary initialized
store.

**Expected invariant.** An initialized store's original physical root and
identity must be anchored to retained approval or evidence that cannot be
re-authored by changing the copied store itself. A copied store whose manifest
and local metadata are consistently rewritten must still require the governed
restore admission path.

**Observed mechanism.** `research_system/store/identity.py` constructs
`store-origin.json` entirely from the current manifest and an
`initial_control_root`, computes `initial_identity_sha256`, and then computes
`origin_sha256` over that same local document. Validation recomputes those
public hashes from the current manifest and origin file. The generic
initializer writes this origin beside the manifest; the authority initializer
does the same while staging. `load_store_manifest` accepts the store as
ordinary when that locally rewritten origin names the current root, so no
independent retained value distinguishes original initialization from a copied
and rebound store.

**Independent reproduction.** The probe used the required interpreter with
bytecode writes disabled:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
@'
# Create one generic store and one authority-aware store.
# For each store: copy the whole store to a different physical root; rewrite
# store-identity.json.control_root; recompute the production _manifest_hash;
# first load with the copied origin unchanged; then replace store-origin.json
# with the production _store_origin_value for the copied root and load again.
'@ | & 'C:\Users\steph\TDL\.venv\Scripts\python.exe' -
```

The probe also exercised missing, empty/stripped, downgraded, and
source/target-conflicting origin records. The captured result was:

```json
{
  "authority_copied_forged": {
    "accepted": true,
    "value": "906ad8200bfee2b3d40b15dfb3ac463cf4d2dd248587a97552147170d902e33d"
  },
  "authority_copied_unforged": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance binding mismatch"
  },
  "authority_identity_preserved": true,
  "authority_initializer": {
    "normal_load": {
      "accepted": true,
      "value": "906ad8200bfee2b3d40b15dfb3ac463cf4d2dd248587a97552147170d902e33d"
    },
    "origin_exists": true
  },
  "authority_missing_origin": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance is missing"
  },
  "copied_forged_origin": {
    "accepted": true,
    "value": "beddf260de9804fc41287a280b2cacdca10791e5f73dda4a4e2c39fc04197848"
  },
  "copied_unforged_origin": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance binding mismatch"
  },
  "generic_identity_preserved": true,
  "generic_initializer": {
    "normal_load": {
      "accepted": true,
      "value": "beddf260de9804fc41287a280b2cacdca10791e5f73dda4a4e2c39fc04197848"
    },
    "origin_exists": true
  },
  "missing_origin": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance is missing"
  },
  "self_hashed_downgraded_origin": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance values are invalid"
  },
  "source_target_conflicting_origin": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance binding mismatch"
  },
  "stripped_origin": {
    "accepted": false,
    "error": "IntegrityError",
    "message": "store origin provenance is invalid"
  }
}
```

The negative cases show that the surface validation works. They do not close
the invariant: after recomputing only values whose algorithms and inputs are
available in the copied store, both initialization families accepted the copied
store at its new root while preserving its store identity. No independently
approved origin was needed, and the restore transaction/admission path was
bypassed.

**Reachability.** This is the production loader used to bind ordinary control
stores. It is not a schema-only or dead helper path. The authority-aware case
also demonstrates that the second initializer does not supply an independent
anchor merely by writing the same local origin during staging.

**Impact.** A copied/rebound store can be made indistinguishable from an
ordinary initialized store using only coordinated local metadata replacement.
That defeats the provenance discriminator on which restore admission depends,
so the implementation cannot establish that the loaded root is the governed
original rather than an unapproved rebound copy.

**Prescribed mechanism not satisfied.** The candidate adds a self-consistent
origin record, but not the required independently verifiable immutable origin.
This is the exact invariant C-02 required, not a preference for a particular
file format or old proof vehicle.

**Closure evidence required.** Bind the initial physical origin and store
identity to a retained authority outside the mutable store set (or an
equivalently independent approved value), then independently demonstrate that
whole-set manifest/origin replacement at a copied root still fails closed for
both initialization families while legitimate initialization and governed
restore continue to load.

## Prior-finding disposition at the bounded stop

| Prior finding | Disposition in this review |
|---|---|
| C-01 native Windows directory durability | The completed direct probe opened the real directory handle with `CreateFileW`, successfully called `FlushFileBuffers`, and closed it with all Win32 errors zero. A separate probe held a visible generation-1 `prepared` transaction unconfirmed across 24 failed directory-durability retries; every retry preserved identical bytes/digest/state/generation, and restoring native durability converged to `cleared` generation 7. This evidence supports the new barrier, but C-02 independently prevents acceptance. |
| C-02 immutable origin | **Open — Critical.** Reproduced above. |
| C-03 retained approval as independent expected side | **Unproven in this bounded review.** Source/call-graph inspection was completed, but the planned coordinated record/evidence/output/actor/grant/receipt/snapshot mutation probe was not run after the stop instruction. No closure or new defect claim is made here. |
| C-04 generation-zero crash/adoption | **Unproven in this bounded review.** The deterministic temporary/adoption and closure code was inspected, but the planned subprocess and foreign/mixed-orphan cohorts were not rerun after the stop instruction. |
| M-01 same-byte physical substitution | **Unproven in this bounded review.** The Windows handle/anchor/delete-by-handle implementation was inspected, but the planned bounded Windows cohort was not rerun after the stop instruction. |
| M-02 symlink/junction/reparse ancestry | **Unproven in this bounded review.** Physical-path checks and their call sites were inspected, but the explicit inside/outside symlink and junction matrix was not rerun after the stop instruction. |

The completed C-01 retry-barrier result was:

```text
native CreateFileW opened=true, FlushFileBuffers flushed=true, CloseHandle closed=true
open_error=0, flush_error=0, close_error=0, candidate wrapper_result=true
first visible record: generation=1, state=prepared, step=output-object-durable
failed durability retries: 24
all_retries_identical=true
final native-durability recovery: generation=7, state=cleared
```

## Validation boundary and residual risk

No additional adversarial/security probes, broad suites, Ruff/format/compile
runs, or unfinished recovery cohorts were run after the decisive C-02 result
and the explicit bounded stop. Those omissions are not presented as passes.
Residual uncertainty therefore remains for C-03, C-04, M-01, and M-02, as
listed above. It cannot improve the verdict because one reachable Critical
provenance defect is sufficient to reject this exact subject.

## Verdict and authority limits

`rework_required`

Candidate `5b9e3d389f59e861b024d0a7ae92d335ec51d29c` does not close C-02. Its origin
discriminator is replaceable self-attestation rather than an independently
anchored immutable provenance claim.

This verdict applies only to the exact candidate and tree recorded above. It
does not remediate production or tests, modify or approve a PR, update Jira,
merge, bind foundation, clear A8, authorize SCALE-01 or Gate 6, invoke providers
or credentials, create external-party records, or request/poll CodeRabbit.
