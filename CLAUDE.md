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
│   ├── chat_routes.py    # Chat SSE streaming + file upload
│   └── routes.py         # Wizard/config API endpoints
├── chat/
│   ├── engine.py         # LiteLLM streaming, multimodal messages
│   ├── session.py        # In-memory session + message store
│   ├── files.py          # FileStore: PDF/image/text upload processing
│   └── system_prompt.py  # 650-line VSM expert prompt (NEVER expose theory to user)
├── checker.py            # Viability checks (S1-S5) + community warnings
├── assessment_transformer.py  # Assessment JSON → viable_system config
├── budget.py             # Token budget calculation
├── coordination.py       # Auto-generated coordination rules
├── generator.py          # OpenClaw package generator
└── langgraph_generator.py

frontend/src/
├── components/chat/      # ChatWindow, MessageBubble, ProviderSelector, AssessmentPreview
├── components/wizard/    # 6-step wizard (Template→Units→Budget→Identity→HITL→Review)
├── store/                # Zustand stores (useChatStore, useConfigStore)
├── api/client.ts         # Typed API client
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

# Backend Tests
pytest tests/ -v
```

### Test Order for Code Changes
1. **TypeScript Check**: `npx tsc --noEmit` → Must pass without errors
2. **Unit Tests**: `vitest run` → All green?
3. **E2E Tests**: `npx playwright test` → All green?
4. **Backend Tests**: `pytest tests/ -v` → All green?
5. Only commit when everything is green

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
