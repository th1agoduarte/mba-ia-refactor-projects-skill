# Catálogo de anti-patterns (Fase 2)

Cada entrada tem: **ID**, severidade padrão, o que é, **sinais de detecção** (buscas que geram candidatos), **como confirmar** (o que precisa ser verdade no trecho lido) e a transformação do playbook (`T-xx`). Os sinais usam `grep -rnE` sobre o código do projeto (aplique as exclusões de escopo do SKILL.md). Adapte a regex à linguagem detectada na Fase 1; a ideia do sinal vale para qualquer stack.

## Escala de severidade

| Severidade | Critério (baseado em MVC e SOLID) |
|---|---|
| **CRITICAL** | Falha grave de arquitetura ou segurança: impede o funcionamento correto, expõe dados sensíveis (credenciais hardcoded, SQL Injection, senha em texto puro) ou viola completamente a separação de responsabilidades (God Class com banco + regra + roteamento) |
| **HIGH** | Violação forte de MVC/SOLID que dificulta muito manutenção e testes: regra de negócio pesada em controller/rota, acoplamento forte sem injeção de dependência, estado global mutável, escrita sem transação |
| **MEDIUM** | Padronização, duplicação, performance moderada: N+1, middleware/tratamento de erro inadequado, validação ausente ou duplicada, APIs deprecated |
| **LOW** | Legibilidade: nomes ruins, magic numbers, imports não usados, logs com `print`, condicionais verbosas |

**Ajuste de severidade:** suba um nível quando o problema estiver num caminho de dinheiro, autenticação ou dados pessoais; desça um nível quando o código afetado for só script de desenvolvimento (seed, fixtures). Registre o ajuste na descrição.

## Índice

| ID | Anti-pattern | Severidade |
|---|---|---|
| AP-01 | Credenciais e segredos hardcoded | CRITICAL |
| AP-02 | SQL Injection (SQL montado com concatenação/interpolação) | CRITICAL |
| AP-03 | God Class / God File | CRITICAL |
| AP-04 | Endpoint administrativo ou destrutivo sem autenticação | CRITICAL |
| AP-05 | Exposição de dados sensíveis (senha, hash, segredo, cartão) | CRITICAL |
| AP-06 | Armazenamento inseguro de senha (texto puro, encoding, hash fraco) | CRITICAL / HIGH |
| AP-07 | Regra de negócio no controller / rota (Fat Controller) | HIGH |
| AP-08 | Estado global mutável | HIGH |
| AP-09 | Acoplamento forte sem injeção de dependência | HIGH |
| AP-10 | Escrita em múltiplas etapas sem transação / integridade referencial | HIGH |
| AP-11 | Modo debug / configuração insegura de runtime | HIGH |
| AP-12 | Queries N+1 | MEDIUM |
| AP-13 | Validação de entrada ausente, inconsistente ou duplicada | MEDIUM |
| AP-14 | Duplicação de código (serialização, regras repetidas) | MEDIUM |
| AP-15 | Tratamento de erro não centralizado / `except` genérico / vazamento de erro | MEDIUM |
| AP-16 | Callback hell / fluxo assíncrono aninhado | MEDIUM |
| AP-17 | Uso de APIs deprecated | MEDIUM |
| AP-18 | Efeitos colaterais acoplados (e-mail, SMS, pagamento inline) | MEDIUM |
| AP-19 | Magic numbers e strings | LOW |
| AP-20 | Nomenclatura ruim | LOW |
| AP-21 | Imports não usados e código morto | LOW |
| AP-22 | Logging com `print`/`console.log` | LOW |
| AP-23 | Condicionais verbosas / aninhamento desnecessário | LOW |

---

## CRITICAL

### AP-01 — Credenciais e segredos hardcoded
Segredo literal no código: `SECRET_KEY`, senha de banco/SMTP, chave de gateway de pagamento, token de API.
- **Sinais:**
  ```bash
  grep -rnEi "(secret|passw(or)?d|pass|pwd|senha|token|api[_-]?key|private[_-]?key|gateway[_-]?key|smtp)[\"']?\s*[:=]\s*[\"'][^\"']{3,}[\"']" .
  grep -rnE "(sk|pk)_(live|test)_[A-Za-z0-9]+|AKIA[0-9A-Z]{16}" .
  ```
- **Confirmar:** o valor é literal (não `os.environ`, `process.env`, `getenv`), não é placeholder vazio e não está só em `.env.example`. Valores repetidos em mais de um arquivo (ex.: a mesma chave na config e numa resposta HTTP) entram no mesmo finding com todas as linhas.
- **Playbook:** T-01.

### AP-02 — SQL Injection
SQL montado com concatenação, f-string, `%`, `.format` ou template string contendo dados de entrada.
- **Sinais:**
  ```bash
  grep -rnE "(execute|query|run|get|all|exec|raw)\(\s*[\"'\`].*(SELECT|INSERT|UPDATE|DELETE)[^\"'\`]*[\"'\`]\s*\+" .
  grep -rnE "(SELECT|INSERT|UPDATE|DELETE)[^\"']*[\"']\s*\+|f[\"'](SELECT|INSERT|UPDATE|DELETE)|\\\$\{.*\}.*(WHERE|VALUES)" .
  grep -rnE "query \+?= .*[\"'].*\+|LIKE '%\" \+" .
  ```
- **Confirmar:** algum valor concatenado vem (direta ou indiretamente) de request, parâmetro de rota ou argumento de função pública. `str(id)` vindo de rota tipada `<int:id>` ainda conta (o padrão é inseguro e se repete em rotas não tipadas).
- **Playbook:** T-02.

### AP-03 — God Class / God File
Uma unidade (arquivo, classe, módulo) concentra responsabilidades de camadas diferentes: conexão/schema/seed do banco, SQL, regra de negócio, validação, roteamento HTTP, integração externa.
- **Sinais:** arquivos com mais de ~250 linhas ou mais de ~15 funções/métodos; uma classe com métodos `initDb`/`setupRoutes`/`process*`; um arquivo que importa ao mesmo tempo o framework HTTP e o driver de banco; um módulo de "models" com funções de domínios diferentes (produto, usuário, pedido, relatório).
  ```bash
  wc -l <arquivos> | sort -n | tail
  grep -cE "^(def |\s+def |function |\s+\w+\(.*\)\s*\{)" <arquivo>
  ```
- **Confirmar:** liste pelo menos 3 responsabilidades distintas com as linhas onde cada uma aparece.
- **Playbook:** T-03, T-07.

### AP-04 — Endpoint administrativo ou destrutivo sem autenticação
Rotas que executam SQL arbitrário, apagam o banco, deletam usuários ou expõem relatórios financeiros/administrativos sem verificar credencial.
- **Sinais:**
  ```bash
  grep -rnE "(admin|reset|drop|truncate|query|delete|financial|report)" <arquivos de rotas>
  grep -rnE "cursor\.execute\(\s*(query|sql|dados|data|req)" .
  ```
- **Confirmar:** a rota não tem decorator/middleware de auth nem checagem de papel. Execução de SQL vindo do corpo da requisição é sempre CRITICAL.
- **Playbook:** T-12.

### AP-05 — Exposição de dados sensíveis
Senha, hash de senha, segredo de configuração, número de cartão ou dados internos (path do banco, flag de debug) aparecendo em respostas HTTP ou logs.
- **Sinais:**
  ```bash
  grep -rnE "[\"'](senha|password|pass|secret_key|db_path|debug)[\"']\s*:" .
  grep -rnE "(print|console\.log|logger\.\w+)\(.*(card|cartao|cc|senha|password|pwd|token|key)" .
  ```
- **Confirmar:** o dado chega ao cliente (serialização usada por uma rota, ex.: `to_dict()` com senha) ou ao log.
- **Playbook:** T-04, T-01.

### AP-06 — Armazenamento inseguro de senha
- **CRITICAL:** senha salva em texto puro, com encoding reversível (Base64) ou "hash caseiro".
- **HIGH:** hash rápido sem salt (MD5, SHA-1, SHA-256 simples).
- **Sinais:**
  ```bash
  grep -rnE "md5|sha1\(|hashlib\.(md5|sha1|sha256)|createHash\(['\"](md5|sha1)|base64|btoa\(" .
  grep -rnE "INSERT INTO \w*(user|usuario)\w*.*(senha|pass)" .
  grep -rnE "(senha|password|pass)\s*=\s*['\"]" .   # comparação direta em login
  ```
- **Confirmar:** como a senha é gravada e como o login compara (comparação direta de texto = texto puro).
- **Playbook:** T-04.

---

## HIGH

### AP-07 — Regra de negócio no controller / rota (Fat Controller)
Handlers HTTP que calculam preço/desconto/total, controlam estoque, processam pagamento, agregam relatórios, disparam notificações ou fazem várias consultas encadeadas.
- **Sinais:** handlers com mais de ~30 linhas; cálculos (`*`, `total +=`, `desconto`, `revenue`), consultas ao ORM/SQL e laços dentro da função de rota; decisão de aprovação de pagamento tomada dentro da rota.
  ```bash
  grep -rnE "\.query\.|execute\(|db\.(all|get|run)\(" <arquivos de rotas/controllers>
  ```
- **Confirmar:** a regra não depende de HTTP e poderia ser testada sem o framework.
- **Playbook:** T-07, T-03.

### AP-08 — Estado global mutável
Variáveis de módulo modificadas em runtime (`global x`, `let cache = {}` exportado, contadores, conexão única global, listas em memória num serviço singleton).
- **Sinais:**
  ```bash
  grep -rnE "^\s*global |^(let|var) \w+\s*=\s*(\{\}|\[\]|0|null)|module\.exports\s*=\s*\{[^}]*(cache|total|state)" .
  grep -rnE "^\w+\s*=\s*None$|^db_connection|_instance\s*=" --include=*.py .
  ```
- **Confirmar:** o valor é alterado depois do carregamento do módulo e é compartilhado entre requisições.
- **Playbook:** T-08.

### AP-09 — Acoplamento forte sem injeção de dependência
Camadas instanciam ou importam diretamente suas dependências concretas (`get_db()` chamado em todo lugar, `new sqlite3.Database` dentro da classe de domínio, serviço de e-mail criado dentro da regra). Também conta a ausência de factory/composition root (`create_app`).
- **Sinais:**
  ```bash
  grep -rnE "from database import|require\(['\"]\./(database|db)|get_db\(\)|new \w+Database\(" .
  grep -rnE "^app\s*=\s*Flask\(|^const app = express\(\)" .
  ```
- **Confirmar:** não há como trocar a dependência (ex.: banco de teste) sem editar o código.
- **Playbook:** T-08, T-03.

### AP-10 — Escrita em múltiplas etapas sem transação / integridade referencial
Fluxos que inserem/atualizam várias tabelas sem transação (pedido + itens + estoque; matrícula + pagamento) ou deletes que deixam registros órfãos.
- **Sinais:** várias chamadas de escrita na mesma função antes de um único `commit`, retornos antecipados no meio do fluxo, `DELETE` em tabela pai sem tratar filhas, ausência de `FOREIGN KEY`/`ON DELETE`, checagem de estoque separada da baixa (race condition).
- **Confirmar:** uma falha no meio deixa o banco inconsistente.
- **Playbook:** T-10.

### AP-11 — Modo debug / configuração insegura de runtime
`debug=True` fixo (o debugger interativo do Werkzeug permite execução remota de código), bind em `0.0.0.0` com debug, CORS liberado para `*` sem necessidade, ambiente "produção" declarado com debug ligado.
- **Sinais:**
  ```bash
  grep -rnE "debug\s*=\s*True|DEBUG[\"']?\]?\s*=\s*True|app\.run\(.*debug|CORS\(app\)|origin:\s*['\"]\*" .
  ```
- **Playbook:** T-01.

---

## MEDIUM

### AP-12 — Queries N+1
Consulta dentro de laço sobre o resultado de outra consulta, inclusive lazy loading de relacionamento ORM dentro de laço.
- **Sinais:**
  ```bash
  grep -rnE -A6 "for .* in .*(fetchall|\.all\(\)|rows|tasks|users)|\.forEach\(|for \(const" . | grep -E "execute|query|\.get\(|db\.(get|all)|\.filter_by|len\(\w+\.\w+\)"
  ```
  Também: várias consultas `COUNT(*)` iguais mudando só o filtro (ex.: uma por status) em vez de um `GROUP BY`.
- **Confirmar:** o número de consultas cresce com o número de registros.
- **Playbook:** T-06.

### AP-13 — Validação de entrada ausente, inconsistente ou duplicada
Rotas que leem o corpo sem validar tipo/obrigatoriedade (ex.: `.get()` sobre corpo `None` causando 500; comparação numérica com valor que chega como string), regras de validação copiadas entre create/update, listas de valores válidos repetidas.
- **Sinais:**
  ```bash
  grep -rnE "request\.get_json\(\)|req\.body\.|request\.args\.get" .
  grep -rnE "not in \[['\"]|\.includes\(['\"]|len\(\w+\) [<>]" .
  ```
- **Playbook:** T-13.

### AP-14 — Duplicação de código
Blocos repetidos: montagem manual de dicionários de resposta para a mesma entidade, cálculo de "atrasado" repetido em várias rotas, laços de pedidos com itens copiados, helpers existentes ignorados.
- **Sinais:** o mesmo bloco de 5+ linhas em dois lugares; `to_dict()` existente ignorado e reescrito na rota.
  ```bash
  grep -rnE "\[['\"](id|nome|title|name)['\"]\]\s*=|['\"](id|nome|title|name)['\"]:\s*\w+\[" .
  ```
- **Playbook:** T-14.

### AP-15 — Tratamento de erro não centralizado
`try/except Exception` (ou `except:` nu) em cada handler, erros engolidos sem log, `str(e)` devolvido ao cliente, callbacks que ignoram `err`, ausência de error handler/middleware global.
- **Sinais:**
  ```bash
  grep -rnE "except:\s*$|except Exception( as \w+)?:|jsonify\(\{[\"']erro?r?[\"']:\s*str\(e\)|\(err(, \w+)?\) => \{\s*$" .
  grep -rnE "errorhandler|app\.use\(\(err" .   # ausência indica falta de handler central
  ```
- **Playbook:** T-05.

### AP-16 — Callback hell / fluxo assíncrono aninhado
Callbacks aninhados em 3+ níveis, contadores manuais para saber quando terminar (`pending--`), `self = this` para escapar do escopo, respostas enviadas em vários pontos.
- **Sinais:**
  ```bash
  grep -rnE "function\s*\(err|\(err, \w+\) =>|Pending--|const self = this" --include=*.{js,ts} .
  ```
- **Playbook:** T-09.

### AP-17 — Uso de APIs deprecated
Uso de APIs marcadas como obsoletas pela linguagem, framework ou biblioteca. Sempre registre o equivalente moderno. **Verificação obrigatória** em toda auditoria: se nada for encontrado, escreva "nenhuma encontrada" com os itens verificados.

| Ecossistema | Deprecated | Equivalente moderno |
|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` |
| Python ≥ 3.12 | adaptadores padrão de data do `sqlite3` | converter explicitamente / `detect_types` com adaptador registrado |
| SQLAlchemy 2.x / Flask-SQLAlchemy 3.x | `Model.query.get(id)` (legacy Query API) | `db.session.get(Model, id)` |
| SQLAlchemy 2.x | `Model.query.filter_by(...).all()` em código novo | `db.session.execute(db.select(Model).filter_by(...)).scalars().all()` |
| Flask ≥ 2.3 | `app.before_first_request`, `flask.json.JSONEncoder`, `FLASK_ENV` | código no `create_app()`, `app.json` provider, `FLASK_DEBUG` |
| Werkzeug | `safe_str_cmp` | `hmac.compare_digest` |
| Node.js | `new Buffer()`, `url.parse()`, `fs.exists()`, `require('querystring')` | `Buffer.from()`, `new URL()`, `fs.existsSync/fs.promises.access`, `URLSearchParams` |
| Express 4 → 5 | `body-parser` separado, `req.param()`, `res.send(status)`, `res.json(obj, status)`, `app.del()` | `express.json()`, `req.params/req.query`, `res.sendStatus()`, `res.status().json()`, `app.delete()` |
| Express (padrão) | callbacks de driver sem Promise | `async/await` com driver promisificado (`util.promisify`) |
| JS | `var`, `arguments`, `substr()` | `const/let`, rest params, `slice()` |

- **Sinais:**
  ```bash
  grep -rnE "utcnow\(|utcfromtimestamp\(|\.query\.get\(|before_first_request|JSONEncoder|safe_str_cmp" --include=*.py .
  grep -rnE "new Buffer\(|url\.parse\(|fs\.exists\(|require\(['\"](body-parser|querystring)['\"]\)|req\.param\(|\.substr\(|\bvar " --include=*.{js,ts} .
  ```
- **Confirmar:** a versão instalada (lockfile/pin) já marca a API como deprecated.
- **Playbook:** T-11.

### AP-18 — Efeitos colaterais acoplados
Envio de e-mail/SMS/push, cobrança ou chamadas externas feitos inline no handler ou na regra de negócio, muitas vezes simulados com `print`, sem abstração (porta/serviço) nem tratamento de falha.
- **Sinais:**
  ```bash
  grep -rnEi "(enviando|sending|send_?email|sms|push|notif|smtplib|nodemailer|charge|payment)" .
  ```
- **Playbook:** T-07 (seção "serviços de integração").

---

## LOW

### AP-19 — Magic numbers e strings
Literais com significado de negócio espalhados: faixas de desconto (`10000`, `0.1`), limites (`200`, `4`), status (`'pendente'`, `'PAID'`), prioridades, portas, cores padrão.
- **Sinais:**
  ```bash
  grep -rnE "[<>]=?\s*[0-9]{2,}|\*\s*0\.[0-9]+|==\s*['\"][a-z_]+['\"]|port\s*[:=]\s*[0-9]{4}" .
  ```
- **Playbook:** T-13 (constantes nomeadas).

### AP-20 — Nomenclatura ruim
Identificadores de uma letra ou abreviações opacas fora de laços curtos (`u`, `e`, `x`, `tmp`, `data2`), nomes vagos ou enganosos (`Manager`, `Helper`, `utils` genérico, `doStuff`, funções cujo nome contradiz o que fazem), campos de contrato crípticos (abreviações de 2–3 letras).
- **Sinais:**
  ```bash
  grep -rnE "\b(let|const|var)\s+[a-z]{1,2}\s*=|^\s*[a-z]{1,2}\s*=\s*" .
  ```
- **Observação:** campos do contrato HTTP público não são renomeados na Fase 3 (quebraria clientes). Renomeie só os identificadores internos e documente o contrato.

### AP-21 — Imports não usados e código morto
- **Sinais:**
  ```bash
  grep -rnE "^import |^from \w+ import|require\(" <arquivo>   # depois confirme o uso de cada nome no arquivo
  ```
- **Confirmar:** o nome importado não aparece em nenhum outro lugar do arquivo. Métodos nunca chamados também contam.

### AP-22 — Logging com `print` / `console.log`
`print`/`console.log` como mecanismo de log de aplicação (sem nível, sem formato, impossível silenciar), muitas vezes com dados pessoais.
- **Sinais:** `grep -rnE "^\s*print\(|console\.(log|error)\(" .`
- **Playbook:** T-05 (logger configurado no composition root).

### AP-23 — Condicionais verbosas / aninhamento desnecessário
`if cond: return True else: return False`, `if` aninhados que poderiam ser uma expressão, comparações repetidas.
- **Sinais:**
  ```bash
  grep -rnE -A3 "if .*:\s*$" --include=*.py . | grep -E "return (True|False)"
  ```
- **Playbook:** T-13.
