# WP6.4 restore-admission exact-subject review - `0368b697`

**Date:** 2026-08-03
**Pull request:** #208
**Verdict:** `accept_exact_subject` (`Critical 0`, `Major 0`, `Minor 0`)

## Exact subject

- Candidate: `0368b69712d915f34722c5f1eded406ed77d6a17`
- Tree: `84353ff8ca24d843851f8825055cbde055395d3d`
- Parent: `406eaa996e7a22f71ab2e58c1df13b98dee9b027`
- Base and merge base: `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e`
- Branch: `codex/wp64-origin-witness-r11`
- Full candidate delta from base: 30 paths, 7,706 insertions, 674 deletions

At the decision point, local `HEAD`, configured upstream, the live remote
branch, and PR #208 head all resolved to the candidate. The base is its merge
base and ancestor. `git diff --check` passed.

## Prior-finding disposition

Both reliability findings against the parent are closed.

1. A non-appending ordinary outcome retains the pending restore result and
   rechecker. Only a successful `EventLedger.append` retires those two fields,
   for both ordinary and T2 submissions. The approved source, witness, and
   witness path remain durable service state and are revalidated on every later
   submission.
2. The single pre-lock preparation now carries an immutable checked-input
   closure for the exact snapshot, endpoint-ownership record, artefact manifest,
   bound artefact paths and digests, and complete registry dataclass state. The
   closure is re-read and exact-compared after acquisition of the target
   composite writer lock and before command mutation. This bounded recheck does
   not invoke the external preparation callback or replay the ledger a second
   time.

Direct exact-head probes confirmed:

- an initial stream-version conflict retained pending preparation; subsequent
  witness drift raised `IntegrityError` with no receipt or append; and
- while a competing writer held the exact target `runtime/writer.lock`, changing
  the bound artefact after preparation caused `IntegrityError: restore artefact
  changed after full preflight`; the ledger remained at position 2 and the
  preparation callback ran once.

## Validation and protected surfaces

The proportional shared-restore, ordinary/T2, recovery, origin-witness,
foundation-contract, and P-045 set passed: `106 passed in 286.43s`.

Relative to the base, the following protected identities are unchanged:

- `.research-system/schemas` tree `087dc165b6ca2b09ce41a53965f70ff485bc1e12`;
- `.research-system/contracts` tree `4138918ab422eec604e8f3251c8846c8227870b4`;
- `contracts` tree `49dfb3bf5e698d6f815e9a475ee54153ff49fd9c`;
- P-045 event-schema blob `bc3efc0fd41e3d9f24c383f2d0d196e26ba0d1e5`;
- P-045 decision blob `552183b39e70cf4b105346bdd7f747496a792e85`; and
- P-045 compatibility-test blob `2c411618f260393501e3b07b7c285ad01cd42d57`.

The pre-existing `.claude/CLAUDE.md` and `.repowise-workspace.yaml` setup
modifications were neither changed nor staged.

## Boundary

This record accepts only the exact candidate above. It does not merge PR #208,
update an external service, materialize owner/foundation authority, or authorize
research execution. Any later substantive commit requires focused re-review.
