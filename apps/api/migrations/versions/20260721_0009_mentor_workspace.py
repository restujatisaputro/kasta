"""Add mentor workspace, follow-up, sessions, and permissions.

Revision ID: 20260721_0009
Revises: 20260721_0008
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0009"
down_revision: str | None = "20260721_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
PERMISSIONS = (
    "mentor.recommendation.manage",
    "mentor.session.manage",
    "mentor.report.export",
)
ROLE_PERMISSIONS = {
    "mentor": PERMISSIONS,
    "organization_admin": PERMISSIONS,
    "super_admin": PERMISSIONS,
}


def _id(prefix: str, code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"{prefix}:{code}")


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "mentor_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mentor_id",
            sa.Uuid(),
            sa.ForeignKey("mentors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(20), server_default="SHARED", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("visibility IN ('SHARED', 'PRIVATE')", name="mentor_note_visibility"),
    )
    op.create_index("ix_mentor_notes_business_id", "mentor_notes", ["business_id"])
    op.create_index("ix_mentor_notes_mentor_id", "mentor_notes", ["mentor_id"])
    op.create_index(
        "ix_mentor_notes_business_created", "mentor_notes", ["business_id", "created_at"]
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mentor_id",
            sa.Uuid(),
            sa.ForeignKey("mentors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), server_default="MEDIUM", nullable=False),
        sa.Column("status", sa.String(20), server_default="OPEN", nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("follow_up_note", sa.String(1000)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH')", name="recommendation_priority"),
        sa.CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED')",
            name="recommendation_status",
        ),
    )
    op.create_index("ix_recommendations_business_id", "recommendations", ["business_id"])
    op.create_index("ix_recommendations_mentor_id", "recommendations", ["mentor_id"])
    op.create_index(
        "ix_recommendations_business_status_due",
        "recommendations",
        ["business_id", "status", "due_date"],
    )
    op.create_index("ix_recommendations_mentor_status", "recommendations", ["mentor_id", "status"])

    op.create_table(
        "mentoring_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mentor_id",
            sa.Uuid(),
            sa.ForeignKey("mentors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("mode", sa.String(20), server_default="ONLINE", nullable=False),
        sa.Column("status", sa.String(20), server_default="SCHEDULED", nullable=False),
        sa.Column("topic", sa.String(300), nullable=False),
        sa.Column("location", sa.String(500)),
        sa.Column("outcome", sa.Text()),
        sa.Column("follow_up_date", sa.Date()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("mode IN ('ONSITE', 'ONLINE', 'PHONE')", name="mentoring_session_mode"),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')",
            name="mentoring_session_status",
        ),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480", name="mentoring_session_duration"
        ),
    )
    op.create_index("ix_mentoring_sessions_business_id", "mentoring_sessions", ["business_id"])
    op.create_index("ix_mentoring_sessions_mentor_id", "mentoring_sessions", ["mentor_id"])
    op.create_index(
        "ix_mentoring_sessions_mentor_schedule",
        "mentoring_sessions",
        ["mentor_id", "status", "scheduled_at"],
    )
    op.create_index(
        "ix_mentoring_sessions_business_schedule",
        "mentoring_sessions",
        ["business_id", "scheduled_at"],
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
    )
    links = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        permissions,
        [
            {
                "id": _id("permission", code),
                "code": code,
                "module": "mentor",
                "description": code,
            }
            for code in PERMISSIONS
        ],
    )
    op.bulk_insert(
        links,
        [
            {
                "id": _id("role-permission", f"{role}:{permission}"),
                "role_id": _id("role", role),
                "permission_id": _id("permission", permission),
            }
            for role, values in ROLE_PERMISSIONS.items()
            for permission in values
        ],
    )


def downgrade() -> None:
    links = sa.table("role_permissions", sa.column("id", sa.Uuid()))
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()))
    link_ids = [
        _id("role-permission", f"{role}:{permission}")
        for role, values in ROLE_PERMISSIONS.items()
        for permission in values
    ]
    op.execute(links.delete().where(links.c.id.in_(link_ids)))
    op.execute(
        permissions.delete().where(
            permissions.c.id.in_([_id("permission", code) for code in PERMISSIONS])
        )
    )
    op.drop_table("mentoring_sessions")
    op.drop_table("recommendations")
    op.drop_table("mentor_notes")
