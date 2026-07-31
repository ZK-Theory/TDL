# PR #198 Independent Pre-Merge Re-Review — Exact Subject `0137d2c`

## Verdict

`accept_exact_subject`

Exact subject reviewed:
`0137d2caadd8b80d7c133bf63fe5f6bea065cf2d`.

PR198-RR2-A is closed at this exact subject. The plan now literally
classifies the shipped `eval validate -> _eval_validate -> load_p0_coverage`
root, closes the parser-derived required-root set, carries the pure-root
negative through Stage B tasks 4 and 8 and close-out evidence, and corrects the
durable registry names. Direct source inspection confirms that the current
root performs package/coverage validation without executor resolution,
lifecycle dispatch, routing, coordination, provider-command construction, or
provider issue.

This report is review-only. It grants no owner acceptance, G-RM gate, stage
dispatch, implementation, provider, result, claim, merge, GitHub-thread, or
review-service authority.

## Exact-subject and isolation evidence

| Item | Required | Independently observed | Result |
|---|---|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\pr198-review-0137d2c\TDL` | same resolved path | match |
| Branch | `review/pr198-premerge-0137d2c` | same symbolic branch | match |
| Initial status | clean | no porcelain entries | pass |
| Local HEAD | `0137d2caadd8b80d7c133bf63fe5f6bea065cf2d` | same commit | match |
| Local tree | `ee7d5109719565d1911da7f9000798973859aedf` | same tree | match |
| Base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | same GitHub base; ancestor of subject | match |
| PR | `stephendor/TDL#198` | open, non-draft | match |
| PR branch | `codex/rm-lane-rereview-remediation` | same remote branch | match |
| Live PR head | exact local HEAD | `0137d2caadd8b80d7c133bf63fe5f6bea065cf2d` | match |
| Base diff | 20 Markdown paths | 20 paths; no non-Markdown path | match |

The local review branch intentionally differs in name from the PR branch. No
identity, ancestry, status, or routing drift was found. GitHub merge state was
not used as semantic evidence.

## Bounded remediation

The diff from
`3577d209a25af272c91ddb2baa4c9e2843ed2af8` to the reviewed subject changes
exactly these two files:

- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md`
- `docs/plans/agentic-research-system/reviews/rm-lane-pr198-premerge-rereview-85f33e6-response-2026-07-31.md`

No Critical, Major, Minor, or editorial finding remains in this bounded
remediation.

## PR198-RR2-A closure matrix

| Required check | Independent disposition |
|---|---|
| 1. Literal root chain | **Closed.** 06j literally records `eval validate -> _eval_validate -> load_p0_coverage` at line 184. The actual parser binds `eval validate` to `_eval_validate` at `research_system/cli.py:611-615`; the handler calls `load_p0_coverage` at `research_system/cli.py:220-232`. |
| 2. Pure validation class and prohibited effects | **Closed.** The normative row classifies the root as pure package/coverage validation and prohibits executor loading, lifecycle-dispatch construction, routing, coordination, and provider issue (`06j:184`). The repository-wide structural obligation also rejects arbitrary-fixture `ProviderCommand` construction (`06j:187-191`), and the pure-root negative is executor/lifecycle/provider-free (`06j:197-201,381-383`). Direct source confirms `_eval_validate` only resolves the coverage roots and calls `load_p0_coverage`; that loader validates exact coverage and fixture packages (`research_system/evals/coverage.py:86-149`), while `validate_fixture_package` performs file/schema/hash/retention validation (`research_system/evals/fixture_package.py:149-250`). No executor, lifecycle, route, coordinator, or provider-command seam is called. |
| 3. Parser-derived structural closure | **Closed.** The required root set is derived from `eval` parser bindings plus first-party coverage/rederivation reachability, with no default class and failure for any unclassified root (`06j:163-167,187-191`). This is not a source-file allowlist or direct-call-only probe (`06j:200-201`). |
| 4. Distinguishing real-parser negative | **Closed.** The normative negative is explicitly parser-dispatched and proves the pure root remains free of executor resolution, lifecycle dispatch, routing, coordination, and provider issue (`06j:197-201`). Stage B task 8 requires dispatch through the real parser (`06j:381-383`). |
| 5. Stage B and close-out evidence | **Closed.** Task 4 derives/classifies the parser-root set and requires pure-root absence of executor/lifecycle/provider effects (`06j:355-364`). Task 8 requires the real-parser negative (`06j:375-387`). Close-out must record the parser-derived set, root class, and executor/provider-free `eval validate` negative (`06j:398-401`). |
| 6. Actual four registry names | **Closed.** The durable response names `CONTROL_STORE_EXECUTORS`, `ADAPTER_SCIENTIFIC_EXECUTORS`, `CONTEXT_ROUTING_EXECUTORS`, and `RELEASE_TRANCHE_EXECUTORS` at lines 30-32. Those exact maps exist in `research_system/evals/executors/control_store.py:234`, `adapter_scientific.py:415`, `context_routing.py:220`, and `release_tranche.py:601`. |
| 7. Stale registry misnames removed | **Closed.** The response contains neither `P0_CASES` nor `ADAPTER_SCIENTIFIC_CASES`. |
| 8. Historical review identity | **Closed.** The preserved historical review is Git blob `6a638f8e59ea5255fa915ae4a3be4be678e78590`, exactly 15,388 bytes, with SHA-256 `a5a6beb7b7094afd5fa8f642d6bee93526d9af2d98a6e893d097387d9d078817`. |
| 9. Diff, links, encoding, line endings, whitespace | **Closed.** The bounded diff contains exactly the two named Markdown files. Both relative links resolve. Both committed blobs decode as strict UTF-8, have no BOM, CRLF, or bare CR, and therefore use LF-only line endings. The plan has a terminal LF; the response's absent terminal LF is inherited from its pre-remediation blob. `git diff --check 3577d209..0137d2c` exits zero. |

## Consistency and authority audit

- The plan's normative root table, structural test, Stage B task 4, Stage B
  task 8, and close-out evidence now carry the same parser-root obligation.
- The response's registry names match the actual source maps and the 06j
  registry table.
- The historical `85f33e6` review identity is byte-authoritative and matches
  the digest recorded in the response.
- G-RM-3 and G-RM-12/13/14 remain owner-controlled and open. Nothing in this
  review dispatches Stage A or Stage B, changes the PR subject, or establishes
  owner acceptance.

## Validation scope and residual risk

Validation was limited to the exact identities, direct source chain, bounded
two-file remediation, Git blob bytes, link resolution, encoding/line endings,
and whitespace checks required for this Markdown-only finding. No runtime
implementation test was credited because 06j Stage B remains future work. The
inherited `TaskCreated` command-schema-field failure was not run or used as
evidence for or against PR198-RR2-A.

The remaining risk is implementation risk: Stage B must later produce the
parser-derived structural test and real-parser negative specified by the
accepted plan. This exact-subject review does not establish that future runtime
closure.

## Files changed by this review

Only this required report was added:

`docs/plans/agentic-research-system/reviews/pr-198-premerge-rereview-0137d2c-2026-07-31.md`

No PR subject, reviewed plan, response, runtime, test, GitHub thread, review
service, merge, stage, or owner-gate state was modified.
