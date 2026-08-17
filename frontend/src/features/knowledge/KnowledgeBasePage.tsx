import React, { useState } from "react";
import {
  BookOpen,
  Search,
  ShieldCheck,
  AlertTriangle,
  Code2,
  X,
  Sparkles,
  Layers,
  FileCode,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
} from "lucide-react";
import {
  useKnowledgeUnits,
  useKnowledgeUnitDetail,
  KnowledgeUnitListItem,
} from "./knowledgeApi";

const CATEGORIES = [
  { id: "ALL", label: "All Standards", icon: Layers },
  { id: "SECURITY", label: "Security & CSRF", icon: ShieldCheck },
  { id: "DATABASE", label: "Database & dbDelta", icon: FileCode },
  { id: "REST_API", label: "REST API", icon: Code2 },
  { id: "WOOCOMMERCE", label: "WooCommerce & HPOS", icon: Sparkles },
  { id: "DOMAIN_PATTERNS", label: "Domain Patterns", icon: BookOpen },
];

function getCategoryColor(category: string): { bg: string; text: string; border: string } {
  switch (category) {
    case "SECURITY":
      return { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-rose-500/30" };
    case "DATABASE":
      return { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/30" };
    case "REST_API":
      return { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30" };
    case "WOOCOMMERCE":
      return { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" };
    case "DOMAIN_PATTERNS":
      return { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30" };
    default:
      return { bg: "bg-slate-500/10", text: "text-slate-400", border: "border-slate-500/30" };
  }
}

export const KnowledgeBasePage: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeUnitId, setActiveUnitId] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const { data: units, isLoading, error } = useKnowledgeUnits({
    category: selectedCategory,
    search: searchQuery,
  });

  const { data: activeUnit, isLoading: isDetailLoading } = useKnowledgeUnitDetail(activeUnitId);

  const handleCopyCode = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-brand-400" />
            WordPress Engineering Knowledge Base
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Structured architectural guidelines, security rules, and code patterns injected into specialist agent prompts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            {units?.length ?? 0} Units Loaded
          </span>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-400">
            Engine v1.0 Active
          </span>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
        <div className="flex flex-wrap items-center gap-1.5">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const isActive = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? "bg-brand-600/30 text-brand-300 border border-brand-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {cat.label}
              </button>
            );
          })}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search rules, keywords, IDs..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {/* Grid of Knowledge Units */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-48 bg-slate-900/40 border border-slate-800/60 rounded-xl animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div className="p-8 text-center text-xs text-rose-400 bg-rose-950/20 border border-rose-900/40 rounded-xl">
          Failed to load knowledge units: {error.message}
        </div>
      ) : units && units.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {units.map((unit: KnowledgeUnitListItem) => {
            const color = getCategoryColor(unit.category);
            return (
              <div
                key={unit.id}
                onClick={() => setActiveUnitId(unit.id)}
                className="bg-slate-900/50 hover:bg-slate-900/80 border border-slate-800/80 hover:border-slate-700/80 rounded-xl p-4 flex flex-col justify-between cursor-pointer transition-all hover:shadow-lg group"
              >
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${color.bg} ${color.text} ${color.border}`}
                    >
                      {unit.category}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 group-hover:text-slate-400">
                      {unit.id}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-slate-100 group-hover:text-brand-300 transition-colors line-clamp-2">
                    {unit.title}
                  </h3>

                  <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                    {unit.description}
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 text-emerald-400">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      {unit.rules_count} Rules
                    </span>
                    <span className="flex items-center gap-1 text-rose-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      {unit.anti_patterns_count} Prohibitions
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400">
                    Conf {Math.round(unit.confidence * 100)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-12 text-center bg-slate-900/30 border border-slate-800/60 rounded-xl text-slate-500 text-xs">
          No knowledge units match your category and search criteria.
        </div>
      )}

      {/* Slide-over Detail Modal */}
      {activeUnitId && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm transition-opacity">
          <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex items-start justify-between sticky top-0 bg-slate-900/95 backdrop-blur z-10">
              <div className="space-y-1.5 pr-4">
                <div className="flex items-center gap-2">
                  {activeUnit && (
                    <span
                      className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                        getCategoryColor(activeUnit.category).bg
                      } ${getCategoryColor(activeUnit.category).text} ${
                        getCategoryColor(activeUnit.category).border
                      }`}
                    >
                      {activeUnit.category}
                    </span>
                  )}
                  <span className="text-xs font-mono text-slate-400">
                    {activeUnitId}
                  </span>
                </div>
                <h2 className="text-base font-bold text-slate-100">
                  {activeUnit?.title || "Loading Unit..."}
                </h2>
              </div>
              <button
                onClick={() => setActiveUnitId(null)}
                className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 flex-1">
              {isDetailLoading || !activeUnit ? (
                <div className="space-y-4 animate-pulse">
                  <div className="h-20 bg-slate-800/40 rounded-lg" />
                  <div className="h-32 bg-slate-800/40 rounded-lg" />
                  <div className="h-48 bg-slate-800/40 rounded-lg" />
                </div>
              ) : (
                <>
                  {/* Description */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                      Architectural Overview
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded-lg border border-slate-800/80">
                      {activeUnit.description}
                    </p>
                  </div>

                  {/* Compatibility */}
                  {activeUnit.compatibility && Object.keys(activeUnit.compatibility).length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Environment Compatibility
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(activeUnit.compatibility).map(([k, v]) => (
                          <span
                            key={k}
                            className="text-xs font-mono px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-brand-300"
                          >
                            <strong className="text-slate-400">{k}:</strong> {String(v)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Mandatory Rules */}
                  {activeUnit.rules && activeUnit.rules.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-2.5 flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4" />
                        Mandatory Engineering Rules
                      </h4>
                      <div className="space-y-2">
                        {activeUnit.rules.map((rule, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-2.5 text-xs text-slate-200 bg-emerald-950/20 border border-emerald-900/40 p-3 rounded-lg leading-relaxed"
                          >
                            <span className="text-emerald-400 font-bold shrink-0">✓</span>
                            <span>{rule}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Forbidden Anti-Patterns */}
                  {activeUnit.anti_patterns && activeUnit.anti_patterns.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-400 mb-2.5 flex items-center gap-1.5">
                        <XCircle className="h-4 w-4" />
                        Forbidden Anti-Patterns
                      </h4>
                      <div className="space-y-2">
                        {activeUnit.anti_patterns.map((anti, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-2.5 text-xs text-slate-300 bg-rose-950/20 border border-rose-900/40 p-3 rounded-lg leading-relaxed"
                          >
                            <span className="text-rose-400 font-bold shrink-0">✗</span>
                            <span>{anti}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Implementation Patterns */}
                  {activeUnit.patterns && activeUnit.patterns.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2.5 flex items-center gap-1.5">
                        <Code2 className="h-4 w-4" />
                        Approved Implementation Patterns
                      </h4>
                      <div className="space-y-4">
                        {activeUnit.patterns.map((pat, idx) => (
                          <div
                            key={idx}
                            className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden"
                          >
                            <div className="p-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
                              <div>
                                <span className="text-xs font-semibold text-slate-200">
                                  {pat.name}
                                </span>
                                {pat.hook && (
                                  <span className="ml-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">
                                    Hook: {pat.hook}
                                  </span>
                                )}
                              </div>
                              {pat.code && (
                                <button
                                  onClick={() => handleCopyCode(pat.code || "", idx)}
                                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded transition-colors"
                                >
                                  {copiedIndex === idx ? (
                                    <>
                                      <Check className="h-3 w-3 text-emerald-400" />
                                      <span className="text-emerald-400">Copied</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="h-3 w-3" />
                                      <span>Copy</span>
                                    </>
                                  )}
                                </button>
                              )}
                            </div>
                            {pat.description && (
                              <p className="px-3 pt-2 text-[11px] text-slate-400 italic">
                                {pat.description}
                              </p>
                            )}
                            {pat.code && (
                              <pre className="p-3 text-[11px] font-mono text-slate-300 overflow-x-auto leading-relaxed bg-slate-950/80">
                                <code>{pat.code}</code>
                              </pre>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
