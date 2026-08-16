import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import { PaginatedResponse } from "@/features/generations/generationsTypes";
import {
  AgentRunFilters,
  ControlCenterAgentRunDetail,
  ControlCenterAgentRunListItem,
} from "./agentRunsTypes";

export function useControlCenterAgentRuns(filters: AgentRunFilters = {}) {
  return useQuery<PaginatedResponse<ControlCenterAgentRunListItem>, Error>({
    queryKey: ["control-center", "runs", filters],
    queryFn: () =>
      apiRequest<PaginatedResponse<ControlCenterAgentRunListItem>>(
        "control-center/runs/",
        {
          params: filters as Record<string, string | number | boolean | null | undefined>,
        }
      ),
    refetchInterval: 10000,
  });
}

export function useControlCenterAgentRunDetail(runId: string | undefined) {
  return useQuery<ControlCenterAgentRunDetail, Error>({
    queryKey: ["control-center", "runs", "detail", runId],
    queryFn: () => apiRequest<ControlCenterAgentRunDetail>(`control-center/runs/${runId}/`),
    enabled: Boolean(runId),
    refetchInterval: 8000,
  });
}
