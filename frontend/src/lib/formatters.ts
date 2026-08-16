/**
 * Formatting utilities for dates, durations, token counts, file sizes, and previews.
 */

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date);
  } catch {
    return dateString;
  }
}

export function formatDuration(
  startStr: string | null | undefined,
  endStr: string | null | undefined
): string {
  if (!startStr) return "—";
  const start = new Date(startStr).getTime();
  const end = endStr ? new Date(endStr).getTime() : Date.now();
  if (isNaN(start) || isNaN(end)) return "—";

  const diffMs = Math.max(0, end - start);
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}s`;
  const minutes = Math.floor(diffSec / 60);
  const seconds = diffSec % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return `${hours}h ${remMinutes}m`;
}

export function formatTokens(tokenUsage: Record<string, unknown> | null | undefined): string {
  if (!tokenUsage) return "0";

  // Check direct keys
  if (typeof tokenUsage.prompt_tokens === "number" || typeof tokenUsage.completion_tokens === "number") {
    const prompt = (tokenUsage.prompt_tokens as number) || 0;
    const completion = (tokenUsage.completion_tokens as number) || 0;
    return `${prompt + completion} (${prompt} in / ${completion} out)`;
  }

  // Check OpenHands accumulated metrics format
  const metrics = tokenUsage.usage_to_metrics as Record<string, unknown> | undefined;
  if (metrics && typeof metrics === "object") {
    for (const key of Object.keys(metrics)) {
      const metricObj = metrics[key] as Record<string, unknown> | undefined;
      const accUsage = metricObj?.accumulated_token_usage as Record<string, unknown> | undefined;
      if (accUsage) {
        const prompt = (accUsage.prompt_tokens as number) || 0;
        const completion = (accUsage.completion_tokens as number) || 0;
        return `${prompt + completion} (${prompt} in / ${completion} out)`;
      }
    }
  }

  return "—";
}

export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return "0 B";
  if (bytes === 0) return "0 B";

  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i] || "B"}`;
}
