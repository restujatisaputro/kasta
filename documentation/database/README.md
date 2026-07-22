# Rancangan Database PostgreSQL KASTA

Dokumen ini adalah rancangan awal database untuk review arsitektur dan akuntansi. DDL belum menjadi
revision Alembic aktif agar keputusan domain dapat disetujui sebelum skema dianggap kontrak rilis.

- [`database-design.md`](database-design.md): ERD, relasi, invariant, RLS, indexing, partitioning,
  audit, dan revision history.
- [`data-dictionary.md`](data-dictionary.md): kamus seluruh tabel dan lifecycle data.
- [`kasta-postgresql-v0.1.sql`](kasta-postgresql-v0.1.sql): DDL PostgreSQL awal yang eksplisit.

## Prinsip utama

1. Semua primary key publik memakai UUID dengan `gen_random_uuid()`.
2. Semua nilai uang memakai `NUMERIC(18,2)`; tidak ada `REAL`, `FLOAT`, atau `DOUBLE PRECISION`.
3. Semua tabel transaksi/keuangan memiliki `business_id NOT NULL` dan foreign key komposit untuk
   mencegah referensi lintas UMKM.
4. Jurnal berstatus `POSTED` wajib memiliki sedikitnya dua baris dan total debit sama dengan kredit.
5. Transaksi yang sudah diposting tidak boleh dihapus atau ditulis ulang. Koreksi dilakukan dengan
   transaksi dan jurnal pembalik.
6. RLS menjadi pertahanan tenant di database; otorisasi use case tetap dilakukan backend.
7. `TIMESTAMPTZ` disimpan dalam UTC dan ditampilkan menurut timezone bisnis.
