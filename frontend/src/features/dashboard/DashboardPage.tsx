import React from "react";
import {
  Activity,
  AlertTriangle,
  Cpu,
  FolderGit2,
  Layers,
  Package,
  Server,
} from "lucide-react";
import { useControlCenterSummary } from "./dashboardApi";
import { StatBlock } from "@/components/ui/StatBlock";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Badge } from "@/components/ui/Badge";

export const DashboardPage: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useControlCenterSummary();

  if (isLoading) {
    return <LoadingState message="Loading Control Center system metrics..." rows={6} />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load summary metrics"
        message={error?.message || "Could not retrieve Control Center summary."}
        onRetry={() => refetch()}
      />
    );
  }

  const { projects, generations, agent_runs, steps, artifacts, runtime } = data;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-brand-400" />
            Operational Summary Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time backend execution health, multi-tenant generations, and worker status.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant="default"
            label={`Runtime: ${runtime.default_backend.toUpperCase()}`}
            className="font-mono"
          />
          <div className="text-xs text-slate-500 font-mono">
            Auto-refresh: 10s
          </div>
        </div>
      </div>

      {/* Top Level KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatBlock
          title="Total Projects"
          value={projects.total}
          subtitle={`${projects.active} active · ${projects.archived} archived`}
          icon={<FolderGit2 className="w-5 h-5" />}
          variant="brand"
        />
        <StatBlock
          title="Active Generations"
          value={generations.active}
          subtitle={`${generations.building} building · ${generations.completed} completed`}
          icon={<Layers className="w-5 h-5" />}
          variant="default"
        />
        <StatBlock
          title="Running Agent Runs"
          value={agent_runs.running}
          subtitle={`${agent_runs.queued} queued · ${agent_runs.completed} succeeded`}
          icon={<Cpu className="w-5 h-5" />}
          variant={agent_runs.running > 0 ? "warning" : "default"}
        />
        <StatBlock
          title="Failed Executions"
          value={generations.failed + agent_runs.failed}
          subtitle={`${generations.failed} gen failed · ${agent_runs.failed} run failed`}
          icon={<AlertTriangle className="w-5 h-5" />}
          variant={generations.failed + agent_runs.failed > 0 ? "error" : "success"}
        />
      </div>

      {/* Domain Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Generations Lifecycle State Breakdown */}
        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-brand-400" />
              Generations Lifecycle
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Total: {generations.total}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Building</span>
              <span className="font-mono font-bold text-amber-400">{generations.building}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Completed</span>
              <span className="font-mono font-bold text-emerald-400">{generations.completed}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Failed</span>
              <span className="font-mono font-bold text-rose-400">{generations.failed}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Cancelled</span>
              <span className="font-mono font-bold text-slate-400">{generations.cancelled}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Draft</span>
              <span className="font-mono font-bold text-slate-400">{generations.draft}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Planning</span>
              <span className="font-mono font-bold text-purple-400">{generations.planning}</span>
            </div>
          </div>
        </div>

        {/* Agent Runs & Steps */}
        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-brand-400" />
              Agent Runs & Steps
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Runs: {agent_runs.total}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Queued Runs</span>
              <span className="font-mono font-bold text-slate-300">{agent_runs.queued}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Running Runs</span>
              <span className="font-mono font-bold text-amber-400">{agent_runs.running}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Completed Runs</span>
              <span className="font-mono font-bold text-emerald-400">{agent_runs.completed}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Failed Runs</span>
              <span className="font-mono font-bold text-rose-400">{agent_runs.failed}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Total Steps</span>
              <span className="font-mono font-bold text-slate-200">{steps.total}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Done Steps</span>
              <span className="font-mono font-bold text-emerald-400">{steps.completed}</span>
            </div>
          </div>
        </div>

        {/* Artifacts Summary */}
        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Package className="w-4 h-4 text-brand-400" />
              Durable Artifacts
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Total: {artifacts.total}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Source Code</span>
              <span className="font-mono font-bold text-slate-200">{artifacts.source_code}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Config Files</span>
              <span className="font-mono font-bold text-slate-200">{artifacts.configuration}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">ZIP Archives</span>
              <span className="font-mono font-bold text-slate-200">{artifacts.zip_archive}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex justify-between items-center">
              <span className="text-slate-400">Reports</span>
              <span className="font-mono font-bold text-slate-200">{artifacts.test_report + artifacts.security_report}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Runtime & Infrastructure Health Panel */}
      <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-sm">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-4">
          <Server className="w-4 h-4 text-emerald-400" />
          Execution Runtime & Integrations Posture
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="text-slate-500 text-[11px] uppercase tracking-wider mb-1">Backend Runtime</div>
            <div className="font-bold text-slate-200">{runtime.default_backend}</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="text-slate-500 text-[11px] uppercase tracking-wider mb-1">OpenHands Agent Server</div>
            <div className="font-bold text-slate-200 truncate" title={runtime.openhands_server_url}>
              {runtime.openhands_server_url}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-slate-500 text-[11px] uppercase tracking-wider mb-1">OpenRouter LLM</div>
              <div className="font-bold text-slate-200">
                {runtime.openrouter_configured ? "Configured & Active" : "Not Configured"}
              </div>
            </div>
            <div className={`w-2.5 h-2.5 rounded-full ${runtime.openrouter_configured ? "bg-emerald-400" : "bg-slate-600"}`} />
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-slate-500 text-[11px] uppercase tracking-wider mb-1">OpenHands Auth Key</div>
              <div className="font-bold text-slate-200">
                {runtime.openhands_api_key_configured ? "Configured" : "None / Unprotected"}
              </div>
            </div>
            <div className={`w-2.5 h-2.5 rounded-full ${runtime.openhands_api_key_configured ? "bg-emerald-400" : "bg-amber-400"}`} />
          </div>
        </div>
      </div>
    </div>
  );
};
