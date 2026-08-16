export interface ControlCenterAgentRunListItem {
  id: string;
  generation_id: string;
  generation_status: string;
  project_id: string;
  project_name: string;
  user_id: string;
  user_email: string;
  step_id: string;
  step_name: string;
  step_number: number;
  run_number: number;
  runtime_type: string;
  status: string;
  model_name: string;
  session_id: string;
  remote_conversation_id: string;
  prompt_preview: string;
  output_preview: string;
  token_usage: Record<string, unknown>;
  failure_category: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentRunFilters {
  page?: number;
  page_size?: number;
  status?: string;
  runtime_type?: string;
  model?: string;
  failure_category?: string;
  generation_id?: string;
  step_id?: string;
  search?: string;
}
