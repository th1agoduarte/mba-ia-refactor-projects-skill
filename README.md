# Skill `refactor-arch` — Refatoração Arquitetural Automatizada

Entrega do desafio **Criação de Skills** (módulo Desenvolvimento de Software e Aplicações com IA, MBA em Engenharia de Software com IA da Full Cycle). O enunciado completo está em [DESAFIO.md](DESAFIO.md) e o roteiro de conferência de cada requisito em [VALIDACAO.md](VALIDACAO.md).

A skill `refactor-arch` audita e refatora qualquer projeto backend para o padrão MVC, em três fases: análise, auditoria com pausa para confirmação, e refatoração com validação. Ela foi executada com o **Claude Code** nos três projetos legados do repositório: dois em Python/Flask e um em Node.js/Express.

| Entregável | Onde |
|---|---|
| Skill (SKILL.md + 5 referências) | `code-smells-project/.claude/skills/refactor-arch/`, com cópias idênticas em `ecommerce-api-legacy/` e `task-manager-api/` |
| Código refatorado (resultado da Fase 3) | as três pastas de projeto, um commit por projeto |
| Relatórios de auditoria (saída da Fase 2) | [reports/audit-project-1.md](reports/audit-project-1.md), [2](reports/audit-project-2.md), [3](reports/audit-project-3.md) |
| Saídas brutas das execuções, contrato HTTP antes/depois | [docs/evidencias/](docs/evidencias/) |

---

## A) Análise Manual

Antes de escrever a skill, li o código dos três projetos e documentei os problemas com severidade, localização e justificativa. A tabela completa (44 problemas, com arquivo:linha no código original) está em **[docs/analise-manual.md](docs/analise-manual.md)**. Resumo dos mais relevantes:

### Projeto 1 — code-smells-project (Python/Flask, e-commerce)

| Sev. | Problema | Onde | Por que importa |
|---|---|---|---|
| CRITICAL | SQL Injection por concatenação em quase todas as queries | `models.py:28, 47-50, 109-111, 289-297...` | Login sem senha com `' OR '1'='1' --`; leitura/remoção de qualquer tabela |
| CRITICAL | `/admin/query` (SQL arbitrário) e `/admin/reset-db` sem autenticação | `app.py:47-78` | Qualquer cliente apaga o banco |
| CRITICAL | `SECRET_KEY` hardcoded e devolvida no `/health` | `app.py:7`, `controllers.py:285-289` | Segredo de sessão público |
| CRITICAL | Senhas em texto puro, devolvidas em `GET /usuarios` | `database.py:75-79`, `models.py:83, 99, 126-129` | Vazamento de credenciais |
| CRITICAL | Sem camadas: `models.py` com 4 domínios + SQL + regra de desconto | `models.py:1-314` | Nada testável isoladamente |
| HIGH | `debug=True` em `0.0.0.0`; conexão global mutável; pedido sem transação | `app.py:8, 88`; `database.py:4-10`; `models.py:133-169` | RCE pelo debugger; estado global; estoque negativo sob concorrência |
| MEDIUM | N+1 em pedidos → itens → produto; `str(e)` devolvido em todo handler; validação duplicada | `models.py:171-233`; `controllers.py`; `controllers.py:28-50 × 72-90` | Performance; vazamento de detalhes; regras divergentes |
| LOW | Magic numbers (faixas de desconto), `print` como log, imports não usados | `models.py:257-262`; `controllers.py:8, 57...`; `models.py:2` | Legibilidade |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express, LMS com checkout)

| Sev. | Problema | Onde | Por que importa |
|---|---|---|---|
| CRITICAL | Credenciais de produção hardcoded (`pk_live`, senha do banco) | `src/utils.js:1-7` | Acesso ao gateway de pagamento |
| CRITICAL | Cartão completo e chave do gateway no log | `src/AppManager.js:45` | Violação de PCI-DSS |
| CRITICAL | "Hash" de senha é Base64 truncado; senha padrão `123456` | `src/utils.js:17-23`; `src/AppManager.js:68` | Reversível e com colisões |
| CRITICAL | God Class `AppManager` (banco, seed, rotas, pagamento, relatório) | `src/AppManager.js:4-139` | Sem camadas |
| CRITICAL | Relatório financeiro e exclusão de usuário sem autenticação | `src/AppManager.js:80, 131` | Dados financeiros públicos |
| HIGH | Checkout sem transação; delete deixa órfãos; estado global exportado | `src/AppManager.js:43-63, 131-136`; `src/utils.js:9-10` | Integridade de dados |
| MEDIUM | Callback hell (5 níveis), N+1 no relatório, erros de callback ignorados | `src/AppManager.js:37-77, 92-125` | Manutenção e performance |
| LOW | Nomes opacos (`u`, `e`, `p`, `cc`), magic strings (`"PAID"`), código morto | `src/AppManager.js:29-33`; `src/utils.js:2-5` | Legibilidade |

### Projeto 3 — task-manager-api (Python/Flask, parcialmente em camadas)

| Sev. | Problema | Onde | Por que importa |
|---|---|---|---|
| CRITICAL | `SECRET_KEY` e senha SMTP hardcoded | `app.py:13`; `services/notification_service.py:7-10` | Credenciais no repositório |
| CRITICAL | Hash da senha devolvido em `/users` e no login | `models/user.py:16-24` | Exposição de credenciais |
| HIGH | MD5 sem salt; token de login falso e previsível; `debug=True` | `models/user.py:27-31`; `routes/user_routes.py:207-211`; `app.py:34` | Segurança |
| HIGH | Regra de negócio e serialização nas rotas (não há controllers) | `routes/task_routes.py:11-154`; `routes/report_routes.py:12-101` | "Organizado" só na aparência |
| MEDIUM | N+1 (`Query.get` por task), lógica de "atrasada" duplicada 6×, APIs deprecated (`Query.get`, `datetime.utcnow`), `except:` nu | `routes/*.py`; `models/*.py` | Performance, duplicação, warnings |
| LOW | Imports não usados, magic numbers ignorando constantes existentes, condicionais verbosas | `app.py:7`; `utils/helpers.py:110-116`; `models/task.py:38-60` | Legibilidade |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                          # o "prompt": papel, regras invioláveis e as 3 fases com formato de saída
└── references/
    ├── project-analysis.md           # Análise de projeto: linguagem, framework, banco, domínio, arquitetura, rotas, como validar
    ├── anti-patterns-catalog.md      # Catálogo: 23 anti-patterns, sinais de detecção (grep), como confirmar, severidade
    ├── report-template.md            # Template do relatório da Fase 2 + exemplo de finding bom e ruim
    ├── mvc-guidelines.md             # Guidelines: camadas, regra de dependência, estruturas alvo por stack, adaptação
    └── refactoring-playbook.md       # Playbook: 14 transformações com código antes/depois (Python e Node)
```

### Decisões de design

- **SKILL.md é o processo; as referências são o conhecimento.** O SKILL.md diz *o que* fazer em cada fase, *quando* ler cada referência e *qual formato* imprimir. O conhecimento de domínio (heurísticas, catálogo, playbook) fica nas referências, carregadas só na fase em que são necessárias (*progressive disclosure*). O SKILL.md tem cerca de 130 linhas.
- **Regras invioláveis no topo**, porque são o que mais falha em agentes:
  1. Fases 1 e 2 somente leitura.
  2. Pausa obrigatória com a frase exata `Proceed with refactoring (Phase 3)? [y/n]`, encerrando a resposta mesmo em modo não interativo.
  3. Toda linha citada vem de `grep -n`/`cat -n`, nunca estimada.
  4. Preservar o contrato externo: rotas, métodos, status, formato JSON e comando de execução.
  5. Nunca declarar sucesso sem executar a validação.
- **Detecção em duas etapas.** Cada anti-pattern tem **sinais** (buscas `grep -rnE` que geram candidatos) e um critério de **confirmação** (o que precisa ser verdade no trecho lido). Isso segue a dica "query SQL dentro de loop for é acionável" e evita falsos positivos de grep puro.
- **Relatório com formato verificável.** O template fixa títulos, `F-xx [SEVERIDADE] Nome (AP-xx)`, `File:` com linha, `Evidence:` com o trecho real, ordenação e a seção obrigatória "Deprecated APIs". Com isso, `tools/check_skill.py` consegue validar os relatórios automaticamente.
- **Contrato preservado com exceções explícitas de segurança.** Uma refatoração não pode mudar o comportamento, mas dois tipos de mudança são desejáveis:
  - remover senha, hash e segredo das respostas;
  - exigir credencial nos endpoints administrativos perigosos.

  A skill só aceita essas duas e precisa listá-las no resumo da Fase 3. Os endpoints `/admin/*` continuam existindo e respondem 401/403 sem token: deletar a rota quebraria o contrato, e mantê-la aberta manteria a falha CRITICAL.
- **Validação comparativa.** Antes de mexer, a Fase 3 sobe a aplicação original e registra o status de cada rota. Depois, sobe a refatorada e compara. "Endpoints respondendo" passa a significar "mesmo status de antes", não apenas "não deu 500".

### Anti-patterns do catálogo (e por quê)

| Severidade | Anti-patterns | Motivo da inclusão |
|---|---|---|
| CRITICAL | AP-01 Segredos hardcoded · AP-02 SQL Injection · AP-03 God Class/File · AP-04 Endpoint admin sem auth · AP-05 Exposição de dados sensíveis · AP-06 Senha insegura (texto puro/Base64 = CRITICAL; MD5 = HIGH) | Exemplos literais da definição de CRITICAL do enunciado e presentes nos 3 projetos |
| HIGH | AP-07 Fat Controller · AP-08 Estado global mutável · AP-09 Acoplamento sem DI · AP-10 Escrita sem transação/órfãos · AP-11 Debug/config insegura | Exemplos da definição de HIGH (lógica em controllers, falta de DI, estado global), mais integridade de dados e o debugger do Werkzeug |
| MEDIUM | AP-12 N+1 · AP-13 Validação ausente/duplicada · AP-14 Duplicação · AP-15 Erro não centralizado · AP-16 Callback hell · **AP-17 APIs deprecated** · AP-18 Efeitos colaterais acoplados | Definição de MEDIUM (N+1, middlewares, validação), mais o requisito de APIs deprecated, com uma tabela de deprecated → moderno para Python, SQLAlchemy, Flask, Node e Express |
| LOW | AP-19 Magic numbers · AP-20 Nomes ruins · AP-21 Imports/código morto · AP-22 `print` como log · AP-23 Condicionais verbosas | Definição de LOW |

O catálogo traz uma regra de ajuste de severidade: sobe um nível em caminhos de dinheiro, auth ou dados pessoais, e desce em scripts de seed. Ela explica por que, por exemplo, um `print` que registra e-mails pode aparecer como MEDIUM.

### Como garanti que a skill é agnóstica de tecnologia

- **Nada nas referências cita os projetos-alvo.** Exemplos de domínio, nomes de classes e campos foram escritos de forma genérica: tirei de propósito `AppManager`, `badCrypto`, `usr/eml`. O playbook usa padrões que observei nos projetos, mas com identificadores genéricos.
- **Heurísticas por evidência, em tabelas multi-stack:**
  - manifesto → linguagem;
  - dependência + sinal no código → framework (Flask, Django, FastAPI, Express, Nest, Spring, Gin, Rails, Laravel);
  - driver/ORM → banco;
  - regex de rotas por framework;
  - versão vinda do pino ou do lockfile.
- **Estruturas alvo por stack** (Flask, Express e mapeamento para Django/FastAPI/Spring) e uma tabela de **adaptação ao ponto de partida**: monolito, arquivos planos ou parcialmente em camadas. A dica do enunciado "projetos diferentes exigem adaptação" virou regra explícita: no projeto 3, a skill preserva o que está certo e cria só a camada que falta.
- **Validação genérica.** A forma de preparar o ambiente (venv ou `npm install`), subir, chamar com `curl` e derrubar vem da referência e serve para qualquer stack HTTP.
- **Teste prático.** A mesma pasta, copiada byte a byte (verificado por `tools/check_skill.py`), rodou nos 3 projetos sem nenhum ajuste por projeto.

### Desafios encontrados e como resolvi

| Desafio | Solução |
|---|---|
| **Provar a pausa da Fase 2.** Num terminal interativo a pausa é visível, mas era preciso evidência reproduzível de que nada é modificado antes do "y". | A skill é executada em **duas etapas headless** (`tools/run_skill.py`). Primeiro `claude -p "/refactor-arch"` **só com ferramentas de leitura liberadas** (`Read`, `Grep`, `Glob` e `grep/find/wc/cat`; `Edit`/`Write` negados). A execução termina na pergunta `[y/n]`, e o script confere com `git status` que nenhum arquivo do projeto mudou. Depois de revisar o relatório, `claude -p --resume <sessão> "y"` retoma a **mesma sessão** e executa a Fase 3. |
| **Linhas exatas.** Agentes tendem a "estimar" linhas. | Regra inviolável no SKILL.md (só linha lida com `grep -n`/`cat -n`), template com `File:` + `Evidence:` obrigatórios e um verificador independente (`tools/verify_citations.py`) que procura o trecho citado no código **original** em volta da linha informada: **58/58 citações conferidas**. |
| **Refatorar sem quebrar, mas corrigindo falhas de segurança.** Endpoints como `/admin/query` (SQL arbitrário) não podem continuar abertos, e apagá-los quebraria o contrato. | Regra 5 da skill: o contrato é preservado e só duas exceções são aceitas (remover dados sensíveis e exigir credencial em endpoints perigosos), sempre listadas no resumo. O teste de contrato chama esses endpoints **duas vezes**: sem credencial aceita 401/403; com `ADMIN_TOKEN` exige o status e o corpo originais. |
| **Skill acoplada aos projetos.** Os primeiros rascunhos das referências usavam nomes vistos nos projetos (`AppManager`, `badCrypto`, campos `usr/eml`). | Troquei por exemplos genéricos antes da primeira execução. As referências descrevem padrões; a detecção acontece no código. |
| **Projeto já organizado (projeto 3).** Uma skill que "sempre cria `src/`" destruiria o que está certo. | Tabela de adaptação em `mvc-guidelines.md`. No projeto 3 a skill manteve `models/` e `routes/`, criou só `controllers/`, `config/` e `middlewares/`, tirou as rotas de categoria de `report_routes.py` e apagou `utils/`, que era código morto. |
| **Ambiente.** O npm 11 bloqueia o install script do `sqlite3` (`allow-scripts`), e a porta 3000 estava ocupada por outro container local. | A referência de validação ensina `npm approve-scripts <pkg>` + `npm rebuild`; o `make setup` faz o rebuild. O teste de contrato usa porta alternativa via `PORT`, que o código refatorado passou a ler da config. |
| **Extração do relatório.** O agente às vezes envolve o relatório num bloco de código. | `run_skill.py` recorta do cabeçalho `ARCHITECTURE AUDIT REPORT` até a pergunta `[y/n]` e remove as cercas de código. |

---

## C) Resultados

Execução: Claude Code 2.1.325, modelo padrão da conta, 3 projetos, **sem nenhum ajuste na skill entre um projeto e outro** (a mesma pasta, copiada byte a byte). Saídas brutas de cada fase, com sessão, turnos, duração e custo: [docs/evidencias/skill-runs/](docs/evidencias/skill-runs/).

### Resumo das auditorias (Fase 2)

| Projeto | Stack detectada (Fase 1) | CRITICAL | HIGH | MEDIUM | LOW | Total | Deprecated APIs |
|---|---|---|---|---|---|---|---|
| 1 · code-smells-project | Python + Flask 3.1.1, e-commerce, monolito em arquivos planos, 4 arquivos | 7 | 4 | 7 | 3 | **21** | nenhuma (verificado e justificado no relatório) |
| 2 · ecommerce-api-legacy | JavaScript (Node.js) + Express 4.22.1, LMS com checkout, God Class, 3 arquivos | 6 | 4 | 4 | 4 | **18** | nenhuma (verificado: `new Buffer`, `url.parse`, `body-parser`, `req.param`...) |
| 3 · task-manager-api | Python + Flask 3.0.0, Task Manager, **parcialmente em camadas**, 15 arquivos | 4 | 5 | 5 | 5 | **19** | `Model.query.get()` (16×), `datetime.utcnow()` (20+×) |

Relatórios completos: [audit-project-1.md](reports/audit-project-1.md), [audit-project-2.md](reports/audit-project-2.md), [audit-project-3.md](reports/audit-project-3.md).

**Análise manual × skill (projeto 1).** Todos os 15 problemas da análise manual aparecem no relatório (o mínimo exigido é 5):

| Análise manual | Finding da skill |
|---|---|
| M1-01 SQL Injection | F-06 (CRITICAL) |
| M1-02 `/admin/*` sem auth | F-02 (CRITICAL) |
| M1-03 segredo hardcoded e exposto | F-01, F-03 (CRITICAL) |
| M1-04 senha em texto puro | F-04 (CRITICAL) |
| M1-05 sem camadas | F-05 (CRITICAL) |
| M1-06 debug em 0.0.0.0 | F-09 (HIGH) |
| M1-07 conexão global | F-11 (HIGH), F-08 (HIGH) |
| M1-08 pedido sem transação | F-07 (CRITICAL; a skill subiu a severidade por ser caminho de dinheiro) |
| M1-09 / M1-12 N+1 e COUNTs | F-17 (MEDIUM) |
| M1-10 erro não centralizado | F-14 (MEDIUM) |
| M1-11 duplicação | F-16 (MEDIUM) |
| M1-13 magic numbers | F-18 (MEDIUM) |
| M1-14 `print` | F-12 (MEDIUM: loga e-mails) |
| M1-15 imports/nomes | F-21, F-19 (LOW) |

Nos projetos 2 e 3, a skill também encontrou o equivalente de todos os itens da análise manual. A única exceção parcial é a coesão das rotas de categoria dentro de `report_routes.py` (M3-11), que não virou finding próprio, mas foi corrigida na Fase 3 (`routes/category_routes.py`).

### Antes × depois

| Projeto | Antes | Depois |
|---|---|---|
| 1 | 4 arquivos, ~780 linhas na raiz: `app.py` (rotas + SQL admin), `controllers.py`, `models.py` (4 domínios + SQL), `database.py` (conexão global) | 31 arquivos: `app.py` (launcher) + `src/{config, models, controllers, views, middlewares, services}`, `create_app()` |
| 2 | 3 arquivos, ~180 linhas: `app.js`, `AppManager.js` (God Class), `utils.js` (segredos + estado global) | 24 arquivos: `src/app.js` (composition root) + `src/{config, database, models, controllers, routes, middlewares, services}` |
| 3 | 15 arquivos: `models/`, `routes/` gordas, `services/` com senha SMTP, `utils/` morto | 28 arquivos: `models/` e `routes/` preservados e afinados + `config/`, `controllers/`, `middlewares/`, `services/token_service.py`; `utils/` removido |

```text
code-smells-project/                  ecommerce-api-legacy/                 task-manager-api/
├── app.py         (launcher)         ├── package.json (npm start)          ├── app.py          (create_app)
├── .env.example                      ├── .env.example                      ├── seed.py · database.py
└── src/                              └── src/                              ├── .env.example
    ├── app.py     (create_app)           ├── app.js   (composition root)   ├── config/settings.py
    ├── config/settings.py                ├── config/ (index, constants,    ├── models/     task, user, category
    ├── database.py · errors.py           │            logger)              ├── controllers/ task, user, category,
    ├── models/      produto, usuario,    ├── database/ connection, schema, │                report, validators
    │                pedido, sistema      │             seed                ├── routes/     task, user, category,
    ├── controllers/ produto, usuario,    ├── models/  user, course, ...    │                report, system
    │                pedido, relatorio,   ├── controllers/ checkout,        ├── middlewares/ error_handler, auth
    │                sistema, validators  │                report, user     └── services/   notification, token
    ├── views/       *_routes.py          ├── routes/  *Routes.js
    ├── middlewares/ error_handler, auth  ├── middlewares/ errorHandler,
    └── services/    notification         │                adminAuth
                                          └── services/ paymentGateway
```

### Aplicações funcionando após a refatoração

`make test` ([log completo](docs/evidencias/validacao-final.log)) sobe cada aplicação com o comando documentado e compara cada chamada com o contrato gravado **no código original, antes da skill** ([contract/](docs/evidencias/contract/)):

| Projeto | Boot | Contrato original | Vazamentos (antes → depois) |
|---|---|---|---|
| 1 | ✓ `python app.py` | **31/31** | `secret_key` no `/health`, `senha` em `/usuarios` → nenhum |
| 2 | ✓ `npm start` | **7/7** | cartão e chave do gateway no log → só os 4 últimos dígitos |
| 3 | ✓ `python seed.py && python app.py` | **36/36** | hash `password` em 5 respostas → nenhum |

Logs de boot e das requisições de cada aplicação refatorada: [docs/evidencias/apps-rodando/](docs/evidencias/apps-rodando/). Exemplo (projeto 2):

```text
WARN PAYMENT_GATEWAY_KEY não definida: usando gateway de pagamento simulado
INFO LMS API rodando na porta 3100
INFO Cobrança simulada: cartão final 4444, valor 497, status PAID
INFO Checkout concluído: curso 2, matrícula 2
```

Mudanças intencionais de contrato, todas de segurança e listadas pela própria skill no resumo da Fase 3:
- `/admin/*` (projeto 1), relatório financeiro e `DELETE /api/users/:id` (projeto 2) e `DELETE /users/:id` (projeto 3) passaram a exigir `ADMIN_TOKEN`: respondem 401/403 sem ele e o status original com ele.
- Senha, hash e segredos saíram das respostas.
- Entradas malformadas que antes derrubavam a aplicação com 500 agora recebem 400.

### Checklist de validação

| Item | P1 | P2 | P3 | Evidência |
|---|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✓ | ✓ | ✓ | `skill-runs/pN-fase1-2.md` |
| Framework detectado corretamente | ✓ Flask 3.1.1 | ✓ Express 4.22.1 (resolvido do lockfile) | ✓ Flask 3.0.0 | idem |
| Domínio descrito corretamente | ✓ e-commerce | ✓ LMS com checkout | ✓ Task Manager | idem |
| Nº de arquivos condiz com a realidade | ✓ 4 | ✓ 3 | ✓ 15 | `find` no commit original |
| **Fase 2** — Relatório segue o template | ✓ | ✓ | ✓ | `make check` |
| Cada finding tem arquivo e linhas exatos | ✓ | ✓ | ✓ | `make citations` (58/58) |
| Ordenados CRITICAL → LOW | ✓ | ✓ | ✓ | `make check` |
| Mínimo de 5 findings | ✓ 21 | ✓ 18 | ✓ 19 | `make check` |
| APIs deprecated (se aplicável) | ✓ verificado, nenhuma | ✓ verificado, nenhuma | ✓ 2 APIs | seção "Deprecated APIs" |
| Pausa e pede confirmação antes da Fase 3 | ✓ | ✓ | ✓ | etapa 1 só leitura + `git status` limpo |
| **Fase 3** — Estrutura segue MVC | ✓ | ✓ | ✓ | árvores acima |
| Config extraída (sem hardcoded) | ✓ `src/config/settings.py` | ✓ `src/config/index.js` | ✓ `config/settings.py` | `.env.example` em cada projeto |
| Models abstraem dados | ✓ | ✓ | ✓ | `models/` |
| Views/Routes separadas | ✓ `src/views/` | ✓ `src/routes/` | ✓ `routes/` | |
| Controllers concentram o fluxo | ✓ | ✓ | ✓ | `controllers/` |
| Error handling centralizado | ✓ `middlewares/error_handler.py` | ✓ `middlewares/errorHandler.js` | ✓ `middlewares/error_handler.py` | |
| Entry point claro | ✓ `app.py` → `create_app()` | ✓ `src/app.js` (`npm start`) | ✓ `app.py` → `create_app()` | |
| Aplicação inicia sem erros | ✓ | ✓ | ✓ | `apps-rodando/` |
| Endpoints originais respondem | ✓ 31/31 | ✓ 7/7 | ✓ 36/36 | `make contract P=N` |

**Critérios de aceite:** Fase 1 detecta a stack em 3/3 · Fase 2 com ≥ 5 findings em 3/3 · ≥ 1 CRITICAL/HIGH em 3/3 · aplicação funcionando após a Fase 3 em 3/3.

### Como a skill se comportou em stacks diferentes

- **Monolito Python (P1):** criou o MVC do zero e escolheu nomes em português (`produto_model.py`), seguindo o idioma do projeto como manda a guideline. Ela também testou além do contrato: um banco legado com senhas em texto puro migrado no boot, um produto com apóstrofo no nome e uma busca com `UNION`.
- **Node.js (P2):** a mesma skill aplicou as transformações específicas do ecossistema: callbacks viraram `async/await` com o driver promisificado, `asyncHandler` com o middleware de erro como último `app.use`, transação com `BEGIN/COMMIT/ROLLBACK` no checkout e no delete. Ela leu a versão real do Express no `package-lock.json` (4.22.1, não o `^4.18.2` do manifesto).
- **Projeto parcialmente organizado (P3):** a Fase 1 classificou como "parcialmente em camadas" e a Fase 3 **não reescreveu do zero**. Preservou `models/` e `routes/`, criou só as camadas que faltavam e trocou as APIs deprecated pelos equivalentes modernos (`db.session.get`, `utcnow()` com timezone).
- **Custo e tempo** (saídas JSON do Claude Code): Fases 1–2 levaram ~3–4 min e ~US$ 1 por projeto; a Fase 3 levou 6–8 min e ~US$ 3–4 por projeto, incluindo a validação.
- **Observações honestas:**
  - O `CLAUDE.md` do workspace (fora do repositório) foi carregado como contexto nas execuções; um resumo da Fase 3 cita "workspace rules". Ele não contém nada sobre os projetos nem sobre os findings.
  - Os resumos da Fase 3 saíram em inglês em dois projetos (P2 e P3); os relatórios saíram em português.
  - As senhas de demonstração do seed continuam no código dos seeds, gravadas com hash forte, para que os usuários de exemplo sigam logando. A skill justificou isso como resto aceito.

---

## D) Como Executar

### Pré-requisitos

- **Claude Code** instalado e logado (`claude --version`, `claude /login`). Para usar outro LLM, veja "Usando outros LLMs" abaixo.
- Python 3.10+ com `uv` (ou `venv` + `pip`), Node.js 18+ e npm, `make`, `curl`.
- `make setup` prepara os 3 projetos: venvs, dependências e `npm install`.

### Executar a skill em cada projeto

Interativo, como no enunciado:

```bash
cd code-smells-project && claude "/refactor-arch"     # Projeto 1
cd ../ecommerce-api-legacy && claude "/refactor-arch" # Projeto 2 (skill já copiada)
cd ../task-manager-api && claude "/refactor-arch"     # Projeto 3 (skill já copiada)
```

A skill imprime a Fase 1 e o relatório da Fase 2 e para em `Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar. Copie o relatório para `reports/audit-project-N.md`.

Headless, como as evidências deste repositório foram geradas:

```bash
make skill-audit P=1      # Fases 1-2 só com ferramentas de leitura; salva reports/audit-project-1.md
make skill-refactor P=1   # retoma a MESMA sessão respondendo "y" -> Fase 3
make sync-skill P=2       # copia a skill do projeto 1 para o projeto 2 (idem P=3)
```

> Os três projetos deste repositório **já estão refatorados**. Para reexecutar sobre o código legado, use um worktree do commit original (VALIDACAO.md, passo 4.0).

### Como validar que a refatoração funcionou

```bash
make check           # estrutura da skill + 3 relatórios (sem LLM)
make citations       # cada arquivo:linha + Evidence dos relatórios conferido no código original
make contract P=1    # sobe o projeto e compara TODOS os endpoints com o contrato original
make test            # check + citations + contrato dos 3 projetos
make run P=2         # sobe o projeto com o comando documentado (python app.py / npm start)
```

`tools/contract_test.py` é independente da skill. Ele sobe a aplicação com o mesmo comando do README do projeto, faz as chamadas gravadas no código original (31 no projeto 1, 7 no projeto 2, 36 no projeto 3, com casos válidos, 404 e 400) e exige o mesmo status HTTP e as mesmas chaves JSON de topo. Ele também mostra os vazamentos de senha e segredo antes × depois.

### Ordem sugerida

1. Ler a análise manual ([docs/analise-manual.md](docs/analise-manual.md)).
2. `make setup && make test-one`.
3. Executar a skill no projeto 1, revisar o relatório e confirmar.
4. `make contract P=1`.
5. Repetir para os projetos 2 e 3 (`make sync-skill P=2|3` antes).
6. `make test`.

### Usando outros LLMs

A skill é Markdown puro. O mesmo `/refactor-arch` roda no Claude Code com outro modelo, escolhido por execução:

| Comando | LLM |
|---|---|
| `make skill-audit P=1` | Login atual do Claude Code (padrão das evidências) |
| `make skill-audit P=1 PROVIDER=anthropic` | `ANTHROPIC_API_KEY` do `.env`, modelo `ANTHROPIC_LLM_MODEL` |
| `make skill-audit P=1 PROVIDER=aws` | AWS Bedrock (`CLAUDE_CODE_USE_BEDROCK=1`, `AWS_*`) |
| `make skill-audit P=1 PROVIDER=google` | Gemini via gateway LiteLLM em Docker (`ANTHROPIC_BASE_URL` → LiteLLM `/v1/messages` → Gemini) |
| `make skill-audit P=1 PROVIDER=openai` | OpenAI via o mesmo gateway |

Configuração em [.env.example](.env.example) (`make env` cria o `.env`). `make gateway-test` faz uma chamada pelo gateway e confirma o caminho Claude Code API → Gemini.
