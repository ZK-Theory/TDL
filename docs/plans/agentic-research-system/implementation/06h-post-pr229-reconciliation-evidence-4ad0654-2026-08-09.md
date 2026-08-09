# WP6.1 06h post-PR #229 reconciliation evidence

**Evidence date:** 2026-08-09

**Branch:** `codex/wp6-1-kan95-06h-reconcile-9736c90`

**Integrated live main:** `35f20340a026aafdd4eb17a594eff8a079f6a493`

**PR #229 merge ancestor:** `a1c917f7e313d9636509795c525d12f97b695be3`

**Preserved G-RM-8 candidate ancestor:** `3ec6a5fdd002443456488e65ba21b124a8df1a97`

**Production candidate:** `4ad065464c5e51f4cc0e4e633af910a548f2c697`

**Production candidate tree:** `e919f54b3e49fe511f9266581099829b166ab46f`

## Capability status

Capability status is **INCOMPLETE**. The real current-producer path, immutable
`RegisteredSchema` identity, complete append-site accounting, owner-selected
G-RM-8 exact-prefix protocol, and final post-PR #229 binding census are
constructed and proven. The exact remaining 06h gap is one fresh no-history
review of the complete exact subject, followed by Stephen's separate acceptance
of that reviewed subject.

No canonical Control mutation, PR creation, merge to main, CodeRabbit action,
06i, G-RM-14, C2 mutation, provider action, Gate 6 closure, C3, or R1 action was
performed by this reconciliation.

## Integrated subject and protected authority

Merge candidate `4ad0654` has first parent `3ec6a5f` and second parent
`35f2034`. It therefore preserves the owner-selected G-RM-8 implementation and
the exact current live-main lineage without rebasing or rewriting either one.

The following protected identities are byte-for-byte unchanged on the
candidate and live main:

| Authority | Exact Git identity |
|---|---|
| Accepted owner source catalogue | blob `1adc66921ee9c90d8786ff173748150922f1035e` |
| Core command schemas | tree `8a86a0c4921343e6a3afca3f491fad33e9a8a10f` |
| Core event schemas | tree `058c1d5ddcb9d249916977f12b11768b6d15de0f` |

The merged PR #229 methods schema is outside those protected core trees. Its
singular `review_subject` export/import invariant passed at the integrated
candidate through the real brief round trip and methods-pack contract.

## Final G-RM-9 census

The public runtime inventory at `4ad0654` contains exactly 112 active bindings.
The deterministic rows
`schema_id|schema_version|command_type|event_type|producer_command_type|policy_action_type`
retain SHA-256
`4b7a5b1813415f360e12d40341320444fc13334a6cb78690effd0695eb4b2b6a`.

The source-derived append census remains exactly six sites: the generic command
service, T2 producer, authority bootstrap, two Control evaluation fixtures, and
the recovery fixture. The executable AST reconciliation found no unmanifested
or stale append site after PR #229 and the intervening live-main merges.

## Frozen Control prefix revalidation

Two independent public-ledger reads before repository reconciliation observed a
stable contiguous tail at global position 79 with exact event hash
`aaa83100505c0f8298a334904e0c969f89bd73cb7ee2fbbbee20d020316b17bb`.
The store identity remained
`2df87684ef33136d85adff91d58a8e91fc31a061a53ced6932988df4e687cd7a`,
the tail event remained `ArtefactRegistered`, and `runtime/writer.lock` was
absent before, between, and after the two reads. The canonical Control store was
not written.

The attributed decision continues to bind only the exact 79-event prefix and
its zero missing-triple set. Later events are not grandfathered and must carry a
complete valid command-schema triple. The historical fact that no pre-06h suite
freeze is reconstructible remains unchanged; no substitute baseline was
created.

## Exact-head validation

Interpreter: `C:\Users\steph\TDL\.venv\Scripts\python.exe`.

Pytest plugin autoload, bytecode, cache, and coverage were disabled for the
focused commands.

- Real public generic append first: **1 passed in 6.47 seconds**.
- Exact immutable identity, 112-binding census, six-site reconciliation,
  generic/T2 missing-triple rejection, and planted unmanifested-site controls:
  **12 passed in 17.71 seconds**.
- Mandated G-RM-8 candidate-head modules (`schema_registry`, `command_service`,
  T2 runtime, replay, and grandfather prefix): **168 passed in 283.19 seconds**.
- PR #229 export/import unit modules, real brief round trip, and methods-pack
  contract: **27 passed in 82.26 seconds**.

The validation ran against committed production candidate `4ad0654`. A delayed
Repowise index refresh rewrote only `.claude/CLAUDE.md` and
`.repowise-workspace.yaml`; both generated setup files were restored to their
proven-clean `HEAD` bytes before this evidence record was written.

## Next action

Freeze and push the evidence packet head, then commission exactly one fresh
no-history independent reviewer against that exact subject. If the reviewer
returns no required findings, present the exact reviewed subject to Stephen for
the separate G-RM-9/06h acceptance decision. `artefact.register`, 06i Stage A,
and G-RM-14 remain blocked until that acceptance.
