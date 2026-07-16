# Adversarial review — ARS Gate 5 integrated foundation (WP5.6, second independent pass)

**Date:** 2026-07-16
**Target:** merged `origin/main` at `981ae5efedc351e970cec0e136561c8090d5922d` (PR #99 merge)
**Review workspace:** fresh linked worktree `C:\Users\steph\.codex\worktrees\wp56-gate5-review`, branch `codex/wp56-gate5-review`, created 2026-07-16 from the exact required baseline; no WP5.2 remediation worker workspace, branch, or conversation state reused
**Predecessor input (not authority):** `adversarial-gate5-foundation-review-2026-07-15.md` (read from the predecessor's standalone clone; every finding independently re-derived from current code)
**Verdict:** `rework_required` — scoped and bounded (see Executive verdict)
**Authority boundary:** this report authorizes nothing. Gate 5 remains unaccepted; Gate 6, live providers, live M/H grading, deletion initiation, pilot work, and research work remain out of scope. No canonical WP5.6 publication, no acceptance record, no vault reconciliation, and no commit/push/PR were performed, per the WP5.6 stop rule.

---

## Exact target and provenance

Recorded before any write, from the review worktree:

```text
cwd            = C:\Users\steph\.codex\worktrees\wp56-gate5-review
symbolic HEAD  = refs/heads/codex/wp56-gate5-review
HEAD           = 981ae5efedc351e970cec0e136561c8090d5922d
origin/main    = 981ae5efedc351e970cec0e136561c8090d5922d (post-fetch)
git-dir        = .git (linked worktree of C:\Users\steph\TDL)
status         = clean
```

Required-baseline confirmation: PR #99 final head `99ee2f894efcf78f6ba7a588c2777455654a88c8` **is an ancestor** of merged baseline `981ae5e`, and `981ae5e` **is merged into** `origin/main` (both by `git merge-base --is-ancestor`, exit 0).

All twelve Gate 5 prerequisite merge SHAs from the predecessor's list, plus the predecessor's own reviewed target `279beac9`, are ancestors of HEAD (thirteen `merge-base --is-ancestor` checks, all exit 0):

```text
d66dfdc9 74a5ea50 8224ce04 f9a72c45 45ed2a9a aad6fa68 1df79634
21ecaf99 1926895b a7866c34 080c5409 ae0a44c2 279beac9
```

Post-predecessor first-parent history contains exactly: `5e7b879` + PR #98 merge `c7aafed` (unrelated Stage-1 gate work), `5cc3c8d` (2-line skill-doc edit, unrelated), and PR #99 merge `981ae5e` (the WP5.2 oracle remediation). No Gate 5 surface was touched outside PR #99.

**PR #99 review-then-merge gate held.** MERGED 2026-07-16T13:45:54Z at head `99ee2f8`; Codacy SUCCESS. CodeRabbit produced three incremental reviews, each with one Major finding that maps to a remediation commit: derive `oracle_match` from bound evidence → `9f7d223`; parity producer rejection test → `e7cca3d`; reject noncanonical oracle bytes → `99ee2f8` (committed 12:52, after the 11:36 review). A final requested review concluded ("Review finished", 13:22:40Z) before the 13:45:54Z merge. Inline comments fetched via `gh api repos/stephendor/TDL/pulls/99/comments`; no unresolved Critical/High thread.

## Governing documents

Read completely before verdict formation: `AGENTS.md`; `CONVENTIONS.md`; the Gate 5 master plan (05-wp5); WP5.1 (05a), WP5.2 (05c), WP5.3 (05d), WP5.3-A (05e), WP5.4 (05b) plans; WP4.8 (04a) and WP4.9 (04b) plans and registers; the P0 master plan (05-p0) and Gate ladder (04-parallel); W6 (design/06) and W7 (design/07); the 2026-07-07 WP4 full review; the Gate 5 orchestration handover prompt (independence and definition-of-done sections); and the predecessor 2026-07-15 review.

Frozen owner decisions treated as immutable: D-G5-1(a), D-G5-2, D-G5-3, D-G5-4, D-G5-5, G5.3-A, G5.3-B(a). Expected integrated evidence: exactly 40 fixtures / 15 blocked / 0 uncalibrated / 302 unique results / calibrated / parity pass / operations pass / candidate blocked / gate5_authorized=false. None of these was weakened, reinterpreted, or silently changed by this review.

## Executive verdict: `rework_required` (bounded; no code-content defect found)

Every code-level Gate 5 acceptance criterion this review attacked **holds on current main**. The predecessor's Critical (G5-C1) is genuinely closed at the producer seam, the evidence-binding layer, the parity coupling, and the publication boundary — verified by direct source inspection, by the committed public-seam negatives, and by an independent end-to-end probe this review wrote and ran (a deterministically wrong non-F-020 producer observation now yields `fixture_error` verdicts, a 16th blocking fixture, and an **unpublishable** snapshot). The correlated expected+observed snapshot forgery and the noncanonical-oracle-bytes follow-up are both closed with committed negatives. The integrated derivation reproduces the exact frozen state twice with equal stable projections.

The verdict is nevertheless `rework_required` under the WP5.6 stop rule, on two bounded, non-code blockers:

1. **G5R-1 — the literal five-materializer gate fails on canonical `C:\Users\steph\TDL`** (exit 1 on the variant-matrix check) while passing 5/5 in this fresh worktree. This is the operational residue of the predecessor's G5-m1: the `.gitattributes eol=lf` fix (commit `050ba49`) makes checkout bytes contractual for every future checkout, but gitattributes never renormalizes an already-checked-out file, and the canonical tree's working copy predates the attribute. The WP5.6 brief classifies a failed required command and an inconsistent canonical/fresh-tree result as stop conditions, and forbids this review from normalizing canonical main.
2. **G5R-2 — the 05e §3.2 owner gate for the integrated production publication is unmet**: no Owner `[DECISION]` records an approved production authority-bootstrap-manifest SHA-256. The only bootstrap hash in the vault (`093d60fa…`, PR #90) is a twice-built test-fixture equality check, not a production approval. Publication of the production P0 decision may not proceed until Stephen records that hash.

Both blockers are resolvable without any repository code change: (1) is a one-time refresh of one generated file's working copy on canonical main (owner action, or an authorized session); (2) is an owner `[DECISION]` recording the bootstrap hash the acceptance runner will present. After both, a bounded re-run of the WP5.6 acceptance path (validation deltas + publication + reconciliation) can proceed without repeating this full review, provided main has not moved.

Per the stop rule: no canonical WP5.6 publication, no acceptance record, no vault reconciliation, no commit/push/PR. This report is the only artifact written, at the required path, uncommitted.

## Findings

### G5R-1 — Canonical-tree variant-matrix materializer check fails; fresh worktree passes (dual-tree divergence)

1. **ID/severity:** G5R-1, **Minor** (content integrity) / **acceptance-blocking** (under the literal five-materializer gate and the WP5.6 canonical/fresh consistency rule).
2. **Claim.** `uv run --no-sync python tools/ars/materialize_p0_variant_matrix.py --check` exits **1** ("p0-variant-matrix.yaml is not byte-identical to regeneration") when run from canonical `C:\Users\steph\TDL`, and exits **0** ("byte-identical") in this fresh worktree at the identical commit.
3. **Evidence.** Canonical working copy: 825 CRLF pairs, 24,274 bytes; `git ls-files --eol` reports `i/lf w/crlf attr/text eol=lf`; `git status` reports the file clean (the clean filter normalizes CRLF→LF before comparison, so the divergence is invisible to git). Fresh worktree (checked out 2026-07-16, after the attribute): `i/lf w/lf`. The checker (`tools/ars/materialize_p0_variant_matrix.py:149`) is a strict `read_bytes() != rendered` comparison with no normalization; `rendered` is LF. The index blob is identical in both trees and equals the regeneration (LF-normalized SHA-256 `e7d61c32c817ca95d21f17d6d8557656b0c99bb3a823a85ee7704d245b0de94f`, matching the PR #92 records). **No semantic or git-content drift exists.**
4. **Failure scenario.** The owner (or any session) runs the required five-materializer validation on the canonical tree — the tree the owner actually uses — and the literal gate fails, indistinguishable at the command level from real matrix drift. Conversely, every fresh checkout passes, so the failure is machine-state-specific and non-obvious (git status is clean).
5. **Impact.** Operational/validity-of-process only. Acceptance evidence produced in a fresh worktree is uncontaminated; but the WP5.6 required validation ("also against canonical … read-only") fails, and the brief's stop rule fires on both "failed required command" and "inconsistent canonical/fresh-tree result".
6. **Disposition — owner action, then resume.** One-time refresh of the single generated file's working copy on canonical main (e.g. `Remove-Item .research-system\evals\p0-variant-matrix.yaml; git checkout -- .research-system/evals/p0-variant-matrix.yaml` from the repo root — re-checkout applies the now-committed `eol=lf` attribute). Alternatively (code-side, separate bounded change): make the checker compare the repository's declared normalized representation instead of raw checkout bytes. This review executed neither (canonical main is explicitly out of its write authority).
7. **Proposed text change.** None to committed content. If the code-side alternative is chosen: `materialize_p0_variant_matrix.py --check` compares `read_bytes().replace(b"\r\n", b"\n") != rendered` **only when** the file's git attribute declares `eol=lf` — or simpler, document the one-time refresh in the Gate 5 runbook.
8. **Affected:** WP5.6 required validation; Gate 5 exit checklist item "integrated acceptance run"; predecessor finding G5-m1 (partially closed: contractual bytes for fresh checkouts delivered by `050ba49`; canonical residue remains).

### G5R-2 — Production authority-bootstrap hash has no Owner decision record (05e §3.2 gate unmet)

1. **ID/severity:** G5R-2, **Major** as an acceptance-path precondition (not a code defect; the code enforces the gate correctly).
2. **Claim.** 05e §3.2 (owner-approved): "the final bootstrap-manifest SHA-256 must be recorded in an Owner decision before the integrated publication run. Store initialization requires exact equality with that approved hash." No vault `[DECISION]` records an approved production bootstrap-manifest hash.
3. **Evidence.** `research_system/authority.py:593-620` enforces `approved_bootstrap_sha256 != bootstrap_hash → ArsError` and `research_system/cli.py:104-113` requires the approval digest inside the strict `ars://core/authority-bootstrap-input` document. Vault grep for "bootstrap": only the 2026-07-13 G5.3-A `[PIPELINE]` entry's twice-built **test-fixture** bootstrap equality hash `093d60fabcba013048612de4021db6db528eb4afb0a4ee742917a128012ccda6`; 05e's own text: "synthetic tests use explicitly test-classified approval records and cannot publish the production P0 decision."
4. **Failure scenario.** An acceptance runner constructs the production bootstrap input, self-supplies the matching `approved_bootstrap_sha256`, initializes the store, and publishes — mechanically valid, but the human governance anchor G5.3-B(a) traded for cryptographic principal authentication would never have existed. The trusted-local-operator model's single compensating control would be silently skipped.
5. **Impact.** Authority/governance. Publication without the owner record would satisfy every machine check while violating the accepted G5.3-B(a) boundary.
6. **Disposition — owner decision required.** The acceptance runner must: build the production bootstrap manifest (project ID, owner actor ID, administrative root grant, publication grant, object hashes, exact `rgd_…` target — which requires the unpublished production decision's allocated ID first), compute its canonical SHA-256, present it to Stephen, and obtain a vault `[DECISION]` recording it **before** `store init`. Then proceed.
7. **Proposed text/interface change.** None; the mechanism is correct. Add the owner-decision step explicitly to the WP5.6 acceptance-run runbook so it is not rediscovered at run time.
8. **Affected:** WP5.6 acceptance path step 2 (canonical publication); O12 closure; G5.3-B(a).

### G5R-3 — PR #99 remediation has no vault record yet

- **Severity:** Minor (record hygiene). The latest ARS entry in `04-Methods/Computational-Log.md` is the 2026-07-13 G5.3-A closure; the WP5.2 oracle remediation (merged 2026-07-16) has no `[PIPELINE]` entry. Consistent with reconciliation being deferred to WP5.6, but if acceptance is deferred further, the remediation should be logged on its own so the repo-vault bridge does not silently gap. **Disposition:** fold into the WP5.6 reconciliation entry when the acceptance run completes; if Gate 5 stalls, write it standalone.

### G5R-4 — Editorial: nested oracle-document schema constraints

- **Severity:** Editorial. `release-control-binding.schema.json` requires the four authority fields with `additionalProperties: false` and exactly 40 items, but the nested `post_control_oracle` object carries no item-level `required`/`additionalProperties`. The load-bearing gate is code-side (`_oracle_authorities` enforces exact key sets, exact assertion shape, and hash recomputation, with committed one-at-a-time tamper negatives), so this is defense-in-depth hardening only. **Disposition:** optional follow-on; do not treat as a control gap.

## Predecessor-finding closure verification (independently re-derived)

| Prior finding | Prescribed disposition | Verified current state | Verdict |
|---|---|---|---|
| **G5-C1** (Critical): variant runner cloned baseline `GraderResult`s; wrong-but-repeatable observations produced passing variant rows | Derive verdicts from produced observation vs post-control oracle; bind comparison + hashes into `execution_evidence_hash`; one-at-a-time producer-seam negatives per executor/row class; wrong non-F-020 observation blocks while F-020 parity stays valid | `variants.py:400-433` re-reads and hash-verifies fixture/stimulus/post-control bytes against the validated package, derives `oracle_match` from both produced observations vs `expected_evidence`; `:445-451` maps mismatch → `fixture_error` (BLOCKING per `release.py:13`); `:504-547` binds expected+observed dicts, all three hashes, and `oracle_match` into `execution_evidence_hash`, fully recomputed in `__post_init__` (`:165-241`). `parity_evidence.py` now enforces oracle↔verdict coupling (mismatch ⇒ all bound results `fixture_error`; match ⇒ none). Committed negatives: `test_wrong_f007_producer_observation_cannot_inherit_passing_variant_verdicts` (8/8 `fixture_error`, parity pass, blocked), `test_all_registered_matrix_executor_provider_families_fail_closed_on_wrong_observations` (all 46 rows, both providers, both families → all `oracle_match=False`, all `fixture_error`), `test_variant_repeat_mismatch_stops_before_evidence_admission`. Independent probe (this review, not in the committed suite): wrong F-007 producer → 16 blocking fixtures and `rederive_release_from_snapshot` rejects the snapshot — the acceptance-shaped packet is unreachable. | **CLOSED** |
| **Manager correlated expected+observed snapshot finding** | A self-consistent forgery of both sides of a stored variant execution must fail | Commit `9ef8f9d`: 40 fixture-oracle authorities in the control-binding document, derived from disk via `validate_fixture_package` (producer, `_fixture_oracle_authorities`), strictly revalidated at consumption (`_oracle_authorities`: exact key sets, `satisfied is True`, hash recomputed from parsed canonical content) with `_require_oracle_authority_bindings` forcing every binding/result/variant-execution oracle hash and expected-evidence dict to equal the authority. Committed negative: `test_stored_snapshot_rejects_correlated_f007_expected_and_observed_forgery` (fully self-consistent forged record incl. recomputed `execution_evidence_hash` → "fixture oracle authority mismatch"); plus a `fixture_oracle_authority` seam in the one-at-a-time tamper matrix. Escalation to full multi-document forgery is defeated by content-addressed refs (`content_artefact_id` check, `release_publication.py:168`), the event's `evaluation_runs_manifest_sha256`/`control_binding_sha256` bindings, and — at publication — the fresh in-process re-derivation from the real corpus (`cli.py:_publication_evidence`: caller can never supply manifest/control content; `decision_document(record) != source → ArsError`). | **CLOSED** |
| **Canonical-oracle-bytes follow-up** (CodeRabbit Major on PR #99) | Noncanonical-but-self-consistent fixture bytes must fail | Commit `99ee2f8`: producer rejects `post_bytes != canonical_bytes(post) + b"\n"` (`release_snapshot.py:184`); consumer recomputes the authority hash from parsed canonical content (`:420`), collapsing byte/content representations. Committed negative: `test_snapshot_builder_rejects_noncanonical_fixture_oracle_bytes` — a **fully self-consistent** rewritten F-007 package (post-control re-serialized `indent=2`, `source-manifest` and `fixture.yaml` hashes all updated) calibrates cleanly but the snapshot build fails with "fixture oracle authority must use canonical JSON". | **CLOSED** |
| **G5-m1** (Minor): exact matrix materializer fails on Windows checkout bytes | Make checkout bytes contractual (LF attribute) or make the checker compare the declared normalized representation | Commit `050ba49` added `.research-system/evals/p0-variant-matrix.yaml text eol=lf`. Fresh checkouts now pass (verified: exit 0 here). Canonical main's pre-attribute working copy still fails (exit 1) — see finding G5R-1. | **CLOSED for fresh checkouts; operational residue on canonical (G5R-1)** |

## Invariant → enforcement point → public-seam test matrix

| # | Invariant (acceptance criterion / exit-checklist item) | Enforcement point | Public-seam test / evidence | Status |
|---|---|---|---|---|
| 1 | All required WP5.1–WP5.4 + prerequisite merges present | Git ancestry | 13 × `merge-base --is-ancestor`, all exit 0 | holds |
| 2 | Exactly 40 selected fixtures, exact revisions | `coverage.load_p0_coverage` per-package revision equality | `eval validate` → `{"fixture_count":40,"status":"valid"}` | holds |
| 3 | Exactly 46 gate5 rows (30 adapter/rendering + 16 sizing), no wildcard/duplicate/stale | `load_gate5_variant_rows` (exact count, wildcard set, dupe key, revision pin, provider whitelist, sizing-field biconditional) | matrix inspection (46/30/16, four fake providers); committed loader negatives | holds |
| 4 | **Variant observation graded against fixture post-control oracle before any verdict** | `variants.py` `oracle_match` derivation + `fixture_error` mapping; `parity_evidence.py` oracle↔verdict coupling | committed F-007 negative; all-46-families negative; repeat-mismatch negative; this review's independent publishability probe | **holds (G5-C1 closed)** |
| 5 | Correlated expected+observed forgery rejected | fixture-oracle authorities: producer disk derivation + consumer strict revalidation + `_require_oracle_authority_bindings` | committed correlated-forgery negative; `fixture_oracle_authority` tamper seam | holds |
| 6 | Noncanonical-but-self-consistent fixture bytes rejected | canonical-JSON byte rule (producer `release_snapshot.py:184`); parsed-content hash recomputation (consumer `:420`) | committed noncanonical-bytes negative | holds |
| 7 | Changing ordinary oracle hashes without authority rejected | `_require_oracle_authority_bindings` over bindings, results, variant executions (incl. `grader_result_bindings[i][3]`) | one-at-a-time tamper matrix | holds |
| 8 | Exact 302 unique six-element result keys (132 + 170) | `variants.py:550-551` (exact 170); strict release closure; `rederive_release_from_snapshot` (`len(results) != 302`) | `eval run` ×2 → 302; stable projections equal | holds |
| 9 | Twice-run byte-identical normalized decisions | per-row repeat-hash equality + `VariantExecutionEvidence.__post_init__` | two `eval run` documents: `stable_projection` equal; committed repeat negative | holds |
| 10 | D-G5-5 exact applicability (4 controls × R0–R3 × 2 selectors), no wildcard/semantic-class inference | `load_policy_control_applicability` (decision/bundle/hash binding) | applicability YAML inspection (4 controls, `r1`, literal tiers, 2 selectors each); committed loader negatives | holds |
| 11 | Eight content-addressed parity evidence records; one W7 row per control; critical gap blocks; percentage diagnostic-only | `build_fake_adapter_parity_evidence` requirement/evidence exact closure; `build_parity_report` | committed negatives (self-attested, forged-oracle coupling, missing control, hash mismatch) | holds |
| 12 | `parity_status=pass` only from schema-valid, complete, no-blocker report; no caller-forced pass | `build_release_decision` + release schema report-ID/hash requirement | committed tests; `eval run` document carries `ppr_`/`pca_` IDs with `parity_status=pass` | holds |
| 13 | M/H capability restriction explicit; 15 blocking fixtures; candidate blocked; `gate5_authorized=false` | coverage (`gate5_authorized: false` committed) + `decide_release` BLOCKING set | `eval run`: blocked; blocking fixtures exactly {F-005, F-009, F-012, F-014, F-020, F-021, F-022, F-025, F-026, F-031, F-032, F-033, F-035, F-036, S-016}; 51 `unable_to_grade`, 0 `fixture_error` | holds |
| 14 | O15: deletion initiation absent and capability-disabled | no `DeleteEvidenceObject` anywhere in `research_system/` (grep); required `capability_disabled` row (`coverage.py:165`, coverage YAML:48) | grep evidence + loader requirement | holds |
| 15 | S-014 restore preflight biconditional; recheck before writer lease | `RestorePreflightResult.__post_init__` (`(status=="verified") != predicates_empty → error`); consumer double-check (`backups.py:327`); service `configure_moved_restore` + rechecker seam | committed WP5.4 negatives (writer lock not entered) | holds |
| 16 | S-015 cycle rejected atomically; cycle check precedes replacement-terminal check; idempotent rejected receipt in WriterLock | `_prepare_supersession` (`service.py:698` cycle before `:705` terminal); exact payload fields (caller lineage forbidden, `:647`) | committed C1→A1 nonterminal cycle test + terminal-replacement traversal (14f45fab remediation) | holds |
| 17 | S-016 outage: no fallback, H blocking `unable_to_grade`, real orchestration seam | `release_tranche.py` `execute_s016` via `RouteCandidate`/`PreparedDispatch` hard gates (`provider_unavailable`/`independence_unavailable`/`capability_insufficient`) | committed tests; S-016 among the 15 blockers | holds |
| 18 | Publication: one ledger-allocated event, self-referential `canonical_event_ref`, exact idempotency tuple, conflicting payload conflicts, authority rechecked under lock, replay pure, sentinel rejected | `CommandService`/`EventLedger` finalizer/`replay` per WP5.3 + three PR #92 remediations | 131-test WP5.3 focused matrix inside the full suite; merge-ancestry-verified remediation records. **Live integrated publication not executed by this review (stop rule)** | holds at test level; runtime acceptance evidence pending G5R-1/G5R-2 |
| 19 | Stored evidence content-addressed; post-publication tamper impossible | `StoredReleasePublicationEvidence` (`content_artefact_id(value) != reference → reject`); event `*_sha256` bindings | committed byte/schema tamper + restart negatives | holds |
| 20 | Five exact materializers byte-identical | `--check` strict byte comparison | fresh worktree: **5/5 exit 0**; canonical: **4/5**, matrix **exit 1** | **violated on canonical (G5R-1)** |
| 21 | No `.env`, credential, live provider, network, raw transcript, restricted data | fake-transport type check (`variants.py:338`); no env/dotenv reads in production code (grep); `bounded_redacted` receipt modes (D-G5-5 values); W7 privacy rules | transport spy tests; grep evidence; probe used synthetic fixtures only | holds |
| 22 | Anti-anchoring: executors derive from stimulus payload only | executor contract + WP4.8 spy test (payload contains no `*_evidence` keys) | committed spy test; variant path passes stimulus payload only (`variants.py:296`) | holds |
| 23 | O10 ID-kind registration | `.research-system/config/id-kind-registry.yaml:26` `release_gate_decision: rgd` (and `:27` `policy_parity_report: ppr`) | direct read | holds — **O10 residual confirmed by this review** |
| 24 | Anti-anchoring of review numbers: observed ≠ pasted-expected | this review recorded observed values before comparing to pre-registered ones | all counts in Validation evidence below are observed outputs | holds |

## Decision audit (keep / amend / reject / defer)

| Decision | Disposition | Evidence |
|---|---|---|
| D-G5-1(a) M/H capability restriction | **Keep.** 15 blocking fixtures exact; 51 `unable_to_grade` rows; no fabricated cross-family pass; restriction explicit in coverage/release | `eval run` documents; blocking-fixture set above |
| D-G5-2 / O15 deferral | **Keep.** `DeleteEvidenceObject` absent from the entire codebase; `EvidenceDeletionPending` consumed (`replay.py:206`) and emitted by nothing; `capability_disabled` row loader-required | grep + coverage inspection |
| D-G5-3 exact re-baselines | **Keep.** 40/15/0/302/calibrated/blocked reproduced twice, observed not pasted | `eval calibrate` + `eval run` ×2 |
| D-G5-4 two provider-specific F-021 sizing rows | **Keep.** Matrix carries exactly two `mandatory_closure_sizing-*` F-021 rows at `p0` stage; 16 gate5 sizing rows = 8 fixtures × 2 counting revisions | matrix inspection |
| D-G5-5 exact four-control applicability | **Keep.** 4 controls at `r1`, literal `[R0,R1,R2,R3]`, exactly 2 selectors each; comparator-only (owner hash never populates observed evidence — committed negative) | applicability YAML + `parity_evidence.py` |
| G5.3-A canonical authority source/resolver | **Keep.** `LedgerAuthorityGrantResolver` merged (PR #87/#90 ancestry verified) and wired in `_eval_publish_release` | cli.py:466-471 |
| G5.3-B(a) trusted-local attribution | **Keep.** No cryptographic principal authentication added; the compensating owner anchor (bootstrap-hash decision) is exactly what G5R-2 enforces | authority.py; 05e §3.2 |

All seven owner records were verified **read-only** in the vault (`04-Methods/Computational-Log.md`): D-G5-1, D-G5-2, D-G5-3(WP5.4), D-G5-4 (all 2026-07-10); G5.3-A/G5.3-B(a) decision (2026-07-12) and closure (2026-07-13); D-G5-3(WP5.2)+D-G5-5 (2026-07-12). No vault file was modified by this review.

## Gate 5 exit checklist (master plan §10) disposition

| Item | Disposition |
|---|---|
| WP5.1–WP5.4 merged via review-then-merge, CodeRabbit concluded pre-merge every PR | **Complete** — merge ancestry verified (13 SHAs); PR #99's three-review + final-conclusion chain verified against commit timestamps |
| D-G5-1, D-G5-2, D-G5-4 recorded as vault `[DECISION]` entries | **Complete** — verified read-only, dated 2026-07-10 |
| All invariant re-baselines pre-registered and approved (D-G5-3 process) | **Complete** — WP5.4 (2026-07-10) and WP5.2 (2026-07-12) records verified; observed values match exactly |
| Integrated acceptance run: one `ReleaseGateDecision`, canonically published, parity evaluated, S-tranche present, capability restrictions explicit | **Not performed** — stopped by G5R-1 (canonical materializer gate) and G5R-2 (missing owner bootstrap-hash record). The *derivation* half is proven (twice, exact); the *publication* half awaits the two blockers |
| Bounded independent review delivered; findings dispositioned (revision or stop) | **This report** — findings dispositioned as owner actions + bounded re-run; no criterion weakened |
| Stephen's recorded acceptance | **Not reached** — `owner_acceptance_pending` is not yet applicable; the acceptance run itself is pending |

## Coverage / fixture gaps

- No missing executor/row family in the producer-seam negatives: the all-46-row sweep covers every `(fixture_id, provider_variant)` pair including both counting revisions — asserted as set equality against the loaded matrix, not a copied list.
- The committed F-007 probe and this review's independent probe differ in depth: the committed test stops at parity/decision assertions; the independent probe additionally proves snapshot **unpublishability** (`rederive_release_from_snapshot` rejection on `fixture_error` + 16-fixture blocking closure). Recommend (non-blocking) promoting that final assertion into the committed test so the publication boundary is exercised in-suite.
- G5R-4 (nested schema hardening) — optional.
- No other coverage gap found: empty/partial/duplicate/extra/stale evidence sets are all exercised at the release, parity, snapshot, and authority seams by committed negatives.

## Practicality assessment

The remediation is proportionate: one producer-derivation change, one evidence-binding layer, one authority mechanism, and committed negatives at exactly the seams the predecessor named — no new architecture, no criterion weakened, no oracle bent. The oracle-authority mechanism reuses the existing package validator and canonical-bytes utilities rather than inventing a parallel trust store. Overhead per run is bounded (one extra package validation per fixture at snapshot build). The two residual blockers are operator/owner actions measured in minutes, not engineering.

## Revision plan

**Immediate (owner or authorized session; no PR required):**
1. Refresh the canonical working copy of `.research-system/evals/p0-variant-matrix.yaml` (delete + `git checkout --` from `C:\Users\steph\TDL`), then re-run the matrix check there and record exit 0. *(G5R-1)*

**Owner decisions (before the acceptance run):**
2. Record the production authority-bootstrap-manifest SHA-256 as a vault `[DECISION]` once the acceptance runner presents the manifest (05e §3.2). *(G5R-2)*

**Bounded WP5.6 acceptance re-run (after 1–2, if main has not moved):**
3. Re-run the canonical-tree matrix check (delta only; all other validation in this report remains valid at `981ae5e`), then execute the acceptance path: allocate the production decision, build/approve the bootstrap, `store init`, `eval publish-release`, exact-retry idempotency proof, conflicting-payload rejection proof, `replay verify`, `eval release`; reconcile vault records; commit/push/PR per the brief; report `owner_acceptance_pending`.

**Optional follow-ons (non-blocking):**
4. Promote the publishability assertion into the committed F-007 producer negative.
5. Nested oracle-document schema hardening (G5R-4).
6. Standalone vault entry for PR #99 if acceptance is deferred (G5R-3).

## Residual risks

- Until the canonical working copy is refreshed, any operator validation run on `C:\Users\steph\TDL` will keep failing the literal materializer gate with a message indistinguishable from real drift — the false-positive direction that trains override reflexes. Refresh, don't override.
- The oracle-authority mechanism anchors trust in the committed fixture corpus at snapshot-build time plus content-addressing afterward. A hostile *commit* to the corpus (rewriting a fixture package and its hashes coherently) remains detectable only by review-then-merge and the materializer byte-identity checks — unchanged from the accepted threat model (trusted-local-operator, G5.3-B(a)).
- The full suite's green status remains necessary-but-insufficient by policy; this review's independent probe and the committed producer-seam negatives are the current decisive controls for the G5-C1 class. Future evidence paths that bind an output hash without an independent expected/observed comparison should be attacked the same way (predecessor's residual-risk note stands, now with one confirmed closure).
- No canonical WP5.6 event/receipt/projection hashes exist from this review; none should be inferred from PR #92's historical worker artifacts.

## Validation evidence

Environment for every Python command:

```text
UV_PROJECT_ENVIRONMENT=C:\Users\steph\TDL\.venv
PYTHONPATH=C:\Users\steph\.codex\worktrees\wp56-gate5-review   (fresh worktree; canonical runs used PYTHONPATH=C:\Users\steph\TDL)
uv run --no-sync everywhere; no .env present or read; fake transports only
```

Executed commands and observed results:

```text
uv run --no-sync ruff check research_system tools/ars tests/research_system
  All checks passed!

uv run --no-sync pytest tests/research_system -q --no-cov            [fresh worktree]
  663 passed in 1863.95s (0:31:03)   [predecessor baseline: 650; +13 = the PR #99 remediation negatives]

five materializers --check                                           [fresh worktree]
  control_store: exit 0 | context_routing: exit 0 | adapter_scientific: exit 0
  p0_variant_matrix: exit 0 ("byte-identical") | gate5_release_tranche: exit 0

five materializers --check                                           [canonical C:\Users\steph\TDL, read-only]
  control_store: exit 0 | context_routing: exit 0 | adapter_scientific: exit 0
  p0_variant_matrix: exit 1 ("not byte-identical")  <-- G5R-1
  gate5_release_tranche: exit 0

uv run --no-sync python -m research_system.cli eval validate --catalogue .research-system/evals/catalogue.yaml
  {"fixture_count":40,"status":"valid"}

uv run --no-sync python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
  {"blocked_fixture_count":15,"fixture_count":40,"fixtures_with_uncalibrated_mutations":0,"mutation_calibration":"calibrated"}

uv run --no-sync python -m research_system.cli eval run --coverage ... --transport fake --output <scratch>\wp56-rgd-run{1,2}_2026-07-16.json
  run1: {"candidate_status":"blocked","result_count":302}
  run2: {"candidate_status":"blocked","result_count":302}
  stable_projection(run1) == stable_projection(run2): True
  decision=blocked | parity_status=pass | operations_status=pass | canonical_event_ref=unpublished:p0
  verdict histogram: 251 pass, 51 unable_to_grade, 0 fixture_error
  blocking fixtures (15, exact): F-005 F-009 F-012 F-014 F-020 F-021 F-022 F-025 F-026 F-031 F-032 F-033 F-035 F-036 S-016
  parity report ppr_… and applicability pca_… IDs present
  gate5_authorized=false (coverage.yaml:46; enforced in code; rederive returns it and the publication path rejects non-False)

independent adversarial probe (this review; synthetic fixtures, fake transports, no repository writes)
  wrapped variants.require_executor to corrupt only F-007's observation deterministically, then ran the
  real public run_p0_coverage seam end-to-end:
    8/8 F-007 variant verdicts == fixture_error; parity_report.passed == True (F-020 untouched);
    decide_p0_release == blocked; blocking fixtures == 16 (the 15 M/H blockers + F-007);
    build_release_snapshot_documents succeeded, then
    rederive_release_from_snapshot REJECTED the packet: "release snapshot result closure mismatch"
  PROBE PASS — a deterministically wrong non-F-020 producer observation can no longer reach an
  acceptance-shaped publishable evidence packet (predecessor G5-C1 scenario, one level deeper).

git diff --check                                                     [fresh worktree]
  clean; worktree status clean (this report is the only new file)
```

Scope audit: the only file written by this review is this report. No runtime code, schema, fixture, policy, materializer, plan, result, or vault file was modified. Canonical `C:\Users\steph\TDL` was touched read-only; its unrelated user work (`.apm/plan.md`, `spec.md`, `tracker.md`, untracked directories) was left untouched.

## Change log

- Added this review report only (uncommitted, per the WP5.6 stop rule: no commit/push/PR on a `rework_required` verdict).
- Two disposable probe/comparison scripts and two `eval run` output documents were written to the session scratchpad outside the repository.
