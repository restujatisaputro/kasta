# KASTA Android

Aplikasi Android KASTA dengan namespace dan application ID `id.kasta.app`. Aplikasi memakai Kotlin,
Jetpack Compose, Material 3, Navigation Compose, Room, Retrofit, WorkManager, CameraX, ML Kit,
Coroutines, Flow, DataStore, dan Hilt. Progres profil usaha disimpan di Room, tetapi password,
kode verifikasi, dan token tidak disimpan pada database perangkat.

## Navigasi dan arsitektur

Navigasi bawah menyediakan Beranda, Transaksi, Foto Nota, Laporan, dan Lainnya. Alur aplikasi
dimulai dari Splash, lalu Login atau Registrasi dan Onboarding. Menu Lainnya membuka Produk, Stok,
Utang, Piutang, Pembina, Profil, Pengaturan, Status Sinkronisasi, dan Penyelesaian Konflik.

Beranda memakai Room sebagai sumber utama untuk saldo, uang masuk/keluar hari ini, perkiraan laba
bulanan, dan transaksi terbaru. Struktur baru mengikuti pembagian pragmatis `presentation`, `domain`,
`data/repository`, `data/local`, dan `data/remote`. Compose Preview tersedia untuk dashboard,
autentikasi, komponen utama, menu Lainnya, dan pengaturan.

## Setup

Gunakan JDK 17 dan Android SDK 35. Gradle Wrapper 8.11.1 sudah menjadi bagian repository, sehingga
Gradle global tidak diperlukan:

```bash
chmod +x gradlew # diperlukan sekali bila mode executable tidak terbawa saat checkout
./gradlew assembleDebug
```

Salin `local.properties.example` ke `local.properties`, sesuaikan `sdk.dir`, dan jangan commit file
tersebut. Base URL emulator dapat diatur dengan:

```properties
KASTA_API_BASE_URL=http://10.0.2.2:8080/api/v1/
```

## Quality commands

```bash
./gradlew ktlintCheck lintDebug testDebugUnitTest
./gradlew ktlintFormat
./gradlew installDebug
```

## Alur onboarding

Layar Android menyediakan sembilan langkah dari pembuatan akun sampai tutorial singkat. Draft mulai
disimpan setelah akun terverifikasi. Setelah selesai, API membuat usaha dan layar menampilkan profil
usaha dari response yang sama. Pengujian Compose utama berada di `app/src/androidTest`.

## Transaksi offline-first

Empat menu transaksi memakai alur tiga langkah. Room menyimpan draft dan transaksi lokal dengan
nilai Rupiah bertipe `Long`; WorkManager mengirim antrean ketika jaringan tersedia melalui endpoint
`/sync/push` dan menarik perubahan memakai cursor melalui `/sync/pull`. DataStore menyimpan ID
perangkat, cursor, dan waktu sinkronisasi terakhir. Konflik transaksi keuangan tidak ditimpa otomatis
dan diselesaikan dari halaman Status Sinkronisasi. Foto URI tetap lokal sampai transaksi mendapat ID
server, lalu file diunggah ke endpoint receipt. Pencarian dan filter bekerja pada data Room sehingga
tetap tersedia tanpa jaringan. Rincian protokol ada di `documentation/offline-sync.md`.

## Foto Nota

Menu Foto Nota memakai CameraX untuk preview/capture dan analisis luminance guna menandai dokumen.
Foto dikoreksi perspektif, dipotong, dibuat grayscale dengan contrast stretching, lalu dibaca oleh
Google ML Kit Text Recognition. Parser lokal memberi pratinjau nama toko, tanggal, nomor nota, item,
total, pembayaran, jenis transaksi, dan kategori sebelum upload. Backend mengembalikan confidence dan
kandidat duplikat; transaksi baru dibuat setelah pengguna menekan “Konfirmasi dan Buat Transaksi”.

Jika upload gagal, layar mempertahankan file cache dan menyediakan “Coba lagi”. Persistensi antrean
scan lintas restart aplikasi menggunakan Room/WorkManager belum termasuk MVP ini dan tercatat sebagai
peningkatan produksi pada `documentation/modules/foto-nota.md`.
