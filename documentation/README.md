# Dokumentasi KASTA

- [Website KASTA](website.md)
- [Aplikasi Android KASTA](android.md)

Direktori ini adalah indeks dokumentasi yang hidup bersama kode.

| Dokumen                                              | Isi                                                      |
| ---------------------------------------------------- | -------------------------------------------------------- |
| [`repository-structure.md`](repository-structure.md) | Struktur lengkap dan fungsi setiap folder                |
| [`conventions.md`](conventions.md)                   | Penamaan file, branch, commit, format, dan lint          |
| [`environments.md`](environments.md)                 | Strategi local, test, staging, dan production            |
| [`development.md`](development.md)                   | Instalasi, run, test, migration, dan Compose             |
| [`database/`](database/)                             | ERD, data dictionary, RLS, audit, dan DDL PostgreSQL     |
| [`adr/`](adr/)                                       | Architecture Decision Record                             |
| [`operations/runbooks/`](operations/runbooks/)       | Prosedur operasional dan respons insiden                 |
| [`api/`](api/)                                       | Catatan penggunaan dan publikasi kontrak API             |
| [`modules/foto-nota.md`](modules/foto-nota.md)       | Kamera, OCR, review, duplikat, dan penyimpanan nota      |
| [`obligations.md`](obligations.md)                   | Utang, piutang, pembayaran, aging, dan pengingat         |
| [`reports.md`](reports.md)                           | Laporan berbasis jurnal, filter, grafik, dan ekspor      |
| [`mentors.md`](mentors.md)                           | Dashboard, indikator, tindak lanjut, dan audit pembina   |
| [`offline-sync.md`](offline-sync.md)                 | Room, WorkManager, version, cursor, dan konflik data     |
| [`security.md`](security.md)                         | Hardening, STRIDE, checklist, backup, dan retention      |
| [`testing/`](testing/)                               | Strategi QA, test case, traceability, dan hasil aktual   |
| [`demo-data.md`](demo-data.md)                       | Seed demo fiktif, akun sementara, dan cara menjalankan   |
| [`deployment.md`](deployment.md)                     | Compose production, HTTPS, backup, restore, dan rollback |

Dokumen sumber yang sudah ada tetap dipertahankan di root repository:

- `../Rancangan_Arsitektur_Sistem_KASTA_Modular_Monolith_v0.1.md`
- `../Dokumen_Kebutuhan_Sistem_KASTA_v0.1.docx`

Keputusan arsitektur yang mengubah batas modul, data tenant, keamanan, kontrak publik, atau
topologi deployment harus dicatat sebagai ADR baru.
