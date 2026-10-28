# WP9.2-1: the bootstrap contract amendment and the W9 acceptance envelope

**Date:** 2026-10-28<br>
**Status:** Revision 2. It reconciles the review `reviews/wp9-2-1-review-7e119810-2026-10-28.md` (accept with required
changes; §6). Not merged and not accepted.<br>
**Package:** 06v WP9.2, first of its two PRs (P-077 item 4). The design note is
`transition/w9/wp9-2-design-note.md`, revision 3, confirmed and merged as `779fc8bc` (PR #405).<br>
**Authority:** P-076, with P-077 items 4 to 6. WP9.2-1 is data and tests: no runtime code, nothing under
`research_system/`, and no store writes.<br>
**Base:** `main` at `779fc8bc`.

## 1. The contract amendment (design note §6.2)

`.research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml`, free text only:
- **`verification_rules`.**
  - "no acceptance instance is materialized in the repository" is dropped from the catalogue rule;
  - "no runtime production Python is changed" is dropped;
  - "the only W9 acceptance envelope instance is .research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json"
    is added;
  - "runtime_activation and materialization_status govern the ars://legacy/ schemas' runtime bindings only; the W9
    runtime is WP9.2's (P-077)" is added. That records the reading of the consts (review M-6).
- **`forbidden`.**
  - "runtime handlers, ledger append, reducers, or projectors", "catalogue acceptance envelope instance" and "W9
    genesis import" are dropped;
  - "any W9 acceptance envelope instance other than .research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json"
    is added;
  - "W9 genesis or any live operation L-0 to L-5 on a store other than a test-created scratch store, and any write to a
    legacy file, without the owner decision that authorizes it (P-076)" is added (review m-2, Stephen's option (a));
  - the Gate 6 store, legacy observation and transition, the `ars://legacy/` binding ban and provider actions stay.

**Departure from note §6.2.** The note's list drops "W9 genesis import" with nothing in its place. The added line
keeps in the contract what P-076 still withholds: genesis and live operations on a real store, and legacy writes. It
names the owner decision rather than restating it, so it stays true once L-3 is authorized.

The schema consts (`materialization_status`, `runtime_activation`, `expected_catalogue`, `acceptance_instance`), the
families, the source identities, `refused_store_identities`, `required_w11_catalogue` and `restricted_suffixes` are
unchanged. No schema changes, so the catalogue's 19 schema source rows are unaffected.

| Identity | Before (`7979e85a`, O-8) | After (this PR) |
|---|---|---|
| Git blob | `96a63114dbf94d3efa8019e18d8208832eee833d` | `6bbbb14a6754b64209bab5e50aa8e552bf71b63d` |
| SHA-256 | `b3352b2c25799a7d975147f2f536290318a9b6baaedf71cb51b77515cd9e3ac1` | `47699ed77c1934ee6764f514e6aecf3ddad3349819106d030b600020c964ddb1` |
| Size | 3,820 bytes | 4,164 bytes |

Revision 1 (`7e119810`) had blob `0579a8a5`, without the m-2 line.

After merge, Stephen accepts the amended contract at its main commit (06v O-3), as its own decision. The genesis
payload of WP9.2-2 names that commit.

## 2. The envelope (design note §5.3)

`.research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json`, `ars://legacy/w9-catalogue-acceptance-envelope`
1.0.0, in `research_system.canonical.canonical_bytes`, one line, no trailing newline, `eol=lf`.

| Identity | Value |
|---|---|
| Git blob | `9b28528c119ef45244b277ccd30855c68826e41f` |
| SHA-256 | `c26f468c9cfa0195d82812f05faa4e6e663a3ceb9737d31f8f5f1bd190465999` |
| Size | 11,185 bytes |

Its values, each derived from Git by the test:

| Field | Value |
|---|---|
| `catalogue_identity` | `7979e85a`, blob `d1916ffd`, `f7e2d9e2…db8c`, 128,583 bytes |
| `owner_annex_identity` | The catalogue's: `fc5f356b`, blob `d8fbda41`, `36a3d1ac…36fc`, 85,664 bytes |
| `specification_identity`, `plan_identity`, `schema_identities` | The catalogue's, verbatim |
| `owner_row_multiset_hash` | `a80788184c02b5baa9ea47cf2f1a254f4f14499188e6a0dcbef8d083072ffde7`, P-077 item 3's value, reproduced by the derivation |
| `bootstrap_contract_identity` | The contract O-8 rested on: `7979e85a`, blob `96a63114` (P-075 carried; review M-5) |
| `schema_generator_identity`, `verifier_identity` | At `7979e85a`: `5b068f9d`, `e8bb5085` |
| `binding_test_identities` | At `7979e85a`: `5a8e1c84`, `4133b75e` |
| `independent_observation_ref` | `obj_01a17eb7-5ae0-7071-b0bf-bacc039a26ce` (the verifier run P-075 cites; the register at `eab253f6`) |
| `independent_review_ref` | `rev_01a17eb7-5ae0-778e-8617-52ef7a4f7665` (the B2 confirmation at `7979e85a`) |
| `acceptance_decision_ref` | `dec_01a17eb7-5ae0-7e7b-9f86-bc9d2f8b07ab` (P-075; the register at `eab253f6`) |
| `accepted_at` | `2026-10-27T18:55:08Z` |
| `acceptance_scope` | "O-8: the W9 expected catalogue and its owner annex at main commit 7979e85a (P-075)" |

**The reserved IDs.** Each is a valid UUIDv7. Its timestamp is `accepted_at`, `1793127308000` ms. `rand_a` is the
first 12 bits, and `rand_b` the next 62 bits, of the SHA-256 of `w9-external:<kind>:<entry>:<repository_path>@<commit>`,
with the full 40-hex commit. `<entry>` is `P-075` for the observation and the decision, and `B2-confirmation` for the
review. `record_revision` is 1, and `content_hash` is the raw SHA-256 of the named file at the named commit. WP9.2-2's
genesis reserves the three IDs, and W9-C25 refuses them as pre-assigned IDs (P-077 item 2).

## 3. Controls

`tests/research_system/contracts/test_w9_acceptance_envelope.py` (new):
- one byte guard, `_is_derived_envelope`: the committed bytes equal `canonical_bytes` of the envelope derived from Git.
  The positive test and every negative control call it (review m-1);
- the envelope validates against its schema;
- **negative controls**, each refused by the guard:
  - a tampered `owner_row_multiset_hash`, which passes the schema;
  - a pretty-printed re-encoding;
  - the committed bytes with an added LF, and with an added CRLF;
  - a changed decision ref, which passes the schema;
- the multiset hash equals P-077's literal, and the annex-row alternative does not;
- the envelope cites contract `96a63114`, and the checked-out contract is no longer that blob;
- the catalogue identity is O-8's;
- `accepted_at` is P-075's main commit time;
- each reserved ID equals its pinned literal, is UUIDv7 with that timestamp, and hashes its named file;
- the IDs are distinct and bound to their domain strings.

`tests/research_system/contracts/test_w9_expected_catalogue.py`: the tracked-instance scan now requires exactly two
instances, the catalogue and the envelope, each with its own kind. The scan's negative controls are unchanged.

`tests/research_system/contracts/test_w9_contract_materialization.py`: the contract's `verification_rules` and
`forbidden` lists are pinned whole, as W11's test pins its rules (review m-3). So the bytes Stephen accepts at O-3 are
the bytes this review saw, until WP9.2-2's `accepted_w9.py` pins the blob.

## 4. Verification

- The W9 tests (envelope, catalogue, stage A): 268 passed.
- Guard-removal mutants of the envelope test (review m-1), each written next to the test, run and deleted:

  | Mutant guard | Controls that fail |
  |---|---|
  | `json.loads(data) == expected_envelope()` (object comparison) | `test_byte_identity_refuses_what_the_schema_admits` |
  | `return True` | that test and `test_a_changed_ref_breaks_the_envelope` |
  | `data.strip() == …` (line endings ignored) | `test_byte_identity_refuses_what_the_schema_admits` |

- `verify_w9_materialization.py --require-catalogue`: 61 pinned rows, 0 problems.
- `ruff check` and `ruff format --check`: clean.

## 5. Not in this PR

- The runtime, `accepted_w9.py`, genesis and the CLI (WP9.2-2).
- O-3, which follows this PR's merge.

## 6. Review reconciliation

The review of revision 1 (`reviews/wp9-2-1-review-7e119810-2026-10-28.md`, `58cc63e1`, cherry-picked as `2277db36`)
returned accept with required changes: no Blocking or Major findings, three Minor and ten Info. It recomputed all 17
envelope fields and the three reserved IDs with its own code, and every one matched; that is the independent
reconstruction of `owner_row_multiset_hash` that note §7.3 relies on. Stephen chose to take all three findings.

| Finding | Disposition |
|---|---|
| **m-1** the negative controls never call the byte guard | Fixed with the review's proposal: one predicate, `_is_derived_envelope`, called by the positive test and every control, with the LF and CRLF cases added. The guard-removal mutants now fail (§4). §3 corrected |
| **m-2** the `forbidden` list is silent on genesis and live operations off a scratch store | Stephen's option (a): the review's line is added, and the departure from note §6.2 is recorded in §1. The contract's identity changes (§1 table) |
| **m-3** no test pins the amended free text | Fixed: both lists are pinned whole in the stage A contract test |
| i-1 to i-10 | Recorded. None needs a change. i-6 (the domain string uses the full 40-hex commit) is as §2 states |

The envelope is unchanged: it cites the contract O-8 rested on (`96a63114`), not the amended one.
