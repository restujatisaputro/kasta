# Modul backend

Setiap direktori adalah batas ownership modular monolith. Modul tidak boleh mengimpor repository,
model persistence, atau tabel milik modul lain. Integrasi dilakukan melalui application service,
port, atau event internal yang eksplisit. Template lapisan saat use case pertama ditambahkan:
`domain/`, `application/`, `infrastructure/`, dan `presentation/`.

| Modul           | Tanggung jawab utama                          |
| --------------- | --------------------------------------------- |
| `auth`          | autentikasi, token, dan sesi                  |
| `users`         | profil pengguna, peran, dan izin              |
| `businesses`    | UMKM, keanggotaan, dan konteks tenant         |
| `accounting`    | bagan akun, jurnal, dan double-entry          |
| `transactions`  | Uang Masuk, Uang Keluar, modal, ambil pribadi |
| `receipts`      | metadata dan foto nota                        |
| `ocr`           | pemrosesan dan hasil ekstraksi nota           |
| `inventory`     | produk, persediaan, dan pergerakan stok       |
| `receivables`   | piutang dan penerimaan pembayaran             |
| `payables`      | utang dan pembayaran                          |
| `mentors`       | persetujuan serta aktivitas pembina           |
| `reports`       | ringkasan dan laporan keuangan                |
| `notifications` | notifikasi dan status pengiriman              |
| `sync`          | idempotensi dan sinkronisasi offline          |
| `audit`         | audit trail immutable                         |
