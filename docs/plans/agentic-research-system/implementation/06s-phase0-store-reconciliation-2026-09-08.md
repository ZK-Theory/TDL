# 06s Phase 0 STORE observation reconciliation — 2026-09-08

Scope: the six named historical observations, the 2026-09-04 D2 observation,
and the Phase 0 fixture observation. This is a verification record, not a new
STORE hardening slice.

| Observation | Verdict | Evidence | Disposition |
|---|---|---|---|
| 01M20GX6Y0HAFAAFW8240X4B0W | ALREADY-FIXED | `test_current_binding.py` helpers now sort numeric batch filename prefixes; two opposite-month controls pass. Old helpers were independently reproduced selecting the wrong batch/order. The repaired Phase 0 packet is 65 passed in 960.11s. | Fixed in PR #271 commit 270012f. |
| 01M044JXXJMJVW6Q24BX50ZANE | ALREADY-FIXED | 06s §4.5 and P-050 require a separate `ProjectUseDecision`, explicitly retaining the historical PARK/no-claim boundary and plain-English research-use disposition. | Closed by existing P-050/06s contract; no production change. |
| 01M044JXYSPP0VXH15TEZVCNA | SUPERSEDED-BY-D5 | This is a deployment-closure freshness/process defect. 06s D5 governs inherited merged STORE bytes and Phase 0 records exact current Git/test evidence; no current STORE behavior is changed by the observation. | Remains an open workflow observation; no Phase 0 code claim. |
| 01M04655YN2KAHRV16BTE8YAS0 | ALREADY-FIXED | Current 06s, P-051–P-056 and the active decision register record the refreshed STORE baseline, current route, remaining phases and Gate 7 separation. | Closed by current plan/decision records; no code change. |
| 01M061T8WEGQNSYKXDTHTYDT83 | SUPERSEDED-BY-D5 | D1–D6 and the bounded brief require ordered effects, explicit boundaries and direct negative evidence before later phases. The Phase 0 packet found no merged STORE failure attributable to this historical construction concern. | No production change; process control remains in 06s. |
| 01M0641MDF9GV509T49SWED57V | STILL-DEFECTIVE | Existing tests cover rollback and redirected paths, but no direct current-main test was found that proves an empty identity directory is classified as unpublished residue and then permits exact retry. | Left OPEN; requires a separately bounded direct test/repair if the owner dispatches it. |
| 01M06KPH7CQRRPFGGXW67HT0Y4 | STILL-DEFECTIVE | Existing STORE tests cover redirected objects and markers in adjacent seams, but no direct current-main negative control was found that redirects the recovery marker before presence/bytes validation. | Left OPEN; requires a separately bounded direct test/repair if the owner dispatches it. |
| 01M1Q8Z3XCVJEBTPMC87W5KFPB | ALREADY-FIXED | `SpecOperatorConfig` on current main accepts only actor/session/grant IDs plus the fixed schema fields; role/owner fields are absent and extra fields reject. 06s D2 now explicitly retains inherited authority checks and adds no role field. | Closed by 06s D2 correction in PR #271. |

The original 11 failures were not legacy bypass candidates. After the fixture
repair, all eleven intended provenance/replay checks passed. No production STORE
bytes, historical schemas, or Gate 7 requirements were changed.
