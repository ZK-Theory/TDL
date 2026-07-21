# WP6.1 Stage-2 external acceptance layer R11 review

**Verdict: `accept` — 0 Critical / 0 Major / 0 Minor.**

This fresh targeted review covers only
`3207bfef0c6680376a6d60fc7945c69516ec1133..dd1a65a65009a6d2221c10dc0285ae0ec2c7a3ae`
on `origin/pipe/ars-wp6-1-task-lifecycle`, limited to the five specified
external-acceptance paths. The review branch was attached at the exact remote
subject before writing this report.

## Scope and immutable candidate

The range changes exactly the intended five paths: the Stage-2 owner record,
its strict schema, the test-only validator and its 12-test suite, and the
Markdown audit rendering. No production module, runtime registration,
dispatch, reducer, projection, migration, hook, Gate 5, or P0 path changed.

The accepted candidate is independently unchanged from
`c7e32755e9adb2f39f6a40056ef6058986c9263d`:

| Identity | Verified value |
| --- | --- |
| Command schema tree / count | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` / 87 |
| Event schema tree / count | `154ffc4bdde82fe903718734687e7a62797b1f69` / 86 |
| Core schema tree / count | `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` / 173 |

Direct `git rev-parse` comparison from `c7e3275` to the reviewed subject also
showed the core tree, both candidate manifests, both Stage-2 strict contracts,
and the Stage-1 acceptance record/contract unchanged. Committed Git blob and
canonical UTF-8/LF SHA-256 checks matched the six candidate artifacts bound by
the new acceptance record.

## Acceptance-record disposition

| Question | Disposition and evidence |
| --- | --- |
| Strict, machine-readable, acyclic, no self hash | Accept. The record and schema validate through public `SchemaRegistry`; an extra root property is rejected. The record has no own blob/SHA field, and the schema `$defs` reference graph is acyclic. |
| Exact candidate / manifests / strict contracts / Stage-1 binding | Accept. All paths, schema IDs, versions, blobs, canonical hashes, tree IDs, and 87 + 86 = 173 cardinality are literal contract bindings and are reverified from immutable `git show c7e3275:<path>` bytes. |
| Verbatim owner statement and exact R10 | Accept. The owner statement, D-G6-3 outcome, and `exact_bytes_only` scope are exact constants. R10 is read from immutable commit `b1863e33106e02edaf3ccf0a18aa9385005b25bd`; its report blob `64e5f18a1b851f991689fdcc9db11bec0143539c`, SHA-256 `383b4680ad2812941cad6b1c1907277f3f00c0fa43ab4aa8775f5bc9541088d8`, and accept/0C/0M/0m text all matched. |
| Independent effective state | Accept. `accepted_exact_bytes_only` is derived only after immutable candidate and R10 checks, public-schema validation, and equality to separately constructed expected candidate/review/decision/hard-stop records. It does not take expected authority from the record under validation. |
| Candidate pending statuses | Accept. The candidate's embedded pending values are verified as snapshot facts from `c7e3275`; effective acceptance remains external. An independent monkeypatched snapshot had no effect on the derived acceptance. |
| Hard stops | Accept. The ten hard-stop fields are strict constants. All ten inversions failed even with a deliberately permissive registry. Runtime registration, dispatch, reduction, projection, migration, hooks, PR merge, further Gate 6 transition, and implementation start remain unauthorized; separate owner authorization remains required. |
| Test-only / discovery boundary | Accept. The validator is confined to `tests/research_system/contracts`; only the schema and record live in contract directories. Public `SchemaRegistry` discovers the schema without production wiring. |
| Markdown authority | Accept. Markdown explicitly identifies itself as an audit rendering. The validator does not consume it to derive acceptance; the external YAML record, immutable candidate objects, and immutable R10 review are the machine authority. |

## Adversarial controls

The focused suite and independent controls fail closed for stale subject/tree,
foreign manifest blob, missing candidate/review/hard-stop fields, extra fields,
wrong R10 commit/report, changed owner statement, changed decision outcome, and
relaxed hard stops. The committed suite's immutable-Git substitution attack
also rejects changed `git show` bytes by blob/SHA mismatch.

An additional in-memory control replaced the mutable checkout record with a
forged R10 commit while replacing SchemaRegistry with a permissive validator.
`load_stage2_owner_acceptance()` still rejected it at the independently built
R10 expectation. This confirms that the authority boundary is not merely the
checkout schema or the record's self-description.

## Validation evidence

All execution used an external short-path checkout at the exact subject with
`core.autocrlf=false`; logs are external under
`C:\Users\steph\.codex\visualizations\2026\07\18\019f7495-7002-7162-a4da-89f5213023c8\wp6-1-stage2-acceptance-r11-evidence`.

| Validation | Result |
| --- | --- |
| Focused acceptance matrix | `12 passed in 15.26s` |
| Independent candidate tree/artifact identity check | Pass |
| Public registry strict/acyclic/no-self-hash smoke | Pass |
| Independent permissive-registry and mutable-checkout substitutions | Pass: all attacks rejected |
| All ten hard-stop inversion control | Pass |
| Ruff on two changed Python files | Pass |
| `contract_binding_check.py --validate-only` | Pass: all gates against 102 contracts |
| `contract_binding_check.py --no-pytest` | Pass: all gates against 102 contracts |

## Limitations and boundary

This is an acceptance-layer review, not a runtime or implementation review. It
does not authorize runtime registration, dispatch, reduction, projection,
migration, hooks, implementation start, PR merge, any further Gate 6
transition, or a CodeRabbit review. No full suite, schema regeneration, PR
operation, or subject-file modification was performed.

