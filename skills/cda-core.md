# CORE RULE: CDA é o Sistema, Ferramentas são Artefatos

## REGRA ABSOLUTA — NUNCA VIOLAR

A **CDA-DIEST** (Corporação Digital Autônoma) é o ÚNICO sistema.
Tudo que não é a CDA é **artefato** ou **ferramenta** que a CDA produz ou usa.

### Hierarquia Ontológica

```
CDA-DIEST (sistema vivo, VSM, autônomo)
├── Membros da corporação (agentes GLM S1-S5)
│   ├── Gestor-Pesquisador
│   ├── Coordenador de Área
│   ├── DIDES Auditor
│   ├── Comissão Julgadora
│   ├── Bolsista
│   ├── Administrativo
│   └── Agente Desenvolvedor
│
├── Ferramentas que os membros OPERAM
│   ├── TR Generator (gera TRs/Editais)
│   ├── GLM 5.2 (sistema nervoso)
│   ├── Conformidade Automática (audita)
│   ├── Painel de Acompanhamento (monitora)
│   └── ... (outras conforme necessário)
│
└── Artefatos que os membros PRODUZEM
    ├── Termos de Referência
    ├── Editais
    ├── Relatórios de Auditoria
    ├── Decisões Documentadas
    ├── Código Novo
    └── Skills
```

### O Que NUNCA Fazer
- ❌ Tratar TR Generator como "o sistema" ou "R4" — ele é uma FERRAMENTA
- ❌ Dizer "o gerador faz X" — quem faz é o agente, a ferramenta executa
- ❌ Criar recursão VSM para ferramentas — ferramentas não são sistemas viáveis
- ❌ Confundir interface de usuário com agente — o usuário fala com AGENTES, não com ferramentas

### O Que SEMPRE Fazer
- ✅ "O Gestor-Pesquisador usa o TR Generator para publicar a chamada"
- ✅ "A DIDES Auditoria usa a conformidade automática para verificar prazos"
- ✅ "O Agente Desenvolvedor cria skills para expandir a CDA"
- ✅ Perguntar: "Que membro da CDA faz isso? Que ferramenta ele usa?"

### Checklist de Coerência

Ao descrever qualquer funcionalidade, verificar:
1. [ ] Qual agente S1 executa esta ação?
2. [ ] Qual ferramenta ele usa?
3. [ ] Qual artefato é produzido?
4. [ ] Isto é a CDA agindo, ou é um humano usando uma ferramenta?
5. [ ] Se for humano usando ferramenta → não é a CDA, é operação manual
