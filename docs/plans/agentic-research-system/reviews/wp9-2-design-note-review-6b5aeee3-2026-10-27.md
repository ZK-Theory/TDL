# WP9.2 design note review at `6b5aeee3`: the legacy runtime, genesis, shared replay and CLI

**Date:** 2026-10-27<br>
**Subject:** `transition/w9/wp9-2-design-note.md`, revision 1, as committed in `6b5aeee3` on the local branch
`pipe/w9-wp9-2-legacy-runtime` (parent `f01505ff`, P-076; base `main` at `eab253f6`, tree `0962a5a4`).<br>
**Mode:** An independent adversarial review in a fresh session (`adversarial-design-review`), as P-076 item 2.2
requires. The U-7 probe was re-run from the kept files, and then re-run with the note's own site-1 shape. Every
identity the note cites was recomputed at `eab253f6`. All probe edits were made in this review worktree, reverted, and
not committed. No ARS store was opened except stores the tests create under a temporary directory.<br>
**Governing texts:**
- 06v, `implementation/06v-w9-implementation-plan.md` (WP9.2 at lines 333-399, §2.8 U-7 at line 163, §3 at lines
  167-218, §8 at lines 610-620);
- W9, `design/09-migration-compatibility-and-pilot.md` §5.3 (lines 254-275);
- the stage B design note, `transition/w9/wp9-1-stage-b-design-note.md`;
- the bootstrap contract `.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml` (blob `96a63114`);
- the W9 schemas under `.research-system/schemas/contracts/w9/`;
- the accepted catalogue `.research-system/evals/expected/w9-legacy-integration-v1.json` (blob `d1916ffd`);
- the B2 review `reviews/wp9-1-stage-b2-review-ea989c7e-2026-10-27.md` (i-3, i-4, i-5);
- P-064 to P-076 in `03-decisions-and-open-questions.md`.

**Known limit (P-058):** the author and this reviewer are on one model family. Recorded as a limit, not a finding.

## Verdict

**`rework_required`** (narrow). One Blocking finding, eight Major, twelve Minor.

U-7 itself holds. The shared-replay edit **can** be confined to the four sites, so the package does not stop. But it
holds only with the prototype's site-1 shape, which the note rejects. The shape the note chooses for the code PR keeps
the lifecycle-binding check for legacy events. That check refuses every schema-valid W9 review and Decision event in
both replay paths. This review reproduced the refusal. Those events belong to 43 of the 61 catalogue rows (B-1).

The rest of the note is sound in direction. Its identities are exact, the probe's other claims reproduce, and
owner points A and C are well chosen. Owner points B and D need rework:
- Point B leaves one required out-of-store ref unaddressed: `independent_observation_ref`.
- Point B's collision argument does not hold, because ARS review and Decision IDs are pre-assigned by the caller.
- Point D's three-PR chain comes from a departure the note does not flag. P-075 records that the envelope cites the
  merged contract `96a63114`, and the note cites an amended contract instead. Kept to P-075, the chain needs two PRs.
- The package also needs edits outside P-076's Boundary line, chiefly `research_system/authority.py`, without which
  no genesis grant can be activated.

A revision 2 that fixes B-1 and M-1 to M-8, followed by a narrow confirmation, should be enough. No finding asks
Stephen to reverse an accepted decision.

## Checks requested by the brief

| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | Every whole-ledger replay path, including verify-restore and `DiscoveryRuntime`'s pre-command replay | **Pass, with m-5** | §A3. Every whole-ledger reducer goes through `_replay` (sites 1 and 4) or selects partitions by equality. That includes `backups.py:1025,1493,1793` and `verify_restore_before_writer_lease` (`backups.py:1638`). `DiscoveryRuntime`'s pre-command replay (`discovery/runtime.py:474-479`) calls `replay_discovery`, whose shared replay passes `validate_discovery_semantics=False` (`projection/replay.py:1199`). So `replay_legacy` never runs before a Discovery command (m-5) |
| 1b | C1 to C4 complete | **Fail (M-1), with m-11** | C3 states a condition the code does not impose, and that the closed W2 payloads cannot meet. A fifth condition is missing (m-11) |
| 1c | Site-1 shape sound, given the lifecycle check the prototype skipped | **Fail (B-1)** | §A2. Reproduced: with the check kept, a C2-compliant `ReviewRequested` under `RequestW9AuthorityReview` is refused by `replay` and `replay_discovery` with "exact lifecycle event provenance mismatch". With the prototype's skip, both pass |
| 1d | Reproduce the probe | **Pass, with m-10** | §A1. Every message in note §2.2 reproduces. Two rows have no kept test, and three kept tests print without asserting. The five fast suites pass against the prototype: 339 passed in 86 s |
| 2 | Owner point A | **Keep (a), with m-2** | The predicate's 12 command types equal the catalogue's 12 (§A4). The rows for genesis only are consistent with 06v WP9.2 ("each W9 command added in this package"). The revision row's rationale is inconsistent with the note's own argument (m-2) |
| 3 | Owner point B | **Rework (M-3, M-4, m-12)** | The schemas' `revId`/`decId` patterns admit a deterministic UUIDv7 (envelope schema line 349). But `independent_observation_ref` (line 18, required) is not addressed. The collision argument ignores pre-assigned IDs. Each ref's referent and hash semantics are under-specified |
| 4 | Owner point C | **Keep** | `a8078818…ffde7` reproduced over the 61 24-field rows (§A4). W11 does have a precedent, and it supports the recommendation (m-8) |
| 5a | Does the bootstrap contract forbid WP9.2? | **Yes, textually** | Contract lines 39, 40, 67, 69, 70. Only line 39's "no acceptance instance" is mechanically enforced, by `test_the_only_tracked_instance_is_the_w9_catalogue` (`test_w9_expected_catalogue.py:499-501`). W11 never amended its own contract (B2 review i-5). The note omits that precedent (m-8) |
| 5b | Free-text amendment possible without a schema or catalogue change | **Yes, with M-6** | `forbidden` and `verification_rules` are free arrays (contract schema). The catalogue's 19 schema source rows pin schemas, not the contract YAML. But the consts `runtime_activation: forbidden` and `materialization_status: inert_foundation_only` would then contradict the package (M-6) |
| 5c | Commit chain right; three PRs needed? | **Chain right, three PRs not needed (M-5)** | The genesis schema requires `git_commit` in `bootstrap_contract_identity` and `external_envelope_identity` (genesis schema lines 23, 52). The envelope schema requires it in `bootstrap_contract_identity` (line 193). The contract-to-envelope link exists only because the note departs from P-075's carried citation. Two PRs keep every identity exact |
| 5d | 06v O-3 still unmet | **Confirmed** | No register entry accepts the bootstrap contract. P-069 says "Not decided here: acceptance of stage A" (register line 4506). P-075 accepts the catalogue and annex only (lines 4749-4772) |
| 6 | Coverage of 06v WP9.2, §3's O-rows, §8, and the citations | **Partial** | Gaps are O-4 grant scope and P-069 item 2 (M-2, M-1); genesis guards and the catalogue's LR-001 preconditions (m-3); W9-T20's three cases and the catalogue's own test identities (m-4); two §8 stop rules (m-9); `accepted_w9.py`'s frozen Gate 6 identity (m-6). Every identity in note §4.1 and §4.4 is exact (i-1) |

## Blocking

### B-1 (Blocking). The chosen site-1 shape refuses every W9 review and Decision event, so the confinement claim fails

**Claim.** Note §2.1 (lines 48-52) keeps `_validate_active_lifecycle_binding` for legacy events and skips only
`apply_event`, "unlike the prototype". C2 (line 84-89) requires a W9 command that emits a W2 event type to record it
under the W2 event schema with a producer binding. Together the two refuse every such event.

**Evidence.**
- `validate_exact_lifecycle_envelope` (`research_system/command/lifecycle.py:470-513`) first looks up
  `_EXACT_LIFECYCLE_PRODUCER_BINDINGS[(schema_id, command_type)]` (`:418`). If that is absent, it falls back to
  `EXACT_LIFECYCLE_BINDINGS[schema_id]`. The fallback maps `ars://core/event/ReviewRequested` to generic `RequestReview`
  (`:261-265`), and does the same for `ReviewVerdictRecorded` (`:300-303`), `DecisionProposed` (`:325-328`) and
  `DecisionResolved` (`:335-338`). A W9 command type then fails the `command_type` equality at `:500-512`.
- W11's own review events never reach this check, because they are Discovery events and site 1 skips it for them
  (`projection/replay.py:1323-1324`). That is why W11 needed no `lifecycle.py` entry.
- **Reproduced (§A2).** A real `ReviewRequested` was produced by `RequestW11AuthorityReview` in the Discovery harness and
  relabelled as `RequestW9AuthorityReview`. Its row ref was changed to `W9:LR-010`, and a W9 producer binding plus the
  12 command rows were added. With the note's shape, both `replay` and `replay_discovery` refuse it: "exact lifecycle
  event provenance mismatch". With the prototype's shape, both pass.
- The affected rows: 43 of 61 catalogue rows emit a W2 event. They are `RequestW9AuthorityReview` (9),
  `RecordW9AuthorityReview` (9), `ProposeW9AuthorityDecision` (12) and `ResolveW9AuthorityDecision` (13) (§A4).
- For WP9.2's own events the check does nothing. Genesis and revision events are `ars://core/event`, and for those the
  validator returns `None` at `lifecycle.py:496-497`. So the note's §7 control, "a control must show it still runs",
  cannot observe anything.

**Failure scenario.** WP9.2 merges with the kept check. WP9.3 or WP9.4 adds `RequestW9AuthorityReview`, and its first
event makes every replay of the store refuse. The fix is either to edit site 1 again, or to add four producer entries
to `command/lifecycle.py`. That file is not one of the four sites. Either way, note §3's premise fails: "Fixing the set
now means later packages never touch the four shared sites again". So does the confinement verdict in §2.5.

**Impact.** Validity of the U-7 resolution (06v §8 stop rule 3) for the package family; the D-2 design.

**Disposition: fix now.** Adopt the prototype's site-1 shape. Legacy events skip both `_validate_active_lifecycle_binding`
and `apply_event`, as Discovery events do. State what replaces the check:
- the command-schema identity is still resolved against its recorded SHA-256 for every event
  (`projection/replay.py:1248-1258`);
- the Discovery envelope validator checks command rows and producer bindings over the whole ledger (C1, C2);
- `replay_legacy` validates payloads (M-1) and refuses a W9 event under a non-W9 command, or the reverse.

**Proposed text** (note §2.1, replacing lines 48-52): "Site 1 treats a legacy event as Discovery's is treated: it
skips `_validate_active_lifecycle_binding` and `apply_event`. The lifecycle check maps each W2 event schema to its
generic producer (`command/lifecycle.py:261-338`), so it would refuse every W9 review and Decision event. Its remaining
protections are covered by the command-schema resolution in `_replay`, by the Discovery envelope validator (C1, C2) and
by `replay_legacy`." §7's "Its negative control" row gains a W2-typed W9 event. A control that restores the check must
then fail with "exact lifecycle event provenance mismatch".

**Affected:** note §2.1, §2.5, §3, §7; 06v U-7 and §8; D-2; WP9.3, WP9.4 and WP9.6.

## Major

### M-1 (Major). C3 misstates the code, cannot be met by W2 payloads, and the W9 event payload layout is never fixed; P-069 item 2 is not carried

**Claim.** Note C3 (lines 90-94): "A W9 transaction must carry exactly one `LR-` row there and no `W11:OR-`
reference … The W9 preparer refuses a violating payload before append."

**Evidence.**
- The code needs no `LR-` row. `_owner_row_id` (`discovery/replay/transactions.py:173-192`) collects every
  top-level `owner_row_id`/`row_id` string, and only the `W11:OR-` entries of `governing_refs` and
  `governing_evidence_refs`. `_matching_contract_rows` keeps only W11 rows whose `command_type` equals the event's
  (`:455-459`), so a W9 command never matches one. With no row, or with an `LR-` row, `validate_transaction_contract`
  returns for any non-Discovery command (`:513-530`).
- Reproduced (§A2): a W9 review event that carries only `W9:LR-010` in `governing_refs` passes
  `replay_discovery`'s transaction validator.
- The rule cannot be met by W2 events. The W2 payloads are closed and admit neither `owner_row_id` nor `row_id`:
  `review_requested.schema.json` line 6 (`additionalProperties: false`); the same holds for `review_verdict_recorded`,
  `decision_proposed` and `decision_resolved` (§A4). `ReviewVerdictRecorded` has no `governing_refs` field at all. W11
  carries its row in `governing_refs` as `W11:OR-112`, which is exactly what C3 forbids for W9.
- The genesis record is also closed and has no row field (`import-accepted-w9-catalogue-genesis.schema.json`). W11's
  genesis *event* payload is not its record: `accepted_w11.py:35-52` adds `owner_row_id: OR-140`.
- P-069 item 2 (register lines 4488-4491) makes it binding that "WP9.2 validates each event's payload record through
  the schema registry". The note never cites P-069. Generic replay does not do this: `_validate_recorded_event_schema`
  returns at once for `ars://core/event` (`projection/replay.py:219-220`).
- The probe's forged payloads are not schema-shaped: `{"owner_row_id": "LR-060", "catalogue_sha256": …}`. Genesis is
  LR-001, not LR-060.

**Failure scenario.** The code PR follows C3 literally. It must then either add a non-schema `owner_row_id` to closed
records, which fails P-069 item 2's validation, or refuse every W2-typed W9 event at the preparer.

**Disposition: fix now.**
1. Restate C3: "No W9 event payload carries a top-level `owner_row_id` or `row_id` naming a W11 row, or a `W11:OR-`
   string in `governing_refs` or `governing_evidence_refs`. An `LR-` row there is inert to Discovery and optional."
2. Add §4.6, "Event payloads", with one row per event kind:
   - for an `E:` event, whether the payload is the record itself (validated against its `ars://legacy/` schema) or a
     named wrapper;
   - for each W2 event, how the W9 row is identified (for example `governing_refs: ["W9:LR-nnn"]`, or by the command
     and the catalogue's `payload_discriminant`);
   - the event-type names, derived from the catalogue tokens by W11's `catalogue_event_name` rule
     (`discovery/routes.py:322-335`). Under that rule `E:legacy-record-observed` gives `LegacyRecordObserved`, not the
     probe's `LegacyObservationRecorded`.
3. State that `replay_legacy` validates each payload through the registry (P-069 item 2), with a test that a
   schema-invalid payload is refused.

**Affected:** note §2.3, §5.4, §7; P-069 item 2; WP9.3 to WP9.6.

### M-2 (Major). The genesis grant cannot be activated without a shared `authority.py` edit; O-4 and G4 are not covered

**Claim.** Note §5.1 says W9 uses "scoped authority with the existing subject kinds". It names no edit outside
`research_system/legacy/`, the four sites and the binding rows, and it does not cite O-4.

**Evidence.**
- `validate_scoped_grant_activation` refuses any allowed command whose `_SCOPED_COMMAND_SUBJECT_KINDS` entry is absent
  (`research_system/authority.py:700-708`: "inactive or has the wrong subject kind").
- That map (`:208-331`) and `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` (`:171-207`) are closed. They list
  `ImportAcceptedW11CatalogueGenesis` and the W11 authority commands, and no W9 command.
- 06v §2.2 (line 59) names "subject kinds in the runtime and in `authority.py`" as a touchpoint. P-076's Boundary line
  (register lines 4819-4820) does not include the file.
- O-4 (06v line 184) requires "genesis under an owner grant scoped to the W9 catalogue stream". The catalogue's
  LR-001 `authority_subject` requires "the exact bootstrap grant scoped to the W9 catalogue stream". Global precondition
  G4 adds that "a path-only, role-only or wildcard subject never satisfies a row".

**Failure scenario.** At L-3, `ars authority activate-grant` refuses the genesis grant. Or the code PR edits
`authority.py` without that edit having been reviewed or authorized.

**Disposition: fix now, plus an owner boundary item (M-8).** Name the `authority.py` entries for every command that
gets a binding row: `ImportAcceptedW9CatalogueGenesis` as `scope_definition`, as W11's genesis is, and the actor-class
set. State how G4 binds the subject: subject ID equals `CATALOGUE_STREAM_ID`, as Discovery uses `target_stream_id`
(`discovery/runtime.py:240`). Add to §7 a grant-scope test: a grant on another stream, or one with no exact subject,
is refused.

**Affected:** note §5.1, §7, §9 (point A); O-4; P-076 Boundary.

### M-3 (Major). Owner point B leaves the required `independent_observation_ref` unaddressed

**Claim.** Note §4.2 (lines 154-158) says the envelope "requires `independent_review_ref` and
`acceptance_decision_ref` as ARS refs".

**Evidence.**
- The envelope schema also requires `independent_observation_ref` (line 18; property at line 314). It is an `anyRef`,
  a union of the store-minted `obj_`, `dec_`, `rev_`, `art_` and `tsk_` ref kinds, so it has the same out-of-store
  problem.
- W11's design sets out what that observation is (`design/11-portfolio-and-discovery-lifecycle.md` lines 1572-1580):
  "an independent observer that executes no W11 command records … Git commit/blob, file length/SHA-256". For W9 the
  candidates include:
  - the B2 review's separate derivation, which "does not call the verifier" (commit message of `7979e85a`);
  - the canonical-checkout verifier run that P-075 cites (B2 review i-6).
- The note also gives no source for the envelope's other required fields: `specification_identity` and
  `plan_identity` (`reviewed_commit` form), the 19 `schema_identities`, `accepted_at` and `acceptance_scope`. 06v has
  two accepted byte states (revision 4 and the P-064 post-acceptance correction), so `plan_identity` needs a stated
  choice.

**Disposition: fix now.** Owner point B covers all three out-of-store refs and names each referent. Add a table giving
every required envelope field with its source. The catalogue's `owner_spec_identity` and `owner_plan_identity` are the
natural source for the specification and plan fields.

**Affected:** note §4.2, §4.4, §9; WP9.2-2 (or its successor under M-5).

### M-4 (Major). Owner point B's collision argument does not hold: review and Decision IDs are pre-assigned by the caller

**Claim.** Note §4.2 (lines 171-173): a store-minted ID "collides only if a store mints at that same millisecond and
draws the same 74 bits; the scratch stores and any later W9 store are created after that time, so their IDs cannot".

**Evidence.**
- W9 review and Decision IDs are chosen by the proposer. P-072 item 1 says "The proposed content already carries the
  pre-assigned `dec_` and `rev_` IDs" (register lines 4598-4599). Global precondition G5 has "the proposal's
  pre-assigned rev_ and dec_ IDs".
- The runtime accepts any well-formed timestamp. The Discovery harness pre-assigns `rev_019fed25-b33e-7740-b280-…`
  (`tests/research_system/integration/test_wp6_6_discovery_runtime.py:317`), whose 48-bit timestamp is
  1786390098750 ms (August 2026), before any store that ran it.
- The derivation is public and deterministic. Anyone can compute the two IDs and pre-assign them.

**Failure scenario.** A later W9 proposal pre-assigns `dec_` equal to the envelope's `acceptance_decision_ref.id`,
whether by a copy-paste slip or a deliberate choice. W9-C25 refuses only "pre-assigned IDs [that] already exist" in
the store (P-073 item 1), and the external IDs do not. The store then holds an in-store Decision with the same ID as
the external P-075 ref, and any later resolution by ID is ambiguous.

**Disposition: fix now.**
- Drop the probability argument.
- Genesis records both external IDs, three with M-3, in the W9 projection's identity set.
- The W9 global identity check, and W9-C25, refuse a pre-assigned ID equal to any of them.
- A test proposes a record that pre-assigns the external `dec_` and expects refusal.

**Affected:** note §4.2, §5.2, §7; P-073 item 1 (W9-C25 scope, read, not changed).

### M-5 (Major). The envelope's contract citation departs from P-075 without saying so, and that departure alone creates the three-PR chain

**Claim.** Note §4.4 (lines 193-194): "`bootstrap_contract_identity` is the exception: it names the amended contract at
WP9.2-1's main commit (§4.5), not `96a63114`." Note §4.5 then builds a three-link chain from it.

**Evidence.**
- P-075, owner-accepted, says under "Not decided here" (register lines 4779-4780): "Carried to WP9.2: … the envelope
  cites the merged contract (`96a63114`), verifier (`e8bb5085`) and test blobs (B2 review i-4)." The note does not cite
  that sentence.
- The note's own rationale for the test blobs, "the envelope records the evidence the acceptance rested on" (lines
  203-205), argues for `96a63114` too. O-8 rested on the contract as merged at `7979e85a`.
- The envelope also departs from P-072 item 6 (register lines 4636-4638): the instance "is written at L-3 in the store,
  or with WP9.2's `accepted_w9.py`, as W11 did". The departure is justified, because the genesis schema's
  `external_envelope_identity` requires a repository path, commit, blob, length and SHA-256 (lines 52-80). Neither
  placement P-072 lists can supply those. But the note does not record this departure either.
- **A simpler sound order.** Suppose the envelope cites the contract at `7979e85a` (blob `96a63114`), per P-075. Then
  the envelope does not depend on the amendment's commit, and the package lands in two PRs:
  1. the contract amendment, the envelope and the instance-scan allowance;
  2. the runtime, with `accepted_w9.py` pinning both at PR 1's main commit.

  The genesis payload's own `bootstrap_contract_identity` names the amended contract at PR 1's commit. That is the
  contract O-3 accepts and genesis re-hashes. Every identity stays exact. The envelope records what O-8 rested on, and
  the genesis payload records what the runtime runs under.
- The note's chain list (lines 219-221) also omits that the genesis payload names the contract directly (genesis
  schema line 23), not only through the envelope.

**Disposition: amend owner point D.** Recommend two PRs, with the envelope citing `96a63114` at `7979e85a` per P-075.
Name the P-072 item 6 departure for Stephen to record. Keep the three-PR option only if Stephen prefers the envelope
to cite the amended contract. That needs a decision that supersedes P-075's carried sentence.

**Affected:** note §4.4, §4.5, §8, §9 (D); P-072 item 6; P-075.

### M-6 (Major). After the amendment, the contract's `runtime_activation: forbidden` contradicts the package O-3 would accept it for

**Claim.** Note §4.5 (lines 213-215): the schema's consts "stay", and only the free-text lists change.

**Evidence.**
- The contract schema fixes `materialization_status: inert_foundation_only` and `runtime_activation: forbidden`
  (§A4). `test_w9_contract_materialization.py:347` asserts the second.
- The stage B note's reason for keeping consts was that they "describe stage A and stay true"
  (`wp9-1-stage-b-design-note.md:218-220`). That reason holds for `expected_catalogue` and `acceptance_instance`, whose
  value is `forbidden_in_stage_a`. It does not hold for the two unqualified consts once the W9 runtime exists.
- The catalogue's LR-001 precondition is "the bootstrap implementation independently verified against the accepted
  contract (W9 §5.3 item 2)". The contract O-3 accepts would therefore say that runtime activation is forbidden.
- One reading makes it consistent. `runtime_activation` can be read as governing the `ars://legacy/` schemas'
  runtime-binding status, per rule 37 and `forbidden` line 66. That reading is not written anywhere. W11's contract
  was never amended at all (B2 review i-5).

**Disposition: owner decision, added to point D.** Before O-3, Stephen records the reading of the two consts in the
O-3 decision. The amended `verification_rules` state it in one line, for example "runtime_activation governs the
`ars://legacy/` schemas' runtime bindings only; the W9 runtime is WP9.2's". The alternative is to follow W11's
precedent and leave the contract unamended. O-3 would then accept it with a recorded scope note, and only the
instance-scan test would change.

**Affected:** note §4.5, §9 (D); O-3; the contract's acceptance.

### M-7 (Major). The Gate 6 refusal is placed "under the lock" in §5.2, and taking that lock writes into the Gate 6 store

**Claim.** Note §5.2 (lines 259-261): "Under the lock, in order: 1. the target store's identity is not a refused
identity (§5.3)".

**Evidence.**
- `WriterLock` creates its lock path in each control root (`research_system/store/writer.py:938`, `:1069`).
  `CompositeWriterLock` "publish[es] a live lease" (`:1503-1504`). Discovery takes it before authority resolution
  (`discovery/runtime.py:194-200`).
- Note §5.3, 06v WP9.2 (lines 368-375) and catalogue precondition G1 ("read unbound before binding") all put the check
  before binding. G1 applies it to every row, not to genesis only.
- 06v §8 stop rule: "a command would write a legacy file or the Gate 6 store".

**Failure scenario.** The code follows §5.2's list. Pointing the runtime at a copy of the Gate 6 store, or the M2
checkout's store, writes lock and lease files into it before the refusal.

**Disposition: fix now.** Move step 1 out of the genesis list. The refusal happens when `LegacyRuntime` binds a store,
before any lock, for every command. W9-T20 adds an assertion that the refused store's control root is byte-identical
afterwards: no lock, lease or receipt file.

**Affected:** note §5.2, §5.3, §7; O-2; W9-T20.

### M-8 (Major). Owner point D needs a named boundary extension and a D-6 exception, not only a PR split

**Claim.** Note §4.5 and §9 present point D as a choice of PR order.

**Evidence.**
- P-076 authorizes WP9.2 "as one package", in the order "Then the code PR" (register lines 4798-4806). Its Boundary is
  "Runtime code under `research_system/legacy/`; the four shared-replay sites named in 06v U-7; the runtime-binding
  rows; tests; docs" (lines 4819-4820). D-6 is "One PR per package" (06v line 568).
- The note's plan also writes:
  - the contract YAML under `.research-system/contracts/w9/`;
  - an envelope JSON under `.research-system/evals/expected/`;
  - `research_system/authority.py` (M-2);
  - `research_system/cli.py`, which P-076's decision item 1 names but its Boundary line omits.
- P-069 (lines 4480-4504) is the precedent: a named D-6 exception plus a by-name boundary extension.

**Disposition: amend owner point D.** Ask Stephen for one decision recording:
- the PR split, two or three per M-5, as a named exception to D-6 and to P-076 item 2.3;
- a by-name extension of P-076's Boundary to the contract YAML, the envelope file, `authority.py` and `cli.py`.

**Affected:** note §4.5, §9; P-076; D-6.

## Minor

- **m-1. The route registry's treatment of the 59 rows WP9.2 does not admit is unspecified.**
  - Genesis guard 7 (note line 267) allows "a recorded exclusion". But §5.4 (lines 290-291) generates a transaction
    contract "for each catalogue row", which implies 61 routes.
  - W11 has three classes: 59 routed, 21 excluded, 1 deferred (`discovery/routes.py:344-355`).
  - Under A(a), say whether all 61 rows are routed (binding rows decide what can append) or 59 are deferred. Say also
    what the partition is if L-3 runs before WP9.3. An "exclusion" in W11 means never implemented under that
    catalogue; it is not the word for "a later package".
- **m-2. Owner point A(a)'s rationale argues against its own revision row.**
  - Option (b) is rejected because ten commands "would then be grantable with no preparer; … the refusal is code
    rather than the binding table".
  - The inert `ImportAcceptedW9CatalogueRevision` (catalogue LR-002, "inert in v1: no accepted revision exists") is in
    exactly that position under (a).
  - Either give the reason it is included (P-072 item 5 asks only that the row exist in the catalogue), or bind
    genesis alone. The revision tests can then use a test registry, as the probe did.
- **m-3. The genesis guards omit four things.**
  - The target stream equals `CATALOGUE_STREAM_ID` (W11: `discovery/runtime.py:2630-2631`).
  - The replayed W11 catalogue's identity equals the payload's `required_w11_catalogue` (blob `8d588185`).
  - Where LR-001's preconditions "the bootstrap implementation independently verified against the accepted contract"
    and "Stephen's O-8 acceptance current" are enforced, or that they are L-3 owner gates.
  - Retry and idempotency (W9-C11-LR-001; W11 design line 1616, "idempotent only for the same envelope hash").
  - Also: give the complete accepted genesis payload field by field. The note names only the two identities, but the
    closed schema also requires `requested_genesis_transaction_id`, `verification_requirements` and
    `activation_status: not_executed` (genesis schema lines 10, 81, 126). How `requested_genesis_transaction_id`
    relates to the ledger-assigned transaction is undefined.
- **m-4. The test list omits identities the accepted catalogue binds for the admitted rows.**
  - The catalogue binds `W9-C01-LR-001`/`-002`, `W9-C03-LR-001-owner-row-mutation`/`-002-…` and
    `W9-C11-LR-001`/`-002` (§A4).
  - 06v §4 (line 243) gives W9-T20's three cases: the original path and a byte copy at a second path, both asserting
    the W9 reason code, and a different identity that passes. It also gives the origin-witness fixture. Note §7 has one
    line for them.
  - Add the grant-scope test (M-2) and the W2-typed event (B-1).
- **m-5. Legacy semantics are never validated before a Discovery command.**
  - `DiscoveryRuntime`'s pre-command replay (`discovery/runtime.py:474-479`) reaches only `_replay_shared_partitions`
    (`discovery/replay/driver.py:70-75`; `validate_discovery_semantics=False` at `projection/replay.py:1199`).
  - A Discovery command can therefore append on top of a ledger whose legacy half `replay_legacy` would refuse. The
    store then fails at the next generic or legacy replay.
  - Adding the call would be a fifth site. Record this as an accepted asymmetry and test that the next generic replay
    refuses.
  - Separately, `replay_legacy` must itself refuse a W9 genesis with no prior W11 genesis. `replay` calls
    `replay_discovery` only when a Discovery event exists (`projection/replay.py:1369-1381`).
- **m-6. `accepted_w9.py` omits the frozen Gate 6 identity, and the O-8 pin would lose its independent expected side.**
  - 06v WP9.1 gate step 3 (line 330-331), re-homed to WP9.2 by P-066 item 2, puts the frozen §2.6 identity in
    `accepted_w9.py`.
  - Note §4.1 (lines 148-150) replaces the O-8 literals in `test_w9_expected_catalogue.py:429-436` with an import of
    `ACCEPTED`. The test's expected side then comes from the module the runtime uses, so one PR that changes both
    passes.
  - Keep the literals, and assert `ACCEPTED` equals them.
- **m-7. §4.4's rationale for the test blobs is inaccurate.**
  - `test_w9_expected_catalogue.py` at `eab253f6` (blob `a7621a39`) was written by PR #404 after O-8. At the accepted
    commit `7979e85a` its blob was `5a8e1c84` (§A4).
  - "The evidence the acceptance rested on" therefore describes `5a8e1c84`.
  - Citing `a7621a39` is defensible, since it is the version that pins the accepted bytes, but say so. P-075's "test
    blobs (B2 review i-4)" read most naturally as the merged ones at `7979e85a`.
- **m-8. Two citations need correcting.**
  - "B2 set the pattern … (B2 review i-5)" (line 214-215). The pattern is the stage B note §6
    (`wp9-1-stage-b-design-note.md:216-220`) as applied in `7979e85a`. i-5 records W11's opposite precedent (W11 never
    amended its contract), which the note should give.
  - "W11 has no precedent" for the multiset hash (line 188-189). W11's design defines "the complete owner-row multiset
    hash" over complete owner-contract rows, and has genesis require "the imported multiset to equal the accepted one"
    (`design/11-portfolio-and-discovery-lifecycle.md:1612-1616`). Its envelope schema has the field. That precedent
    supports point C.
- **m-9. §10 checks six of 06v §8's eight stop rules.** Add "a successor guard needs a core schema change …" and "any W9
  §13.4 criterion applies", each N/A with a reason.
- **m-10. The probe's evidence is weaker than §2.2 reads.**
  - Of the kept tests, `test_without_w9_command_bindings`, `test_w2_event_type_without_producer_binding` and
    `test_w9_payload_citing_a_w11_row` print and never assert.
  - Two §2.2 rows have no kept test: "Site 3 alone removed", and "producer binding but recorded as
    `ars://core/event`".
  - This review reproduced every message, including site 3 by disabling the branch (§A1). The code PR's tests must
    assert each message, and use catalogue-derived event types and schema-valid payloads (M-1).
- **m-11. A fifth condition, C5, is missing.**
  - Site 2 sends `PartialOutcomeRecorded` and `LeaseReleased` to `operational` before any other branch
    (`discovery/routes.py:309-310`). Site 1's predicate keys on command type alone.
  - A W9 command that emitted an operational, artefact, context or control event type would be skipped at site 1 and
    reduced elsewhere.
  - The catalogue emits none (§A4). Add C5, "no W9 row emits an event type in the operational, artefact, context or
    control sets", with a test over the catalogue's `ordered_events`.
- **m-12. Owner point B's derivation is under-specified.**
  - Which 74 bits of the digest, in what order, go into `rand_a` and `rand_b`.
  - The exact `accepted_at`. "The P-075 commit's time" could be the squash `eab253f6`, at 2026-10-27T18:55:08Z
    committer time, or a branch commit. Stephen's acceptance was in chat earlier, and Git times have one-second
    resolution.
  - The decision domain string names the 365,418-byte register at a commit, not P-075. Add the entry ID, for example
    `w9-external:decision:P-075:<path>@<commit>`.
  - `content_hash` as a raw file SHA-256 differs from the record-content hash ARS refs carry elsewhere. State that no
    consumer dereferences these refs as store records, and test it.

## Info

- **i-1.** Every identity in note §4.1 and §4.4 is exact at `eab253f6` (§A4):
  - the verifier `e8bb5085`, `a19c23ab…5368`, 28,330 bytes;
  - the generator `5b068f9d`, `932985f4…4c14`, 56,544 bytes;
  - `test_w9_expected_catalogue.py` `a7621a39`, `6c4e1c7d…0126`, 24,626 bytes;
  - `test_w9_contract_materialization.py` `4133b75e`, `d6819a52…36e5`, 52,688 bytes;
  - the contract `96a63114`, `b3352b2c…3ac1`, 3,820 bytes;
  - the catalogue and annex as P-075 records;
  - trees `0962a5a4` (base) and `d6746b4d` (accepted).

  The catalogue and annex blobs are identical at `3241f0e9`, `7d0872f9` and `7979e85a`. So the B2 confirmation did
  review the accepted bytes, as note §4.2 says.
- **i-2.** Owner point C's value reproduces: `a80788184c02b5baa9ea47cf2f1a254f4f14499188e6a0dcbef8d083072ffde7` over the
  61 rows. Guard 6 recomputes it from the same file guard 5 re-hashes, so it adds no assurance beyond guard 5. The
  independent value comes from the envelope reviewer, who must reconstruct it, as W11's design item 5 requires.
- **i-3.** C4's consumer list is complete. `discovery/runtime.py:2254` is `!= "artefact": continue`, which is a positive
  selection. `discovery/replay/driver.py:59,64` also select by equality and set membership.
- **i-4.** O-3 is unmet, confirmed (check 5d). 06v §3 gives its disposition as "WP9.1 (contract)", and P-075 declared
  WP9.1 complete without it. Point D is the first place it is surfaced, which is correct.
- **i-5.** P-076 exists only on the unpushed branch (`f01505ff`). Documents that cite it by commit must cite its `main`
  commit after merge (06v §2.4).

## Decision audit

### Owner points

| Point | Note's recommendation | Review disposition |
|---|---|---|
| A | (a) binding rows for genesis and revision import; predicate over all 12 | **Keep the predicate and (a).** Add the `authority.py` rows (M-2). Justify or drop the revision row (m-2). Fix the route classes (m-1) |
| B | (a) deterministic UUIDv7 external refs for review and decision | **Amend.** Cover `independent_observation_ref` (M-3). Replace the collision argument with identity reservation (M-4). Pin the derivation (m-12). Options (b) and (c) are correctly rejected |
| C | Catalogue's 24-field rows | **Keep.** Value reproduced (i-2). Correct the precedent claim (m-8) |
| D | (a) three PRs: contract (then O-3), envelope, runtime | **Amend.** Two PRs, with the envelope citing `96a63114` per P-075 (M-5). Add the const reading (M-6), the boundary extension and the D-6 exception (M-8) |

### Decisions the note relies on

| Decision | Note's use | Disposition |
|---|---|---|
| P-064 (06v accepted; D-1 to D-9) | WP9.2 scope; U-7; §8 | Keep. The note corrects two 06v statements (§2.4). Both corrections are right and were reproduced. They are corrections to 06v's text, made without editing its accepted bytes |
| P-065 | Not cited | Not engaged. WP9.2 is outside it, as P-076 records |
| P-066 item 2 | `accepted_w9.py` in WP9.2 | Keep. Add the frozen Gate 6 identity from 06v WP9.1 step 3 (m-6) |
| P-067, P-068 | Not engaged | N/A to WP9.2 (the segmentation contract is WP9.3's) |
| P-069 item 2 | **Not cited** | **Must be carried**: WP9.2 validates each event's payload record through the registry (M-1) |
| P-069 item 1 | Cited implicitly as the split precedent | Keep as precedent for M-8's form |
| P-070 | Not engaged | N/A until WP9.6 (supersession targets) |
| P-071 items 4-6 | Revision import; W9-C tests | Keep. The catalogue's W9-C identities for LR-001/002 go into §7 (m-4) |
| P-072 item 1 | Not cited | Bears on M-4 (pre-assigned IDs) |
| P-072 item 5 | Revision import inert | Keep (m-2 on its binding row) |
| P-072 item 6 | **Not cited** | **Departure to record** (M-5): the envelope becomes a repository file, which the genesis schema requires |
| P-073 item 1 (W9-C25) | Not cited | Its scope must cover the reserved external IDs (M-4) |
| P-074 item 1 | Hash definitions | Keep (point C) |
| P-075 | O-8 identities; carried i-3 and i-4 | Identities keep (i-1). **The carried contract citation is departed from without notice** (M-5) |
| P-076 | Authority and order | Keep the order. Its Boundary and "one package" need the named extension of M-8 |
| D-1 | Gate 6 frozen identity | Keep (§5.3), with M-7's ordering |
| D-2 | Discovery-style path, shared replay | Keep, with B-1's site-1 shape |
| D-3 | Not engaged | N/A (WP9.4) |
| D-4 | §8 list | Keep. Add nothing for `authority.py`: it is not a P-059 protected identity. The 06h test names it only as the `initialize_authority_control_store` append site (`test_wp6_1_06h_append_path_closure.py:34-38`), which the M-2 edit does not touch, and `wp6_2_t2_expectations.py` does not name it |
| D-5 | Not engaged | N/A (WP9.5) |
| D-6 | Implicitly departed from | Needs the named exception (M-8) |
| D-7, D-8 | Not engaged | N/A |
| D-9 | Contract `restricted_suffixes` kept | Keep. The amendment leaves that list alone |

## Consistency matrix (invariant → enforcement → test)

| Invariant | Enforcement point | Test in note §7 | Gap |
|---|---|---|---|
| Every shared replay recognises W9 events | Sites 1-4 | Shared replay plus negative control | B-1: add a W2-typed event |
| W9 events stay out of Discovery's partitions | Site 2, C4 | Consumer test | m-11 (C5) |
| Command provenance for W9 events | `_replay` schema resolution; Discovery envelope validator | C1, C2 | none |
| Payload records valid (P-069 item 2) | `replay_legacy` | **none** | M-1 |
| No W11 row in a W9 transaction | Discovery transaction validator | C3 | M-1 (restate) |
| Genesis only from the accepted payload | Pre-lock check; replay reducer | Genesis negatives | m-3 |
| Gate 6 store never touched | Before binding, every command | W9-T20 | M-7, m-4 |
| Genesis under an exact scoped grant (O-4, G4) | `authority.py` plus the runtime | **none** | M-2 |
| External refs unique in the store | Genesis identity reservation; W9-C25 | **none** | M-4 |
| W11 pins unchanged | Unchanged W11 tests | "W11 unchanged" | none (339 passed) |

## Revision plan

**Immediate (revision 2):** B-1; M-1, M-2, M-3, M-4, M-7; m-1, m-3 to m-12; add §4.6 (event payloads) and a full
envelope-field source table.

**Owner decisions (Stephen, after revision 2):**
- A, as amended;
- B, as amended;
- C;
- D, now asking for two PRs, the M-6 const reading, and the M-8 boundary extension and D-6 exception;
- the P-072 item 6 departure (M-5).

**Later work:** WP9.3 to WP9.6 carry their own binding rows and D-4 re-acceptance. The C2 producer bindings land with
them. Under B-1's fix, they need no `lifecycle.py` entries.

## Residual risks

- The probe drives forged, re-hashed ledgers. The code PR's tests are the first to append W9 events through a real
  preparer and lock.
- `test_wp6_6_discovery_runtime.py` (100 tests, 26 minutes) was not re-run here. The prototype's site-1 change matters
  only to ledgers that hold legacy events, and none of that suite's ledgers do. The five fast suites passed.
- Same model family (P-058).

## Appendix: verification evidence

All commands ran in this review's worktree (branch `review/w9-wp9-2-note` at `6b5aeee3`). They used the main
checkout's interpreter with `PYTHONPATH=.` and `-p no:cacheprovider -o addopts=""` (no coverage writes). After the
runs, `git checkout --` restored the three shared files, and `research_system/legacy/` and the two probe test files
were deleted. `git status --short` was empty before this report was written.

### A1. Kept probe, reproduced

The prototype diff and module were applied, and `test_u7_probe.py` was copied into `tests/research_system/integration/`
(6 passed, 93 s). The printed results:
- partitions: `['legacy', 'legacy']`; `REPLAY_LEGACY_CALLS [2, 2]`;
- predicate removed: generic replay gives "unsupported event type: W9CatalogueGenesisImported", and
  `replay_discovery` gives "invalid Discovery operational partition";
- no W9 command rows: both give "Discovery persisted schema provenance mismatch at 2", cause "active command binding
  mismatch";
- no producer binding: both give "… at 4", cause "unbound event producer";
- `W11:OR-010` in a W9 payload: "Discovery transaction carries conflicting W11 owner rows";
- site 3 disabled, the others in place: "unsupported Discovery event: W9CatalogueGenesisImported".

Five fast suites against the prototype (`test_wp6_6_discovery_activation.py`, `test_wp6_6_discovery_architecture.py`,
`test_w11_expected_catalogue.py`, `test_w11_contract_materialization.py`, `test_p045_envelope_decision.py`): 339 passed
in 86.25 s.

### A2. Site-1 shapes on a W2-typed W9 event

A review probe (`test_review_wp9_2_probe.py`, not kept) worked as follows:
- It drove `_advance_w11_authority(..., "dossier_expected_set", …, through_index=2)` to obtain a real `ReviewRequested`,
  schema `ars://core/event/ReviewRequested`, command schema `ars://core/command`.
- It copied that event and set `command_type: RequestW9AuthorityReview`, `governing_refs` with `W9:LR-010` in place of
  `W11:OR-112`, a fresh stream and transaction, and a re-hashed chain.
- It added the 12 command rows and a `ReviewRequested` producer binding for `RequestW9AuthorityReview`.
- Site 1 was toggled between the note's shape and the prototype's.

| Site-1 shape | `replay` | `replay_discovery` |
|---|---|---|
| Note §2.1 (lifecycle check kept) | REFUSED: "exact lifecycle event provenance mismatch" | REFUSED: same |
| Prototype (check skipped) | PASSED | PASSED |

A first attempt that put `owner_row_id: LR-010` into the payload was refused by schema validation:
`ars://core/event/ReviewRequested: payload …`. That is the M-1 evidence that closed W2 payloads cannot carry it.

### A3. Whole-ledger replay inventory

Every caller of `replay`, `_replay`, `replay_grandfathered`, `rebuild_projection`, `replay_discovery`,
`replay_control_plane` and `shared_event_partition` under `research_system/` was enumerated with `Grep`:
- `authority.py:1364,2033`; `cli.py:1498,1540,1701,1922,2114`; `artefacts/use_resolver.py:239`;
- `command/service.py:443,1956,2060,2206,2424,2594,4877`; `command/t2.py:1061`;
- `operations/backups.py:1025,1493,1793`; `evals/executors/release_tranche.py:455`;
- `discovery/spec*.py`; `projection/grandfather.py:640` (`_replay`).

All reach `_replay`. `replay_control_plane` is fed only `operational` partitions:
- `discovery/runtime.py:2214`;
- `discovery/replay/driver.py:292,696`;
- `discovery/rules.py:1044` and `discovery/replay/spike.py:110,164`, through the driver's list.

`command/t2.py:525` selects by schema prefix. No other raiser of an unknown-event error exists: `Grep` for "unsupported
… event" found only `projection/replay.py:1125`, `command/reducers.py:1808`, `command/t2.py:515` and
`discovery/replay/driver.py:500,669`.

### A4. Catalogue, schema and identity probes

Read-only scripts ran under the scratchpad.

**Catalogue.**
- 61 rows of 24 fields.
- 12 distinct command types, equal to the prototype's `LEGACY_COMMAND_TYPES`.
- 43 rows emit a W2 event: `DecisionResolved` 13, `DecisionProposed` 12, `ReviewRequested` 9,
  `ReviewVerdictRecorded` 9.
- No row emits an operational, artefact, context or control event type.
- LR-001 is genesis, LR-002 the revision import, each with W9-C01, W9-C03 and W9-C11 identities and binding test
  W9-T20.
- `owner_row_multiset_hash` over the rows is `a8078818…ffde7`.

**Schemas.**
- W2 `review_requested`, `review_verdict_recorded`, `decision_proposed` and `decision_resolved` payloads are
  `additionalProperties: false`, with no `row_id` or `owner_row_id`.
- The W9 envelope requires 17 fields, including `independent_observation_ref` (`anyRef`).
- The genesis schema requires `git_commit` in both identities, and `activation_status: not_executed`.
- The contract schema has the consts listed in M-6.

**Identities at `eab253f6`:** as i-1. Author and committer time of `eab253f6` is 2026-10-27T18:55:08Z, and of
`7979e85a` 2026-10-27T08:48:08Z.

## Change log

- Added this file. No other file changed. The probe edits were made in this worktree and reverted, as the appendix
  records.
