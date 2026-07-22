# Strategi Environment

## Matriks

| Environment  | Tujuan                        | Data                 | Infrastruktur          | Debug                    |
| ------------ | ----------------------------- | -------------------- | ---------------------- | ------------------------ |
| `local`      | Pengembangan pribadi          | Sintetis             | Docker Compose/lokal   | Aktif                    |
| `test`       | Unit dan integration otomatis | Ephemeral            | Proses/containers CI   | Nonaktif kecuali failure |
| `staging`    | UAT dan rehearsal rilis       | Sintetis/tersamarkan | Menyerupai produksi    | Nonaktif                 |
| `production` | Pengguna nyata                | Riil dan sensitif    | HA, backup, monitoring | Nonaktif                 |

Artefak aplikasi yang sama dipromosikan dari staging ke production; konfigurasi diberikan saat
runtime. Image tidak dibangun ulang hanya untuk mengganti environment.

## Sumber konfigurasi

- `.env.example`: katalog nama variabel dan default lokal nonrahasia.
- `.env`: override lokal, diabaikan Git.
- API: variabel berprefix `KASTA_`, dibaca dan divalidasi Pydantic Settings.
- Web: hanya nilai aman untuk browser memakai `PUBLIC_`; secret tetap di server/secret manager.
- Android: `local.properties` atau Gradle property untuk developer; BuildConfig per build type.
- Staging/production: secret manager/platform environment, bukan file dalam repository.

Urutan precedence lokal: environment process > `.env` > default kode yang aman. Aplikasi harus
gagal saat startup bila konfigurasi wajib hilang atau nilai development dipakai di production.

## Struktur `.env`

Template root mengelompokkan nilai menjadi:

1. identitas runtime dan observability;
2. PostgreSQL;
3. autentikasi/JWT;
4. MinIO/object storage;
5. konfigurasi public website;
6. pin image container.

Aturan keamanan:

- jangan simpan secret asli pada `PUBLIC_*`, image, log, fixture, atau repository;
- gunakan kredensial berbeda per environment dan least privilege;
- signing key JWT produksi dikelola dan dirotasi terpisah;
- koneksi produksi memakai TLS dan database/object storage tidak diekspos langsung;
- backup terenkripsi dengan akun dan lifecycle berbeda dari runtime utama.
