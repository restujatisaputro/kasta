# Kontrak API

Kontrak publik berada di `packages/contracts/openapi/kasta-api.yaml`. API menggunakan
`/api/v1`, error mengikuti bentuk `ProblemDetails`, dan perubahan breaking memerlukan versi mayor
atau masa kompatibilitas yang disetujui.

Jalankan `scripts/export_openapi.py` untuk membandingkan skema FastAPI aktual dengan kontrak yang
dikomit. Tipe web dan Android nantinya dihasilkan dari OpenAPI, bukan ditulis ulang manual.

Spesifikasi perilaku endpoint transaksi sederhana dan protokol sinkronisasi tersedia di
[`../modules/transaksi-sederhana.md`](../modules/transaksi-sederhana.md).
