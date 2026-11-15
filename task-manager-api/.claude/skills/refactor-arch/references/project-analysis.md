# Análise de projeto — heurísticas (Fase 1)

Objetivo: descobrir **o que** o projeto é (linguagem, framework, banco, domínio) e **como** está organizado (arquitetura, entry point, rotas), usando evidências do próprio repositório. Toda conclusão precisa de uma evidência: um arquivo, uma linha ou uma dependência.

## 1. Inventário de arquivos

```bash
# arquivos de código (ajuste as extensões ao que existir)
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.mjs" -o -name "*.cjs" \
  -o -name "*.go" -o -name "*.java" -o -name "*.kt" -o -name "*.rb" -o -name "*.php" -o -name "*.cs" \) \
  -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/.git/*" \
  -not -path "*/.claude/*" -not -path "*/__pycache__/*" -not -path "*/dist/*" -not -path "*/build/*" | sort
wc -l <arquivos>   # total de linhas
```

- **Source files** conta só código da aplicação (inclui seeds/scripts do projeto; exclui testes gerados, vendor e configuração pura). Arquivos `__init__.py` vazios contam como arquivo, mas não pesam na análise.
- Registre também os arquivos de apoio: `README*`, `*.http`, `.env*`, `Dockerfile`, `docker-compose*`.

## 2. Linguagem

| Evidência | Linguagem |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, maioria `.py` | Python |
| `package.json` + `.js`/`.mjs`/`.cjs` | JavaScript (Node.js) |
| `package.json` + `tsconfig.json` / `.ts` | TypeScript (Node.js) |
| `go.mod` | Go |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `*.csproj`, `*.sln` | C# (.NET) |

A versão da linguagem só entra se estiver declarada (`python_requires`, `.python-version`, `engines.node`, `go 1.xx`, Dockerfile `FROM python:3.12`).

## 3. Framework e versão

1. Leia o manifesto. A versão vem do pino (`flask==3.1.1`). Se o pino for um range (`^4.18.2`), use o lockfile (`package-lock.json` → `node_modules/express` → `"version"`) e informe a versão resolvida.
2. Confirme pelo uso no código (o import precisa existir):

| Dependência / import | Framework | Sinal no código |
|---|---|---|
| `flask` | Flask | `Flask(__name__)`, `@app.route`, `Blueprint`, `add_url_rule` |
| `django` | Django | `urls.py`, `INSTALLED_APPS`, `models.Model` |
| `fastapi` | FastAPI | `FastAPI()`, `@app.get`, `APIRouter` |
| `express` | Express | `express()`, `app.get/post`, `express.Router()` |
| `@nestjs/core` | NestJS | `@Controller`, `@Module` |
| `koa`, `fastify`, `hapi` | Koa / Fastify / Hapi | `new Koa()`, `fastify()` |
| `spring-boot-starter-web` | Spring Boot | `@RestController`, `@GetMapping` |
| `gin-gonic/gin`, `labstack/echo` | Gin / Echo | `gin.Default()`, `e.GET` |
| `rails` | Rails | `config/routes.rb` |
| `laravel/framework` | Laravel | `routes/*.php` |

**Dependencies:** liste as que afetam arquitetura ou segurança (ORM, driver de banco, CORS, validação, HTTP client, auth, dotenv). Não liste o próprio framework de novo.

## 4. Banco de dados e tabelas

| Sinal | Banco / acesso |
|---|---|
| `import sqlite3`, `require('sqlite3')`, `sqlite:///`, `:memory:` | SQLite (driver cru ou via ORM) |
| `flask_sqlalchemy`, `sqlalchemy`, `db.Model` | SQLAlchemy ORM (dialeto pela URI) |
| `psycopg`, `pg`, `postgres://` | PostgreSQL |
| `mysql`, `pymysql`, `mysql2` | MySQL |
| `mongoose`, `pymongo`, `mongodb://` | MongoDB |
| `prisma`, `typeorm`, `sequelize`, `knex` | ORM/Query builder Node |

Tabelas/entidades:

```bash
grep -rniE "create table( if not exists)?" --include=*.{py,js,ts,sql} .
grep -rnE "__tablename__|class \w+\((db\.)?Model\)|mongoose\.model\(|@Entity" .
```

Informe também onde o banco é criado (arquivo:linha), se é em memória ou arquivo e se há seed (dados iniciais).

## 5. Entry point e comando de execução

Procure, nesta ordem:

1. README: seção "Como rodar" / "Run" / "Getting started" (é o comando que o usuário conhece; **ele precisa continuar funcionando depois da Fase 3**).
2. `package.json` → `scripts.start` e `main`.
3. Python: arquivo com `if __name__ == "__main__":` chamando `app.run(...)`; `wsgi.py`; `manage.py`.
4. Dockerfile `CMD` / `ENTRYPOINT`, `Procfile`.

Registre também a porta (`app.run(port=...)`, `app.listen(...)`, `PORT`) e passos prévios obrigatórios (ex.: `python seed.py`).

## 6. Inventário de rotas

```bash
# Flask
grep -rnE "@(app|\w+_bp|\w+)\.route\(|add_url_rule\(|Blueprint\(" --include=*.py .
# FastAPI
grep -rnE "@(app|router)\.(get|post|put|patch|delete)\(" --include=*.py .
# Express / Koa / Fastify
grep -rnE "\b(app|router)\.(get|post|put|patch|delete|all|use)\(\s*['\"\`]/" --include=*.{js,ts,mjs,cjs} .
# Spring / Nest
grep -rnE "@(Get|Post|Put|Patch|Delete|Request)Mapping|@(Get|Post|Put|Patch|Delete)\(" .
```

Para cada rota: método, path completo (some o prefixo de `Blueprint(url_prefix=...)` ou `app.use('/prefix', router)`), handler e arquivo:linha. Esse inventário é a base da validação da Fase 3.

## 7. Domínio

Infira o domínio a partir de três fontes que precisam concordar: nomes de tabelas/entidades, paths das rotas e textos (README, mensagens, nomes de projeto). Exemplos de leitura:

- tabelas de produto/pedido/item de pedido + rotas de carrinho ou vendas → E-commerce.
- curso/matrícula/pagamento + rota de checkout → LMS / plataforma de cursos com checkout.
- tarefa/projeto/categoria + rotas de status ou relatórios → Task Manager / gestão de projetos.
- conta/transação/saldo → financeiro; paciente/consulta → saúde; post/comentário → blog/CMS.

Nomes podem estar em qualquer idioma (`produtos`, `orders`, `pedidos`): traduza o conceito, não a palavra.

Descreva em uma linha: `<tipo de sistema> (<entidades principais>)`.

## 8. Classificação da arquitetura atual

| Classificação | Sinais |
|---|---|
| **Monolítica (single file / God Class)** | Um arquivo ou classe concentra rotas + SQL + regra de negócio (ex.: classe `*Manager` com `initDb` e `setupRoutes`) |
| **Monolítica em arquivos planos** | Poucos arquivos na raiz divididos por "tipo" (`models.py`, `controllers.py`), mas sem fronteiras reais: o "controller" lê `request` e chama SQL, o "model" tem regra de negócio, tudo depende de estado global |
| **Parcialmente em camadas** | Pastas `models/`, `routes/`, `services/`, `utils/` existem, mas a regra de negócio está nas rotas, serviços têm segredos/IO acoplado, há duplicação entre camadas, e falta config e tratamento de erro centralizados |
| **Em camadas (MVC/Clean)** | Rotas finas, controllers/serviços com o fluxo, models com acesso a dados, config e erros centralizados, injeção de dependência |

Justifique com evidência concreta (ex.: "`src/Manager.js:1-140` cria o banco, registra as rotas e processa pagamento na mesma classe").

## 9. Validação (usada na Fase 3)

**Preparar o ambiente isolado** (nunca instale pacotes no sistema):

| Stack | Preparação | Subir |
|---|---|---|
| Python | Reaproveite `.venv/` se existir; senão `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (ou `uv venv && uv pip install -r requirements.txt`) | `.venv/bin/python <entry>` ou o comando do README usando o Python do venv |
| Node.js | `npm install` (se `node_modules/` não existir). Dependências nativas com install script bloqueado (npm ≥ 11): `npm approve-scripts <pkg>` e depois `npm rebuild <pkg>` | `npm start` |

**Rodar e testar:**

1. Rode passos prévios (seed), apagando antes bancos em arquivo gerados por execuções anteriores, para partir do estado limpo.
2. Suba em background redirecionando a saída para um log (`... > /tmp/<projeto>-server.log 2>&1 &`), guarde o PID e espere a porta abrir (laço com `curl -s -o /dev/null` por até 30 s). Desligue o modo debug/reloader se ele duplicar processos.
3. Chame cada rota do inventário com `curl -s -o /dev/null -w "%{http_code}" -X <MÉTODO> -H "Content-Type: application/json" -d '<json>' http://localhost:<porta><path>`. Cubra caminho feliz (200/201), recurso inexistente (404) e entrada inválida (400) quando a rota tiver esses casos.
4. Confira o log: nenhum traceback ou stack trace durante o boot e as chamadas.
5. Encerre com `kill <PID>` (e confirme que a porta foi liberada).
