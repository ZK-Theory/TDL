# Proposal: collision-resistant observation-log IDs

**Status:** PROPOSAL — awaiting Stephen's approval (research-observer protocol change; not self-applied)
**Date:** 2026-07-21 · **Source:** weekly system review, skill-observation 69
**Owner decision required:** yes (changes the meta-skill's own numbering rule)

## Problem

The observation log (`~/.claude/skill-observations/log.md`) numbers entries by
"read `max(N)`, append `max+1`". Under **parallel sessions** this races: two
sessions both read the same max and both write `N+1`. The log currently contains
**duplicate numbers 58, 59, and 85** — the collision has already happened
(obs 69), and the max+1 rule cannot prevent it because the read and the write
are not atomic across sessions.

This is a shared-mutable-state hazard: the "unique ID" is derived from a
full-file read that another writer can invalidate before the append lands.

## Proposed schemes (owner picks)

**Option A — ULID IDs (recommended).**
Replace the integer counter with a **ULID** minted locally without reading the
whole file. One canonical format is specified so independent writers agree:

- **Format:** [ULID](https://github.com/ulid/spec) — a 26-char Crockford-base32
  string, `<48-bit ms timestamp><80-bit randomness>`, e.g.
  `01J8Z9K3QX7M2AB4CD5EF6GH7J` (rendered uppercase, no separators).
- **Precision / ordering:** millisecond-resolution timestamp in the high bits →
  IDs are lexicographically sortable and monotonic across sessions at ms
  granularity; same-millisecond entries order by their random low bits (i.e.
  arrival order within a ms is not preserved — acceptable for an observation log).
- **Entropy / uniqueness:** 80 bits of randomness per ID. This is
  **collision-resistant, not collision-free** — the probability of a collision
  is negligible (birthday bound ≈ 1 in 10²⁴ per millisecond even at thousands of
  IDs/ms), which is the actual guarantee. A bare second- or ms-resolution
  timestamp *without* the random component is explicitly **rejected**: two
  parallel writers in the same tick would collide, reproducing today's failure.
- **Validation:** new IDs must match `^[0-9A-HJKMNP-TV-Z]{26}$` (Crockford base32,
  excluding I/L/O/U); a helper/regex check rejects malformed IDs at write time.
- **Compatibility:** existing integer observations stay as-is (historical); new
  ones use ULIDs. Sorting mixes the two by writing integers as a distinct,
  earlier-sorting class (or by treating the migration date as the boundary).

**Option B — atomic append helper.**
A small `log_observation` helper that takes a file lock, reads max, writes
`max+1`, releases — serializing the read-modify-write. Keeps integer IDs but
requires every writer to go through the helper (instruction-form discipline,
which the project's own record says fails when it is the only countermeasure).

**Option C — per-session ID prefix.**
Each session mints `<session-short-id>-<local-seq>`, so two sessions never share
a namespace. Unique **only if** two guarantees hold, which must be stated as
part of choosing C: (1) the `session-short-id` is itself globally unique across
concurrent sessions (a truncated random/session UUID with enough entropy that two
live sessions do not collide — a short hash of a human label is not sufficient);
and (2) `local-seq` is incremented collision-safely **within** a session (a
single-writer counter, so no intra-session race). Readable, but ordering across
sessions is not chronological unless the prefix also encodes a timestamp.

Recommended: **A** — it removes the shared-max dependency entirely (no
cross-session read), which is the root cause; B still relies on every writer
cooperating.

## Changes required

- Update the numbering rule in the `research-observer` skill (`SKILL.md` in
  `~/.claude/skills/` and the authoring source if one exists) and its
  `task-observer` predecessor's shared text.
- Optionally annotate the existing duplicate 58/59/85 entries (e.g. suffix
  `-b`) so references stay unambiguous; do not renumber history destructively.

## Owner decision points

- Which scheme (A / B / C)?
- Renumber/annotate the existing duplicates, or leave them with a note?
- The log is global (`~/.claude`), not repo-scoped — confirm the change should
  live in the global skill, and whether a copy of the rule belongs in the repo
  for discoverability.
