# Test Plan KASTA

Versi dokumen: 1.0  
Pemilik: QA Lead  
Status: aktif  
Tanggal acuan: 22 Juli 2026

## 1. Tujuan dan prinsip

Pengujian memastikan KASTA aman digunakan untuk pencatatan keuangan banyak UMKM pada website dan
Android, termasuk saat offline. Urutan risiko tertinggi adalah isolasi tenant, integritas jurnal,
otorisasi pembina, idempotensi sinkronisasi, pemulihan data, lalu pengalaman pengguna.

Prinsip yang wajib dipertahankan:

1. kegagalan tidak boleh menghasilkan setengah transaksi, jurnal tidak seimbang, atau stok yang
   berbeda dari transaksi;
2. test lintas tenant memakai sedikitnya dua `business_id` dan membuktikan data tidak terlihat,
   bukan hanya mengharapkan kode HTTP tertentu;
3. transaksi keuangan yang telah diposting diuji melalui reversal, bukan penghapusan;
4. fixture hanya memakai data sintetis dan secret pengujian tidak disimpan di repository;
5. test deterministik menggunakan waktu, UUID, dan idempotency key yang dikendalikan;
6. performa tidak boleh ditingkatkan dengan melemahkan transaksi database atau validasi jurnal.

## 2. Ruang lingkup

Termasuk API FastAPI, PostgreSQL dan RLS, object storage nota, website SvelteKit, Android Room dan
WorkManager, kontrak sinkronisasi, mesin jurnal, OCR/parser, permission pembina, keamanan,
aksesibilitas, performa baca, dan proses backup-restore.

Integrasi FCM/email nyata, malware scanner nyata, kestabilan jaringan operator, dan pemulihan
infrastruktur produksi diuji di staging/operasional karena membutuhkan layanan serta credential
eksternal. Test lokal tetap memverifikasi adapter, fallback, dan failure path-nya.

## 3. Pendekatan dan matriks jenis test

| Jenis              | Tujuan                                                     | Implementasi                                              | Frekuensi dan quality gate                              |
| ------------------ | ---------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------- |
| Unit               | Aturan murni, pembulatan, parser, keputusan retry          | Pytest, Hypothesis, JUnit, Vitest                         | Setiap PR; seluruh test harus lulus                     |
| Integration        | Transaksi service-repository dan rollback atomik           | Pytest async; PostgreSQL/MinIO melalui Compose            | Setiap PR untuk inti; nightly untuk dependency nyata    |
| API                | Status, schema, permission, problem response, idempotensi  | HTTPX ASGI terhadap `/api/v1`                             | Setiap PR; P0/P1 100% lulus                             |
| Database           | Migration, FK, check constraint, trigger, indeks           | Alembic, `test-financial-integrity.sql`, dan `psql`       | Setiap PR; migration `head` wajib berhasil              |
| Tenant isolation   | Token/query tidak dapat berpindah usaha                    | Pytest dengan usaha A dan B                               | Setiap PR; kebocoran apa pun menggagalkan rilis         |
| Row-Level Security | Pertahanan PostgreSQL untuk anggota, pembina, support      | `scripts/postgres/test-rls.sql` sebagai role `kasta_app`  | Setiap PR pada PostgreSQL nyata                         |
| Accounting journal | Template, pembulatan, keseimbangan, reversal, revision     | Pytest + property test                                    | Setiap PR; tidak boleh ada jurnal tidak seimbang        |
| OCR parser         | Format Indonesia, ekstraksi, duplikat, confidence          | Pytest parser dan service; JUnit parser Android           | Setiap PR; minimal 20 skenario parser                   |
| Sync               | Push/pull/status, idempotensi, version conflict, tombstone | Pytest API                                                | Setiap PR; konflik finansial tidak boleh auto-merge     |
| Offline            | Room sebagai sumber utama, antrean, retry jaringan         | JUnit dan instrumented Room test                          | Unit setiap PR; instrumented nightly/release            |
| Android UI         | Navigasi, tiga langkah, bahasa sederhana, konfirmasi OCR   | Compose UI test                                           | Compile setiap PR; emulator nightly/release             |
| Website component  | State form, dialog, tabel, grafik, empty/error/loading     | Vitest + Testing Library Svelte                           | Setiap PR                                               |
| End-to-end         | Navigasi browser dan alur kritis antar-container           | Playwright desktop dan mobile                             | Setiap PR untuk publik; staging untuk alur login        |
| Accessibility      | Semantik, keyboard, fokus, nama aksesibel, WCAG            | axe-core Playwright dan Compose semantics                 | Setiap PR; tidak ada impact serious/critical            |
| Performance        | Latensi, error rate, ukuran respons                        | k6 profil smoke                                           | Sebelum merge perubahan query/laporan dan sebelum rilis |
| Load               | Ketahanan 50 VU dan pool resource                          | k6 profil load di staging                                 | Nightly terjadwal/kandidat rilis                        |
| Security           | Auth, IDOR, rate limit, upload, header, dependency         | Pytest, RLS SQL, pip-audit, pnpm audit, dependency review | Setiap PR; tidak ada Critical/High terbuka              |
| Backup restore     | Checksum, dekripsi, restore, migrasi, jurnal, RLS          | `restore-drill.sh` pada database terisolasi               | Bulanan dan sebelum rilis mayor                         |

## 4. Lingkungan pengujian

| Lingkungan       | Penggunaan                                            | Data                                                               |
| ---------------- | ----------------------------------------------------- | ------------------------------------------------------------------ |
| Lokal cepat      | Unit/API/service dengan SQLite in-memory              | Fixture sintetis per test                                          |
| CI PostgreSQL    | Migration, runtime role, FORCE RLS, audit append-only | Data SQL dalam transaksi lalu `ROLLBACK`                           |
| CI browser       | SvelteKit dev server dan Chromium                     | Halaman publik, tanpa credential                                   |
| Android JVM      | Domain, parser, repository, retry                     | Entity lokal sintetis                                              |
| Android emulator | Room dan Compose UI                                   | Database in-memory/perangkat test                                  |
| Staging          | E2E terautentikasi, MinIO, OCR, performance/load      | Tenant khusus QA, dapat dihapus terjadwal                          |
| Restore test     | Pemulihan backup                                      | Database bernama akhiran `_restore_test`; terisolasi dari produksi |

Versi PostgreSQL, API, web, Android, migration revision, browser, dan commit SHA harus dicatat pada
setiap hasil eksekusi. Jam host menggunakan UTC; tampilan diverifikasi pada zona `Asia/Jakarta`.

## 5. Data dan fixture

- Gunakan dua usaha minimum untuk test tenant: Usaha A sebagai subjek dan Usaha B sebagai target
  negatif.
- Nominal memakai nilai batas `0.01`, nilai umum, `NUMERIC(18,2)` maksimum yang diizinkan, serta
  pembayaran satu sen di atas sisa tagihan.
- Nota sintetis mencakup variasi `Rp25.000`, tanggal Indonesia, confidence tinggi/rendah, gambar
  identik, dan object storage yang sengaja gagal.
- Sync memakai dua `device_id`, `operation_id`, `batch_id`, versi server, dan request replay yang
  eksplisit.
- Waktu kedaluwarsa dibekukan atau ditetapkan jelas sebelum `now`; hindari assertion yang bergantung
  pada pergantian menit.

## 6. Entry criteria

1. kebutuhan dan acceptance criteria modul tersedia;
2. migration dapat diterapkan dari database kosong;
3. build API, web, dan Android dapat dibuat;
4. akun/tenant QA dan secret staging tersedia melalui secret manager;
5. defect Critical/High dari tahap sebelumnya sudah ditutup atau diterima tertulis oleh pemilik
   risiko.

## 7. Exit criteria dan quality gate

- Semua P0 dan P1 lulus; tidak ada defect severity Critical atau High yang terbuka.
- Backend, web, Android unit, lint, type-check, migration, dan PostgreSQL RLS lulus.
- Seluruh jurnal hasil test memiliki total debit sama dengan kredit dan transaksi gagal tidak
  meninggalkan side effect.
- Tidak ditemukan data usaha lain melalui API maupun query langsung sebagai role runtime.
- Playwright desktop/mobile lulus; axe-core tidak menemukan pelanggaran serious/critical.
- Smoke performance: error HTTP `<1%`, checks `>99%`, p95 `<750 ms`, p99 `<1.500 ms`.
- Restore drill terbaru lulus dan menyimpan bukti checksum, revision, integritas jurnal, serta RLS.
- Risiko test yang belum dapat dijalankan dicatat sebagai kondisi rilis, bukan dinyatakan lulus.

Target coverage berbasis risiko: 100% cabang aturan posting/reversal/permission tenant, minimal 90%
untuk service keamanan dan sinkronisasi, serta minimal 80% line coverage backend secara keseluruhan.
Coverage tidak menggantikan property test dan test PostgreSQL nyata.

## 8. Severity defect

| Severity | Definisi                                                                               | Contoh                                      | SLA keputusan                               |
| -------- | -------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| Critical | Kebocoran tenant, jurnal salah, kehilangan data, auth bypass, restore merusak produksi | UMKM A membaca transaksi UMKM B             | Hentikan rilis dan perbaiki segera          |
| High     | Alur inti gagal tanpa workaround aman atau perubahan finansial tidak atomik            | reversal hanya terbentuk separuh            | Hentikan tahap/rilis                        |
| Medium   | Fitur penting terganggu tetapi ada workaround aman, tanpa korupsi data                 | filter laporan salah sementara ekspor benar | Perbaiki sebelum rilis atau risk acceptance |
| Low      | Masalah minor/kosmetik/dokumentasi                                                     | jarak elemen tidak konsisten                | Masuk backlog terjadwal                     |

## 9. Priority eksekusi

| Priority | Kapan dijalankan                          | Cakupan                                                        |
| -------- | ----------------------------------------- | -------------------------------------------------------------- |
| P0       | Setiap commit/PR dan smoke setelah deploy | tenant/RLS, jurnal, auth, transaksi, reversal, sync idempotent |
| P1       | Setiap PR dan kandidat rilis              | OCR, pembina, utang/piutang, UI utama, accessibility           |
| P2       | Nightly atau sebelum rilis                | E2E luas, load, emulator matrix, dependency nyata              |
| P3       | Berkala                                   | kompatibilitas perangkat luas, endurance, exploratory kosmetik |

Severity menyatakan dampak jika gagal; priority menyatakan urutan test. Kasus dapat ber-Severity
Critical sekaligus Priority P0.

## 10. Siklus defect dan bukti

Test gagal dibuatkan defect berisi test case ID, build/commit, lingkungan, langkah reproduksi,
expected/actual, request ID, log yang sudah disensor, screenshot/trace, severity, priority, dan
pemilik. Setelah patch, jalankan test terfokus lalu seluruh suite terdampak. Defect baru boleh
ditutup setelah retest lulus dan bukti dilampirkan.

Artifact CI disimpan 14 hari untuk trace/screenshot Playwright. Laporan keamanan dan restore harus
disimpan sesuai retensi operasional tanpa menyertakan token, kata sandi, isi nota asli, atau data
pribadi.

## 11. Perintah utama

```powershell
# Backend
& apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests

# Web component
pnpm --filter kasta_web test

# E2E + accessibility (menghidupkan SvelteKit test server)
pnpm test:e2e

# Android unit dan kompilasi instrumented test
Set-Location apps/android
./gradlew testDebugUnitTest assembleDebugAndroidTest

# PostgreSQL RLS pada database Compose (PowerShell)
Get-Content scripts/postgres/configure-runtime-role.sql -Raw |
  docker exec -i kasta-platform-postgres-1 psql -v ON_ERROR_STOP=1 -U kasta -d kasta
Get-Content scripts/postgres/test-rls.sql -Raw |
  docker exec -i kasta-platform-postgres-1 psql -v ON_ERROR_STOP=1 -U kasta -d kasta
Get-Content scripts/postgres/test-financial-integrity.sql -Raw |
  docker exec -i kasta-platform-postgres-1 psql -v ON_ERROR_STOP=1 -U kasta -d kasta

# Performance dan load
k6 run tests/performance/k6-smoke.js
$env:KASTA_LOAD_PROFILE='load'; k6 run tests/performance/k6-smoke.js

# Restore drill: hanya database dengan nama *_restore_test
./scripts/backup/restore-drill.sh backups/kasta-postgres-<timestamp>.dump.age
```
