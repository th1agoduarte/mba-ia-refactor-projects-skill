# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, refatorada para MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas com hash).

## Configuração

Todas as variáveis são opcionais e estão documentadas em [`.env.example`](.env.example). As principais:

| Variável | Default | Efeito |
|---|---|---|
| `SECRET_KEY` | aleatória por boot | chave de assinatura do Flask |
| `ADMIN_TOKEN` | vazio | habilita `POST /admin/reset-db` e `POST /admin/query` (header `X-Admin-Token`); vazio = 403 |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | bind do servidor (mesmo padrão do legado) |
| `FLASK_DEBUG` | `0` | modo debug |
| `CORS_ORIGINS` | `*` | origens liberadas para CORS, separadas por vírgula (padrão do legado: todas) |

Exemplo de endpoint administrativo:

```bash
ADMIN_TOKEN=troque-me python app.py
curl -X POST -H "X-Admin-Token: troque-me" -H "Content-Type: application/json" \
     -d '{"sql":"SELECT COUNT(*) AS n FROM produtos"}' http://localhost:5000/admin/query
```

`/admin/query` aceita só uma consulta `SELECT`, executada numa conexão somente leitura.

## Estrutura

```
app.py                  # entry point (python app.py) → src.app.create_app()
src/app.py              # composition root: config, banco, models, controllers, blueprints, error handlers
src/config/settings.py  # variáveis de ambiente + constantes de domínio
src/database.py         # conexão por requisição, schema e seed
src/models/             # acesso a dados (SQL parametrizado) e serialização
src/controllers/        # casos de uso: validação, regras, transações
src/views/              # rotas (Blueprints) finas
src/middlewares/        # error handler central e autorização admin
src/services/           # notificações
```
