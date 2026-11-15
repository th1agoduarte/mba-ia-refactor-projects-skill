"""
Teste de contrato HTTP independente da skill: sobe a aplicação com o MESMO comando
documentado no README do projeto, chama todos os endpoints originais e grava
status + corpo de cada resposta em JSON.

- Antes da refatoração:  python tools/contract_test.py p1 --out docs/evidencias/contract/p1-antes.json
- Depois da refatoração: python tools/contract_test.py p1 --out .../p1-depois.json --baseline .../p1-antes.json

Com --baseline, cada endpoint deve devolver o mesmo status do original (ou um dos
status explicitamente aceitos para endpoints perigosos que passam a exigir auth),
e um 2xx com corpo JSON objeto precisa manter as chaves de topo do original, exceto
chaves sensíveis que a refatoração deve remover (ex.: secret_key). Endpoints administrativos (ADMIN) são chamados sem e com
a credencial (X-Admin-Token e Authorization: Bearer; o app sobe com ADMIN_TOKEN). A seção
"security" mostra vazamentos (senha/hash/secret) antes x depois.

Só usa a biblioteca padrão. Sai com código 1 se algum endpoint quebrar.
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Chaves de topo que podem (e devem) sumir depois da refatoração.
SENSITIVE_TOP_KEYS = {"secret_key", "db_path", "debug", "password", "senha"}
# Marcadores de vazamento procurados no corpo das respostas.
LEAK_MARKERS = ['"senha"', '"password"', "secret_key", "minha-chave-super-secreta"]

PY = ".venv/bin/python"

# Endpoint administrativo: chamado 2x. Sem token pode responder 401/403 (passou a exigir
# credencial); com X-Admin-Token válido precisa devolver o status e as chaves originais.
ADMIN = "admin"
ADMIN_TOKEN = "contract-test-" + os.urandom(8).hex()

PROJECTS = {
    "p1": {
        "dir": "code-smells-project",
        "port": 5000,
        "pre": [],
        "cmd": [PY, "app.py"],
        "clean": ["loja.db"],
        "requests": [
            ("GET", "/", None, None),
            ("GET", "/health", None, None),
            ("GET", "/produtos", None, None),
            ("GET", "/produtos/busca?q=Mouse", None, None),
            ("GET", "/produtos/busca?categoria=informatica&preco_min=100&preco_max=500", None, None),
            ("GET", "/produtos/1", None, None),
            ("GET", "/produtos/9999", None, None),
            ("POST", "/produtos", {"nome": "Produto Teste", "descricao": "x", "preco": 10.5, "estoque": 3, "categoria": "livros"}, None),
            ("POST", "/produtos", {}, None),
            ("POST", "/produtos", {"nome": "Ruim", "preco": -1, "estoque": 1}, None),
            ("PUT", "/produtos/1", {"nome": "Notebook Gamer X", "descricao": "d", "preco": 6000, "estoque": 9, "categoria": "informatica"}, None),
            ("DELETE", "/produtos/11", None, None),
            ("DELETE", "/produtos/9999", None, None),
            ("GET", "/usuarios", None, None),
            ("GET", "/usuarios/1", None, None),
            ("GET", "/usuarios/9999", None, None),
            ("POST", "/usuarios", {"nome": "Teste", "email": "teste@email.com", "senha": "segredo1"}, None),
            ("POST", "/usuarios", {"nome": "Sem email"}, None),
            ("POST", "/login", {"email": "joao@email.com", "senha": "123456"}, None),
            ("POST", "/login", {"email": "teste@email.com", "senha": "segredo1"}, None),
            ("POST", "/login", {"email": "joao@email.com", "senha": "errada"}, None),
            ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 2}, {"produto_id": 3, "quantidade": 1}]}, None),
            ("POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 999}]}, None),
            ("POST", "/pedidos", {"usuario_id": 2, "itens": []}, None),
            ("GET", "/pedidos", None, None),
            ("GET", "/pedidos/usuario/2", None, None),
            ("PUT", "/pedidos/1/status", {"status": "aprovado"}, None),
            ("PUT", "/pedidos/1/status", {"status": "invalido"}, None),
            ("GET", "/relatorios/vendas", None, None),
            # Endpoints administrativos perigosos: podem passar a exigir autenticação.
            ("POST", "/admin/query", {"sql": "SELECT COUNT(*) AS n FROM produtos"}, ADMIN),
            ("POST", "/admin/reset-db", None, ADMIN),
        ],
    },
    "p2": {
        "dir": "ecommerce-api-legacy",
        "port": 3000,
        "pre": [],
        "cmd": ["npm", "start", "--silent"],
        "clean": [],
        "requests": [
            ("POST", "/api/checkout", {"usr": "Guilherme", "eml": "gui@fullcycle.com.br", "pwd": "senhaforte", "c_id": 2, "card": "4111222233334444"}, None),
            ("POST", "/api/checkout", {"usr": "Leonan", "eml": "leonan@fullcycle.com.br", "pwd": "123", "c_id": 2, "card": "4111222233334444"}, None),
            ("POST", "/api/checkout", {"usr": "João", "eml": "joao@teste.com", "pwd": "123", "c_id": 1, "card": "5111222233334444"}, None),
            ("POST", "/api/checkout", {"usr": "X", "eml": "x@x.com"}, None),
            ("POST", "/api/checkout", {"usr": "X", "eml": "x@x.com", "pwd": "1", "c_id": 999, "card": "4111"}, None),
            ("GET", "/api/admin/financial-report", None, ADMIN),
            ("DELETE", "/api/users/1", None, ADMIN),
        ],
    },
    "p3": {
        "dir": "task-manager-api",
        "port": 5000,
        "pre": [[PY, "seed.py"]],
        "cmd": [PY, "app.py"],
        "clean": ["tasks.db", "instance/tasks.db"],
        "requests": [
            ("GET", "/", None, None),
            ("GET", "/health", None, None),
            ("GET", "/tasks", None, None),
            ("GET", "/tasks/1", None, None),
            ("GET", "/tasks/9999", None, None),
            ("GET", "/tasks/search?q=a", None, None),
            ("GET", "/tasks/search?status=pending&priority=1", None, None),
            ("GET", "/tasks/stats", None, None),
            ("POST", "/tasks", {"title": "Nova task", "description": "d", "priority": 2, "user_id": 1, "category_id": 1, "due_date": "2030-01-01", "tags": ["a", "b"]}, None),
            ("POST", "/tasks", {}, None),
            ("POST", "/tasks", {"title": "ab"}, None),
            ("POST", "/tasks", {"title": "Task ruim", "status": "xpto"}, None),
            ("PUT", "/tasks/1", {"status": "in_progress", "priority": 1}, None),
            ("PUT", "/tasks/1", {"priority": 9}, None),
            ("PUT", "/tasks/9999", {"status": "done"}, None),
            ("GET", "/users", None, None),
            ("GET", "/users/1", None, None),
            ("GET", "/users/9999", None, None),
            ("POST", "/users", {"name": "Novo", "email": "novo@email.com", "password": "segredo1", "role": "user"}, None),
            ("POST", "/users", {"name": "Dup", "email": "novo@email.com", "password": "segredo1"}, None),
            ("POST", "/users", {"name": "Ruim", "email": "invalido", "password": "segredo1"}, None),
            ("PUT", "/users/2", {"name": "Maria S."}, None),
            ("GET", "/users/1/tasks", None, None),
            ("POST", "/login", {"email": "joao@email.com", "password": "1234"}, None),
            ("POST", "/login", {"email": "novo@email.com", "password": "segredo1"}, None),
            ("POST", "/login", {"email": "joao@email.com", "password": "errada"}, None),
            ("GET", "/reports/summary", None, None),
            ("GET", "/reports/user/1", None, None),
            ("GET", "/reports/user/9999", None, None),
            ("GET", "/categories", None, None),
            ("POST", "/categories", {"name": "Nova cat", "color": "#ff0000"}, None),
            ("POST", "/categories", {}, None),
            ("PUT", "/categories/1", {"description": "editada"}, None),
            ("DELETE", "/tasks/2", None, None),
            ("DELETE", "/users/3", None, ADMIN),
            ("DELETE", "/categories/9999", None, None),
        ],
    },
}


def wait_port(port: int, timeout: float = 40) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.3)
    return False


def call(base: str, method: str, path: str, body, headers: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            status, raw = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # conexão recusada, timeout...
        return 0, f"<{type(e).__name__}: {e}>"
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def run(name: str, port: int | None = None) -> dict:
    spec = dict(PROJECTS[name])
    if port:  # porta alternativa: só funciona se o app ler PORT do ambiente (código refatorado)
        spec["port"] = port
    cwd = ROOT / spec["dir"]
    for f in spec["clean"]:
        (cwd / f).unlink(missing_ok=True)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", spec["port"])) == 0:
            sys.exit(f"porta {spec['port']} já está em uso; pare o processo antes")

    env = {**os.environ, "FLASK_DEBUG": "0", "PYTHONUNBUFFERED": "1", "PORT": str(spec["port"]), "ADMIN_TOKEN": ADMIN_TOKEN}
    for pre in spec["pre"]:
        subprocess.run(pre, cwd=cwd, env=env, check=True, capture_output=True)

    log = open(ROOT / "tools" / f".{name}-server.log", "w")
    proc = subprocess.Popen(spec["cmd"], cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        booted = wait_port(spec["port"])
        base = f"http://127.0.0.1:{spec['port']}"
        results = []
        if booted:
            for method, path, body, kind in spec["requests"]:
                status, resp = call(base, method, path, body)
                entry = {"method": method, "path": path, "body": body, "admin": kind == ADMIN,
                         "status": status, "response": resp}
                if kind == ADMIN and status in (401, 403):  # protegido: repete com a credencial
                    entry["status_token"], entry["response_token"] = call(
                        base, method, path, body, {"X-Admin-Token": ADMIN_TOKEN, "Authorization": f"Bearer {ADMIN_TOKEN}"})
                results.append(entry)
        return {"project": spec["dir"], "command": " ".join(spec["cmd"]), "booted": booted,
                "booted_alive": proc.poll() is None, "results": results}
    finally:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
        log.close()


def leaks(resp) -> list[str]:
    text = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
    return [m for m in LEAK_MARKERS if m in text]


def compare(current: dict, baseline: dict) -> int:
    failures = 0
    print(f"\n{'Endpoint':<62} {'antes':>5} {'depois':>6}  resultado")
    for before, after in zip(baseline["results"], current["results"]):
        label = f"{before['method']} {before['path']}"[:62]
        note = ""
        status, response = after["status"], after["response"]
        if after.get("admin") and "status_token" in after:
            # sem token: 401/403 aceito; com token: tem que ser o comportamento original
            note = f"(sem token {after['status']}, com token {after['status_token']})"
            status, response = after["status_token"], after["response_token"]
        ok = status == before["status"]
        if ok and 200 <= status < 300 and isinstance(before["response"], dict) and isinstance(response, dict):
            missing = set(before["response"]) - set(response) - SENSITIVE_TOP_KEYS
            if missing:
                ok, note = False, f"chaves ausentes: {sorted(missing)}"
        failures += not ok
        print(f"{label:<62} {before['status']:>5} {status:>6}  {'✓' if ok else '✗'} {note}")
    print("\nSecurity (marcadores de vazamento nas respostas):")
    for before, after in zip(baseline["results"], current["results"]):
        lb = leaks(before["response"])
        la = leaks(after["response"]) + leaks(after.get("response_token", ""))
        if lb or la:
            print(f"  {before['method']} {before['path']}: antes={lb or '-'} depois={la or '-'}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", choices=sorted(PROJECTS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--port", type=int, help="porta alternativa (repassada ao app como PORT)")
    args = ap.parse_args()

    current = run(args.project, args.port)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(current, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"Projeto: {current['project']} | comando: {current['command']}" + (f" | PORT={args.port}" if args.port else ""))
    print(f"{'✓' if current['booted'] else '✗'} aplicação iniciou (porta aberta) | viva após os testes: {current['booted_alive']}")
    if not current["booted"]:
        print((ROOT / "tools" / f".{args.project}-server.log").read_text()[-3000:])
        return 1
    if args.baseline:
        failures = compare(current, json.loads(Path(args.baseline).read_text()))
        total = len(current["results"])
        print(f"\n{total - failures}/{total} endpoints com o contrato original preservado")
        return 1 if failures else 0
    for r in current["results"]:
        print(f"  {r['status']:>3} {r['method']} {r['path']}")
    return 0 if all(r["status"] for r in current["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
