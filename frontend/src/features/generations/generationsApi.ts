import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import {
  ControlCenterGenerationDetail,
  ControlCenterGenerationListItem,
  GenerationFilters,
  PaginatedResponse,
} from "./generationsTypes";

export function useControlCenterGenerations(filters: GenerationFilters = {}) {
  return useQuery<PaginatedResponse<ControlCenterGenerationListItem>, Error>({
    queryKey: ["control-center", "generations", filters],
    queryFn: () =>
      apiRequest<PaginatedResponse<ControlCenterGenerationListItem>>(
        "control-center/generations/",
        {
          params: filters as Record<string, string | number | boolean | null | undefined>,
        }
      ),
    refetchInterval: 10000,
  });
}

export function useControlCenterGenerationDetail(generationId: string | undefined) {
  return useQuery<ControlCenterGenerationDetail, Error>({
    queryKey: ["control-center", "generations", "detail", generationId],
    queryFn: () =>
      apiRequest<ControlCenterGenerationDetail>(`control-center/generations/${generationId}/`),
    enabled: Boolean(generationId),
    refetchInterval: 8000, // Live poll generation detail every 8s
  });
}
