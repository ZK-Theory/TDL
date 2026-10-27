# WP9.2 design note confirmation at `0fa7eb09`: revision 2 and P-077

**Date:** 2026-10-27<br>
**Subject:** `0fa7eb09` on the local branch `pipe/w9-wp9-2-legacy-runtime`. It has three parts:
- `transition/w9/wp9-2-design-note.md`, revision 2;
- `reviews/wp9-2-design-note-reconciliation-2026-10-27.md`;
- P-077 in `03-decisions-and-open-questions.md`.

**Mode:** A narrow confirmation by the reviewer of revision 1 (`reviews/wp9-2-design-note-review-6b5aeee3-2026-10-27.md`,
`bec863d3`, cherry-picked as `8eea8edd`). Two things were checked:
- whether each finding is closed as the reconciliation says;
- whether the new material is free of errors.

Unchanged text was not re-reviewed, and no test suite was re-run. Checks ran as read-only scripts over the catalogue
and schemas, and as reads of the cited code. No store was opened.<br>
**Known limit (P-058):** one model family.

## Verdict

**`pass_with_findings`.** Every finding of the review is closed: B-1, M-1 to M-8 and m-1 to m-12. P-077 matches what
revision 2 does. No new finding is Blocking or Major.

Four new Minor findings, n-1 to n-4, are errors in the new material. Each needs a text fix:
- n-1: §4's row identification is wrong for some E: and W2 Decision rows. It binds no WP9.2 code, but §4 says it fixes
  the layout for later packages.
- n-2: §5.2 and §7.3's retry design contradicts the guard order, and the retry mechanism the runtime copies.
- n-3: the route table's package tags.
- n-4: the genesis grant's actor class.

They can be folded into a revision 3 without another review round, as 06v's c-1 was, if Stephen agrees. n-1 must be
settled before WP9.3's dispatch. n-2 to n-4 must be settled before WP9.2-2's code.

i-1 to i-4 are Info.

## Closure of the review's findings

| Finding | Closed? | Evidence in revision 2 |
|---|---|---|
| B-1 site-1 lifecycle check | **Closed** | §2.1 row 1 skips both `_validate_active_lifecycle_binding` and `apply_event`, and the paragraph after it states what covers the check. §2.2 adds the review's §A2 row. §9's "Negative controls" restore the check and expect "exact lifecycle event provenance mismatch" on a W2-typed event |
| M-1 C3, payload layout, P-069 item 2 | **Closed, with n-1** | C3 is restated in the review's words (§2.3 item 3). §4 adds the payload layout. `replay_legacy` validates every `E:` payload, and §9's "Payload validation" row tests it. The row-identification column has errors (n-1) |
| M-2 `authority.py`, O-4, G4 | **Closed, with n-4** | §3 names both entries. Line refs are correct: `:171-207`; W11's genesis at `:180`; the map at `:208-331`; refusal at `:700-708`. The subject is `CATALOGUE_STREAM_ID`, with a grant-scope test in §9 |
| M-3 `independent_observation_ref`; field sources | **Closed** | §5.3's table covers all 17 required fields. The catalogue's `owner_spec_identity`, `owner_plan_identity` and `schema_source_rows` have exactly the field sets of the envelope's closed `specification_identity`, `plan_identity` and `schema_identities` items, so "verbatim" is admissible (§A1) |
| M-4 reservation | **Closed, with i-3** | §5.3 drops the probability argument. Genesis reserves the three IDs (§7.3), and W9-C25 refuses them, with a test in §9 |
| M-5 P-075 citation; two PRs | **Closed** | §5.3 cites the contract at `7979e85a`, blob `96a63114`. §6.3 gives two PRs. P-077 item 6 records the P-072 item 6 departure |
| M-6 const reading | **Closed** | §6.2 adds the reading as a verification rule, and P-077 item 4 records it |
| M-7 Gate 6 before any lock | **Closed** | §7.2 places the refusal at bind, for every command, before any lock. W9-T20's three cases assert a byte-identical control root. §8 runs the refusal for the CLI too |
| M-8 D-6 exception, boundary | **Closed** | P-077 item 5 names all four paths and the two exceptions |
| m-1 route classes | **Closed, with n-3** | §3: 1 routed and 60 deferred, no "excluded" class, deferred-row events refused |
| m-2 revision row | **Closed** | No binding row; tests use a test registry (§3; P-077 item 1) |
| m-3 guards and payload | **Closed, with n-2** | §5.2 gives the payload field by field, and §7.3 adds guards 2 and 4. LR-001's owner preconditions are L-3 gates. The retry guard (9) is mis-specified (n-2) |
| m-4 test identities, W9-T20 | **Closed** | §9's "Catalogue identities" row and §7.2 |
| m-5 asymmetry | **Closed** | §2.5, §7.3's replay check, and a test in §9 |
| m-6 Gate 6 identity; O-8 pin | **Closed** | §5.1 adds `gate6_store_identity` and keeps the `O8_ACCEPTED` literals |
| m-7 test blobs | **Closed** | §5.3 cites `5a8e1c84` and `4133b75e` at `7979e85a`. Both are correct (review §A4) |
| m-8 citations | **Closed, with i-4** | §6.1 gives both precedents. Revision 2 removes the inaccurate "W11 has no precedent" sentence. The reconciliation says W11's multiset precedent "is given" in §5.3, but it is not there (i-4) |
| m-9 stop rules | **Closed** | §11 adds both, N/A with reasons |
| m-10 probe evidence | **Closed** | §2.2's opening paragraph; §9 "Every negative control asserts its message" |
| m-11 C5 | **Closed** | §2.3 item 5, with the line ref corrected to `routes.py:309-310` |
| m-12 derivation | **Closed** | §5.3 fixes the domain strings, bit layout and `content_hash` semantics. `unix_ts_ms` 1793127308000 is 2026-10-27T18:55:08Z, which is `eab253f6`'s author and committer time (§A1) |

## P-077 against the note

| P-077 item | Note | Match |
|---|---|---|
| 1. Genesis-only binding row; `authority.py` entries; subject `CATALOGUE_STREAM_ID`; revision with no row; predicate over 12 | §3 | Yes. The note also names the actor-class set entry, which item 1 does not mention but item 5's "the item 1 entries" covers (n-4 concerns its value) |
| 2. Three reserved refs, their referents, the `content_hash` semantics, reservation and W9-C25 | §5.3, §7.3, §9 | Yes |
| 3. Hash over the 61 catalogue rows | §5.1, §5.3 | Yes |
| 4. Two PRs; contract lists amended; the envelope cites `96a63114` at `7979e85a`; consts kept with their reading; O-3 after WP9.2-1 | §6.2, §6.3 | Yes |
| 5. D-6 exception; Boundary extended to the contract, the envelope, `authority.py` and `cli.py` | §6.3, header | Yes. Everything else the plan writes is in P-076's Boundary: the binding row in `schema_registry.py`, `research_system/legacy/`, the four sites, and tests (the instance scan, the 06h manifest and test, the ID re-derivation test) |
| 6. P-072 item 6 departure | §6.3 | Yes |

## New findings

### n-1 (Minor, required before WP9.3). §4's "W9 row identified by" column is wrong for some rows

**Claim.** §4 (lines 185-190) sets three identification rules:
- `E:` events: "The command type and the record's `payload_discriminant`, matched to exactly one catalogue row";
- `W2:DecisionProposed` and `W2:DecisionResolved`: "The Decision ID, through the proposal that pre-assigned it";
- the section claims to fix the layout "so that WP9.3 and later packages add bindings and reducers, not a layout"
  (line 192).

**Evidence (§A1, §A2).**
- **No record carries a `payload_discriminant`.** It is a catalogue row field, and none of the 19 W9 schemas has the
  property. The natural substitute, command type plus record kind, is not unique for E:-only transactions:
  - `CreateLegacyPaperRoot` writes `legacy-paper-root` under both LR-035 (`create-legacy-paper-root/ordinary`) and
    LR-038 (`…/recovery`);
  - under `ResolveW9AuthorityDecision`, LR-054 and LR-055 share the record kind `legacy-ownership-transitioned` and
    differ only by direction (`…/to_successor_owned`, `…/successor_to_closed_reference`).
- **Some Decisions have no pre-assigning proposal.** The stage B flow pre-assigns `dec_` in a `ProposeLegacyRecord`
  record (`wp9-1-stage-b-design-note.md:51-54`). Three Decision pairs write no W9 record (catalogue G5), so no such
  proposal exists for them:
  - the integration-pilot outcome, LR-021 and LR-022;
  - the reviewer-eligibility Decision, LR-024 and LR-025;
  - the paper-root recovery Decision, LR-036 and LR-037.

  LR-024 also shares its command and record kind (`legacy-adoption-decision`) with LR-028.
- **A field that works already exists.** The closed W2 `DecisionProposed` and `DecisionResolved` payloads require
  `governing_evidence_refs`, an array of non-empty strings (`decision_proposed.schema.json:54-62`, required at
  `:115`). A `W9:LR-nnn` string there is inert to Discovery, because `_owner_row_id` reads only `W11:OR-` strings
  (`discovery/replay/transactions.py:186-189`). `ReviewRequested`'s `governing_refs` already uses this form in §4.

**Failure scenario.** WP9.3 or WP9.4 implements §4 as written. `replay_legacy` cannot assign a pilot-outcome or
eligibility `DecisionProposed` to a row, or it assigns LR-038's recovery root to LR-035.

**Disposition: fix the text.**
- `W2:DecisionProposed` and `W2:DecisionResolved` are identified by `governing_evidence_refs` containing exactly one
  `W9:LR-nnn`, as `ReviewRequested` uses `governing_refs`.
- `ReviewVerdictRecorded` stays identified through its `review_id`.
- For a transaction of `E:` events only, define the discriminant function on the record's content. For example:
  - `legacy-paper-root` with a predecessor is `…/recovery`;
  - an ownership record's from-mode and to-mode select LR-054 or LR-055.
- A test shows the function is a bijection onto the 61 rows' `payload_discriminant` values.

### n-2 (Minor, required before WP9.2-2). The retry design contradicts the guard order and the receipt path the runtime copies

**Claim.** §5.2 (line 236) makes `requested_genesis_transaction_id` "the request's idempotency anchor. The receipt
maps it to the ledger transaction. A retry with the same anchor and the same envelope hash returns the original
result". §7.3 lists the retry as guard 9 (line 386), after guard 3, "no W9 genesis exists in the replayed legacy
projection".

**Evidence.**
- **Order.** A retry after a successful genesis meets guard 3 first and is refused. It never reaches guard 9.
- **What the runtime copies.** `DiscoveryRuntime`, which §7.1 copies, answers a retry before preparation. It looks up
  the scoped receipt by idempotency scope, command payload hash and authority, and returns it. Failing that, it looks
  up the receipt by command ID (`discovery/runtime.py:484-511`). Guards never see a retry.
- **The anchor distinguishes nothing.**
  - The anchor is a field of `accepted_genesis_payload()`, which every genesis command must equal before binding
    (§7.3, line 375). So every genesis command carries the same anchor.
  - "Another payload under the same anchor" is already refused by that equality check.
  - The envelope hash is fixed by `ACCEPTED` (guard 6), so "only for the same envelope hash" cannot vary.
  - No receipt field holds this anchor.
- **The prefix.** A `txb_` constant uses the ledger's own `event_batch` prefix (`.research-system/config/id-kind-registry.yaml:19`;
  minted at `store/ledger.py:447`). A reader would take it for a ledger transaction ID.

**Failure scenario.** The code follows §7.3. W9-C11-LR-001, the retry test, either fails, or passes only because the
receipt path, which the note never names, answers the retry first.

**Disposition: fix the text.**
- Delete guard 9.
- State that a retry is answered from the scoped receipt and the command-ID receipt before preparation, as Discovery
  does (`discovery/runtime.py:484-511`), and that W9-C11-LR-001 tests that path.
- Describe `requested_genesis_transaction_id` as a fixed nominal value that the closed schema requires. It is not
  compared with the ledger's transaction.
- Either give it a value that cannot be read as a ledger ID, or say why `txb_` is acceptable.

### n-3 (Minor, required before WP9.2-2). The deferred-row tags do not fit the stated package set

**Claim.** §3 (lines 172-173): every deferred row is "tagged with the package that routes it (WP9.3, WP9.4 or WP9.6,
from 06v §5)", and a test pins the partition.

**Evidence.**
- 06v §5 was written before the stage B command set existed (P-071 to P-073), so it maps no LR row to a package. The
  tags are new, and the note does not list them.
- Two rows do not fit the set:
  - LR-002, the inert revision import. Per §3 its reducer and guards are built in WP9.2, and only an accepted catalogue
    revision routes it (P-071 item 4; P-072 item 5).
  - The `RecordAdoptionUseMismatch` row. P-072 item 3 adds it "for WP9.7's guard to request". If WP9.7 routes it,
    WP9.7 adds a command, which D-4's expected list ("WP9.2, WP9.3, WP9.4 and WP9.6", 06v line 566) does not foresee.

**Disposition: fix the text.** List the 60 tags in the note, or in the test that pins them. Allow a tag such as
`catalogue_revision` for LR-002. Say which package routes `RecordAdoptionUseMismatch`; if it is WP9.7, note the D-4
consequence.

### n-4 (Minor, required before WP9.2-2). The genesis grant's actor class is not a valid value

**Claim.** §3 (lines 149-151): "The grant's allowed actor classes then follow the catalogue's LR-001
(`eligible_actor: operator`)."

**Evidence.**
- Scoped grants take actor classes from `_SCOPED_ACTOR_CLASSES = {"human", "agent", "service"}`
  (`research_system/authority.py:170`). "operator" is a W9 actor role, not a class.
- Commands in `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` that are submitted by anyone other than the owner need a grant
  with exactly one actor class (`authority.py:2721-2726`).

**Disposition: fix the text.** Name the genesis grant's single allowed actor class (presumably `human`, for the
operator acting at L-3), and how "operator" maps onto it. Add it to §9's grant-scope test.

## Info

- **i-1.** Checks that passed (§A1):
  - the envelope copies are shape-compatible;
  - the timestamp is correct;
  - `(command_type, payload_discriminant)` is unique over the 61 rows;
  - `E:` kinds number 24 plus genesis and revision;
  - `W9:LR-nnn` in `governing_refs` passes Discovery (review §A2).
- **i-2.** The observation and decision refs hash the same file, the register at `eab253f6`. So the "independent
  observation" is evidenced by a sentence in the owner's decision record.
  - The B2 review's separate derivation, committed at `7979e85a`, rebuilt the catalogue without the verifier. It is
    closer to W11's definition of an "independent observer that executes no W11 command"
    (`design/11-portfolio-and-discovery-lifecycle.md:1572-1574`).
  - Stephen chose the verifier run (P-077 item 2), and no failure follows from it. Recorded, no change.
- **i-3.** The reservation is W9-scoped, but the `obj_`, `rev_` and `dec_` namespaces are store-wide. Discovery's
  identity contract (`discovery/routes.py:290-296`) and the generic review paths do not see the reserved IDs. This is
  acceptable because no consumer dereferences the refs (§5.3 item 6, tested). If that ever changes, the reservation
  must widen.
- **i-4.** The reconciliation's m-8 row says W11's multiset-hash precedent "is given" in §5.3. It is not given anywhere
  in the note. m-8 still closes, because the inaccurate sentence was removed. Correct the row or add the citation
  (`design/11-portfolio-and-discovery-lifecycle.md:1612-1616`).

## Appendix: verification evidence

All reads ran at `0fa7eb09` in this worktree (branch `review/w9-wp9-2-note-confirm`).

### A1. Catalogue and schema checks

Read-only scripts ran under the scratchpad.

- The envelope's `schema_identities` items require exactly `file_length`, `file_sha256`, `git_blob`, `git_commit`,
  `repository_path`, `schema_id` and `schema_version`, closed. The catalogue's `schema_source_rows` have exactly those
  keys.
- `specification_identity` and `plan_identity` require `git_blob`, `raw_bytes`, `raw_sha256`, `repository_path` and
  `reviewed_commit`. The catalogue's `owner_spec_identity` (W9 at `50371fac`, blob `ea3a8e4a`) and
  `owner_plan_identity` (06v at `4999111c`, blob `2b40fae4`) have exactly those keys.
- `datetime.fromtimestamp(1793127308000 / 1000, UTC)` is `2026-10-27T18:55:08+00:00`.
- `(command_type, payload_discriminant)` has no duplicates over the 61 rows.
- No W9 schema has a `payload_discriminant` property.
- Grouping the 18 E:-only rows by `(command_type, record_schema_id)` leaves one ambiguous pair, LR-035 and LR-038
  (`CreateLegacyPaperRoot`, `legacy-paper-root`).
- The W2 rows: LR-021, LR-022, LR-024, LR-025, LR-036 and LR-037 emit only `W2:DecisionProposed` or
  `W2:DecisionResolved`, and their discriminants name the pilot outcome, reviewer eligibility and paper-root recovery.

### A2. Code reads

| Claim tested | Evidence |
|---|---|
| Retry handling | `discovery/runtime.py:474-511`: replay, then the scoped receipt (`load_scoped`), then the command-ID receipt, all before preparation |
| The `txb_` prefix | `.research-system/config/id-kind-registry.yaml:19`, `event_batch: txb` |
| Ledger transaction minting | `store/ledger.py:447`, `new_id("event_batch")` |
| Actor classes | `authority.py:170` |
| W2 Decision payload field | `decision_proposed.schema.json:54-62`: `governing_evidence_refs`, an array of non-empty strings |

## Change log

- Added this file. No other file changed.
