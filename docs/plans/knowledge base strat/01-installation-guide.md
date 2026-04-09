# Installation Guide

Step-by-step instructions for deploying all artefacts from the LLM Knowledge
Base Strategy into the correct locations. Work through these in order — later
items depend on earlier ones.

---

## 1. CONVENTIONS.md files (both vaults)

These go in first because the amended session skills will try to load them.

### TDA-Research vault
```
Copy: CONVENTIONS-TDA.md
To:   C:\Users\steph\Documents\TDA-Research\CONVENTIONS.md
```

Open it and review the "Always" and "Never" sections. The content is seeded
from what I know about your methodological decisions — correct anything that's
wrong or add decisions I've missed. This file should feel like *your* voice
codifying *your* rules, not an external imposition.

### Counting Lives vault
```
Copy: CONVENTIONS-CL.md
To:   C:\Users\steph\Documents\Counting Lives\Counting Lives\CONVENTIONS.md
```

Same review — check the register description, the anti-patterns list, and the
structural conventions. The anti-patterns should align with what your humanizer
skill already catches.

---

## 2. New skills (Cowork)

### session-capture
```
Create folder: session-capture/
Place:         session-capture-SKILL.md → session-capture/SKILL.md
Install:       Add to your Cowork skills for BOTH projects
               (it auto-detects which vault to file into)
```

### vault-health-check
```
Create folder: vault-health-check/
Place:         vault-health-check-SKILL.md → vault-health-check/SKILL.md
Install:       Add to your Cowork skills for BOTH projects
```

### Test both skills:
- Open a Cowork session on either vault
- Say "health check" — it should scan and produce a report
- After a substantive conversation, say "capture this session" — it should
  extract and file the outputs

---

## 3. Amend existing session skills

These are patches, not replacements. Apply them carefully to preserve the
existing skill logic.

### tda-session
Open your existing `tda-session/SKILL.md` and apply the three amendments
from `tda-session-amendments.md`:

1. Insert **Step 0** (CONVENTIONS + INDEX check) before the current Step 1
2. Insert **Step 7** (session close: index update + session capture offer)
   after the current "After presenting the brief" section
3. Update the brief template's "Attention Needed" section to include
   INDEX.md drift and health check recency

Renumber steps if needed to keep the flow clean.

### chapter-session
Open your existing `chapter-session/SKILL.md` and apply the four amendments
from `chapter-session-amendments.md`:

1. Insert **Step 0** (CONVENTIONS loading) before Step 1
2. Add the Index.md check to **Step 2**
3. Insert **Step 7** (session close) after Step 6
4. Add the vault status diagnostic to the **Step 5** brief template

---

## 4. Review personas (shared reference)

```
Copy: review-personas.md
To:   A location accessible to both Cowork projects
```

Options:
- Place in each vault at the root level
- Or keep in a shared location that both projects reference
- The personas file doesn't need to be a skill — it's a reference document
  that skills can load when review is needed

---

## 5. Blueprint template (website project)

```
Copy: implementation-blueprint-template.md
To:   [website project root]/docs/blueprints/TEMPLATE.md
```

Before implementing any feature from the PRD, copy the template to a new
file named `YYYY-MM-DD-[feature-slug].md`, fill it in, and get it to
"approved" status before writing code.

---

## 6. VAULT-MAP.md (both vaults)

After installing everything above, run a session with each vault and let
the amended session skills generate the first VAULT-MAP.md (or the
`## Vault Map` appendix to the existing INDEX.md). This establishes the
baseline that future sessions will incrementally update.

If the Longform-generated INDEX.md is tightly coupled to Longform's compile
order (which it likely is for the Counting Lives chapters), the safer option
is to create a separate VAULT-MAP.md at the vault root rather than appending
to INDEX.md. The session skills will detect and use whichever exists.

---

## 7. First health check

Once everything is installed, run a health check on each vault:
- "health check the TDA vault"
- "health check the Counting Lives vault"

This establishes a baseline and will immediately surface any orphan notes,
stale TODOs, or unverified Perplexity captures that have accumulated. It
also tests that the new skill works correctly with your actual vault
structure.

---

## Verification checklist

After installation, verify each component:

- [ ] CONVENTIONS.md loads correctly in a TDA session (Step 0 references it)
- [ ] CONVENTIONS.md loads correctly in a chapter session
- [ ] Session capture correctly identifies the target vault
- [ ] Session capture creates notes in the right locations
- [ ] Health check finds and reports on actual vault contents
- [ ] INDEX.md / VAULT-MAP.md gets updated at session close
- [ ] Review personas load and produce distinct feedback per specialist
- [ ] Blueprint template is accessible from the website project

---

## Ongoing maintenance

| Task | Frequency | Trigger |
|---|---|---|
| Update CONVENTIONS.md | Per session | When a decision is locked |
| Run health check | Weekly | Or when >14 days since last |
| Regenerate VAULT-MAP.md | Per session | Automatic at session close |
| Capture session outputs | Per session | Offered automatically |
| Review with specialist personas | Per draft | Before submission/completion |
| Create implementation blueprints | Per feature | Before coding website features |
