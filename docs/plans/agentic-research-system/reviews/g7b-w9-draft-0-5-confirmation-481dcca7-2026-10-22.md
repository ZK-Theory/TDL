# G7-B confirmation: W9 draft 0.5 at `481dcca7`

**Date:** 2026-10-22
**Reviewer:** the independent session that reviewed W9 drafts 0.1 to 0.4; not the author
**Scope:** only `git diff 250408c6 481dcca7 -- <path>` (s-1, s-2 and the passages they touched)

| Identity | Value |
|---|---|
| File | `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md` |
| Commit | `481dcca7` on `claude/gate7-prep-docs-5202cf` |
| Blob | `ea3a8e4a5e89a599c255fd881c2a040db4f2d3c5` (confirmed with `git rev-parse`) |
| origin/main verified against | `3fa437a160ab75c5fa0083fd35176006b1ee19a4` |

**Verdict: PASS.** The diff closes both minors as proposed and introduces nothing new.

- **s-1 (closed).** §13.1 and the §5.2 `legacy-paper-root` row now fix the order. Stephen's recovery Decision comes
  first and names only the predecessor root and the recovery intent, and the recovery root names that Decision and
  its predecessor. W9-T21 rejects a Decision that names its recovery root, so the chain is acyclic.
- **s-2 (closed).** Manual-mode commits must be signed with a key Stephen has registered for the named writer, or
  pushed under a recorded GitHub actor identity. The import verifies that attribution and rejects any commit it
  cannot attribute. W9-T23 is the negative control.

Two cosmetic notes, neither a finding: W9-T23 sits before W9-T22 in the §17 table. §18's `db294c9e` is the commit
of the 0.4 re-check, whose blob `5fba7a7b` equals the bytes I wrote.

Limit: same model family as the author, and the same reviewer for every round (the P-058 known limit).
