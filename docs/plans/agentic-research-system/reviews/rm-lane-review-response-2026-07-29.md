# RM lane plan suite — response to the G-RM-3 adversarial review

**Response date:** 2026-07-29
**Responds to:** `adversarial-rm-lane-plan-suite-review-2026-07-29.md`
(review of subject `6e7d0e0add73ab4af33ebcf2acb96ae73f6d97e2`)
**Author:** authoring session (Claude, Opus 5), TDL main checkout
**Status:** revision record. This document disposes of every review finding and
points at the revised plan text. It confers no dispatch authority: G-RM-3 is
re-opened against the **revised** suite and requires a fresh independent review.

---

## 1. Verdict on the verdict

The review is accepted in full. **No finding is rejected.** Every Critical and
Major was verified against live source before being acted on, not taken on the
reviewer's authority; §2 records what that verification found. Three findings
(C-1, C-3, M-8) were confirmed by direct inspection of code the review cited,
and one (M-9's implied line-number drift) turned out to understate the problem —
the superseded RM-01 cited `pyproject.toml:96,103` for the coverage and
first-party edits, and the real lines are `106` and `113`.

The suite verdict `rework_required` stands. This revision does the rework.

**What survives unchanged:** the accepted owner decisions. P-042, P-043 and
P-044 are not amended, reopened, or weakened by anything here. The review was
explicit that its findings reject the execution plans and not those decisions,
and the revision keeps that line: every change below is a change to *how* the
accepted direction is executed.

## 2. Independent verification of the Criticals

Performed in the main checkout at `bdfdb30` before revising any plan.

| Finding | Verification performed | Result |
|---|---|---|
| C-1 | Read `research_system/schema_registry.py` in full | **Confirmed.** `__init__` does `json.loads(path.read_text(...))` and stores only the parsed `dict` in `_schemas` (l. 63-73); `validate()` retrieves only that dict (l. 85). Neither raw bytes nor `path` survives construction. P-043's byte-exact digest is unobtainable through this interface. |
| C-2 | Re-read RM-02 Task 2 and its contract test requirement | **Confirmed by construction.** Frontmatter "mirroring its manifest entry" + a test asserting "same ID, version, hash" places a file's own SHA-256 inside the bytes it digests. |
| C-3 | Read `CommandService._build_event` (l. 831-893) and `projection/replay.py` (l. 355-395) | **Confirmed.** `_build_event` handles a closed six-member set and raises `unsupported command type` otherwise; it hard-codes `schema_id` as `ars://core/event/{event_type}`. Replay raises `unknown event schema` for any `schema_id` outside the `ars://core/event/` and `ars://wp6-2/t2/event/` prefixes. An `ars://methods/event/...` family is unreachable through the command path and fatal on replay. |
| C-4 | Re-read RM-04's runner spec against W8 and the repository's gitignored `.env` | **Confirmed.** No isolation, egress control, or non-self-attested approval. `--approved-by` is a caller-typed string. |
| M-8 | Read `research_system/ids.py` and `.research-system/config/id-kind-registry.yaml` | **Confirmed.** Identities are registered-prefix + UUIDv7, not ULID. The catalogue has 26 kinds; none is a brief, method result, or verification request. `artefact: art` **is** registered. |
| M-9 | `grep -n` on `pyproject.toml` | **Confirmed and extended.** `known-first-party` is line 106, `addopts` line 113 — the superseded plan's 96/103 were stale, which is exactly the class of defect M-9 raises. |

## 3. The finding that changes the architecture

C-1 and C-3 look like two problems in two plans. They are one problem in one
place, and locating it is the main substantive result of this revision.

Inspecting the schema tree while verifying C-3 turned up the decisive fact:

- `.research-system/schemas/core/commands/` contains **86 accepted command
  schemas**, and `.research-system/schemas/core/events/` the corresponding
  **86 event schemas**.
- Among them are `RegisterArtefact`, `SetArtefactUseAuthority`,
  `SupersedeArtefact`, `RecordScientificReview`, `RecordStructuralValidation`,
  `RecordArtefactIntegrity`, and `AdoptLateArtefact`.
- `ars://core/command/SetArtefactUseAuthority` carries a payload of exactly
  `{artefact_id, use_authority, subject_sha256, consumer_predicate,
  evidence_refs}`, where `use_authority` is the closed enum
  `candidate | accepted_for_scope | rejected | superseded | restricted`.
- `ars://core/command`'s `target_stream_id` pattern already admits `art_`.
- Every one of these schemas is marked `x-lifecycle: proposed_materialized`,
  and `CommandService._build_event` implements **six** command types.

Three consequences follow, and they restructure the suite:

1. **RM-03 was inventing a mechanism ARS has already accepted.** The review
   offered two remedies — build a reviewed methods event family, or reuse "an
   already accepted generic artefact event". The second is right, and it is
   more concrete than the review could state: the artefact family is not a
   generic fallback to be repurposed, it is the *designed* home for exactly
   this. A brief and an imported result are artefacts. This revision takes that
   path and drops `ars://methods/event/*` entirely.

2. **M-5's firewall already exists in accepted form.** The review is correct
   that four local status enums do not make escalation unrepresentable, because
   nothing stops a consumer citing an `imported` record directly. But
   `SetArtefactUseAuthority` is a W2-native, authority-checked, owner-attributed
   transition binding `subject_sha256` and a `consumer_predicate`. Imported
   material lands at `use_authority: candidate` and can only reach
   `accepted_for_scope` through an attributed command. That is a real firewall
   rather than a schema-spelling one, and it costs no new design.

3. **C-1 and C-3 share a root cause and a fix location.** Both are symptoms of
   the WP6.1 runtime implementing a fraction of its own accepted surface: the
   registry discards schema identity, and 80 of 86 accepted command types are
   unwired. Handoff 26's Defect 3 — 86 generated event schemas demanding
   `command_schema_*` fields no producer emits — is the third symptom of the
   same gap. One main-path work package closes all three.

That work package is **`06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md`**,
new in this revision, and it is WP6.1 main-path work, not RM lane work. Hoisting
it out of RM also discharges M-2, which objected to a Gate-6-critical repair
being hosted inside a lane declared off the critical path. The dependency the RM
lane declares is now on an accepted *capability*, not on a document named RM-01.

## 4. Disposition of every finding

`fixed` = the revised text implements the required change.
`gated` = the required change is an owner decision, hoisted to a master gate.
No finding is dispositioned `rejected` or `deferred without owner`.

### Critical

| # | Disposition | Where | Note |
|---|---|---|---|
| C-1 | **fixed + gated** | new `06h` §Task 1; gate **G-RM-9** | `RegisteredSchema` retains `source_path`, `raw_bytes`, `raw_bytes_sha256`; `validate()` and the producer consume the same instance. The historical-event policy (migrate / grandfather / assert no prior store) is an owner decision, not a Worker judgement call — hence the gate. RM-01's prohibition on editing `schema_registry.py` is lifted only inside `06h`. |
| C-2 | **fixed** | RM-02 §Task 2, §Task 3 | Frontmatter never carries its own hash. External manifest alone records identity, as Git-blob or declared LF-canonical digest. The reviewer's replacement text is adopted close to verbatim, plus the self-hash negative fixture. |
| C-3 | **fixed + gated** | `06h` §Task 3; RM-03 §Architecture; gate **G-RM-10** | Resolved via the accepted artefact family rather than either option the review offered — see §3. G-RM-10 confirms that choice, since it commits the lane to a W2 interface. |
| C-4 | **fixed by removal + gated** | RM-04 §Scope, §Deferred; gate **G-RM-11** | All execution is removed from RM-04. No runner, no `brief verify`, no pilots involving execution. RM-04 keeps the manuscript-review lane (which needs no new code) and non-executing request/result *records*. Execution returns only behind an OS-enforced isolation substrate with W8 records and a threat model, as a separately planned RM-05 that does not exist yet. |

### Major

| # | Disposition | Where | Note |
|---|---|---|---|
| M-1 | **fixed** | RM-00 §3 | R1-3b hoisted as **G-RM-7**. `--allow-candidate` deleted from RM-03 outright rather than gated. G-RM-3 redefined: `accept` or `accept_with_required_changes` **only** once every dispatch-blocking condition has independent closure evidence; any `reject` blocks. |
| M-2 | **fixed** | `06h`; RM-00 §1, §2 | The WP6.1 repair leaves the RM lane. RM lane is RM-01..RM-04, none on the Gate 6 critical path. RM-03 depends on the accepted append/artefact capability, not on a plan name. |
| M-3 | **fixed** | RM-02 §Architecture, §Task 1, §Task 3 | Immutable asset revisions with Git-blob identity; prior identities persisted in an append-only revision history, not inferred from the current manifest; lifecycle transitions carry an external accepted-decision reference; W3 §13.2 permissions and observer-overlay fields added; EOL/checkout-stability tests. |
| M-4 | **fixed** | RM-03 §Task 5 | Denylist replaced by a capability boundary: AST import allowlist for `research_system/methods/**`, no transport or tool interface anywhere in its dependency graph, negative controls for dynamic import, subprocess, socket, generic URL, MCP/tool seam and transitive dependency. Neutral synthetic modules in test data, so the guard no longer contradicts the lane's own naming rule. |
| M-5 | **fixed** | RM-03 §Consumer firewall | Claim narrowed to "schema-local escalation is unrepresentable". End-to-end firewall via accepted `SetArtefactUseAuthority` (§3). Operator theorem verification becomes a separate attributed record bound to the exact citation, not a self-asserted enum member. |
| M-6 | **fixed** | RM-03 §Brief bundle | The brief binds an accepted W3 packet by `context_id`, revision and exact packet hash, and is explicitly defined as a **non-governing rendering** derived from it. No second weakened W3 manifest. Stale, omitted-governing-source, conflict, unsafe-source, superseded-packet and delivery-binding controls added. |
| M-7 | **fixed** | RM-03 §Session record | The WP6.3 assurance-pack allowlist is no longer read. An RM-owned session record captures the operator-selected application family as attributed evidence, with no eligibility gate. The accepted pack returns to being untouched bytes. |
| M-8 | **fixed** | RM-03, RM-04 §Interfaces | ULID wording deleted. Brief, imported result and verification record are all `art_`-prefixed UUIDv7 artefacts under the existing registered kind — no catalogue amendment needed. `verification_context` specified now as `{schema_id, schema_version, verification_result_id, content_hash}`, with a shared RM-03/RM-04 schema-equality test. |
| M-9 | **fixed** | RM-01 §Task B | Dispatch-head collection manifest recorded before any production mutation; the 156 handoff-28 node IDs preserved as a named historical cohort; both cohort and full current universe compared. "Green" claim withdrawn until G-RM-7 resolves R1-3b. Reviewer's confirmation that the R1-3a ordering is correct is retained. |
| M-10 | **fixed** | RM-02 asset 3; RM-03 §De-identification | The sidecar becomes an immutable ARS-side object with ID, revision, hash, subject set, transform version, sensitivity/retention class and authorized consumers. The operator-facing manifest carries only an opaque ID and hash. Exact round-trip, wrong-sidecar, missing-sidecar, stale-revision and unauthorized-access tests added. |
| M-11 | **fixed** | RM-02 R2-4, R2-6 | Theorem retrieval re-cited to §§2.2-2.3 (the §2.5 reference pointed at a heading the pinned document does not contain). "Minimal-instance-first" is demoted from a requirement to an explicitly labelled ARS-added heuristic and removed from the obligation register, since no accepted repository source carries it. |
| M-12 | **fixed** | RM-00 §5.6; RM-03, RM-04 assurance sections | RM-03 and RM-04 classified Output/Provenance **and Paper Claim governance**. RM-02 stays Output/Provenance. Verification records certify execution only and inherit no scientific lane. |

### Minor

| # | Disposition | Note |
|---|---|---|
| m-1 | **fixed** | `P-044 (pending)` → `accepted 2026-07-28; G-RM-3 and plan-specific dependencies remain open` in RM-02/03/04. The historical proposal document is not edited. |
| m-2 | **fixed** | RM-02's stale O-RM-10 reason replaced with the reviewer's text: registry expansion is outside RM-02's accepted file map and needs a reviewed cross-family plan. |
| m-3 | **fixed** | "Full gates" replaced in RM-02/03/04 with the exact command set and its trigger. |

## 5. Coverage and fixture gaps

The review's ten required additions are carried into the plans that own them:
1-2 into `06h` and RM-02, 3 into `06h` (the artefact-family wiring now owns
replay fixtures), 4 into RM-03 Task 5, 5 into RM-03's firewall task, 6 into
RM-03's packet binding, 7 into RM-02/RM-03 sidecar tasks, 9 into the shared
RM-03/RM-04 contract test, 10 into RM-01 Task B. Item 8 (isolation escape
controls) has **no owner in this revision by design** — it is the entry
condition for the deferred RM-05, recorded under G-RM-11.

## 6. New owner gates created by this response

The review named five owner decisions. They become gates in RM-00 §3:

| Gate | Decision | Blocks |
|---|---|---|
| G-RM-7 | Resolve R1-3b: add `receipt-v2` to the closed literal, or confirm the omission is a deliberate unreviewed-schema-addition gate | RM-01 close-out; any "suite green" claim |
| G-RM-8 | Historical-event policy for events predating `command_schema_*`: migrate, grandfather, or assert no prior store exists | `06h` Task 2 |
| G-RM-9 | Approve the `RegisteredSchema` exact-byte registry interface | `06h` Task 1 |
| G-RM-10 | Confirm RM records use the accepted artefact command family rather than a new reviewed event family | `06h` Task 3; RM-03 |
| G-RM-11 | Decide whether isolated verification execution is funded behind a real W8/OS isolation substrate, or stays deferred | RM-05 (unwritten) |

G-RM-8 and G-RM-9 are separated deliberately: the interface shape and the
back-compatibility policy are different questions with different blast radii,
and the review's C-1 required both without merging them.

## 7. What this response does not do

- It does not re-run the suite. RM-01 Task B's collection manifest is still
  owed; the review's read-only count of **1,561 tests** at the subject is
  recorded in RM-01 as the currency signal, not as that manifest.
- It does not implement anything. No production file, schema, contract or test
  changed; this revision is plan text only.
- It does not close G-RM-3. The revised suite — including the new `06h`, which
  no reviewer has yet seen — needs a fresh independent adversarial review under
  a new exact subject. The prior review's brief (handoff 30) is reusable in
  form, but its pinned identities are all superseded.

## 8. Residual risks the review named that survive revision

Carried forward verbatim into RM-00 §8, because none of them is closed by
changing plan text: static controls cannot substitute for process-level
restrictions on executed code; recording an operator session does not evidence
the returned content's truth; imported material still influences humans outside
ARS regardless of the mechanical firewall; Git-blob identity is stable for
tracked text but operator-facing rendered bytes need their own canonicalization;
and a generic artefact event minimizes code only if consumer predicates stay
strict enough that "generic" does not become an authority bypass. The last one
is a direct consequence of the §3 architecture choice and is the thing most
worth attacking in the next review.
