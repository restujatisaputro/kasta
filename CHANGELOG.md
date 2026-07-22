# Changelog

Semua perubahan penting KASTA dicatat di dokumen ini.

## Unreleased

- Menambahkan fondasi monorepo KASTA untuk API FastAPI, website SvelteKit, dan aplikasi Android.
- Menambahkan migration PostgreSQL, modul accounting double-entry, autentikasi, otorisasi, tenant isolation, RLS, OCR, offline sync, laporan, notifikasi, pembina, serta inventory dan kewajiban.
- Menambahkan Docker Compose development/production, Caddy HTTPS, backup/restore, workflow CI, dan dokumentasi operasional.
- Menambahkan katalog unit/integration/API/security test dan validasi struktur/database.

## Catatan validasi

- Validasi struktur dan rancangan database lulus.
- Validasi konfigurasi Docker Compose development, API, dan production lulus.
- Validasi Caddyfile production lulus.
- Pytest lokal menunggu instalasi dependency Python; CI menjalankan test melalui workflow resmi.
