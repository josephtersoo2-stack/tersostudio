import React from "react";
import { getStatusStyle } from "@/lib/statusStyles";

interface BadgeProps {
  status?: string;
  label?: string;
  variant?: "default" | "status" | "success" | "warning" | "error" | "info";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  status,
  label,
  variant = "status",
  className = "",
}) => {
  const displayLabel = label || status || "—";

  if (variant === "status" && status) {
    const style = getStatusStyle(status);
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${style.bg} ${style.text} ${style.border} ${className}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
        {displayLabel}
      </span>
    );
  }

  const variantStyles = {
    default: "bg-slate-800 text-slate-300 border-slate-700",
    status: "bg-slate-800 text-slate-300 border-slate-700",
    success: "bg-emerald-950/60 text-emerald-300 border-emerald-800/60",
    warning: "bg-amber-950/60 text-amber-300 border-amber-700/60",
    error: "bg-rose-950/60 text-rose-300 border-rose-800/60",
    info: "bg-blue-950/60 text-blue-300 border-blue-800/60",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${variantStyles[variant]} ${className}`}
    >
      {displayLabel}
    </span>
  );
};
