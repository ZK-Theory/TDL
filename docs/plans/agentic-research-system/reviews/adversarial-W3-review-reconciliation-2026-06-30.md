---
review: Reconciliation of the adversarial W3 context review
date: 2026-06-30
review_commit: 1d6ade22
reviewed_design_commit: c16f5bff
status: approved_for_specification_integration
authority: Stephen
implementation_authority: none
---

# Adversarial W3 Review Reconciliation — 2026-06-30

## 1. Purpose and boundary

This record preserves `adversarial-W3-context-review-2026-06-30.md` unchanged and evaluates its findings against the accepted W1 v0.3, W2 v0.3, W6 v0.2 catalogue, and P-020–P-027. Stephen approved this exact integration boundary for W3 v0.2 and the dated W6 catalogue addendum on 2026-06-30.

The approval authorizes specification integration only. It does not authorize implementation, alter active APM/T1.28 work, permit migration, or promote any research evidence or claim.

## 2. Technical disposition

| Finding | Approved disposition | Integration rule |
|---|---|---|
| W3-M1 | **Accept; correct in W3.** | Governing rules, amendments, decisions, contract assertions, and review verdicts may never be replaced by compaction at any risk tier. R2/R3 additionally require the exact purpose-required subject artefact. |
| W3-M2 | **Accept; correct in W3.** | A memory item may reference a canonical governing object and its ID/hash; the memory item never carries or grants that authority. |
| W3-M3 | **Accept with technical amendment; approved.** | Enforce two unit-safe gates before issuance: reference-token count against the W3 profile ceiling, and bound-provider token count against 80% of provider usable input. Do not compare counts from different tokenizers through one `min(...)`. Use the exact versioned provider tokenizer where available; otherwise require a W7-evaluated conservative upper-bound counter. A route with neither is ineligible. Any failure returns `context_budget_exceeded`, the section 8.3 safe options, and no issued packet. |
| W3-M4 | **Accept; approved.** | Reserve F-025–F-030 in a dated W6 addendum and amend P-024 through a new dated decision. Do not rewrite the accepted 40-fixture catalogue history. |
| W3-M5 | **Accept as a Gate 1 materialization precondition, not a prerequisite for written W3 acceptance.** | W6 must measure mandatory closure for F-025, F-026, F-021, and F-022 under both token-count gates before compiler/profile release. An over-ceiling closure is a blocking design signal requiring evidence-backed ceiling change or explicit decomposition preserving cross-cutting evidence; it is not fixture noise. |
| W3-m6 | **Accept; wording correction.** | Two-manifest independence applies when the assurance grade requires a distinct verifier. R0/R1 delegated acceptance remains permitted by P-022. |
| W3-m7 | **Accept; factual correction.** | Describe the approximately 80,000-token value as a word-to-token heuristic for generic Manager preload, not a measurement or a like-for-like mandatory-closure baseline. Replace “at least 40% smaller” with “nominally 40% below that estimate.” |
| W3-m8 | **Accept with authority rule; approved.** | Delta-review exposure must be allowed by a versioned assurance policy and attributed at use. Manager may authorize an allowed R2 exposure; Stephen authorizes R3 exposure. Exposure changes the recorded independence profile and never becomes hidden inheritance of producer reasoning. |
| W3-m9 | **Reject the proposed field-dropping; accept a clarification.** | W3 section 9.1 delivers a manifest reference, not the full manifest, so the review establishes no token-budget burden from empty manifest groups. Keep one canonical manifest schema with explicit empty/`not_applicable` values. Clarify that manifest metadata is outside model-visible managed-token accounting unless deliberately rendered into the packet; if rendered, it is counted. Measure operational overhead before introducing an R0 schema variant. |
| W3-m10 | **Accept; editorial.** | Use `independent verifier packet` consistently and cross-reference `conflicted` freshness to section 11.3. |

## 3. Additional integration correction

The reconciliation found one lifecycle contradiction not identified by the submitted review:

- W3 section 10.1 step 8 says issuance occurs only after delivery validation, while section 12.1 defines `validated -> issued -> delivered`.

W3 v0.2 should use this order:

```text
requested -> compiling -> compiled -> validated -> issued -> delivered
```

The compiled candidate is routed; the bound adapter supplies its provider-token count or evaluated upper bound; W3 completes budget, manifest, security, and independence validation; only then is the packet issued. `delivered` follows a matching content-hash delivery receipt. Delivery failure never retroactively makes an over-budget packet valid.

## 4. Approved W4/W7 token-accounting seam

The M3 change should freeze this handshake before W4/W5 proceed:

1. W3 produces a deterministic `compiled` candidate with rendered bytes/hash and reference-tokenizer version/count.
2. W4 selects an evaluated provider/model/profile candidate from the role, risk, capacity, and independence requirements.
3. W7 supplies the exact provider-tokenizer version/count for those bytes, or an evaluated conservative upper-bound counter and evidence version.
4. W3 validates both independent gates and records both counts in the manifest.
5. A failed route returns to W4 only through an explicit failed candidate outcome; W3 never drops mandatory content or silently chooses another route.
6. W3 issues only after one route passes; W7 then delivers the exact issued bytes and returns a content-hash receipt.

The 20% provider reserve remains reserved for active interaction, provider instructions, and tool results. It is not consumed as an undocumented tokenizer-drift allowance.

## 5. Approved W6 addendum

The dated addendum should reserve:

| ID | Design | Priority | Proposed incident basis / input fidelity |
|---|---|---:|---|
| F-025 | Orchestrator scope-collapse retrieval | P0 | `historical` / `reconstructed` |
| F-026 | Implementer frozen-representation/null/vintage retrieval | P0 | `domain_coverage` / `synthetic` |
| F-027 | Optional-index deletion equivalence | P0 | `specification` / `synthetic` |
| F-028 | Budget overflow fails closed without mandatory omission | P0 | `specification` / `synthetic` |
| F-029 | Safe-distractor invariance | P1 | `specification` / `synthetic` |
| F-030 | Addendum lineage and cumulative-budget conformance | P1 | `specification` / `synthetic` |

F-025 and F-026 may cite the existing failure families as historical motivation, but fixture input fidelity must be based on the actual minimized reconstruction/source manifest. No fixture may use T1.28 or live restricted data.

F-021 and F-022 remain the cross-cutting amendment and independence cases; the new IDs do not duplicate or renumber them.

## 6. Approved acceptance boundary

Stephen approved this reconciliation on 2026-06-30 with the instruction “Okay, that looks good. Proceed.” The approved integration sequence is:

1. record P-028 as the dated W3 acceptance and P-024 clarification;
2. integrate M1–M3, M5, m6–m10, and the lifecycle correction into W3 v0.2;
3. add the dated W6 F-025–F-030 reservation without rewriting the accepted v0.2 catalogue record;
4. update package status, roadmap, review record, and downstream dependency wording;
5. run a bounded delta review of W3 sections 6–17 and the W6 addendum;
6. mark W3 accepted only if that delta review confirms the five Major findings are closed and no new interface contradiction remains.

W6 executable materialization and empirical closure sizing remain deferred. W4/W5 may consume the interface only after the v0.2 integration and bounded delta review pass.

## 7. Approved decision bundle

- the unconditional M1/M2 authority boundary;
- the two-gate, pre-issue M3 token-accounting handshake;
- the F-025–F-030 dated reservation and M5 sizing precondition;
- Manager-at-R2 / Stephen-at-R3 delta-review exposure authority;
- rejection of m9 field-dropping in favor of one out-of-band canonical manifest schema;
- the lifecycle-order correction and remaining factual/editorial fixes.
