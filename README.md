# kasta-platform

Monorepo **KASTA (Keuangan dan Asistensi UMKM)** untuk API FastAPI, website SvelteKit,
aplikasi Android, kontrak API, aset bersama, dan infrastruktur. Fondasi ini mengikuti
arsitektur **modular monolith**: satu unit deploy backend dengan batas modul yang tegas,
serta OpenAPI sebagai kontrak integrasi antarklien.

> Status: fondasi dan modul bisnis MVP aktif dikembangkan, termasuk transaksi, jurnal,
> persediaan, utang-piutang, Foto Nota, laporan keuangan, dan pendampingan pembina UMKM.

## Struktur ringkas

```text
kasta-platform/
├── apps/
│   ├── api/                 # FastAPI, SQLAlchemy 2, Alembic, Pytest
│   ├── web/                 # SvelteKit, TypeScript, Tailwind CSS, Zod, ECharts
│   └── android/             # Kotlin, Compose, Room, WorkManager, Retrofit, Hilt
├── packages/
│   ├── contracts/           # OpenAPI dan tipe klien hasil generasi
│   └── shared/              # Tipe/config netral dan TypeScript lintas package
├── infrastructure/
│   ├── docker/              # Compose dan Dockerfile
│   └── caddy/               # Reverse proxy lokal/produksi
├── documentation/           # Struktur, konvensi, environment, ADR, runbook
├── scripts/                 # Bootstrap dan otomasi pengembang
├── tests/                   # Contract, integration, dan end-to-end lintas aplikasi
└── .github/workflows/       # Continuous integration
```

Rincian fungsi folder dan struktur target tersedia di
[`documentation/repository-structure.md`](documentation/repository-structure.md).

## Prasyarat

- Git 2.45+
- Python 3.14 dan [uv](https://docs.astral.sh/uv/)
- Node.js 22 atau 24 dan pnpm 11.9.0 (versi dipin melalui `packageManager`)
- JDK 17, Android SDK 35, dan Android Studio
- Docker Engine/Desktop dengan Docker Compose v2

## Instalasi awal

PowerShell:

```powershell
Copy-Item .env.example .env
./scripts/bootstrap.ps1
```

Bash:

```bash
cp .env.example .env
./scripts/bootstrap.sh
```

Bootstrap memasang dependency Python dan JavaScript. Gradle Wrapper 8.11.1 sudah disertakan,
sehingga instalasi Gradle global tidak diperlukan. Dependency Android diunduh saat perintah
`gradlew` pertama dijalankan.

Jangan commit `.env` atau `apps/android/local.properties`.

## Menjalankan aplikasi

API pada `http://localhost:8000`:

```bash
uv run --project apps/api uvicorn kasta_api.main:app --reload --host 0.0.0.0 --port 8000
```

Website pada `http://localhost:5173`:

```bash
pnpm --filter kasta_web dev
```

Android (emulator/perangkat aktif):

```bash
cd apps/android
./gradlew installDebug
```

Di Windows gunakan `gradlew.bat installDebug`. Emulator Android mengakses host lokal melalui
`http://10.0.2.2:8080`; nilai ini dapat ditimpa lewat properti `KASTA_API_BASE_URL`.

Seluruh stack lokal melalui Docker Compose:

```bash
docker compose --env-file .env -f infrastructure/docker/compose.yaml up --build
docker compose --env-file .env -f infrastructure/docker/compose.yaml ps
docker compose --env-file .env -f infrastructure/docker/compose.yaml logs -f api
docker compose --env-file .env -f infrastructure/docker/compose.yaml down
```

Tambahkan `--volumes` pada `down` hanya bila memang ingin menghapus seluruh data lokal.

Panduan deployment production, konfigurasi domain `admniaga.com`, HTTPS Caddy, backup, restore,
resource limit, dan rollback ada di [`documentation/deployment.md`](documentation/deployment.md).

## Database dan migration

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "create table name"
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade -1
```

Migration produksi dijalankan sebagai job rilis tunggal sebelum aplikasi baru menerima trafik,
bukan otomatis oleh setiap replika API.

## Data demo

Untuk development atau staging, setelah migration selesai, jalankan seed fiktif berikut:

```bash
uv run --project apps/api python scripts/seed_demo.py
# atau: uv run --project apps/api python -m kasta_api.seed_demo
```

Seed membuat 1 organisasi, 3 pembina, 10 UMKM, 20 pengguna, 100 produk, 500 transaksi dengan
jurnal seimbang, 30 utang, 30 piutang, 100 nota/OCR, 20 rekomendasi, dan 20 sesi pendampingan.
Seed idempoten dan menolak environment production. Detail akun demo serta caveat object MinIO ada
di [`documentation/demo-data.md`](documentation/demo-data.md).

## Test, lint, dan format

```bash
# Backend
uv run --project apps/api pytest apps/api/tests
uv run --project apps/api ruff check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api ruff format --check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src

# JavaScript / TypeScript / Svelte
pnpm check
pnpm lint
pnpm test
pnpm format:check

# Android
cd apps/android
./gradlew ktlintCheck lintDebug testDebugUnitTest

# Validasi struktur lintas repository
uv run --project apps/api python scripts/check_structure.py
uv run --project apps/api python scripts/check_database_design.py
```

## Konvensi singkat

- Branch: `feature/<issue>-<slug>`, `fix/<issue>-<slug>`, `chore/<slug>`,
  `release/<version>`, atau `hotfix/<issue>-<slug>`.
- Commit: [Conventional Commits](https://www.conventionalcommits.org/), contoh
  `feat(api): add cash transaction endpoint`.
- Python: `snake_case`; class `PascalCase`; konstanta `UPPER_SNAKE_CASE`.
- TypeScript/Svelte: file modul `kebab-case.ts`; komponen `PascalCase.svelte`.
- Kotlin: class/file `PascalCase.kt`; fungsi/properti `camelCase`.
- Migration: timestamp/sequence Alembic dengan pesan imperatif yang spesifik.

Aturan lengkap ada di [`documentation/conventions.md`](documentation/conventions.md), sedangkan
strategi environment ada di [`documentation/environments.md`](documentation/environments.md).

## Dokumentasi rancangan

- [Rancangan arsitektur modular monolith](Rancangan_Arsitektur_Sistem_KASTA_Modular_Monolith_v0.1.md)
- [Rancangan database PostgreSQL](documentation/database/database-design.md)
- [Laporan keuangan berbasis jurnal](documentation/reports.md)
- [Modul pembina UMKM](documentation/mentors.md)
- [Notifikasi web dan Android](documentation/notifications.md)
- [Keamanan dan threat model STRIDE](documentation/security.md)
- Dokumen kebutuhan sistem: `Dokumen_Kebutuhan_Sistem_KASTA_v0.1.docx`
- [Indeks dokumentasi](documentation/README.md)

## Keamanan

Nilai di `.env.example` hanya untuk lokal. Staging dan production wajib menggunakan secret
manager, TLS, kredensial unik, rotasi signing key JWT, database non-publik, bucket privat,
serta image yang dipin dengan tag immutable atau digest.
