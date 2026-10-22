# G7-C owner acceptance: the Gate 7 definition and P-062, revision 3

**Date:** 2026-10-22
**Decision:** `accepted`. P-062 is accepted, which completes W9's acceptance.
**Owner:** Stephen Dorman
**Authority:** Stephen, in chat, 2026-10-22: "I accept G7-C revision 3 at 2b257da0 (04-plan blob 964e4e10, 03 blob
5b665beb) and G7C-D1 to G7C-D4 as recommended. P-062 is accepted, which completes W9's acceptance. Record it."
**Runtime authority:** none. This acceptance does not open Gate 7. Opening needs Stephen's separate decision against the
opening bar in 04-plan §4, Gate 7. Nothing is dispatched, implemented, imported or transitioned, and no store is
written.

## Exact accepted subject

Commit `2b257da0` on branch `claude/gate7-prep-docs-5202cf` (not yet on main). All paths are under
`docs/plans/agentic-research-system/`.

| File | Accepted content | Blob |
|---|---|---|
| `04-parallel-specification-and-foundation-pilot-plan.md` | Currency note; §4 "Gate 7 — Legacy research integration" | `964e4e1072aa918235a016d698e3f3fa2fbeb2de` |
| `03-decisions-and-open-questions.md` | P-062; the pointer notes in P-026, P-034, A-001 and A-002 | `5b665beb4f756342901a5935a04f1268278e1f62` |
| `implementation/06l-wp6-7-legacy-consolidation-sequencing.md` | Pointer note | `24961ba2c4ff58237912d31488524af5ae562ead` |
| `implementation/06-wp6-gate6-readiness-and-integration-plan.md` | WP6.7 pointer note | `f5e3fbacb899be527b87a7d266f7cc65a93fbe67` |
| `02-design-and-deliverables-roadmap.md` | §2 and §4 pointer notes | `bbb87c715b9b95e5025a62aa106c7b12666ce7e7` |

The old texts P-062 quotes are bound to origin/main `3fa437a1`.

**Status lines recorded after acceptance.** The pointer notes send readers to P-062's status line, so leaving it at
"Proposed" would misstate the record. The commit that adds this file therefore changes exactly three status lines, and
nothing else in the accepted files:

- P-062's `**Status:**` line in 03;
- the Gate 7 `**Status (2026-10-22):**` line in 04-plan;
- the G7-C row of the Gate 7 governing-documents table in 04-plan.

`git diff 2b257da0 <that commit> -- 03-decisions-and-open-questions.md 04-parallel-specification-and-foundation-pilot-plan.md`
shows only those lines. Any other difference from the blobs above is outside this acceptance.

## Review evidence

| Round | Subject | Verdict | Record |
|---|---|---|---|
| Review | revision 1, `1126eb60` | REWORK REQUIRED, narrow (0 Blocking, 4 Major, 11 Minor, 7 Info) | `reviews/g7c-gate7-definition-review-1126eb60-2026-10-22.md` (`e8bcf243`) |
| Re-review | revision 2, `2d567a38` | PASS WITH FINDINGS (0, 0, 6, 6) | `reviews/g7c-gate7-definition-re-review-2d567a38-2026-10-22.md` (`9b89a2e6`) |
| Confirmation | revision 3, `2b257da0` | **PASS** | `reviews/g7c-gate7-definition-confirmation-2b257da0-2026-10-22.md` (`377918c1`) |

The author's reconciliation is in `reviews/g7c-gate7-definition-reconciliation-2026-10-22.md`: §§1–3 cover revision 2
and §4 covers revision 3.

One independent session (g7c-review) did every review round. It was distinct from the author session and from the
G7-A, W9 and D8c sessions. It ran on the same model family as the author, a known limit recorded under P-058.

The reviewer could not read Jira, because the Atlassian connector was not authorized in its session. The KAN criteria it
used are the author's summary of the 2026-10-22 read.

## Owner decisions

| ID | Accepted as |
|---|---|
| G7C-D1 | P-062 is the one operative amendment record. Pointer notes go only in 06l, the 06-wp6 WP6.7 section, roadmap §§2 and 4, the 04-plan currency note, and the 03 entries P-026, P-034, A-001 and A-002. Handoffs 07 and 08 and the W0 manifest get no note. **The record of Stephen's W0-D1 signing cites P-062 C1 as the operative wording of the W0 manifest §14 checklist.** |
| G7C-D2 | The Gate 7 exit is reached when all 38 intake units have an attributed disposition, and each P01 paper root has transitioned or stays `legacy_owned` with a recorded reason. Retiring an APM surface is not an exit condition. After closure, a remaining Step 6 cutover or Step 7 retirement proceeds under 06l as amended and W9 §4.5, each by Stephen's separate decision, without reopening Gate 7. |
| G7C-D3 | Parked compute follows W9 §4.5's successor-compute row. Its legacy rows are proposed as integration-pilot members. Compute waits neither for those rows' acceptance nor for the pilot's thresholds, unless it uses such a row as an input. Such an input needs closed-reference acceptance and adoption first. |
| G7C-D4 | KAN-14, KAN-16, KAN-17, KAN-23 and KAN-25 close on this acceptance. KAN-13 and KAN-26 close with P-062, which completes W9's acceptance. KAN-22 and KAN-60 stay open, and their closure is not decided here. Each change is read back. |

## State after this acceptance

- **P-062:** accepted. Its old→new texts A1 to G6 are now the operative wording. The old texts stay in place as
  written.
- **W9:** the third condition (G7-C's register entry) is met, so all three conditions hold. **W9 draft 0.5, blob
  `ea3a8e4a`, is `accepted`.** This record is its completion record (`reviews/g7b-w9-owner-acceptance-2026-10-22.md`,
  "Conditions for completion").
- **The 06l Step 0 documents are now accepted:** G7-A on 2026-10-22, W9 and G7-C now. Under 06l §6 as amended (B5),
  the next transition is Step 1, Stephen's separate Gate 7 opening decision.
- **Gate 7: NOT OPEN.** Under the capability table it is OWNER-BLOCKED: the documents are accepted and the Gate 6
  closure evidence is on file. Still required are the 06l Step 1 check (opening-bar condition 4) and Stephen's opening
  decision.
- **W0 series:** still `post_terminal_recorded`, not `sealed`. Sealing needs Stephen's W0-D1 signatures, which cite
  C1, and the W0-D2 Stage 2 decision.

## Jira (G7C-D4): pending

The Atlassian connector is not authorized in the author session at this record's time, so none of the G7C-D4 changes
has been made. When it is available, the changes are:

- move KAN-14, KAN-16, KAN-17, KAN-23, KAN-25, KAN-13 and KAN-26 to Done, each with a comment citing this record;
- leave KAN-22 and KAN-60 open, with a status comment;
- read every change back.

## Integration

The accepted bytes reach main only through a PR that Stephen opens and merges after CodeRabbit review. The branch also
carries G7-A, W9 and their records.
