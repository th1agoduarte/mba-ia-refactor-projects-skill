# Playbook de refatoração (Fase 3)

Cada transformação diz **quando usar** (anti-patterns que resolve), **passos** e um exemplo **antes/depois**. Os exemplos alternam Python/Flask e Node.js/Express; aplique a mesma ideia na stack detectada. Ordem de execução: T-01 → T-02 → T-04 → T-12 → T-03 → T-07 → T-08 → T-10 → T-05 → demais.

| ID | Transformação | Resolve |
|---|---|---|
| T-01 | Extrair configuração e segredos para o ambiente | AP-01, AP-05, AP-11 |
| T-02 | Consultas parametrizadas | AP-02 |
| T-03 | Quebrar God Class em Model / Controller / Routes | AP-03, AP-09 |
| T-04 | Hash de senha forte e serialização sem dados sensíveis | AP-05, AP-06 |
| T-05 | Error handling centralizado + logger | AP-15, AP-22 |
| T-06 | Eliminar N+1 (JOIN, agregação, eager loading) | AP-12 |
| T-07 | Mover regra de negócio para controllers e integrações para services | AP-07, AP-18 |
| T-08 | Substituir estado global por injeção de dependência (factory) | AP-08, AP-09 |
| T-09 | Callback hell → async/await | AP-16 |
| T-10 | Transações e integridade referencial | AP-10 |
| T-11 | Substituir APIs deprecated | AP-17 |
| T-12 | Proteger endpoints administrativos | AP-04 |
| T-13 | Validação centralizada, constantes nomeadas e condicionais limpas | AP-13, AP-19, AP-23 |
| T-14 | Remover duplicação (serializer/helper único) | AP-14, AP-20, AP-21 |

---

## T-01 — Extrair configuração e segredos para o ambiente

**Passos:** criar o módulo de config; ler cada valor de variável de ambiente; para segredos ausentes, gerar valor efêmero (com aviso) ou desabilitar o recurso, sem literal no código; `debug` desligado por padrão; criar `.env.example`; remover segredos de respostas e logs.

```python
# ANTES — app.py
app.config["SECRET_KEY"] = "minha-chave-123"
app.config["DEBUG"] = True
app.run(host="0.0.0.0", port=5000, debug=True)
```

```python
# DEPOIS — src/config/settings.py
import os, secrets, logging

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)  # efêmera se ausente
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")  # sem token = endpoints admin bloqueados

if not os.environ.get("SECRET_KEY"):
    logging.getLogger(__name__).warning("SECRET_KEY não definida; usando chave efêmera")

# app.py (entry)
app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
```

```js
// ANTES — utils.js
const config = { dbPass: "senha_prod_123", paymentGatewayKey: "pk_live_abc", port: 3000 };
// DEPOIS — src/config/index.js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  dbPath: process.env.DB_PATH || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',   // vazio = modo simulado
  adminToken: process.env.ADMIN_TOKEN || '',
});
```

## T-02 — Consultas parametrizadas

**Passos:** trocar toda concatenação/interpolação por placeholders do driver (`?`, `%s`, `$1`, `:nome`); para filtros dinâmicos, montar a lista de condições e a lista de parâmetros em paralelo; `LIKE` recebe o `%` no parâmetro.

```python
# ANTES
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query = "SELECT * FROM produtos WHERE 1=1"
if termo: query += " AND nome LIKE '%" + termo + "%'"
```

```python
# DEPOIS
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
clauses, params = [], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
sql = "SELECT * FROM produtos" + (" WHERE " + " AND ".join(clauses) if clauses else "")
cursor.execute(sql, params)
```

```js
// ANTES
db.get(`SELECT * FROM users WHERE email = '${email}'`, cb);
// DEPOIS
const user = await db.get('SELECT * FROM users WHERE email = ?', [email]);
```

## T-03 — Quebrar God Class em Model / Controller / Routes

**Passos:** (1) listar as responsabilidades do arquivo com as linhas; (2) mover schema/conexão/seed para `database`; (3) mover SQL de cada entidade para `models/<entidade>`; (4) mover o fluxo de cada caso de uso para `controllers/<entidade>`; (5) mover o registro de rotas para `routes|views/<entidade>`; (6) composition root conecta tudo; (7) apagar o arquivo original.

```js
// ANTES — uma classe faz tudo
class MainManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + seed */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* validação + SQL + pagamento + resposta */ });
  }
}
```

```js
// DEPOIS
// src/models/courseModel.js
class CourseModel {
  constructor(db) { this.db = db; }
  findActiveById(id) { return this.db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]); }
}
// src/controllers/checkoutController.js
class CheckoutController {
  constructor({ courseModel, userModel, enrollmentService }) { Object.assign(this, { courseModel, userModel, enrollmentService }); }
  async checkout(input) {
    const course = await this.courseModel.findActiveById(input.courseId);
    if (!course) throw new NotFoundError('Curso não encontrado');
    return this.enrollmentService.enroll(input, course);
  }
}
// src/routes/checkoutRoutes.js
module.exports = (controller) => {
  const router = express.Router();
  router.post('/api/checkout', asyncHandler(async (req, res) => {
    const result = await controller.checkout(parseCheckout(req.body));
    res.status(200).json(result);
  }));
  return router;
};
```

```python
# DEPOIS (Flask) — src/views/produto_routes.py
def create_produto_blueprint(controller):
    bp = Blueprint("produtos", __name__)
    @bp.get("/produtos/<int:id>")
    def buscar(id):
        return jsonify({"dados": controller.buscar(id), "sucesso": True}), 200
    return bp
```

## T-04 — Hash de senha forte e serialização sem dados sensíveis

**Passos:** gravar senha com KDF com salt (`werkzeug.security.generate_password_hash` / `hashlib.scrypt` / `bcrypt` / Node `crypto.scrypt`); login busca por e-mail e verifica o hash em tempo constante; seed grava o hash (as senhas do seed continuam válidas); serialização pública nunca inclui senha/hash; remover logs de dados sensíveis (cartão, senha).

```python
# ANTES
self.password = hashlib.md5(pwd.encode()).hexdigest()
def to_dict(self): return {"id": self.id, "email": self.email, "password": self.password}
```

```python
# DEPOIS
from werkzeug.security import generate_password_hash, check_password_hash
def set_password(self, pwd): self.password = generate_password_hash(pwd)
def check_password(self, pwd): return check_password_hash(self.password, pwd)
def to_dict(self): return {"id": self.id, "email": self.email}   # sem senha
```

```js
// ANTES
function weakHash(pwd) { return Buffer.from(pwd).toString('base64').substring(0, 10); }
console.log(`Processando cartão ${cc}`);
// DEPOIS — src/utils/password.js
const crypto = require('node:crypto');
function hashPassword(pwd) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `${salt}:${crypto.scryptSync(pwd, salt, 64).toString('hex')}`;
}
function verifyPassword(pwd, stored) {
  const [salt, hash] = stored.split(':');
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), crypto.scryptSync(pwd, salt, 64));
}
logger.info(`Processando cartão final ${card.slice(-4)}`);
```

Migração de dados legados: se já houver senhas em texto puro no banco de seed, regrave-as com hash no seed. Não mantenha o formato antigo.

## T-05 — Error handling centralizado + logger

**Passos:** criar exceções de domínio com status; registrar um handler global; remover `try/except` repetidos dos handlers; erro inesperado → log com stack + resposta genérica (sem `str(e)`); trocar `print`/`console.log` por logger configurado no composition root. Preserve o **formato** de erro que o projeto já usava (ex.: `{"erro": ...}` ou `{"error": ...}`).

```python
# ANTES — em cada handler
try:
    ...
except Exception as e:
    print("ERRO: " + str(e))
    return jsonify({"erro": str(e)}), 500
```

```python
# DEPOIS — src/middlewares/error_handler.py
import logging
log = logging.getLogger(__name__)

class AppError(Exception):
    status = 400
    def __init__(self, message, status=None):
        super().__init__(message); self.message = message; self.status = status or self.status
class NotFoundError(AppError): status = 404
class ValidationError(AppError): status = 400

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({"erro": e.message, "sucesso": False}), e.status
    @app.errorhandler(Exception)
    def handle_unexpected(e):
        log.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
```

```js
// DEPOIS — src/middlewares/errorHandler.js
class AppError extends Error { constructor(message, status = 400) { super(message); this.status = status; } }
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
function errorHandler(err, req, res, next) {
  if (err instanceof AppError) return res.status(err.status).send(err.message);
  console.error(err);                       // ou logger.error(err)
  return res.status(500).send('Erro interno');
}
module.exports = { AppError, asyncHandler, errorHandler };
```

Atenção ao 404 de rota inexistente e ao `HTTPException` do Flask: não converta em 500. Use `@app.errorhandler(HTTPException)` devolvendo `e.code`.

## T-06 — Eliminar N+1

**Passos:** substituir consultas dentro de laço por um `JOIN` ou por uma consulta `IN (...)` e agrupar em memória; contagens por status viram um `GROUP BY`; no ORM, usar eager loading (`joinedload`/`selectinload`) ou agregação.

```python
# ANTES — 1 + N + N*M consultas
for row in pedidos:
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()
```

```python
# DEPOIS — 2 consultas
pedidos = db.execute("SELECT * FROM pedidos WHERE usuario_id = ?", (uid,)).fetchall()
ids = [p["id"] for p in pedidos]
itens = db.execute(
    f"SELECT i.*, COALESCE(p.nome, 'Desconhecido') AS produto_nome FROM itens_pedido i "
    f"LEFT JOIN produtos p ON p.id = i.produto_id WHERE i.pedido_id IN ({','.join('?' * len(ids))})", ids
).fetchall() if ids else []
por_pedido = defaultdict(list)
for i in itens: por_pedido[i["pedido_id"]].append(i)
```

```python
# ANTES (ORM) — uma query por status e uma por usuário
pending = Task.query.filter_by(status='pending').count()
done = Task.query.filter_by(status='done').count()
# DEPOIS
rows = db.session.execute(db.select(Task.status, db.func.count()).group_by(Task.status)).all()
by_status = {s: 0 for s in VALID_STATUSES} | dict(rows)
tasks = db.session.execute(db.select(Task).options(joinedload(Task.user), joinedload(Task.category))).scalars().all()
```

```js
// ANTES — forEach com db.get aninhado por matrícula
// DEPOIS — uma consulta com JOIN
const rows = await db.all(`
  SELECT c.id, c.title, u.name AS student, p.amount, p.status
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.id
  LEFT JOIN users u ON u.id = e.user_id
  LEFT JOIN payments p ON p.enrollment_id = e.id`);
```

## T-07 — Mover regra de negócio para controllers e integrações para services

**Passos:** a rota só extrai a entrada e chama o controller; cálculos (total, desconto, estoque), regras de status e agregações vão para o controller (ou para o model, quando forem regra intrínseca da entidade); notificações, pagamento e e-mail ficam atrás de um service injetado. Credenciais do service vêm da config.

```python
# ANTES — rota calcula desconto e "envia" notificações
@app.post("/pedidos")
def criar_pedido():
    ...
    print("ENVIANDO EMAIL: Pedido criado")
    print("ENVIANDO SMS: ...")
```

```python
# DEPOIS — src/controllers/pedido_controller.py
class PedidoController:
    def __init__(self, pedido_model, produto_model, notifier):
        self.pedidos, self.produtos, self.notifier = pedido_model, produto_model, notifier
    def criar(self, usuario_id, itens):
        validar_pedido(usuario_id, itens)                # ValidationError
        pedido = self.pedidos.criar_com_itens(usuario_id, itens)   # transação no model
        self.notifier.pedido_criado(pedido)              # service injetado
        return pedido

# src/services/notification_service.py
class NotificationService:
    def __init__(self, logger): self.log = logger
    def pedido_criado(self, pedido): self.log.info("Notificação: pedido %s criado", pedido["pedido_id"])
```

## T-08 — Substituir estado global por injeção de dependência (factory)

**Passos:** remover variáveis globais mutáveis (`global db_connection`, caches/contadores exportados); criar as dependências no composition root e injetá-las; conexão de banco por requisição (Flask `g`) ou por instância injetada; caches viram objeto com dono claro.

```python
# ANTES
db_connection = None
def get_db():
    global db_connection
    if db_connection is None: db_connection = sqlite3.connect("loja.db", check_same_thread=False)
    return db_connection
```

```python
# DEPOIS — src/database.py
import sqlite3
from flask import g, current_app
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None: db.close()
def init_app(app):
    app.teardown_appcontext(close_db)

# src/app.py
def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)
    database.init_app(app)
    with app.app_context(): database.init_schema(); database.seed()
    produto_ctrl = ProdutoController(ProdutoModel())
    app.register_blueprint(create_produto_blueprint(produto_ctrl))
    register_error_handlers(app)
    return app
```

```js
// ANTES
let globalCache = {}; let totalRevenue = 0; module.exports = { globalCache, totalRevenue };
// DEPOIS — dono explícito, injetado
class CheckoutCache { constructor() { this.map = new Map(); } set(k, v) { this.map.set(k, v); } }
const cache = new CheckoutCache();                       // criado no composition root
const controller = new CheckoutController({ ..., cache });
```

## T-09 — Callback hell → async/await

**Passos:** criar wrappers que retornam Promise para o driver; reescrever o fluxo linear com `await`; um único ponto de resposta; erros sobem para o `asyncHandler`/error middleware.

```js
// ANTES
db.get(sqlA, [a], (err, x) => {
  if (err) return res.status(500).send('Erro');
  db.run(sqlB, [b], function (err) {
    if (err) return res.status(500).send('Erro');
    db.run(sqlC, [this.lastID], (err) => { res.json({ ok: true }); });
  });
});
```

```js
// DEPOIS — src/database/connection.js
const run = (sql, params = []) => new Promise((resolve, reject) =>
  db.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); }));
const get = (sql, params = []) => new Promise((res, rej) => db.get(sql, params, (e, row) => (e ? rej(e) : res(row))));
const all = (sql, params = []) => new Promise((res, rej) => db.all(sql, params, (e, rows) => (e ? rej(e) : res(rows))));

// controller
const x = await get(sqlA, [a]);
const { lastID } = await run(sqlB, [b]);
await run(sqlC, [lastID]);
return { ok: true };
```

## T-10 — Transações e integridade referencial

**Passos:** envolver escritas relacionadas numa transação (`BEGIN`/`COMMIT`/`ROLLBACK`, `with conn:`, `db.session.begin()`); validar tudo antes de escrever; baixa de estoque condicional (`UPDATE ... SET estoque = estoque - ? WHERE id = ? AND estoque >= ?`); deletes de entidade pai removem/tratam filhos na mesma transação (ou `ON DELETE CASCADE` com `PRAGMA foreign_keys = ON`).

```python
# ANTES — pedido inserido; se um item falhar, pedido fica sem itens
cursor.execute("INSERT INTO pedidos ...")
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
db.commit()
```

```python
# DEPOIS
with db:   # sqlite3: commit no sucesso, rollback na exceção
    cur = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)", (uid, STATUS_PENDENTE, total))
    for item in itens:
        db.execute("INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                   (cur.lastrowid, item["produto_id"], item["quantidade"], precos[item["produto_id"]]))
        db.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (item["quantidade"], item["produto_id"]))
```

```js
// DEPOIS — delete sem órfãos
await run('BEGIN');
try {
  await run('DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [id]);
  await run('DELETE FROM enrollments WHERE user_id = ?', [id]);
  await run('DELETE FROM users WHERE id = ?', [id]);
  await run('COMMIT');
} catch (e) { await run('ROLLBACK'); throw e; }
```

## T-11 — Substituir APIs deprecated

**Passos:** para cada item da seção "Deprecated APIs" do relatório, aplicar o substituto da tabela do catálogo (AP-17); rodar a aplicação com warnings visíveis (`python -W default`, `node --trace-deprecation`) e confirmar que sumiram.

```python
# ANTES
user = User.query.get(user_id)
created_at = db.Column(db.DateTime, default=datetime.utcnow)
if task.due_date < datetime.utcnow(): ...
```

```python
# DEPOIS
from datetime import datetime, timezone
def utcnow():                      # mantém datetime "naive" em UTC, compatível com colunas existentes
    return datetime.now(timezone.utc).replace(tzinfo=None)
user = db.session.get(User, user_id)
created_at = db.Column(db.DateTime, default=utcnow)
if task.due_date < utcnow(): ...
```

```js
// ANTES
const buf = new Buffer(pwd); const q = url.parse(req.url, true).query;
// DEPOIS
const buf = Buffer.from(pwd); const q = Object.fromEntries(new URL(req.url, 'http://x').searchParams);
```

## T-12 — Proteger endpoints administrativos

**Passos:** manter a rota (contrato), mas exigir credencial de administrador vinda da config (header `X-Admin-Token` comparado com `hmac.compare_digest`/`crypto.timingSafeEqual`, ou papel admin autenticado); sem token configurado, o recurso fica desabilitado (403); SQL arbitrário, quando mantido, aceita só leitura (`SELECT`) e só com credencial.

```python
# ANTES
@app.route("/admin/reset-db", methods=["POST"])
def reset_database(): ...
```

```python
# DEPOIS — src/middlewares/auth.py
import hmac
from functools import wraps
from flask import request, current_app
def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        if not expected:
            raise ForbiddenError("Endpoint administrativo desabilitado (defina ADMIN_TOKEN)")
        if not hmac.compare_digest(request.headers.get("X-Admin-Token", ""), expected):
            raise UnauthorizedError("Credencial de administrador inválida")
        return fn(*args, **kwargs)
    return wrapper

@bp.post("/admin/reset-db")
@require_admin
def reset_database(): return jsonify(admin_controller.reset()), 200
```

```js
// DEPOIS — src/middlewares/auth.js
module.exports = (config) => (req, res, next) => {
  const token = req.get('X-Admin-Token') || '';
  if (!config.adminToken) return res.status(403).send('Endpoint administrativo desabilitado');
  const ok = token.length === config.adminToken.length &&
    crypto.timingSafeEqual(Buffer.from(token), Buffer.from(config.adminToken));
  return ok ? next() : res.status(401).send('Não autorizado');
};
```

## T-13 — Validação centralizada, constantes nomeadas e condicionais limpas

**Passos:** criar validadores reutilizáveis (funções ou schema) usados por create e update; listas e limites viram constantes na config/domínio; tratar corpo ausente/tipo inválido como 400; simplificar condicionais.

```python
# ANTES
if status not in ['pending', 'in_progress', 'done', 'cancelled']: ...
if priority < 1 or priority > 5: ...
if faturamento > 10000: desconto = faturamento * 0.1
def is_admin(self):
    if self.role == 'admin': return True
    else: return False
```

```python
# DEPOIS — src/config/settings.py
VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
PRIORITY_RANGE = range(1, 6)
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))   # (faturamento acima de, taxa)

# validators
def validate_priority(value):
    if not isinstance(value, int) or value not in PRIORITY_RANGE:
        raise ValidationError("Prioridade deve ser entre 1 e 5")

def desconto_para(faturamento):
    return next((faturamento * taxa for limite, taxa in DISCOUNT_TIERS if faturamento > limite), 0)

def is_admin(self): return self.role == ROLE_ADMIN
```

## T-14 — Remover duplicação (serializer/helper único)

**Passos:** um único serializer por entidade (`to_dict`/`toJSON`) usado em todas as rotas, com campos derivados (ex.: `overdue`) calculados por um método do model; laços copiados viram uma função; apagar imports não usados e helpers mortos; renomear identificadores internos opacos.

```python
# ANTES — o mesmo bloco em 3 rotas
task_data = {}; task_data['id'] = t.id; task_data['title'] = t.title  # ...
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled': task_data['overdue'] = True
```

```python
# DEPOIS — models/task.py
def is_overdue(self):
    return bool(self.due_date and self.due_date < utcnow() and self.status not in CLOSED_STATUSES)
def to_dict(self, include_relations=False):
    data = {..., "overdue": self.is_overdue()}
    if include_relations:
        data["user_name"] = self.user.name if self.user else None
        data["category_name"] = self.category.name if self.category else None
    return data
```

**Cuidado com o contrato:** se rotas diferentes devolviam subconjuntos diferentes de campos, o serializer único precisa aceitar opções (`fields=`/`include_relations=`) para que cada rota continue com as mesmas chaves.
