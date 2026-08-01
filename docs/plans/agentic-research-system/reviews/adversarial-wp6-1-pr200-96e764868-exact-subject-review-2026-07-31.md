# WP6.1 PR #200 exact-subject semantic review

**Date:** 2026-07-31  
**Verdict:** `rework_required`  
**Findings:** 0 Critical, 1 Major, 0 Minor  
**Immutable reviewed subject:** `96e764868eb7b52b4a4543ca3ff0152ac33265fa`  
**Required base / sole parent:** `919a11f0045f810164ea028b29bd2c3b80781619`  
**Reviewed branch:** `codex/wp61-scope-task-revisions`  
**Remote binding:** `origin/codex/wp61-scope-task-revisions` resolved to the reviewed subject

## 1. Executive verdict

The exact subject correctly activates the six accepted command/event pairs for
`scope.create`, `scope.amend_revision`, `scope.supersede`, `task.create`,
`task.amend_revision`, and `task.supersede`. It binds exact command and event
schema identities, records command-schema hashes, builds the accepted payload
shapes, preserves immutable Task and ScopeDefinition revision evidence, projects
and replays exact and generic pre-cutover history, binds committed idempotency
to actor/grant/command/schema/payload/stream/version, rejects foreign project and
subject substitutions, and propagates the runtime registry through restore and
authority-store exact-retry paths. The accepted 87 command and 86 event schema
files, and the protected WP6.1 catalogue/identity/acceptance records, are
unchanged from the base.

One accepted row is nevertheless not semantically closed. A non-empty
`AmendScopeDefinition` member change is accepted solely because it is present
and has a unique member ID. The service does not prove that it changes the
current typed membership. Consequently it accepts and publishes:

- an identical existing member as a false new revision;
- a removal whose declared `member_kind` contradicts the committed member kind;
  and
- an `amendment_authority` projection change while `changed_fields` declares
  only `members`.

The same permissive materialization runs during replay. This violates the
versioned amendment-delta contract and the subject's claim that submission and
replay reject no-op revisions. The subject therefore requires rework before
merge.

Direct post-genesis lifecycle grant enforcement is deliberately treated as a
WP6.3 dependency, not as a defect in this slice. This review does not interpret
green tests, the review record, or a future merge as owner acceptance.

## 2. Identity, scope, and authority

Before review:

- cwd and Git top-level both resolved to
  `C:\Users\steph\.codex\worktrees\6f50\TDL`;
- the symbolic branch was `codex/wp61-scope-task-revisions`;
- `HEAD` and the remote branch both resolved to the immutable reviewed subject;
- the required base was the subject's sole parent and an ancestor;
- the only pre-existing worktree changes were Repowise setup state in
  `.claude/CLAUDE.md` and `.repowise-workspace.yaml`; neither was touched,
  staged, reverted, or used as review evidence.

The governing boundary was reconstructed from:

- handoff 32 §§0, 5A0, 6, and 9;
- implementation plans 06 §§3, 6, 7, and 9; 06g §§1-7; and 06a §§2-6;
- the KAN-64 command-schema currency review;
- the WP6.3 control-store acceptance mechanics review, only for the deferred
  authority boundary;
- the accepted W2 versioning, ScopeDefinition, command, and supersession rules;
  and
- the accepted 06d six-row catalogue records and closed negative profiles.

The six rows remain one bounded WP6.1 vertical. The accepted catalogue requires
actual versioned ScopeDefinition membership, exact prior revisions, typed member
changes, immutable history, and the `NS` negative profile for
`scope.amend_revision` (`06d`, lines 53-68 and 219-224). W2 states that a changed
definition creates a new immutable revision and authorizing event, and that a
ScopeDefinition has versioned membership and typed dispositions
(`design/02-task-event-and-artifact-schema.md`, lines 207-217 and 375-388).

## 3. Blocking finding

### M-1 — Major — ScopeDefinition amendment deltas are shape-checked but not bound to the committed typed membership

1. **Claim.** `scope.amend_revision` can publish a semantically false revision
   because the candidate proves only that `member_changes` is non-empty and its
   IDs are unique. It does not prove an actual typed membership delta.

2. **Evidence.**

   - The service requires only `changed_fields == {"members"}`, a non-empty
     `member_changes` list, unique member IDs, and presence of the prior object;
     it then returns the payload without comparing the current and proposed
     materialized memberships
     (`research_system/command/service.py`, lines 1138-1184).
   - The reducer removes by member ID without checking the committed
     `member_kind`, overwrites an existing member even when the replacement
     triple is identical, copies `amendment_authority` into the materialized
     definition, and advances the revision
     (`research_system/command/reducers.py`, lines 387-416 and 444-479).
   - The durable no-op test covers only `member_changes: []`; it does not attack
     a non-empty but unchanged typed member record
     (`tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py`,
     lines 1671-1725).
   - An independent exact-subject probe created revision 1 containing
     `(TASK_A, task, accepted)`, then submitted revision 2 with the identical
     tuple. The receipt was `accepted`, replay advanced to revision 2, the
     revision-1 and revision-2 member lists were equal, and two events were
     committed.
   - A second probe removed the same committed Task member while declaring
     `member_kind: scope` and changed `amendment_authority` while declaring
     `changed_fields: ["members"]`. The command was `accepted`; replay removed
     the member and projected the new authority string.

3. **Concrete failure scenario.** A caller submits a syntactically non-empty
   amendment that repeats current membership or names the right member ID under
   the wrong kind. ARS records `ScopeDefinitionAmended`, writes an immutable
   revision object, advances the current revision, and presents the resulting
   projection as a governed membership change even though no valid typed delta
   occurred. Downstream completion or supersession can then bind to a revision
   whose change record is false.

4. **Impact.** The canonical ScopeDefinition revision history no longer proves
   what changed. Typed membership and amendment-authority projections can drift
   from the declared delta, weakening the exact-revision basis for later scope
   completion, supersession, audit, and recovery.

5. **Recommended disposition.** Fix in this slice and obtain a fresh review of
   the new exact subject. Do not merge this subject.

6. **Required interface change.** Before object or event publication, derive the
   current typed member map from committed exact history, apply the proposed
   change set, and reject:

   - a change set whose materialized typed member map is unchanged;
   - removal or replacement of an existing member under the wrong
     `member_kind`;
   - removal of an absent member; and
   - any projected definition-field change not represented by
     `changed_fields`.

   Apply the same independently derived checks in replay. Add submission and
   replay negatives for a non-empty identical member, wrong-kind removal, and
   absent-member removal. Preserve the accepted schema bytes unless a separate
   exact-byte defect and owner-authorized schema subject are established.

7. **Affected decisions and contracts.** P-012 ScopeDefinition authority; W2
   §§7.2, 10.2, and 19.2; 06a T1/T8; 06d `scope.amend_revision` and its `NS`
   profile.

8. **Affected work packages.** WP6.1 first lifecycle slice. The deferred WP6.3
   grant-issuance package is not part of this remediation.

## 4. Six-row disposition matrix

| Accepted row | Exact pair | Disposition |
|---|---|---|
| `scope.create` | `CreateScopeDefinition -> ScopeDefinitionCreated` | Closed for this subject: exact active binding, subject/project binding, immutable object, reducer/projection, replay, and create negatives passed. |
| `scope.amend_revision` | `AmendScopeDefinition -> ScopeDefinitionAmended` | **Open — M-1.** Exact binding and ordinary revision flow pass, but the semantic member delta is not closed. |
| `scope.supersede` | `SupersedeScopeDefinition -> ScopeDefinitionSuperseded` | Closed for this subject: current replacement, terminal/cycle, exact member-disposition, subject, replay, and history negatives passed. |
| `task.create` | `CreateTask -> TaskCreated` | Closed for this subject: A0 binding retained; definition identity/project/content hash, object/event equality, idempotency, replay, and generic-history boundary passed. |
| `task.amend_revision` | `AmendTask -> TaskAmended` | Closed for this subject: current consecutive revision, immutable source/replacement binding, actual typed-field delta, replay, and no-op negatives passed. |
| `task.supersede` | `SupersedeTask -> TaskSuperseded` | Closed for this subject: current existing compatible replacement, terminal/cycle, disposition, generic/rich provenance, orphan, replay, and history negatives passed. |

## 5. Verification evidence

- `git diff --check 919a11f0..96e76486` — passed.
- Accepted schema subtree check — 87 command schemas plus 86 event schemas;
  byte diff from the required base was empty.
- Protected WP6.1 catalogue, schema-identity manifest, and stage-2 owner
  acceptance record — no changed paths.
- Focused lifecycle module:
  `test_wp6_1_task_scope_lifecycle.py` — **28 passed**.
- Exact restore/history propagation:
  authority-store exact retry, restore-preflight replay, and pre-cutover generic
  Task replay/resolution — **3 passed**.
- Independent semantic probes — both reproduced M-1 with accepted receipts and
  replayed invalid revisions.
- CodeRabbit was not requested, triggered, polled, or awaited.
- No full repository or full authority-module run was performed; the bounded
  tests above exercise the changed six-row surface and the two registry
  propagation seams.

## 6. Deferred boundary and residual risk

Per the review assignment, direct post-genesis lifecycle authority enforcement
remains assigned to WP6.3 and is not a finding here. Handoff 32 and the current
WP6.3 mechanics review describe a scoped post-genesis grant path primarily for
`accept_r3_assurance_requirement`; the future WP6.3 delivery must explicitly map
the six Task/Scope command types and their project/subject scopes rather than
assuming that acceptance grant covers them.

The five closed rows above are closed only relative to this exact subject and
the stated authority deferral. They are not owner acceptance, permission to
merge, or evidence that later WP6.1 catalogue rows are implemented.

## 7. Final decision

`rework_required`
