================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0
Files:   15 analyzed | ~1158 lines of code
Date:    2026-11-15

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 5 | LOW: 5

| Severity | Findings |
|---|---|
| CRITICAL | F-01, F-02, F-03, F-04 |
| HIGH | F-05, F-06, F-07, F-08, F-09 |
| MEDIUM | F-10, F-11, F-12, F-13, F-14 |
| LOW | F-15, F-16, F-17, F-18, F-19 |

## Findings

### F-01 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
File: app.py:13
      services/notification_service.py:7-10
Evidence: `app.config['SECRET_KEY'] = 'super-secret-***'` / `self.email_password = 'senha***'`
Description: A `SECRET_KEY` do Flask está fixa no código. O `NotificationService` também traz literais para o host SMTP, o usuário `taskmanager@gmail.com` e a senha do e-mail. Nada é lido do ambiente, mesmo com `python-dotenv` em `requirements.txt`.
Impact: Quem lê o repositório consegue forjar cookies e sessões assinadas e entrar na conta SMTP. Para trocar um segredo é preciso editar o código e fazer deploy.
Recommendation: Criar um módulo `config/settings.py` que lê `SECRET_KEY` e `SMTP_*` de `os.environ`. Sem `SECRET_KEY`, gerar uma chave aleatória em runtime e registrar um aviso no log. Documentar as variáveis em `.env.example` (T-01).

### F-02 [CRITICAL] Exposição de dados sensíveis (AP-05)
File: models/user.py:21
      routes/user_routes.py:33, 85, 129, 209
Evidence: `'password': self.password,`
Description: `User.to_dict()` serializa o hash da senha. Ele é usado em GET `/users/<id>` (linha 33), POST `/users` (85), PUT `/users/<id>` (129) e POST `/login` (209), então o hash vai para o cliente em todas essas respostas.
Impact: Qualquer cliente obtém o hash MD5 da senha de qualquer usuário (somado a F-03, a senha original sai por rainbow table). É dado de autenticação.
Recommendation: Tirar `password` da serialização pública de `to_dict()` (T-04).

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-06)
File: models/user.py:29, 32
Evidence: `self.password = hashlib.md5(pwd.encode()).hexdigest()`
Description: As senhas são gravadas com MD5 sem salt, e `check_password` compara com `==`. Pelo catálogo seria HIGH; subiu para CRITICAL porque fica no caminho de autenticação e o hash é exposto pela API (F-02).
Impact: MD5 sem salt cai por rainbow table ou força bruta em segundos. A senha do seed `1234` é recuperada na hora. A comparação com `==` também não é em tempo constante.
Recommendation: Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (pbkdf2/scrypt com salt, já incluídos no Flask). O seed passa a gravar o hash, mantendo as mesmas senhas (T-04).

### F-04 [CRITICAL] Endpoint administrativo ou destrutivo sem autenticação (AP-04)
File: routes/user_routes.py:52, 71-72, 119-122, 134-151, 210
Evidence: `role = data.get('role', 'user')` / `'token': 'fake-jwt-token-' + str(user.id)`
Description: DELETE `/users/<id>` apaga o usuário e todas as tasks dele (140-145) sem nenhuma credencial. POST `/users` e PUT `/users/<id>` aceitam `role: "admin"` de qualquer chamador. O "token" do login é `fake-jwt-token-<id>`, previsível e nunca verificado.
Impact: Um anônimo consegue se promover a admin ou apagar qualquer usuário junto com as tarefas dele.
Recommendation: Proteger com credencial de administrador vinda da config (`ADMIN_TOKEN`, header `Authorization: Bearer`) a remoção de usuários e a atribuição de papel diferente de `user`. Sem credencial, responder 401/403 (T-12).

### F-05 [HIGH] Acoplamento forte sem injeção de dependência (AP-09)
File: app.py:9-31
      seed.py:2
Evidence: `app = Flask(__name__)` / `from app import app, db`
Description: A aplicação nasce como variável de módulo, com URI do banco, segredo e blueprints fixos em `app.py:11-20`. `db.create_all()` roda como efeito colateral do import (30-31), e o `seed.py` importa esse objeto global. Não existe `create_app()`.
Impact: Não há como subir a app com outro banco (por exemplo, de teste) ou outra config sem editar o código. Importar `app` já cria tabelas.
Recommendation: Criar uma application factory `create_app(config)` como composition root (config, `db.init_app`, blueprints, error handlers). O `seed.py` passa a usar `create_app()` (T-08, T-03).

### F-06 [HIGH] Modo debug / configuração insegura de runtime (AP-11)
File: app.py:15, 34
Evidence: `app.run(debug=True, host='0.0.0.0', port=5000)` / `CORS(app)`
Description: O debug fica sempre ligado com bind em todas as interfaces, e o CORS é liberado para qualquer origem.
Impact: O debugger interativo do Werkzeug permite execução remota de código por qualquer host da rede. Com o CORS aberto, qualquer site chama a API.
Recommendation: Ler `FLASK_DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` da config, com debug desligado e host `127.0.0.1` por padrão (T-01).

### F-07 [HIGH] Regra de negócio na rota (Fat Controller) (AP-07)
File: routes/report_routes.py:12-101, 103-155
Evidence: `for t in all_tasks: if t.due_date: if t.due_date < datetime.utcnow(): ...`
Description: `summary_report` (90 linhas) e `user_report` calculam contagens por status e prioridade, atrasos, dias de atraso, atividade dos últimos 7 dias e produtividade por usuário dentro do handler HTTP. Tudo isso é regra de negócio pura.
Impact: Os relatórios só podem ser testados via HTTP, e as mesmas regras se repetem em outras rotas (F-11).
Recommendation: Mover as agregações para `controllers/report_controller.py`, apoiadas em métodos de consulta nos models, e deixar a rota só extraindo parâmetros e serializando (T-07).

### F-08 [HIGH] Regra de negócio na rota (Fat Controller) (AP-07)
File: routes/task_routes.py:85-154, 156-223, 273-299
Evidence: `if status not in ['pending', 'in_progress', 'done', 'cancelled']:`
Description: `create_task` (70 linhas) e `update_task` (68 linhas) validam campos, checam a existência de usuário e categoria, convertem datas e tags e fazem commit no handler. `task_stats` calcula atrasos e taxa de conclusão na rota.
Impact: O fluxo de criação e edição não pode ser reutilizado nem testado sem Flask, e as regras divergem entre create e update (F-13).
Recommendation: Criar `controllers/task_controller.py` com os casos de uso (`create`, `update`, `delete`, `search`, `stats`) lançando erros de domínio, e deixar as rotas finas (T-07, T-03).

### F-09 [HIGH] Regra de negócio na rota (Fat Controller) (AP-07)
File: routes/user_routes.py:42-90, 92-132, 185-211
Evidence: `existing = User.query.filter_by(email=email).first()`
Description: `create_user`, `update_user` e `login` concentram no handler a validação de e-mail, senha e papel, a unicidade de e-mail, a checagem de usuário ativo e a persistência.
Impact: A regra de cadastro e autenticação fica presa à camada HTTP e duplicada entre create e update.
Recommendation: Criar `controllers/user_controller.py` (cadastro, edição, remoção, autenticação) e deixar as rotas finas (T-07).

### F-10 [MEDIUM] Uso de APIs deprecated (AP-17)
File: models/category.py:11
      models/task.py:15-16, 52
      models/user.py:14
      routes/report_routes.py:35, 42, 45, 71, 105, 133, 192, 213
      routes/task_routes.py:31, 42, 51, 67, 72, 117, 122, 158, 188, 195, 215, 227, 285
      routes/user_routes.py:29, 94, 136, 155, 172
      services/notification_service.py:35
      utils/helpers.py:38
      seed.py:66-67, 69-70, 74
Evidence: `user = User.query.get(user_id)` / `default=datetime.utcnow`
Description: `datetime.utcnow()` está deprecated desde o Python 3.12. `Model.query.get()` é Legacy Query API no SQLAlchemy 2.x (Flask-SQLAlchemy 3.1.1 exige SQLAlchemy ≥ 2.0.16) e emite `LegacyAPIWarning`.
Impact: Gera warnings em runtime, e as APIs serão removidas em versões futuras.
Recommendation: Trocar por `db.session.get(Model, id)` e por um helper único `utcnow()` baseado em `datetime.now(timezone.utc)`. Como o banco guarda datetimes naive, o helper remove o tzinfo para manter as comparações (T-11).

### F-11 [MEDIUM] Duplicação de código (AP-14)
File: models/task.py:50-60
      routes/report_routes.py:34-36, 67, 132-135, 151
      routes/task_routes.py:17-39, 71-80, 284-287, 296
      routes/user_routes.py:162-180
Evidence: `if t.status != 'done' and t.status != 'cancelled': task_data['overdue'] = True`
Description: O cálculo de "atrasada" foi copiado 6 vezes nas rotas, e `Task.is_overdue()` existe mas nunca é chamado. `get_tasks` reescreve campo a campo o `Task.to_dict()` (17-28). A taxa de conclusão aparece 3 vezes, enquanto `calculate_percentage` é importado e não é usado.
Impact: Uma mudança na regra (por exemplo, um novo status final) precisa ser feita em 7 lugares, com risco de divergência.
Recommendation: Ter uma única fonte para `Task.is_overdue()`, `to_dict()` com opções (`include_overdue`, `include_relations`) e um helper de percentual (T-14).

### F-12 [MEDIUM] Queries N+1 (AP-12)
File: routes/report_routes.py:19-28, 53-56, 159-163
      routes/task_routes.py:41-57, 275-279
      routes/user_routes.py:22
Evidence: `user = User.query.get(t.user_id)` (dentro de `for t in tasks`)
Description: GET `/tasks` faz 2 consultas por task (usuário e categoria). GET `/users` dispara lazy load de `u.tasks` por usuário. `summary_report` consulta tasks por usuário, e `/categories` faz um `COUNT` por categoria. Os contadores por status e prioridade são 4 a 9 `COUNT`s separados em vez de um `GROUP BY`.
Impact: O número de queries cresce linearmente com tasks, usuários e categorias, e a latência acompanha.
Recommendation: Usar `joinedload`/`selectinload` nos relacionamentos e agregações `GROUP BY` (`func.count`) encapsuladas nos models (T-06).

### F-13 [MEDIUM] Validação de entrada ausente, inconsistente ou duplicada (AP-13)
File: routes/report_routes.py:180, 196-202
      routes/task_routes.py:96-100, 110-114, 166-184, 261, 264
      routes/user_routes.py:61-72, 102-125
      utils/helpers.py:57-108
Evidence: `if priority < 1 or priority > 5:` / `data = request.get_json()` seguido de `if 'name' in data:`
Description: `priority` enviado como string (`"2"`) gera `TypeError` (500) em create e update. `?priority=abc` e `?user_id=abc` em `/tasks/search` geram `ValueError` (500). PUT `/categories/<id>` não checa corpo `None`. `color` não é validada (`is_valid_color` existe e não é usada), e `name`/`active` de usuário são aceitos sem validação. As listas de status e papéis, o regex de e-mail e os limites de título e senha estão copiados entre create e update, e `process_task_data` em `utils/helpers.py` duplica tudo isso sem ser usado.
Impact: Entradas inválidas viram 500 em vez de 400, e as regras divergem (o update de título não faz `strip`, o create aceita só `YYYY-MM-DD`).
Recommendation: Centralizar a validação em funções/validadores únicos usados pelos controllers, com constantes da config, e devolver 400 com a mesma mensagem (T-13).

### F-14 [MEDIUM] Tratamento de erro não centralizado (AP-15)
File: routes/report_routes.py:186, 207, 221
      routes/task_routes.py:62-63, 137, 151-154, 204, 221-223, 236
      routes/user_routes.py:87-90, 130, 149
      services/notification_service.py:23-25
      utils/helpers.py:46, 49, 88
Evidence: `except:` / `return jsonify({'error': 'Erro interno'}), 500`
Description: Há 16 blocos `except:` nus ou `except Exception` espalhados pelos handlers, e `get_tasks` engole qualquer erro sem log. Não existe `@app.errorhandler`, então erros não capturados (F-13) caem na página HTML 500 padrão do Flask.
Impact: Falhas reais ficam invisíveis, o formato de erro é inconsistente (JSON ou HTML) e os handlers ficam cheios de boilerplate.
Recommendation: Criar exceções de domínio (`NotFoundError`, `ValidationError`, `ConflictError`, `UnauthorizedError`) e um `middlewares/error_handler.py` que as converte em JSON, com rollback e log no handler genérico (T-05).

### F-15 [LOW] Imports não usados e código morto (AP-21)
File: app.py:7
      models/task.py:3, 38-48
      models/user.py:34-38
      routes/report_routes.py:7-8
      routes/task_routes.py:7
      routes/user_routes.py:6
      services/notification_service.py:4-48
      utils/helpers.py:3-7, 9-108
      requirements.txt:4-6
Evidence: `import os, sys, json, datetime` / `import json, os, sys, time`
Description: Os imports `os`, `sys`, `json`, `time`, `hashlib`, `math`, `format_date` e `calculate_percentage` não são usados. `Task.validate_status`, `Task.validate_priority`, `User.is_admin`, toda a classe `NotificationService` e todas as funções de `utils/helpers.py` nunca são chamadas. `marshmallow`, `requests` e `python-dotenv` são declarados e nunca importados.
Impact: Ruído de leitura, falsa impressão de que existe validação e notificação, e dependências instaladas à toa.
Recommendation: Remover os imports e o código morto, aproveitar o que for útil (validações) na camada certa e enxugar o `requirements.txt` (T-13, T-14).

### F-16 [LOW] Magic numbers e strings (AP-19)
File: app.py:34
      routes/report_routes.py:19-28, 45, 129, 180
      routes/task_routes.py:96-114, 167-184
      routes/user_routes.py:64, 71, 115, 120
      utils/helpers.py:110-116
Evidence: `if len(title) < 3:` / `seven_days_ago = datetime.utcnow() - timedelta(days=7)`
Description: Status (`'pending'`, `'done'`...), faixa de prioridade 1–5, limites de título 3/200, senha mínima 4, janela de 7 dias, "alta prioridade" `<= 2`, cor `'#000000'` e porta 5000 aparecem como literais. As constantes de `utils/helpers.py:110-116` existem mas não são usadas.
Impact: Mudar uma regra exige caçar literais pelo código.
Recommendation: Definir constantes nomeadas em `config/settings.py` e usá-las nos validadores e controllers (T-13).

### F-17 [LOW] Nomenclatura ruim (AP-20)
File: models/category.py:14
      models/task.py:45
      routes/report_routes.py:10, 24-28, 157-223
Evidence: `report_bp = Blueprint('reports', __name__)` (que também registra `/categories`)
Description: O CRUD de categorias mora no blueprint e no arquivo de relatórios, e o nome do módulo engana sobre o conteúdo. Há também variáveis opacas: `p1`–`p5`, `d`, `p`, `cat`, `u`, `t`.
Impact: Fica difícil localizar o código de categorias e ler as agregações.
Recommendation: Separar as categorias em `routes/category_routes.py` + `controllers/category_controller.py` e usar nomes descritivos internamente. Os paths e campos do contrato não mudam (T-03).

### F-18 [LOW] Condicionais verbosas / aninhamento desnecessário (AP-23)
File: models/task.py:38-60
      models/user.py:34-38
      routes/task_routes.py:30-39, 71-80
      routes/user_routes.py:171-180
      utils/helpers.py:19-23, 52-55
Evidence: `if self.role == 'admin': return True else: return False`
Description: Há `if/else` retornando booleanos e `is_overdue` com 4 níveis de aninhamento, onde caberia uma única expressão.
Impact: Leitura mais lenta e mais superfície para erro.
Recommendation: Reescrever como expressões booleanas diretas (`return self.role == ROLE_ADMIN`) (T-13).

### F-19 [LOW] Logging com print (AP-22)
File: routes/task_routes.py:149, 153, 219, 234
      routes/user_routes.py:83, 89, 147
      services/notification_service.py:21, 24
      utils/helpers.py:39, 41
Evidence: `print(f"Usuário criado: {user.id} - {user.name}")`
Description: A aplicação registra eventos e erros com `print`, sem nível nem formato, e inclui dado pessoal (nome do usuário). Os `print` de `seed.py:93-96` são saída normal de um script de CLI e não entram no finding.
Impact: Não dá para filtrar, silenciar ou direcionar o log, e há dado pessoal no stdout.
Recommendation: Usar o `logging` configurado no composition root (`logger = logging.getLogger(__name__)`) e não registrar PII (T-05).

## Deprecated APIs
| Local | API deprecated | Substituto moderno |
|---|---|---|
| models/task.py:15-16, 52; models/user.py:14; models/category.py:11 | `datetime.utcnow` (default de coluna e comparação) | helper `utcnow()` com `datetime.now(timezone.utc)` (naive UTC para o SQLite) |
| routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; routes/report_routes.py:35, 42, 45, 71, 133; services/notification_service.py:35; utils/helpers.py:38; seed.py:66-67, 69-70, 74 | `datetime.utcnow()` | mesmo helper `utcnow()` |
| routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155; routes/report_routes.py:105, 192, 213 | `Model.query.get(id)` (SQLAlchemy 2.x Legacy Query API) | `db.session.get(Model, id)` |

Verificado também, sem ocorrências: `utcfromtimestamp`, `before_first_request`, `JSONEncoder`, `safe_str_cmp`, `FLASK_ENV`.

## Architecture Notes
- Arquitetura atual: Parcialmente em camadas. Há pastas `models/`, `routes/`, `services/`, `utils/`, mas a regra de negócio está nas rotas, o service tem segredos e não é usado, `utils/` está morto, e não há config, factory nem error handler central. Não há SQL Injection (AP-02): o ORM parametriza todas as consultas, inclusive o `LIKE` de `/tasks/search`.
- Estrutura MVC proposta:
  ```
  app.py                      # composition root: create_app() + app.run (comando `python app.py` preservado)
  seed.py                     # usa create_app(); grava hash forte
  config/settings.py          # env vars + constantes de domínio
  database.py                 # db = SQLAlchemy()
  models/{task,user,category}.py           # entidades, is_overdue, hash, to_dict sem senha, consultas agregadas
  controllers/{task,user,category,report}_controller.py
  routes/{task,user,category,report}_routes.py   # blueprints finos (views)
  middlewares/{error_handler,auth}.py
  services/notification_service.py         # config injetada, logging
  ```
- Contrato a preservar: 22 rotas, comando `python seed.py && python app.py` (porta 5000)

================================
Total: 19 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
