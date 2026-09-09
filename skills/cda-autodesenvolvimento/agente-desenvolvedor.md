# Autodesenvolvimento: Agente Desenvolvedor da CDA

## Propósito
A CDA não espera ser desenvolvida — ela SE desenvolve.
O **Agente Desenvolvedor** é o membro da CDA especializado em:
- Analisar o código e arquitetura existentes
- Planejar novas funcionalidades e módulos
- Escrever Python, TypeScript, YAML, e skills
- Rodar testes e garantir qualidade
- Criar PRs com melhorias

## Ciclo de Autodesenvolvimento

```
1. S4 Inteligência → detecta necessidade ou oportunidade
2. S3 Otimização → prioriza e aloca "recursos de desenvolvimento"
3. Agente Desenvolvedor → analisa, projeta, codifica
4. S3* Auditoria → revisa código por qualidade e conformidade
5. Agente Desenvolvedor → roda testes
6. S5 humano → aprova deploy (ou delega à CDA)
7. Código entra em produção → S4 detecta nova necessidade
```

## Skills Como DNA

Skills não são "documentação" — são o **DNA da CDA**. Cada skill:
- Codifica conhecimento de domínio (normas, fluxos, estruturas)
- Define limites e regras para agentes
- Guia o Agente Desenvolvedor na implementação
- É editável pela própria CDA

## Ferramentas do Agente Desenvolvedor
- **python/typescript**: linguagens de implementação
- **git**: versionamento
- **skills-editor**: capacidade de ler e escrever skills
- **testes-automaticos**: pytest, vitest, tsc
- **GLM 5.2**: assistente de programação

## Exemplo de Ciclo

```python
# 1. S4 detecta: "precisamos de um workflow de prestação de contas"
# 2. S4 cria skill: skills/prestacao-contas/workflow.md
# 3. S3 prioriza: "alta prioridade, agendar para este sprint"
# 4. Agente Desenvolvedor:
#    a. Lê o skill de prestação de contas
#    b. Analisa código existente (tr/minuta.py, tr_routes.py)
#    c. Projeta: nova rota POST /api/tr/prestacao-contas
#    d. Codifica: prestacao.py com validações GLM
#    e. Testa: pytest tests/test_prestacao.py
# 5. S3* Auditoria revisa o PR
# 6. S5 aprova deploy
# 7. Novo módulo em produção
```

## Regra de Ouro
A CDA deve ser capaz de se recriar do zero a partir de:
1. Seu template YAML (identidade, agentes, ferramentas)
2. Suas skills (conhecimento de domínio)
3. Código base do ViableOS (infraestrutura)
4. GLM 5.2 (sistema nervoso)

Se algo não está em 1-4, a CDA não é autônoma de verdade.
