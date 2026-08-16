import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Cpu, Search, Filter, RefreshCw, AlertCircle, Clock } from "lucide-react";
import { useControlCenterAgentRuns } from "./agentRunsApi";
import { formatDate, formatDuration, formatTokens } from "@/lib/formatters";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";

const STATUS_OPTIONS = [
  "QUEUED",
  "RUNNING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "TIMED_OUT",
];

const RUNTIME_OPTIONS = ["openhands", "mock"];

export const AgentRunsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [runtimeFilter, setRuntimeFilter] = useState<string>("");
  const [searchInput, setSearchInput] = useState<string>("");
  const [search, setSearch] = useState<string>("");

  const { data, isLoading, isError, error, refetch, isFetching } =
    useControlCenterAgentRuns({
      page,
      page_size: 20,
      status: statusFilter || undefined,
      runtime_type: runtimeFilter || undefined,
      search: search || undefined,
    });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const handleClearFilters = () => {
    setStatusFilter("");
    setRuntimeFilter("");
    setSearchInput("");
    setSearch("");
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-brand-400" />
            Agent Runs Directory
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Low-level execution attempts dispatched to OpenHands SDK, Celery workers, and LLM backends.
          </p>
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

      {/* Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full md:max-w-md flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search prompt, output, model, session, conversation..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs text-slate-200 placeholder:text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm">
            Search
          </Button>
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs text-slate-200 focus:border-brand-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>

          {/* Runtime Filter */}
          <div className="flex items-center gap-2">
            <select
              value={runtimeFilter}
              onChange={(e) => {
                setRuntimeFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs text-slate-200 focus:border-brand-500 focus:outline-none font-mono"
            >
              <option value="">All Runtimes</option>
              {RUNTIME_OPTIONS.map((rt) => (
                <option key={rt} value={rt}>
                  {rt}
                </option>
              ))}
            </select>
          </div>

          {(statusFilter || runtimeFilter || search) && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <LoadingState message="Loading agent runs..." rows={8} />
      ) : isError ? (
        <ErrorState
          title="Error loading agent runs"
          message={error?.message || "Failed to fetch agent run records."}
          onRetry={() => refetch()}
        />
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="No agent runs found"
          description={
            statusFilter || runtimeFilter || search
              ? "No agent runs match your selected filter criteria. Try resetting filters."
              : "No agent run attempts have been recorded yet."
          }
          action={
            (statusFilter || runtimeFilter || search) && (
              <Button variant="secondary" size="sm" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            )
          }
        />
      ) : (
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/30 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-semibold font-mono">
                <tr>
                  <th className="py-3 px-4">Run / Attempt</th>
                  <th className="py-3 px-4">Generation & Step</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Runtime & Model</th>
                  <th className="py-3 px-4">Session & Remote Conv</th>
                  <th className="py-3 px-4">Output Preview</th>
                  <th className="py-3 px-4">Tokens</th>
                  <th className="py-3 px-4">Timing</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {data.results.map((run) => (
                  <tr
                    key={run.id}
                    className="hover:bg-slate-800/30 transition-colors"
                  >
                    {/* Run & Prompt */}
                    <td className="py-3.5 px-4 max-w-xs">
                      <Link to={`/agent-runs/${run.id}`} className="group/link block">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] font-semibold text-brand-400 group-hover/link:underline">
                            Attempt #{run.run_number} &rarr;
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">
                            ({run.id.substring(0, 8)}...)
                          </span>
                        </div>
                        <div
                          className="text-slate-400 group-hover/link:text-slate-200 line-clamp-2 mt-1"
                          title={run.prompt_preview}
                        >
                          {run.prompt_preview}
                        </div>
                      </Link>
                    </td>

                    {/* Generation & Step */}
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-200">
                        Step {run.step_number}: {run.step_name}
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono mt-0.5">
                        <Link
                          to={`/generations/${run.generation_id}`}
                          className="text-slate-400 hover:text-brand-300 hover:underline"
                        >
                          Gen: {run.generation_id.substring(0, 8)}...
                        </Link>
                        <span>·</span>
                        <span className="text-slate-400">{run.user_email}</span>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      <Badge status={run.status} />
                      {run.failure_category && (
                        <div className="mt-1 flex items-center gap-1 text-[10px] font-mono text-rose-400 font-semibold">
                          <AlertCircle className="w-3 h-3" />
                          {run.failure_category}
                        </div>
                      )}
                    </td>

                    {/* Runtime & Model */}
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <div className="text-brand-300 font-semibold uppercase text-[10px]">
                        {run.runtime_type}
                      </div>
                      <div
                        className="text-slate-300 truncate max-w-[160px] mt-0.5"
                        title={run.model_name}
                      >
                        {run.model_name || "—"}
                      </div>
                    </td>

                    {/* Session & Remote Conversation UUID */}
                    <td className="py-3.5 px-4 font-mono text-[11px] max-w-xs">
                      <div className="text-slate-400 truncate" title={run.session_id}>
                        {run.session_id || "—"}
                      </div>
                      <div
                        className="text-slate-500 text-[10px] truncate mt-0.5"
                        title={run.remote_conversation_id}
                      >
                        {run.remote_conversation_id ? `conv: ${run.remote_conversation_id.substring(0, 12)}...` : "—"}
                      </div>
                    </td>

                    {/* Output Preview */}
                    <td className="py-3.5 px-4 max-w-xs">
                      {run.output_preview ? (
                        <div
                          className="text-slate-300 font-mono text-[11px] line-clamp-2 bg-slate-950/40 p-1.5 rounded border border-slate-800/40"
                          title={run.output_preview}
                        >
                          {run.output_preview}
                        </div>
                      ) : (
                        <span className="text-slate-600 font-mono text-[11px]">No output produced</span>
                      )}
                    </td>

                    {/* Tokens */}
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-300 whitespace-nowrap">
                      {formatTokens(run.token_usage)}
                    </td>

                    {/* Timing */}
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      <div className="flex items-center gap-1 text-slate-300">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{formatDuration(run.started_at, run.completed_at)}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {formatDate(run.created_at)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="border-t border-slate-800 bg-slate-950/40 px-4">
            <Pagination
              currentPage={data.pagination.current_page}
              totalPages={data.pagination.total_pages}
              totalCount={data.pagination.count}
              pageSize={data.pagination.page_size}
              onPageChange={(newPage) => setPage(newPage)}
            />
          </div>
        </div>
      )}
    </div>
  );
};
