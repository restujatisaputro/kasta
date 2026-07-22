# PostgreSQL test scripts

Skrip di folder ini dijalankan pada database CI atau staging yang terisolasi.
Jangan menjalankannya langsung pada database produksi. Semua fixture pada
`test-rls.sql` dan `test-financial-integrity.sql` berada di dalam transaksi dan
diakhiri `ROLLBACK`.

Prasyarat:

- migration Alembic sudah berada pada `head`;
- role pemilik/migrasi (`POSTGRES_USER`) dapat menjalankan `psql`;
- role runtime `kasta_app` sudah dibuat sebagai `NOSUPERUSER NOBYPASSRLS`,
  mendapat privilege tabel, dan tidak dapat membuat role/database;
- referensi role (`business_owner`) sudah di-seed.

Contoh menjalankan pada Compose:

```powershell
Get-Content scripts/postgres/configure-runtime-role.sql -Raw |
  docker exec -i kasta-platform-postgres-1 psql -v ON_ERROR_STOP=1 -U kasta -d kasta

Get-Content scripts/postgres/test-rls.sql -Raw |
  docker exec -i kasta-platform-postgres-1 psql -v ON_ERROR_STOP=1 -U kasta -d kasta

Get-Content scripts/postgres/test-financial-integrity.sql -Raw |
  docker exec -i kasta-platform-postgres-1 psql -v ON_ERROR_STOP=1 -U kasta -d kasta
```

`test-rls.sql` memverifikasi `FORCE/ENABLE ROW LEVEL SECURITY`, isolasi anggota
usaha, scope pembina aktif dan kedaluwarsa, grant dukungan time-bound, audit append-only,
dan penolakan insert lintas tenant. `test-financial-integrity.sql`
memeriksa jurnal yang sudah ada, pasangan transaksi-jurnal, trigger reversal/
immutability, audit append-only, dan check jurnal seimbang.

Untuk drill backup, `scripts/backup/restore-drill.sh` memanggil test RLS jika
`RUN_RESTORE_RLS_TEST=true` dan `POSTGRES_RESTORE_URL` diarahkan ke database
restore yang namanya berakhiran `_restore_test`.
