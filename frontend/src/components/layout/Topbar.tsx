import React from "react";
import { LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "@/features/auth/authStore";
import { Button } from "@/components/ui/Button";

export const Topbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 shrink-0 bg-slate-950/60 border-b border-slate-800/80 px-6 flex items-center justify-between backdrop-blur-md sticky top-0 z-20">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span>Tersuite AI Studio Environment:</span>
        <span className="font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-200">
          Internal Production
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* User Card */}
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
          <div className="w-6 h-6 rounded-md bg-brand-900/40 border border-brand-700/50 flex items-center justify-center text-brand-300">
            <UserIcon className="w-3.5 h-3.5" />
          </div>
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200 leading-none">
              {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : user?.email}
            </div>
            <div className="text-[10px] font-mono text-brand-400 leading-none mt-1">
              {user?.is_superuser ? "Superuser Operator" : "Staff Operator"}
            </div>
          </div>
        </div>

        {/* Logout */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => logout()}
          className="text-slate-400 hover:text-rose-300"
          title="Sign out of Control Center"
        >
          <LogOut className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
};
