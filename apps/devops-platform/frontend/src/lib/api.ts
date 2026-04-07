import type {
  Incident,
  IncidentAnalysisPayload,
  IncidentAnalysisResponse,
  IncidentPayload,
  OverviewResponse,
  Project,
  ProjectPayload,
  Service,
  ServiceActionResponse,
  ServicePayload,
} from "../types";

interface RequestOptions extends RequestInit {
  body?: unknown;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  const body =
    options.body === undefined || options.body === null
      ? undefined
      : JSON.stringify(options.body);

  if (body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    headers,
    body,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? JSON.stringify(payload);
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail || "Request failed");
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}

export const api = {
  getHealth: () => request<{ status: string }>("/api/health"),
  getOverview: () => request<OverviewResponse>("/api/overview"),
  getProjects: () => request<Project[]>("/api/portfolio/projects"),
  getProject: (id: number) => request<Project>(`/api/portfolio/projects/${id}`),
  createProject: (payload: ProjectPayload) =>
    request<Project>("/api/portfolio/projects", { method: "POST", body: payload }),
  updateProject: (id: number, payload: ProjectPayload) =>
    request<Project>(`/api/portfolio/projects/${id}`, { method: "PUT", body: payload }),
  deleteProject: (id: number) =>
    request<null>(`/api/portfolio/projects/${id}`, { method: "DELETE" }),
  getServices: () => request<Service[]>("/api/services"),
  getService: (id: number) => request<Service>(`/api/services/${id}`),
  createService: (payload: ServicePayload) =>
    request<Service>("/api/services", { method: "POST", body: payload }),
  updateService: (id: number, payload: ServicePayload) =>
    request<Service>(`/api/services/${id}`, { method: "PUT", body: payload }),
  deleteService: (id: number) => request<null>(`/api/services/${id}`, { method: "DELETE" }),
  queueServiceAction: (id: number, action: "restart" | "start" | "stop") =>
    request<ServiceActionResponse>(`/api/services/${id}/actions`, {
      method: "POST",
      body: { action },
    }),
  getIncidents: () => request<Incident[]>("/api/incidents"),
  getIncident: (id: number) => request<Incident>(`/api/incidents/${id}`),
  createIncident: (payload: IncidentPayload) =>
    request<Incident>("/api/incidents", { method: "POST", body: payload }),
  updateIncident: (id: number, payload: IncidentPayload) =>
    request<Incident>(`/api/incidents/${id}`, { method: "PUT", body: payload }),
  deleteIncident: (id: number) =>
    request<null>(`/api/incidents/${id}`, { method: "DELETE" }),
  analyzeIncident: (payload: IncidentAnalysisPayload) =>
    request<IncidentAnalysisResponse>("/api/ai/incidents/analyze", {
      method: "POST",
      body: payload,
    }),
};
