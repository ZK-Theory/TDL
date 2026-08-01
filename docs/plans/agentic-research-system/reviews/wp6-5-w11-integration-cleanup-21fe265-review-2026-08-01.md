# WP6.5 W11 integration cleanup exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent exact-subject semantic review; read-only except this record
- Review CWD: `C:\Users\steph\.codex\worktrees\26d0\TDL`
- Reviewed candidate: `21fe265736834263e9c3094c89fc6a390670be7b`
- Expected parent: `98447202951ea4643435b223f3099b02376d4367`
- Expected tree: `6c6f8619dba09c7a371dad0e63155e1f83ea616b`
- Review branch: `codex/review-kan58-w11-integration-cleanup-21fe265`
- Producer remote: `origin/codex/kan58-w11-integration-cleanup-r4`
- Verdict: `accept_exact_subject`
- Findings: 0 Critical, 0 Major, 0 Minor

## Executive disposition

The exact candidate closes the three current CodeRabbit test findings recorded
against live PR #204 at the accepted parent, and independently closes the two
older semantic seams under review. The five cooperating `physicalIdentity`
definitions are exactly equal to the canonical eight-field shape. The rubric
verifier controls every field consumed after the reference callback, including
allowed-set, bounds, and required-axis shapes, with malformed inputs producing
controlled `SchemaError` outcomes.

The Git hardening is bounded and preserves production semantics: Git is resolved
to an absolute executable once, both subprocess calls remain argv-only with
`shell=False`, validated SHA values cannot become options or subcommands, and
missing Git produces the controlled materialization error. No schema, runtime,
catalogue, acceptance, producer, reducer, projection, CLI, migration, or
cutover change is present.

This verdict accepts only the exact candidate SHA. It does not merge PR #204,
authorize a later head, or replace owner/Gate 6 acceptance.

## Exact identity and scope

The review worktree was initially detached at the exact candidate and the
pre-created review branch resolved to the same SHA. The one deterministic switch
to that branch succeeded. After the routing update, the worktree was rechecked
without another switch and remained symbolically attached to the required
review branch at the exact candidate with clean status.

The candidate has the expected parent, tree, ancestry, and producer-remote
equality. Its exact delta from the accepted parent is only:

- `tools/verify_w11_materialization.py`
- `tests/research_system/contracts/test_w11_contract_materialization.py`

The foundation range from `c84eb2aaf0890d36d3735d08a14169f4c50935cd` to the
candidate contains exactly 65 paths. No unrelated working-tree changes were
present before this record was written.

## Findings and dispositions

There are no Critical, Major, or Minor findings.

### Current CodeRabbit test findings

The live PR #204 review at parent `98447202951ea4643435b223f3099b02376d4367`
contains three test-only findings. Each is closed by the candidate without
changing production semantics:

1. The independent `_test_canonical_bytes` helper now passes
   `allow_nan=False` at `tests/research_system/contracts/test_w11_contract_materialization.py:295-302`.
   This preserves independence from production `canonical_bytes` while making
   non-finite fixture hashing fail closed.
2. `test_spike_verdict_requires_evidence_and_an_applicable_predicate` now creates
   one format-checking validator and reuses it for every assertion at
   `tests/research_system/contracts/test_w11_contract_materialization.py:767-786`.
3. `_test_expected_set_closure_hash` is the shared helper at
   `tests/research_system/contracts/test_w11_contract_materialization.py:313-327`,
   and both the valid fixture and coordinated-duplicate test call it at
   `:668` and `:1390`; the repeated closure formula is removed.

### Physical-identity compatibility thread

The old incompatibility finding is stale. The independent test at
`tests/research_system/contracts/test_w11_contract_materialization.py:827-862`
checks all five cooperating W11 schemas, requires the same `$ref`, and compares
the complete `$defs.physicalIdentity` object against an independently declared
eight-field expected shape. The direct JSON comparison also passed for:

- `path-registration-content`
- `legacy-portfolio-path-observation`
- `legacy-record-observed`
- `legacy-source-inventory-content`
- `legacy-cutover-closure-content`

The shape requires `canonical_target`, `reparse_chain`,
`volume_serial_number`, `stable_file_id`, `link_count`, `case_aliases`,
`unicode_aliases`, and `short_name_aliases`, with closed additional properties.

### Malformed-rubric downstream closure

The old malformed-rubric finding is stale. After the callback boundary, the
verifier explicitly controls:

- rubric presence, identity, revision, and ambiguity;
- `axis_definitions` container and every axis mapping;
- axis identity, uniqueness, kind, and value type;
- exactly one non-empty domain, with JSON-list `allowed_set` values checked
  against the declared kind;
- numeric `bounds` shape, finite endpoint types, and ordering;
- non-empty, unique, non-blank `required_axis_ids` and their resolution; and
- every scorecard axis identity, kind, value, duplicate, and complete axis set.

Direct current-code evidence is at
`tools/verify_w11_materialization.py:423-525` and `:528-591`. The focused
negative matrix covers null, integer, tuple, set, empty, mixed, and missing
`allowed_set` domains; malformed and empty/duplicate `required_axis_ids`; and
string, boolean, non-finite, inverted, and incomplete bounds at
`tests/research_system/contracts/test_w11_contract_materialization.py:1213-1345`.
All invalid cases returned controlled `SchemaError` results, including the
no-op callback route, and unrelated callback failures remain unmasked.

### Git identity and subprocess boundary

The candidate resolves Git once with `shutil.which("git")` and
`Path(...).resolve()` at `tools/verify_w11_materialization.py:35-37`.
`_git_executable` fails with `MaterializationVerificationError` when resolution
is absent at `:612-615`. The two and only two subprocess calls are the ancestry
call at `:622-632` and identity call at `:645-655`; both use lists, an absolute
executable, fixed Git subcommands, `shell=False`, and the repository `cwd`.
The B404 import suppression and the two B603 suppressions are line-scoped and
accurately justify these required argv-only calls; no shell invocation is hidden.

Envelope SHA values pass `_require_sha1` before any Git call at
`:195-197`, `:618-620`, and `:606-609`. Repository-relative paths are checked
at `:214-220` before path identity is queried. The remaining Git arguments are
fixed subcommands or values derived from validated SHAs and validated repository
paths; no envelope value is passed as a standalone option or subcommand.

An independent runtime probe changed `PATH` after import, captured both argv and
keyword arguments, attempted an option-like SHA, and set the resolved executable
to missing. It confirmed absolute executable/cwd binding, `shell=False`, no
subprocess call for the malformed SHA, and the controlled missing-Git error.

## Consistency matrix

| Invariant | Enforcement | Evidence | Disposition |
|---|---|---|---|
| Exact subject identity and two-path delta | Git parent/tree/ancestry/remote and diff checks | Exact SHA/tree/parent; 2 paths | Keep |
| Five-schema physical identity interoperability | Independent expected-shape equality and `$ref` checks | 5-schema test and direct JSON comparison | Keep; old thread stale |
| Rubric downstream shape closure | Verifier guards plus no-op/custom callback negatives | 33 targeted tests/probes | Keep; old thread stale |
| Git executable and envelope safety | Absolute path, SHA/path validation, argv-only `shell=False` calls | Source inspection plus independent probe | Keep |
| W11 remains inert | Runtime binding absence and inactive-registry checks | Focused suite | Keep |
| Protected W11 authority bytes | Explicit commit/blob/raw SHA/byte/LF checks | Focused suite plus direct raw-byte probe | Keep |
| Current CodeRabbit test findings | Three exact test changes | Current test lines and diff | Closed |

## Validation evidence

All validation used `C:\Users\steph\TDL\.venv\Scripts\python.exe` directly,
with bytecode disabled, third-party pytest plugin autoload disabled, pytest
cache provider disabled, and configured coverage addopts overridden.

- Full focused W11 contract suite: `63 passed`.
- Git-envelope, physical-identity, malformed-rubric, raw-identity, and inert
  subset: `33 passed, 30 deselected`.
- Ruff on both changed files: passed.
- `git diff --check`: passed.
- Exact parent-to-candidate delta: 2 paths, exactly the named files.
- Foundation range count: exactly 65 paths.
- Five-schema physical-identity exact equality: passed.
- Protected W11 commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`, blob
  `f90729d0c42a0de98d064fac0824d1969c871c82`, raw SHA-256
  `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`,
  `185214` bytes, and LF-only bytes: passed.
- Final pre-record worktree: exact review branch, candidate `HEAD`, and clean
  status.

## Change log and authority boundary

- Files edited by this review: this named review record only.
- No production or test remediation was performed.
- No schema/runtime/catalogue/acceptance change was made.
- No PR, Jira, merge, or CodeRabbit action was performed.

The review-record commit SHA is intentionally reported separately from the
reviewed candidate SHA in the task handoff.
