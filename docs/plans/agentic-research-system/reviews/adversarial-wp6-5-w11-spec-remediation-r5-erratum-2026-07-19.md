# Additive erratum to the WP6.5 W11 remediation R5 review — 2026-07-19

## 1. Corrected artefact and trigger

- **Corrected artefact:** `adversarial-wp6-5-w11-spec-remediation-r5-review-2026-07-19.md`
- **Artefact commit:** `07d2d1315accb211d4c257cc7ea28985871dc4f1`
- **Artefact Git blob:** `057789ec492db7e12560b0ec22aea439af569aad`
- **Artefact SHA-256:** `f7c5d37736661d7c62b7ee94420e185eb93f73796b0347ea7ed439e46cee83b2`
- **R5 exact reviewed subject:** `892d1d1650cdcf71d2a886318e174a18e11d5de0`
- **Correction trigger:** CodeRabbit review `4729612870` at exact PR head
  `ef300900476a7479e7926fc345279bb09800447c`
- **Finding comments:** `PRRC_kwDOQn1MU87XJRLV` and
  `PRRC_kwDOQn1MU87XJRLW`

This is an additive, epoch-aware correction. The R5 artefact remains byte-identical.
The corrections below supersede only the identified wording for later interpretation;
they do not alter R5's `approved` verdict, severity counts, reviewed subject, finding
dispositions, or action authority.

## 2. Correction to the R3-M2 finding label

R5 line 110 records the label:

> R3-M2 — catalogue bootstrap required prohibited runtime

The corrected label is:

> R3-M2 — catalogue bootstrap required a prohibited runtime

The omitted article was a catalogue-summary wording defect only. The finding ID,
`Closed` disposition, explanation, R3 evidence, and R5 verdict are unchanged.

## 3. Correction to the R5 action boundary

R5 §15 incompletely states that the review made no file changes and refers to PR #124
without explaining that it was a cross-PR safety boundary. For all later use, interpret
and cite the R5 action boundary as follows:

> The R5 review execution was read-only through its exit checks. Creating and
> provenance-tightening the R5 report was the reviewer's sole authorized post-review
> file write; the reviewer did not stage, commit, or push it. The main agent later
> recorded that report in the separate provenance commit
> `07d2d1315accb211d4c257cc7ea28985871dc4f1`. Apart from creating the report, no
> reviewed artefact changed. Neither the review nor report creation made a branch
> change, push, PR comment, thread resolution, CodeRabbit trigger, merge, acceptance
> decision, schema/runtime mutation, admission, ownership transition, cutover, result,
> eligibility, or claim action. The reviewed PR was #121; PR #124 and every other PR
> were untouched.

This correction distinguishes the read-only review epoch from the authorized creation
and later recording of its evidence. It neither recasts the R5 report as part of its own
reviewed subject nor claims that R5 independently reviewed its post-review write.

## 4. Preservation and decision boundary

The R5 report, R4 report, W11 specification, live-evidence register, decision register,
schemas, runtime, projections, and vault state are unchanged by this erratum. R5 remains
historical review evidence for subject `892d1d1650cdcf71d2a886318e174a18e11d5de0`.
R6 remains the independent review of the later normative clarification at subject
`c21b366caa751265e455435f23d1232f0bb6220c`.

This erratum does not accept W11, merge PR #121, authorize implementation, approve an
ownership-transition batch, close either D-G6-4 limb, or perform any admission,
transition, cutover, result, eligibility, or claim action.

## 5. Erratum action boundary

Creating this file is the sole change in this correction step. No earlier evidence was
rewritten, and no PR comment, thread resolution, CodeRabbit trigger, merge, acceptance,
schema/runtime mutation, admission, transition, cutover, result, eligibility, or claim
action was performed.
