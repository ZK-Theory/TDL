# Discovery & Triage Harness — Handoff (2026-06-16)

**For:** the next agent (Claude Code or Codex CLI) continuing this work.
**Read first:** the canonical plan `docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md`
(esp. §2 decisions, §2a resolutions, §5 Assay rubric, §11 phasing). This handoff is the
short orientation; the plan is the spec.

---

## 1. What this is

A **living front-of-funnel** for finding and vetting TDA research topics — the repeatable
counterpart to the static `Meta-Research-Plan-23-03-2026.md` / `Programme-Map.md`. It feeds
the **existing** APM execution + assurance backend; it does not replace it.

```
SCOUT → ASSAY → SPIKE ──(pre-registration)──► APM execution → assurance → paper
(watch) (score) (probe)                         (existing, untouched)
```

- **SCOUT** = weekly literature gather → inbox note. **BUILT, TESTED, SCHEDULED.**
- **ASSAY** = 3-axis viability scorecard → ranked backlog. **BUILT and used for STRAND.**
- **SPIKE** = time-boxed feasibility probe → pre-registration. **BUILT and used for STRAND.**

## 2. Current state (what is done)

- **Branch `docs/discovery-harness`** contains the design lock, Scout fixes, frontmatter
  fix, `/scout-review`, and the current uncommitted Assay/Spike/Phase-C execution work.
  **Unmerged** — Manager/User merges per APM rules.
- **Scout is built, tested, and scheduled:**
  - `scout/watchlist.yaml` — sources, streams, the gate-vs-label matching rule.
  - `scout/scout-weekly-job.md` — the Codex `codex exec` prompt (gather only).
  - `scout/run-scout.ps1` — Task Scheduler wrapper (`Start-Process` + file redirects).
  - Windows Task **`TDL-Scout-Weekly`**, Sundays 20:00, interactive (runs as the user).
  - First test produced `vault/00-Meta/Discovery/_inbox/2026-W25.md` (9 real hits;
    arXiv:2606.11911 verified live). Network works under Codex `workspace-write`.
- **Assay/Spike:** STRAND (`arXiv:2606.11911`) was triaged from the W25 inbox, assayed
  PROMOTE, explicitly approved for Spike, computed at toy scale, and converted into a
  dispatch-ready `/pre-reg-to-dispatch` packet.
- **Vault index:** `00-Meta/Discovery-Harness.md`. Discovery vault artifacts now include
  `_inbox/2026-W25.md`, `_backlog.md`, STRAND assay, Spike pre-reg, and Spike result.

## 3. Locked decisions (do not re-litigate — see plan §2/§2a)

D1 full integrated loop · D2 viability = **topology-earns-keep (gate) + data-feasibility +
novelty**, *programme-fit excluded* · D3 tool-agnostic, Claude-first · D4 standing
surveillance · D5 **Codex CLI runs Scout; Claude runs the judgment** · D6 plan-first.
PROMOTE rule: Axis-1 gate pass **and** (Axis2+Axis3) ≥ 4, neither = 0. FIN-01 seeds a full
finance stream.

## 4. How Scout works operationally

`run-scout.ps1` pipes `scout-weekly-job.md` into `codex exec --cd <repo> --sandbox
workspace-write`. Codex reads `watchlist.yaml`, fetches OpenAlex + arXiv (free, no auth),
applies the **relevance gate** (must match a `tda_terms` term) then **tags streams** by
discriminating `topic_keywords`, dedups against `01-Literature` + prior inbox, and writes
one weekly inbox note. **Gather only — no triage/scoring/commit.** Web sources
(SSRN/Scholar) are best-effort and were skipped (no web tool in the exec context).

## 5. Open threads / blockers

- The old Codex skill-loading blocker is resolved by the frontmatter fix commit
  `ac857a3`; do not reintroduce skills without YAML frontmatter.
- The Scout scheduled task exists locally as `TDL-Scout-Weekly` and next runs Sunday
  2026-06-21 at 20:00 local. If migrating machines, recreate that OS-level state.

## 6. Next tasks (priority order)

1. **APM Manager dispatch for STRAND** — use
   `vault/00-Meta/Discovery/strand-persistence-survival-testing-pre-reg-to-dispatch.md`
   to open a bounded STRAND-vs-W2/landscape comparison task. Do not treat the Spike result
   as paper-facing evidence.
2. **Commit/merge hygiene** — review the untracked Discovery Harness implementation files,
   commit with the project prefix convention, then Manager/User merges per APM rules.
3. **Next weekly Scout cycle** — let `TDL-Scout-Weekly` produce the next inbox; run
   `/scout-review` only after the gather lands.

## 7. Conventions & gotchas (learned this session)

- **Vault writes** via `Write`/`Edit` on `vault/<path>` or the real
  `C:\Users\steph\Documents\TDA-Research\` path — never `vault_observe`. New log entries go
  **top-of-page, reverse-chronological**.
- **`Glob` does NOT cross the `vault/` junction** — use `Read`/PowerShell for vault paths.
- **Commit messages:** `[PREFIX] PXX:`-style, BOM-free message file via `git commit -F`
  (PS `Out-File -Encoding utf8` adds a BOM that breaks the prefix hook). Co-Authored-By
  trailer required. Never `--no-verify`. Workers commit on branches; Manager merges.
- **PowerShell runner scripts around native exes:** use `Start-Process` with
  `-RedirectStandardInput/Output/Error` to files + `$proc.ExitCode`, **not** a pipeline
  with `*>>` under `ErrorActionPreference=Stop` (it turns benign stderr into a fatal error).
- **Keyword watchlists:** generic terms gate, discriminating terms label (never let a shared
  term assign a category).
- Run `task-observer` at session start (global policy); but the **Scout unattended job is
  told to skip session-meta skills** — keep it that way.
