# Adversarial WP6.1 schema-fact annex R7 review — 2026-07-19

## 1. Review identity and verdict

- **Reviewed PR:** #124
- **Exact reviewed subject:** `da94bd62fbf19021f3046c19fae5117c19219c95`
- **Subject branch:** `codex/wp6-1-r1-remediation` / `pipe/ars-wp6-1-task-lifecycle`
- **R6 reviewed subject:** `5f795e165cb8029aefcaf512da4e8076d7d64395`
- **Review mode:** fresh independent exact-byte adversarial delta review
- **Verdict:** `approved`

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 0 |
| Minor | 0 |

R6-M1 is closed. Independent derivation finds exactly three variant-controlled
ResourceRequest fields and 35 globally required non-variant fields. Each branch has a
fully type-valid witness, zero required/forbidden intersection, and exact 38-field
coverage. Required rule, precedence, boolean, empty-language, and instance mutations
all fail closed. The R5 gate/provenance closures remain intact, and no new
severity-bearing issue was found.

This approval is review evidence, not Stephen's acceptance. It does not merge the PR
or authorize runtime registration, dispatch, reduction, projection, migration, hooks,
or a Gate 6 transition.

## 2. Exact-head and byte verification

At review start and immediately before report creation, cwd was
`C:\Users\steph\.codex\worktrees\cfe3\TDL`, branch was
`codex/wp6-1-r1-remediation`, and the worktree was clean. Local `HEAD`,
`origin/pipe/ars-wp6-1-task-lifecycle`, freshly fetched `refs/pull/124/head`, remote
branch/pull refs, and GitHub `headRefOid` all equalled
`da94bd62fbf19021f3046c19fae5117c19219c95`. PR #124 remained open, draft, and
merge-state clean.

| Authority object | Git blob | SHA-256 | Bytes |
|---|---|---|---:|
| `docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md` | `73677f4a49a9752f6536b103321f654cd8575075` | `4b997c85184d8a8842b5524ffe4595473697c3438b70c224685c0b291a4760d0` | 39,567 |
| `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml` | `2f55b82f1a84cc0de081d38f8500c73a2083bac4` | `d52c9b4e923d7f31f7201213335a147ff48293f96c0aab7c9eb59f8e7ff96441` | 360,272 |
| `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json` | `d9e82a041337dfa7df65408e93798aaf37841afe` | `7599bf7b2174a2e2e35362427a20ae1357f4c33d13b3d4324a05330ad67c21ec` | 31,674 |

All are UTF-8/LF with no BOM. Immutable W2, W8, and 06d Git blobs and SHA-256
identities at `fe5f1d40bc8f05f061317c677b5891cea0711249` also match the proposal.

Every changed byte since `5f795e1...` was reviewed: immutable R6 report `a6b44aa...`,
proposal/companion/Markdown remediation `848d5fd...`, and oracle/tests `da94bd6...`.
No reviewed file was modified by this review.

## 3. R6-M1 disposition

**R6-M1 — contradictory global and variant requiredness: closed as prescribed.**

The YAML and companion schema now freeze the same-object exception, union derivation,
controlled-field-only precedence, global requiredness of all other outer fields,
non-null selected fields, absent forbidden fields, and ordinary requiredness of every
selected nested field. The Markdown and decision register repeat the same scope without
broadening or narrowing it.

Independent composition produced:

```text
WITNESS trivial      controlled=3 common=35 required=36 forbidden=2 union=38 intersection=0 nested=12 typed_valid=True
WITNESS bounded      controlled=3 common=35 required=36 forbidden=2 union=38 intersection=0 nested=4  typed_valid=True
WITNESS long_running controlled=3 common=35 required=36 forbidden=2 union=38 intersection=0 nested=6  typed_valid=True
```

Deleting the exception reproduces the exact R6 empty-language intersections: each
branch again requires its two forbidden foreign evidence fields. The remediation fixes
the underlying composition rather than merely blocking the earlier attack vehicle.

## 4. Independent attack and closure results

The review independently rejected:

- missing, changed, cross-object, and all-field exception scope;
- changed controlled-set derivation;
- reversed and overbroad precedence;
- each of the five requiredness booleans changed to `false`;
- an explicit required/forbidden intersection on each branch;
- a missing common field;
- null, empty, and incomplete selected evidence;
- either foreign-field leakage, fallback profile, and extra outer fields; and
- the explicit no-exception empty-language case.

All 29 reusable objects have finite exact-key type-valid witnesses. All five nullable
reusable-object fields remain present as required keys whose values may be null. No
other object participates in a variant rule, and no required cycle, cross-object
exception, or nullable contradiction was found.

## 5. Preserved invariant matrix

| Invariant | Independent disposition |
|---|---|
| Six-verdict total gate map | Pass: `approve` succeeds; conditional approval requires a non-empty valid condition; four negative verdicts fail |
| Verdict-scoped minimum | Pass: minimum 1 only at the conditional gate; no global list minimum |
| Conservative gate-disposition provenance | Pass: enum, field, and ordered binding row remain `conservative_proposal` |
| Exact source provenance | Pass: standard-library-only oracle and exact ordered 229-tuple ledger |
| R4 wrong-but-resolving attacks | Pass: all three rejected |
| ResourceRequest composition | Pass: three complete typed witnesses and all required mutations rejected |
| Counts and closure | Pass: `104/104/106/87/86/173/17/27/14` |
| Generation boundary | Pass: `stage_1_ready: false`, runtime authority false, explicit owner approval pending |

The proposal source-binding array is unchanged from R6 and equals the independently
maintained ordered 229 ledger. The oracle imports only Python standard-library modules;
it does not import the proposal, resolver, materializer, generated schemas, validator,
or companion schema.

## 6. Decision audit

All 14 decision-register entries were re-read; each retains
`generator_byte_change_allowed: false`. Scope/IDs, Task, Dispatch, Lease,
Attempt/checkpoint, Message, Blocker, Artefact policy gates, Review, Decision,
RuleEvaluation's conservative `val_` cross-use, Correction's 15 branches,
Resource/operation unions/bounds/profile composition, and Backup/recovery are all
**keep**. No generic fallback, self-hash, acceptance claim, inferred owner verdict,
generated schema, registry change, or runtime implementation was added.

## 7. Mechanical and external evidence

| Check | Exact-head result |
|---|---|
| Independent focused oracle suite | `241 passed in 1.59s` |
| Draft 2020-12 companion validation | Pass |
| Independent all-object/witness evaluator | 29 objects and all three ResourceRequest branches pass |
| Exact bytes, Git blobs, SHA-256, UTF-8/LF | Pass |
| Exact ordered binding ledger | 229, pass |
| R4 attacks | 3/3 rejected |
| `git diff --check` | Pass |
| Codacy `88185004791` | Success at exact head, 0 annotations |

Controller evidence also records 55 foundation/materialization tests and 175 legacy
mutation cases passed, with Ruff and diff checks green. Those broader batteries were
not rerun in this report-only task; the focused suite and independent semantic attacks
were rerun directly.

## 8. Stage-1 approval tuple and owner wording

This clean review presents, but does not itself accept, the exact Stage-1 tuple:

```yaml
stage_1_review_verdict: approved
reviewed_subject_commit: da94bd62fbf19021f3046c19fae5117c19219c95
proposal:
  path: .research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml
  schema_id: ars://contracts/wp6-1-schema-fact-annex-proposal
  schema_version: 1.0.0
  git_blob: 2f55b82f1a84cc0de081d38f8500c73a2083bac4
  sha256: d52c9b4e923d7f31f7201213335a147ff48293f96c0aab7c9eb59f8e7ff96441
companion_schema:
  path: .research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json
  git_blob: d9e82a041337dfa7df65408e93798aaf37841afe
  sha256: 7599bf7b2174a2e2e35362427a20ae1357f4c33d13b3d4324a05330ad67c21ec
proposal_markdown:
  path: docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md
  git_blob: 73677f4a49a9752f6536b103321f654cd8575075
  sha256: 4b997c85184d8a8842b5524ffe4595473697c3438b70c224685c0b291a4760d0
decision_register_entries: 14
generation_scope:
  command_schema_identities: 87
  event_schema_identities: 86
  total_schema_identities: 173
```

Recommended exact owner wording:

> I explicitly accept the Stage-1 WP6.1 schema-fact annex tuple reviewed at
> `da94bd62fbf19021f3046c19fae5117c19219c95`, including the exact proposal,
> companion-schema, Markdown blobs/SHA-256 identities, schema ID/version, and all 14
> frozen decision-register entries listed in the R7 report. I authorize only
> deterministic generation of exactly 173 schemas — 87 command and 86 event semantic
> identities — from those accepted bytes. The generated outputs require their own
> later exact-byte validation, independent review, and owner decision. This acceptance
> does not authorize runtime registration, dispatch, reduction, projection, migration,
> hooks, PR merge, or any Gate 6 transition.

Stephen must supply that acceptance explicitly; it is not inferred from this report.

## 9. Limitations

No generated schema set exists at this subject, so generated paths, bytes, content
observations, registry behavior, and runtime integration remain outside this review.
CodeRabbit was not invoked or inspected. The PR was not pushed, merged, marked ready,
or otherwise mutated.
