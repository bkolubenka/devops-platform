"""add service action jobs

Revision ID: 20260329_02
Revises: 20260329_01
Create Date: 2026-03-29 01:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260329_02"
down_revision = "20260329_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS service_action_jobs (
                id SERIAL PRIMARY KEY,
                service_id INTEGER NOT NULL REFERENCES services(id),
                action VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                requested_by VARCHAR(100) DEFAULT 'portal',
                result_detail TEXT,
                error_detail TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS service_action_jobs"))
