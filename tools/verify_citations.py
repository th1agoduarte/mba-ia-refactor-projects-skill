"""
Confere se as citações dos relatórios batem com o código ORIGINAL (upstream/main):
para cada finding, TODOS os arquivos citados em `File:` precisam existir no commit original,
as linhas citadas precisam caber em cada arquivo e o trecho de `Evidence:` precisa aparecer
em um deles, dentro de ±3 linhas de alguma linha citada (trechos mascarados com *** são
comparados só até a máscara). Trecho com menos de 8 caracteres falha; finding sem
Evidence é contado à parte, não como conferido.

Uso: python tools/verify_citations.py [--ref upstream/main]
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = {1: "code-smells-project", 2: "ecommerce-api-legacy", 3: "task-manager-api"}


def original(ref: str, path: str) -> list[str] | None:
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else None


def cited_lines(spec: str) -> list[int]:
    out = []
    for a, b in re.findall(r"(\d+)(?:-(\d+))?", spec):
        out += list(range(int(a), int(b or a) + 1))
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else "upstream/main"
    total = ok = no_evidence = 0
    for n, proj in PROJECTS.items():
        text = (ROOT / "reports" / f"audit-project-{n}.md").read_text(encoding="utf-8")
        print(f"\nreports/audit-project-{n}.md ({proj})")
        for block in re.split(r"^### ", text, flags=re.M)[1:]:
            fid = block.split()[0]
            if not fid.startswith("F-"):
                continue
            cites, in_file = [], False
            for line in block.splitlines()[1:]:
                if line.startswith("File:") or (in_file and line.startswith((" ", "\t")) and ":" in line):
                    in_file = True
                    cites += re.findall(r"([\w./-]+\.\w+):([\d][\d,\s-]*)", line.replace("File:", ""))
                elif in_file:
                    in_file = False
            m_ev = re.search(r"^Evidence: `(.*)`\s*$", block, re.M)
            total += 1
            if not cites:
                print(f"  ✗ {fid}: sem File: arquivo:linha")
                continue
            problems, windows = [], []
            for path, spec in cites:
                src = original(ref, f"{proj}/{path}")
                lines = cited_lines(spec)
                if src is None:
                    problems.append(f"{path} não existe no original")
                elif not lines or max(lines) > len(src):
                    problems.append(f"{path}:{spec.strip()} fora do arquivo ({len(src)} linhas)")
                else:
                    windows.append((path, src, lines))
            if problems:
                print(f"  ✗ {fid}: " + "; ".join(problems))
                continue
            label = ", ".join(f"{p}:{s.strip()}" for p, s in cites)[:70]
            if not m_ev:
                no_evidence += 1
                print(f"  ~ {fid}: {label} existe, mas sem Evidence (trecho não conferível)")
                continue
            raw = m_ev.group(1).replace("\\`", "`")
            # Evidence pode ter vários trechos (`a` / `b`); cada um com >= 8 caracteres é testado.
            parts = [norm(x)[:60] for x in re.split(r"\*\*\*|\.\.\.|…|`", raw)]
            parts = [x for x in parts if len(x) >= 8 and x not in ("/", "//")]
            if not parts:  # trecho vazio ou curto demais casaria com qualquer linha
                print(f"  ✗ {fid}: Evidence curta demais para conferir (`{raw[:40]}`)")
                continue
            snippet, hit = parts[0], False
            for path, src, lines in windows:
                win = sorted({i for l in lines for i in range(max(1, l - 3), min(len(src), l + 3) + 1)})
                text = norm(" ".join(src[i - 1] for i in win))
                found = next((x for x in parts if x in text), None)
                if found:
                    snippet, hit = found, True
                    break
            ok += hit
            print(f"  {'✓' if hit else '✗'} {fid}: {label} ← `{snippet[:50]}`")
    failed = total - ok - no_evidence
    print(f"\n{total} findings: {ok} com o trecho conferido na linha citada do código original, "
          f"{no_evidence} sem Evidence (só arquivo e linhas conferidos), {failed} com divergência")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
