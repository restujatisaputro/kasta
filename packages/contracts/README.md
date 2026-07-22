# @kasta/contracts

Kontrak HTTP KASTA yang bersifat lintas bahasa. `openapi/generated-kasta-api.json` diekspor langsung
dari FastAPI dan menjadi gambaran kontrak aktual. `openapi/kasta-api.yaml` tetap dipertahankan sebagai
baseline fondasi yang mudah dibaca. Direktori `src/generated` disediakan untuk generator TypeScript;
Android dapat menghasilkan model/klien Kotlin dari skema aktual yang sama.

```bash
pnpm --filter @kasta/contracts lint
pnpm --filter @kasta/contracts build
uv run --project apps/api python scripts/export_openapi.py
```

Tipe fondasi di `src/index.ts` ditulis manual hanya sampai pipeline generator dipilih. Setelah itu,
hasil generasi harus diverifikasi CI dan tidak diedit langsung.

Kontrak Foto Nota berada pada router `/businesses/{business_id}/receipt-scans`. Tipe status, field
OCR, item, kandidat duplikat, review, dan konfirmasi tersedia pada `src/index.ts`; kontrak aktual
multipart serta response diekspor dari FastAPI ke OpenAPI JSON.
