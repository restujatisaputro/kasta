#!/usr/bin/env sh
set -eu
umask 077

: "${MINIO_BACKUP_ENDPOINT:?MINIO_BACKUP_ENDPOINT is required}"
: "${MINIO_BACKUP_ACCESS_KEY:?MINIO_BACKUP_ACCESS_KEY is required}"
: "${MINIO_BACKUP_SECRET_KEY:?MINIO_BACKUP_SECRET_KEY is required}"
: "${MINIO_BACKUP_BUCKET:?MINIO_BACKUP_BUCKET is required}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT is required}"

backup_dir="${BACKUP_DIRECTORY:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="${backup_dir}/kasta-minio-${timestamp}.tar.age"
work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT INT TERM
mkdir -p "${backup_dir}"

mc alias set kasta-backup "${MINIO_BACKUP_ENDPOINT}" \
  "${MINIO_BACKUP_ACCESS_KEY}" "${MINIO_BACKUP_SECRET_KEY}"
mc mirror --overwrite "kasta-backup/${MINIO_BACKUP_BUCKET}" "${work_dir}/objects"
tar -C "${work_dir}" -cf - objects \
  | age --recipient "${BACKUP_AGE_RECIPIENT}" --output "${output}"
sha256sum "${output}" > "${output}.sha256"
printf '%s\n' "Encrypted MinIO backup: ${output}"
