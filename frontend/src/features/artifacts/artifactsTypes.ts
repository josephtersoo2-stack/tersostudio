export interface ControlCenterArtifactListItem {
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

export interface ArtifactFilters {
  page?: number;
  page_size?: number;
  generation_id?: string;
  artifact_type?: string;
  search?: string;
}
