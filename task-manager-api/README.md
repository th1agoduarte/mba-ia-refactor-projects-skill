# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Foi refatorada para MVC pela skill `/refactor-arch`, mantendo as mesmas rotas, métodos, status HTTP e formato JSON.

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo. **Rode-o antes do primeiro boot**, senão os endpoints devolvem listas vazias. Os usuários do seed entram com as mesmas senhas de antes (`joao@email.com` / `1234`, que é admin).

## Configuração

Tudo vem de variáveis de ambiente (ou de um `.env` na raiz do projeto). Veja `.env.example`. Sem nenhuma variável, a aplicação sobe com debug desligado, bind em `0.0.0.0` e CORS liberado (os mesmos do sistema legado; restrinja com `HOST` e `CORS_ORIGINS`), `SECRET_KEY` aleatória (com aviso no log) e SMTP desabilitado.

## Operações administrativas

`DELETE /users/<id>`, criar um usuário com `role` diferente de `user` e alterar o `role` de um usuário exigem o header `Authorization: Bearer <credencial>`. A credencial pode ser:

- o valor de `ADMIN_TOKEN`; ou
- o `token` devolvido por `POST /login` para um usuário admin ativo.

Sem credencial, essas operações respondem 401. Com a credencial de um usuário que não é admin, respondem 403.

## Estrutura

```
app.py                  # composition root: create_app() + python app.py
seed.py                 # dados iniciais
database.py             # db (Flask-SQLAlchemy) + utcnow()
config/settings.py      # variáveis de ambiente e constantes de domínio
models/                 # entidades, regras da entidade, consultas e serialização
controllers/            # casos de uso, validação e transações
routes/                 # blueprints finos (method + path → controller → JSON)
middlewares/            # error handler central + autorização de admin
services/               # e-mail de notificação e tokens de login
```
