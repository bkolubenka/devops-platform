"""Fix backend service health endpoint to use localhost

Revision ID: 20260408_04
Revises: 20260331_03
Create Date: 2026-04-08 00:00:00.000000

The backend service's health_endpoint was set to http://backend:8000/health, which
relies on Docker DNS self-resolution.  Some Docker setups (including certain Docker
Engine versions and network configurations) fail to resolve a container's own service
name, causing the inline probe in compute_overview to time-out and report
backend_status="error" even when the backend is healthy.

Using http://127.0.0.1:8000/health instead removes the Docker DNS dependency: the
backend container always reaches its own port 8000 via loopback.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260408_04"
down_revision = "20260331_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE services SET health_endpoint = 'http://127.0.0.1:8000/health' "
            "WHERE name = 'backend' AND health_endpoint = 'http://backend:8000/health'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE services SET url = 'http://127.0.0.1:8000/' "
            "WHERE name = 'backend' AND url = 'http://backend:8000/'"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE services SET health_endpoint = 'http://backend:8000/health' "
            "WHERE name = 'backend' AND health_endpoint = 'http://127.0.0.1:8000/health'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE services SET url = 'http://backend:8000/' "
            "WHERE name = 'backend' AND url = 'http://127.0.0.1:8000/'"
        )
    )
