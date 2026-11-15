# Projeto 1 — code-smells-project: Fases 1 e 2 (saída bruta do Claude Code)

Comando: `cd code-smells-project && claude -p "/refactor-arch"` (só ferramentas de leitura liberadas)
- Sessão: `5fe1884a-5af4-424d-877d-c3fba71bcc4b`
- Turnos: 13 | duração: 201.4 s | custo estimado: US$ 1.09
- Tokens: entrada 16 (+cache 401446), saída 23116
- Status: success | erro: False

---

================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (versão não declarada)
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib, driver cru, sem ORM)
Domain:        E-commerce / loja virtual (produtos, usuários, pedidos, itens de pedido, relatório de vendas)
Architecture:  Monolítica em arquivos planos — 4 arquivos na raiz divididos por tipo, sem fronteiras reais: app.py:47-78 executa SQL nas rotas, controllers.py:264-274 faz SQL, models.py:256-262 guarda regra de desconto e database.py:4-10 mantém conexão global
Source files:  4 files analyzed (~780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido (SQLite em arquivo `loja.db`, criado e com seed em database.py:7-86)
Entry point:   app.py (run: python app.py, porta 5000)
Endpoints:     19 routes (GET /, GET|POST /produtos, GET /produtos/busca, GET|PUT|DELETE /produtos/<id>, GET|POST /usuarios, GET /usuarios/<id>, POST /login, GET|POST /pedidos, GET /pedidos/usuario/<id>, PUT /pedidos/<id>/status, GET /relatorios/vendas, GET /health, POST /admin/reset-db, POST /admin/query)
================================

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-11-15

## Summary
CRITICAL: 7 | HIGH: 4 | MEDIUM: 7 | LOW: 3

| Severity | Findings |
|---|---|
| CRITICAL | F-01, F-02, F-03, F-04, F-05, F-06, F-07 |
| HIGH | F-08, F-09, F-10, F-11 |
| MEDIUM | F-12, F-13, F-14, F-15, F-16, F-17, F-18 |
| LOW | F-19, F-20, F-21 |

## Findings

### F-01 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
File: app.py:7
File: controllers.py:289
Evidence: `app.config["SECRET_KEY"] = "minha-chave-***"`
Description: a `SECRET_KEY` do Flask é um literal no código, e o mesmo valor aparece de novo, literal, na resposta de `health_check`.
Impact: qualquer pessoa com acesso ao código (ou ao `/health`) consegue forjar sessões e cookies assinados. Trocar a chave exige editar e reimplantar o código.
Recommendation: ler `SECRET_KEY` do ambiente num módulo de config, gerar valor aleatório em runtime com aviso no log quando ausente e documentar em `.env.example` (T-01).

### F-02 [CRITICAL] Endpoint administrativo ou destrutivo sem autenticação (AP-04)
File: app.py:47-57, 59-78
Evidence: `@app.route("/admin/query", methods=["POST"])` … `cursor.execute(query)`
Description: `reset_database` apaga as 4 tabelas, e `executar_query` executa qualquer SQL vindo de `dados.get("sql")` e faz commit. Nenhuma das duas rotas checa credencial ou papel.
Impact: um único POST anônimo apaga o banco inteiro ou lê/altera qualquer tabela (ex.: `SELECT * FROM usuarios` devolve todas as senhas).
Recommendation: manter as rotas, mas exigir credencial de administrador vinda da config por middleware de auth (401/403 sem ela) e tirar o SQL da rota (T-12).

### F-03 [CRITICAL] Exposição de dados sensíveis (AP-05)
File: controllers.py:285-289
File: models.py:83, 99
Evidence: `"db_path": "loja.db", "debug": True, "secret_key": "minha-chave-***"` / `"senha": row["senha"],`
Description: `GET /health` devolve `secret_key`, `db_path`, `debug` e `"ambiente": "producao"`. `get_todos_usuarios` e `get_usuario_por_id` serializam a coluna `senha`, que sai em `GET /usuarios` e `GET /usuarios/<id>`.
Impact: qualquer cliente obtém a chave de assinatura e a senha de todos os usuários (em texto puro, ver F-04).
Recommendation: serialização pública sem `senha` (`to_dict` sem campos sensíveis) e remoção dos campos de config da resposta do health (T-04, T-01).

### F-04 [CRITICAL] Armazenamento inseguro de senha (AP-06)
File: database.py:75-83
File: models.py:109-111, 126-129
Evidence: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`
Description: o seed grava `admin123`, `123456` e `senha123` em texto puro. `criar_usuario` insere a senha recebida sem hash, e `login_usuario` compara a senha em texto puro dentro do SQL.
Impact: qualquer vazamento do banco (ou do `/admin/query`, ou do `GET /usuarios`) entrega as credenciais reais de todos os usuários.
Recommendation: hash forte com salt (ex.: `werkzeug.security.generate_password_hash`/`check_password_hash`), seed gravando o hash e login verificando o hash no model (T-04).

### F-05 [CRITICAL] God Class / God File (AP-03)
File: models.py:1-314
File: controllers.py:1-292
File: app.py:6-78
Description: `models.py` tem 15 funções de 4 domínios: produtos (4-70), usuários e autenticação (72-131), pedidos com controle de estoque (133-233), relatório com política de desconto (235-273) e busca (285-314). `controllers.py` tem 16 handlers de 5 domínios, mais acesso direto ao banco em `health_check` (264-274). `app.py` junta config (7-9), roteamento (11-30) e handlers com SQL cru (47-78).
Impact: qualquer mudança mexe em arquivos que tudo importa. Não dá para testar um domínio isolado, e regra de negócio, SQL e HTTP ficam misturados.
Recommendation: quebrar por domínio em `models/`, `controllers/` e `views/`, com config e composition root separados (T-03, T-07).

### F-06 [CRITICAL] SQL Injection (AP-02)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-299
Evidence: `query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"`
Description: todas as funções de escrita e de busca por id montam SQL concatenando valores do corpo, da query string ou da rota: `nome`, `descricao`, `categoria`, `email`, `senha`, `termo`, `novo_status`, `item["produto_id"]`, `item["quantidade"]`.
Impact: `POST /login` com `email = "' OR '1'='1' --"` autentica como o primeiro usuário (Admin) sem senha. `GET /produtos/busca?q=` permite ler outras tabelas via `UNION`. Um produto com apóstrofo no nome quebra o INSERT (500).
Recommendation: consultas parametrizadas (`?`) em todas as queries, com a busca dinâmica montando a lista de parâmetros (T-02).

### F-07 [CRITICAL] Escrita em múltiplas etapas sem transação / integridade referencial (AP-10)
File: models.py:133-169, 65-70
File: database.py:36-53
Evidence: `if produto["estoque"] < item["quantidade"]:` (146) … `"UPDATE produtos SET estoque = estoque - " + ...` (163-166)
Description: `criar_pedido` checa o estoque num laço (139-146) e só baixa depois (163-166), insere `pedidos` (148-151) e `itens_pedido` (157-161) e faz um único `commit` no fim (168), sem `rollback`. Um item sem `quantidade` gera `KeyError` depois do INSERT, e a transação aberta na conexão global é commitada pela próxima requisição. `deletar_produto` apaga produtos que estão em `itens_pedido`, e o schema não tem `FOREIGN KEY`. Severidade elevada de HIGH para CRITICAL por ser caminho de dinheiro (total do pedido e estoque).
Impact: pedidos parciais ou sem itens, estoque negativo sob concorrência (check-then-act) e itens órfãos que aparecem como "Desconhecido".
Recommendation: transação explícita no controller (commit/rollback), baixa condicional de estoque (`UPDATE ... WHERE estoque >= ?`) e chaves estrangeiras no schema (T-10).

### F-08 [HIGH] Acoplamento forte sem injeção de dependência (AP-09)
File: app.py:4, 6, 49, 66, 82
File: controllers.py:3, 266
File: models.py:1, 5, 25, 44, 55, 66, 73, 90, 106, 123, 134, 172, 204, 236, 276, 286
Evidence: `from database import get_db` / `app = Flask(__name__)`
Description: cada função chama `get_db()` direto, que aponta para o `loja.db` fixo. A app é criada no nível do módulo, sem `create_app`.
Impact: não dá para usar um banco de teste nem configurar a app por ambiente sem editar o código. Todo teste precisa do arquivo real.
Recommendation: composition root `create_app()` que cria a conexão a partir da config e a entrega aos models e controllers (T-08, T-03).

### F-09 [HIGH] Modo debug / configuração insegura de runtime (AP-11)
File: app.py:8-9, 88
Evidence: `app.run(host="0.0.0.0", port=5000, debug=True)`
Description: `DEBUG = True` fixo, `debug=True` com bind em `0.0.0.0` e `CORS(app)` liberando qualquer origem.
Impact: o debugger interativo do Werkzeug fica acessível na rede, com execução remota de código em qualquer traceback. Qualquer site pode chamar a API pelo navegador da vítima.
Recommendation: `DEBUG`, `HOST`, `PORT` e origens de CORS vindos da config, com default seguro (debug desligado) (T-01).

### F-10 [HIGH] Regra de negócio no controller / rota (Fat Controller) (AP-07)
File: controllers.py:26-54, 66-90, 188-216, 237-250, 264-274
Evidence: `categorias_validas = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]`
Description: os handlers leem `request`, aplicam regras de domínio (categorias válidas, limites de nome, preço e estoque, transições de status), disparam notificações e, em `health_check`, executam SQL. `atualizar_status_pedido` anuncia "Devolver estoque" no cancelamento, mas não devolve nada, e responde 200 para pedido inexistente.
Impact: as regras só podem ser testadas via HTTP, ficam duplicadas entre create e update, e o fluxo de cancelamento fica inconsistente com o estoque.
Recommendation: controllers recebem dados já extraídos e orquestram models e serviços; as rotas ficam finas; o SQL do health vai para o model (T-07, T-03).

### F-11 [HIGH] Estado global mutável (AP-08)
File: database.py:4-10
Evidence: `global db_connection` … `sqlite3.connect(db_path, check_same_thread=False)`
Description: uma única conexão SQLite global, criada sob demanda e compartilhada entre todas as threads do servidor (`check_same_thread=False`), sem lock.
Impact: as requisições concorrentes dividem a mesma transação. O commit de uma confirma escritas pela metade de outra (ver F-07), e um erro numa requisição contamina as seguintes.
Recommendation: conexão por requisição em `flask.g` com `teardown_appcontext`, criada pelo `create_app` a partir da config (T-08).

### F-12 [MEDIUM] Logging com `print` (AP-22)
File: app.py:56, 83-86
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Evidence: `print("Login falhou: " + email)`
Description: todo o log da aplicação usa `print`, sem nível nem formato. `criar_usuario` e `login` registram o e-mail do usuário. Severidade elevada de LOW para MEDIUM por envolver dados pessoais no caminho de autenticação.
Impact: não dá para filtrar nem silenciar os logs, e e-mails de usuários, inclusive de tentativas de login falhas, vazam para a saída padrão.
Recommendation: `logging` configurado no composition root, com níveis e sem dados pessoais (T-05).

### F-13 [MEDIUM] Validação de entrada ausente, inconsistente ou duplicada (AP-13)
File: app.py:61-62
File: controllers.py:28-50, 72-90, 119-121, 169-171, 195-201, 239-242
Evidence: `dados = request.get_json()` / `email = dados.get("email", "")`
Description: `login`, `atualizar_status_pedido` e `/admin/query` chamam `.get` sobre um corpo que pode ser `None`. `preco < 0` com string gera `TypeError`, e `float(preco_min)` inválido gera `ValueError`. Os itens do pedido não são validados (`produto_id`, `quantidade`). As validações de create (28-54) são copiadas no update (72-90), mas o update ignora o tamanho do nome e a categoria.
Impact: entradas inválidas viram 500 em vez de 400, e um produto atualizado pode ficar com categoria inválida ou nome vazio.
Recommendation: um validador único por entidade, reutilizado em create e update, que levanta `ValidationError` (400), com listas de valores válidos em constantes (T-13).

### F-14 [MEDIUM] Tratamento de erro não centralizado (AP-15)
File: app.py:77-78
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Evidence: `except Exception as e: return jsonify({"erro": str(e)}), 500`
Description: 17 blocos `except Exception` repetidos devolvem `str(e)` ao cliente. Não existe `errorhandler` registrado.
Impact: mensagens internas (SQL, nomes de colunas, tipos) vazam para o cliente, erros de validação viram 500, e não há log com stack trace.
Recommendation: exceções de domínio e um error handler central registrado no `create_app` (T-05).

### F-15 [MEDIUM] Efeitos colaterais acoplados (AP-18)
File: controllers.py:208-210, 247-250
Evidence: `print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + ...)`
Description: o envio de e-mail, SMS e push na criação do pedido e as notificações de mudança de status são simulados inline no handler, sem abstração nem tratamento de falha.
Impact: trocar por um provedor real exige mexer no controller, e uma falha no envio derrubaria a requisição depois do pedido já gravado.
Recommendation: `services/notification_service.py` atrás de uma interface, injetado no controller (T-07).

### F-16 [MEDIUM] Duplicação de código (AP-14)
File: models.py:12-21, 31-40, 304-313, 79-86, 95-102, 171-201, 203-233
Evidence: `"nome": row["nome"],` (bloco de 8 campos repetido 3x)
Description: a serialização de produto aparece 3 vezes e a de usuário 2 vezes. `get_pedidos_usuario` e `get_todos_pedidos` são cópias quase idênticas de 30 linhas, que só diferem no `WHERE`.
Impact: mudar um campo exige editar vários lugares. Foi assim que a `senha` vazou nas duas serializações de usuário (F-03).
Recommendation: uma função de serialização (`to_dict`) por entidade e uma única consulta de pedidos com filtro opcional (T-14).

### F-17 [MEDIUM] Queries N+1 (AP-12)
File: models.py:186-199, 218-231, 239-254
Evidence: `cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))`
Description: para cada pedido, uma query de itens. Para cada item, uma query do nome do produto. `relatorio_vendas` faz 5 queries separadas (COUNT e SUM, mais um COUNT por status).
Impact: o número de queries cresce com pedidos × itens, e `GET /pedidos` fica linear em consultas conforme a base cresce.
Recommendation: `JOIN` entre `itens_pedido` e `produtos`, carregando os itens de todos os pedidos numa consulta, e `GROUP BY status` no relatório (T-06).

### F-18 [MEDIUM] Magic numbers e strings (AP-19)
File: models.py:257-262, 150, 247-253
File: controllers.py:49, 52, 242
File: app.py:88
Evidence: `if faturamento > 10000: desconto = faturamento * 0.1`
Description: as faixas de desconto (`10000`/`0.1`, `5000`/`0.05`, `1000`/`0.02`), os status (`'pendente'`, `'aprovado'`, `'cancelado'`), o limite de nome `200`, a lista de categorias e a porta `5000` estão espalhados como literais. Severidade elevada de LOW para MEDIUM porque as faixas de desconto estão no caminho de dinheiro.
Impact: mudar a política de desconto ou incluir um status exige caçar literais em vários arquivos, com risco de divergência.
Recommendation: constantes nomeadas no módulo de config (faixas de desconto, status válidos, categorias, limites) (T-13).

### F-19 [LOW] Nomenclatura ruim (AP-20)
File: controllers.py:14, 56, 64, 98, 136, 160
File: models.py:24, 54, 65, 89, 187, 191, 193, 219, 223, 225
Evidence: `def buscar_produto(id):` / `cursor3 = db.cursor()`
Description: `id` sobrescreve o builtin como parâmetro e como variável local, e `cursor2`, `cursor3` e `prod` são nomes sem significado.
Impact: a leitura fica mais difícil e o builtin `id` fica sombreado.
Recommendation: renomear para `produto_id`, `usuario_id`, `itens_cursor` etc., sem tocar nos campos do contrato JSON (T-13).

### F-20 [LOW] Condicionais verbosas / aninhamento desnecessário (AP-23)
File: controllers.py:17-20, 139-142, 177-183, 200
Evidence: `if not itens or len(itens) == 0:`
Description: há `if ...: return ... else: return ...` com `else` desnecessário depois do `return`, e checagem redundante de lista vazia (`not itens` já cobre `len == 0`).
Impact: código mais longo que o necessário.
Recommendation: guard clauses com retorno antecipado e uma condição única (T-13).

### F-21 [LOW] Imports não usados e código morto (AP-21)
File: database.py:2
File: models.py:2, 63, 70, 283
Evidence: `import os` / `import sqlite3` / `return True`
Description: `os` (database.py) e `sqlite3` (models.py) são importados e nunca usados. `atualizar_produto`, `deletar_produto` e `atualizar_status_pedido` sempre retornam `True`, e nenhum chamador usa o valor.
Impact: ruído, e um falso sinal de que a operação pode falhar silenciosamente.
Recommendation: remover os imports e os retornos sem uso. A falha passa a ser sinalizada por exceção (T-05).

## Deprecated APIs
Nenhuma encontrada. Verificado: `datetime.utcnow()`/`utcfromtimestamp()` (não usados), adaptadores padrão de data do `sqlite3` (não usados; `criado_em` vem de `CURRENT_TIMESTAMP` no SQL e não há `detect_types`), `Model.query.get` (sem SQLAlchemy), `before_first_request`, `flask.json.JSONEncoder`, `FLASK_ENV`, `safe_str_cmp` (ausentes). APIs usadas do Flask 3.1.1 (`Flask`, `jsonify`, `request`, `add_url_rule`, `route`) e do flask-cors 5.0.1 (`CORS`) estão vigentes.

## Architecture Notes
- Arquitetura atual: Monolítica em arquivos planos (app.py, controllers.py, models.py, database.py na raiz, com SQL em rotas e controllers, regra de desconto no model e conexão global)
- Estrutura MVC proposta:
  ```
  app.py                      # launcher fino (python app.py)
  .env.example
  src/app.py                  # create_app(): config, db, blueprints, error handlers
  src/config/settings.py      # env vars + constantes de domínio
  src/database.py             # conexão por request (g), schema, seed com hash
  src/models/{produto,usuario,pedido,relatorio}_model.py
  src/controllers/{produto,usuario,pedido,relatorio,health,admin}_controller.py
  src/views/{produto,usuario,pedido,relatorio,health,admin}_routes.py
  src/middlewares/{error_handler,auth}.py
  src/services/notification_service.py
  ```
- Contrato a preservar: 19 rotas, comando `python app.py` (porta 5000)

================================
Total: 21 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````