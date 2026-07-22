#!/usr/bin/env sh
set -eu
umask 077

: "${MINIO_RESTORE_ENDPOINT:?MINIO_RESTORE_ENDPOINT is required}"
: "${MINIO_RESTORE_ACCESS_KEY:?MINIO_RESTORE_ACCESS_KEY is required}"
: "${MINIO_RESTORE_SECRET_KEY:?MINIO_RESTORE_SECRET_KEY is required}"
: "${MINIO_RESTORE_BUCKET:?MINIO_RESTORE_BUCKET is required}"
: "${BACKUP_AGE_IDENTITY:?BACKUP_AGE_IDENTITY is required}"

backup_file="${1:?Usage: restore-minio.sh <backup.tar.age>}"
work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT INT TERM
sha256sum --check "${backup_file}.sha256"
age --decrypt --identity "${BACKUP_AGE_IDENTITY}" "${backup_file}" \
  | tar -C "${work_dir}" -xf -
mc alias set kasta-restore "${MINIO_RESTORE_ENDPOINT}" \
  "${MINIO_RESTORE_ACCESS_KEY}" "${MINIO_RESTORE_SECRET_KEY}"
mc mb --ignore-existing "kasta-restore/${MINIO_RESTORE_BUCKET}"
mc mirror --overwrite "${work_dir}/objects" "kasta-restore/${MINIO_RESTORE_BUCKET}"
printf '%s\n' "MinIO restore completed from ${backup_file}"
