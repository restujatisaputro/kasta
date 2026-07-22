# Modul Transaksi Sederhana

## Tujuan dan bahasa pengguna

Modul ini menyediakan empat tindakan utama: **Uang Masuk**, **Uang Keluar**, **Tambah Modal**, dan
**Ambil Uang Pribadi**. Pengguna menyelesaikan transaksi dalam paling banyak tiga langkah:

1. tanggal, nominal Rupiah, kategori/sumber, dan metode pembayaran;
2. pelanggan/pemasok, catatan, foto bukti, serta pilihan berulang yang semuanya opsional;
3. pemeriksaan dan penyimpanan atau penyimpanan sebagai draft.

Istilah debit dan kredit tidak ditampilkan. Backend tetap membuat jurnal berpasangan dalam satu
transaksi database. Transaksi yang sudah terposting tidak dapat dihapus permanen.

## Pemetaan jurnal otomatis

| Tindakan           | Sisi masuk                        | Sisi keluar                   |
| ------------------ | --------------------------------- | ----------------------------- |
| Uang Masuk         | Kas, Bank, atau Dompet Digital    | Sumber pemasukan yang dipilih |
| Uang Keluar        | Kategori pengeluaran yang dipilih | Kas atau Bank                 |
| Tambah Modal       | Kas                               | Modal Pemilik                 |
| Ambil Uang Pribadi | Prive                             | Kas                           |

Nilai dikirim sebagai string desimal dan disimpan sebagai `NUMERIC(18,2)`. Android menyimpan Rupiah
sebagai `Long`; tidak ada `Float` atau `Double` pada jalur nilai keuangan.

## Endpoint

Semua endpoint berada di `/api/v1/businesses/{business_id}` dan memeriksa keanggotaan tenant serta
permission pengguna.

| Method dan path                          | Kegunaan                                                      | Permission                  |
| ---------------------------------------- | ------------------------------------------------------------- | --------------------------- |
| `GET /transactions/options`              | kategori dengan yang terakhir dipakai di urutan awal          | `transaction.read`          |
| `GET /transactions`                      | pencarian dan filter tanggal, jenis, status, kategori, metode | `transaction.read`          |
| `POST /transactions`                     | posting transaksi dan jurnal otomatis                         | `transaction.create`        |
| `GET/POST /transactions/drafts`          | daftar atau buat draft                                        | `transaction.read/create`   |
| `PUT/DELETE /transactions/drafts/{id}`   | ubah atau hapus draft yang belum terposting                   | `transaction.update/delete` |
| `POST /transactions/drafts/{id}/post`    | posting satu draft                                            | `transaction.create`        |
| `POST /transactions/{id}/revision`       | reversal catatan lama dan posting versi baru                  | `transaction.update`        |
| `POST /transactions/{id}/reversal`       | pembatalan dengan alasan                                      | `transaction.delete`        |
| `GET/POST/PATCH /transactions/recurring` | kelola aturan transaksi berulang                              | sesuai operasi transaksi    |
| `POST /transactions/recurring/run-due`   | materialisasi jadwal yang jatuh tempo secara idempoten        | `transaction.create`        |
| `POST /transactions/{id}/receipts`       | unggah foto bukti maksimal 8 MB                               | `receipt.upload`            |
| `POST /sync/transactions`                | push operasi offline dan pull perubahan server                | per operasi                 |

## Protokol sinkronisasi Android

Android menyimpan transaksi, draft, foto URI, dan status sinkronisasi pada Room terlebih dahulu.
Operasi terposting diberi `client_operation_id` UUID dan status `PENDING`. WorkManager hanya berjalan
saat jaringan tersedia, mengirim paling banyak 100 operasi, lalu menandai hasil `SYNCED` atau
`FAILED`. `client_operation_id` adalah kunci idempotensi: pengiriman ulang mengembalikan hasil lama
tanpa membuat transaksi atau jurnal ganda.

Operasi sinkronisasi:

- `CREATE`: membuat transaksi baru;
- `SAVE_DRAFT`: menyimpan draft server;
- `REVISE`: membuat revision history, reversal, dan transaksi pengganti;
- `REVERSE`: membatalkan transaksi dengan jurnal lawan.

`pull_updated_after` berisi waktu server dari sinkronisasi sukses terakhir. Response menyertakan
perubahan transaksi dan `server_time`; waktu perangkat tidak dipakai sebagai checkpoint. Jika access
token kedaluwarsa, Android melakukan satu kali refresh token rotation sebelum mencoba ulang.

Foto bukti diunggah setelah transaksi mendapat ID server. Object key tidak pernah diterima dari
klien dan objek berada dalam bucket privat MinIO. API hanya menerima JPEG, PNG, atau WebP.

## Transaksi berulang, revisi, dan pembatalan

Aturan berulang menyimpan template transaksi, frekuensi mingguan/bulanan, interval, tanggal proses
berikutnya, serta tanggal akhir opsional. Kombinasi aturan dan tanggal kejadian dibuat unik agar job
yang dijalankan ulang tidak menggandakan transaksi.

Revisi tidak mengubah jurnal lama. Sistem menyimpan snapshot sebelum perubahan, membuat reversal,
lalu memposting versi pengganti dengan tautan revision. Pembatalan juga menghasilkan reversal;
database menolak `DELETE` terhadap transaksi, jurnal, dan baris jurnal terposting.

## Seed referensi

`seed_transaction_reference_data(session, business_id)` memastikan seluruh template akun sumber
pemasukan dan kategori pengeluaran tersedia untuk satu usaha. Service transaksi juga menjalankan
mekanisme yang sama secara idempoten saat transaksi pertama dibuat, sehingga usaha lama tetap dapat
memakai modul ini setelah migrasi.

## Pengoperasian

1. Jalankan migrasi Alembic sampai revision `20260721_0005`.
2. Pastikan bucket privat receipt pada MinIO tersedia.
3. Jalankan job `run-due` terjadwal sekali sehari; panggilan ulang aman.
4. Pantau kegagalan sync berdasarkan request ID dan `client_operation_id`.
5. Pertahankan backup PostgreSQL dan object storage sebagai satu recovery set.

## Cakupan test

Backend menguji jurnal Uang Masuk, urutan kategori terakhir, siklus draft, transaksi berulang yang
idempoten, replay sinkronisasi, serta revisi dan pembatalan. Website menguji alur tiga langkah dan
format Rupiah. Android memiliki unit test pemformat Rupiah dan Compose test untuk empat menu serta
indikator tiga langkah.
