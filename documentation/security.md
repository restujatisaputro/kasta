# Keamanan KASTA

Dokumen ini menetapkan baseline keamanan untuk API, web, Android, PostgreSQL, MinIO,
backup, dan proses rilis KASTA. Kontrol harus diuji ulang pada setiap rilis.

## Ringkasan kontrol

- Password menggunakan Argon2id (`m=65536`, `t=3`, `p=4`) dan otomatis di-rehash saat
  parameter berubah.
- Access token JWT berumur 15 menit, memuat issuer, audience, `jti`, session, dan
  `business_id`. Refresh token bersifat opaque, hanya hash HMAC yang disimpan, dirotasi
  setiap penggunaan, dan reuse mencabut session.
- Login dilindungi rate limit kombinasi identifier–IP dan lockout per akun. Endpoint API
  memperoleh burst limit tambahan. Pada deployment multi-replika, gateway/WAF tetap harus
  menerapkan rate limit terdistribusi.
- Browser hanya boleh mengirim credential dari origin CORS yang didaftarkan. Autentikasi
  memakai header `Authorization`, bukan cookie, sehingga CSRF token tidak diperlukan.
  Jika autentikasi cookie ditambahkan kelak, SameSite dan synchronizer/double-submit token
  menjadi wajib sebelum fitur dirilis.
- Semua endpoint bisnis membandingkan `business_id` URL/payload dengan klaim token,
  membership aktif, permission, dan—untuk pembina/dukungan—scope persetujuan aktif.
- Tabel tenant memakai PostgreSQL RLS dan `FORCE ROW LEVEL SECURITY`. Runtime role tidak
  boleh superuser, owner tabel, atau mempunyai `BYPASSRLS`.
- Bucket MinIO bersifat privat. Signed URL hanya dibuat setelah permission dan objek
  `(business_id, id)` tervalidasi, dengan masa berlaku default lima menit.
- Gambar diverifikasi dari isi aktual oleh Pillow, MIME yang diklaim harus cocok, ukuran
  dibatasi, decompression bomb ditolak, dan ClamAV dapat diaktifkan dengan mode fail-closed.
- Audit log append-only melalui RLS dan trigger PostgreSQL. Secret disuplai melalui secret
  manager atau `/run/secrets`; tidak boleh disimpan pada repository maupun image.
- Android mengenkripsi access/refresh token dengan AES-256-GCM; key non-exportable disimpan
  oleh Android Keystore. Backup aplikasi dinonaktifkan agar ciphertext session tidak dipindah
  ke perangkat yang tidak memiliki key terkait.

## Threat model STRIDE

| Kategori               | Ancaman utama                                                           | Aset/dampak                | Kontrol                                                                                                            | Residual risk/tindakan                                                        |
| ---------------------- | ----------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Spoofing               | Credential stuffing, pencurian refresh token, header proxy palsu        | Akun dan session           | Argon2id, lockout akun, rate limit, rotasi refresh, session revocation, trusted proxy CIDR                         | Tambahkan MFA untuk admin dan notifikasi login baru sebelum produksi luas     |
| Tampering              | Manipulasi `business_id`, jurnal, nota, audit log, atau backup          | Integritas keuangan        | Permission dependency, transaksi DB, jurnal seimbang, RLS FORCE, audit append-only, checksum backup                | Tanda tangan release dan immutable backup masih dikontrol platform deployment |
| Repudiation            | Pengguna/pembina menyangkal perubahan atau akses                        | Bukti aktivitas            | Audit actor, request ID, revision/reversal, log akses pembina/dukungan                                             | Sinkronisasi jam host dan retensi log wajib dimonitor                         |
| Information disclosure | IDOR lintas UMKM, bucket publik, log/token bocor, export salah pengguna | Data pribadi dan finansial | Token-bound tenant, query `(business_id,id)`, RLS, signed URL pendek, bucket privat, redaksi log, export self-only | Screenshot/perangkat pengguna berada di luar kontrol server                   |
| Denial of service      | Login flood, request flood, upload besar/decompression bomb, OCR mahal  | Ketersediaan               | Rate limit, batas 8 MB/8192 px, validasi sebelum proses, timeout scanner, resource limit proxy/container           | Terapkan WAF/CDN dan quota terdistribusi saat API direplikasi                 |
| Elevation of privilege | Role/permission dimanipulasi, admin melewati consent, RLS bypass        | Seluruh tenant             | Permission granular, support grant terbatas waktu dan diaudit, runtime role least privilege, RLS FORCE             | Review grant admin dan role database setiap kuartal                           |

## Alur keamanan autentikasi

```mermaid
sequenceDiagram
    participant C as Klien
    participant API as FastAPI
    participant DB as PostgreSQL
    C->>API: Login + business_id + device
    API->>DB: Cek rate limit dan lockout akun
    API->>API: Verifikasi Argon2id
    API->>DB: Cek membership/scope aktif
    API->>DB: Simpan hash refresh token dan session
    API-->>C: Access JWT 15 menit + refresh opaque
    C->>API: Refresh token
    API->>DB: SELECT FOR UPDATE session
    API->>DB: Ganti hash refresh dan naikkan counter
    API-->>C: Pasangan token baru
    Note over API,DB: Reuse token lama mencabut session
```

## Upload dan object storage

Urutan pemeriksaan: batas byte → MIME deklarasi → ClamAV (jika aktif) → deteksi format
aktual → verifikasi decoder → batas dimensi → kecocokan MIME → penyimpanan bucket privat.
Nama objek selalu dibuat server dan diawali `businesses/{business_id}`; nama berkas pengguna
tidak menjadi object key.

Aktifkan scanner pada production:

```env
KASTA_MALWARE_SCAN_ENABLED=true
KASTA_MALWARE_SCAN_HOST=clamav
KASTA_MALWARE_SCAN_PORT=3310
KASTA_MALWARE_SCAN_FAIL_CLOSED=true
```

Untuk lokal dengan Compose:

```bash
docker compose --profile security --env-file .env \
  -f infrastructure/docker/compose.yaml up -d --build
```

## Backup terenkripsi dan restore

Gunakan key `age` dari secret manager. Private identity tidak boleh berada pada host aplikasi
atau repository. Backup dikirim ke storage berbeda akun/region dan memakai object lock bila
tersedia.

```bash
export POSTGRES_BACKUP_URL='postgresql://backup-user:***@postgres:5432/kasta'
export BACKUP_AGE_RECIPIENT='age1...'
./scripts/backup/backup-postgres.sh

export BACKUP_AGE_IDENTITY='/run/secrets/kasta-backup-age-key'
export POSTGRES_RESTORE_URL='postgresql://restore-user:***@restore-db:5432/kasta_restore_test'
./scripts/backup/restore-postgres.sh backups/kasta-postgres-<timestamp>.dump.age
```

Restore wajib dilakukan ke lingkungan terisolasi dan diverifikasi dengan migration head,
jumlah record, jurnal seimbang, checksum objek, serta test RLS. Jangan menjalankan restore
uji ke database produksi.

## Retention dan penghapusan akun

- Data transaksi, jurnal, dan bukti keuangan: minimal 1.825 hari (5 tahun), lalu mengikuti
  kebijakan hukum/kontrak yang berlaku.
- Audit log: minimal 2.555 hari (7 tahun) dan append-only.
- Token sekali pakai, outbox terkirim, session kedaluwarsa/dicabut, dan rate-limit record:
  90 hari; terapkan dengan `scripts/postgres/apply-retention.sql`.
- Penghapusan akun membutuhkan password dan frasa konfirmasi. Akun pemilik terakhir tidak
  dapat dihapus sebelum kepemilikan dialihkan. Identifier dianonimkan, seluruh session
  dicabut, membership dinonaktifkan, sementara referensi audit/keuangan pseudonim tetap ada.
- Export data hanya berisi data subjek yang sedang login dan event auditnya pada tenant aktif.

## Secrets management

Production menggunakan secret manager platform atau Docker/Kubernetes secrets yang dipasang
ke `/run/secrets`. KASTA menolak nilai development, secret pendek, origin non-HTTPS, access
token di atas 15 menit, dan endpoint object non-HTTPS saat `KASTA_ENVIRONMENT=production`.
Rotasikan JWT signing key, token hash key, kredensial database/MinIO, dan encryption key
melalui prosedur dual-key/maintenance yang terencana; rotasi refresh key dapat memaksa login
ulang seluruh perangkat.

## Security checklist rilis

### Identity dan session

- [ ] Argon2id dan test parameter hash lulus.
- [ ] JWT maksimal 15 menit; issuer/audience/type/jti diverifikasi.
- [ ] Refresh rotation, reuse detection, logout satu/semua perangkat lulus.
- [ ] Lockout akun dan rate-limit endpoint sensitif aktif.
- [ ] Akun admin memakai MFA pada identity provider/deployment console.

### Akses dan data

- [ ] Semua route tenant memakai permission dependency dan query `(business_id,id)`.
- [ ] Migration head sudah diterapkan dengan schema owner terpisah.
- [ ] Runtime role `NOSUPERUSER`, `NOBYPASSRLS`, bukan owner tabel.
- [ ] Test PostgreSQL RLS anggota, pembina, dan support grant lulus.
- [ ] Audit log menolak UPDATE dan DELETE.
- [ ] Export dan penghapusan akun diuji; pemilik terakhir tidak dapat menghapus akun.

### Network, web, dan berkas

- [ ] HTTPS/HSTS aktif dan CORS hanya memuat domain resmi.
- [ ] Security headers diverifikasi dari domain publik, bukan hanya container API.
- [ ] Bucket tidak anonymous; signed URL maksimal 15 menit.
- [ ] Batas upload, actual MIME, decompression bomb, dan file rusak diuji.
- [ ] ClamAV aktif fail-closed atau pengecualian risiko disetujui tertulis.

### Operasi dan supply chain

- [ ] Secret berasal dari secret manager dan hasil secret scan bersih.
- [ ] Dependabot, pip-audit, pnpm audit, dan dependency review lulus.
- [ ] Image dipin immutable/digest dan vulnerability scan tidak memiliki Critical/High terbuka.
- [ ] Backup PostgreSQL dan MinIO terenkripsi; checksum dan restore drill lulus.
- [ ] Retention job dijadwalkan dan hasilnya dicatat.
- [ ] Alert login flood, malware, 401/403/429 spike, dan perubahan grant aktif.

## Automated security test

```bash
uv run --project apps/api pytest apps/api/tests/test_security_hardening.py \
  apps/api/tests/test_authentication.py apps/api/tests/test_authorization.py \
  apps/api/tests/test_tenant_isolation.py
uv run --project apps/api ruff check --config apps/api/pyproject.toml apps/api scripts tests
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
```

CI juga menjalankan migration pada PostgreSQL 17, membuat runtime role least privilege, dan
menjalankan `scripts/postgres/test-rls.sql`. Dependency dengan severity High atau Critical
harus memblokir merge kecuali ada risk acceptance bertanggal dan pemilik mitigasi.
