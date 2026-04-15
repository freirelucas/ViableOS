import type {
  BudgetPlan,
  Config,
  CoordinationRule,
  ModelInfo,
  Presets,
  Template,
  ViabilityReport,
  AssessmentConfig,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

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

async function postBlob(path: string, body: unknown): Promise<Blob> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.blob();
}

export const api = {
  // Templates
  getTemplates: () => get<Template[]>('/templates'),
  getTemplate: (key: string) => get<Config>(`/templates/${key}`),

  // Models
  getModels: () => get<ModelInfo[]>('/models'),
  getModelsByProvider: (provider: string) => get<string[]>(`/models/${provider}`),

  // Presets
  getPresets: () => get<Presets>('/presets'),

  // Validation & Budget
  validate: (config: Config) => post<string[]>('/validate', config),
  calculateBudget: (config: Config) => post<BudgetPlan>('/budget', config),
  checkViability: (config: Config) => post<ViabilityReport>('/check', config),

  // Coordination
  generateRules: (units: Array<Record<string, unknown>>) =>
    post<CoordinationRule[]>('/coordination/rules', units),

  // Generation
  generatePackage: (config: Config) => postBlob('/generate', config),
  generateLanggraphPackage: (config: Config) => postBlob('/generate/langgraph', config),

  // Chat file upload
  chatUploadFile: async (sessionId: string, file: File) => {
    const form = new FormData();
    form.append('session_id', sessionId);
    form.append('file', file);
    const res = await fetch(`${API_BASE}/chat/upload`, { method: 'POST', body: form });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json() as Promise<{ id: string; filename: string; type: string; size: number }>;
  },

  // Assessment
  transformAssessment: (assessment: AssessmentConfig) =>
    post<Config>('/assessment/transform', assessment),

  // Ops Room
  opsConnect: (runtime: string, url: string, apiKey: string) =>
    post<{ connected: boolean; error?: string }>('/ops/connect', { runtime, url, api_key: apiKey }),
  opsDisconnect: () => post<{ disconnected: boolean }>('/ops/disconnect', {}),
  opsAgents: () => get<Array<Record<string, unknown>>>('/ops/agents'),
  opsActivity: () => get<Array<Record<string, unknown>>>('/ops/activity'),
  opsSignals: () => get<Array<Record<string, unknown>>>('/ops/signals'),
  opsWorkPackages: () => get<Array<Record<string, unknown>>>('/ops/workpackages'),
  opsDecisions: () => get<Array<Record<string, unknown>>>('/ops/decisions'),
  opsResolveDecision: (id: string, action: string) =>
    post<Record<string, unknown>>(`/ops/decisions/${id}/resolve`, { action }),

  // Simulation
  runSimulation: (config: Config, ticks: number, scenario: string, triggerSyntegrationAt?: number) =>
    post<SimulationResult>('/simulate', {
      config,
      ticks,
      scenario,
      trigger_syntegration_at: triggerSyntegrationAt,
    }),
};

// Simulation response types
export interface AgentSnapshot {
  name: string;
  system_level: string;
  step_count: number;
  tasks_completed: number;
  beliefs_count: number;
  inbox_size: number;
}

export interface SyntegrationSnapshot {
  id: string;
  trigger: string;
  proposed_by: string;
  phase: string;
  topics: string[];
  outcomes_count: number;
  started_at_tick: number;
  completed_at_tick: number | null;
}

export interface SimulationResult {
  ticks_run: number;
  mode: string;
  agents: AgentSnapshot[];
  messages_sent: number;
  messages_delivered: number;
  messages_blocked: number;
  algedonic_signals: number;
  environment_events_total: number;
  syntegrations_completed: number;
  syntegration_history: SyntegrationSnapshot[];
  metrics: Array<Record<string, unknown>>;
}
