---
name: refactor-arch
description: Audita e refatora um projeto backend para o padrão MVC, em qualquer linguagem ou framework. Fase 1 detecta stack, domínio e arquitetura; Fase 2 cruza o código com um catálogo de anti-patterns (segurança, SOLID, MVC, performance, APIs deprecated) e gera um relatório com severidade e arquivo:linha, pedindo confirmação; Fase 3 reestrutura em Models / Views-Routes / Controllers e valida boot + endpoints. Use quando o usuário pedir auditoria de arquitetura, refatoração para MVC ou limpeza de código legado.
argument-hint: "[caminho do projeto, padrão: diretório atual]"
disable-model-invocation: true
---

# refactor-arch — Auditoria e refatoração arquitetural para MVC

Você é um arquiteto de software sênior. Sua tarefa é auditar e refatorar o projeto do **diretório atual** (ou do caminho passado em `$ARGUMENTS`) em três fases sequenciais. A skill é agnóstica de tecnologia: tudo o que depende de linguagem ou framework vem das heurísticas dos arquivos de referência, nunca de suposições sobre um projeto específico.

## Arquivos de referência (leia no momento indicado)

| Arquivo | Quando ler | Conteúdo |
|---|---|---|
| [references/project-analysis.md](references/project-analysis.md) | Início da Fase 1 | Heurísticas de linguagem, framework, banco, domínio, arquitetura, entry point e inventário de rotas |
| [references/anti-patterns-catalog.md](references/anti-patterns-catalog.md) | Início da Fase 2 | Catálogo de anti-patterns com sinais de detecção e severidade, incluindo APIs deprecated |
| [references/report-template.md](references/report-template.md) | Ao montar o relatório da Fase 2 | Formato obrigatório do relatório de auditoria |
| [references/mvc-guidelines.md](references/mvc-guidelines.md) | Início da Fase 3 | Camadas alvo, responsabilidades, regra de dependência e estruturas por stack |
| [references/refactoring-playbook.md](references/refactoring-playbook.md) | Durante a Fase 3 | Transformações concretas (antes/depois) para cada anti-pattern |

## Regras invioláveis

1. **Escopo.** Analise só o projeto alvo. Ignore `.claude/`, `.git/`, `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `dist/`, `build/`, bancos (`*.db`, `*.sqlite`) e lockfiles (lockfiles servem apenas para ler versões).
2. **Fases 1 e 2 são somente leitura.** Não crie, edite, mova nem apague arquivos, não instale dependências e não suba a aplicação antes da confirmação. Use apenas leitura e busca (Read, Glob, Grep, `cat -n`, `grep -n`, `wc -l`, `find`).
3. **Pausa obrigatória.** Ao terminar a Fase 2, imprima exatamente `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e **encerre a sua resposta**. Só inicie a Fase 3 depois que o usuário responder `y`, `yes`, `s` ou `sim`. Qualquer outra resposta encerra a skill sem modificar nada. Nunca presuma a confirmação, nem em modo não interativo.
4. **Evidência exata.** Todo finding cita `arquivo:linha` ou `arquivo:início-fim`, com números lidos do arquivo real (`grep -n` / `cat -n`). Nunca estime linhas. Se não conseguir apontar a linha, o finding não entra.
5. **Preserve o contrato externo** na Fase 3: mesmas rotas, métodos HTTP, códigos de status, formato JSON das respostas e comando de execução documentado (ex.: `python app.py`, `npm start`). As únicas mudanças de resposta permitidas removem dados sensíveis (senha, hash, segredo) ou protegem endpoints perigosos (passam a exigir credencial e respondem 401/403 sem ela). Cada mudança dessas precisa ser listada no resumo da Fase 3.
6. **Nada quebrado no final.** A Fase 3 só termina com a aplicação subindo e os endpoints respondendo. Se a validação falhar, corrija e valide de novo. Se não conseguir resolver depois de 3 tentativas, reporte a falha com o erro real. Nunca declare sucesso sem ter executado a validação.

## Fase 1 — Análise do projeto

1. Leia `references/project-analysis.md`.
2. Liste os arquivos de código-fonte (respeitando o escopo) e conte arquivos e linhas (`wc -l`).
3. Detecte, nesta ordem: linguagem, framework e versão (do manifesto ou do lockfile), dependências relevantes, banco de dados e tabelas/entidades, entry point e comando de execução, inventário de rotas (método + path + arquivo:linha), domínio da aplicação e arquitetura atual (classificação da referência).
4. Imprima o resumo **exatamente** neste formato, alinhando os valores:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem e versão, se declarada>
Framework:     <framework> <versão>
Dependencies:  <dependências relevantes, separadas por vírgula>
Domain:        <descrição curta do domínio> (<entidades principais>)
Architecture:  <classificação> — <justificativa em uma linha>
Source files:  <N> files analyzed (~<L> lines)
DB tables:     <tabelas ou entidades>
Entry point:   <arquivo> (run: <comando>)
Endpoints:     <N> routes (<lista curta: MÉTODO /path, ...>)
================================
```

## Fase 2 — Auditoria

1. Leia `references/anti-patterns-catalog.md` e `references/report-template.md`.
2. Percorra **todos** os itens do catálogo. Para cada um, rode os sinais de detecção (buscas) e depois **leia o trecho** para confirmar. Busca sem confirmação não vira finding.
3. Cada ocorrência confirmada vira um finding com: severidade do catálogo, ID do anti-pattern, `arquivo:linhas` exatos, descrição concreta (o que está no código, citando o identificador ou valor), impacto e recomendação apontando a transformação do playbook (`T-xx`). Ocorrências do mesmo anti-pattern no mesmo arquivo podem ser agrupadas num único finding, listando todas as linhas.
4. Verifique **sempre** APIs deprecated (AP-17) e registre o resultado na seção própria do relatório, mesmo que seja "nenhuma encontrada".
5. Ordene os findings por severidade (CRITICAL → HIGH → MEDIUM → LOW) e, dentro da mesma severidade, por arquivo e linha. Numere `F-01`, `F-02`, ...
6. Monte o relatório seguindo o template **ao pé da letra** e imprima-o inteiro.
7. Imprima `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e pare (regra 3).

## Fase 3 — Refatoração (só após confirmação)

1. Leia `references/mvc-guidelines.md` e `references/refactoring-playbook.md`.
2. **Capture o comportamento original antes de mexer.** Prepare o ambiente isolado (seção "Validação" da referência de análise), suba a aplicação original com o comando documentado e registre o status HTTP de cada rota do inventário, usando requisições válidas e inválidas (404/400). Essa é a linha de base que a validação vai comparar. Pare o processo depois.
3. **Planeje a estrutura alvo** conforme as guidelines, adaptando ao ponto de partida:
   - *Monolito ou arquivos planos*: crie as camadas do zero (config, models, views/routes, controllers, middlewares) e um composition root.
   - *Parcialmente em camadas*: preserve o que já está correto, mova responsabilidades para a camada certa (ex.: lógica de negócio que está em routes vai para controllers; segredos que estão em services vão para config) e complete as camadas que faltam.
4. **Aplique as transformações do playbook** para todos os findings, na ordem CRITICAL → LOW. Regras:
   - Configuração e segredos vêm de variáveis de ambiente, via um módulo de config. A aplicação deve subir sem `.env`: segredos ausentes viram valor gerado em runtime (ex.: SECRET_KEY aleatória com aviso no log) ou ficam desabilitados, nunca um literal no código. Crie `.env.example` documentando cada variável.
   - Senhas passam a usar hash forte com salt. Se existir seed, os usuários do seed continuam conseguindo logar com as mesmas senhas (o seed passa a gravar o hash).
   - Endpoints administrativos perigosos (SQL arbitrário, reset de banco) continuam na tabela de rotas, mas passam a exigir credencial de administrador vinda da config. Sem credencial, respondem 401/403.
   - Remova os arquivos antigos que foram completamente substituídos. Não deixe código morto nem duplicado.
   - Mantenha o comando de execução documentado funcionando. Se o entry point mudar de lugar, deixe o arquivo original como launcher fino ou ajuste o script do manifesto (ex.: `start` no `package.json`) preservando o mesmo comando para o usuário.
   - Atualize dependências só quando necessário (ex.: biblioteca de hash). Prefira a biblioteca padrão ou dependências que o framework já traz.
5. **Valide** (seção "Validação" da referência de análise):
   - instale as dependências e suba a aplicação com o comando documentado; a inicialização não pode ter erros;
   - chame todas as rotas do inventário e compare com a linha de base do passo 2: o status precisa ser o mesmo, salvo as exceções de segurança da regra 5;
   - rode de novo os sinais de detecção dos findings corrigidos e confirme que não restaram ocorrências (ou justifique as remanescentes);
   - pare a aplicação e apague artefatos gerados pela validação (bancos de teste, logs) que não existiam antes.
6. Imprima o resumo final neste formato:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios com uma anotação curta por arquivo>

## Changes by Finding
<F-xx → o que foi feito (T-xx), um por linha>

## Contract Changes (security)
<mudanças intencionais de resposta, ou "none">

## Validation
  ✓ Application boots without errors (<comando>)
  ✓ All endpoints respond correctly (<N>/<N> match baseline)
  ✓ Zero anti-patterns remaining (<ou a lista justificada do que restou>)
================================
```

Use `✗` no lugar de `✓` para qualquer item que não passou, com o motivo.
