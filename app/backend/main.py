import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Project as DBProject
from .models import Service as DBService
from .models import Skill as DBSkill

Base.metadata.create_all(bind=engine)

APP_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

INCIDENT_RUNBOOKS: dict[str, dict[str, Any]] = {
    "service_unavailable": {
        "priority": "high",
        "confidence": "high",
        "suspected_causes": [
            "The service process is not responding on its configured health target.",
            "A recent container restart, bad config, or unreachable upstream may have made the service unavailable.",
        ],
        "recommended_checks": [
            "Verify the service container is running and healthy.",
            "Inspect recent container logs for startup or dependency failures.",
            "Check whether the configured URL or health endpoint still resolves correctly.",
        ],
        "suggested_runbook": [
            "Run a targeted health check against the service endpoint.",
            "Inspect `docker ps` and `docker logs <service>` on the VM.",
            "If the service was changed recently, redeploy the last known good revision.",
        ],
    },
    "database_connectivity": {
        "priority": "critical",
        "confidence": "high",
        "suspected_causes": [
            "The application cannot establish a connection to PostgreSQL.",
            "Database credentials, networking, or startup ordering may have regressed.",
        ],
        "recommended_checks": [
            "Confirm the PostgreSQL container is healthy and listening.",
            "Validate `DATABASE_URL` and current DB credentials.",
            "Check application logs for connection refused, timeout, or authentication errors.",
        ],
        "suggested_runbook": [
            "Inspect the DB container health and logs.",
            "Run a simple DB connectivity check from the backend container.",
            "If the issue started after config changes, roll back the connection settings.",
        ],
    },
    "reverse_proxy_routing": {
        "priority": "high",
        "confidence": "high",
        "suspected_causes": [
            "Nginx routing or upstream proxy configuration is mismatched with the backend.",
            "The reverse proxy may be stripping or misrouting a request path.",
        ],
        "recommended_checks": [
            "Inspect Nginx container logs for upstream or config errors.",
            "Confirm the proxied path exists on the backend and returns 200.",
            "Verify the correct dev or prod Nginx config is mounted into the container.",
        ],
        "suggested_runbook": [
            "Check `/health`, `/api/health`, and the affected route through Nginx and directly against the backend.",
            "Validate the active Nginx config inside the container.",
            "Restart Nginx only after confirming the upstream target is healthy.",
        ],
    },
    "deployment_regression": {
        "priority": "high",
        "confidence": "medium",
        "suspected_causes": [
            "A recent deployment introduced an incompatible config or behavior change.",
            "The runtime image or compose stack may no longer match the expected environment.",
        ],
        "recommended_checks": [
            "Review the latest application and deployment changes.",
            "Compare current environment variables and container image behavior with the previous stable state.",
            "Check whether new migrations, routes, or proxy changes were introduced.",
        ],
        "suggested_runbook": [
            "Inspect the latest CI/deploy run and application logs.",
            "Confirm the expected compose file and environment profile were used.",
            "If impact is high, redeploy the previous known good commit.",
        ],
    },
    "high_latency": {
        "priority": "medium",
        "confidence": "medium",
        "suspected_causes": [
            "The service is reachable but responding slowly.",
            "The issue may be caused by database load, resource pressure, or upstream timeouts.",
        ],
        "recommended_checks": [
            "Measure response time for the affected endpoint and health endpoint.",
            "Inspect CPU, memory, and database activity around the incident window.",
            "Check for timeouts or retry storms in application or proxy logs.",
        ],
        "suggested_runbook": [
            "Compare current response time with a known healthy baseline.",
            "Inspect database-intensive requests or recent changes in traffic profile.",
            "Scale down troubleshooting scope to the affected service and its direct dependencies.",
        ],
    },
    "unknown": {
        "priority": "medium",
        "confidence": "low",
        "suspected_causes": [
            "The signal is incomplete or does not match the current incident patterns.",
            "A cross-service or environment-specific issue may be involved.",
        ],
        "recommended_checks": [
            "Clarify what changed, which service is impacted, and what symptoms are visible.",
            "Check the affected service, its dependencies, and the current platform overview.",
            "Collect logs, timing, and health data before taking destructive actions.",
        ],
        "suggested_runbook": [
            "Start with service health, logs, and dependency checks.",
            "Compare current behavior with the last known healthy deployment.",
            "Escalate once you have a minimal reproducible failure pattern.",
        ],
    },
}

INCIDENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "database_connectivity": (
        "database",
        "postgres",
        "postgresql",
        "db",
        "connection refused",
        "authentication failed",
        "sqlalchemy",
    ),
    "reverse_proxy_routing": (
        "nginx",
        "proxy",
        "502",
        "504",
        "routing",
        "upstream",
        "bad gateway",
        "gateway timeout",
    ),
    "deployment_regression": (
        "deploy",
        "deployment",
        "release",
        "rollback",
        "after update",
        "after merge",
        "new version",
    ),
    "high_latency": (
        "slow",
        "latency",
        "timeout",
        "timed out",
        "sluggish",
        "performance",
    ),
    "service_unavailable": (
        "down",
        "unavailable",
        "not responding",
        "refused",
        "crash",
        "stopped",
    ),
}


def ensure_schema_alignment() -> None:
    """Keep the demo schema aligned without requiring migrations yet."""
    project_columns = [
        ("category", "VARCHAR(100) DEFAULT 'Platform'"),
        ("status", "VARCHAR(50) DEFAULT 'active'"),
        ("owner", "VARCHAR(100)"),
        ("featured", "BOOLEAN DEFAULT FALSE"),
    ]
    with engine.begin() as connection:
        for column_name, column_definition in project_columns:
            connection.execute(
                text(
                    f"ALTER TABLE projects "
                    f"ADD COLUMN IF NOT EXISTS {column_name} {column_definition}"
                )
            )


ensure_schema_alignment()

app = FastAPI(title="DevOps Platform API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=10)
    technologies: list[str]
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    image_url: Optional[str] = None
    category: str = "Platform"
    status: str = "active"
    owner: Optional[str] = None
    featured: bool = False


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SkillRead(BaseModel):
    id: int
    name: str
    level: int
    category: str
    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    name: str
    level: int = Field(ge=1, le=5)
    category: str


class ServiceBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    service_type: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5)
    url: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    health_endpoint: Optional[str] = None
    environment: str = "dev"
    status: str = "running"
    owner: Optional[str] = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(ServiceBase):
    pass


class ServiceRead(ServiceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ServiceOverview(BaseModel):
    id: int
    name: str
    service_type: str
    environment: str
    status: str
    url: Optional[str]
    health_endpoint: Optional[str]
    owner: Optional[str]
    healthy: bool
    detail: str


class OverviewResponse(BaseModel):
    backend_status: str
    database_status: str
    frontend_status: str
    nginx_status: str
    project_count: int
    service_count: int
    healthy_service_count: int
    featured_project_count: int
    environment: str
    services: list[ServiceOverview]


class IncidentRequest(BaseModel):
    summary: str = Field(min_length=5)
    affected_service_id: Optional[int] = None
    affected_service_name: Optional[str] = None
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    symptoms: str = Field(min_length=5)
    recent_changes: Optional[str] = None

    @model_validator(mode="after")
    def validate_service_reference(self) -> "IncidentRequest":
        if not self.affected_service_id and not self.affected_service_name:
            raise ValueError(
                "Either affected_service_id or affected_service_name must be provided."
            )
        return self


class IncidentServiceContext(BaseModel):
    id: Optional[int]
    name: str
    service_type: str
    environment: str
    status: str
    owner: Optional[str]
    url: Optional[str]
    health_endpoint: Optional[str]
    healthy: Optional[bool]
    health_detail: Optional[str]


class IncidentAnalysisResponse(BaseModel):
    incident_class: str
    priority: str
    confidence: str
    suspected_causes: list[str]
    recommended_checks: list[str]
    suggested_runbook: list[str]
    service_context: IncidentServiceContext
    overview_snapshot: dict[str, Any]


class TextGenerationRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 200


class TextGenerationResponse(BaseModel):
    generated_text: str


def serialize_project(project: DBProject) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        technologies=json.loads(project.technologies),
        github_url=project.github_url,
        demo_url=project.demo_url,
        image_url=project.image_url,
        category=project.category or "Platform",
        status=project.status or "active",
        owner=project.owner,
        featured=bool(project.featured),
    )


def serialize_service(service: DBService) -> ServiceRead:
    return ServiceRead.model_validate(service)


def check_http_target(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return True, f"http {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"http {exc.code}"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def build_service_overview(service: DBService) -> ServiceOverview:
    target = service.health_endpoint or service.url
    if target:
        healthy, detail = check_http_target(target)
    else:
        healthy, detail = False, "no health target configured"

    return ServiceOverview(
        id=service.id,
        name=service.name,
        service_type=service.service_type,
        environment=service.environment,
        status=service.status,
        url=service.url,
        health_endpoint=service.health_endpoint,
        owner=service.owner,
        healthy=healthy,
        detail=detail,
    )


def compute_overview(db: Session) -> OverviewResponse:
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    backend_ok, _ = check_http_target("http://127.0.0.1:8000/health")
    frontend_ok, _ = check_http_target("http://frontend/")
    nginx_ok, _ = check_http_target("http://nginx/health")

    services = [
        build_service_overview(service)
        for service in db.query(DBService).filter(DBService.is_active.is_(True)).all()
    ]

    return OverviewResponse(
        backend_status="ok" if backend_ok else "error",
        database_status=database_status,
        frontend_status="ok" if frontend_ok else "error",
        nginx_status="ok" if nginx_ok else "error",
        project_count=db.query(DBProject).filter(DBProject.is_active.is_(True)).count(),
        service_count=len(services),
        healthy_service_count=sum(1 for service in services if service.healthy),
        featured_project_count=db.query(DBProject)
        .filter(DBProject.is_active.is_(True), DBProject.featured.is_(True))
        .count(),
        environment=APP_ENVIRONMENT,
        services=services,
    )


def resolve_service_context(db: Session, payload: IncidentRequest) -> IncidentServiceContext:
    service: Optional[DBService] = None
    if payload.affected_service_id is not None:
        service = (
            db.query(DBService)
            .filter(
                DBService.id == payload.affected_service_id,
                DBService.is_active.is_(True),
            )
            .first()
        )
    elif payload.affected_service_name:
        service = (
            db.query(DBService)
            .filter(
                text("lower(name) = :service_name"),
                DBService.is_active.is_(True),
            )
            .params(service_name=payload.affected_service_name.lower())
            .first()
        )

    if not service:
        raise HTTPException(status_code=404, detail="Affected service not found")

    overview = build_service_overview(service)
    return IncidentServiceContext(
        id=overview.id,
        name=overview.name,
        service_type=overview.service_type,
        environment=overview.environment,
        status=overview.status,
        owner=overview.owner,
        url=overview.url,
        health_endpoint=overview.health_endpoint,
        healthy=overview.healthy,
        health_detail=overview.detail,
    )


def classify_incident(
    summary: str,
    symptoms: str,
    recent_changes: Optional[str],
    service_context: IncidentServiceContext,
) -> str:
    combined = " ".join(
        filter(
            None,
            [
                summary.lower(),
                symptoms.lower(),
                (recent_changes or "").lower(),
                service_context.service_type.lower(),
                service_context.name.lower(),
            ],
        )
    )

    scores = {key: 0 for key in INCIDENT_RUNBOOKS}

    for incident_class, keywords in INCIDENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                scores[incident_class] += 1

    if service_context.service_type == "reverse-proxy":
        scores["reverse_proxy_routing"] += 2
    if service_context.service_type in {"database", "db"}:
        scores["database_connectivity"] += 2
    if service_context.name == "db":
        scores["database_connectivity"] += 2
    if recent_changes:
        scores["deployment_regression"] += 1
    if service_context.healthy is False:
        scores["service_unavailable"] += 1

    best_class = max(scores, key=scores.get)
    return best_class if scores[best_class] > 0 else "unknown"


def apply_service_context_guidance(
    base_items: list[str], service_context: IncidentServiceContext
) -> list[str]:
    items = list(base_items)
    if service_context.health_endpoint:
        items.append(
            f"Check the service health target directly: {service_context.health_endpoint}"
        )
    if service_context.url:
        items.append(f"Validate the primary service URL path: {service_context.url}")
    if service_context.owner:
        items.append(f"Coordinate with the recorded service owner: {service_context.owner}")
    return items


def build_incident_analysis(
    db: Session, payload: IncidentRequest
) -> IncidentAnalysisResponse:
    service_context = resolve_service_context(db, payload)
    overview = compute_overview(db)
    incident_class = classify_incident(
        payload.summary, payload.symptoms, payload.recent_changes, service_context
    )
    runbook = INCIDENT_RUNBOOKS[incident_class]

    suspected_causes = list(runbook["suspected_causes"])
    recommended_checks = apply_service_context_guidance(
        runbook["recommended_checks"], service_context
    )
    suggested_runbook = apply_service_context_guidance(
        runbook["suggested_runbook"], service_context
    )

    if payload.recent_changes:
        suspected_causes.append(
            f"Recent change noted by the operator: {payload.recent_changes}"
        )
    if service_context.healthy is False and service_context.health_detail:
        suspected_causes.append(
            f"Current service health probe is failing: {service_context.health_detail}"
        )

    return IncidentAnalysisResponse(
        incident_class=incident_class,
        priority=runbook["priority"] if payload.severity in {"low", "medium"} else payload.severity,
        confidence=runbook["confidence"],
        suspected_causes=suspected_causes,
        recommended_checks=recommended_checks,
        suggested_runbook=suggested_runbook,
        service_context=service_context,
        overview_snapshot=overview.model_dump(),
    )


def initialize_sample_data(db: Session) -> None:
    if db.query(DBProject).count() == 0:
        project_records = [
            DBProject(
                title="DevOps Platform",
                description=(
                    "Full-cycle DevOps portal with containerized services, "
                    "Ansible deployment, GitHub Actions CI/CD, and incident assistance."
                ),
                technologies=json.dumps(
                    ["Python", "FastAPI", "Docker", "Nginx", "Ansible", "GitHub Actions"]
                ),
                github_url="https://github.com/bkolubenka/devops-platform",
                demo_url="http://localhost/",
                category="Platform",
                status="running",
                owner="Meirambek Kydyrov",
                featured=True,
            ),
            DBProject(
                title="AIOps Incident Assistant",
                description=(
                    "Deterministic service-aware assistant that classifies incidents "
                    "and suggests runbooks using current platform health and service metadata."
                ),
                technologies=json.dumps(["FastAPI", "PostgreSQL", "Nginx", "AIOps"]),
                category="AI/ML",
                status="running",
                owner="Meirambek Kydyrov",
                featured=True,
            ),
        ]
        db.add_all(project_records)

    if db.query(DBSkill).count() == 0:
        skill_records = [
            DBSkill(name="Python", level=5, category="Backend"),
            DBSkill(name="FastAPI", level=4, category="Backend"),
            DBSkill(name="Docker", level=4, category="DevOps"),
            DBSkill(name="Ansible", level=4, category="Infrastructure"),
            DBSkill(name="PostgreSQL", level=3, category="Database"),
            DBSkill(name="GitHub Actions", level=4, category="CI/CD"),
        ]
        db.add_all(skill_records)

    if db.query(DBService).count() == 0:
        service_records = [
            DBService(
                name="frontend",
                service_type="web-ui",
                description="Static frontend served behind Nginx.",
                url="http://frontend/",
                health_endpoint="http://frontend/",
                environment="dev",
                status="running",
                owner="Frontend",
            ),
            DBService(
                name="backend",
                service_type="api",
                description="FastAPI application serving overview, CRUD, and incident assistant endpoints.",
                url="http://backend:8000/",
                health_endpoint="http://backend:8000/health",
                environment="dev",
                status="running",
                owner="Platform",
            ),
            DBService(
                name="nginx",
                service_type="reverse-proxy",
                description="Ingress container routing frontend and backend traffic.",
                url="http://nginx/",
                health_endpoint="http://nginx/health",
                environment="dev",
                status="running",
                owner="Platform",
            ),
        ]
        db.add_all(service_records)

    db.commit()


@app.on_event("startup")
async def startup_event() -> None:
    db = next(get_db())
    try:
        initialize_sample_data(db)
    finally:
        db.close()


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "DevOps Platform API running"}


@app.get("/api/overview", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)) -> OverviewResponse:
    return compute_overview(db)


@app.get("/api/portfolio/projects", response_model=list[ProjectRead])
def get_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    projects = db.query(DBProject).filter(DBProject.is_active.is_(True)).all()
    return [serialize_project(project) for project in projects]


@app.get("/api/portfolio/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectRead:
    project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.is_active.is_(True))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize_project(project)


@app.post(
    "/api/portfolio/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    db_project = DBProject(
        title=project.title,
        description=project.description,
        technologies=json.dumps(project.technologies),
        github_url=project.github_url,
        demo_url=project.demo_url,
        image_url=project.image_url,
        category=project.category,
        status=project.status,
        owner=project.owner,
        featured=project.featured,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return serialize_project(db_project)


@app.put("/api/portfolio/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)
) -> ProjectRead:
    db_project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.is_active.is_(True))
        .first()
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_project.title = payload.title
    db_project.description = payload.description
    db_project.technologies = json.dumps(payload.technologies)
    db_project.github_url = payload.github_url
    db_project.demo_url = payload.demo_url
    db_project.image_url = payload.image_url
    db_project.category = payload.category
    db_project.status = payload.status
    db_project.owner = payload.owner
    db_project.featured = payload.featured

    db.commit()
    db.refresh(db_project)
    return serialize_project(db_project)


@app.delete("/api/portfolio/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> Response:
    db_project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.is_active.is_(True))
        .first()
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_project.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/portfolio/skills", response_model=list[SkillRead])
def get_skills(db: Session = Depends(get_db)) -> list[SkillRead]:
    skills = db.query(DBSkill).filter(DBSkill.is_active.is_(True)).all()
    return [SkillRead.model_validate(skill) for skill in skills]


@app.post(
    "/api/portfolio/skills",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
)
def create_skill(skill: SkillCreate, db: Session = Depends(get_db)) -> SkillRead:
    db_skill = DBSkill(name=skill.name, level=skill.level, category=skill.category)
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return SkillRead.model_validate(db_skill)


@app.get("/api/services", response_model=list[ServiceRead])
def get_services(db: Session = Depends(get_db)) -> list[ServiceRead]:
    services = db.query(DBService).filter(DBService.is_active.is_(True)).all()
    return [serialize_service(service) for service in services]


@app.get("/api/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: Session = Depends(get_db)) -> ServiceRead:
    service = (
        db.query(DBService)
        .filter(DBService.id == service_id, DBService.is_active.is_(True))
        .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return serialize_service(service)


@app.post("/api/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(service: ServiceCreate, db: Session = Depends(get_db)) -> ServiceRead:
    db_service = DBService(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return serialize_service(db_service)


@app.put("/api/services/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int, payload: ServiceUpdate, db: Session = Depends(get_db)
) -> ServiceRead:
    db_service = (
        db.query(DBService)
        .filter(DBService.id == service_id, DBService.is_active.is_(True))
        .first()
    )
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")

    for field, value in payload.model_dump().items():
        setattr(db_service, field, value)

    db.commit()
    db.refresh(db_service)
    return serialize_service(db_service)


@app.delete("/api/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: Session = Depends(get_db)) -> Response:
    db_service = (
        db.query(DBService)
        .filter(DBService.id == service_id, DBService.is_active.is_(True))
        .first()
    )
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")

    db_service.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/ai/incidents/analyze",
    response_model=IncidentAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_incident(
    payload: IncidentRequest, db: Session = Depends(get_db)
) -> IncidentAnalysisResponse:
    return build_incident_analysis(db, payload)


@app.post("/api/ai/generate-text", response_model=TextGenerationResponse)
def generate_text(request: TextGenerationRequest) -> TextGenerationResponse:
    prompt = request.prompt.lower()

    if "incident" in prompt or "service" in prompt:
        generated = (
            "Use the incident assistant to classify failures, inspect service context, "
            "and get deterministic runbook guidance."
        )
    elif "portfolio" in prompt:
        generated = (
            "This platform supports portfolio CRUD, service inventory, overview metrics, "
            "and an AIOps-oriented incident assistant."
        )
    elif "devops" in prompt:
        generated = (
            "This demo combines FastAPI, Docker, Nginx, Ansible, PostgreSQL, "
            "GitHub Actions, and an incident assistant into one deployable platform."
        )
    else:
        generated = (
            f"Thank you for your input: '{request.prompt}'. "
            "The main AI capability in this platform is now the incident assistant."
        )

    return TextGenerationResponse(generated_text=generated[: request.max_length or 200])


@app.get("/api/ai/models")
def get_available_models() -> dict[str, object]:
    return {
        "models": [
            {
                "name": "incident-assistant-v1",
                "type": "rule-based-aiops",
                "description": "Deterministic service-aware incident assistant",
            },
            {
                "name": "text-generator-v1",
                "type": "text-generation",
                "description": "Lightweight demo text generation endpoint",
            },
        ],
        "status": "local-first",
    }
