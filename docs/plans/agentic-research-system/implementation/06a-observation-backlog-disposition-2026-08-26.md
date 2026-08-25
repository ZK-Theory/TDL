# WP6 Gate, Invariant, and Process Backlog Disposition

Date: 2026-08-26
Governing plan: `06-wp6-gate6-readiness-and-integration-plan.md`
Subject main SHA: `6b72a26726e737adbafd12260558cf1d3164b4ec`

## Purpose and authority

This ledger records the owner-approved disposition of the observations enumerated by
`34-observation-backlog-handoff-2026-08-25.md`. The governing plan named above
supersedes earlier, conflicting WP6 planning mechanics. This is a backlog decision
record, not evidence that Gate 6 has passed or that the WP6 capability is integrated.

Disposition meanings:

- `ACTIONED`: current-main code, tests, or an adopted operating rule implements the
  observation's requested control.
- `SUPERSEDED`: the observation targets retired work or conflicts with the governing
  plan.
- `DECLINED`: the proposed mechanism is not being adopted; the underlying principle
  may still guide work.
- `OPEN`: a current functional, evidentiary, or owner-system gap remains.
- `ROUTED`: the observation belongs to another repository or owner surface.
- `OWNER-ONLY`: resolution requires changing accepted/protected authority bytes or an
  owner-controlled external system; it is not implementer-authorized work for this PR.

## Schema and identity

| Observation | Disposition | Basis |
|---|---|---|
| `01M0GPWXK3RYSW5HQV9CWRKB5G` | ACTIONED | The schema identity history and registry resolve exact superseded bytes. |
| `2026-08-22-deterministic-id-retrofit-erased-historical-state` | SUPERSEDED | The defect belonged to the retired, unmerged SpecFlow design. |
| `01KZZ56Y8ZSJWCF0D13EX447B5` | ACTIONED | Lineage-only schemas are explicitly distinguished from current authority. |
| `01M065H67WF1BT5ZY8FTZFXPVY` | ACTIONED | Public intent uses separately typed, validated schema identities. |
| `01M0NVDGS4CBFMH6RYFCMK2Y01` | ACTIONED | The release snapshot contract is checked against the producer. |

Evidence packet: 5 focused tests passed, including exact historical-byte resolution,
release-snapshot producer parity, public intent reading, and current-binding drift.

## STORE cleanup and recovery

| Observation | Disposition | Basis |
|---|---|---|
| `01M0P48MTW2G1ZY1M7RJ7GG6SM` | ACTIONED | Fail-closed poisoned cleanup is covered directly. |
| `01M0P8Z0SW8RK6BWA1YP54ZC2J` | ACTIONED | Cleanup is anchored to the physical generation. |
| `01M0Q19XP9P3R6B1CF9TS6BF3Z` | ACTIONED | Link receipt is persisted immediately. |
| `01M0Q5WWJTYMEX0CJFVK1A2Z8Z` | ACTIONED | Retry survives the safe point. |
| `01M0QAD7EVJ5RK5XQJV9TMWHCQ` | ACTIONED | Full owner state is retained for recovery. |
| `01M0QC2T5RFAAV3SEVWCDA4YNC` | ACTIONED | Caller-frame drain is covered. |
| `01M0QAFYK52K1C6YMZ0KJ6JMN9` | ACTIONED | Domain snapshots now exclude `runtime/`; protocol snapshots bind exact bytes, physical identity, and timestamps, permit only the fixed guard after denial, reject residue by exact-set comparison, and remain identical across retry. |

Evidence packet: 9 focused Windows tests passed.

## Replay and authority propagation

| Observation | Disposition | Basis |
|---|---|---|
| `01M02FCZWS5EKPER5XYKJ8CZJE` | ACTIONED | Recursive Discovery calls retain the validator. |
| `01M0668E8R3B941Z3KJRC0XK9D` | ACTIONED | Release publication now constructs one canonical authority resolver and passes its administration validator into the single replay used by every reference in the operation. |
| `01M06KMJM5VVR1MMGM59D0AS2M` | ACTIONED | Local store administration remains bound to the store's `LedgerAuthorityGrantResolver`; external artefact semantics remain bound separately by the content-addressed artefact consumer/resolver. The publication seam no longer substitutes one role for the other. |
| `01M06KDPPT6AYE3Y0S4XKY7D7Z` | ACTIONED | Release publication now freezes one ledger snapshot and one replay result before constructing the per-reference closure. A two-reference control proves one snapshot, one replay, and one validator invocation. |
| `01M0N26XTRERJH5M2PT7ZZ1JDT` | ACTIONED | The public artefact-use resolver binds replay registration, immutable manifest/object state, resolved external bytes, exact SHA-256, and size; substituted bytes fail read-only. Focused evidence: 6 resolver controls passed. |

Three direct propagation controls passed. The CLI replay control did not reach replay:
persisted binding evidence names a missing Codex worktree schema store. This is recorded
as current-main configuration drift, not as a candidate regression and not as green
replay evidence.

## Process

| Observation | Disposition | Basis |
|---|---|---|
| `01KZK529D6RRSG25B6C8T10TR6` | ACTIONED | Four focused controls prove the atomic prefix cut. |
| `01KZYZV73TPBSJNAPBKA73TFMP` | ACTIONED | Baseline truth before implementation is adopted in current procedure. |
| `01M0JEKDT55EG2AAWCCJ1HEEFK` | ACTIONED | The supervision procedure now has a bounded rescope stop after repeated final remediation. |
| `01M0KXHJP4701QHA4FH6BB5D07` | ACTIONED | Explorer evidence must include the current repository and remote delta. |
| `01M0P5ZCBYR5HT1V47F2G1X7D2` | ACTIONED | Final review evidence must be external and exact-head. |
| `2026-08-24-plan-as-overengineering-vector` | ACTIONED | The owner selected the smaller governing plan and superseded the conflicting mechanics. |
| `01M0KTDNNMXXVP88WWFRRPK49E` | SUPERSEDED | Its competing-plan premise is displaced by the owner's governing-plan decision. |
| `01M0N5A18XF2FJV93J6PCF3K0J` | SUPERSEDED | Its SOURCE-before-STORE sequence belongs to the superseded campaign. |
| `01M0NMFM1R8GG5W183ND0YJ33Z` | DECLINED | Do not add an automated module-cohesion gate. |
| `01M0TD1B8W1PY7J0QXJC5Y08X6` | DECLINED | Do not add a campaign-demotion or scope-budget hook. |
| `2026-08-18-quarantined-checkout-not-mechanically-blocked` | DECLINED | Do not add a quarantine trip-wire. |
| `01KZMNV2ZQ3A2MDC9JN0XE9G13` | ACTIONED | The final-review contract below requires the real acceptance seam and its cross-record identifiers; isolated schema/review validity is explicitly insufficient. |
| `01KZMYBM61C5QDY995MXN3FCHS` | ACTIONED | The final-review contract below requires the real preparation/acceptance entry point and the full chronology tuple; a narrower virtual projection cannot claim equivalence. |
| `01KZMZJ0489J0R0EHB94P0BACA` | OWNER-ONLY | Jira parent reconciliation requires authenticated owner-authorized Jira mutation and link readback. |
| `01KZN1N4CWERHRZ6HWEHGX0BCA` | SUPERSEDED | The historical module-global publication helper is absent from the current governed publication seam, which uses typed authority context. |
| `01KZYX3JFKQ3XQD8N9S8MFKTJW` | OWNER-ONLY | Correcting Jira-side owner-blocker wording requires authenticated owner-authorized Jira mutation and readback. |

The three declined mechanisms must not be recreated indirectly. Their general
principles remain available for proportionate design decisions.

## Older WP6 observations

| Observation | Disposition | Basis |
|---|---|---|
| `01KZKCZYZF4TRYVMWSC4Z60MZ0` | ACTIONED | Manifest authority metadata is present. |
| `01KZR0P7WS2FMC2DG6D42PDRD2` | ACTIONED | Terminal promotion routing is implemented. |
| `01KZWYYAG485N6XQ7BAWYX86BB` | ACTIONED | Discovery transaction semantics are implemented. |
| `2026-08-12-conditional-namespace-in-a-global-identity-fence` | ACTIONED | The pre-genesis identity fence is enforced. |
| `2026-08-12-partial-application-of-a-new-enforcement-pattern` | ACTIONED | Same-transaction dossier binding is enforced. |
| `01M02E379MRA7C8SJ953QR0C1T` | ACTIONED | Mixed scoped-grant schema replay is covered. |
| `01KZZ84DZNGBQYSJ1WEYP85PBY` | ACTIONED | Pre-publication crash recovery is covered. |
| `01M084RS15MANFKZR2HQYP82R5` | ACTIONED | Owner-row handling is candidate-qualified. |
| `01M08ZABERS77G9G7YT5WH6BHY` | ACTIONED | Terminal provenance is separated from semantic identity. |
| `01M0N26XWWD3N7AHCMQ87YVWH2` | ACTIONED | No-replace cleanup behavior is covered. |
| `2026-08-22-focused-tests-masked-import-cycle` | ACTIONED | Cold-import and import-cycle controls exist. |
| `01KZP0F2TWTQ9BTVPVE02NMRSW` | SUPERSEDED | The observation targets the historical caller-built W4/W7 context-packet transition. The governing Gate 6 path uses persisted artefact authority and content-addressed consumer resolution instead. |
| `01KZQ8225BFXSTAZBFNM2JCPAV` | DECLINED | Do not add a generated repository-wide matrix over implementation-level direct indexing. Retain bounded public-seam malformed-input/no-mutation negatives where governed inputs are decoded. |
| `2026-08-12-wp61-lane-lacks-t2-independence-guard` | OWNER-ONLY | The requested generated guard requires adding artifact roles to protected membership/identity contracts and therefore changing exact accepted bytes. Owner action: authorize and accept a new contract revision before implementation. |
| `2026-08-13-exemption-granularity-mismatch` | ACTIONED | `TransactionVariant.command_payload_binding` and `STATEFUL_COMMAND_VARIANTS` bind exemptions to exact `(row_id, event_types)` variants; satisfied variants retain durable digest binding. Nine focused transaction controls passed. |
| `01M083VSDNA910RQXWRAPZC66F` | ACTIONED | `AdoptLateArtefact` now enforces `terminal_recorded_at < late_observed_at <= command.submitted_at`; the positive derives from the terminal event and a future claim is rejected without domain publication. |
| `01M083YZH31FKM1DASB8VZ5K3A` | ACTIONED | Release publication context now requires non-empty string `content_sha256`, `task_id`, and `accepted_scope` fields before constructing the consumer context; missing or wrong-type values fail closed without coercion. |
| `01M08470YEG5EX6X168AGPA0ZM` | ACTIONED | A real Windows child now exits while owning `WriterLock`; native `GetExitCodeProcess` establishes death, the stale generation is reclaimed, and the next writer enters. The paired live/recycled-owner controls also pass. |
| `01M084XV9K5T9J5RSQ9CNG0AYN` | ACTIONED | Accepted artefact authority now rejects caller evaluation time later than the injected trusted service clock before evidence resolution or publication. |
| `01KZY8D591593SM3BW9KJCM5PT` | ROUTED | Codacy tool/rule configuration and emitted evidence belong to the external Codacy service configuration surface. |
| `01M03BG9WHTFRCPATN3F49G2F0` | SUPERSEDED | The affected head-only tag implementation is absent from current main. |

The representative 35-test packet produced 33 passes and 2 failures. Both failures
were diagnostic-order drift: malformed history failed earlier at event-schema
validation than the tests' later semantic-error regex allowed. Invalid history was
still rejected. The packet is therefore not reported as green.

## Cheap gates, escalations, and external routing

| Observation | Disposition | Basis |
|---|---|---|
| `2026-08-11-post-commit-repowise-guard-untested` | OWNER-ONLY | Adding a repository-wide post-commit hook control requires owner approval of hook behavior and side effects. |
| `2026-08-11-results-no-overwrite-untested` | ACTIONED | `test_eval_run_refuses_overwrite` exercises the public CLI, requires a nonzero result for an existing output, and proves the pre-existing bytes remain identical. Focused evidence passed. |
| `2026-08-13-crlf-byte-surface-unenforced` | OWNER-ONLY | Rejecting CRLF on accepted byte surfaces is a repository-wide policy change requiring owner approval before enforcement. |
| `2026-08-11-no-mechanical-premerge-review-gate` | OWNER-ONLY | Enforcing unresolved-thread state before merge requires owner-controlled GitHub branch/ruleset configuration and a live probe. |
| `01M0PWSR73ABY48X8YW7KQX6Q6` | OWNER-ONLY | Merge-thread invalidation is enforced on the owner-controlled GitHub merge surface, not by this bounded repository candidate. |
| `01M0Q0WXJSCX5WJ69H2G9DG4E3` | OWNER-ONLY | Linux-before-review ordering requires owner-controlled GitHub workflow/ruleset changes and a live probe. |
| `2026-08-09-commit-gate-repowise-tracked-write` | OWNER-ONLY | A side-effect-free Repowise commit gate needs an owner-approved repository-wide hook design. |
| `01KZK2BCXT7EKFZ6ZM2AMKFXJR` | OWNER-ONLY | Changing historical-store lineage is a durable record-authority design decision reserved to the owner. |
| `01KZW6BZYXZX7JGB85MXKTA007` | ROUTED | This belongs to the separate `codex_workflow` repository. |
| `01KZW6Y38D80D3HZCQ4089XYV8` | ROUTED | This belongs to the separate `codex_workflow` repository. |

## Result and next production action

This pass removes resolved, superseded, declined, and externally owned items from
the active TDL implementation backlog without claiming Gate 6 completion. No row in
this disposition remains `OPEN`; owner-only and routed work remains explicitly
outside this candidate rather than being presented as resolved.

Owner direction on 2026-08-26 skips the legacy persisted-binding repair pending
confirmation that the replacement Gate 6 process still consumes that mechanism. The
stale binding is therefore not a campaign blocker or the next implementation action.

The domain/protocol snapshot item `01M0QAFYK52K1C6YMZ0KJ6JMN9` is now actioned.

## Final review and Gate 6 evidence contract

Independent review of this candidate must exercise the real public
preparation/acceptance entry point, not isolated schema validators or a virtual
projection. The review handback must record:

- the exact candidate commit and the exact persisted contract, schema, producer,
  pack-review, and provisional owner-record identities used by the probe;
- the cross-record identifiers that the real acceptance seam requires to be equal;
- the chronology tuple `relationship effective_at <= requirement accepted_at <=
  pack authored_at <= evaluation_time`; and
- the exact public-run result, including any no-write failure result.

A later real Gate 6 run must still use paid AI services and real persisted outputs;
mocks, temporary stores, fabricated permissions, synthetic receipts, and
agent-written declarations do not prove Gate 6.
