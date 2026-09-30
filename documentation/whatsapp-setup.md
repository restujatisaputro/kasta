# Menyiapkan pengiriman WhatsApp KASTA

Kode verifikasi KASTA dikirim lewat email atau WhatsApp. Jalur email siap pakai
begitu `KASTA_MAIL_ENABLED=true` dan SMTP terisi. Jalur WhatsApp memerlukan
WhatsApp Business Platform milik Meta, dan dokumen ini memuat langkah lengkapnya
beserta jebakan yang sudah ditemui.

## Yang perlu dipahami lebih dulu

**Yang wajib terdaftar adalah nomor pengirim, bukan penerima.** Pengguna KASTA
menerima kode di WhatsApp biasa; itu memang cara kerjanya. Hanya nomor yang
dipakai server untuk mengirim yang harus terdaftar di Cloud API.

**Jangan pakai nomor pribadi sebagai pengirim.** Nomor yang didaftarkan ke Cloud
API tidak boleh sedang aktif di WhatsApp biasa maupun aplikasi WhatsApp Business.
Mendaftarkannya akan memutus WhatsApp nomor itu di ponsel.

**Registrasi tidak berhenti bila WhatsApp mati.** Pengguna dapat mendaftar dengan
email. Yang berbahaya adalah mematikan keduanya: bila `KASTA_MAIL_ENABLED` dan
`KASTA_WHATSAPP_ENABLED` sama-sama `false`, `_deliver_batch` langsung
mengembalikan 0 dan kode verifikasi hanya mengendap di outbox tanpa pesan error.

## Jalur pengujian tanpa biaya

Meta menyediakan nomor tes gratis yang dapat mengirim ke maksimal lima nomor
penerima terdaftar. Jalur ini cukup untuk memverifikasi seluruh rantai tanpa
membeli nomor, tanpa verifikasi bisnis, dan tanpa mengganggu nomor pribadi.

### 1. Buat aplikasi Meta

Buka `developers.facebook.com`, masuk dengan akun Facebook biasa, buat app bertipe
**Business**, lalu tambahkan produk **WhatsApp**.

### 2. Daftarkan nomor penerima tes

Pada **WhatsApp > API Setup**, bagian **To**, pilih **Manage phone number list**
dan tambahkan nomor tujuan dalam format internasional. Masukkan kode konfirmasi
yang dikirim ke WhatsApp nomor tersebut.

Melewatkan langkah ini menghasilkan error **131030**.

### 3. Salin kredensial

Pada halaman yang sama tersedia **Phone number ID** milik nomor tes dan
**temporary access token** yang berlaku 24 jam. Token sementara cukup untuk
pengujian; produksi memerlukan token permanen dari System User.

### 4. Buat template

Pada **WhatsApp Manager > Message templates > Create template**:

| Field    | Nilai                 |
| -------- | --------------------- |
| Nama     | `kasta_verification`  |
| Kategori | **Authentication**    |
| Bahasa   | **Indonesian** (`id`) |
| Tombol   | **Copy code**         |

Kategori dan tombol bukan detail kosmetik. Template Authentication mewajibkan kode
dikirim dua kali, di body dan sebagai parameter tombol salin-kode; mengirim body
saja menghasilkan error **132000**. Perilaku ini dikendalikan
`KASTA_WHATSAPP_TEMPLATE_OTP_BUTTON`, yang bernilai `true` secara default. Bila
template yang dipakai berkategori Utility atau Marketing tanpa tombol, setel
variabel tersebut ke `false`.

Tunggu status template menjadi **Approved** sebelum mengaktifkan pengiriman.

### 5. Uji sebelum menyentuh produksi

Gunakan `scripts/check-whatsapp.py`. Skrip tersebut membentuk payload yang sama
persis dengan `delivery.py`, membaca token dari environment agar tidak tersimpan
di riwayat shell, dan menerjemahkan kode error Meta.

```bash
export KASTA_WHATSAPP_PHONE_NUMBER_ID=...
export KASTA_WHATSAPP_ACCESS_TOKEN=...
python scripts/check-whatsapp.py +628123456789
```

Menguji lewat skrip lebih dulu memisahkan dua kemungkinan yang mudah tertukar:
bila skrip berhasil tetapi server tetap gagal, masalahnya pada konfigurasi server;
bila skrip gagal, masalahnya pada template atau kredensial Meta.

### 6. Aktifkan di server

Setelah skrip berhasil, isi `/opt/kasta/.env.production`:

```properties
KASTA_WHATSAPP_ENABLED=true
KASTA_WHATSAPP_PHONE_NUMBER_ID=<phone number id>
KASTA_WHATSAPP_ACCESS_TOKEN=<token permanen>
KASTA_WHATSAPP_TEMPLATE_NAME=kasta_verification
KASTA_WHATSAPP_TEMPLATE_LANGUAGE=id
KASTA_WHATSAPP_TEMPLATE_OTP_BUTTON=true
```

`KASTA_WHATSAPP_PHONE_NUMBER_ID` dan `KASTA_WHATSAPP_ACCESS_TOKEN` wajib terisi
saat `KASTA_WHATSAPP_ENABLED=true`; API menolak start bila kosong.

Perubahan environment memerlukan container API dijalankan ulang, bukan sekadar
reload.

### 7. Pasang webhook status pengiriman

Respons Graph API `200` hanya berarti Meta menerima permintaan, bukan pesan sampai.
Kegagalan seperti nomor tidak terjangkau (131026) baru dilaporkan belakangan lewat
webhook. KASTA mencatat status itu di log; pesan masuk diabaikan.

1. Buat verify token acak, misalnya `openssl rand -hex 32`.
2. Salin **App secret** dari **App settings > Basic** di aplikasi Meta.
3. Tambahkan keduanya ke `/opt/kasta/.env.production`, lalu jalankan ulang container
   API. Keduanya wajib diisi bersamaan; bila keduanya kosong, endpoint menjawab 404.

   ```properties
   KASTA_WHATSAPP_WEBHOOK_VERIFY_TOKEN=<verify token>
   KASTA_WHATSAPP_APP_SECRET=<app secret>
   ```

4. Di **WhatsApp > Configuration > Webhook**, pilih **Edit** dan isi:

   | Field        | Nilai                                                 |
   | ------------ | ----------------------------------------------------- |
   | Callback URL | `https://kasta.admniaga.com/api/v1/webhooks/whatsapp` |
   | Verify token | verify token dari langkah 1                           |

   Meta langsung memanggil `GET` dengan `hub.challenge`; tombol **Verify and save**
   hanya berhasil bila container sudah memuat token yang sama.

5. Pada daftar **Webhook fields**, **Subscribe** ke `messages`. Field ini membawa
   status `sent`, `delivered`, `read`, dan `failed`.

Setiap `POST` divalidasi dengan header `X-Hub-Signature-256` (HMAC-SHA256 isi
permintaan memakai app secret). Tanda tangan yang salah dijawab `401`.

## Membaca kegagalan

Sejak perbaikan pada `delivery.py`, isi error Graph API ikut tercatat, bukan hanya
kode HTTP.

```bash
docker logs --tail 100 kasta-production-api-1 2>&1 | grep -i "whatsapp\|delivery failed"
```

Log pengiriman memuat `whatsapp_message_id`; cari id yang sama untuk melihat status
lanjutan yang dilaporkan webhook:

```bash
docker logs kasta-production-api-1 2>&1 | grep "wamid.<id>"
```

| Kode   | Arti                                              | Tindakan                                                       |
| ------ | ------------------------------------------------- | -------------------------------------------------------------- |
| 132000 | Jumlah parameter tidak cocok                      | Sesuaikan `KASTA_WHATSAPP_TEMPLATE_OTP_BUTTON` dengan template |
| 132001 | Template tidak ditemukan pada bahasa tersebut     | Periksa nama template dan kode bahasa                          |
| 132015 | Template belum disetujui atau sedang dijeda       | Tunggu persetujuan Meta                                        |
| 131030 | Nomor tujuan belum terdaftar sebagai penerima tes | Tambahkan nomor pada daftar penerima                           |
| 190    | Access token tidak valid atau kedaluwarsa         | Terbitkan token baru, gunakan System User untuk produksi       |
| 133010 | Nomor pengirim belum terdaftar di Cloud API       | Selesaikan registrasi nomor pengirim                           |
| 131026 | Pesan tidak dapat diantar (via webhook)           | Pastikan nomor tujuan aktif di WhatsApp                        |

Kegagalan tidak langsung menghanguskan pesan. Percobaan ulang memakai backoff
bertingkat dari 5 detik hingga 8 jam, dengan batas sepuluh percobaan.

## Menuju produksi

Nomor tes hanya melayani lima penerima terdaftar dan tidak cocok untuk pengguna
sungguhan. Produksi memerlukan nomor khusus yang belum pernah dipakai WhatsApp,
verifikasi bisnis Meta, serta token permanen dari System User. Verifikasi bisnis
dapat memakan beberapa hari, jadi mulailah lebih awal bila WhatsApp direncanakan
sebagai kanal utama.
