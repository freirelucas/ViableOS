const API_BASE = import.meta.env.VITE_API_URL || '/api';

// Token S5 (R5): ações de veredito — resolver/rejeitar/delegar decisão e
// responder sinal algédonico — exigem JWT com escopo admin ou cda:s5.
// O token é colado na view de Decisões da Sala de Operação (CDAPage).
const TOKEN_KEY = 'viableos_token';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage indisponível — segue sem token
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.json();
}

async function postS5<T>(path: string, body: unknown): Promise<T> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.json();
}

export interface CDAAgente {
  id: string;
  nome: string;
  tipo: string;
  status: 'online' | 'trabalhando' | 'standby' | 'erro';
  proposito: string;
  atividade: string;
  ultima_acao: string;
  ferramentas: string[];
  decisoes_pendentes: number;
  intencoes_ativas?: number;
  estrategia?: string;
  modelo?: string;
}

export interface CDAAgenteDetalhe extends CDAAgente {
  decisoes: Array<{
    id: string;
    assunto: string;
    contexto: string;
    urgencia: string;
    opcoes: string[];
    criado_em: string;
  }>;
}

export interface Decisao {
  id: string;
  assunto: string;
  solicitante: string;
  contexto: string;
  urgencia: string;
  opcoes: string[];
  criado_em: string;
  justificativa?: string;
  status?: string;
  papel_origem?: string;
}

export interface Sinal {
  id: string;
  fonte: string;
  gravidade: string;
  assunto: string;
  mensagem: string;
  timestamp: string;
  respondido: boolean;
  gatilho?: string;
  nivel?: string;
}

export interface CDAStatus {
  total_agentes: number;
  online: number;
  standby: number;
  decisoes_pendentes: number;
  sinais_pendentes: number;
  sinais_vermelhos: number;
  niveis: number;
}

export interface NivelInfo {
  id: string;
  nome: string;
  nivel: number;
  proposito: string;
  proposito_completo: string;
  agentes: number;
  subniveis: number;
  decisoes_pendentes: number;
  sinais_pendentes: number;
  parent: string | null;
}

export interface RelatorioAuditoria {
  nivel: string;
  nivel_num: number;
  status: 'conforme' | 'atencao' | 'critico';
  agentes: number;
  decisoes_pendentes: number;
  sinais_vermelhos: number;
  agentes_offline: number;
  intencoes_ativas: number;
  conflitos_intencoes: number;
  proposito: string;
  parent: string;
}

export interface ResultadoAuditoriaRegra {
  regra: string;
  descricao: string;
  status: 'conforme' | 'violado' | 'nao_aplicavel';
  detalhes: string;
}

export interface IntencaoInfo {
  id: string;
  agente: string;
  desejo: string;
  plano: string;
  status: string;
  estrategia: string;
  passos: number;
  passo_atual: string | null;
  proporcao_concluida: number;
  prioridade: number;
  adotada_em: string;
  evidencia_contraria: string[];
}

export interface AgendaStatus {
  agentes_com_intencoes: number;
  total_intencoes_ativas: number;
  conflitos: number;
  motores: Record<string, unknown>;
}

export interface CoerenciaConflito {
  intencao_a: string;
  agente_a: string;
  intencao_b: string;
  agente_b: string;
  recursos_conflitantes: string[];
}

export interface TreeNode {
  id: string;
  nome: string;
  nivel: number;
  proposito: string;
  proposito_completo: string;
  agentes: CDAAgente[];
  decisoes: Decisao[];
  sinais_pendentes: Array<{ id: string; fonte: string; gravidade: string; assunto: string; mensagem: string; timestamp: string }>;
  subniveis: TreeNode[];
}

export const cdaApi = {
  agentes: () => get<CDAAgente[]>('/cda/agentes'),
  agente: (nome: string) => get<CDAAgenteDetalhe>(`/cda/agentes/${encodeURIComponent(nome)}`),
  agendaBratman: () => get<AgendaStatus>('/cda/bratman/agenda'),
  intencoesAgente: (agente: string) => get<IntencaoInfo[]>(`/cda/bratman/intencoes/${encodeURIComponent(agente)}`),
  adotarIntencao: (agente: string, desejo: string, plano: string, passos?: unknown[], prioridade = 3) =>
    post<{ status: string; intencao_id: string }>('/cda/bratman/adotar', { agente, desejo, plano, passos, prioridade }),
  coerenciaIntencoes: () => get<CoerenciaConflito[]>('/cda/bratman/coerencia'),
  constituicao: () => get<{ conteudo: string }>('/cda/constituicao'),
  auditoriaRegras: () => get<ResultadoAuditoriaRegra[]>('/cda/auditoria/regras'),
  definirAtividade: (nome: string, atividade: string) =>
    post<{ status: string }>(`/cda/agentes/${encodeURIComponent(nome)}/atividade`, { atividade }),
  solicitarDecisao: (nome: string, assunto: string, contexto: string, opcoes: string[], urgencia = 'media') =>
    post<{ status: string; decisao_id: string }>(`/cda/agentes/${encodeURIComponent(nome)}/decisao`, { assunto, contexto, opcoes, urgencia }),
  decisoes: () => get<Decisao[]>('/cda/decisoes'),
  resolverDecisao: (decisaoId: string, resolucao: string) =>
    postS5<{ status: string }>(`/cda/decisoes/${decisaoId}/resolver`, { resolucao }),
  rejeitarDecisao: (decisaoId: string, feedback: string) =>
    postS5<{ status: string }>(`/cda/decisoes/${decisaoId}/rejeitar`, { feedback }),
  delegarDecisao: (decisaoId: string) =>
    postS5<{ status: string }>(`/cda/decisoes/${decisaoId}/delegar`, {}),
  historicoDecisoes: () => get<Decisao[]>(`/cda/decisoes/historico`),
  sinais: (gravidade?: string) => get<Sinal[]>(`/cda/sinais${gravidade ? `?gravidade=${gravidade}` : ''}`),
  dispararSinal: (fonte: string, gravidade: string, assunto: string, mensagem: string, contexto?: Record<string, unknown>, gatilho?: string) =>
    post<{ status: string; sinal_id: string }>('/cda/sinais', { fonte, gravidade, assunto, mensagem, contexto, gatilho }),
  responderSinal: (sinalId: string, resolucao: string) =>
    postS5<{ status: string }>(`/cda/sinais/${sinalId}/responder`, { resolucao }),
  status: () => get<CDAStatus>('/cda/status'),
  tree: () => get<TreeNode>('/cda/tree'),
  niveis: () => get<NivelInfo[]>('/cda/niveis'),
  auditoria: () => get<RelatorioAuditoria[]>('/cda/auditoria'),
  tarefas: (projeto?: string) => get<Tarefa[]>(`/cda/dev/tarefas${projeto ? `?projeto=${projeto}` : ''}`),
  criarTarefa: (titulo: string, descricao: string, projeto = 'Projeto 1', solicitante = 'S3 - Gestão de Projetos') =>
    post<{ status: string; tarefa_id: string }>('/cda/dev/tarefas', { titulo, descricao, projeto, solicitante }),
  iniciarTarefa: (tarefaId: string) => post<{ status: string }>(`/cda/dev/tarefas/${tarefaId}/iniciar`, {}),
  concluirTarefa: (tarefaId: string, notas = '') => post<{ status: string }>(`/cda/dev/tarefas/${tarefaId}/concluir`, { notas }),
  artefatos: (projeto?: string) => get<Artefato[]>(`/cda/dev/artefatos${projeto ? `?projeto=${projeto}` : ''}`),
  registrarArtefato: (payload: Record<string, unknown>) => post<{ status: string; artefato_id: string }>('/cda/dev/artefatos', payload),
  healthCheckBoot: () => get<Record<string, unknown>>('/cda/health/boot'),
  healthCheckPeriodico: () => get<Record<string, unknown>>('/cda/health/periodico'),
  listarCenarios: () => get<Array<{ nome: string; eventos: number }>>('/cda/cenarios'),
  simularCenario: (nome: string, ticks = 100) => post<Record<string, unknown>>(`/cda/cenarios/${encodeURIComponent(nome)}/simular`, { ticks }),
  historicoSimulacoes: () => get<Array<Record<string, unknown>>>('/cda/cenarios/historico'),
  listarSyntegration: () => get<{ ativos: unknown[]; historico: unknown[] }>('/cda/syntegration'),
  iniciarSyntegration: (gatilho: string) => post<{ status: string; protocolo_id: string; fase: string }>('/cda/syntegration/iniciar', { gatilho }),
  avancarSyntegration: (protocoloId: string) => post<{ status: string; fase: string }>(`/cda/syntegration/${encodeURIComponent(protocoloId)}/avancar`, {}),
  topology: () => get<{ canais: unknown }>('/cda/topology'),
  validarComunicacao: (origem: string, destino: string, tipoMsg: string) => post<{ valido: boolean; erro?: string }>('/cda/topology/validar', { origem, destino, tipo_msg: tipoMsg }),
};

export interface Tarefa {
  id: string;
  titulo: string;
  descricao: string;
  projeto: string;
  status: string;
  artefatos: string[];
  solicitante: string;
  criado_em: string;
  concluido_em: string | null;
}

export interface Artefato {
  id: string;
  nome: string;
  tipo: string;
  descricao: string;
  caminho: string;
  projeto: string;
  linguagem: string;
  linhas: number;
  criado_em: string;
  autor: string;
}
