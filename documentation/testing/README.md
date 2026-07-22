# Dokumentasi pengujian KASTA

- [`test-plan.md`](test-plan.md): strategi, ruang lingkup, lingkungan, quality gate, dan tanggung
  jawab.
- [`test-cases.md`](test-cases.md): katalog kasus uji dan traceability skenario berisiko tinggi.
- [`actual-result-template.md`](actual-result-template.md): formulir hasil eksekusi dan pelaporan
  defect.

Automation utama berada dekat dengan aplikasi yang diuji:

- Backend: [`../../apps/api/tests/`](../../apps/api/tests/), termasuk unit, API, accounting,
  tenant, keamanan, OCR, sync, notifikasi, dan laporan.
- Android: [`../../apps/android/app/src/test/`](../../apps/android/app/src/test/) untuk JVM serta
  [`../../apps/android/app/src/androidTest/`](../../apps/android/app/src/androidTest/) untuk emulator.
- Website/E2E/performance: [`../../apps/web/`](../../apps/web/) dan
  [`../../tests/`](../../tests/).
- PostgreSQL/RLS/integritas: [`../../scripts/postgres/`](../../scripts/postgres/).
- Backup/restore drill: [`../../scripts/backup/`](../../scripts/backup/).

Katalog pada `test-cases.md` adalah rencana dan template eksekusi. Status `NOT RUN` tidak berarti
lulus; hasil nyata harus dilampirkan melalui `actual-result-template.md` dan artifact CI/staging.
Khusus test RLS, load, dan restore, test harus dijalankan terhadap service nyata sesuai prasyarat,
bukan hanya terhadap mock atau SQLite.

## Perintah ringkas

```powershell
# Backend unit/API
& apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests

# Validasi katalog QA sebelum merge
& apps/api/.venv/Scripts/python.exe scripts/check_test_catalog.py

# Website component dan E2E
pnpm --filter kasta_web test
pnpm test:e2e

# Android unit + instrumented compile/test
Set-Location apps/android
./gradlew testDebugUnitTest assembleDebugAndroidTest
```

CI wajib menyimpan report JUnit, coverage, screenshot/trace E2E, log k6, dan bukti RLS/restore
setelah secret dan data pribadi disensor.
