# WP6.3 fresh semantic review handback, after PR #173

**Created:** 2026-07-28
**Responds to:** `24-wp6-3-post-pr173-semantic-review-handoff.md`
**Workflow system:** `standalone` (no `.apm` initialized or used)
**Repository:** `stephendor/TDL`
**Reviewer authority:** review only. No acceptance, implementation, Jira-transition, provider, migration, pilot, result, or claim authority was exercised by the reviewer.

## Verdict

**`accept_exact_subject`**

All ten review scope items pass. Two non-blocking observations were returned; neither blocks acceptance and neither was remediated (see "Carry-forward" below and the reason for not touching bytes).

## Owner acceptance

**Stephen explicitly accepted the exact contract and schema bytes at
`449b0d002edea3013dcc32a115f1870c4a082974` on 2026-07-28.**

This closes step 2 of the packet-24 post-review sequence. It is an exact-byte
acceptance of the two artifacts named below, not a lifecycle transition: no gate
closed, no Jira state moved, and no downstream authority was conferred by the
acceptance itself.

## Subject and computed identities

**Subject commit:** `449b0d002edea3013dcc32a115f1870c4a082974` — PR #173 merge commit, `origin/main`, unmoved.

Recomputed here from the committed blobs, independently of the reviewer's worktree:

| Artifact | Blob | SHA-256 |
|---|---|---|
| `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` | `7298b994ca80fb43364ec53964b735f1c7e3929a` | `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` |
| `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json` | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` |
| `tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | `70583aaad3b60510753d0793d126de8b4c0bd030` | `39065c5bc395dbfa1fe9c9ab5443cb5fd7ae4f957dd7ceb006a538bb918ac25d` |

All six values match the reviewer's report and the packet-24 cross-check exactly. Three-way agreement (packet 24 → reviewer → this recomputation). No divergence.

**Scope note.** The owner acceptance names the contract and schema. The test
module is the enforcement surface, reviewed and reported at the same subject but
not an object of the exact-byte acceptance.

## Validation reported by the reviewer

```
C:\Users\steph\TDL\.venv\Scripts\python.exe -m pytest -q tests/research_system/contracts/test_wp6_3_tdl_private_assurance_pack_contract.py -o "addopts=" -p no:cacheprovider -p no:cov
```

`38 passed in 171.31s`. A first invocation exceeded a 60-second window and was
inconclusive; the completed rerun passed. No broader suite was run because no
focused failure or dependency trigger arose. This matches the packet-24 criterion
(38 cases from 37 defined functions, one parametrized) and the merge-seam run
performed when packet 24 was drafted.

Reviewer final state: detached clean worktree at the subject; no repository file
edited, staged, committed, or pushed; no lifecycle, Jira, provider, or acceptance
state advanced.

## Scope findings — all pass

1. **External authority resolution.** Candidate-supplied record bodies and hash oracles prohibited by contract; validator requires a typed trusted resolver, binds its root to the W1/W2 subjects, and revalidates contents.
2. **Exact-reference currency.** All six contract and six skill rows resolve at the subject with matching blob and SHA-256. Derived and declared pending sets both empty. Load, acceptance and consumption revalidation enforced.
3. **Two-key obligation closure.** Lane counts 11/11/12/10/11/14 — exactly 69 unique `(lane_id, obligation_id)` keys. Schema enforces cardinality and evidence-row value shapes; validator enforces exact two-key membership, uniqueness, non-compensation and owner binding.
4. **Lifecycle ordering.** Candidate self-acceptance schema-rejected; exact review and owner subjects externally resolved; ordering covers contract/schema review, requirement acceptance, registration, candidate authorship, review and owner acceptance. Supersession immutable.
5. **Provenance typing.** All three review record types require typed operators, distinct tasks and sessions, fresh context, `fork_turns: none`, and one stable handoff ID — with closed application across all three types.
6. **Operator-model coherence.** Contract selects both currently recognised agent/session families; validator reads those allowlists; schema and validator both exclude `human_owner` from review-operator positions.
7. **Fixture/lane agreement.** Every lane fixture link resolves to its own lane or `cross_lane`; no foreign link remains; the representation-specific correction has a reachable negative control.
8. **Intended negative cases.** The 53-row catalogue is unique and entirely blocked. Missing/extra/swapped reference, fixture and obligation cases, authority substitutions, no-op, degenerate, claim-escalation and provenance controls all passed. Downstream scientific execution remains explicitly deferred rather than self-attested.
9. **Declared-set bindings** (the PR #173 F-1 remediation). Reference counts and boundary-copy agreement validator-enforced; review-type and temporal declarations schema-pinned plus code-side checked; distinct pairs iterated by the validator.
10. **Enforcement-surface closure** (the PR #173 F-2 remediation). 37 defined test functions, exactly partitioned into 36 durable and one task-local declaration; 38 cases from parametrization. The extracted `_assert_test_surface_closure` helper retains presence, task-local presence, disjointness, closure constant and bidirectional equality checks.

The packet-24 instruction block on schema-versus-validator enforcement worked:
every finding above names which layer enforces it, and no "X is not enforced"
false positive was filed this round. That pattern had recurred three times across
packets 20–23.

## Non-blocking observations, verified here

Both were checked against the committed bytes at the subject rather than accepted on report.

**O-A — inaccurate comment at test line 3748.** The comment reads "the schema
pins the list to 11 pairs, so a shorter list fails schema validation before
reaching the check under test," justifying an in-place mutation instead of a
truncation. **Confirmed inaccurate.** The schema defines
`required_distinct_pairs` with `minItems: 7`, `uniqueItems: true`, and **no**
`maxItems`. A truncation to ten would remain schema-valid and would reach the
check. The mutate-in-place technique is still the right one — it isolates the
distinctness violation from any cardinality effect — but the stated reason is
false. No behavioural defect: the subject's contract declares eleven pairs and
the validator iterates the declared set, so eleven are enforced at this subject.

A second-order point the reviewer did not raise: `minItems: 7` means a future
contract revision could declare seven pairs and stay schema-valid, silently
dropping four independence separations. That risk is bounded by the review gate
— any such revision is a contract change requiring fresh independent review —
but the floor is looser than the comment implies and looser than the enforced
set.

**O-B — unreachable status-mutation branches at validator lines 1885–1910.**
The `key_a_status != "passed"` / `key_b_status != "passed"` /
`forbidden_state_or_claim != "absent"` disjuncts cannot fire: the external-record
schema rejects those mutations first. **Confirmed.** The schema is the effective
layer for status. The relational checks in the same block —
`set(evidence_rows) != expected_applicability` and `len(evidence_rows) != 69` —
remain reachable and are doing real work.

This is precisely the inverse finding packet 24 asked the reviewer to look for:
an existing runtime check made unreachable by a schema constraint firing first.
It is dead enforcement that reads as coverage. Harmless in itself; misleading to
a future reader auditing what the validator actually proves.

## Carry-forward — deliberately not remediated now

Neither observation was fixed, and that is a decision rather than an omission.

Both live in the test module. The module is the enforcement surface for an
artifact set that has just been reviewed and owner-accepted at an exact commit.
Editing it now would move the enforcement surface off the reviewed subject
immediately after acceptance, for two changes that alter no behaviour: O-A is a
comment, O-B is a redundant disjunct. Neither is worth re-opening a byte-exact
review boundary.

Both are therefore folded into the bounded WP6.3 pack implementation brief
(sequence step 5), which will touch the module anyway:

- **O-A** — correct the comment to state the actual schema floor (`minItems: 7`,
  no upper bound) and why mutation is still preferred to truncation.
- **O-B** — either drop the unreachable status disjuncts and note that the schema
  owns status, or add a control proving they are reachable. Do not leave them
  unlabelled.
- **O-A second-order** — decide whether `minItems: 7` is the intended floor for
  `required_distinct_pairs`. If eleven separations are load-bearing, the schema
  should say so; if seven is a deliberate minimum with the contract free to
  declare more, record that rationale.

## Where this leaves the sequence

From the packet-24 post-review sequence:

1. ~~Review returns `accept_exact_subject`~~ — **done.**
2. ~~Stephen accepts the exact contract and schema bytes~~ — **done, 2026-07-28.**
3. **Next:** W1 authority registers the `assurance_pack` id-kind and object in
   `.research-system/config/id-kind-registry.yaml`. The registry at the subject
   carries 25 kinds and has no `assurance_pack` entry; a short code must be
   allocated alongside `asr` (`assurance_requirement`) without colliding with it.
4. KAN-56 readiness re-run. KAN-56 is already `In Progress` with resolution
   cleared (decided 2026-07-28: reopen, no new ticket), so no transition is
   outstanding beforehand.
5. A passing reassessment authorizes one bounded WP6.3 pack implementation brief,
   carrying O-A and O-B above. Pack authored → independently reviewed →
   owner-accepted → Gate A A7 closes.
6. WP6.1 currency re-verified — KAN-54's `Done` covers the D-G6-3 precheck only,
   not broader runtime completion.
7. KAN-57 / WP6.4 binding and preflight → Gate 6.

## Sensitive information

No credentials, OAuth material, provider session data, tokens, private research
data, or account details are included.
