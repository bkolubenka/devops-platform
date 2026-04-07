import { startTransition, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { BuildFooter } from "../components/BuildFooter";
import { SharedNav } from "../components/SharedNav";
import { api } from "../lib/api";
import {
  emptyToNull,
  formatTimestamp,
  getEnvironmentLink,
  getStatusTone,
  inferEnvironmentLabel,
  parseTechnologies,
  pickRecentIncidents,
  summarizeEnvironmentState,
} from "../lib/utils";
import type {
  BuildMetadata,
  Incident,
  IncidentAnalysisResponse,
  IncidentPayload,
  OverviewResponse,
  Project,
  ProjectPayload,
  Service,
  ServicePayload,
} from "../types";

type SectionId = "home" | "portfolio" | "services" | "incidents" | "ai" | "observability";

const validSections: SectionId[] = [
  "home",
  "portfolio",
  "services",
  "incidents",
  "ai",
  "observability",
];

interface ProjectFormState {
  title: string;
  description: string;
  technologies: string;
  category: string;
  status: string;
  owner: string;
  image_url: string;
  github_url: string;
  demo_url: string;
  featured: boolean;
}

interface ServiceFormState {
  name: string;
  service_type: string;
  description: string;
  environment: string;
  url: string;
  health_endpoint: string;
  port: string;
  status: string;
  owner: string;
}

interface IncidentFormState {
  title: string;
  affected_service_id: string;
  severity: Incident["severity"];
  summary: string;
  symptoms: string;
  recent_changes: string;
  status: Incident["status"];
}

interface AnalysisFormState {
  incident_id: string;
  affected_service_id: string;
  severity: Incident["severity"];
  summary: string;
  symptoms: string;
  recent_changes: string;
}

function getSectionFromHash(hash: string): SectionId {
  const next = hash.replace("#", "") as SectionId;
  return validSections.includes(next) ? next : "home";
}

function getDefaultProjectForm(): ProjectFormState {
  return {
    title: "",
    description: "",
    technologies: "",
    category: "Platform",
    status: "active",
    owner: "",
    image_url: "",
    github_url: "",
    demo_url: "",
    featured: false,
  };
}

function getDefaultServiceForm(): ServiceFormState {
  return {
    name: "",
    service_type: "",
    description: "",
    environment: "dev",
    url: "",
    health_endpoint: "",
    port: "",
    status: "running",
    owner: "",
  };
}

function getDefaultIncidentForm(): IncidentFormState {
  return {
    title: "",
    affected_service_id: "",
    severity: "medium",
    summary: "",
    symptoms: "",
    recent_changes: "",
    status: "open",
  };
}

function getDefaultAnalysisForm(): AnalysisFormState {
  return {
    incident_id: "",
    affected_service_id: "",
    severity: "medium",
    summary: "",
    symptoms: "",
    recent_changes: "",
  };
}

export function PortalPage() {
  const [activeSection, setActiveSection] = useState<SectionId>(() =>
    getSectionFromHash(window.location.hash),
  );
  const [healthStatus, setHealthStatus] = useState("Checking backend health...");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [servicesError, setServicesError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [incidentsError, setIncidentsError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<IncidentAnalysisResponse | null>(null);
  const [analysisState, setAnalysisState] = useState<"idle" | "loading" | "error">("idle");
  const [analysisMessage, setAnalysisMessage] = useState(
    "Select a service, describe the symptoms, and the assistant will return incident class, likely causes, and next checks.",
  );
  const [build, setBuild] = useState<BuildMetadata | null>(null);
  const [buildError, setBuildError] = useState<string | null>(null);

  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editingServiceId, setEditingServiceId] = useState<number | null>(null);
  const [editingIncidentId, setEditingIncidentId] = useState<number | null>(null);

  const [projectForm, setProjectForm] = useState<ProjectFormState>(getDefaultProjectForm);
  const [serviceForm, setServiceForm] = useState<ServiceFormState>(getDefaultServiceForm);
  const [incidentForm, setIncidentForm] = useState<IncidentFormState>(getDefaultIncidentForm);
  const [analysisForm, setAnalysisForm] = useState<AnalysisFormState>(getDefaultAnalysisForm);

  const projectFormRef = useRef<HTMLFormElement | null>(null);
  const serviceFormRef = useRef<HTMLFormElement | null>(null);
  const incidentFormRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    const onHashChange = () => {
      startTransition(() => {
        setActiveSection(getSectionFromHash(window.location.hash));
      });
    };

    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    void refreshPortal();
  }, []);

  useEffect(() => {
    if (activeSection === "observability" && !overview && !overviewError) {
      void loadOverview();
    }
  }, [activeSection, overview, overviewError]);

  async function refreshPortal() {
    await Promise.all([
      loadHealth(),
      loadOverview(),
      loadProjects(),
      loadServices(),
      loadIncidents(),
    ]);
  }

  async function loadHealth() {
    try {
      const data = await api.getHealth();
      setHealthStatus(`Backend health: ${data.status}`);
    } catch {
      setHealthStatus("Backend health check failed");
    }
  }

  async function loadOverview() {
    try {
      const data = await api.getOverview();
      setOverview(data);
      setBuild(data.build);
      setOverviewError(null);
      setBuildError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load overview";
      setOverviewError(message);
      setBuildError(message);
    }
  }

  async function loadProjects() {
    try {
      const data = await api.getProjects();
      setProjects(data);
      setProjectsError(null);
    } catch (error) {
      setProjectsError(error instanceof Error ? error.message : "Failed to load projects");
    }
  }

  async function loadServices() {
    try {
      const data = await api.getServices();
      setServices(data);
      setServicesError(null);
    } catch (error) {
      setServicesError(error instanceof Error ? error.message : "Failed to load services");
    }
  }

  async function loadIncidents() {
    try {
      const data = await api.getIncidents();
      setIncidents(data);
      setIncidentsError(null);
    } catch (error) {
      setIncidentsError(error instanceof Error ? error.message : "Failed to load incidents");
    }
  }

  function scrollToForm(form: HTMLFormElement | null) {
    form?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function resetProjectForm() {
    setEditingProjectId(null);
    setProjectForm(getDefaultProjectForm());
  }

  function resetServiceForm() {
    setEditingServiceId(null);
    setServiceForm(getDefaultServiceForm());
  }

  function resetIncidentForm() {
    setEditingIncidentId(null);
    setIncidentForm(getDefaultIncidentForm());
  }

  function fillProjectForm(project: Project) {
    setEditingProjectId(project.id);
    setProjectForm({
      title: project.title,
      description: project.description,
      technologies: project.technologies.join(", "),
      category: project.category || "Platform",
      status: project.status || "active",
      owner: project.owner ?? "",
      image_url: project.image_url ?? "",
      github_url: project.github_url ?? "",
      demo_url: project.demo_url ?? "",
      featured: project.featured,
    });
    scrollToForm(projectFormRef.current);
  }

  function fillServiceForm(service: Service) {
    setEditingServiceId(service.id);
    setServiceForm({
      name: service.name,
      service_type: service.service_type,
      description: service.description,
      environment: service.environment,
      url: service.url ?? "",
      health_endpoint: service.health_endpoint ?? "",
      port: service.port ? String(service.port) : "",
      status: service.status,
      owner: service.owner ?? "",
    });
    scrollToForm(serviceFormRef.current);
  }

  function fillIncidentForm(incident: Incident) {
    setEditingIncidentId(incident.id);
    setIncidentForm({
      title: incident.title,
      affected_service_id: String(incident.affected_service_id),
      severity: incident.severity,
      summary: incident.summary,
      symptoms: incident.symptoms,
      recent_changes: incident.recent_changes ?? "",
      status: incident.status,
    });
    scrollToForm(incidentFormRef.current);
  }

  function applyIncidentToAssistant(incident: Incident) {
    window.history.replaceState(null, "", "/#ai");
    setActiveSection("ai");
    setAnalysisForm({
      incident_id: String(incident.id),
      affected_service_id: String(incident.affected_service_id),
      severity: incident.severity,
      summary: incident.summary,
      symptoms: incident.symptoms,
      recent_changes: incident.recent_changes ?? "",
    });
    setAnalysis(null);
    setAnalysisMessage(
      "Incident loaded into the assistant. Review the details and run analysis when ready.",
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleProjectSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: ProjectPayload = {
      title: projectForm.title.trim(),
      description: projectForm.description.trim(),
      technologies: parseTechnologies(projectForm.technologies),
      category: projectForm.category.trim() || "Platform",
      status: projectForm.status.trim() || "active",
      owner: emptyToNull(projectForm.owner),
      image_url: emptyToNull(projectForm.image_url),
      github_url: emptyToNull(projectForm.github_url),
      demo_url: emptyToNull(projectForm.demo_url),
      featured: projectForm.featured,
    };

    try {
      if (editingProjectId) {
        await api.updateProject(editingProjectId, payload);
      } else {
        await api.createProject(payload);
      }
      resetProjectForm();
      await Promise.all([loadProjects(), loadOverview()]);
    } catch (error) {
      window.alert(`Project save failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleServiceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: ServicePayload = {
      name: serviceForm.name.trim(),
      service_type: serviceForm.service_type.trim(),
      description: serviceForm.description.trim(),
      environment: serviceForm.environment.trim() || "dev",
      url: emptyToNull(serviceForm.url),
      health_endpoint: emptyToNull(serviceForm.health_endpoint),
      port: serviceForm.port ? Number(serviceForm.port) : null,
      status: serviceForm.status.trim() || "running",
      owner: emptyToNull(serviceForm.owner),
    };

    try {
      if (editingServiceId) {
        await api.updateService(editingServiceId, payload);
      } else {
        await api.createService(payload);
      }
      resetServiceForm();
      await Promise.all([loadServices(), loadOverview(), loadIncidents()]);
    } catch (error) {
      window.alert(`Service save failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleIncidentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: IncidentPayload = {
      title: incidentForm.title.trim(),
      affected_service_id: Number(incidentForm.affected_service_id),
      severity: incidentForm.severity,
      summary: incidentForm.summary.trim(),
      symptoms: incidentForm.symptoms.trim(),
      recent_changes: emptyToNull(incidentForm.recent_changes),
      status: incidentForm.status,
    };

    try {
      if (editingIncidentId) {
        await api.updateIncident(editingIncidentId, payload);
      } else {
        await api.createIncident(payload);
      }
      resetIncidentForm();
      await loadIncidents();
    } catch (error) {
      window.alert(`Incident save failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleAnalysisSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !analysisForm.affected_service_id ||
      !analysisForm.summary.trim() ||
      !analysisForm.symptoms.trim()
    ) {
      return;
    }

    setAnalysisState("loading");
    setAnalysisMessage("Correlating service context, platform overview, and incident patterns...");
    setAnalysis(null);

    try {
      const result = await api.analyzeIncident({
        incident_id: analysisForm.incident_id ? Number(analysisForm.incident_id) : null,
        affected_service_id: Number(analysisForm.affected_service_id),
        severity: analysisForm.severity,
        summary: analysisForm.summary.trim(),
        symptoms: analysisForm.symptoms.trim(),
        recent_changes: emptyToNull(analysisForm.recent_changes),
      });
      setAnalysis(result);
      setAnalysisState("idle");
    } catch (error) {
      setAnalysisState("error");
      setAnalysisMessage(
        `AI incident analysis failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  }

  async function handleEditProject(id: number) {
    try {
      const project = await api.getProject(id);
      fillProjectForm(project);
    } catch (error) {
      window.alert(`Failed to load project: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleDeleteProject(id: number) {
    if (!window.confirm("Remove this project from the active portfolio?")) {
      return;
    }
    try {
      await api.deleteProject(id);
      if (editingProjectId === id) {
        resetProjectForm();
      }
      await Promise.all([loadProjects(), loadOverview()]);
    } catch (error) {
      window.alert(`Failed to remove project: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleEditService(id: number) {
    try {
      const service = await api.getService(id);
      fillServiceForm(service);
    } catch (error) {
      window.alert(`Failed to load service: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleDeleteService(id: number) {
    if (!window.confirm("Remove this service from the catalog?")) {
      return;
    }
    try {
      await api.deleteService(id);
      if (editingServiceId === id) {
        resetServiceForm();
      }
      await Promise.all([loadServices(), loadOverview(), loadIncidents()]);
    } catch (error) {
      window.alert(`Failed to remove service: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleServiceAction(id: number, action: "restart" | "start" | "stop") {
    if (!window.confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} this service?`)) {
      return;
    }
    try {
      await api.queueServiceAction(id, action);
      await Promise.all([loadServices(), loadOverview(), loadIncidents()]);
    } catch (error) {
      window.alert(
        `Failed to ${action} service: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  }

  async function handleEditIncident(id: number) {
    try {
      const incident = await api.getIncident(id);
      fillIncidentForm(incident);
    } catch (error) {
      window.alert(`Failed to load incident: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleDeleteIncident(id: number) {
    if (!window.confirm("Remove this incident from the log?")) {
      return;
    }
    try {
      await api.deleteIncident(id);
      if (editingIncidentId === id) {
        resetIncidentForm();
      }
      await loadIncidents();
    } catch (error) {
      window.alert(`Failed to remove incident: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async function handleAnalyzeIncident(id: number) {
    try {
      const incident = await api.getIncident(id);
      applyIncidentToAssistant(incident);
    } catch (error) {
      window.alert(
        `Failed to load incident for analysis: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  }

  async function handleIncidentTemplateChange(value: string) {
    setAnalysisForm((current) => ({ ...current, incident_id: value }));
    if (!value) {
      return;
    }
    try {
      const incident = await api.getIncident(Number(value));
      applyIncidentToAssistant(incident);
    } catch (error) {
      window.alert(
        `Failed to load incident template: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  }

  async function isEnvironmentHealthy(environmentName: string) {
    const environment = getEnvironmentLink(environmentName);
    const healthUrl = new URL("api/health", environment.href).toString();
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 4500);

    try {
      const response = await fetch(healthUrl, { signal: controller.signal });
      if (!response.ok) {
        return false;
      }
      const payload = (await response.json()) as { status?: string };
      return payload.status === "ok";
    } catch {
      return false;
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  const [productionReachable, setProductionReachable] = useState(false);
  const [developmentReachable, setDevelopmentReachable] = useState(false);

  useEffect(() => {
    if (!overview) {
      return;
    }
    const environmentLabel = inferEnvironmentLabel(overview.environment);
    ["production", "development"]
      .filter((environmentName) => environmentName !== environmentLabel)
      .forEach((environmentName) => {
        void isEnvironmentHealthy(environmentName).then((healthy) => {
          if (environmentName === "production") {
            setProductionReachable(healthy);
          } else {
            setDevelopmentReachable(healthy);
          }
        });
      });
  }, [overview]);

  const environmentLabel = overview ? inferEnvironmentLabel(overview.environment) : "unknown";
  const environmentSummary = overview
    ? summarizeEnvironmentState(overview, environmentLabel)
    : { production: false, development: false };

  const environmentCards = {
    production: environmentLabel === "production" ? environmentSummary.production : productionReachable,
    development:
      environmentLabel === "development" ? environmentSummary.development : developmentReachable,
  };

  const openIncidents = incidents.filter((incident) => incident.status === "open").length;
  const highSeverityOpen = incidents.filter(
    (incident) =>
      incident.status === "open" &&
      (incident.severity === "high" || incident.severity === "critical"),
  ).length;

  return (
    <>
      <SharedNav activeSection={activeSection} />
      <div className="page-shell">
        <main>
          <section className={`section${activeSection === "home" ? " active" : ""}`}>
            <div className="hero">
              <div>
                <p className="eyebrow">DevOps Full Cycle Project</p>
                <h1>Platform as Code</h1>
                <p>
                  A React-powered internal platform portal showing service inventory, project
                  portfolio data, and infrastructure health from one deployed stack.
                </p>
                <div className="status-pill">
                  <span className="status-dot" />
                  <span>{healthStatus}</span>
                </div>
              </div>
            </div>

            <section className="summary-grid">
              {overview ? (
                <>
                  <MetricCard
                    label="Backend"
                    value={overview.backend_status}
                    tone={getStatusTone(overview.backend_status)}
                    meta="API status inside the backend container."
                  />
                  <MetricCard
                    label="Database"
                    value={overview.database_status}
                    tone={getStatusTone(overview.database_status)}
                    meta="Connectivity from FastAPI to PostgreSQL."
                  />
                  <MetricCard
                    label="Frontend / Proxy"
                    value={`${overview.frontend_status} / ${overview.nginx_status}`}
                    meta="Portal delivery path through the reverse proxy."
                  />
                  <MetricCard
                    label="Portfolio"
                    value={String(overview.project_count)}
                    meta={`${overview.featured_project_count} featured projects tracked.`}
                  />
                  <MetricCard
                    label="Services"
                    value={String(overview.service_count)}
                    meta={`${overview.healthy_service_count} healthy service targets.`}
                  />
                  <EnvironmentCard
                    title="Production"
                    current={environmentLabel === "production"}
                    online={environmentCards.production}
                    href="https://kydyrov.dev/"
                  />
                  <EnvironmentCard
                    title="Development"
                    current={environmentLabel === "development"}
                    online={environmentCards.development}
                    href="https://local.kydyrov.dev/"
                  />
                </>
              ) : (
                <div className="empty">
                  {overviewError ? `Failed to load overview: ${overviewError}` : "Loading overview..."}
                </div>
              )}
            </section>

            <div className="section-layout">
              <section className="panel">
                <p className="eyebrow">Infrastructure</p>
                <h2>Service Health</h2>
                <div className="stack">
                  {overview?.services.length ? (
                    overview.services.map((service) => (
                      <article className="card" key={service.id || service.name}>
                        <h3 className="card-title">{service.name}</h3>
                        <p>
                          {service.service_type} in {service.environment}
                        </p>
                        <div className="muted-row">
                          <span>Owner: {service.owner || "unassigned"}</span>
                          <span className={`service-health ${service.healthy ? "ok" : "bad"}`}>
                            {service.healthy ? "healthy" : "unhealthy"}
                          </span>
                        </div>
                        <div className="muted-row">
                          <span>Status: {service.status}</span>
                          <span>{service.detail}</span>
                        </div>
                      </article>
                    ))
                  ) : (
                    <div className="empty">
                      {overviewError ? `Failed to load service health: ${overviewError}` : "No tracked services yet."}
                    </div>
                  )}
                </div>
              </section>

              <section className="panel">
                <p className="eyebrow">Platform Summary</p>
                <h2>What this stack is doing</h2>
                <div className="detail-list">
                  <div className="detail-item">
                    <span>Frontend</span>
                    <strong>Vite + React + TypeScript behind Nginx</strong>
                  </div>
                  <div className="detail-item">
                    <span>Backend</span>
                    <strong>FastAPI + PostgreSQL CRUD APIs</strong>
                  </div>
                  <div className="detail-item">
                    <span>Deploy</span>
                    <strong>Ansible on VM self-hosted runner</strong>
                  </div>
                  <div className="detail-item">
                    <span>Focus</span>
                    <strong>Projects, services, and platform visibility</strong>
                  </div>
                </div>
              </section>
            </div>
          </section>

          <section className={`section${activeSection === "portfolio" ? " active" : ""}`}>
            <p className="eyebrow">Portfolio Management</p>
            <h1>Projects</h1>
            <p>
              Manage portfolio entries with richer metadata, editable details, and soft-delete
              support. Resume details stay in the dedicated Resume tab.
            </p>

            <div className="section-layout">
              <section className="panel">
                <p className="eyebrow">Editor</p>
                <h2>{editingProjectId ? "Edit Project" : "Add Project"}</h2>
                <form ref={projectFormRef} onSubmit={handleProjectSubmit}>
                  <input
                    value={projectForm.title}
                    onChange={(event) =>
                      setProjectForm((current) => ({ ...current, title: event.target.value }))
                    }
                    type="text"
                    placeholder="Project title"
                    required
                  />
                  <textarea
                    value={projectForm.description}
                    onChange={(event) =>
                      setProjectForm((current) => ({ ...current, description: event.target.value }))
                    }
                    placeholder="Describe the project"
                    required
                  />
                  <input
                    value={projectForm.technologies}
                    onChange={(event) =>
                      setProjectForm((current) => ({ ...current, technologies: event.target.value }))
                    }
                    type="text"
                    placeholder="Technologies, comma separated"
                    required
                  />
                  <div className="two-up">
                    <input
                      value={projectForm.category}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, category: event.target.value }))
                      }
                      type="text"
                      placeholder="Category"
                    />
                    <input
                      value={projectForm.status}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, status: event.target.value }))
                      }
                      type="text"
                      placeholder="Status"
                    />
                  </div>
                  <div className="two-up">
                    <input
                      value={projectForm.owner}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, owner: event.target.value }))
                      }
                      type="text"
                      placeholder="Owner"
                    />
                    <input
                      value={projectForm.image_url}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, image_url: event.target.value }))
                      }
                      type="text"
                      placeholder="Image URL"
                    />
                  </div>
                  <div className="two-up">
                    <input
                      value={projectForm.github_url}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, github_url: event.target.value }))
                      }
                      type="url"
                      placeholder="GitHub URL"
                    />
                    <input
                      value={projectForm.demo_url}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, demo_url: event.target.value }))
                      }
                      type="url"
                      placeholder="Demo URL"
                    />
                  </div>
                  <label className="checkbox-row">
                    <input
                      checked={projectForm.featured}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, featured: event.target.checked }))
                      }
                      type="checkbox"
                    />
                    Featured project
                  </label>
                  <div className="actions">
                    <button className="btn-primary" type="submit">
                      {editingProjectId ? "Save project" : "Create project"}
                    </button>
                    <button className="btn-secondary" type="button" onClick={resetProjectForm}>
                      Reset
                    </button>
                  </div>
                </form>
              </section>

              <section className="panel">
                <p className="eyebrow">Collection</p>
                <h2>Current Projects</h2>
                {projectsError ? (
                  <div className="empty">Failed to load projects: {projectsError}</div>
                ) : projects.length === 0 ? (
                  <div className="empty">No projects yet. Create the first one from the editor.</div>
                ) : (
                  <div className="grid">
                    {projects.map((project) => (
                      <article className="card" key={project.id}>
                        <h3 className="card-title">{project.title}</h3>
                        <p>{project.description}</p>
                        <div className="tag-list">
                          {project.technologies.map((tech) => (
                            <span className="tag" key={`${project.id}-${tech}`}>
                              {tech}
                            </span>
                          ))}
                        </div>
                        <div className="muted-row">
                          <span>Category: {project.category}</span>
                          <span className={getStatusTone(project.status)}>Status: {project.status}</span>
                          <span>{project.featured ? "Featured" : "Standard"}</span>
                        </div>
                        <div className="muted-row">
                          <span>Owner: {project.owner || "unassigned"}</span>
                          {project.github_url ? (
                            <a className="project-link" href={project.github_url} target="_blank" rel="noreferrer">
                              GitHub
                            </a>
                          ) : null}
                          {project.demo_url ? (
                            <a className="project-link" href={project.demo_url} target="_blank" rel="noreferrer">
                              Demo
                            </a>
                          ) : null}
                        </div>
                        <div className="actions top-gap">
                          <button className="btn-secondary" onClick={() => void handleEditProject(project.id)} type="button">
                            Edit
                          </button>
                          <button className="btn-danger" onClick={() => void handleDeleteProject(project.id)} type="button">
                            Remove
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </section>

          <section className={`section${activeSection === "services" ? " active" : ""}`}>
            <p className="eyebrow">Infrastructure Catalog</p>
            <h1>Services</h1>
            <p>
              Track the platform services you operate, their owners, health targets, and
              environment metadata.
            </p>

            <div className="section-layout">
              <section className="panel">
                <p className="eyebrow">Editor</p>
                <h2>{editingServiceId ? "Edit Service" : "Add Service"}</h2>
                <form ref={serviceFormRef} onSubmit={handleServiceSubmit}>
                  <input
                    value={serviceForm.name}
                    onChange={(event) =>
                      setServiceForm((current) => ({ ...current, name: event.target.value }))
                    }
                    type="text"
                    placeholder="Service name"
                    required
                  />
                  <div className="two-up">
                    <input
                      value={serviceForm.service_type}
                      onChange={(event) =>
                        setServiceForm((current) => ({ ...current, service_type: event.target.value }))
                      }
                      type="text"
                      placeholder="Service type"
                      required
                    />
                    <input
                      value={serviceForm.environment}
                      onChange={(event) =>
                        setServiceForm((current) => ({ ...current, environment: event.target.value }))
                      }
                      type="text"
                      placeholder="Environment"
                    />
                  </div>
                  <textarea
                    value={serviceForm.description}
                    onChange={(event) =>
                      setServiceForm((current) => ({ ...current, description: event.target.value }))
                    }
                    placeholder="Describe the service"
                    required
                  />
                  <div className="two-up">
                    <input
                      value={serviceForm.url}
                      onChange={(event) =>
                        setServiceForm((current) => ({ ...current, url: event.target.value }))
                      }
                      type="url"
                      placeholder="Public or internal URL"
                    />
                    <input
                      value={serviceForm.health_endpoint}
                      onChange={(event) =>
                        setServiceForm((current) => ({ ...current, health_endpoint: event.target.value }))
                      }
                      type="url"
                      placeholder="Health endpoint URL"
                    />
                  </div>
                  <div className="two-up">
                    <input
                      value={serviceForm.port}
                      onChange={(event) =>
                        setServiceForm((current) => ({ ...current, port: event.target.value }))
                      }
                      type="number"
                      min="1"
                      max="65535"
                      placeholder="Port"
                    />
                    <input
                      value={serviceForm.status}
                      onChange={(event) =>
                        setServiceForm((current) => ({ ...current, status: event.target.value }))
                      }
                      type="text"
                      placeholder="Status"
                    />
                  </div>
                  <input
                    value={serviceForm.owner}
                    onChange={(event) =>
                      setServiceForm((current) => ({ ...current, owner: event.target.value }))
                    }
                    type="text"
                    placeholder="Owner"
                  />
                  <div className="actions">
                    <button className="btn-primary" type="submit">
                      {editingServiceId ? "Save service" : "Create service"}
                    </button>
                    <button className="btn-secondary" type="button" onClick={resetServiceForm}>
                      Reset
                    </button>
                  </div>
                </form>
              </section>

              <section className="panel">
                <p className="eyebrow">Catalog</p>
                <h2>Tracked Services</h2>
                {servicesError ? (
                  <div className="empty">Failed to load services: {servicesError}</div>
                ) : services.length === 0 ? (
                  <div className="empty">No services yet. Add a tracked service from the editor.</div>
                ) : (
                  <div className="grid">
                    {services.map((service) => (
                      <article className="card" key={service.id}>
                        <h3 className="card-title">{service.name}</h3>
                        <p>{service.description}</p>
                        <div className="muted-row">
                          <span>Type: {service.service_type}</span>
                          <span>Env: {service.environment}</span>
                          <span className={getStatusTone(service.status)}>Status: {service.status}</span>
                        </div>
                        <div className="muted-row">
                          <span>Owner: {service.owner || "unassigned"}</span>
                          {service.port ? <span>Port: {service.port}</span> : null}
                        </div>
                        <div className="muted-row">
                          {service.url ? <span>URL: {service.url}</span> : null}
                          {service.health_endpoint ? <span>Health: {service.health_endpoint}</span> : null}
                        </div>
                        <div className="actions top-gap">
                          {service.allowed_actions
                            .filter((action) => {
                              if (action === "start") {
                                return service.status !== "running";
                              }
                              if (action === "stop") {
                                return service.status !== "stopped";
                              }
                              return true;
                            })
                            .map((action) => (
                              <button
                                key={`${service.id}-${action}`}
                                className={action === "restart" ? "btn-primary" : action === "start" ? "btn-secondary" : "btn-danger"}
                                onClick={() => void handleServiceAction(service.id, action as "restart" | "start" | "stop")}
                                type="button"
                              >
                                {action.charAt(0).toUpperCase() + action.slice(1)}
                              </button>
                            ))}
                          <button className="btn-secondary" onClick={() => void handleEditService(service.id)} type="button">
                            Edit
                          </button>
                          <button className="btn-danger" onClick={() => void handleDeleteService(service.id)} type="button">
                            Remove
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </section>

          <section className={`section${activeSection === "incidents" ? " active" : ""}`}>
            <p className="eyebrow">Operational Log</p>
            <h1>Incidents &amp; Events</h1>
            <p>
              Capture manual incidents, monitor-worker summaries, and service-action outcomes.
              Reuse them directly inside the assistant.
            </p>

            <div className="section-layout">
              <section className="panel">
                <p className="eyebrow">Editor</p>
                <h2>{editingIncidentId ? "Edit Incident" : "Add Incident"}</h2>
                <form ref={incidentFormRef} onSubmit={handleIncidentSubmit}>
                  <input
                    value={incidentForm.title}
                    onChange={(event) =>
                      setIncidentForm((current) => ({ ...current, title: event.target.value }))
                    }
                    type="text"
                    placeholder="Incident title"
                    required
                  />
                  <div className="two-up">
                    <select
                      value={incidentForm.affected_service_id}
                      onChange={(event) =>
                        setIncidentForm((current) => ({
                          ...current,
                          affected_service_id: event.target.value,
                        }))
                      }
                      required
                    >
                      <option value="">Select affected service</option>
                      {services.map((service) => (
                        <option key={service.id} value={service.id}>
                          {service.name} ({service.service_type})
                        </option>
                      ))}
                    </select>
                    <select
                      value={incidentForm.status}
                      onChange={(event) =>
                        setIncidentForm((current) => ({
                          ...current,
                          status: event.target.value as Incident["status"],
                        }))
                      }
                    >
                      <option value="open">Open</option>
                      <option value="investigating">Investigating</option>
                      <option value="resolved">Resolved</option>
                    </select>
                  </div>
                  <div className="two-up">
                    <select
                      value={incidentForm.severity}
                      onChange={(event) =>
                        setIncidentForm((current) => ({
                          ...current,
                          severity: event.target.value as Incident["severity"],
                        }))
                      }
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                    <input
                      value={incidentForm.summary}
                      onChange={(event) =>
                        setIncidentForm((current) => ({ ...current, summary: event.target.value }))
                      }
                      type="text"
                      placeholder="Short summary"
                      required
                    />
                  </div>
                  <textarea
                    value={incidentForm.symptoms}
                    onChange={(event) =>
                      setIncidentForm((current) => ({ ...current, symptoms: event.target.value }))
                    }
                    placeholder="Observed symptoms"
                    required
                  />
                  <textarea
                    value={incidentForm.recent_changes}
                    onChange={(event) =>
                      setIncidentForm((current) => ({
                        ...current,
                        recent_changes: event.target.value,
                      }))
                    }
                    placeholder="Optional recent changes"
                  />
                  <div className="actions">
                    <button className="btn-primary" type="submit">
                      {editingIncidentId ? "Save incident" : "Create incident"}
                    </button>
                    <button className="btn-secondary" type="button" onClick={resetIncidentForm}>
                      Reset
                    </button>
                  </div>
                </form>
              </section>

              <section className="panel">
                <p className="eyebrow">Timeline</p>
                <h2>Operational Records</h2>
                {incidentsError ? (
                  <div className="empty">Failed to load incidents: {incidentsError}</div>
                ) : incidents.length === 0 ? (
                  <div className="empty">
                    No operational records yet. Log an incident or wait for the monitor-worker to
                    create platform history.
                  </div>
                ) : (
                  <div className="grid">
                    {incidents.map((incident) => (
                      <article className="card" key={incident.id}>
                        <h3 className="card-title">{incident.title}</h3>
                        <p>{incident.summary}</p>
                        <div className="muted-row">
                          <span className={getStatusTone(incident.severity)}>
                            Severity: {incident.severity}
                          </span>
                          <span>Status: {incident.status}</span>
                          <span>Service ID: {incident.affected_service_id}</span>
                        </div>
                        <div className="muted-row">
                          <span>Source: {incident.source || "manual"}</span>
                          <span>Type: {incident.event_type || "incident"}</span>
                          <span>Recorded: {formatTimestamp(incident.created_at)}</span>
                        </div>
                        <div className="actions top-gap">
                          <button className="btn-primary" onClick={() => void handleAnalyzeIncident(incident.id)} type="button">
                            Analyze
                          </button>
                          {(incident.source || "manual") === "manual" ? (
                            <button className="btn-secondary" onClick={() => void handleEditIncident(incident.id)} type="button">
                              Edit
                            </button>
                          ) : null}
                          {(incident.source || "manual") === "manual" ? (
                            <button className="btn-danger" onClick={() => void handleDeleteIncident(incident.id)} type="button">
                              Remove
                            </button>
                          ) : null}
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </section>

          <section className={`section${activeSection === "ai" ? " active" : ""}`}>
            <p className="eyebrow">AIOps Assistant</p>
            <h1>Incident Response Copilot</h1>
            <p>
              Analyze incidents or logged events against the current service catalog and platform
              overview to get deterministic triage guidance and runbook steps.
            </p>

            <div className="section-layout top-gap-large">
              <section className="panel">
                <p className="eyebrow">Incident Input</p>
                <h2>Analyze Incident</h2>
                <form onSubmit={handleAnalysisSubmit}>
                  <select
                    value={analysisForm.incident_id}
                    onChange={(event) => void handleIncidentTemplateChange(event.target.value)}
                  >
                    {incidents.length === 0 ? (
                      <option value="">No logged incidents yet</option>
                    ) : (
                      <>
                        <option value="">Select existing incident</option>
                        {incidents.map((incident) => (
                          <option key={incident.id} value={incident.id}>
                            {incident.title} ({incident.source || "manual"} · {incident.event_type || "incident"})
                          </option>
                        ))}
                      </>
                    )}
                  </select>
                  <p className="metric-meta helper-copy">
                    Leave empty to analyze a free-form incident, or pick a logged record to autofill.
                  </p>
                  <div className="two-up">
                    <select
                      value={analysisForm.affected_service_id}
                      onChange={(event) =>
                        setAnalysisForm((current) => ({
                          ...current,
                          affected_service_id: event.target.value,
                        }))
                      }
                      required
                    >
                      <option value="">Select affected service</option>
                      {services.map((service) => (
                        <option key={service.id} value={service.id}>
                          {service.name} ({service.service_type})
                        </option>
                      ))}
                    </select>
                    <select
                      value={analysisForm.severity}
                      onChange={(event) =>
                        setAnalysisForm((current) => ({
                          ...current,
                          severity: event.target.value as Incident["severity"],
                        }))
                      }
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <input
                    value={analysisForm.summary}
                    onChange={(event) =>
                      setAnalysisForm((current) => ({ ...current, summary: event.target.value }))
                    }
                    type="text"
                    placeholder="Short summary, e.g. API returns 502 through nginx"
                    required
                  />
                  <textarea
                    value={analysisForm.symptoms}
                    onChange={(event) =>
                      setAnalysisForm((current) => ({ ...current, symptoms: event.target.value }))
                    }
                    placeholder="Observed symptoms, logs, errors, timeouts, or user impact"
                    required
                  />
                  <textarea
                    value={analysisForm.recent_changes}
                    onChange={(event) =>
                      setAnalysisForm((current) => ({
                        ...current,
                        recent_changes: event.target.value,
                      }))
                    }
                    placeholder="Optional: recent deploys, config changes, dependency updates"
                  />
                  <div className="actions">
                    <button className="btn-primary" type="submit" disabled={analysisState === "loading"}>
                      {analysisState === "loading" ? "Analyzing..." : "Analyze Incident"}
                    </button>
                  </div>
                </form>
              </section>

              <section className="panel">
                <p className="eyebrow">Assistant Output</p>
                <h2>Runbook Guidance</h2>
                <div className="ai-output">
                  {analysis ? (
                    <div className="stack">
                      <div>
                        <div className="label">Incident Class</div>
                        <p className="card-title">{analysis.incident_class}</p>
                      </div>
                      <div className="two-up">
                        <div className="card">
                          <div className="label">Priority</div>
                          <p className={`card-title ${getStatusTone(analysis.priority)}`}>
                            {analysis.priority}
                          </p>
                        </div>
                        <div className="card">
                          <div className="label">Confidence</div>
                          <p className="card-title">{analysis.confidence}</p>
                        </div>
                      </div>
                      <div className="card">
                        <div className="label">Service Context</div>
                        <p className="card-title">{analysis.service_context.name}</p>
                        <div className="muted-row">
                          <span>Type: {analysis.service_context.service_type}</span>
                          <span>Env: {analysis.service_context.environment}</span>
                          <span>Status: {analysis.service_context.status}</span>
                        </div>
                        <div className="muted-row">
                          <span>
                            Health: {analysis.service_context.healthy ? "healthy" : "unhealthy"}
                          </span>
                          <span>{analysis.service_context.health_detail || "no probe result"}</span>
                        </div>
                      </div>
                      <AdviceCard title="Suspected Causes" items={analysis.suspected_causes} />
                      <AdviceCard title="Recommended Checks" items={analysis.recommended_checks} />
                      <AdviceCard title="Suggested Runbook" items={analysis.suggested_runbook} />
                      <div className="card">
                        <div className="label">Overview Snapshot</div>
                        <div className="muted-row">
                          <span>Backend: {analysis.overview_snapshot.backend_status}</span>
                          <span>Database: {analysis.overview_snapshot.database_status}</span>
                          <span>Nginx: {analysis.overview_snapshot.nginx_status}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    analysisMessage
                  )}
                </div>
              </section>
            </div>
          </section>

          <section className={`section${activeSection === "observability" ? " active" : ""}`}>
            <p className="eyebrow">Metrics &amp; Monitoring</p>
            <h1>Observability</h1>
            <p>
              Real-time platform health derived from the overview API and probe data collected by
              the monitor-worker. Prometheus scrapes <code>/metrics</code> from backend and
              monitor-worker every 30 seconds. Grafana dashboards are provisioned automatically.
            </p>

            <section className="summary-grid top-gap-large">
              <MetricCard
                label="Healthy Services"
                value={
                  overview
                    ? `${overview.healthy_service_count} / ${overview.service_count}`
                    : "loading"
                }
                tone={
                  overview && overview.healthy_service_count === overview.service_count ? "ok" : "bad"
                }
                meta="Services passing their health probe."
              />
              <MetricCard
                label="Open Incidents"
                value={String(openIncidents)}
                tone={openIncidents === 0 ? "ok" : openIncidents > 3 ? "bad" : "warn"}
                meta={`${highSeverityOpen} high/critical severity.`}
              />
              <MetricCard
                label="Backend"
                value={overview?.backend_status || "loading"}
                tone={getStatusTone(overview?.backend_status || "error")}
                meta="API health inside container."
              />
              <MetricCard
                label="Database"
                value={overview?.database_status || "loading"}
                tone={getStatusTone(overview?.database_status || "error")}
                meta="PostgreSQL reachability."
              />
            </section>

            <iframe
              className="grafana-embed"
              src="/grafana/d/devops-platform-overview/devops-platform-overview?orgId=1&kiosk&refresh=30s"
              loading="lazy"
              title="DevOps Platform Overview Dashboard"
            />

            <div className="section-layout top-gap">
              <section className="panel">
                <p className="eyebrow">Recent Incidents</p>
                <h2>Last 5 Events</h2>
                <div className="stack">
                  {pickRecentIncidents(incidents).length === 0 ? (
                    <div className="empty">No operational records yet.</div>
                  ) : (
                    pickRecentIncidents(incidents).map((incident) => (
                      <article className="card" key={`recent-${incident.id}`}>
                        <p className="card-title">{incident.title}</p>
                        <div className="muted-row">
                          <span className={getStatusTone(incident.severity)}>{incident.severity}</span>
                          <span>{incident.status}</span>
                          <span>{incident.source || "manual"}</span>
                          <span>{formatTimestamp(incident.created_at)}</span>
                        </div>
                      </article>
                    ))
                  )}
                </div>
              </section>

              <section className="panel">
                <p className="eyebrow">External Tools</p>
                <h2>Dashboards</h2>
                <div className="detail-list">
                  <div className="detail-item">
                    <span>Grafana</span>
                    <a
                      className="inline-link"
                      href="/grafana/d/devops-platform-overview/devops-platform-overview"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open full dashboard ->
                    </a>
                  </div>
                  <div className="detail-item">
                    <span>Prometheus</span>
                    <a className="inline-link" href="/prometheus/targets" target="_blank" rel="noreferrer">
                      Open Prometheus ->
                    </a>
                  </div>
                </div>
                <p className="metric-meta top-gap">
                  Routed via Nginx: /prometheus/ and /grafana/ · Scrape interval: 30s · Retention:
                  7 days
                </p>
              </section>
            </div>
          </section>

          <BuildFooter build={build} error={buildError} />
        </main>
      </div>
    </>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  meta: string;
  tone?: "ok" | "warn" | "bad";
}

function MetricCard({ label, value, meta, tone }: MetricCardProps) {
  return (
    <article className="card">
      <div className="label">{label}</div>
      <div className={`metric${tone ? ` ${tone}` : ""}`}>{value}</div>
      <p className="metric-meta">{meta}</p>
    </article>
  );
}

interface EnvironmentCardProps {
  title: string;
  current: boolean;
  online: boolean;
  href: string;
}

function EnvironmentCard({ title, current, online, href }: EnvironmentCardProps) {
  if (current) {
    return (
      <article className="card">
        <div className="label">Environment</div>
        <div className="metric">{title.toLowerCase()}</div>
        <p className="metric-meta">Current application profile returned by the API.</p>
      </article>
    );
  }

  return online ? (
    <a className="card env-card-link" href={href}>
      <div className="label">{title}</div>
      <div className="metric env-card-status env-card-status-online">Online</div>
      <p className="metric-meta">Open the public entrypoint for this environment.</p>
    </a>
  ) : (
    <article className="card card-disabled env-card-offline">
      <div className="label">{title}</div>
      <div className="metric env-card-status env-card-status-offline">Offline</div>
      <p className="metric-meta">This environment is unavailable until the platform recovers.</p>
    </article>
  );
}

interface AdviceCardProps {
  title: string;
  items: string[];
}

function AdviceCard({ title, items }: AdviceCardProps) {
  return (
    <div className="card">
      <div className="label">{title}</div>
      <ul>
        {items.map((item) => (
          <li key={`${title}-${item}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
