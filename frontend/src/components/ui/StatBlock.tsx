import React from "react";

interface StatBlockProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: "default" | "brand" | "success" | "warning" | "error";
  className?: string;
}

export const StatBlock: React.FC<StatBlockProps> = ({
  title,
  value,
  subtitle,
  icon,
  variant = "default",
  className = "",
}) => {
  const variantStyles = {
    default: "border-slate-800 bg-slate-900/50 text-slate-100",
    brand: "border-brand-800/40 bg-brand-950/20 text-brand-100",
    success: "border-emerald-800/40 bg-emerald-950/20 text-emerald-100",
    warning: "border-amber-800/40 bg-amber-950/20 text-amber-100",
    error: "border-rose-800/40 bg-rose-950/20 text-rose-100",
  };

  const iconColors = {
    default: "text-slate-400 bg-slate-800/80",
    brand: "text-brand-400 bg-brand-900/40",
    success: "text-emerald-400 bg-emerald-900/40",
    warning: "text-amber-400 bg-amber-900/40",
    error: "text-rose-400 bg-rose-900/40",
  };

  return (
    <div
      className={`p-5 rounded-xl border ${variantStyles[variant]} backdrop-blur-sm relative overflow-hidden flex flex-col justify-between ${className}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            {title}
          </p>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight">
            {value}
          </div>
        </div>
        {icon && (
          <div className={`p-2.5 rounded-lg ${iconColors[variant]}`}>
            {icon}
          </div>
        )}
      </div>
      {subtitle && (
        <p className="mt-3 text-xs text-slate-400/90 flex items-center gap-1.5">
          {subtitle}
        </p>
      )}
    </div>
  );
};
