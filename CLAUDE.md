# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Desafio 02 (módulo Desenvolvimento de Software e Aplicações com IA). Clone of `devfullcycle/mba-ia-refactor-projects-skill`, delivered as a **public GitHub fork**. Remotes: `upstream` = devfullcycle (read-only, holds the **legacy** code) and `origin` = `git@github.com:th1agoduarte/mba-ia-refactor-projects-skill.git`. Statement: `DESAFIO.md`. Deliverable docs: `README.md`. Requirement-by-requirement check: `VALIDACAO.md`.

The deliverable is a Claude Code skill (`.claude/skills/refactor-arch/`: `SKILL.md` + 5 references in `references/`) plus the result of running it on three legacy APIs: `code-smells-project` (Flask), `ecommerce-api-legacy` (Express), `task-manager-api` (Flask, partially layered). The three projects are **already refactored** in `main`; the legacy code only exists in `upstream/main`.

## Commands

```bash
make setup                 # venvs (uv) for the 2 Flask projects + npm install (rebuilds sqlite3 if npm 11 blocked its script)
make test                  # check + citations + contract-all (no LLM)
make check                 # tools/check_skill.py --reports: skill structure + 3 reports
make citations             # tools/verify_citations.py: every File:line + Evidence checked against upstream/main
make contract P=1|2|3      # tools/contract_test.py: boots the app with its documented command, replays the legacy contract
make run P=N               # run one app in the foreground
make sync-skill P=2|3      # copy the skill from project 1 (source of truth) to project P
make skill-audit P=N       # headless phases 1-2, read-only tools; writes reports/audit-project-N.md   (costs Claude tokens)
make skill-refactor P=N    # resumes that session answering "y" -> phase 3                             (costs Claude tokens)
```

`PROVIDER=anthropic|aws|google|openai` switches the LLM behind Claude Code (`google`/`openai` go through the LiteLLM gateway in `docker-compose.yml`, which exposes the Anthropic `/v1/messages` API). Default = the logged-in Claude Code account. `make gateway-test` sends one call Claude-API → Gemini.

## How the pieces fit

- **Skill source of truth is `code-smells-project/.claude/skills/refactor-arch/`.** Edit it there, then `make sync-skill P=2` and `P=3`; `check_skill.py` fails if the copies differ. Keep references free of project-specific names (agnosticism is a graded requirement). `check_skill.py` parses `## Fase N — <nome>`, `### AP-xx —`, the catalog index table, `## T-xx` sections with ANTES/DEPOIS code blocks, and report headings `### F-xx [SEV] ...` / `File: path:line`. Changing those formats means updating the checker.
- **Two-step headless run (`tools/run_skill.py`)** proves the mandatory phase-2 pause: step 1 allows only read tools and checks `git status`; step 2 is `claude -p --resume <session> "y"`. Session ids are stored in `docs/evidencias/skill-runs/pN-session.json`. Raw outputs: `pN-fase1-2.md`, `pN-fase3.md`.
- **Contract test is independent of the skill.** Baselines `docs/evidencias/contract/pN-antes.json` were recorded on the legacy code and must not be re-recorded on refactored code (`make contract-baseline` refuses). Endpoints marked `ADMIN` are called without a credential (401/403 accepted) and again with `X-Admin-Token` + `Authorization: Bearer` (the app is started with `ADMIN_TOKEN`), and must return the original status. If the default port is busy, the test uses port +100 via `PORT` (works only on refactored code). A local NestJS container often holds 3000.
- To re-run the skill on legacy code without touching the deliverable: `git worktree add ../refactor-legado upstream/main` and copy `.claude/` into each project there.

## Constraints

- Statement requirements: skill name `refactor-arch` and file `SKILL.md` are fixed; ≥ 8 anti-patterns (all 4 severities, deprecated APIs included); ≥ 8 playbook transformations with before/after code; phase 2 must pause before any change; phase 3 must validate boot + endpoints; reports in `reports/audit-project-{1,2,3}.md` at the repo root; one commit of refactored code per project.
- Phase-3 security changes allowed by the skill: removing sensitive fields from responses and requiring an admin credential on dangerous endpoints. Everything else must match the legacy contract.
- Seed demo passwords stay in the seeds (stored hashed) so the contract logins keep working.

## Status (2026-11-15)

Done: manual analysis (`docs/analise-manual.md`), skill, 3 runs (21/18/19 findings), refactor committed per project, contract 31/31 · 7/7 · 36/36, citations 58/58, README A–D. One run per project, no iterations needed. Costs: ~US$ 1 (phases 1–2) + ~US$ 3–4 (phase 3) per project on Claude Code.
