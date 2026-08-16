export interface PaginationMetadata {
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  page_size: number;
}

export interface PaginatedResponse<T> {
  pagination: PaginationMetadata;
  results: T[];
}

export interface ControlCenterGenerationListItem {
  id: string;
  project_id: string;
  project_name: string;
  user_id: string;
  user_email: string;
  prompt_preview: string;
  status: string;
  current_step_number: number;
  total_steps: number;
  steps_count: number;
  runs_count: number;
  artifacts_count: number;
  workspace_id: string | null;
  failure_category: string;
  error_message_preview: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  paused_at: string | null;
}

export interface GenerationFilters {
  page?: number;
  page_size?: number;
  status?: string;
  project_id?: string;
  user_id?: string;
  search?: string;
}
