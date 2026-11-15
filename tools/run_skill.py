"""
Executa a skill /refactor-arch num projeto com o Claude Code em modo headless,
em DUAS etapas, para provar a pausa obrigatória da Fase 2:

  etapa 1  claude -p "/refactor-arch"   só com ferramentas de LEITURA liberadas
           → Fase 1 + Fase 2 + pergunta "[y/n]"; o processo termina aí.
           O relatório (output da Fase 2) é salvo em reports/audit-project-N.md.
  etapa 2  claude -p --resume <sessão> "y"   com edição e Bash liberados
           → Fase 3 (refatoração + validação).

Uso: python tools/run_skill.py N [--phase 12|3|all] [--answer y]
Saídas: docs/evidencias/skill-runs/pN-fase1-2.md, pN-fase3.md, pN-session.json

Variáveis opcionais: CLAUDE_MODEL (ex.: claude-sonnet-5-5) e as do provider
(CLAUDE_CODE_USE_BEDROCK, ANTHROPIC_BASE_URL...), que o Makefile injeta via PROVIDER=.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = {1: "code-smells-project", 2: "ecommerce-api-legacy", 3: "task-manager-api"}
OUT = ROOT / "docs" / "evidencias" / "skill-runs"

# Etapa 1: nada que escreva em disco. Edit/Write/NotebookEdit e Bash genérico ficam negados.
READ_ONLY_TOOLS = [
    "Read", "Glob", "Grep",
    "Bash(grep:*)", "Bash(find:*)", "Bash(wc:*)", "Bash(cat:*)", "Bash(ls:*)",
    "Bash(head:*)", "Bash(tail:*)", "Bash(sort:*)", "Bash(tree:*)", "Bash(awk:*)",
]
DENY_WRITE = ["Edit", "Write", "NotebookEdit"]
PHASE3_TOOLS = ["Read", "Glob", "Grep", "Edit", "Write", "Bash"]


def claude(args: list[str], cwd: Path) -> dict:
    cmd = ["claude", "-p", *args, "--output-format", "json"]
    if os.environ.get("CLAUDE_MODEL"):
        cmd += ["--model", os.environ["CLAUDE_MODEL"]]
    print("$", " ".join(cmd), f"(cwd={cwd.name})", flush=True)
    start = time.time()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0 and not proc.stdout.strip():
        sys.exit(f"claude falhou ({proc.returncode}): {proc.stderr[-2000:]}")
    data = json.loads(proc.stdout)
    data["_wall_seconds"] = round(time.time() - start, 1)
    return data


def meta_lines(data: dict) -> list[str]:
    usage = data.get("usage") or {}
    return [
        f"- Sessão: `{data.get('session_id')}`",
        f"- Turnos: {data.get('num_turns')} | duração: {data.get('_wall_seconds')} s"
        f" | custo estimado: US$ {data.get('total_cost_usd', 0):.2f}",
        f"- Tokens: entrada {usage.get('input_tokens', 0)} (+cache {usage.get('cache_read_input_tokens', 0)})"
        f", saída {usage.get('output_tokens', 0)}",
        f"- Status: {data.get('subtype')} | erro: {data.get('is_error')}",
    ]


def extract_report(text: str) -> str:
    """Do separador que precede 'ARCHITECTURE AUDIT REPORT' até o fim (inclui a pergunta [y/n])."""
    idx = text.find("ARCHITECTURE AUDIT REPORT")
    if idx < 0:
        return text
    start = text.rfind("================================", 0, idx)
    lines = text[start if start >= 0 else idx:].strip().splitlines()
    while lines and set(lines[-1].strip()) <= {"`"}:  # remove a cerca de código final (``` ou ````)
        lines.pop()
    return "\n".join(lines).rstrip() + "\n"


def phase12(n: int) -> str:
    cwd = ROOT / PROJECTS[n]
    data = claude(["/refactor-arch", "--permission-mode", "default",
                   "--allowedTools", *READ_ONLY_TOOLS, "--disallowedTools", *DENY_WRITE], cwd)
    text = data.get("result", "")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"p{n}-fase1-2.md").write_text(
        "\n".join([f"# Projeto {n} — {PROJECTS[n]}: Fases 1 e 2 (saída bruta do Claude Code)", "",
                   f"Comando: `cd {PROJECTS[n]} && claude -p \"/refactor-arch\"` (só ferramentas de leitura liberadas)",
                   *meta_lines(data), "", "---", "", text]), encoding="utf-8")
    report = ROOT / "reports" / f"audit-project-{n}.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text(extract_report(text), encoding="utf-8")
    (OUT / f"p{n}-session.json").write_text(json.dumps({"session_id": data.get("session_id")}), encoding="utf-8")
    git = subprocess.run(["git", "status", "--porcelain", "--", PROJECTS[n]], cwd=ROOT, capture_output=True, text=True).stdout
    changed = [l for l in git.splitlines() if "/.claude/" not in l]
    print(text[-1500:])
    print(f"\n✓ relatório salvo em {report.relative_to(ROOT)}")
    print("✓ nenhum arquivo do projeto modificado nas Fases 1-2" if not changed else f"✗ arquivos modificados: {changed}")
    return data.get("session_id")


def phase3(n: int, answer: str) -> None:
    cwd = ROOT / PROJECTS[n]
    session = json.loads((OUT / f"p{n}-session.json").read_text())["session_id"]
    data = claude(["--resume", session, answer, "--permission-mode", "acceptEdits",
                   "--allowedTools", *PHASE3_TOOLS], cwd)
    text = data.get("result", "")
    (OUT / f"p{n}-fase3.md").write_text(
        "\n".join([f"# Projeto {n} — {PROJECTS[n]}: Fase 3 (saída bruta do Claude Code)", "",
                   f"Comando: `claude -p --resume {session} \"{answer}\"` (resposta à pergunta da Fase 2)",
                   *meta_lines(data), "", "---", "", text]), encoding="utf-8")
    print(text[-3000:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=int, choices=sorted(PROJECTS))
    ap.add_argument("--phase", choices=["12", "3", "all"], default="all")
    ap.add_argument("--answer", default="y")
    args = ap.parse_args()
    if args.phase in ("12", "all"):
        phase12(args.project)
    if args.phase in ("3", "all"):
        phase3(args.project, args.answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
