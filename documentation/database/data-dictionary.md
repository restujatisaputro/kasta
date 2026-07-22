# Data Dictionary KASTA

## Notasi umum

- `NN`: `NOT NULL`; `N`: nullable.
- Semua tabel memiliki `id UUID PK NN DEFAULT gen_random_uuid()`, kecuali tidak disebut lain tetap
  mengikuti aturan ini.
- Semua tabel memiliki `created_at TIMESTAMPTZ NN DEFAULT now()` dan `updated_at TIMESTAMPTZ NN
DEFAULT now()`.
- `SD: ya` berarti memiliki `deleted_at TIMESTAMPTZ N` dan query normal wajib memfilter
  `deleted_at IS NULL`. `SD: tidak` berarti append-only/financial record dan tidak boleh memakai soft
  delete sebagai cara koreksi.
- Semua uang: `NUMERIC(18,2)`. Semua kuantitas: `NUMERIC(18,4)`. Tidak ada float.
- Setiap tabel bertenant memiliki `business_id UUID NN FK businesses(id)` dan `UNIQUE
(business_id,id)` untuk mendukung foreign key komposit satu tenant.
- Nama constraint dan index definitif ada di `kasta-postgresql-v0.1.sql`.

## A. Identitas, role, tenant, dan pembina

### `roles`

- Kolom: `code VARCHAR(50) NN`; `name VARCHAR(100) NN`; `scope VARCHAR(20) NN DEFAULT 'BUSINESS'`;
  `description TEXT N`; `is_system BOOLEAN NN DEFAULT false`; timestamp umum; `deleted_at`.
- Unique/check: `UNIQUE(scope,code)`; scope hanya `PLATFORM|BUSINESS`.
- Index: partial `lower(name)` untuk role aktif. SD: ya, tetapi role system tidak boleh dihapus.

### `permissions`

- Kolom: `code VARCHAR(100) NN`; `name VARCHAR(120) NN`; `module VARCHAR(50) NN`;
  `description TEXT N`; `is_system BOOLEAN NN DEFAULT true`; timestamp; `deleted_at`.
- Unique/check: `UNIQUE(code)`; code/name/module tidak boleh kosong.
- Index: `(module,code)` untuk row aktif. SD: ya, permission system dilindungi aplikasi.

### `role_permissions`

- Kolom: `role_id UUID NN FK roles`; `permission_id UUID NN FK permissions`; timestamp;
  `deleted_at`.
- Unique/check: partial unique `(role_id,permission_id)` saat aktif.
- Index: `permission_id`; SD: ya agar pencabutan grant tetap terlacak.

### `users`

- Kolom: `platform_role_id UUID N FK roles`; `email CITEXT N`; `phone VARCHAR(24) N`;
  `password_hash TEXT N`; `full_name VARCHAR(150) NN`; `status VARCHAR(20) NN DEFAULT 'ACTIVE'`;
  `locale VARCHAR(10) NN DEFAULT 'id-ID'`; waktu verifikasi email/telepon N; `last_login_at` N;
  timestamp; `deleted_at`.
- Unique/check: minimal email atau phone; status `INVITED|ACTIVE|SUSPENDED|DISABLED`; partial unique
  email dan phone saat aktif.
- Index: `platform_role_id`, `status`; SD: ya, dengan anonymization sesuai retensi.

### `organizations`

- Kolom: `code VARCHAR(40) NN`; `name VARCHAR(160) NN`; `legal_name VARCHAR(200) N`;
  `organization_type VARCHAR(30) NN`; email/phone N; `address JSONB NN DEFAULT '{}'`;
  `status VARCHAR(20) NN DEFAULT 'ACTIVE'`; timestamp; `deleted_at`.
- Unique/check: partial unique `lower(code)` aktif; type `MENTOR_INSTITUTION|COOPERATIVE|UMKM_GROUP|
GOVERNMENT|PLATFORM|OTHER`; status `ACTIVE|INACTIVE|SUSPENDED`.
- Index: `organization_type,status`; SD: ya.

### `businesses`

- Kolom: `organization_id UUID N FK organizations`; `created_by_user_id UUID NN FK users`;
  `code VARCHAR(40) NN`; `name VARCHAR(160) NN`; `legal_name VARCHAR(200) N`;
  registration/tax ID N; email/phone N; `address JSONB NN DEFAULT '{}'`; `currency_code CHAR(3) NN
DEFAULT 'IDR'`; `timezone VARCHAR(64) NN DEFAULT 'Asia/Jakarta'`; `fiscal_year_start SMALLINT NN
DEFAULT 1`; `status VARCHAR(20) NN DEFAULT 'ACTIVE'`; timestamp; `deleted_at`.
- Unique/check: partial unique `lower(code)` aktif; bulan fiskal 1–12; currency tiga huruf kapital;
  status `ACTIVE|SUSPENDED|CLOSED`.
- Index: organization dan status; SD: ya hanya setelah retention/closure workflow.

### `business_members`

- Kolom tenant; `user_id UUID NN FK users`; `role_id UUID NN FK roles`; `status VARCHAR(20) NN
DEFAULT 'INVITED'`; `invited_by_user_id UUID N FK users`; `joined_at`, `last_active_at` N;
  timestamp; `deleted_at`.
- Unique/check: partial unique `(business_id,user_id)` aktif; status `INVITED|ACTIVE|SUSPENDED|LEFT`.
- Index: `(user_id,status)` dan `(business_id,role_id)` aktif. SD: ya.

### `mentors`

- Kolom: `user_id UUID NN FK users`; `organization_id UUID N FK organizations`;
  `mentor_code VARCHAR(40) NN`; `bio TEXT N`; `expertise TEXT[] NN DEFAULT '{}'`;
  `status VARCHAR(20) NN DEFAULT 'ACTIVE'`; timestamp; `deleted_at`.
- Unique/check: partial unique user dan `lower(mentor_code)` aktif; status
  `ACTIVE|INACTIVE|SUSPENDED`.
- Index: organization/status. SD: ya.

### `mentor_business_access`

- Kolom tenant; `mentor_id UUID NN FK mentors`; `requested_by_user_id UUID N FK users`;
  `granted_by_user_id UUID N FK users`; `status VARCHAR(20) NN DEFAULT 'REQUESTED'`; boolean scope
  `can_view_summary` default true, `can_view_reports`, `can_view_transactions`, `can_view_receipts`
  default false, `can_add_notes`, `can_add_recommendations` default true; `requested_at NN DEFAULT
now()`; `granted_at`, `valid_from`, `expires_at`, `revoked_at` N; `revocation_reason` N;
  `revision_no INTEGER NN DEFAULT 1`; timestamp; `deleted_at`.
- Unique/check: partial unique mentor–business untuk status requested/active; active membutuhkan grant;
  expiry setelah valid-from; revoked membutuhkan `revoked_at`; revision positif. Unique tambahan
  `(business_id,id,mentor_id)` memastikan note/session memakai mentor pada izin yang sama.
- Index: `(mentor_id,status,expires_at)`, `(business_id,status)`. SD: ya hanya request yang belum aktif;
  histori grant/revoke dipertahankan.

## B. Akun, pihak, produk, dan metode bayar

### `account_categories`

- Kolom global: `code VARCHAR(40) NN`; `name VARCHAR(120) NN`; `account_type VARCHAR(20) NN`;
  `normal_balance VARCHAR(10) NN`; `report_group VARCHAR(30) NN`; `display_order INTEGER NN DEFAULT
0`; `is_system BOOLEAN NN DEFAULT true`; timestamp; `deleted_at`.
- Unique/check: code unik; type `ASSET|LIABILITY|EQUITY|REVENUE|EXPENSE`; normal balance harus debit
  untuk asset/expense dan credit untuk liability/equity/revenue; report group terbatas.
- Index: `(account_type,display_order)`. SD: ya, system category dilindungi.

### `accounts`

- Kolom tenant; `category_id UUID NN FK account_categories`; `parent_account_id UUID N` self FK
  satu tenant; `code VARCHAR(30) NN`; `name VARCHAR(120) NN`; `description TEXT N`; `is_system
BOOLEAN NN DEFAULT false`; `allow_manual_entry BOOLEAN NN DEFAULT true`; `is_active BOOLEAN NN
DEFAULT true`; timestamp; `deleted_at`.
- Unique/check: partial unique `(business_id,lower(code))`; code/name tidak kosong dan parent bukan
  dirinya sendiri.
- Index: category, parent, dan `(business_id,is_active)`. SD: ya jika belum dipakai; akun terpakai
  dinonaktifkan, bukan dihapus.

### `payment_methods`

- Kolom tenant; `account_id UUID NN` composite FK accounts; `code VARCHAR(30) NN`; `name VARCHAR(100)
NN`; `method_type VARCHAR(20) NN`; `is_active BOOLEAN NN DEFAULT true`; timestamp; `deleted_at`.
- Unique/check: partial unique `(business_id,lower(code))`; type `CASH|BANK_TRANSFER|CARD|EWALLET|
OTHER`.
- Index: account dan status aktif. SD: ya jika belum dipakai; setelah dipakai dinonaktifkan.

### `customers`

- Kolom tenant; `code VARCHAR(40) N`; `name VARCHAR(160) NN`; email/phone N; `address JSONB NN
DEFAULT '{}'`; `tax_id VARCHAR(40) N`; `notes TEXT N`; `is_active BOOLEAN NN DEFAULT true`;
  timestamp; `deleted_at`.
- Unique/check: partial unique code bila tidak null; name tidak kosong.
- Index: `lower(name)`, phone, status aktif. SD: ya dengan referential restriction.

### `suppliers`

- Kolom sama dengan customer: tenant, code N, name NN, contact/address/tax/notes, is_active,
  timestamp, `deleted_at`.
- Unique/check/index: partial unique code; index `lower(name)`, phone, active. SD: ya.

### `products`

- Kolom tenant; `sku VARCHAR(60) N`; `name VARCHAR(180) NN`; `unit VARCHAR(30) NN DEFAULT 'pcs'`;
  `sales_price NUMERIC(18,2) NN DEFAULT 0`; `cost_price NUMERIC(18,2) NN DEFAULT 0`;
  `track_stock BOOLEAN NN DEFAULT true`; `minimum_stock NUMERIC(18,4) NN DEFAULT 0`;
  `is_active BOOLEAN NN DEFAULT true`; timestamp; `deleted_at`.
- Unique/check: partial unique SKU; harga dan minimum stock tidak negatif; name/unit tidak kosong.
- Index: `lower(name)` dan status aktif. SD: ya jika belum dipakai; produk historis dinonaktifkan.

## C. Transaksi, jurnal, stok, piutang, dan utang

### `transactions`

- Kolom tenant; `transaction_number VARCHAR(40) NN`; `transaction_type VARCHAR(30) NN`;
  `transaction_date DATE NN`; `description TEXT N`; `currency_code CHAR(3) NN DEFAULT 'IDR'`;
  `total_amount NUMERIC(18,2) NN`; `status VARCHAR(20) NN DEFAULT 'DRAFT'`;
  `payment_method_id`, `customer_id`, `supplier_id` UUID N composite FK tenant;
  `idempotency_key UUID N`; `source VARCHAR(20) NN DEFAULT 'WEB'`; `reversal_of_transaction_id UUID N`
  self FK tenant; actor create/post/void UUID; waktu post/void N; `void_reason TEXT N`;
  `revision_no INTEGER NN DEFAULT 1`; timestamp; `deleted_at`.
- Unique/check: number unik per business; idempotency partial unique; hanya satu reversal per original;
  amount nonnegative; tepat maksimal satu customer/supplier; reversal reference wajib untuk type
  `REVERSAL`; posted/voided wajib metadata aktor/waktu; deleted hanya draft.
- Index: date/id, status/date, customer/date, supplier/date, creator/date. SD: hanya draft.

### `transaction_items`

- Kolom tenant; `transaction_id UUID NN` composite FK; `line_no INTEGER NN`; `product_id UUID N`;
  `account_id UUID N`; `description VARCHAR(250) NN`; `quantity NUMERIC(18,4) NN DEFAULT 1`;
  `unit_price`, `discount_amount`, `tax_amount NUMERIC(18,2) NN DEFAULT 0`; `line_total
NUMERIC(18,2)` generated stored; `revision_no INTEGER NN DEFAULT 1`; timestamp; `deleted_at`.
- Unique/check: `(transaction_id,line_no)` unik; quantity positif; komponen uang nonnegative;
  generated total nonnegative.
- Index: product dan account per business. SD: hanya selama parent draft.

### `journal_entries`

- Kolom tenant; `entry_number VARCHAR(40) NN`; `entry_date DATE NN`; `source_type VARCHAR(30) NN`;
  `transaction_id UUID N` composite FK; `reversal_of_entry_id UUID N` self FK; `memo TEXT N`;
  `status VARCHAR(20) NN DEFAULT 'DRAFT'`; `total_debit`, `total_credit NUMERIC(18,2) NN DEFAULT 0`;
  actor create/post UUID; waktu post N; actor/waktu/alasan reversal N; `revision_no INTEGER NN DEFAULT
1`; timestamp; `deleted_at`.
- Unique/check: number unik/business; maksimal satu jurnal sumber untuk transaksi pada desain awal;
  satu reversal per jurnal; posted harus total >0 dan debit=credit; deleted hanya draft.
- Index: date, status/date, transaction. SD: hanya draft; posted/reversed immutable.

### `journal_lines`

- Kolom tenant; `journal_entry_id UUID NN`; `line_no INTEGER NN`; `account_id UUID NN`;
  `transaction_item_id UUID N`; `description VARCHAR(250) N`; `debit_amount`, `credit_amount
NUMERIC(18,2) NN DEFAULT 0`; `revision_no INTEGER NN DEFAULT 1`; timestamp; `deleted_at`.
- Unique/check: `(journal_entry_id,line_no)` unik; nilai nonnegative dan tepat satu sisi >0.
- Index: `(business_id,account_id,journal_entry_id)` dan item. Constraint deferred menguji minimal
  dua line serta total seimbang saat parent posted. SD: hanya saat parent draft.

### `stock_movements`

- Kolom tenant; `product_id`, `transaction_id UUID NN`; `transaction_item_id UUID N`; `movement_type
VARCHAR(20) NN`; `movement_at TIMESTAMPTZ NN`; `quantity_delta NUMERIC(18,4) NN`; `unit_cost
NUMERIC(18,2) NN DEFAULT 0`; `reversal_of_movement_id UUID N` self FK; `created_by_user_id UUID NN`;
  `revision_no INTEGER NN DEFAULT 1`; timestamp umum tanpa deleted.
- Unique/check: quantity tidak nol, cost nonnegative, reversal harus berlawanan dan type `REVERSAL`;
  satu reversal per movement.
- Index: product/time dan transaction. SD: tidak; pembalikan memakai row baru.

### `receivables`

- Kolom tenant; `receivable_number VARCHAR(40) NN`; `customer_id UUID NN`; `source_transaction_id
UUID NN`; `account_id UUID NN`; issue/due date NN; `original_amount`, `outstanding_amount
NUMERIC(18,2) NN`; `status VARCHAR(20) NN DEFAULT 'OPEN'`; `revision_no INTEGER NN DEFAULT 1`;
  timestamp tanpa deleted.
- Unique/check: number dan source transaction unik per business; due >= issue; original >0;
  outstanding 0..original; status sesuai saldo.
- Index: partial due date status terbuka, customer/status. SD: tidak; void melalui reversal.

### `receivable_payments`

- Kolom tenant; `receivable_id`, `transaction_id`, `payment_method_id UUID NN`; `payment_date DATE NN`;
  `amount NUMERIC(18,2) NN`; `status VARCHAR(20) NN DEFAULT 'POSTED'`; `reversal_of_payment_id UUID N`;
  `created_by_user_id UUID NN`; `revision_no INTEGER NN DEFAULT 1`; timestamp tanpa deleted.
- Unique/check: transaction unik; satu reversal per payment; amount >0; status `POSTED|VOIDED`.
- Index: receivable/date, payment method/date. SD: tidak.

### `payables`

- Kolom tenant; `payable_number VARCHAR(40) NN`; `supplier_id`, `source_transaction_id`, `account_id
UUID NN`; issue/due date; original/outstanding money; status; revision; timestamp tanpa deleted.
- Unique/check: sama dengan receivables; source/number unik; tanggal dan saldo valid.
- Index: partial jatuh tempo terbuka dan supplier/status. SD: tidak.

### `payable_payments`

- Kolom tenant; `payable_id`, `transaction_id`, `payment_method_id UUID NN`; payment date; amount;
  status; reversal self FK; creator; revision; timestamp tanpa deleted.
- Unique/check/index: sama dengan receivable payments. SD: tidak.

## D. Nota dan OCR

### `receipts`

- Kolom tenant; `transaction_id UUID N`; `uploaded_by_user_id UUID NN`; `receipt_number VARCHAR(60) N`;
  `merchant_name VARCHAR(180) N`; `receipt_date DATE N`; `total_amount NUMERIC(18,2) N`;
  `status VARCHAR(30) NN DEFAULT 'UPLOADING'`; `notes TEXT N`; `revision_no INTEGER NN DEFAULT 1`;
  timestamp; `deleted_at`.
- Unique/check: receipt number partial unique bila ada; amount nonnegative; status terbatas.
- Index: transaction, status, receipt date. SD: ya sebagai arsip/purge workflow; metadata audit tetap.

### `receipt_images`

- Kolom tenant; `receipt_id UUID NN`; `bucket_name VARCHAR(100) NN`; `object_key VARCHAR(500) NN`;
  `etag VARCHAR(160) N`; `mime_type VARCHAR(100) NN`; `byte_size BIGINT NN`; `sha256 CHAR(64) NN`;
  width/height N; `page_number INTEGER NN DEFAULT 1`; `is_primary BOOLEAN NN DEFAULT false`;
  `upload_status VARCHAR(20) NN DEFAULT 'PENDING'`; timestamp; `deleted_at`.
- Unique/check: object key global unik; receipt/page unik aktif; satu primary aktif per receipt; size >0,
  page >0, dimension positif bila ada, SHA-256 hex.
- Index: receipt/status, checksum. SD: ya; object deletion mengikuti retention dan audit.

### `ocr_results`

- Kolom tenant; `receipt_image_id UUID NN`; `engine VARCHAR(30) NN`; `engine_version VARCHAR(60) N`;
  `status VARCHAR(20) NN DEFAULT 'PENDING'`; `confidence NUMERIC(5,4) N`; `raw_text TEXT N`;
  `raw_payload JSONB N`; `is_current BOOLEAN NN DEFAULT true`; `processed_at TIMESTAMPTZ N`;
  `error_code`, `error_message` N; timestamp; `deleted_at`.
- Unique/check: satu current result aktif per image; confidence 0..1; status terbatas; completed wajib
  processed_at.
- Index: image/time, status. SD: ya; raw payload dapat dipurge lebih cepat.

### `ocr_fields`

- Kolom tenant; `ocr_result_id UUID NN`; `field_name VARCHAR(60) NN`; `occurrence INTEGER NN DEFAULT 1`;
  `raw_value TEXT N`; `normalized_value TEXT N`; `confidence NUMERIC(5,4) N`; `bounding_box JSONB N`;
  `was_corrected BOOLEAN NN DEFAULT false`; `corrected_by_user_id UUID N`; `corrected_at TIMESTAMPTZ N`;
  timestamp; `deleted_at`.
- Unique/check: result/field/occurrence unik aktif; confidence 0..1; correction metadata konsisten.
- Index: result/field dan corrector. SD: ya.

## E. Pendampingan dan notifikasi

### `mentor_notes`

- Kolom tenant; `mentor_id UUID NN`; `mentor_business_access_id UUID NN` dengan FK komposit yang juga
  mencocokkan mentor; `subject VARCHAR(180) NN`; `note_body TEXT NN`; `visibility VARCHAR(30) NN
DEFAULT 'OWNER_ONLY'`; `revision_no INTEGER NN DEFAULT 1`; timestamp; `deleted_at`.
- Unique/check: subject/body nonempty; visibility `OWNER_ONLY|OWNER_AND_STAFF`.
- Index: business/time dan mentor/time. SD: ya; penghapusan tetap diaudit.

### `recommendations`

- Kolom tenant; mentor dan access UUID NN; `mentor_note_id UUID N`; `title VARCHAR(180) NN`;
  `description TEXT NN`; `category VARCHAR(40) NN`; `priority VARCHAR(10) NN DEFAULT 'MEDIUM'`;
  `status VARCHAR(20) NN DEFAULT 'OPEN'`; `due_date DATE N`; acknowledged/completed actor+waktu N;
  `revision_no INTEGER NN DEFAULT 1`; timestamp; `deleted_at`.
- Unique/check: priority/status terbatas; metadata acknowledge/completed konsisten.
- Index: business/status/due, mentor/time, note. SD: ya.

### `mentoring_sessions`

- Kolom tenant; mentor dan access UUID NN; `scheduled_at TIMESTAMPTZ NN`; start/end N;
  `channel VARCHAR(20) NN`; `location VARCHAR(250) N`; `status VARCHAR(20) NN DEFAULT 'SCHEDULED'`;
  `summary`, `action_items` TEXT N; `created_by_user_id UUID NN`; `revision_no INTEGER NN DEFAULT 1`;
  timestamp; `deleted_at`.
- Unique/check: end > start; channel/status terbatas; completed membutuhkan start/end.
- Index: business/schedule, mentor/schedule, status. SD: ya untuk pembatalan draft; histori sesi selesai
  dipertahankan.

### `notifications`

- Kolom: `business_id UUID N`; `user_id UUID NN`; `notification_type VARCHAR(50) NN`; `title
VARCHAR(180) NN`; `message TEXT NN`; `payload JSONB NN DEFAULT '{}'`; `channel VARCHAR(20) NN
DEFAULT 'IN_APP'`; `status VARCHAR(20) NN DEFAULT 'PENDING'`; `scheduled_at TIMESTAMPTZ N`;
  sent/read/failed timestamp N; `failure_reason` N; timestamp; `deleted_at`.
- Unique/check: channel/status terbatas dan timestamp status konsisten.
- Index: unread partial user/time, business/time, delivery queue. SD: ya sesuai retensi notifikasi.

## F. Perangkat, sinkronisasi, dan audit

### `device_sessions`

- Kolom: `user_id UUID NN`; `business_id UUID N`; `device_identifier_hash CHAR(64) NN`;
  `platform VARCHAR(20) NN`; `device_name VARCHAR(120) N`; `app_version VARCHAR(30) N`;
  `refresh_token_hash TEXT NN`; `push_token_ciphertext TEXT N`; `last_seen_at TIMESTAMPTZ NN DEFAULT
now()`; `expires_at TIMESTAMPTZ NN`; `revoked_at TIMESTAMPTZ N`; `revision_no INTEGER NN DEFAULT 1`;
  timestamp; `deleted_at`.
- Unique/check: active user/device hash unik; SHA hex; platform `ANDROID|WEB`; expiry setelah create.
- Index: user/last seen, business/user, expiry aktif. SD: ya setelah revoke/retensi.

### `sync_logs`

- Kolom tenant; `device_session_id UUID NN`; `client_batch_id UUID NN`; `client_operation_id UUID NN`;
  `direction VARCHAR(10) NN`; `entity_type VARCHAR(80) NN`; `entity_id UUID NN`; `operation
VARCHAR(10) NN`; `client_revision INTEGER NN`; `server_revision INTEGER N`; `status VARCHAR(20) NN`;
  `request_hash CHAR(64) NN`; `conflict_payload JSONB N`; `error_code`, `error_message` N;
  `processed_at TIMESTAMPTZ NN DEFAULT now()`; timestamp umum tanpa deleted.
- Unique/check: `(business_id,device_session_id,client_operation_id)` idempotent; revisions nonnegative;
  direction/operation/status dan SHA valid.
- Index: device/batch, business/server revision, status/time; BRIN created_at saat besar. SD: tidak,
  append-only dengan retensi/partition drop.

### `audit_logs`

- Kolom: `business_id UUID N`; `actor_user_id UUID N`; `action VARCHAR(30) NN`; `entity_type
VARCHAR(80) NN`; `entity_id UUID N`; `entity_revision INTEGER N`; `before_data`, `after_data JSONB N`;
  `changed_fields TEXT[] NN DEFAULT '{}'`; `correlation_id`, `request_id UUID N`; `source
VARCHAR(20) NN DEFAULT 'API'`; `ip_address INET N`; `user_agent TEXT N`; `occurred_at TIMESTAMPTZ NN
DEFAULT now()`; `previous_hash`, `entry_hash BYTEA N`; timestamp umum tanpa deleted.
- Unique/check: action/source terbatas; minimal salah satu snapshot untuk operasi data; revision positif.
- Index: entity history, actor/time, correlation, BRIN occurred_at. SD: tidak; update/delete ditolak dan
  ekspor WORM direkomendasikan.
