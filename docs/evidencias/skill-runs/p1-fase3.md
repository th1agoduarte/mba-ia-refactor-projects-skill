# Projeto 1 — code-smells-project: Fase 3 (saída bruta do Claude Code)

Comando: `claude -p --resume 5fe1884a-5af4-424d-877d-c3fba71bcc4b "y"` (resposta à pergunta da Fase 2)
- Sessão: `5fe1884a-5af4-424d-877d-c3fba71bcc4b`
- Turnos: 48 | duração: 470.2 s | custo estimado: US$ 3.58
- Tokens: entrada 46 (+cache 3328951), saída 51903
- Status: success | erro: False

---

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
```
code-smells-project/
├── app.py                          # launcher fino: create_app() + app.run(HOST, PORT, DEBUG) — mesmo `python app.py`
├── .env.example                    # todas as variáveis documentadas (nenhuma obrigatória)
├── README.md                       # como rodar, configuração, estrutura
├── requirements.txt                # inalterado (hash via werkzeug, que já vem com o Flask)
└── src/
    ├── app.py                      # composition root: config, banco, models, controllers, blueprints, error handlers
    ├── errors.py                   # exceções de domínio (Validation/NotFound/Unauthorized/Forbidden/ServiceUnavailable)
    ├── database.py                 # conexão por requisição (flask.g) + read-only, schema com FK, seed com hash, migração de senhas legadas
    ├── config/settings.py          # Settings do ambiente + constantes de domínio (categorias, status, faixas de desconto, limites)
    ├── models/
    │   ├── base_model.py           # provedor de conexão injetado + transacao() (commit/rollback)
    │   ├── produto_model.py        # SQL parametrizado, busca dinâmica, baixa de estoque condicional, produto_to_dict
    │   ├── usuario_model.py        # hash/verificação de senha, serialização sem senha
    │   ├── pedido_model.py         # pedidos + itens em 2 consultas (JOIN), estatísticas com GROUP BY
    │   └── sistema_model.py        # contagens do health, reset transacional, consulta somente leitura
    ├── controllers/
    │   ├── validators.py           # validadores reutilizáveis
    │   ├── produto_controller.py   # validação única para create/update, regras de produto
    │   ├── usuario_controller.py   # cadastro e login
    │   ├── pedido_controller.py    # pedido transacional (confere → grava → baixa estoque) + notificação depois do commit
    │   ├── relatorio_controller.py # política de desconto (FAIXAS_DESCONTO)
    │   └── sistema_controller.py   # índice, health, reset e consulta admin
    ├── views/                      # Blueprints finos: produto, usuario, pedido, relatorio, sistema (_routes.py)
    ├── middlewares/
    │   ├── error_handler.py        # handler central (AppError → JSON, HTTPException passa direto, resto → 500 genérico + log)
    │   └── auth.py                 # @require_admin com X-Admin-Token e hmac.compare_digest
    └── services/notification_service.py  # notificações por e-mail/SMS/push atrás de uma interface (por ora só registram no log)
```
Removidos: `controllers.py`, `models.py`, `database.py` (substituídos por inteiro).

## Changes by Finding
F-01 → `SECRET_KEY` vem do ambiente, com chave efêmera e aviso no log quando ausente; o literal sumiu do código e do `/health` (T-01)
F-02 → `/admin/reset-db` e `/admin/query` exigem `X-Admin-Token`; a query aceita só `SELECT` numa conexão read-only (T-12)
F-03 → `/health` não expõe mais `secret_key`, `db_path` e `debug`; a serialização de usuário não inclui `senha` (T-04, T-01)
F-04 → senhas gravadas com scrypt (werkzeug); o login verifica o hash; o seed grava hash; senhas em texto puro de bancos antigos são migradas no boot (T-04)
F-05 → models, controllers e views separados por domínio, com composition root `create_app()` (T-03, T-07)
F-06 → todas as queries usam placeholders `?`; a busca monta cláusulas e parâmetros em paralelo (T-02)
F-07 → criação de pedido numa transação única com rollback, baixa de estoque condicional (`estoque >= ?`) e FK `itens_pedido.pedido_id ON DELETE CASCADE` em bancos novos (T-10)
F-08 → models recebem o provedor de conexão por injeção; `get_db` só é referenciado no composition root (T-08, T-03)
F-09 → `DEBUG` desligado por padrão, `HOST` padrão `127.0.0.1`, CORS só para `CORS_ORIGINS` configuradas (T-01)
F-10 → regras (validação, categorias, transições de status, desconto) estão nos controllers; as rotas só extraem a entrada e serializam; o SQL do health foi para o model (T-07)
F-11 → conexão global trocada por conexão por requisição em `flask.g` com `teardown_appcontext` (T-08)
F-12 → `print` trocado por `logging` configurado no `create_app`; e-mails não vão mais para o log, só ids (T-05)
F-13 → um validador único para create e update; corpo ausente ou com tipo errado vira 400; listas e limites viram constantes (T-13)
F-14 → os 17 `try/except Exception` foram removidos; error handler central e 500 genérico sem `str(e)` (T-05)
F-15 → notificações via `LogNotificationService` injetado, disparadas depois do commit (T-07)
F-16 → `produto_to_dict`/`usuario_to_dict` únicos e uma só consulta de pedidos com filtro opcional (T-14)
F-17 → pedidos com itens em 2 consultas (`LEFT JOIN`) e relatório com `GROUP BY status` (T-06)
F-18 → faixas de desconto, status, categorias, limites e porta movidos para `config/settings.py` (T-13)
F-19 → `id` virou `produto_id`/`usuario_id`; `cursor2`, `cursor3` e `prod` foram eliminados (T-14)
F-20 → guard clauses e checagem de lista vazia única (T-13)
F-21 → imports `os` e `sqlite3` sem uso removidos, assim como os `return True` mortos; pyflakes limpo (T-14)

## Contract Changes (security)
- `GET /health`: saem `secret_key`, `db_path` e `debug` (o resto igual, `ambiente` vem de `APP_ENV`).
- `GET /usuarios` e `GET /usuarios/<id>`: sai o campo `senha`.
- `POST /login` com payload de SQL injection (`' OR '1'='1' --`): antes 200 logado como Admin, agora 401.
- `POST /admin/reset-db` e `POST /admin/query`: 403 sem `ADMIN_TOKEN` configurado, 401 com token errado, 200 com token válido. `/admin/query` só aceita `SELECT` (escrita → 400).
- Runtime: bind padrão `127.0.0.1` (antes `0.0.0.0`), debug desligado e CORS desligado por padrão. `HOST`, `FLASK_DEBUG` e `CORS_ORIGINS` restauram o comportamento antigo se for preciso.
- Mudanças fora da segurança, só em caminhos que antes davam 500: corpo ausente, preço como string, `preco_min` inválido e item de pedido malformado ou com quantidade negativa agora respondem 400 com mensagem; erros inesperados devolvem `{"erro": "Erro interno do servidor"}` em vez de `str(e)`. O update de produto passou a validar nome e categoria como o create. Com o debug desligado, o JSON sai compacto em vez de indentado.

## Validation
  ✓ Application boots without errors (`.venv/bin/python app.py`; zero tracebacks; zero DeprecationWarning com `-W error::DeprecationWarning`)
  ✓ All endpoints respond correctly (38/42 match baseline; as 4 diferenças são as exceções de segurança acima: login com SQLi e as 3 chamadas admin. Fora as exceções, 37/37 corpos JSON com os mesmos valores, desconsiderando timestamps e campos sensíveis removidos)
  ✓ Zero anti-patterns remaining. Restos justificados:
     - f-strings em `pedido_model.py:29,36`, `produto_model.py:36` e `sistema_model.py:24` só interpolam fragmentos fixos do código (cláusula `WHERE` constante, nomes de tabela de `TABELAS_RESET`); todo valor de entrada vai por `?`.
     - `DEFAULT 'pendente'` no DDL (`database.py:35`) é o default do schema.
     - Comportamentos mantidos de propósito por contrato: `PUT /pedidos/<id>/status` com id inexistente continua 200; pedido com `usuario_id` inexistente continua 201; apagar um produto mantém os itens de pedido históricos, exibidos como "Desconhecido" como antes.
     - Os outros acertos dos greps (AP-12/19/20/23) são falsos positivos: `WHERE id = ?`, `if __name__`, laços sem query.
================================

Além do resumo acima:

- **Testes extras:** um banco legado com senhas em texto puro foi migrado no boot, e `admin123`/`senha123` continuam logando. Os casos que antes davam 500 agora dão 400. Um produto com apóstrofo no nome é criado normalmente, e a busca com `UNION` devolve lista vazia.
- **`loja.db`:** voltou ao arquivo original, que já estava vazio porque alguém tinha chamado `reset-db`. No próximo boot o seed roda de novo, agora com hash. Os `__pycache__` gerados pela validação foram apagados.
- **Evidência:** os scripts e os resultados da linha de base e da validação ficaram fora do projeto, em `/tmp/p1-validate/` (`baseline.txt`, `after.txt`, `after-token.txt` e os corpos das respostas). Se quiser guardar como evidência, copie para `docs/evidencias/` antes de limpar o `/tmp`.
- **Git:** nada foi commitado nem deixado no stage. As remoções de `controllers.py`, `models.py` e `database.py` e os arquivos novos estão só no working tree.