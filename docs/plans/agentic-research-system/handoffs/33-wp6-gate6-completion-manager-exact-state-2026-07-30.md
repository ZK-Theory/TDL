# WP6 / Gate 6 completion manager exact state

Date: 2026-07-30
Workflow: standalone delivery
Tracker: KAN-65
Management branch: `codex/wp6-gate6-completion`

## Integrated state

- PR #199 is merged.
- Accepted A0 commit: `9df9fe07b8f1ed1de97012dd9873976b5d70dcd9`.
- Accepted remediation head: `6bff8d642e02c4d85d381d615646eb09b7360d74`.
- Merge commit on `main`: `919a11f0045f810164ea028b29bd2c3b80781619`.
- The management branch was fast-forwarded from its required start
  `9ed1fa034efd262061e820b48a58924d63ca3f3c` to that merge commit.
- The active first-slice branch is `codex/wp61-scope-task-revisions`, based
  exactly on `919a11f0045f810164ea028b29bd2c3b80781619`.

The final PR #199 exact-subject review accepted the subject. Focused validation
passed 143 schema/release tests, 112 command/store/replay tests, both contract
framework modes over 103 contracts, the P-045/protected-membership pair, and
the repository-root path test. The final authority plus Gate 5 cohort exposed
four pre-existing WP6.1 lifecycle defects: same-task higher revisions were
rejected, stale replacements were misclassified, incompatible replacements
were accepted, and continuing-consumer drift was accepted.

KAN-64 is Done with the merge and test evidence. KAN-65 is In Progress and owns
the remaining WP6.1 catalogue. The first slice below resolves all four defects
without changing accepted contract bytes.

## Current bounded delivery

The dependency-leading slice contains six catalogue rows:

1. `scope.create`;
2. `scope.amend_revision`;
3. `scope.supersede`;
4. `task.create`;
5. `task.amend_revision`;
6. `task.supersede`.

A0 already activated `CreateTask -> TaskCreated`, so the runtime-binding delta
is five command/event pairs. The candidate now proves all six rows across
schema binding, payload construction, immutable revision state, reducers and
projections, replay/history, idempotency, project and schema authority binding,
and decisive negative cases.

The accepted command and event schema subtrees remain protected. No accepted
WP6.1 schema, catalogue, identity, or acceptance-record byte may change in this
delivery. Generic pre-cutover history must remain replayable, while newly
activated events are selected by their recorded schema identity and version.

The implementation binds exact command and event identities, command payload
hashes, subjects, projects, revisions, and immutable object content. It
validates amendment deltas and supersession graphs during both submission and
replay; rejects missing, stale, terminal, cyclic, incompatible, or
under-dispositioned replacements; preserves the narrow generic same-task
higher-revision compatibility path; and rejects rich same-task orphan
activation. Scope and Task object revisions are checked against their
committed exact event content, including coordinated content-addressed
replacement.

The first precommit review returned `rework_required` for three roots:
incomplete replay graph/provenance parity, no-op amendment acceptance, and
shape-based generic/rich Task classification. All three were reproduced,
remediated, and covered by durable negatives. A separate residual audit found
that restore preflight and authority-store exact retry supplied inert
registries to whole-ledger replay. Both now use the accepted runtime bindings;
payload-backed authority events retain their exact payload validation under
that registry. Event-bearing restore and authority-retry regressions prove the
two paths.

Current validation at the candidate content:

- 94 store, lifecycle, Gate 5, and restore tests passed;
- 56 command-service, replay, canonical-ID, and exact runtime-binding tests
  passed;
- 6 authority genesis, schema-binding, revocation-restart, and exact-retry
  tests passed;
- after hook formatting, the final combined lifecycle, Gate 5, authority exact
  retry, command-service, and replay cohort passed 116/116;
- Ruff and `git diff --check` passed;
- all 173 accepted command/event schema files remain byte-identical to the
  integrated base.

The full authority integration module exceeded a 15-minute execution bound
without emitting a pytest verdict. It is recorded as a timeout, not a pass or
failure and not acceptance evidence; the six-test changed-path cohort above is
the decisive authority validation for this slice.

Post-genesis lifecycle authority-grant enforcement remains assigned to WP6.3;
this slice does not fabricate authority or widen the publication-only bootstrap
grant.

## Remaining campaign sequence

After this slice: finish the remaining WP6.1 lifecycle slices; implement the
scoped WP6.3 authority grant, external record writer, and production acceptance
runner; complete the owner-operated WP6.4 preflight; finish WP6.5-WP6.7 and
their live Jira tickets; record WP6.2 provider automation as deferred under
P-042; then run the final Gate 6 integration suite and durable acceptance
reconciliation.

No provider invocation, credentials, live research execution, fabricated
authority, or producer self-review is authorized.

## One next action

Commit and push this bounded candidate, open its sub-100-path PR, and obtain a
fresh independent exact-subject review before merge.
