API_DESCRIPTION = """
API modular monolith untuk KASTA (Keuangan dan Asistensi UMKM).

Fondasi ini menyediakan autentikasi business-scoped, otorisasi granular, transaksi dan jurnal,
persediaan, utang-piutang, laporan keuangan, serta workspace pendampingan pembina UMKM. Endpoint
tersedia di bawah `/api/v1`.
"""

OPENAPI_TAGS = [
    {"name": "system", "description": "Status hidup dan kesiapan layanan."},
    {"name": "auth", "description": "Autentikasi dan sesi pengguna."},
    {"name": "users", "description": "Profil dan akses pengguna."},
    {"name": "businesses", "description": "UMKM dan keanggotaan usaha."},
    {"name": "accounting", "description": "Akun dan jurnal double-entry."},
    {"name": "transactions", "description": "Pencatatan transaksi usaha."},
    {"name": "receipts", "description": "Nota dan lampiran transaksi."},
    {"name": "ocr", "description": "Ekstraksi data nota."},
    {"name": "inventory", "description": "Produk dan pergerakan stok."},
    {"name": "receivables", "description": "Piutang dan pembayarannya."},
    {"name": "payables", "description": "Utang dan pembayarannya."},
    {"name": "mentors", "description": "Akses dan pendampingan pembina."},
    {"name": "reports", "description": "Laporan dan ringkasan keuangan."},
    {"name": "notifications", "description": "Notifikasi pengguna."},
    {"name": "sync", "description": "Sinkronisasi klien offline."},
    {"name": "audit", "description": "Jejak audit perubahan."},
]
