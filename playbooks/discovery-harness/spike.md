# Spike Playbook

Use this when no skill wrapper is available and a worker must run a bounded
Discovery Spike after a PROMOTE Assay and explicit user approval.

## Inputs

- `vault/00-Meta/Discovery/_backlog.md`
- Validated Assay note with `assay_scorecard`
- `contracts/discovery-harness/spike-pre-registration.yaml`
- Existing data/result artifacts named by the pre-registration

## Procedure

1. Confirm the backlog entry is `state: assayed` and `decision: PROMOTE`.
2. Confirm explicit user approval for this candidate.
3. Write `vault/00-Meta/Discovery/<slug>-spike-prereg.md` with a fenced
   `spike_preregistration` block.
4. Validate the pre-registration before doing compute.
5. Run only the toy-scale probe named in the pre-registration.
6. Confirm the metric-space object exists, a toy signal or negative result can
   be stated, and the null operation perturbs the actual Spike input.
7. On success, update the backlog to `spiked` and hand the pre-registration to
   `/pre-reg-to-dispatch`; on failure, write a `[NEGATIVE]` note and update the
   backlog with KILL/PARK reasons.

## Outputs

- Spike pre-registration note with `spike_preregistration` block.
- Spike result note or `[NEGATIVE]` note.
- Updated `_backlog.md` entry.

## Validation

Run `validate_spike_preregistration` from
`trajectory_tda.discovery.spike_preregistration` before compute. Any result must
also report topology, null-model, representation, and provenance evidence.
