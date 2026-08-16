import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Lock, Mail, Shield, AlertCircle } from "lucide-react";
import { useAuth } from "./authStore";
import { Button } from "@/components/ui/Button";

export const LoginPage: React.FC = () => {
  const { isAuthenticated, isStaff, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already authenticated as staff, redirect to dashboard
  if (isAuthenticated && isStaff) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please provide both email and password.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const user = await login(email, password);
      if (user.is_staff || user.is_superuser) {
        navigate("/dashboard", { replace: true });
      } else {
        // Will be caught by route guard / AccessDenied
      }
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      setError(errObj?.message || "Invalid credentials or server unavailable.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-950 px-4 py-12">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md rounded-2xl border border-slate-800/80 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600/20 border border-brand-500/30 text-brand-400">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-100 tracking-tight">
              Tersuite Control Center
            </h1>
            <p className="text-xs text-slate-400">Operator & Staff Access</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-rose-900/50 bg-rose-950/30 p-3.5 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Operator Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="staff.operator@tersuite.com"
                className="w-full rounded-lg border border-slate-800 bg-slate-950/60 pl-10 pr-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 transition-colors font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-lg border border-slate-800 bg-slate-950/60 pl-10 pr-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 transition-colors"
              />
            </div>
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              className="w-full py-2.5 font-semibold"
              isLoading={isSubmitting}
            >
              Sign In to Control Center
            </Button>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-800/80 text-center">
          <p className="text-xs text-slate-500">
            Tersuite AI Studio · Internal Engineering Platform
          </p>
        </div>
      </div>
    </div>
  );
};
