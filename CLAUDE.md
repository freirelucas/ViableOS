# CLAUDE.md — ViableOS

## Project

ViableOS — "The operating system for viable AI agent organizations."
A design tool that structures organizations based on the Viable System Model (VSM) and generates agent configurations.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, LiteLLM, PyMuPDF
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS 4, Zustand
- **No DB** — everything in-memory (Sessions, FileStore). Ephemeral by design.

## Architecture

```
src/viableos/
├── api/
│   ├── chat_routes.py      # Chat SSE streaming + file upload
│   ├── routes.py           # Wizard/config API endpoints
│   └── cda_routes.py       # CDA Sala de Op — agentes, decisões, sinais, bratman, auditoria
├── cda/                    # Núcleo da Corporação Digital Autônoma
│   ├── agente.py           # AgenteGLM com Bratman intention engine
│   ├── bratman.py          # Motor Bratmaniano (intenção, filtro, estratégias)
│   ├── algedonic.py        # Canal algédonico + tabela R4 (GATILHOS_R4 — fonte única)
│   ├── decisoes.py         # Motor de decisões: autonomia, R6 na entrada, papéis
│   ├── auditoria_regras.py # Auditoria das 6 regras + taxa de discordância
│   ├── fabrica.py          # Constrói árvore VSM recursiva + tick real (4 gatilhos)
│   ├── glm.py              # Integração GLM 5.2 + contabilidade de uso (budget)
│   ├── provenancia.py      # Ledger hash-chain + papel organizacional + replay
│   ├── budget_monitor.py   # Monitor de orçamento → sinal DESVIO_ORCAMENTO
│   └── recursao/
│       ├── nivel.py        # NivelVSM (S1-S5 recursivo)
│       ├── orquestrador.py # Orquestrador (bargain, algêdonico, auditoria)
│       ├── clock.py        # Sistema de clocks assimétricos
│       └── bargain.py      # Protocolo de negociação entre níveis
├── chat/
│   ├── engine.py           # LiteLLM streaming, multimodal messages
│   ├── session.py          # In-memory session + message store
│   ├── files.py            # FileStore: PDF/image/text upload processing
│   └── system_prompt.py    # 650-line VSM expert prompt
├── checker.py              # Viability checks (S1-S5) + community warnings
├── assessment_transformer.py  # Assessment JSON → viable_system config
├── budget.py               # Token budget calculation
├── coordination.py         # Auto-generated coordination rules
├── generator.py            # OpenClaw package generator
└── langgraph_generator.py

frontend/src/
├── api/
│   ├── client.ts         # Typed API client (VSM wizard)
│   ├── cdaClient.ts      # Sala de Op client (+ token S5 em postS5)
│   └── trClient.ts       # TR Generator API client
├── components/chat/      # ChatWindow, MessageBubble, ProviderSelector, AssessmentPreview
├── components/wizard/    # 6-step wizard (Template→Units→Budget→Identity→HITL→Review)
├── pages/
│   ├── TRBuilderPage.tsx # 5-step TR Generator wizard (info/perfil/objeto/criterios/revisao)
│   ├── ChatPage.tsx
│   ├── WizardPage.tsx
│   ├── DashboardPage.tsx
│   ├── OpsRoomPage.tsx
│   └── SimulationPage.tsx
├── store/                # Zustand stores (useChatStore, useConfigStore)
└── types/index.ts        # All TypeScript interfaces
```

## Chat Flow

1. User chats with VSM expert (LiteLLM streaming via SSE)
2. Can upload PDFs, screenshots, files (drag&drop, paste, paperclip)
3. LLM conducts a 4-phase assessment interview
4. "Finalize Assessment" extracts JSON from last assistant message
5. "Use in Wizard" transforms → opens Config Wizard
6. Wizard Step 6 (ReviewStep) calls `/api/check` for Viability Report

## SSE Streaming

**Important**: Chunks are sent JSON-encoded (`json.dumps(chunk)`) so that newlines in LLM output don't break the SSE format. Frontend parses with `JSON.parse()`.

## Known Patterns

- API keys only in-memory (never persisted, no localStorage)
- CSS variables instead of hardcoded colors (`var(--color-primary)` etc.)
- Provider abstraction via LiteLLM (Anthropic, OpenAI, Google, DeepSeek, xAI, Ollama)
- `system_prompt.py` contains deep VSM knowledge, but the LLM must NEVER use academic terms

## ⚠️ REGRA ABSOLUTA — NUNCA VIOLAR (leia sempre primeiro)

**A CDA (Corporação Digital Autônoma) é o ÚNICO sistema.**
A CDA é uma corporação de agentes autônomos contratada para **digitalizar o IPEA**.
O TR Generator é apenas um artefato do Projeto 1.

### Hierarquia Ontológica (decorar)

```
CDA (corporação autônoma que digitaliza o IPEA) ← ÚNICO SISTEMA
├── Sala de Operação → onde a DIRETORA gerencia a CDA
├── Membros da corporação (agentes GLM S1-S5)
│   ├── Inteligência (S4)
│   ├── Gestão de Projetos (S3)
│   ├── Auditoria (S3*)
│   ├── Coordenação (S2)
│   ├── Agente Desenvolvedor (S1)
│   ├── Gestor de Bolsas (S1) — alocado no Projeto 1
│   └── Analista de Processos (S1)
├── Projetos que a CDA EXECUTA
│   └── Projeto 1: Gestão de Bolsistas (MVP)
│       ├── Agentes designados: Gestor de Bolsas, Desenvolvedor
│       └── Ferramentas construídas:
│           ├── TR Generator (src/viableos/tr/)
│           └── ... 
└── Artefatos que a CDA PRODUZ
    ├── Termos de Referência, Editais, Relatórios
    ├── Código, Skills, Decisões Documentadas
```

### O Que NUNCA Fazer (checklist auto-auditoria)
- ❌ "O TR Generator é o sistema" → NÃO. É ferramenta do Projeto 1.
- ❌ "A CDA é gestão de bolsistas" → NÃO. A CDA digitaliza o IPEA. Projeto 1 é um dos projetos.
- ❌ Tratar ferramenta como nível de recursão VSM → NÃO. Ferramenta não é sistema viável.
- ❌ Confundir Sala de Operação com interface de ferramenta → NÃO. Sala é para a Diretora gerenciar a CDA.
- ❌ Dizer "o sistema faz X" → QUEM faz é o agente. O sistema É a corporação.
- ✅ SEMPRE: "O agente X, usando ferramenta Y, produziu o artefato Z para o projeto W"

### Narrativa Correta
1. A Diretora IPEA contratou a CDA para digitalizar processos
2. A CDA designou agentes para o Projeto 1: Gestão de Bolsistas
3. O Agente Desenvolvedor construiu o TR Generator como ferramenta
4. O Gestor de Bolsas opera o TR Generator para publicar chamadas
5. A Diretora acompanha tudo pela Sala de Operação
6. A CDA se autodesenvolve: agentes escrevem código e skills

## CDA — Frontend

### Pages
- `CDAPage.tsx` — **Sala de Operação** (painel, agentes, projetos, decisões, sinais)
- `TRBuilderPage.tsx` — Ferramenta do Projeto 1 (acessada pela CDA, não pela Diretora)
- View type: `'cda'` (sidebar: "Sala Op." com Building2 icon)

## Bratman Intention Engine

The CDA's agents use a **Bratmanian intention engine** (`src/viableos/cda/bratman.py`) with three functional roles:

1. **Deliberation**: Filter of admissibility — only compatible desires become intentions
2. **Means-end reasoning**: Plans with steps, executed one at a time
3. **Intention stability**: Three commitment strategies control reconsideration

### Commitment Strategies
- `SINGLE_MINDED` (default S1): Reconsiders only with strong contrary evidence
- `BLIND` (S3*): Never reconsiders — used for audit functions  
- `OPEN` (S4): Always open to reconsideration — used for intelligence

### Filter of Admissibility
`_filtrar_admissiveis()` blocks new intentions whose resource requirements conflict with existing active intentions. Resources are extracted from `Passo.recursos` and compared as sets.

### Six Non-Negotiable Rules
Audited at runtime by `AuditoriaSeisRegras` (`src/viableos/cda/auditoria_regras.py`):
- R1: LLM only in S1 — **imposta na fronteira**: chat com agente (`POST /api/cda/chat/{nome}`) recusa não-S1
- R2: Reversible write envelope (all S1 agents must have git) — artefatos carregam `hash_conteudo` sha-256
- R3: S3* anti-correlated model (different from S1)
- R4: Only 4 algedonic triggers — tabela constante `GATILHOS_R4` em `algedonic.py` (fonte única); API `/api/cda/sinais` valida `gatilho` na entrada; tick da fábrica dispara timeout/conflito/orçamento
- R5: S5 is always human — **imposta**: `require_s5` (JWT escopo admin/cda:s5) em resolver/rejeitar/delegar decisão e responder sinal; identidade vem do `sub` do token, nunca do payload
- R6: Complete decision cascade — **imposta na entrada**: `solicitar()` levanta `ValueError` sem contexto/opções/justificativa; auditoria lê o enum real de status

Proveniência organizacional (`src/viableos/cda/provenancia.py`): papel no ato (`PapelProveniencia`), carimbo de hash da constituição, ledger JSONL append-only com hash-chain; `CDA_STATE_DIR` habilita persistência + replay no startup (`docs/audits/2026-09-03-coerencia-cda.md`).

## CDA — Backend

### Template YAML
- `templates/cda-diest.yaml` — Template da CDA (S1-S5, agentes, projetos, canais algêdonicos)
- Registrado em `api/routes.py` como `"cda-diest"` (7 units)

### Ferramenta do Projeto 1: TR Generator (`src/viableos/tr/`)
- Módulo Python completo (norma, modalidades, format, conformidade, minuta, perfil)
- API REST em `api/tr_routes.py` (prefixo `/api/tr`)
- Frontend: `TRBuilderPage.tsx` (5-step wizard)

### Auth: `src/viableos/api/auth.py` + `auth_routes.py`
JWT com bcrypt. Endpoints: `POST /api/auth/login`, `GET /api/auth/me`.
Ações S5 (resolver/rejeitar/delegar decisão, responder sinal) exigem `require_s5` — token com escopo `admin` ou `cda:s5`. O frontend guarda o token em `localStorage['viableos_token']` (colado na view Decisões da CDAPage) e o envia via `postS5` no cdaClient.

### CDA — Variáveis de ambiente
- `CDA_STATE_DIR` — habilita o ledger de proveniência/persistência (replay no startup). Vazio = modo demo (seed em memória).
- `CDA_ORCAMENTO_USD` — teto mensal para o gatilho R4-2 (0 = monitor inerte).
- `CDA_CUSTO_POR_1K_TOKENS` — preço estimado por 1k tokens (converte uso em custo).

## Testing

### Test Commands
```bash
# TypeScript check
cd frontend && npx tsc --noEmit

# Linting
cd frontend && npm run lint

# Unit Tests (Vitest)
cd frontend && vitest run

# E2E Tests (Playwright – starts dev server automatically)
cd frontend && npx playwright test

# Backend Tests (all)
pytest tests/ -v

# Backend Tests (curated — CDA coherent set)
pytest tests/test_bratman.py tests/test_auditoria_regras.py tests/test_integracao_bratman_cda.py tests/test_consistencia_temporal.py tests/test_decisoes.py tests/test_algedonic.py tests/test_r5_imposicao.py tests/test_provenancia.py -v
```

### Test Files
- `test_bratman.py` (10) — Motor Bratmaniano: intenção, filtro, estratégias
- `test_auditoria_regras.py` (7) — 6 regras inegociáveis da Constituição S5
- `test_integracao_bratman_cda.py` (7) — Bratman dentro da arquitetura VSM
- `test_consistencia_temporal.py` (12) — Clocks, bargain, consistência temporal
- `test_decisoes.py` (15) — R6 na entrada, autonomia, papéis de proveniência
- `test_algedonic.py` (15) — Tabela R4, gatilhos com dedup, budget → sinal
- `test_r5_imposicao.py` (5) — require_s5: 401/403/escopos/token expirado
- `test_provenancia.py` (10) — Ledger hash-chain, carimbo, replay, adulteração

### Test Order for Code Changes
1. **TypeScript Check**: `npx tsc --noEmit` → Must pass without errors
2. **Backend Tests (curated)**: `pytest tests/test_bratman.py tests/test_auditoria_regras.py tests/test_integracao_bratman_cda.py tests/test_consistencia_temporal.py tests/test_decisoes.py tests/test_algedonic.py tests/test_r5_imposicao.py tests/test_provenancia.py -v` → All green?
3. **Full Backend**: `pytest tests/ -v` → Ignore pre-existing failures (UnicodeEncodeError on Windows, missing pytest-asyncio)
4. Only commit when everything is green

### When Tests Fail
- Playwright screenshots: `frontend/tests/e2e/screenshots/`
- Playwright HTML report: `cd frontend && npx playwright show-report`
- Console errors are shown directly in the test output
- Fix the error and re-run the tests before continuing

## Gotchas

- `checker.py`: success_criteria priorities can be `int` or `string` — always cast with `str()`
- `assessment_transformer.py`: Returns `{"viable_system": {...}}`, not just the viable_system
- FileStore is a global singleton (`file_store`) — no cleanup implemented
- `max_tokens=4096` in engine.py — may be too low for long assessment JSONs
