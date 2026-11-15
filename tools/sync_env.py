"""
Cria/atualiza o .env do projeto a partir do .env.example e de um .env "raiz"
compartilhado entre desafios (opcional).

- Se .env não existe, copia .env.example.
- Variáveis VAZIAS no .env são preenchidas com o valor do .env raiz, quando houver.
  Valores já preenchidos nunca são sobrescritos.
- Gera LITELLM_MASTER_KEY aleatória se estiver vazia.
- Nunca imprime valores, só os nomes das variáveis alteradas.

Uso: python scripts/sync_env.py [caminho/do/.env/raiz]   (padrão: ../.env)
"""

import re
import secrets
import shutil
import sys
from pathlib import Path

from dotenv import dotenv_values

PROJECT = Path(__file__).resolve().parent.parent
ENV = PROJECT / ".env"
EXAMPLE = PROJECT / ".env.example"

LINE = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*)=(?P<value>.*)$")


def main() -> int:
    root_env = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT.parent / ".env"

    if not ENV.exists():
        shutil.copy(EXAMPLE, ENV)
        print(f"✓ .env criado a partir de .env.example")

    root = {k: v for k, v in dotenv_values(root_env).items() if v} if root_env.is_file() else {}
    if not root:
        print(f"ℹ️  .env raiz não encontrado ou vazio em {root_env}; nada a copiar")

    filled = []
    lines = ENV.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = LINE.match(line)
        if not m or m["value"].strip():
            continue
        key = m["key"]
        if key == "LITELLM_MASTER_KEY":
            value = "sk-" + secrets.token_urlsafe(24)
        elif key in root:
            value = root[key]
        else:
            continue
        lines[i] = f"{key}={value}"
        filled.append(key)

    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("✓ preenchidas: " + (", ".join(filled) if filled else "nenhuma (já estava tudo preenchido)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
