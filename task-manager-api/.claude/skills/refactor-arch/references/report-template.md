# Template do relatório de auditoria (Fase 2)

O relatório é impresso no terminal e precisa ser salvo como está (é o arquivo `reports/audit-project-N.md`). Siga a estrutura abaixo **na ordem e com os mesmos títulos**. O texto pode estar em português; os títulos das seções ficam como no template.

## Regras de preenchimento

- **Summary:** contagem por severidade igual à lista de findings; `Total` = soma.
- **Ordem:** CRITICAL → HIGH → MEDIUM → LOW. Dentro da severidade, por arquivo e linha.
- **ID:** `F-01`, `F-02`, ... na ordem final. O anti-pattern do catálogo vai entre parênteses no título (`AP-xx`).
- **File:** caminho relativo à raiz do projeto + linha (`app.py:7`), intervalo (`models.py:28-41`) ou lista (`models.py:28, 48-50, 92`). Um finding pode citar mais de um arquivo, um por linha em `File:`.
- **Evidence:** trecho curto copiado do código (1–3 linhas), sem segredos completos: mascare valores sensíveis mantendo só o começo (`'minha-chave-***'`).
- **Description** diz o que está errado neste código; **Impact** diz a consequência concreta; **Recommendation** diz o que fazer e cita a transformação (`T-xx`).
- **Deprecated APIs:** seção obrigatória, mesmo quando vazia.
- O relatório termina com a pergunta de confirmação. Nada é modificado antes da resposta.

## Estrutura

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome da pasta do projeto>
Stack:   <Linguagem> + <Framework> <versão>
Files:   <N> analyzed | ~<L> lines of code
Date:    <AAAA-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| Severity | Findings |
|---|---|
| CRITICAL | F-01, F-02 |
| HIGH | F-03 |
| MEDIUM | ... |
| LOW | ... |

## Findings

### F-01 [CRITICAL] <Nome do anti-pattern> (AP-xx)
File: <arquivo>:<linhas>
Evidence: `<trecho>`
Description: <o que está errado, citando identificadores reais>
Impact: <consequência concreta>
Recommendation: <ação> (T-xx)

### F-02 [CRITICAL] ...

## Deprecated APIs
| Local | API deprecated | Substituto moderno |
|---|---|---|
| <arquivo>:<linha> | `<api>` | `<substituto>` |

(ou: "Nenhuma encontrada. Verificado: <lista do que foi checado>.")

## Architecture Notes
- Arquitetura atual: <classificação da Fase 1>
- Estrutura MVC proposta: <árvore curta de diretórios alvo>
- Contrato a preservar: <N> rotas, comando `<comando>`

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````

## Exemplo de finding bem escrito

```markdown
### F-02 [CRITICAL] SQL Injection (AP-02)
File: repository.py:28, 48-50, 110
Evidence: `cursor.execute("SELECT * FROM items WHERE id = " + str(id))`
Description: 3 funções montam SQL concatenando parâmetros recebidos da rota e do corpo (id, nome, email).
Impact: um corpo com `' OR '1'='1` no login autentica sem senha; dá para ler ou apagar qualquer tabela.
Recommendation: usar consultas parametrizadas (`?` / placeholders) em todas as queries (T-02).
```

Exemplo ruim (não aceito): `File: repository.py` (sem linha), `Description: código inseguro` (genérico), severidade diferente da do catálogo sem justificar.
