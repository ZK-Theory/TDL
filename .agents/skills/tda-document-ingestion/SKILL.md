---
name: tda-document-ingestion
description: Use when converting PDFs, DOCX, XLSX, web captures, survey codebooks, appendices, or tables into vault-ready Markdown or structured artifacts for TDL.
---

# TDA Document Ingestion

Convert documents into usable artifacts without laundering them into
"verified sources": **converted text is not automatically a verified source**,
and OCR/table extraction is provisional until checked. Citation verification
is `tda-literature-verification`'s job — this skill feeds it, never bypasses
it.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Procedure

1. Identify the source type: academic paper, survey codebook, official
   report, reviewer attachment, table/appendix, web capture.
2. Decide the parser: simple conversion, layout-aware extraction, table
   extraction, or manual inspection. Prefer the lightest tool that preserves
   what matters.
3. Convert to Markdown or a structured artifact; preserve page/section
   anchors where possible so later citations can point into the source.
4. Flag uncertain OCR regions, equations, and tables explicitly — a silently
   mangled table is worse than no table.
5. Route by type:
   - academic sources → the Zotero / literature-note workflow
     (`tda-literature-verification`);
   - survey documentation and codebooks → the method-documentation notes
     (wave-specific coding claims still go through `bhps-wave-crosswalk`);
   - reviewer attachments → the relevant paper's notes directory.
6. Record limitations of the conversion in the artifact header.
7. Numbers extracted from tables that will be cited or computed on are
   treated as **unverified** until checked against the source rendering.

## Required Output Record

```text
source path/URL · parser used · conversion command · output path ·
layout/table caveats · manual verification needed (y/n + where) ·
Zotero status · literature-note status · claim relevance
```

## Self-Test Prompts

- *A converted PDF paragraph is pasted into a draft with a citation.* →
  Expected: stop — conversion is not verification; the source goes through
  the literature-verification pipeline first.
- *An extracted codebook table will drive a variable recode.* → Expected:
  the table values are checked against the source rendering, and the coding
  claim goes through the wave-crosswalk check.

## Escalate Or Stop When

- The document's provenance/authorship is unclear (an unlabelled PDF, a
  vendor whitepaper posing as documentation) — verify what the document *is*
  before using its content.
- Extraction quality is too poor to trust — say so; do not present a lossy
  conversion as the source.

## Related Skills

`tda-literature-verification` (verification — always downstream of academic
ingestion) · `bhps-wave-crosswalk` (survey coding claims) ·
`tda-external-data-lookup` (structured data retrieval) · `vault-sync`
(filing the artifacts).
