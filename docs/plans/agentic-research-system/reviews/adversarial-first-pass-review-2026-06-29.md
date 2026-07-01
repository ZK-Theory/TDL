---
review: Adversarial first-pass review of the Agentic Research System design
date: 2026-06-29
reviewer: Independent adversarial reviewer (fresh context)
subject_commit: bcc3c0739e17869315f8744a50eac32e995dda13
subject_documents:
  - docs/plans/agentic-research-system/{README,00-master-transition-plan,01-current-system-evidence,02-design-and-deliverables-roadmap,03-decisions-and-open-questions}.md
  - docs/plans/agentic-research-system/transition/W0-legacy-closeout-transition-manifest-2026-06-28.md
  - docs/plans/agentic-research-system/design/{README,01-system-architecture,02-task-event-and-artifact-schema,06-evaluation-observability-and-audit}.md
status: complete
verdict: accept_with_required_changes
documents_edited: none
---

# Adversarial First-Pass Review — Agentic Research System

This review attacks the plan and the three completed first-pass designs (W1 architecture, W2 schema/lifecycle, W6 initial fixture catalogue) against direct evidence. It does **not** rewrite any reviewed document. Findings are separated into factual/editorial corrections, proposed design amendments, decisions requiring Stephen/Manager, and work deferred to later packages. Implementation is out of scope.

**Method note.** I read the full required source set directly (package, W0, W1, W2, W6, Meta-Research-Plan) and verified W0-cited evidence read-only. The two "framing" PDFs were extracted by a read-only delegate and their identity confirmed by direct title-page text. Live repository state was checked against the dated W0 snapshot without touching T1.28 or any no-migration work. No subagent conclusion is reported without my own check of its cited source.

---

## 1. Executive verdict

**`accept_with_required_changes`.**

The design is unusually disciplined and, where I could check it, evidentially honest. The diagnostic base is corroborated (policy drift, unsafe skill sync, single-slot bus, frozen-representation and vintage failures, contract self-approval, stale projections all verified against live files). The architecture's separations — events vs. projections, attempt-completion vs. task-acceptance, structural vs. scientific validation, mechanical RuleEvaluation vs. authorized Decision, multidimensional artefact authority, versioned scope completion — are the right ones and would represent a real improvement over APM. Several of my strongest attacks **fail** against the design (comparative attempts, idempotency, `StatusChanged` prohibition, scope-collapse, last-write-wins), and I say where.

It is not `accept`, for two reasons. First, one architectural tension is genuinely unresolved and becomes **Critical if implemented naively**: a git-tracked, version-controlled JSONL ledger with a single global monotonic position and a global hash chain (P-001 + P-006) is in direct tension with the project's pervasive multi-worktree / branch-per-task execution model. The W1→W2 boundary defers the concurrency algorithm to W2, and W2 only specifies single-instance optimistic concurrency — leaving cross-branch ledger divergence unaddressed (Finding **M-1**). Second, the W0 snapshot is now materially stale (T1.6's cited merge commit was reverted; T1.28 has moved from "prepared, no compute" to active, blocked-then-unblocked on extractor bugs), which must be captured in the dated addendum W0 itself anticipated before A-001 is confirmed (Finding **M-7**).

It is not `rework_required`, because none of the findings overturns the accepted direction or reveals a fabricated evidentiary foundation; all are bounded amendments to a proposal that is explicitly pre-implementation.

**Required changes before W2 acceptance / any implementation plan:** M-1, M-2, M-3, M-5, M-8, M-9, M-10, and the M-7 addendum + EF-2 citation fix (see §8).

---

## 2. Critical and Major findings

Severity key (from the prompt): **Critical** — can corrupt authority/evidence, permit scientifically invalid acceptance, leak restricted information, or make deterministic recovery impossible. **Major** — material ambiguity, missing control, untestable interface, likely operational bypass, or unjustified architecture commitment.

Each finding: claim · evidence · failure scenario · impact · disposition · proposed change · affected decisions/WPs.

---

### M-1 — Git-tracked JSONL ledger vs. single global position + hash chain is unresolved under multi-worktree operation (Major; Critical if implemented naively)

- **Claim.** P-001 makes append-only JSONL canonical *for the reasons that it is version-controlled and Git-readable*; P-006/W2 §9 give every event a single monotonic `global_position` and a global `previous_event_hash` chain; W2 §21/§23 make replay **fail closed** on "duplicate or overlapping positions." A single total order plus a global hash chain assumes one serializing authority. The project's execution model is the opposite: branch-per-task worktrees (`.apm/worktrees/*`, `run/…`, `pipe/…`), Codex worktrees, and a documented parallel-dispatch cap of 3–4.
- **Evidence.** P-001/P-006 (`03-decisions-and-open-questions.md:52`, `:106`); global position + hash chain (`design/02-task-event-and-artifact-schema.md:303-323`, `:560`, `:870-872`); fail-closed on overlapping positions (`design/02-…:936-937`, `:1054`); concurrency algorithm deferred from W1 (`design/01-system-architecture.md:302`) to W2; W2 concurrency is single-instance optimistic only (`design/02-…:541-560`). Multi-worktree is the live norm (`CLAUDE.md` APM_RULES "Parallel dispatch via worktrees … concurrency cap 3–4"; W0 retained worktrees `transition/W0-…:362-368`).
- **Failure scenario.** Two task branches each run an ARS command-service instance against their own working tree. Each reads the canonical tail at `global_position = N` and commits a new batch file named with start-position `N+1` (W2 §9.1 names files by start position). Atomic-rename-per-file prevents *in-file* corruption (P-006) but not *cross-branch* allocation of the same position in two different files. On `git merge`, both `…N+1-….jsonl` files coexist → replay sees overlapping positions / a broken `previous_event_hash` fork → **authoritative projection stops** (W2 §23). The ledger the whole design treats as canonical cannot be merged.
- **Impact.** Deterministic recovery becomes impossible for exactly the workflow the system targets; "rebuild from genesis" (W1 §16.2 sc.8) fails after any parallel-branch advance. This is the architecture's deepest tension and the one most likely to bite in week one.
- **Disposition.** **Amend decision (required before implementation).** Resolve the storage model explicitly; do not leave it to "W2 scope" when W2 does not address it.
- **Proposed change.** Choose and document one: (a) **per-stream/per-actor position partitioning** — replace the single `global_position` total order with per-stream monotonic versions (already present as `stream_version`) plus a merge-time reconciliation that orders only within a stream, dropping the global hash chain in favour of per-stream chains; or (b) **canonical ledger is a single shared store outside all worktrees** (not branch-tracked), with Git holding only *projections* for inspectability — which contradicts P-001's "version-controlled JSONL is canonical" rationale and must be stated as such; or (c) **single-writer-per-project enforced operationally** (one command service, worktrees submit commands to it over a local port/socket) with an explicit prohibition on per-worktree ledgers. Add the chosen rule to W1 §6.3 and W2 §13, and add fixture **S-012** (§6).
- **Affected.** P-001, P-003, P-006; Q-001; W1, W2, W6, W8, W9.

---

### M-2 — Canonical store placement vs. the main-checkout/worktree split reintroduces F-003 (Major)

- **Claim.** The single-writer "repository-local command lock" and `.research-system/` root are specified without saying where they live relative to git worktrees — the exact ambiguity F-003 exists to kill.
- **Evidence.** "repository-local lock" (`design/01-…:302`, `design/02-…:289`); `.research-system/` layout with `events/`, `runtime/` (`design/01-…:310-326`); F-003 main-checkout/worktree split (`01-current-system-evidence.md:154-163`, W0 `transition/W0-…:391`). The design *names* control/code/result/cache roots in dispatch (W1 §7.2; W2 §12.1) but never classifies `.research-system/` itself.
- **Failure scenario.** If `.research-system/events/` is a tracked path, each worktree gets an independent copy → M-1 divergence. If it is gitignored `runtime/`, a worktree process must write "across" to the main checkout's store — the precise wrong-root pattern F-003 forbids, now at the level of the control plane rather than the bus.
- **Impact.** The control plane could become the new instance of the failure it was built to prevent.
- **Disposition.** **Amend decision (required).** State whether `.research-system/` canonical subdirectories are single-instance (main-checkout-only, addressed by M-1c) or per-worktree (addressed by M-1a). Bind the control root into the same typed root-binding F-003/W2 §12.1 already define, so a worktree cannot silently redirect the ledger.
- **Affected.** P-002, P-003; Q-002; W1, W8, W9; fixture F-003.

---

### M-3 — The compatibility adapter cannot prevent dual authority against legacy *direct* writers (Major)

- **Claim.** P-004 forbids `dual_owned`; W1 §10.2 lets the adapter write a successor-owned `task.md`/`report.md` only when the existing file is empty or carries the same ownership marker. But legacy APM agents edit bus files **directly by design** (they do not submit commands), and they remain unmodified under the no-migration rule. The no-dual-authority guarantee is enforced only against ARS-side writers.
- **Evidence.** P-004 (`03-…:82-90`); guarded-view rules (`design/01-…:432-443`); legacy agents edit state directly is the very thing P-003 contrasts itself against (`03-…:76`); legacy bus is single-slot and overwrite-prone and remains legacy-owned (`transition/W0-…:309`, `:356-360`). Live corroboration: `7c8de855` "harden APM bus write ownership" added ownership checks to the `apm-communication` **skill prose** (both `.claude` and `.agents` copies) — i.e., the only current defense is an instruction an agent may ignore, not a mechanical gate.
- **Failure scenario.** A successor-owned task's compatibility `report.md` shares the slot a still-installed legacy Worker skill writes/clears. The legacy Worker, following its unchanged protocol, overwrites the slot without checking the ARS ownership marker. Two authorities have now written the same canonical-adjacent file; the adapter's "fail closed on foreign content" only fires on the *next ARS* write, after the legacy overwrite already happened.
- **Impact.** The redesign's headline guarantee ("no task or report can be silently overwritten," success criterion 1) is conditional on legacy cooperation it cannot compel.
- **Disposition.** **Amend decision (required).** Make compatibility views **non-shared by construction**: a successor-owned task renders to a *distinct* path the legacy tooling never writes (e.g. `.apm/bus/<agent>/ars.task.md`), or the legacy slot is made read-only for the duration of successor ownership via a PreToolUse hook that blocks non-adapter writes to that specific slot. State plainly that "no dual authority" holds only when every writer to a shared path is ARS-mediated, and that sharing a legacy-writable slot is therefore prohibited for successor-owned tasks.
- **Affected.** P-003, P-004; W1 §10, W7, W9; fixtures F-001/F-002, S-006.

---

### M-4 — Human authority is a structural bottleneck and "independent review" is partly unattainable for a solo operator (Major)

- **Claim.** P-005 reserves five transition classes for Stephen alone; D-007 + W4/W5 require independent review for R2/R3. With a single human authority, "independence" reduces to model/context diversity, not human independence — and every R3 dispatch, decision reversal, claim promotion, pre-reg change, and provisional→authoritative upgrade routes through one person.
- **Evidence.** P-005 (`03-…:92-100`); D-007 (`03-…:38-41`); §9.1 human boundary and §9.4 independent-review boundary (`design/01-…:386-400`); the operator is singular throughout success criteria (`00-master-transition-plan.md:521`). The prompt names this attack directly ("review independence that exists only on paper because contexts/models share the same source error"; "human authority … operationally usable rather than a bottleneck").
- **Failure scenario.** Under deadline, the single human approves both keys; the "independent verifier" is another agent the same human prompted, sharing the human's framing error. The system records two attestations and zero genuine independence. Or: approval volume makes Stephen the throughput limiter, and operators route work to lower tiers to avoid the gate (the bypass the design's own §9 risk table warns of).
- **Impact.** A core control (two-key validity, D-007) is partly aspirational for N=1; if the spec implies human independence it cannot deliver, it manufactures false confidence — precisely the §9 "false confidence from schemas" risk, one level up.
- **Disposition.** **Amend decision + Stephen decision.** State honestly that for a solo programme the realized control is **cross-family/cross-context** verification (D-006, Q-004), not human independence, and design the eval to grade *that* (see M-8). Budget P-005 approval points to genuine forks only (Q-006), and define a delegated-acceptance envelope (§9.1) precise enough that the Manager can clear R0/R1 and routine R2 without Stephen, reserving Stephen for R3 and the five reserved classes — so authority is "explicit but usable," not a queue.
- **Affected.** D-006, D-007, P-005; Q-004, Q-006; W4, W5.

---

### M-5 — Review independence is *attested*, not *checkable* (Major)

- **Claim.** W2 records independence as a self-declared attestation/relationship field; nothing binds it to a verifiable property of the verifier's context. The grader therefore grades a declaration.
- **Evidence.** "independence attestation" in the verdict (`design/02-…:757`), "independence relationship to the subject" in the actor record (`design/02-…:853`), reviewer "independence constraints" in the request (`design/02-…:733`); context compilation deferred to W3 (`design/01-…:209`). F-014 graders are `D,T,H` over declared authority (`design/06-…:173`).
- **Failure scenario.** An implementer and a "verifier" run on the same model family with a context packet derived from the implementer's own trace. Both records assert independence; F-014 passes; the shared blind spot survives — the F-016 conceptual-direction error the eval exists to catch.
- **Impact.** F-014/F-016 can pass while the independence they certify is fictional; the "no R2/R3 self-approval" invariant (W1 §14.9, W2 §25.13) is only as strong as an honest declaration.
- **Disposition.** **Amend decision (required).** Make independence a *checkable property of the context packet*: the verifier's `ctx_id` must be distinct, compiled from canonical sources, and carry **no `causation_id` linkage to the implementer's attempt/trace**; W6 must grade context-packet provenance (different compiler inputs, no implementer-trace inclusion), not the attestation. Add this as an explicit W3 constraint and a W6 grader requirement.
- **Affected.** D-007, P-013; W2 §17/§20, W3, W5, W6; fixtures F-014, F-016; new F-022 (§6).

---

### M-6 — W2 §18.4 lets a mechanical RuleEvaluation stand without a Decision, in tension with the project's audited lesson (Major)

- **Claim.** W2 §18.4 makes a deterministic pre-registered outcome mapping a `RuleEvaluation` and requires a separate `Decision` "only when policy assigns interpretation, claim, amendment, or migration authority beyond the mechanical mapping." This appears to pre-settle the open W0 question (`[RESULT]` vs `[DECISION]` lock convention) that W0 explicitly routes to W5, and it sits against the project's hardest-won provenance lesson.
- **Evidence.** W2 §18.4 (`design/02-…:801-805`); the open question W0 hands to W5 (`transition/W0-…:349`); the audited lesson is in the live observation log: a different-*object* result masqueraded as a mechanical fix because the entry named the issue but not the referent, surfacing only weeks later (skill-observations Obs 13–15), and "an experiment-change must be logged as a decision *at* the change or its reasoning becomes unrecoverable" (Obs 14). T1.9b — the case W2 §18.4 cites approvingly — is the same family.
- **Failure scenario.** A Worker's `[RESULT]` is accepted as a prose-lock landing via a RuleEvaluation that records "rule, inputs, output, evidence hash," but the *inputs* are a different comparison than the governing rule names (Obs 13's exact failure). Because no Decision forced a referent attestation, the substitution is invisible until downstream prose uses it.
- **Impact.** The mechanism that should prevent silent object-substitution is made optional precisely where the project has already been burned.
- **Disposition.** **Amend decision (required) + defer to W5.** W2 §18.4 should (a) require any RuleEvaluation that *feeds a claim or prose lock* to carry a referent attestation (which two clusterings / estimand / metric + denominator the inputs actually are) and an accompanying `claim_promotion` Decision, and (b) explicitly state the broader `[RESULT]`-vs-`[DECISION]` policy is W5's to set, rather than appearing to resolve it. Note: this *strengthens* §18.4's existing "exact inputs + evidence hash," which is good and already partially addresses Obs 13.
- **Affected.** P-005, P-013; W2 §18, W5; fixtures F-015, F-016, F-019; new F-023 (§6).

---

### M-7 — The W0 2026-06-28 snapshot is materially stale; A-001 cannot be confirmed against it without a dated addendum (Major)

- **Claim.** Live state diverges from W0 in at least three material ways. Per the prompt, this requires a **proposed dated addendum**, not a rewrite of the snapshot.
- **Evidence (read-only, live).**
  1. **T1.6 merge anchor moved.** W0 cites `551a9888` as T1.6's merge (`transition/W0-…:135`, `:92`). Live: `551a9888` ("Merge T1.6 … into main", 2026-06-28 10:29) was a *premature* merge, **reverted** by `17ae8c91` ("revert premature T1.6 merge (551a9888) — re-route through CodeRabbit-gated PR", 11:00) and re-merged via **PR #55** at `7e798464` (11:14). T1.6 remains authoritative, but the cited anchor now points at a reverted commit. (This matches the project's standing rule that CodeRabbit must review before merge.)
  2. **T1.28 is no longer "prepared, no compute active."** W0 §6.2 records no task log, no producing JSON, no active compute (`transition/W0-…:204-219`). Live: `e7204373` "T1.28 BHPS 'data blocker' verified as extractor bugs; fix-extractor follow-up dispatched"; `results/panel_methodology/fdr/` now holds `bhps_compute_log_2026-06-28.txt`, `bhps_cohort_nssec_log_2026-06-29.txt`, `bhps_gender_usoc_rm_log_2026-06-29.txt` (last-written 21:06 today), `subgroup_checkpoints/`, and `run_gender_usoc_rm.ps1`. No final `stratified_w2_*.json` and no `.apm/memory/stage-01/task-01-28.log.md` yet. T1.28 is mid-execution and was blocked on an extractor defect — directly bearing on A-001.
  3. **A bus-ownership control was backported to legacy.** `7c8de855` "harden APM bus write ownership" (2026-06-28 22:32) postdates the §4.3/§4.5 evidence snapshot and partially pre-implements P-009/F-001/F-002 *as skill prose* (see M-3).
- **Impact.** A reviewer confirming the W0 review gate (§14, "T1.28 is the sole remaining Stage 1 task") against the snapshot would be reasoning from stale state; the A-001 confirmation condition ("no additional Phase 1 task remains open after T1.28 review and closeout") is now entangled with an in-flight extractor fix.
- **Disposition.** **Propose a dated W0 addendum (do not rewrite the snapshot).** Record items 1–3, restate that T1.28 remains legacy-owned and untouched, and flag the A-001 confirmation to Manager/Stephen. **Stop-condition observed:** I did not alter W0, T1.28, or any no-migration artefact.
- **Affected.** A-001, A-002; W0, W1 §10.4 (post-T1.28 reconciliation gate), W9.

---

### M-8 — W6 model graders for scientific fixtures are not required to be cross-family from the producer (Major)

- **Claim.** F-012/F-016/F-019 use model graders (`M`) defined as "independent model … independently compiled context," but the catalogue does not pin grader *model family* distinct from the producer; Q-004 mandates cross-family only for R3.
- **Evidence.** Grader class M (`design/06-…:129`); fixtures F-012 `D,T,R,M`, F-016 `D,R,M`, F-019 `R,M,H` (`design/06-…:171,175,178`); Q-004 default "Different family for R3" (`03-…:290-291`); calibration requires blinded examples but not producer-correlation cases (`design/06-…:296-308`).
- **Failure scenario.** Producer and M-grader are the same family; both share the inductive bias that makes a label-invariant null look significant (F-012) or a density-peak inversion look correct (F-016). The grader passes the defect.
- **Impact.** The evals meant to catch model-correlated scientific error are themselves model-correlated — the §9 "model monoculture" risk inside the safety net.
- **Disposition.** **Amend decision (required).** Bind M-grader family-diversity into the fixture grader spec for scientific-validity fixtures, and require the calibration blinded set (§13.6) to include **producer-correlated error cases**, not just generic positive/negative/ambiguous.
- **Affected.** D-006, P-015, P-016; Q-004; W4, W6.

---

### M-9 — Deterministic graders can certify a scientific property by trusting a self-reported "check passed" event (Major)

- **Claim.** For fixtures whose control is a scientific property, the deterministic graders (`D`) as written can pass by observing that a "check ran / passed" event exists, without independently establishing the property — the exact failure mode the project has already hit.
- **Evidence.** F-012 null-invariance post-control "Preflight demonstrates the null changes the tested object" graded `D,T,R,M`; F-011 frozen-representation "any fit call or mismatched fingerprint blocks acceptance" graded `D,T,R`; F-008 cost-probe graded `D,T,O,R` (`design/06-…:167,170,171`). The realized failure: a broken construction returned a *plausible constant* (max-achievable ARI = 1.0 from an `n<2 → 1.0` fallback) that passed every software test and made normalisation vacuous (skill-observations Obs 20); an mtime/vintage signal over-fired while only a content canary was decisive (Obs 18).
- **Failure scenario.** A producer emits `null_invariance_check: passed` from a path that silently no-ops (degenerate fallback). The `D` grader sees the event and passes; the eval certifies a vacuous null-check.
- **Impact.** The harness eval inherits the in-range-constant blind spot it exists to detect.
- **Disposition.** **Amend decision (required).** For scientific-property fixtures, the `D`/`T` graders must independently recompute or *bound* the property (e.g. confirm the shuffled object's hash actually differs; confirm a normalised statistic lies strictly inside the open interval, excluding the degenerate constant a fallback would emit) rather than trusting a producer-emitted flag — and the fixture must include a mutation that exercises the degenerate path (§13.3 already asks for one mutation; require *this* one).
- **Affected.** P-014, P-016; W5, W6; fixtures F-008, F-011, F-012.

---

### M-10 — F-001 (and partly F-002) cannot be materialized from preserved evidence and is mislabeled "historical" (Major)

- **Claim.** F-001's failure mode (single-slot overwrite) destroyed its own evidence; the original overwritten T0.3 message is gone *because* it was overwritten. It therefore cannot be a "historical" fixture materialized from preserved files; it can only be a synthetic reconstruction from Tracker prose.
- **Evidence.** F-001 sourced to "T0.3 bus overwritten by T0.12" — known only as Tracker narrative (`01-current-system-evidence.md:126`, `transition/W0-…:389`); P-014 requires "demonstrate the intended pre-control failure … under versioned inputs and oracles" (`03-…:194`); W6 lists F-001 as a historical fixture (`design/06-…:160`). The prompt's test: "whether its pre-control failure is demonstrable rather than retrospective storytelling."
- **Failure scenario.** A fixture author tries to bind F-001 to "exact minimized files and hashes" (W6 §6 instruction) and finds none exist — the overwriting *is* the data loss. The fixture is silently authored from a reconstructed input while labeled as historical evidence, weakening its calibration claim.
- **Impact.** A P0 release blocker rests on storytelling unless explicitly reconstructed; conflates "we remember this happened" with "we can reproduce the input state."
- **Disposition.** **Amend decision (required, small).** Reclassify F-001 (and the overwrite half of F-002) as **synthetic-reconstructed** with explicitly synthesized inputs; P-014's paired-evidence requirement is then met by the reconstruction, and the synthetic S-001/S-006 conformance scenarios become its real calibration anchor. Note this is the *only* fixture so affected; the others (F-004 stale log, F-005 scope, F-011 cells, F-013 vintage, F-007/F-008 benchmark) do have preserved artefacts (verified).
- **Affected.** P-014, P-019; W6; fixtures F-001, F-002.

---

## 3. Minor findings and editorial corrections

- **EF-2 — "Task Observer Observation 7" is miscited (Minor; recurs 3×).** W2 §2 and §14.3 and P-009 attribute to "Task Observer Observation 7" the principle "bus writes need explicit ownership and collision failure, not only read-before-write" (`design/02-…:37`, `:606`; `03-…:142`). The canonical log's Observation 7 is "Manager delegated contract-YAML authorship to the Worker" — *contract authorship*, not bus ownership; **no** observation in the log states the cited principle (verified). Worse, Obs 7's actual content supports **F-014/§4.8** (self-approved contracts), suggesting a citation swap. *Disposition:* proposed correction (not applied — it underpins a decision's evidence): cite F-001/F-002 + `01-current-system-evidence.md` §4.3 for P-009's bus-ownership principle, and cite Observation 7 where contract-authorship independence is discussed. The principle itself is independently supported, so no design change follows.
- **EF-3 — "Framing material" PDFs are third-party vendor whitepapers; evidence register cites them by bare filename (Minor).** `Day_1_v3.pdf` = "The New SDLC With Vibe Coding" (Osmani, Saboo, Kartakis) and the Day-3 PDF = "Context Engineering: Sessions, Memory" (Milam, Gulli, Nawalgaria) are Google "Agents Whitepaper Series" practitioner documents (May 2026), **verified by title-page text**, not bespoke project framing notes. The design uses them correctly — the principles attributed to them (six context types, tests-vs-evals, static/dynamic split, async background, declarative/procedural memory, multi-agent handoff, model routing) *are* present; architecture-specific choices (JSONL, single-writer, event batches, domain packs) are grounded in the W0 corpus, **not** the PDFs (verified — these documents contain no such mandate); and §6 correctly subordinates external material below repository evidence. *Disposition:* editorial — `01-current-system-evidence.md` §2.1 should name authorship/venue and label them practitioner vendor guidance of limited authority, so a future reviewer is not misled by the prompt's "Original framing material" label.
- **EF-4 — Evidence-doc claims about the Meta-Research-Plan are accurate (no finding).** The plan does call Mapper colouring a "causal geography" (`Meta-Research-Plan-23-03-2026.md:33` → F-019), does forecast the Wasserstein/null work as completing "in minutes" (lines 19–20, 141 → §4.10/§2.2), and is calendar-staged. Supported.
- **EF-5 — §4.5 stale-path detail confirmed (no finding; out-of-scope to fix).** `CLAUDE.md` references `.apm/Implementation_Plan.md`; the real file is `.apm/plan.md` (`.apm/metadata.json` records `v1.0.1`, plan file `plan.md`). The evidence doc's "current files use different paths" is correct. `CLAUDE.md` is an unrelated tracked-modified file and outside this review's scope; not edited.
- **m-A3 — Hash chain vs. routine git history operations (Minor→Major depending on storage model).** If event batches are git-tracked (P-001), a `git revert`/`rebase` of an event file breaks `previous_event_hash` and replay fails closed — correct behaviour, but it means the canonical ledger cannot tolerate the history operations the project performs (the T1.6 revert is a live example). Folds into M-1's storage decision; record it there.
- **m-A5 — Topology leaks into the domain-neutral portfolio object (Minor).** `00-master-transition-plan.md:152` lists "topology or specialist method's incremental value" as a per-study *core* portfolio field, mildly violating D-004/§5.8 ("core does not hard-code persistent homology"). W1 §5.1's portfolio catalogue is clean. *Fix:* generalize the master-plan field to "specialist-method incremental value."
- **m-B6 — Accepted artefact can become unavailable when it is a gitignored intermediate (Minor).** The Availability dimension (W2 §16.2) correctly represents `missing`, but the project routinely deletes gitignored caches/intermediates; an accepted result that was such an intermediate becomes `missing` while still `accepted_for_scope`. *Fix:* the retention class should distinguish "regenerable from pinned script+inputs (hash-verified)" from "irreproducible," so a missing-but-regenerable artefact does not block downstream (ties to the canary lesson, Obs 16/18).
- **m-B8 — "Rebuild from genesis = acceptance test" forces unbounded reducer backward-compatibility (Minor→Major over the multi-year horizon).** §21.2 stops replay on unknown major versions and §21.3 keeps genesis-replay as *the* acceptance test, so every historical major-version reducer must be retained forever. *Fix:* permit verified-snapshot-anchored replay to retire pre-snapshot reducers, with periodic genesis replay as an audit rather than the sole acceptance test.
- **m-B9 — Lease expiry on a personal/sleeping machine (Minor; W8).** Deterministic `ExpireLease` (W2 §12.3) is correct, but on a single personal machine running a multi-day job, no operator submits it; a slept process can resume past nominal expiry as a valid attempt. Flag for W8 heartbeat/operator design.
- **m-C2/C6 — Gameable/obscurable graders (Minor).** F-007's hidden-work oracle can be satisfied by emitting required progress events before doing hidden compute; add an `O` cross-check of wall-time/CPU vs. declared bounded work. The §10 dashboard's "first-pass acceptance %" can mask all-P0 failures; require P0-critical status displayed as a separate non-aggregated gate (the per-fixture non-compensable rule is already correct; this is about the human-facing roll-up).
- **m-B12 — Exception escape-hatches (Minor).** `methodological_exception`/`policy_exception` Decisions and the `other_typed_extension` blocker are authority-gated bypass surfaces; add a trajectory fixture exercising "exception used to bypass a critical control" so the gate is itself evaluated.

No broken links or malformed Markdown were found in the reviewed documents; none were edited.

---

## 4. Decision audit

Disposition vocabulary: **keep** · **keep+amend** (change required/recommended, direction stands) · **reject** · **defer**. Stephen-approved items (D-001–D-008, P-001–P-005) are challenged only with concrete contrary evidence; none warrants reject.

### Accepted directions

| ID | Disposition | Rationale |
|---|---|---|
| D-001 | keep | Sound; this review is itself the durable-folder pattern paying off. |
| D-002 | keep | Scope breadth justified by the evidence. |
| D-003 | keep | Preserved mechanisms verified to exist and be valuable. |
| D-004 | keep+amend | Direction sound; fix the topology leak into the core portfolio object (m-A5) and the absence of any qualitative fixture (M-? → F-024, §7). |
| D-005 | keep | Phase-boundary transition is appropriate; M-7 shows the boundary is not yet sealed (as W0 already says). |
| D-006 | keep+amend | Keep high-reasoning routing; reinforce with grader family-diversity (M-8). |
| D-007 | keep+amend | Separate authorities is right; state the solo-operator limit honestly (M-4) and make independence checkable (M-5). |
| D-008 | keep | Local inspectable control plane is the correct first step; M-1 is *how*, not *whether*. |

### W1 proposals (Stephen-approved 2026-06-28; Manager confirmation pending)

| ID | Disposition | Rationale / required change |
|---|---|---|
| P-001 | keep+amend (required) | Canonical JSONL is right, but resolve the git-tracked-vs-single-global-order tension (M-1) before implementation. |
| P-002 | keep+amend | Neutral root accepted; classify `.research-system/` placement vs. worktrees (M-2) and name framing-source provenance (EF-3). |
| P-003 | keep+amend (required) | Serialized command boundary accepted; specify cross-worktree writer behaviour (M-1/M-2) and that legacy direct writers defeat it on shared paths (M-3). |
| P-004 | keep+amend (required) | Exclusive ownership accepted; "no dual authority" must be enforced by *non-shared* compatibility paths, not legacy cooperation (M-3). |
| P-005 | keep+amend | Reserved human transitions accepted; define the delegated-acceptance envelope so authority is usable, not a bottleneck (M-4). |

### W2 proposals (proposed)

| ID | Disposition | Rationale / required change |
|---|---|---|
| P-006 | keep+amend (required) | Atomic batch-per-command is good; address cross-branch position allocation (M-1). |
| P-007 | keep | Prefixed UUIDv7 + scoped aliases handle cross-project/import collision; no contrary evidence. |
| P-008 | keep | Separate Task vs. operational state machines — strong; directly fixes the §4.2 state/sequence mismatch. |
| P-009 | keep+amend | Immutable messages / clearing-as-ack is sound; **fix the Observation 7 citation** (EF-2). |
| P-010 | keep | Partial/reopen epochs fit long mathematical runs; defends the T1.6/T1.9b cases. |
| P-011 | keep+amend | Multidimensional artefact authority — strong; add regenerable-vs-irreproducible retention (m-B6). |
| P-012 | keep | Versioned ScopeDefinition completion — strong; F-005 evidence verified (22 tasks, T2.22 gate, "Stage 2: Complete" label). |
| P-013 | keep+amend (required) | Hash-bound verdicts are right; make review independence a checkable context-packet property, not an attestation (M-5). |

### W6 proposals (proposed)

| ID | Disposition | Rationale / required change |
|---|---|---|
| P-014 | keep+amend (required) | Paired pre/post evidence is right; reclassify F-001/F-002-overwrite as synthetic-reconstructed (M-10). |
| P-015 | keep | Non-compensable critical graders — strong and correctly specified. |
| P-016 | keep+amend (required) | Deterministic-first is right, but a deterministic grader must not certify a scientific property via a self-reported flag (M-9); model graders need family-diversity (M-8). |
| P-017 | keep | Minimized/redacted sources — sound and consistent with the no-migration data boundary. |
| P-018 | keep | Change-to-fixture coverage manifests — sound; reinforced by the new fixtures in §6. |
| P-019 | keep+amend | P0/P1 priority sound; re-tier after M-10 reclassification and place the new critical fixtures (S-012, F-022/F-023) appropriately. |

### Assumptions and bounded decisions

| ID | Disposition | Rationale |
|---|---|---|
| A-001 | confirm-with-addendum | T1.28 is now active and was blocked-then-unblocked on extractor bugs; confirm only via the M-7 addendum and live Manager statement. |
| A-002 | keep (unchanged) | The 14 unlogged Stage-2 tasks remain a live `decision_required`; verified (22 in plan, ≤8 logged). |
| Q-001 | resolved (P-001) + reopen sub-question | Reopen only the git-tracking sub-question per M-1. |
| Q-002 | resolved (P-002) + amend | Add `.research-system/` worktree placement (M-2). |
| Q-003 | keep | Pilot rubric is sound; the M-1 storage decision should be exercised by the pilot. |
| Q-004 | keep+amend | Strengthen with grader family-diversity (M-8). |
| Q-005 | keep | Generic interface + two implemented adapters is proportionate. |
| Q-006 | keep+amend | Tie to the delegated-acceptance envelope (M-4). |
| Q-007 | keep | Selective import (not full normalization) is correct and matches the W0 import policy. |

---

## 5. W1–W2–W6 consistency matrix

Columns: W1 invariant (§14) → W2 enforcement mechanism → W6 fixture. ✓ = coherent; ⚠ = gap/finding.

| W1 invariant | W2 enforcement | W6 fixture | Status |
|---|---|---|---|
| 1 transition has identity/actor/time/reason/position | Event envelope §9.2; authority snapshot §20 | graded across all | ✓ |
| 2 state reconstructible w/o DB/session/bus | Replay §21; snapshots are indexes §21.3 | S-009 | ✓ |
| 3 exactly one canonical owner per active task | Ownership modes §22.3; expected-version §13.2 | F-001, S-006 | ⚠ cross-worktree owner unenforced (M-1/M-2); legacy direct write (M-3) |
| 4 no view authorizes its own transition | Projection ≠ command §5; drift §21.4 | F-004, F-006, S-009 | ✓ |
| 5 no agent edits canonical events | Command-only mutation §8 | (all) | ✓ |
| 6 no provider file is sole policy | Adapter boundary §22.3; policy objects | F-020 | ✓ |
| 7 no domain pack changes core/grants authority | Pack boundary (W1 §5.11) | (W10-deferred) | ⚠ no fixture this pass |
| 8 no execution success implies acceptance | Attempt vs Task §12.4, §25.7 | F-007, S-003 | ✓ |
| 9 no R2/R3 implementer self-approves | Review authority §17.4 | F-014 | ⚠ independence attested not checked (M-5) |
| 10 no silent overwrite of predecessor | Supersession §16.4/§19; immutable batches | F-001, F-018 | ⚠ legacy shared-path overwrite (M-3) |
| 11 context packets identify sources/omissions | (W3 — referenced) | F-003–F-006, F-011–F-019 | ⚠ W3-deferred; amendment-omission fixture missing (F-021) |
| 12 restricted data/secrets stay out | Boundary §9.6; rejection §23 | F-013 (`P`); §12 | ✓ |
| 13 optional indexes disposable + disclose freshness | §21.3, §7.3 | S-009 | ✓ |
| 14 compatibility collisions fail closed | §14.3 ownership markers | S-006, F-001 | ⚠ only vs ARS writers (M-3) |
| 15 legacy history governed until cutover | Two-step observe/adopt §22.2 | F-018 | ✓ |

**Additional cross-spec gaps (W2 mechanism with no W6 fixture, or W6 oracle needing an undefined record):**

- W2 §18.5 "amendment after producing work cannot be a pre-registration" — **no fixture**; live-relevant (T1.28 carries a 2026-06-27 amendment). → propose **F-021** (and a synthetic check).
- W2 §19.2 supersession-cycle rejection — **no fixture**. → propose **S-015**.
- W1 §16.2 sc.6 / W2 §12 "provider outage → task waits, no sub-threshold fallback" — **no fixture** (F-020 tests drift, not outage). → propose **S-016**.
- F-008's oracle ("validates sample size, backend, worker scaling, memory") requires a **feasibility/scaling record** that W2 does not define (it is W8 scope). The fixture is ahead of its schema; W6 §1 acknowledges executable design is deferred, but flag the dependency so F-008 is not "materialized" before W8 lands.
- Cross-branch ledger divergence (M-1) — **no W2 mechanism and no W6 fixture**. → propose **S-012** (highest priority).

---

## 6. Fixture coverage gaps and proposed new fixture IDs

The prompt's candidate missing families, checked against the catalogue, yield these gaps (all materializable without T1.28 or restricted data):

| New ID | Family | Why needed | Priority |
|---|---|---|---|
| **S-012** | Divergent git branches generate colliding event positions | Tests the M-1 tension directly; without it the catalogue cannot certify the canonical store under the project's own workflow. | P0 |
| **S-011** | Writer lock loss / interrupted atomic rename | Crash-window behaviour (W2 §23) is asserted but unexercised. | P0 |
| **S-013** | Malformed / unauthorized adapter command rejected | W1 §9.8 adapter boundary is untested; §3.3 currently excludes it. | P0 |
| **S-014** | Backup/restore + multi-machine synchronization | T0.3 is exactly this; ties A1/A2; no current coverage. | P1 |
| **S-015** | Supersession cycle rejected | W2 §19.2/§23 rule has no fixture. | P1 |
| **S-016** | Provider/model outage for R3 → task waits, no sub-threshold fallback | W1 invariant with no fixture. | P1 |
| **F-021** | Context compiler omits a governing **amendment** | T1.28's 2026-06-27 amendment is a live case; stale/omitted governing doc is the F-004/Obs-12 family. (W3-dependent; name now.) | P1 |
| **F-022** | Correlated "independent" reviewers share the same source error | Mechanizes M-5/M-8; the independence control's own failure mode. | P0 |
| **F-023** | Ambiguous human approval ("looks good"/`Success`/`Done`) not adopted as a P-005 decision | The W0 import boundary and EF-1 (premature merge) family; human-approval-captured-ambiguously. | P1 |
| **F-024** | Qualitative / non-computational research artefact lifecycle | D-004 claims support for qualitative/mixed-methods work; **zero** fixtures and no record shape exercise it (see §7). | P1 |

Existing fixtures needing reclassification: **F-001** (and the overwrite half of **F-002**) → synthetic-reconstructed (M-10).

---

## 7. Practicality and proportionality

| Workload | Expected overhead | Risk of bypass | Recommendation |
|---|---|---|---|
| **R0 mechanical, reversible** | Full command/event/receipt/review envelope is heavy for a one-shot reversible action. | High — operators will edit a file directly rather than submit a command for a trivial change. | Define an **R0 fast-path**: lightweight command, deterministic graders only, no independent review; still append-only but minimal envelope. |
| **R2 mathematical implementation** | Contract-author/implementer/verifier split + independent scientific review. | Medium — latency; for a solo operator "independence" is cross-model (M-4/M-5). | Acceptable **if** the R0 fast-path funds the overhead and independence is made checkable (M-5). |
| **R3 claim / methodological reversal** | Dual independent review + Stephen approval + full trace. | Medium — Stephen becomes the throughput limiter (M-4). | Appropriate; reserve P-005 for genuine forks (Q-006) and define the delegated envelope. |
| **Long-running checkpointed local compute** | Lease/heartbeat/`ExpireLease`, guardrail→stop transition. | Low on correctness, medium on operability (m-B9 sleeping machine). | Guardrail-as-state-transition (F-009) is a real improvement over prose; specify heartbeat/operator behaviour in W8 for unattended personal-machine runs. |
| **Small non-TDA project** | `.research-system/` schema + adapters + evals as release obligations. | Medium — the full control plane is heavy for a 1-person non-TDA pilot. | The W10 template must demonstrate a *minimal* profile (R0/R2 only, no parity matrix) so the core is adoptable without the full apparatus; portfolio fields (novelty/estimand/falsification) presume hypothesis-testing research — make them optional. |
| **Qualitative / mixed-methods** | Multidimensional artefact authority is quantitative-flavoured (hash/integrity/structural-validation); a qualitative artefact (coding memo, interview synthesis) has no deterministic validator. | High — falls entirely to `M`/`H` graders with no `D`/`T` floor, so the eval system has little to assert. | **Gap vs. D-004's explicit claim.** Add F-024, and state the limitation: for non-computational artefacts the system provides provenance/lifecycle/authority but not deterministic validation, and the assurance weight shifts to human/independent review. Do not imply parity with the quantitative path. |

General proportionality: the design's own §9 risk table and "stop-doing list" already internalize the over-engineering risk, and the modular-monolith choice (vs. a distributed framework) is the right proportionality call. The residual proportionality risk is concentrated in (a) the envelope weight for R0 and small projects, and (b) human-authority throughput (M-4) — both addressable without changing direction.

---

## 8. Proposed revision plan

### 8.1 Immediate corrections (editorial / factual; low-risk)

1. **EF-2** — correct the "Observation 7" citation in W2 §2, §14.3 and P-009 (cite F-001/F-002 + evidence §4.3 for bus ownership; reserve Obs 7 for contract-authorship/F-014). *Proposed, not applied — touches a decision's evidence.*
2. **EF-3** — in `01-current-system-evidence.md` §2.1, name the PDFs' authorship/venue and label them practitioner vendor whitepapers.
3. **m-A5** — generalize `00-master-transition-plan.md:152` "topology or specialist method" to "specialist-method incremental value."

### 8.2 Stephen / Manager decisions required

1. **M-1 / M-2 (storage vs. worktrees)** — choose the canonical-store concurrency model (per-stream partitioning, single shared store, or operational single-writer) and `.research-system/` placement. *This is the gating decision; W2 cannot be accepted without it.*
2. **M-3 (compatibility dual authority)** — approve non-shared compatibility paths / slot-locking for successor-owned tasks.
3. **M-4 (human authority)** — approve the honest restatement of solo-operator independence and the delegated-acceptance envelope.
4. **M-7 (W0 addendum)** — accept a dated W0 addendum recording the T1.6 re-merge, T1.28 active/extractor-blocked state, and bus-ownership backport; re-confirm A-001 against live state.
5. **A-002 / Stage-2 scope** — the standing `decision_required` (14 unlogged tasks) still gates the W0 seal.

### 8.3 Later-work dependencies (defer, with the dependency named)

- **M-5 (checkable independence)** → W3 context-packet provenance + W6 grader.
- **M-6 (RuleEvaluation vs Decision)** → W5 `[RESULT]`-vs-`[DECISION]` policy; add referent attestation now.
- **M-8 / M-9 (grader family-diversity; no self-reported certification)** → W6 executable design.
- **m-B8 (snapshot-anchored replay)** → W2 implementation planning.
- **m-B9 (unattended lease)** → W8.
- **F-021/F-024 and the S-01x scenarios** → W6 materialization (after W3–W5 interfaces), but reserve the IDs and priorities now.

---

## 9. Residual risks after proposed changes

1. **The storage decision (M-1) may force a hard trade-off**: full Git-inspectability of the canonical ledger and a single global hash chain may be mutually exclusive under multi-worktree operation. If the resolution is "ledger lives outside Git," P-001's inspectability rationale weakens and must be re-argued; if "per-stream chains," the global-ordering guarantees in W2 §9/§21 must be re-specified. Either way, expect a non-trivial W2 revision.
2. **Solo-operator independence remains a partial control** even after M-4/M-5: cross-family verification reduces but cannot eliminate correlated error when one human frames both sides. The eval (M-8) mitigates, not closes, this.
3. **Compatibility-window complexity (M-3)**: non-shared paths add operator cognitive load during migration; the W9 pilot should measure whether operators actually use the ARS path or fall back to the legacy slot.
4. **Eval-of-the-eval regress**: M-8/M-9 harden graders, but a sufficiently correlated model ecosystem still bounds what any model grader can catch; human/independent review (H) remains the backstop for R3, which reintroduces the M-4 throughput risk.
5. **Currency drift will recur**: W0 will go stale again as T1.28 completes; the addendum mechanism (M-7) must be a standing practice, not a one-off, or the next reviewer inherits the same problem.

---

## 10. Verification evidence

- **Documents edited by this review: none.** Only this report was created (`docs/plans/agentic-research-system/reviews/adversarial-first-pass-review-2026-06-29.md`). No reviewed document, `.apm/` file, contract, result, vault, branch, worktree, checkpoint, or T1.28/no-migration artefact was modified. Stop-conditions respected: no W1-approved decision reversed, no human-authority change enacted, no evidence migrated, no implementation authorized.
- **Read-only live checks performed** (commit-anchored, against W0 snapshot `c182e646`):
  - `git log c182e646..HEAD` (11 commits incl. the T1.6 revert chain and `7c8de855`); `git show -s` on `c182e646`, `551a9888`, `17ae8c91`, `7e798464`, `a1e624f9`, `7c8de855`.
  - Directory listing of `results/panel_methodology/fdr/` (T1.28 compute logs, `subgroup_checkpoints/`, no final `stratified_w2_*.json`); absence of `.apm/memory/stage-01/task-01-28.log.md`.
  - Title-page text of both PDFs (provenance).
- **W0-cited evidence corroborated read-only** (full results in the change log): policy-drift hooks (`.claude/settings.json`, `.codex/hooks.json`), `CLAUDE.md`↔`.apm/metadata.json` version/path mismatch, `APM_RULES` absent from `AGENTS.md`, `tools/sync_agent_skills.py` full-replace sync, `shared/manager_dispatch_check.py`, `contracts/README.md` authorship rule, both `SUPERSEDED.md`, `.apm/plan.md` 22 Stage-2 tasks + T2.22 + `tracker.md` "Stage 2: Complete", `task-01-06.log.md` frontmatter/body contradiction, `contracts/manifests/T1.28.yaml` + `input-provenance/t128-inputs.yaml` + three `stratified-w2-*` pending contracts, and the Observation-7 miscitation.

---

## Change log (separate, per the prompt — no reviewed document was silently rewritten)

| # | Action | Target | Applied? |
|---|---|---|---|
| 1 | Created this review report | `reviews/adversarial-first-pass-review-2026-06-29.md` | Yes |
| 2 | Proposed Observation-7 citation fix (EF-2) | W2 §2/§14.3, P-009 | No — proposed only (decision evidence) |
| 3 | Proposed framing-source provenance line (EF-3) | `01-current-system-evidence.md` §2.1 | No — proposed only |
| 4 | Proposed core-portfolio wording fix (m-A5) | `00-master-transition-plan.md:152` | No — proposed only |
| 5 | Proposed dated W0 addendum (M-7) | new `transition/W0-…-addendum-2026-06-29.md` | No — requires Stephen/Manager; snapshot not rewritten |

**Completion check.** Every W1 invariant (§5), every W2 critical mechanism/invariant and the ten stress scenarios (§5, Appendix), every W0 fixture F-001–F-020 and synthetic scenario S-001–S-010 (§5–§6, Appendix), and every decision D-001–D-008 / P-001–P-019 / A-001–A-002 / Q-001–Q-007 (§4) has an explicit disposition. No implementation or migration follows from this verdict.

---

## Appendix — explicit dispositions for W2 invariants and fixtures (completion standard)

**W2 core invariants (§25):** 1–6 ✓ (with inv. 3/6 caveats M-1/M-3); 7 ✓; 8 ✓; 9 ⚠ (M-5); 10 ✓; 11 ✓; 12 ✓ (M-5); 13 ⚠ (M-5); 14 ✓ (P-012); 15 ✓; 16 ⚠ (M-3); 17 ✓; 18 ✓ (M-1 caveat on replay determinism across branches); 19 ✓; 20 ✓.

**W6 historical fixtures:** F-001 ⚠ reclassify (M-10); F-002 ⚠ overwrite-half reclassify (M-10); F-003 ✓ (M-2 root-placement caveat); F-004 ✓ (evidence verified); F-005 ✓ (verified); F-006 ✓; F-007 ✓ (m-C2 gameability); F-008 ✓ (record schema W8-dependent); F-009 ✓ (strong); F-010 ✓; F-011 ✓ (M-9 grader); F-012 ✓ (M-8/M-9 graders); F-013 ✓ (verified materializable); F-014 ✓ (M-5 independence); F-015 ✓; F-016 ✓ (M-5/M-8); F-017 ✓; F-018 ✓; F-019 ✓ (M-8); F-020 ✓ (verified).

**W6 synthetic scenarios:** S-001 ✓; S-002 ✓; S-003 ✓; S-004 ✓; S-005 ✓ (defends the comparative-conflict attack); S-006 ✓ (M-3 legacy caveat); S-007 ✓; S-008 ✓ (defends scope-collapse); S-009 ✓; S-010 ✓. **Proposed additions:** S-011, S-012 (P0), S-013 (P0), S-014, S-015, S-016; F-021, F-022 (P0), F-023, F-024.
