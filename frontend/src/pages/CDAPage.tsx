import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Users, ClipboardList, AlertTriangle, FolderOpen, MessageSquare, ChevronRight, CheckCircle, Code, Brain, ShieldCheck, FileText } from 'lucide-react';
import type { CDAAgente, Decisao, Sinal, CDAStatus, Tarefa, Artefato, IntencaoInfo, ResultadoAuditoriaRegra, AgendaStatus, CoerenciaConflito } from '../api/cdaClient';
import { cdaApi, getAuthToken, setAuthToken } from '../api/cdaClient';
import { AgentChatModal } from '../components/AgentChatModal';
import { useCDASSE } from '../hooks/useCDASSE';

type CDAView = 'painel' | 'agentes' | 'projetos' | 'sinais' | 'decisoes' | 'desenvolvimento' | 'intencoes' | 'constituicao' | 'auditoria' | 'saude' | 'cenarios' | 'syntegration';

const STATUS_AGENTE = { online: 'text-green-500', trabalhando: 'text-blue-500', standby: 'text-yellow-500', erro: 'text-red-500' };

function AgentStatusDot({ status }: { status: string }) {
  return <span className={`w-2 h-2 rounded-full ${STATUS_AGENTE[status as keyof typeof STATUS_AGENTE] || 'text-gray-500'}`} />;
}

export function CDAPage() {
  const [view, setView] = useState<CDAView>('painel');
  const [agentes, setAgentes] = useState<CDAAgente[]>([]);
  const [decisoes, setDecisoes] = useState<Decisao[]>([]);
  const [sinais, setSinais] = useState<Sinal[]>([]);
  const [status, setStatus] = useState<CDAStatus | null>(null);
  const [tarefas, setTarefas] = useState<Tarefa[]>([]);
  const [artefatos, setArtefatos] = useState<Artefato[]>([]);
  const [chatAgente, setChatAgente] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolvingIds, setResolvingIds] = useState<Set<string>>(new Set());
  const [respondingIds, setRespondingIds] = useState<Set<string>>(new Set());
  const [intencoes] = useState<IntencaoInfo[]>([]);
  const [constituicao, setConstituicao] = useState<string>('');
  const [auditoriaRegras, setAuditoriaRegras] = useState<ResultadoAuditoriaRegra[]>([]);
  const [agenda, setAgenda] = useState<AgendaStatus | null>(null);
  const [conflitos, setConflitos] = useState<CoerenciaConflito[]>([]);
  const [healthCheck, setHealthCheck] = useState<Record<string, unknown> | null>(null);
  const [cenarios, setCenarios] = useState<Array<{ nome: string; eventos: number }>>([]);
  const [resultadoSimulacao, setResultadoSimulacao] = useState<Record<string, unknown> | null>(null);
  const [syntegrationData, setSyntegrationData] = useState<{ ativos: unknown[]; historico: unknown[] } | null>(null);
  const [tokenInput, setTokenInput] = useState<string>(getAuthToken() ?? '');

  const fetchAll = useCallback(async () => {
    try {
      const [a, d, s, st, t, ar] = await Promise.all([
        cdaApi.agentes(),
        cdaApi.decisoes(),
        cdaApi.sinais(),
        cdaApi.status(),
        cdaApi.tarefas(),
        cdaApi.artefatos(),
      ]);
      setAgentes(a);
      setDecisoes(d);
      setSinais(s);
      setStatus(st);
      setTarefas(t);
      setArtefatos(ar);
      const [aReg, ag, confs, c] = await Promise.all([
        cdaApi.auditoriaRegras(),
        cdaApi.agendaBratman(),
        cdaApi.coerenciaIntencoes(),
        cdaApi.constituicao(),
      ]);
      setAuditoriaRegras(aReg);
      setAgenda(ag);
      setConflitos(confs);
      setConstituicao(c.conteudo);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchIntencoes = useCallback(async () => {
    try {
      const [ag, confs] = await Promise.all([
        cdaApi.agendaBratman(),
        cdaApi.coerenciaIntencoes(),
      ]);
      setAgenda(ag);
      setConflitos(confs);
    } catch { /* ignore */ }
  }, []);

  const fetchConstituicao = useCallback(async () => {
    try {
      const c = await cdaApi.constituicao();
      setConstituicao(c.conteudo);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // SSE atualiza em tempo real (substitui polling)
  useCDASSE((event) => {
    if (event.tipo === 'status') {
      setStatus(event.dados as unknown as CDAStatus);
    }
  });

  const handleResolve = async (decisaoId: string, resolucao: string) => {
    setResolvingIds(prev => new Set(prev).add(decisaoId));
    await cdaApi.resolverDecisao(decisaoId, resolucao);
    setResolvingIds(prev => { const n = new Set(prev); n.delete(decisaoId); return n; });
    await fetchAll();
  };

  const handleDelegar = async (decisaoId: string) => {
    setResolvingIds(prev => new Set(prev).add(decisaoId));
    await cdaApi.delegarDecisao(decisaoId);
    setResolvingIds(prev => { const n = new Set(prev); n.delete(decisaoId); return n; });
    await fetchAll();
  };

  const handleResponderSinal = async (sinalId: string) => {
    setRespondingIds(prev => new Set(prev).add(sinalId));
    await cdaApi.responderSinal(sinalId, 'Sinal recebido e processado pela Diretora.');
    setRespondingIds(prev => { const n = new Set(prev); n.delete(sinalId); return n; });
    await fetchAll();
  };

  const navItems: { key: CDAView; label: string; icon: typeof Activity }[] = [
    { key: 'painel', label: 'Painel Geral', icon: Activity },
    { key: 'agentes', label: 'Agentes', icon: Users },
    { key: 'projetos', label: 'Projetos', icon: FolderOpen },
    { key: 'decisoes', label: 'Decisões', icon: ClipboardList },
    { key: 'sinais', label: 'Sinais', icon: AlertTriangle },
    { key: 'intencoes', label: 'Intenções', icon: Brain },
    { key: 'auditoria', label: 'Auditoria', icon: ShieldCheck },
    { key: 'constituicao', label: 'Constituição', icon: FileText },
    { key: 'saude', label: 'Saúde', icon: Activity },
    { key: 'cenarios', label: 'Cenários', icon: ClipboardList },
    { key: 'syntegration', label: 'Syntegration', icon: Users },
    { key: 'desenvolvimento', label: 'Dev', icon: Code },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-700 flex items-center justify-center text-white font-bold shadow-lg">CDA</div>
        <div>
          <h1 className="text-2xl font-bold">Sala de Operação</h1>
          <p className="text-sm text-[var(--color-muted)]">Corporação Digital Autônoma — Digitalização do IPEA</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full ${status && status.online > 0 ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
            <span className={`w-2 h-2 rounded-full ${status && status.online > 0 ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'} `} />
            {status ? `${status.online}/${status.total_agentes} ativos` : '...'}
          </span>
          <span className="text-xs text-[var(--color-muted)]">{status?.total_agentes || 0} agentes • {decisoes.length} decisões</span>
        </div>
      </div>

      <div className="flex items-center gap-1 mb-6 flex-wrap border-b border-[var(--color-border)] pb-3">
        {navItems.map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setView(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              view === key ? 'bg-[var(--color-primary)] text-white shadow-sm' : 'text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-card)]'
            }`}
          ><Icon className="w-4 h-4" />{label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={view} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.15 }}>
          {view === 'painel' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold flex items-center gap-2"><Users className="w-4 h-4 text-[var(--color-primary)]" />Agentes em Atividade</h3>
                    <button onClick={() => setView('agentes')} className="text-xs text-[var(--color-primary)] hover:underline flex items-center gap-1">Ver todos <ChevronRight className="w-3 h-3" /></button>
                  </div>
                  <div className="space-y-1">
                    {agentes.filter(a => a.status !== 'standby').slice(0, 5).map((a) => (
                      <div key={a.nome} className="flex items-center justify-between text-sm p-2 rounded-lg hover:bg-[var(--color-bg)]">
                        <div className="flex items-center gap-2.5"><AgentStatusDot status={a.status} /><span className="font-medium">{a.nome}</span><span className="text-xs text-[var(--color-muted)]">{a.atividade}</span></div>
                        <span className="text-[10px] text-[var(--color-muted)]">{new Date(a.ultima_acao).toLocaleTimeString('pt-BR')}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><ClipboardList className="w-4 h-4 text-yellow-500" />Decisões Pendentes</h3>
                  {decisoes.slice(0, 3).map((d) => (
                    <div key={d.id} className="p-3 rounded-lg bg-[var(--color-bg)] mb-2 last:mb-0">
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-medium">{d.assunto}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${d.urgencia === 'alta' ? 'bg-red-500/10 text-red-500' : 'bg-yellow-500/10 text-yellow-500'}`}>{d.urgencia}</span>
                      </div>
                      <p className="text-xs text-[var(--color-muted)] mt-1">{d.contexto}</p>
                      <p className="text-[10px] text-[var(--color-muted)] mt-1">De: {d.solicitante}</p>
                      <button onClick={() => setView('decisoes')} className="mt-2 text-xs text-[var(--color-primary)] hover:underline">Revisar e decidir →</button>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-yellow-500" />Sinais Recentes</h3>
                  {sinais.filter(s => !s.respondido).slice(0, 3).map((s) => (
                    <div key={s.id} className={`p-3 rounded-lg mb-2 last:mb-0 text-sm ${s.gravidade === 'amarelo' ? 'bg-yellow-500/5 border border-yellow-500/20' : s.gravidade === 'vermelho' ? 'bg-red-500/5 border border-red-500/20' : 'bg-green-500/5 border border-green-500/20'}`}>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${s.gravidade === 'vermelho' ? 'bg-red-500' : s.gravidade === 'amarelo' ? 'bg-yellow-500' : 'bg-green-500'}`} />
                        <span className="font-medium text-xs">{s.assunto}</span>
                        <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${s.gravidade === 'vermelho' ? 'bg-red-500/10 text-red-500' : s.gravidade === 'amarelo' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-green-500/10 text-green-500'}`}>{s.gravidade}</span>
                      </div>
                      <p className="text-xs text-[var(--color-muted)] mt-1">{s.mensagem}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {view === 'agentes' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                <h3 className="text-sm font-semibold mb-2">S5 — Diretora (Humano)</h3>
                <p className="text-xs text-[var(--color-muted)]">Você. Decide o quê. A CDA decide como.</p>
              </div>
              {agentes.map((a) => (
                <div key={a.nome} className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5"><AgentStatusDot status={a.status} />
                      <div><h3 className="font-semibold text-sm">{a.nome}</h3><p className="text-[10px] text-[var(--color-muted)] uppercase tracking-wider">{a.tipo}</p></div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                        a.status === 'online' ? 'bg-green-500/10 text-green-500' : a.status === 'trabalhando' ? 'bg-blue-500/10 text-blue-500' : a.status === 'standby' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-red-500/10 text-red-500'
                      }`}>{a.status}</span>
                      <button onClick={() => setChatAgente(a.nome)} className="text-xs text-[var(--color-muted)] hover:text-[var(--color-primary)] flex items-center gap-1"><MessageSquare className="w-3 h-3" /> Falar</button>
                    </div>
                  </div>
                  <p className="text-sm mt-2">Atividade: <span className="text-[var(--color-muted)]">{a.atividade}</span></p>
                  {'intencoes_ativas' in a && (
                    <p className="text-[10px] text-[var(--color-muted)] mt-1">
                      Intenções: {a.intencoes_ativas} • Estratégia: {a.estrategia}
                      {a.modelo && ` • Modelo: ${a.modelo}`}
                    </p>
                  )}
                  {a.ferramentas.length > 0 && (
                    <div className="mt-2 flex gap-1 flex-wrap">
                      {a.ferramentas.map(f => <span key={f} className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)]">{f}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {view === 'projetos' && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--color-muted)]">Projetos que a CDA está executando para digitalizar o IPEA</p>
              <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                <div className="flex items-center justify-between mb-2">
                  <div><h3 className="font-semibold">Automação da Gestão de Bolsistas</h3><p className="text-xs text-[var(--color-muted)]">Projeto 1 — MVP</p></div>
                  <span className="text-xs px-2 py-1 rounded-full font-medium bg-blue-500/10 text-blue-500">ativo</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span>Progresso:</span>
                  <div className="flex-1 h-2 rounded-full bg-[var(--color-border)] overflow-hidden">
                    <div className="h-full rounded-full bg-[var(--color-primary)] transition-all" style={{ width: '35%' }} />
                  </div>
                  <span className="text-[var(--color-muted)]">35%</span>
                </div>
                <div className="mt-2 flex gap-1.5 flex-wrap">
                  {['TR Generator', 'API de Conformidade', 'Skills Gestão Bolsistas'].map(a => (
                    <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)]">{a}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {view === 'decisoes' && (
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                <p className="text-[10px] uppercase tracking-wide text-[var(--color-muted)] mb-1.5">Autenticação S5 (R5)</p>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder="Token JWT (login /api/auth/login → escopo admin ou cda:s5)"
                    className="flex-1 text-xs px-3 py-1.5 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] outline-none"
                  />
                  <button
                    onClick={() => setAuthToken(tokenInput.trim() || null)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white font-medium"
                  >
                    Salvar token
                  </button>
                </div>
                <p className="text-[10px] text-[var(--color-muted)] mt-1.5">
                  Confirmar, delegar e responder sinal exigem humano autenticado — a identidade registrada vem do token.
                </p>
              </div>
              {loading && <p className="text-sm text-[var(--color-muted)]">Carregando...</p>}
              {!loading && decisoes.length === 0 && (
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-center text-sm text-[var(--color-muted)]">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                  Nenhuma decisão pendente. A CDA está operando dentro da alçada dos agentes.
                </div>
              )}
              {decisoes.map((d) => (
                <div key={d.id} className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div><h3 className="font-semibold text-sm">{d.assunto}</h3><p className="text-xs text-[var(--color-muted)]">Solicitado por: {d.solicitante}</p></div>
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${d.urgencia === 'alta' ? 'bg-red-500/10 text-red-500' : 'bg-yellow-500/10 text-yellow-500'}`}>{d.urgencia}</span>
                  </div>
                  <p className="text-sm bg-[var(--color-bg)] p-3 rounded-lg mb-3">{d.contexto}</p>
                  {d.justificativa && <p className="text-xs text-[var(--color-muted)] mb-3 italic">Justificativa: {d.justificativa}</p>}
                  <span className="text-xs text-[var(--color-muted)]">Opções recomendadas:</span>
                  <div className="space-y-2 mt-2">
                    {d.opcoes.map((o, i) => (
                      <label key={i} className="flex items-center gap-2 text-sm p-2 rounded-lg hover:bg-[var(--color-bg)] cursor-pointer">
                        <input type="radio" name={`decisao-${d.id}`} className="accent-[var(--color-primary)]" />{o}
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button onClick={() => handleResolve(d.id, d.opcoes[0] || 'aprovado')} disabled={resolvingIds.has(d.id)}
                      className="px-4 py-1.5 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium disabled:opacity-50">Confirmar Decisão</button>
                    <button onClick={() => handleDelegar(d.id)} disabled={resolvingIds.has(d.id)}
                      className="px-4 py-1.5 rounded-lg bg-[var(--color-bg)] text-sm disabled:opacity-50">Delegar à CDA</button>
                    <button className="px-4 py-1.5 rounded-lg bg-[var(--color-bg)] text-sm">Solicitar mais análise</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {view === 'sinais' && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--color-muted)]">Sinais algêdonicos — comunicação direta dos agentes para a Diretora, pulando a hierarquia</p>
              {sinais.filter(s => !s.respondido).length === 0 && (
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-center text-sm text-[var(--color-muted)]">
                  ✅ Nenhum sinal pendente. A CDA está operando sem emergências.
                </div>
              )}
              {sinais.filter(s => !s.respondido).map((s) => (
                <div key={s.id} className={`p-4 rounded-xl border ${s.gravidade === 'vermelho' ? 'bg-red-500/5 border-red-500/30' : s.gravidade === 'amarelo' ? 'bg-yellow-500/5 border-yellow-500/30' : 'bg-green-500/5 border-green-500/30'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`w-3 h-3 rounded-full ${s.gravidade === 'vermelho' ? 'bg-red-500 animate-pulse' : s.gravidade === 'amarelo' ? 'bg-yellow-500' : 'bg-green-500'}`} />
                    <h3 className="font-semibold text-sm">{s.assunto}</h3>
                    <span className={`ml-auto text-xs font-bold px-2 py-0.5 rounded ${s.gravidade === 'vermelho' ? 'bg-red-500/10 text-red-500' : s.gravidade === 'amarelo' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-green-500/10 text-green-500'}`}>{s.gravidade.toUpperCase()}</span>
                  </div>
                  <p className="text-sm mb-2">{s.mensagem}</p>
                  <div className="flex items-center justify-between text-xs text-[var(--color-muted)]">
                    <span>Fonte: {s.fonte}</span>
                    <span>{new Date(s.timestamp).toLocaleString('pt-BR')}</span>
                  </div>
                  {['vermelho', 'amarelo'].includes(s.gravidade) && (
                    <div className="flex gap-2 mt-3">
                      <button onClick={() => handleResponderSinal(s.id)} disabled={respondingIds.has(s.id)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50">Responder ao Sinal</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {view === 'intencoes' && (
            <div className="space-y-4">
              <button onClick={() => { fetchIntencoes(); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white mb-2">Recarregar Intenções</button>
              {agenda && (
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="p-3 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-center">
                    <span className="text-2xl font-bold text-[var(--color-primary)]">{agenda.total_intencoes_ativas}</span>
                    <p className="text-xs text-[var(--color-muted)]">Intenções Ativas</p>
                  </div>
                  <div className="p-3 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-center">
                    <span className="text-2xl font-bold text-green-500">{agenda.agentes_com_intencoes}</span>
                    <p className="text-xs text-[var(--color-muted)]">Agentes com Intenções</p>
                  </div>
                  <div className="p-3 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-center">
                    <span className={`text-2xl font-bold ${agenda.conflitos > 0 ? 'text-red-500' : 'text-green-500'}`}>{agenda.conflitos}</span>
                    <p className="text-xs text-[var(--color-muted)]">Conflitos</p>
                  </div>
                </div>
              )}
              {conflitos.length > 0 && (
                <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/30">
                  <h3 className="text-sm font-semibold mb-2 text-red-500">⚠ Conflitos de Recursos Detectados</h3>
                  {conflitos.map((c, i) => (
                    <p key={i} className="text-xs text-[var(--color-muted)] mb-1">{c.agente_a} vs {c.agente_b}: {c.recursos_conflitantes.join(', ')}</p>
                  ))}
                </div>
              )}
              {intencoes.length === 0 && (
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-center text-sm text-[var(--color-muted)]">
                  <Brain className="w-8 h-8 mx-auto mb-2 text-[var(--color-primary)]" />
                  Nenhuma intenção registrada. Use o botão "Adotar Intenção" para começar.
                </div>
              )}
              {intencoes.map((i) => (
                <div key={i.id} className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-sm">{i.desejo}</h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      i.status === 'ativa' || i.status === 'em_execucao' ? 'bg-blue-500/10 text-blue-500' :
                      i.status === 'concluida' ? 'bg-green-500/10 text-green-500' :
                      i.status === 'suspensa' ? 'bg-yellow-500/10 text-yellow-500' :
                      'bg-red-500/10 text-red-500'
                    }`}>{i.status}</span>
                  </div>
                  <p className="text-xs text-[var(--color-muted)] mb-1">Agente: {i.agente} • Plano: {i.plano} • Estratégia: {i.estrategia}</p>
                  <div className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
                    <span>Passos: {i.passos}</span>
                    {i.passo_atual && <span>• Atual: {i.passo_atual}</span>}
                    <span>• {Math.round(i.proporcao_concluida * 100)}% concluído</span>
                  </div>
                  {i.evidencia_contraria.length > 0 && (
                    <p className="text-xs text-yellow-500 mt-1">Evidência contrária: {i.evidencia_contraria.join(', ')}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          {view === 'auditoria' && (
            <div className="space-y-4">
              <button onClick={fetchAll} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white mb-2">Re-auditar</button>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-green-500" />6 Regras Inegociáveis</h3>
                  {auditoriaRegras.map((r) => (
                    <div key={r.regra} className={`p-3 rounded-xl border text-sm ${
                      r.status === 'conforme' ? 'bg-green-500/5 border-green-500/30' :
                      r.status === 'violado' ? 'bg-red-500/5 border-red-500/30' :
                      'bg-gray-500/5 border-gray-500/30'
                    }`}>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${
                          r.status === 'conforme' ? 'bg-green-500' :
                          r.status === 'violado' ? 'bg-red-500' : 'bg-gray-500'
                        }`} />
                        <span className="font-medium">{r.regra} — {r.descricao}</span>
                        <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          r.status === 'conforme' ? 'bg-green-500/10 text-green-500' :
                          r.status === 'violado' ? 'bg-red-500/10 text-red-500' :
                          'bg-gray-500/10 text-gray-500'
                        }`}>{r.status}</span>
                      </div>
                      <p className="text-xs text-[var(--color-muted)] mt-1">{r.detalhes}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {view === 'constituicao' && (
            <div className="p-6 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
              <button onClick={fetchConstituicao} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white mb-4">Carregar Constituição</button>
              {constituicao ? (
                <div className="prose prose-sm max-w-none">
                  {constituicao.split('\n').map((line, i) => (
                    <p key={i} className={`text-sm ${
                      line.startsWith('#') ? 'text-lg font-bold mt-4 mb-2' :
                      line.startsWith('##') ? 'text-base font-semibold mt-3 mb-1' :
                      line.startsWith('###') ? 'text-sm font-medium mt-2' :
                      line.startsWith('-') ? 'text-sm ml-4' :
                      'text-sm text-[var(--color-muted)]'
                    }`}>{line}</p>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[var(--color-muted)]">Clique em "Carregar Constituição" para exibir a Constituição S5.</p>
              )}
            </div>
          )}
          {view === 'desenvolvimento' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Code className="w-4 h-4 text-[var(--color-primary)]" />Tarefas de Desenvolvimento</h3>
                  {tarefas.length === 0 && <p className="text-sm text-[var(--color-muted)]">Nenhuma tarefa cadastrada.</p>}
                  {tarefas.map((t) => (
                    <div key={t.id} className="p-3 rounded-lg bg-[var(--color-bg)] mb-2 last:mb-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{t.titulo}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                          t.status === 'concluida' ? 'bg-green-500/10 text-green-500' :
                          t.status === 'em_execucao' ? 'bg-blue-500/10 text-blue-500' :
                          t.status === 'bloqueada' ? 'bg-red-500/10 text-red-500' :
                          'bg-gray-500/10 text-gray-500'
                        }`}>{t.status}</span>
                      </div>
                      <p className="text-xs text-[var(--color-muted)] mb-1">{t.descricao}</p>
                      <div className="flex items-center gap-2 text-[10px] text-[var(--color-muted)]">
                        <span>Projeto: {t.projeto}</span>
                        <span>Solicitante: {t.solicitante}</span>
                        {t.artefatos.length > 0 && <span>{t.artefatos.length} artefatos</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <h3 className="text-sm font-semibold mb-3">Artefatos Produzidos</h3>
                  {artefatos.length === 0 && <p className="text-sm text-[var(--color-muted)]">Nenhum artefato registrado.</p>}
                  {artefatos.map((a) => (
                    <div key={a.id} className="p-3 rounded-lg bg-[var(--color-bg)] mb-2 last:mb-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{a.nome}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)]">{a.tipo}</span>
                      </div>
                      <p className="text-xs text-[var(--color-muted)]">{a.descricao}</p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-[var(--color-muted)]">
                        <span>{a.linguagem}</span>
                        <span>{a.linhas} linhas</span>
                        <span>{a.projeto}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {view === 'saude' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <button onClick={async () => { const r = await fetch('/api/cda/health/boot').then(res => res.json()); setHealthCheck(r); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white">Health Check Boot</button>
                <button onClick={async () => { const r = await fetch('/api/cda/health/periodico').then(res => res.json()); setHealthCheck(r); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">Health Check Periódico</button>
              </div>
              {healthCheck && (
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold">Resultado: {healthCheck.momento as string}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${(healthCheck.saudavel as boolean) ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                      {(healthCheck.saudavel as boolean) ? 'Saudável' : 'Crítico'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="text-center p-2 rounded-lg bg-green-500/5"><span className="text-lg font-bold text-green-500">{healthCheck.passes as number}</span><p className="text-[10px] text-[var(--color-muted)]">Passes</p></div>
                    <div className="text-center p-2 rounded-lg bg-yellow-500/5"><span className="text-lg font-bold text-yellow-500">{healthCheck.warnings as number}</span><p className="text-[10px] text-[var(--color-muted)]">Warnings</p></div>
                    <div className="text-center p-2 rounded-lg bg-red-500/5"><span className="text-lg font-bold text-red-500">{healthCheck.criticals as number}</span><p className="text-[10px] text-[var(--color-muted)]">Criticals</p></div>
                  </div>
                  <div className="space-y-1">
                    {(healthCheck.itens as Array<{ nome: string; categoria: string; passou: boolean; severidade: string; detalhes: string }>).map((item, idx) => (
                      <div key={idx} className={`flex items-center gap-2 text-xs p-2 rounded ${item.passou ? 'bg-green-500/5' : item.severidade === 'critical' ? 'bg-red-500/5' : 'bg-yellow-500/5'}`}>
                        <span className={`w-2 h-2 rounded-full ${item.passou ? 'bg-green-500' : item.severidade === 'critical' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                        <span className="font-medium">{item.nome}</span>
                        <span className="text-[var(--color-muted)] ml-auto">{item.detalhes}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {view === 'cenarios' && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--color-muted)]">Simulador de cenários IPEA — teste decisões antes de executar</p>
              <div className="flex items-center gap-2 mb-4">
                <button onClick={async () => { const r = await fetch('/api/cda/cenarios').then(res => res.json()); setCenarios(r); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white">Listar Cenários</button>
              </div>
              {cenarios.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {cenarios.map((c) => (
                    <div key={c.nome} className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                      <h3 className="font-semibold text-sm mb-2">{c.nome}</h3>
                      <p className="text-xs text-[var(--color-muted)] mb-3">{c.eventos} eventos</p>
                      <button onClick={async () => { const r = await fetch(`/api/cda/cenarios/${c.nome}/simular`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticks: 100 }) }).then(res => res.json()); setResultadoSimulacao(r); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white">Simular</button>
                    </div>
                  ))}
                </div>
              )}
              {resultadoSimulacao && (
                <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                  <h3 className="text-sm font-semibold mb-2">Resultado: {resultadoSimulacao.cenario as string}</h3>
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    <div className="text-center p-2 rounded-lg bg-blue-500/5"><span className="text-lg font-bold text-blue-500">{resultadoSimulacao.ticks as number}</span><p className="text-[10px] text-[var(--color-muted)]">Ticks</p></div>
                    <div className="text-center p-2 rounded-lg bg-green-500/5"><span className="text-lg font-bold text-green-500">{resultadoSimulacao.eventos as number}</span><p className="text-[10px] text-[var(--color-muted)]">Eventos</p></div>
                    <div className="text-center p-2 rounded-lg bg-yellow-500/5"><span className="text-lg font-bold text-yellow-500">{resultadoSimulacao.sinais as number}</span><p className="text-[10px] text-[var(--color-muted)]">Sinais</p></div>
                    <div className="text-center p-2 rounded-lg bg-red-500/5"><span className="text-lg font-bold text-red-500">{resultadoSimulacao.decisoes as number}</span><p className="text-[10px] text-[var(--color-muted)]">Decisões</p></div>
                  </div>
                </div>
              )}
            </div>
          )}
          {view === 'syntegration' && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--color-muted)]">Team Syntegrity — deliberação não-hierárquica para consenso</p>
              <div className="flex items-center gap-2 mb-4">
                <button onClick={async () => { const r = await fetch('/api/cda/syntegration').then(res => res.json()); setSyntegrationData(r); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white">Carregar</button>
                <button onClick={async () => { await fetch('/api/cda/syntegration/iniciar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ gatilho: 'manual_diretora' }) }); const r = await fetch('/api/cda/syntegration').then(res => res.json()); setSyntegrationData(r); }} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white">Iniciar Syntegration</button>
              </div>
              {syntegrationData && (
                <div className="space-y-4">
                  {syntegrationData.ativos.length > 0 && (
                    <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                      <h3 className="text-sm font-semibold mb-2">Protocolos Ativos</h3>
                      {(syntegrationData.ativos as Array<{ id: string; gatilho: string; fase: string; participantes: number; topicos: string[] }>).map((p) => (
                        <div key={p.id} className="p-3 rounded-lg bg-[var(--color-bg)] mb-2">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-sm">{p.id}</span>
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500">{p.fase}</span>
                          </div>
                          <p className="text-xs text-[var(--color-muted)] mt-1">Gatilho: {p.gatilho} • {p.participantes} participantes</p>
                          <p className="text-xs text-[var(--color-muted)]">Tópicos: {p.topicos.join(', ')}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {syntegrationData.historico.length > 0 && (
                    <div className="p-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)]">
                      <h3 className="text-sm font-semibold mb-2">Histórico</h3>
                      <p className="text-xs text-[var(--color-muted)]">{syntegrationData.historico.length} protocolos concluídos</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
      <AgentChatModal open={chatAgente !== null} agenteNome={chatAgente || ''} onClose={() => setChatAgente(null)} />
    </div>
  );
}
