import { useState } from 'react';
import {
  Play,
  RotateCcw,
  Activity,
  Users,
  MessageSquare,
  AlertTriangle,
  Zap,
  Globe,
} from 'lucide-react';
import { useConfigStore } from '../store/useConfigStore';
import { api } from '../api/client';
import type { SimulationResult, AgentSnapshot } from '../api/client';

const SCENARIOS = [
  { value: 'policy_research', label: 'DIEST Policy Research' },
  { value: 'minimal', label: 'Minimal (test)' },
  { value: 'none', label: 'No environment' },
];

const LEVEL_COLORS: Record<string, string> = {
  s1: 'var(--color-accent)',
  s2: 'var(--color-warning)',
  s3: 'var(--color-primary)',
  s3star: 'var(--color-danger)',
  s4: 'var(--color-secondary)',
  s5: 'var(--color-success)',
};

const LEVEL_LABELS: Record<string, string> = {
  s1: 'S1 Operations',
  s2: 'S2 Coordination',
  s3: 'S3 Control',
  s3star: 'S3* Audit',
  s4: 'S4 Intelligence',
  s5: 'S5 Policy',
};

function BarChart({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="w-full h-2 rounded-full bg-[var(--color-border)]">
      <div
        className="h-2 rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Activity;
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4 flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ backgroundColor: `${color || 'var(--color-primary)'}20` }}
      >
        <Icon className="w-5 h-5" style={{ color: color || 'var(--color-primary)' }} />
      </div>
      <div>
        <div className="text-xs text-[var(--color-muted)]">{label}</div>
        <div className="text-lg font-bold text-[var(--color-text)]">{value}</div>
      </div>
    </div>
  );
}

function AgentRow({ agent, maxSteps }: { agent: AgentSnapshot; maxSteps: number }) {
  const color = LEVEL_COLORS[agent.system_level] || 'var(--color-muted)';
  return (
    <div className="flex items-center gap-3 py-2">
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />
      <div className="w-44 truncate text-sm text-[var(--color-text)]">{agent.name}</div>
      <div className="w-16 text-xs text-[var(--color-muted)]">
        {LEVEL_LABELS[agent.system_level]?.split(' ')[0] || agent.system_level.toUpperCase()}
      </div>
      <div className="flex-1">
        <BarChart value={agent.step_count} max={maxSteps} color={color} />
      </div>
      <div className="w-16 text-right text-xs text-[var(--color-muted)]">
        {agent.step_count} steps
      </div>
      <div className="w-16 text-right text-xs text-[var(--color-text)]">
        {agent.tasks_completed} tasks
      </div>
    </div>
  );
}

export function SimulationPage() {
  const config = useConfigStore((s) => s.config);
  const [ticks, setTicks] = useState(100);
  const [scenario, setScenario] = useState('policy_research');
  const [triggerSynteg, setTriggerSynteg] = useState(false);
  const [syntegTick, setSyntegTick] = useState(40);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState('');

  const hasConfig = config.viable_system.name && config.viable_system.system_1.length > 0;

  const runSimulation = async () => {
    setRunning(true);
    setError('');
    setResult(null);
    try {
      const res = await api.runSimulation(
        config,
        ticks,
        scenario,
        triggerSynteg ? syntegTick : undefined,
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed');
    } finally {
      setRunning(false);
    }
  };

  if (!hasConfig) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Play className="w-12 h-12 text-[var(--color-muted)]" />
        <p className="text-[var(--color-muted)] text-lg">Configure a system first</p>
        <p className="text-[var(--color-muted)] text-sm">
          Use the Chat or Wizard to create a VSM configuration, then simulate it here.
        </p>
      </div>
    );
  }

  const maxSteps = result
    ? Math.max(...result.agents.map((a) => a.step_count), 1)
    : 1;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          VSM Simulation
        </h1>
        <p className="text-sm text-[var(--color-muted)] mt-1">
          Run {config.viable_system.name} as a multi-agent simulation with Beer's tempo hierarchy
        </p>
      </div>

      {/* Controls */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs text-[var(--color-muted)] mb-1">Ticks</label>
            <input
              type="number"
              value={ticks}
              onChange={(e) => setTicks(Math.max(1, Math.min(1000, Number(e.target.value))))}
              className="w-24 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)]"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--color-muted)] mb-1">Scenario</label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)]"
            >
              {SCENARIOS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="synteg"
              checked={triggerSynteg}
              onChange={(e) => setTriggerSynteg(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="synteg" className="text-xs text-[var(--color-muted)]">
              Trigger Syntegration at tick
            </label>
            {triggerSynteg && (
              <input
                type="number"
                value={syntegTick}
                onChange={(e) => setSyntegTick(Number(e.target.value))}
                className="w-16 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-1 text-sm text-[var(--color-text)]"
              />
            )}
          </div>
          <div className="flex gap-2 ml-auto">
            <button
              onClick={() => setResult(null)}
              disabled={!result}
              className="rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors disabled:opacity-30"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={runSimulation}
              disabled={running}
              className="rounded-lg bg-[var(--color-primary)] px-6 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {running ? 'Running...' : 'Run Simulation'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-[var(--color-danger)] bg-[var(--color-danger)]/10 p-4 text-sm text-[var(--color-danger)]">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={Activity}
              label="Ticks Simulated"
              value={result.ticks_run}
              color="var(--color-primary)"
            />
            <StatCard
              icon={MessageSquare}
              label="Messages Sent"
              value={result.messages_sent}
              color="var(--color-accent)"
            />
            <StatCard
              icon={AlertTriangle}
              label="Algedonic Alerts"
              value={result.algedonic_signals}
              color={result.algedonic_signals > 0 ? 'var(--color-danger)' : 'var(--color-muted)'}
            />
            <StatCard
              icon={Globe}
              label="Environment Events"
              value={result.environment_events_total}
              color="var(--color-secondary)"
            />
          </div>

          {/* Agent Activity */}
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4">
            <h2 className="text-sm font-bold text-[var(--color-text)] mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Agent Activity
            </h2>
            <div className="space-y-1">
              {result.agents
                .sort((a, b) => {
                  const order = ['s5', 's4', 's3', 's3star', 's2', 's1'];
                  return order.indexOf(a.system_level) - order.indexOf(b.system_level);
                })
                .map((agent) => (
                  <AgentRow key={agent.name} agent={agent} maxSteps={maxSteps} />
                ))}
            </div>
          </div>

          {/* Syntegration History */}
          {result.syntegration_history.length > 0 && (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4">
              <h2 className="text-sm font-bold text-[var(--color-text)] mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Syntegration Events
              </h2>
              {result.syntegration_history.map((s) => (
                <div
                  key={s.id}
                  className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-3 mb-2"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[var(--color-text)]">
                      #{s.id}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        s.phase === 'completed'
                          ? 'bg-[var(--color-success)]/20 text-[var(--color-success)]'
                          : 'bg-[var(--color-warning)]/20 text-[var(--color-warning)]'
                      }`}
                    >
                      {s.phase}
                    </span>
                  </div>
                  <div className="text-xs text-[var(--color-muted)] space-y-1">
                    <div>
                      Trigger: <span className="text-[var(--color-text)]">{s.trigger}</span> by{' '}
                      <span className="text-[var(--color-text)]">{s.proposed_by}</span>
                    </div>
                    <div>
                      Ticks: {s.started_at_tick} &rarr; {s.completed_at_tick ?? '...'}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {s.topics.map((t) => (
                        <span
                          key={t}
                          className="px-2 py-0.5 rounded-full bg-[var(--color-primary)]/15 text-[var(--color-primary)] text-xs"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                    <div>Outcomes: {s.outcomes_count}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Message Flow Summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4 text-center">
              <div className="text-2xl font-bold text-[var(--color-accent)]">
                {result.messages_sent}
              </div>
              <div className="text-xs text-[var(--color-muted)]">Messages Sent</div>
            </div>
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4 text-center">
              <div className="text-2xl font-bold text-[var(--color-success)]">
                {result.messages_delivered}
              </div>
              <div className="text-xs text-[var(--color-muted)]">Delivered</div>
            </div>
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4 text-center">
              <div
                className="text-2xl font-bold"
                style={{
                  color:
                    result.messages_blocked > 0
                      ? 'var(--color-danger)'
                      : 'var(--color-success)',
                }}
              >
                {result.messages_blocked}
              </div>
              <div className="text-xs text-[var(--color-muted)]">Blocked (VSM violations)</div>
            </div>
          </div>

          {/* Mode */}
          <div className="text-xs text-[var(--color-muted)] text-center">
            Final mode: <span className="text-[var(--color-text)] font-medium">{result.mode}</span>
            {' | '}Agents: {result.agents.length}
            {' | '}Syntegrations: {result.syntegrations_completed}
          </div>
        </>
      )}
    </div>
  );
}
