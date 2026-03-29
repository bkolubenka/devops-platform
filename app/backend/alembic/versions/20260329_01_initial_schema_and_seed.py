"""initial schema and seed data

Revision ID: 20260329_01
Revises:
Create Date: 2026-03-29 00:00:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "20260329_01"
down_revision = None
branch_labels = None
depends_on = None


def _create_projects_table() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                technologies TEXT NOT NULL,
                github_url VARCHAR(500),
                demo_url VARCHAR(500),
                image_url VARCHAR(500),
                category VARCHAR(100) DEFAULT 'Platform',
                status VARCHAR(50) DEFAULT 'active',
                owner VARCHAR(100),
                featured BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )
    )

    for column_name, column_definition in [
        ("category", "VARCHAR(100) DEFAULT 'Platform'"),
        ("status", "VARCHAR(50) DEFAULT 'active'"),
        ("owner", "VARCHAR(100)"),
        ("featured", "BOOLEAN DEFAULT FALSE"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ]:
        op.execute(
            sa.text(
                f"ALTER TABLE projects ADD COLUMN IF NOT EXISTS {column_name} {column_definition}"
            )
        )


def _create_skills_table() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                level INTEGER NOT NULL,
                category VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )
    )

    op.execute(
        sa.text("ALTER TABLE skills ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    )


def _create_services_table() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS services (
                id SERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                service_type VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                url VARCHAR(500),
                port INTEGER,
                health_endpoint VARCHAR(500),
                environment VARCHAR(50) DEFAULT 'dev',
                status VARCHAR(50) DEFAULT 'running',
                owner VARCHAR(100),
                runtime_target VARCHAR(120),
                control_mode VARCHAR(50) DEFAULT 'observe',
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )
    )

    for column_name, column_definition in [
        ("environment", "VARCHAR(50) DEFAULT 'dev'"),
        ("status", "VARCHAR(50) DEFAULT 'running'"),
        ("owner", "VARCHAR(100)"),
        ("runtime_target", "VARCHAR(120)"),
        ("control_mode", "VARCHAR(50) DEFAULT 'observe'"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ]:
        op.execute(
            sa.text(
                f"ALTER TABLE services ADD COLUMN IF NOT EXISTS {column_name} {column_definition}"
            )
        )


def _create_incidents_table() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                affected_service_id INTEGER,
                severity VARCHAR(50) NOT NULL DEFAULT 'medium',
                summary TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                recent_changes TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                source VARCHAR(100) DEFAULT 'manual',
                event_type VARCHAR(100) DEFAULT 'incident',
                overview_snapshot TEXT,
                analysis TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )
    )

    for column_name, column_definition in [
        ("source", "VARCHAR(100) DEFAULT 'manual'"),
        ("event_type", "VARCHAR(100) DEFAULT 'incident'"),
        ("overview_snapshot", "TEXT"),
        ("analysis", "TEXT"),
        ("created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
    ]:
        op.execute(
            sa.text(
                f"ALTER TABLE incidents ADD COLUMN IF NOT EXISTS {column_name} {column_definition}"
            )
        )


def _seed_projects() -> None:
    conn = op.get_bind()
    for project in [
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
    ]:
        conn.execute(
            sa.text(
                """
                INSERT INTO projects (
                    title, description, technologies, github_url, demo_url, image_url,
                    category, status, owner, featured
                )
                SELECT
                    :title, :description, :technologies, :github_url, :demo_url, :image_url,
                    :category, :status, :owner, :featured
                WHERE NOT EXISTS (
                    SELECT 1 FROM projects WHERE title = :title
                )
                """
            ),
            project,
        )


def _seed_skills() -> None:
    conn = op.get_bind()
    for skill in [
        {"name": "Python", "level": 5, "category": "Backend"},
        {"name": "FastAPI", "level": 4, "category": "Backend"},
        {"name": "Docker", "level": 4, "category": "DevOps"},
        {"name": "Ansible", "level": 4, "category": "Infrastructure"},
        {"name": "PostgreSQL", "level": 3, "category": "Database"},
        {"name": "GitHub Actions", "level": 4, "category": "CI/CD"},
    ]:
        conn.execute(
            sa.text(
                """
                INSERT INTO skills (name, level, category)
                SELECT :name, :level, :category
                WHERE NOT EXISTS (
                    SELECT 1 FROM skills WHERE name = :name
                )
                """
            ),
            skill,
        )


def _seed_services() -> None:
    conn = op.get_bind()
    services = [
        {
            "name": "frontend",
            "service_type": "web-ui",
            "description": "Static frontend served behind Nginx.",
            "url": "http://frontend/",
            "port": None,
            "health_endpoint": "http://frontend/",
            "environment": "dev",
            "status": "running",
            "owner": "Frontend",
            "runtime_target": "frontend",
            "control_mode": "restart_only",
        },
        {
            "name": "backend",
            "service_type": "api",
            "description": "FastAPI application serving overview, CRUD, and incident assistant endpoints.",
            "url": "http://backend:8000/",
            "port": 8000,
            "health_endpoint": "http://backend:8000/health",
            "environment": "dev",
            "status": "running",
            "owner": "Platform",
            "runtime_target": "backend",
            "control_mode": "restart_only",
        },
        {
            "name": "nginx",
            "service_type": "reverse-proxy",
            "description": "Ingress container routing frontend and backend traffic.",
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
            "environment": "dev",
            "status": "running",
            "owner": "Platform",
            "runtime_target": "monitor_worker",
            "control_mode": "managed",
        },
    ]

    for service in services:
        conn.execute(
            sa.text(
                """
                INSERT INTO services (
                    name, service_type, description, url, port, health_endpoint,
                    environment, status, owner, runtime_target, control_mode
                )
                SELECT
                    :name, :service_type, :description, :url, :port, :health_endpoint,
                    :environment, :status, :owner, :runtime_target, :control_mode
                WHERE NOT EXISTS (
                    SELECT 1 FROM services WHERE name = :name
                )
                """
            ),
            service,
        )


def _seed_incidents() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO incidents (
                title, affected_service_id, severity, summary, symptoms,
                recent_changes, status, source, event_type, overview_snapshot
            )
            SELECT
                :title,
                s.id,
                :severity,
                :summary,
                :symptoms,
                :recent_changes,
                :status,
                :source,
                :event_type,
                :overview_snapshot
            FROM services s
            WHERE s.name = :service_name
              AND NOT EXISTS (
                    SELECT 1 FROM incidents WHERE title = :title
              )
            """
        ),
        {
            "title": "Sample API incident",
            "service_name": "backend",
            "severity": "medium",
            "summary": "API health degraded after a recent backend change.",
            "symptoms": "Users report slow responses and occasional 502 errors through nginx.",
            "recent_changes": "Recent backend deploy with API changes.",
            "status": "open",
            "source": "manual",
            "event_type": "incident",
            "overview_snapshot": json.dumps(
                {
                    "seeded": True,
                    "note": "Initial demo incident for incident autofill and analysis.",
                }
            ),
        },
    )


def upgrade() -> None:
    _create_projects_table()
    _create_skills_table()
    _create_services_table()
    _create_incidents_table()
    _seed_projects()
    _seed_skills()
    _seed_services()
    _seed_incidents()


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS incidents"))
    op.execute(sa.text("DROP TABLE IF EXISTS services"))
    op.execute(sa.text("DROP TABLE IF EXISTS skills"))
    op.execute(sa.text("DROP TABLE IF EXISTS projects"))

