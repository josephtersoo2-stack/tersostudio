import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  Cpu,
  Download,
  FileCode2,
  FolderGit2,
  HardDrive,
  Layers,
  Package,
  RefreshCw,
  User,
} from "lucide-react";
import { useControlCenterGenerationDetail } from "./generationsApi";
import { LiveEventsPanel } from "./LiveEventsPanel";
import { formatDate, formatDuration, formatFileSize } from "@/lib/formatters";
import { downloadFile } from "@/lib/apiClient";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";

export const GenerationDetailPage: React.FC = () => {
  const { generationId } = useParams<{ generationId: string }>();
  const { data: gen, isLoading, isError, error, refetch, isFetching } =
    useControlCenterGenerationDetail(generationId);

  const [downloadingArtifactId, setDownloadingArtifactId] = useState<string | null>(null);

  const handleDownload = async (artifactId: string, filename: string) => {
    try {
      setDownloadingArtifactId(artifactId);
      await downloadFile(`control-center/artifacts/${artifactId}/download/`, filename);
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      alert(errObj?.message || "Failed to download artifact.");
    } finally {
      setDownloadingArtifactId(null);
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading generation operational details..." rows={8} />;
  }

  if (isError || !gen) {
    return (
      <ErrorState
        title="Failed to load generation detail"
        message={error?.message || "Could not retrieve generation operational record."}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Navigation & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-4">
          <Link
            to="/generations"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Back to Generations"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-slate-100 tracking-tight font-mono">
                Generation {gen.id.substring(0, 13)}...
              </h1>
              <Badge status={gen.status} />
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 font-mono">
              <span className="flex items-center gap-1">
                <FolderGit2 className="w-3.5 h-3.5 text-slate-500" />
                {gen.project.name}
              </span>
              <span>·</span>
              <span className="flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-slate-500" />
                {gen.user.email}
              </span>
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

      {/* Failure Diagnostic Alert (if present) */}
      {gen.failure_category && (
        <div className="p-4 rounded-xl border border-rose-900/60 bg-rose-950/30 text-xs text-rose-200 space-y-2">
          <div className="flex items-center gap-2 font-bold font-mono text-rose-400">
            <AlertCircle className="w-4 h-4" />
            <span>Failure Classification: {gen.failure_category}</span>
          </div>
          {gen.error_message && (
            <p className="text-slate-300 font-mono bg-slate-950/60 p-3 rounded-lg border border-rose-900/40 whitespace-pre-wrap">
              {gen.error_message}
            </p>
          )}
        </div>
      )}

      {/* Top Grid: Prompt & Lifecycle Timestamps */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Full Prompt Card */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-brand-400" />
              Full Specification & Requirements Prompt
            </h3>
            <span className="text-[11px] font-mono text-slate-500">
              {gen.prompt.length} chars
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-200 font-mono leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
            {gen.prompt}
          </div>

          {/* Metadata Tags */}
          {gen.metadata && Object.keys(gen.metadata).length > 0 && (
            <div className="pt-2 flex items-center gap-2 flex-wrap text-[11px] font-mono">
              <span className="text-slate-500">Config:</span>
              {Object.entries(gen.metadata).map(([k, v]) => (
                <span
                  key={k}
                  className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300"
                >
                  {k}: <strong className="text-brand-300">{String(v)}</strong>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Timestamps & Lifecycle Card */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2 border-b border-slate-800 pb-2.5">
            <Calendar className="w-3.5 h-3.5 text-brand-400" />
            Lifecycle State Timestamps
          </h3>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Created</span>
              <span className="text-slate-200">{formatDate(gen.timestamps.created_at)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Last Updated</span>
              <span className="text-slate-200">{formatDate(gen.timestamps.updated_at)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Completed</span>
              <span className="text-slate-200">
                {gen.timestamps.completed_at ? formatDate(gen.timestamps.completed_at) : "—"}
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Failed</span>
              <span className="text-rose-400">
                {gen.timestamps.failed_at ? formatDate(gen.timestamps.failed_at) : "—"}
              </span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-slate-400">Progress</span>
              <span className="text-brand-300 font-bold">
                Step {gen.current_step_number} of {gen.total_steps || "—"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Steps & Agent Runs */}
      <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 overflow-hidden shadow-xl space-y-3">
        <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Execution Steps & Agent Runs ({gen.steps.length} Steps)
            </h3>
          </div>
        </div>

        {gen.steps.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            No execution steps planned or created yet.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {gen.steps.map((step) => (
              <div key={step.id} className="p-4 space-y-3 hover:bg-slate-900/40 transition-colors">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-md bg-slate-800 flex items-center justify-center font-mono text-xs font-bold text-slate-200">
                      {step.step_number}
                    </span>
                    <div>
                      <h4 className="text-xs font-bold text-slate-100">{step.name}</h4>
                      <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                        Role: {step.agent_role}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge status={step.status} />
                    <span className="text-[11px] font-mono text-slate-500">
                      {formatDuration(step.started_at, step.completed_at)}
                    </span>
                  </div>
                </div>

                {/* Nested Agent Runs for this Step */}
                {step.runs.length > 0 && (
                  <div className="ml-9 rounded-lg border border-slate-800/60 bg-slate-950/60 p-3 space-y-2">
                    <div className="text-[11px] uppercase tracking-wider font-mono text-slate-500 font-semibold">
                      Run Attempts ({step.runs.length})
                    </div>
                    <div className="space-y-1.5">
                      {step.runs.map((r) => (
                        <div
                          key={r.id}
                          className="flex items-center justify-between gap-3 text-xs font-mono p-2 rounded bg-slate-900/60 border border-slate-800/40 hover:border-slate-700 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-slate-300 font-semibold">
                              Attempt #{r.run_number}
                            </span>
                            <span className="text-slate-500">({r.id.substring(0, 8)}...)</span>
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300">
                              {r.runtime_type}
                            </span>
                            {r.model_name && (
                              <span className="text-slate-400 text-[11px] truncate max-w-xs">
                                {r.model_name}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-3">
                            <Badge status={r.status} />
                            <Link
                              to={`/agent-runs/${r.id}`}
                              className="text-[11px] text-brand-400 hover:text-brand-300 hover:underline"
                            >
                              Inspect Run &rarr;
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Workspace & Artifacts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workspace Card */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <HardDrive className="w-3.5 h-3.5 text-brand-400" />
              Runtime Workspace Environment
            </h3>
            {gen.workspace && (
              <span
                className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded ${
                  gen.workspace.is_active
                    ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {gen.workspace.is_active ? "Active" : "Unmounted"}
              </span>
            )}
          </div>

          {gen.workspace ? (
            <div className="space-y-2 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 truncate">
                <span className="text-slate-500">Path: </span>
                <span className="text-slate-200 font-semibold">{gen.workspace.workspace_path}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60">
                  <span className="text-slate-500">Storage: </span>
                  <span className="text-slate-300 uppercase">{gen.workspace.storage_type}</span>
                </div>
                <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60">
                  <span className="text-slate-500">Disk Usage: </span>
                  <span className="text-slate-300">{formatFileSize(gen.workspace.disk_usage_bytes)}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-slate-500 font-mono">
              No isolated workspace provisioned for this generation.
            </div>
          )}
        </div>

        {/* Artifacts Card */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Package className="w-3.5 h-3.5 text-brand-400" />
              Generated Durable Artifacts ({gen.artifacts.length})
            </h3>
          </div>

          {gen.artifacts.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 font-mono">
              No artifacts produced yet.
            </div>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {gen.artifacts.map((art) => (
                <div
                  key={art.id}
                  className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs font-mono"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileCode2 className="w-4 h-4 text-brand-400 shrink-0" />
                    <div className="truncate">
                      <div className="text-slate-200 font-medium truncate" title={art.name}>
                        {art.name}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate">
                        {art.artifact_type} · {formatFileSize(art.size_bytes)}
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(art.id, art.name)}
                    isLoading={downloadingArtifactId === art.id}
                    leftIcon={<Download className="w-3.5 h-3.5" />}
                  >
                    Download
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Live Events Timeline Panel */}
      <LiveEventsPanel generationId={gen.id} />
    </div>
  );
};
