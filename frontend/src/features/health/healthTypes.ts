export interface ServiceStatus {
  status: "healthy" | "unhealthy" | "degraded" | "unreachable" | "simulated";
  latency_ms?: number;
  engine?: string;
  transport?: string;
  server_url?: string;
  status_code?: number;
  error?: string;
  note?: string;
}

export interface RuntimeConfig {
  backend: string;
  openrouter_configured: boolean;
  openhands_api_key_configured: boolean;
}

export interface ControlCenterHealthResponse {
  status: "ready" | "degraded" | "unhealthy";
  services: {
    database: ServiceStatus;
    redis: ServiceStatus;
    celery_broker: ServiceStatus;
    openhands: ServiceStatus;
  };
  runtime: RuntimeConfig;
}
