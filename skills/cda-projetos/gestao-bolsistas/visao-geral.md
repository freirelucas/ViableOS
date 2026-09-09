# Projeto 1: Automação da Gestão de Bolsistas

## Status: MVP em produção ✅

Este é o **primeiro projeto** que a Diretora contratou a CDA para executar.
A CDA está construindo e operando as ferramentas de automação da gestão
de bolsistas da DIEST.

## Escopo
1. **TR Generator** ✅ — Geração de Termos de Referência e Editais
2. **Seleção** 🔄 — Análise curricular com GLM, homologação
3. **Acompanhamento** 📋 — Painel do bolsista, relatórios, avaliações
4. **Prestação de Contas** 📄 — Workflow de encerramento

## Agentes Designados
| Agente CDA | Papel no Projeto |
|------------|------------------|
| Gestor de Bolsas | Opera o TR Generator, supervisiona ciclo |
| Agente Desenvolvedor | Codifica novos módulos |
| Auditoria (S3*) | Revisa conformidade PN 317/2025 |
| Coordenação (S2) | Resolve conflitos entre subsistemas |

## Ferramentas Construídas
- `src/viableos/tr/` — Módulo Python de geração
- `api/tr_routes.py` — API REST
- `frontend/src/pages/TRBuilderPage.tsx` — Interface da ferramenta
- `templates/cda-diest.yaml` — Template da CDA (não do TR)

## Skills Associados
- `cda-projetos/gestao-bolsistas/agentes/` — Perfis dos agentes designados
- `cda-projetos/gestao-bolsistas/ferramentas/` — Documentação das ferramentas
