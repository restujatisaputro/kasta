#!/usr/bin/env sh
set -eu

: "${POSTGRES_RESTORE_URL:?POSTGRES_RESTORE_URL is required}"

database_name="$(psql "${POSTGRES_RESTORE_URL}" -Atc 'SELECT current_database()')"
case "${database_name}" in
  *_restore_test) ;;
  *)
    printf '%s\n' "Refusing verification outside a *_restore_test database: ${database_name}" >&2
    exit 2
    ;;
esac

psql "${POSTGRES_RESTORE_URL}" --set=ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE
    invalid_count bigint;
BEGIN
    IF (SELECT count(*) FROM alembic_version) <> 1 THEN
        RAISE EXCEPTION 'Restore must contain exactly one active Alembic revision';
    END IF;

    SELECT count(*) INTO invalid_count
    FROM journal_entries
    WHERE total_debit <> total_credit OR total_debit <= 0;
    IF invalid_count <> 0 THEN
        RAISE EXCEPTION 'Restore contains % invalid journal headers', invalid_count;
    END IF;

    SELECT count(*) INTO invalid_count
    FROM (
        SELECT entry.id
        FROM journal_entries AS entry
        LEFT JOIN journal_lines AS line ON line.journal_entry_id = entry.id
        GROUP BY entry.id, entry.total_debit, entry.total_credit
        HAVING count(line.id) < 2
            OR coalesce(sum(line.debit_amount), 0) <> coalesce(sum(line.credit_amount), 0)
            OR coalesce(sum(line.debit_amount), 0) <> entry.total_debit
            OR coalesce(sum(line.credit_amount), 0) <> entry.total_credit
    ) AS invalid_entries;
    IF invalid_count <> 0 THEN
        RAISE EXCEPTION 'Restore contains % journals whose lines do not balance', invalid_count;
    END IF;

    SELECT count(*) INTO invalid_count
    FROM transactions AS txn
    LEFT JOIN journal_entries AS entry
      ON entry.transaction_id = txn.id
     AND entry.business_id = txn.business_id
    WHERE entry.id IS NULL;
    IF invalid_count <> 0 THEN
        RAISE EXCEPTION 'Restore contains % financial transactions without a journal', invalid_count;
    END IF;
END
$$;
SQL

printf '%s\n' "PASS: PostgreSQL restore integrity verified in ${database_name}"
