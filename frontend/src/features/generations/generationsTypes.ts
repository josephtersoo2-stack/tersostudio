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

// CC-02 Detail Interfaces

export interface GenerationTimestamps {
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  paused_at: string | null;
}

export interface ControlCenterNestedRun {
  id: string;
  run_number: number;
  runtime_type: string;
  status: string;
  model_name: string;
  session_id: string;
  remote_conversation_id: string;
  failure_category: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ControlCenterStepDetail {
  id: string;
  step_number: number;
  name: string;
  agent_role: string;
  status: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  runs: ControlCenterNestedRun[];
}

export interface ControlCenterWorkspaceDetail {
  id: string;
  workspace_path: string;
  storage_type: string;
  is_active: boolean;
  disk_usage_bytes: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ControlCenterArtifactSummary {
  id: string;
  generation_id: string;
  project_name: string;
  agent_run_id: string | null;
  name: string;
  file_path: string;
  artifact_type: string;
  mime_type: string;
  size_bytes: number;
  checksum_sha256: string;
  storage_backend: string;
  storage_key: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ControlCenterGenerationDetail {
  id: string;
  project: {
    id: string;
    name: string;
  };
  user: {
    id: string;
    email: string;
  };
  prompt: string;
  status: string;
  current_step_number: number;
  total_steps: number;
  metadata: Record<string, unknown>;
  failure_category: string;
  error_message: string;
  timestamps: GenerationTimestamps;
  steps: ControlCenterStepDetail[];
  workspace: ControlCenterWorkspaceDetail | null;
  artifacts: ControlCenterArtifactSummary[];
}
