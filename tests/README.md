# Test lintas aplikasi

- `contract/`: kompatibilitas OpenAPI dan consumer web/Android.
- `integration/`: API dengan PostgreSQL, MinIO, dan dependency nyata dalam container.
- `e2e/`: alur utama pengguna pada build yang sudah dirakit.
- `performance/`: smoke dan load test k6 yang hanya membaca data.
- `fixtures/`: data sintetis bersama, termasuk golden accounting dataset kelak.

Unit/component test tetap dekat dengan aplikasi masing-masing. Data pengguna nyata, nota asli, dan
credential tidak boleh masuk fixture.

Strategi, quality gate, katalog kasus, serta template actual result tersedia di
[`../documentation/testing/`](../documentation/testing/).
