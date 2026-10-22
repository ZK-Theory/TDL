---
document: G7-B reconciliation of the independent review of W9 draft 0.1
date: 2026-10-22
review: reviews/g7b-w9-draft-0-1-review-97f71c19-2026-10-22.md (committed b7fd4415)
review_subject: design/09-migration-compatibility-and-pilot.md draft 0.1 at 97f71c19
reconciled_subject: the same file, draft 0.2 (the commit that adds this record)
author: the Gate 7 prep session (the W9 author; not the reviewer)
status: author reconciliation; not acceptance
---

# G7-B reconciliation: W9 draft 0.2

Stephen directed this reconciliation on 2026-10-22, choosing route (ii) for B-1: "a W9-owned closed schema family
reusing W11's observation-inventory-mapping-transition pattern, with a lighter closed_reference observation path.
Write W9 revision 0.2 for B-1 and the other findings, putting the remaining owner decisions to me as
recommendations."

No finding is rejected. Section references are to draft 0.2 unless marked 0.1.

## 1. Blocking and Major

| Finding | Disposition | Where in 0.2 |
|---|---|---|
| **B-1** W11 reuse infeasible | **Fixed by route (ii).** W11 recorded as accepted (blob `f90729d0`; KAN-19; KAN-84 catalogue; genesis import), with the stranded record noted. A W9-owned closed family under `ars://legacy/` copies W11's DAG pattern with its own registration root (repository, untracked and vault files), selectors (JSON-pointer membership tables), target kinds and catalogue with its own one-time genesis (W9-D10). "Extends its `role` enum" deleted. Each §8.4 row names its target. | §1 items 3–5; §2.1; §5; §6.2; §8.4; W9-D10 |
| **M-1** adoption undefined | **Fixed.** `AdoptLegacyAuthority`: use-scoped, Stephen-only (P-005), W5 admissibility consequence, revalidation on re-observation. A discharge relation lets a successor result close an A-001 item under W0-D1. A1–A4 carried as `open_review_finding` qualifiers. | §1 item 1; §5.2; §6.4; §9; W9-D11 |
| **M-2** unsigned W0 classes | **Fixed.** Observations carry classes only from the signed W0 revision; Stephen's signature on all eight §14 items precedes any closed-reference acceptance. | §1 item 6; §4.5; §5.2; §8.5 item 2 |
| **M-3** wholesale globs; writer list incomplete | **Fixed.** Exact-file registration only; #168, #169, #334 added to §4.1; successor results root `results/ars/` named; `contracts/` split into legacy-bound, shared enforcement surface and ARS-owned. | §3.1; §4.1; §4.3; W9-D14 |
| **M-4** writer class (b) loophole; client-side guard | **Fixed.** Class (b) needs Stephen's note naming files and old/new blobs plus an independent semantic-equivalence review; any blob change re-triggers observation. Detectors: server-side branch protection, a post-merge first-parent detector with `5df0c001`/`811d5a2b` replays as negative controls, and a vault detector. | §4.2; §4.4; W9-D5; W9-T7 |
| **M-5** shared-writer files | **Fixed as an owner decision.** Bounded exception for the Computational-Log and `CONVENTIONS.md`: heading-anchored entry-hash selector, prepend-only rule, entry-hash window, vault detector; alternative of frozen exports. `CONVENTIONS.md` registered at its repository path only. | §7.3; W9-D9 |
| **M-6** uncommitted sources; bus | **Fixed.** Source identity kinds include untracked and vault files (handle-bound SHA-256 plus frozen copy, "no Git identity" as a non-inference). The bus is not imported, with a recorded closure inventory. The bus and Tracker deprecation path is written as seven steps. | §5.2; §8.4; §13.3 |
| **M-7** parked-compute contradictions; restricted inputs | **Fixed.** New pre-registration citing the legacy one, resolved by Stephen; inputs regenerated from committed scripts or hash-referenced; restricted bytes never in the ARS store; outputs under `results/ars/`; the G7-A §17 trigger as a dispatch precondition. | §10; W9-D1; W9-T10; W9-T11 |
| **M-8** post-commit rollback | **Fixed.** Paper recovery by a new successor paper object or a declared manual-operation mode; `legacy-record-supersession` for erroneous records; "tested rollback handle" replaced; 06l Steps 5–7 amendments listed for G7-C. | §5.2; §13.1; §13.2; §16.2; W9-D4 |
| **M-9** pilot rubric missing | **Fixed.** An integration-pilot rubric (closed-reference items only, bounded, supersedable, papers last) and a separate Phase F wider-adoption authorization; old→new text for roadmap §4 and 04-plan §6. | §14.2; §16.2; W9-D12a |
| **M-10** unmeasurable metrics | **Fixed.** Recall baseline compiled and hashed by an independent reviewer before the batch; one tokenizer (W3 reference, P-028); cost added; thresholds filed as a hashed dated pre-registration before the first acceptance; a missed threshold stops further batches. | §14.3; W9-T16 |
| **M-11** fixture set not closed | **Fixed.** The set is derived from the 05-plan §4.4 deferred list, 06a and 06b; every member assigned or excluded (F-024 proposed excluded; S-016 re-specified under P-042); applicability proposed by the reviewer and fixed by Stephen. | §12.3; W9-D12b |
| **M-12** W9-D3 scope and timing | **Fixed as re-framed.** The question is whether P-029's family rule survives P-042; if it does, it applies at dispatch over P-005's full R3 set; if not, a per-item recorded known limit. | §11.2; W9-D3; W9-T12 |
| **M-13** Discovery inventory with no rows | **Fixed, option (b) with (a) proposed.** §15 says it is not the inventory; W9-D8c proposes a non-author, read-only, dated observation of `_backlog.md` before W9's acceptance; until accepted, W0-D4's condition stays open. P04's mode is W9-D13. | §15; W9-D8c; W9-D13 |

## 2. Minor and Info

| Finding | Disposition | Where |
|---|---|---|
| m-1 W9-A2 "only" | Fixed: no handler for OR-122 to OR-139; schemas materialized and accepted | §2.1 W9-A1 |
| m-2 families flattened | Fixed: LM-sensitivity, T1.2g/T1.7 qualified, dedup files added; a "qualified" treatment | §6.1; §6.2 |
| m-3 precedence drift | Fixed: §8.4 quoted verbatim; resolve, not block; `stale_projection`; lines 69–71 | §6.3; W9-T4 |
| m-4 instance-only correction | Fixed: general `corrected_by` relation; values from the canonical source | §6.4; W9-T13 |
| m-5 KAN-13 gaps | Fixed: W3 and W7 in the authority header; W9-A2 states W7's role; "additive 06i" resolved to 06l | Header; §2.1; §16.2 |
| m-6 KAN-26 gaps | Fixed: migration and path mutation prohibited explicitly; D-1's supersession of the pilot-promotion bar recorded | §4.5 |
| m-7 stop list | Fixed: the three 04-plan §7 rules added | §13.4 |
| m-8 §13.1 "Met" overstated | Fixed: "Met with P-058 known limits", each named; same-disk caveat | §14.1 |
| m-9 P-026 "Preserved" | Fixed: "Amended through G7-C", with old→new texts; acceptance conditional on G7-C | §2.1; §16.2; §18 |
| m-10 "Gate 6 Manager" roles | Fixed: mapped to migration analyst, independent observer and reviewer, Stephen | §8.6 |
| m-11 other legacy papers | Fixed as W9-D13 | §3.2 |
| m-12 W9-D8 bundled | Fixed: split into D8a, D8b, D8c | §16.1 |
| I-1 branch-only subjects | Noted; no change | — |
| I-2 decisions verified | Noted | — |
| I-3 fixture IDs | Noted; membership fixed under M-11 | §12.3 |
| I-4 H10 | Noted | §6.4 |
| I-5 stranded W11 record | **Acted on outside W9:** Stephen started a separate session (2026-10-22) to land `cee20209`'s record on main | §2.1 |
| I-6 R4 and frozen representations | Adopted: §3.3 routes any R4 use of a P01 representation through §9 and §10 | §3.3 |

## 3. Owner decisions after reconciliation

W9-D1 to W9-D7 are revised (W9-D3 re-framed; W9-D4 extended to 06l Steps 5–7; W9-D5 with server-side and vault
detectors). W9-D8 is split into D8a to D8c. New: W9-D9 (shared-writer exception), W9-D10 (W9 catalogue and genesis),
W9-D11 (adoption), W9-D12a/b (pilot rubric and Phase F; S-016 and F-024), W9-D13 (P04), W9-D14 (shared enforcement
surfaces and the successor results root). Route (ii) itself is decided (Stephen, 2026-10-22).

## 4. What the focused re-review should check

1. B-1: that the W9 family (§5) is coherent, does not touch W11's accepted schemas, and that every §8.4 row has a
   target that its schema can hold.
2. M-1, M-2, M-7, M-8: that adoption, signed classes, the parked-compute route and paper recovery close the failures
   the review described, without a new route for legacy evidence to reach successor use ungated.
3. M-4, M-5: that the detectors and the shared-writer exception would catch the observed cases.
4. M-9 to M-11: that the rubric, metrics and fixture set are closed and measurable.
5. Any new claim or identity in draft 0.2.

## 5. Author's limits

- The schema family is specified at field level, not as JSON Schema; its exact shapes are the implementation plan's.
- §12.3's assignments are the author's proposal; Stephen fixes them per batch.
- Same model family as the reviewer (a P-058 known limit).
