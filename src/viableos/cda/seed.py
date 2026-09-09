"""Dados de seed para demonstrar a CDA em funcionamento.

Escreve nos objetos POR NÍVEL (fabrica.raiz.motor / fabrica.raiz.canal) —
os singletons de compatibilidade de decisoes.py/algedonic.py ficam órfãos
da árvore e a Sala de Op não os enxerga (bug registrado na
docs/audits/2026-09-03-coerencia-cda.md §2.2).
"""

from __future__ import annotations

from viableos.cda.autodesenvolvimento import pipeline, TipoArtefato
from viableos.cda.recursao.bargain import protocolo_bargain


def seed_all() -> None:
    """Popula dados iniciais da CDA para demonstração."""

    # Tarefas de desenvolvimento
    t1 = pipeline.criar_tarefa(
        titulo="Implementar módulo de prestação de contas",
        descricao="Criar API REST para prestação de contas de bolsistas: "
                  "upload de relatórios, validação automática, notificação.",
        projeto="Projeto 1",
        solicitante="Gestão de Projetos (S3)",
    )
    pipeline.iniciar(t1.id)

    a1 = pipeline.registrar_artefato(
        nome="prestacao_contas.py",
        tipo=TipoArtefato.CODIGO,
        descricao="Módulo principal de prestação de contas",
        caminho="src/viableos/prestacao_contas/",
        projeto="Projeto 1",
        linguagem="Python",
        linhas=240,
    )
    pipeline.vincular_artefato(t1.id, a1.id)

    a2 = pipeline.registrar_artefato(
        nome="prestacao_contas_routes.py",
        tipo=TipoArtefato.CODIGO,
        descricao="API routes para prestação de contas",
        caminho="src/viableos/api/",
        projeto="Projeto 1",
        linguagem="Python",
        linhas=85,
    )
    pipeline.vincular_artefato(t1.id, a2.id)

    t2 = pipeline.criar_tarefa(
        titulo="Criar skill de auditoria de conformidade",
        descricao="Desenvolver skill para o agente Auditoria verificar "
                  "conformidade de TRs com PN 317/2025 automaticamente.",
        projeto="Projeto 1",
        solicitante="Auditoria (S3*)",
    )

    # ═══ Registrar no nível CDA (Level 1) — visível na Sala de Op ═══
    from viableos.cda.fabrica import fabrica
    if fabrica.raiz:
        # Decisões de exemplo (S4 com recomendação → sobe para Diretora)
        # R6: cascata completa — contexto, opções e justificativa
        fabrica.raiz.motor.solicitar(
            solicitante="Inteligência Estratégica (S4)",
            tipo_solicitante="s4_inteligencia",
            assunto="Priorizar sprint 3 vs Projeto 2",
            contexto="Recursos estão sobrecarregados. Devemos concluir "
                     "prestação de contas (sprint 3) ou iniciar Projeto 2?",
            opcoes=[
                "Concluir sprint 3 com equipe atual",
                "Reduzir escopo e iniciar Projeto 2",
                "Alocar mais 1 desenvolvedor para fazer ambos",
            ],
            urgencia="alta",
            justificativa="S4: sprint 3 está a 80% e o Projeto 2 perde janela "
                          "de contratação se não iniciar no próximo trimestre.",
        )

        fabrica.raiz.motor.solicitar(
            solicitante="Inteligência Estratégica (S4)",
            tipo_solicitante="s4_inteligencia",
            assunto="Definir escopo de digitalização do fluxo de contratação",
            contexto="Recomendamos iniciar mapeamento do fluxo de "
                     "contratação de terceirizados como Projeto 2. "
                     "Estimar 4 sprints.",
            opcoes=[
                "Iniciar Projeto 2 na próxima semana",
                "Aguardar conclusão do Projeto 1",
                "Solicitar estudo mais detalhado da S4",
            ],
            urgencia="media",
            justificativa="S4: mapeamento prévio indica 4 sprints e dependência "
                          "apenas de dados já disponíveis no ComprasNet.",
        )

        # Registros de atividade por agente
        s4 = fabrica.raiz.obter_agente("Inteligência Estratégica (S4)")
        if s4:
            s4.registrar_acao("Seed: decisão de priorização", "pendente")
        s3 = fabrica.raiz.obter_agente("Gestão de Projetos (S3)")
        if s3:
            s3.registrar_acao("Seed: decisão de escopo", "pendente")

        # Decisões no nível Projeto 1 (Level 2)
        proj1 = None
        for sub in fabrica.raiz.listar_subniveis():
            if sub.nome == "Projeto 1":
                proj1 = sub
                break
        if proj1:
            dev = proj1.obter_agente("Agente Desenvolvedor")
            if dev:
                dev.registrar_acao("Seed: tarefa de prestação de contas", "em andamento")

        # Sinal de exemplo no canal do nível CDA
        from viableos.cda.algedonic import GravidadeSinal, TipoGatilho

        fabrica.raiz.canal.disparar(
            fonte="Agente Desenvolvedor",
            gravidade=GravidadeSinal.AMARELO,
            gatilho=TipoGatilho.CONFLITO_AGENTES,
            assunto="Dependência externa SISBOLSAS",
            mensagem="Módulo de prestação de contas depende de API do "
                     "SISBOLSAS. Sem previsão de disponibilização.",
            contexto={"dependencia": "SISBOLSAS", "bloqueia": "prestacao_contas"},
        )

    # Bargain de exemplo
    n = protocolo_bargain.solicitar(
        subnivel="Projeto 1",
        nivel_pai="CDA",
        recursos=[
            {"tipo": "agente_desenvolvedor", "quantidade": 1, "unidade": "40h/semana", "prioridade": 2},
            {"tipo": "api_calls_glm", "quantidade": 10000, "unidade": "chamadas/mês", "prioridade": 3},
        ],
        justificativa="Projeto 1 precisa de mais capacidade para concluir sprint 3 no prazo.",
    )
