# Projeto 2 — ecommerce-api-legacy: Fases 1 e 2 (saída bruta do Claude Code)

Comando: `cd ecommerce-api-legacy && claude -p "/refactor-arch"` (só ferramentas de leitura liberadas)
- Sessão: `eb858141-a4e0-4134-8243-c90e25424de8`
- Turnos: 11 | duração: 189.9 s | custo estimado: US$ 0.97
- Tokens: entrada 18 (+cache 432966), saída 21764
- Status: success | erro: False

---

================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js), versão não declarada (sem `engines`)
Framework:     Express 4.22.1 (`^4.18.2` no package.json, versão resolvida pelo package-lock.json)
Dependencies:  sqlite3 5.1.7 (driver cru com callbacks), sem dotenv, sem auth, sem CORS, sem validação
Domain:        LMS / plataforma de cursos com checkout (usuários, cursos, matrículas, pagamentos, log de auditoria)
Architecture:  Monolítica (God Class): `src/AppManager.js:1-141` cria o banco, define schema e seed, registra as 3 rotas e decide o pagamento na mesma classe
Source files:  3 files analyzed (~180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite `:memory:`, seed no boot em `src/AppManager.js:18-21`)
Entry point:   src/app.js (run: `npm start` → `node src/app.js`, porta 3000)
Endpoints:     3 routes (POST /api/checkout, GET /api/admin/financial-report, DELETE /api/users/:id)
================================

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.22.1
Files:   3 analyzed | ~180 lines of code
Date:    2026-11-15

## Summary
CRITICAL: 6 | HIGH: 4 | MEDIUM: 4 | LOW: 4

| Severity | Findings |
|---|---|
| CRITICAL | F-01, F-02, F-03, F-04, F-05, F-06 |
| HIGH | F-07, F-08, F-09, F-10 |
| MEDIUM | F-11, F-12, F-13, F-14 |
| LOW | F-15, F-16, F-17, F-18 |

## Findings

### F-01 [CRITICAL] God Class / God File (AP-03)
File: src/AppManager.js:1-141
Evidence: `class AppManager {` … `initDb() {` … `setupRoutes(app) {`
Description: uma única classe `AppManager` acumula: conexão com o banco (7), criação de schema e seed (10-23), registro de rotas HTTP (25-138), busca ou criação de usuário com hash de senha (66-72), decisão de aprovação do pagamento (46-48), escrita de matrícula, pagamento e auditoria (50-60) e agregação do relatório financeiro (80-129). Ela importa ao mesmo tempo o driver `sqlite3` (1) e recebe o `app` do Express.
Impact: nenhuma regra pode ser testada sem subir HTTP e o banco. Qualquer mudança no checkout, no relatório ou no schema mexe no mesmo arquivo, e não existem fronteiras para trocar o banco ou o gateway.
Recommendation: separar em config, conexão/schema, models por tabela, serviços (pagamento, hash), controllers e rotas, com um composition root em `app.js` (T-03, T-07).

### F-02 [CRITICAL] Escrita em múltiplas etapas sem transação / integridade referencial (AP-10)
File: src/AppManager.js:12-16, 46-48, 50-60, 69-71, 133-135
Evidence: `this.db.run("INSERT INTO enrollments ...` → `self.db.run("INSERT INTO payments ...` → `self.db.run("INSERT INTO audit_logs ...`
Description: o checkout grava `enrollments` (50), `payments` (54) e `audit_logs` (57) em callbacks separados, sem `BEGIN`/`COMMIT`/`ROLLBACK`. Um usuário novo é inserido (69) antes da checagem do cartão (46-48), então um cartão recusado deixa o usuário criado. O schema (12-16) não tem `FOREIGN KEY`, e `DELETE FROM users` (133) deixa matrículas e pagamentos órfãos, como admite a própria resposta (135). Severidade elevada de HIGH para CRITICAL por ser caminho de dinheiro (matrícula e pagamento).
Impact: uma falha no INSERT de `payments` deixa uma matrícula ativa sem pagamento (aluno matriculado sem pagar) e responde 500. Usuários deletados continuam no relatório como `'Unknown'` com valor pago.
Recommendation: transação explícita no fluxo de checkout (commit/rollback) e chaves estrangeiras com `ON DELETE` no schema, ou exclusão em cascata no model (T-10).

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-06)
File: src/AppManager.js:18, 68-69
File: src/utils.js:17-23
Evidence: `hash += Buffer.from(pwd).toString('base64').substring(0, 2);` / `return hash.substring(0, 10);`
Description: o seed grava a senha `'123'` em texto puro (18). `badCrypto` codifica a senha em Base64, repete os 2 primeiros caracteres 10000 vezes e corta em 10. O resultado (ex.: `"senhaforte"` → `c2c2c2c2c2`) depende só do primeiro caractere e de metade do segundo, é reversível e não tem salt. Quando `pwd` não vem, a senha padrão `"123456"` é usada (68).
Impact: quem lê o banco recupera ou adivinha as senhas na hora, e senhas diferentes que começam com a mesma letra geram o mesmo "hash".
Recommendation: hash forte com salt (`crypto.scrypt` da biblioteca padrão, com salt aleatório e `timingSafeEqual`), seed gravando o hash e sem senha padrão (T-04).

### F-04 [CRITICAL] Exposição de dados sensíveis (AP-05)
File: src/AppManager.js:45
Evidence: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`);`
Description: cada checkout escreve no log o número completo do cartão (`cc`, de `req.body.card`) e a chave de produção do gateway de pagamento (`config.paymentGatewayKey`).
Impact: os números de cartão dos clientes e a chave `pk_live_***` ficam na saída padrão e em qualquer agregador de logs, o que viola PCI-DSS.
Recommendation: nunca registrar o PAN nem segredos; no máximo os 4 últimos dígitos mascarados, via logger configurado (T-04, T-01).

### F-05 [CRITICAL] Endpoint administrativo ou destrutivo sem autenticação (AP-04)
File: src/AppManager.js:80-129, 131-136
Evidence: `app.get('/api/admin/financial-report', (req, res) => {` / `app.delete('/api/users/:id', (req, res) => {`
Description: o relatório financeiro (nome de todos os alunos, valor pago e receita por curso) e a exclusão de qualquer usuário por id não verificam credencial. Não há middleware de autenticação em `src/app.js:6` nem dentro dos handlers.
Impact: qualquer cliente anônimo lê dados financeiros e pessoais e apaga usuários em massa (`DELETE /api/users/1`, `/2`, ...).
Recommendation: middleware de autenticação de administrador com credencial vinda da config, aplicado às duas rotas e respondendo 401/403 sem ela (T-12).

### F-06 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
File: src/utils.js:2-5
Evidence: `dbPass: "senha_super_***"` / `paymentGatewayKey: "pk_live_***"`
Description: o objeto `config` traz literais de usuário e senha de banco (`dbUser`, `dbPass`), a chave de produção do gateway (`paymentGatewayKey`, usada em `src/AppManager.js:45`) e o usuário SMTP (`smtpUser`). A porta (6) também é fixa. Nada vem de `process.env`.
Impact: os segredos de produção ficam no controle de versão, ao alcance de qualquer pessoa com acesso ao repositório. Trocar a chave exige um deploy de código.
Recommendation: módulo de config lendo `process.env`, segredos ausentes desabilitados ou gerados em runtime com aviso, e `.env.example` documentando cada variável (T-01).

### F-07 [HIGH] Acoplamento forte sem injeção de dependência (AP-09)
File: src/app.js:5-10
File: src/AppManager.js:2, 7
Evidence: `this.db = new sqlite3.Database(':memory:');` / `const manager = new AppManager();`
Description: o `AppManager` cria a própria conexão no construtor (7) e importa `config` diretamente de `./utils` (2). O `app` do Express é criado no nível do módulo (5) junto com `listen`, sem factory nem composition root.
Impact: não dá para injetar um banco de teste, um gateway falso ou subir a app sem abrir a porta (testes de integração) sem editar o código.
Recommendation: composition root (`createApp(deps)`) que cria a conexão e os serviços a partir da config e os entrega aos models e controllers; `listen` fica só no entry point (T-08, T-03).

### F-08 [HIGH] Regra de negócio no controller / rota (Fat Controller) (AP-07)
File: src/AppManager.js:28-78, 80-129
Evidence: `let status = cc.startsWith("4") ? "PAID" : "DENIED";`
Description: o handler de `POST /api/checkout` (51 linhas) lê o corpo, consulta o curso, busca ou cria o usuário com hash, decide a aprovação do pagamento (46), grava matrícula, pagamento e auditoria e atualiza o cache. O handler do relatório (50 linhas) agrega a receita (`courseData.revenue += payment.amount`, 108-110) dentro da rota.
Impact: as regras de checkout e de receita só podem ser testadas via HTTP e ficam presas ao formato de callbacks do driver.
Recommendation: controller fino que extrai a entrada e chama um serviço de checkout/relatório que orquestra models e o gateway (T-07, T-03).

### F-09 [HIGH] Validação de entrada ausente, inconsistente ou duplicada (AP-13)
File: src/AppManager.js:29-35, 46, 68, 132
Evidence: `if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");`
Description: a única validação é a de truthiness (35). `card` numérico (ex.: `4111222233334444` sem aspas) passa e quebra em `cc.startsWith` (46) com `TypeError` dentro de um callback do `sqlite3`, fora do alcance do Express. `c_id` e o `:id` da rota (132) não têm tipo checado, `eml` não tem formato validado e `pwd` é opcional, com senha padrão (68). Severidade elevada de MEDIUM para HIGH por ser caminho de dinheiro e porque a exceção não tratada derruba o processo.
Impact: uma única requisição com `card` numérico encerra o servidor e tira do ar todas as rotas (DoS).
Recommendation: validador do payload de checkout (tipos, formato de e-mail, cartão como string de dígitos, `c_id` inteiro) que responde 400, e validação do `:id` (T-13).

### F-10 [HIGH] Estado global mutável (AP-08)
File: src/utils.js:9-10, 12-15, 25
File: src/AppManager.js:2, 59
Evidence: `let globalCache = {};` / `globalCache[key] = data;`
Description: `globalCache` é um objeto de módulo exportado e alterado a cada checkout (`last_checkout_<userId>`, 59), sem limite nem expiração, e nunca é lido. `totalRevenue` é exportado como primitivo (cópia) e importado em `AppManager.js:2`, mas nunca é atualizado.
Impact: o cache cresce sem limite a cada checkout, um vazamento de memória compartilhado entre requisições. `totalRevenue` dá a falsa impressão de um total de receita mantido em memória.
Recommendation: remover o estado global. Se um cache for necessário, que seja um serviço injetado com limite (T-08).

### F-11 [MEDIUM] Callback hell / fluxo assíncrono aninhado (AP-16)
File: src/AppManager.js:26, 37-77, 86-121
Evidence: `const self = this;` … `coursesPending--;` … `enrPending--;`
Description: o checkout encadeia 6 níveis de callbacks (37 → 40 → 69 → 50 → 54 → 57) e usa `self = this` (26) porque `function(err)` é necessária para ler `this.lastID`. O relatório controla o término com contadores manuais (`coursesPending`, `enrPending`: 86, 93, 97, 117, 120) e envia a resposta a partir de 3 pontos (87, 98, 121).
Impact: o fluxo é difícil de ler e de corrigir. A ordem do relatório depende da ordem de chegada dos callbacks, e um erro no meio deixa o contador sem chegar a zero, o que faz a requisição nunca responder.
Recommendation: `async/await` com o driver promisificado (`util.promisify` ou wrapper `run/get/all` que retorna Promise) (T-09).

### F-12 [MEDIUM] Tratamento de erro não centralizado (AP-15)
File: src/AppManager.js:38, 41, 51, 55, 57, 70, 84, 92-93, 104-106, 133-135
File: src/app.js:5-10
Evidence: `if (err || !course) return res.status(404).send("Curso não encontrado");` / `this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {`
Description: cada callback trata `err` à sua maneira. Um erro de banco vira 404 (38), o erro do INSERT de auditoria é ignorado (57), os erros de 92, 104 e 106 são ignorados, e com erro em 92 `enrollments.length` (93) lança `TypeError`. O DELETE ignora `err` e responde 200 mesmo para um id inexistente (133-135). As mensagens 500 são textos soltos (41, 51, 55, 70, 84), e `app.js` não registra middleware de erro.
Impact: falhas de banco ficam mascaradas como "não encontrado" ou como sucesso, e exceções em callbacks derrubam o processo.
Recommendation: handlers `async` que propagam erros para um middleware de erro central (`app.use((err, req, res, next) => ...)`), com log e resposta padronizada (T-05).

### F-13 [MEDIUM] Efeitos colaterais acoplados (AP-18)
File: src/AppManager.js:45-48, 59
Evidence: `let status = cc.startsWith("4") ? "PAID" : "DENIED";`
Description: a cobrança é simulada inline no handler (cartão que começa com `"4"` é aprovado), sem uma porta ou serviço de gateway nem tratamento de falha da integração. O efeito `logAndCache` (59) também é disparado inline.
Impact: trocar o gateway simulado por um real, ou testar o checkout com um gateway falso, exige reescrever o handler.
Recommendation: serviço `PaymentGateway` com método `charge(card, amount)` injetado no serviço de checkout (T-07, seção "serviços de integração").

### F-14 [MEDIUM] Queries N+1 (AP-12)
File: src/AppManager.js:83, 89-92, 102-106
Evidence: `courses.forEach(c => {` … `enrollments.forEach(enr => {` … `this.db.get("SELECT name, email FROM users WHERE id = ?"`
Description: o relatório faz 1 consulta de cursos, 1 consulta de matrículas por curso e 2 consultas (usuário e pagamento) por matrícula: 1 + C + 2·E consultas.
Impact: o número de consultas cresce linearmente com o número de matrículas, e o relatório fica lento conforme a base cresce.
Recommendation: uma consulta com `LEFT JOIN` entre courses, enrollments, users e payments, com a agregação feita no model ou serviço (T-06).

### F-15 [LOW] Logging com `print` / `console.log` (AP-22)
File: src/app.js:13
File: src/utils.js:13
Evidence: `console.log(\`[LOG] Salvando no cache: ${key}\`);`
Description: o log da aplicação usa `console.log` sem nível nem formato. O caso com cartão e chave (`src/AppManager.js:45`) já está em F-04.
Impact: não dá para filtrar nem silenciar os logs por nível.
Recommendation: logger simples com níveis, configurado no composition root (T-05).

### F-16 [LOW] Imports não usados e código morto (AP-21)
File: src/AppManager.js:2, 104
File: src/utils.js:2-3, 5, 9-10, 25
Evidence: `const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');`
Description: `totalRevenue` é importado (2) e nunca usado. `dbUser`, `dbPass` e `smtpUser` nunca são lidos. `globalCache` é escrito, mas nunca lido, e `totalRevenue` nunca é atualizado. A consulta de 104 seleciona `email`, que não é usado.
Impact: ruído que esconde o que de fato é usado e mantém segredos no código sem necessidade.
Recommendation: remover os imports, campos e exports sem uso.

### F-17 [LOW] Nomenclatura ruim (AP-20)
File: src/AppManager.js:4, 29-33, 89
File: src/utils.js:17
Evidence: `let u = req.body.usr; let e = req.body.eml; let p = req.body.pwd;`
Description: a classe tem o nome vago `AppManager`. As variáveis internas são de 1 a 3 letras (`u`, `e`, `p`, `cid`, `cc`, `c`), a função se chama `badCrypto`, e o módulo genérico `utils` mistura config, cache e criptografia.
Impact: o código não comunica intenção e as responsabilidades do `utils` ficam escondidas.
Recommendation: nomes de domínio (`name`, `email`, `password`, `courseId`, `cardNumber`) nos identificadores internos. Os campos do contrato HTTP (`usr`, `eml`, `pwd`, `c_id`, `card`) não são renomeados e ficam documentados.

### F-18 [LOW] Magic numbers e strings (AP-19)
File: src/AppManager.js:37, 46, 48, 68, 108
File: src/utils.js:6, 19
Evidence: `cc.startsWith("4") ? "PAID" : "DENIED"` / `port: 3000`
Description: os status de pagamento `"PAID"`/`"DENIED"` se repetem como literais (46, 48, 108). Também são literais o prefixo de cartão aprovado `"4"` (46), `active = 1` (37), a senha padrão `"123456"` (68), a porta `3000` e a iteração `10000`.
Impact: mudar um status ou uma regra exige caçar literais, e um erro de digitação passa sem aviso.
Recommendation: constantes nomeadas (`PaymentStatus.PAID`, `APPROVED_CARD_PREFIX`) e porta vinda da config (T-13).

## Deprecated APIs
Nenhuma encontrada. Verificado: `new Buffer()` (o código usa `Buffer.from` em `src/utils.js:20`), `url.parse()`, `fs.exists()`, `require('body-parser')` / `require('querystring')` (o código usa `express.json()` em `src/app.js:6`), `req.param()`, `res.send(status)`, `res.json(obj, status)`, `app.del()`, `.substr()` (o código usa `.substring`, que não está deprecated) e `var`. A API de callbacks do `sqlite3` 5.1.7 não está marcada como deprecated. O estilo de callbacks sem Promise está registrado em F-11.

## Architecture Notes
- Arquitetura atual: Monolítica (single file / God Class). `AppManager` concentra banco, rotas e regras, e `utils.js` concentra config, cache e criptografia.
- Sem ocorrências: AP-02 (todas as queries usam placeholders `?`), AP-11 (sem modo debug nem CORS), AP-14 e AP-23.
- Estrutura MVC proposta:
  src/
    app.js                  (entry point: carrega config, cria app, listen)
    config/index.js         (env vars, defaults seguros)
    database/connection.js  (abre o SQLite e promisifica run/get/all; transação)
    database/schema.js      (CREATE TABLE com FOREIGN KEY + seed com hash)
    models/                 (user, course, enrollment, payment, auditLog, report)
    services/               (checkoutService, paymentGateway, passwordHasher)
    controllers/            (checkoutController, reportController, userController)
    routes/index.js         (mesmas 3 rotas)
    middlewares/            (adminAuth, errorHandler, validação)
- Contrato a preservar: 3 rotas, comando `npm start` (`node src/app.js`, porta 3000), campos `usr`/`eml`/`pwd`/`c_id`/`card` e mesmos status (200/400/404). Mudança de segurança prevista: `GET /api/admin/financial-report` e `DELETE /api/users/:id` passam a exigir credencial de administrador (401/403 sem ela).

================================
Total: 18 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]