# Website KASTA

Website KASTA menggunakan SvelteKit, TypeScript, Tailwind CSS, Zod, dan Apache ECharts. Antarmuka
dibagi menjadi area publik, ruang usaha, dan ruang pembina. Bahasa antarmuka mengutamakan istilah
yang digunakan pelaku UMKM seperti Uang Masuk, Uang Keluar, Utang, Piutang, dan Foto Nota.

## Struktur antarmuka

- `apps/web/src/app.css`: design tokens global, warna semantik, focus ring, mode gelap, serta kelas
  form dan kartu.
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
