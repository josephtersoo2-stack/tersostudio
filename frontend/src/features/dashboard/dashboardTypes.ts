export interface ProjectMetrics {
  total: number;
  active: number;
  archived: number;
}

export interface GenerationMetrics {
  total: number;
  active: number;
  draft: number;
  specification: number;
  approved: number;
  planning: number;
  building: number;
  testing: number;
  review: number;
  packaging: number;
  completed: number;
  failed: number;
  cancelled: number;
  paused: number;
  retrying: number;
}

export interface AgentRunMetrics {
  total: number;
  queued: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  timed_out: number;
}

export interface StepMetrics {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  skipped: number;
}

export interface ArtifactMetrics {
  total: number;
  source_code: number;
  configuration: number;
  test_report: number;
  documentation: number;
  zip_archive: number;
  security_report: number;
  other: number;
}

export interface RuntimeMetrics {
  default_backend: string;
  openhands_server_url: string;
  openrouter_configured: boolean;
  openhands_api_key_configured: boolean;
}

export interface KnowledgeMetrics {
  total: number;
  categories: Record<string, number>;
}

export interface ControlCenterSummary {
  projects: ProjectMetrics;
  generations: GenerationMetrics;
  agent_runs: AgentRunMetrics;
  steps: StepMetrics;
  artifacts: ArtifactMetrics;
  runtime: RuntimeMetrics;
  knowledge_units?: KnowledgeMetrics;
}
