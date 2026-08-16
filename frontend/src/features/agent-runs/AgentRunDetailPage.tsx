import React from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Cpu,
  FileCode2,
  Layers,
  RefreshCw,
  Sparkles,
  Terminal,
} from "lucide-react";
import { useControlCenterAgentRunDetail } from "./agentRunsApi";
import { formatDate, formatDuration, formatTokens } from "@/lib/formatters";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";

export const AgentRunDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const { data: run, isLoading, isError, error, refetch, isFetching } =
    useControlCenterAgentRunDetail(runId);

  if (isLoading) {
    return <LoadingState message="Loading agent run diagnostics..." rows={8} />;
  }

  if (isError || !run) {
    return (
      <ErrorState
        title="Failed to load agent run diagnostics"
        message={error?.message || "Could not retrieve agent run record."}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Back Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-4">
          <Link
            to="/agent-runs"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Back to Agent Runs"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-slate-100 tracking-tight font-mono">
                Run Attempt #{run.run_number} ({run.id.substring(0, 8)}...)
              </h1>
              <Badge status={run.status} />
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 font-mono">
              <span className="flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-brand-400" />
                Step {run.step.step_number}: {run.step.name}
              </span>
              <span>·</span>
              <Link
                to={`/generations/${run.generation.id}`}
                className="text-brand-400 hover:underline flex items-center gap-1"
              >
                Generation {run.generation.id.substring(0, 8)}... &rarr;
              </Link>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            isLoading={isFetching}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Failure Diagnostic Alert */}
      {run.failure_category && (
        <div className="p-4 rounded-xl border border-rose-900/60 bg-rose-950/30 text-xs text-rose-200 space-y-2">
          <div className="flex items-center gap-2 font-bold font-mono text-rose-400">
            <AlertCircle className="w-4 h-4" />
            <span>Failure Classification: {run.failure_category}</span>
          </div>
          {run.error_details && Object.keys(run.error_details).length > 0 && (
            <div className="bg-slate-950/70 p-3 rounded-lg border border-rose-900/40 font-mono text-[11px] overflow-x-auto">
              <pre className="text-slate-300">
                {JSON.stringify(run.error_details, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Execution Context & Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Runtime & Model */}
        <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-1.5 font-mono text-xs">
          <div className="text-slate-500 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-brand-400" />
            Runtime Adapter & Model
          </div>
          <div className="font-bold text-slate-100 uppercase">{run.runtime_type}</div>
          <div className="text-slate-400 truncate text-[11px]" title={run.model_name}>
            {run.model_name || "—"}
          </div>
        </div>

        {/* Identifiers */}
        <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-1.5 font-mono text-xs">
          <div className="text-slate-500 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-brand-400" />
            Session & Conversation
          </div>
          <div className="text-slate-300 truncate text-[11px]" title={run.session_id}>
            sess: {run.session_id || "—"}
          </div>
          <div className="text-slate-400 truncate text-[11px]" title={run.remote_conversation_id}>
            conv: {run.remote_conversation_id || "—"}
          </div>
        </div>

        {/* Tokens & Cost */}
        <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-1.5 font-mono text-xs">
          <div className="text-slate-500 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Token Consumption
          </div>
          <div className="font-bold text-slate-200">
            {formatTokens(run.token_usage)}
          </div>
          <div className="text-[10px] text-slate-500">Live LiteLLM metrics</div>
        </div>

        {/* Timing & Duration */}
        <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-1.5 font-mono text-xs">
          <div className="text-slate-500 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            Execution Duration
          </div>
          <div className="font-bold text-emerald-400">
            {formatDuration(run.started_at, run.completed_at)}
          </div>
          <div className="text-[10px] text-slate-500">
            Started: {run.started_at ? formatDate(run.started_at) : "Pending"}
          </div>
        </div>
      </div>

      {/* Full Prompt & Full Output Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Full Prompt Block */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <FileCode2 className="w-3.5 h-3.5 text-brand-400" />
              Full Dispatched Prompt
            </h3>
            <span className="text-[11px] font-mono text-slate-500">
              {run.prompt.length} chars
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-200 font-mono leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
            {run.prompt}
          </div>
        </div>

        {/* Full Output Block */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
              Final Execution Output & Synthesis
            </h3>
            <span className="text-[11px] font-mono text-slate-500">
              {run.output.length} chars
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-200 font-mono leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
            {run.output || (
              <span className="text-slate-600 italic">No output text generated.</span>
            )}
          </div>
        </div>
      </div>

      {/* Raw Token Usage Payload Viewer */}
      {run.token_usage && Object.keys(run.token_usage).length > 0 && (
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/30 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2 border-b border-slate-800 pb-2.5">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            Detailed Token Usage & Cost Breakdown
          </h3>

          <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 font-mono text-[11px] overflow-x-auto">
            <pre className="text-slate-300">
              {JSON.stringify(run.token_usage, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
