# Auditoria de Coerência da CDA — 3 de setembro de 2026

**Objeto:** núcleo CDA (`src/viableos/cda/`), camada de API (`src/viableos/api/`) e camada de registro do ViableOS.
**Método:** auditoria somente-leitura, cruzamento de três fontes normativas contra a implementação, com verificação de fontes primárias do estado da arte (benchmarking de 3/9/2026).
**Autoridade:** diagnóstico produzido por agente; **nenhuma decisão S5 foi tomada aqui**. A proposta de emenda à R4 (ver `docs/propostas/emenda-r4-gatilhos.md`) aguarda aprovação da Diretora.

---

## 1. Matriz de coerência — três fontes, um código

Fontes normativas: (A) `CONSTITUICAO_S5.md` local; (B) handout da corporação cibernética (`regras_inegociaveis.md`, seis regras); (C) briefing de estado da arte (set/2026, regras fechadas da Parte 1.2).

| Regra | A (local) | B (handout) | C (briefing) | Implementação | Veredito |
|---|---|---|---|---|---|
| LLM só no S1 | R1 | R3 (canais determinísticos) | Regra 1 | ✓ no pacote `cda/` — única fronteira LLM em `glm.py:22`; ✗ `agente_chat_routes.py:16-27` alimenta persona de S2–S4 ao LLM | Fronteira violável |
| Envelope reversível | R2 | R1 + negação abaixo do agente | Regras 2–3 | "git" existe só como string em `fabrica.py:122,134,146` e como substring checada em `auditoria_regras.py:84`. Nenhum código executa git/branch/draft/rate-limit/reversão | **Ausente como mecanismo** |
| Anticorrelação S3\* | R3 | R4 | Regra 5 | Declarativa: `fabrica.py:88` (claude-3-5-sonnet) vs S1 glm; o campo `modelo` nunca é usado para chamar nada — auditoria é Python puro | Conforme-decorativo |
| Quatro gatilhos | R4: timeout / orçamento / conflito / **oportunidade** | R5: **irreversível [bloqueio]** / teto [**bloqueio**] / conflito / desvio-constituição | Regra 6 (idem B) | Enum local fiel (`algedonic.py:25-29`), mas **todos os 4 são só notificação; 3 de 4 nunca disparam** (ver §2.3) | Incoerente com B/C; inócuo consigo |
| S5 humano | R5 | Vetos absolutos (só humano faz merge) | Regra 7 + R6 (S5 é humano) | Sem agente S5 na fábrica (conforme), mas `POST /decisoes/{id}/resolver` **não tem autenticação** (`cda_routes.py:224-239`); `resolvido_por` aceita qualquer string; S3\* e S1-dev têm autonomia TOTAL (`decisoes.py:30,32`) | **Frágil** |
| Cascata rastreável | R6 | "Nunca afirmar resultado sem proveniência rastreável" | C1 (esquema de proveniência) | `DecisaoWorkflow` tem todos os campos (`decisoes.py:38-54`), mas `solicitar()` aceita cascata vazia; check R6 compara `status=="resolvida"` que nunca ocorre (`auditoria_regras.py:207`); histórico exportado omite contexto/opções/justificativa (`cda_routes.py:375-384`) | Parcial — convenção, não imposição |
| Intenção persistente | *(ausente)* | R2 — obrigatória em substrato sem estado; "agente amnésico reiniciado por cron é o gerador de deriva" | Regra 4 | Estado 100% em memória — 9 singletons de módulo; restart apaga intenções, decisões pendentes, sinais e auditoria | **Ausente — viola B** |
| Começar mínimo | *(ausente)* | R6 — "cada ausência é uma decisão, não uma lacuna" | Regra 7 + antiobjetivo 4.5 | Singleton no import constrói árvore completa + seed (`fabrica.py:218`, `seed.py`) | Divergência a registrar |

## 2. Achados com evidência

### 2.1 O que está certo (e deve ser preservado)

O núcleo é **admiravelmente determinístico**: zero chamadas de LLM em decisões (`decisoes.py`), canal algedônico (`algedonic.py`), auditoria (`auditoria_regras.py`), clocks (`clock.py`), bargain (`bargain.py`) e fábrica (`fabrica.py`). A única fronteira LLM do pacote é `glm.py:22` (`glm_chat` → IpeaGPT) — o desenho "variedade onde se trabalha, confiabilidade onde se guarda" (Ashby, Regra 3 do handout) está correto no código. O motor Bratman implementa filtro de admissibilidade, três estratégias de compromisso, planos parciais e verificação de coerência entre agentes (`bratman.py:98-123, 83-95, 43-77, 342-362`), com 10 testes travando o comportamento.

### 2.2 Falhas de integridade

1. **Split-brain de singletons.** O seed registra decisões no `motor` global (`seed.py:54-81`) e sinal no `canal` global (`seed.py:106-114`), mas a API lê/escreve via `nivel.motor`/`nivel.canal` (`cda_routes.py:88,313`; `nivel.py:35-36`). Sinais e decisões semeados são invisíveis na Sala de Op.
2. **`NameError` latente** em `orquestrador.py:52` — usa `logger.warning` sem `import logging`.
3. **Duplicação de sinais por tick** — `propagar_sinais()` (`orquestrador.py:35-67`) copia sinais pendentes do filho ao pai a cada tick sem dedup ou marcação; crescimento ilimitado de cópias não respondidas.
4. **Endpoint quebrado** — `GET /agentes/{nome}` (`cda_routes.py:52-64`) itera `listar_agentes()` (objetos `AgenteGLM`) como se fossem decisões, acessando atributos inexistentes.
5. **`nivel` hardcoded** — `SinalAlgedonico.nivel` é sempre `"R3-S1"` (`algedonic.py:86`).
6. **Health check de boot vazio** — `cda_routes.py:460-468` passa `fabrica.arvore()` (chave `agentes`) para checks que procuram `config["agents"]`; todos os checks R1–R5 passam com lista vazia.
7. **R6-audit cega** — `auditar_regras` coleta histórico sem `status` (`orquestrador.py:126-131`); ignora canal/motor da raiz; não audita `justificativa` nem `solicitante`.

### 2.3 Gatilhos algedônicos: declarados, nunca disparados

| Gatilho | Detector que existe | Por que nunca dispara |
|---|---|---|
| `timeout_decisao` | `verificar_timeouts()` (`algedonic.py:159-166`) | Nenhum chamador |
| `desvio_orcamento` | `budget_monitor` (`budget_monitor.py:87-131`) | Triplamente morto: `tokens_usados` nunca populado (`fabrica.py:179` vs `clock.py:156`); `definir_orcamento` nunca chamado → `orcado=0` → `continue` (`budget_monitor.py:96-98`); singleton criado sem canal (`budget_monitor.py:219,54`) → `_disparar_sinal` aborta |
| `conflito_agentes` | `agenda_bratman.verificar_coerencia()` (`bratman.py:342`) | Detecta conflitos mas `disparar_conflito` (`algedonic.py:118-128`) não tem chamador |
| `oportunidade_estrategica` | `disparar_oportunidade` (`algedonic.py:130-140`) | Sem chamador |

Agravante: `POST /api/cda/sinais` não aceita parâmetro `gatilho` (`cda_routes.py:313-319`) → todo sinal manual é classificado como `timeout_decisao` por default. E **nenhum gatilho tem semântica de bloqueio** — o briefing exige 2 bloqueantes (irreversível, teto), o handout idem; a implementação tem 0.

### 2.4 R5 (S5 humano) sem imposição técnica

- `resolver()` aceita qualquer `resolvido_por` (default `"Diretora"`, `decisoes.py:112`) — o endpoint de resolução não exige JWT nem escopo (`auth.py` existe mas não é dependência do `cda_router`).
- `AUTONOMIA_POR_TIPO` dá TOTAL a `s3_auditoria` e `s1_desenvolvedor` (`decisoes.py:30,32`) — auto-aprovam com `opcoes[0]` sempre (`decisoes.py:91-98`), sem análise.
- `NivelAutonomia.NENHUMA` declarada (`decisoes.py:16`) e nunca tratada.

### 2.5 Proveniência ausente (cruzamento com o benchmark de 2026)

- Zero `hashlib` em `src/` — nenhum hash de código/entrada/saída em artefatos (`autodesenvolvimento.py:33-44` registra `caminho` + `linhas`) ou anexos (`chat/files.py:17-24`).
- Timestamps simples ISO-UTC (`decisoes.py:50`, `algedonic.py:49`), não assinados, sem cadeia.
- Nenhum registro carrega **papel organizacional** estruturado (S1 executou / S3\* replicou / S5 humano aprovou) — `solicitante` e `resolvido_por` são strings spoofáveis sem vínculo com o JWT.
- Nenhum registro carrega **versão/hash da constituição vigente**; `GET /api/cda/constituicao` relê o disco a cada request sem carimbar.
- Compromisso bratmaniano não é referenciado por decisões/sinais — impossível reconstruir "sob qual compromisso esta afirmação foi feita".
- Evidência multimodal do chat evapora: conteúdo injetado só em `messages[-1]` do turno corrente (`engine.py:114-116`); a sessão guarda só `AttachmentMeta` sem hash (`session.py:16-20`); `FileStore` nunca re-injeta.
- `AgenteGLM.historico` é write-only (`agente.py:93,121-126`) — nunca exposto.

### 2.6 Comportamento testado vs. não testado

**Travado:** Bratman (10 testes — filtro, estratégias, coerência), auditoria R1/R2/R5/R6 (8), integração Bratman-CDA (7), consistência temporal (12), coordenação (13), topology (12), budget monitor local (8), health check sintético.

**Sem cobertura:** `decisoes.py` inteiro (zero testes), `algedonic.py` inteiro (zero testes), `propagar_sinais` (dedup/NameError), R3 e R4 da auditoria, loop real do Clock, rotas `/api/cda/*` (o endpoint quebrado nunca foi pego por esse motivo), fronteira R1 do chat, perda de estado.

## 3. Aprendizados do benchmark → consequências para as features

| Aprendizado (verificado em fonte primária) | Consequência |
|---|---|
| **CaMeL** (arXiv 2503.18813, DeepMind+ETH, 2025) — control/data flow extraído da query confiável; dados não-confiáveis nunca afetam o fluxo; **imposição fora-de-banda por design** | O modelo CDA (canais determinísticos) está certo, mas **imposição inócua é não-imposição**: a fronteira precisa interceptar *ação*, não só registrar decisão |
| **Família out-of-band** — FIDES, Progent, RTBAS, FORGE organizadas como Bibi/reference monitor/least privilege (arXiv 2606.26479); CaMeL anterior a OCL/Faramesh/KAIJU | A genealogia "terreno ocupado" começa antes, na segurança clássica; envelope/ratelimit de escrita é reference monitor, não feature nova |
| **Caveat de avaliação adaptativa** (idem 2606.26479): defesas validadas só em benchmarks estáticos quebraram a >90% sob ataque adaptativo | Testes atuais validam caminho feliz; os dois módulos de governança zero-testados são exatamente onde o adversário bate (quem resolve sem auth? o que acontece com sinal duplicado?) |
| **PACT** (arXiv 2605.11039): proveniência a nível de argumento, "authority binding" | Papel estruturado no registro (S1/S3\*/S5-humano) + hash de evidência + vínculo JWT→ato — as lacunas exatas do §2.5. PACT é proveniência *de segurança*; a CDA reivindica proveniência *organizacional de pesquisa* — citação obrigatória para manter a distinção defensável |
| **MAST** (arXiv 2503.13657): ~79% das falhas multiagente = especificação e coordenação | Split-brain do seed, gatilhos desconectados, duplicação de sinais são falhas de *coordenação*, não de capacidade — prioridade sobre qualquer nova feature |
| **Terminal-Bench 2.1**: +12 pontos percentuais vieram de manutenção de benchmark, não engenharia | Health check de boot vazio que sempre passa = métrica inócua (o "denominador comprimido" em miniatura); consertar o morto antes de construir novo |
| **METR** (arXiv 2503.14499, NeurIPS 2025): horizonte de tarefa dobra ~7 meses | Trabalho de longo horizonte exige **intenção persistida** (Regra 2 do handout); restart que apaga intenções é o teto prático do horizonte da CDA |
| **PaperBench** (arXiv 2504.01848): replicação medida por rubrica hierárquica; melhor agente 21%, humano vence | S3\* real = **taxa de discordância registrada como dado**, não persona declarativa; o campo sabe medir replicação — a CDA deve registrar, não "auditar" |
| **Pilha de assinatura** (Sigstore/RFC 3161/SLSA/in-toto/W3C VC): padrão existente para atestação de proveniência | Timestamps assináveis e `resolvido_por` spoofável são o Gap Part 11 em miniatura; hash-chain append-only é o mínimo viável hoje, a pilha completa é roadmap |

## 4. Worklist desta revisão

**P0 — fazer o que existe funcionar**
1. [x] Ligar os 4 gatilhos: `verificar_timeouts` no tick da fábrica (com dedup por decisão); `verificar_coerencia` → `disparar_conflito` (com dedup por par de intenções); orçamento real (`glm.py` contabiliza tokens/custo a cada chamada, singleton conectado ao canal da raiz no startup, `definir_orcamento` via `CDA_ORCAMENTO_USD`); `POST /sinais` aceita e valida `gatilho` contra a tabela.
2. [x] R5 imposta: `Depends(require_s5)` (escopo admin/cda:s5) em resolver/rejeitar/delegar/responder-sinal; `resolvido_por` e `resolvido_por_sub` derivados do `sub` do JWT; `NENHUMA` tratada (sobe ao S5 com feedback explícito).
3. [x] Bugs: logger importado no orquestrador; dedup na propagação (`propagado_para`, persistido no ledger); endpoint `/agentes/{nome}` corrigido (motor do nível do agente, filtrado por solicitante); `nivel` real do sinal (não hardcoded); R6-audit com enum real + justificativa/solicitante/papéis; health/boot com `{"agents": [...]}`; health/periodico com sinais e budget reais; seed escreve nos objetos por nível (fim do split-brain); `_historico_completo` exporta a cascata inteira; `verificar_desvio(tick=...)` com argumento correto e sem dupla contagem.
4. [x] Testes: `test_decisoes.py` (15), `test_algedonic.py` (15), `test_r5_imposicao.py` (5), `test_provenancia.py` (10).

**P1 — coerência constitucional**
5. [x] R1 no chat: `glm_chat` negado para agentes não-S1 (`agente_chat_routes.py`).
6. [x] R6 na entrada: `solicitar()` levanta `ValueError` sem contexto/opções/justificativa ("decisões sem cascata são nulas").
7. [x] R2 honesta: `hash_conteudo` SHA-256 obrigatório nos artefatos quando há conteúdo (param `conteudo` ou leitura do `caminho`), com flag `verificado`; anexos do chat carregam `sha256` (FileStore + AttachmentMeta + histórico).

**P2 — proveniência**
8. [x] `cda/provenancia.py`: `PapelProveniencia` (S1_EXECUTOU / S3STAR_REPLICOU / S5_HUMANO_APROVOU / CONTROLE_DETERMINISTICO + mapeamento por tipo), hash-chain append-only (`LedgerProveniencia`), carimbo de versão+hash da constituição em todo registro, `verificar_cadeia()`.
9. [x] Campos de papel em decisões/sinais (`papel_origem`, `papel_aprovacao`, `resolvido_por_sub`, `constituicao_hash`, `intencao_id`); resolução carimba `sub` do JWT; hash nos attachments.
10. [x] Persistência JSONL append-only com replay no startup (`CDA_STATE_DIR`; sem a variável = modo demo com seed, comportamento anterior preservado). Nenhum novo deployment obrigatório.
11. [x] Taxa de discordância S3* como dado: `GET /api/cda/auditoria/discordancia` (proxy estrutural, nota explícita de que não é veredito; S3*-LLM real é roadmap).

**Registro de decisões pendentes (S5)**
- [ ] Emenda R4 (síntese das listas de gatilhos) — proposta em `docs/propostas/emenda-r4-gatilhos.md`, aguarda Diretora.

**Fora de escopo de código nesta revisão (roadmap)**
- Envelope git completo (integração com runtimes externos OpenClaw/LangGraph).
- S3*-LLM anticorrelacionado real (exige segundo provider em produção).
- Timestamp assinado RFC 3161/Sigstore (hash-chain é o mínimo de hoje).
- `topology.py` fail-open → fail-closed (delicado: o mapeamento recursivo `f"s{sub.nivel}"` depende dele; registrar e mudar com teste dedicado).
- Persistência SQLite do `docs/plans/2026-02-20-runtime-engine.md` (v0.3; JSONL é o passo mínimo).
- Autodegradação de modelo no teto orçamentário (docstring do BudgetMonitor promete; bloqueio de fato é gatilho da emenda R4).

## 4.1 Registro de execução (mesma data)

Executado em modo autônomo autorizado; verificação em 09/09/2026:

| Verificação | Resultado |
|---|---|
| `pytest` dos 4 arquivos novos (45 testes) | 45 aprovados |
| Suporte curada (bratman, auditoria, integração, temporal) | 37/37 aprovados |
| Suíte completa backend | 385 aprovados; 82 falhas = as duas categorias preexistentes documentadas no CLAUDE.md (UnicodeEncodeError cp1252 nos geradores; pytest-asyncio ausente) — nenhuma em módulo CDA |
| `npx tsc --noEmit` (frontend) | sem erros |

Alterações de comportamento visíveis:
- Resolver/rejeitar/delegar decisão e responder sinal agora exigem JWT (401/403 sem token/escopo); a CDAPage ganhou campo de token S5 na view Decisões.
- Agentes S2-S4 não conversam via LLM (R1) — o chat direto retorna erro explicativo.
- Solicitar decisão sem cascata completa retorna erro (R6).
- `s1_desenvolvedor` passou de TOTAL para RECOMENDACAO (decisão técnica §2.4 — não requer emenda ministerial).
- Com `CDA_STATE_DIR` definido o estado sobrevive a restart (replay do ledger); sem a variável, o modo demo anterior é preservado.

## 5. Convenção daqui em diante

- Toda nova feature cita o aprendizado do benchmark que a motiva (rastro de proveniência do diagnóstico).
- Nenhuma regra constitucional é alterada por agente — só proposta documentada, decisão da Diretora.
- A auditoria das 6 regras passa a consumir a estrutura real dos registros (incluindo raiz e `status` do enum).
