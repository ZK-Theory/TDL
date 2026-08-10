# WP6.1 06j/W3 G-RM-12 exact-byte owner acceptance

## Decision provenance

Statement provenance: owner-supplied task message.

Recorded date: 2026-08-10.

Acceptance timestamp: not recorded; none is invented.

After receiving the exact independently reviewed decision subject, Stephen
Dorman stated:

> Accept these exact candidate bytes as G-RM-12 and authorize/ratify continued
> use and completion of the unchanged corresponding Stage B materialization and
> runtime subject.

## Accepted identity tuple

- Gate: `G-RM-12`.
- Stage A candidate tree:
  `d2b83f598bbe8d2bfc7a3471f1df23dafa8c6c21`.
- Identity-manifest blob:
  `0148fa379bcc7d7a92fc044f7e74f4180d816654`.
- Identity-manifest raw SHA-256:
  `b82b20c97eec4c7494ea143ec7b1252d9699fb818bb8b5392d076cdb57d3aee5`.
- Identity manifest binds 24 non-manifest leaves by exact path, Git blob and raw
  SHA-256.
- Candidate-to-canonical comparison: 24 of 24 bound leaves byte-identical.
- Canonical context-contract tree:
  `fa427aedfd58c859938f908f4ebafbf90c732163`.
- Reviewed runtime commit:
  `849ab0b3c289c2864072ab0c89fcb4704102ac5f`.
- Reviewed runtime tree:
  `9f33abeb06ee9b76fabe5a8c65bb20c3f9719e7d`.
- Runtime base:
  `4773e90981dce739c1761b9cbd68ad6768085b86`.
- Review record:
  `docs/plans/agentic-research-system/reviews/wp6-1-06j-849ab0b-exact-subject-review-2026-08-10.md`.
- Independent verdict: `accept_exact_subject`; no actionable finding.
- PR at acceptance: `stephendor/TDL#240`.
- Branch at acceptance: `codex/wp6-1-06j-w3-context-packet`.

The exact leaf manifest is the accepted `identity-manifest.yaml` blob above. It
is the authority for every accepted candidate path, Git blob and raw SHA-256;
this decision does not accept a mutable branch name, regenerated equivalent
content or later changed bytes.

## Effect

This explicit decision closes G-RM-12 for the exact accepted Stage A bytes and
ratifies continued use and completion of their unchanged Stage B materialization
and reviewed runtime subject. Recording this decision after the reviewed subject
does not rewrite or replace the accepted bytes. The accepted runtime commit must
remain a reachable ancestor of any integration commit.

## Boundary

This decision does not satisfy G-RM-13 or RM-03 acceptance; authorize provider
transport, credentials or external execution; authorize mutation of the accepted
candidate bytes; close R1/KAN-102 or KAN-75; promote a result or claim; or close
Gate 6. CodeRabbit and final merge mechanics remain owner-controlled. Any later
candidate or runtime behavior change requires a fresh exact-subject review and,
where accepted candidate bytes change, a new owner decision.
