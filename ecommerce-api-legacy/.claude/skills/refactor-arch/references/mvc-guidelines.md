# Guidelines de arquitetura — MVC alvo (Fase 3)

## Camadas e responsabilidades

| Camada | Pode | Não pode |
|---|---|---|
| **Config** (`config/`) | Ler variáveis de ambiente, definir defaults seguros, expor constantes de domínio (status válidos, limites, faixas de desconto) | Conter segredos literais; importar framework HTTP ou models |
| **Models** (`models/`) | Representar entidades, encapsular acesso a dados (SQL parametrizado, ORM), regras intrínsecas da entidade (ex.: `is_overdue`, hash/checagem de senha), serialização pública (`to_dict` sem campos sensíveis) | Ler `request`/`req`, devolver respostas HTTP, chamar serviços externos |
| **Controllers** (`controllers/`) | Concentrar o fluxo da aplicação de cada caso de uso: validar entrada, orquestrar models e serviços, abrir/fechar transação, decidir o resultado e lançar erros de domínio | Conhecer detalhes de SQL; montar respostas HTTP específicas do framework (exceto quando o framework exigir, mantendo-se fino); guardar estado entre requisições |
| **Views / Routes** (`views/` ou `routes/`) | Mapear método + path → controller, extrair parâmetros da requisição, aplicar middlewares (auth), serializar o resultado (JSON) com o status HTTP | Conter regra de negócio, SQL ou laços de agregação |
| **Middlewares** (`middlewares/`) | Tratamento de erro centralizado, autenticação/autorização, logging de requisição | Regra de negócio |
| **Services** (`services/`, opcional) | Integrações externas atrás de uma interface (e-mail, SMS, pagamento) | Regra de negócio central; segredos literais |
| **Composition root** (`app.py`/`app.js` ou `create_app()`) | Criar a aplicação, carregar config, instanciar dependências (banco, serviços), injetar nos controllers, registrar rotas, middlewares e handlers de erro | Conter rotas com lógica |

Numa API JSON, a **View** é a representação da resposta: o módulo de rotas, que define o formato HTTP, e a serialização dos models (`to_dict`/`toJSON`).

## Regra de dependência

```
views/routes ──▶ controllers ──▶ models ──▶ database
      │                │
      ▼                ▼
 middlewares        services        config (lido por todos, não depende de ninguém)
```

- Dependências apontam só para baixo. Model nunca importa controller; controller nunca importa o objeto `request`/`req` (recebe dados já extraídos).
- Erros sobem como exceções de domínio (`NotFoundError`, `ValidationError`, `ConflictError`, `UnauthorizedError`) e o middleware de erro as converte em status HTTP. Nada de `try/except` por handler só para devolver 500.
- Dependências são injetadas: o composition root cria a conexão/repositório/serviço e entrega a quem precisa (argumento de construtor, factory ou `app.extensions`/`app.locals`). Isso elimina estado global e permite testes.

## Estruturas alvo por stack

Adapte nomes ao idioma e às convenções do projeto (ex.: `produto_model.py` em projeto em português). Mantenha o **comando de execução** original.

### Python / Flask

```
<projeto>/
├── app.py                     # entry point fino: from src.app import create_app; app = create_app(); app.run(...)
├── seed.py                    # (se existia) usa create_app() + models
├── requirements.txt
├── .env.example
└── src/
    ├── __init__.py
    ├── app.py                 # create_app(): config, db, blueprints, error handlers (composition root)
    ├── config/settings.py     # Config a partir de os.environ, constantes de domínio
    ├── database.py            # conexão/sessão (sqlite3 por request via g, ou SQLAlchemy db)
    ├── models/<entidade>_model.py
    ├── controllers/<entidade>_controller.py
    ├── views/<entidade>_routes.py   # Blueprints finos (ou routes/)
    ├── middlewares/error_handler.py # register_error_handlers(app) + exceções de domínio
    ├── middlewares/auth.py          # (se houver endpoints protegidos)
    └── services/notification_service.py  # (se houver integração externa)
```

- Flask: use **application factory** (`create_app`) e **Blueprints** por domínio.
- Banco `sqlite3` cru: conexão por requisição em `flask.g` + `teardown_appcontext`, ou repositório injetado; `row_factory = sqlite3.Row`; schema e seed em funções explícitas chamadas pelo composition root.
- Flask-SQLAlchemy: `db = SQLAlchemy()` em `database.py`, `db.init_app(app)` no factory, `db.session.get(Model, id)`.

### Node.js / Express

```
<projeto>/
├── package.json               # "start" continua funcionando (ajuste o caminho se o entry mudar)
├── .env.example
└── src/
    ├── app.js                 # composition root: cria db, models, controllers, rotas, error handler; listen
    ├── config/index.js        # config a partir de process.env
    ├── database/connection.js # abre o banco e expõe helpers async (run/get/all promisificados), schema + seed
    ├── models/<entidade>Model.js      # acesso a dados com SQL parametrizado
    ├── controllers/<entidade>Controller.js  # fluxo do caso de uso (async/await)
    ├── routes/<entidade>Routes.js     # express.Router(), handlers finos, asyncHandler
    ├── middlewares/errorHandler.js    # (err, req, res, next) + AppError
    ├── middlewares/auth.js            # (se houver endpoints protegidos)
    └── services/paymentService.js     # (se houver integração externa)
```

- Use `async/await` com o driver promisificado (`util.promisify` ou wrappers que retornam Promise).
- Um wrapper `asyncHandler(fn)` encaminha rejeições para o middleware de erro.
- O error handler é o último `app.use`.

### Outras stacks

Mesmo princípio: Django (`views.py` finos + `services.py` + `models.py`), FastAPI (`routers/` + `services/` + `repositories/`), Spring (`@RestController` + `@Service` + `@Repository`). Mapeie para as 3 camadas e explique o mapeamento no resumo.

## Adaptação ao ponto de partida

| Ponto de partida | Estratégia |
|---|---|
| **Monolito / God Class** | Extrair por responsabilidade: config → models (SQL) → controllers (fluxo) → routes (HTTP) → middlewares. Remover o arquivo original no final. |
| **Arquivos planos (`models.py`, `controllers.py`)** | Quebrar por domínio (um model/controller por entidade), criar `views/` com o roteamento que estava no `app.py`, mover validação e regras para controllers, remover SQL dos controllers. |
| **Parcialmente em camadas** | Não reescrever o que está certo. Reaproveitar models existentes (corrigindo serialização e deprecated APIs), criar `controllers/` com a lógica que está nas rotas, deixar `routes/` finos, mover segredos de services para config, reutilizar `utils/` (validações) em vez de duplicar, criar error handler central. |

## Checklist de conformidade (use na validação)

- [ ] Estrutura de diretórios com `config/`, `models/`, `views/` (ou `routes/`), `controllers/`, `middlewares/`
- [ ] Nenhum segredo literal no código; config lida do ambiente, com `.env.example`
- [ ] Models abstraem os dados (nenhum SQL/ORM fora de models/database)
- [ ] Views/Routes só roteiam e serializam
- [ ] Controllers concentram o fluxo (validação, orquestração, transação)
- [ ] Error handling centralizado (handler/middleware único + exceções de domínio)
- [ ] Entry point claro (composition root) e comando de execução original funcionando
- [ ] Aplicação inicia sem erros e todos os endpoints originais respondem
