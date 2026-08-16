import React from "react";
import { ShieldAlert, LogOut } from "lucide-react";
import { useAuth } from "./authStore";
import { Button } from "@/components/ui/Button";

export const AccessDeniedPage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-md rounded-2xl border border-rose-900/40 bg-slate-900/70 p-8 text-center shadow-2xl backdrop-blur-xl">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-950/60 border border-rose-800/60 text-rose-400 mb-6">
          <ShieldAlert className="h-7 w-7" />
        </div>

        <h1 className="text-xl font-bold text-slate-100">Staff Access Required</h1>
        <p className="mt-2 text-sm text-slate-400 leading-relaxed">
          The Tersuite Control Center is restricted to authorized operations staff.
          Your account (<span className="text-slate-200 font-mono text-xs">{user?.email}</span>) does
          not have staff privileges.
        </p>

        <div className="mt-8 flex flex-col gap-3">
          <Button
            variant="secondary"
            onClick={() => logout()}
            leftIcon={<LogOut className="h-4 w-4" />}
          >
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
};
