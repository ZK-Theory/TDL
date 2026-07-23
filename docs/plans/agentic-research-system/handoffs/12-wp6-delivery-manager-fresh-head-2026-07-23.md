# WP6 Delivery Manager Fresh-Head Handoff

**Date:** 2026-07-23  
**Workflow system:** Standalone; never APM  
**Supervision phase:** Certify, then deliver one vertical action at a time  
**Scope:** WP6 repository delivery only  
**Efficiency-audit boundary:** The token-efficiency audit is a separate task and must not
be read, managed, reviewed, or implemented here.

## 1. Current repository state

Remote state was refreshed on 2026-07-23:

- `origin/main`: `3cc6f2a1f7a90dfd77f8bdae0de9e2c5f934a66d`.
- WP6.1 command/event/contract stack is merged through:
  - #153, merge `f032c0d0119dff433ea3029dbfbc03b52d7d4324`;
  - #154, merge `a876eaa886411dc88faae59c33f22e298a8e74e1`;
  - #155, merge `efcecd8669fb225061c6eaf300e31bc07d352f6e`.
- WP6.1 status remains `accepted_exact_bytes_only`. The merged schemas, contracts,
  validators, and tests do not themselves authorize or prove the WP6.1 runtime lifecycle.
- WP6.2 T1a is accepted and merged through #122:
  - accepted subject `599050b0809ed63a69e1a9ce6ac491b61f7ad33e`;
  - merge `e68a7c3d393782cb900154d7fb399a7deab8e275`;
  - protocol blob `4c9721a047c9b66912b9786a3b983c6f84e5ab00`;
  - canonical SHA-256 `e9512bef147d0de9bc9103b20eb1ede8b927979bfe43dd85e61fb6c27f05efda`;
  - owner comment `5013060835` accepted the exact subject before merge.

The sole WP6.2 dependency graph remains:

`T1a -> T2 -> T3/T4 -> T1b-M + T1b-H -> T5 -> T6 -> T7 -> T8`

T3 and T4 may run in parallel only after the merged T2 boundary. T1b requires both
provider lanes plus its independent human-evidence lane. T5-T8 and every M/H eligibility
transition require Stephen's later acceptance of the exact composite T1b policy/evidence
hash.

## 2. WP6.2 T2 exact accepted state

The contract/addendum phase is complete but not integrated into `main`:

- accepted candidate: `391a92753d7f746fa91a6b5455c9ce0fd01baa52`;
- candidate tree: `0254c5416925126412867d61b3045ee1563abd0c`;
- direct parent: `bba49c11ef8cd37dee7fa571f712d77a954f6b16`;
- candidate branch: `pipe/ars-wp6-2-t2-r3-remediation`;
- final independent R3 review: `655f4173db93447a068adc6e92621455c4abc85d`;
- R3 verdict: `accept`, 0 Critical, 0 Major, 0 Minor;
- owner acceptance P-040: `cbe47e1b7ed382308df61e9173722dc9085f4548`;
- author exact-state handback: `e1fe6b95cc9024cf40f1aa410f1a8970091bf4dc`;
- accepted candidate delta: exactly 27 paths from its direct parent, including one
  authorized deletion;
- current merge-base file count against `origin/main`: 53 paths.

Primary evidence:

- `docs/plans/agentic-research-system/reviews/wp6-2-t2-r3-owner-acceptance-2026-07-22.md`
- `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t2-authority-addendum-r3-review-2026-07-22.md`
- `docs/plans/agentic-research-system/handoffs/trials/gate6-wp6-2-t2-authority-addendum-exact-state-handback.md`
- `docs/plans/agentic-research-system/proposals/wp6-2-t2-research-first-scope-and-r3-remediation-ruling-2026-07-22.md`

No pull request currently integrates this accepted T2 line. Candidate, review, handback,
and owner acceptance are split across branches. None is reachable from current
`origin/main`.

## 3. Immediate next vertical action

Certify the live remote facts, then create one T2 integration line that:

1. preserves accepted candidate `391a9275...` as a reachable ancestor;
2. includes the final R3 review, exact-state handback, and P-040 owner acceptance record;
3. incorporates current `origin/main` without rewriting or regenerating accepted bytes;
4. contains no token-efficiency or workflow-method material;
5. reruns only the integration-seam validations needed for the merged state; and
6. is independently checked against the exact accepted identities before merge.

Recount `git diff --name-only origin/main...<integration-head>` before opening the pull
request. CodeRabbit will not review more than 100 files; target 90 or fewer. The present
53-path count is below the cap but is not a substitute for recounting the final head.
Stephen triggers and monitors CodeRabbit manually. Do not request, poll, wait for, or
schedule it.

The open #157 concerns workflow instructions and is unrelated to WP6 delivery. Do not
merge, amend, close, depend on, or otherwise manage it in this task.

## 4. Authority after T2 integration

P-040 accepts contract/addendum bytes only. It explicitly grants no runtime
implementation, credential resolution, provider call, T3/T4, T1b, eligibility, result,
claim, publication, or further Gate 6 transition.

After the T2 integration is merged, the next manager action is therefore a separate,
owner-authorized runtime-T2 brief. That brief must implement only the accepted
research-first authority/cost/provenance surface, pass the accepted pre-issue negative
matrix, and remain provider-call-free during its contract/runtime boundary work. Do not
infer runtime authority from the integration merge.

Only after runtime T2 is merged and independently passing may T3 and T4 be dispatched as
separate provider-specific canary/transport packages. Live calls remain bounded by the
accepted T1a protocol and the T2 cost/credential boundary.

## 5. Other WP6 package state

### WP6.1

The exact schema/contract surface is merged and accepted. Runtime Task/operator
implementation remains separately gated. WP6.4 cannot treat A4/A5 as cleared merely
because #153-#155 merged.

### WP6.3

The upstream assurance-pack contract line merged through #123 at
`9f42655d3e23a8f4bb3753f67be427093886c4d9`, final branch head
`4fa8a70bf1b061e5ddc83a7a1af202350536e976`. Earlier R3 evidence at `ae2a6cdd...`
reported three Major findings, followed by several remediation commits before merge.
Do not infer exact owner acceptance or final independent-review closure from the merge.
Reconstruct the final-head review/acceptance evidence before declaring WP6.3 complete.

### WP6.4

Project binding and the Gate 6 preflight package come after WP6.1, WP6.2, and WP6.3
outputs satisfy their own gates. WP6.4 establishes preflight eligibility; it does not
itself dispatch SCALE-01.

### WP6.5

The W11 specification line merged through #121 at
`c941965a5851d8d7063c411f65f26bb0e0957594`, final head
`5b7afca85a134aea58a513853e85e2fdeae3fe57`. The R7 report found no remaining finding
in that exact head but expressly did not accept W11 for Stephen. D-G6-4 remains open for
Stephen's exact-revision acceptance and a separate first ownership-transition batch.
No migration or ownership transition follows from the merge alone.

### WP6.6 and WP6.7

WP6.6 dossier admission requires accepted WP6.5/W11 authority and the WP6.1 operator
route. WP6.7 is a gated legacy-consolidation sequencing document only and also depends
on its named W9/T1.28 closeouts. Neither should be started by implication.

## 6. Governing sources

Read these first and only expand when a live delta or unresolved gate requires it:

- `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md`
- `docs/plans/agentic-research-system/implementation/06a-wp6-1-runtime-task-lifecycle-plan.md`
- `docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md`
- `docs/plans/agentic-research-system/implementation/06f-wp6-2-p1-activation-contract.md`
- `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
- the four exact T2 evidence records in section 2.

## 7. Manager operating boundary

- This is standalone, not APM. Do not load numbered APM skills or `.apm` state.
- Start with certification of current remote and exact Git objects; do not replay the
  entire historical campaign.
- Manage one vertical action at a time. First action is T2 integration only.
- Preserve accepted bytes and candidate ancestry. Do not squash/rebase away the accepted
  subject or rewrite it to embed later lifecycle state.
- Do not regenerate accepted WP6.1, T1a, or T2 artifacts.
- Do not reopen settled R3 findings unless the integration delta touches their authority.
- Do not authorize provider calls, T3/T4, T1b, T5-T8, eligibility, results, claims, or
  publication during T2 integration.
- Keep the token-efficiency audit entirely outside this task.

At rotation, leave one compact exact-state handback with the current remote facts, the
one action completed or blocked, and the next authorized action.
