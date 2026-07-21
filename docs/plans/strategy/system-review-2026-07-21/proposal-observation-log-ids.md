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

**Option A — timestamp / ULID IDs (recommended).**
Replace the integer counter with a sortable, collision-free ID minted locally
without reading the whole file: `2026-07-21T14-03-09Z` or a ULID. Observations
stay chronologically sortable; two parallel sessions cannot collide because the
ID encodes wall-clock + entropy, not a global max. Existing integer observations
stay as-is (historical); new ones use the new scheme.

**Option B — atomic append helper.**
A small `log_observation` helper that takes a file lock, reads max, writes
`max+1`, releases — serializing the read-modify-write. Keeps integer IDs but
requires every writer to go through the helper (instruction-form discipline,
which the project's own record says fails when it is the only countermeasure).

**Option C — per-session ID prefix.**
Each session mints `<session-short-id>-<local-seq>`, so two sessions never share
a namespace. Unique by construction; slightly less readable.

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
