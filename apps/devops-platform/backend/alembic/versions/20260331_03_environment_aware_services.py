"""make service environments multi-env aware

Revision ID: 20260331_03
Revises: 20260329_02
Create Date: 2026-03-31 00:00:00.000000

Services that exist in both dev and prod Docker Compose stacks get
environment='all'.  The nginx service stays 'dev' because it only
runs as a Docker container in dev – production uses host Nginx.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260331_03"
down_revision = "20260329_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # backend, frontend, monitor-worker containers exist in both dev and prod
    conn.execute(
        sa.text(
            "UPDATE services SET environment = 'all' "
            "WHERE name IN ('backend', 'frontend', 'monitor-worker')"
        )
    )
    # nginx only runs as a Docker container in dev; prod uses host Nginx
    conn.execute(
        sa.text(
            "UPDATE services SET description = "
            "'Ingress container routing traffic (dev only; prod uses host Nginx).' "
            "WHERE name = 'nginx'"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE services SET environment = 'dev' "
            "WHERE name IN ('backend', 'frontend', 'monitor-worker')"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE services SET description = "
            "'Ingress container routing frontend and backend traffic.' "
            "WHERE name = 'nginx'"
        )
    )
