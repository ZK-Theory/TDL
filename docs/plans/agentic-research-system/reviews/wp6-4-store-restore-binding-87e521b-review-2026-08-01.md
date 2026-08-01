# WP6.4 restored-store binding third-remediation exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 1 Critical, 1 Major, 0 Minor.

This is a fresh, independent, read-only review of the exact corrective
subject. It is not owner acceptance, PR or merge evidence, A8 closure, Gate 6
acceptance, or authorization to dispatch research.

## Exact review identity

- Producer task: `019fbebd-62fb-7001-bf21-8d6c7bf5cec2`
- Independent reviewer task: `019fbee3-24b6-7683-aa09-2f2adc256132`
- Subject: `87e521beee53e76fb522eeb1ba61b4173337dd54`
- Parent: `37fd36cda2ba08bad0412b64da00904b6fdef6c8`
- Tree: `cc426a194d305bb3ef107701e8d2cfd56cd1d46a`
- Producer remote: `origin/codex/wp64-store-restore-binding-r4`
- Exact corrective delta: 5 paths
  - `research_system/cli.py`
  - `research_system/config.py`
  - `research_system/operations/backups.py`
  - `research_system/store/identity.py`
  - `tests/research_system/integration/test_external_assurance_record_cli.py`

The reviewer confirmed the exact subject, parent, tree, remote equality,
five-path boundary, and clean tracked and untracked review state. The project
hook had rewritten the producer's commit subject to `[EXPLORE] PXX:`; that
message defect was recorded without amending or treating it as semantic
evidence.

## Executive disposition

The subject closes the three specifically targeted test gaps: approved-binding
load no longer creates an absent root, the output is revalidated after the
`output-published` journal mark, and process-exit/restart controls now cover the
output, evidence, and journal-clear boundaries.

It does not close the transaction. Output replacement immediately after the
new validator can make the command raise while leaving a rebound manifest,
durable success-claiming evidence, and no recovery journal. The approved
foundation loader also accepts a manifest-valid store after a required store
directory is removed.

The subject remains quarantined. It is a clean rejected handoff point and must
not be integrated. Any later correction is a new exact subject requiring fresh
independent review.

## C-01 - post-validation output replacement leaves success state after failure

At `research_system/cli.py:485-490,512-530`, the output validator runs before
manifest and evidence publication. At
`research_system/store/identity.py:944-964,980-981`, the journal is cleared
before the caller's final output check.

The reviewer replaced the output immediately after the final validator
returned. The command correctly raised `ArsError` when it later observed the
foreign bytes, but by then the target manifest was rebound, durable evidence
claimed `bound-and-config-published`, the journal was absent, and the foreign
output remained. A failed operation therefore leaves durable state claiming
success with no remaining recovery authority.

A later correction must keep this interval inside a recoverable transaction:
no fallible output check may occur after the journal is irreversibly cleared,
and no failure may leave a rebound manifest or accepted evidence for foreign
configuration bytes.

## M-01 - manifest-valid partial stores pass approved foundation loading

`ApprovedProjectBinding.load` at `research_system/config.py:127-148` checks the
root/schema directories and manifest identity, but not the complete set of
required store directories defined at `research_system/store/layout.py:7-14`.

The reviewer removed the approved source store's `objects` directory while
preserving its valid `store-identity.json`. The approved foundation loader
returned success. The later full CLI preflight rejected the fixture, but the
foundation authority had already accepted a physically incomplete store.

The loader must validate the existing store layout read-only and fail before
returning an approved binding. The negative must compare the complete
filesystem state and prove that validation neither creates nor repairs the
partial root.

## Preserved closures and validation

The fresh reviewer independently established:

```text
Exact new controls: 7 passed
Additional bounded restore-focused controls: 11 passed
Focused Ruff and git diff --check: passed
Protected contract/schema/config/06/06g bytes: zero delta
Tracked and untracked review state: clean
```

The seven exact controls comprise two read-only foundation negatives, two
output-substitution negatives, and three process-exit recovery cases. Their
success establishes those exact sequences but does not cover either later
attack above.

No provider, credential, transport, live research, fabricated record or grant,
or production-foundation mutation was used. The real current owner operational
bundle remains intentionally absent. It is a later legitimate owner dependency
and was neither fabricated nor treated as the cause of these mechanical
findings.
