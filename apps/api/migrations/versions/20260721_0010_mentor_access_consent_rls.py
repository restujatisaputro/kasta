"""Add scoped mentor consent, support grants, and PostgreSQL RLS.

Revision ID: 20260721_0010
Revises: 20260721_0009
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0010"
down_revision: str | None = "20260721_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
NEW_MENTOR_READ_PERMISSIONS = (
    "product.read",
    "receivable.read",
    "payable.read",
)

TABLE_SCOPES: dict[str, tuple[str, ...]] = {
    "business_profiles": ("SUMMARY",),
    "accounts": ("SUMMARY", "REPORTS"),
    "journal_entries": ("SUMMARY", "REPORTS"),
    "journal_lines": ("SUMMARY", "REPORTS"),
    "transactions": ("SUMMARY", "REPORTS", "TRANSACTIONS"),
    "transaction_items": ("REPORTS", "TRANSACTIONS", "INVENTORY"),
    "transaction_revisions": ("TRANSACTIONS",),
    "transaction_drafts": ("TRANSACTIONS",),
    "recurring_transactions": ("TRANSACTIONS",),
    "transaction_sync_logs": ("TRANSACTIONS",),
    "receipts": ("REPORTS", "RECEIPTS"),
    "receipt_images": ("RECEIPTS",),
    "receipt_items": ("RECEIPTS",),
    "receipt_corrections": ("RECEIPTS",),
    "ocr_results": ("RECEIPTS",),
    "ocr_fields": ("RECEIPTS",),
    "products": ("REPORTS", "INVENTORY"),
    "stock_movements": ("INVENTORY",),
    "customers": ("SUMMARY", "REPORTS", "OBLIGATIONS"),
    "suppliers": ("SUMMARY", "REPORTS", "OBLIGATIONS"),
    "receivables": ("SUMMARY", "REPORTS", "OBLIGATIONS"),
    "receivable_payments": ("SUMMARY", "REPORTS", "OBLIGATIONS"),
    "payables": ("SUMMARY", "REPORTS", "OBLIGATIONS"),
    "payable_payments": ("SUMMARY", "REPORTS", "OBLIGATIONS"),
}

MENTOR_ACTIVITY_TABLES = ("mentor_notes", "recommendations", "mentoring_sessions")


def _id(prefix: str, code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"{prefix}:{code}")


def _scope_array(scopes: tuple[str, ...]) -> str:
    values = ", ".join(f"'{scope}'" for scope in scopes)
    return f"ARRAY[{values}]::text[]"


def upgrade() -> None:
    op.drop_constraint(
        "uq_mentor_business_access_mentor_id",
        "mentor_business_access",
        type_="unique",
    )
    op.drop_constraint(
        "mentor_access_status",
        "mentor_business_access",
        type_="check",
    )
    op.drop_index("ix_mentor_business_access_active", table_name="mentor_business_access")

    op.add_column(
        "mentor_business_access", sa.Column("requested_by_user_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "mentor_business_access", sa.Column("granted_by_user_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "mentor_business_access",
        sa.Column(
            "scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "mentor_business_access", sa.Column("request_message", sa.String(500), nullable=True)
    )
    op.add_column(
        "mentor_business_access",
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "mentor_business_access", sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "mentor_business_access", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "mentor_business_access", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "mentor_business_access", sa.Column("rejection_reason", sa.String(500), nullable=True)
    )
    op.add_column(
        "mentor_business_access", sa.Column("revocation_reason", sa.String(500), nullable=True)
    )
    op.add_column(
        "mentor_business_access",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "mentor_business_access",
        sa.Column("revision_no", sa.Integer(), server_default="1", nullable=False),
    )

    op.execute(
        """
        UPDATE mentor_business_access AS access
           SET requested_by_user_id = mentor.user_id,
               granted_by_user_id = COALESCE(
                   (
                       SELECT member.user_id
                         FROM business_members AS member
                         JOIN roles AS role ON role.id = member.role_id
                        WHERE member.business_id = access.business_id
                          AND member.status = 'ACTIVE'
                          AND member.deleted_at IS NULL
                          AND role.code = 'business_owner'
                        ORDER BY member.created_at
                        LIMIT 1
                   ),
                   mentor.user_id
               ),
               requested_at = access.created_at,
               granted_at = access.created_at,
               revoked_at = CASE
                   WHEN access.status = 'REVOKED'
                   THEN COALESCE(access.updated_at, access.created_at)
                   ELSE NULL
               END,
               scope = (
                   CASE WHEN access.can_view_summary THEN '["SUMMARY", "REPORTS"]'::jsonb
                        ELSE '[]'::jsonb END
                   || CASE WHEN access.can_view_transactions THEN '["TRANSACTIONS"]'::jsonb
                           ELSE '[]'::jsonb END
                   || '["RECEIPTS", "INVENTORY", "OBLIGATIONS", "EXPORT_REPORTS"]'::jsonb
               )
          FROM mentors AS mentor
         WHERE mentor.id = access.mentor_id
        """
    )
    op.alter_column("mentor_business_access", "requested_by_user_id", nullable=False)
    op.alter_column("mentor_business_access", "requested_at", nullable=False)
    op.create_foreign_key(
        "fk_mentor_business_access_requested_by_user_id_users",
        "mentor_business_access",
        "users",
        ["requested_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_mentor_business_access_granted_by_user_id_users",
        "mentor_business_access",
        "users",
        ["granted_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("mentor_business_access", "can_create_notes")
    op.drop_column("mentor_business_access", "can_view_transactions")
    op.drop_column("mentor_business_access", "can_view_summary")

    op.create_check_constraint(
        "mentor_access_status",
        "mentor_business_access",
        "status IN ('REQUESTED', 'ACTIVE', 'REJECTED', 'REVOKED', 'EXPIRED')",
    )
    op.create_check_constraint(
        "mentor_access_revision", "mentor_business_access", "revision_no > 0"
    )
    op.create_check_constraint(
        "mentor_access_grant",
        "mentor_business_access",
        "status <> 'ACTIVE' OR (granted_by_user_id IS NOT NULL AND granted_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "mentor_access_validity",
        "mentor_business_access",
        "expires_at IS NULL OR expires_at > COALESCE(granted_at, requested_at)",
    )
    op.create_check_constraint(
        "mentor_access_revoked",
        "mentor_business_access",
        "status <> 'REVOKED' OR revoked_at IS NOT NULL",
    )
    op.create_index(
        "uq_mentor_business_access_open",
        "mentor_business_access",
        ["mentor_id", "business_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('REQUESTED', 'ACTIVE') AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_mentor_business_access_active",
        "mentor_business_access",
        ["mentor_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_mentor_business_access_business_status",
        "mentor_business_access",
        ["business_id", "status"],
    )
    op.create_index(
        "ix_mentor_business_access_requested_by_user_id",
        "mentor_business_access",
        ["requested_by_user_id"],
    )
    op.create_index(
        "ix_mentor_business_access_granted_by_user_id",
        "mentor_business_access",
        ["granted_by_user_id"],
    )
    op.create_index(
        "ix_mentor_business_access_expires_at",
        "mentor_business_access",
        ["expires_at"],
    )

    op.create_table(
        "support_access_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "admin_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "granted_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("ticket_reference", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED', 'EXPIRED')", name="support_access_status"
        ),
        sa.CheckConstraint("expires_at > granted_at", name="support_access_validity"),
        sa.CheckConstraint(
            "status <> 'REVOKED' OR revoked_at IS NOT NULL", name="support_access_revoked"
        ),
    )
    op.create_index(
        "ix_support_access_grants_business_id", "support_access_grants", ["business_id"]
    )
    op.create_index(
        "ix_support_access_grants_admin_user_id", "support_access_grants", ["admin_user_id"]
    )
    op.create_index(
        "ix_support_access_grants_granted_by_user_id",
        "support_access_grants",
        ["granted_by_user_id"],
    )
    op.create_index(
        "ix_support_access_admin_active",
        "support_access_grants",
        ["admin_user_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_support_access_business_active",
        "support_access_grants",
        ["business_id", "status", "expires_at"],
    )

    for permission in NEW_MENTOR_READ_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO role_permissions (id, role_id, permission_id) "
                "VALUES (:id, :role_id, :permission_id) ON CONFLICT DO NOTHING"
            ).bindparams(
                id=_id("role-permission", f"mentor:{permission}"),
                role_id=_id("role", "mentor"),
                permission_id=_id("permission", permission),
            )
        )

    _create_rls_functions()
    _create_rls_policies()


def _create_rls_functions() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_context_uuid(setting_name text)
        RETURNS uuid LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting(setting_name, true), '')::uuid
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_actor_type()
        RETURNS text LANGUAGE sql STABLE AS $$
            SELECT COALESCE(NULLIF(current_setting('app.actor_type', true), ''), 'NONE')
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_is_business_actor(target_business_id uuid)
        RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            SELECT kasta_actor_type() = 'BUSINESS'
               AND kasta_context_uuid('app.business_id') = target_business_id
               AND EXISTS (
                   SELECT 1
                     FROM business_members AS member
                    WHERE member.business_id = target_business_id
                      AND member.user_id = kasta_context_uuid('app.user_id')
                      AND member.status = 'ACTIVE'
                      AND member.deleted_at IS NULL
               )
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_has_mentor_scope(
            target_business_id uuid,
            required_scopes text[]
        ) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            SELECT EXISTS (
                SELECT 1
                  FROM mentor_business_access AS access
                 WHERE access.business_id = target_business_id
                   AND access.mentor_id = kasta_context_uuid('app.mentor_id')
                   AND access.status = 'ACTIVE'
                   AND access.deleted_at IS NULL
                   AND (access.expires_at IS NULL OR access.expires_at > now())
                   AND access.scope ?| required_scopes
            )
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_has_support_scope(
            target_business_id uuid,
            required_scopes text[]
        ) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            SELECT kasta_actor_type() = 'SUPPORT' AND EXISTS (
                SELECT 1
                  FROM support_access_grants AS support
                 WHERE support.id = kasta_context_uuid('app.support_grant_id')
                   AND support.business_id = target_business_id
                   AND support.admin_user_id = kasta_context_uuid('app.user_id')
                   AND support.status = 'ACTIVE'
                   AND support.expires_at > now()
                   AND support.scope ?| required_scopes
            )
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_is_own_mentor_request(
            target_business_id uuid,
            target_access_id uuid
        ) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            SELECT EXISTS (
                SELECT 1
                  FROM mentor_business_access AS access
                 WHERE access.id = target_access_id
                   AND access.business_id = target_business_id
                   AND access.mentor_id = kasta_context_uuid('app.mentor_id')
                   AND access.requested_by_user_id = kasta_context_uuid('app.user_id')
                   AND access.status = 'REQUESTED'
            )
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_touch_mentor_access(target_business_id uuid)
        RETURNS void LANGUAGE sql VOLATILE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            UPDATE mentor_business_access
               SET last_accessed_at = now(), updated_at = now()
             WHERE business_id = target_business_id
               AND mentor_id = kasta_context_uuid('app.mentor_id')
               AND status = 'ACTIVE'
               AND deleted_at IS NULL
               AND (expires_at IS NULL OR expires_at > now())
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_touch_support_access(target_business_id uuid)
        RETURNS void LANGUAGE sql VOLATILE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            UPDATE support_access_grants
               SET last_accessed_at = now(), updated_at = now()
             WHERE id = kasta_context_uuid('app.support_grant_id')
               AND business_id = target_business_id
               AND admin_user_id = kasta_context_uuid('app.user_id')
               AND status = 'ACTIVE'
               AND expires_at > now()
        $$
        """
    )


def _create_rls_policies() -> None:
    for table_name, scopes in TABLE_SCOPES.items():
        scope_array = _scope_array(scopes)
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table_name}_business_all ON {table_name} FOR ALL "
            "USING (kasta_is_business_actor(business_id)) "
            "WITH CHECK (kasta_is_business_actor(business_id))"
        )
        op.execute(
            f"CREATE POLICY {table_name}_mentor_read ON {table_name} FOR SELECT "
            f"USING (kasta_has_mentor_scope(business_id, {scope_array}))"
        )
        op.execute(
            f"CREATE POLICY {table_name}_support_read ON {table_name} FOR SELECT "
            f"USING (kasta_has_support_scope(business_id, {scope_array}))"
        )

    op.execute("ALTER TABLE mentor_business_access ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY mentor_access_business_read ON mentor_business_access FOR SELECT
        USING (kasta_is_business_actor(business_id))
        """
    )
    op.execute(
        """
        CREATE POLICY mentor_access_business_update ON mentor_business_access FOR UPDATE
        USING (kasta_is_business_actor(business_id))
        WITH CHECK (kasta_is_business_actor(business_id))
        """
    )
    op.execute(
        """
        CREATE POLICY mentor_access_mentor_read ON mentor_business_access FOR SELECT
        USING (mentor_id = kasta_context_uuid('app.mentor_id'))
        """
    )
    op.execute(
        """
        CREATE POLICY mentor_access_mentor_request ON mentor_business_access FOR INSERT
        WITH CHECK (
            mentor_id = kasta_context_uuid('app.mentor_id')
            AND requested_by_user_id = kasta_context_uuid('app.user_id')
            AND status = 'REQUESTED'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY mentor_access_support_read ON mentor_business_access FOR SELECT
        USING (kasta_has_support_scope(business_id, ARRAY['ACCESS_MANAGEMENT']::text[]))
        """
    )

    for table_name in MENTOR_ACTIVITY_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table_name}_business_read ON {table_name} FOR SELECT "
            "USING (kasta_is_business_actor(business_id))"
        )
        op.execute(
            f"CREATE POLICY {table_name}_mentor_all ON {table_name} FOR ALL "
            "USING (mentor_id = kasta_context_uuid('app.mentor_id') "
            "AND kasta_has_mentor_scope(business_id, ARRAY['SUMMARY']::text[])) "
            "WITH CHECK (mentor_id = kasta_context_uuid('app.mentor_id') "
            "AND kasta_has_mentor_scope(business_id, ARRAY['SUMMARY']::text[]))"
        )
        op.execute(
            f"CREATE POLICY {table_name}_support_read ON {table_name} FOR SELECT "
            "USING (kasta_has_support_scope(business_id, ARRAY['SUMMARY']::text[]))"
        )

    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY audit_business_read ON audit_logs FOR SELECT "
        "USING (kasta_is_business_actor(business_id))"
    )
    op.execute(
        "CREATE POLICY audit_business_insert ON audit_logs FOR INSERT "
        "WITH CHECK (kasta_is_business_actor(business_id) "
        "AND actor_user_id = kasta_context_uuid('app.user_id'))"
    )
    op.execute(
        "CREATE POLICY audit_mentor_read ON audit_logs FOR SELECT "
        "USING (actor_user_id = kasta_context_uuid('app.user_id') "
        "AND kasta_has_mentor_scope(business_id, ARRAY['SUMMARY', 'REPORTS', "
        "'TRANSACTIONS', 'RECEIPTS', 'INVENTORY', 'OBLIGATIONS', "
        "'EXPORT_REPORTS']::text[]))"
    )
    op.execute(
        "CREATE POLICY audit_mentor_insert ON audit_logs FOR INSERT "
        "WITH CHECK (actor_user_id = kasta_context_uuid('app.user_id') "
        "AND (kasta_has_mentor_scope(business_id, ARRAY['SUMMARY', 'REPORTS', "
        "'TRANSACTIONS', 'RECEIPTS', 'INVENTORY', 'OBLIGATIONS', "
        "'EXPORT_REPORTS']::text[]) "
        "OR (entity_type = 'MENTOR_ACCESS' AND action = 'MENTOR_ACCESS_REQUESTED' "
        "AND kasta_is_own_mentor_request(business_id, entity_id))))"
    )
    op.execute(
        "CREATE POLICY audit_support_insert ON audit_logs FOR INSERT "
        "WITH CHECK (actor_user_id = kasta_context_uuid('app.user_id') "
        "AND kasta_has_support_scope(business_id, ARRAY['SUMMARY', 'REPORTS', "
        "'TRANSACTIONS', 'RECEIPTS', 'INVENTORY', 'OBLIGATIONS', "
        "'EXPORT_REPORTS']::text[]))"
    )

    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY notifications_business_all ON notifications FOR ALL "
        "USING (kasta_is_business_actor(business_id)) "
        "WITH CHECK (kasta_is_business_actor(business_id))"
    )
    op.execute(
        "CREATE POLICY notifications_mentor_insert ON notifications FOR INSERT "
        "WITH CHECK (kasta_has_mentor_scope(business_id, ARRAY['SUMMARY']::text[]) "
        "OR (notification_type = 'MENTOR_ACCESS_REQUEST' "
        "AND kasta_is_own_mentor_request(business_id, entity_id)))"
    )

    op.execute("ALTER TABLE support_access_grants ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY support_grant_business_read ON support_access_grants FOR SELECT "
        "USING (kasta_is_business_actor(business_id))"
    )
    op.execute(
        "CREATE POLICY support_grant_admin_read ON support_access_grants FOR SELECT "
        "USING (admin_user_id = kasta_context_uuid('app.user_id'))"
    )


def downgrade() -> None:
    rls_tables = (
        *TABLE_SCOPES.keys(),
        "mentor_business_access",
        *MENTOR_ACTIVITY_TABLES,
        "audit_logs",
        "notifications",
        "support_access_grants",
    )
    for table_name in rls_tables:
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP FUNCTION IF EXISTS kasta_has_support_scope(uuid, text[]) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS kasta_touch_support_access(uuid)")
    op.execute("DROP FUNCTION IF EXISTS kasta_touch_mentor_access(uuid)")
    op.execute("DROP FUNCTION IF EXISTS kasta_is_own_mentor_request(uuid, uuid) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS kasta_has_mentor_scope(uuid, text[]) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS kasta_is_business_actor(uuid) CASCADE")
    op.execute("DROP FUNCTION IF EXISTS kasta_actor_type() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS kasta_context_uuid(text) CASCADE")

    links = sa.table("role_permissions", sa.column("id", sa.Uuid()))
    op.execute(
        links.delete().where(
            links.c.id.in_(
                [_id("role-permission", f"mentor:{code}") for code in NEW_MENTOR_READ_PERMISSIONS]
            )
        )
    )
    op.drop_table("support_access_grants")

    op.add_column(
        "mentor_business_access",
        sa.Column("can_view_summary", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "mentor_business_access",
        sa.Column("can_view_transactions", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "mentor_business_access",
        sa.Column("can_create_notes", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.execute(
        "UPDATE mentor_business_access SET "
        "can_view_summary = scope ? 'SUMMARY', "
        "can_view_transactions = scope ? 'TRANSACTIONS'"
    )
    op.execute(
        """
        DELETE FROM mentor_business_access AS older
         USING mentor_business_access AS newer
         WHERE older.mentor_id = newer.mentor_id
           AND older.business_id = newer.business_id
           AND (older.created_at, older.id) < (newer.created_at, newer.id)
        """
    )

    op.drop_index("ix_mentor_business_access_expires_at", table_name="mentor_business_access")
    op.drop_index(
        "ix_mentor_business_access_granted_by_user_id", table_name="mentor_business_access"
    )
    op.drop_index(
        "ix_mentor_business_access_requested_by_user_id", table_name="mentor_business_access"
    )
    op.drop_index("ix_mentor_business_access_business_status", table_name="mentor_business_access")
    op.drop_index("ix_mentor_business_access_active", table_name="mentor_business_access")
    op.drop_index("uq_mentor_business_access_open", table_name="mentor_business_access")
    for constraint_name in (
        "mentor_access_revoked",
        "mentor_access_validity",
        "mentor_access_grant",
        "mentor_access_revision",
        "mentor_access_status",
    ):
        op.drop_constraint(
            constraint_name,
            "mentor_business_access",
            type_="check",
        )
    op.drop_constraint(
        "fk_mentor_business_access_granted_by_user_id_users",
        "mentor_business_access",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_mentor_business_access_requested_by_user_id_users",
        "mentor_business_access",
        type_="foreignkey",
    )
    for column_name in (
        "revision_no",
        "last_accessed_at",
        "revocation_reason",
        "rejection_reason",
        "revoked_at",
        "expires_at",
        "granted_at",
        "requested_at",
        "request_message",
        "scope",
        "granted_by_user_id",
        "requested_by_user_id",
    ):
        op.drop_column("mentor_business_access", column_name)
    op.execute(
        "UPDATE mentor_business_access SET status = CASE "
        "WHEN status = 'ACTIVE' THEN 'ACTIVE' ELSE 'REVOKED' END"
    )
    op.create_check_constraint(
        "mentor_access_status",
        "mentor_business_access",
        "status IN ('ACTIVE', 'REVOKED')",
    )
    op.create_unique_constraint(
        "uq_mentor_business_access_mentor_id",
        "mentor_business_access",
        ["mentor_id", "business_id"],
    )
    op.create_index(
        "ix_mentor_business_access_active",
        "mentor_business_access",
        ["mentor_id", "business_id", "status"],
    )
