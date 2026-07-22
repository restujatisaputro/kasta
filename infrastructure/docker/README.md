# Docker infrastructure

`compose.yaml` menyediakan PostgreSQL, MinIO, inisialisasi bucket privat, migration, runtime role,
API, web, Caddy, dan seed demo opt-in untuk local/integration. Data persisten berada pada named
volume Docker.

`compose.api.yaml` adalah stack backend minimal yang hanya berisi API dan PostgreSQL:

```bash
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml up --build
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml down
```

```bash
docker compose --env-file .env -f infrastructure/docker/compose.yaml config --quiet
docker compose --env-file .env -f infrastructure/docker/compose.yaml up --build
docker compose --env-file .env -f infrastructure/docker/compose.yaml down
```

Image `latest` MinIO hanya default lokal. Staging/production wajib mem-pin tag immutable atau digest.
Compose production membuat user aplikasi MinIO dengan policy terbatas dari
`minio-kasta-policy.json`; kredensial user tersebut berbeda dari root MinIO.

## Production

Gunakan file production dengan environment yang disimpan di luar repository:

```bash
cp infrastructure/docker/.env.production.example /opt/kasta/.env.production
# isi secret melalui secret manager, lalu:
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml config --quiet
docker compose --env-file /opt/kasta/.env.production \
  -f infrastructure/docker/compose.production.yaml up -d
```

Compose production menunggu migration dan pembuatan role `kasta_app` sebelum API aktif, tidak
mempublish PostgreSQL/MinIO ke host, memakai Caddy untuk HTTPS, dan mengaktifkan resource limit
serta rotasi log. Detail DNS, backup, restore, dan rollback ada di
[`documentation/deployment.md`](../../documentation/deployment.md).
