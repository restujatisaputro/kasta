"""Add the posting engine, immutable revisions, and audit trail.

Revision ID: 20260721_0004
Revises: 20260721_0003
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0004"
down_revision: str | None = "20260721_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
REVERSE_PERMISSION = "transaction.reverse"
REVERSE_ROLES = ("business_owner", "business_staff", "super_admin")


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.add_column("accounts", sa.Column("system_key", sa.String(50)))
    op.add_column("accounts", sa.Column("normal_balance", sa.String(10)))
    op.add_column(
        "accounts",
        sa.Column("is_system", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute(
        sa.text(
            "UPDATE accounts SET system_key = CASE code "
            "WHEN '1101' THEN 'CASH' WHEN '1102' THEN 'BANK' "
            "WHEN '3101' THEN 'OWNER_CAPITAL' ELSE NULL END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE accounts SET normal_balance = CASE "
            "WHEN account_type = 'ASSET' THEN 'DEBIT' ELSE 'CREDIT' END, "
            "is_system = CASE WHEN system_key IS NOT NULL THEN true ELSE false END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE accounts SET name = CASE code "
            "WHEN '1101' THEN 'Kas' WHEN '1102' THEN 'Bank' "
            "WHEN '3101' THEN 'Modal Pemilik' ELSE name END"
        )
    )
    op.alter_column("accounts", "normal_balance", nullable=False)
    op.drop_constraint(op.f("ck_accounts_account_type"), "accounts", type_="check")
    op.create_check_constraint(
        "account_type",
        "accounts",
        "account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')",
    )
    op.create_check_constraint(
        "account_normal_balance",
        "accounts",
        "normal_balance IN ('DEBIT', 'CREDIT')",
    )
    op.create_unique_constraint(
        "uq_accounts_business_system_key", "accounts", ["business_id", "system_key"]
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("transaction_number", sa.String(50), nullable=False),
        sa.Column("transaction_type", sa.String(40), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("payment_account_key", sa.String(50)),
        sa.Column("category_account_key", sa.String(50)),
        sa.Column("status", sa.String(20), server_default="POSTED", nullable=False),
        sa.Column("idempotency_key", sa.String(100)),
        sa.Column(
            "root_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "supersedes_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "reverses_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "reversed_by_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "posted_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "transaction_type IN ('CASH_SALE', 'NON_CASH_SALE', 'CREDIT_SALE', "
            "'CASH_PURCHASE', 'CREDIT_PURCHASE', 'CAPITAL_CONTRIBUTION', 'OWNER_DRAW', "
            "'PAYABLE_PAYMENT', 'RECEIVABLE_RECEIPT', 'OPERATING_EXPENSE', 'REVERSAL')",
            name="financial_transaction_type",
        ),
        sa.CheckConstraint("status IN ('POSTED', 'REVERSED')", name="financial_transaction_status"),
        sa.CheckConstraint("amount > 0", name="financial_transaction_positive_amount"),
        sa.CheckConstraint("revision_number >= 1", name="financial_transaction_revision_number"),
        sa.UniqueConstraint(
            "business_id", "transaction_number", name="uq_transactions_business_number"
        ),
        sa.UniqueConstraint(
            "business_id", "idempotency_key", name="uq_transactions_business_idempotency"
        ),
        sa.UniqueConstraint(
            "reverses_transaction_id", name="uq_transactions_reverses_transaction_id"
        ),
        sa.UniqueConstraint(
            "supersedes_transaction_id", name="uq_transactions_supersedes_transaction_id"
        ),
    )
    op.create_index("ix_transactions_business_id", "transactions", ["business_id"])
    op.create_index("ix_transactions_posted_by_user_id", "transactions", ["posted_by_user_id"])
    op.create_index(
        "ix_transactions_business_date", "transactions", ["business_id", "transaction_date"]
    )

    op.add_column("journal_entries", sa.Column("transaction_id", sa.Uuid()))
    op.add_column("journal_entries", sa.Column("reversal_of_entry_id", sa.Uuid()))
    op.add_column("journal_entries", sa.Column("reversed_by_entry_id", sa.Uuid()))
    op.add_column("journal_entries", sa.Column("posted_by_user_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_journal_entries_transaction_id_transactions",
        "journal_entries",
        "transactions",
        ["transaction_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_journal_entries_reversal_of_entry_id_journal_entries",
        "journal_entries",
        "journal_entries",
        ["reversal_of_entry_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_journal_entries_reversed_by_entry_id_journal_entries",
        "journal_entries",
        "journal_entries",
        ["reversed_by_entry_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_journal_entries_posted_by_user_id_users",
        "journal_entries",
        "users",
        ["posted_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_journal_entries_transaction_id", "journal_entries", ["transaction_id"]
    )
    op.create_unique_constraint(
        "uq_journal_entries_reversal_of_entry_id",
        "journal_entries",
        ["reversal_of_entry_id"],
    )
    op.create_index("ix_journal_entries_transaction_id", "journal_entries", ["transaction_id"])
    op.create_index(
        "ix_journal_entries_posted_by_user_id", "journal_entries", ["posted_by_user_id"]
    )

    op.create_table(
        "transaction_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "related_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("event_sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number >= 1", name="transaction_revision_number"),
        sa.CheckConstraint("event_sequence >= 1", name="transaction_event_sequence"),
        sa.CheckConstraint(
            "event_type IN ('POSTED', 'REVERSED', 'REVISED')",
            name="transaction_revision_event_type",
        ),
        sa.UniqueConstraint(
            "transaction_id", "event_sequence", name="uq_transaction_revisions_transaction_id"
        ),
    )
    op.create_index(
        "ix_transaction_revisions_business_id", "transaction_revisions", ["business_id"]
    )
    op.create_index(
        "ix_transaction_revisions_transaction_id", "transaction_revisions", ["transaction_id"]
    )
    op.create_index(
        "ix_transaction_revisions_actor_user_id", "transaction_revisions", ["actor_user_id"]
    )
    op.create_index(
        "ix_transaction_revisions_business_transaction",
        "transaction_revisions",
        ["business_id", "transaction_id"],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("before_data", sa.JSON()),
        sa.Column("after_data", sa.JSON()),
        sa.Column("reason", sa.String(500)),
        sa.Column("request_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_business_id", "audit_logs", ["business_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index(
        "ix_audit_logs_business_entity",
        "audit_logs",
        ["business_id", "entity_type", "entity_id"],
    )
    op.create_index("ix_audit_logs_business_created", "audit_logs", ["business_id", "created_at"])

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        permissions,
        [
            {
                "id": uuid5(AUTH_NAMESPACE, f"permission:{REVERSE_PERMISSION}"),
                "code": REVERSE_PERMISSION,
                "module": "transaction",
                "description": REVERSE_PERMISSION,
            }
        ],
    )
    op.bulk_insert(
        role_permissions,
        [
            {
                "id": uuid5(
                    AUTH_NAMESPACE,
                    f"role-permission:{role}:{REVERSE_PERMISSION}",
                ),
                "role_id": uuid5(AUTH_NAMESPACE, f"role:{role}"),
                "permission_id": uuid5(AUTH_NAMESPACE, f"permission:{REVERSE_PERMISSION}"),
            }
            for role in REVERSE_ROLES
        ],
    )

    op.execute(
        """
        CREATE FUNCTION kasta_reject_financial_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Posted financial records cannot be deleted; use reversal';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in (
        "transactions",
        "journal_entries",
        "journal_lines",
        "transaction_revisions",
        "audit_logs",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete "
            f"BEFORE DELETE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_financial_delete()"
        )
    op.execute(
        """
        CREATE FUNCTION kasta_reject_immutable_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Immutable financial history cannot be changed';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in ("journal_lines", "transaction_revisions", "audit_logs"):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update "
            f"BEFORE UPDATE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_immutable_update()"
        )
    op.execute(
        """
        CREATE FUNCTION kasta_guard_posted_record_update() RETURNS trigger AS $$
        BEGIN
            IF TG_TABLE_NAME = 'transactions' THEN
                IF (to_jsonb(NEW) - 'status' - 'reversed_by_transaction_id' - 'updated_at')
                   IS DISTINCT FROM
                   (to_jsonb(OLD) - 'status' - 'reversed_by_transaction_id' - 'updated_at') THEN
                    RAISE EXCEPTION 'Posted transaction content is immutable; use revision';
                END IF;
                IF NEW.status IS DISTINCT FROM OLD.status
                   AND NOT (OLD.status = 'POSTED' AND NEW.status = 'REVERSED') THEN
                    RAISE EXCEPTION 'Invalid transaction status transition';
                END IF;
            ELSIF TG_TABLE_NAME = 'journal_entries' THEN
                IF (to_jsonb(NEW) - 'status' - 'reversed_by_entry_id' - 'updated_at')
                   IS DISTINCT FROM
                   (to_jsonb(OLD) - 'status' - 'reversed_by_entry_id' - 'updated_at') THEN
                    RAISE EXCEPTION 'Posted journal content is immutable; use reversal';
                END IF;
                IF NEW.status IS DISTINCT FROM OLD.status
                   AND NOT (OLD.status = 'POSTED' AND NEW.status = 'REVERSED') THEN
                    RAISE EXCEPTION 'Invalid journal status transition';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_transactions_guard_update
        BEFORE UPDATE ON transactions FOR EACH ROW
        EXECUTE FUNCTION kasta_guard_posted_record_update()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entries_guard_update
        BEFORE UPDATE ON journal_entries FOR EACH ROW
        EXECUTE FUNCTION kasta_guard_posted_record_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION kasta_validate_balanced_journal() RETURNS trigger AS $$
        DECLARE
            target_entry_id uuid;
            expected_debit numeric(18, 2);
            expected_credit numeric(18, 2);
            actual_debit numeric(18, 2);
            actual_credit numeric(18, 2);
            line_count integer;
        BEGIN
            IF TG_TABLE_NAME = 'journal_entries' THEN
                target_entry_id := NEW.id;
            ELSIF TG_OP = 'DELETE' THEN
                target_entry_id := OLD.journal_entry_id;
            ELSE
                target_entry_id := NEW.journal_entry_id;
            END IF;

            SELECT total_debit, total_credit
              INTO expected_debit, expected_credit
              FROM journal_entries
             WHERE id = target_entry_id;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;

            SELECT count(*),
                   coalesce(sum(debit_amount), 0),
                   coalesce(sum(credit_amount), 0)
              INTO line_count, actual_debit, actual_credit
              FROM journal_lines
             WHERE journal_entry_id = target_entry_id;

            IF line_count < 2
               OR actual_debit <= 0
               OR actual_debit <> actual_credit
               OR actual_debit <> expected_debit
               OR actual_credit <> expected_credit THEN
                RAISE EXCEPTION 'Journal % is not balanced or does not match its lines',
                    target_entry_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_journal_entries_balanced
        AFTER INSERT OR UPDATE OF total_debit, total_credit ON journal_entries
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION kasta_validate_balanced_journal()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_journal_lines_balanced
        AFTER INSERT OR UPDATE OR DELETE ON journal_lines
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION kasta_validate_balanced_journal()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_journal_lines_balanced ON journal_lines")
    op.execute("DROP TRIGGER IF EXISTS trg_journal_entries_balanced ON journal_entries")
    op.execute("DROP FUNCTION IF EXISTS kasta_validate_balanced_journal()")
    op.execute("DROP TRIGGER IF EXISTS trg_journal_entries_guard_update ON journal_entries")
    op.execute("DROP TRIGGER IF EXISTS trg_transactions_guard_update ON transactions")
    op.execute("DROP FUNCTION IF EXISTS kasta_guard_posted_record_update()")
    for table_name in ("journal_lines", "transaction_revisions", "audit_logs"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update ON {table_name}")
    for table_name in (
        "transactions",
        "journal_entries",
        "journal_lines",
        "transaction_revisions",
        "audit_logs",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS kasta_reject_immutable_update()")
    op.execute("DROP FUNCTION IF EXISTS kasta_reject_financial_delete()")

    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id = "
            f"'{uuid5(AUTH_NAMESPACE, f'permission:{REVERSE_PERMISSION}')}'"
        )
    )
    op.execute(sa.text(f"DELETE FROM permissions WHERE code = '{REVERSE_PERMISSION}'"))

    op.drop_table("audit_logs")
    op.drop_table("transaction_revisions")
    op.drop_index("ix_journal_entries_posted_by_user_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_transaction_id", table_name="journal_entries")
    op.drop_constraint("uq_journal_entries_reversal_of_entry_id", "journal_entries", type_="unique")
    op.drop_constraint("uq_journal_entries_transaction_id", "journal_entries", type_="unique")
    op.drop_constraint(
        "fk_journal_entries_posted_by_user_id_users", "journal_entries", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_journal_entries_reversed_by_entry_id_journal_entries",
        "journal_entries",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_journal_entries_reversal_of_entry_id_journal_entries",
        "journal_entries",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_journal_entries_transaction_id_transactions",
        "journal_entries",
        type_="foreignkey",
    )
    for column_name in (
        "posted_by_user_id",
        "reversed_by_entry_id",
        "reversal_of_entry_id",
        "transaction_id",
    ):
        op.drop_column("journal_entries", column_name)
    op.drop_table("transactions")

    op.drop_constraint("uq_accounts_business_system_key", "accounts", type_="unique")
    op.drop_constraint(op.f("ck_accounts_account_normal_balance"), "accounts", type_="check")
    op.drop_constraint(op.f("ck_accounts_account_type"), "accounts", type_="check")
    op.create_check_constraint(
        "account_type",
        "accounts",
        "account_type IN ('ASSET', 'EQUITY')",
    )
    op.drop_column("accounts", "is_system")
    op.drop_column("accounts", "normal_balance")
    op.drop_column("accounts", "system_key")
