---
name: apm-4-check-tasks
description: Deliver a Task Prompt to an APM Worker.
user-invocable: true
---

# APM 1.0.1 - Worker Check Tasks Command

Check your Task Bus for pending Task Prompts. If you are a Planner, Manager, or non-APM agent, concisely decline and take no action. This command replaces manual file referencing - you resolve your bus path from your registered identity or from the provided `[agent-id]` argument.

Accepts an optional `[agent-id]` argument. If registered, ignore it (bus path already known). If not registered, the argument is required to resolve identity.

**Procedure:**
1. Determine registration state:
   - If registered, resolve bus path from registration. Continue to step 3.
   - If not registered, `(the text provided by the User after the command invocation, if any)` is required. If no argument provided, inform User that an agent-id is required.

2. Resolve agent-id (unregistered Workers only): resolve `(the text provided by the User after the command invocation, if any)` against `.apm/bus/` directory names per `.agents/skills/apm-communication/SKILL.md` §4.2 Agent ID Resolution. Initialize per `.agents/skills/apm-3-initiate-worker/SKILL.md` §2 Initiation.

3. Read Task Bus at `.apm/bus/<agent-slug>/task.md`.
   - If empty, inform User that no pending Task is available. Await next invocation.
   - If content present, continue to step 4.

4. Cross-validate `agent` field in YAML frontmatter against registered identity. Mismatch flags a routing error - decline and direct User to the correct Worker. Process the Task per `.codex/apm-guides/task-execution.md` §3 Task Execution Procedure.

---

**End of Command**
