"""Add owner-managed support access grant RLS workflow.

Revision ID: 20260722_0012
Revises: 20260722_0011
Create Date: 2026-07-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260722_0012"
down_revision: str | None = "20260722_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_is_business_owner(target_business_id uuid)
        RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = public, pg_temp AS $$
            SELECT kasta_actor_type() = 'BUSINESS'
               AND kasta_context_uuid('app.business_id') = target_business_id
               AND EXISTS (
                   SELECT 1
                     FROM business_members AS member
                     JOIN roles AS role ON role.id = member.role_id
                    WHERE member.business_id = target_business_id
                      AND member.user_id = kasta_context_uuid('app.user_id')
                      AND member.status = 'ACTIVE'
                      AND member.deleted_at IS NULL
                      AND role.code = 'business_owner'
               )
        $$
        """
    )
    op.execute("DROP POLICY IF EXISTS support_grant_business_read ON support_access_grants")
    op.execute(
        """
        CREATE POLICY support_grant_owner_manage ON support_access_grants FOR ALL
        USING (kasta_is_business_owner(business_id))
        WITH CHECK (
            kasta_is_business_owner(business_id)
            AND granted_by_user_id = kasta_context_uuid('app.user_id')
        )
        """
    )
    op.execute("ALTER TABLE support_access_grants FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS support_grant_owner_manage ON support_access_grants")
    op.execute(
        """
        CREATE POLICY support_grant_business_read ON support_access_grants FOR SELECT
        USING (kasta_is_business_actor(business_id))
        """
    )
    op.execute("ALTER TABLE support_access_grants NO FORCE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS kasta_is_business_owner(uuid)")
