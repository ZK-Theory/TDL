# Gate 7+ intake: deferred and carried items

| Field | Value |
|---|---|
| Date | 2026-11-08 |
| Status | Running list. Created on Stephen's approval of the 2026-11-03 system review packet (PR #412, Group H, option (a)), 2026-11-08 |
| Purpose | The one place where a Gate 7 planning pass, or the W9 package a row names, finds work that a system review deferred to it |
| Check | `uv run python tools/observation_log_lint.py <log> --intake <this file>` reports any DEFERRED observation sent to a gate's intake that has no row here. The option is added by PR #417, so the check runs once #417 is on `main`; the weekly system review runs it in step 1 from then on |

Before this list existed, four approved deferrals were recorded only in the observation log, which planning sessions do
not read, and Gate 7 opened without them (observation `2026-11-03-gate7-intake-deferrals-have-no-landing-record`).

## How to use it

- **A Gate 7 planning pass** reads §1 and gives each row a disposition: planned into a numbered task, deferred again to a
  named later gate, or declined by Stephen. Write the disposition and its decision or commit in the row's last column.
  Never delete a row.
- **The author of a W9 package** reads §2 for rows naming that package and enters each in the package's obligation
  register (`writing-plans-extras`, Forward-Obligation Scan step 7).
- **A system review** that defers a limb to Gate 7+ intake adds its row here in the same campaign.

## 1. Deferred to Gate 7+ intake

| Observation | Limb | Deferred | Owning artefact | Disposition |
|---|---|---|---|---|
| `2026-08-12-file-map-frozen-since-wp1` | Limb 1: when later work packages supersede a plan's file map, the superseding plan restates or amends the map. It goes with the planning-template work | 2026-10-17, system review Group H | the ARS planning template; `writing-plans-extras` | open |
| `2026-08-22-retired-procedure-kept-live-imperatives` | The enumerable-contract planning rule: a plan that claims an exact registry, configuration or discriminated result enumerates the complete catalogue, the required and prohibited fields, and the completeness negatives before the slice opens. The gate limb is on `main` (#334) | 2026-10-17, system review Group H | ARS planning review | open |
| `2026-10-22-superseded-md-lags-reclassifying-results` | A supersession-currency contract: a `[RESULT]` or `[DECISION]` commit that names a file listed in a `SUPERSEDED.md` changes that `SUPERSEDED.md` in the same PR, or carries a "no supersession change" marker. Negative control: a fixture commit naming a listed file without a hunk fails. The instance is fixed (#401) | 2026-10-27, system review Group E1 | `contracts/`, via `schema-contract-design`. W9 imports read `SUPERSEDED.md` (W0 manifest §8.1) | open |
| `2026-10-22-gate-definition-restates-owning-matrix-narrowly` | Widen `tools/check_retired_imperatives.py` beyond `implementation/` to 03, `04-plan` and the roadmap, or record why not. Control: a fixture retired imperative in `04-plan` is flagged | 2026-10-27, system review Group C, to the next Gate 7 planning pass | `tools/check_retired_imperatives.py` | open |
| `2026-10-27-note-departed-from-a-carried-owner-item-silently` | The carried-obligation lint: extract each register sentence that names a package ("Carried to WP9.2", "WP9.2 validates") and require that package's design note to cite it with a keep or depart disposition. Until it exists, `writing-plans-extras` step 7 has the grep | 2026-11-08, system review 2026-11-03 Group C3 | a new lint over `03-decisions-and-open-questions.md` | open |

## 2. Carried to a named W9 package

| Observation | Item | Package | Control | Disposition |
|---|---|---|---|---|
| `2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it` | A contract test that holds W9 §12.3's fixture-to-row assignments as an owned table and checks that each catalogue row's `pilot_promotion_fixtures` equals it. Put it in a new test file: the O-8 acceptance envelope binds `test_w9_expected_catalogue.py` | WP9.3-2 (LR-016 to LR-020) | the three-fixture reading of LR-020 fails | open |
| `2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema` | A precondition-to-field table: every row precondition that says a payload lists, carries or names a datum maps to a field of the row's record schema or of one of its `ordered_events`. Also a new test file, for the same reason | WP9.3-2 | LR-016 as accepted at `7979e85a` fails | open |
| `2026-10-28-shared-location-named-but-never-defined` | A "W9 paths" table listing the evidence area (P-081) and every other location that two packages share. 06v is accepted at revision 4, so this is a dated addendum, not an edit of the accepted text | 06v, after #411 merges | — | done: `implementation/06v-addendum-2026-11-10-w9-paths.md` (system review 2026-11-10, Group C2). Three file names stay open there, each owned by a named package |
