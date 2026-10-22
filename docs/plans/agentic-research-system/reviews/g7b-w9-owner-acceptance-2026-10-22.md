# G7-B owner acceptance: W9 migration, compatibility and pilot specification, draft 0.5

**Date:** 2026-10-22
**Decision:** `accepted_conditionally`. The acceptance becomes complete when the three conditions below are met;
until then W9 governs nothing.
**Owner:** Stephen Dorman
**Authority:** Stephen, in chat, 2026-10-22: "I accept W9 draft 0.5 at 481dcca7 (blob ea3a8e4a) and W9-D1 to W9-D14
as recommended. Acceptance is conditional on the evidence-register addendum (D8a), the non-author Discovery
observation (D8c) and G7-C's register entry. Record it and set up the D8a and D8c work."
**Runtime authority:** none. W9 authorizes no implementation, import, transition, dispatch or store write.

## Exact accepted subject

| Identity | Value |
|---|---|
| File | `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md` |
| Revision | draft 0.5 (specification version 0.5) |
| Commit | `481dcca7` on branch `claude/gate7-prep-docs-5202cf` (not yet on main) |
| Blob | `ea3a8e4a5e89a599c255fd881c2a040db4f2d3c5` |
| Verified against | origin/main `3fa437a1` |

The file's frontmatter status `review_pending` is the reviewed snapshot's state. This record supplies its effective
status without rewriting the reviewed bytes. If the blob ever differs from `ea3a8e4a`, this acceptance does not
cover the difference.

## Review evidence

| Round | Subject | Verdict | Record |
|---|---|---|---|
| Review | draft 0.1, `97f71c19` | REWORK REQUIRED (1 Blocking, 13 Major, 12 Minor, 6 Info) | `reviews/g7b-w9-draft-0-1-review-97f71c19-2026-10-22.md` (`b7fd4415`) |
| Re-review | draft 0.2, `34ac441e` | REWORK REQUIRED, narrow (0, 6, 11, 4) | `reviews/g7b-w9-draft-0-2-re-review-34ac441e-2026-10-22.md` (`6ac30e2e`) |
| Re-check | draft 0.3, `e5432e44` | REWORK REQUIRED, narrow (0, 2, 10, 4) | `reviews/g7b-w9-draft-0-3-re-check-e5432e44-2026-10-22.md` (`b51d3728`) |
| Re-check | draft 0.4, `250408c6` | PASS WITH FINDINGS (0, 0, 2, 4) | `reviews/g7b-w9-draft-0-4-re-check-250408c6-2026-10-22.md` (`db294c9e`) |
| Confirmation | draft 0.5, `481dcca7` | **PASS** | `reviews/g7b-w9-draft-0-5-confirmation-481dcca7-2026-10-22.md` (`8581d677`) |

Author reconciliation: `reviews/g7b-w9-reconciliation-2026-10-22.md` (§§1–3 for draft 0.2, §6 for 0.3, §7 for 0.4,
§8 for 0.5). Every round came from one independent session (g7b-w9-review), distinct from the author and from the
G7-A reviewer, and on the same model family as the author (a P-058 known limit). Stephen was offered a final pass by a
different session and accepted without it.

## Owner decisions

Stephen's choices made during drafting:

- **Route (ii):** a W9-owned closed schema family reusing W11's observation-inventory-mapping-transition pattern,
  with a lighter closed-reference path.
- **N-1:** the full-path target is a W9-owned `legacy-paper-root` record that a later W11 dossier admission
  references.

W9-D1 to W9-D14, accepted as recommended in §16.1 of the accepted bytes:

| ID | Accepted as |
|---|---|
| W9-D1 | Parked compute runs as new successor Tasks with new pre-registrations; inputs regenerated or hash-referenced; restricted bytes never in the store; the G7-A §17 addendum accepted before dispatch |
| W9-D2 | Gate 7 dispatch is operator-mediated under P-042; no provider reactivation |
| W9-D3 | P-029's two-family rule survives P-042 and applies at dispatch over P-005's full R3 set, with eligibility checked before dispatch by someone other than the producer and the second-family session |
| W9-D4 | Rollback is one way; recovery is successor-side, including the paper recovery route; G7-C amends 06l Steps 5–7 |
| W9-D5 | Ruleset 20822054 kept, its bypass list read before each batch; a post-merge detector with the `results/` prefix rule and rule-suite reads; baseline-backed vault and `CONVENTIONS.md` checks; each detector watched to fail before the first registration |
| W9-D6 | Papers transition whole and last, as `legacy-paper-root` records; citation status in a separate relation over an independently frozen cited-family set |
| W9-D7 | Prose waits for Gate 9's manuscript-review capability |
| W9-D8a | A dated W9 addendum to `01-current-system-evidence.md` before acceptance (**condition 1**) |
| W9-D8b | `.research-system/projections/legacy/`, registered under the W9 family |
| W9-D8c | A non-author, read-only, dated observation of the vault Discovery backlog before acceptance (**condition 2**) |
| W9-D9 | The shared-writer exception, with the object-then-date legacy set (Stephen accepts the classified list when the baseline is taken), the Git-anchored log export, the `4b143c92` `CONVENTIONS.md` baseline, the insertion-only rule and the detectors |
| W9-D10 | The W9 catalogue enters a store the implementation plan names and Stephen decides, never the Gate 6 store, through a separately accepted bootstrap contract and a scoped grant, after W11's genesis in a new store, with P-059 re-acceptance |
| W9-D11 | `AdoptLegacyAuthority`: Stephen only, use-scoped, revalidating |
| W9-D12a | The integration-pilot rubric; wider adoption authorized separately after the pilot |
| W9-D12b | S-016 re-specified under P-042 by a dated W6 addendum; F-024 excluded for P01 only |
| W9-D13 | P04 and other legacy families stay `legacy_owned`, unregistered, guarded by the `results/` prefix rule |
| W9-D14 | The `shared_enforcement_surface` split with reviewer-derived affected results; `results/ars/` registered as the successor results root |

## Conditions for completion

| # | Condition | State at this record |
|---|---|---|
| 1 | **D8a:** the dated W9 addendum to `01-current-system-evidence.md` | Added as §9 of that file in the same commit as this record; complete when this commit is on the reviewed branch |
| 2 | **D8c:** a non-author, read-only, dated observation of `00-Meta/Discovery/_backlog.md`, independently reviewed and accepted by Stephen (W9 §15) | Not done. A separate session is being set up to take it |
| 3 | **G7-C's register entry** carrying W9 §16.2's old→new texts and the G7-A amendments | Not done. G7-C is not drafted |

When all three hold, a short completion note is added to this file's directory (or this record is superseded by a
completion record) and the acceptance becomes `accepted`.

## Carried, not decided here

- The W9 implementation plan: the schemas, catalogue, bootstrap contract, genesis, detectors and commands, with the
  re-check's Info I-c (a mechanical citation extractor or a second derivation for W9-T17).
- A dated W6 addendum for S-016 (W9-D12b).
- G7-C: the 06l, P-026, P-034, 04-plan and roadmap amendments, and W0-D4's condition.

## Jira

KAN-13 (W9) stays In Progress until the conditions hold. KAN-26 (the boundary matrix) is met by W9 §4.5 and closes
with KAN-13.
