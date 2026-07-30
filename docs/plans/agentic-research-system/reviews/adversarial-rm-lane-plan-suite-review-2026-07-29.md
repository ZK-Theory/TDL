# Adversarial review: RM lane plan suite (G-RM-3)

**Review date:** 2026-07-29

**Review subject:** `6e7d0e0add73ab4af33ebcf2acb96ae73f6d97e2`

**Reviewer:** OpenAI Codex, GPT-5 family, fresh task context
**Independence basis (P-022):** this reviewer did not author the suite and did
not inspect or reconstruct its authoring-session transcript or hidden reasoning.
The exact subject, governing specifications, implementation source, vault
sources, current repository state, and the review brief were visible. This is
contextual/model independence, not independent human authority.
**Assurance lanes:** Output/Provenance primary. RM-03's acceptance firewall and
RM-04's manuscript-review and candidate-verification interfaces also touch
Paper Claim governance. No mathematical, statistical, topological, or
representation result was recomputed.

## Exact-subject and source identity gate

The hard drift gate passed. The following identities were recomputed before
review:

| Subject | Recomputed identity | Expected | Result |
|---|---|---|---|
| `implementation/rm-00-research-methods-lane-master-plan.md` | `911243b773a906a1cc9f92af0631d2251cd7e1ee` | same | match |
| `implementation/rm-01-unblock-and-suite-recovery-plan.md` | `652bcf24ad21bbc24e6c3d57162d1ba7d1891fbf` | same | match |
| `implementation/rm-02-research-methods-pack-plan.md` | `fb2478f103206a6df0da6e64ea3a8191e19b5ba1` | same | match |
| `implementation/rm-03-brief-export-import-plan.md` | `0126fd2d5f6f19cb811f2c1d4f61f491af10cddd` | same | match |
| `implementation/rm-04-verification-execution-and-manuscript-review-plan.md` | `55ffae966715d547eefbbccf6668a07378ab2eda` | same | match |
| `proposals/research-methods-integration-plan-2026-07-28.md` | `15de3b81f9ab0ab17ff0cc13a18166f9c13e911f` | same | match |
| `proposals/rm-decision-entry-drafts-2026-07-28.md` | `9141f6887d532ecbc71b48f0169c8845130dfd12` | same | match |
| `03-decisions-and-open-questions.md` | `c57bbfe2300f7ccb42b3ca81035e470a1620a2a2` | same | match |
| Vault report 1 | `23873353d96593c35ef4bb1a50eb893af5432c40eb5d1851e1e7dcda74fd426c` | same | match |
| Vault report 2 | `2d727f63139a5063a976b388c76c25652472d86b9f995e52fcfdaff658719650` | same | match |
| Vault source paper | `43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24` | same | match |

The current working copies of all eight pinned Git files also hash to the
subject blobs. No dated addendum is needed for those files.

## Executive verdict

**Suite verdict: `rework_required`.**

- **RM-00 readiness:** `not_ready`
- **RM-01 dispatch:** `reject`
- **RM-02 dispatch:** `reject`
- **RM-03 dispatch:** `reject`
- **RM-04 dispatch:** `reject`

No RM plan is dispatchable as written. The strongest failures are reachable
before implementation:

1. RM-01 is required to emit a digest of the exact schema bytes used for
   validation, but `SchemaRegistry` discards both those bytes and their paths,
   while RM-01 prohibits the registry change needed to expose them.
2. RM-02 requires each asset to contain the SHA-256 of the file that contains
   that SHA-256. This is an unsatisfied cryptographic self-edge.
3. RM-03's `ars://methods/event/...` family is not an accepted event family in
   the ledger/replay implementation, and no planned command types can
   authoritatively produce its events.
4. RM-04 executes arbitrary model-proposed Python with the project interpreter
   beside a gitignored `.env` and vault/data roots, without sandboxing, egress
   denial, mount restriction, W8 grant/lease/process controls, or non-self-
   attested approval.

The direction accepted in P-043/P-044 remains viable. These findings reject
the present execution plans, not those owner decisions.

## Critical findings

### C-1 — RM-01 cannot obtain the exact schema bytes P-043 requires

**Claim.** RM-01 says the producer will compute
`command_schema_sha256` from "the registered command schema actually used to
validate" the command and independently reproduce the digest from the schema
file (`rm-01-unblock-and-suite-recovery-plan.md:18-24, 108-112`). P-043 is
stricter: the digest is of the "exact schema bytes used for that validation —
never of a reserialized or reconstructed representation"
(`03-decisions-and-open-questions.md:787-794`).

**Direct evidence.** `SchemaRegistry.__init__` reads text, parses JSON, and
stores only `dict` values in `_schemas`; `validate()` retrieves only that
parsed value (`research_system/schema_registry.py:53-73, 75-99`). It retains
neither raw bytes, source path, schema version metadata, nor an identity record.
`CommandService` receives only the registry object
(`research_system/command/service.py:99-119`). RM-01's Partial criteria prohibit
editing `schema_registry.py` (`rm-01...md:119-124`).

**Failure scenario.** The Worker either reserializes `_schemas[schema_id]`,
which violates P-043, or independently searches a checkout path after
validation, which does not prove those are the bytes the registry loaded and
introduces a time-of-check/time-of-use seam. Following the plan literally
reaches its own Partial stop.

**Impact.** The event's provenance identity can be false while schema
validation passes. The WP6.1 repair and every downstream RM-03 append-path
dependency remain unavailable. Existing durable events also remain unresolved:
handoff 26 explicitly requires a migration/grandfather/no-prior-store decision
for events lacking the new fields (`handoffs/26-research-system-suite-red-briefing.md:172-185`),
but RM-00/RM-01 do not dispose of it.

**Required disposition:** **fix now; stop RM-01 dispatch.**

**Exact required interface change.** Precede RM-01 with a separately reviewed
WP6.1 schema-identity amendment that exposes an immutable registry entry such
as:

```text
RegisteredSchema {
  schema_id,
  schema_version,
  source_path,
  raw_bytes_sha256,
  raw_bytes_identity
}
```

`validate()` and the producer must consume the same `RegisteredSchema`
instance. The test independently hashes `source_path` and compares it with
`raw_bytes_sha256`. The plan must also record the existing-ledger
migration/grandfather/no-prior-store decision and a replay fixture for that
decision. Remove `schema_registry.py` from the Partial prohibition only through
that accepted amendment.

**Affected decisions/work packages:** P-043, G-RM-1, RM-01 Task A, RM-03
dependency, WP6.1 currency, Gate 6.

### C-2 — RM-02 specifies an impossible self-referential asset hash

**Claim.** The manifest binds each asset's SHA-256, each asset has YAML
frontmatter "mirroring its manifest entry", and the contract test requires
"same ID, version, hash" between frontmatter and manifest
(`rm-02-research-methods-pack-plan.md:14-18, 119-143`).

**Direct evidence.** The asset file's recorded hash is therefore inside the
bytes whose hash it claims to equal. No non-hashed indirection or excluded
canonical subset is defined.

**Failure scenario.** Writing hash value `h` into frontmatter changes the file
bytes and produces `SHA256(file_with_h) != h`; replacing it with the new digest
changes the bytes again. The Worker cannot produce five files satisfying the
test except by finding an infeasible SHA-256 fixed point.

**Impact.** RM-02 cannot reach green, so G-RM-4 and the RM-03 asset dependency
cannot exist. Deterministic pack recovery is impossible under the specified
identity graph.

**Required disposition:** **fix now; stop RM-02 dispatch.**

**Exact required text change.** Replace "same ID, version, hash" with:

> Asset frontmatter repeats `asset_id`, `name`, `version`, lineage and
> applicability metadata, but never its own content hash. The external
> manifest alone records the Git-blob identity for tracked Markdown assets
> (or a declared LF-canonical byte hash). The binding test compares all
> duplicated non-hash fields and independently recomputes the external
> identity.

Add a negative fixture that inserts a self-hash field and rejects the manifest
shape.

**Affected decisions/work packages:** P-044 item 1, G-RM-4, RM-02 Tasks 1-3,
RM-03 dependency.

### C-3 — RM-03's event family has no authoritative producer or replay path

**Claim.** RM-03 creates `ars://methods/event/MethodBriefRecorded` and
`ars://methods/event/MethodResultImported`, emits them through the existing
command/ledger seams, and requires replay to reproduce the projection
(`rm-03-brief-export-import-plan.md:14-25, 34-40, 45-69, 127-133, 162-194`).

**Direct evidence.**

- `CommandService._build_event` recognizes a closed set of command types,
  rejects all others, and assigns `ars://core/event/...`
  (`research_system/command/service.py:831-893`). RM-03 neither defines command
  schemas/types nor modifies this file.
- For non-T2 events, `EventLedger.append` derives a core event schema for
  validation; a supplied methods `$id` is not validated against the methods
  schema (`research_system/store/ledger.py:275-350`).
- Replay accepts only `ars://core/event/...` or
  `ars://wp6-2/t2/event/...`; any methods event raises `unknown event schema`
  (`research_system/projection/replay.py:360-395`).
- W2 requires authority/idempotency/state-transition validation before a
  write and pure versioned reducers during replay
  (`design/02-task-event-and-artifact-schema.md:255-269, 874-895`).

**Failure scenario.** Using `CommandService` rejects the new command. Calling
`ledger.append` directly can create a synthetic `LedgerInternalAppend` event
without the intended command authority, does not validate the methods schema,
and later makes authoritative replay fail.

**Impact.** This crosses both authority and recovery boundaries: an import can
either not land, land outside its declared command authority, or make
deterministic recovery impossible.

**Required disposition:** **architectural amendment; stop RM-03 dispatch.**

**Exact required interface change.** Choose and review one event-family owner.
The amendment must define:

1. registered prefixed-UUIDv7 kinds for brief/import records;
2. exact `RecordMethodBrief` and `ImportMethodResult` command schemas;
3. authority, expected-version, idempotency, write-set and object-write rules;
4. an event-family dispatch registry used by both ledger validation and replay;
5. pure reducers for both event types;
6. unknown-major and unsupported-event failure behavior; and
7. positive plus unknown-family, direct-append-bypass, replay and atomic-
   rejection negative controls.

The implementation file map must include the actual command, ID-registry,
ledger/replay and reducer owners. If core routing remains frozen, use an
already accepted generic artefact event rather than inventing an unrouteable
family.

**Affected decisions/work packages:** P-044 item 2, O-RM-16, RM-03 Tasks 1-6,
RM-04, W2 replay/authority.

### C-4 — RM-04 executes untrusted code without a security boundary

**Claim.** RM-04 runs model-proposed Python with the project interpreter,
declared cwd, wall time and `--approved-by`, while explicitly disclaiming
sandbox security (`rm-04-verification-execution-and-manuscript-review-plan.md:16-30,
72-92`). It claims network-needing recipes fail with a typed error
(`rm-04...md:35-42`).

**Direct evidence.**

- `approved_for_execution_by` is just a request field and `--approved-by` a
  caller-supplied CLI string (`rm-04...md:74-85`); no independently resolved
  actor, grant, decision, signature or exact-script approval is required.
- RM-03's guard scans package imports, not arbitrary recipe bodies. It cannot
  stop `socket`, `importlib`, `subprocess`, PowerShell, a config URL, or an
  indirect dependency.
- W8 requires typed roots, network/external-write/sensitivity constraints,
  grants, leases, process/child identity and stop evidence
  (`design/08-resource-checkpoint-and-operations.md:126-157, 212-224,
  226-269, 300-317`). RM-04 downgrades this to "W8 spirit"
  (`rm-04...md:99-105`).
- The reviewed repository has a present, gitignored `.env`; the vault is also
  gitignored. W3 expressly excludes credentials, `.env` contents and raw
  restricted data (`design/03-context-memory-and-retrieval.md:465-478`).

**Failure scenario.** A returned recipe reads `.env`, walks the vault or other
gitignored data, sends it over a socket, mutates the repository, or launches a
child that survives the parent's timeout. `cwd` and a wall-time timeout prevent
none of those actions. Any caller can type Stephen's name into `--approved-by`.

**Impact.** Credential/restricted-data leakage, repository/evidence corruption,
and false approval provenance are reachable by design. An honest disclaimer
does not make the execution acceptable.

**Required disposition:** **reject and redesign before implementation.**

**Exact required interface change.** Verification execution must occur in an
OS-enforced isolation profile with:

- a disposable interpreter/environment, sanitized environment variables and
  no inherited credentials;
- deny-by-default network egress;
- read-only exact input mounts and one disposable writable scratch mount,
  with no repository, `.env`, vault or home visibility;
- W8 `ResourceGrant`, `ExecutionLease`, `ProcessIdentity`, child-process and
  stop-confirmation records;
- an attributed approval command that resolves canonical actor/authority and
  binds the exact request/script hash; and
- negative controls that attempt absolute-path reads, `.env` access, network
  egress, repository writes, child escape, forged approver identity and
  timeout survival.

Until that substrate exists, RM-04 may define schemas and a non-executing
verification-request record only.

**Affected decisions/work packages:** P-042 credential boundary, P-044 item 3,
RM-04 Tasks 1-4, W8, G-RM-5.

## Major findings

### M-1 — RM-00's owner-gate table is incomplete and two gates fail open

**Claim/evidence.** RM-00 says every child owner precondition is hoisted and
the runner uses only its table (`rm-00...md:52-56`). R1-3b is nevertheless an
explicit "Owner decision point" in RM-01 (`rm-01...md:97-103, 204-213`) and has
no G-RM row. G-RM-4 says accepted assets are exportable by default, while
RM-03 permits `--allow-candidate` (`rm-00...md:57-64`;
`rm-03...md:93-100`). G-RM-3 requires only accepted review disposition plus
zero Critical, not closure of blocking Major conditions.

**Failure scenario/impact.** Dispatch proceeds from the master table while the
receipt-v2 ownership decision remains hidden; an unaccepted method asset is
exported by a local flag; or a plan with unresolved required Major changes is
treated as dispatchable.

**Required disposition:** amend now. Add a master gate for R1-3b; remove
`--allow-candidate` from governing export or make each use an attributed owner
gate; define G-RM-3 as `accept`, or `accept_with_required_changes` only after
every dispatch-blocking condition has independent closure evidence. A `reject`
verdict always blocks.

**Affected:** G-RM-3, G-RM-4, RM-00, RM-01, RM-03.

### M-2 — A Gate-6-critical WP6.1 repair is mislabeled as independent-lane work

**Claim/evidence.** P-044 and RM-00 say RM is "never" on the Gate 6 critical
path, but RM-00 then excepts RM-01 Task A as a WP6.1 main-path repair and RM-01
records acceptance against WP6.1 (`03-decisions...md:813-825`;
`rm-00...md:11-15`; `rm-01...md:27-29`). P-042 defines WP6.1 as part of the
active Gate 6 path (`03-decisions...md:746-752`).

**Failure scenario/impact.** Status reporting can say the independent RM lane
is optional while the only plan that closes a WP6.1 currency defect sits
inside it. Acceptance authority and scheduling dependencies become
document-name dependent.

**Required disposition:** split the P-043 repair into a WP6.1 main-path plan
and make RM-03 depend on the accepted append-path capability, not on "RM-01".
Alternatively redefine the RM lane as RM-02..RM-04 and retain RM-01 only as a
cross-lane prerequisite record.

**Affected:** P-043, P-044, RM-00 dependency graph, RM-01, Gate 6.

### M-3 — RM-02's lifecycle and metadata controls are declarations without state authority

**Claim/evidence.** RM-02 promises W3 lifecycle enforcement, same-version hash
edit rejection and owner acceptance through a manifest revision
(`rm-02...md:58-78, 145-160`). A loader looking only at the current manifest
has no prior version/hash/state against which to detect an in-place edit.
The proposed metadata also omits W3's required permissions and applicable
observer overlays (`design/03-context-memory-and-retrieval.md:410-421`).
Raw checkout-byte hashing of tracked Markdown is not Windows/EOL-stable.

**Failure scenario/impact.** A reviewed asset's bytes and hash are replaced
under the same version, the current manifest remains internally consistent,
and all listed tests pass. An agent can also write `owner_acceptance` directly
into YAML; the field records an assertion, not the accepting command/decision.

**Required disposition:** use immutable asset revisions with Git-blob identity
or explicit LF canonicalization; persist prior identities in an independently
authoritative registry/event stream; make lifecycle transitions command-
authorized; resolve owner acceptance by exact external decision reference;
include W3 permissions and overlay identity; test every forbidden transition,
history removal, stale revision, EOL variant and forged owner reference.

**Affected:** O-RM-7/O-RM-8, G-RM-4, RM-02 Tasks 1-3.

### M-4 — The P-042 guard is open-world and contradicts the suite's naming rule

**Claim/evidence.** RM-03 calls a maintained SDK/HTTP denylist the mechanical
P-042 guard (`rm-03...md:179-191`). RM-00 says no lane file may name a model
provider outside evidence lineage (`rm-00...md:16-19`), yet the proposed test
must embed provider module names. The guard does not inspect `importlib`,
subprocesses, sockets, config-driven endpoints, plugins/MCP/tool seams or
dependencies that call out.

**Failure scenario/impact.** `importlib.import_module(config["backend"])`, a
generic HTTP client outside `research_system/methods`, or a subprocess wrapper
crosses P-042 while the test remains green.

**Required disposition:** replace the denylist with a capability boundary:
an AST/import allowlist for the methods package, no transport/tool interface in
its dependency graph, process-level egress denial for execution, and negative
tests for indirect import, subprocess, generic URL, socket, MCP/tool and
transitive dependency paths. Security test data may use neutral synthetic
modules; provider-specific evidence stays in a separate lineage fixture.

**Affected:** P-042, O-RM-1/O-RM-14, RM-03 Task 5, RM-04.

### M-5 — Closed import enums do not provide an end-to-end claim firewall

**Claim/evidence.** RM-03 calls escalation "structurally unrepresentable" based
on four local status enums (`rm-03...md:14-23, 102-118, 137-147`). W5 makes
promotion depend on the complete source/result/evidence set and a new
attributed decision, not the spelling of an upstream artefact's status
(`design/05-research-assurance-and-independent-review.md:502-551`).
`TheoremCitation.verification = verified_by_operator` is itself imported from
the returned document; no separate operator act proves it.

**Failure scenario/impact.** A consumer cites an `imported` finding or
`candidate` counterexample directly as accepted evidence, creates a result
decision from it, reclassifies it in a projection, or accepts the model's
`verified_by_operator` assertion. Every import schema still validates.

**Required disposition:** narrow the claim to "schema-local escalation is
unrepresentable" and add a consumer firewall: imported RM records are
ineligible for result/claim evidence until a separately authorized,
exact-subject `ArtefactUseAccepted`/validation/result decision admits them.
Operator verification must be a separate attributed record bound to the exact
citation. Test direct reference, projection reclassification, supersession,
loose-status consumers, forged operator verification and absent P-005.

**Affected:** O-RM-4/O-RM-5, P-044, RM-03 Tasks 3-6, RM-04.

### M-6 — The “bounded W3 packet” is a materially narrowed substitute

**Claim/evidence.** The proposal says export compiles a W3-bounded packet, and
RM-03's manifest is the implementation (`research-methods-integration-plan...md:97-137`;
`rm-03...md:71-100`). Accepted W3 requires authority warning, scope,
dependencies/prohibitions, governing designs/decisions/contracts, assurance,
roots/provenance, unresolved conflicts/omissions, freshness/currency,
sensitivity/redaction, retention, supersession and delivery evidence
(`design/03-context-memory-and-retrieval.md:238-298, 326-385, 465-478`).
Most are absent.

**Failure scenario/impact.** A brief is schema-valid while omitting a governing
amendment, carrying stale subjects, excluding an assurance requirement or
leaking an unsafe source. `subjects[].sha256` alone does not establish W3
mandatory closure.

**Required disposition:** either compile an accepted W3 packet and have the
brief manifest bind its `context_id`, revision and exact packet/manifest hashes,
or explicitly define the brief as a non-governing presentation derived from
such a packet. Do not create a second weakened W3 manifest. Add stale,
omitted-governing-source, conflict, unsafe-source, superseded-packet and
delivery-binding controls.

**Affected:** P-042 bounded briefs, P-044, O-RM-3/O-RM-6, RM-03 Tasks 1-2.

### M-7 — RM-03 reuses a semantically foreign, provider-specific allowlist

**Claim/evidence.** `application_family` is to read the WP6.3 assurance-pack
allowlist by path/hash (`rm-03...md:120-133, 141-147`). That contract's
`operator_model` governs independent review agents and currently lists
`codex_standalone`/`claude_standalone`, not external research-application
sessions (`.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml:247-255`).

**Failure scenario/impact.** A valid operator-selected external research
session is rejected because it is not an assurance-pack reviewer family, or
RM silently inherits future WP6.3 review-policy changes as RM session policy.
The accepted exact-byte pack becomes a mutable semantic dependency it never
owned for this purpose.

**Required disposition:** define a P-042/P-044-owned session-record contract.
Prefer recording the operator-selected family as attributed evidence rather
than treating a closed reviewer allowlist as eligibility authority. If an
allowlist is required, it needs its own owner, revision/hash, lifecycle and
provider-neutral rationale.

**Affected:** P-042 operator choice, P-044 provider neutrality, R3-1/R3-9,
RM-03.

### M-8 — Cross-plan identities and `verification_context` are undefined

**Claim/evidence.** RM-03 requires a "new ULID per
`research_system.ids` conventions" (`rm-03...md:77-92`), but W2 and
`research_system.ids` use registered prefixes plus UUIDv7
(`design/02-task-event-and-artifact-schema.md:129-167`;
`research_system/ids.py:14-112`). No `brief`, method-result or verification-
request kind exists in `.research-system/config/id-kind-registry.yaml`, and
the file maps do not amend it. RM-03 reserves `verification_context` only as
nullable, while RM-04 later embeds a complete result and asserts no schema
version bump (`rm-03...md:77-92`; `rm-04...md:83-88`).

**Failure scenario/impact.** Implementers invent an unregistered ULID or reuse
an unrelated artefact kind inconsistently; RM-04 either violates
`additionalProperties: false` or leaves `verification_context` unconstrained.
Cross-version readers cannot tell what was embedded.

**Required disposition:** define canonical prefixed-UUIDv7 kinds in the owning
ID catalogue or explicitly use `art_` with typed artefact manifests. Specify
`verification_context` now as a versioned reference object
`{schema_id, schema_version, verification_result_id, content_hash}`; embed no
unversioned open object. Add RM-03/RM-04 shared-schema equality tests.

**Affected:** W2 identity, RM-03 Tasks 1-3, RM-04 Tasks 1-3.

### M-9 — RM-01's baseline is stale and its stated “green” exit is inconsistent

**Claim/evidence.** RM-01 treats handoff 28's 1,515-test tree as the comparator
and predicts 156 cases move together (`rm-01...md:94-103, 153-178`). At the
review subject/current tree, read-only collection produced **1,561 tests**.
Between `97f447f` and the review subject, three new test modules and material
WP6.3 tests landed. The two old non-Defect-3 cases still exist:
`test_every_core_schema_declares_closed_object_contract` still omits
`receipt-v2`, and the signature guard still expects `Receipt` while the
implementation returns `Receipt | T2Receipt`
(`tests/research_system/unit/test_schema_registry.py:175-199`;
`tests/research_system/unit/test_release_publication.py:949-961`;
`research_system/command/service.py:172-177`).

**Failure scenario/impact.** A post-fix run is compared to a different test
universe; new failures cannot be distinguished from the P-043 delta. RM-01
also promises a green suite while deliberately allowing R1-3b to remain red.

**Required disposition:** collect and record the exact dispatch-head node set
before production mutation, preserve the 156 original node IDs as a named
cohort, and compare both cohort and complete current universe. Resolve R1-3b
before claiming green. The R1-3a pre-step ordering is correct and should stay.

**Affected:** R1-3/R1-3a/R1-3b, Task B, RM-01 success criteria.

### M-10 — The de-identification sidecar cannot support re-identification

**Claim/evidence.** RM-02 requires a provenance sidecar and RM-03 records only
`{stripped: [...], mapping_sha256}`, saying the mapping remains ARS-side
(`rm-02...md:65-68, 130-133`; `rm-03...md:81-92`). No object ID, revision,
locator, access class, schema or lifecycle connects the digest to retrievable
mapping bytes, and no round-trip test is listed.

**Failure scenario/impact.** Import proves only that some unknown mapping once
had a digest. ARS cannot locate or authorize the mapping needed to re-identify
the returned result, and two same-shaped briefs can be joined to the wrong
mapping.

**Required disposition:** make the ARS-only sidecar an immutable object with
ID/revision/hash, subject set, transform version, sensitivity/retention class
and authorized consumers. The operator-facing manifest carries only the
opaque ID/hash. Add exact round-trip, wrong-sidecar, missing-sidecar, stale-
revision and unauthorized-access tests.

**Affected:** R2-5, R3-1/R3-5, RM-02 asset 3, RM-03 export/import.

### M-11 — Two method requirements are not supported by their cited paper

**Claim/evidence.** RM-02 attributes "minimal-instance-first" to paper
§2.3/§9.2 and theorem retrieval to §2.5 (`rm-02...md:64-68`). The pinned paper
supports counterexample construction and neutral "prove or refute", but does
not state minimal-instance-first (`Gemini For Research.md:205-220, 4080-4090`).
The theorem-retrieval/external-verification material is in §§2.2-2.3
(`Gemini For Research.md:197-220`); the pinned Markdown has no §2.5 heading.

**Failure scenario/impact.** An asset presents a project-added heuristic as a
source-derived protocol, and its lineage lookup points to a nonexistent
section. This violates the prompt's quarantine rule even though the additions
may be sensible.

**Required disposition:** cite theorem retrieval to §§2.2-2.3. Either remove
minimal-instance-first or identify it explicitly as an ARS-added requirement
with an accepted repository source/owner decision. Keep the three-stage
self-critique, neutral prove/refute, human verification, traceback feedback,
context de-identification and decomposition requirements; those are directly
supported.

**Affected:** R2-4/R2-6, RM-02 assets 2 and 4, provenance trace.

### M-12 — RM-03/RM-04 under-classify Paper Claim governance

**Claim/evidence.** Every plan declares Output/Provenance only
(`rm-00...md:108-116`; RM-03/RM-04 assurance sections). RM-03 defines the
claim-promotion firewall and imports review findings/counterexamples;
RM-04 feeds manuscript review and executes candidate-specific checks. W3 and
W2 both classify comparable carrying/governance work as Output/Provenance
**and Paper Claim governance**
(`design/03-context-memory-and-retrieval.md:607-611`;
`design/02-task-event-and-artifact-schema.md:1116-1126`).

**Failure scenario/impact.** A review treats the plans as provenance-only and
omits the claim-consumer, wording-strength, independent review and human-
authority controls needed precisely where imported findings approach a paper.

**Required disposition:** classify RM-03 and RM-04 as
Output/Provenance primary plus Paper Claim governance. Verification results
inherit the candidate's scientific-lane metadata but certify only execution
unless an independent property method is separately accepted. RM-02 remains
procedural-memory Output/Provenance unless an asset defines a scientific
method rather than a review procedure.

**Affected:** RM-00 §5.6, RM-03/RM-04 assurance requirements, W5 §14.6/§19.

## Minor and editorial findings

### m-1 — Accepted owner decisions are still labeled pending

**Claim/evidence.** RM-02, RM-03 and RM-04 say `"P-044 (pending)"`
(`rm-02...md:22`; `rm-03...md:26`; `rm-04...md:32`), while the exact register
records it accepted (`03-decisions...md:806-844`).

**Failure scenario/impact.** A Worker treats a closed owner decision as a
dispatch blocker or seeks to reopen it. This is local status drift, not a
change in authority.

**Required disposition and exact change.** Replace `pending` with
`accepted 2026-07-28; G-RM-3 and plan-specific dependencies remain open`. Do
not change the historical proposal.

**Affected:** RM-02/RM-03/RM-04 status headers only.

### m-2 — RM-02 carries a discharged registry warning

**Claim/evidence.** RM-02 says O-RM-10 `"may still be active"` in a Partial
criterion (`rm-02...md:82-85`), while RM-00 records Defects 1-2 discharged
(`rm-00...md:82-85`).

**Failure scenario/impact.** A Worker reports the wrong blocker even though
stopping on an unplanned registry expansion remains conservative. The
operational direction is safe but its provenance is stale.

**Required disposition and exact change.** Replace the stale reason with:
`schema-registry expansion is outside RM-02's accepted file map and requires a
reviewed cross-family plan`.

**Affected:** RM-02 Partial criteria and R2 close-out wording.

### m-3 — “Full gates” is not an executable close-out command set

**Claim/evidence.** RM-03/RM-04 close with `"Full quality gates"`/`"Full
gates"` without exact commands or a named gate manifest
(`rm-03...md:197-202`; `rm-04...md:145-150`).

**Failure scenario/impact.** Two Workers run different test surfaces and both
report close-out complete. This is an operational ambiguity; it does not by
itself change architecture.

**Required disposition and exact change.** Name the targeted tests, smoke
gate, Ruff scope and any mandated final suite, with the concrete trigger for
broader validation.

**Affected:** RM-03 and RM-04 close-out verification only.

## Informational clean results

- The seven Git subject blobs, register blob and three vault hashes match.
- The source paper's three-stage adversarial self-critique, neutral
  prove-or-refute warning, human theorem verification, traceback feedback,
  context de-identification and decomposition claims are faithfully
  recognized, subject to M-11's citation/added-heuristic correction.
- RM-01 and RM-02 planned production file sets are disjoint. Their declared
  parallelism is sound at the file level.
- RM-00 §6 gives every listed deferral an owner and next gate.
- RM-04's manuscript lane proposes no direct claim write. The defect is its
  missing Paper Claim governance classification and consumer controls, not a
  hidden claim-mutation implementation.
- The accepted WP6.3 do-not-touch paths remain outside every production file
  map.

## Attack-surface disposition

| # | Surface | Outcome |
|---|---|---|
| 1 | P-042 boundary and real guard | **Findings:** C-4, M-4, M-7 |
| 2 | Claim-promotion firewall | **Finding:** M-5 |
| 3 | Owner-touchpoint hoisting | **Finding:** M-1 |
| 4 | Independent forward-obligation scan | **Findings:** C-1 (back-compat omission), M-3, M-6, M-9, M-10 |
| 5 | Lane-independence coherence | **Finding:** M-2 |
| 6 | RM-01 seam/P-043 implementability | **Finding:** C-1; direct source confirms `CommandService.submit -> ledger.append`, but the exact-byte source is absent |
| 7 | Baseline currency/delta | **Finding:** M-9; R1-3a ordering itself is clean |
| 8 | Method-asset fidelity/neutrality | **Findings:** C-2, M-4, M-11; remaining cited method primitives clean |
| 9 | RM-04 execution honesty/control | **Finding:** C-4; disclaimer is honest but insufficient |
| 10 | Binding tests/negative controls | **Findings:** C-1 through C-4, M-3 through M-5, M-8 through M-10 |
| 11 | Cross-plan interfaces | **Findings:** C-3, M-7, M-8, M-10; RM-01/RM-02 file parallelism clean |
| 12 | Assurance-lane classification | **Finding:** M-12 |

## Provenance trace

The obligation rows are used as the suite's substantive-requirement inventory.
"Report" appears only where the report is the historical lead; independently
verified support is named separately. No requirement is accepted solely
because a report recommended it.

| Requirement | Support traced | Disposition |
|---|---|---|
| R1-1 producer emits schema triple | Accepted P-043 + repository schema/runtime state | Supported direction; C-1 blocks interface |
| R1-2 cover every producer | Handoff 26 + repository call sites | Supported; must include direct/T2/internal paths without inventing false command provenance |
| R1-3 156-case cohort | Measured handoff 28 | Supported only as historical cohort; M-9 requires current universe |
| R1-3a signature guard first | Handoff 28 + current source | Supported and correctly ordered |
| R1-3b receipt-v2 decision | Handoff 28 + current source + observer record | Supported; not hoisted (M-1) |
| R1-4 coverage/Ruff accounting | Report 1 lead, independently verified in `pyproject.toml:106,113` | Quarantine held; repository-supported |
| R1-5 append smoke/liveness | Repository observer record 137 + reproduced schema/runtime gap | Supported |
| R1-6 Defects 1-2 discharged | Repository history/handoff 28 | Supported |
| R1-7 vault close-out | Repository working rules | Supported, operational |
| R2-1 W3 procedural metadata | Accepted W3 §13.2 | Partially rendered; permissions/overlays missing (M-3) |
| R2-2 memory lifecycle | Accepted W3 §13.1 | Direction supported; enforcement missing (M-3) |
| R2-3 three-stage review | Source paper §§2.1/3.2 | Supported |
| R2-4 neutral counterexample framing | Source paper §9.2 | Supported; minimal-instance-first unsourced (M-11) |
| R2-5 de-identification + sidecar | Paper §2.7 for de-identification; W3 for provenance | Supported combination; interface incomplete (M-10) |
| R2-6 theorem verification | Source paper §§2.2-2.3 | Supported; cited section wrong (M-11) |
| R2-7 decomposition | Source paper §2.1 | Supported |
| R2-8 STEM-generic/provider-neutral | Accepted P-044 | Supported |
| R2-9 append-only manifest | Accepted W2/W3 | Supported direction; current mechanism not append-only (M-3) |
| R3-1 exact brief/session evidence | Accepted P-042 + W3 | Supported; narrowed packet and wrong session authority (M-6/M-7) |
| R3-2 no provider invocation | Accepted P-042 | Supported; proposed guard insufficient (M-4) |
| R3-3 below acceptance/promotion | Accepted W5 §19 | Supported; schema-only firewall insufficient (M-5) |
| R3-4 no transcripts/reasoning | Accepted W3 §15 | Supported; closed schema protects only named import object |
| R3-5 subject hash | Accepted W3 §9 | Supported but insufficient for W3 closure (M-6) |
| R3-6 theorem verification enum | Source paper + RM-02 | Supported vocabulary; operator act self-attested (M-5) |
| R3-7 append/replay | Accepted W2 | Supported requirement; architecture fails it (C-3) |
| R3-8 immutable rollback | Report 2 lead + accepted W2/W5 supersession | Direction independently supported; disable mechanism not specified |
| R3-9 reused WP6.3 allowlist | **Plan-local choice; no accepted support for this semantic reuse** | Major M-7 |
| R4-1 execute/traceback/feed back | Source paper §2.6 | Supported pattern; execution controls fail (C-4) |
| R4-2 execution success not acceptance | Accepted W5 §17 | Supported |
| R4-3 no network/provider | Accepted P-042 | Supported requirement; unenforced for recipes (C-4/M-4) |
| R4-4 wall time/root/approver | Plan says "W8 spirit"; accepted W8 requires much more | Under-specified and unsafe (C-4) |
| R4-5 append-only result binding | Accepted W2 | Supported requirement; depends on broken RM event path (C-3) |
| R4-6 owner pilot subjects | Accepted G-RM-5/P-044 boundary | Supported |
| R4-7 vault record | Repository working rules | Supported, operational |
| R4-8 no security theater | General repository security principle | Honest description, but not authority to run unsafe code (C-4) |

**Report-only quarantine result.** R1-4 survives because its report-1 lead was
verified directly. Report 2 accurately pointed to operator-mediated methods,
typed import and immutable rollback, but its claim that the fast path needs
only "new schemas, prompt-pack assets, CLI commands, and import/eval logic"
is disproved by the current command, ledger, replay and ID-registry seams
(C-3). The suite adopted that unsupported implementation-simplicity claim.

## Decision and gate disposition

| Decision/gate | Disposition | Faithful rendering? |
|---|---|---|
| P-042 | **keep** | **No.** Operator mediation is preserved in prose, but M-4's open-world guard, M-7's foreign allowlist and C-4's recipe execution permit boundary violations. |
| P-043 | **keep; amend implementation plan** | **No.** Producer-emits direction is faithful; byte-exact implementability and historical-event policy are missing (C-1). |
| P-044 | **keep; amend plan suite** | **No.** Provider-neutral independent lane is rendered, but M-2, C-3, C-4 and M-12 break its boundary/interface. |
| G-RM-1 | **closed as owner decision; execution still blocked** | P-043 exists, but C-1 prevents its planned execution. |
| G-RM-2 | **closed** | P-044 exists and authorizes bounded work only after plan review. |
| G-RM-3 | **not satisfied** | This review rejects all four dispatch plans; gate wording also needs M-1's exact verdict/condition closure. |
| G-RM-4 | **open** | Correct owner gate, but `--allow-candidate` bypasses it (M-1). |
| G-RM-5 | **open** | Correctly hoisted for pilots; cannot clear C-4 by subject choice. |
| G-RM-6 | **open** | Correctly hoisted; append smoke design still needs C-1/M-9 corrections. |
| Missing receipt-v2 gate | **add** | R1-3b is owner-reserved in child prose but absent from master (M-1). |

## Invariant → enforcement → test consistency matrix

| Invariant | Proposed enforcement | Test/control | Disposition |
|---|---|---|---|
| P-043 exact schema bytes | Registry-derived triple | Independent file hash | **Broken:** registry does not retain bytes/path (C-1) |
| No caller override | Producer overwrites/rejects | Caller-supplied triple | Partial; add valid-but-wrong triple substitution |
| Every producer covered | Single derivation + sweep | Event-family smoke | Partial; direct/T2/internal producers unresolved |
| Asset identity immutable | Manifest hash | Tamper test | **Impossible self-edge** (C-2) |
| Asset lifecycle authorized | Manifest state/owner field | State/schema negatives | **Inert against history/forged owner** (M-3) |
| Only accepted assets govern export | Default filter | Candidate rejection | **Bypass:** `--allow-candidate` (M-1) |
| No provider invocation | Import/HTTP denylist | Planted denylisted import | **Open-world** (M-4) |
| Import below promotion | Closed status enums | `accepted/promoted` rejection | **Schema-local only** (M-5) |
| No transcript/reasoning fields | Closed schemas | extra-field rejection | Good for typed import object; does not sanitize subject/brief content |
| Exact brief response | manifest hash/event join | absent/bad hash | Depends on unsupported event family (C-3) |
| Session family authorized | WP6.3 review allowlist | outside-family rejection | Wrong authority/semantic object (M-7) |
| Append-only/replayable import | methods events + replay | round-trip/replay | **Unsupported family** (C-3) |
| De-identification reversible | mapping digest | none specified | No locator/round-trip (M-10) |
| Script approval | `approved_by` string | none beyond presence | Self-attestation (C-4) |
| Recipe bounded/isolated | cwd + timeout | sleep/tamper tests | No security boundary, network/root/child controls absent (C-4) |
| Verification is not acceptance | result naming/no lifecycle code | review question | Needs consumer firewall and Paper Claim lane (M-5/M-12) |
| Shared RM-03/RM-04 context | nullable reserved field | round-trip | Undefined versioned interface (M-8) |
| Gate liveness | one negative per gate | listed mutations | Several mutations test schema shape, not the claimed end-to-end property |

## Coverage and fixture gaps

Required additions before a revised plan can pass G-RM-3:

1. Registry exact-byte identity, TOCTOU substitution, valid-but-wrong identity
   triple and historical-event replay fixtures.
2. Asset hash-graph self-edge rejection, EOL/checkout identity, prior-version
   removal, same-version replacement, forged acceptance and every forbidden
   lifecycle transition.
3. Command authority, ID-catalogue, direct-ledger bypass, unsupported family,
   unknown major, reducer absence, object/event atomicity and genesis/incremental
   replay fixtures for RM events.
4. Indirect provider import, dynamic import, subprocess, generic URL, socket,
   MCP/tool and transitive dependency guard controls.
5. Direct imported-evidence-to-result, projection reclassification,
   supersession, loose status parsing, fabricated operator verification and
   absent P-005 controls.
6. Full W3 closure: omitted governing source, stale subject, conflict,
   unsafe/restricted source, superseded packet and delivery mismatch.
7. De-identification sidecar wrong join/missing/stale/unauthorized controls.
8. Isolation escape controls: `.env`/home/vault read, repository write,
   network egress, environment leak, child survival, forged approver and
   timeout cleanup.
9. A shared RM-03/RM-04 schema-contract test that equality-checks IDs, event
   names, `$id`s and `verification_context`.
10. A current dispatch-head collection manifest plus the preserved 156-node
    historical cohort for RM-01.

## Practicality and proportionality

| Plan | Planned overhead | Assessment |
|---|---|---|
| RM-01 | Focused unit/adapter slice, <60 s smoke, one ~hour full suite | Proportionate after C-1/M-9. The full suite should run once at final exact head; current collection is 1,561 tests. |
| RM-02 | One loader/schema module and focused contract tests | Small and worthwhile, but immutable lifecycle history is not optional. Use Git-blob identity and one external acceptance record rather than inventing a second ledger if W2 generic artefacts suffice. |
| RM-03 | Seven schemas, two modules, CLI, integration/replay | Underestimated. The present code needs an accepted command/event/ID/reducer extension. Reusing a generic accepted artefact event may be the smallest safe control. |
| RM-04 | Runner, three schemas, CLI, pilots | Disproportionate and unsafe without an isolation substrate. Defer execution; retain non-executing request/result schemas only if they can use the corrected RM-03/W2 path. |

The smallest safe revision sequence is therefore: WP6.1 exact-byte seam;
methods-pack identity/lifecycle; generic authoritative artefact import; only
then isolated execution. Do not build a bespoke event family if the accepted
generic artefact lifecycle already satisfies P-044.

## Revision plan

### Immediate corrections

1. Correct stale P-044 status lines and paper section citations.
2. Remove the asset self-hash and `--allow-candidate`.
3. Replace ULID wording with the accepted ID-catalogue decision.
4. Update the RM-01 baseline to a dispatch-head collection manifest and
   explicitly preserve the 156-case cohort.
5. Add R1-3b to the master gate table and tighten G-RM-3 semantics.
6. Classify RM-03/RM-04 as touching Paper Claim governance.

### Owner decisions / accepted amendments required

1. Approve a WP6.1 exact-schema-byte registry interface and historical-event
   policy (C-1).
2. Choose whether RM records use an accepted generic W2 artefact event or a
   new reviewed command/event/reducer family (C-3).
3. Approve an RM-owned external-session family contract, or decide that
   attributed free recording is sufficient (M-7).
4. Resolve the receipt-v2 closed-set gate (R1-3b).
5. Decide whether arbitrary verification execution is deferred or funded
   behind a real isolation/W8 substrate (C-4).

### Later-work dependencies

1. Implement and independently review the exact-byte registry seam.
2. Implement RM-02 with immutable external identity and lifecycle controls.
3. Implement the chosen W2 artefact/event path and full W3 packet binding.
4. Re-review RM-03 against the exact accepted event/ID interfaces.
5. Design and threat-model isolation before re-reviewing any executing RM-04.

## Per-document verdicts and exact clearance conditions

### RM-00 — `not_ready`

Must clear M-1/M-2, incorporate every Critical/Major child dependency into its
obligation/gate register, declare Paper Claim governance, and replace
"zero unresolved Critical" with exact per-plan verdict/condition closure. The
revised master must be reviewed before it governs dispatch.

### RM-01 — `reject`

Clear C-1; record the historical-event decision; make every producer path's
command-schema identity truthful; establish the dispatch-head collection
manifest and preserved 156-node cohort; resolve R1-3b; then rerun focused
public-seam/negative controls and one final exact-head suite. Acceptance remains
WP6.1 authority, not RM authority.

### RM-02 — `reject`

Clear C-2, M-3 and M-11; use checkout-stable external identity; define
authoritative lifecycle history and exact owner-acceptance resolution; include
all W3 §13.2 metadata; and prove all sibling assets/transitions, not one
example. G-RM-4 remains owner-only after implementation review.

### RM-03 — `reject`

Clear C-3 and M-4 through M-8 plus M-10/M-12; bind export to a complete W3
packet; use an RM-owned session contract; establish an end-to-end claim
consumer firewall; define de-identification sidecar recovery; and demonstrate
authoritative append plus full replay on the exact accepted event/ID interface.

### RM-04 — `reject`

Clear C-4 and inherit the accepted RM-03 interface. No execution task may be
dispatched until OS-enforced isolation, W8 records, exact-script approval and
escape negative controls are reviewed and accepted. Any schema-only precursor
must explicitly exclude execution and pilots.

## Residual risks after required revision

- Static controls can reduce accidental provider coupling but cannot replace
  process-level network/root restrictions for executed code.
- Operator-mediated sessions remain a human provenance boundary: recording an
  application/session does not prove the returned content's truth.
- Imported review/counterexample material can still influence humans outside
  ARS; the mechanical firewall governs canonical use, not cognition.
- Git-blob identity is stable for tracked text, but operator-facing rendered
  bytes still need their own explicit canonicalization and content hash.
- A generic artefact event may minimize code, but its consumer predicates must
  remain strict enough that "generic" does not become an authority bypass.

## Change log and verification evidence

**Files edited:** this review report only. No reviewed plan, proposal, design,
source, schema, contract, test or runtime file was edited.

**Read-only checks performed:**

- fetched `origin/main` and resolved subject commit;
- recomputed eight Git blobs and three vault SHA-256 hashes;
- confirmed pinned working copies equal the subject blobs;
- inspected P-042/P-043/P-044, W2/W3/W5/W8, handoffs 25/26/28, README,
  CONVENTIONS, source paper and both reports;
- verified `SchemaRegistry`, `CommandService`, `EventLedger`, replay,
  `ObjectStore`, ID registry and current producer call sites directly;
- compared `97f447f..6e7d0e0` and confirmed relevant post-baseline test changes;
- collected `tests/research_system` read-only with an existing interpreter:
  `1561 tests collected in 22.63s`;
- disabled bytecode, cache and coverage writes for collection; repository
  status after collection was unchanged apart from the user's pre-existing
  `.claude/CLAUDE.md`, `.claude/settings.json`, and
  `.repowise-workspace.yaml` modifications.

No tests, research computation, provider session, dispatch, migration,
acceptance, claim, CodeRabbit action, commit, staging or merge was performed.
