# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-08-09

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`

**Scope:** all 72 OPEN observations

**Decision owner:** Stephen

**Operating rule:** approval authorizes a bounded verify-then-fix campaign on a reviewed branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named controls.

## How to use this packet

Choose one box per campaign. **Approve** is my recommendation in every case below. An approved campaign first re-resolves every mapped observation against current HEAD and the owning repository:

1. already compliant or superseded → record evidence, mark ACTIONED/DECLINED, archive;
2. still valid and in scope → implement the named mechanism with its negative control;
3. contradicted or owned elsewhere → record the exact owner/blocker and keep only that bounded remainder open.

This makes the log a work-control input, not a permanent accumulation of “escalated” entries.

## Decision summary

| Campaign | OPEN observations | Recommended resolution | Decision |
|---|---:|---|---|
| A. Dispatch and state currency | 13 | One state-manifest and dependency-closure campaign | `[x] APPROVED 2026-08-09` |
| B. Operational workflow boundaries | 3 | Make bus clearing, credentials, and external waits explicit boundaries | `[x] APPROVED 2026-08-09` |
| C. Git, hook, and review-seam liveness | 15 | One candidate-tree and hook-liveness campaign | `[x] APPROVED 2026-08-09` |
| D. Contract and runtime semantic coverage | 16 | Derive coverage from governed sets and real public seams | `[x] APPROVED 2026-08-09` |
| E. Durable-store and recovery invariants | 12 | One recovery/admission invariant campaign | `[x] APPROVED 2026-08-09` |
| F. MathUni curriculum integrity | 12 | Dispatch one bounded MathUni gate campaign | `[x] APPROVED 2026-08-09` |
| G. Token telemetry accounting | 1 | Fix cumulative-delta accounting with a repeated-record fixture | `[x] APPROVED 2026-08-09` |

## A — Dispatch and state currency

**Problem.** Plans, handoffs, and task prompts repeatedly freeze perishable state, omit required registries or roots, or dispatch work that has already completed.

**Approve this mechanism:** extend the existing dispatch state manifest rather than adding more prose. Before branch/worktree allocation it must resolve:

- current branch/HEAD/worktree ownership and ancestry;
- every stated blocker and claimed incomplete deliverable;
- every input root, planned contract, output path, transition owner, registry dependency, derived-field preimage, and required schema field;
- multi-lane tasks independently, advancing completed lanes directly to their next gate;
- the skill required by the artifact type before authoring begins.

**Controls:** stale blocker; already-existing deliverable; missing contract; rootless input; omitted registry; unresolved required field; duplicate attached branch; completed lane incorrectly redispatched.

**Closure evidence:** a table for all 13 observations showing fixed / already compliant / superseded, plus manifest fixture results and synchronized skill checks.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## B — Operational workflow boundaries

**Problem.** Three operations are being treated as ordinary task steps even though they cross a permission or external-owner boundary: clearing an APM bus slot, checking specialist credentials, and waiting for owner-controlled review.

**Approve this mechanism:** define explicit terminal seams:

- bus clearing uses the authorized file-write path after durable task-log capture; inability to clear is surfaced once, never bypassed;
- external specialist work begins with a cheap credential smoke test and hard-stops on auth failure;
- large delivery goals end at durable PR-ready handoff; a fresh lightweight closer resumes after Stephen reports external review completion.

**Controls:** denied bus clear preserves the report; expired credential stops before expensive work; unchanged external review state does not rehydrate a large campaign repeatedly.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## C — Git, hook, and review-seam liveness

**Problem.** Gates sometimes judge the mutable working tree rather than the candidate tree, lose interpreter/path/mode assumptions, or have no evidence they executed. Review evidence also decays at merge.

**Approve this mechanism:** one Git/gate campaign that:

- evaluates commit admissibility against an isolated staged candidate tree;
- uses history-bearing, `core.autocrlf=false`, `core.longpaths=true` validation clones when tests inspect Git objects;
- keeps read-only review roots clean by using an external/pre-existing interpreter;
- adds watched failures and durable receipts for hook installation and mirror-tree decisions;
- restores and continuously verifies tracked hook executable modes;
- rejects direct local-main integration and copied merge-message impersonation;
- revalidates exact-reference pins and affected tests at the real merge seam;
- classifies parent-baseline controls as remediation-red or preservation-green;
- fixes the empty-index `prepare-commit-msg` count without changing hook policy.

**Controls:** missing/non-executable hook; malformed mirror path; linked-worktree interpreter; staged restoration; long path omitted at checkout; unrelated dirty result file; one-parent copied merge message; stale merge reference; empty staged set with stderr; parent preservation control.

**Closure evidence:** every hook has both a watched failure and positive execution receipt; `git diff --check`; exact staged-tree and merge-seam fixture results.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## D — Contract and runtime semantic coverage

**Problem.** Several green suites prove literal shape, one instance, or one command/event cardinality while leaving the governed semantic set, sibling records, downstream consumers, or runtime activation untested.

**Approve this mechanism:** make validators derive their cases from the accepted governed set and exercise the real public seam:

- equality pins for derived constants, with machine-diffable coverage of the contract’s constant list;
- executable enum boundaries and canonical payload preimages;
- exact sibling/class enumeration from contract/catalogue authority;
- proposed schemas excluded from runtime activation until accepted;
- lifecycle adjacency sequences and one-to-many/many-to-one binding rows;
- complete external-record writer/resolver classes and downstream consumer shapes;
- retry identity bound before missing-index repair;
- authorizing events committed before independently consumable derived objects.

**Controls:** omitted sibling; governed-set shrink; contradictory enum boundary; copied-but-noncanonical payload; proposed schema presented to runtime; adjacent lifecycle order; batch cardinality mutation; downstream shape near-miss; changed retry command; object without authorizing event.

**Closure evidence:** generated coverage matrix equals the authoritative set, with no hand-maintained subset; public-seam negatives prove unchanged durable state on rejection.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## E — Durable-store and recovery invariants

**Problem.** Recovery and admission paths can mutate before validation, lose command/origin identity, race on locks, trust non-durable generations, or accidentally depend on a retired source.

**Approve this mechanism:** one durable-store campaign that establishes:

- side-effect-free `open_existing` validation before any constructor repair;
- complete command/schema identity in recovery markers and cross-command rollback isolation;
- atomic stale-lock reclamation and physical-root identity on Windows aliases;
- read paths never create directories;
- cleanup preserves the primary failure and retryable state;
- directory-flush failure blocks generation admission;
- initialization records immutable origin provenance;
- configured restore source joins exactly to the approved witness;
- moved-store acceptance resumes after mutation and succeeds with the original root unavailable;
- test lock wrappers conform to the real lock identity.

**Controls:** missing child remains absent; changed schema/actor/grant/payload marker; competing command owns target; two reclaimers/new owner; `\\?\` alias; read rejection inventory unchanged; multi-handle cleanup failure; repeated directory-flush failure; deleted origin; mismatched source witness; retired source removed; nonconforming lock double.

**Closure evidence:** real public loader/CLI probes on the native platform plus decisive no-mutation negatives.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## F — MathUni curriculum integrity

**Problem.** Curriculum migrations, ID renames, generated lesson quality, stdout encoding, semantic linting, and zero-denominator coverage currently have silent green paths.

**Approve this mechanism:** dispatch to the MathUni repository as one bounded integrity campaign:

- resolve unit resources to real sections and cross-check primary-text migrations;
- reconcile syllabus IDs across progress, SRS, lessons, problems, solutions, and learning records;
- add a scored strong-reviewer lesson rubric after mechanical admission;
- add piped CLI encoding smoke tests;
- prove `update_unlocks` preserves existing progress before removing stale caution prose;
- decide and lock line-ending policy;
- add semantic near-miss, missing-input, entity/leak, structural-count, and balanced-tag controls;
- report coverage denominators and classify zero references as UNCHECKED, with `--min-refs` where applicable.

**Controls:** nonexistent section; orphan ID; mathematically wrong but well-formed lesson; cp1252 pipe; mastered-status regression; near-miss resource; absent input; malformed entity; crossed `sup/sub`; zero references.

**Closure evidence:** corpus-wide run, selftests with watched failures, and an explicit disposition for existing corpus debt rather than silently grandfathering it.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## G — Token telemetry accounting

**Problem.** A repeated nonzero last-call record can be double-counted even when cumulative token usage did not advance.

**Approve this mechanism:** calculate calls and phase slices only from positive deltas between successive cumulative totals; warn when last-call components disagree with the cumulative delta; expose cache-write input explicitly.

**Control:** repeated last-call record plus compaction bookkeeping record must add zero incremental usage.

**Decision:** `[x] APPROVED BY STEPHEN — 2026-08-09`

## Complete observation-to-campaign map

This is the completeness ledger. An observation may inform several controls, but it has one owning resolution campaign.

### Campaign A

`58`, `65`, `70`, `73`, `74`, `77`, `80`, `88`, `100`, `124`, `140`, `01KYY7DWPYBAQX3P9Q422TDZH0`, `01KZ1V1SERAEPB2ASJDMXRJ80F`

### Campaign B

`64`, `91`, `01KZ3HM36Q8MDY2G2HSK334DP1`

### Campaign C

`84`, `101`, `103`, `104`, `120`, `121`, `122`, `123`, `137`, `146`, `01KZ2SJJJ55APRV36G53DPGC40`, `01KZ8F4J6W3Q2N7M9T5R0C8BHD`, `01KZ913F8WDQPQBQ987V305D7S`, `2026-08-06-precommit-hook-exec-bit-dropped`, `01KZJRRT4QK55YKM9Z7ZVX0DYV`

### Campaign D

`86`, `87`, `111`, `117`, `128`, `129`, `131`, `138`, `139`, `147`, `01KYV4AHVH5DRSGZMXD8YPR0GN`, `01KYXYHVJQZ3DAVF8GQG67V10D`, `01KYYDXV2C93X7S3P8R3WDNBPV`, `01KYZ4VJAG6JVF1T3ZX5JRE2NM`, `01KZ2FR7BMBDNHJVBEAYJPD4P6`, `01KZ5BSJV5B79JTMSMSRNX0N9X`

### Campaign E

`01KYZ84R9Y80VG8N5BJQJ0C79C`, `01KYZ84RB87PZ7HCR71984FAQ4`, `01KYZ84RCMT2Q5V202TMRVZQC6`, `01KYZ8W4ETJ9FGVZ2PYNAC7FVF`, `01KYZBCCM5Y6XK8EVVTSC9ASZF`, `01KYZW4ZHN97PYCGYXTWE9HAF5`, `2026-08-02-validate-layout-before-mutating-constructors`, `2026-08-02-win32-directory-durability-retry-barrier`, `2026-08-02-store-origin-information-loss`, `01KZ1P33M70RPNQW1HAVEDD9HG`, `01KZ2K4C0E2PTX15WC1G923QV7`, `01KZ3MM325YW3PCPYNT8KZT1QM`

### Campaign F

`96`, `97`, `98`, `99`, `102`, `107`, `109`, `113`, `115`, `119`, `2026-08-08-lesson-lint-no-tag-balance`, `2026-08-08-coverage-gate-vacuous-when-source-unnumbered`

### Campaign G

`110`

## Recommended execution order

1. **A — dispatch/state currency:** prevents new work from being launched against stale or incomplete premises.
2. **C — Git/hook/review seams:** restores trust in the gates used by every later campaign.
3. **D — semantic contract coverage:** closes false-green acceptance paths in active lifecycle work.
4. **E — durable recovery:** highest consequence runtime invariants, after the review seams are trustworthy.
5. **B — workflow boundaries:** small, independent operational correction.
6. **F — MathUni integrity:** separate repository and owner surface.
7. **G — telemetry:** useful but does not affect scientific or runtime correctness.

## Resolution rule after Stephen’s decisions

For each approved campaign, create one bounded implementation/reconciliation task. On completion, update every mapped observation with one of:

- `ACTIONED — Applied to <artifact> (<evidence>)`;
- `ACTIONED — Already compliant at <exact commit/path/control>`;
- `DECLINED — <owner rationale>`;
- `OPEN — BLOCKED on <specific owner/external action>` only when implementation genuinely cannot proceed.

Archive all ACTIONED/DECLINED entries in the same transaction. The weekly review is not complete merely because an OPEN entry contains the word “escalated.”
