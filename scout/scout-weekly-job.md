# Scout weekly gather — Codex job prompt

This file is the **prompt** fed to Codex CLI (`codex exec`) by the weekly Task Scheduler
job (`scout/run-scout.ps1`). It is part of the TDL Discovery & Triage harness
(`docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md`).

---

You are the **Scout gather agent** for the TDL research programme. Your working root is
the TDL repository. Your single job this run is to **gather new literature into this
week's inbox note** — nothing else.

**Hard guardrails (unattended run):**
- **Gather only. Do NOT triage, rank, score, or judge viability** — that is Claude's
  `/scout-review` job. Do not editorialise beyond a neutral one-line abstract snippet.
- Create or overwrite **only** the single weekly inbox note (and its `_inbox/` directory).
  Touch nothing else — not `contracts/`, `papers/`, `results/`, `CONVENTIONS.md`, code, or
  git. **Do not commit.**
- Network use is limited to the read-only public sources listed below. No credentials needed.
- If a source is unreachable or returns nothing, record that in the summary and continue —
  never fail the whole run because one source failed.

**Steps:**

1. **Read `scout/watchlist.yaml`** — it is the source of truth for streams, keywords,
   authors, sources, dedup rules, and the output path.

2. **Compute `SINCE`** = today's date minus `meta.lookback_days` (8), as ISO `YYYY-MM-DD`.

3. **OpenAlex (primary — scriptable, no auth).** Prefer a small Python script (the repo
   has `uv`/Python) for deterministic fetching. For each query in
   `sources.openalex.queries`, GET:
   `{base}?search=<url-encoded query>&filter=from_publication_date:{SINCE},type:article|preprint&sort=publication_date:desc&per_page=25&select=<select>`
   Reconstruct each abstract from `abstract_inverted_index`.

4. **arXiv (scriptable, no auth — Atom feed).** Query `sources.arxiv.base` with
   `search_query` combining the categories (`cat:`) and stream keywords (`all:`),
   `sortBy=submittedDate&sortOrder=descending`; keep entries whose submitted date ≥ `SINCE`.

5. **SSRN + Google Scholar (best-effort).** If a web-search tool is available, run the
   `web_search` queries under `sources.ssrn` and `sources.google_scholar`. If no web tool
   is available, skip them and note "web sources skipped (no web tool)" in the summary.

6. **Extract** per hit: title, authors, year, arXiv ID or DOI, a ~40–60 word abstract
   snippet, source, `matched_terms`, and `matched_streams` (every stream whose keywords it
   matches). Also flag hits by any author in `authors`.

7. **Deduplicate** against `dedup.against` (existing `vault/01-Literature` and every prior
   `vault/00-Meta/Discovery/_inbox/*.md`), matching on DOI / arXiv ID / normalized title
   (lowercased, punctuation-stripped, whitespace-collapsed). Keep all surviving hits
   (`retain_all_raw: true`).

8. **Write the inbox note** to the path in `output.inbox` (ISO year + ISO week, e.g.
   `vault/00-Meta/Discovery/_inbox/2026-W25.md`), creating directories as needed. If the
   note for this week already exists (a re-run), overwrite it with a fresh gather. Use this
   format exactly:

   ```markdown
   ---
   type: scout-inbox
   week: <YYYY-Www>
   generated: <ISO timestamp>
   runner: codex-cli <version>
   since: <SINCE>
   ---

   # Scout inbox — <YYYY-Www>

   > Gathered by Codex. Triage with Claude `/scout-review`. No viability judgment applied here.

   ## Summary
   - OpenAlex: N · arXiv: N · SSRN: N · Scholar: N · after dedup: M
   - Streams: longitudinal_social N · finance N · methods_frontier N · topological_deep_learning N · spatial_segregation N
   - Author-flagged: N

   ## Hits

   ### [<stream tags>] <Title>
   - **Authors:** ...
   - **Year:** ... · **ID:** arXiv:xxxx.xxxxx / doi:10.xxxx/...
   - **Source:** OpenAlex | arXiv | SSRN | Scholar
   - **Matched:** keyword1, keyword2 (author: Name, if applicable)
   - **Abstract:** snippet...

   <repeat per hit, grouped by stream, newest first>
   ```

9. **Print a final summary line** to stdout: counts per source and per stream, plus the
   output path written. That is the end of the run.
