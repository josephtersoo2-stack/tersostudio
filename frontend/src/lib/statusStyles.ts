/**
 * Consistent Tailwind color classes and badge styles for generation & agent run statuses.
 */

export interface StatusStyle {
  bg: string;
  text: string;
  border: string;
  dot: string;
}

export const GENERATION_STATUS_STYLES: Record<string, StatusStyle> = {
  DRAFT: {
    bg: "bg-slate-800/60",
    text: "text-slate-300",
    border: "border-slate-700",
    dot: "bg-slate-400",
  },
  SPECIFICATION: {
    bg: "bg-blue-950/60",
    text: "text-blue-300",
    border: "border-blue-800/60",
    dot: "bg-blue-400",
  },
  APPROVED: {
    bg: "bg-cyan-950/60",
    text: "text-cyan-300",
    border: "border-cyan-800/60",
    dot: "bg-cyan-400",
  },
  PLANNING: {
    bg: "bg-purple-950/60",
    text: "text-purple-300",
    border: "border-purple-800/60",
    dot: "bg-purple-400",
  },
  BUILDING: {
    bg: "bg-amber-950/60",
    text: "text-amber-300",
    border: "border-amber-700/60",
    dot: "bg-amber-400 animate-pulse",
  },
  TESTING: {
    bg: "bg-indigo-950/60",
    text: "text-indigo-300",
    border: "border-indigo-800/60",
    dot: "bg-indigo-400 animate-pulse",
  },
  REVIEW: {
    bg: "bg-sky-950/60",
    text: "text-sky-300",
    border: "border-sky-800/60",
    dot: "bg-sky-400",
  },
  PACKAGING: {
    bg: "bg-teal-950/60",
    text: "text-teal-300",
    border: "border-teal-800/60",
    dot: "bg-teal-400",
  },
  COMPLETED: {
    bg: "bg-emerald-950/60",
    text: "text-emerald-300",
    border: "border-emerald-800/60",
    dot: "bg-emerald-400",
  },
  FAILED: {
    bg: "bg-rose-950/60",
    text: "text-rose-300",
    border: "border-rose-800/60",
    dot: "bg-rose-400",
  },
  CANCELLED: {
    bg: "bg-zinc-800/60",
    text: "text-zinc-400",
    border: "border-zinc-700",
    dot: "bg-zinc-500",
  },
  PAUSED: {
    bg: "bg-yellow-950/60",
    text: "text-yellow-300",
    border: "border-yellow-800/60",
    dot: "bg-yellow-400",
  },
  RETRYING: {
    bg: "bg-orange-950/60",
    text: "text-orange-300",
    border: "border-orange-800/60",
    dot: "bg-orange-400 animate-pulse",
  },
};

export const RUN_STATUS_STYLES: Record<string, StatusStyle> = {
  QUEUED: {
    bg: "bg-slate-800/60",
    text: "text-slate-300",
    border: "border-slate-700",
    dot: "bg-slate-400",
  },
  RUNNING: {
    bg: "bg-amber-950/60",
    text: "text-amber-300",
    border: "border-amber-700/60",
    dot: "bg-amber-400 animate-pulse",
  },
  COMPLETED: {
    bg: "bg-emerald-950/60",
    text: "text-emerald-300",
    border: "border-emerald-800/60",
    dot: "bg-emerald-400",
  },
  FAILED: {
    bg: "bg-rose-950/60",
    text: "text-rose-300",
    border: "border-rose-800/60",
    dot: "bg-rose-400",
  },
  CANCELLED: {
    bg: "bg-zinc-800/60",
    text: "text-zinc-400",
    border: "border-zinc-700",
    dot: "bg-zinc-500",
  },
  TIMED_OUT: {
    bg: "bg-red-950/60",
    text: "text-red-300",
    border: "border-red-800/60",
    dot: "bg-red-400",
  },
};

export function getStatusStyle(status: string | undefined): StatusStyle {
  if (!status) {
    return {
      bg: "bg-slate-800/60",
      text: "text-slate-400",
      border: "border-slate-700",
      dot: "bg-slate-500",
    };
  }
  const key = status.toUpperCase();
  return (
    GENERATION_STATUS_STYLES[key] ||
    RUN_STATUS_STYLES[key] || {
      bg: "bg-slate-800/60",
      text: "text-slate-300",
      border: "border-slate-700",
      dot: "bg-slate-400",
    }
  );
}
