# Laporan Keuangan KASTA

Modul laporan menyajikan kondisi usaha dengan bahasa sederhana tanpa meminta pengguna memahami
debit dan kredit. Seluruh angka keuangan utama dihitung dari `journal_entries` dan
`journal_lines`, bukan dari nilai ringkasan pada tabel transaksi. Transaksi yang dibatalkan tetap
ada dan dinetralkan oleh jurnal pembalik.

## Isi laporan

- Ringkasan pemasukan, pengeluaran, perkiraan laba, arus kas, utang, piutang, dan persediaan.
- Uang masuk dan keluar serta arus kas sederhana.
- Laporan laba rugi dan laporan posisi keuangan.
- Penjualan dan pengeluaran per kategori.
- Utang dan piutang yang belum lunas.
- Persediaan, produk paling laku, dan perbandingan enam bulan terakhir.
- Lima grafik: pemasukan versus pengeluaran, tren laba, kategori pengeluaran, penjualan harian,
  dan produk terlaris.
- Penjelasan sederhana di bawah laporan utama agar pengguna tidak hanya membaca tabel.

## Endpoint dan izin

Semua path diawali `/api/v1/businesses/{business_id}/reports`.

| Method | Path                | Izin            | Hasil                   |
| ------ | ------------------- | --------------- | ----------------------- |
| GET    | `/financial`        | `report.read`   | JSON untuk layar/grafik |
| GET    | `/financial/export` | `report.export` | PDF, XLSX, atau CSV     |

Endpoint selalu memeriksa keanggotaan tenant dan permission. `branch_id` juga diperiksa terhadap
tenant. Pada MVP, satu `business` diperlakukan sebagai satu cabang sehingga `branch_id` harus sama
dengan `business_id`. Model cabang terpisah dapat ditambahkan kemudian tanpa mengubah bentuk filter.

## Filter

| Parameter        | Nilai                                                          |
| ---------------- | -------------------------------------------------------------- |
| `period`         | `DAY`, `WEEK`, `MONTH`, `QUARTER`, `YEAR`, atau `CUSTOM`       |
| `reference_date` | Tanggal acuan selain periode kustom                            |
| `date_from/to`   | Wajib untuk `CUSTOM`; rentang maksimal sepuluh tahun           |
| `category`       | Kunci akun pemasukan/pengeluaran, misalnya `SALES` atau `RENT` |
| `payment_method` | `CASH`, `BANK_TRANSFER`, `QRIS`, `E_WALLET`, atau `CARD`       |
| `branch_id`      | Cabang yang boleh diakses pengguna                             |
| `format`         | Khusus ekspor: `PDF`, `XLSX`, atau `CSV`                       |

Filter kategori dan metode memilih jurnal yang terkait transaksi tersebut lalu tetap membaca
seluruh baris jurnalnya. Cara ini menjaga pasangan jurnal tetap lengkap. Laporan posisi keuangan
dengan filter transaksi tertentu adalah tampilan analitis, bukan neraca resmi tanpa filter.

## Sumber dan aturan perhitungan

- Pemasukan dan pengeluaran berasal dari baris akun kategori `REVENUE` dan `EXPENSE`.
- Kas masuk/keluar berasal dari perubahan akun `CASH`, `BANK`, dan `DIGITAL_WALLET`.
- Posisi keuangan memakai seluruh jurnal sampai tanggal akhir laporan, bukan hanya jurnal di dalam
  periode.
- Perkiraan laba berjalan ditambahkan ke dana pemilik agar persamaan posisi keuangan tetap terbaca.
- Penjualan produk hanya dihitung jika transaksi memiliki jurnal pendapatan yang memenuhi filter.
- Jurnal pembalik mengurangi hasil periode sesuai tanggal pembatalannya.
- Nilai utama utang, piutang, dan persediaan berasal dari saldo jurnal pada tanggal akhir laporan.
  Sisa daftar tagihan dan stok operasional tetap ditampilkan sebagai pembanding agar selisih
  rekonsiliasi terlihat.
- Nilai uang diproses sebagai `Decimal`/`NUMERIC(18,2)`, bukan `float`.

## Output

- Layar web memakai Apache ECharts dan layar Android memakai grafik batang ringan berbasis Compose.
- PDF berisi halaman ringkasan dan laporan utama yang siap dibaca/dicetak.
- XLSX memiliki lembar terpisah untuk ringkasan, laba rugi, posisi keuangan, arus kas, penjualan,
  pengeluaran, produk, dan perbandingan bulanan.
- CSV memakai UTF-8 BOM agar teks Indonesia dan Rupiah terbuka dengan baik di aplikasi spreadsheet.

Android memakai pemilih dokumen sistem sehingga pengguna menentukan sendiri lokasi file. Website
mengunduh file dengan nama `laporan-kasta` dan ekstensi yang sesuai.

## Pemeriksaan dan rekonsiliasi

Respons memuat `context.source = JOURNAL` dan `balance_sheet.difference`. Pengujian otomatis secara
sengaja mengubah nominal header transaksi setelah jurnal diposting; angka laporan tidak ikut berubah.
Hal ini menjadi regression guard bahwa jurnal tetap merupakan sumber kebenaran laporan.
