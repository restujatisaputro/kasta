#!/usr/bin/env sh
set -eu
umask 077

: "${POSTGRES_BACKUP_URL:?POSTGRES_BACKUP_URL is required}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT is required}"

backup_dir="${BACKUP_DIRECTORY:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="${backup_dir}/kasta-postgres-${timestamp}.dump.age"
mkdir -p "${backup_dir}"

pg_dump --dbname="${POSTGRES_BACKUP_URL}" --format=custom --no-owner --no-privileges \
  | age --recipient "${BACKUP_AGE_RECIPIENT}" --output "${output}"
sha256sum "${output}" > "${output}.sha256"
printf '%s\n' "Encrypted PostgreSQL backup: ${output}"
