# Utang dan Piutang KASTA

Modul ini adalah subledger per UMKM untuk piutang pelanggan dan utang pemasok. Pengguna bekerja
dengan istilah sederhana, sedangkan sistem membuat transaksi dan jurnal double-entry secara
otomatis. Semua query dan perubahan wajib membawa `business_id` dari URL dan melewati pemeriksaan
keanggotaan serta permission.

## Aturan bisnis

- Nilai awal, pembayaran, dan sisa memakai `NUMERIC(18,2)`; tidak ada nilai `float`.
- Sisa tagihan selalu memenuhi `nilai awal = sudah dibayar + sisa`.
- Pembayaran sebagian mengubah status menjadi `PARTIALLY_PAID`; sisa nol menjadi `PAID`.
- `OVERDUE` dihitung dari tanggal jatuh tempo saat data dibaca agar tidak bergantung pada proses
  terjadwal. Status tersimpan tetap diperbarui ketika pembayaran dilakukan.
- Kelebihan pembayaran ditolak dengan HTTP 409 sebelum jurnal atau riwayat pembayaran dibuat.
- Pembayaran bersifat immutable. Tagihan yang sudah memiliki pembayaran tidak dapat dibatalkan
  langsung karena perlu alur pengembalian dana yang terpisah.
- Tagihan tanpa pembayaran dapat dibatalkan. Transaksi awal tidak dihapus; sistem membuat jurnal
  pembalik dan memberi status `CANCELLED`.
- Pengingat dibuat idempoten per jenis tagihan, ID tagihan, UMKM, dan tanggal jadwal.

## Jurnal otomatis

| Peristiwa                   | Debit            | Kredit        |
| --------------------------- | ---------------- | ------------- |
| Piutang baru                | Piutang          | Penjualan     |
| Penerimaan piutang          | Kas atau Bank    | Piutang       |
| Utang baru                  | Pembelian        | Utang Usaha   |
| Pembayaran utang            | Utang Usaha      | Kas atau Bank |
| Pembatalan tanpa pembayaran | Kebalikan jurnal | Jurnal awal   |

Pembuatan jurnal, perubahan saldo subledger, riwayat pembayaran, dan audit log menggunakan satu
database transaction. Kegagalan satu langkah membatalkan seluruh perubahan.

## Bahasa status UI

| Status teknis    | Bahasa pengguna  |
| ---------------- | ---------------- |
| `OPEN`           | Belum Dibayar    |
| `PARTIALLY_PAID` | Dibayar Sebagian |
| `PAID`           | Sudah Lunas      |
| `OVERDUE`        | Terlambat        |
| `CANCELLED`      | Dibatalkan       |

## Endpoint

Semua path diawali `/api/v1/businesses/{business_id}`.

| Method   | Path                              | Fungsi                            |
| -------- | --------------------------------- | --------------------------------- |
| GET/POST | `/customers`                      | Daftar/tambah pelanggan           |
| GET/POST | `/suppliers`                      | Daftar/tambah pemasok             |
| GET/POST | `/receivables`                    | Filter/tambah piutang             |
| GET      | `/receivables/{id}`               | Detail dan riwayat pembayaran     |
| POST     | `/receivables/{id}/payments`      | Catat penerimaan sebagian/penuh   |
| POST     | `/receivables/{id}/cancellation`  | Batalkan piutang tanpa pembayaran |
| GET/POST | `/payables`                       | Filter/tambah utang               |
| GET      | `/payables/{id}`                  | Detail dan riwayat pembayaran     |
| POST     | `/payables/{id}/payments`         | Catat pembayaran sebagian/penuh   |
| POST     | `/payables/{id}/cancellation`     | Batalkan utang tanpa pembayaran   |
| GET      | `/obligations/aging`              | Aging utang dan piutang           |
| GET      | `/obligations/reminders`          | Kandidat pengingat jatuh tempo    |
| POST     | `/obligations/reminders/generate` | Buat notifikasi secara idempoten  |
| GET      | `/notifications`                  | Daftar notifikasi UMKM            |

Filter daftar mendukung `q`, `status`, `due_from`, `due_to`, dan `overdue_only`. Aging terdiri dari
belum jatuh tempo, terlambat 1-30, 31-60, 61-90, dan lebih dari 90 hari.

## Penjadwalan pengingat

Pada MVP, endpoint generator dapat dipanggil satu kali sehari oleh cron eksternal atau GitHub
Actions terjadwal untuk setiap tenant aktif. Produksi sebaiknya menggunakan worker terjadwal yang
mengambil tenant secara bertahap. Karena notifikasi memiliki unique constraint, pengulangan job pada
tanggal yang sama tidak membuat notifikasi ganda.
