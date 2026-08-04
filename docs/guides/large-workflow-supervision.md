# Large-Workflow Supervision Examples

**Status:** Active examples; the canonical procedure is
`.agents/skills/tda-large-workflow-supervision/SKILL.md`.
**Workflow system:** Standalone TDL supervision; not APM.

This guide illustrates the canonical skill. It does not add requirements. In
particular, estimated token ceilings, fixed skill counts, and producer-reported
efficiency fields are not valid evidence that a workflow saves tokens.

## Certification Example

Reconstruct the campaign once, verify exact Git and owner state, and write a
compact identity-based packet that points to authorities. A later delivery task
reads the packet and only the authorities needed for its vertical action. The
packet carries the end-to-end capability state; certifying the packet is not
capability completion.

## Independent Review Example

During construction, use direct tests and proportionate review. Once the real
end-to-end path forms an integrated candidate, give the independent reviewer the
exact subject, review remit, evidence paths, deliverable, and hard stops with no
parent conversation history. Fresh context protects independence; it is not
presumed to save tokens.

## Implementation Continuation Example

For a new or independence-sensitive subject, start fresh. For direct work on
the same subject, use a bounded continuation when that avoids replaying the
same evidence. Record the reason for the choice rather than applying one mode
to every implementer. A missing producer or recovery path required by the named
capability stays in the campaign; it is not converted into an unowned successor
because the preceding slice passed.

## Multi-PR Capability Example

If review capacity requires three PRs, record their dependency order and
integration seams, but keep one capability status across all three. Each merge
is a milestone. Claim `INTEGRATED` only after the assembled production path is
exercised through the real seam.

## Actual-Compaction Example

When actual compaction makes the current task an unreliable continuation
surface, emit a compact exact-state handoff and continue elsewhere. Do not use
an estimated live-token threshold as the trigger.

## Token Measurement Example

Evaluate efficiency outside the producing task. Join stable task/session IDs to
session JSONL and `ccusage codex session` output, then compare input, cached
input, output, duration, replayed evidence, and completed useful work. Do not
ask every producer to estimate or narrate these metrics in its handoff.

## Delivery Constraints

Research-value staging, exact-subject preservation, final acceptance-remediation
stops, and external-review capacity remain delivery controls. They bound how the
capability is delivered; they do not redefine a slice or PR as the completed
capability and should not be described as token savings unless separate
telemetry demonstrates that effect.
