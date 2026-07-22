# KASTA API

Backend modular monolith KASTA berbasis Python 3.14, FastAPI, SQLAlchemy 2 async, Alembic,
PostgreSQL, dan Pydantic Settings. Package Python bernama `kasta_api` dan menggunakan layout
`src/` agar import tidak bergantung pada working directory.

Fondasi ini sudah mencakup autentikasi, otorisasi business-scoped, onboarding pemilik UMKM, serta
mesin pencatatan double-entry. Onboarding membuat profil usaha, metode pembayaran, saldo awal
berpasangan, dan sesi perangkat dalam satu transaksi database.

## Prasyarat

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 17, atau Docker dengan Compose v2

## Instalasi

Jalankan dari root repository:

```powershell
Copy-Item .env.example .env
uv sync --project apps/api --extra dev --locked
```

Pada Bash gunakan `cp .env.example .env`.

## Menjalankan secara lokal

Jalankan PostgreSQL:

```bash
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml up -d postgres
```

Jalankan migration lalu API:

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api uvicorn kasta_api.main:app --reload --host 0.0.0.0 --port 8000
```

Alamat layanan:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- Liveness: `GET http://localhost:8000/api/v1/health/live`
- Readiness PostgreSQL: `GET http://localhost:8000/api/v1/health/ready`

`live` hanya memeriksa proses API. `ready` menjalankan `SELECT 1` ke PostgreSQL dan mengembalikan
HTTP 503 bila database belum siap.

## Seed data demo

Setelah migration, seed dapat dijalankan dari root repository atau direktori `apps/api`:

```bash
uv run --project apps/api python -m kasta_api.seed_demo
```

Seed ini seluruhnya fiktif, memakai UUID deterministik, dan aman dijalankan ulang tanpa menghapus
data yang sudah ada.  Data mencakup satu organisasi pembina, tiga pembina, sepuluh UMKM, dua puluh
pengguna (kata sandi demo `DemoKasta123!`), seratus produk, lima ratus transaksi dengan jurnal
double-entry seimbang, utang/piutang, nota beserta metadata OCR, rekomendasi, dan sesi pendampingan.
Jangan menjalankan seed demo pada production. CLI akan menolak ketika
`KASTA_ENVIRONMENT=production`; gunakan hanya pada development atau staging.

## Menjalankan dengan Docker Compose

```bash
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml up --build
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml ps
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml logs -f api
docker compose --env-file .env -f infrastructure/docker/compose.api.yaml down
```

Gunakan `down --volumes` hanya bila data PostgreSQL lokal memang boleh dihapus.

## Konfigurasi environment

Semua konfigurasi backend memakai prefix `KASTA_`. Nilai lokal tersedia di `.env.example`.

| Variabel                             | Fungsi                                                        |
| ------------------------------------ | ------------------------------------------------------------- |
| `KASTA_ENVIRONMENT`                  | `local`, `test`, `staging`, atau `production`                 |
| `KASTA_DEBUG`                        | Mode debug aplikasi                                           |
| `KASTA_LOG_LEVEL`                    | Level log standar Python                                      |
| `KASTA_LOG_FORMAT`                   | `json` atau `text`                                            |
| `KASTA_DATABASE_URL`                 | URL SQLAlchemy menggunakan driver `psycopg`                   |
| `KASTA_DATABASE_ECHO`                | Menampilkan SQL untuk diagnosis lokal                         |
| `KASTA_DATABASE_POOL_SIZE`           | Ukuran pool koneksi utama                                     |
| `KASTA_DATABASE_MAX_OVERFLOW`        | Koneksi tambahan maksimum                                     |
| `KASTA_CORS_ORIGINS`                 | Array JSON origin web yang diizinkan                          |
| `KASTA_REQUEST_ID_HEADER`            | Nama header korelasi request                                  |
| `KASTA_JWT_SIGNING_KEY`              | Signing key autentikasi; nilai production wajib unik          |
| `KASTA_TOKEN_HASH_KEY`               | Kunci HMAC untuk refresh token, device ID, dan rate-limit key |
| `KASTA_OUTBOX_ENCRYPTION_KEY`        | Kunci AES-GCM base64 32 byte untuk payload outbox autentikasi |
| `KASTA_ACCESS_TOKEN_MINUTES`         | Umur JWT access token                                         |
| `KASTA_ONBOARDING_TOKEN_MINUTES`     | Umur token singkat setelah verifikasi akun                    |
| `KASTA_REFRESH_TOKEN_DAYS`           | Umur maksimum sesi/refresh token                              |
| `KASTA_LOGIN_RATE_MAX_ATTEMPTS`      | Batas kegagalan login dalam satu window                       |
| `KASTA_OBJECT_ENDPOINT`              | Endpoint MinIO/S3-compatible untuk object storage             |
| `KASTA_OBJECT_BUCKET_BUSINESS_LOGOS` | Bucket privat untuk logo usaha                                |
| `KASTA_OBJECT_ACCESS_KEY`            | Access key object storage                                     |
| `KASTA_OBJECT_SECRET_KEY`            | Secret key object storage                                     |

Konfigurasi production menolak debug aktif serta seluruh secret development. Gunakan secret yang
berbeda untuk signing JWT, hashing token, dan enkripsi outbox; secret staging/production harus
berasal dari secret manager, bukan file `.env` di repository.

## Autentikasi dan otorisasi

Endpoint publik tersedia untuk login, refresh, verifikasi email/telepon, serta lupa/reset password.
Login wajib menerima `business_id`; refresh tetap terikat pada `business_id` di device session.
Endpoint terlindungi berada pada pola `/api/v1/businesses/{business_id}/...` dan dependency izin
selalu memeriksa empat hal: claim JWT, sesi yang belum dicabut, akses tenant aktif di database, dan
permission granular. Claim token tidak menjadi sumber otorisasi tunggal.

Refresh token adalah secret acak satu kali pakai yang disimpan sebagai HMAC. Setiap refresh merotasi
secret; pemakaian ulang token lama mencabut seluruh session family. Password disimpan sebagai
Argon2id. Reset password mencabut semua sesi pengguna.

Token verifikasi dan reset tidak pernah disimpan mentah. API menaruh token ke tabel
`auth_delivery_outbox` dalam payload AES-GCM untuk dikirim worker email/SMS. Worker pengiriman
merupakan integrasi deployment berikutnya; jangan menampilkan token tersebut di response atau log.

Endpoint publik tidak memiliki principal sehingga tidak memeriksa permission. Semua endpoint yang
sudah terautentikasi wajib membawa `business_id` dan memakai `require_permission(...)`.

## Onboarding pemilik UMKM

Alur API berada di `/api/v1`: `POST /onboarding/account`, `POST /onboarding/verify`,
`GET /onboarding/categories`, lalu `POST /onboarding/complete`. Endpoint terakhir hanya menerima
token onboarding untuk akun yang sudah terverifikasi dan hanya mendukung pilihan “Saya Pemilik
UMKM”.

Profil dapat dibaca dan diubah melalui `/businesses/{business_id}/profile`. Logo disimpan pada bucket
privat dan diakses melalui endpoint terlindungi `/businesses/{business_id}/profile/logo`. Semua
endpoint profil memeriksa tenant dari `business_id` serta permission `business.profile.read` atau
`business.profile.update`.

## Mesin akuntansi

Klien mengirim jenis transaksi, jumlah, tanggal, deskripsi, serta pilihan pembayaran/kategori bila
diperlukan ke `POST /api/v1/businesses/{business_id}/accounting/transactions`. Klien tidak pernah
mengirim baris debit atau kredit. Mesin memilih dua akun dari 24 akun sistem, membulatkan nilai
dengan aturan `ROUND_HALF_UP` ke dua angka desimal, lalu menyimpan transaksi, jurnal seimbang,
revision snapshot, dan audit log dalam satu transaksi database.

Endpoint terkait:

- `GET /businesses/{business_id}/accounting/accounts`
- `GET /businesses/{business_id}/accounting/transactions/{transaction_id}`
- `GET /businesses/{business_id}/accounting/transactions/{transaction_id}/history`
- `POST /businesses/{business_id}/accounting/transactions/{transaction_id}/reversal`
- `POST /businesses/{business_id}/accounting/transactions/{transaction_id}/revision`

Tidak ada endpoint penghapusan transaksi terposting. Reversal membuat transaksi dan jurnal lawan;
revision membuat reversal lalu pengganti dalam satu boundary database. Migrasi PostgreSQL juga
menolak penghapusan catatan keuangan, menjaga histori/audit tetap immutable, dan memakai deferred
constraint trigger untuk membandingkan total jurnal dengan seluruh barisnya saat commit.

## Transaksi sederhana dan sinkronisasi

Router `/businesses/{business_id}/transactions` menerjemahkan Uang Masuk, Uang Keluar, Tambah Modal,
dan Ambil Uang Pribadi ke command mesin akuntansi. Modul mencakup draft, pencarian/filter, kategori
terakhir, transaksi berulang, revision, reversal, foto bukti privat, dan endpoint sinkronisasi
idempoten untuk Android. Detail kontrak dan operasional ada di
`documentation/modules/transaksi-sederhana.md`.

## Foto Nota

Router `/businesses/{business_id}/receipt-scans` menerima gambar asli dan hasil crop Android, teks
ML Kit, serta field parser perangkat. Backend memvalidasi dan memproses ulang gambar, menyimpan objek
privat di MinIO, mem-parsing format nota Indonesia, menghitung perceptual hash, serta mencari duplikat.
Upload berhenti pada `NEEDS_REVIEW`; endpoint `/confirm` satu-satunya jalur pembentukan transaksi.
Rancangan data, alur, permission, dan batas MVP dijelaskan di
`documentation/modules/foto-nota.md`.

## Struktur kode

```text
src/kasta_api/
├── api/             # Router, dependency FastAPI, metadata OpenAPI
├── core/            # Config, logging, middleware, dan error contract
├── db/              # Declarative base, engine, session factory
├── modules/         # Batas ownership modul bisnis
└── main.py          # Application factory dan entry point
```

Modul bisnis yang disiapkan:

`auth`, `users`, `businesses`, `accounting`, `transactions`, `receipts`, `ocr`, `inventory`,
`receivables`, `payables`, `mentors`, `reports`, `notifications`, `sync`, dan `audit`.

Setiap modul tetap sederhana sampai memiliki use case pertama. Lapisan `domain`, `application`,
`infrastructure`, atau `presentation` baru dibuat ketika benar-benar diperlukan.

## Database dan dependency injection

`kasta_api.db.session.get_db_session` menyediakan satu `AsyncSession` per request. Use case yang
melakukan perubahan bertanggung jawab memanggil `commit`; dependency akan melakukan rollback bila
terjadi exception dan selalu menutup session.

Gunakan alias `DatabaseSession` dari `kasta_api.api.dependencies` pada endpoint. Semua model domain
kelak mewarisi `Base`; mixin UUID dan timestamp tersedia tanpa memaksa semua tabel memakainya.

## Error dan request ID

Semua error HTTP dan validasi menggunakan media type `application/problem+json`. Setiap respons
memiliki `X-Request-ID`; request ID valid dari klien dipertahankan, sedangkan nilai yang tidak aman
diganti UUID baru. Nilai yang sama masuk ke structured log untuk korelasi.

Contoh respons:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Not Found",
  "instance": "/api/v1/not-found",
  "request_id": "6fe85375-1f3d-4a58-8705-a2368a67eaa8"
}
```

## Test dan quality gate

```bash
uv run --project apps/api pytest apps/api/tests
uv run --project apps/api ruff check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api ruff format --check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
```

## Alembic

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini current
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "describe change"
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade -1
```

Revision yang sudah dirilis tidak boleh diedit. Pastikan model baru terimpor ke `Base.metadata` dan
tinjau hasil autogenerate sebelum commit.
