# Desafio 02 — Skill refactor-arch. Rode `make help`.
#
# P=1|2|3 escolhe o projeto:
#   1 = code-smells-project (Python/Flask)
#   2 = ecommerce-api-legacy (Node.js/Express)
#   3 = task-manager-api (Python/Flask)
#
# PROVIDER escolhe o LLM do Claude Code na execução da skill:
#   (vazio)    login atual do Claude Code (padrão)
#   anthropic  ANTHROPIC_API_KEY do .env
#   aws        AWS Bedrock (CLAUDE_CODE_USE_BEDROCK=1)
#   google     gateway LiteLLM -> Gemini (Docker)
#   openai     gateway LiteLLM -> OpenAI (Docker)
#   gateway    alias de google (testa o gateway)

SHELL := /bin/bash
-include .env

P ?= 1
PROJ_1 := code-smells-project
PROJ_2 := ecommerce-api-legacy
PROJ_3 := task-manager-api
PROJ := $(PROJ_$(P))
ifeq ($(PROJ),)
  $(error P inválido: '$(P)'. Use 1, 2 ou 3)
endif
SKILL_SRC := $(PROJ_1)/.claude/skills/refactor-arch
EVID := docs/evidencias
GATEWAY_URL := http://localhost:$(or $(GATEWAY_PORT),4000)

PROVIDER ?=
GATEWAY_ENV = ANTHROPIC_BASE_URL=$(GATEWAY_URL) ANTHROPIC_AUTH_TOKEN=$(LITELLM_MASTER_KEY) ANTHROPIC_API_KEY=
ifeq ($(PROVIDER),)
  RUN_ENV :=
else ifeq ($(PROVIDER),anthropic)
  RUN_ENV := ANTHROPIC_API_KEY=$(ANTHROPIC_API_KEY) CLAUDE_MODEL=$(ANTHROPIC_LLM_MODEL)
else ifeq ($(PROVIDER),aws)
  RUN_ENV := CLAUDE_CODE_USE_BEDROCK=1 AWS_REGION=$(AWS_REGION) CLAUDE_MODEL=$(AWS_LLM_MODEL)
else ifneq ($(filter $(PROVIDER),google gateway),)
  RUN_ENV = $(GATEWAY_ENV) CLAUDE_MODEL=gemini/$(GOOGLE_LLM_MODEL) ANTHROPIC_DEFAULT_HAIKU_MODEL=gemini/$(GOOGLE_LLM_MODEL)
  NEEDS_GATEWAY := 1
else ifeq ($(PROVIDER),openai)
  RUN_ENV = $(GATEWAY_ENV) CLAUDE_MODEL=openai/$(OPENAI_LLM_MODEL) ANTHROPIC_DEFAULT_HAIKU_MODEL=openai/$(OPENAI_LLM_MODEL)
  NEEDS_GATEWAY := 1
else
  $(error PROVIDER inválido: '$(PROVIDER)'. Use anthropic | aws | google | openai | gateway)
endif
ENSURE_GATEWAY = $(if $(NEEDS_GATEWAY),@$(MAKE) --no-print-directory gateway-up,@true)

.PHONY: upstream help setup env check-env smoke check citations test test-one contract contract-all contract-baseline sync-skill \
        skill skill-audit skill-refactor run gateway-up gateway-down gateway-logs gateway-test clean

help: ## Lista os alvos
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo "  P=1|2|3 escolhe o projeto; PROVIDER=anthropic|aws|google|openai troca o LLM do agente"

setup: ## Prepara os 3 projetos (venv Python + npm install) e o .env
	@for p in $(PROJ_1) $(PROJ_3); do \
	  (cd $$p && [ -d .venv ] || uv venv -q .venv) && uv pip install -q -p $$p/.venv/bin/python -r $$p/requirements.txt && echo "✓ $$p"; done
	@cd $(PROJ_2) && npm install --no-audit --no-fund --silent && \
	  (node -e "require('sqlite3')" 2>/dev/null || npm rebuild sqlite3 --foreground-scripts >/dev/null) && \
	  node -e "require('sqlite3')" && echo "✓ $(PROJ_2)"
	@$(MAKE) --no-print-directory env

env: ## Cria/completa o .env a partir do .env.example + ../.env (não imprime segredos)
	@uv run -q --no-project --with python-dotenv python tools/sync_env.py

check: ## Requisitos estruturais da skill e dos 3 relatórios (sem LLM)
	@python3 tools/check_skill.py --reports

citations: upstream ## Confere arquivo:linha + Evidence de cada finding no código ORIGINAL (upstream/main)
	@python3 tools/verify_citations.py

test: check citations contract-all ## Validação completa: estrutura, citações e contrato HTTP dos 3 projetos

test-one: upstream ## Uma verificação: T=skill|reports|citations|contract (contract usa P=)
	@case "$(T)" in \
	  skill) python3 tools/check_skill.py ;; \
	  reports) python3 tools/check_skill.py --reports ;; \
	  citations) python3 tools/verify_citations.py ;; \
	  contract) $(MAKE) --no-print-directory contract P=$(P) ;; \
	  *) echo "use T=skill|reports|citations|contract"; exit 1 ;; esac

check-env: ## Ferramentas e configuração do agente, sem imprimir segredos
	@command -v claude >/dev/null && echo "✓ $$(claude --version)" || echo "✗ claude não encontrado (instale o Claude Code)"
	@for c in node npm uv python3 docker; do command -v $$c >/dev/null && echo "✓ $$c" || echo "✗ $$c"; done
	@echo "PROVIDER: $(or $(PROVIDER),login do Claude Code)"
	@case "$(PROVIDER)" in \
	  anthropic) v=ANTHROPIC_API_KEY ;; aws) v="AWS_ACCESS_KEY_ID AWS_LLM_MODEL" ;; \
	  google|gateway) v="GOOGLE_API_KEY LITELLM_MASTER_KEY" ;; openai) v="OPENAI_API_KEY OPENAI_LLM_MODEL LITELLM_MASTER_KEY" ;; *) v= ;; esac; \
	  for k in $$v; do n=$$(grep -E "^$$k=" .env 2>/dev/null | cut -d= -f2- | tr -d '\n' | wc -c); \
	    [ "$$n" -gt 0 ] && echo "✓ $$k ($$n caracteres)" || echo "✗ $$k vazio no .env"; done

smoke: ## Uma chamada curta ao Claude Code com o PROVIDER escolhido (custo mínimo)
	$(ENSURE_GATEWAY)
	@$(RUN_ENV) claude -p "Responda apenas: ok" --max-turns 1 $$( [ -n "$$CLAUDE_MODEL" ] && echo --model "$$CLAUDE_MODEL") | sed 's/^/✓ resposta: /'

contract: ## Sobe o projeto P e compara todos os endpoints com o contrato original
	@python3 tools/contract_test.py p$(P) --out $(EVID)/contract/p$(P)-depois.json --baseline $(EVID)/contract/p$(P)-antes.json $(if $(PORT),--port $(PORT)) --server-log $(EVID)/apps-rodando/p$(P)-server.log

contract-all: ## Contrato HTTP dos 3 projetos
	@set -e; for p in 1 2 3; do $(MAKE) --no-print-directory contract P=$$p; done

contract-baseline: ## (Re)grava o contrato ORIGINAL do projeto P. Só faz sentido no código legado
	@git diff --quiet upstream/main -- $(PROJ) ':!$(PROJ)/.claude' || { echo "✗ $(PROJ) já foi alterado; use: git stash / git worktree com upstream/main"; exit 1; }
	@python3 tools/contract_test.py p$(P) --out $(EVID)/contract/p$(P)-antes.json

sync-skill: ## Copia a skill do projeto 1 para o projeto P (2 ou 3)
	@[ "$(P)" != 1 ] || { echo "P=1 é a origem"; exit 1; }
	@rm -rf $(PROJ)/.claude/skills/refactor-arch && mkdir -p $(PROJ)/.claude/skills && \
	  cp -r $(SKILL_SRC) $(PROJ)/.claude/skills/ && echo "✓ skill copiada para $(PROJ)"

skill: ## Executa /refactor-arch no projeto P: Fases 1-2, pausa, depois Fase 3 com "y"
	$(ENSURE_GATEWAY)
	@echo "→ /refactor-arch no projeto $(P) | LLM: $(or $(PROVIDER),login do Claude Code)"
	@$(RUN_ENV) python3 tools/run_skill.py $(P) --phase all

skill-audit: ## Só as Fases 1-2 (somente leitura); salva reports/audit-project-P.md
	$(ENSURE_GATEWAY)
	@echo "→ Fases 1-2 no projeto $(P) | LLM: $(or $(PROVIDER),login do Claude Code)"
	@$(RUN_ENV) python3 tools/run_skill.py $(P) --phase 12

skill-refactor: ## Responde "y" à sessão da auditoria e executa a Fase 3 (ANSWER=n para recusar)
	$(ENSURE_GATEWAY)
	@echo "→ Fase 3 no projeto $(P) (resposta: $(or $(ANSWER),y)) | LLM: $(or $(PROVIDER),login do Claude Code)"
	@$(RUN_ENV) python3 tools/run_skill.py $(P) --phase 3 --answer $(or $(ANSWER),y)

run: ## Sobe o projeto P em primeiro plano, com o comando documentado
	@case $(P) in \
	  1) cd $(PROJ) && .venv/bin/python app.py ;; \
	  2) cd $(PROJ) && npm start ;; \
	  3) cd $(PROJ) && .venv/bin/python seed.py && .venv/bin/python app.py ;; esac

gateway-up: ## Sobe o gateway LiteLLM (Docker) e espera ficar saudável
	@docker compose up -d --wait llm-gateway >/dev/null && echo "✓ gateway em $(GATEWAY_URL)"

gateway-down: ## Derruba o gateway
	docker compose down

gateway-logs: ## Logs do gateway
	docker compose logs -f llm-gateway

gateway-test: gateway-up ## Uma chamada /v1/messages (API da Anthropic) -> Gemini pelo gateway
	@curl -sf $(GATEWAY_URL)/v1/messages -H "x-api-key: $(LITELLM_MASTER_KEY)" -H "anthropic-version: 2023-06-01" \
	  -H "content-type: application/json" \
	  -d '{"model":"gemini/$(GOOGLE_LLM_MODEL)","max_tokens":256,"messages":[{"role":"user","content":"Responda só: ok"}]}' \
	  | python3 -c "import json,sys; d=json.load(sys.stdin); print('✓ gateway -> Gemini:', d['content'][0]['text'].strip(), '| modelo:', d.get('model'))"

clean: ## Remove bancos e logs gerados pelos testes
	rm -f $(PROJ_1)/loja.db $(PROJ_3)/tasks.db $(PROJ_3)/instance/tasks.db tools/.*-server.log tools/.run-*.log

upstream: ## Garante o remote upstream (repositório base) usado nas comparações; cria no clone limpo
	@git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/devfullcycle/mba-ia-refactor-projects-skill.git
	@git fetch -q upstream
