# Análise Manual

Feita lendo o código original (commit `6d1ce62` do repositório base) **antes** de executar a skill. As linhas se referem ao código legado (`git show upstream/main:<arquivo>`). Severidade pela escala do enunciado.

## Projeto 1 — code-smells-project (Python/Flask, API de E-commerce)

| # | Sev. | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| M1-01 | CRITICAL | SQL Injection em praticamente todas as queries (concatenação de strings) | `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 149-150, 174, 279-281, 289-297` | `POST /login` com `' OR '1'='1' --` no e-mail autentica sem senha; a busca permite ler ou apagar qualquer tabela |
| M1-02 | CRITICAL | Endpoints administrativos sem autenticação: SQL arbitrário e reset do banco | `app.py:47-78` | Qualquer cliente executa `DROP TABLE` ou apaga todos os dados com um POST |
| M1-03 | CRITICAL | Segredos hardcoded e expostos em resposta HTTP | `app.py:7`; `controllers.py:285-289` (`/health` devolve `secret_key`, `db_path`, `debug`) | A chave de sessão vaza para qualquer um que chame o health check |
| M1-04 | CRITICAL | Senhas em texto puro e devolvidas pela API | `database.py:75-79` (seed), `models.py:126-129` (insert), `models.py:83, 99` (`GET /usuarios` retorna `senha`) | Vazamento direto de credenciais de todos os usuários |
| M1-05 | CRITICAL | Nenhuma separação de camadas: `models.py` mistura 4 domínios, SQL, regra de desconto e formatação; `controllers.py` faz validação, notificação e acesso ao banco; `app.py` roteia e executa SQL | `models.py:1-314`, `controllers.py:1-292`, `app.py:11-78` | Impossível testar ou alterar um domínio sem afetar os outros |
| M1-06 | HIGH | `debug=True` fixo com bind em `0.0.0.0` | `app.py:8, 88` | O debugger do Werkzeug permite execução remota de código |
| M1-07 | HIGH | Conexão SQLite global e mutável compartilhada entre threads (`check_same_thread=False`) | `database.py:4-10` | Estado global, sem injeção de dependência; concorrência insegura |
| M1-08 | HIGH | Criação de pedido sem transação: estoque checado num laço e baixado em outro, sem lock nem `WHERE estoque >= ?` | `models.py:133-169` | Pedidos concorrentes deixam estoque negativo |
| M1-09 | MEDIUM | N+1: para cada pedido busca os itens e, para cada item, o produto (código duplicado em duas funções) | `models.py:171-201`, `203-233` | O número de queries cresce com pedidos × itens |
| M1-10 | MEDIUM | Tratamento de erro repetido em todo handler devolvendo `str(e)` ao cliente; `login` e `atualizar_status_pedido` quebram com corpo vazio (500) | `controllers.py:10-12, 21-22, ...`, `169-170`, `239-240` | Vaza detalhes internos e não há handler central |
| M1-11 | MEDIUM | Duplicação: mapeamento row → dict copiado; validação de produto duplicada em criar/atualizar | `models.py:12-21, 31-40, 304-313`; `controllers.py:28-50` × `72-90` | Regras divergem com o tempo (o update não valida categoria nem tamanho do nome) |
| M1-12 | MEDIUM | Relatório faz 5 `COUNT`/`SUM` separados em vez de uma agregação | `models.py:239-254` | Queries desnecessárias |
| M1-13 | LOW | Magic numbers e listas soltas: faixas de desconto, categorias e status válidos | `models.py:257-262`; `controllers.py:52, 242` | Regra de negócio escondida em literais |
| M1-14 | LOW | `print` como log, inclusive de e-mails de usuários | `controllers.py:8, 57, 161, 179, 182, 208-210`; `app.py:56, 83-86` | Sem nível nem formato; dados pessoais no log |
| M1-15 | LOW | Imports não usados e nomes que sombreiam builtins | `models.py:2` (`sqlite3`), `database.py:2` (`os`); `controllers.py:56, 160` (`id`) | Ruído e risco de bug |

## Projeto 2 — ecommerce-api-legacy (Node.js/Express, LMS com checkout)

| # | Sev. | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| M2-01 | CRITICAL | Credenciais de produção hardcoded (senha do banco, chave `pk_live` do gateway de pagamento, usuário SMTP) | `src/utils.js:1-7` | Quem tem acesso ao código tem acesso ao gateway de pagamento |
| M2-02 | CRITICAL | Número completo do cartão e chave do gateway impressos no log | `src/AppManager.js:45` | Viola PCI-DSS; o log vira um vazamento de dados de cartão |
| M2-03 | CRITICAL | "Criptografia" de senha é Base64 truncado (`badCrypto`); seed com senha em texto puro; senha padrão `123456` quando `pwd` não vem | `src/utils.js:17-23`; `src/AppManager.js:18, 68` | Reversível e com colisões: senhas diferentes geram o mesmo "hash" |
| M2-04 | CRITICAL | God Class: `AppManager` cria o banco, faz o seed, registra rotas, processa pagamento e monta relatório | `src/AppManager.js:4-139` | Nenhuma camada testável isoladamente |
| M2-05 | CRITICAL | Endpoints administrativos sem autenticação: relatório financeiro e exclusão de usuários | `src/AppManager.js:80, 131` | Qualquer cliente lê o faturamento e apaga usuários |
| M2-06 | HIGH | Checkout sem transação: matrícula, pagamento e auditoria em inserts encadeados; regra de aprovação (`cc.startsWith("4")`) dentro da rota | `src/AppManager.js:43-63` | Falha no meio deixa matrícula sem pagamento; regra de negócio presa no handler |
| M2-07 | HIGH | `DELETE /api/users/:id` deixa matrículas e pagamentos órfãos e ignora o erro | `src/AppManager.js:131-136` | Integridade referencial quebrada (a própria resposta admite) |
| M2-08 | HIGH | Estado global mutável exportado (`globalCache`, `totalRevenue`) | `src/utils.js:9-10, 12-15` | Cache sem dono, compartilhado entre requisições; `totalRevenue` exportado como primitivo nunca é atualizado |
| M2-09 | MEDIUM | Callback hell (5 níveis) e contadores manuais para saber quando responder | `src/AppManager.js:37-77, 83-128` | Ilegível, propenso a resposta dupla ou nenhuma resposta |
| M2-10 | MEDIUM | N+1 no relatório financeiro: por curso → matrículas → usuário + pagamento | `src/AppManager.js:92-125` | 1 + C + 2·M queries |
| M2-11 | MEDIUM | Erros de callback ignorados e sem tratamento central (respostas em texto solto) | `src/AppManager.js:57, 92, 104, 106, 133` | Erros silenciosos e respostas inconsistentes |
| M2-12 | LOW | Nomes opacos: `u`, `e`, `p`, `cid`, `cc`, `self = this`, `badCrypto`, `AppManager` | `src/AppManager.js:26, 29-33` | Leitura difícil |
| M2-13 | LOW | Magic strings/números: `"PAID"`, `"DENIED"`, `10000` iterações, porta `3000` | `src/AppManager.js:46`; `src/utils.js:19, 6` | Regras escondidas em literais |
| M2-14 | LOW | Código morto e `console.log` como log: `dbUser`, `dbPass`, `smtpUser` e `totalRevenue` nunca usados | `src/utils.js:2-5, 10`; `src/AppManager.js:2` | Ruído e falsa impressão de uso |

## Projeto 3 — task-manager-api (Python/Flask, Task Manager parcialmente em camadas)

| # | Sev. | Problema | Onde | Por que é relevante |
|---|---|---|---|---|
| M3-01 | CRITICAL | Segredos hardcoded: `SECRET_KEY` e senha SMTP | `app.py:13`; `services/notification_service.py:7-10` | Credenciais no repositório |
| M3-02 | CRITICAL | Hash da senha devolvido pela API (`to_dict` inclui `password`) em `POST/GET/PUT /users` e no login | `models/user.py:16-24`; `routes/user_routes.py:85, 129, 209` | Expõe o hash de todos os usuários |
| M3-03 | HIGH | Senha com MD5 sem salt | `models/user.py:27-31` | Quebrável por rainbow table em segundos |
| M3-04 | HIGH | Regra de negócio, validação e serialização dentro das rotas (não existe camada de controller); relatórios agregados na rota | `routes/task_routes.py:11-154`; `routes/report_routes.py:12-100` | "Parcialmente organizado" só na aparência: rotas gordas e impossíveis de testar |
| M3-05 | HIGH | Token de login falso e previsível (`fake-jwt-token-<id>`), nenhuma rota exige autenticação | `routes/user_routes.py:207-211` | Qualquer cliente apaga usuários e tasks |
| M3-06 | HIGH | `debug=True` com `host='0.0.0.0'` | `app.py:34` | Debugger remoto (execução de código) |
| M3-07 | MEDIUM | N+1: `User.query.get`/`Category.query.get` por task; `len(u.tasks)` por usuário; uma query por usuário no relatório; `count` por categoria | `routes/task_routes.py:41-57`; `routes/user_routes.py:22`; `routes/report_routes.py:55-56, 163` | Escala linearmente com os dados |
| M3-08 | MEDIUM | Duplicação: cálculo de "atrasada" repetido 6× apesar de `Task.is_overdue()` (`models/task.py:50-60`); serialização manual apesar de `to_dict()`; `utils.process_task_data` e constantes de `helpers.py` nunca usados | `routes/task_routes.py:30-39, 71-80, 283-287`; `routes/user_routes.py:171-180`; `routes/report_routes.py:34-43, 132-135`; `utils/helpers.py:57-116` | Regras divergem; código morto |
| M3-09 | MEDIUM | APIs deprecated: `Model.query.get()` (legado no SQLAlchemy 2.x) e `datetime.utcnow()` (deprecated no Python 3.12+) | `routes/*.py` (ex.: `task_routes.py:42, 51, 67`); `models/*.py` (ex.: `task.py:15-16`) | Gera `DeprecationWarning`; quebra em versões futuras |
| M3-10 | MEDIUM | `except:` nu engolindo erros; validação frágil (`priority` string → `TypeError` 500; `PUT /categories` sem checar corpo) | `routes/task_routes.py:62, 137, 204, 236`; `routes/user_routes.py:130, 149`; `utils/helpers.py:46, 49, 88`; `routes/task_routes.py:113`; `routes/report_routes.py:196` | Erros silenciosos e 500 onde deveria ser 400 |
| M3-11 | MEDIUM | Rotas de categoria dentro de `report_routes.py`; 9 `COUNT` separados no resumo | `routes/report_routes.py:157-223`; `15-28` | Baixa coesão e queries redundantes |
| M3-12 | LOW | Imports não usados | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `utils/helpers.py:2-7`; `models/task.py:3` | Ruído |
| M3-13 | LOW | Magic numbers/strings: status, faixa de prioridade 1–5, senha mínima 4 repetidos nas rotas | `routes/task_routes.py:110, 113`; `routes/user_routes.py:64, 71` | Constantes já existem em `utils/helpers.py:110-116` e são ignoradas |
| M3-14 | LOW | Condicionais verbosas (`if x: return True else: return False`, `if` aninhados) | `models/task.py:38-60`; `models/user.py:34-38` | Legibilidade |
| M3-15 | LOW | `print` como log; `NotificationService` guarda notificações numa lista em memória e nunca é usado | `routes/*.py`; `services/notification_service.py:6, 43-48` | Estado em memória e código morto |
