import React from "react";

interface LoadingStateProps {
  message?: string;
  rows?: number;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading data...",
  rows = 5,
  className = "",
}) => {
  return (
    <div className={`space-y-4 p-6 ${className}`}>
      <div className="flex items-center gap-3 text-sm text-slate-400">
        <svg
          className="animate-spin h-4 w-4 text-brand-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <span>{message}</span>
      </div>

      <div className="space-y-2.5">
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="h-12 w-full rounded-lg bg-slate-900/60 border border-slate-800/60 animate-pulse"
          />
        ))}
      </div>
    </div>
  );
};
