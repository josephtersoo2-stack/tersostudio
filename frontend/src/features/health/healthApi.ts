import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import { ControlCenterHealthResponse } from "./healthTypes";

export function useControlCenterHealth() {
  return useQuery<ControlCenterHealthResponse, Error>({
    queryKey: ["control-center", "health"],
    queryFn: () => apiRequest<ControlCenterHealthResponse>("control-center/health/"),
    refetchInterval: 10000,
  });
}
