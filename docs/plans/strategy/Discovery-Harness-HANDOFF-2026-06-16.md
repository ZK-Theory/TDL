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

- **SCOUT** = weekly literature gather → inbox note. **BUILT & LIVE.**
- **ASSAY** = 3-axis viability scorecard → ranked backlog. **NOT BUILT.**
- **SPIKE** = time-boxed feasibility probe → pre-registration. **NOT BUILT.**

## 2. Current state (what is done)

- **Branch `docs/discovery-harness`**, commits `926ac66` ([DECISION] design lock) and
  `e7bb371` ([EXPLORE] post-test fixes). **Unmerged** — Manager/User merges per APM rules.
- **Scout is built, tested, and scheduled:**
  - `scout/watchlist.yaml` — sources, streams, the gate-vs-label matching rule.
  - `scout/scout-weekly-job.md` — the Codex `codex exec` prompt (gather only).
  - `scout/run-scout.ps1` — Task Scheduler wrapper (`Start-Process` + file redirects).
  - Windows Task **`TDL-Scout-Weekly`**, Sundays 20:00, interactive (runs as the user).
  - First test produced `vault/00-Meta/Discovery/_inbox/2026-W25.md` (9 real hits;
    arXiv:2606.11911 verified live). Network works under Codex `workspace-write`.
- **Vault index:** `00-Meta/Discovery-Harness.md`. **Session log:** Computational-Log
  2026-06-16 entry + daily note `05-Daily/2026-06-16.md`.

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

- **BLOCKER for the Codex-co-worker goal (Phase C):** all 14 `.agents/skills/*/SKILL.md`
  lack YAML frontmatter, so **Codex loads zero TDL skills** (see `scout/logs/*.err.log`).
  Scout doesn't need them, but Assay/Spike-as-Codex would. Before fixing, find out how
  `.agents/skills/` is generated (hand-maintained vs synced from `.superpowers`).

## 6. Next tasks (priority order)

1. **`/scout-review`** (Claude) — read the latest `_inbox/*.md`, cluster, drop noise, and
   for survivors draft a one-line relevance note; promote the strongest into Assay. This is
   the deferred judgment half of Scout (D5).
2. **`/assay`** (Claude) — the 3-axis scorecard (plan §5). Axis-1 *topology-earns-its-keep*
   is an **adversarial pass/fail gate run first** (argue why TDA is NOT needed; require a
   named baseline + a falsifiable feature→claim mapping). Back it with a **scorecard JSON
   schema in `contracts/`** authored via `schema-contract-design` + a binding test. Output
   PROMOTE/PARK/KILL as a **user-decision point**; write to `00-Meta/Discovery/_backlog.md`.
3. **`00-Meta/Discovery/_backlog.md`** — the living ranked candidate list (single source of
   truth for lifecycle states: inbox → triaged → assayed → spiked → registered → …).
4. **`/spike`** (Claude) — time-boxed feasibility probe (reuse `new-analysis`,
   `tda-experiment`, `null-operation-invariance-audit`, `statistical-design-audit`,
   `representation-freeze-audit`) emitting a pre-reg consumed by `pre-reg-to-dispatch`.
5. **Phase C** — agent-neutral task contract + Codex playbooks (after the `.agents/skills`
   fix); optionally promote Scout to an automated cloud routine.

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
