# Ferramenta: TR Generator

## Status
✅ MVP funcional — 13 seções de TR, 7 checks de conformidade, 8 modalidades

## O Que É
Ferramenta operada pelos agentes **Gestor-Pesquisador** e **Administrativo**
da CDA para gerar Termos de Referência e Editais de Chamada Pública.

## Quem USA
- **Gestor-Pesquisador**: define perfil, critérios, objeto → gera TR → revisa
- **Administrativo**: gera TR → publica chamada → emite termo de outorga

## Como a CDA USA
```
Gestor-Pesquisador (agente GLM)
  → decide: "preciso de um bolsista perfil X para projeto Y"
  → usa GLM para definir: tema, linha, recorte, ênfase, atividades, critérios
  → aciona TR Generator com os parâmetros
  → TR Generator → produz TR + Edital
  → Gestor-Pesquisador revisa → aprova
  → Administrativo publica
```

## Endpoints (API)
```
POST /api/tr/generate    → {type, form} → {sections, text}
POST /api/tr/validate    → {form} → {checks, summary}
POST /api/tr/compose/*   → {perfil, atividades, criterios, objeto}
GET  /api/tr/data/*      → modalidades, diretorias, perfis, norma
```

## Relação com a CDA
TR Generator é UMA DAS FERRAMENTAS. Não confundir com a CDA.
A CDA existiria sem TR Generator (usaria outro meio de publicar chamadas).
O TR Generator não existe sem a CDA (quem o opera são os agentes da CDA).
