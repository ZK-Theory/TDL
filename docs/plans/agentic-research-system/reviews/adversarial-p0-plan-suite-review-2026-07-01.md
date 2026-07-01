# Adversarial Review — ARS P0 Materialization and Foundation Plan Suite

**Date:** 2026-07-01<br>
**Verdict:** `rework_required`<br>
**Subjects:** `05-p0-materialization-and-foundation-implementation-plan.md` and implementation plans 01–04 at commit `9c55cb2fe5dbafe27ccf1dda0feac1d053c110d9`<br>
**Live review base:** `main` at `172fdefa30b3014019e48b8a8e15e8bce760c087`<br>
**Authority:** Planning review only; no implementation, fixture materialization, external control/evidence root, live provider use, migration, pilot, or research claim is authorized

## 1. Executive verdict

The four-package decomposition and non-migration boundary are directionally sound, and the declared 37-case set is exact. The suite is not executable as written. Three Critical defects can permit invalid authority/evidence or break deterministic recovery, and seven Major defects leave accepted W1–W8/06c obligations unimplemented or mutually incompatible.

Implementation must not begin. The plans require a bounded reconciliation, followed by a fresh documentation-only validation and Stephen's explicit approval of the resulting exact scope. Findings P0-C1 through P0-C3 and P0-M1 through P0-M7 are required changes, not optional hardening.

## 2. Critical findings

### P0-C1 — Mandatory W3 sources can be omitted from an issued context

**Claim.** WP2's proposed `validate_manifest()` treats a mandatory source as satisfactory when its ID appears in `omissions`, even if it is absent from `included`.

**Evidence.** WP2 lines 136–139 compute `required - included - omissions`. Accepted W3 lines 227–234 prohibit dropping mandatory content to meet either gate; lines 286–297 state that a mandatory candidate cannot end as an omission in an issued packet; lines 480–495 require compilation failure when a mandatory source is missing, unreadable, unsafe, stale, or conflicted.

**Failure scenario.** A governing amendment is unavailable, recorded as `access_denied`, and removed from `included`. The proposed predicate reports no unexplained source, allowing the candidate to continue toward routing and issue.

**Impact.** Authority and scientific validity can be evaluated against an incomplete governing context; F-021/F-025/F-026 can falsely pass.

**Disposition.** Fix now.

**Exact change.** Replace the predicate with two independent rules: `(required - included)` must always be empty for any candidate eligible for validation/issue; omissions may describe only optional candidates. Missing/unsafe mandatory sources must return the W3 typed failure with no validated or issued packet. Add negative tests for every accepted mandatory-source failure class.

**Affected decisions/work packages.** P-028; W3 sections 7–12 and 16; WP2 Tasks 1–2; WP4 F-021/F-025/F-026/F-028.

### P0-C2 — The proposed release gate can pass with missing required graders

**Claim.** WP4's `decide_release()` requires only one result per fixture and checks only the results that happen to be supplied. It does not compare each fixture's declared `required_graders` and exact revision to the observed grader-result set.

**Evidence.** WP4 lines 281–296 build `by_fixture`, test only missing fixture IDs, and return `pass` when supplied results contain no blocking verdict. Accepted W6 lines 148–157 require every required critical D/T/P and every required R/M/H grader to pass. W6 lines 506–530 require a coverage manifest with selected fixture revisions and required grader sets, and a release decision listing every required fixture and grader verdict.

**Failure scenario.** F-036 declares D/T/R/M graders. The run supplies one passing D result and omits T/R/M. `by_fixture` contains F-036, `blocking` is empty, and the function returns `pass`.

**Impact.** Invalid P0 acceptance, including scientific-property and human/model review bypass.

**Disposition.** Fix now.

**Exact change.** Build the required `(fixture_id, fixture_revision, grader_id, grader_class, criticality, independence requirement)` set from the immutable coverage/fixture definitions; require exact closure; classify any missing/stale/duplicate/incompatible result as `blocked`; verify subject, trace, oracle, policy, and threshold hashes before considering a verdict.

**Affected decisions/work packages.** P-015/P-018/P-019/P-023/P-029/P-030; W5 two-key validity; W6 sections 20–27; WP4 Tasks 1–2 and 6.

### P0-C3 — Crash after event commit but before receipt has no specified reconstructive path

**Claim.** WP1's literal service order publishes the event batch and only then writes the immutable receipt, while its retry pre-check reads the receipt. The plan does not define the required event-derived receipt reconstruction before a retry can allocate or publish again.

**Evidence.** WP1 line 521 states `atomically publishes it, then writes the immutable receipt`; line 563 only broadly says crash before/after replace. Accepted W2 lines 269–278 require accepted idempotency outcomes to be reconstructible from events; lines 284–303 make rename the commit point; lines 938–947 require a crash after rename and before receipt to be discovered on retry and return the receipt; lines 1066–1079 require the exact stress scenario.

**Failure scenario.** The writer commits a batch, crashes before receipt publication, then receives an identical retry. A receipt-only idempotency lookup misses the accepted command and may publish a duplicate batch or return an unrecoverable conflict.

**Impact.** Duplicate canonical state or failure of deterministic recovery at the event commit boundary.

**Disposition.** Fix now.

**Exact change.** Specify and test an accepted-command/idempotency index rebuilt from committed events, including command ID, full idempotency tuple, payload hash, event IDs/positions, and resulting versions. On a missing receipt, recovery must reconstruct and immutably publish the identical receipt before accepting further mutation. Add fault injection at each boundary: object write, temp fsync, rename, ledger-tail visibility, receipt temp write, and receipt rename.

**Affected decisions/work packages.** P-006/P-020; W2 sections 8–9, 13, 21, and 23; S-001/S-011/S-012; WP1 Tasks 3–5.

## 3. Major findings

### P0-M1 — Canonical ID generation contradicts accepted identity contracts

**Claim.** WP1 proposes arbitrary lowercase prefixes plus unhyphenated UUID4 hex, while accepted W2 requires registered kind prefixes and hyphenated UUIDv7. WP2 also uses `arq_` for `AssuranceRequirement`, although W5 owns `asr_`.

**Evidence.** WP1 lines 129–135 define the generic UUID4 format; line 283 uses noncanonical `prj_ars_foundation_p0`. WP2 lines 76–83 use `arq_`. W2 lines 127–167 and verification lines 1087–1102 require prefixed UUIDv7 validation. W5 lines 146–159 define `assurance_requirement_id asr_...`. P-007 preserves the UUIDv7 rule; P-030 requires exact owner-defined identifiers.

**Failure scenario.** Records generated by WP1 fail owner schemas or pass a permissive core validator under the wrong record kind; cross-spec references cannot resolve reliably.

**Impact.** Identity ambiguity, schema incompatibility, and unreliable replay/reference validation.

**Disposition.** Amend the plan before implementation. If the accepted W7/W8 prefix catalogues require a grammar wider than W2's three-letter wording, record a bounded versioned identity reconciliation rather than silently weakening the validator.

**Exact change.** Replace arbitrary `new_id(prefix)` with owner-registered record-kind constructors and validators using UUIDv7; test every accepted prefix and reject unknown/wrong-kind prefixes. Replace the template project value with a canonical project identity or explicitly classify it as a non-ID alias.

**Affected decisions/work packages.** P-007/P-030; W2 section 6; W4/W5/W6/W7/W8 owner catalogues; WP1 Tasks 1–2; WP2 Task 1; WP4 schemas.

### P0-M2 — The provider-capacity gate compares bytes with provider-token capacity

**Claim.** WP2 labels UTF-8 byte length as `provider_token_upper_bound` and compares it directly with `usable_capacity * 0.80` without a validated byte-to-token bound or provider/model scope.

**Evidence.** WP2 lines 274–278 return UTF-8 bytes under provider-token units; lines 229–234 exercise that value against `usable_capacity`. W3 lines 202–213 require separate unit-safe gates and either the exact provider tokenizer or a W7-evaluated conservative upper-bound counter. W7 lines 221–230 require versioned provider/model accounting, usable-capacity derivation, wrapper/system reserve, and fail-closed handling.

**Failure scenario.** `usable_capacity` is tokens while `count` is bytes. ASCII and multibyte inputs receive incomparable margins; the same candidate may be wrongly rejected or admitted depending on encoding rather than a validated provider bound.

**Impact.** Invalid routing eligibility and inability to prove F-028 or Gate 3 token semantics.

**Disposition.** Fix now.

**Exact change.** Treat UTF-8 bytes as diagnostic evidence only. Define an evaluated upper-bound interface whose units are provider tokens, scoped to provider/model/rendering/wrapper revision, with calibration evidence and expiry. Preserve independent reference-token and provider-token fields and tests.

**Affected decisions/work packages.** P-028/P-030; W3 section 8; W7 section 13; 06c sections 3/5/7; WP2 Task 2; WP3 Tasks 1–2; F-028.

### P0-M3 — WP2 implements the wrong W5 assurance universe and identity

**Claim.** WP2 invents ten `CORE_LANES`, renames accepted lanes, and reduces `AssuranceRequirement` to a small record that omits the requirement-scope reviewer, canonical epistemic floor evidence, exact owner/revision/hash/source position, complete applicability authority, and human gates.

**Evidence.** WP2 lines 146–168 define the ten-lane model. Accepted W5 lines 19–29 and 185–205 define six core lanes and the full requirement contract; lines 161–173 and 291–320 require producer-independent requirement-scope review and activation authority. F-035 explicitly attacks an omitted or producer-weakened lane universe.

**Failure scenario.** A producer authors and accepts an R2 record containing the invented lane set, with no distinct scope reviewer or R3 action-semantic check; schema tests pass while F-035's attack remains representable as valid.

**Impact.** Assurance weakening and no-self-approval bypass.

**Disposition.** Fix now.

**Exact change.** Import the exact six owner-defined W5 lane identifiers; represent software/operations/privacy as assertion classes, evidence classes, or reviewed pack extensions rather than silent core additions. Implement the complete W5 section 7 requirement fields and lifecycle, including `asr_`, prospective-producer relationship evidence, independent scope review, and R3/Stephen gates.

**Affected decisions/work packages.** P-022/P-023/P-029; W5 sections 6–11 and 17; WP2 Tasks 1 and 3–5; F-014/F-035/F-036.

### P0-M4 — WP2/WP3 share no coherent prepared-dispatch interface, and fixture ownership collides

**Claim.** WP2 returns `PreparedDispatch(context, route, state)` while WP3 immediately requires `prepared.provider_evidence` and `prepared.attempt_id`. WP2 also claims F-032/F-034 integration tests even though the master plan and WP4 assign those cases to adapters/operations.

**Evidence.** WP2 lines 535–542 construct the object; WP3 lines 478–487 consume missing fields. WP2 lines 443–510 claim F-031–F-034; the master plan assigns WP2 F-031/F-033 and WP3 F-032/F-034; WP4 line 500 preserves that split.

**Failure scenario.** WP2 passes independently, WP3 cannot construct a provider command or grant because evidence/attempt identity is absent; parallel branches add incompatible helpers or duplicate fixture ownership.

**Impact.** Work-package integration failure, shared-helper collision, and unverifiable two-stage ordering.

**Disposition.** Fix now.

**Exact change.** Add a single owner-defined `PreparedDispatch` schema/model with all exact W2/W3/W4/W5/W6/W7/W8 bindings, hashes, expiry, and state. Assign each shared module/helper and fixture test to one work package; other packages consume it through contract tests. Keep F-032/F-034 orchestration assertions in WP3/WP4, with WP2 limited to route primitives and explicit provider/operations ports.

**Affected decisions/work packages.** P-029/P-030; 06c sections 3/7; WP2 Tasks 4–5; WP3 Task 5; WP4 Task 5.

### P0-M5 — W7 parity and W8 conflict predicates can falsely pass

**Claim.** `build_parity_report()` checks only manifests supplied by the caller and can pass a critical control when one required first-release provider is absent. `has_resource_conflict()` examines only the requested mode and misses a shared request against an already exclusive held resource.

**Evidence.** WP3 lines 141–155 iterate caller-supplied manifests with no required provider set; lines 381–382 ignore the held mode. W7 lines 276–290 require one Claude and one Codex disposition per control. W8 lines 159–178 require typed atomic `exclusive`, `capacity_shared`, and `read_shared` conflict evaluation.

**Failure scenario.** A critical control is supported by Claude but Codex has no manifest; parity returns `passed`. Separately, a `read_shared` request is admitted while the key is held `exclusive`.

**Impact.** Unsupported provider eligibility or unsafe resource overcommit.

**Disposition.** Fix now.

**Exact change.** Bind parity to the accepted evaluated provider set and emit `unsupported/missing` rows for absent manifests. Implement a symmetric compatibility matrix over requested and held modes/capacities and atomically test all mode pairs.

**Affected decisions/work packages.** P-025/P-029/P-030; W7 section 17; W8 sections 9/11; WP3 Tasks 1 and 3; F-020/F-031/F-034.

### P0-M6 — Required sizing, calibration, and adapter-variant decisions remain placeholders

**Claim.** The suite names files and fixtures but does not set the exact repeated-run counts, uncertainty rules, calibration acceptance evidence, or adapter fixture revisions/variants required before activation. Its F-021/F-022 “measurement” test asserts only a literal metadata dictionary.

**Evidence.** WP2 lines 237–239 do not compile or count a context. WP4 names `threshold-policies.yaml` and generic fields but supplies no exact model-grader run counts or decision rules. W3 lines 561–579 and 06a section 4 require empirical mandatory-closure sizing for F-025/F-026/F-021/F-022 under both gates. W4 lines 264–289, 06b section 4, and W6 lines 543–557 require exact repeated-run counts, uncertainty, false-accept/false-reject evidence, and threshold ownership. W7 line 366 requires exact adapter fixture revisions/variants.

**Failure scenario.** Fixture packages exist and one paired test passes, but no accepted sampling/calibration rule establishes model-grade reliability or provider/profile closure. Activation becomes dependent on implementation-time defaults.

**Impact.** Gate 1 and P0 release cannot be decided reproducibly; implementation would invent foundation-critical policy.

**Disposition.** Owner decision required before implementation.

**Exact change.** Add a forward-obligation appendix that maps every deferred specification obligation to an exact policy/fixture/review owner. Define the four sizing matrices and recorded outputs; enumerate adapter/provider/model/rendering variants; set or explicitly block pending accepted repeated-run/uncertainty/false-accept rules. No implementation task may choose these values ad hoc.

**Affected decisions/work packages.** P-018/P-028/P-029/P-030; W3/W4/W6/W7; 06a/06b; WP2 Task 2; WP4 Tasks 4–6.

### P0-M7 — Deletion verification is modeled as caller-supplied booleans, not a verifier

**Claim.** WP4's concrete `deletion_verdict()` trusts five booleans and has no evidence-root identity, authorized-location registry, filesystem inspection, evidence hash, replica receipt, actor/authority, or immutable proof binding.

**Evidence.** WP4 lines 398–408 define the boolean predicate and then promise stronger behavior in prose. The master plan section 7 requires absence from primary/runtime/staging/temp/registered replicas, proof canonical payloads never contained the content, projection rebuild, and an R0 `EvidenceDeletionVerified` event/receipt. W6 lines 559–572 require accepted ownership and deletion verification for each R1/R2 type.

**Failure scenario.** A caller sets all booleans true while a stale staging copy or unregistered replica remains; the release report treats deletion as verified.

**Impact.** False deletion assurance and possible restricted-evidence retention.

**Disposition.** Fix now and retain the duration/authority rows as owner decisions requiring explicit acceptance.

**Exact change.** Define a verifier that derives checked locations from an immutable authorized evidence-store/replica registry, performs the checks, hashes the verification manifest, records inaccessible locations as pending, and emits the event/receipt only through WP1. Add adversarial tests for stale temp/staging copies, inaccessible replicas, symlink/junction escape, canonical payload contamination, and self-approved extension/deletion.

**Affected decisions/work packages.** W6 section 28; master section 7; WP1 command/replay; WP4 Task 3; retention-owner approval.

## 4. Minor and editorial corrections

1. WP1 lines 60–65 place raw file paths inside a Python block; executing the snippet is a syntax error. Split files into separate fenced blocks or comments.
2. WP1's multi-line ruff example lists paths as separate PowerShell commands. Put the full command on one line or use a PowerShell argument array.
3. Rename the master retention-table column `Review lead` to `Review lead time`; its values are durations, not actors.
4. Define every helper used in tests (`load_catalogue`, `load_fixture`, `evaluate_hard_gates`, `route_failure`, `route_decision`, `PreparedDispatch`) in the owning task/file map, with one stable signature and contract test.
5. Specify the external root safety predicate across all registered code worktrees and Windows reparse-point/symlink resolution; the current WP1 helper checks only whether the control root is beneath one code root.

## 5. Decision and work-package audit

| Suite item | Disposition | Reason |
|---|---|---|
| Master §§1–3 authority, package order, file layout | Keep with amendments | Non-migration and WP1 -> WP2/WP3 -> WP4 order are sound; shared interface ownership needs P0-M4 reconciliation |
| Master §4 exact materialization closure | Keep | The listed set has exactly 37 unique IDs; F-021 remains P1 with `p0_materialization`; S-014/S-015/S-016 remain deferred |
| Master §5 checkpoints | Amend | Add identity, crash-receipt, mandatory-context, release-closure, and policy-value freezes before package consumption |
| Master §7 retention proposal | Owner decision required | Durations/owners/extension authorities are proposals; P0-M7 blocks technical acceptance |
| Master §§8–10 commands, evidence, stop rules | Keep with amendments | Boundaries are conservative; exact plan commands/helper APIs need repair |
| WP1 Task 1 | Rework | P0-M1 and malformed snippets |
| WP1 Task 2 | Rework | Owner-prefix/schema validation and canonical project identity |
| WP1 Task 3 | Rework | External-root/worktree/reparse checks and writer-recovery authority |
| WP1 Task 4 | Rework | P0-C3 accepted-command reconstruction and exact idempotency tuple |
| WP1 Task 5 | Rework | Fault-injection coverage must include commit-before-receipt and exact receipt reconstruction |
| WP2 Task 1 | Rework | P0-C1/P0-M1/P0-M3 |
| WP2 Task 2 | Rework | P0-M2/P0-M6 and real four-fixture sizing |
| WP2 Task 3 | Rework | Bind exact W5 requirement/relationship evidence rather than reduced booleans |
| WP2 Task 4 | Rework | Exact W4 reason/identity catalogue and fixture ownership split |
| WP2 Task 5 | Rework | P0-M4 shared interface |
| WP3 Task 1 | Rework | P0-M5 complete provider matrix |
| WP3 Task 2 | Amend | Preserve normalized/minimized receipts and prohibit full stdout/stderr transcript persistence |
| WP3 Task 3 | Rework | P0-M5 symmetric resource compatibility |
| WP3 Task 4 | Amend | Add complete checkpoint schema/design/epoch/root compatibility and verified stop paths |
| WP3 Task 5 | Rework | P0-M4 and lifecycle commands must be explicit in the algorithm, not prose only |
| WP4 Task 1 | Rework | Implement exact W6 fields/IDs rather than the reduced illustrative dataclasses |
| WP4 Task 2 | Rework | P0-C2 exact grader-set closure |
| WP4 Task 3 | Rework | P0-M7 and explicit owner acceptance |
| WP4 Task 4 | Amend | Exact 37-case closure is right; add accepted revision/variant matrix |
| WP4 Task 5 | Rework | P0-M6 paired and repeated calibration policy; independent grader authority |
| WP4 Task 6 | Rework | P0-C2 complete release decision and Gate 5 deferrals |

## 6. Cross-spec invariant and test matrix

| Invariant | Enforcement point required | Current test disposition |
|---|---|---|
| Exact owner identity and UUID format | Core ID registry plus every schema | Missing/contradicted — P0-M1 |
| One committed command batch and reconstructible receipt | Writer, event-derived idempotency index, recovery | Incomplete — P0-C3 |
| One registered writer/control store | Store identity, lock/lease recovery, branch rejection | Partial; stale/crash recovery and all-worktree root checks need specification |
| Mandatory W3 closure cannot be omitted | Compiler validation before route/issue | Incorrect — P0-C1 |
| Reference/provider token units remain separate | W3/W7 counter evidence and W4 gate | Incorrect — P0-M2 |
| Complete W5 lane/floor/scope authority | `AssuranceRequirement` lifecycle and schemas | Incorrect/incomplete — P0-M3 |
| Provider/operations evidence precedes route; grant follows route | Shared `PreparedDispatch` and coordinator trace | Interface mismatch — P0-M4 |
| Claude/Codex critical parity is non-compensable | Required provider matrix | Incomplete — P0-M5 |
| Hard resource conflicts never overcommit | Atomic symmetric compatibility matrix | Incorrect — P0-M5 |
| Every required fixture/grader is present and passes | Coverage manifest and release decision | Incorrect — P0-C2 |
| F-021 stays P1 while sizing runs at P0 | Catalogue/fixture schema | Correct metadata; executable sizing absent — P0-M6 |
| R1/R2 payload deletion is evidenced, not asserted | Authorized evidence registry/verifier and event receipt | Incomplete — P0-M7 |
| Gate 5/pilot cases remain deferred | Coverage/release capability restrictions | Correct in scope text; release function must enforce it |

## 7. Coverage and fixture disposition

The master and WP4 lists contain the same 37 unique IDs: 25 priority-P0 F cases, the P1 F-021 sizing variant, and 11 S cases. No listed ID is duplicated, and F-021 is not relabeled. S-014/S-015/S-016 remain outside P0.

Coverage is nevertheless not activation-ready:

- F-021/F-022/F-025/F-026 do not yet have executable two-gate sizing tests or measurement records;
- F-031/F-033 ownership belongs to WP2, while F-032/F-034 integrated ownership belongs to WP3/WP4;
- F-035 requires the exact six-lane W5 universe and requirement-scope authority;
- F-036 requires all declared graders and accepted calibration policy, not one result per fixture;
- adapter/provider/model/rendering revisions and variants are not enumerated;
- S-011 lacks explicit commit-before-receipt reconstruction coverage.

## 8. Practicality and proportionality

The modular monolith, deterministic fakes, explicit roots, and four-package order are proportionate. The plans become impractical where they duplicate policy truth in illustrative dataclasses/tables or leave critical values to implementation-time choice. The smallest acceptable correction is not a larger architecture; it is a narrower contract layer:

1. exact owner schemas and identity registry;
2. one shared prepared-dispatch contract;
3. one event-derived idempotency/recovery contract;
4. one coverage/grader-closure algorithm;
5. one authorized evidence-store/deletion-verification contract;
6. one forward-obligation matrix with owner-approved policy values.

## 9. Required revision plan

### Immediate plan corrections

1. Correct P0-C1 through P0-C3 and P0-M1 through P0-M5 in the child plans and tests.
2. Add explicit shared-module ownership, signatures, and cross-package contract tests.
3. Repair literal command/code snippets and external-root safety tests.
4. Replace reduced illustrative models where they contradict owner specifications.

### Owner decisions

1. Accept or amend the R1/R2 durations, review-lead times, owners, extension authorities, consumers, replica policy, and `EvidenceDeletionVerified` semantics.
2. Resolve any registered-prefix grammar conflict between W2's UUIDv7 wording and accepted downstream owner catalogues without inventing implementation-only aliases.
3. Accept exact repeated-run counts, uncertainty/calibration policy, false-accept/false-reject evidence, and provider/model/adapter variant scope, or keep affected capabilities explicitly blocked.

### Later dependencies retained

1. S-014 backup/restore, S-015 supersession cycle, and S-016 R3 outage remain Gate 5/pilot dependencies.
2. Live provider smoke remains a separate bounded approval after deterministic WP3 review.
3. Migration, active APM adoption, greenfield pilot initialization, and claim promotion remain separately prohibited.

## 10. Residual risks

- A local single-writer lock that is safe but unrecoverable after host death can halt the system; stale-lock break authority must be evidence-based and integrated with W8 process/lease recovery.
- Provider CLI flags and capabilities can drift after plan acceptance; activation must bind locally verified versions and expire on change.
- Synthetic scientific fixtures can validate the harness while retaining a weak oracle; independent F-011/F-012/F-022/F-026/F-035/F-036 review remains mandatory.
- Windows junctions/reparse points can defeat lexical root checks; root identity must use resolved paths and tested escape cases.

## 11. Change log and verification evidence

**Files edited by this review:**

- `docs/plans/agentic-research-system/reviews/adversarial-p0-plan-suite-review-2026-07-01.md` — new review record only.

**Read-only live-state evidence:**

- repository/worktree: `C:\Users\steph\TDL`, branch `main`;
- review base: `172fdefa30b3014019e48b8a8e15e8bce760c087`;
- P0 plan commit `9c55cb2fe5dbafe27ccf1dda0feac1d053c110d9` and Gate 3 acceptance `bdff66f` are ancestors of the review base;
- ARS planning tree was clean before this review write;
- existing unrelated `.superpowers` and research result/checkpoint changes were not used as P0 evidence and were not modified;
- local `codex exec --help` confirms the planned Codex flags `--ephemeral`, `--ignore-user-config`, `--json`, and stdin `-`; local Claude help could not run without the documented Git-Bash environment, so Claude flags remain subject to version-bound WP3 verification.

**Required documentation verification after reconciliation:**

```powershell
git diff --check
git diff --cached --check
```

Before any reconciliation commit, run GitNexus `detect_changes(scope: staged)`, inspect the staged diff, and confirm no implementation, `.apm/`, research, contract, result, checkpoint, cache, vault, external control-root, or evidence-root path changed.

## 12. Gate outcome

**Outcome:** `REWORK_REQUIRED — P0 plan review completed; implementation remains unauthorized pending required plan reconciliation, owner decisions, documentation verification, and Stephen's explicit approval of the exact revised scope`.
