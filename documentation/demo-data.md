# Data demo KASTA

Seed demo menyediakan data fiktif untuk pengujian manual, tangkapan layar, dan
demonstrasi produk. Tidak ada data pribadi nyata: alamat memakai nama fiktif,
dan seluruh alamat email berada pada domain `example.test`.

## Isi seed

| Entitas | Jumlah |
| --- | ---: |
| Organisasi pembina | 1 |
| Pembina | 3 |
| UMKM | 10 |
| Pengguna | 20 |
| Produk | 100 |
| Transaksi terposting | 500 |
| Jurnal | 500 (1.000 baris) |
| Utang | 30 |
| Piutang | 30 |
| Nota dan metadata OCR | 100 |
| Rekomendasi | 20 |
| Sesi pendampingan | 20 |
| Audit transaksi | 500 |

Sepuluh jenis usaha yang dipakai adalah warung makan, toko kelontong, kopi,
laundry, fesyen, kerajinan, jasa digital, bengkel, katering, dan toko online.
Semua transaksi memiliki dua baris jurnal dan jumlah debit sama dengan kredit.

## Menjalankan

1. Terapkan migration ke database development atau staging.

   ```bash
   uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
   ```

2. Pastikan `KASTA_DATABASE_URL` memakai akun database owner/bypass-RLS untuk
   proses seed. Role aplikasi `kasta_app` sengaja tidak dapat mengisi tenant
   secara lintas bisnis.

3. Jalankan seed dari root repository:

   ```bash
   uv run --project apps/api python scripts/seed_demo.py
   # atau
   uv run --project apps/api python -m kasta_api.seed_demo
   ```

Perintah bersifat idempoten: UUID deterministik dipakai untuk mengenali baris
yang sudah ada dan tidak ada data yang dihapus. Seed ditolak ketika
`KASTA_ENVIRONMENT=production`.

## Akun demo

Semua akun memakai kata sandi sementara `DemoKasta123!`. Email memakai pola:

- `demo.owner01@example.test` sampai `demo.owner10@example.test`;
- `demo.staff01@example.test` sampai `demo.staff07@example.test`;
- `demo.mentor01@example.test` sampai `demo.mentor03@example.test`.

Ganti atau hapus kredensial ini sebelum lingkungan demo dibuka ke pengguna luar.
Object key gambar nota adalah metadata demonstrasi; unggah objek nyata ke MinIO
terlebih dahulu bila ingin menguji signed URL atau pratinjau gambar.
