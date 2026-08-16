import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Layers, Search, Filter, AlertCircle, RefreshCw } from "lucide-react";
import { useControlCenterGenerations } from "./generationsApi";
import { formatDate } from "@/lib/formatters";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";

const STATUS_OPTIONS = [
  "DRAFT",
  "SPECIFICATION",
  "APPROVED",
  "PLANNING",
  "BUILDING",
  "TESTING",
  "REVIEW",
  "PACKAGING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "PAUSED",
  "RETRYING",
];

export const GenerationsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchInput, setSearchInput] = useState<string>("");
  const [search, setSearch] = useState<string>("");

  const { data, isLoading, isError, error, refetch, isFetching } =
    useControlCenterGenerations({
      page,
      page_size: 20,
      status: statusFilter || undefined,
      search: search || undefined,
    });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const handleClearFilters = () => {
    setStatusFilter("");
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
            <Layers className="w-5 h-5 text-brand-400" />
            Generations Directory
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            System-wide autonomous plugin generation lifecycles across all customer tenants.
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
              placeholder="Search prompt, project, user email, failure..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs text-slate-200 placeholder:text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm">
            Search
          </Button>
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
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

          {(statusFilter || search) && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <LoadingState message="Loading generations..." rows={8} />
      ) : isError ? (
        <ErrorState
          title="Error loading generations"
          message={error?.message || "Failed to fetch generation records."}
          onRetry={() => refetch()}
        />
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="No generations found"
          description={
            statusFilter || search
              ? "No generations match your selected filters. Try clearing the search or status filter."
              : "No generation records have been created in the system yet."
          }
          action={
            (statusFilter || search) && (
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
                  <th className="py-3 px-4">Generation</th>
                  <th className="py-3 px-4">Project</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Progress</th>
                  <th className="py-3 px-4 text-center">Steps</th>
                  <th className="py-3 px-4 text-center">Runs</th>
                  <th className="py-3 px-4 text-center">Files</th>
                  <th className="py-3 px-4">Diagnostic / Error</th>
                  <th className="py-3 px-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {data.results.map((gen) => (
                  <tr
                    key={gen.id}
                    className="hover:bg-slate-800/30 transition-colors"
                  >
                    {/* Generation Prompt Preview */}
                    <td className="py-3.5 px-4 max-w-xs">
                      <Link
                        to={`/generations/${gen.id}`}
                        className="group/link block"
                      >
                        <div className="font-mono text-[11px] text-brand-400 group-hover/link:underline truncate" title={gen.id}>
                          {gen.id.substring(0, 8)}... &rarr;
                        </div>
                        <div
                          className="text-slate-200 group-hover/link:text-white line-clamp-2 mt-0.5"
                          title={gen.prompt_preview}
                        >
                          {gen.prompt_preview}
                        </div>
                      </Link>
                    </td>

                    {/* Project */}
                    <td className="py-3.5 px-4 font-medium text-slate-200">
                      {gen.project_name}
                    </td>

                    {/* User */}
                    <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                      {gen.user_email}
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      <Badge status={gen.status} />
                    </td>

                    {/* Progress */}
                    <td className="py-3.5 px-4 text-center font-mono">
                      <span className="text-slate-200">
                        {gen.current_step_number}
                      </span>
                      <span className="text-slate-500"> / {gen.total_steps || "—"}</span>
                    </td>

                    {/* Steps Count */}
                    <td className="py-3.5 px-4 text-center font-mono font-medium text-slate-300">
                      {gen.steps_count}
                    </td>

                    {/* Runs Count */}
                    <td className="py-3.5 px-4 text-center font-mono font-medium text-slate-300">
                      {gen.runs_count}
                    </td>

                    {/* Artifacts Count */}
                    <td className="py-3.5 px-4 text-center font-mono font-medium text-slate-300">
                      {gen.artifacts_count}
                    </td>

                    {/* Failure / Diagnostic */}
                    <td className="py-3.5 px-4 max-w-xs">
                      {gen.failure_category ? (
                        <div className="flex flex-col gap-0.5">
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold text-rose-400">
                            <AlertCircle className="w-3 h-3" />
                            {gen.failure_category}
                          </span>
                          {gen.error_message_preview && (
                            <span
                              className="text-[11px] text-slate-400 truncate"
                              title={gen.error_message_preview}
                            >
                              {gen.error_message_preview}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-600 font-mono text-[11px]">None</span>
                      )}
                    </td>

                    {/* Created At */}
                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                      {formatDate(gen.created_at)}
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
