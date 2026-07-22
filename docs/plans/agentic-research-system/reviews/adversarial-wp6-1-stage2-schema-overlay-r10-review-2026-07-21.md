# WP6.1 Stage-2 schema overlay R10 targeted review

## Verdict

**accept** — **0 Critical, 0 Major, 0 Minor** findings in the deliberately
narrow R9-M2 remediation scope.

This is an independent review of the exact committed subject
`c7e32755e9adb2f39f6a40056ef6058986c9263d` on
`origin/pipe/ars-wp6-1-task-lifecycle`.  It neither re-accepts the wider
Stage-2 work nor infers owner acceptance, a merge, runtime authorization, or
any Gate transition.

## Identity and scope

| Item | Exact value / result |
| --- | --- |
| Subject | `c7e32755e9adb2f39f6a40056ef6058986c9263d` |
| Subject implementation parent | `05898522e28598d63c9e8d2640d64f7d17e29d81` |
| Reviewed implementation range | `05898522e28598d63c9e8d2640d64f7d17e29d81..c7e32755e9adb2f39f6a40056ef6058986c9263d` |
| R9 review evidence | commit `e050c7b7a1320fa9933ac41d5684ddacf65afa4b`; report blob `610a7406c5ea5c6444d5bd45552129d05fcc8b8c`; verdict `0C/1M/0m` |
| R9 relation | The R9 review commit is not an ancestor of this subject; its M2 finding was used as an attack specification, not as authority. |
| Accepted Stage-1 proposal | revision `da94bd62fbf19021f3046c19fae5117c19219c95`; blob `2f55b82f1a84cc0de081d38f8500c73a2083bac4`; canonical UTF-8/LF SHA-256 `d52c9b4e923d7f31f7201213335a147ff48293f96c0aab7c9eb59f8e7ff96441` |
| Schema tree | `.research-system/schemas/core` is `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46` at both subject and baseline `00ca238b2faa33dffe00fd55e10c8702f28268ee`. |

The subject implementation delta has exactly two paths:

- `tests/research_system/contracts/wp6_1_stage2_span_editor.py`
- `tests/research_system/contracts/test_wp6_1_stage2_span_editor.py`

There is no schema-tree change and no runtime registration, dispatch,
reduction, projection, migration, hook, shared-runtime-manifest, Gate, or
other transition-surface change. `git diff --check` is clean.

## R9 M2 disposition: resolved

R9's Major finding was that the old regression patched an unused path while a
coordinated replacement of the imported helper, proposal bytes, and matching
baseline could still alter generated expectations. The remediation closes the
consumed seam:

1. `build_stage2_overlays` now consumes `_bound_accepted_fact_annex_bytes`.
2. That function reads the imported `approved_fact_annex_bytes` helper and a
   separately imported `approved_source_bytes(repo_root, FACT_ANNEX_SOURCE)`.
3. The latter performs `git show` at the accepted immutable revision and
   validates the accepted blob and canonical SHA-256. A byte mismatch raises
   `ValueError("fact-annex helper bytes diverge from immutable accepted source")`.
4. The replacement regression directly monkeypatches the consumed
   `span_editor.approved_fact_annex_bytes` helper with a proposal in which
   `CreateScopeDefinition` becomes `CreateScopeAlias`, and provides a complete
   matching baseline with the same coordinated change. It asserts the exact
   fail-closed error.

An independent in-memory attack in the external checkout confirmed that the
immutable read equals `git show da94bd62...:.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml`, that the unpatched helper agrees with it,
and that patching only the consumed helper produces the divergence error. The
separately imported immutable reader was not patched.

## Retained accepted-artifact spot checks

The following R9-accepted artifacts are byte-identical at `00ca...` and the
subject; these were spot checks only, not a re-review of M1/M3/M4 content.

| Surface | Git blob |
| --- | --- |
| M1 identity manifest | `54a2938d34cea9c4a88d23585ce012a86bc3209d` |
| M1 owner-source catalogue | `1adc66921ee9c90d8786ff173748150922f1035e` |
| M1 Stage-1 owner-acceptance record | `42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83` |
| M3 identity schema | `5857d1dbf80ca86d711641b1206267fa2fa44202` |
| M3 source-catalogue schema | `8e7ae9079304e20de6d70f74f581d479391f8a31` |
| M3 owner-acceptance-record schema | `63762c1555515ae9a2db071663d7fe9e2e86a96a` |
| M4 materialization test | `87ddc59817995804dfc9a3d524389512440b974b` |

## Validation evidence

| Check | Result |
| --- | --- |
| Direct M2 regression `test_wp6_1_coordinated_checkout_substitution_cannot_change_immutable_expectations` | Passed (`1 passed`). |
| Focused span/materialization smoke | External detached exact-subject checkout with `core.autocrlf=false`: `12 passed` in 17.45s. |
| Changed-file Ruff | `ruff check tests/research_system/contracts/test_wp6_1_stage2_span_editor.py tests/research_system/contracts/wp6_1_stage2_span_editor.py` — passed. |
| Contract binding, validation gate | `contract_binding_check.py --validate-only` — all gates passed against 102 contracts. |
| Contract binding, no-pytest gate | `contract_binding_check.py --no-pytest` — all gates passed against 102 contracts. |
| Diff whitespace check | `git diff --check 05898522... c7e32755...` — passed. |

The original application worktree materializes some committed canonical-LF
artifacts as CRLF. There, the broader focused smoke reported three byte/hash
failures despite a clean Git status. This is a checkout effect, not a subject
finding: the external detached exact-subject checkout with `core.autocrlf=false`
had LF bytes in the affected artifacts and passed all 12 focused tests. No
schema regeneration or broad suite was run.

## Limitations and authority boundary

This review is restricted to the R9 M2 source-seam remediation plus the stated
tree, scope, and retained-artifact checks. It does not authorize an owner
decision, D-G6-3, runtime work, a Gate transition, a merge, or any PR action.
