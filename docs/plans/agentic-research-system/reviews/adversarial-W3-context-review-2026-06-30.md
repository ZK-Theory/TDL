# Adversarial Review — W3 Context, Memory, and Retrieval Specification

**Reviewer:** Independent adversarial review (Claude Opus 4.8), commissioned by Stephen
**Date:** 2026-06-30
**Subject:** `design/03-context-memory-and-retrieval.md` (Specification v0.1, frozen at `c16f5bff`)
**Method:** `adversarial-design-review` skill; fresh-context attack against direct evidence
**Verdict:** **`accept_with_required_changes`**

---

## 0. Executive summary

W3 is a strong specification. It absorbed the lessons of the first-pass round: its W1/W2/W6
citations are accurate (verified line-by-line below), it correctly downgrades the external
whitepapers to "terminology and practitioner guidance, not project authority" (§2) — the
exact handling the prior review's PDF-provenance finding asked for — and it fails closed
almost everywhere. The strongest classical attacks on a retrieval layer **fail by design**
here, and I show why in §3.

The deliverable is accepted subject to required changes. There is **no Critical finding**
and **no rework**. The headline issue is narrow and important: W3 builds an almost-airtight
guarantee that *governing material is never displaced or summarised away*, and then opens
**exactly two wording cracks in §13** through which governing authority can leak —
(M-1) a tier-qualifier that, read literally, lets R0/R1 compaction replace a governing
amendment, and (M-2) a declarative-memory field that, read literally, lets a memory item
*be* governing. Both are one-to-three-line fixes, but both sit on the authority boundary the
entire system exists to protect, so they are Major. The remaining Majors are at the seams:
W3↔W7 token accounting (M-3), W3↔W6 fixture-ID coverage (M-4), and the unverified
feasibility of the hard ceilings on the flagship fixtures (M-5).

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — |
| Major | 5 | W3-M1 … W3-M5 |
| Minor | 5 | W3-m6 … W3-m10 |

No reviewed document was edited (consistent with the first-pass precedent: findings are
proposed here for Stephen's reconciliation, not self-applied). Change log in §12.

---

## 1. Scope, authority, and evidence verified

**In scope:** the W3 written specification (§§1–22) and its consistency with the accepted
W1 v0.3, W2 v0.3, W6 v0.2 catalogue, the W0 manifest/addendum, and the decision register
D-001–D-008 / P-001–P-027 / A-001–A-002 / Q-001–Q-007.

**Authority respected:** P-020–P-027 are Stephen-approved; I challenge none of them by
preference. W3's own §1 binding choices are conceptually approved by Stephen (2026-06-30,
§"Review record") but the *written specification* is explicitly review-pending — that is the
gate this review serves. I created only the review deliverable; I did not edit W3, the
register, the vault, `.apm/`, contracts, results, or any T1.28 / no-migration artefact, and
I used no active research task as an experiment.

**Direct-evidence checks performed (not taken from summaries):**

| W3 claim | Verified against | Result |
|---|---|---|
| "W1 sections 5.7, 6, 7, 9, 14, 16, 18" carry the cited content (§2) | `design/01-system-architecture.md` | **Accurate.** §5.7 context compiler; §6 canonical/projected; §7 index boundaries; §9 trust boundaries; §14 invariants (inc. inv. 11 on context packets); §16 verification (scenarios 5, 11); §18 W3 constraint mirrors W3 §1.5–1.6 |
| W2 carries "context references … replay positions … F-021/F-022 carrying fields" (§2) | `design/02-task-event-and-artifact-schema.md` §§17, 20, 26, 28 | **Accurate.** §28 W3 constraint; §26 F-021 "binds the governing amendment and omission record", F-022 "Independence grade compares producer/verifier actors, sessions, model families, context manifests, and trace visibility" |
| W6 F-021 = "governing-amendment omission", F-022 = "correlated reviewer contexts" (§2, §18.3) | `design/06-…-audit.md` §6 | **Accurate.** F-021 "Governing amendment omitted" (P1, context/governance); F-022 "Correlated reviewer contexts" (P0, authority/scientific review) |
| External whitepapers are practitioner guidance, not authority (§2) | first-pass review EF-3; W1 §2 | **Accurate and consistent** |
| "measured ~80,000-token Manager initialization burden" (§2) | `01-current-system-evidence.md` §4.1 | **Overstated** — source is "roughly 80,000 tokens under a *simple word-to-token estimate*" of a 60,621-word audited file set. See W3-m7 |
| Currency: reviewed doc is live | `git`: HEAD `c16f5bff`, W3 doc clean/tracked | **Current.** No stale-snapshot addendum needed (unlike W0) |

The accuracy of the cross-references is itself a finding worth recording: the first-pass
round was marred by an "Observation 7" miscitation; W3 has no equivalent. The citations hold.

---

## 2. Major findings

### W3-M1 — `§13.3` compaction tier-qualifier permits governing-amendment loss at R0/R1 *(Major; headline)*

**Claim.** §13.3 states a compaction summary "cannot replace an exact governing rule,
amendment, decision, contract assertion, subject artefact, or review verdict **for R2/R3
work**" (line 419). The trailing qualifier scopes the prohibition to R2/R3, which —
read literally — permits compaction to replace a governing **amendment** in an **R0/R1**
packet.

**Why it crosses a boundary.** This directly contradicts two *unconditional* rules in the
same document: §1 item 7 ("Compaction and memory consolidation … do not supersede governing
decisions, pre-registrations, contracts, results, or reviews", line 29) and §3.3 non-goal
("allowing smaller context to weaken a governing design, hard guardrail, review requirement,
or human decision gate", line 79). It also defeats fixture **F-021** (governing-amendment
omission) at low tiers: R1 is "bounded implementation under stable specification" — exactly
the case where a stale-amendment substitution produces wrong-but-plausible work. The entire
§13 design exists to stop a *summary of a decision* from standing in for *the decision*; the
qualifier reopens that door for two of the four tiers.

**Failure scenario.** An R1 implementation packet for a task whose governing design received
an amendment is compiled; the compactor replaces the "repetitive" design narrative —
including the amendment clause — with a summary that omits the amendment. Because the
prohibition is scoped to R2/R3, no rule is violated; the packet issues; the implementer
builds to the superseded design. F-021's protection never engages because F-021 is exercised
against the R2/R3 path.

**Disposition: fix now (wording).** Make the prohibition unconditional and reserve the
R2/R3-specific clause for the *additional* stricter requirement (exact subject artefact
rendering). Proposed §13.3 replacement for the final two sentences:

> It may replace repetitive non-governing narrative in a packet. A compaction summary may
> **never**, at any risk tier, replace an exact governing rule, amendment, decision,
> contract assertion, or review verdict. **For R2/R3 work it additionally cannot** replace
> the exact subject artefact required for the purpose.

**Affected:** W3 §13.3, §1.7, §3.3; W6 F-021; P-022/P-025.

---

### W3-M2 — `§13.1` lets a declarative-memory item *carry* governing authority *(Major)*

**Claim.** §13.1's memory-item field list includes "explicit statement that the memory
**does or does not carry governing authority**" (line 392). Read literally, a memory item
may be marked `carries_governing_authority: true`.

**Why it crosses a boundary.** This contradicts §5 (declarative memory authority =
"Retrieval aid … never silently governing", line 116; and the §5 footer "A memory of a
decision is not the decision", line 122) and §13.1's own closing sentence ("A governing
decision remains the linked decision/pre-registration/contract object, **not the memory item
summarizing it**", line 402). The safe and clearly-intended invariant is that memory *points
at* authority and never *holds* it. As written, an implementer could add a boolean that makes
a memory item authoritative — a memory could then substitute for an amendment (the M-1
failure by a second route) and the "summary is not the event" principle collapses.

**Disposition: fix now (wording).** Reframe the field as a *reference flag*, never an
authority grant. Proposed §13.1 bullet replacement:

> - whether the memory **references** a governing object (and, if so, that object's canonical
>   ID/hash); the memory item itself never carries governing authority and is never a
>   substitute for the referenced decision, pre-registration, contract, result, or review.

**Affected:** W3 §13.1, §5; W6 F-021/F-024.

---

### W3-M3 — Reference-tokenizer vs provider-tokenizer gap creates an issue-then-reject dead-end *(Major; W3↔W7 seam)*

**Claim.** Budgets are validated at compile time in "managed tokens" via a "versioned
reference-tokenizer count" (§8.1, line 208); the *provider* token count is recorded by W7
and checked at delivery. §16 then lists two different over-budget outcomes: "Mandatory
closure exceeds budget → `context_budget_exceeded`; no packet issued" (compile, line 480)
and "Provider token count exceeds effective ceiling → **Reject delivery**; compile a
compliant packet or reroute through W4" (delivery, line 481).

**Why it crosses a boundary.** Mandatory content can never be dropped (§8.3) and compilation
is deterministic (§8.2). A mandatory-heavy packet sized at, say, 47k *reference* tokens
passes compilation, is **issued** (§12.1 `validated → issued → delivered`), then counts 50k
on the bound provider's tokenizer (cross-provider divergence of 5–15% is routine) and is
rejected at delivery. "Compile a compliant packet" reproduces the identical mandatory closure
→ 50k again → reject again. "Reroute through W4" presupposes a larger evaluated profile that
may not exist. The 20% reserve is explicitly reserved "for the active interaction, provider
instructions, and tool results" (§8.1) — **not** for tokenizer drift — so there is no margin
to absorb the gap, and the over-budget condition surfaces *after issuance* with no safe-options
path, unlike the compile-time row.

**Disposition: amend.** The bound provider/model is known at dispatch (W2 §12.1 / W4). Require
the compiler to validate the mandatory closure against the **bound provider's token count
(or a conservative reference→provider ratio margin)** at compile time, so an over-ceiling
mandatory closure surfaces as `context_budget_exceeded` (compile failure *with* the §8.3 safe
options) rather than a post-issue delivery rejection. Add to §17.1 that W4 supplies the bound
provider tokenizer/ratio to W3 before issuance. Collapse the two §16 rows so the
provider-count check inherits the same safe-options/no-issue behaviour.

**Affected:** W3 §8.1, §10.1 (step 7–8), §16, §17.1; W7; P-025.

---

### W3-M4 — `§18` mandates fixtures that W6 reserves no IDs for *(Major; W3↔W6 coverage)*

**Claim.** §18 "fixes the minimum fixture designs that foundation-critical W6 must
implement" and §18.4 gates W3 acceptance on metrics for: an **orchestrator** scope-collapse
retrieval fixture (§18.1), an **implementer** retrieval fixture (§18.2), **optional-index
deletion equivalence**, **budget-overflow fail-closed**, and **safe-distractor invariance**
(§18.3). W6's catalogue reserves only F-021–F-024 (P-024), of which F-023 (ambiguous
approval) and F-024 (qualitative lifecycle) are unrelated; only F-021/F-022 are context
fixtures. W6's change-gate row anticipates "**later W3 retrieval fixtures**" (W6 §6,
line 289) but assigns them no IDs, priority, or provenance class.

**Why it matters.** §18.4's acceptance metrics ("direct-retrieval equivalence after
optional-index deletion: 1.0"; "independence … accuracy: 1.0 on F-022 cases"; orchestrator
≤48k; implementer/verifier ≤32k) are gated on fixtures that **do not exist in the catalogue
the gate runs against**. A W1-invariant-with-no-W2-enforcement-point is exactly the
cross-spec hole this class of review must flag — here it is a W3-acceptance-metric with no
W6 catalogue entry.

**Disposition: defer with dependency (reserve IDs now).** Add a W6 addendum reserving a W3
retrieval block — proposed **F-025 … F-030** — and map each §18 design to one ID with P0/P1
and a two-axis provenance class:

| New ID | §18 design | Priority | Provenance |
|---|---|---|---|
| F-025 Orchestrator scope-collapse retrieval | §18.1 | P0 | reconstructed (Stage-2 family, minimized/synthetic) |
| F-026 Implementer frozen-rep/vintage retrieval | §18.2 | P0 | reconstructed (F-011/F-012/F-013 bundle, not T1.28) |
| F-027 Optional-index deletion equivalence | §18.3 | P0 | synthetic |
| F-028 Budget overflow fails closed (no mandatory omission) | §18.3 | P0 | synthetic |
| F-029 Safe-distractor invariance | §18.3 | P1 | synthetic |
| F-030 Addendum lineage / cumulative-budget conformance | §12.2, §18.4 | P1 | synthetic |

(F-021/F-022 remain as-is and are the cross-cutting amendment/independence cases.)

**Affected:** W3 §18; W6 §3, §6, §14; P-024.

---

### W3-M5 — Hard-ceiling feasibility on the flagship fixtures is asserted, not measured *(Major; evidence/operations)*

**Claim.** §18.4 requires the orchestrator packet ≤48k and the R2 implementer/verifier ≤32k
"while retaining every mandatory item", with mandatory-source recall = 1.0 as a
*non-aggregated* gate, and asserts "the orchestrator ceiling is at least 40% smaller" than
the ~80k baseline (line 567). No measurement of the **mandatory-closure size** for any
fixture is provided.

**Why it matters.** If the genuine mandatory closure for the scope-collapse orchestration
decision (full governing design + every effective amendment + a 22-member ScopeDefinition +
W0 precedence + decision authority + contracts) exceeds 48k, the §18 gate is *unachievable*:
compilation fails closed (correct, safe) but the acceptance fixture can never pass, and the
pressure to pass it becomes pressure to decompose the very orchestration task whose
cross-cutting evidence is the point (this is W3's own §19.2 Q6). The 80k baseline does not
de-risk this, because it is **not like-for-like** (see W3-m7): 80k is generic Manager preload
(including a 20k-word Tracker W3 reclassifies as a projection); the mandatory closure for one
decision is a different, unmeasured quantity. The R2 implementer side (§18.2: hashes,
transform identity, vintages, parameters, schemas) is plausibly well under 32k; the
orchestrator/R3 side is the live risk.

**Disposition: required change — defer with dependency to W6.** Before the §18 ceilings are
frozen as acceptance gates, W6 materialization must **empirically size the mandatory closure**
of F-025 (orchestrator) and the F-021/F-022 cases. A mandatory closure exceeding its tier
ceiling is a **recorded design signal** — raise the profile ceiling with retrieval-eval
evidence per §8.1, or decompose with explicit cross-cutting-evidence preservation — **not**
a silent compilation failure absorbed as fixture noise. Add this as an explicit precondition
in §18.4 and the §14 W6 materialization sequence.

**Affected:** W3 §8.1, §18.4, §19.2 Q6; W6 §14; P-024/P-025.

---

## 3. Why the strongest attacks *fail* (demonstrated, not assumed)

Per method, where the strongest attack fails I show why rather than inflate it:

- **"Can an index or summary become authority?"** No. Every selected index hit is re-resolved
  to a direct source and re-verified (§10.1 step 6); indexes "cannot establish source
  authority, freshness, or inclusion" (§10.2); mandatory closure uses direct sources only.
  A lying or stale index can only degrade *optional* recall, which is recorded (§10.2). This
  is materially stronger than the first-pass M-9 ("graders trust self-reported flags").
- **"Can a packet hide an omitted governing item under the ceiling?"** No — *except* via M-1.
  Mandatory recall = 1.0 is a non-aggregated gate (§18.4); overflow fails closed with safe
  options and *no issued packet* (§8.3); F-021 exercises the amendment case. The only crack
  is the §13.3 compaction qualifier (M-1) — which is why M-1 is the headline.
- **"Can a nominal verifier inherit the producer's conclusion while the manifest claims
  independence?"** Not silently — the exclusion is machine-checkable (§19.3) and overlap is
  classified (§14, §18.4). The residual is *who authorises* a delta-review exposure (m8).
- **"Can stale memory override a current amendment?"** No — *except* via M-2's literal
  reading. §13.2 ("a procedure conflict blocks or creates an explicit omission") and §5 are
  otherwise unconditional.

The pattern: W3 is airtight on these except for the two §13 wording cracks. Fixing M-1 and
M-2 closes the loop.

---

## 4. Minor findings and editorial

- **W3-m6 — §1 item 8 over-states independence as universal.** "Reviewer independence is
  checkable from two different context manifests" (line 30) reads as always-two-manifests; but
  P-022 (and W2 §17.4) allow R0/R1 *delegated Manager acceptance* with a single producer
  manifest. *Fix:* qualify — "When the assurance grade requires a separate verifier (R2/R3 per
  P-022), reviewer independence is checkable from two context manifests …". (§14.1 already
  defers grading to W4, so this is wording only.)
- **W3-m7 — §2 "measured" overstates an estimate; §18.4 baseline is not like-for-like.** The
  ~80k figure is "roughly 80,000 tokens under a simple word-to-token estimate"
  (`01-current-system-evidence.md` §4.1) of 60,621 audited words of *generic Manager preload*
  (spec/plan/tracker/instructions/skills), explicitly excluding task-specific sources. *Fix:*
  in §2 replace "measured" with "estimated (word-to-token heuristic)"; in §18.4 state the 80k
  is generic preload, not the mandatory closure, so "≥40% smaller" is a conservative floor and
  the real feasibility claim is M-5's (mandatory closure ≤ tier ceiling, to be demonstrated).
- **W3-m8 — §14.2 delta-review exposure has no named authority.** Exposing producer
  conclusions to a verifier "unless a bounded delta-review policy explicitly requires and
  records exposure" (line 454) is an independence-*weakening* act with no stated decision
  authority. *Fix:* require an attributed decision (tier-appropriate per P-022: Manager for
  R2, Stephen for R3) to authorise any delta-review exposure; record as a W4/W5 dependency.
- **W3-m9 — no R0 minimal-manifest profile.** Every packet carries the full ~20-group manifest
  (§9.2) plus candidate-set digest and omission entries (§9.4); for an R0 8k mechanical packet
  this provenance overhead is disproportionate and risks the bypass P-025 warns about. *Fix:*
  define an R0 minimal-manifest profile (identity/source/hash/security mandatory; independence
  evidence and empty conflict/omission summaries droppable), explicitly under P-025.
- **W3-m10 — editorial.** No broken links or malformed markup found. §1 item 8 / §14 use
  "verifier packet" and "independent verifier packet" interchangeably; pick one term. §11.1
  freshness state `conflicted` and §11.3 "unresolved governing conflict" should cross-reference.

---

## 5. Answers to W3's own adversarial questions (§19.2)

The user flagged §19.2 as key. Direct answers, post-fix:

1. **Hide an omitted governing item under the ceiling?** Only through M-1 (R0/R1 compaction).
   Closed by the M-1 fix; otherwise no (mandatory recall 1.0, fail-closed overflow).
2. **Index/summary become authority vs direct evidence?** No (re-resolution + §10.2). Strength.
3. **Verifier inherit producer's conclusion while claiming independence?** Not silently;
   checkable exclusion. Tighten the *authority* to grant delta-review exposure (m8).
4. **Stale memory/procedure override a current amendment/contract?** No, except M-2's literal
   reading; closed by the M-2 fix. §13.2 procedure-conflict-blocks is sound.
5. **Unsafe source copied in because mandatory?** No — §15 fails compilation and reports the
   access gap rather than copying; strong and consistent with W1 §9.6.
6. **Do hard ceilings encourage risky decomposition / loss of cross-cutting evidence?** Yes,
   *if* a mandatory closure exceeds its ceiling (M-5). The mitigation (raise ceiling with
   eval evidence, §8.1) exists but must be *exercised* with measured evidence, not left as a
   theoretical valve. This is the one place the ceiling model could harm the orchestration
   case it most needs to serve.

---

## 6. Decision audit

Every governing decision W3 consumes, with disposition. None requires reversal.

| Decision | W3 interaction | Disposition |
|---|---|---|
| D-001…D-004, D-008 | Durable folder, system redesign, domain-general core, local control plane — all upheld by W3's provider-/domain-neutral, source-linked packet model (§§5–10) | **Keep** |
| D-005 | Phase-boundary transition — W3 §3.3 bars T1.28/active tasks as compiler inputs | **Keep** |
| D-006 | High-reasoning models on risky work — W3 §8 ceilings + §17 routing leave model choice to W4 | **Keep** |
| D-007 | Separate scientific authorities — W3 §14 independence inputs operationalise it | **Keep** |
| P-001 / P-020 | JSONL canonical + single-writer linear ledger — W3 §10.1 binds packets to control-store identity + source position; §11.2 currency on stream advance | **Keep — consistent** |
| P-002 | Neutral root — W3 §6.2 provider-neutral policy; W7 may tighten not weaken | **Keep** |
| P-005 / P-022 | Human-reserved transitions; graded independence (R0/R1 delegated, R2 verifier, R3 Stephen) — W3 §14 consistent; **m6** flags §1.8 wording; **m8** flags un-authored delta-review exposure | **Keep; see m6, m8** |
| P-011 | Multidimensional artefact authority — W3 §9.3/§11 freshness×authority preserved | **Keep** |
| P-012 | Versioned scope completion — W3 §18.1 orchestrator fixture exercises it | **Keep** |
| P-013 | Review binds subject hash — W3 §14 "exact subject artefact/object hashes" | **Keep** |
| P-014–P-019 | Paired evidence, non-compensable graders, deterministic-first, minimized sources, coverage manifests, P0/P1 — W3 §18 honours all (non-aggregated gates) | **Keep** |
| P-023 | Independent property grading / family diversity — W3 §14.2 same-family risk recorded, fails closed | **Keep** |
| **P-024** | Fixture provenance + reserved F-021–F-024 — **W3 §18 demands ≥6 fixtures beyond the reserved set** | **Amend — extend reservation (F-025–F-030) per M-4** |
| **P-025** | Proportional R0/minimal/qualitative — **W3 lacks an R0 minimal-manifest profile** | **Keep; address via m9** |
| P-026 | Parallel spec sequence; clean-paper pilot; T1.28 legacy-owned — W3 §3.3, §17.3 consistent; review gate respected | **Keep** |
| P-027 | W1/W2/W6 acceptance — W3 design authority correctly cites it | **Keep** |
| A-001 / A-002 | T1.28 final-task / Phase-2 authority pending — W3 does not depend on their resolution; §3.3 keeps them out | **No action (out of W3 scope)** |
| Q-001 / Q-002 | Resolved by P-001/P-020/P-002 — W3 consistent | **Keep** |
| Q-004 / Q-006 | Independence diversity / human-approval points — W3 §14 supplies evidence, W4 grades | **Keep (W4 dependency)** |
| Q-003 / Q-005 / Q-007 | Pilot task / runtime boundary / import depth | **Out of W3 scope** |

W3's own §1 nine binding choices: all **Keep**, except choice 7 (compaction) needs the M-1
wording fix and choice 6's memory-class boundary needs the M-2 fix.

---

## 7. Cross-spec consistency matrix

Invariant → enforcement point → fixture/test. Gaps flagged.

| W3 contract | W1 enforcement | W2 enforcement | W6 fixture / test | Status |
|---|---|---|---|---|
| Immutable packet + append-only addenda (§9, §12) | §5.7 immutable context packet refs | `ctx_` prefix (§6.1); §28 "cannot alter state" | F-030 (proposed) | **OK (needs F-030, M-4)** |
| Mandatory closure not displaceable by budget (§7, §8.3) | inv. 11 | §28 governing-amendment refs | F-021, F-028 (proposed) | **OK except M-1 crack** |
| Direct source > index; re-resolve hits (§5, §10) | §7.3, inv. 13 | §21.3 indexes disclose freshness | F-027 (proposed) | **OK (needs F-027)** |
| Source/excerpt identity = commit+hash, not line nos (§9.3) | §6.1 hash refs | §7.1 content_hash; §16.1 manifest | S-009 replay; D-grader | **OK** |
| Currency on source-position advance (§11.2) | §6.2 source position on projections | §9.2 `global_position`; §21.4 drift | S-009/S-010 | **OK** |
| Independence overlap/exclusion evidence (§14) | §9.4 | §17, §20, §26 F-022 fields | F-022 | **OK** |
| Governing material never compacted/memorised away (§13) | §5.7 boundary | §18.4 RuleEvaluation≠Decision | F-021 | **CRACK — M-1, M-2** |
| Budget measured + provider reserve (§8) | §7.3 degraded path | — (deferred to W3) | F-028, + W7 parity | **GAP — M-3 (provider tokenizer)** |
| Restricted data / secrets / transcripts excluded (§15) | §9.6 | inv. 20; §22.4 | P-grader; F-013 | **OK** |
| §18 acceptance metrics | §15 fixture coverage | §26 matrix | **F-021/F-022 only reserved** | **GAP — M-4** |

---

## 8. Fixture coverage gaps and proposed IDs

Summarised from M-4. W6 should add, by addendum (no materialisation): **F-025**
(orchestrator scope-collapse retrieval, P0), **F-026** (implementer frozen-rep/vintage
retrieval, P0), **F-027** (optional-index deletion equivalence, P0), **F-028** (budget
overflow fails closed without mandatory omission, P0), **F-029** (safe-distractor
invariance, P1), **F-030** (addendum lineage / cumulative-budget conformance, P1). Each
carries two-axis provenance (all reconstructed-or-synthetic; none may use T1.28 or live data,
per §18.1/§18.2). This also satisfies W6's own "later W3 retrieval fixtures" placeholder.

---

## 9. §21 review-gate checklist disposition

| §21 item | Disposition |
|---|---|
| Immutable base + append-only addenda model | **Confirmed** (§9, §12; option analysis §4 sound) |
| Information classes distinct | **Confirmed** except the §13.1 memory-authority field (M-2) |
| Mandatory closure complete, not budget-displaceable | **Confirmed** except the §13.3 R0/R1 crack (M-1) |
| Ceilings + 20% reserve explicit/proportionate | **Confirmed as explicit; feasibility unverified (M-5); reserve doesn't cover tokenizer drift (M-3)** |
| Manifest fields sufficient for W4/W5 | **Confirmed** (§9.2, §17) — add R0 minimal profile (m9) |
| Direct sources authoritative; index-deletion preserves mandatory | **Confirmed** — needs F-027 to *test* it (M-4) |
| Compaction/memory cannot supersede governing evidence | **Conditional — fails literally at R0/R1 (M-1) and via memory field (M-2); pass after fixes** |
| Failures close conservatively | **Confirmed** except provider-token over-budget path (M-3) |
| Verifier exposes subject, excludes conclusions | **Confirmed** — bind delta-review authority (m8) |
| Secrets/restricted/transcripts excluded | **Confirmed** (§15) |
| Gate-1 fixtures achieve metrics under ceilings | **Cannot confirm pre-measurement (M-4 IDs, M-5 sizing)** |
| No runtime/migration/active-APM/claim change | **Confirmed** |
| W4/W5 can proceed across the §17 freeze | **Confirmed after M-3 adds provider-tokenizer to §17.1** |

Net: 8 confirmed, 5 conditional on the five Majors. The interface is freezable for W4/W5
once M-3's §17.1 addition and the M-1/M-2 wording fixes land; M-4/M-5 are W6-side dependencies
that do not block the W4/W5 *interface* freeze.

---

## 10. Practicality and proportionality

- **R0 mechanical (8k):** packet budget fine; *manifest* overhead disproportionate (m9). Add
  minimal profile.
- **R1 bounded implementation (16k):** workable; M-1 is the live risk (amendment loss).
- **R2 mathematical implementation (32k):** the §18.2 mandatory set (hashes, transform
  identity, vintages, parameters, schemas) is small structured data — 32k is plausibly ample.
- **R3 design / claim review (48k):** the tight case (M-5). Orchestration mandatory closure
  must be measured before the ceiling is trusted as a gate.
- **Long-running checkpointed compute:** W3 is largely orthogonal (operational context →
  W8); §11.2 currency-on-stream-advance correctly avoids invalidating a packet on unrelated
  events.
- **Non-TDA / small project:** §20 W9/W10 constraint ("minimal R0/R1 … without TDL paths or
  topology assumptions") is correct; the R0 minimal-manifest profile (m9) is what makes it real.
- **Qualitative / mixed-methods:** §5 information classes + F-024 handle it; deterministic
  scientific validation `not_applicable` is honoured. Good.

No bureaucracy-driven bypass risk beyond the R0 manifest weight (m9).

---

## 11. Proposed revision plan

**Immediate corrections (wording; W3 owner can apply directly):**
- M-1 §13.3 — make the governing-material prohibition unconditional; reserve R2/R3 clause for subject artefact.
- M-2 §13.1 — reframe the memory field as a reference flag, never an authority grant.
- m6 §1.8 — qualify independence by grade. m7 §2/§18.4 — "estimated"; clarify baseline. m10 — term consistency.

**Stephen / Manager decisions:**
- M-3 — approve adding the bound-provider tokenizer/ratio to the §17.1 W4→W3 interface and compile-time provider-count validation (touches the frozen interface — needs sign-off before W7).
- M-4 / P-024 — approve reserving F-025–F-030 in a W6 addendum.
- m8 — set the decision authority for delta-review exposure (Manager R2 / Stephen R3).

**Later-work dependencies (do not block W3 acceptance, do block the §18 gate):**
- M-5 — W6 materialisation measures mandatory-closure size for F-025/F-021/F-022 before the ceilings are frozen as acceptance gates.
- m9 — define R0 minimal-manifest profile under P-025 (can land in W3 or W4 profile work).

---

## 12. Residual risks after proposed changes

1. **Ceiling feasibility (M-5)** remains an empirical unknown until W6 sizes the orchestration
   closure. The fail-closed behaviour makes this *safe* but potentially *blocking*; the
   ceiling-raise valve must be used with evidence, not as a rubber stamp.
2. **Provider tokenizer drift (M-3)** is bounded only as well as the chosen conservatism
   margin; a new provider with a much denser tokenizer could still surprise the margin. W7
   parity testing must include worst-case-ratio fixtures.
3. **Delta-review exposure (m8)** is the one sanctioned channel that *weakens* independence;
   even with named authority it deserves an eval fixture (a correlated-context case where
   exposure is wrongly granted).
4. Everything else (index-as-authority, omission-hiding, unsafe-source copy, stale-as-current)
   is closed by the existing design once M-1/M-2 land.

---

## 13. Change log and verification evidence

- **Files created:** this review (`reviews/adversarial-W3-context-review-2026-06-30.md`).
- **Reviewed documents edited:** none (proposals only, per first-pass precedent).
- **Currency check:** `git` — HEAD `c16f5bff`; `git status --porcelain` on the W3 doc = clean
  (reviewed text is the committed text); `c16f5bff` introduced the W3 doc (651 lines) plus the
  W1/W2/W6/register updates and the W1/W2/W6 acceptance record. No stale-snapshot addendum
  required.
- **Citation verification:** W1 §§5.7/6/7/9/14/16/18, W2 §§17/20/26/28, W6 §§3/6, and
  `01-current-system-evidence.md` §4.1 read directly; results in §1 table above.

**Verdict: `accept_with_required_changes`.** Apply M-1 and M-2 (wording) and M-3's §17.1
interface addition before the W4/W5 freeze; carry M-4/M-5 as W6 dependencies of the §18 gate.
The specification is otherwise sound and ready to govern W4/W5 across §17.
