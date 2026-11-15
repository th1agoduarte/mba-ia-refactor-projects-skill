"""
Verifica, sem LLM, os requisitos estruturais do desafio:

- skill `refactor-arch` presente nos 3 projetos, com SKILL.md e cópias idênticas;
- SKILL.md com frontmatter, 3 fases e pausa de confirmação antes da Fase 3;
- as 5 áreas de conhecimento cobertas por arquivos de referência em Markdown;
- catálogo com >= 8 anti-patterns, todas as severidades e detecção de APIs deprecated;
- playbook com >= 8 transformações, cada uma com exemplo antes/depois em código;
- relatórios reports/audit-project-{1,2,3}.md (se existirem): >= 5 findings,
  >= 1 CRITICAL/HIGH, arquivo:linha em todo finding, ordem CRITICAL → LOW,
  Summary coerente com a lista e seção de APIs deprecated.

Uso: python tools/check_skill.py [--reports]   (--reports torna os relatórios obrigatórios)
"""

import filecmp
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ["code-smells-project", "ecommerce-api-legacy", "task-manager-api"]
SKILL = Path(".claude/skills/refactor-arch")
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

failures = 0


def check(ok: bool, msg: str) -> bool:
    global failures
    failures += not ok
    print(f"  {'✓' if ok else '✗'} {msg}")
    return ok


def tree_equal(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    return not mismatch and not errors and all(tree_equal(a / d, b / d) for d in cmp.common_dirs)


def check_skill() -> None:
    base = ROOT / PROJECTS[0] / SKILL
    print("Skill")
    for p in PROJECTS:
        check((ROOT / p / SKILL / "SKILL.md").is_file(), f"{p}/{SKILL}/SKILL.md existe")
    for p in PROJECTS[1:]:
        if (ROOT / p / SKILL).is_dir():
            check(tree_equal(base, ROOT / p / SKILL), f"cópia em {p} idêntica à do projeto 1")

    skill = (base / "SKILL.md").read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
    check(bool(fm) and re.search(r"^name:\s*refactor-arch\s*$", fm.group(1), re.M) is not None,
          "frontmatter com name: refactor-arch")
    check(bool(fm) and "description:" in fm.group(1), "frontmatter com description")
    for n, word in [(1, "Análise"), (2, "Auditoria"), (3, "Refatoração")]:
        check(re.search(rf"^## Fase {n} — {word}", skill, re.M) is not None, f"SKILL.md define a Fase {n} — {word}")
    check("Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]" in skill, "Fase 2 termina pedindo confirmação [y/n]")
    check(re.search(r"somente leitura", skill, re.I) is not None, "Fases 1 e 2 declaradas somente leitura")
    check(re.search(r"boot|sobe|subir", skill, re.I) is not None and "endpoint" in skill.lower(),
          "Fase 3 valida boot + endpoints")

    refs = {f.name: f.read_text(encoding="utf-8") for f in (base / "references").glob("*.md")}
    print("Referências (5 áreas de conhecimento, Markdown)")
    areas = {
        "Análise de projeto": ("project-analysis.md", ["Linguagem", "Framework", "Banco de dados", "arquitetura"]),
        "Catálogo de anti-patterns": ("anti-patterns-catalog.md", ["Sinais", "Severidade"]),
        "Template de relatório": ("report-template.md", ["ARCHITECTURE AUDIT REPORT", "## Summary", "## Findings"]),
        "Guidelines de arquitetura": ("mvc-guidelines.md", ["Models", "Controllers", "Views"]),
        "Playbook de refatoração": ("refactoring-playbook.md", ["ANTES", "DEPOIS"]),
    }
    for area, (name, words) in areas.items():
        text = refs.get(name, "")
        check(bool(text) and all(w.lower() in text.lower() for w in words), f"{area}: {name}")

    catalog = refs.get("anti-patterns-catalog.md", "")
    entries = re.findall(r"^### (AP-\d+) — (.+)$", catalog, re.M)
    index = dict(re.findall(r"^\| (AP-\d+) \| .+? \| ([A-Z /]+) \|$", catalog, re.M))
    sev_found = {s for v in index.values() for s in SEVERITIES if s in v}
    print("Catálogo")
    check(len(entries) >= 8, f"{len(entries)} anti-patterns (mínimo 8)")
    check(sev_found == set(SEVERITIES), f"severidades distribuídas: {sorted(sev_found)}")
    check(re.search(r"deprecated", catalog, re.I) is not None and "Equivalente moderno" in catalog,
          "inclui detecção de APIs deprecated com equivalente moderno")
    no_signal = [ap for ap, _ in entries if not re.search(rf"### {ap} —.*?\*\*Sinais", catalog, re.S)]
    check(not no_signal, "todo anti-pattern tem sinais de detecção")

    playbook = refs.get("refactoring-playbook.md", "")
    sections = re.split(r"^## (?=T-\d+)", playbook, flags=re.M)[1:]
    with_examples = [s.split("\n", 1)[0] for s in sections if "ANTES" in s and "DEPOIS" in s and s.count("```") >= 4]
    print("Playbook")
    check(len(sections) >= 8, f"{len(sections)} transformações (mínimo 8)")
    check(len(with_examples) == len(sections), f"{len(with_examples)}/{len(sections)} com código antes/depois")


def check_report(n: int, required: bool) -> None:
    path = ROOT / "reports" / f"audit-project-{n}.md"
    print(f"Relatório {path.relative_to(ROOT)}")
    if not path.is_file():
        check(not required, "arquivo existe" if required else "ainda não gerado (ok antes da execução)")
        return
    text = path.read_text(encoding="utf-8")
    findings = re.findall(r"^### (F-\d+) \[(CRITICAL|HIGH|MEDIUM|LOW)\] (.+)$", text, re.M)
    blocks = re.split(r"^### F-\d+ ", text, flags=re.M)[1:]
    sevs = [s for _, s, _ in findings]
    check("ARCHITECTURE AUDIT REPORT" in text and "## Summary" in text and "## Findings" in text,
          "segue o template (cabeçalho, Summary, Findings)")
    check(len(findings) >= 5, f"{len(findings)} findings (mínimo 5)")
    check(any(s in ("CRITICAL", "HIGH") for s in sevs), "pelo menos 1 CRITICAL ou HIGH")
    check(sevs == sorted(sevs, key=SEVERITIES.index), "ordenados CRITICAL → LOW")
    no_line = [f for f, b in zip(findings, blocks) if not re.search(r"^File: .+:\d+", b, re.M)]
    check(not no_line, "todo finding tem arquivo:linha" + (f" (faltando: {[f[0] for f in no_line]})" if no_line else ""))
    summary = re.search(r"CRITICAL: (\d+) \| HIGH: (\d+) \| MEDIUM: (\d+) \| LOW: (\d+)", text)
    if check(bool(summary), "linha de Summary presente"):
        counts = dict(zip(SEVERITIES, map(int, summary.groups())))
        check(all(counts[s] == sevs.count(s) for s in SEVERITIES), f"Summary bate com a lista {counts}")
    check("## Deprecated APIs" in text, "seção de APIs deprecated presente")
    check("Proceed with refactoring (Phase 3)? [y/n]" in text, "termina com o pedido de confirmação")


def main() -> int:
    required = "--reports" in sys.argv
    check_skill()
    for n in (1, 2, 3):
        check_report(n, required)
    print(f"\n{'✅ tudo ok' if not failures else f'❌ {failures} verificação(ões) falharam'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
