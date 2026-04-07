export type StatusTone = "ok" | "warn" | "bad";

export interface BuildMetadata {
  app_version: string;
  build_sha: string;
  image_tag: string;
  build_date: string;
  build_id: string;
  container_registry: string;
  environment: string;
  component_versions: Record<string, string>;
}

export interface Project {
  id: number;
  title: string;
  description: string;
  technologies: string[];
  github_url: string | null;
  demo_url: string | null;
  image_url: string | null;
  category: string;
  status: string;
  owner: string | null;
  featured: boolean;
}

export interface Service {
  id: number;
  name: string;
  service_type: string;
  description: string;
  url: string | null;
  port: number | null;
  health_endpoint: string | null;
  environment: string;
  status: string;
  owner: string | null;
  runtime_target: string;
  control_mode: string;
  control_plane: boolean;
  allowed_actions: string[];
}

export interface ServiceOverview {
  id: number;
  name: string;
  service_type: string;
  environment: string;
  status: string;
  url: string | null;
  health_endpoint: string | null;
  owner: string | null;
  healthy: boolean;
  detail: string;
}

export interface OverviewResponse {
  backend_status: string;
  database_status: string;
  frontend_status: string;
  nginx_status: string;
  project_count: number;
  service_count: number;
  healthy_service_count: number;
  featured_project_count: number;
  environment: string;
  build: BuildMetadata;
  services: ServiceOverview[];
}

export interface Incident {
  id: number;
  title: string;
  affected_service_id: number;
  severity: "low" | "medium" | "high" | "critical";
  summary: string;
  symptoms: string;
  recent_changes: string | null;
  status: "open" | "investigating" | "resolved";
  source: string | null;
  event_type: string | null;
  overview_snapshot: Record<string, unknown> | null;
  analysis: Record<string, unknown> | null;
  created_at: string;
}

export interface IncidentAnalysisResponse {
  incident_class: string;
  priority: string;
  confidence: string;
  suspected_causes: string[];
  recommended_checks: string[];
  suggested_runbook: string[];
  service_context: {
    id: number | null;
    name: string;
    service_type: string;
    environment: string;
    status: string;
    owner: string | null;
    url: string | null;
    health_endpoint: string | null;
    healthy: boolean | null;
    health_detail: string | null;
  };
  overview_snapshot: {
    backend_status: string;
    database_status: string;
    nginx_status: string;
  };
}

export interface ServiceActionResponse {
  job_id: number;
  service_id: number;
  service_name: string;
  action: string;
  status: string;
  detail: string;
}

export interface ProjectPayload {
  title: string;
  description: string;
  technologies: string[];
  category: string;
  status: string;
  owner: string | null;
  image_url: string | null;
  github_url: string | null;
  demo_url: string | null;
  featured: boolean;
}

export interface ServicePayload {
  name: string;
  service_type: string;
  description: string;
  environment: string;
  url: string | null;
  health_endpoint: string | null;
  port: number | null;
  status: string;
  owner: string | null;
}

export interface IncidentPayload {
  title: string;
  affected_service_id: number;
  severity: Incident["severity"];
  summary: string;
  symptoms: string;
  recent_changes: string | null;
  status: Incident["status"];
}

export interface IncidentAnalysisPayload {
  incident_id: number | null;
  affected_service_id: number;
  severity: Incident["severity"];
  summary: string;
  symptoms: string;
  recent_changes: string | null;
}
