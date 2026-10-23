# 06v confirmation: the W9 implementation plan, revision 3, at `943c446e`

**Date:** 2026-10-23
**Reviewer:** the session that reviewed revisions 1 (`b3fe778c`) and 2 (`d7f149ff`); distinct from the 06v author
**Subject:** `implementation/06v-w9-implementation-plan.md`, revision 3, commit `943c446e`, blob
`953280d1328284cececd25b14a3ccbe6c176f4bc`; reconciliation §5 in the same commit
**Scope:** as the re-review's §6 proposed:
- the WP9.2 guard text and W9-T20;
- the WP9.7 and §2.7 guard text;
- U-7, D-4, D-7 and O-32;
- the new D-9, U-8 and U-9;
- the author's two verification changes.

**Method:** `git diff d7f149ff 943c446e`; every cited range was re-read at origin/main `e82f9630`:
- `research_system/store/identity.py:333,355,600-651,818-829,857-875`;
- `research_system/artefacts/runtime.py:25-55`;
- `research_system/discovery/spec.py:343-353`;
- `research_system/discovery/spec_assay.py:1130-1136`.

I also grepped every `"root_id": "` literal in `research_system/` and `tools/`, and every `read(self, *, root_id`
implementation. No other file was edited. No store, `ars`, Jira or GitHub write was made.

**Verdict: PASS WITH FINDINGS.** 0 Blocking, 0 Major, 1 Minor, 3 Info. N-1, N-2 and n-1 to n-5 are closed. The one
Minor (c-1) is a one-sentence fix to who writes O-32's change list. It does not need another review round; the
author can fold it in before Stephen's acceptance.

## The author's two verification changes

- **(1) N-2 and the 1.0.0 manifest form: confirmed.** `_validate_manifest_identity` (`identity.py:607-634`) checks
  only the form of a `1.0.0` identity (64 hex characters). For `1.1.0` it requires `store_identity` to equal
  `sha256` over `schema_id`, `schema_version`, `store_nonce`, `project_id` and `bootstrap_manifest_sha256`
  (`:623-633`). `initialize_control_store` still writes the 1.0.0 form (`:818-829`). A fixture can therefore carry the
  frozen Gate 6 identity only as a 1.0.0 manifest, as revision 3 says. My N-2 prescription missed this
  version-dependent check.
- **(2) N-1 and the control-only reader: confirmed.** The one content-reader implementation,
  `ControlRootArtefactContentReader.read`, refuses any `root_id` other than `"control"`
  (`artefacts/runtime.py:38-40`); `use_resolver.py:53` is its interface. Every artefact producer in the code
  registers with `root_id: "control"` (`cli.py:1847`, `discovery/spec_assay.py:1382`, `discovery/spec_result.py:410`,
  `discovery/spec_source.py:353`). Registering and reading successor results in the repository's `results/ars/` is
  genuinely unsettled, so U-8 is the right home for it. Rule (e) refuses no existing producer.
- **Also confirmed:** my re-review's n-1 cited `spec_assay.py:84` as a consumer. That line is the import; the
  consumer is `:1133`, as revision 3 cites.

## One line per finding

| Finding | Status |
|---|---|
| N-1 RegisterArtefact guard | **Closed.** It resolves the root, normalizes the path, applies rules (a) to (e), and has the negative controls including the must-not-fire case. "Null caches" go through rule (c). The `control` and `repo` tokens are the binding's two roots, as Discovery builds them (`spec.py:349`). |
| N-2 W9-T20 copy case | **Closed.** The unbound read and identity refusal come before the control-root check (`identity.py:867-868`), so both the original-path and copy cases fail on the W9 reason code, and a third case passes the guard. The fixture is built through `build_store_origin_witness` and `persist_store_origin_witness` (`:333,355`) in the 1.0.0 form, without patching. |
| n-1 U-7 | **Closed.** Three named sites; a new `legacy` partition value, with reuse forbidden; one `continue` in `driver.py:379-408`; a consumer test at `runtime.py:2214,2254`, `spec.py:284` and `spec_assay.py:1133`; the §8 stop rule matches. |
| n-2 D-4 | **Closed.** It re-accepts the bytes in the merge-queue entry, re-looks after any rebase, includes the T2 expectations and seal, and merges command-adding packages one at a time. |
| n-3 D-7 / L-0b | **Closed.** The segmentation contract is accepted together with the export, so L-0b waits for no code package. |
| n-4 O-34 | **Closed** as an open interface: a §2.7 row and U-9. |
| n-5 detector rule 3 | **Closed in substance**, but the writer of the change list is unworkable as stated (c-1). |
| D-9 | **Agree** with the decision as framed: Stephen fixes the exact list, and the reach over all producers is explicit. See I-a on the exemption sentence. |
| U-8 | **Agree.** It is real (see (2) above) and correctly blocks the WP9.7 guard. |
| U-9 | **Agree.** |

## Remaining

- **c-1 (Minor). The post-merge detector cannot append to a committed list on `main`.** O-32 and WP9.5 rule 3 say
  the detector "appends an entry to a committed list" for every shared-surface change. The detector runs after the
  merge, on push to `main`. Ruleset 20822054 requires a pull request and the merge queue and forbids non-fast-forward
  updates on `main`; its only bypass is `RepositoryRole` 5 in `pull_request` mode (W9:195). A workflow therefore
  cannot commit the entry to `main`.

  **Fix:** the PR that changes a shared surface carries its own change-list entry, naming the contract and its old
  and new blobs. The detector fails when a merged change has no entry, or has no W9 §4.3 owner note. WP9.3 reads the
  list unchanged.
- **I-a (Info).** D-9's "explicit, owner-recorded exemption naming the file" has no input that the guard reads. As
  written, an exemption would in practice be a reviewed code change to the suffix list or a new rule. Either say so,
  or name the record the guard consults.
- **I-b (Info).** The author's verification caught two errors in my prescriptions: N-2's missed version check, and
  n-1's import-line citation. That is the reviewer-prescription failure mode, logged in observation
  2026-10-22-reviewer-prescribed-identifiers-copied-unverified. The reconciliation's re-reading is what caught both.
- **I-c (Info). Known limit, not a finding.** The author and reviewer run on one model family, and the same
  reviewer did all three rounds (P-058).
