# Versão de Teste — v0.3.0rc1

**Data:** 9 de setembro de 2026.
**Base:** `fda43b2` (coerência constitucional) + auditoria dinâmica/cosmológica de 09/09.
**Veredicto da auditoria:** mundo coerente; fisiologia com laços abertos conhecidos (D1–D5 em `docs/audits/2026-09-09-coerencia-dinamica-cosmologica.md`) — nenhum bloqueia o teste.

## O que é esta versão

Primeira versão em que a constituição R1–R6 está **imposta na fronteira HTTP**, não apenas no núcleo, e em que a corporação **renasce com memória** (ledger de proveniência com replay no startup).

- **Modo demo** (padrão, sem `CDA_STATE_DIR`): efêmero, semeado — para mostrar a Sala de Op.
- **Modo ledger** (com `CDA_STATE_DIR`): estado persistente, seed desligado — para uso real. `/health` informa `"modo": "demo"|"ledger"`.

## Como rodar (Windows, dev)

```powershell
cd ViableOS
.\start-dev.ps1          # API :8000 + frontend :5173
```

Login dev: `admin` / `admin123` → copie o token em **Sala Op. → Decisões** para resolver/rejeitar/delegar.

## Smoke automático (testar no ar)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\teste-no-ar.ps1
```

17 passos: boot, login, R6 na entrada, R5 (401 sem token; identidade do JWT), R4 (gatilho inválido), constituição, health/boot, kill, **restart com replay do ledger**, nenhuma pendente fantasma.

## Roteiro manual sugerido (30 min)

1. **Boot demo** (`start-dev.ps1`) — Sala de Op mostra seed (2 decisões, 1 sinal amarelo).
2. **R6**: tente criar decisão sem justificativa via API → deve recusar com motivo R6.
3. **R5**: resolva a decisão "Priorizar sprint 3…" — sem token → 401; com token colado → ok; o histórico mostra `resolvido_por` do token, não do payload.
4. **R4**: `POST /api/cda/sinais` com `gatilho: "qualquer"` → rejeitado; com `gatilho: "oportunidade_estrategica"` → aceito.
5. **Ledger**: pare a API, suba com `$env:CDA_STATE_DIR="C:\temp\cda-estado"`, crie/resolva uma decisão, mate o processo, reinicie com o MESMO `CDA_STATE_DIR` → decisão resolvida sobrevive no histórico; `/health` mostra `modo: ledger`.
6. **Auditoria**: `GET /api/cda/health/boot` (13 checks) e `GET /api/cda/auditoria/discordancia`.

## Limitações conhecidas (não são bugs novos)

- **D1**: resposta do S5 não desce ao agente de origem (sinal original fica pendente no subnível).
- **D2**: conflito de intenções sinaliza 1× e silencia enquanto persistir.
- **D3**: alerta de orçamento é one-shot — sem reset mensal automático.
- **C3**: constituição ainda não declara a doutrina de memória (ledger).
- Gatilhos bloqueantes (irreversível/teto) só existem na emenda R4, aguardando decisão da Diretora.

## Verificação executada nesta revisão

- Suíte curada: 101/101 · suíte completa: 404 passam (82 falhas preexistentes, nenhuma em módulo CDA)
- `tsc -b` + `vite build` de produção: limpos
- Smoke ao vivo: 17/17 (dois boots reais + replay)
