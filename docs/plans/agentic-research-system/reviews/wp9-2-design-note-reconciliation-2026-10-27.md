# WP9.2 design note reconciliation: revision 2 against the review of `6b5aeee3`

**Date:** 2026-10-27<br>
**Author:** the WP9.2 author session<br>
**Review:** `reviews/wp9-2-design-note-review-6b5aeee3-2026-10-27.md` (`bec863d3`, cherry-picked as `8eea8edd`).
Verdict: rework required (narrow). 1 Blocking, 8 Major, 12 Minor, 5 Info.<br>
**Owner decisions:** P-077. Stephen chose the recommended option on A, B, C and D, each as the review amended it.<br>
**Status:** Revision 2 is ready for a narrow confirmation. Nothing is implemented, pushed or merged.

## 1. Files

| File | Change |
|---|---|
| `transition/w9/wp9-2-design-note.md` | Revision 2 |
| `03-decisions-and-open-questions.md` | P-077 |
| this file | New |

## 2. Dispositions

| Finding | Disposition | Note section |
|---|---|---|
| **B-1** site 1 keeps the lifecycle check, which refuses every W9 review and Decision event | Fixed with the review's text. Site 1 skips `_validate_active_lifecycle_binding` and `apply_event` for legacy events, as for Discovery events. What covers the check is stated. A negative control restores the check and expects "exact lifecycle event provenance mismatch" on a W2-typed W9 event | §2.1, §9 |
| **M-1** C3 misstates the code; W2 payloads cannot meet it; no payload layout; P-069 item 2 not carried | Fixed. C3 restated in the review's words. New §4 gives every event kind's type name (W11's `catalogue_event_name` rule), schema, payload and row identification. `replay_legacy` validates every `E:` payload through the registry, with a test | §2.3, §4, §9 |
| **M-2** the genesis grant needs `authority.py` entries; O-4 and G4 | Fixed. The two `authority.py` entries are named, the subject is `CATALOGUE_STREAM_ID`, and a grant-scope test is added. The boundary extension is P-077 item 5 | §3, §9 |
| **M-3** `independent_observation_ref` unaddressed; envelope field sources | Fixed. All three refs are covered (P-077 item 2), and a table gives the source of all 17 envelope fields. The spec and plan identities are the catalogue's | §5.3 |
| **M-4** the collision argument fails for pre-assigned IDs | Fixed. The probability argument is dropped. Genesis reserves the three IDs, and W9-C25 refuses a pre-assigned ID equal to one, with a test | §5.3, §7.3, §9 |
| **M-5** the envelope's contract citation departs from P-075 and creates the three-PR chain | Fixed. The envelope cites `96a63114` at `7979e85a`, per P-075. Two PRs (P-077 item 4). The P-072 item 6 departure is recorded (P-077 item 6) | §5.3, §6 |
| **M-6** `runtime_activation: forbidden` contradicts the package | Fixed as Stephen chose under D: the consts stay, and a verification rule records their reading (P-077 item 4) | §6.2 |
| **M-7** the Gate 6 refusal under the lock writes into the Gate 6 store | Fixed. The refusal runs at bind, before any lock, for every command. W9-T20 asserts the control root is byte-identical | §7.2, §9 |
| **M-8** D-6 exception and boundary extension | Recorded in P-077 item 5 | §6.3 |
| **m-1** route classes | Fixed: 1 routed, 60 deferred, each tagged with its package; no "excluded" class; deferred-row events refused | §3 |
| **m-2** the revision row's rationale | Fixed: no binding row for the revision import (P-077 item 1); its tests use a test registry | §3 |
| **m-3** genesis guards; the full payload | Fixed. Guards for the target stream, the W11 catalogue identity and idempotency added. LR-001's two owner preconditions are L-3 owner gates. The payload is given field by field. `requested_genesis_transaction_id` is the request's idempotency anchor, because the ledger mints transaction IDs (`store/ledger.py:447`) | §5.2, §7.3 |
| **m-4** catalogue test identities; W9-T20's three cases | Fixed | §7.2, §9 |
| **m-5** legacy semantics never validated before a Discovery command | Recorded as an accepted asymmetry, with a test; `replay_legacy` checks for W11 genesis itself | §2.5, §7.3 |
| **m-6** `accepted_w9.py` omits the Gate 6 identity; the O-8 pin's expected side | Fixed. The identity is added. The test keeps its literals and asserts `ACCEPTED` equals them | §5.1 |
| **m-7** the test-blob rationale | Fixed. The envelope cites the test blobs at `7979e85a` (`5a8e1c84`, `4133b75e`), which is what O-8 rested on | §5.3 |
| **m-8** two citations | Fixed: the stage B note §6 is the amendment pattern, and W11's contrary precedent is given (§6.1). The inaccurate "W11 has no precedent" sentence is removed; W11's multiset-hash precedent (`design/11-portfolio-and-discovery-lifecycle.md:1612-1616`) is not cited in the note (corrected here after confirmation i-4) | §6.1 |
| **m-9** two stop rules unchecked | Fixed: both N/A, with reasons | §11 |
| **m-10** probe evidence weaker than stated | Fixed: §2.2 says the probe's payloads and names were not catalogue-shaped. Every negative control in §9 asserts its message | §2.2, §9 |
| **m-11** C5 missing | Fixed: C5 added, with a test over `ordered_events` | §2.3 |
| **m-12** the derivation under-specified | Fixed: domain strings with entry IDs, bit layout, the exact `accepted_at` (`eab253f6`, 2026-10-27T18:55:08Z, `1793127308000` ms), and the `content_hash` semantics | §5.3 |
| i-1 | Recorded. Identities exact | — |
| i-2 | Recorded: the multiset hash adds nothing beyond guard 6; the WP9.2-1 reviewer reconstructs it | §7.3 |
| i-3 | Recorded: C4's list complete | §2.3 |
| i-4 | Recorded: O-3 follows WP9.2-1 | §6.3 |
| i-5 | Recorded in the note's header | header |

## 3. Owner points (P-077)

| Point | Stephen's choice | Applied |
|---|---|---|
| A | Genesis only: one binding row and its `authority.py` entries; the predicate over all 12 | §3 |
| B | Reserved external refs for the observation, review and decision | §5.3 |
| C | The catalogue's 24-field rows: `a8078818…ffde7` | §5.1, §5.3 |
| D | Two PRs; the contract amended with the const reading; the envelope cites `96a63114` | §6 |

## 4. Not done

- No code, no envelope and no contract amendment: those are WP9.2-1 and WP9.2-2.
- O-3 is not decided; it follows WP9.2-1's merge.
- Nothing is pushed.

## 5. Revision 3: the confirmation's findings

The confirmation of revision 2 (`reviews/wp9-2-design-note-confirmation-0fa7eb09-2026-10-27.md`, `f64d4e9c`,
cherry-picked as `47b049ba`) passed with findings: every original finding closed, P-077 matching the note, and four new
Minor findings. Stephen asked for them to be folded into revision 3 with no further review round.

| Finding | Disposition | Note section |
|---|---|---|
| **n-1** §4's row identification is wrong for some rows | Fixed. W2 Decision events are identified by `governing_evidence_refs` holding one `W9:LR-nnn`. A transaction with a W2 event takes that event's row, which separates LR-054/LR-055 and LR-024/LR-028. The 18 `E:`-only rows get an explicit discriminant function, with LR-035/LR-038 split on `recovery`. A bijection test is added | §4, §9 |
| **n-2** the retry design contradicts the guard order and the receipt path | Fixed. Retries are answered from the scoped receipt and the command-ID receipt before preparation, as `DiscoveryRuntime` does (`discovery/runtime.py:474-511`); guard 9 is deleted; W9-C11-LR-001 tests the receipt path. `requested_genesis_transaction_id` is the nominal string `w9-genesis-request-v1`, not compared with the ledger and not `txb_`-prefixed | §5.2, §7.3, §9 |
| **n-3** the deferred-row tags | Fixed. A tag table by record kind and Decision, with `catalogue_revision` for LR-002 and `WP9.7` for the use-mismatch row and the eligibility and pilot-outcome Decisions; the per-row list lives in the route table, pinned by a test. WP9.7 therefore also carries a D-4 re-acceptance | §3 |
| **n-4** the genesis grant's actor class | Fixed. The one class is `human`; LR-001's `operator` is a role that maps to it. The grant-scope test covers it | §3, §9 |
| i-1 | Recorded | — |
| i-2 | Recorded. Stephen chose the verifier run (P-077 item 2); no change | — |
| i-3 | Recorded. The reservation is W9-scoped; it must widen if a consumer ever dereferences the refs | — |
| i-4 | Fixed in this file's m-8 row | §2 |

The `WP9.4` and `WP9.6` tags for the paper-root, source-inventory, mapping and ownership rows are the author's reading of
06v §5's package scopes, which name no rows. The package that takes a row may move it, by changing the tag table.
