#!/usr/bin/env sh
set -eu
umask 077

: "${POSTGRES_RESTORE_URL:?POSTGRES_RESTORE_URL is required}"
: "${BACKUP_AGE_IDENTITY:?BACKUP_AGE_IDENTITY is required}"

backup_file="${1:?Usage: restore-postgres.sh <backup.dump.age>}"
sha256sum --check "${backup_file}.sha256"
age --decrypt --identity "${BACKUP_AGE_IDENTITY}" "${backup_file}" \
  | pg_restore --dbname="${POSTGRES_RESTORE_URL}" --exit-on-error --single-transaction \
      --no-owner --no-privileges
printf '%s\n' "PostgreSQL restore completed from ${backup_file}"
