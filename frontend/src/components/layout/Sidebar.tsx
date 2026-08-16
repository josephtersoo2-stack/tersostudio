import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Cpu,
  Layers,
  FolderGit2,
  Package,
  Activity,
  ShieldCheck,
  Terminal,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
}

const navItems: NavItem[] = [
  { name: "Overview Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Generations", href: "/generations", icon: Layers },
  { name: "Agent Runs", href: "/agent-runs", icon: Cpu },
  { name: "Runtime Health", href: "/runtime-health", icon: Activity },
  { name: "Artifacts", href: "/artifacts", icon: Package },
  { name: "Projects", href: "/projects", icon: FolderGit2, disabled: true },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 shrink-0 bg-slate-950/90 border-r border-slate-800/80 flex flex-col h-screen select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800/80">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600/20 border border-brand-500/30 text-brand-400">
          <Terminal className="h-5 w-5" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-100 tracking-tight flex items-center gap-1.5">
            Tersuite Studio
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-brand-950 border border-brand-800/60 text-brand-300">
              CC-02
            </span>
          </div>
          <p className="text-[11px] text-slate-400">Control Center</p>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Operations
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          if (item.disabled) {
            return (
              <div
                key={item.name}
                className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-slate-600 cursor-not-allowed group"
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </div>
                <span className="text-[9px] uppercase tracking-wider bg-slate-900 border border-slate-800/80 px-1.5 py-0.5 rounded text-slate-500 font-mono">
                  Soon
                </span>
              </div>
            );
          }

          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-brand-600/20 text-brand-300 border border-brand-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Footer info */}
      <div className="p-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-emerald-400">
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>Staff Guard Active</span>
        </div>
        <span className="font-mono text-[10px] text-slate-600">v1.42</span>
      </div>
    </aside>
  );
};
