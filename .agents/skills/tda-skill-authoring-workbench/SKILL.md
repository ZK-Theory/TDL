---
name: tda-skill-authoring-workbench
description: Use when creating, reviewing, or refactoring TDL agent skills — deciding whether something should be a skill, reducing overlap between skills, or working the dual-tree authoring-and-sync mechanics for Claude Code and Codex.
---

# TDA Skill Authoring Workbench

The TDL-specific procedure for adding or changing skills. It exists because
the repo keeps skills in a **dual-tree layout**: the `.agents` tree is the
authoring source of truth for both runtimes, byte-mirrored into the `.claude`
tree by `tools/sync_agent_skills.py` (pre-commit Gate 0). Do not use this
skill to execute the task a skill describes — only to author the skill.

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## Dual-Tree Mechanics (non-negotiable)

1. **Author in the `.agents` tree.** Never edit the `.claude` mirror — an
   edit applied to the mirror is overwritten (or worse, reverses a fix) at
   the next sync. Fixes to existing skills also land on the authoring side.
2. **Register every new skill in `SYNC_SKILLS`** in
   `tools/sync_agent_skills.py` in the same change — classification is
   fail-safe, and an unregistered skill hard-errors every sync run.
   Runtime-specific skills go to `EXCLUDE_PATTERNS` with a comment instead.
3. **Run the sync tool**, then its `--check` mode; both trees must be
   byte-identical before commit.
4. Skill bodies must not contain tree-specific path literals (the sync tool
   lints for them) — cross-reference other skills by name only.

## Required Decisions (before writing)

- Is this skill user-invoked (an orchestrating command) or model-invoked
  (discipline the agent reaches for by description match)?
- Is it core (tier 1), specialist (tier 2), or optional (tier 3)? Tier 2
  carries the TDL integration rule; tier 3 carries the Tier 3 constraint.
- Does it touch an assurance lane? Then it must route to, not duplicate,
  the lane skills.
- Does it duplicate or overlap an existing skill? Resolve by boundary
  statement in both directions, or don't write it.
- Does it need an output schema? (Specialist skills without one degrade
  into prose advice.)
- Does it need self-test prompts?
- Does it need runtime-specific wording? (Then it may not be mirrorable —
  consider exclusion.)

## House Style

Frontmatter `name` + `description`; description is **trigger-only, third
person, starts with "Use when"** — never a workflow summary (agents follow a
summarized description instead of reading the skill). Body: boundary-setting
intro, procedure, TDL guardrails with the *why* (dated locks, incidents),
completion checklist or output record, "Escalate Or Stop When",
"Related Skills". Compact — 60–120 lines; one excellent example beats three
mediocre ones.

## Self-Test Prompts

- *A fix for an existing skill is about to be applied to the mirror-tree
  copy.* → Expected: stop — apply it to the authoring tree and run the sync;
  a mirror edit is overwritten (or reverses a newer fix) at the next sync.
- *A new skill is authored but the sync manifest is untouched.* → Expected:
  register it in `SYNC_SKILLS` (or exclude it with a comment) in the same
  change — an unregistered skill hard-errors every subsequent sync run.
- *A proposed description reads "runs X, then Y, then Z".* → Expected:
  rewrite as trigger-only — a workflow-summarizing description causes agents
  to follow the description instead of reading the skill body.

## Completion Checklist

- [ ] Clear trigger and non-trigger (boundary vs neighbouring skills).
- [ ] Tier classified; the matching clause included (tier 2/3).
- [ ] Assurance-lane routing checked (no duplication of lane audits).
- [ ] Output record or schema where the skill produces artifacts.
- [ ] Self-test prompts for behaviour-shaping skills.
- [ ] No tree-specific path literals in the body.
- [ ] Registered in the sync manifest; sync run; `--check` green.
- [ ] Cross-links added in both directions where skills reference each other.

## Escalate Or Stop When

- The new skill would restate a locked convention differently — reference
  `CONVENTIONS.md`; never paraphrase a lock.
- Two existing skills already split the territory — propose a merge or a
  boundary fix as a User decision instead of adding a third.

## Related Skills

`tda-light-task-triage` (is this worth a skill?) · `adversarial-design-review`
(reviewing a skill suite as a design artifact) · the task-observer log
(observations tagged to a skill feed its next revision).
