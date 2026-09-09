import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ChevronRight, FileText, AlertTriangle, Loader2 } from 'lucide-react';
import { trApi } from '../api/trClient';

type Step = 'info' | 'perfil' | 'objeto' | 'criterios' | 'revisao';

interface TrForm {
  ministerio: string;
  orgao_solicitante: string;
  orgao_executor: string;
  modalidade: string;
  diretoria: string;
  funcao: string;
  tema: string;
  linha: string;
  recorte: string;
  enfase: string;
  projeto: string;
  objetivo_geral: string;
  justificativa: string;
  numero_vagas: number;
  data_inicio: string;
  data_fim: string;
  prazo_execucao: number;
  valor_global: number;
  valor_bolsa: number;
  orcamento: string;
}

const INITIAL_FORM: TrForm = {
  ministerio: 'Ministério do Planejamento e Orçamento',
  orgao_solicitante: 'Instituto de Pesquisa Econômica Aplicada',
  orgao_executor: 'Instituto de Pesquisa Econômica Aplicada',
  modalidade: '',
  diretoria: '',
  funcao: '',
  tema: '',
  linha: '',
  recorte: '',
  enfase: '',
  projeto: '',
  objetivo_geral: '',
  justificativa: '',
  numero_vagas: 1,
  data_inicio: '',
  data_fim: '',
  prazo_execucao: 0,
  valor_global: 0,
  valor_bolsa: 0,
  orcamento: '1230 - Operações Especiais: Cumprimento de Sentenças Judiciais / 00.00.00.000.0000',
};

const MODALIDADES = [
  'Seleção Simplificada', 'Chamada Pública Especializada', 'Seleção de Bolsistas',
  'Licitação', 'Contratação Direta', 'Credenciamento', 'Prêmio', 'Convênio',
];

const FUNCOES = [
  'Pesquisador Visitante', 'Assistente de Pesquisa', 'Especialista em Dados',
  'Especialista em Território', 'Consultor Técnico', 'Apoio Técnico',
];

const DIRETORIAS = [
  'Diretoria de Estudos e Políticas Sociais', 'Diretoria de Estudos e Políticas Regionais, Urbanas e Ambientais',
  'Diretoria de Estudos e Políticas Setoriais, de Inovação, Regulação e Infraestrutura',
  'Diretoria de Estudos e Políticas Macroeconômicas', 'Diretoria de Estudos e Políticas do Estado, das Relações de Poder e Desenvolvimento',
  'Diretoria de Estudos Internacionais',
];

const STEP_LABELS: { key: Step; label: string }[] = [
  { key: 'info', label: 'Informações Básicas' },
  { key: 'perfil', label: 'Perfil' },
  { key: 'objeto', label: 'Objeto' },
  { key: 'criterios', label: 'Critérios' },
  { key: 'revisao', label: 'Revisão' },
];

const STEPS: Step[] = ['info', 'perfil', 'objeto', 'criterios', 'revisao'];

function classNames(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ');
}

function Input({ label, value, onChange, type = 'text', className }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; className?: string;
}) {
  return (
    <label className={classNames('flex flex-col gap-1', className)}>
      <span className="text-xs font-medium text-[var(--color-muted)]">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/40"
      />
    </label>
  );
}

function Select({ label, value, onChange, options, className }: {
  label: string; value: string; onChange: (v: string) => void; options: string[]; className?: string;
}) {
  return (
    <label className={classNames('flex flex-col gap-1', className)}>
      <span className="text-xs font-medium text-[var(--color-muted)]">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/40"
      >
        <option value="">Selecione...</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

/* ───── Step Components ───── */

function InfoStep({ form, setForm }: { form: TrForm; setForm: (f: TrForm) => void }) {
  const u = (key: keyof TrForm) => (v: string) => setForm({ ...form, [key]: v });
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Informações Básicas do Documento</h2>
      <div className="grid grid-cols-2 gap-4">
        <Input label="Ministério" value={form.ministerio} onChange={u('ministerio')} />
        <Input label="Órgão Solicitante" value={form.orgao_solicitante} onChange={u('orgao_solicitante')} />
        <Input label="Órgão Executor" value={form.orgao_executor} onChange={u('orgao_executor')} />
        <Select label="Modalidade" value={form.modalidade} onChange={u('modalidade')} options={MODALIDADES} />
        <Select label="Diretoria" value={form.diretoria} onChange={u('diretoria')} options={DIRETORIAS} />
        <Input label="Data Início" type="date" value={form.data_inicio} onChange={u('data_inicio')} />
        <Input label="Data Fim" type="date" value={form.data_fim} onChange={u('data_fim')} />
        <Input label="Prazo Execução (dias)" type="number" value={String(form.prazo_execucao)} onChange={(v) => setForm({ ...form, prazo_execucao: Number(v) || 0 })} />
        <Input label="Valor Global (R$)" type="number" value={String(form.valor_global)} onChange={(v) => setForm({ ...form, valor_global: Number(v) || 0 })} />
        <Input label="Valor Bolsa (R$)" type="number" value={String(form.valor_bolsa)} onChange={(v) => setForm({ ...form, valor_bolsa: Number(v) || 0 })} />
      </div>
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-[var(--color-muted)]">Orçamento</span>
        <textarea
          value={form.orcamento}
          onChange={(e) => setForm({ ...form, orcamento: e.target.value })}
          rows={2}
          className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/40"
        />
      </label>
    </div>
  );
}

function PerfilStep({ form, setForm }: { form: TrForm; setForm: (f: TrForm) => void }) {
  const [composed, setComposed] = useState<string | null>(null);
  const [atividades, setAtividades] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const u = (key: keyof TrForm) => (v: string) => setForm({ ...form, [key]: v });

  useEffect(() => {
    if (form.funcao && form.tema) {
      setLoading(true);
      trApi.compose.criterios(form.modalidade || 'Chamada Pública Especializada', [form.funcao])
        .then(() => trApi.compose.perfil(form.modalidade || 'Chamada Pública Especializada', [form.funcao], [form.tema]))
        .then((r) => {
          setComposed(r.text);
          trApi.compose.atividades([form.funcao], [form.tema])
            .then((a) => setAtividades([a.text]))
            .catch(() => setAtividades([]));
        })
        .catch(() => { setComposed(null); setAtividades([]); })
        .finally(() => setLoading(false));
    } else {
      setComposed(null);
      setAtividades([]);
    }
  }, [form.funcao, form.tema, form.modalidade]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Perfil do Bolsista / Contratado</h2>
      <div className="grid grid-cols-2 gap-4">
        <Select label="Função" value={form.funcao} onChange={u('funcao')} options={FUNCOES} />
        <Input label="Tema de Pesquisa" value={form.tema} onChange={u('tema')} />
        <Input label="Linha de Pesquisa" value={form.linha} onChange={u('linha')} />
        <Input label="Recorte" value={form.recorte} onChange={u('recorte')} />
        <Input label="Ênfase" value={form.enfase} onChange={u('enfase')} />
      </div>
      {loading && <div className="flex items-center gap-2 text-sm text-[var(--color-muted)]"><Loader2 className="w-4 h-4 animate-spin" />Gerando perfil...</div>}
      {composed && (
        <div className="p-4 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] space-y-3">
          <div>
            <span className="text-xs font-medium text-[var(--color-muted)]">Perfil Sugerido</span>
            <p className="text-sm mt-1 whitespace-pre-wrap">{composed}</p>
          </div>
          {atividades.length > 0 && (
            <div>
              <span className="text-xs font-medium text-[var(--color-muted)]">Atividades Sugeridas</span>
              <ul className="list-disc list-inside text-sm mt-1 space-y-1">
                {atividades.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ObjetoStep({ form, setForm }: { form: TrForm; setForm: (f: TrForm) => void }) {
  const u = (key: keyof TrForm) => (v: string) => setForm({ ...form, [key]: v });
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Objeto da Contratação</h2>
      <Input label="Nome do Projeto" value={form.projeto} onChange={u('projeto')} />
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-[var(--color-muted)]">Objetivo Geral</span>
        <textarea
          value={form.objetivo_geral}
          onChange={(e) => setForm({ ...form, objetivo_geral: e.target.value })}
          rows={4}
          className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/40"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-[var(--color-muted)]">Justificativa</span>
        <textarea
          value={form.justificativa}
          onChange={(e) => setForm({ ...form, justificativa: e.target.value })}
          rows={4}
          className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/40"
        />
      </label>
      <Input label="Número de Vagas" type="number" value={String(form.numero_vagas)} onChange={(v) => setForm({ ...form, numero_vagas: Number(v) || 1 })} />
    </div>
  );
}

function CriteriosStep({ form }: { form: TrForm }) {
  const [criterios, setCriterios] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (form.modalidade && form.funcao) {
      setLoading(true);
      trApi.compose.criterios(form.modalidade, [form.funcao])
        .then((r) => setCriterios([r.text]))
        .catch(() => setCriterios([]))
        .finally(() => setLoading(false));
    }
  }, [form.modalidade, form.funcao]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Critérios de Seleção</h2>
      {loading && <div className="flex items-center gap-2 text-sm text-[var(--color-muted)]"><Loader2 className="w-4 h-4 animate-spin" />Gerando critérios...</div>}
      {criterios.length > 0 && (
        <div className="p-4 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-[var(--color-muted)]">Critérios Sugeridos</span>
            <button onClick={() => setExpanded(!expanded)} className="text-xs text-[var(--color-primary)] hover:underline">
              {expanded ? 'Recolher' : 'Expandir'}
            </button>
          </div>
          {expanded ? (
            <div className="space-y-3">
              {criterios.map((c, i) => (
                <div key={i} className="p-3 rounded border border-[var(--color-border)] text-sm whitespace-pre-wrap">{c}</div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-muted)]">{criterios.length} critério(s) gerado(s)</p>
          )}
        </div>
      )}
    </div>
  );
}

function RevisaoStep({ form, generated, validating, validationResult, onGenerate, onValidate }: {
  form: TrForm;
  generated: string | null;
  validating: boolean;
  validationResult: Record<string, unknown>[] | null;
  onGenerate: () => void;
  onValidate: () => void;
}) {
  const [showDoc, setShowDoc] = useState(false);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Revisão e Exportação</h2>

      <div className="grid grid-cols-2 gap-2 text-sm p-4 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)]">
        {Object.entries(form).filter(([, v]) => v).map(([k, v]) => (
          <div key={k} className="flex gap-2">
            <span className="font-medium text-[var(--color-muted)] capitalize">{k.replace(/_/g, ' ')}:</span>
            <span className="truncate">{String(v)}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button
          onClick={onGenerate}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90"
        >
          <FileText className="w-4 h-4" /> Gerar TR
        </button>
        <button
          onClick={onValidate}
          disabled={validating}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--color-border)] text-sm font-medium hover:bg-[var(--color-card)]"
        >
          {validating ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertTriangle className="w-4 h-4" />}
          Validar Conformidade
        </button>
      </div>

      {validationResult && (
        <div className="p-4 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] space-y-2">
          <span className="text-xs font-medium text-[var(--color-muted)]">Resultado da Validação</span>
          {validationResult.map((r, i) => {
            const ok = r.status === 'ok' || r.pass === true;
            return (
              <div key={i} className={`flex items-start gap-2 text-sm ${ok ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
                <span>{ok ? '✓' : '✗'}</span>
                <span>{String(r.rule || r.mensagem || r.message || '')}</span>
              </div>
            );
          })}
        </div>
      )}

      {generated && (
        <div>
          <button
            onClick={() => setShowDoc(!showDoc)}
            className="flex items-center gap-2 text-sm text-[var(--color-primary)] hover:underline"
          >
            {showDoc ? 'Ocultar' : 'Visualizar'} documento gerado
          </button>
          {showDoc && (
            <div className="mt-2 p-4 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] text-sm whitespace-pre-wrap max-h-96 overflow-y-auto font-mono">
              {generated}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ───── Main Page ───── */

export function TRBuilderPage() {
  const [form, setForm] = useState<TrForm>(INITIAL_FORM);
  const [step, setStep] = useState(0);
  const [generated, setGenerated] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<Record<string, unknown>[] | null>(null);
  const [, setGenerating] = useState(false);

  const currentStep = STEPS[step];

  const canAdvance = useCallback(() => {
    switch (currentStep) {
      case 'info': return !!form.modalidade && !!form.diretoria && !!form.data_inicio;
      case 'perfil': return !!form.funcao && !!form.tema;
      case 'objeto': return !!form.projeto;
      case 'criterios': return true;
      case 'revisao': return true;
    }
  }, [currentStep, form]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const r = await trApi.generate(form as unknown as Record<string, unknown>);
      setGenerated(r.text);
    } catch { setGenerated('Erro ao gerar documento.'); }
    finally { setGenerating(false); }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const r = await trApi.validate(form as unknown as Record<string, unknown>);
      setValidationResult(r.checks);
    } catch { setValidationResult([{ status: 'error', message: 'Erro ao validar.' }]); }
    finally { setValidating(false); }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-1 mb-6">
        {STEP_LABELS.map((s, i) => {
          const active = i === step;
          const done = i < step;
          return (
            <button
              key={s.key}
              onClick={() => setStep(i)}
              className={classNames(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                active && 'bg-[var(--color-primary)] text-white',
                done && 'bg-[var(--color-success)]/15 text-[var(--color-success)]',
                !active && !done && 'text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-card)]',
              )}
            >
              {done ? <Check className="w-3 h-3" /> : <span className="w-4 text-center">{i + 1}</span>}
              {s.label}
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
          className="min-h-[300px]"
        >
          {currentStep === 'info' && <InfoStep form={form} setForm={setForm} />}
          {currentStep === 'perfil' && <PerfilStep form={form} setForm={setForm} />}
          {currentStep === 'objeto' && <ObjetoStep form={form} setForm={setForm} />}
          {currentStep === 'criterios' && <CriteriosStep form={form} />}
          {currentStep === 'revisao' && (
            <RevisaoStep
              form={form}
              generated={generated}
              validating={validating}
              validationResult={validationResult}
              onGenerate={handleGenerate}
              onValidate={handleValidate}
            />
          )}
        </motion.div>
      </AnimatePresence>

      <div className="flex justify-between mt-8">
        <button
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
          className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-sm font-medium disabled:opacity-30 hover:bg-[var(--color-card)]"
        >
          Anterior
        </button>
        {step < STEPS.length - 1 && (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canAdvance()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium disabled:opacity-30 hover:opacity-90"
          >
            Próximo <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
