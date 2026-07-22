# ADR 0001: Menggunakan modular monolith untuk backend

- Status: accepted
- Tanggal: 2026-07-21

## Konteks

KASTA membutuhkan konsistensi transaksi double-entry, audit, dan pengembangan MVP oleh tim yang
belum memerlukan kompleksitas operasional microservices.

## Keputusan

Backend dibangun sebagai satu aplikasi FastAPI dan satu unit deploy, dengan package per bounded
context, kepemilikan tabel yang jelas, serta larangan akses repository lintas modul.

## Konsekuensi

Transaksi database dan deployment lebih sederhana. Disiplin batas modul wajib ditegakkan melalui
review dan test arsitektur. Modul dapat diekstrak hanya setelah kebutuhan skala/organisasi terukur.
