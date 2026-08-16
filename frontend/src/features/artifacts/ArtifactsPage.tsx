import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Download,
  FileCode2,
  Filter,
  Package,
  RefreshCw,
  Search,
} from "lucide-react";
import { useControlCenterArtifacts } from "./artifactsApi";
import { formatDate, formatFileSize } from "@/lib/formatters";
import { downloadFile } from "@/lib/apiClient";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";

const ARTIFACT_TYPE_OPTIONS = [
  "SOURCE_CODE",
  "CONFIGURATION",
  "TEST_REPORT",
  "DOCUMENTATION",
  "ZIP_ARCHIVE",
  "SECURITY_REPORT",
  "OTHER",
];

export const ArtifactsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchInput, setSearchInput] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const { data, isLoading, isError, error, refetch, isFetching } =
    useControlCenterArtifacts({
      page,
      page_size: 20,
      artifact_type: typeFilter || undefined,
      search: search || undefined,
    });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const handleClearFilters = () => {
    setTypeFilter("");
    setSearchInput("");
    setSearch("");
    setPage(1);
  };

  const handleDownload = async (artifactId: string, filename: string) => {
    try {
      setDownloadingId(artifactId);
      await downloadFile(`control-center/artifacts/${artifactId}/download/`, filename);
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      alert(errObj?.message || "Failed to download artifact.");
    } finally {
      setDownloadingId(null);
    }
  };

  const getTypeBadgeClass = (type: string) => {
    switch (type?.toUpperCase()) {
      case "SOURCE_CODE":
        return "bg-brand-950/60 text-brand-300 border-brand-800/60";
      case "CONFIGURATION":
        return "bg-purple-950/60 text-purple-300 border-purple-800/60";
      case "ZIP_ARCHIVE":
        return "bg-amber-950/60 text-amber-300 border-amber-800/60";
      case "TEST_REPORT":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-800/60";
      case "SECURITY_REPORT":
        return "bg-rose-950/60 text-rose-300 border-rose-800/60";
      default:
        return "bg-slate-900 text-slate-400 border-slate-800";
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Package className="w-5 h-5 text-brand-400" />
            Durable Artifacts Directory
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Persisted code files, manifests, archives, and test reports across all generation runs.
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
              placeholder="Search filename, path, checksum, project..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs text-slate-200 placeholder:text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm">
            Search
          </Button>
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          {/* Artifact Type Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs text-slate-200 focus:border-brand-500 focus:outline-none font-mono"
            >
              <option value="">All Types</option>
              {ARTIFACT_TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {(typeFilter || search) && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <LoadingState message="Loading artifacts catalog..." rows={8} />
      ) : isError ? (
        <ErrorState
          title="Error loading artifacts"
          message={error?.message || "Failed to fetch artifacts records."}
          onRetry={() => refetch()}
        />
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="No artifacts found"
          description={
            typeFilter || search
              ? "No artifacts match your selected filter criteria. Try resetting filters."
              : "No durable artifacts have been saved yet."
          }
          action={
            (typeFilter || search) && (
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
                  <th className="py-3 px-4">Artifact Name & Path</th>
                  <th className="py-3 px-4">Generation & Project</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Size & MIME</th>
                  <th className="py-3 px-4">Checksum (SHA-256)</th>
                  <th className="py-3 px-4">Storage</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {data.results.map((art) => (
                  <tr
                    key={art.id}
                    className="hover:bg-slate-800/30 transition-colors"
                  >
                    {/* Name & Path */}
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="flex items-center gap-2 font-mono">
                        <FileCode2 className="w-4 h-4 text-brand-400 shrink-0" />
                        <span className="font-semibold text-slate-200 truncate" title={art.name}>
                          {art.name}
                        </span>
                      </div>
                      <div
                        className="text-[11px] text-slate-500 font-mono truncate mt-0.5 ml-6"
                        title={art.file_path}
                      >
                        {art.file_path}
                      </div>
                    </td>

                    {/* Generation & Project */}
                    <td className="py-3.5 px-4 font-mono text-xs">
                      <div className="text-slate-200 font-medium truncate max-w-[180px]">
                        {art.project_name}
                      </div>
                      <Link
                        to={`/generations/${art.generation_id}`}
                        className="text-[11px] text-brand-400 hover:underline block truncate mt-0.5"
                      >
                        Gen: {art.generation_id.substring(0, 8)}... &rarr;
                      </Link>
                    </td>

                    {/* Type Badge */}
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded border text-[10px] font-mono font-semibold uppercase ${getTypeBadgeClass(
                          art.artifact_type
                        )}`}
                      >
                        {art.artifact_type}
                      </span>
                    </td>

                    {/* Size & MIME */}
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-300 whitespace-nowrap">
                      <div>{formatFileSize(art.size_bytes)}</div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[120px]">
                        {art.mime_type}
                      </div>
                    </td>

                    {/* Checksum SHA256 */}
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 max-w-[140px]">
                      {art.checksum_sha256 ? (
                        <div
                          className="truncate cursor-pointer hover:text-slate-200"
                          title={art.checksum_sha256}
                          onClick={() => navigator.clipboard.writeText(art.checksum_sha256)}
                        >
                          {art.checksum_sha256.substring(0, 12)}...
                        </div>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    {/* Storage Backend */}
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400">
                      <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
                        {art.storage_backend}
                      </span>
                    </td>

                    {/* Created At */}
                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                      {formatDate(art.created_at)}
                    </td>

                    {/* Download CTA */}
                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDownload(art.id, art.name)}
                        isLoading={downloadingId === art.id}
                        leftIcon={<Download className="w-3.5 h-3.5" />}
                      >
                        Download
                      </Button>
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
