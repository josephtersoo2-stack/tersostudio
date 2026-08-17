import React, { useState } from "react";
import {
  FolderGit2,
  Search,
  Layers,
  ChevronLeft,
  ChevronRight,
  User,
  Calendar,
  Archive,
  CheckCircle2,
} from "lucide-react";
import { useProjects, ProjectListItem } from "./projectsApi";

export const ProjectsPage: React.FC = () => {
  const [page, setPage] = useState<number>(1);
  const [search, setSearch] = useState<string>("");
  const [archivedFilter, setArchivedFilter] = useState<string>("all");

  const { data, isLoading, error } = useProjects({
    page,
    page_size: 15,
    is_archived: archivedFilter,
    search: search || undefined,
  });

  const projects = data?.results ?? [];
  const pagination = data?.pagination;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FolderGit2 className="h-6 w-6 text-brand-400" />
            WordPress Engineering Projects
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Registered WordPress plugins, target runtime configurations, and lifecycle generation records.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            {pagination?.count ?? 0} Total Projects
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              setArchivedFilter("all");
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              archivedFilter === "all"
                ? "bg-brand-600/30 text-brand-300 border border-brand-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
            }`}
          >
            All Projects
          </button>
          <button
            onClick={() => {
              setArchivedFilter("false");
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              archivedFilter === "false"
                ? "bg-emerald-600/30 text-emerald-300 border border-emerald-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
            }`}
          >
            Active Only
          </button>
          <button
            onClick={() => {
              setArchivedFilter("true");
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              archivedFilter === "true"
                ? "bg-amber-600/30 text-amber-300 border border-amber-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
            }`}
          >
            Archived
          </button>
        </div>

        <div className="relative min-w-[260px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search projects, slugs, owners..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {/* Projects Table */}
      <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-4">Project Name & Slugs</th>
                <th className="py-3 px-4">Owner</th>
                <th className="py-3 px-4">WP / PHP Target</th>
                <th className="py-3 px-4">Generations</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-4 w-4 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
                      <span>Loading projects...</span>
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-rose-400">
                    Failed to load projects: {error.message}
                  </td>
                </tr>
              ) : projects.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No projects found matching the specified filters.
                  </td>
                </tr>
              ) : (
                projects.map((project: ProjectListItem) => (
                  <tr
                    key={project.id}
                    className="hover:bg-slate-850/50 transition-colors"
                  >
                    <td className="py-3.5 px-4">
                      <div>
                        <span className="font-semibold text-slate-100 block">
                          {project.name}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="font-mono text-[10px] text-slate-500">
                            /{project.slug}
                          </span>
                          {project.plugin_slug && (
                            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-950 border border-slate-800 text-brand-300">
                              slug: {project.plugin_slug}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <User className="h-3.5 w-3.5 text-slate-500" />
                        <span className="font-mono text-[11px]">
                          {project.user.email}
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-950/50 border border-blue-800/50 text-blue-300">
                          WP {project.wordpress_version || "6.7"}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/50 border border-purple-800/50 text-purple-300">
                          PHP {project.php_version || "8.2"}
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                        <Layers className="h-3 w-3 text-slate-400" />
                        {project.generations_count}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      {project.is_archived ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-950/40 border border-amber-800/50 px-2 py-0.5 rounded-full">
                          <Archive className="h-3 w-3" />
                          Archived
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded-full">
                          <CheckCircle2 className="h-3 w-3" />
                          Active
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-slate-500" />
                        {new Date(project.created_at).toLocaleDateString()}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {pagination && pagination.total_pages > 1 && (
          <div className="p-3.5 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing Page <strong className="text-slate-200">{pagination.current_page}</strong> of{" "}
              <strong className="text-slate-200">{pagination.total_pages}</strong> ({pagination.count} items)
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={!pagination.previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="flex items-center gap-1 px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-xs transition-colors"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </button>
              <button
                disabled={!pagination.next}
                onClick={() => setPage((p) => p + 1)}
                className="flex items-center gap-1 px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-xs transition-colors"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
