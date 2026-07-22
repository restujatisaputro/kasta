# Konvensi Pengembangan

## Penamaan file dan simbol

| Area        | File/direktori                                       | Simbol                                                                         |
| ----------- | ---------------------------------------------------- | ------------------------------------------------------------------------------ |
| Python      | `snake_case.py`                                      | fungsi/variabel `snake_case`, class `PascalCase`, konstanta `UPPER_SNAKE_CASE` |
| Svelte      | komponen `PascalCase.svelte`, route sesuai SvelteKit | komponen `PascalCase`, fungsi `camelCase`                                      |
| TypeScript  | `kebab-case.ts`                                      | type/class `PascalCase`, fungsi/variabel `camelCase`                           |
| Kotlin      | satu class utama per `PascalCase.kt`                 | class/composable `PascalCase`, fungsi/properti `camelCase`                     |
| SQL         | tabel/kolom/index `snake_case`                       | FK `<entity>_id`, index `ix_<table>_<columns>`                                 |
| Alembic     | revision generator Alembic                           | pesan imperatif, misalnya `create transaction table`                           |
| Test Python | `test_<subject>.py`                                  | `test_<condition>_<expected_result>`                                           |
| Test TS     | `<subject>.test.ts`                                  | deskripsi perilaku pengguna                                                    |
| Test Kotlin | `<Subject>Test.kt`                                   | nama method backtick yang menjelaskan perilaku                                 |

Nama API memakai noun jamak, `kebab-case`, dan versi mayor: `/api/v1/cash-transactions`.
Kolom tenant wajib bernama `tenant_id`. Identifier publik memakai UUID/ULID, bukan sequence internal.

## Branch Git

Branch utama adalah `main` dan selalu deployable. Gunakan branch singkat:

- `feature/KAS-123-uang-masuk`
- `fix/KAS-456-sync-idempotency`
- `chore/update-python-tooling`
- `docs/tenant-authorization`
- `release/1.2.0`
- `hotfix/KAS-789-token-validation`

Gunakan huruf kecil pada slug, pisahkan kata dengan tanda hubung, sertakan nomor issue bila ada,
dan hapus branch setelah merge. Merge ke `main` melalui pull request dengan squash merge kecuali
release membutuhkan riwayat terpisah.

## Commit

Gunakan Conventional Commits:

```text
<type>(<scope>): <ringkasan imperatif>
```

Type yang diizinkan: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`,
dan `revert`. Scope umum: `api`, `web`, `android`, `contracts`, `infra`, `docs`.

Contoh:

```text
feat(api): add cash transaction command
fix(android): preserve idempotency key after retry
docs(infra): document restore rehearsal
```

Breaking change memakai `!` dan footer `BREAKING CHANGE:`. Jangan campurkan formatting massal
dengan perubahan perilaku dalam commit yang sama.

## Format, lint, dan kualitas

- Python: Ruff untuk format/lint, mypy strict bertahap, Pytest.
- Svelte/TypeScript: Prettier, ESLint, `svelte-check`, TypeScript strict, Vitest.
- Kotlin: ktlint, Android Lint, JUnit; Compose memakai compiler plugin Kotlin.
- YAML/Markdown/JSON: Prettier; Compose diverifikasi dengan `docker compose config`.
- API: OpenAPI divalidasi dan dibandingkan terhadap kontrak yang dikomit.

Tidak boleh menonaktifkan lint secara global untuk menyelesaikan satu peringatan. Pengecualian lokal
harus memiliki alasan. CI wajib lulus sebelum merge.
