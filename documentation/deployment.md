# Deployment KASTA dengan Docker Compose

Dokumen ini menjelaskan deployment production dan development. Compose production
tidak menyimpan secret; file environment production harus dibuat di server,
di luar repository, lalu diberikan ke Docker Compose dengan `--env-file`.

## Topologi

```mermaid
flowchart LR
    DNS[DNS admniaga.com] --> Caddy[Caddy HTTPS :80/:443]
    Caddy --> Web[SvelteKit web]
    Caddy --> API[FastAPI api]
    Caddy --> Minio[MinIO signed objects]
    API --> PG[(PostgreSQL)]
    API --> Minio
    Migrate[one-shot Alembic migrate] --> PG
    Role[one-shot runtime role grant] --> PG
    API -. depends on .-> Migrate
    API -. depends on .-> Role
```

Redis dan worker belum diperlukan pada MVP: rate limiting dan OCR lanjutan masih
dapat berjalan tanpa antrean terpisah. Tambahkan Redis/worker ketika pekerjaan OCR
atau notifikasi sudah asynchronous dan volume produksinya memerlukan isolasi resource.
ClamAV tersedia sebagai profile opsional `security`; aktifkan profile tersebut dan
set `KASTA_MALWARE_SCAN_ENABLED=true` bila layanan scanner sudah dialokasikan resource.

## Domain dan reverse proxy

| Domain                  | Tujuan                                       |
| ----------------------- | -------------------------------------------- |
| `kasta.admniaga.com`    | Redirect permanen ke `appkasta.admniaga.com` |
| `appkasta.admniaga.com` | Website SvelteKit                            |
| `apikasta.admniaga.com` | API FastAPI dan signed URL MinIO             |

`infrastructure/caddy/Caddyfile.production` mengatur routing tersebut. Caddy
menerbitkan dan memperbarui sertifikat Let's Encrypt secara otomatis. DNS ketiga
domain harus mengarah ke server dan port TCP/UDP 443 serta TCP 80 harus terbuka
untuk ACME HTTP challenge. Bucket MinIO tetap private; jangan mengaktifkan anonymous read.

## File dan image

- `infrastructure/docker/api.Dockerfile`: build multi-stage Python 3.14, virtualenv
  runtime non-root, Alembic dan health check.
- `infrastructure/docker/web.Dockerfile`: build SvelteKit adapter-node, runtime
  Node 22 non-root dan health check.
- `infrastructure/docker/compose.yaml`: development lengkap (PostgreSQL, MinIO,
  API, web, Caddy, optional ClamAV).
- `infrastructure/docker/compose.api.yaml`: development backend minimal.
- `infrastructure/docker/compose.production.yaml`: production dengan volume,
  dependency health, resource limit, log rotation, dan one-shot bootstrap.

Tag image production harus immutable (tag rilis atau digest), bukan `latest`.

## Environment dan secret

1. Salin `infrastructure/docker/.env.production.example` ke lokasi di luar repo,
   misalnya `/opt/kasta/.env.production`.
2. Ganti seluruh `REPLACE_*` melalui secret manager. Minimal secret yang harus
   dirotasi adalah password PostgreSQL owner, password role `kasta_app`, kredensial
   MinIO, JWT signing key, token hash key, dan AES outbox key.
3. Gunakan password URL-safe pada `KASTA_MIGRATION_DATABASE_URL`, atau URL-encode
   password tersebut. Jangan menaruh nilai ini di GitHub Actions log.
4. Pastikan `KASTA_CORS_ORIGINS` berupa JSON array HTTPS, tanpa wildcard.

Contoh pembuatan nilai acak (jalankan di mesin admin, bukan commit):

```bash
openssl rand -hex 32
openssl rand -base64 32
openssl rand -hex 24
chmod 600 /opt/kasta/.env.production
```

Periksa hasil interpolasi tanpa menjalankan service:

```bash
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml config --quiet
```

## Deploy production

```bash
cd /opt/kasta/kasta-platform
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml build --pull
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml up -d
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml ps
```

Urutan bootstrap yang dipaksakan Compose:

1. PostgreSQL dan MinIO liveness sehat.
2. `migrate` menjalankan `alembic upgrade head` memakai akun owner.
3. `db-role` menjalankan `scripts/postgres/configure-runtime-role.sql` untuk
   membuat/grant role `kasta_app` tanpa superuser dan tanpa bypass RLS.
4. API, web, dan Caddy menerima trafik setelah health check lulus.

Migration dapat dijalankan ulang secara eksplisit:

```bash
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml run --rm migrate
```

Seed hanya untuk development atau staging dan tidak termasuk startup default:

```bash
docker compose --env-file .env -f infrastructure/docker/compose.yaml \
  --profile demo run --rm seed
```

Pada production, gunakan seed demo di database terpisah. CLI juga menolak saat
`KASTA_ENVIRONMENT=production`.

## Development

```bash
cp .env.example .env
docker compose --env-file .env -f infrastructure/docker/compose.yaml up --build
docker compose --env-file .env -f infrastructure/docker/compose.yaml ps
```

Alamat lokal: `http://localhost:8080`, API langsung `http://localhost:8000`,
MinIO console `http://localhost:9001`. Gunakan `down --volumes` hanya jika data
lokal boleh dihapus.

## Health check dan observability

- API liveness: `GET https://apikasta.admniaga.com/api/v1/health/live`.
- API readiness: `GET https://apikasta.admniaga.com/api/v1/health/ready`.
- Compose menunggu PostgreSQL, MinIO, migration, role grant, API, dan web sehat.
- Setiap container memakai Docker `json-file` dengan rotasi 20 MB × 5 file.
  Forward log ke collector terpusat sebelum volume log penuh.
- Monitor status container, HTTP 5xx, latency p95, disk PostgreSQL/MinIO, expiry
  sertifikat Caddy, backup terakhir, dan kegagalan migration.

## Backup PostgreSQL

Backup harus terenkripsi, diuji restore, dan disimpan di lokasi berbeda. Script
repository memakai `pg_dump` custom format + `age` + checksum:

```bash
export POSTGRES_BACKUP_URL='postgresql://kasta_owner:URL_SAFE_PASSWORD@db.internal:5432/kasta'
export BACKUP_AGE_RECIPIENT='age1...'
export BACKUP_DIRECTORY=/var/backups/kasta
./scripts/backup/backup-postgres.sh
```

Jadwalkan dengan systemd timer/cron pada host backup, bukan cron di container.
Simpan minimal backup harian 35 hari dan backup bulanan sesuai kebijakan retensi.

## Backup MinIO

Gunakan akun backup read-only dan endpoint internal atau tunnel admin:

```bash
export MINIO_BACKUP_ENDPOINT='https://apikasta.admniaga.com'
export MINIO_BACKUP_ACCESS_KEY='backup-read-only'
export MINIO_BACKUP_SECRET_KEY='SET_VIA_SECRET_MANAGER'
export MINIO_BACKUP_BUCKET=kasta-receipts
export BACKUP_AGE_RECIPIENT='age1...'
export BACKUP_DIRECTORY=/var/backups/kasta
./scripts/backup/backup-minio.sh
```

Ulangi untuk bucket `kasta-business-logos`. Jangan memakai root MinIO untuk job
backup rutin; kredensial pada contoh di atas hanya placeholder environment.

## Restore dan restore drill

Restore dilakukan pada database baru atau maintenance window, bukan menimpa
database aktif tanpa persetujuan:

```bash
export POSTGRES_RESTORE_URL='postgresql://kasta_owner:...@db.internal:5432/kasta_restore_test'
export BACKUP_AGE_IDENTITY=/run/secrets/backup-age-key
./scripts/backup/restore-postgres.sh /var/backups/kasta/kasta-postgres-<timestamp>.dump.age
./scripts/backup/verify-postgres-restore.sh
```

Restore object storage memakai `restore-minio.sh` dengan bucket kosong atau
namespace terpisah. Setelah verifikasi:

1. Hentikan API/web atau aktifkan maintenance page.
2. Restore PostgreSQL dan MinIO.
3. Jalankan integrity check, RLS test, dan smoke test login/transaksi.
4. Jalankan migration jika target tertinggal.
5. Hidupkan API/web/Caddy dan pantau error selama 30 menit.

`restore-drill.sh` tersedia untuk latihan berkala dan menolak verifikasi di luar
database bernama `*_restore_test`.

## HTTPS dan security baseline

Caddy mengatur HSTS, security headers, gzip/zstd, redirect domain, dan reverse proxy.
TLS termination hanya di Caddy; API dan MinIO berkomunikasi melalui network Docker
internal. PostgreSQL tidak dipublish ke host production. Gunakan firewall yang hanya
membuka 80/443 dan akses SSH terbatas.

## Restart, resource, dan rollback

Service stateless memakai `restart: unless-stopped`; job migration/role/seed memakai
`restart: "no"` agar kegagalan terlihat dan tidak mengulang perubahan diam-diam.

| Service    |    RAM | CPU |
| ---------- | -----: | --: |
| PostgreSQL |   1 GB |   2 |
| MinIO      |   1 GB |   2 |
| API        | 768 MB |   2 |
| Web        | 512 MB |   1 |
| Caddy      | 256 MB | 0.5 |

Sesuaikan setelah benchmark. Untuk rollback aplikasi, gunakan tag image rilis
sebelumnya dan `docker compose up -d`; jangan melakukan downgrade migration yang
telah menyentuh data tanpa prosedur restore. Jika migration baru tidak kompatibel,
kembalikan image hanya setelah schema aman atau restore database ke titik sebelum rilis.
