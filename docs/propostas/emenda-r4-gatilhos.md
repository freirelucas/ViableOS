# Proposta de Emenda — R4 (Gatilhos Algedônicos)

**Documento:** proposta formal, **não é emenda**. A Constituição S5 só é alterada por decisão da Diretora com justificativa registrada (`CONSTITUICAO_S5.md`, seção "Alterações").
**Data da proposta:** 3 de setembro de 2026.
**Proponente:** agente de auditoria (documentado na `docs/audits/2026-09-03-coerencia-cda.md`, §2.3).

---

## 1. Genealogia do problema

Existem duas listas de gatilhos algedônicos na linhagem do projeto, e a implementação escolheu uma delas:

**Fonte mãe — handout da corporação cibernética (`regras_inegociaveis.md`, Regra 5):**

> Interrompem o humano: (1) **tentativa de ação irreversível**; (2) **teto de orçamento atingido**; (3) conflito cross-projeto / de prioridade; (4) **desvio da constituição S5**. Os dois primeiros são freezes determinísticos **"bloqueia-então-notifica"**; os dois últimos são pedidos semânticos **"notifica-e-espera"**.

A mesma lista consta no briefing de estado da arte (set/2026, regra fechada 6) com a mesma semântica: (a) e (b) bloqueio determinístico; (c) e (d) notificação semântica.

**Fonte local — `CONSTITUICAO_S5.md` R4 (vigente):**

> 1. Timeout de decisão · 2. Desvio orçamentário · 3. Conflito entre agentes · 4. Oportunidade estratégica

**Implementação atual:** o enum `TipoGatilho` (`algedonic.py:25-29`) segue fielmente a lista local — mesmos quatro nomes. A auditoria R4 trava esse conjunto (`auditoria_regras.py:153-178`). Nenhuma semântica de bloqueio existe em nenhum gatilho.

## 2. Análise

| Critério | Lista do handout/briefing | Lista local |
|---|---|---|
| Gatilho de **irreversibilidade** (o mais crítico: ouvindo o canal algedônico, o S5 humano é interrompido *antes* do dano) | Sim — bloqueio determinístico | **Ausente** |
| Bloqueio determinístico (2 de 4) | Sim (irreversível, teto) | **Nenhum** (4 de 4 só notificação) |
| Desvio da constituição como exceção algedônica | Sim — notificação | **Ausente** |
| Timeout de decisão | Ausente (pressupõe tratamento operacional no clock/motor) | Presente como gatilho |
| Oportunidade estratégica | Ausente (fluxo ordinário do S4) | Presente como gatilho |
| Coincidência | conflito (c) ≈ conflito (3); teto (b) ≈ desvio orçamentário (2) | idem |

A lista local operacionalizou dois mecanismos como se fossem gatilhos: o **timeout** (questão de validade de pendências no motor de decisões) e a **oportunidade** (questão de fluxo ordinário de inteligência). Em troca, perdeu o único gatilho que protege contra dano irreversível e o que liga a constituição ao canal algedônico.

## 3. Síntese proposta (mantém "quatro e só quatro")

**R4 emendada:**

1. **Tentativa de ação irreversível** — bloqueio determinístico ("bloqueia-então-notifica"). Nenhuma ação classificada como irreversível executa sem aprovação humana registrada.
2. **Teto orçamentário atingido** — bloqueio determinístico (congela + notifica). *(Subsume o "desvio orçamentário" atual: desvio abaixo do teto continua notificável como dado de orçamento, sem congelamento.)*
3. **Conflito entre agentes/projetos** — notificação ("notifica-e-aguarda orientação").
4. **Desvio da constituição S5** — notificação (a auditoria das 6 regras passa a alimentar o canal algedônico automaticamente quando detecta VIOLADO).

**Reclassificação (não é perda, é alocação correta):**

- **Timeout de decisão** → mecanismo interno do motor de decisões/clock: decisões pendentes além do prazo viram **escalação por cascata** ao S5, sem consumir um slot algedônico. O prazo continua existindo; muda o canal.
- **Oportunidade estratégica** → fluxo ordinário do S4 (inteligência), registrado como decisão RECOMENDACAO. O S4 não precisa de exceção algedônica para chamar a atenção da Diretora — essa é a função dele.

## 4. Impacto na implementação (se aprovada)

- `TipoGatilho` vira: `ACAO_IRREVERSIVEL`, `TETO_ORCAMENTO`, `CONFLITO`, `DESVIO_CONSTITUICAO` — a lista já vive em tabela constante única desde a revisão de coerência de 3/9/2026; a emenda é troca de constante, não de arquitetura.
- Gatilhos 1 e 2 exigem mecanismo de bloqueio na fronteira de execução (envelope R2) — o bloqueio sem envelope é promessa vazia; a emenda **condiciona** os gatilhos bloqueantes à existência do envelope mínimo.
- Gatilho 4 conecta `auditoria_regras` → canal algedônico (hoje o resultado da auditoria não notifica ninguém).
- Testes `test_algedonic.py` seguem a tabela constante (parametrizados — nenhum teste novo precisa nascer da emenda).
- Sinais históricos registrados com a lista antiga permanecem válidos com sua classificação de origem (proveniência preservada).

## 5. Registro de decisão S5

| Campo | Valor |
|---|---|
| Decidido por | *(aguarda Diretora)* |
| Data | — |
| Decisão | [ ] Aprovar síntese · [ ] Manter lista local · [ ] Outra |
| Justificativa registrada | — |

> **Nota do proponente:** a síntese restaura o par "bloqueia/notifica" que a fonte mãe exige e mantém a regra "quatro e só quatro" intacta. Se a decisão for manter a lista local, recomenda-se ao menos registrar na constituição **por que** a CDA dispensa o gatilho de irreversibilidade — hoje a omissão parece acidental, não deliberada.
