# Migration database

Semua perubahan skema dibuat melalui revision Alembic di `versions/`. Revision yang sudah pernah
diterapkan ke staging/production bersifat immutable. Satu migration harus memiliki strategi
upgrade, rollback yang realistis, serta tidak mengandalkan data tenant tertentu.

Jalankan dari root repository:

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "message"
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
```

Model SQLAlchemy harus diimpor oleh package modulnya sebelum `--autogenerate` dijalankan agar masuk
ke `Base.metadata`. Tinjau SQL hasil autogenerate secara manual sebelum revision digunakan.
