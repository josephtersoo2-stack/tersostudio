import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import {
  ControlCenterGenerationDetail,
  ControlCenterGenerationListItem,
  ControlCenterNestedRun,
  ControlCenterStepDetail,
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

export interface CancelGenerationPayload {
  generationId: string;
  reason?: string;
}

export function useCancelGeneration() {
  const queryClient = useQueryClient();

  return useMutation<ControlCenterGenerationDetail, Error, CancelGenerationPayload>({
    mutationFn: ({ generationId, reason }) =>
      apiRequest<ControlCenterGenerationDetail>(
        `control-center/generations/${generationId}/cancel/`,
        {
          method: "POST",
          body: JSON.stringify({ reason: reason || "Cancelled by Control Center operator." }),
        }
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(
        ["control-center", "generations", "detail", data.id],
        data
      );
      queryClient.invalidateQueries({ queryKey: ["control-center", "generations"] });
      queryClient.invalidateQueries({ queryKey: ["control-center", "summary"] });
    },
  });
}

export interface RetryStepPayload {
  stepId: string;
  generationId?: string;
}

export interface RetryStepResponse {
  step: ControlCenterStepDetail;
  run: ControlCenterNestedRun;
  generation_id: string;
  generation_status: string;
}

export function useRetryStep() {
  const queryClient = useQueryClient();

  return useMutation<RetryStepResponse, Error, RetryStepPayload>({
    mutationFn: ({ stepId }) =>
      apiRequest<RetryStepResponse>(`control-center/steps/${stepId}/retry/`, {
        method: "POST",
      }),
    onSuccess: (data) => {
      if (data.generation_id) {
        queryClient.invalidateQueries({
          queryKey: ["control-center", "generations", "detail", data.generation_id],
        });
      }
      queryClient.invalidateQueries({ queryKey: ["control-center", "generations"] });
      queryClient.invalidateQueries({ queryKey: ["control-center", "runs"] });
      queryClient.invalidateQueries({ queryKey: ["control-center", "summary"] });
    },
  });
}
