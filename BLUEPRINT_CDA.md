# CDA — Corporação Digital Autônoma para Digitalização do IPEA

> **A CDA não é um sistema de gestão de bolsistas.**
> A CDA é uma **corporação de agentes autônomos** contratada para
> **digitalizar processos do IPEA**. A gestão de bolsistas é apenas
> o primeiro projeto (MVP). A Sala de Operação é onde a **Diretora
> e sua equipe gerenciam a CDA**.

---

## O Que é a CDA

A CDA (Corporação Digital Autônoma) é uma **pessoa jurídica digital** —
uma organização completa composta de agentes de IA (GLM 5.2) que:

1. **Recebe contratos** da Diretora IPEA para automatizar processos
2. **Executa projetos** usando seus agentes especializados
3. **Se autodesenvolve** — seus agentes Desenvolvedores escrevem código
4. **Presta contas** via Sala de Operação (Ops Room)
5. **Escala problemas** via canais algêdonicos quando algo foge do controle

### Analogia

```
IPEA (cliente)
  └── Contrata a CDA para digitalizar processos
       ├── Projeto 1: Automação da Gestão de Bolsistas (MVP)
       │   └── Ferramenta: TR Generator
       ├── Projeto 2: Automatizar fluxo de contratação
       ├── Projeto 3: Automatizar prestação de contas
       └── Projeto N: (o que a Diretora decidir)
```

---

## Quem Usa a Sala de Operação

| Papel | O que faz na Sala de Operação |
|-------|-------------------------------|
| **Diretora IPEA** | Monitora KPIs, aprova decisões críticas, responde a canais algêdonicos |
| **Equipe de Confiança** | Atribui projetos à CDA, revisa entregas, direciona prioridades |
| **CDA (agentes)** | Aparecem na Sala como membros da corporação — status, decisões pendentes, sinais |

A Diretora NÃO usa o TR Generator diretamente. Ela **determina o que a CDA deve fazer**, e a CDA usa o TR Generator para executar.

---

## Estrutura da CDA

```
Sala de Operação (interface da Diretora) ← você está aqui
  │
  ▼
CDA (corporação autônoma)
  ├── S5: Diretora (humana — decide o quê)
  ├── S4: Inteligência Estratégica (agente — detecta oportunidades)
  ├── S3: Gestão de Projetos (agente — aloca recursos, define prioridades)
  ├── S3*: Auditoria (agente — conformidade, qualidade)
  ├── S2: Coordenação (agente — resolve conflitos entre projetos)
  └── S1: Agentes Executantes (cada um = especialista)
      ├── Desenvolvedor (escreve código)
      ├── Analista de Processos (mapeia fluxos)
      ├── Gestor de Bolsas (opera TR Generator — PROJETO 1)
      ├── ... (novos agentes criados conforme novos projetos)
```

---

## A Sala de Operação (Ops Room da CDA)

A Sala mostra à Diretora:

### 1. Painel Geral
- Status da CDA (operacional/em alerta/em crise)
- Projetos ativos e seu progresso
- KPIs corporativos (taxa de automação, tempo de resposta, satisfação)

### 2. Agentes da CDA
- Quem são, o que estão fazendo agora, status (online/trabalhando/erro)
- Decisões pendentes que precisam de aprovação humana
- Comunicação direta com cada agente

### 3. Canais Algêdonicos
- Sinais vermelhos (emergência — resposta em 24h)
- Sinais amarelos (atenção — resposta em 48h)
- Sinais verdes (informativo)

### 4. Workflow de Projetos
- Novos projetos solicitados
- Projetos em execução
- Projetos concluídos
- Artefatos produzidos

---

## Fluxo de Trabalho Típico

```
1. DIRETORA na Sala de Operação:
   "Precisamos automatizar a gestão de bolsistas."
   
2. CDA-S4 (Inteligência) analisa e propõe:
   "Vou dividir em 4 subprojetos: TR Generator, Seleção, Acompanhamento, Contas."
   
3. CDA-S3 (Gestão) aloca:
   "Agente Desenvolvedor, prioridade máxima para TR Generator."
   
4. CDA-S1 (Agente Desenvolvedor) executa:
   Cria o módulo Python, API, frontend, skills.
   
5. CDA-S3* (Auditoria) revisa:
   "Código aprovado. Conforme com PN 317/2025."
   
6. SALA DE OPERAÇÃO notifica Diretora:
   "TR Generator concluído. Pronto para produção."
   
7. DIRETORA aprova:
   "Publicar."
```

---

## O MVP (TR Generator) no Contexto Correto

O TR Generator **não é um sistema**. É um **artefato** que a CDA produziu
no seu primeiro projeto. A CDA continha existir sem ele.

```
Antes (ERRADO):    "O TR Generator faz... o TR Generator tem..."
Depois (CORRETO):  "A CDA, através do seu agente Gestor de Bolsas,
                    usando a ferramenta TR Generator, produziu o
                    Termo de Referência para a chamada X."
```

---

## Localização dos Componentes

```
C:\Users\r1843101\Documents\teste_openCode\ViableOS\
│
├── BLUEPRINT_CDA.md              ← Este documento
├── skills/
│   ├── cda-core.md                ← Regra: CDA é o sistema
│   ├── cda-sala-operacao/         ← Skills da Sala de Operação
│   ├── cda-projetos/              ← Skills de projetos da CDA
│   │   └── gestao-bolsistas/      ← Projeto 1: Gestão de Bolsistas
│   │       ├── tr-generator.md    ← Ferramenta que a CDA construiu
│   │       └── ... 
│   ├── cda-agentes/               ← Skills dos tipos de agente
│   └── infraestrutura/            ← Skills técnicos
│
├── src/viableos/
│   ├── api/
│   │   ├── tr_routes.py           ← API da ferramenta TR Generator
│   │   ├── cda_routes.py          ← API da Sala de Operação (futuro)
│   │   └── ...
│   ├── tr/                        ← Módulo TR Generator (ferramenta)
│   └── cda/                       ← Núcleo da CDA (futuro)
│
└── frontend/src/
    ├── pages/
    │   ├── CDAPage.tsx            ← Sala de Operação da CDA
    │   └── TRBuilderPage.tsx      ← Interface da ferramenta TR Generator
    │                               (acessada pela CDA, não pela Diretora)
    └── ...
```

---

## Regras de Ouro

1. **A CDA é a corporação que digitaliza o IPEA** — não é um sistema de gestão
2. **A Sala de Operação é para a Diretora** — ela gerencia a CDA, não opera ferramentas
3. **TR Generator é um artefato do Projeto 1** — não é o sistema
4. **Agentes são membros da corporação** — não são funções ou perfis
5. **A CDA se autodesenvolve** — seus agentes escrevem código e skills
6. **GLM 5.2 é o cérebro de cada agente** — um modelo, todos os agentes
7. **Humanos decidem O QUÊ, a CDA decide COMO**
