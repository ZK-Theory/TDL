---
name: gh-address-comments-extras
description: Complement github:gh-address-comments for Windows UTF-8 failures and external scanner remediation. Use when thread-fetch scripts decode GitHub JSON under a Windows locale, when check annotations omit scanner rule IDs, or before adding suppressions for Codacy, Semgrep, CodeQL, or similar PR checks.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - implementer
    - operator
  runtime: agnostic
---

# GitHub Address Comments Extras

Use alongside github:gh-address-comments. Treat GitHub API JSON encoding and scanner rule identity as evidence requirements.

## Windows UTF-8 Gate

Before running Python-based thread fetchers on Windows:

1. Force UTF-8 mode for the process, for example by setting PYTHONUTF8=1.
2. Prefer helpers that pass encoding=utf-8 and errors=strict to subprocess text reads.
3. Exercise the fetch path with non-ASCII review text when modifying or validating a helper.
4. Treat locale-decoding failure as incomplete thread inventory; do not fall back to a partial flat-comment view without saying so.

## Scanner Suppression Gate

Before prescribing or adding a suppression:

1. Fetch the current check-run annotations or scanner export and map every finding to current HEAD.
2. Record scanner/tool, exact rule ID, message, path, and line. An annotation message alone is not a rule identity.
3. If the rule ID is absent, resolve it through the scanner API or the upstream rule source using the exact message and tool context.
4. Do not infer an ID from a similarly named rule. If exact metadata remains unavailable, prefer a documented line-scoped suppression only when the scanner supports it and record the uncertainty.
5. Run a fresh remote analysis. Only that rerun proves the suppression matched and the finding closed.

## Pre-Delivery Check

Confirm thread retrieval was complete under explicit UTF-8 decoding and every suppression is backed by exact scanner metadata plus a fresh remote result. Label unresolved metadata or pending reruns explicitly. After a timeout or uncertain response, do not retry blindly: query by the exact head and review identifier, or use an equivalent idempotency mechanism, to determine whether the review already exists; record the confirmed result and ensure only one review is posted.
## Review-finding verification

- Verify a scanner's claimed rule against the effective local configuration and a focused invocation. Preserve a valid style request while correcting an inaccurate enforcement rationale.
- Before optimizing a test, name the defect it proves and retain that falsification power through a deterministic clock or synchronization seam.
- When subprocess use is flagged, prefer a constrained metadata seam with fixed executable/arguments and validated inputs; do not broaden into general command execution.
- Classify a target as current authority or immutable historical evidence before editing. Search for downstream blob/SHA/path pins and use additive superseding records for content-addressed history.
- Treat the review service's latest availability countdown as authoritative. Persist the exact head, wait through the stated window plus margin, confirm no review is active, and post only once.

Before delivery, re-check each accepted fix against the original behavioral claim, effective tool configuration, evidence epoch, and exact reviewed head.
