"""Prova negativa de autorização no projeto 3 (task-manager-api), sem rede e sem LLM.

Achado do code review independente: PUT /users/<id> aberto permitia trocar a senha do admin
sem credencial. Este script sobe a app com o test client do Flask num banco temporário e
confere que só o próprio usuário ou um administrador altera um usuário.
Uso: python3 tools/seguranca_p3.py   (usa task-manager-api/.venv)
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROJETO = RAIZ / "task-manager-api"

SONDA = r'''
import sys
import seed
from app import create_app
app = create_app()
seed.seed_data(app)
c = app.test_client()
falhas = []
def checar(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"{'PASS' if ok else 'FAIL'} {nome}: {obtido} (esperado {esperado})")
    if not ok: falhas.append(nome)
def login(e, p): return c.post('/login', json={'email': e, 'password': p}).get_json().get('token')
checar('PUT /users/1 trocar senha sem credencial', c.put('/users/1', json={'password': 'invadido'}).status_code, 401)
checar('PUT /users/1 desativar sem credencial', c.put('/users/1', json={'active': False}).status_code, 401)
tm = {'Authorization': 'Bearer ' + login('maria@email.com', 'abcd')}
checar('usuário comum altera outro usuário (admin)', c.put('/users/1', json={'password': 'invadido'}, headers=tm).status_code, 403)
checar('usuário comum se promove a admin', c.put('/users/2', json={'role': 'admin'}, headers=tm).status_code, 403)
checar('usuário altera o próprio nome', c.put('/users/2', json={'name': 'Maria S.'}, headers=tm).status_code, 200)
checar('ADMIN_TOKEN altera outro usuário', c.put('/users/2', json={'name': 'M'}, headers={'Authorization': 'Bearer tok-admin-teste'}).status_code, 200)
checar('DELETE /users/3 sem credencial', c.delete('/users/3').status_code, 401)
checar('senha do admin não foi trocada (login original funciona)', bool(login('joao@email.com', '1234')), True)
print(f"\nresumo: {len(falhas)} falha(s) {falhas}")
sys.exit(1 if falhas else 0)
'''

with tempfile.TemporaryDirectory() as tmp:
    copia = Path(tmp) / "app"
    shutil.copytree(PROJETO, copia, ignore=shutil.ignore_patterns(".venv", "instance", "__pycache__"))
    env = {**os.environ, "ADMIN_TOKEN": "tok-admin-teste"}
    r = subprocess.run([str(PROJETO / ".venv/bin/python"), "-c", SONDA], cwd=copia, env=env, capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith(("PASS", "FAIL", "resumo"))))
    if r.returncode not in (0, 1):
        print(r.stderr[-2000:])
    sys.exit(r.returncode)
