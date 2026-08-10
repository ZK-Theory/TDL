# WP6.1 final assembled exact-subject review — 2026-08-10

## Executive verdict

`accept_exact_subject`

The immutable production/proof candidate at commit
`b0058f396f538a63f94ce68d8f6a49b25f4c4c8f` is accepted as the assembled WP6.1
proof subject. No Critical, Major, or Minor finding was reproduced. This verdict binds
only the candidate bytes and does not constitute owner acceptance, merge, push, Jira
transition, Gate 6 acceptance, provider action, pilot execution, or live restore.

## Exact subject and scope

- Review worktree: `C:\Users\steph\.codex\worktrees\kan75-final-review`
- Review-record branch: `codex/wp6-1-final-proof-kan75-review-record`
- Candidate commit: `b0058f396f538a63f94ce68d8f6a49b25f4c4c8f`
- Candidate tree: `327a85187ebdb11daad7d906ebd09bb9a6b0e4b3`
- Candidate parent and accepted base: `09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6`
- Refreshed `origin/main`: `09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6`
- Ancestry: both `origin/main` and the required base are ancestors of the candidate.
- Initial status: clean.
- Candidate changed paths, and no others:
  - `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`
  - `tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`

The candidate refreshes the manifest's accounted base and the independently derived
runtime-binding closure from 164 to 218 bindings. It changes neither production code
nor protected schema/catalogue bytes.

## Protected identities and catalogue closure

Direct Git-object checks at the candidate resolved:

- `.research-system/schemas/core/commands` tree:
  `8a86a0c4921343e6a3afca3f491fad33e9a8a10f`
- `.research-system/schemas/core/events` tree:
  `058c1d5ddcb9d249916977f12b11768b6d15de0f`
- `.research-system/contracts/wp6-1-owner-source-catalogue.yaml` blob:
  `1adc66921ee9c90d8786ff173748150922f1035e`

These equal the manifest's accepted authorities. The public registry census resolved
all 104 normative catalogue rows to active command bindings and found zero remaining.
The independent materialization validator reconstructed exactly 104 normalized rows
and 182 expanded lifecycle edges.

## Adversarial semantic review

The strongest attack was whether the two changed proof files merely copied current
values and could therefore certify a semantically incomplete assembled system. That
attack failed for the following direct reasons:

1. The binding digest is re-derived from the public runtime schema registry using a
   fixed six-field, LF-terminated row format. The candidate value was independently
   reproduced as 218 rows with SHA-256
   `96ac13de1e2477117e8f7741692ff8025a4b49a82b6496c6fd61e975ad2047cc`.
2. Append closure is AST-discovered across the production package and reconciled for
   exact path, symbol, receiver, and classification. Direct, aliased, nested-aliased,
   bound-method, duplicate-method, and unproved-`self` controls all passed, including
   decisive stale/unmanifested failures.
3. The selected 06h grandfather authority is byte-bound to its canonical committed
   decision, historical copy, packaged authority, selected lineage, store identity,
   tail/event-set/raw-prefix hashes, missing-triple digest, and exact ancestry. Forged
   identity, owner, date, statement, store, missing-position, and count variants failed.
4. The exact 104-row catalogue and 182-edge reconstruction are independent of the
   refreshed manifest. The public registry census independently confirmed 104 active
   and zero missing bindings.
5. The real public/production seams passed across record identities and temporal joins:
   C1 admission reached a claimed Task and running Attempt; C2 blocked that running
   Task and replayed it; C3 kept review evidence distinct from owner Decision and
   preserved append-only amendment/correction history; artefact consumption joined the
   exact P-005 Decision, governing independent review set, immutable events, resolver,
   and projections; W3 ran requested through delivered and resolved with ordered
   lifecycle and replay; and `CreateBackup`/`VerifyRestore` appended evidence-only
   receipts, replayed equivalently, and performed no live cutover.
6. The same bounded suite included the 06h invalid/stale/forged authority,
   missing-provenance, alias, changed-classification, and unmanifested-site negatives.
   The exercised public positives also assert their family-specific retry, replay,
   immutable receipt/event, authority, temporal-order, and no-mutation conditions.

The assembled evidence therefore supports the named WP6.1 capability at this exact
subject: cross-family admission/running, operating lifecycle, completion/decision,
current schema and artefact authority, immutable events/receipts, reducer/projection/
replay equivalence, W3 context delivery, and evidence-only backup/restore. No isolated
schema-validity result was used as a substitute for those public seams.

## Direct verification evidence

Identity and scope commands:

```text
git fetch origin --prune
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git rev-parse 'HEAD^'
git rev-parse origin/main
git merge-base --is-ancestor origin/main HEAD
git merge-base --is-ancestor 09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6 HEAD
git diff-tree --no-commit-id --name-status -r HEAD
git rev-parse 'HEAD:.research-system/schemas/core/commands'
git rev-parse 'HEAD:.research-system/schemas/core/events'
git rev-parse 'HEAD:.research-system/contracts/wp6-1-owner-source-catalogue.yaml'
```

All resolved to the identities and two-path scope recorded above; both ancestry checks
exited zero.

The bounded read-only pytest command used
`C:\Users\steph\TDL\.venv\Scripts\python.exe`, `-p no:cacheprovider`, and `--no-cov`.
It ran the complete 06h append-closure module plus the exact active census,
104-row/182-edge materialization, and these public seams:

```text
test_public_admission_chain_reaches_claimed_task_and_running_attempt
test_public_block_task_suspends_a_running_c1_task_and_replays
test_decision_rule_and_correction_rows_are_append_only_and_review_does_not_resolve
test_claim_consumption_binds_current_p005_owner_decision_and_review_set
test_context_packet_runs_requested_through_delivered_and_resolves
test_store_verify_restore_appends_evidence_without_cutover_and_replays
```

Result: **50 passed in 109.86 seconds**.

Producer evidence at the same exact candidate reports 62 passed in 251.16 seconds,
including the six positive seams, exact census/materialization, all 42 06h controls,
and representative invalid/retry/stale/tamper/recovery no-mutation negatives. The
repository staged-contract gate reports 103 contracts passed. Those producer results
were treated as corroboration, not as the independent verdict's sole basis.

The full `tests/research_system` run timed out after 1204.1 seconds without a terminal
summary. It is explicitly **unresolved, not green**, was not rerun, and is excluded
from the acceptance evidence. The verdict rests on the direct changed-behaviour and
public-seam evidence above.

## Findings and dispositions

- Critical: none.
- Major: none.
- Minor: none.
- Candidate controls and governing decisions: keep unchanged.
- Broad-suite timeout: retain as an explicit unresolved aggregate-gate limitation; it
  does not contradict the bounded exact-subject evidence and is not represented as a
  passing gate.

## Explicit exclusions and residual boundary

This review made no production, test, schema, catalogue, Jira, PR, provider,
credential, pilot, restore, WP6.6/WP6.7, Gate 6, or CodeRabbit change or decision. It
did not perform a live restore or cutover. Acceptance of this exact subject does not
authorize any of those actions and does not reopen already completed campaigns absent
a separately reproduced contradiction.

The only post-subject byte is this review record. Its later commit records the verdict
and does not alter or supersede the reviewed candidate commit/tree.
