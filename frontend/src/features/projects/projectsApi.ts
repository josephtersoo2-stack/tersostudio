import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/apiClient";

export interface ProjectUser {
  id: string;
  email: string;
}

export interface ProjectListItem {
  id: string;
  name: string;
  slug: string;
  plugin_slug: string;
  user: ProjectUser;
  description: string;
  wordpress_version: string;
  php_version: string;
  metadata: Record<string, any>;
  generations_count: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  page_size: number;
}

export interface ProjectsListResponse {
  pagination: PaginationMeta;
  results: ProjectListItem[];
}

export interface ProjectsQueryParams {
  page?: number;
  page_size?: number;
  is_archived?: string;
  search?: string;
}

export function useProjects(params?: ProjectsQueryParams) {
  const queryParams = new URLSearchParams();
  if (params?.page) {
    queryParams.set("page", params.page.toString());
  }
  if (params?.page_size) {
    queryParams.set("page_size", params.page_size.toString());
  }
  if (params?.is_archived !== undefined && params.is_archived !== "all") {
    queryParams.set("is_archived", params.is_archived);
  }
  if (params?.search) {
    queryParams.set("search", params.search);
  }

  const queryStr = queryParams.toString();
  const endpoint = queryStr ? `control-center/projects/?${queryStr}` : "control-center/projects/";

  return useQuery<ProjectsListResponse, Error>({
    queryKey: ["control-center-projects", params],
    queryFn: () => apiRequest<ProjectsListResponse>(endpoint),
    staleTime: 30000,
  });
}
