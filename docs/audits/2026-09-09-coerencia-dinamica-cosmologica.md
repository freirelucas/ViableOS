# Auditoria de Coerência Dinâmica e Cosmológica — CDA

**Data:** 9 de setembro de 2026.
**Escopo:** o trabalho inteiro — constituição, handout, núcleo CDA, API, frontend, seeds, testes, documentação.
**Método:** duas lentes complementares à auditoria estática de 03/09/2026 (que comparou *listas* e *estados*):

1. **Lente cosmológica** — a CDA é *um só mundo*? A ontologia declarada (constituição, CLAUDE.md, handout) coincide com a ontologia executável (código, seed, API)? Há fraturas entre o que o sistema *diz que é* e o que ele *é*?
2. **Lente dinâmica** — os laços fecham? Um organismo viável não é um organograma: é um conjunto de ciclos de feedback que se retroalimentam no tempo. Onde a dor sobe sem a cura descer? Onde o alerta se extingue sozinho? O que a memória (ledger) ressuscita e o que ela ressuscita errado?

Veredicto curto: **o mundo é coerente; a fisiologia tem laços abertos.** Nenhuma fractura ontológica; cinco laços dinâmicos abertos ou amortecidos demais, registrados abaixo como D1–D5.

---

## 1. Lente cosmológica

### C1 — Ontologia única e íntegra ✓

Constituição (`CONSTITUICAO_S5.md`), blueprint (`CLAUDE.md`), fábrica (`fabrica.py`), seed (`seed.py`) e frontend contam **a mesma história, linha a linha**: a CDA é a corporação que digitaliza o IPEA; o Projeto 1 é a Gestão de Bolsistas; o TR Generator é *artefato construído pelo Agente Desenvolvedor*, não sistema; a Sala de Operação é o espaço da Diretora. Verificado:

- `fabrica.py:45-49` — propósito da raiz: "Digitalizar processos do IPEA como corporação autônoma de agentes GLM".
- `seed.py:19-57` — tarefas e artefatos do Projeto 1 (prestação de contas, PN 317/2025, SISBOLSAS, ComprasNet): o mundo sociotécnico é o IPEA de ponta a ponta.
- Hierarquia de agentes S4→S1 idêntica em `fabrica.py` e na seção "Hierarquia Ontológica" do `CLAUDE.md`.
- Nenhuma rota, prompt ou teste trata o TR Generator como sistema.

### C2 — Lei escrita = lei viva (R4) ✓

A constituição vigente (lista local de 4 gatilhos) é o que o código impõe — `GATILHOS_R4` em `algedonic.py` é a tabela única, validada na entrada de sinais, na auditoria e no tick. A emenda (`docs/propostas/emenda-r4-gatilhos.md`) existe **só como proposta** — nenhuma superposição quântica entre lei escrita e lei viva.

### C3 — A constituição não conhece a memória ⚠

O princípio 4 ("Transparência total") ganhou corpo: o ledger de proveniência (`provenancia.py`) faz a CDA **reencarnar** — o processo morre, a corporação lembra (`CDA_STATE_DIR` + replay no startup). Mas:

- A constituição não declara doutrina de memória/reencação;
- `CLAUDE.md` ainda abre com "No DB — everything in-memory. Ephemeral by design" — o *charter* da ferramenta nega a fisiologia da corporação que descreve depois.

Fratura de baixo custo: uma linha na constituição ("A CDA persiste seu estado de decisão/sinal por ledger imutável; a morte do processo não apaga a corporação") e correção do CLAUDE.md resolveriam.

### C4 — "S5 é humano" tornou-se "S5 é credencial" ⚠

R5 está tecnicamente imposta (`require_s5`, identidade do JWT, nunca do payload). Mas a implementação prova **posse de credencial**, não humanidade. A constituição fala de *Diretora IPEA (humana)*; o sistema conhece `sub="admin"`. Para a versão de teste é suficiente; para o cosmologista, a ressalva: o sistema não sabe quem é humano, sabe quem tem a chave.

### C5 — O corpo sem reflexos (herdado do handout) ⚠

O handout (fonte mãe) exige gatilhos **bloqueia-então-notifica** (irreversível, teto); a constituição local só conhece **notifica-e-espera**. A CDA hoje *sente* dor mas não tem reflexo espinhal: nenhum sinal impede execução. A emenda R4 propõe o conserto e o condiciona ao envelope R2. Até lá, vale registrar: a cosmologia vigente é a de um organismo que relata tudo e não se protege de nada.

### C6 — Tensão S3* TOTAL × R5 ⚠

`AUTONOMIA_POR_TIPO` (`decisoes.py:36-45`) dá autonomia **TOTAL** a `s3_auditoria`: a auditoria decide e executa (`opcoes[0]`) sem humano — em tensão com R5 ("a decisão final é sempre humana"). A justificativa registrada (BLIND, função de auditoria) é razoável, mas a constituição não conhece a exceção. Recomendação: uma linha em R5 ("exceto atos de auditoria da S3*, que se auto-executam sob envelope reversível") ou rebaixar S3* para LIMITADA.

---

## 2. Lente dinâmica

### D1 — Loop de cura aberto: a resposta nunca desce ⟲ (achado central)

A dor sobe: `propagar_sinais()` copia sinais pendentes dos subníveis para cima (`orquestrador.py:38-77`), com dedup por `propagado_para` — correto. Mas a **cura nunca desce**:

- `MotorDecisoes.resolver/rejeitar/delegar` (`decisoes.py:155-201`) move a decisão para o histórico e registra no ledger — **nenhum mecanismo informa o agente solicitante**;
- `CanalAlgedonico.responder` (`algedonic.py:189`) marca `resolucao` **na cópia propagada** (nível de cima); o sinal original no subnível fica `resolucao=None` para sempre (`orquestrador.py:42` filtra apenas pendentes — a cópia respondida deixa de propagar, o original adoece sozinho).

Consequência fisiológica: o organismo sente dor, o cérebro delibera, o membro não cicatriza. Os agentes GLM são stateless e não "sentem" a pendência hoje, então o dano prático é baixo — mas qualquer consumidor futuro do estado (S1 real, dashboard de agente) herdaria a mentira: sinal pendente que já foi respondido lá em cima.

**Correção mínima sugerida:** ao responder sinal propagado, marcar o original (propagação em ambas as direções do *estado*, não do ruído) e ao resolver decisão, registrar ação no agente (`agente.registrar_acao`).

### D2 — Conflito crônico silenciado pelo dedup ⟲

O gatilho de conflito dispara uma vez por par de intenções (`fabrica.py:197-205`), mas **nada remove as intenções conflitantes** — nem resolução, nem expiração. Resultado: o conflito persiste no Bratman para sempre e o canal cala para sempre. Dor crônica que o analgésico do dedup esconde. A resposta humana ao sinal deveria (opcionalmente) revogar uma das intenções; hoje só documenta.

### D3 — Orçamento: alerta one-shot, sem ciclo mensal ⟲

`BudgetMonitor._alertas_disparados` (`budget_monitor.py:59,112,126`) nunca é limpo — `resetar()` existe (linha 219) e **não tem chamador**. O orçamento é *mensal* na cosmologia (`CDA_ORCAMENTO_USD`), mas a dinâmica não tem fronteira de mês: o uso acumula para sempre, o primeiro alerta amarelo e o primeiro vermelho disparam uma única vez na vida do processo, e o sinal de excesso do mês seguinte nunca chega. **Correção mínima:** no tick, comparar `datetime.utcnow().month` com o mês do último alerta e chamar `resetar()` na virada.

### D4 — Memória fiel no renascimento ✓

Ponto alto da auditoria dinâmica: o replay (`provenancia.py`) preserva `resolucao` **e** `propagado_para` (linhas 306-307) — após restart, sinais respondidos não ressuscitam como pendentes e sinais propagados não re-propagam. Provado no smoke ao vivo (`scripts/teste-no-ar.ps1`, passos 14-17) e nos testes de replay (`test_provenancia.py`, `test_ciclo_vida_cda.py`). A morte do processo não zera a memória nem a duplica.

### D5 — Dois modos de existência ⟲

O mesmo organismo tem duas ontologias de tempo: **modo demo** (sem `CDA_STATE_DIR`: efêmero, semeado, renasce igual a cada boot) e **modo ledger** (persistente, seed desligado). Coerente por design e documentado (`CLAUDE.md`, docstring de `main.py`), mas o operador precisa saber em qual universo está: a Sala de Op idêntica pode ser memória de demonstração ou verdade viva. Sugestão para a versão de teste: o `/health` já expõe `version`; expor também `modo: demo|ledger` (uma linha em `main.py`/`cda_routes.py`).

### D6 — Órgãos vestigiais ⚠

Os singletons de compatibilidade `motor` (`decisoes.py:263`) e o singleton algedônico de `algedonic.py` ficam **órfãos da árvore** — qualquer código que os importe escreve num órgão fora do corpo (o bug do seed, §2.2 da auditoria de 03/09, nasceu daí). Já foram neutralizados no seed e nos hooks, mas continuam importáveis. Removê-los quebraria compatibilidade; no mínimo, `DeprecationWarning` no acesso.

### D7 — Versão dividida ⚠ (corrigido nesta revisão)

`pyproject.toml` dizia `0.2.0`; `main.py` dizia `0.3.0` — a ferramenta e a corporação não sabiam quantos anos têm. Unificado em `0.3.0rc1` nesta revisão.

---

## 3. Veredicto

| Dimensão | Nota |
|---|---|
| Coerência cosmológica | **Sólida** — um mundo, uma história, sem fracturas ontológicas; ressalvas doutrinárias C3–C6 são de documentos, não de código |
| Coerência dinâmica | **Funcional com laços abertos** — D1 (cura não desce) e D3 (sem ciclo mensal) são os dois laços que a próxima revisão deve fechar |
| Memória e renascimento | **Fiel** — replay não duplica, não ressuscita morto, preserva proveniência |

Nada aqui bloqueia a versão de teste: os laços abertos são limitações fisiológicas conhecidas, registradas com correção mínima proposta.

## 4. Roteiro da versão de teste (v0.3.0rc1)

Ver `docs/versao-teste-v0.3.0rc1.md`.
