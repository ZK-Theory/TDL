# RM Lane Plan-Suite Adversarial Re-Review — 2026-07-30

## Review identity and exact subject

- **Review date:** 2026-07-30
- **Review subject:** merge commit
  `c99cec8051be634b00681e92022ebadc9cb66019`
- **Parents:**
  `7487c9a5bbaf265b3d8acf8836e1f689e63468e1`,
  `e148d28c4d2b4afa63617bcc3faaae6d2461b610`
- **PR reference:** PR #193; PR head
  `e148d28c4d2b4afa63617bcc3faaae6d2461b610`
- **Reviewer:** Codex, GPT-5 family, fresh adversarial-rereview context
- **Context basis:** the pinned rereview prompt, pinned plans/review/response,
  governing specifications and decisions, exact-subject source and tests, and
  the three hash-pinned vault inputs.
- **Independence statement (P-022):** I did not author or remediate PR #193 and
  did not consult its authoring/remediation session. I reviewed the durable
  bytes and exact-subject implementation independently. This is model-family
  and session separation, not a claim of organizational or human independence.

A fresh history-bearing clone was configured with `core.autocrlf=false` and
`core.longpaths=true`, detached at the exact merge commit, and was clean before
and after validation. The superseded
`implementation/rm-04-verification-execution-and-manuscript-review-plan.md`
is absent.

### Recomputed Git identities

| Subject | Recomputed blob | Expected | Result |
|---|---|---|---|
| `implementation/06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md` | `9050249c07de31f0796f1ab808d3842911e06705` | same | match |
| `implementation/README.md` | `a5d6ddafef702ba74a7a4d7cbb54660f2cb3509c` | same | match |
| `implementation/rm-00-research-methods-lane-master-plan.md` | `1fcdd82ba5a8ab882df0599ed72e0a7e843ad5e6` | same | match |
| `implementation/rm-01-unblock-and-suite-recovery-plan.md` | `6b9c5214a97522f3d00a4c46876ab73c8e443284` | same | match |
| `implementation/rm-02-research-methods-pack-plan.md` | `f8fab2495f16a4e250e0bf1445999a37598cf41c` | same | match |
| `implementation/rm-03-brief-export-import-plan.md` | `d334ae1ec8e73dc33f5f7e3562f6dce4d2eb0dc5` | same | match |
| `implementation/rm-04-manuscript-review-and-verification-records-plan.md` | `50465793b270b132d02da0699d0caba0fd283181` | same | match |
| `reviews/rm-lane-review-response-2026-07-29.md` | `985afdfc71ac44f3301b6adda7a2abe43f620dbb` | same | match |
| `reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md` | `de400d801349f138ac18052ca834173201a950e2` | same | match |
| `03-decisions-and-open-questions.md` | `24228fb83f1cad4500967088f27606db7a68fe1f` | same | match |

### Recomputed external-input identities

| Input | Recomputed SHA-256 | Expected | Result |
|---|---|---|---|
| `ars-plus-deep-research-report.md` | `23873353d96593c35ef4bb1a50eb893af5432c40eb5d1851e1e7dcda74fd426c` | same | match |
| `ars-plus-deep-research-report-2.md` | `2d727f63139a5063a976b388c76c25652472d86b9f995e52fcfdaff658719650` | same | match |
| `Gemini For Research.md` | `43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24` | same | match |

The drift hard stop did not fire.

## Executive verdict

**Exact-subject verdict: `rework_required`.**

- **06h dispatch:** `reject`
- **RM-00 readiness:** `not_ready`
- **RM-01 dispatch:** `reject`
- **RM-02 dispatch:** `reject`
- **RM-03 dispatch:** `reject`
- **RM-04 dispatch:** `reject`

No document can proceed independently as written. RM-02 remains file-level
independent of 06h, but its claimed append-only history has no independent
anchor. RM-04 cleanly removes execution, but it depends on the rejected RM-03
authority and capability seams.

PR #193 materially improves revision 1: it removes untrusted execution, makes
the asset identity graph acyclic, separates WP6.1 work from the RM lane, stops
inventing an event family, hoists owner gates, and corrects most provenance and
governance classifications. Those improvements do not make the suite
dispatchable. The load-bearing replacement architecture is still incomplete:

1. the proposed artefact commands are not bound to the accepted authority
   catalogue's admission semantics;
2. the claimed consumer firewall is a test specification without a named
   production enforcement point;
3. T2 demonstrably bypasses the claimed single schema-identity derivation
   point;
4. the historical-event branches are not executable specifications;
5. RM-01 measures two post-06h states and therefore cannot attribute a delta to
   06h;
6. no accepted W3 packet resolver/producer exists at the review subject;
7. RM-02's revision history can be rewritten together with the current
   manifest; and
8. RM-03's capability-boundary scope contradicts RM-04 and omits the modified
   CLI handlers.

## Critical findings

### RR-C1 — Artefact acceptance is schema-reachable without the catalogue's authority semantics

**Precise claim.** RM-00 calls `SetArtefactUseAuthority` “authority-checked,
owner-attributed” and says imported material moves from candidate “only by
attributed command” (`rm-00...md:208-214`). The 06h plan does not specify the
accepted authority resolver, actor/scope/effectivity checks, six-dimension
consumer-predicate evaluation, or the governing review-set checks needed to
make that statement true.

**Quoted evidence.**

- 06h Task 3 says only: “Honour W2 §8 ordering: authority, expected version,
  idempotency and state-transition validation precede the write”
  (`06h...md:272-277`), and for use authority it requires an enum transition
  plus `subject_sha256` equality (`06h...md:278-284`).
- Its required negatives cover direct append, unknown type/major, reducer
  absence, replay equality, illegal transition, and hash mismatch
  (`06h...md:290-296`). They do not cover missing/wrong/expired/not-yet-effective
  authority, prohibited actor class, wrong scope/subject, authority-rule
  mutation, or incomplete independent review.
- The exact owner catalogue defines `RegisterArtefact` as `none -> candidate`
  (`wp6-1-owner-source-catalogue.yaml:6315-6321`), prohibits the `importer`
  actor class (`:6351-6367`), and requires the authority negatives listed at
  `:6372-6393`.
- For `SetArtefactUseAuthority`, the authority precondition is “consumer
  predicate over all six dimensions” (`:6874-6875`), with the authority and
  independent-review negatives at `:6895-6921`.
- The generated `RegisterArtefact` schema itself admits every
  `use_authority`, including `accepted_for_scope`
  (`register_artefact.schema.json:429-463`); schema shape therefore does not
  enforce the catalogue's `none -> candidate` transition.
- `SetArtefactUseAuthority.consumer_predicate` is only a non-empty string in
  schema (`set_artefact_use_authority.schema.json:29-41`).
- At the exact subject, generic `CommandService.submit` validates the generic
  envelope and appends after command-specific special cases
  (`research_system/command/service.py:173-312`). Canonical authority preparation
  exists only for publication/revocation, and `_scoped_authority_receipt`
  explicitly admits only those two command types (`:404-410`).

**Concrete failure scenario.** An agent or importer submits a schema-valid
`RegisterArtefact` manifest whose embedded authority is
`accepted_for_scope`, or submits `SetArtefactUseAuthority` with a syntactically
valid grant ID and an arbitrary non-empty consumer predicate. The proposed
implementation can append and replay an accepted-looking artefact without
proving current scope, actor eligibility, grant effectivity, six-dimension
predicate satisfaction, reviewer independence, or governing-review
completeness.

**Impact.** Invalid material can become canonical evidence and feed result or
claim use. This is a reachable authority violation, not a missing hardening
test. G-RM-10 cannot be accepted on the current text.

**Recommended disposition.** Fix before dispatch. Do not treat “schema-valid”
or `subject_sha256` equality as authority.

**Exact required interface/text.**

1. Make `RegisterArtefact` normalize or require the authoritative initial state
   `candidate`, independently of any caller-provided manifest value.
2. Route both commands through one canonical, lock-safe authority resolver that
   checks current grant, actor class, exact project/kind/id scope, effectivity,
   expiry, expected version, and idempotency before any event, receipt
   acceptance, object write, or projection mutation.
3. Define a versioned, independently accepted registry for the six-dimension
   `consumer_predicate`; a caller-supplied free string is not authority.
4. For transitions to `accepted_for_scope`, resolve and bind the complete
   governing review set, eligibility, relatedness, independence grade, and
   Stephen's applicable decision.
5. Import every NA/NI catalogue control at
   `wp6-1-owner-source-catalogue.yaml:6372-6393,6895-6921`, including atomic
   no-side-effect assertions.

**Affected decisions/work packages.** P-005, P-043, P-044, W2 §§8 and 16, W5
§§17 and 19, G-RM-3, G-RM-10, O-RM-4, O-RM-16, 06h Task 3, RM-03, RM-04.

### RR-C2 — The claimed consumer firewall has no production enforcement seam

**Precise claim.** RM-03 says consumer-level protection is “tested end to end”
and that candidate artefacts cannot be consumed as result or claim evidence
(`rm-03...md:57-65,313-327`). Its file map creates schemas, exporter/importer
modules, CLI handlers, and tests, but names no production result/claim consumer,
policy resolver, or canonical citation seam (`:87-113`).

**Quoted evidence.**

- Task 6 creates `test_claim_consumer_firewall.py` and asserts six properties,
  but no implementation step or production module owns those properties
  (`rm-03...md:313-327`).
- The exact-subject `research_system/**/*.py` tree contains no runtime
  occurrence of `context_packet`, `consumer_predicate`,
  `accepted_for_scope`, or `use_authority`.
- The sidecar specification carries `authorized_consumers` inside the sidecar
  itself (`rm-02...md:229-235`), while RM-03 merely lists unauthorized-consumer
  fixtures (`rm-03...md:289-290`); no independent access-authority source or
  enforcement point is named.
- Operator verification is a separately imported candidate record
  (`rm-03...md:198-206`), but the plan names no canonical actor/session
  authority resolver for `verified_by_actor_id`.

**Concrete failure scenario.** A consumer reads an imported object directly by
ID or content hash and treats its schema-local status, an attached
`OperatorVerification`, or a sidecar's self-declared `authorized_consumers`
as permission. The proposed tests can stay green against a test helper while
the actual result/claim citation path never consults artefact use authority.

**Impact.** Candidate evidence and sensitive re-identification mappings can be
used outside their accepted scope. P-005 claim-promotion separation exists in
prose but not at every canonical consumer.

**Recommended disposition.** Fix before RM-03 or RM-04 dispatch.

**Exact required interface/text.** Name and modify the actual result,
manuscript, review, and claim-evidence resolution seams. All canonical
consumers must call one fail-closed policy function over the replay-derived
artefact state, exact content hash, accepted predicate identity, consumer
identity, scope, and current authority evidence. The plan must enumerate those
call sites and include bypass fixtures for direct object read, local-status
parsing, projection reclassification, separately-valid record substitution,
supersession, and unauthorized sidecar resolution. P-005 promotion remains a
separate Stephen-attributed decision.

**Affected decisions/work packages.** P-005, P-042, P-044, W3 §§9 and 15, W5
§§14.6 and 19, O-RM-4, O-RM-21, O-RM-22, RM-03 Tasks 4 and 6, RM-04.

## Major findings

### RR-M1 — The “single derivation point every producer flows through” excludes T2

**Precise claim.** 06h says producer truthfulness is derived at “the single
point every producer flows through” (`06h...md:65-68`) and H-4 explicitly
includes T2 (`:154`). Its Task 2 file map does not include
`research_system/command/t2.py` (`:115-121`).

**Quoted evidence.**

- `CommandService.submit` returns through `submit_t2` before generic validation
  (`research_system/command/service.py:181-183`).
- `submit_t2` performs its own command-specific validation
  (`research_system/command/t2.py:998-1008`).
- `_event_envelope` constructs T2 events without the
  `command_schema_{id,version,sha256}` triple (`:866-888`), and T2 appends
  directly (`:1152-1153`).
- The plan postpones the bounded producer inventory until Task 4 after
  implementation (`06h...md:299-308`).

**Failure scenario.** TaskCreated passes the new seam while every T2 event
continues to omit P-043 identity. The Worker either violates the file map by
editing `t2.py`, or reaches Partial after already changing the generic path.

**Impact.** P-043 remains false for an authoritative producer family, and the
156-node recovery claim cannot be established.

**Recommended disposition.** Amend before dispatch.

**Exact required interface/text.** Build the source-derived producer matrix
before Task 2. Include `t2.py` and any command-originated helper in the file
map; pass the exact `RegisteredSchema` used by T2 validation into its event
builder. Define a separate explicit policy for legitimately commandless
internal/eval appends rather than fabricating command provenance.

**Affected decisions/work packages.** P-043, 06h Tasks 2 and 4, H-4, RM-01
Task D, Gate 6.

### RR-M2 — G-RM-8 offers choices whose evidence and consequences are unspecified

**Precise claim.** G-RM-8 asks Stephen to choose migrate, grandfather, or
no-prior-store (`rm-00...md:92`), and 06h repeats the three branches
(`06h...md:223-230`). The plan does not define branch-specific evidence,
migration identity, idempotency, replay effect, rollback/stop semantics, or a
bounded grandfather predicate.

**Failure scenario.** A grandfather condition such as “missing the new fields”
continues to admit newly malformed events, or a migration rewrites/replays
events non-idempotently. Stephen must choose before the plan makes those
consequences inspectable.

**Impact.** The historical policy can weaken P-043 or corrupt replay while
appearing to satisfy an owner gate.

**Recommended disposition.** Specify all three protocols before requesting the
owner choice; keep G-RM-8 open.

**Exact required text.** For each branch name: authoritative store inventory;
admission predicate; evidence producer independent of the migration; migration
ID and exact input/output identity; repeat-run behavior; replay semantics;
rollback/stop rule; and a negative fixture distinguishing historical events
from newly malformed events.

**Affected decisions/work packages.** P-043, G-RM-8, H-3, 06h Task 2, replay.

### RR-M3 — RM-01 cannot measure a pre/post-06h delta

**Precise claim.** RM-01 branches “after 06h has merged”
(`rm-01...md:34-36`). Task A then collects the dispatch-head comparator
“before anything else” (`:116-147`), while Task B runs “after 06h has merged”
(`:149-169`). Both measurements are post-06h.

**Failure scenario.** The preserved 156-node cohort is collected only after the
schema-identity fix. Comparing it with the subsequent full run cannot
distinguish 06h movement from no movement. Task A's instruction to restore a
regressed prerequisite “before dispatching 06h” is also temporally impossible
inside this post-06h plan (`:123-130`).

**Impact.** The headline suite-delta evidence is non-causal and cannot close
R1-3/P-043 recovery.

**Recommended disposition.** Reorder before dispatch.

**Exact required text.** Collect and durably record the full node-ID manifest,
156-node outcomes, and prerequisite signature at the exact pre-06h accepted
head, either as 06h Task 0 or a separate predecessor. Run the same node set and
current-universe accounting once at the exact post-06h head. Preserve additions,
removals, and renames explicitly.

**Affected decisions/work packages.** P-043, G-RM-7, R1-3/R1-7, RM-01 Tasks A
and B.

### RR-M4 — RM-03 has no reachable accepted W3 packet mechanism

**Precise claim.** RM-03 requires an “accepted W3 packet” and fails export when
it is absent, superseded, or hash-mismatched (`rm-03...md:124-162`). Its own
Partial criteria admit that “no accepted W3 packet mechanism is reachable”
must stop the task (`:254-258`).

**Direct evidence.** No exact-subject runtime Python source contains
`context_packet`. RM-03 depends on 06h and RM-02, neither of which creates a W3
packet producer, lifecycle authority, or resolver (`rm-00...md:62-66`).

**Failure scenario.** Task 2 cannot produce its positive export fixture without
inventing a substitute packet, which M-6 expressly forbids.

**Impact.** RM-03 is known to reach Partial before its main happy path; RM-04
cannot follow.

**Recommended disposition.** Add and independently review the W3 packet
capability as a predecessor. Do not weaken the packet into a local manifest.

**Exact required interface/text.** Name the accepted packet schema, producer,
ID/revision/hash authority, lifecycle/supersession source, subject-scope and
delivery bindings, resolver, and wrong-but-valid substitution fixtures. RM-03
must consume that interface read-only.

**Affected decisions/work packages.** W3 §§9 and 13, O-RM-20, RM-03 Tasks 2
and 4, RM-04.

### RR-M5 — RM-02's “append-only” revision history is self-attested

**Precise claim.** RM-02 says `methods-pack-revisions.yaml` is append-only and
“what makes tamper detection possible” (`rm-02...md:83-88`). The loader parses
the current manifest and current history together and checks one against the
other (`:180-194`); no prior history identity, prefix commitment, chain, Git
ancestor, event stream, or external anchor is specified.

**Failure scenario.** Replace an asset under the same version, update the
current manifest, and rewrite or remove the corresponding history entry. The
two current files remain mutually consistent, so the specified loader has no
trusted expected value from which to detect removal or replacement.

**Impact.** Candidate history can be silently rewritten and the claimed
same-version/removed-entry negatives (`rm-02...md:259-261`) cannot be made
meaningful.

**Recommended disposition.** Amend before RM-02 dispatch.

**Exact required interface/text.** Anchor the prior history independently:
use an append-chained record with a previous-history hash plus an accepted root,
a canonical event stream, or a pinned prior Git blob/ancestor rule. The negative
control must mutate current asset, manifest, and history together and still
fail.

**Affected decisions/work packages.** W3 §13, G-RM-4, O-RM-8, RM-02 Tasks 1
and 3.

### RR-M6 — The P-042 capability boundary omits the CLI surface it claims to cover

**Precise claim.** RM-03 modifies `research_system/cli.py`
(`rm-03...md:109-113`), but Task 5 analyzes only
`research_system/methods/**` and allowlists all `research_system.*`
(`:297-312`). RM-04 says the same boundary extends over “the new brief command
handlers and their call graph in `research_system/cli.py`”
(`rm-04...md:72-80`).

**Failure scenario.** A CLI handler or first-party transitive helper imports a
transport, dynamic loader, tool seam, or process launcher. The RM-03 test passes
because the code lies outside its scanned root or inside the broad first-party
allowlist.

**Impact.** P-042 can be bypassed through the actual entry point while the
declared guard stays green.

**Recommended disposition.** Reconcile the two plans before RM-03 dispatch.

**Exact required text.** Analyze the changed methods modules, the exact new CLI
handlers, and their fully resolved transitive call/import graph. Replace the
blanket `research_system.*` allowance with a closed module set. Preserve only
the pre-existing fixed-argv Git-root-discovery exception by exact structural
identity, and test all CLI/transitive bypasses.

**Affected decisions/work packages.** P-042, O-RM-1, RM-03 Task 5, RM-04
global constraints.

## Minor and editorial findings

### RR-m1 — RM-01's corrected `pyproject.toml` line numbers are already stale

RM-01 says the relevant lines are 106 and 113 (`rm-01...md:30,173-175`).
At the exact subject, `known-first-party` is line 130 and `addopts` line 137
(`pyproject.toml:129-137`). The instruction says to reverify before editing, so
this does not independently block dispatch, but it repeats the drift class the
plan claims to correct.

**Disposition:** update to symbols/keys rather than volatile line numbers.

### RR-m2 — RM-01 closes out against the wrong README path

RM-01 requires updating
`docs/plans/agentic-research-system/README.md` (`rm-01...md:208`), while the RM
lane status row is in `implementation/README.md` (`implementation/README.md:60-65`);
06h correctly names that file (`06h...md:322`).

**Disposition:** change the RM-01 close-out path to
`implementation/README.md`.

### RR-m3 — O-RM-5 names an obsolete record type

RM-00 says a `VerificationResult` “certifies execution only”
(`rm-00...md:124`), while the revised non-executing plan consistently defines
`OperatorVerificationRun` (`rm-04...md:22,50,87,120`). The old term also
suggests ARS execution, which revision 2 removed.

**Disposition:** name `OperatorVerificationRun` and state that it records an
operator-reported run; it does not certify ARS execution or acceptance.

## Prior-finding closure matrix

| Prior | Prescribed invariant | Revised mechanism and direct evidence | Distinguishing negative control | Disposition |
|---|---|---|---|---|
| C-1 | Exact bytes/path retained; validator and producer use one immutable identity record | 06h defines `RegisteredSchema` with one read and same-instance return (`06h...md:55-68,210-220`) | TOCTOU, duplicate ID, mutation, wrong triple are named; full producer set is not bound | `partially_closed` |
| C-2 | Remove asset self-hash; define stable external identity | RM-02 puts identity only in external manifest and offers Git blob or LF-canonical SHA-256 (`rm-02...md:90-99,178-179`) | Self-hash-shape and EOL fixtures (`:262-266`) | `closed` |
| C-3 | Use an authoritative command/ledger/replay family | 06h chooses existing core artefact commands and reducers (`06h...md:70-76,265-296`) | Replay/direct-append controls exist, but accepted authority controls do not | `superseded_by_new_finding` (RR-C1) |
| C-4 | No untrusted execution without an accepted isolation substrate | Old RM-04 is deleted; new RM-04 prohibits execution/subprocess/runner (`rm-04...md:72-88`); G-RM-11 requires independent exact-subject readiness | RM-04 requires static prohibitions and escape fixtures; no runner exists | `closed` |
| M-1 | Hoist all owner gates; make review semantics fail closed | RM-00 lists G-RM-1..11 and tightens G-RM-3 (`rm-00...md:75-109`) | `reject` always blocks; required changes need independent closure | `closed` |
| M-2 | Separate WP6.1 main-path work | 06h is explicitly main-path and RM-03 depends on its capability (`rm-00...md:58-73`) | README/status separation is explicit | `closed` |
| M-3 | Authoritative revision/lifecycle/permissions/overlays/external acceptance | Permissions, overlays, external two-phase resolver are specified (`rm-02...md:101-116,120-128`) | Acceptance mutations are strong; history removal is not independently detectable | `partially_closed` (RR-M5) |
| M-4 | Closed capability boundary over CLI and transitive dependencies | RM-03 replaces denylist with AST/transitive test (`rm-03...md:297-312`) | Evasion fixtures named, but CLI is outside scanned root | `open` (RR-M6) |
| M-5 | End-to-end consumer/claim firewall | Artefact use authority replaces local enums (`rm-03...md:57-65,313-327`) | Tests named, no production consumer seam | `superseded_by_new_finding` (RR-C1/RR-C2) |
| M-6 | Brief is one non-governing rendering of accepted W3 packet | Exact packet reference and fail-closed export rules are specified (`rm-03...md:124-162`) | Wrong/stale packet fixtures named, but no reachable packet authority exists | `open` (RR-M4) |
| M-7 | RM-owned session evidence, not provider eligibility or WP6.3 coupling | Free-string operator choice; WP6.3 pack is not read (`rm-03...md:164-175`) | No allowlist; wrong-session/brief binding controls | `closed` |
| M-8 | Accepted kinds and UUIDv7; shared identity definitions | Brief and run artefacts use registered `art_` UUIDv7; document schema IDs are not event/ID-kind extensions (`rm-03...md:115-146`; `rm-04...md:95-125`) | `$id` uniqueness and reference/hash substitution controls | `closed` |
| M-9 | Dispatch-current, cohort-preserving baseline ordered around the fix | Fresh manifest and preserved 156-node cohort are specified (`rm-01...md:116-169`) | Divergence is measurable, but both measurements occur post-06h | `open` (RR-M3) |
| M-10 | Sidecar locatable, exact, authorized, reversible and joined | ID/revision/hash/subject/transform/sensitivity/retention fields and round trip are specified (`rm-02...md:229-235`; `rm-03...md:289-290`) | Wrong/missing/stale/unauthorized fixtures named; independent access authority absent | `partially_closed` (RR-C2) |
| M-11 | Source-supported methods; label heuristics | Minimal-first is explicitly ARS-added; source sections are named (`rm-02...md:220-245`) | Lineage section resolution is required | `closed` |
| M-12 | Paper Claim governance at relevant seams | RM-03 and RM-04 explicitly carry Output/Provenance plus Paper Claim governance (`rm-00...md:171-178`; `rm-03...md:240-253`) | Promotion absence and consumer tests are named, subject to RR-C2 | `closed` as classification |
| m-1 | Render accepted decisions and gate state consistently | P-044 is closed at G-RM-2; G-RM-3 is correctly reopened (`rm-00...md:85-95`) | README says revision 2 is not accepted | `closed` |
| m-2 | Scope registry ownership to 06h/G-RM-9 | O-RM-10 is discharged and `schema_registry.py` is editable only in 06h under G-RM-9 (`rm-00...md:129,158-167`) | Cross-plan do-not-touch rules are explicit | `closed` |
| m-3 | Exact close-out commands and triggers | Each dispatchable plan lists concrete pytest/ruff/full-suite commands and expansion triggers | Commands are executable, despite RR-m1's stale line references | `closed` |

## Attack-surface disposition

| # | Surface | Disposition |
|---|---|---|
| 1 | Exact subject and merge seam | **Clean.** Commit, parents, all pinned blobs, deletion, and vault hashes match; exact clone stayed clean. |
| 2 | Exact schema identity | **Partial.** Same-instance raw-byte design is feasible; producer completeness and path-alias/symlink/case controls are not fully bounded (RR-M1). |
| 3 | Producer derivation and command-specific authority | **Failed.** T2 bypasses the claimed single point; internal/direct append paths lack a pre-dispatch disposition. |
| 4 | Historical-event policy | **Failed.** Three branches are names, not executable protocols (RR-M2). |
| 5 | Accepted artefact family, authority, replay | **Failed.** Schema/event/reducer route is plausible; catalogue authority semantics and negatives are absent (RR-C1). |
| 6 | Consumer firewall and claim promotion | **Failed.** No production consumer enforcement point; P-005 remains prose-only at the seam (RR-C2). |
| 7 | RM-02 identity/history/external acceptance | **Partial.** Identity DAG and external acceptance resolver are strong; revision history is self-attested (RR-M5). |
| 8 | W3 packet/assets/sidecar | **Failed.** Assets and method lineage are well specified; packet authority is absent and sidecar authorization is not independently sourced. |
| 9 | RM-03 import/capability boundary | **Partial/failed.** Cross-brief join is explicit and strong; capability guard omits CLI/transitive first-party closure (RR-M6). |
| 10 | RM-04 verification-context integrity | **Clean with dependency.** Reference-only schema/version/ID/hash binding, exact traceback rendering, and wrong-reference controls are specified; it still depends on rejected RM-03 consumers. |
| 11 | Execution removal/G-RM-11 | **Clean.** Execution is absent; re-entry needs an independently accepted exact-subject isolation substrate. |
| 12 | RM-01 baseline/G-RM-7 | **Failed.** Gate semantics are honest, but temporal ordering cannot measure the 06h delta (RR-M3). |
| 13 | Gates/dependencies/owner touchpoints | **Failed.** Touchpoints are hoisted, but G-RM-8/G-RM-10 do not present acceptable choices/mechanisms and the W3 predecessor is missing. |
| 14 | Enforcement completeness/practicality/residual risk | **Failed.** Several tasks necessarily reach their own Partial stop; tests are used as placeholders for absent production authority. |

No new mathematical, statistical, topological, representation, or
source-paper factual defect was found. No execution path remains in RM-04.
No new methods event family or WP6.3 accepted-byte dependency remains.

## Cross-spec consistency matrix

| Invariant | Authoritative definition | Enforcement point required | Evidence producer | Distinguishing negative control | Acceptor | Result |
|---|---|---|---|---|---|---|
| Exact command-schema bytes | P-043; W2 event identity | `SchemaRegistry.validate` returning one `RegisteredSchema`; every command producer | Registry plus command service | TOCTOU, wrong registered schema, alias/case/symlink, T2 bypass | Independent review; Stephen at G-RM-9 | Partial |
| Producer triple on every command event | P-043; H-4 | Generic and T2 event builders before append | Command service/T2 | Missing mapping and command-originated direct append | Independent 06h review | Failed |
| Historical event admission | P-043; handoff 26 | Replay/load admission or migration | Independent store inventory/migrator | New malformed event must not satisfy historical predicate | Stephen at G-RM-8 | Failed |
| Artefact `none -> candidate` | W2 §16; owner catalogue `artefact.register` | Command authority resolver before object/event/receipt/projection | Canonical grant and catalogue | Imported actor; caller asks for accepted initial state; atomic no-side-effect | Stephen at G-RM-10 plus command-family acceptance | Failed |
| Artefact accepted-for-scope | W2 §16; W5 §§17/19; P-005 | Versioned six-dimension predicate and review-set resolver | Canonical grant, reviews, Stephen decision | Wrong scope/actor/grant/reviewer set; free-string predicate | Stephen/P-005 | Failed |
| Candidate cannot feed claims | W5 §§14.6/19 | Every result/review/manuscript/claim evidence resolver | Replay-derived artefact state | Direct object read, loose local status, substituted authority record | Claim owner/Stephen | Failed |
| Brief binds accepted packet | W3 §§9/13 | Accepted packet resolver at export/import | Canonical packet producer/lifecycle store | Wrong-but-valid/stale packet and cross-packet subject | Packet owner | Missing |
| Methods history append-only | W3 §13 | Independently anchored history chain/store | Prior accepted history root | Coordinated rewrite of asset, manifest, and history | Methods-pack owner at G-RM-4 | Failed |
| Sidecar access and reversal | W3 §15; O-RM-21 | Object resolver plus independent access policy | Sidecar producer and authority store | Wrong join, stale revision, unauthorized consumer, exact round trip | Data/packet owner | Partial |
| No provider operation | P-042 | Closed import/call graph across methods and CLI | Static capability guard | Dynamic/transitive/CLI/tool/process/network fixtures | Stephen's fixed P-042 boundary | Partial |
| No execution | P-042; W8; G-RM-11 | Absence guard now; isolation substrate before future runner | Static scan; future W8 records | Runner/process/egress/mount/credential escape fixtures | Independent readiness review and Stephen | Satisfied for revision 2 |

## Provenance trace

Deep-research reports were treated as discovery leads only. No requirement was
accepted solely because either report asserted it.

| Plan / substantive requirement | Provenance authority | Disposition |
|---|---|---|
| RM-02 provider-neutral, reusable method assets | P-044; W3 §13 | Supported |
| RM-02 risk-led review finding shape | pinned Woodruff paper §§2.4, 9.1; RM-02 lineage checks | Supported |
| RM-02 counterexample/prove-or-refute shape | pinned paper §9.2 | Supported |
| Minimal-instance-first heuristic | ARS-added heuristic, explicitly labelled in RM-02 | Correctly not attributed to paper |
| RM-02 theorem retrieval plus external verification | pinned paper §§2.2-2.3; P-042 operator boundary | Supported |
| RM-02 decomposition scaffold | pinned paper §2.1 | Supported |
| RM-02 de-identification, permissions, overlays, lifecycle | W3 §§13 and 15; prior review M-3/M-10 | Supported, but history/access enforcement incomplete |
| RM-02 external owner acceptance | W3 lifecycle; repository `ContentAddressedAuthorityResolver` seam | Read-side feasible; no writer is inferred |
| RM-03 operator-mediated session record | P-042/O-RM-3 | Supported |
| RM-03 non-governing brief bound to packet | W3 §9 and §13; prior M-6 | Required, but runtime authority absent |
| RM-03 typed returned evidence and transcript/hidden-reasoning exclusion | P-042; W3 §15 | Supported |
| RM-03 accepted artefact landing/replay | W2 §16; P-043; prior C-3 | Family exists in specification; authority rendering incomplete |
| RM-03 consumer firewall and claim separation | W5 §§14.6 and 19; P-005; prior M-5/M-12 | Required, but production enforcement unsourced |
| RM-03 de-identification sidecar | W3 §15; prior M-10/O-RM-21 | Required; independent authorization source missing |
| RM-03 capability boundary | P-042; prior M-4 | Required; CLI/transitive scope inconsistent |
| RM-04 verification request, traceback feedback, operator-run record | pinned paper §2.6; P-042 operator relay | Supported and non-executing |
| RM-04 manuscript review evidence and Paper Claim governance | W5 §§14.6, 16-19; P-044/O-RM-22 | Supported |
| RM-04 no execution and future isolation gate | P-042; W8; prior C-4/G-RM-11 | Supported |
| Report 1 recommendations | Vault report 1 | Lead only; independently grounded above |
| Report 2 rollback/sidecar recommendations | Vault report 2; independently checked against W2/W3 | Lead only; authoritative rendering is W2/W3 |
| Production claim-consumer module | `unsourced` in plan/source | Missing; RR-C2 |
| Accepted W3 packet producer/resolver | `unsourced` in plan/source | Missing; RR-M4 |
| Independently anchored methods revision history | `unsourced` in plan/source | Missing; RR-M5 |

## Gate audit

| Gate | Disposition at exact subject |
|---|---|
| G-RM-1 | **Closed historical fact.** P-043 exists; does not imply implementation acceptance. |
| G-RM-2 | **Closed historical fact.** P-044 exists; does not imply suite acceptance. |
| G-RM-3 | **Open and blocking.** This rereview returns `rework_required`. |
| G-RM-4 | **Open.** Owner must accept methods assets through real external authority. RM-02 may produce candidates only; RR-M5 must close first. |
| G-RM-5 | **Open, later owner choice.** Correctly blocks only the RM-04 pilot. |
| G-RM-6 | **Open, later owner choice.** Smoke-gate location remains Stephen's decision. |
| G-RM-7 | **Open.** Branch semantics are explicit, but RM-01 cannot make a causal delta claim until RR-M3 closes. |
| G-RM-8 | **Open and under-specified.** Do not request owner choice until RR-M2's branch protocols exist. |
| G-RM-9 | **Open.** The `RegisteredSchema` interface is technically feasible; acceptance still belongs to Stephen after full producer coverage is specified. |
| G-RM-10 | **Open and blocking.** Family choice is directionally sound, but RR-C1/RR-C2 must close before owner confirmation. |
| G-RM-11 | **Open by design and correctly fail-closed.** No execution is authorized; future re-entry needs independent exact-subject readiness evidence. |

## Obligation and decision audit

| Item | Disposition |
|---|---|
| O-RM-1 | **Partial.** Provider-operation ban is correct; capability enforcement omits CLI/transitive closure (RR-M6). |
| O-RM-2 | **Satisfied historical rendering.** P-044 supplies the implementation decision. |
| O-RM-3 | **Adequately specified.** RM-owned attributed session evidence, no eligibility allowlist. |
| O-RM-4 | **Open.** Candidate/claim separation lacks authoritative transition and production consumer enforcement (RR-C1/RR-C2). |
| O-RM-5 | **Partial/editorial.** Two-key rule remains; obsolete `VerificationResult` wording must be corrected (RR-m3). |
| O-RM-6 | **Adequately specified.** Closed schemas and explicit forbidden-field fixtures; no hidden-reasoning intake. |
| O-RM-7 | **Adequately specified.** Permissions and observer overlays are restored to RM-02. |
| O-RM-8 | **Open.** Lifecycle shape is specified, but append-only history authority fails (RR-M5). |
| O-RM-9 | **Satisfied.** WP6.3 accepted-byte files are neither modified nor read by RM-03. |
| O-RM-10 | **Satisfied historical rendering.** Registry ownership is correctly scoped to 06h/G-RM-9. |
| O-RM-11 | **Open implementation.** P-043 direction is accepted; producer coverage is incomplete (RR-M1). |
| O-RM-12 | **Adequately planned.** Each plan carries the required vault close-out. |
| O-RM-13 | **Adequately planned.** Worktree/commit/review constraints are repeated. |
| O-RM-14 | **Satisfied in plan text.** Provider-neutral naming retained; neutral synthetic capability fixtures used. |
| O-RM-15 | **Adequately specified.** Rollback uses immutable supersession/rejection, not deletion. |
| O-RM-16 | **Open.** Append-only family is plausible, but command authority/producer completeness is not (RR-C1/RR-M1). |
| O-RM-17 | **Satisfied as deferral.** Owner and next gate are named. |
| O-RM-18 | **Partial.** Status close-out exists, but RM-01 names the wrong README (RR-m2). |
| O-RM-19 | **Satisfied for this suite.** Execution removed; G-RM-11 blocks re-entry. |
| O-RM-20 | **Open.** Accepted W3 packet capability is absent (RR-M4). |
| O-RM-21 | **Partial.** Locatability/reversal/join are planned; independent access authority is absent (RR-C2). |
| O-RM-22 | **Satisfied as classification.** RM-03/RM-04 declare Paper Claim governance, though enforcement still fails RR-C2. |
| P-042 | **Direction upheld; rendering partial.** No provider or execution surface is intentionally added, but the static boundary is incomplete. |
| P-043 | **Not implemented by a dispatchable plan.** Exact-byte design is feasible; T2 and historical policy remain open. |
| P-044 | **Direction upheld.** The independent provider-neutral RM lane remains valid; these plans do not yet render it dispatchably. |

## Per-document closure conditions

### 06h — `reject`

Independent closure requires:

1. pre-dispatch source-derived producer matrix, including T2 and commandless
   append dispositions;
2. T2 file/interface changes in scope so the exact validated schema identity
   reaches its event builder;
3. complete, executable migrate/grandfather/no-store protocols before G-RM-8;
4. exact catalogue-derived authority resolver, transition, review-set, and
   atomic negative controls for both artefact commands; and
5. an independent rereview of the amended exact subject followed by Stephen's
   G-RM-8/G-RM-9/G-RM-10 decisions. Passing schema tests is not closure.

### RM-00 — `not_ready`

Independent closure requires:

1. replace the false “real consumer firewall” and authority assertions with
   interfaces that satisfy RR-C1/RR-C2;
2. add the accepted W3 packet capability to the dependency graph;
3. make RR-M2/RR-M3/RR-M5/RR-M6 visible as blocking obligations;
4. correct O-RM-5 and O-RM-18 rendering; and
5. obtain a fresh G-RM-3 review verdict on the revised bytes.

### RM-01 — `reject`

Independent closure requires a pinned pre-06h manifest/outcome record and a
post-06h run over the preserved cohort/current universe, with exact commit
identity and no temporal contradiction. Correct the `pyproject.toml` references
and README close-out path. Stephen still chooses G-RM-6/G-RM-7; those choices
do not repair invalid comparison ordering.

### RM-02 — `reject`

Independent closure requires a history authority that survives coordinated
asset/manifest/history rewrite, plus the matching coordinated-rewrite negative
fixture. Keep assets candidate until a production external owner-acceptance
writer and Stephen's G-RM-4 record exist; do not fabricate that writer in
RM-02.

### RM-03 — `reject`

Independent closure requires:

1. an accepted, reachable W3 packet producer/lifecycle/resolver predecessor;
2. exact authoritative artefact-transition semantics from the corrected 06h;
3. named production result/review/manuscript/claim consumer seams that all
   enforce replay-derived use authority and P-005 separation;
4. an independent sidecar access-authority source; and
5. a capability guard closed over the changed CLI handlers and complete
   transitive graph.

### RM-04 — `reject`

The non-executing redesign is acceptable in isolation, but dispatch requires
accepted RM-03 interfaces and the corrected shared capability guard. After
those dependencies close, independently verify the shared verification-context
schema identity/hash contract and the no-execution call graph. G-RM-5 remains
Stephen's later pilot-subject choice. G-RM-11 remains closed to execution.

## Coverage and fixture gaps

Required additions, grouped to avoid duplicative suites:

1. **Schema identity/producer:** path alias, symlink, case variant,
   valid-wrong command schema, T2 event, every command-originated append, and
   explicit commandless paths.
2. **Historical policy:** one positive and one bypass-negative fixture for each
   migrate, grandfather, and no-store branch; repeat migration and replay.
3. **Artefact authority:** every NA/NI owner-catalogue case, including
   importer actor, wrong scope/kind/id, grant time bounds, rule mutation,
   reviewer eligibility/relatedness/independence/review-set completeness, and
   atomic no event/accepted receipt/object/projection effects.
4. **Consumer firewall:** direct object read, local status parse, projection
   reclassification, wrong-but-valid authority record, superseded object,
   missing P-005 decision, and sidecar access by a syntactically valid but
   unauthorized consumer—all through real production consumers.
5. **W3 packet:** absent, stale, wrong-but-valid, cross-packet subject,
   delivery mismatch, unresolved conflict, unsafe source, and omitted governing
   source through the accepted packet resolver.
6. **Methods history:** coordinated replacement of asset, current manifest,
   and history; history prefix deletion/reordering/duplication/extra entry.
7. **P-042 boundary:** each evasion planted in methods, new CLI handlers, and a
   first-party transitive dependency; exact structural exception for existing
   fixed-argv Git root discovery.
8. **Baseline:** same preserved 156-node cohort observed at pinned pre- and
   post-06h subjects.

## Practicality assessment

- The 06h `RegisteredSchema` interface is practical and appropriately small.
- The artefact-family choice is reusable and avoids a new event namespace, but
  implementing two catalogue-governed commands is not a two-event routing
  exercise; authority, atomicity, review-set, replay, and consumer enforcement
  are the dominant work.
- RM-02's content and external acceptance read-side are practical. A plain YAML
  file cannot become append-only by schema declaration.
- RM-03 is not practical until the W3 packet and consumer-authority seams exist.
  Its own Partial criteria correctly reveal that dependency.
- RM-04's record-only redesign is practical and substantially safer than
  revision 1, but it cannot bypass RM-03.
- The requested validation ladder remains proportionate: direct identity
  checks, focused semantic controls, then one final broader gate only after the
  exact blocking seams exist.

## Revision plan

### Immediate factual and interface corrections

1. Correct RM-01's temporal ordering, line references, and README path.
2. Correct `VerificationResult` to `OperatorVerificationRun`.
3. Replace 06h's post-implementation producer sweep with a pre-dispatch
   source-derived matrix and include T2.
4. Expand G-RM-8 into three executable branch specifications.
5. Bind artefact commands to the complete owner-catalogue authority contract,
   not only generated schemas and hash equality.
6. Name actual production consumer and sidecar-access enforcement points.
7. Anchor RM-02 history independently.
8. Reconcile RM-03/RM-04 capability-boundary scope over methods, CLI, and
   transitive dependencies.

### Owner decisions, after mechanisms are inspectable

1. Stephen chooses G-RM-8 historical policy.
2. Stephen accepts or rejects the exact `RegisteredSchema` interface at G-RM-9.
3. Stephen confirms the corrected artefact-family authority rendering at
   G-RM-10.
4. Stephen chooses the RM-01 smoke location and R1-3b branch at G-RM-6/G-RM-7.
5. Stephen may later accept methods assets at G-RM-4 and choose the RM-04 pilot
   at G-RM-5.
6. No execution decision is requested; G-RM-11 remains closed.

### Later-work dependencies

1. Build and independently accept the W3 packet capability before RM-03.
2. Provide the external methods-asset acceptance writer before accepted assets
   are claimed; candidate authoring may precede that only after RR-M5 closes.
3. Keep the 78-command family sweep, RM-05, provider adapters, formalization
   expansion, remote MCP, and fine-tuning in their named later gates.

## Residual risks and validation evidence

Residual risk remains concentrated in semantic authority, not schema shape:
free-string predicates, self-attested histories/access lists, test-only
firewalls, and incomplete producer inventories can all produce internally
consistent but unauthorized state.

Validation performed:

- verified the exact merge commit and both parents;
- recomputed all ten pinned Git blobs and all three vault SHA-256 identities;
- verified the superseded RM-04 path is absent;
- verified `.gitattributes` fixes `.research-system/**` to LF at the exact
  subject;
- enumerated exact-subject runtime references for packet/use-authority terms
  (none) and direct ledger append sites;
- traced `CommandService.submit`, `submit_t2`, T2 event construction, authority
  resolver use, and owner-catalogue artefact rows;
- ran the smallest relevant existing read-only schema-contract slice with
  bytecode, cache, and coverage writes disabled:

  `3 passed in 23.81s`

  (`test_wp6_1_identity_manifest_binds_raw_schema_bytes_paths_ids_versions_and_git_blobs`,
  `test_wp6_1_payload_oracle_covers_the_exact_owner_catalogue_key_set`, and
  `test_wp6_1_generated_schemas_are_closed_domain_specific_and_cover_shared_unions`).

Those passing tests establish generated-schema materialization and catalogue
coverage, not runtime authority or plan acceptance.

The exact-subject clone was clean after validation. The only repository file
written by this review is this report. The host worktree was already dirty on
branch `pipe/wp6-runtime-schema-binding-a0` at
`cddb5b79c3a5b142a5a10170d26f97da7563f4f2`; all pre-existing changes were
preserved and were not used as exact-subject evidence.
