import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import { ControlCenterGenerationListItem, GenerationFilters, PaginatedResponse } from "./generationsTypes";

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
