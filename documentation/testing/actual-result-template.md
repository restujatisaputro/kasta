# Template Actual Result KASTA

Gunakan satu salinan bagian berikut untuk setiap test case manual, exploratory, performance, atau
restore. Untuk automation, tautkan job dan artifact tanpa menyalin secret atau data pribadi.

## Formulir eksekusi

| Field                     | Nilai                                                          |
| ------------------------- | -------------------------------------------------------------- |
| Test case ID              | `QA-...`                                                       |
| Judul                     |                                                                |
| Jenis test                | Unit / Integration / API / Database / RLS / UI / E2E / lainnya |
| Modul                     |                                                                |
| Tujuan                    |                                                                |
| Severity                  | Critical / High / Medium / Low                                 |
| Priority                  | P0 / P1 / P2 / P3                                              |
| Build / commit SHA        |                                                                |
| Versi API / web / Android |                                                                |
| Alembic revision          |                                                                |
| Lingkungan                | Local / CI / Staging / Restore test                            |
| Perangkat, OS, browser    |                                                                |
| Tenant dan akun sintetis  |                                                                |
| Tanggal dan zona waktu    |                                                                |
| Penguji                   |                                                                |
| Prasyarat                 |                                                                |

### Langkah dan hasil

| No. | Langkah | Hasil yang diharapkan | Hasil aktual | Status                          |
| --: | ------- | --------------------- | ------------ | ------------------------------- |
|   1 |         |                       |              | PASS / FAIL / BLOCKED / NOT RUN |
|   2 |         |                       |              | PASS / FAIL / BLOCKED / NOT RUN |
|   3 |         |                       |              | PASS / FAIL / BLOCKED / NOT RUN |

### Kesimpulan

| Field                  | Nilai                                                              |
| ---------------------- | ------------------------------------------------------------------ |
| Status akhir           | PASS / FAIL / BLOCKED / NOT RUN                                    |
| Durasi                 |                                                                    |
| Severity jika gagal    | Critical / High / Medium / Low (isi hanya jika FAIL)               |
| Priority perbaikan     | P0 / P1 / P2 / P3                                                  |
| Defect ID              |                                                                    |
| Request/correlation ID |                                                                    |
| Bukti                  | Tautan log tersensor, screenshot, trace, laporan k6, atau checksum |
| Catatan                |                                                                    |

## Template defect

**Judul:** `[Severity][Modul][Test case ID] Ringkasan perilaku salah`

**Kondisi:** build, revision, lingkungan, tenant sintetis, perangkat/browser.  
**Langkah reproduksi:** langkah minimum yang deterministik.  
**Expected:** hasil yang seharusnya.  
**Actual:** hasil aktual termasuk status HTTP/field yang salah.  
**Dampak:** data, pengguna, tenant, dan kemungkinan pemulihan.  
**Bukti:** request ID dan artifact yang sudah disensor.  
**Workaround:** hanya jika aman dan tidak mengubah data keuangan.  
**Retest:** commit perbaikan, suite terdampak, tanggal, penguji, hasil.

## Aturan status

- **PASS**: seluruh expected result terpenuhi dan bukti tersedia.
- **FAIL**: sedikitnya satu expected result tidak terpenuhi; buat defect.
- **BLOCKED**: prasyarat eksternal tidak tersedia; tulis pemilik dan target penyelesaian.
- **NOT RUN**: belum dijadwalkan/dieksekusi; tidak boleh dihitung sebagai lulus.
