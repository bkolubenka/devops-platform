import type { Incident, OverviewResponse, StatusTone } from "../types";

export function getStatusTone(value: string): StatusTone {
  if (value === "ok" || value === "running" || value === "healthy") {
    return "ok";
  }
  if (value === "warning" || value === "planned" || value === "investigating" || value === "medium") {
    return "warn";
  }
  return "bad";
}

export function inferEnvironmentLabel(apiEnvironment: string): string {
  const hostname = window.location.hostname;
  if (hostname === "local.kydyrov.dev") {
    return "development";
  }
  if (hostname === "kydyrov.dev" || hostname === "www.kydyrov.dev") {
    return "production";
  }
  return apiEnvironment || "unknown";
}

export function getEnvironmentLink(environmentName: string) {
  if (environmentName === "development") {
    return { label: "dev", href: "https://local.kydyrov.dev/" };
  }
  if (environmentName === "production") {
    return { label: "prod", href: "https://kydyrov.dev/" };
  }
  return { label: environmentName || "unknown", href: "/" };
}

export function isPlatformOnline(data: OverviewResponse) {
  return [data.backend_status, data.database_status, data.frontend_status, data.nginx_status].every(
    (value) => value === "ok",
  );
}

export function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "unknown";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function parseTechnologies(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function emptyToNull(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function summarizeEnvironmentState(overview: OverviewResponse, environmentLabel: string) {
  const platformOnline = isPlatformOnline(overview);
  return {
    production: environmentLabel === "production" ? platformOnline : false,
    development: environmentLabel === "development" ? platformOnline : false,
  };
}

export function pickRecentIncidents(incidents: Incident[], count = 5) {
  return incidents.slice(0, count);
}
