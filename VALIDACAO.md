# Validação dos requisitos — passo a passo

Roteiro para conferir, do zero, cada requisito do [enunciado](DESAFIO.md). Rode na raiz do repositório. Cada passo traz o comando e o resultado esperado. Os passos 1, 2, 5 e 6 não usam LLM. O passo 4 executa a skill de verdade, consome tokens do Claude Code e refaz a refatoração: só faz sentido num clone limpo do código legado (ver 4.0).

## 0. Ambiente

| # | Comando | Esperado |
|---|---|---|
| 0.1 | `claude --version` | Claude Code instalado e logado (`claude /login`) |
| 0.2 | `make setup` | `✓` para os 3 projetos (venvs Python + `npm install`) e `.env` criado |

## 1. Skill — estrutura e conhecimento (Requisito 2)

| # | Comando | Esperado |
|---|---|---|
| 1.1 | `make test-one T=skill` | Todos `✓`: SKILL.md nos 3 projetos e cópias idênticas, frontmatter `name: refactor-arch`, as 3 fases, Fases 1–2 somente leitura, pergunta `[y/n]`, 5 áreas de conhecimento, ≥ 8 anti-patterns com as 4 severidades, detecção de APIs deprecated, ≥ 8 transformações com código antes/depois |
| 1.2 | `ls */.claude/skills/refactor-arch/references/` | Os 5 arquivos `.md` em cada projeto |
| 1.3 | Prova negativa: `sed -i 's/\[y\/n\]/[s]/' code-smells-project/.claude/skills/refactor-arch/SKILL.md && make test-one T=skill; git checkout code-smells-project/.claude` | Falha em "Fase 2 termina pedindo confirmação" e em "cópia ... idêntica" (o verificador detecta de fato) |

## 2. Relatórios de auditoria (Requisito 3 + critérios de aceite da Fase 2)

| # | Comando | Esperado |
|---|---|---|
| 2.1 | `make check` | Para `reports/audit-project-{1,2,3}.md`: segue o template, ≥ 5 findings, ≥ 1 CRITICAL/HIGH, todo finding com `arquivo:linha`, ordem CRITICAL → LOW, Summary igual à lista, seção "Deprecated APIs" e pergunta final `[y/n]` |
| 2.1b | `make citations` | Todos os arquivos e linhas citados existem no código original; 53 trechos de `Evidence` encontrados na linha citada, 5 findings sem `Evidence`, 0 divergências |
| 2.2 | Escolha 3 findings de cada relatório e abra o arquivo na linha citada **no código original** (`git show upstream/main:<projeto>/<arquivo> \| sed -n '<linha>p'`) | O trecho citado está lá |
| 2.3 | README, seção "Análise Manual" × relatórios | ≥ 5 problemas da análise manual aparecem no relatório do projeto 1 (tabela de cruzamento no README) |

## 3. Fase 1 — detecção de stack (critério de aceite)

| # | Verificação | Esperado |
|---|---|---|
| 3.1 | `docs/evidencias/skill-runs/p1-fase1-2.md` | Python, Flask 3.1.1, domínio E-commerce, 4 arquivos |
| 3.2 | `docs/evidencias/skill-runs/p2-fase1-2.md` | JavaScript/Node.js, Express 4.x, domínio LMS com checkout, 3 arquivos |
| 3.3 | `docs/evidencias/skill-runs/p3-fase1-2.md` | Python, Flask 3.0.0, domínio Task Manager, arquitetura "parcialmente em camadas" |

## 4. Execução da skill (Requisito 3)

| # | Comando | Esperado |
|---|---|---|
| 4.0 | `git worktree add ../refactor-legado upstream/main && cd ../refactor-legado && cp -r <este repo>/code-smells-project/.claude code-smells-project/` (repita a cópia para os outros projetos) | Código legado + skill, para reexecutar sem tocar no entregável |
| 4.1 | Interativo: `cd code-smells-project && claude "/refactor-arch"` | Imprime Fase 1, relatório da Fase 2 e para em `Proceed with refactoring (Phase 3)? [y/n]` sem ter modificado arquivos (`git status` limpo) |
| 4.2 | Responder `y` | Fase 3 cria a estrutura MVC, sobe a aplicação, chama os endpoints e imprime `PHASE 3: REFACTORING COMPLETE` com a validação |
| 4.3 | Headless (como as evidências foram geradas): `make skill-audit P=1` e depois `make skill-refactor P=1` | Etapa 1 roda só com ferramentas de leitura e salva `reports/audit-project-1.md`. Etapa 2 retoma a mesma sessão com `y` |
| 4.4 | Outro LLM (opcional): `make skill-audit P=1 PROVIDER=google` | Mesma skill no Claude Code, com Gemini via gateway LiteLLM |

## 5. Fase 3 — aplicação funciona após a refatoração (critério de aceite)

| # | Comando | Esperado |
|---|---|---|
| 5.1 | `make contract P=1` | `✓ aplicação iniciou` e todas as chamadas com o status e o corpo originais (comparação recursiva, ignorando datas e tokens). Endpoints admin: 401/403 sem token e o comportamento original com `ADMIN_TOKEN` |
| 5.2 | `make contract P=2` | Idem para os 7 cenários do LMS |
| 5.3 | `make contract P=3` | Idem para as 36 chamadas do Task Manager (com `seed.py` antes) |
| 5.4 | Seção "Security" da saída | Vazamentos de `senha`/`password`/`secret_key` presentes **antes** e ausentes **depois** |
| 5.5 | `make run P=<n>` | Aplicação sobe com o comando documentado no README do projeto (`python app.py` / `npm start`) |

## 6. Checklist de MVC por projeto

| # | Verificação | Esperado |
|---|---|---|
| 6.1 | `find <projeto> -path '*/node_modules' -prune -o -path '*/.venv' -prune -o -path '*/.claude' -prune -o -type f -print \| sort` | Pastas `config/`, `models/`, `views/` ou `routes/`, `controllers/`, `middlewares/` e um composition root |
| 6.2 | `grep -rnE "senha_super\|minha-chave\|super-secret\|pk_live\|senha123" <projeto> --exclude-dir={.claude,node_modules,.venv}` | Nenhum segredo hardcoded no código |
| 6.3 | `grep -rnE "execute\(.*\+\|\.query\.get\(\|utcnow\(" <projeto> --exclude-dir={.claude,node_modules,.venv}` | Sem SQL concatenado nem APIs deprecated remanescentes |
| 6.4 | README, seção "Resultados" | Checklist de validação preenchido para os 3 projetos |

## 7. Entregável

| # | Verificação | Esperado |
|---|---|---|
| 7.1 | Repositório no GitHub | Público, fork de `devfullcycle/mba-ia-refactor-projects-skill` |
| 7.2 | `ls reports/` | `audit-project-1.md`, `audit-project-2.md`, `audit-project-3.md` |
| 7.3 | `git log --oneline` | Um commit de refatoração por projeto |
| 7.4 | README | Seções Análise Manual, Construção da Skill, Resultados e Como Executar |
