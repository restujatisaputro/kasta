# Persetujuan Akses Pembina KASTA

## Prinsip privasi

- Akses ditolak secara bawaan dan hanya aktif setelah persetujuan pemilik UMKM.
- Pemilik memilih ruang lingkup dan tanggal berakhir. Masa berlaku maksimum 366 hari.
- Pencabutan berlaku pada pemeriksaan otorisasi berikutnya; token lama tidak mempertahankan izin.
- Pembina hanya mendapat akses baca ke data usaha. Scope `SUMMARY` juga mengizinkan pembina
  membuat catatan, rekomendasi, dan kegiatan pendampingan, tetapi tidak mengubah transaksi.
- Semua pembacaan data pembina dan dukungan administrator menghasilkan audit log serta
  memperbarui `last_accessed_at`.

## Ruang lingkup

| Scope            | Tampilan pengguna         | Data yang diizinkan                                |
| ---------------- | ------------------------- | -------------------------------------------------- |
| `SUMMARY`        | Melihat ringkasan         | Ringkasan, profil umum, dan aktivitas pendampingan |
| `REPORTS`        | Melihat laporan           | Laporan yang bersumber dari jurnal                 |
| `TRANSACTIONS`   | Melihat transaksi         | Transaksi dan riwayat revisinya, baca saja         |
| `RECEIPTS`       | Melihat nota              | Nota, gambar, OCR, dan koreksi                     |
| `INVENTORY`      | Melihat stok              | Produk dan pergerakan stok                         |
| `OBLIGATIONS`    | Melihat utang dan piutang | Pelanggan, pemasok, utang, piutang, pembayaran     |
| `EXPORT_REPORTS` | Mengunduh laporan         | Ekspor laporan yang sudah diizinkan                |

## Endpoint API

- `POST /api/v1/mentors/me/access-requests` — pembina mengirim permintaan.
- `GET /api/v1/mentors/me/access-requests` — pembina melihat status permintaannya.
- `GET /api/v1/businesses/{business_id}/mentor-access` — pemilik melihat riwayat izin.
- `PATCH /api/v1/businesses/{business_id}/mentor-access/{access_id}/decision` — pemilik
  menyetujui atau menolak.
- `POST /api/v1/businesses/{business_id}/mentor-access/{access_id}/revoke` — pemilik mencabut.
- `GET /api/v1/businesses/{business_id}/mentor-access/history` — pemilik melihat jejak akses.

Endpoint pengelolaan izin mensyaratkan role `business_owner`; permission administrator organisasi
atau platform tidak dapat dipakai untuk menyetujui izin atas nama pemilik.

## Row-Level Security PostgreSQL

Migrasi `20260721_0010` mengaktifkan RLS pada tabel data keuangan, transaksi, nota,
OCR, stok, utang/piutang, kegiatan pembina, notifikasi, dan audit. API mengisi konteks transaksi
`app.user_id`, `app.business_id`, `app.actor_type`, `app.mentor_id`, dan
`app.support_grant_id` menggunakan `set_config(..., true)`.

Kebijakan database memeriksa izin berstatus `ACTIVE`, belum dicabut, belum kedaluwarsa, dan
memiliki scope yang sesuai. Aplikasi produksi harus memakai role PostgreSQL non-superuser yang
bukan pemilik tabel agar RLS tidak dapat dilewati oleh koneksi runtime.

## Akses dukungan administrator

Administrator tidak otomatis memperoleh akses data usaha. Pengecualian dukungan memakai
`support_access_grants` yang wajib mencatat pemilik pemberi izin, scope baca, alasan, referensi
tiket, waktu mulai, dan waktu berakhir. Otorisasi menghapus seluruh permission data usaha dari
administrator bila grant aktif tidak ada. Setiap akses dukungan dicatat sebagai
`ADMIN_SUPPORT_DATA_ACCESSED`, termasuk ID grant yang dipakai.

### Workflow resmi grant dukungan

1. Tim dukungan membuat tiket penanganan dan menyampaikan identitas administrator kepada
   pemilik UMKM.
2. Pemilik UMKM yang sedang berada pada tenant terkait membuat grant melalui
   `POST /api/v1/businesses/{business_id}/support-access-grants` dengan `admin_user_id`, daftar
   `scope`, alasan, referensi tiket, dan `expires_at`.
3. Sistem hanya menerima pengguna aktif dengan role `organization_admin` atau `super_admin`,
   menolak grant aktif ganda, dan membatasi masa berlaku maksimum 24 jam.
4. PostgreSQL RLS mengizinkan administrator membaca hanya data dalam scope grant aktif.
5. Pemilik meninjau grant melalui
   `GET /api/v1/businesses/{business_id}/support-access-grants` dan dapat mencabutnya melalui
   `POST /api/v1/businesses/{business_id}/support-access-grants/{grant_id}/revoke`.
6. Pembuatan dan pencabutan dicatat sebagai `ADMIN_SUPPORT_GRANT_CREATED` dan
   `ADMIN_SUPPORT_GRANT_REVOKED`; pembacaan data dicatat sebagai
   `ADMIN_SUPPORT_DATA_ACCESSED`.

Ketiga endpoint pengelolaan grant hanya menerima `business_owner` pada `business_id` yang sama.
Administrator tidak memiliki endpoint untuk membuat grant bagi dirinya sendiri.

### Verifikasi PostgreSQL lokal

Role runtime dipasang setelah migration oleh `scripts/postgres/configure-runtime-role.sql`.
Role ini harus memiliki `rolsuper = false`, `rolcreatedb = false`, dan `rolcreaterole = false`.
Uji langsung `scripts/postgres/test-rls.sql` memverifikasi isolasi anggota usaha, pembina tanpa
izin, pembina berizin, dan grant dukungan. Seluruh fixture uji dijalankan dalam transaksi lalu
di-rollback.
