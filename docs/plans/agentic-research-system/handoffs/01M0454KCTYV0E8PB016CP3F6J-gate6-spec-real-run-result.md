# Gate 6 SPEC real-run result

**Recorded:** 2026-08-16

**Route:** `SPEC-GATE6-RUN-V1`

**Candidate branch:** `codex/gate6-spec01-spec02-real-run`

**Implementation head before this record:** `5d2301e3356347bf41e9335f1a45726ba2036f05`

**Jira capability:** KAN-103, under KAN-12

## Result in plain English

Gate 6 has now been exercised as a real research workflow rather than only as
a collection of schemas and tests. The public ARS route admitted the SPEC
contracts, ran SPEC-01 against a real paper and repository, obtained
independent review and an owner decision, then deliberately continued through
SPEC-02 as a non-promotional methods spike.

The result is useful but bounded. The spectral persistent-homology method is a
credible candidate for an experimental or benchmark track in the ongoing
research project. It is **not yet justified as the default empirical method or
as the basis of a research claim**. The run therefore ends at `PARK`, which in
this context means "retain and revisit when the empirical design is ready",
not "the method failed".

The first SPEC-01 assessment understated the source evidence by treating the
paper-cited `neurips2024` locator as an unavailable branch. The locator is a
valid lightweight Git tag at commit
`145efcde673f1a1897eff250b77221d26c34c479`. An append-only correction withdrew
that limitation before the final owner decision. This exposed a genuine ARS
resolver weakness: it had treated a branch-shaped web URL too literally and
did not resolve heads, tags, and direct Git locators as one source-reference
family.

## What was actually run

- SPEC-01 assessed Damrich, Berens, and Kobak, *Persistent Homology for
  High-dimensional Data Based on Spectral Methods* (NeurIPS 2024) for
  suitability in the ongoing project.
- SPEC-02 executed 126 frozen configurations and 42 deterministic reruns.
- All six spectral configurations passed their frozen technical checks:
  effective-resistance neighbourhoods at `k=15` and `k=100`, and diffusion
  neighbourhoods at `k=15` and `k=100` for `t=8` and `t=64`.
- A second whole-run execution reproduced the raw result bytes exactly.
- The run used synthetic data only. It did not estimate a substantive effect,
  publish a scientific claim, or promote the method into the primary analysis.
- A stable-index local k-nearest-neighbour wrapper replaced unavailable
  `vis_utils` packaging. That was adequate for the bounded implementation
  spike but remains a limitation for upstream-equivalence claims.

## Durable result

The final public status is:

```json
{
  "block_reason": "candidate evidence is recorded; no scientific claim was published",
  "capability_state": "PROVEN",
  "completed_stage": "spec_02_owner_decided",
  "next_action": null,
  "route_id": "SPEC-GATE6-RUN-V1"
}
```

The live control ledger closes this run at position 444 with
`ResourcesReleased`, event hash
`ff738e0e548eb556faf520e72cce56c8acb1599ffab6a584ecea5ea6deb349da`.
The research candidate remains parked:

- candidate: `obj_01a00620-0f74-7613-a7b0-dffbb50d9663`;
- assay: `asy_01a00620-0f74-74e6-b440-f760f4eb6731`;
- spike: `spk_9fc9324c-8f28-7066-89bb-d4f708ef7d44`;
- completed attempt: `att_c7cf1966-93a1-7114-9b00-61df0d7b94ca`.

The live control store contains the following hash-verified artefacts:

| Purpose | Artefact | SHA-256 |
| --- | --- | --- |
| Raw SPEC-02 execution | `art_449b7235-3114-7043-8b3e-6ca76dc14768` | `dc3811bd50423ebf7748e14d998e5cbe237e59b83661ee5feca0e78807139103` |
| Source evidence | `art_2e7531f9-020b-7775-83c4-cac52a2f6fed` | `ac0d2c49c0563926a1a52aba91fe0dbd95d8d4e7c2d3143a6c3e4c23bcbc8464` |
| Frozen checks | `art_f0cbbf39-1356-772a-86c2-fca6391bfa45` | `5705c5be0e9217c84dc8cefe9a7699913ca593dcc92fe1937c6bc650d3ef36be` |
| Result summary | `art_ddf81b12-ffb4-7944-872f-aff3177b46c4` | `792eeccfba777963fd67bc7178ebdd0c3c751035b224473b9e05288ccb7358a8` |
| Canonical return wrapper | `art_8e65db46-dd82-702b-84ff-c7282bc88c61` | `a334a81c61e803c5dad90078cc8be808230ec12b1c05c9272c39ccafaa7df14c` |
| Source correction | `art_f14d8ecc-9204-7ee3-a7be-6d72c870f986` | `01de9ae097a589deec560c0b1eef8739f4828cc96e4ecddc6f4f94ab6360c3c4` |
| Live SPEC-02 approval | `art_0b3578b7-c96f-7e0e-a6d0-a1a38ba9c1de` | `99407a4c96a5c5a00135fb02e7a04dac6034fe8750b2cc89d9aa8e804c62a024` |

These are durable in `C:\Users\steph\TDL-ARS-WP64-Control`; that live store is
the evidence authority. A separate backup/archive copy has not yet been
verified.

## What the candidate branch adds

The branch turns the SPEC route into a public, durable workflow. Its main
capabilities are:

- exact SPEC-01 and SPEC-02 route, dossier, path, brief, return, correction,
  approval, and evidence contracts;
- governed repair and descendant advancement of a stale live store binding;
- governed registration of real Codex Desktop actors and scoped owner grants;
- owner-operated context handoff without a provider launch;
- public Discovery operator and SPEC coordinator commands;
- real brief-input registration, scientific review and use-authority gates;
- exact assay scoring, review, owner decision, spike execution, return,
  correction, and terminal non-promotional decision;
- replay compatibility for historical authority events and mixed control /
  Discovery ledgers;
- idempotency, recovery, physical-path, redirect, provenance, role-separation,
  and no-corruption controls across those seams.

Construction and verification used focused contract, unit, integration,
public-CLI, recovery, adversarial, replay, and exact-head checks. The real live
route is the decisive positive-path proof. No single monolithic full repository
suite was used as the acceptance oracle for this campaign.

## Gate 6 interpretation

The run proves that the assembled Gate 6 machinery can carry a real research
subject through durable evidence, independent review, owner decisions, an
actual bounded computation, correction, and terminal cleanup. That is a
substantial validation of the system.

It does not mean every Gate 6 concern is closed or that the branch is already
integrated. At the time of this record the capability state is:

**PROVEN, awaiting pull-request review and integration.**

The research outcome is:

**PARK for empirical adoption; retain as a promising experimental / benchmark
candidate.**

## Remaining work after this pull request is formed

1. Review and integrate the candidate branch; re-read the final merged Jira and
   repository state before marking the capability integrated.
2. Preserve an independent backup/archive of the durable result artefacts and
   verify restoration by hash.
3. Generalise source-location resolution so paper links backed by branches,
   tags, or direct commits are resolved semantically before absence is claimed.
4. Decide whether to replace the local stable-index wrapper with the upstream
   repository's exact neighbour construction and, if so, run an equivalence
   comparison.
5. Freeze the real survey estimand, representation, data-access path, and
   non-redundant research question before using this method in an empirical
   analysis.
6. Reconcile the auxiliary operational task projection
   `tsk_60c5549e-d11f-7d17-8145-d80e144aa537`, which remains `in_progress`
   although its attempt completed and its lease and resources were released.
7. Improve the standard human-readable result view so future operators do not
   have to reconstruct the research judgement from technical ledger records.

Those are follow-on jobs. They are deliberately not mixed into the present
candidate or used to erase the successful real-run evidence.
