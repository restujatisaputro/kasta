# Produk dan Stok KASTA

Modul inventori menyediakan data produk per UMKM, saldo stok, riwayat yang tidak dapat diubah,
peringatan stok minimum, produk terlaris, dan nilai persediaan sederhana. Semua endpoint berada di
`/api/v1/businesses/{business_id}/inventory` dan selalu melewati pemeriksaan tenant serta permission.

## Aturan utama

- `products.current_stock` adalah saldo cepat; sumber riwayatnya adalah `stock_movements`.
- Stok menggunakan `NUMERIC(18,3)`, sedangkan harga dan nilai menggunakan `NUMERIC(18,2)`.
- Saldo stok tidak boleh negatif. Perubahan yang melampaui stok tersedia menghasilkan HTTP 409.
- `transaction_items` dan `stock_movements` bersifat immutable dan tidak boleh dihapus permanen.
- Edit metadata produk tidak dapat mengubah stok. Gunakan stok masuk, stok keluar, penyesuaian,
  rusak, atau hilang agar alasan dan pelakunya tercatat.
- Penjualan dengan item produk mengurangi stok; pembelian menambah stok. Pembatalan membuat gerakan
  kebalikan. Revisi mengembalikan gerakan lama lalu menerapkan item baru.
- Jurnal, transaksi, item, gerakan stok, dan saldo produk memakai satu database transaction. Jika
  salah satu gagal, seluruh perubahan di-rollback.

## Endpoint ringkas

| Method | Path                               | Permission         | Fungsi                                        |
| ------ | ---------------------------------- | ------------------ | --------------------------------------------- |
| GET    | `/products`                        | `product.read`     | Daftar, cari, dan filter stok minimum         |
| POST   | `/products`                        | `product.create`   | Tambah produk dan stok awal                   |
| GET    | `/products/by-barcode/{barcode}`   | `product.read`     | Cari hasil scan barcode                       |
| PUT    | `/products/{product_id}`           | `product.update`   | Edit metadata produk                          |
| POST   | `/products/{product_id}/movements` | `stock.manage`     | Catat perubahan stok                          |
| GET    | `/movements`                       | `product.read`     | Riwayat stok                                  |
| GET    | `/summary`                         | `product.read`     | Nilai persediaan, stok minimum, dan terlaris  |
| POST   | `/products/import-csv`             | `inventory.import` | Impor maksimal 1.000 baris/2 MB secara atomik |
| GET    | `/products/export.xlsx`            | `inventory.export` | Ekspor workbook Excel                         |

## Format CSV

CSV harus UTF-8 dan memiliki header berikut:

```csv
sku,barcode,nama,kategori,satuan,harga_beli,harga_jual,stok_awal,stok_minimum,aktif
KOPI-001,8991234567890,Kopi Susu Botol,Minuman,PCS,8000,12000,10,5,ya
```

Satuan yang didukung: `PCS`, `BOX`, `PACK`, `KG`, `GRAM`, `LITER`, `ML`, `METER`, `SET`, dan
`UNIT`. Nilai `aktif` menerima `ya/tidak`, `true/false`, atau `1/0`. Jika satu baris tidak valid atau
SKU/barcode ganda, seluruh impor dibatalkan.

## Android dan barcode

Android menggunakan CameraX dan Google ML Kit Barcode Scanning. Nilai barcode yang terbaca dikirim
ke endpoint pencarian tenant; saldo stok tidak disimpan sebagai sumber kebenaran kedua di perangkat.
Saat offline, transaksi yang sudah ada tetap mengikuti antrean sinkronisasi Android. Perubahan stok
manual memerlukan koneksi pada versi MVP agar konflik stok dapat ditolak server secara langsung.
