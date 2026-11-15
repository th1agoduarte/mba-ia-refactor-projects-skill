# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`, já refatorada para MVC.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Configuração por variáveis de ambiente (todas opcionais, documentadas em `.env.example`; um `.env` na raiz é carregado se existir):

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `DB_PATH` | `:memory:` | Banco SQLite |
| `ADMIN_TOKEN` | vazio | Credencial dos endpoints administrativos (header `X-Admin-Token`). Vazio = 403 |
| `PAYMENT_GATEWAY_KEY` | vazio | Chave do gateway; vazio = gateway simulado |
| `LOG_LEVEL` | `info` | `error`, `warn`, `info`, `debug` |

```bash
ADMIN_TOKEN=meu-token npm start
curl -H "X-Admin-Token: meu-token" http://localhost:3000/api/admin/financial-report
```

Exemplos de requisições estão em `api.http`.

## Estrutura

```
src/
├── app.js            # composition root + listen
├── config/           # config (env), constantes de domínio, logger
├── database/         # conexão promisificada + transação, schema, seed
├── models/           # acesso a dados (SQL parametrizado) e hash de senha
├── services/         # gateway de pagamento (simulado)
├── controllers/      # casos de uso: checkout, relatório, exclusão de usuário
├── routes/           # rotas Express finas
├── middlewares/      # autenticação admin e tratamento de erro central
└── errors.js         # exceções de domínio
```
