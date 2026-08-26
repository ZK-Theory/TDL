# TDL Handoff: research-observer backlog, two-week window (2026-08-11 → 2026-08-25)

Date: 2026-08-25
For: the next agent picking up TDL/ARS work — implementation, review, or campaign supervision
Source of truth: `~/.claude/skill-observations/log.md` (the canonical per-user location, shared by supported agent environments). This handoff is a navigation and prioritization layer over that log, not a replacement for it — every item below names its observation ID so you can pull the full issue/suggested-improvement/principle text.
Companion document: a matching handoff, `MathUni: gate-hardening backlog handoff (2026-08-25)`, covers the MathUni repo's items from the same window — not duplicated here.

## Read this first — two things block or bound almost everything below

### 1. The quarantined checkout — status changed mid-write of this handoff. Re-verify before trusting either version.

`C:\Users\steph\TDL` on branch `codex/gate6-eligibility-envelope` had been sitting dirty since **2026-08-14** with the exact state a handoff explicitly told everyone not to touch. The authoritative nine-file quarantine manifest was:

- `docs/plans/agentic-research-system/handoffs/01KZZ1YVPV5SMAHWZGDWZWBK9J-gate6-real-run-reset.md`
- `docs/plans/agentic-research-system/implementation/06p-gate6-control-model-proposal.md`
- `docs/plans/agentic-research-system/implementation/06sgate6deliveryreplanandgate7integration.md`
- `research_system/cli.py`
- `research_system/config.py`
- `research_system/store/identity.py`
- `research_system/store/schema_binding.py`
- `tests/research_system/integration/test_command_cli.py`
- `tests/research_system/integration/test_restore_recovery_origin_witness.py`

The two additional paths later shown by commit `6a29694`, `.claude/CLAUDE.md` and
`.repowise-workspace.yaml`, were Repowise integration rewrites, not members of the
nine-file quarantined task surface. That is the state this whole document was drafted against.

**While this handoff was being written (2026-08-25, same session), the repo changed under it:** the quarantined branch was committed as `6a29694` ("Expose governed discovery submission CLI", authored by `stephendor <stephen@zktheory.org>`, 2026-08-25 18:31:31+01:00 — i.e. under Stephen's own git identity, not an agent's), and the checkout was then switched to `main`. PR #257 (which tracked that branch) is now CLOSED, not merged. Local `main` is itself behind `origin/main` (`d64c58f` vs `6b72a26`), confirming other work landed on `main` very recently too. **This means someone — plausibly Stephen or a concurrent Codex session acting on his behalf — made the explicit decision the 2026-08-14 handoff required, right around the time this handoff was being drafted.** I have not re-verified what state Gate 6 is actually in after that commit, whether `6a29694`'s content matches what the quarantined diff described, or what `origin/main` at `6b72a26` now contains.

**Before doing anything else:** run `git status`, `git log --oneline -5`, `git branch --show-current`, and `git fetch && git log main..origin/main --oneline` to see current reality — do not assume either "still quarantined" (this document's original framing) or "resolved" (what the commit suggests) without checking. The original quarantine instruction (`01KZZ1YVPV5SMAHWZGDWZWBK9J-gate6-real-run-reset.md`, still in the repo) and the enforcement-gap observation (`2026-08-18-quarantined-checkout-not-mechanically-blocked`) remain valid reading regardless of current git state — the gap they describe (a "do not touch without owner approval" instruction with no mechanical backstop) is a standing process issue, not a one-time incident.

### 2. Gate 6 delivery has failed three times and is mid-replan. Read the two newest PROCESS observations before writing any Gate 6 code.

- `01M0TD1B8W1PY7J0QXJC5Y08X6` (2026-08-24): the STORE phase alone burned ~21,860 gross additions / 4,880 deletions across 33 commits and seven PRs (#262–#268), including one retired repair candidate, while the public SPEC capability *remained incomplete*. The agent kept turning reachable/hypothetical review findings into broader storage-engine work despite repeated owner corrections and explicit "smallest complete vertical path" instructions. **Suggested fix (not yet built):** a slice manifest with hard file/line/time ceilings enforced by a hook or orchestrator external to the implementing agent, plus automatic demotion from "autonomous campaign manager" after a second scope breach.
- `2026-08-24-plan-as-overengineering-vector`: the governing plan itself (06q, 853 lines) *mandated* the overengineering — exact blob-hash bindings, closed schemas, five-role cryptographic authority, exhaustive negative matrices, for what is a solo-researcher assurance package. A replan is in flight: `06q → 06s`, and the untracked `06sgate6deliveryreplanandgate7integration.md` file above is presumably that replan draft. **Before writing any new Gate 6 implementation**, confirm whether 06s has been reviewed/accepted, and read its "assurance bar vs. actual threat model" section if one exists — this observation asks for that section to be a required part of ARS plan review going forward, and for CONVENTIONS.md to gain a `[DECISION]` entry once 06s lands.

**Net effect for you:** do not start a fourth from-scratch Gate 6 implementation attempt without first (a) resolving or explicitly ignoring the quarantined checkout per Stephen's instruction, and (b) confirming 06s's status and scope boundaries. Everything else in this document is either report-only (GATE/INVARIANT/PROCESS — needs Stephen's approval before any enforcement change) or narrowly-scoped code fixes you can pick up independently.

## Escalated — still awaiting Stephen's design approval (carried forward unchanged, no new information this window)

These were already ESCALATED in the 2026-08-09/11 reviews and remain untouched:

| ID | One-line | Target |
|---|---|---|
| `2026-08-09-commit-gate-repowise-tracked-write` | Pre-commit validation runs repowise reindexing as a side effect, rewriting tracked `.claude/CLAUDE.md`/`.repowise-workspace.yaml` | pre-commit contract framework |
| `01KZK2BCXT7EKFZ6ZM2AMKFXJR` | G-RM-8 owner-decision packet needs a store-lineage registry before presenting "no prior store" as an option | WP6.1 06h decision packet |
| `01KZK529D6RRSG25B6C8T10TR6` | Historical policy needs an atomic ledger prefix-cut contract, not a "wait for final position" heuristic | G-RM-8 protocol |

Do not act on these without Stephen's sign-off; they need a design decision, not a patch.

## Cheap, low-risk, TDL-actionable now (additive test coverage only — good first picks)

These are still exactly as valid as when logged; nothing has touched them:

- **`2026-08-11-post-commit-repowise-guard-untested`** — `.githooks/post-commit`'s three protective branches (missing `.repowise/`, symlinked `.repowise/`, lock-file overlap) have zero test coverage. Add a test module mirroring `tests/tools/test_system_review_hook_gates.py`'s `mirror-tree-guard` pattern.
- **`2026-08-11-results-no-overwrite-untested`** — `.claude/hooks/results-no-overwrite.sh` enforces the CONVENTIONS-locked "never overwrite a results file" invariant with zero test coverage. Same fix shape.
- **`2026-08-13-crlf-byte-surface-unenforced`** — the declared `git_blob_utf8_lf` canonical byte surface has no pre-commit enforcement for ordinary `*.py` source (only contract artifacts are covered via `.gitattributes` patterns). Twelve files were committed CRLF by a Windows `Path.write_text` call and nothing caught it. Add a pre-commit byte-level check (reject staged blobs containing `\r\n`) with a CRLF fixture as negative control.

None of these three require a design decision — they're pure test/gate additions with a stated negative control already specified in the log.

## Re-verify before trusting: my last review's "ACTIONED" call needs a second look

**Important correction to the 2026-08-18 system review.** That review verified the `P-049 Gate 6 main merge admission` GitHub ruleset was live and marked `2026-08-11-no-mechanical-premerge-review-gate` as ACTIONED on the strength of `required_review_thread_resolution: true` plus required status checks. Five days later, `01M0PWSR73ABY48X8YW7KQX6Q6` (2026-08-23) recorded a live counterexample: five Codex review threads were published **89 seconds before PR #262 merged** and remained unresolved after merge, despite the ruleset. The gap: thread-clean evidence was read once, before all reviewers had finished, not re-evaluated at the exact merge moment. **Suggested fix:** merge admission must re-check unresolved/non-outdated threads at the exact candidate after every configured review producer reaches a terminal state, and treat a newly-published thread as invalidating prior clean evidence. This needs its own ruleset/Action change — report to Stephen, don't self-apply (GATE lane).

Also re-verify **`01M0Q0WXJSCX5WJ69H2G9DG4E3`**: the first PR #263 head passed 148 Windows-reachable controls and an independent review while 13 decisive POSIX controls were skipped; the Ubuntu-required workflow then failed 14 tests, and an isolated Linux run found 35 failures from a path-derived guard defect. If Gate 6 work touches any filesystem/concurrency code on this branch again, **require the Linux job to run before accepting review**, not after.

## Gate 6 / research_system — GATE and INVARIANT clusters (report-only; group before dispatching, don't patch one-by-one)

These are the STORE/replay/authority remediation trail from PRs #258 through #268. Per `01M0JEKDT55EG2AAWCCJ1HEEFK` (specimen-by-specimen remediation has no convergence gate — 27 threads concentrated in `discovery/spec_flow.py` alone, each fix adding a specimen test rather than closing a governed class), **do not work these as an unordered bug list.** Group by owning invariant first.

### Cluster A — directory/object-store transaction and cleanup-ownership (all 2026-08-23, all `research_system.store`)
One coherent invariant keeps getting violated in different corners: *once a durable effect is publicly observable, cleanup must never be able to erase it, and ownership of "who may still clean up" must survive process/caller-frame boundaries.*
- `01M0P48MTW2G1ZY1M7RJ7GG6SM` — `WriterLock`: publication proof and cleanup state conflated; a failed directory-durability sync was treated as successful ownership, and an anchor-close cleanup error could erase an already-completed exact-ownership proof.
- `01M0P8Z0SW8RK6BWA1YP54ZC2J` — `DirectoryAnchor`: object effects weren't bound to the held generation; identity verification happened *after* the effect, too late to prevent a race.
- `01M0Q19XP9P3R6B1CF9TS6BF3Z` — object link effect ownership starts too late: a post-link identity-read failure on Linux could raise before `owns_claim`/`owns_final` was set, leaving orphaned claim/final files with no cleanup call.
- `01M0Q5WWJTYMEX0CJFVK1A2Z8Z` — delayed cleanup can invalidate a successful retry: once a final link can support public success, the suggested fix is that rollback deletion authority must be **permanently revoked** from that point.
- `01M0QAFYK52K1C6YMZ0KJ6JMN9` — domain snapshots must exclude protocol/runtime-namespace files, or a valid safety mechanism (a lock file) gets misreported as a domain mutation.
- `01M0QAD7EVJ5RK5XQJV9TMWHCQ` — retained namespace ownership must survive the caller frame (a discarded local transaction object could strand a pending-deletion owner).
- `01M0QC2T5RFAAV3SEVWCDA4YNC` — recovery negative controls must cross the real balanced `with`/context-manager boundary, not simulate an unbalanced manual `__enter__()` call (which tests caller misuse, not recovery).

**Suggested consolidated action:** one mechanical transition matrix — staged / canonical-linked / durable-acquired / cleanup-deferred / released / fail-closed-poison — with injected failures at every edge (including rollback and handle-close failures on both Windows and POSIX), rather than continuing to patch each corner as review finds it.

### Cluster B — replay-validator propagation and authority binding (spans 2026-08-15 → 2026-08-18, still open)
- `01M02FCZWS5EKPER5XYKJ8CZJE` — recursive replay drops the authority validator after the first Discovery event.
- `01M0668E8R3B941Z3KJRC0XK9D` — external evidence replay lacked validator propagation to shared projection/context/command-service callers.
- `01M06KMJM5VVR1MMGM59D0AS2M` — backup/restore conflated two distinct authority roles (local-administration vs. external-semantic-authority) under one injected resolver.
- `01M06KDPPT6AYE3Y0S4XKY7D7Z` — multi-reference consumers (release publication) rebuilt ledger/resolver/replay independently per reference, risking two references resolved from different ledger tails in one logical operation.
- `01M0N26XTRERJH5M2PT7ZZ1JDT` — replay verified ledger hashes without binding resolved external-document bytes to the recorded registration identity (a coherently rehashed substitution could pass).

**Suggested consolidated action:** one shared, typed replay-validator dependency contract that every replay caller must accept explicitly — this is named directly in `01M0668E8R3B941Z3KJRC0XK9D`'s suggested improvement and would close most of this cluster at once.

### Cluster C — schema/identity binding, one-off (still open)
- `01M0GPWXK3RYSW5HQV9CWRKB5G` (2026-08-21) — persisted active schemas need a *generic* immutability gate. A `RepairStoreBinding` v1 schema was tightened in place (SHA-256 changed) and passed all 103 pre-commit contracts, but broke replay of the live 444-event control ledger at position 146. Fixed for that one schema; **nothing generic stops the next one.** Suggested: an append-only manifest of persisted active `(schema_id, version, sha256)` identities, checked in CI/pre-commit against every current active schema.
- `2026-08-22-deterministic-id-retrofit-erased-historical-state` (CONTRACT lane) — a deterministic brief-input identity retrofit was reused as the read predicate for *historical* state too, silently resetting a terminal `PROVEN` result to `NOT_RUNNABLE`. Suggested: any identity-derivation retrofit needs a three-part contract (canonical identity for new writes / fail-closed admission for historical reads / a real persisted-fixture replay control bypassing the new writer).
- `01KZZ56Y8ZSJWCF0D13EX447B5` — content identity (SHA-256) proved a historical file's bytes but not its *current authority*; a superseded prerequisite an owner decision had already rejected could re-enter as a governed member via exact-byte binding alone.
- `01M065H67WF1BT5ZY8FTZFXPVY` — a public CLI accepted a flat semantic intent under a schema_id naming the protected durable *envelope* schema, without validating public bytes against the identity they declared.
- `01M0NVDGS4CBFMH6RYFCMK2Y01` (2026-08-23) — a frozen release-snapshot scenario contract named events the live Gate-3 producer no longer emits (producer/consumer drift, not a changed result). Fix candidate exists, awaiting independent review + integration.

### Cluster D — older WP6/authority items, still unaddressed (from the 2026-08-09/12/14 batch)
- `01KZKCZYZF4TRYVMWSC4Z60MZ0` — executable manifests validate binding/digest fields but not authority-metadata fields (`accounted_base`, `protocol_activation`, `owner_protocol_decision`).
- `01KZMNV2ZQ3A2MDC9JN0XE9G13` — independent review didn't exercise the real acceptance provenance join across contract/schema/producer/pack records with distinct handoff identifiers.
- `01KZMYBM61C5QDY995MXN3FCHS` — virtual preparation projection omitted a chronology invariant (`relationship effective_at <= requirement accepted_at <= pack authored_at <= evaluation_time`) that the real seam enforces.
- `01KZN1N4CWERHRZ6HWEHGX0BCA` — a reused publication helper captured stale actor/time defaults as Python-level mutable module globals.
- `01KZP0F2TWTQ9BTVPVE02NMRSW` — a public transition path accepted a schema-valid caller-built substitute for a sealed upstream producer's output without verifying producer provenance.
- `01KZR0P7WS2FMC2DG6D42PDRD2` — a "positive lifecycle" test stopped short of the catalogue's terminal promotion rows (OR-026/OR-027 never reached in routing).
- `[01KZQ8225BFXSTAZBFNM2JCPAV]` — PARTIALLY addressed (PR #246 fixed one instance); the systemic ask — a generated parameterized negative matrix over every direct-index boundary, not just the three JSON fields CodeRabbit named — is still open.
- `2026-08-12-conditional-namespace-in-a-global-identity-fence` — `research_system/discovery/runtime.py::_discovery_identity_exists`'s "unconditional" fence is still state-conditional; three rows executed pre-genesis could permanently brick the one-time W11 genesis.
- `2026-08-12-partial-application-of-a-new-enforcement-pattern` — a new same-transaction-join binding pattern was applied to 2 of 3 sites it should govern.
- `2026-08-12-wp61-lane-lacks-t2-independence-guard` — the WP6.1 materialization lane has the exact producer/validator import-independence property T2's sibling lane machine-checks via AST, but no equivalent guard.
- `[01KZWYYAG485N6XQ7BAWYX86BB]` — Discovery topology gates prove import direction/reachability but not that each accepted command's complete transaction/streams/digest/authority are bound before reduction.
- `2026-08-13-exemption-granularity-mismatch` — `transactions.py`'s digest-binding exemption is declared per-row where the underlying property (preimage recoverable?) varies per write-set *variant*; the existing binding test is a tautology over its own table.
- `01M02E379MRA7C8SJ953QR0C1T` — actor census recognizes multiple scoped-grant schema identities but validates all of them against the default schema, breaking on a live mixed store.
- `01M03BG9WHTFRCPATN3F49G2F0` — a head-only `git ls-remote --heads` query misclassified an available cited **tag** as missing code (promoted absence-from-one-namespace into "source unavailable").
- `[01KZZ84DZNGBQYSJ1WEYP85PBY]` — pre-publication interruption leaves empty staging directories even though the durable ledger correctly shows zero-mutation.
- `01M083VSDNA910RQXWRAPZC66F` — `AdoptLateArtefact` has no upper bound on caller-asserted observation time (a 2099 timestamp was accepted).
- `01M083YZH31FKM1DASB8VZ5K3A` — release-publication context coerces malformed manifest fields to strings instead of failing closed at the decoder.
- `01M08470YEG5EX6X168AGPA0ZM` — Windows lock-crash recovery has mocked controls only; no real spawned-process-crash control, and the generic `os.kill(pid, 0)` fallback returns "unknown" on Windows.
- `01M084RS15MANFKZR2HQYP82R5` — SPEC coordinator treats shared-ledger `row_id`/`owner_row_id` as globally unique, letting unrelated events from other Candidates advance status/idempotency/actor checks.
- `01M084XV9K5T9J5RSQ9CNG0AYN` — caller-controlled `submitted_at` passed directly to governing-review/decision currentness resolution with no upper bound against the trusted service clock.
- `01M08ZABERS77G9G7YT5WH6BHY` — replay-provenance fields (terminal event ID/hash) got folded into the durable semantic-decision hash, silently breaking two production authority consumers' compatibility.
- `01KZY8D591593SM3BW9KJCM5PT` — Codacy check annotations lack tool/rule identity on the GitHub check surface; the unauthenticated v3 API can restore it but isn't wired into the pre-merge gate.
- `01M0N26XWWD3N7AHCMQ87YVWH2` — a recovery path's "replace into random cleanup name" pattern doesn't prove the claimed inode is still the source it inspected (should be a no-replace hard-link claim primitive instead).
- `2026-08-22-focused-tests-masked-import-cycle` — a cold-import + independent-collection check exposed a candidate-only circular import that package-focused tests never would; suggested as a standing pre-freeze step.

## PROCESS — workflow/supervision lessons (report-only; feeds ARS process design, not code)

- `01KZMZJ0489J0R0EHB94P0BACA`, `01KZP2M6V6J3Q4Y8N7C1H5RT9A` — **blocked on Atlassian auth.** The Jira MCP connector is unauthenticated in this Claude Code environment (and was in the last review too). Can't re-verify KAN-65/KAN-97 state from here — needs `/mcp` auth in an interactive session, or check directly via the Atlassian web UI.
- `[01KZYX3JFKQ3XQD8N9S8MFKTJW]` — a Gate 6 capability description said Stephen must "supply" a `ResearchDossierAdmitted` record, when it's actually an internal receipt the system must produce — vocabulary that manufactures a false owner blocker. Worth checking whether any *current* Gate 6/Jira description repeats this pattern.
- `[01KZYZV73TPBSJNAPBKA73TFMP]` — a "certify" dispatch discovered uncommitted implementation deltas already present in the audit worktree before baseline truth was established (same shape as this handoff's own quarantined-checkout finding, one level up).
- `01M0P5ZCBYR5HT1V47F2G1X7D2` — an in-tree review record can't certify the commit that contains it (self-reference loop); final-head authority needs to live outside the subject it certifies (external GitHub review, or an immutable out-of-tree artifact).
- `[01M0KTDNNMXXVP88WWFRRPK49E]` — a read-only Explorer dispatch recommended creating a *second* competing plan (`06s`) despite an explicit single-authority constraint naming `06q`. (Given the replan is now genuinely happening per `2026-08-24-plan-as-overengineering-vector`, this earlier objection may be moot — but check that whoever approved 06s did so as an explicit supersession, not by drift.)
- `01M0KXHJP4701QHA4FH6BB5D07` — an Explorer privileged a stale pre-integration review over live Jira + merged-main evidence, nearly reopening completed WP6.1 work.
- `01M0N5A18XF2FJV93J6PCF3K0J` — a SOURCE slice was sequenced before the STORE boundary it depended on, forcing unfinished global infrastructure into a "local" patch; suggested: require each slice to prove its shared-capability dependencies already landed before implementation starts.
- `01M0NMFM1R8GG5W183ND0YJ33Z` — file/line-count caps didn't stop a ~1000-line module from absorbing multiple independently-testable owners (subject policy + filesystem I/O + transaction orchestration + replay admission in one file); suggested: a cohesion check at the module-owner boundary, not just a size cap.
- `2026-08-22-retired-procedure-kept-live-imperatives` (RECORD lane, PR #259 documentation-contract threads) — a historical plan was labelled non-operative but still carried a complete block of unquoted, live Jira imperatives contradicting the active plan's decomposition; the same review found "exact" registries/configs/sum-types called exact without freezing their complete member catalogue. Suggested: retirement checks should fail on unquoted-imperative conflicts, and planning review should require any claimed-exact catalogue to enumerate its complete members plus completeness negatives before implementation opens.

## codex_workflow package (a separate tool, not TDL repo code — verify which repo owns it before acting)

- `[01KZW6BZYXZX7JGB85MXKTA007]` — the v1.1.1 release's `bootstrap.md` documents a `bootstrap` CLI subcommand the shipped CLI doesn't expose.
- `[01KZW6Y38D80D3HZCQ4089XYV8]` — the installer's project-entry renderer drops the original file's terminal newline when wrapping content in its protected-region markers.

## Completeness ledger

Every TDL-tagged OPEN/ESCALATED item from the 2026-08-11→2026-08-25 window is accounted for above, in exactly one group:

- **Blocking/must-read-first:** 2 (quarantined checkout, Gate 6 replan status)
- **Escalated, unchanged:** 3
- **Cheap TDL-actionable wins:** 3
- **Re-verify prior "ACTIONED" call:** 2
- **Cluster A (store/cleanup-ownership):** 7
- **Cluster B (replay-validator propagation):** 5
- **Cluster C (schema/identity binding):** 5
- **Cluster D (older WP6/authority, ungrouped singles):** 24
- **PROCESS:** 10 (2 blocked on auth)
- **codex_workflow:** 2

If a fresh full-text scan of `log.md` for `**Environment:** Codex` or a TDL file target turns up an ID not listed here, treat that as this handoff being incomplete for a newer entry added after 2026-08-25 — check `last-review-date.txt` and the tail of `log.md` past this handoff's date.

## What NOT to do

- Do not commit, discard, or build on the nine quarantined files listed in section 1 without an explicit fresh instruction from Stephen.
- Do not start a new from-scratch Gate 6 implementation slice without confirming 06s's status.
- Do not self-apply any GATE/INVARIANT/PROCESS fix listed above as a merge-admission, contract, or workflow change — propose it, stage it, and get review-then-merge; these are report-only per research-observer's routing rules.
- Do not re-fix an item without first checking whether it was already fixed in a later commit — several 2026-08-21/22/23 entries describe "Done" or "Fixed" inline; verify via `git log -p` / `git blame` on the named file before writing new code.
