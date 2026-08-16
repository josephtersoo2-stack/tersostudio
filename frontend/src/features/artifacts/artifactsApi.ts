import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import { PaginatedResponse } from "@/features/generations/generationsTypes";
import { ArtifactFilters, ControlCenterArtifactListItem } from "./artifactsTypes";

export function useControlCenterArtifacts(filters: ArtifactFilters = {}) {
  return useQuery<PaginatedResponse<ControlCenterArtifactListItem>, Error>({
    queryKey: ["control-center", "artifacts", filters],
    queryFn: () =>
      apiRequest<PaginatedResponse<ControlCenterArtifactListItem>>(
        "control-center/artifacts/",
        {
          params: filters as Record<string, string | number | boolean | null | undefined>,
        }
      ),
    refetchInterval: 10000,
  });
}
