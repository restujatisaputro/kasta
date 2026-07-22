# Struktur Monorepo KASTA

## Struktur target

```text
kasta-platform/
├── .github/
│   └── workflows/
│       └── ci.yml                         # CI lint, test, build, dan contract check
├── apps/
│   ├── api/
│   │   ├── migrations/
│   │   │   ├── versions/                 # Revision Alembic; tidak diedit setelah rilis
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── src/kasta_api/
│   │   │   ├── api/routes/               # HTTP adapter dan health endpoint
│   │   │   ├── core/                     # Config, error, logging, security lintas modul
│   │   │   ├── db/                       # Base metadata dan session SQLAlchemy
│   │   │   └── modules/                  # Batas modul modular monolith
│   │   │       ├── auth/
│   │   │       ├── users/
│   │   │       ├── businesses/
│   │   │       ├── accounting/
│   │   │       ├── transactions/
│   │   │       ├── receipts/
│   │   │       ├── ocr/
│   │   │       ├── inventory/
│   │   │       ├── receivables/
│   │   │       ├── payables/
│   │   │       ├── mentors/
│   │   │       ├── reports/
│   │   │       ├── notifications/
│   │   │       ├── sync/
│   │   │       └── audit/
│   │   ├── tests/                         # Unit/component test API
│   │   ├── alembic.ini
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── web/
│   │   ├── src/
│   │   │   ├── lib/
│   │   │   │   ├── api/                  # HTTP client dan adapter contract
│   │   │   │   ├── components/           # Komponen UI reusable
│   │   │   │   ├── config/               # Config public tervalidasi Zod
│   │   │   │   └── features/             # Slice UI per capability
│   │   │   ├── routes/                   # SvelteKit routes
│   │   │   ├── app.css
│   │   │   └── app.html
│   │   ├── static/
│   │   ├── tests/                         # Unit/component test web
│   │   ├── package.json
│   │   └── README.md
│   └── android/
│       ├── app/src/
│       │   ├── main/java/id/kasta/app/
│       │   │   ├── core/                 # DB, network, sync, DI, UI system
│       │   │   └── feature/              # Feature modules saat dikembangkan
│       │   ├── main/res/
│       │   ├── test/                      # JVM unit test
│       │   └── androidTest/               # Instrumentation test
│       ├── gradle/libs.versions.toml
│       ├── gradle/wrapper/                 # Wrapper Gradle dan checksum distribusi
│       ├── gradlew                          # Entrypoint Gradle POSIX
│       ├── gradlew.bat                      # Entrypoint Gradle Windows
│       ├── build.gradle.kts
│       ├── settings.gradle.kts
│       └── README.md
├── packages/
│   ├── contracts/
│   │   ├── openapi/kasta-api.yaml         # Source of truth kontrak HTTP
│   │   ├── src/generated/                 # Tipe hasil generator; jangan edit manual
│   │   ├── src/index.ts
│   │   └── package.json
│   └── shared/
│       ├── config/environments.json       # Config netral bahasa, tanpa secret
│       ├── src/                           # Tipe/konstanta TypeScript lintas package
│       └── package.json
├── infrastructure/
│   ├── docker/
│   │   ├── compose.yaml
│   │   ├── api.Dockerfile
│   │   └── web.Dockerfile
│   └── caddy/
│       └── Caddyfile
├── documentation/
│   ├── adr/                               # Catatan keputusan arsitektur
│   ├── api/                               # Panduan kontrak dan kompatibilitas
│   ├── operations/runbooks/               # Backup, restore, incident response
│   ├── database/                           # ERD, data dictionary, dan DDL awal
│   └── *.md
├── scripts/
│   ├── bootstrap.ps1                      # Bootstrap Windows
│   ├── bootstrap.sh                       # Bootstrap POSIX
│   ├── check_structure.py                 # Guardrail struktur repository
│   └── export_openapi.py                  # Ekspor OpenAPI dari FastAPI
├── tests/
│   ├── contract/                          # Consumer/contract checks lintas klien
│   ├── integration/                       # API + PostgreSQL + MinIO
│   ├── e2e/                               # Alur pengguna lintas aplikasi
│   └── fixtures/                          # Fixture lintas platform, tanpa data sensitif
├── .editorconfig
├── .dockerignore
├── .env.example
├── .gitattributes
├── .gitignore
├── package.json
├── pnpm-workspace.yaml
└── README.md
```

## Fungsi dan batas tanggung jawab

### `apps/api`

Unit deploy backend FastAPI. Semua modul memakai database PostgreSQL yang sama, tetapi tabel,
service, dan repository memiliki pemilik modul yang jelas. Modul tidak boleh membaca tabel modul
lain secara langsung. Route hanya menerjemahkan HTTP ke application service; aturan bisnis dan
posting double-entry nantinya berada di modul domain/application.

Setiap modul yang mulai berisi fitur mengikuti pola:

```text
module_name/
├── domain/          # Entity, value object, invariant, domain service
├── application/     # Use case, command/query, port
├── infrastructure/  # SQLAlchemy repository dan adapter eksternal
└── presentation/    # Router dan Pydantic schema HTTP
```

Folder lapisan dibuat ketika ada use case pertama agar scaffold tidak dipenuhi file kosong.

### `apps/web`

Klien SvelteKit. `routes` menangani routing dan server/browser boundary; `features` mengelompokkan
UI berdasarkan kapabilitas pengguna; `lib/api` menjadi satu-satunya pintu HTTP. Secret backend
tidak boleh memakai prefix `PUBLIC_` atau masuk ke bundle browser.

### `apps/android`

Klien offline-first. Room akan menjadi sumber data UI, Retrofit menangani remote API, WorkManager
menjalankan antrean sinkronisasi, Hilt menghubungkan dependency, CameraX mengambil nota, dan ML Kit
melakukan OCR awal di perangkat. `applicationId` dan namespace adalah `id.kasta.app`.

### `packages/contracts`

Kontrak OpenAPI lintas API, web, dan Android. File di `src/generated` selalu dibuat generator;
perubahan manual dilarang. Kontrak tidak memuat implementasi atau kredensial.

### `packages/shared`

Aset tanpa secret yang dapat dibagikan, terutama untuk package TypeScript. Python dan Kotlin tidak
mengimpor package npm ini; keduanya menggunakan OpenAPI atau JSON netral bila perlu. Aturan domain
akuntansi tetap dimiliki backend.

### `infrastructure`

Definisi runtime lokal dan baseline produksi. Compose ditujukan untuk development/integration;
konfigurasi produksi menggunakan image immutable, secret manager, volume/layanan terkelola, dan
deployment pipeline terpisah.

### `documentation`, `scripts`, dan `tests`

`documentation` menyimpan keputusan dan prosedur; `scripts` hanya otomasi deterministik dan aman;
`tests` di root menguji batas antarkomponen, sedangkan test yang dekat dengan unit tetap berada di
masing-masing aplikasi.
