"""Ensure production service seeds exist with correct endpoints

Revision ID: 20260409_05
Revises: 20260408_04
Create Date: 2026-04-09 00:00:00.000000

Production deployments may have an empty services table if the initial seed
migration (20260329_01) was skipped or the DB was re-initialised without data.
This migration upserts the four core platform services with the correct
endpoints for production:

- backend  : http://127.0.0.1:8000/health  (loopback, avoids Docker DNS self-lookup)
- frontend : http://frontend/              (Docker service-name DNS, port 80)
- nginx    : environment=dev only          (host Nginx in prod has no container)
- monitor-worker: http://monitor-worker:9000/health

All app services are set to environment='all' so they appear in both dev and
prod overview queries.  nginx stays 'dev' because it is a Docker container only
in dev; production uses host Nginx.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260409_05"
down_revision = "20260408_04"
branch_labels = None
depends_on = None

_SERVICES = [
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
        "name": "frontend",
        "service_type": "web-ui",
        "description": "Static frontend served behind Nginx.",
        "url": "http://frontend/",
        "port": None,
        "health_endpoint": "http://frontend/",
        "environment": "all",
        "status": "running",
        "owner": "Frontend",
        "runtime_target": "frontend",
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


def upgrade() -> None:
    conn = op.get_bind()
    for svc in _SERVICES:
        # Insert if not present.
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
            svc,
        )
        # Update the endpoint + environment for existing rows to match the
        # correct production values set by previous migrations.
        conn.execute(
            sa.text(
                """
                UPDATE services
                SET
                    health_endpoint = :health_endpoint,
                    url             = :url,
                    environment     = :environment,
                    description     = :description
                WHERE name = :name
                """
            ),
            svc,
        )


def downgrade() -> None:
    # Nothing to revert — removing seeds would destroy user data if they
    # registered additional services under the same names.
    pass
