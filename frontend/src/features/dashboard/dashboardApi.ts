import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";
import { ControlCenterSummary } from "./dashboardTypes";

export function useControlCenterSummary() {
  return useQuery<ControlCenterSummary, Error>({
    queryKey: ["control-center", "summary"],
    queryFn: () => apiRequest<ControlCenterSummary>("control-center/summary/"),
    refetchInterval: 10000, // Live poll every 10 seconds for real-time operations
  });
}
