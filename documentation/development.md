# Panduan Pengembangan Lokal

## Bootstrap

```powershell
Copy-Item .env.example .env
./scripts/bootstrap.ps1
```

Atau pada POSIX:

```bash
cp .env.example .env
./scripts/bootstrap.sh
```

Perintah manual ekuivalen:

```bash
uv sync --project apps/api --extra dev
pnpm install --frozen-lockfile
cd apps/android && ./gradlew --version
```

## Run

```bash
uv run --project apps/api uvicorn kasta_api.main:app --reload
pnpm --filter kasta_web dev
cd apps/android && ./gradlew installDebug
```

Untuk dependency PostgreSQL dan MinIO saja:

```bash
docker compose --env-file .env -f infrastructure/docker/compose.yaml up -d postgres minio minio-init
```

Untuk semua container:

```bash
docker compose --env-file .env -f infrastructure/docker/compose.yaml up --build
```

## Migration

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini current
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "describe change"
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade -1
```

Periksa SQL migration dan dampak lock secara manual. Revision yang sudah pernah dirilis tidak boleh
diubah; buat revision koreksi baru.

## Test dan quality gate

```bash
uv run --project apps/api pytest apps/api/tests
uv run --project apps/api ruff check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api ruff format --check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
pnpm check
pnpm lint
pnpm test
pnpm format:check
cd apps/android && ./gradlew ktlintCheck lintDebug testDebugUnitTest
```

Integration test dijalankan setelah dependency Compose sehat. End-to-end test tidak digabung dengan
unit test agar kegagalan dan waktu eksekusinya mudah dibedakan.
