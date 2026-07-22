# Performance dan load test

Skrip `k6-smoke.js` memakai dua profil dan tidak pernah menulis transaksi keuangan.

```bash
# Smoke: 5 virtual users selama 30 detik
k6 run tests/performance/k6-smoke.js

# Jika k6 berjalan di container tetapi Caddy lokal hanya menerima host localhost
KASTA_BASE_URL=http://host.docker.internal:8080 KASTA_HOST_HEADER=localhost:8080 \
k6 run tests/performance/k6-smoke.js

# Load: 50 virtual users selama 5 menit
KASTA_LOAD_PROFILE=load KASTA_BASE_URL=https://staging.example.test \
KASTA_ACCESS_TOKEN='token-test' KASTA_BUSINESS_ID='uuid-tenant-test' \
k6 run tests/performance/k6-smoke.js
```

Ambang lulus: error HTTP kurang dari 1%, check lebih dari 99%, p95 di bawah 750 ms, dan p99 di
bawah 1,5 detik. Jalankan profil `load` hanya terhadap staging atau lingkungan performa dengan data
sintetis. Token harus berasal dari akun pengujian dan tidak boleh disimpan di repository.
