"""Backfill baseline portal projects and services for production

Revision ID: 20260410_06
Revises: 20260409_05
Create Date: 2026-04-10 00:00:00.000000

Production can report healthy infrastructure but zero tracked inventory when the
database exists without the baseline seeded rows. This migration idempotently
upserts the default portfolio projects and core platform services.
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "20260410_06"
down_revision = "20260409_05"
branch_labels = None
depends_on = None

_PROJECTS = [
    {
        "title": "DevOps Platform",
        "description": (
            "Full-cycle DevOps portal with containerized services, "
            "Ansible deployment, GitHub Actions CI/CD, and incident assistance."
        ),
        "technologies": json.dumps(
            ["Python", "FastAPI", "Docker", "Nginx", "Ansible", "GitHub Actions"]
        ),
        "github_url": "https://github.com/bkolubenka/devops-platform",
        "demo_url": "http://localhost/",
        "image_url": None,
        "category": "Platform",
        "status": "running",
        "owner": "Meirambek Kydyrov",
        "featured": True,
    },
    {
        "title": "AIOps Incident Assistant",
        "description": (
            "Deterministic service-aware assistant that classifies incidents "
            "and suggests runbooks using current platform health and service metadata."
        ),
        "technologies": json.dumps(["FastAPI", "PostgreSQL", "Nginx", "AIOps"]),
        "github_url": None,
        "demo_url": None,
        "image_url": None,
        "category": "AI/ML",
        "status": "running",
        "owner": "Meirambek Kydyrov",
        "featured": True,
    },
]

_SERVICES_WITH_PORT = [
    {
        "name": "backend",
        "service_type": "api",
        "description": "FastAPI application serving overview, CRUD, and incident assistant endpoints.",
        "url": "http://127.0.0.1:8000/",
        "port": 8000,
        "health_endpoint": "http://127.0.0.1:8000/health",
        "environment": "all",
        "status": "running",
        "owner": "Platform",
        "runtime_target": "backend",
        "control_mode": "restart_only",
    },
    {
        "name": "nginx",
        "service_type": "reverse-proxy",
        "description": "Ingress container routing traffic (dev only; prod uses host Nginx).",
        "url": "http://nginx/",
        "port": 80,
        "health_endpoint": "http://nginx/health",
        "environment": "dev",
        "status": "running",
        "owner": "Platform",
        "runtime_target": "nginx",
        "control_mode": "restart_only",
    },
    {
        "name": "monitor-worker",
        "service_type": "ops-worker",
        "description": (
            "Minute-based platform monitor that checks service health, records "
            "operational events, and powers incident autofill."
        ),
        "url": "http://monitor-worker:9000/",
        "port": 9000,
        "health_endpoint": "http://monitor-worker:9000/health",
        "environment": "all",
        "status": "running",
        "owner": "Platform",
        "runtime_target": "monitor_worker",
        "control_mode": "managed",
    },
]

_SERVICES_WITHOUT_PORT = [
    {
        "name": "frontend",
        "service_type": "web-ui",
        "description": "Static frontend served behind Nginx.",
        "url": "http://frontend/",
        "health_endpoint": "http://frontend/",
        "environment": "all",
        "status": "running",
        "owner": "Frontend",
        "runtime_target": "frontend",
        "control_mode": "restart_only",
    },
]

_INSERT_PROJECT = sa.text(
    """
    INSERT INTO projects (
        title, description, technologies, github_url, demo_url, image_url,
        category, status, owner, featured, is_active
    )
    SELECT
        :title, :description, :technologies, :github_url, :demo_url, :image_url,
        :category, :status, :owner, :featured, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM projects WHERE title = :title
    )
    """
)

_UPDATE_PROJECT = sa.text(
    """
    UPDATE projects
    SET
        description = :description,
        technologies = :technologies,
        github_url = :github_url,
        demo_url = :demo_url,
        image_url = :image_url,
        category = :category,
        status = :status,
        owner = :owner,
        featured = :featured,
        is_active = TRUE
    WHERE title = :title
    """
)

_INSERT_SERVICE_WITH_PORT = sa.text(
    """
    INSERT INTO services (
        name, service_type, description, url, port, health_endpoint,
        environment, status, owner, runtime_target, control_mode, is_active
    )
    SELECT
        :name, :service_type, :description, :url, :port, :health_endpoint,
        :environment, :status, :owner, :runtime_target, :control_mode, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM services WHERE name = :name
    )
    """
)

_INSERT_SERVICE_WITHOUT_PORT = sa.text(
    """
    INSERT INTO services (
        name, service_type, description, url, health_endpoint,
        environment, status, owner, runtime_target, control_mode, is_active
    )
    SELECT
        :name, :service_type, :description, :url, :health_endpoint,
        :environment, :status, :owner, :runtime_target, :control_mode, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM services WHERE name = :name
    )
    """
)

_UPDATE_SERVICE = sa.text(
    """
    UPDATE services
    SET
        service_type = :service_type,
        description = :description,
        url = :url,
        health_endpoint = :health_endpoint,
        environment = :environment,
        status = :status,
        owner = :owner,
        runtime_target = :runtime_target,
        control_mode = :control_mode,
        is_active = TRUE
    WHERE name = :name
    """
)

_UPDATE_SERVICE_PORT = sa.text(
    """
    UPDATE services
    SET port = :port
    WHERE name = :name
    """
)


def upgrade() -> None:
    conn = op.get_bind()

    for project in _PROJECTS:
        conn.execute(_INSERT_PROJECT, project)
        conn.execute(_UPDATE_PROJECT, project)

    for service in _SERVICES_WITH_PORT:
        conn.execute(_INSERT_SERVICE_WITH_PORT, service)
        conn.execute(_UPDATE_SERVICE, service)
        conn.execute(_UPDATE_SERVICE_PORT, service)

    for service in _SERVICES_WITHOUT_PORT:
        conn.execute(_INSERT_SERVICE_WITHOUT_PORT, service)
        conn.execute(_UPDATE_SERVICE, service)
        conn.execute(_UPDATE_SERVICE_PORT, {"name": service["name"], "port": None})


def downgrade() -> None:
    pass