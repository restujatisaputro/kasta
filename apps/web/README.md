# KASTA Web

Website KASTA berbasis SvelteKit, TypeScript, Tailwind CSS, Zod, dan Apache ECharts.

```bash
pnpm install
pnpm --filter kasta_web dev
pnpm --filter kasta_web check
pnpm --filter kasta_web test
pnpm --filter kasta_web build
```

Nilai `PUBLIC_*` masuk ke browser dan tidak boleh berisi secret. Seluruh akses API harus melewati
`src/lib/api` agar autentikasi, error mapping, dan observability konsisten.

## Area dan rute

- Publik: `/`, `/tentang`, `/fitur`, `/bantuan`, `/kebijakan-privasi`,
  `/syarat-penggunaan`, `/login`, `/registrasi`, dan `/lupa-password`.
- UMKM: `/usaha/{businessId}` beserta transaksi, Uang Masuk, Uang Keluar, Foto Nota, produk,
  stok, utang, piutang, laporan, pembina, anggota, profil, dan pengaturan.
- Pembina: `/pembina` beserta UMKM binaan, detail UMKM, catatan, rekomendasi, jadwal,
  laporan agregat, dan permintaan akses.

## Fondasi desain

Token warna, permukaan, teks, border, focus ring, dan mode gelap berada di `src/app.css`.
Komponen di `src/lib/components` mencakup shell/layout, tombol, kartu, field, select, tabel,
grafik ECharts, empty/loading/error state, dialog konfirmasi, dan toast. Semua kontrol utama
memiliki target sentuh minimal 44 piksel dan fokus keyboard yang terlihat.

## Transaksi sederhana

Halaman `/usaha/{businessId}/transaksi` menyediakan Uang Masuk, Uang Keluar, Tambah Modal, dan Ambil
Uang Pribadi. Form dibatasi tiga langkah, memformat nominal sebagai Rupiah, dapat menyimpan draft,
menjadwalkan transaksi berulang, mengunggah foto bukti, mencari/memfilter, mengubah dengan alasan,
dan membatalkan melalui reversal.
