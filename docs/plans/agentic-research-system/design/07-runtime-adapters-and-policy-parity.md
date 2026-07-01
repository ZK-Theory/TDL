# W7 — Runtime Adapters and Policy-Parity Specification

**Date:** 2026-07-01<br>
**Status:** Draft complete; joint Gate 3 review pending<br>
**Specification version:** 0.1<br>
**Design authority:** Accepted W1–W5, W6 catalogue/addenda, D-001–D-008, P-001–P-029, and Stephen's approved Gate 3 conceptual design<br>
**Implementation authority:** None; this document creates no adapter, hook, generated policy, provider invocation, credential, runtime, migration, fixture, or `.research-system/` state<br>
**Review owner:** Stephen; bounded joint W6/W7/W8/06c adversarial review required

## 1. Decision summary

W7 defines a provider-neutral runtime boundary that prevents model choice from changing the safety or research policy applied to a Task.

It makes these binding draft choices:

1. canonical policy is a versioned semantic bundle, never `CLAUDE.md`, `AGENTS.md`, a hook file, a skill tree, or provider prose;
2. adapters translate accepted ARS requests into provider actions and normalize receipts; they do not allocate canonical event positions or decide acceptance;
3. every provider/model/profile advertises explicit capabilities and absences; unsupported semantics are not emulated silently;
4. Claude and Codex are the only first-release evaluated families, but neither receives universal eligibility;
5. parity is semantic, field-by-field, and fail-closed; byte identity between provider files is neither necessary nor sufficient;
6. provider fallback is a new W4 route under the original immutable requirements, not an adapter shortcut;
7. credentials, hidden reasoning, raw restricted data, and full transcripts never enter policy or receipt records;
8. changes to provider, adapter, hook, generated file, skill package, tokenizer, or tool mapping stale affected eligibility and require declared W6 coverage.

## 2. Sources and evidence

W7 implements:

- W1 provider-neutral core, single-writer boundary, and adapter ownership;
- W2 command, message, receipt, authority, idempotency, and non-shared compatibility rules;
- W3 immutable context bytes/hashes, two token gates, sensitivity, exclusions, and delivery evidence;
- W4 capability profiles, eligibility-first routing, immutable routing snapshots, fallback, permissions, and family coverage;
- W5 assurance/review visibility and prohibited producer-material rules;
- W6 F-020, F-028, F-031–F-034, S-006, S-007, S-013, and S-016 obligations;
- current-system evidence that Claude/Codex hooks, guides, and root instructions diverge and that blind skill synchronization can erase stronger safeguards.

The existing `tools/sync_agent_skills.py` is evidence of a useful fail-safe classification pattern, not the W7 implementation and not canonical ARS policy.

## 3. Scope and exclusions

### 3.1 In scope

- canonical policy representation and compilation inputs;
- adapter identity, capability and lifecycle;
- normalized provider command and receipt envelopes;
- Claude and Codex semantic mappings;
- tool, root, network, write, sensitivity and context semantics;
- hook/guide/skill generation boundaries;
- policy-parity evidence, upgrades, suspensions and rollback;
- provider outage and failure classification;
- trace, privacy and W6 coverage requirements.

### 3.2 Out of scope

- implementing adapters or generated provider files;
- invoking provider APIs or local CLIs;
- storing credentials or configuring accounts;
- selecting models, routes, assurance lanes or human authority;
- command-service/event-store implementation;
- executable P0 fixtures or calibration results;
- migration of `.claude/`, `.codex/`, `.agents/`, `.apm/`, active tasks or current papers.

## 4. Ownership boundary

| Concern | Owner | W7 responsibility |
|---|---|---|
| Canonical Task/event state | W1/W2 command service | Submit typed commands; never write event batches directly |
| Context content and token gates | W3 | Deliver exact accepted candidate and return provider accounting evidence |
| Route/profile/model selection | W4 | Enforce selected profile and report capability/availability; never rerank |
| Assurance/review requirements | W5 | Preserve exact visibility, independence and prohibited-material constraints |
| Fixture verdict/release evidence | W6 | Emit gradeable normalized evidence; never declare fixture pass |
| Resources/process/checkpoints | W8 | Consume grants and emit provider-side observations; never grant resources |
| Provider translation/parity | W7 | Own semantic mappings, capability declarations, receipts and parity reports |

An adapter is an untrusted boundary component. Provider success, exit code zero, a generated file, or a delivered message is evidence to validate, not an ARS state transition.

## 5. Core identities

```text
canonical_policy_bundle_id   cpb_...
adapter_profile_id           adp_...
adapter_capability_id        acm_...
provider_command_id          pcmd_...
provider_receipt_id          prcp_...
policy_parity_report_id      ppr_...
adapter_upgrade_decision_id  aud_...
generated_projection_id      gpr_...
```

Every object carries revision, content hash, schema major/minor, effective interval, owner, source positions, supersession lineage, and currency triggers.

## 6. Lifecycle

### 6.1 Policy bundle

```text
draft -> reviewed -> accepted -> active
accepted/active -> superseded | retired
```

A bundle is not active merely because provider projections were generated. Activation requires accepted semantic coverage and successful applicable W6 gates.

### 6.2 Adapter profile

```text
draft -> mapped -> evaluated -> eligible
mapped/evaluated -> rejected
eligible -> suspended -> eligible | retired
eligible -> superseded
```

Any change to provider family, model/version, adapter code, tokenizer/accounting, tool surface, hook interface, generated policy, reasoning setting, or provider terms creates a new revision or forces reevaluation.

### 6.3 Provider command

```text
prepared -> issued -> acknowledged -> terminal
prepared/issued -> blocked | expired | superseded
issued/acknowledged -> timed_out | uncertain
```

`uncertain` is not success. Reconciliation requires a provider receipt or a safe idempotent retry tied to the original command.

## 7. `CanonicalPolicyBundle`

Required fields include:

- identity/revision/hash/schema and effective scope;
- accepted W1–W8 policy/rule IDs and source hashes;
- normalized action classes, preconditions, denials and failure codes;
- role/profile, risk, assurance, independence and human-gate constraints;
- context byte/hash, token-accounting, sensitivity and prohibited-source rules;
- command/message/tool/root/network/write semantics;
- resource/lease/checkpoint/stop evidence required from W8;
- normalized receipt and trace obligations;
- provider projection targets and allowed provider-specific additions;
- W6 coverage manifest and activation/suspension criteria;
- privacy, redaction, retention and prohibited fields.

Provider-specific files are projections with bundle ID/hash and generator version. A hand-edited projection becomes divergent evidence; it cannot silently amend canonical policy.

## 8. `AdapterCapabilityManifest`

Each provider/model/adapter profile declares:

- exact provider, model, family, version/alias and reasoning controls;
- supported command, tool, message and receipt classes;
- tokenizer/accounting method, usable-input calculation and evidence quality;
- context delivery byte preservation and content-hash support;
- root/path and permission granularity;
- network, external-write and restricted-data controls;
- hook/pre-action/post-action/error interception semantics;
- streaming, cancellation, timeout, idempotency and reconciliation support;
- process/resource observations exposed to W8;
- known absences, degraded semantics and prohibited risk/capability combinations;
- evaluation revision, expiry and suspension triggers.

Missing features are `unsupported`, not inferred from provider marketing or approximated without an accepted W7 mapping and W6 evidence.

## 9. `ProviderCommand`

A normalized command binds:

- provider-command ID and idempotency key;
- W2 command/message/dispatch ID and expected control-store position;
- selected W4 route/profile/eval/policy and routing-snapshot IDs/hashes;
- W3 context candidate/packet/addendum IDs, exact content hash and both token-gate evidence;
- W5 assurance/review purpose, subject/evidence visibility and prohibited producer material;
- W8 resource grant, lease and stop-policy IDs;
- normalized operation class and provider-specific rendered payload hash;
- tools, roots, network/write/sensitivity classes and default-deny set;
- expected receipt fields, timeout, expiry and retry/reconciliation policy.

The adapter cannot add permissions, omit mandatory context, weaken risk/assurance, alter the selected model/profile, or substitute another provider command under the same identity.

## 10. `ProviderReceipt`

Required fields include:

- command/provider/profile/adapter/policy identities and hashes;
- provider request/session/response IDs where exposed;
- issued, acknowledged and terminal timestamps;
- exact delivered context/payload hash or an explicit inability to prove it;
- provider token count/accounting method and capacity outcome;
- tools/actions attempted, allowed, denied and completed;
- normalized terminal status and provider-native status/error class;
- output/artefact/message references and hashes;
- cancellation/timeout/retry/duplicate/reconciliation evidence;
- resource/process observations linked to W8;
- redaction and omitted-evidence declarations.

A receipt is incomplete if it cannot bind the actual provider/model/profile and exact command revision. Incomplete receipts may support diagnosis but cannot satisfy dispatch, delivery or review gates.

## 11. Normalized operation classes

First-release W7 supports only operation classes required by the narrow foundation:

```text
deliver_context
request_model_work
invoke_declared_tool
submit_ars_command
deliver_message
request_review
cancel_provider_work
query_provider_status
```

`submit_ars_command` submits to the W2 command service; it never writes canonical storage. External publication, arbitrary shell/network access, credential management and unrestricted provider plugins are outside the initial surface.

## 12. Permissions and tool semantics

- Effective permission is the intersection of W4 profile, W2 authority grant, W7 adapter capability and W8 operational grant.
- Any missing dimension denies the action.
- Read, write, execute, network, external publication and decision authority remain distinct.
- Provider-native broad permission modes cannot widen the canonical grant.
- Roots use W1/W2 typed identities; cwd inference is diagnostic only.
- Tool aliases map to normalized operation classes and include argument/result hashes with secret/restricted fields redacted.
- A denied tool call is part of the normalized trace and cannot be suppressed as provider noise.

## 13. Context and token accounting

W7 preserves W3's two independent gates:

1. the versioned reference-token count satisfies the risk-profile ceiling;
2. exact bound-provider counting, or a W7-evaluated conservative upper bound, satisfies 80% of provider usable input.

Counts from different tokenizers are never compared as one unit. The adapter records the accounting method/version, usable-capacity derivation, rendered provider payload hash and whether any provider wrapper/system material is included. Missing or stale accounting blocks issue.

Provider rendering may add required wrapper syntax but cannot change managed content, fragment order or hashes without producing a new W3/W7 candidate and rerouting.

## 14. Generated hooks, guides and skill packages

Canonical policy compiles into provider projections only when each projection declares:

- source bundle and generator identity/hash;
- semantic controls implemented, unsupported or provider-native;
- precedence relative to provider/global/project instructions;
- failure mode (`fail_closed`, `diagnostic_only`, `not_supported`);
- expected parity tests and W6 coverage;
- local additions that are explicitly noncanonical.

Byte mirroring is allowed only for artifacts classified runtime-agnostic. A richer destination cannot be overwritten by a poorer source merely because one tree is named canonical. Divergence produces a report and blocks affected eligibility until reconciled.

## 15. Claude first-release mapping

The Claude adapter specification must map:

- project/user instruction precedence and generated policy projection;
- skill discovery/package identity;
- pre/post tool hooks and whether failures block;
- tool allow/deny and root semantics;
- context delivery and token accounting;
- model/family/version/reasoning identity;
- command/message/receipt correlation and cancellation.

Existing `.claude/` material is legacy evidence. W7 does not bless its current contents or sync direction.

## 16. Codex first-release mapping

The Codex adapter specification must map the same normalized fields for:

- AGENTS/instruction precedence and generated policy projection;
- skill/plugin discovery and package identity;
- approval/sandbox/tool permission behavior;
- hook availability or explicit absence;
- workspace roots, command execution and file-write semantics;
- context delivery and token accounting;
- model/family/version/reasoning identity;
- command/receipt correlation, cancellation and uncertain outcomes.

Codex capability absence relative to Claude is a parity finding, not permission to drop the canonical control.

## 17. `PolicyParityReport`

A parity report is computed against one canonical bundle and contains one row per normalized semantic control:

| Field | Meaning |
|---|---|
| control ID/revision | Canonical semantic identity |
| required risk/capability | Where the control is mandatory |
| Claude disposition | native, generated, adapter-enforced, unsupported, divergent |
| Codex disposition | native, generated, adapter-enforced, unsupported, divergent |
| evidence | Projection/hook/test/receipt IDs and hashes |
| consequence | eligible, constrained, suspended, blocked |
| owner/resume condition | Required remediation |

Aggregate parity percentages are diagnostic only. One missing critical control blocks the affected capability/risk route.

## 18. `AdapterUpgradeDecision`, upgrade and rollback

`AdapterUpgradeDecision` is the immutable authority record that promotes, suspends, constrains, or rolls back an adapter/provider revision. It records:

- predecessor/successor identities and semantic diff;
- capability, tokenizer, tool, hook, permission and receipt changes;
- affected routes/profiles/contexts/fixtures;
- W6 coverage selected and omitted with rationale;
- rollout window, canary scope and rollback target;
- approving authority and suspension behavior.

Poorer projections never overwrite richer policy. Rollback creates a new active revision and preserves all prior commands, receipts and parity evidence.

## 19. Outage, fallback and uncertain completion

- Provider outage marks affected candidates unavailable and invokes W4 fallback under the original request.
- W7 never chooses a substitute provider/model or lowers independence.
- If issue status is uncertain, the adapter queries provider status or retries only with proven idempotency.
- Duplicate responses remain linked; they do not create duplicate W2 commands/events.
- If exact delivered bytes/model identity/receipt cannot be proven, dispatch or review satisfaction fails even when output exists.

## 20. Failure behavior

| Failure | Required result |
|---|---|
| Canonical bundle missing/stale | Block generation and provider issue |
| Projection hash/source mismatch | `policy_projection_divergent`; suspend affected profile |
| Critical semantic unsupported | Mark capability absent; no emulation or lower-risk fiction |
| Adapter/provider/model identity changed | Expire command/route; require reevaluation |
| Provider accounting unavailable/stale | Block W3 provider gate and issue |
| Managed context hash differs after rendering | Reject command before issue |
| Permission/root/sensitivity mismatch | Deny action; no widening |
| Missing/incomplete receipt | `provider_completion_unproven`; no dispatch/review satisfaction |
| Hook/provider failure is diagnostic-only for a required control | Capability ineligible until adapter enforcement exists |
| Parity report has critical gap | Fail affected W6/W7 release gate |
| Provider outage | Reroute through W4 or block; preserve every requirement |
| Retry cannot prove idempotency | Do not retry automatically; `input_required`/reconciliation |

## 21. Privacy and retention

- Credentials, provider tokens, `.env`, raw restricted data, hidden reasoning and full transcripts are prohibited.
- Provider-native IDs may be stored; raw prompts/responses are retained only when separately authorized and minimized.
- Restricted inputs use opaque local references or approved tools, never convenience copying.
- Normalized command/receipt evidence retains hashes, semantic classes and redaction declarations sufficient for W6 grading.
- Provider deletion does not erase canonical ARS evidence; it records external unavailability.

## 22. Observability

W7 emits normalized evidence for:

- policy/projection/adapter/provider/model/profile identities;
- semantic-control coverage and parity;
- exact command/rendered-payload/context hashes;
- token/accounting and usable-capacity derivation;
- tool/permission/root/sensitivity decisions;
- provider acknowledgements, terminal status and receipts;
- outage, fallback trigger, retry, cancellation and reconciliation;
- actual versus expected latency/cost/resource observations without hidden reasoning.

## 23. W6 coverage obligations

Foundation-critical W7 coverage includes:

- F-020 provider policy drift;
- F-028 token/accounting overflow;
- F-031 deterministic routing evidence inputs;
- F-032 requirement-preserving outage fallback;
- F-033 verifier-route/provider-family evidence;
- F-034 permission/root/sensitivity denial;
- S-006 non-shared compatibility ownership;
- S-007 exact review-subject identity;
- S-013 unauthorized adapter command;
- S-016 required-provider outage.

Priority and `gate_stage` remain separate. The later P0 plan must bind exact fixture revisions/variants to each implemented adapter surface.

## 24. Downstream constraints

### W6

Grade normalized semantic controls, commands, receipts and parity evidence. Do not treat provider success or byte-identical projections as parity.

### W8

Define process/resource/lease/checkpoint evidence used by commands and receipts. W7 cannot synthesize operational proof.

### W9/W10

Migration and templates may generate provider projections only from accepted canonical bundles. TDL-private paths and provider credentials never enter public templates.

## 25. Joint Gate 3 review questions

1. Can any provider-specific convenience weaken a W3/W4/W5 requirement?
2. Can missing hook semantics be disguised as parity by generated prose?
3. Can a provider success response satisfy ARS without an exact normalized receipt?
4. Can fallback change model family, permissions, context or independence without rerouting?
5. Are tokenizer units and usable-capacity calculations dimensionally explicit?
6. Can blind synchronization erase a richer safeguard?
7. Are unsupported semantics explicit enough to constrain eligibility?
8. Can an adapter or provider write canonical state directly?

## 26. Review gate

W7 can move from `review_pending` to `accepted` only when Stephen confirms after joint W6/W7/W8/06c review that:

- [ ] Canonical policy is provider-neutral, versioned and separate from projections.
- [ ] Every normalized action has one command/receipt meaning and authority boundary.
- [ ] Claude and Codex mappings expose explicit capabilities and absences.
- [ ] Tool/root/network/write/sensitivity semantics are default-deny and non-widening.
- [ ] W3 byte/hash and two-token-gate semantics survive provider rendering.
- [ ] Critical parity is non-compensable and safeguard deletion fails closed.
- [ ] Provider fallback always returns through W4 under original requirements.
- [ ] Uncertain completion, retry and cancellation preserve idempotency and evidence.
- [ ] Privacy rules exclude credentials, restricted data, hidden reasoning and full transcripts.
- [ ] W6 receives sufficient evidence to grade commands, receipts, parity and upgrades.
- [ ] No adapter, hook, generated file, provider invocation, migration or active-task change is introduced.

## 27. Outcome

**Outcome:** `REVIEW_PENDING — W7 v0.1 runtime-adapter and policy-parity specification complete; implementation and P0 evidence remain gated`.

The next action is bounded joint Gate 3 adversarial review with W6 v0.3, W8 v0.1 and manifest 06c. No adapter implementation or policy generation begins before that review and a separately approved P0 plan.
