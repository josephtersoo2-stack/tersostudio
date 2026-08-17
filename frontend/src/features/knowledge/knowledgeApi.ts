import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";

export interface KnowledgeUnitListItem {
  id: string;
  title: string;
  category: string;
  domain: string;
  description: string;
  rules_count: number;
  anti_patterns_count: number;
  patterns_count: number;
  compatibility: Record<string, string>;
  confidence: number;
}

export interface KnowledgePattern {
  name: string;
  description?: string;
  hook?: string;
  code?: string;
}

export interface KnowledgeUnitDetail {
  id: string;
  title: string;
  category: string;
  domain: string;
  description: string;
  rules: string[];
  patterns: KnowledgePattern[];
  anti_patterns: string[];
  compatibility: Record<string, string>;
  confidence: number;
}

export interface KnowledgeQueryParams {
  category?: string;
  domain?: string;
  search?: string;
  min_confidence?: number;
}

export function useKnowledgeUnits(params?: KnowledgeQueryParams) {
  const queryParams = new URLSearchParams();
  if (params?.category && params.category !== "ALL") {
    queryParams.set("category", params.category);
  }
  if (params?.domain) {
    queryParams.set("domain", params.domain);
  }
  if (params?.search) {
    queryParams.set("search", params.search);
  }
  if (params?.min_confidence !== undefined) {
    queryParams.set("min_confidence", params.min_confidence.toString());
  }

  const queryStr = queryParams.toString();
  const endpoint = queryStr ? `control-center/knowledge/?${queryStr}` : "control-center/knowledge/";

  return useQuery<KnowledgeUnitListItem[], Error>({
    queryKey: ["knowledge-units", params],
    queryFn: () => apiRequest<KnowledgeUnitListItem[]>(endpoint),
    staleTime: 60000,
  });
}

export function useKnowledgeUnitDetail(unitId: string | null) {
  return useQuery<KnowledgeUnitDetail, Error>({
    queryKey: ["knowledge-unit-detail", unitId],
    queryFn: () => apiRequest<KnowledgeUnitDetail>(`control-center/knowledge/${unitId}/`),
    enabled: Boolean(unitId),
    staleTime: 60000,
  });
}
