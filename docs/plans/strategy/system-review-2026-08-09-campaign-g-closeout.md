# System Review 2026-08-09 - Campaign G Closeout

## Outcome

Observation `110` is ACTIONED. TDL now has a standalone Codex JSONL token-telemetry auditor whose additive source is positive deltas of the monotone cumulative counters. `last_token_usage` is never summed.

## Enforced invariant

- repeated nonzero last-call records with an unchanged cumulative snapshot add zero usage and emit a warning;
- compaction bookkeeping with zero components and a nonzero last total adds zero usage and emits a distinct warning;
- an explicit sequence boundary retains the last pre-boundary cumulative snapshot and counts only child-local deltas, excluding inherited fork history;
- last-call/cumulative-delta disagreement is visible but cannot change the additive result;
- raw cumulative `cache_write_input_tokens` deltas are exposed rather than rewritten to zero;
- malformed JSONL lines are counted and make the CLI fail while valid records remain auditable.

## Simplification sweep

The tool does not reproduce `ccusage`, infer billing cost, or classify model activity. It implements only the disputed additive invariant and emits machine-readable JSON for downstream analysis.

## Validation contract

- 4 focused fixtures passed: repeated-last/compaction, child boundary, mismatch/cache-write, and malformed CLI input;
- a live Codex session audit parsed 110 token records, rejected one repeated-last record from additive usage, and emitted its warning;
- diff hygiene passed;
- the campaign changes 3 files, below the 100-file PR limit.
