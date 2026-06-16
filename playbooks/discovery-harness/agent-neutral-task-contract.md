# Discovery Harness Agent-neutral Task Contract

This is the portable task shape for a non-Claude worker to read from the APM bus,
execute, and report back without needing a slash-command skill wrapper.

## Bus Files

- Task input: `.apm/bus/<agent-slug>/task.md`
- Report output: `.apm/bus/<agent-slug>/report.md`

The worker reads the task, executes only the bounded objective, then writes the
report. The Manager or user delivers the report with `/apm-5-check-reports
<agent-slug>`.

## Task Frontmatter

```yaml
schema_version: discovery-agent-task/v1
task_id: discovery-strand-spike-001
agent: codex-worker
objective: Run the bounded Discovery Harness task described below.
inputs:
  - vault/00-Meta/Discovery/strand-persistence-survival-testing.md
  - playbooks/discovery-harness/spike.md
outputs:
  - vault/00-Meta/Discovery/strand-persistence-survival-testing-spike-result.md
acceptance_criteria:
  - The output exists at the declared path.
  - The validator named in the playbook passes.
research_assurance:
  lanes:
    - topology
    - null-model
    - provenance
  governing_artifacts:
    - contracts/discovery-harness/spike-pre-registration.yaml
report_contract:
  must_include:
    - Summary
    - Files changed or written
    - Validation commands and results
    - Research assurance evidence
    - Open risks or blockers
```

## Body Template

```markdown
# Discovery Agent Task

## Objective

One bounded objective. Do not infer broader scope.

## Inputs

List every file, URL, or vault note the worker may rely on.

## Procedure

Name the plain Markdown playbook to follow. If multiple playbooks apply, list
the order.

## Outputs

List exact paths to write. Do not write outside these paths without reporting a
blocker.

## Acceptance Criteria

Bullet list of evidence that proves completion.

## Reporting

Write `.apm/bus/<agent-slug>/report.md` using the report_contract fields.
```

## Report Template

```markdown
# Discovery Agent Report

## Summary

What was done and the verdict.

## Files Changed Or Written

Exact paths.

## Validation Commands And Results

Commands run and pass/fail result.

## Research Assurance Evidence

Lane-by-lane evidence for topology, null model, representation, output, and
paper-claim risks touched by the task.

## Open Risks Or Blockers

Anything the Manager/user must decide.
```
