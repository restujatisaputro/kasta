# Website KASTA

Website KASTA menggunakan SvelteKit, TypeScript, Tailwind CSS, Zod, dan Apache ECharts. Antarmuka
dibagi menjadi area publik, ruang usaha, dan ruang pembina. Bahasa antarmuka mengutamakan istilah
yang digunakan pelaku UMKM seperti Uang Masuk, Uang Keluar, Utang, Piutang, dan Foto Nota.

## Struktur antarmuka

- `apps/web/src/app.css`: design tokens global, warna semantik, focus ring, mode gelap, serta kelas
  form dan kartu.
- `apps/web/static/brand`: logo KASTA dan latar hero resmi. Versi WebP dipakai sebagai sumber utama
  agar halaman tetap ringan, dengan PNG sebagai fallback.
- `apps/web/src/lib/components`: komponen reusable, layout, form, tabel, grafik, dan feedback state.
- `apps/web/src/lib/api`: satu pintu komunikasi HTTP ke API KASTA.
- `apps/web/src/routes`: halaman publik, UMKM, dan pembina.

Shell `AppShell` dan `MentorShell` menyediakan sidebar pada layar besar serta navigasi bawah pada
perangkat seluler. `MarketingShell` digunakan untuk halaman publik. Setiap halaman menyediakan
judul dokumen, heading utama, focus state, serta state kosong, memuat, atau gagal sesuai konteks.

## Menjalankan

```bash
pnpm install
pnpm --filter kasta_web dev
```

Website development tersedia di `http://localhost:5173`. Pada Docker Compose, reverse proxy
menyediakannya di `http://localhost:8080`.

## Identitas visual

Palet utama mengikuti logo KASTA: hijau-teal gelap untuk tindakan utama, sage lembut untuk bidang
pendukung, emas hangat untuk penekanan, dan krem-putih sebagai latar. Kelas `kasta-brand-hero`
memakai latar gelombang dan ilustrasi keuangan pada halaman publik serta onboarding. Komponen
`BrandLogo` menjadi sumber tunggal logo pada marketing shell, ruang usaha, ruang pembina, dan
halaman autentikasi.

## Motion dan feedback

Motion menggunakan durasi pendek dengan easing lembut agar terasa responsif tanpa mengganggu
pencatatan. Root layout menampilkan progress bar tipis saat perpindahan route, lalu setiap halaman
masuk dengan fade dan pergeseran kecil. Kartu, tombol, ikon, toast, dialog konfirmasi, dan skeleton
loading memiliki feedback yang konsisten. Semua animasi menghormati `prefers-reduced-motion`; pada
perangkat yang meminta pengurangan gerak, transisi dipersingkat dan animasi dekoratif dihentikan.

## Pemeriksaan kualitas

```bash
pnpm --filter kasta_web check
pnpm --filter kasta_web lint
pnpm --filter kasta_web test
pnpm --filter kasta_web build
```

Uji komponen memeriksa nama tabel untuk pembaca layar, empty state, dan penutupan dialog dengan
tombol Escape. Form autentikasi serta transaksi menggunakan Zod untuk validasi sisi pengguna;
backend tetap menjadi sumber validasi dan otorisasi akhir.
