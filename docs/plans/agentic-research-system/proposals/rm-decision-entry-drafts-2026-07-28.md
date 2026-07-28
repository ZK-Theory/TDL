# Draft decision entries: P-043 and P-044 (Research Methods lane)

**Created:** 2026-07-28
**Status:** EXECUTED — Stephen accepted the proposal on 2026-07-28 and both entries
were added to `../03-decisions-and-open-questions.md` on his instruction the same day.
Retained as drafting provenance; the register is the authority.
The in-conversation acceptances of D-1/D-2/D-3 on 2026-07-28 are the basis;
these drafts convert them into durable register entries per the folder's
change discipline ("Planning decisions are recorded in
03-decisions-and-open-questions.md before being assumed by a design
specification").

---

## Proposed entry: P-043 — WP6.1 event-schema currency: producer emits

**Date:** 2026-07-28<br>
**Status:** PROPOSED (drafted by agent; awaiting Stephen's register entry)<br>
**Context:** Handoff 26 established, reproduced on a detached worktree at
`449b0d00`, that 86 generated event schemas under
`.research-system/schemas/core/events/` (88 files repo-wide) require
`command_schema_id`, `command_schema_version`, and `command_schema_sha256`,
while no production code emits them; `CommandService.submit` →
`ledger.append` → `SchemaRegistry.validate` therefore fails on `main`. The
contracts suite stayed green because it validates the WP6.1 materialization,
not the runtime append path.<br>
**Decision:** The runtime producer rises to meet the accepted schemas. The
command-submission path derives all three fields at submit time from the
registered command schema actually used to validate the submitted command.
The generated event schemas are not relaxed. Caller-supplied values for these
fields are never authoritative.<br>
**Rationale:** The fields exist to bind events to exact command-schema
identities — the WP6.1 binding intent. Relaxing an owner-reviewed generated
schema family to fit an incomplete producer would weaken an accepted
materialization to accommodate a defect.<br>
**Execution:** RM-01 Task A
(`implementation/rm-01-unblock-and-suite-recovery-plan.md`); acceptance is
recorded against WP6.1 currency, not the RM lane.<br>
**Boundary:** No schema edit under `schemas/core/events/`; no change to WP6.3
accepted bytes; no invariant drift in the P0 eval corpus.

---

## Proposed entry: P-044 — Research Methods lane (RM)

**Date:** 2026-07-28<br>
**Status:** PROPOSED (drafted by agent; awaiting Stephen's register entry)<br>
**Relationship to P-042:** P-042's boundary clause authorizes plan and
dependency correction only; this entry supplies the new owner decision P-042
requires before implementation of operator-mediated tooling.<br>
**Decision:** Create an independent Research Methods (RM) lane — parallel to
the WP6.1+WP6.3 → WP6.4 → Gate 6 path and never on its critical path — that
implements, inside the P-042 owner-operated-session regime:

1. a provider-neutral Research Methods Pack (versioned W3 procedural-memory
   assets distilled from Woodruff et al., *Accelerating Scientific Research
   with Gemini*, cited as evidence lineage only);
2. `ars brief export` / `ars brief import` — fail-closed compilation and
   recording of bounded operator briefs, and typed append-only landing of
   operator-returned results strictly below result acceptance and claim
   promotion;
3. a bounded local verification-execution lane (`ars brief verify`) and a
   manuscript-review lane feeding, never performing, W5 review.

Naming is provider-neutral throughout (accepted D-3). The lane runs as
plan-per-package with independent adversarial review before each dispatch
(governing suite: `implementation/rm-00-research-methods-lane-master-plan.md`
and RM-01..RM-04).<br>
**Owner gates preserved:** the G-RM-1..G-RM-6 checklist in rm-00 §3; W5 §19.3
claim promotion remains exclusively Stephen's P-005 authority; pack-asset
acceptance is an explicit owner action (G-RM-4).<br>
**Boundary:** This decision authorizes the RM plan suite's review and, upon
per-plan review acceptance (G-RM-3), bounded implementation of RM-01..RM-04
only. It does not authorize provider invocation, credential access, any Gate
6 artifact, W11/WP6.5 interaction, migration, pilot-paper initialization,
eligibility transition, result acceptance, or claim. Reactivation of any
direct-provider transport still requires a separate future decision.<br>
**Evidence:** `proposals/research-methods-integration-plan-2026-07-28.md`
(analysis and adversarial review of the two external deep-research reports);
`implementation/rm-00-research-methods-lane-master-plan.md` (obligation
register and forward-obligation scan).
