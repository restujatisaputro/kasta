# Panduan Kontribusi KASTA

1. Buat branch sesuai `documentation/conventions.md`.
2. Batasi perubahan pada satu tujuan yang dapat direview.
3. Tambahkan atau perbarui test untuk perilaku yang berubah.
4. Jalankan format, lint, test, dan validasi kontrak sebelum membuka pull request.
5. Jelaskan migration, dampak tenant, keamanan, dan cara rollback di deskripsi pull request.

Perubahan kontrak API dimulai dari `packages/contracts/openapi/kasta-api.yaml`. Perubahan database
harus menyertakan migration Alembic yang bersifat forward-compatible selama rolling deployment.
Jangan membuat dependensi langsung antarmodul bisnis; gunakan application service atau port yang
dimiliki modul tujuan.
