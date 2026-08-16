import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Failed to load data",
  message = "An error occurred while fetching information from the server.",
  onRetry,
  className = "",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-12 text-center rounded-xl border border-rose-900/40 bg-rose-950/10 ${className}`}
    >
      <div className="p-3 rounded-full bg-rose-900/30 text-rose-400 mb-4 border border-rose-800/40">
        <AlertCircle className="w-8 h-8 stroke-[1.5]" />
      </div>
      <h3 className="text-base font-semibold text-rose-200">{title}</h3>
      <p className="mt-1.5 text-sm text-slate-400 max-w-md">{message}</p>
      {onRetry && (
        <div className="mt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={onRetry}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Try Again
          </Button>
        </div>
      )}
    </div>
  );
};
