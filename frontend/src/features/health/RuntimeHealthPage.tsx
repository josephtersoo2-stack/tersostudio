import React from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  Layers,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useControlCenterHealth } from "./healthApi";
import { ServiceStatus } from "./healthTypes";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";

export const RuntimeHealthPage: React.FC = () => {
  const { data: health, isLoading, isError, error, refetch, isFetching } =
    useControlCenterHealth();

  if (isLoading) {
    return <LoadingState message="Probing system health and connectivity..." rows={6} />;
  }

  if (isError || !health) {
    return (
      <ErrorState
        title="Health probe failed"
        message={error?.message || "Could not reach Control Center health endpoint."}
        onRetry={() => refetch()}
      />
    );
  }

  const { status, services, runtime } = health;

  const renderServiceStatusBadge = (svc: ServiceStatus) => {
    if (svc.status === "healthy") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-[11px] font-mono font-semibold">
          <CheckCircle2 className="w-3 h-3" />
          Healthy
        </span>
      );
    }
    if (svc.status === "degraded" || svc.status === "simulated") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-400 text-[11px] font-mono font-semibold">
          <AlertTriangle className="w-3 h-3" />
          {svc.status.toUpperCase()}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-950/60 border border-rose-800/60 text-rose-400 text-[11px] font-mono font-semibold">
        <AlertTriangle className="w-3 h-3" />
        {svc.status.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-emerald-400" />
            Runtime & System Health
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Live health verification, latency diagnostics, and execution connectivity across services.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-500 font-mono">
            Auto-refresh: 10s
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            isLoading={isFetching}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Probe Now
          </Button>
        </div>
      </div>

      {/* Overall Posture Banner */}
      <div
        className={`p-6 rounded-2xl border backdrop-blur-md flex items-center justify-between gap-4 ${
          status === "ready"
            ? "border-emerald-900/60 bg-emerald-950/20 text-emerald-300"
            : status === "degraded"
            ? "border-amber-900/60 bg-amber-950/20 text-amber-300"
            : "border-rose-900/60 bg-rose-950/20 text-rose-300"
        }`}
      >
        <div className="flex items-center gap-4">
          <div
            className={`w-12 h-12 rounded-xl border flex items-center justify-center ${
              status === "ready"
                ? "bg-emerald-900/40 border-emerald-700/50 text-emerald-400"
                : status === "degraded"
                ? "bg-amber-900/40 border-amber-700/50 text-amber-400"
                : "bg-rose-900/40 border-rose-700/50 text-rose-400"
            }`}
          >
            {status === "ready" ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : (
              <AlertTriangle className="w-6 h-6" />
            )}
          </div>

          <div>
            <div className="text-base font-bold text-slate-100 uppercase tracking-wide font-mono">
              System Health Status: {status}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {status === "ready"
                ? "All execution pipelines, database clusters, Celery brokers, and agent runtimes are operating nominally."
                : status === "degraded"
                ? "Auxiliary services or agent endpoints are experiencing latency or degraded connectivity."
                : "Critical database or message brokers are unresponsive. Action required."}
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 font-mono text-xs text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800/80">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Staff Telemetry</span>
        </div>
      </div>

      {/* Services Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Database */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-bold">
              <Database className="w-4 h-4 text-brand-400" />
              <span>Primary Database (PostgreSQL)</span>
            </div>
            {renderServiceStatusBadge(services.database)}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-500">Latency:</span>
              <span className="text-slate-200">
                {services.database.latency_ms !== undefined
                  ? `${services.database.latency_ms} ms`
                  : "—"}
              </span>
            </div>
            {services.database.error && (
              <div className="text-rose-400 text-[11px] mt-1 bg-rose-950/40 p-2 rounded border border-rose-900/60">
                {services.database.error}
              </div>
            )}
          </div>
        </div>

        {/* Redis */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-bold">
              <Radio className="w-4 h-4 text-rose-400" />
              <span>Redis (Channel Layer & Tasks)</span>
            </div>
            {renderServiceStatusBadge(services.redis)}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-500">Ping Latency:</span>
              <span className="text-slate-200">
                {services.redis.latency_ms !== undefined
                  ? `${services.redis.latency_ms} ms`
                  : "—"}
              </span>
            </div>
            {services.redis.error && (
              <div className="text-rose-400 text-[11px] mt-1 bg-rose-950/40 p-2 rounded border border-rose-900/60">
                {services.redis.error}
              </div>
            )}
          </div>
        </div>

        {/* Celery Broker */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-bold">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>Celery Worker Broker</span>
            </div>
            {renderServiceStatusBadge(services.celery_broker)}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-500">Transport:</span>
              <span className="text-slate-200 uppercase">
                {services.celery_broker.transport || "redis"}
              </span>
            </div>
            {services.celery_broker.error && (
              <div className="text-rose-400 text-[11px] mt-1 bg-rose-950/40 p-2 rounded border border-rose-900/60">
                {services.celery_broker.error}
              </div>
            )}
          </div>
        </div>

        {/* OpenHands Agent Server */}
        <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-bold">
              <Server className="w-4 h-4 text-purple-400" />
              <span>OpenHands Agent Server</span>
            </div>
            {renderServiceStatusBadge(services.openhands)}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-500">Endpoint:</span>
              <span className="text-slate-200 truncate max-w-xs" title={services.openhands.server_url}>
                {services.openhands.server_url || "http://localhost:8010"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-500">Response Latency:</span>
              <span className="text-slate-200">
                {services.openhands.latency_ms !== undefined
                  ? `${services.openhands.latency_ms} ms`
                  : "—"}
              </span>
            </div>
            {services.openhands.error && (
              <div className="text-rose-400 text-[11px] mt-1 bg-rose-950/40 p-2 rounded border border-rose-900/60">
                {services.openhands.error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Runtime Configuration Posture */}
      <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-sm space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-brand-400" />
          Execution Engine & Provider Posture
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Active Backend Adapter</div>
            <div className="font-bold text-slate-200 uppercase">{runtime.backend}</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">OpenRouter LLM Provider</div>
              <div className="font-bold text-slate-200">
                {runtime.openrouter_configured ? "Configured & Active" : "Not Configured"}
              </div>
            </div>
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                runtime.openrouter_configured ? "bg-emerald-400" : "bg-slate-600"
              }`}
            />
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">OpenHands Auth Key</div>
              <div className="font-bold text-slate-200">
                {runtime.openhands_api_key_configured ? "Configured" : "None / Local Only"}
              </div>
            </div>
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                runtime.openhands_api_key_configured ? "bg-emerald-400" : "bg-amber-400"
              }`}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
