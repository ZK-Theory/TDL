---
name: tda-literature-verification
description: Use when a new source, DOI, arXiv ID, or literature lead enters the project — from Perplexity, web search, a reviewer, Scout, or a citation in another paper — before it is cited, added to Zotero, or turned into a literature note.
---

# TDA Literature Verification

**Leads are not sources.** Search outputs — Perplexity included — confabulate
quotations and invent plausible-sounding papers, and are never cited directly.
The locked pipeline is: lead → verify existence → Zotero entry → literature
note → prose. No shortcuts, no orphan notes. Do not use this skill to draft
prose from unverified results; verification comes first.

## Procedure

1. Capture the lead with every identifier it carries (DOI, arXiv ID, URL,
   title + authors + year).
2. Verify existence against an authoritative source: DOI resolution, the
   arXiv listing, the publisher page, or Crossref / OpenAlex / Semantic
   Scholar. The identifier must resolve to the **claimed** paper — matching
   title, authors, year, and venue. A DOI that resolves to a different paper
   is a failed verification, not a near-match.
3. Check full-text availability and note the access route.
4. Create or update the Zotero entry via the available Zotero tooling.
5. Create or update the literature note (`@AuthorYear - Title.md` filename
   pattern) with the metadata block below.
6. Tag paper targets — every source is cross-referenced against the pipeline
   (P01-A, P01-B, P04, FIN-01, P05–P10). Orphan literature notes accumulate
   without this discipline.
7. Record which claim or section the source supports.
8. Quarantine dubious sources as `needs-check` or `rejected` — they never
   reach prose.

## Literature Note Metadata

```markdown
---
citekey:
title:
authors:
year:
venue:
doi:
url:
verified: true
verified_date:
source_type:
paper_targets: [P01-A]
claim_support:
status: usable | background | rejected | needs-check
---
```

## Completion Checklist

- [ ] Source existence verified against an authoritative source.
- [ ] Metadata matched: title, authors, year, venue, DOI.
- [ ] Zotero entry created or updated.
- [ ] Literature note created or updated with the metadata block.
- [ ] Paper target(s) assigned — no orphan notes.
- [ ] Claim relevance stated.
- [ ] No search/Perplexity output cited directly anywhere in prose.

## Dispatching Search Sub-Agents

When delegating a literature scan to a sub-agent, NAME the search tools to
use (WebSearch/WebFetch, the alphaXiv MCP `discover_papers`/`get_paper_content`,
arXiv Atom, OpenAlex) and explicitly name the ones to AVOID for topic-specific
work (a general-science semantic-search gateway will confidently return
off-topic results for a narrow method query — e.g. multiparameter-persistence
hits for a persistent-Laplacians query — and a confident final report can
understate how patchy the underlying retrieval actually was). Require the
agent to record, per novelty/"gap" claim, which backend(s) it actually
searched and whether any returned an on-query result, so "not found" carries
its provenance. A citation that justifies an **exclusion** (KILL / near-miss /
"already done") is more dangerous wrong than one that justifies an inclusion —
a wrong inclusion is caught at the next gate, a wrong exclusion silently
removes an option forever. Verify kill-justifying citations hardest: fetch the
paper and confirm it says what it is claimed to say before treating a roam's
KILL list as anything but provisional.

## Escalate Or Stop When

- Metadata mismatch between the lead and what the identifier resolves to
  (wrong year, different author list) — treat as unverified and quarantine.
- A prose claim needs a source that cannot be verified — flag the claim as
  unsupported; never substitute a near-match.

## Related Skills

`scout-review` (weekly discovery triage, upstream of this skill) · `assay`
(viability scoring of promoted leads) · `tda-peer-review-panel` (review
passes consume verified sources only) · `paper-claim-trace` (binding claims
to evidence) · `tda-document-ingestion` (document conversion upstream of
verification — converted text is not yet a verified source).
