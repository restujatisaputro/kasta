#!/usr/bin/env sh
set -eu

backup_file="${1:?Usage: restore-drill.sh <backup.dump.age>}"
script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"

"${script_dir}/restore-postgres.sh" "${backup_file}"
"${script_dir}/verify-postgres-restore.sh"

if [ "${RUN_RESTORE_RLS_TEST:-false}" = "true" ]; then
  repository_root="$(CDPATH='' cd -- "${script_dir}/../.." && pwd)"
  psql "${POSTGRES_RESTORE_URL}" --set=ON_ERROR_STOP=1 \
    --file="${repository_root}/scripts/postgres/test-rls.sql"
fi

printf '%s\n' 'PASS: encrypted PostgreSQL backup restore drill completed'
