# WP6.4 Origin Witness Review — 031af78d

## Decision

- Semantic subject: `031af78d97d30258fc16a6543d6b4719e6b7776d`
- Subject tree: `c2825889d4f1ed5e2616cc75a8f35469fdb07234`
- Parent: `67427402ceb453334ceebdce7bf38dc015fec226`
- Base: `dd67dca5ff69c1aeefb903c63f3437df357280c0`
- Branch: `codex/wp64-origin-witness-r11`
- Scope: 25 paths relative to the base

Fresh independent Luna Max review context was detached and read-only. The exact
subject is **accepted** with `Critical 0`, `Major 0`, and `Minor 0`.

## Evidence

- Identity: the reviewed subject, tree, parent, branch, and 25-path scope match
  the pinned record above.
- Live remote: local `HEAD`, configured upstream, and the live branch ref all
  resolve to `031af78d97d30258fc16a6543d6b4719e6b7776d`.
- Ancestry: `origin/main` is `dd67dca5ff69c1aeefb903c63f3437df357280c0`,
  `merge-base(origin/main, HEAD)` is that same commit, and both the base and
  accepted producer history remain ancestors of the subject.
- Worktree: clean.
- `git diff --check HEAD^ HEAD`: pass.

The independent review validation was 10 passed in 6.99s: eight POSIX cleanup
controls, the S-014 positive control, and the S-014 source-lineage mismatch
control.

## Accepted behavior

POSIX cleanup uses a same-parent private `0700` quarantine and an atomic rename.
The quarantined candidate is classified without following links. No pathname
deletion occurs after the final verification, so verified artifacts remain
available as evidence and foreign or ambiguous objects are preserved without
overwriting concurrent paths. Windows behavior is unchanged. The retained
POSIX quarantine is intentional and requires separately governed cleanup.

The producer's final validation also passed: the final focused cohort was
`24/24`, the POSIX controls were `8/8`, and Ruff, format, diff, and compile
checks passed.

No schema bytes, provider or credential paths, or owner pins were changed or
fabricated.

## Scope boundary and owner act

This decision accepts the code subject only. It does not materialize foundation
owner pins or authorize research execution.

After integration, the later non-delegable owner act is to approve the exact
external witness path and raw SHA-256, then materialize the canonical foundation
fields.
