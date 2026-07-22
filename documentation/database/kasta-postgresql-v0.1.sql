-- KASTA PostgreSQL schema draft v0.1
-- Design artifact: review before converting to Alembic revisions.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE SCHEMA IF NOT EXISTS kasta;
SET search_path TO kasta, public;

CREATE TABLE kasta.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    scope VARCHAR(20) NOT NULL DEFAULT 'BUSINESS',
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_roles_scope_code UNIQUE (scope, code),
    CONSTRAINT ck_roles_code CHECK (length(btrim(code)) > 0 AND code = upper(code)),
    CONSTRAINT ck_roles_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_roles_scope CHECK (scope IN ('PLATFORM', 'BUSINESS'))
);

CREATE TABLE kasta.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(120) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_permissions_code UNIQUE (code),
    CONSTRAINT ck_permissions_code CHECK (length(btrim(code)) > 0 AND code = upper(code)),
    CONSTRAINT ck_permissions_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_permissions_module CHECK (length(btrim(module)) > 0)
);

CREATE TABLE kasta.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_role_id UUID REFERENCES kasta.roles(id) ON DELETE RESTRICT,
    email CITEXT,
    phone VARCHAR(24),
    password_hash TEXT,
    full_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    locale VARCHAR(10) NOT NULL DEFAULT 'id-ID',
    email_verified_at TIMESTAMPTZ,
    phone_verified_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_users_login_identifier CHECK (email IS NOT NULL OR phone IS NOT NULL),
    CONSTRAINT ck_users_full_name CHECK (length(btrim(full_name)) > 0),
    CONSTRAINT ck_users_status CHECK (status IN ('INVITED', 'ACTIVE', 'SUSPENDED', 'DISABLED'))
);

CREATE TABLE kasta.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    legal_name VARCHAR(200),
    organization_type VARCHAR(30) NOT NULL,
    email CITEXT,
    phone VARCHAR(24),
    address JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_organizations_code CHECK (length(btrim(code)) > 0),
    CONSTRAINT ck_organizations_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_organizations_type CHECK (
        organization_type IN (
            'MENTOR_INSTITUTION', 'COOPERATIVE', 'UMKM_GROUP', 'GOVERNMENT', 'PLATFORM', 'OTHER'
        )
    ),
    CONSTRAINT ck_organizations_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    CONSTRAINT ck_organizations_address_object CHECK (jsonb_typeof(address) = 'object')
);

CREATE TABLE kasta.businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES kasta.organizations(id) ON DELETE RESTRICT,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    legal_name VARCHAR(200),
    registration_number VARCHAR(80),
    tax_id VARCHAR(40),
    email CITEXT,
    phone VARCHAR(24),
    address JSONB NOT NULL DEFAULT '{}'::jsonb,
    currency_code CHAR(3) NOT NULL DEFAULT 'IDR',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Jakarta',
    fiscal_year_start SMALLINT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_businesses_code CHECK (length(btrim(code)) > 0),
    CONSTRAINT ck_businesses_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_businesses_currency CHECK (currency_code ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_businesses_timezone CHECK (length(btrim(timezone)) > 0),
    CONSTRAINT ck_businesses_fiscal_month CHECK (fiscal_year_start BETWEEN 1 AND 12),
    CONSTRAINT ck_businesses_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CLOSED')),
    CONSTRAINT ck_businesses_address_object CHECK (jsonb_typeof(address) = 'object')
);

CREATE TABLE kasta.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES kasta.roles(id) ON DELETE RESTRICT,
    permission_id UUID NOT NULL REFERENCES kasta.permissions(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE kasta.business_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    role_id UUID NOT NULL REFERENCES kasta.roles(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'INVITED',
    invited_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    joined_at TIMESTAMPTZ,
    last_active_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_business_members_tenant_id UNIQUE (business_id, id),
    CONSTRAINT ck_business_members_status CHECK (status IN ('INVITED', 'ACTIVE', 'SUSPENDED', 'LEFT')),
    CONSTRAINT ck_business_members_joined CHECK (status <> 'ACTIVE' OR joined_at IS NOT NULL)
);

CREATE TABLE kasta.mentors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    organization_id UUID REFERENCES kasta.organizations(id) ON DELETE RESTRICT,
    mentor_code VARCHAR(40) NOT NULL,
    bio TEXT,
    expertise TEXT[] NOT NULL DEFAULT '{}'::text[],
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_mentors_code CHECK (length(btrim(mentor_code)) > 0),
    CONSTRAINT ck_mentors_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'))
);

CREATE TABLE kasta.mentor_business_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    mentor_id UUID NOT NULL REFERENCES kasta.mentors(id) ON DELETE RESTRICT,
    requested_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    granted_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'REQUESTED',
    can_view_summary BOOLEAN NOT NULL DEFAULT true,
    can_view_reports BOOLEAN NOT NULL DEFAULT false,
    can_view_transactions BOOLEAN NOT NULL DEFAULT false,
    can_view_receipts BOOLEAN NOT NULL DEFAULT false,
    can_add_notes BOOLEAN NOT NULL DEFAULT true,
    can_add_recommendations BOOLEAN NOT NULL DEFAULT true,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revocation_reason TEXT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_mentor_access_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_mentor_access_tenant_id_mentor UNIQUE (business_id, id, mentor_id),
    CONSTRAINT ck_mentor_access_status CHECK (status IN ('REQUESTED', 'ACTIVE', 'REVOKED', 'EXPIRED', 'REJECTED')),
    CONSTRAINT ck_mentor_access_revision CHECK (revision_no > 0),
    CONSTRAINT ck_mentor_access_grant CHECK (
        status <> 'ACTIVE' OR (granted_by_user_id IS NOT NULL AND granted_at IS NOT NULL)
    ),
    CONSTRAINT ck_mentor_access_validity CHECK (
        expires_at IS NULL OR expires_at > COALESCE(valid_from, granted_at, requested_at)
    ),
    CONSTRAINT ck_mentor_access_revoked CHECK (status <> 'REVOKED' OR revoked_at IS NOT NULL)
);

CREATE TABLE kasta.account_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(40) NOT NULL,
    name VARCHAR(120) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    normal_balance VARCHAR(10) NOT NULL,
    report_group VARCHAR(30) NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_system BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_account_categories_code UNIQUE (code),
    CONSTRAINT ck_account_categories_code CHECK (length(btrim(code)) > 0 AND code = upper(code)),
    CONSTRAINT ck_account_categories_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_account_categories_type CHECK (
        account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')
    ),
    CONSTRAINT ck_account_categories_balance CHECK (
        (account_type IN ('ASSET', 'EXPENSE') AND normal_balance = 'DEBIT')
        OR (account_type IN ('LIABILITY', 'EQUITY', 'REVENUE') AND normal_balance = 'CREDIT')
    ),
    CONSTRAINT ck_account_categories_report CHECK (
        report_group IN ('BALANCE_SHEET', 'PROFIT_LOSS', 'CASH_FLOW', 'MEMO')
    )
);

CREATE TABLE kasta.accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    category_id UUID NOT NULL REFERENCES kasta.account_categories(id) ON DELETE RESTRICT,
    parent_account_id UUID,
    code VARCHAR(30) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false,
    allow_manual_entry BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_accounts_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_accounts_parent FOREIGN KEY (business_id, parent_account_id)
        REFERENCES kasta.accounts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_accounts_code CHECK (length(btrim(code)) > 0),
    CONSTRAINT ck_accounts_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_accounts_not_own_parent CHECK (parent_account_id IS NULL OR parent_account_id <> id)
);

CREATE TABLE kasta.payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    account_id UUID NOT NULL,
    code VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    method_type VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_payment_methods_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_payment_methods_account FOREIGN KEY (business_id, account_id)
        REFERENCES kasta.accounts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_payment_methods_code CHECK (length(btrim(code)) > 0),
    CONSTRAINT ck_payment_methods_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_payment_methods_type CHECK (
        method_type IN ('CASH', 'BANK_TRANSFER', 'CARD', 'EWALLET', 'OTHER')
    )
);

CREATE TABLE kasta.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    code VARCHAR(40),
    name VARCHAR(160) NOT NULL,
    email CITEXT,
    phone VARCHAR(24),
    address JSONB NOT NULL DEFAULT '{}'::jsonb,
    tax_id VARCHAR(40),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_customers_tenant_id UNIQUE (business_id, id),
    CONSTRAINT ck_customers_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_customers_address_object CHECK (jsonb_typeof(address) = 'object')
);

CREATE TABLE kasta.suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    code VARCHAR(40),
    name VARCHAR(160) NOT NULL,
    email CITEXT,
    phone VARCHAR(24),
    address JSONB NOT NULL DEFAULT '{}'::jsonb,
    tax_id VARCHAR(40),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_suppliers_tenant_id UNIQUE (business_id, id),
    CONSTRAINT ck_suppliers_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_suppliers_address_object CHECK (jsonb_typeof(address) = 'object')
);

CREATE TABLE kasta.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    sku VARCHAR(60),
    name VARCHAR(180) NOT NULL,
    unit VARCHAR(30) NOT NULL DEFAULT 'pcs',
    sales_price NUMERIC(18,2) NOT NULL DEFAULT 0,
    cost_price NUMERIC(18,2) NOT NULL DEFAULT 0,
    track_stock BOOLEAN NOT NULL DEFAULT true,
    minimum_stock NUMERIC(18,4) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_products_tenant_id UNIQUE (business_id, id),
    CONSTRAINT ck_products_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_products_unit CHECK (length(btrim(unit)) > 0),
    CONSTRAINT ck_products_prices CHECK (sales_price >= 0 AND cost_price >= 0),
    CONSTRAINT ck_products_minimum_stock CHECK (minimum_stock >= 0)
);

CREATE TABLE kasta.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    transaction_number VARCHAR(40) NOT NULL,
    transaction_type VARCHAR(30) NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT,
    currency_code CHAR(3) NOT NULL DEFAULT 'IDR',
    total_amount NUMERIC(18,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    payment_method_id UUID,
    customer_id UUID,
    supplier_id UUID,
    idempotency_key UUID,
    source VARCHAR(20) NOT NULL DEFAULT 'WEB',
    reversal_of_transaction_id UUID,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    posted_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    posted_at TIMESTAMPTZ,
    voided_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    voided_at TIMESTAMPTZ,
    void_reason TEXT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_transactions_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_transactions_number UNIQUE (business_id, transaction_number),
    CONSTRAINT fk_transactions_payment_method FOREIGN KEY (business_id, payment_method_id)
        REFERENCES kasta.payment_methods(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_transactions_customer FOREIGN KEY (business_id, customer_id)
        REFERENCES kasta.customers(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_transactions_supplier FOREIGN KEY (business_id, supplier_id)
        REFERENCES kasta.suppliers(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_transactions_reversal FOREIGN KEY (business_id, reversal_of_transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_transactions_number CHECK (length(btrim(transaction_number)) > 0),
    CONSTRAINT ck_transactions_type CHECK (
        transaction_type IN (
            'MONEY_IN', 'MONEY_OUT', 'CAPITAL_IN', 'OWNER_DRAW', 'SALE', 'PURCHASE',
            'RECEIVABLE_PAYMENT', 'PAYABLE_PAYMENT', 'STOCK_ADJUSTMENT', 'REVERSAL', 'ADJUSTMENT'
        )
    ),
    CONSTRAINT ck_transactions_currency CHECK (currency_code ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_transactions_amount CHECK (
        total_amount >= 0 AND (status = 'DRAFT' OR total_amount > 0)
    ),
    CONSTRAINT ck_transactions_status CHECK (status IN ('DRAFT', 'POSTED', 'VOIDED')),
    CONSTRAINT ck_transactions_party CHECK (num_nonnulls(customer_id, supplier_id) <= 1),
    CONSTRAINT ck_transactions_source CHECK (source IN ('WEB', 'ANDROID', 'IMPORT', 'SYSTEM')),
    CONSTRAINT ck_transactions_reversal CHECK (
        (transaction_type = 'REVERSAL') = (reversal_of_transaction_id IS NOT NULL)
    ),
    CONSTRAINT ck_transactions_posted CHECK (
        status = 'DRAFT' OR (posted_by_user_id IS NOT NULL AND posted_at IS NOT NULL)
    ),
    CONSTRAINT ck_transactions_voided CHECK (
        status <> 'VOIDED'
        OR (voided_by_user_id IS NOT NULL AND voided_at IS NOT NULL AND length(btrim(void_reason)) > 0)
    ),
    CONSTRAINT ck_transactions_revision CHECK (revision_no > 0),
    CONSTRAINT ck_transactions_soft_delete CHECK (deleted_at IS NULL OR status = 'DRAFT')
);

CREATE TABLE kasta.transaction_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    transaction_id UUID NOT NULL,
    line_no INTEGER NOT NULL,
    product_id UUID,
    account_id UUID,
    description VARCHAR(250) NOT NULL,
    quantity NUMERIC(18,4) NOT NULL DEFAULT 1,
    unit_price NUMERIC(18,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    line_total NUMERIC(18,2) GENERATED ALWAYS AS (
        round(quantity * unit_price, 2) - discount_amount + tax_amount
    ) STORED,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_transaction_items_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_transaction_items_line UNIQUE (transaction_id, line_no),
    CONSTRAINT fk_transaction_items_transaction FOREIGN KEY (business_id, transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_transaction_items_product FOREIGN KEY (business_id, product_id)
        REFERENCES kasta.products(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_transaction_items_account FOREIGN KEY (business_id, account_id)
        REFERENCES kasta.accounts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_transaction_items_line CHECK (line_no > 0),
    CONSTRAINT ck_transaction_items_description CHECK (length(btrim(description)) > 0),
    CONSTRAINT ck_transaction_items_quantity CHECK (quantity > 0),
    CONSTRAINT ck_transaction_items_amounts CHECK (
        unit_price >= 0 AND discount_amount >= 0 AND tax_amount >= 0 AND line_total >= 0
    ),
    CONSTRAINT ck_transaction_items_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    entry_number VARCHAR(40) NOT NULL,
    entry_date DATE NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    transaction_id UUID,
    reversal_of_entry_id UUID,
    memo TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    total_debit NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_credit NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    posted_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    posted_at TIMESTAMPTZ,
    reversed_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    reversed_at TIMESTAMPTZ,
    reversal_reason TEXT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_journal_entries_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_journal_entries_number UNIQUE (business_id, entry_number),
    CONSTRAINT fk_journal_entries_transaction FOREIGN KEY (business_id, transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_journal_entries_reversal FOREIGN KEY (business_id, reversal_of_entry_id)
        REFERENCES kasta.journal_entries(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_journal_entries_number CHECK (length(btrim(entry_number)) > 0),
    CONSTRAINT ck_journal_entries_source CHECK (
        source_type IN ('TRANSACTION', 'OPENING', 'ADJUSTMENT', 'CLOSING', 'REVERSAL', 'SYSTEM')
    ),
    CONSTRAINT ck_journal_entries_status CHECK (status IN ('DRAFT', 'POSTED', 'REVERSED')),
    CONSTRAINT ck_journal_entries_totals CHECK (
        total_debit >= 0 AND total_credit >= 0
        AND (status = 'DRAFT' OR (total_debit > 0 AND total_debit = total_credit))
    ),
    CONSTRAINT ck_journal_entries_posted CHECK (
        status = 'DRAFT' OR (posted_by_user_id IS NOT NULL AND posted_at IS NOT NULL)
    ),
    CONSTRAINT ck_journal_entries_reversed CHECK (
        status <> 'REVERSED'
        OR (
            reversed_by_user_id IS NOT NULL AND reversed_at IS NOT NULL
            AND length(btrim(reversal_reason)) > 0
        )
    ),
    CONSTRAINT ck_journal_entries_revision CHECK (revision_no > 0),
    CONSTRAINT ck_journal_entries_soft_delete CHECK (deleted_at IS NULL OR status = 'DRAFT')
);

CREATE TABLE kasta.journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    journal_entry_id UUID NOT NULL,
    line_no INTEGER NOT NULL,
    account_id UUID NOT NULL,
    transaction_item_id UUID,
    description VARCHAR(250),
    debit_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    credit_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_journal_lines_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_journal_lines_line UNIQUE (journal_entry_id, line_no),
    CONSTRAINT fk_journal_lines_entry FOREIGN KEY (business_id, journal_entry_id)
        REFERENCES kasta.journal_entries(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_journal_lines_account FOREIGN KEY (business_id, account_id)
        REFERENCES kasta.accounts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_journal_lines_item FOREIGN KEY (business_id, transaction_item_id)
        REFERENCES kasta.transaction_items(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_journal_lines_line CHECK (line_no > 0),
    CONSTRAINT ck_journal_lines_one_side CHECK (
        (debit_amount > 0 AND credit_amount = 0)
        OR (credit_amount > 0 AND debit_amount = 0)
    ),
    CONSTRAINT ck_journal_lines_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    transaction_id UUID NOT NULL,
    transaction_item_id UUID,
    movement_type VARCHAR(20) NOT NULL,
    movement_at TIMESTAMPTZ NOT NULL,
    quantity_delta NUMERIC(18,4) NOT NULL,
    unit_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    reversal_of_movement_id UUID,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_stock_movements_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_stock_movements_product FOREIGN KEY (business_id, product_id)
        REFERENCES kasta.products(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_stock_movements_transaction FOREIGN KEY (business_id, transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_stock_movements_item FOREIGN KEY (business_id, transaction_item_id)
        REFERENCES kasta.transaction_items(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_stock_movements_reversal FOREIGN KEY (business_id, reversal_of_movement_id)
        REFERENCES kasta.stock_movements(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_stock_movements_type CHECK (
        movement_type IN ('PURCHASE', 'SALE', 'RETURN_IN', 'RETURN_OUT', 'ADJUSTMENT', 'OPENING', 'REVERSAL')
    ),
    CONSTRAINT ck_stock_movements_quantity CHECK (quantity_delta <> 0),
    CONSTRAINT ck_stock_movements_cost CHECK (unit_cost >= 0),
    CONSTRAINT ck_stock_movements_reversal CHECK (
        (movement_type = 'REVERSAL') = (reversal_of_movement_id IS NOT NULL)
    ),
    CONSTRAINT ck_stock_movements_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.receivables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    receivable_number VARCHAR(40) NOT NULL,
    customer_id UUID NOT NULL,
    source_transaction_id UUID NOT NULL,
    account_id UUID NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    original_amount NUMERIC(18,2) NOT NULL,
    outstanding_amount NUMERIC(18,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_receivables_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_receivables_number UNIQUE (business_id, receivable_number),
    CONSTRAINT uq_receivables_source UNIQUE (business_id, source_transaction_id),
    CONSTRAINT fk_receivables_customer FOREIGN KEY (business_id, customer_id)
        REFERENCES kasta.customers(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_receivables_transaction FOREIGN KEY (business_id, source_transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_receivables_account FOREIGN KEY (business_id, account_id)
        REFERENCES kasta.accounts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_receivables_number CHECK (length(btrim(receivable_number)) > 0),
    CONSTRAINT ck_receivables_dates CHECK (due_date >= issue_date),
    CONSTRAINT ck_receivables_amounts CHECK (
        original_amount > 0 AND outstanding_amount BETWEEN 0 AND original_amount
    ),
    CONSTRAINT ck_receivables_status CHECK (
        status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'VOIDED')
    ),
    CONSTRAINT ck_receivables_status_balance CHECK (
        (status = 'PAID' AND outstanding_amount = 0)
        OR (status IN ('OPEN', 'PARTIALLY_PAID', 'OVERDUE') AND outstanding_amount > 0)
        OR status = 'VOIDED'
    ),
    CONSTRAINT ck_receivables_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.receivable_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    receivable_id UUID NOT NULL,
    transaction_id UUID NOT NULL,
    payment_method_id UUID NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
    reversal_of_payment_id UUID,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_receivable_payments_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_receivable_payments_transaction UNIQUE (business_id, transaction_id),
    CONSTRAINT fk_receivable_payments_receivable FOREIGN KEY (business_id, receivable_id)
        REFERENCES kasta.receivables(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_receivable_payments_transaction FOREIGN KEY (business_id, transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_receivable_payments_method FOREIGN KEY (business_id, payment_method_id)
        REFERENCES kasta.payment_methods(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_receivable_payments_reversal FOREIGN KEY (business_id, reversal_of_payment_id)
        REFERENCES kasta.receivable_payments(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_receivable_payments_amount CHECK (amount > 0),
    CONSTRAINT ck_receivable_payments_status CHECK (status IN ('POSTED', 'VOIDED')),
    CONSTRAINT ck_receivable_payments_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.payables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    payable_number VARCHAR(40) NOT NULL,
    supplier_id UUID NOT NULL,
    source_transaction_id UUID NOT NULL,
    account_id UUID NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    original_amount NUMERIC(18,2) NOT NULL,
    outstanding_amount NUMERIC(18,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_payables_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_payables_number UNIQUE (business_id, payable_number),
    CONSTRAINT uq_payables_source UNIQUE (business_id, source_transaction_id),
    CONSTRAINT fk_payables_supplier FOREIGN KEY (business_id, supplier_id)
        REFERENCES kasta.suppliers(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_payables_transaction FOREIGN KEY (business_id, source_transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_payables_account FOREIGN KEY (business_id, account_id)
        REFERENCES kasta.accounts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_payables_number CHECK (length(btrim(payable_number)) > 0),
    CONSTRAINT ck_payables_dates CHECK (due_date >= issue_date),
    CONSTRAINT ck_payables_amounts CHECK (
        original_amount > 0 AND outstanding_amount BETWEEN 0 AND original_amount
    ),
    CONSTRAINT ck_payables_status CHECK (
        status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'VOIDED')
    ),
    CONSTRAINT ck_payables_status_balance CHECK (
        (status = 'PAID' AND outstanding_amount = 0)
        OR (status IN ('OPEN', 'PARTIALLY_PAID', 'OVERDUE') AND outstanding_amount > 0)
        OR status = 'VOIDED'
    ),
    CONSTRAINT ck_payables_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.payable_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    payable_id UUID NOT NULL,
    transaction_id UUID NOT NULL,
    payment_method_id UUID NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
    reversal_of_payment_id UUID,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_payable_payments_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_payable_payments_transaction UNIQUE (business_id, transaction_id),
    CONSTRAINT fk_payable_payments_payable FOREIGN KEY (business_id, payable_id)
        REFERENCES kasta.payables(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_payable_payments_transaction FOREIGN KEY (business_id, transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_payable_payments_method FOREIGN KEY (business_id, payment_method_id)
        REFERENCES kasta.payment_methods(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_payable_payments_reversal FOREIGN KEY (business_id, reversal_of_payment_id)
        REFERENCES kasta.payable_payments(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_payable_payments_amount CHECK (amount > 0),
    CONSTRAINT ck_payable_payments_status CHECK (status IN ('POSTED', 'VOIDED')),
    CONSTRAINT ck_payable_payments_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    transaction_id UUID,
    uploaded_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    receipt_number VARCHAR(60),
    merchant_name VARCHAR(180),
    receipt_date DATE,
    total_amount NUMERIC(18,2),
    status VARCHAR(30) NOT NULL DEFAULT 'UPLOADING',
    notes TEXT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_receipts_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_receipts_transaction FOREIGN KEY (business_id, transaction_id)
        REFERENCES kasta.transactions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_receipts_amount CHECK (total_amount IS NULL OR total_amount >= 0),
    CONSTRAINT ck_receipts_status CHECK (
        status IN (
            'UPLOADING', 'READY', 'OCR_PROCESSING', 'REVIEW_REQUIRED',
            'CONFIRMED', 'FAILED', 'ARCHIVED'
        )
    ),
    CONSTRAINT ck_receipts_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.receipt_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    receipt_id UUID NOT NULL,
    bucket_name VARCHAR(100) NOT NULL,
    object_key VARCHAR(500) NOT NULL,
    etag VARCHAR(160),
    mime_type VARCHAR(100) NOT NULL,
    byte_size BIGINT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    width_px INTEGER,
    height_px INTEGER,
    page_number INTEGER NOT NULL DEFAULT 1,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    upload_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_receipt_images_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_receipt_images_object_key UNIQUE (object_key),
    CONSTRAINT fk_receipt_images_receipt FOREIGN KEY (business_id, receipt_id)
        REFERENCES kasta.receipts(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_receipt_images_bucket CHECK (length(btrim(bucket_name)) > 0),
    CONSTRAINT ck_receipt_images_object CHECK (length(btrim(object_key)) > 0),
    CONSTRAINT ck_receipt_images_mime CHECK (mime_type LIKE 'image/%' OR mime_type = 'application/pdf'),
    CONSTRAINT ck_receipt_images_size CHECK (byte_size > 0),
    CONSTRAINT ck_receipt_images_sha CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_receipt_images_dimensions CHECK (
        (width_px IS NULL OR width_px > 0) AND (height_px IS NULL OR height_px > 0)
    ),
    CONSTRAINT ck_receipt_images_page CHECK (page_number > 0),
    CONSTRAINT ck_receipt_images_upload CHECK (upload_status IN ('PENDING', 'UPLOADED', 'VERIFIED', 'FAILED'))
);

CREATE TABLE kasta.ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    receipt_image_id UUID NOT NULL,
    engine VARCHAR(30) NOT NULL,
    engine_version VARCHAR(60),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    confidence NUMERIC(5,4),
    raw_text TEXT,
    raw_payload JSONB,
    is_current BOOLEAN NOT NULL DEFAULT true,
    processed_at TIMESTAMPTZ,
    error_code VARCHAR(60),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_ocr_results_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_ocr_results_image FOREIGN KEY (business_id, receipt_image_id)
        REFERENCES kasta.receipt_images(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_ocr_results_engine CHECK (engine IN ('ML_KIT_DEVICE', 'SERVER', 'MANUAL')),
    CONSTRAINT ck_ocr_results_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    CONSTRAINT ck_ocr_results_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT ck_ocr_results_processed CHECK (status <> 'COMPLETED' OR processed_at IS NOT NULL),
    CONSTRAINT ck_ocr_results_payload CHECK (raw_payload IS NULL OR jsonb_typeof(raw_payload) = 'object')
);

CREATE TABLE kasta.ocr_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    ocr_result_id UUID NOT NULL,
    field_name VARCHAR(60) NOT NULL,
    occurrence INTEGER NOT NULL DEFAULT 1,
    raw_value TEXT,
    normalized_value TEXT,
    confidence NUMERIC(5,4),
    bounding_box JSONB,
    was_corrected BOOLEAN NOT NULL DEFAULT false,
    corrected_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    corrected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_ocr_fields_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_ocr_fields_result FOREIGN KEY (business_id, ocr_result_id)
        REFERENCES kasta.ocr_results(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_ocr_fields_name CHECK (length(btrim(field_name)) > 0),
    CONSTRAINT ck_ocr_fields_occurrence CHECK (occurrence > 0),
    CONSTRAINT ck_ocr_fields_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT ck_ocr_fields_bounding_box CHECK (
        bounding_box IS NULL OR jsonb_typeof(bounding_box) = 'object'
    ),
    CONSTRAINT ck_ocr_fields_corrected CHECK (
        (was_corrected AND corrected_by_user_id IS NOT NULL AND corrected_at IS NOT NULL)
        OR (NOT was_corrected AND corrected_by_user_id IS NULL AND corrected_at IS NULL)
    )
);

CREATE TABLE kasta.mentor_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    mentor_id UUID NOT NULL REFERENCES kasta.mentors(id) ON DELETE RESTRICT,
    mentor_business_access_id UUID NOT NULL,
    subject VARCHAR(180) NOT NULL,
    note_body TEXT NOT NULL,
    visibility VARCHAR(30) NOT NULL DEFAULT 'OWNER_ONLY',
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_mentor_notes_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_mentor_notes_access FOREIGN KEY (business_id, mentor_business_access_id, mentor_id)
        REFERENCES kasta.mentor_business_access(business_id, id, mentor_id) ON DELETE RESTRICT,
    CONSTRAINT ck_mentor_notes_subject CHECK (length(btrim(subject)) > 0),
    CONSTRAINT ck_mentor_notes_body CHECK (length(btrim(note_body)) > 0),
    CONSTRAINT ck_mentor_notes_visibility CHECK (visibility IN ('OWNER_ONLY', 'OWNER_AND_STAFF')),
    CONSTRAINT ck_mentor_notes_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    mentor_id UUID NOT NULL REFERENCES kasta.mentors(id) ON DELETE RESTRICT,
    mentor_business_access_id UUID NOT NULL,
    mentor_note_id UUID,
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(40) NOT NULL,
    priority VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    due_date DATE,
    acknowledged_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    acknowledged_at TIMESTAMPTZ,
    completed_by_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    completed_at TIMESTAMPTZ,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_recommendations_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_recommendations_access FOREIGN KEY (business_id, mentor_business_access_id, mentor_id)
        REFERENCES kasta.mentor_business_access(business_id, id, mentor_id) ON DELETE RESTRICT,
    CONSTRAINT fk_recommendations_note FOREIGN KEY (business_id, mentor_note_id)
        REFERENCES kasta.mentor_notes(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_recommendations_title CHECK (length(btrim(title)) > 0),
    CONSTRAINT ck_recommendations_description CHECK (length(btrim(description)) > 0),
    CONSTRAINT ck_recommendations_category CHECK (length(btrim(category)) > 0),
    CONSTRAINT ck_recommendations_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    CONSTRAINT ck_recommendations_status CHECK (
        status IN ('OPEN', 'ACKNOWLEDGED', 'IN_PROGRESS', 'DONE', 'DISMISSED')
    ),
    CONSTRAINT ck_recommendations_acknowledged CHECK (
        (acknowledged_by_user_id IS NULL) = (acknowledged_at IS NULL)
    ),
    CONSTRAINT ck_recommendations_completed CHECK (
        (status = 'DONE' AND completed_by_user_id IS NOT NULL AND completed_at IS NOT NULL)
        OR (status <> 'DONE')
    ),
    CONSTRAINT ck_recommendations_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.mentoring_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    mentor_id UUID NOT NULL REFERENCES kasta.mentors(id) ON DELETE RESTRICT,
    mentor_business_access_id UUID NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    channel VARCHAR(20) NOT NULL,
    location VARCHAR(250),
    status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    summary TEXT,
    action_items TEXT,
    created_by_user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_mentoring_sessions_tenant_id UNIQUE (business_id, id),
    CONSTRAINT fk_mentoring_sessions_access FOREIGN KEY (business_id, mentor_business_access_id, mentor_id)
        REFERENCES kasta.mentor_business_access(business_id, id, mentor_id) ON DELETE RESTRICT,
    CONSTRAINT ck_mentoring_sessions_channel CHECK (channel IN ('IN_PERSON', 'PHONE', 'VIDEO', 'CHAT')),
    CONSTRAINT ck_mentoring_sessions_status CHECK (
        status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW')
    ),
    CONSTRAINT ck_mentoring_sessions_time CHECK (ended_at IS NULL OR ended_at > started_at),
    CONSTRAINT ck_mentoring_sessions_completed CHECK (
        status <> 'COMPLETED' OR (started_at IS NOT NULL AND ended_at IS NOT NULL)
    ),
    CONSTRAINT ck_mentoring_sessions_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(180) NOT NULL,
    message TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    channel VARCHAR(20) NOT NULL DEFAULT 'IN_APP',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_notifications_type CHECK (length(btrim(notification_type)) > 0),
    CONSTRAINT ck_notifications_title CHECK (length(btrim(title)) > 0),
    CONSTRAINT ck_notifications_message CHECK (length(btrim(message)) > 0),
    CONSTRAINT ck_notifications_payload CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT ck_notifications_channel CHECK (channel IN ('IN_APP', 'PUSH', 'EMAIL')),
    CONSTRAINT ck_notifications_status CHECK (status IN ('PENDING', 'SENT', 'READ', 'FAILED', 'CANCELLED')),
    CONSTRAINT ck_notifications_sent CHECK (status NOT IN ('SENT', 'READ') OR sent_at IS NOT NULL),
    CONSTRAINT ck_notifications_read CHECK (status <> 'READ' OR read_at IS NOT NULL),
    CONSTRAINT ck_notifications_failed CHECK (status <> 'FAILED' OR failed_at IS NOT NULL)
);

CREATE TABLE kasta.device_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES kasta.users(id) ON DELETE RESTRICT,
    business_id UUID REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    device_identifier_hash CHAR(64) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    device_name VARCHAR(120),
    app_version VARCHAR(30),
    refresh_token_hash TEXT NOT NULL,
    push_token_ciphertext TEXT,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revision_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_device_sessions_tenant_id UNIQUE (business_id, id),
    CONSTRAINT ck_device_sessions_hash CHECK (device_identifier_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_device_sessions_platform CHECK (platform IN ('ANDROID', 'WEB')),
    CONSTRAINT ck_device_sessions_expiry CHECK (expires_at > created_at),
    CONSTRAINT ck_device_sessions_revision CHECK (revision_no > 0)
);

CREATE TABLE kasta.sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    device_session_id UUID NOT NULL,
    client_batch_id UUID NOT NULL,
    client_operation_id UUID NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL,
    client_revision INTEGER NOT NULL,
    server_revision BIGINT,
    status VARCHAR(20) NOT NULL,
    request_hash CHAR(64) NOT NULL,
    conflict_payload JSONB,
    error_code VARCHAR(60),
    error_message TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sync_logs_tenant_id UNIQUE (business_id, id),
    CONSTRAINT uq_sync_logs_operation UNIQUE (business_id, device_session_id, client_operation_id),
    CONSTRAINT fk_sync_logs_device FOREIGN KEY (business_id, device_session_id)
        REFERENCES kasta.device_sessions(business_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_sync_logs_direction CHECK (direction IN ('PUSH', 'PULL')),
    CONSTRAINT ck_sync_logs_entity CHECK (length(btrim(entity_type)) > 0),
    CONSTRAINT ck_sync_logs_operation CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    CONSTRAINT ck_sync_logs_revision CHECK (
        client_revision >= 0 AND (server_revision IS NULL OR server_revision >= 0)
    ),
    CONSTRAINT ck_sync_logs_status CHECK (
        status IN ('APPLIED', 'CONFLICT', 'REJECTED', 'DUPLICATE', 'PENDING')
    ),
    CONSTRAINT ck_sync_logs_hash CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_sync_logs_conflict CHECK (
        conflict_payload IS NULL OR jsonb_typeof(conflict_payload) = 'object'
    )
);

CREATE TABLE kasta.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES kasta.businesses(id) ON DELETE RESTRICT,
    actor_user_id UUID REFERENCES kasta.users(id) ON DELETE RESTRICT,
    action VARCHAR(30) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id UUID,
    entity_revision INTEGER,
    before_data JSONB,
    after_data JSONB,
    changed_fields TEXT[] NOT NULL DEFAULT '{}'::text[],
    correlation_id UUID,
    request_id UUID,
    source VARCHAR(20) NOT NULL DEFAULT 'API',
    ip_address INET,
    user_agent TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    previous_hash BYTEA,
    entry_hash BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_audit_logs_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'EXPORT', 'ACCESS')),
    CONSTRAINT ck_audit_logs_entity CHECK (length(btrim(entity_type)) > 0),
    CONSTRAINT ck_audit_logs_revision CHECK (entity_revision IS NULL OR entity_revision > 0),
    CONSTRAINT ck_audit_logs_source CHECK (source IN ('API', 'WEB', 'ANDROID', 'WORKER', 'ADMIN', 'SYSTEM')),
    CONSTRAINT ck_audit_logs_snapshot CHECK (
        action NOT IN ('INSERT', 'UPDATE', 'DELETE') OR before_data IS NOT NULL OR after_data IS NOT NULL
    )
);

-- Unique and lookup indexes. Tenant columns lead tenant-scoped indexes for RLS locality.
CREATE UNIQUE INDEX uq_users_email_active ON kasta.users(email)
    WHERE email IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX uq_users_phone_active ON kasta.users(phone)
    WHERE phone IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_users_platform_role ON kasta.users(platform_role_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_users_status ON kasta.users(status) WHERE deleted_at IS NULL;

CREATE INDEX ix_roles_name_active ON kasta.roles(lower(name)) WHERE deleted_at IS NULL;
CREATE INDEX ix_permissions_module_code ON kasta.permissions(module, code) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_role_permissions_active
    ON kasta.role_permissions(role_id, permission_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_role_permissions_permission ON kasta.role_permissions(permission_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uq_organizations_code_active ON kasta.organizations(lower(code))
    WHERE deleted_at IS NULL;
CREATE INDEX ix_organizations_type_status ON kasta.organizations(organization_type, status)
    WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_businesses_code_active ON kasta.businesses(lower(code))
    WHERE deleted_at IS NULL;
CREATE INDEX ix_businesses_organization ON kasta.businesses(organization_id)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_businesses_status ON kasta.businesses(status) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uq_business_members_active ON kasta.business_members(business_id, user_id)
    WHERE deleted_at IS NULL AND status <> 'LEFT';
CREATE INDEX ix_business_members_user_status ON kasta.business_members(user_id, status)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_business_members_role ON kasta.business_members(business_id, role_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uq_mentors_user_active ON kasta.mentors(user_id) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_mentors_code_active ON kasta.mentors(lower(mentor_code))
    WHERE deleted_at IS NULL;
CREATE INDEX ix_mentors_organization_status ON kasta.mentors(organization_id, status)
    WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_mentor_access_open ON kasta.mentor_business_access(business_id, mentor_id)
    WHERE deleted_at IS NULL AND status IN ('REQUESTED', 'ACTIVE');
CREATE INDEX ix_mentor_access_mentor_status
    ON kasta.mentor_business_access(mentor_id, status, expires_at) WHERE deleted_at IS NULL;
CREATE INDEX ix_mentor_access_business_status
    ON kasta.mentor_business_access(business_id, status) WHERE deleted_at IS NULL;

CREATE INDEX ix_account_categories_type_order
    ON kasta.account_categories(account_type, display_order) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_accounts_code_active ON kasta.accounts(business_id, lower(code))
    WHERE deleted_at IS NULL;
CREATE INDEX ix_accounts_category ON kasta.accounts(business_id, category_id)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_accounts_parent ON kasta.accounts(business_id, parent_account_id)
    WHERE parent_account_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_accounts_active ON kasta.accounts(business_id, is_active) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uq_payment_methods_code_active
    ON kasta.payment_methods(business_id, lower(code)) WHERE deleted_at IS NULL;
CREATE INDEX ix_payment_methods_account ON kasta.payment_methods(business_id, account_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uq_customers_code_active ON kasta.customers(business_id, lower(code))
    WHERE code IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_customers_name ON kasta.customers(business_id, lower(name)) WHERE deleted_at IS NULL;
CREATE INDEX ix_customers_phone ON kasta.customers(business_id, phone)
    WHERE phone IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX uq_suppliers_code_active ON kasta.suppliers(business_id, lower(code))
    WHERE code IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_suppliers_name ON kasta.suppliers(business_id, lower(name)) WHERE deleted_at IS NULL;
CREATE INDEX ix_suppliers_phone ON kasta.suppliers(business_id, phone)
    WHERE phone IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX uq_products_sku_active ON kasta.products(business_id, lower(sku))
    WHERE sku IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_products_name ON kasta.products(business_id, lower(name)) WHERE deleted_at IS NULL;
CREATE INDEX ix_products_active ON kasta.products(business_id, is_active) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uq_transactions_idempotency ON kasta.transactions(business_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX uq_transactions_reversal ON kasta.transactions(business_id, reversal_of_transaction_id)
    WHERE reversal_of_transaction_id IS NOT NULL;
CREATE INDEX ix_transactions_business_date
    ON kasta.transactions(business_id, transaction_date DESC, id) WHERE deleted_at IS NULL;
CREATE INDEX ix_transactions_status_date
    ON kasta.transactions(business_id, status, transaction_date DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_transactions_customer_date
    ON kasta.transactions(business_id, customer_id, transaction_date DESC)
    WHERE customer_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_transactions_supplier_date
    ON kasta.transactions(business_id, supplier_id, transaction_date DESC)
    WHERE supplier_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_transaction_items_product ON kasta.transaction_items(business_id, product_id)
    WHERE product_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_transaction_items_account ON kasta.transaction_items(business_id, account_id)
    WHERE account_id IS NOT NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX uq_journal_entries_transaction
    ON kasta.journal_entries(business_id, transaction_id) WHERE transaction_id IS NOT NULL;
CREATE UNIQUE INDEX uq_journal_entries_reversal
    ON kasta.journal_entries(business_id, reversal_of_entry_id) WHERE reversal_of_entry_id IS NOT NULL;
CREATE INDEX ix_journal_entries_date
    ON kasta.journal_entries(business_id, entry_date DESC, id) WHERE deleted_at IS NULL;
CREATE INDEX ix_journal_entries_status_date
    ON kasta.journal_entries(business_id, status, entry_date DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_journal_lines_account_entry
    ON kasta.journal_lines(business_id, account_id, journal_entry_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_journal_lines_item ON kasta.journal_lines(business_id, transaction_item_id)
    WHERE transaction_item_id IS NOT NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX uq_stock_movements_reversal
    ON kasta.stock_movements(business_id, reversal_of_movement_id)
    WHERE reversal_of_movement_id IS NOT NULL;
CREATE INDEX ix_stock_movements_product_time
    ON kasta.stock_movements(business_id, product_id, movement_at DESC, id);
CREATE INDEX ix_stock_movements_transaction ON kasta.stock_movements(business_id, transaction_id);

CREATE INDEX ix_receivables_due_open ON kasta.receivables(business_id, due_date, id)
    WHERE status IN ('OPEN', 'PARTIALLY_PAID', 'OVERDUE');
CREATE INDEX ix_receivables_customer_status
    ON kasta.receivables(business_id, customer_id, status);
CREATE UNIQUE INDEX uq_receivable_payments_reversal
    ON kasta.receivable_payments(business_id, reversal_of_payment_id)
    WHERE reversal_of_payment_id IS NOT NULL;
CREATE INDEX ix_receivable_payments_receivable_date
    ON kasta.receivable_payments(business_id, receivable_id, payment_date DESC);
CREATE INDEX ix_receivable_payments_method_date
    ON kasta.receivable_payments(business_id, payment_method_id, payment_date DESC);

CREATE INDEX ix_payables_due_open ON kasta.payables(business_id, due_date, id)
    WHERE status IN ('OPEN', 'PARTIALLY_PAID', 'OVERDUE');
CREATE INDEX ix_payables_supplier_status ON kasta.payables(business_id, supplier_id, status);
CREATE UNIQUE INDEX uq_payable_payments_reversal
    ON kasta.payable_payments(business_id, reversal_of_payment_id)
    WHERE reversal_of_payment_id IS NOT NULL;
CREATE INDEX ix_payable_payments_payable_date
    ON kasta.payable_payments(business_id, payable_id, payment_date DESC);
CREATE INDEX ix_payable_payments_method_date
    ON kasta.payable_payments(business_id, payment_method_id, payment_date DESC);

CREATE UNIQUE INDEX uq_receipts_number_active ON kasta.receipts(business_id, receipt_number)
    WHERE receipt_number IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_receipts_transaction ON kasta.receipts(business_id, transaction_id)
    WHERE transaction_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_receipts_status_date ON kasta.receipts(business_id, status, receipt_date DESC)
    WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_receipt_images_page_active
    ON kasta.receipt_images(business_id, receipt_id, page_number) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_receipt_images_primary_active
    ON kasta.receipt_images(business_id, receipt_id) WHERE is_primary AND deleted_at IS NULL;
CREATE INDEX ix_receipt_images_status ON kasta.receipt_images(business_id, receipt_id, upload_status)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_receipt_images_sha ON kasta.receipt_images(sha256) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_ocr_results_current
    ON kasta.ocr_results(business_id, receipt_image_id) WHERE is_current AND deleted_at IS NULL;
CREATE INDEX ix_ocr_results_image_time
    ON kasta.ocr_results(business_id, receipt_image_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_ocr_results_status ON kasta.ocr_results(business_id, status, created_at)
    WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_ocr_fields_active
    ON kasta.ocr_fields(business_id, ocr_result_id, field_name, occurrence)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_ocr_fields_result_name
    ON kasta.ocr_fields(business_id, ocr_result_id, field_name) WHERE deleted_at IS NULL;

CREATE INDEX ix_mentor_notes_business_time
    ON kasta.mentor_notes(business_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_mentor_notes_mentor_time
    ON kasta.mentor_notes(mentor_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_recommendations_status_due
    ON kasta.recommendations(business_id, status, due_date) WHERE deleted_at IS NULL;
CREATE INDEX ix_recommendations_mentor_time
    ON kasta.recommendations(mentor_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_recommendations_note
    ON kasta.recommendations(business_id, mentor_note_id)
    WHERE mentor_note_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_mentoring_sessions_business_schedule
    ON kasta.mentoring_sessions(business_id, scheduled_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_mentoring_sessions_mentor_schedule
    ON kasta.mentoring_sessions(mentor_id, scheduled_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX ix_notifications_unread
    ON kasta.notifications(user_id, created_at DESC) WHERE read_at IS NULL AND deleted_at IS NULL;
CREATE INDEX ix_notifications_business_time
    ON kasta.notifications(business_id, created_at DESC)
    WHERE business_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_notifications_delivery
    ON kasta.notifications(status, scheduled_at, created_at)
    WHERE status = 'PENDING' AND deleted_at IS NULL;

CREATE UNIQUE INDEX uq_device_sessions_active
    ON kasta.device_sessions(
        user_id,
        COALESCE(business_id, '00000000-0000-0000-0000-000000000000'::uuid),
        device_identifier_hash
    ) WHERE revoked_at IS NULL AND deleted_at IS NULL;
CREATE INDEX ix_device_sessions_user_seen
    ON kasta.device_sessions(user_id, last_seen_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX ix_device_sessions_business_user
    ON kasta.device_sessions(business_id, user_id) WHERE business_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_device_sessions_expiry
    ON kasta.device_sessions(expires_at) WHERE revoked_at IS NULL AND deleted_at IS NULL;

CREATE INDEX ix_sync_logs_device_batch
    ON kasta.sync_logs(business_id, device_session_id, client_batch_id, created_at);
CREATE INDEX ix_sync_logs_server_revision
    ON kasta.sync_logs(business_id, server_revision) WHERE server_revision IS NOT NULL;
CREATE INDEX ix_sync_logs_status_time ON kasta.sync_logs(business_id, status, created_at);
CREATE INDEX ix_sync_logs_created_brin ON kasta.sync_logs USING brin(created_at);

CREATE INDEX ix_audit_logs_entity_history
    ON kasta.audit_logs(business_id, entity_type, entity_id, occurred_at DESC)
    WHERE entity_id IS NOT NULL;
CREATE INDEX ix_audit_logs_actor_time ON kasta.audit_logs(actor_user_id, occurred_at DESC)
    WHERE actor_user_id IS NOT NULL;
CREATE INDEX ix_audit_logs_correlation ON kasta.audit_logs(correlation_id)
    WHERE correlation_id IS NOT NULL;
CREATE INDEX ix_audit_logs_occurred_brin ON kasta.audit_logs USING brin(occurred_at);

-- Consistent timestamps and optimistic revision numbers.
CREATE OR REPLACE FUNCTION kasta.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION kasta.bump_revision_no()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.revision_no := OLD.revision_no + 1;
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'roles', 'permissions', 'users', 'organizations', 'businesses', 'role_permissions',
        'business_members', 'mentors', 'mentor_business_access', 'account_categories', 'accounts',
        'payment_methods', 'customers', 'suppliers', 'products', 'transactions', 'transaction_items',
        'journal_entries', 'journal_lines', 'receivables', 'receivable_payments', 'payables',
        'payable_payments', 'receipts', 'receipt_images', 'ocr_results', 'ocr_fields', 'mentor_notes',
        'recommendations', 'mentoring_sessions', 'notifications', 'device_sessions'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_touch_updated_at BEFORE UPDATE ON kasta.%I '
            'FOR EACH ROW EXECUTE FUNCTION kasta.touch_updated_at()',
            table_name
        );
    END LOOP;

    FOREACH table_name IN ARRAY ARRAY[
        'mentor_business_access', 'transactions', 'transaction_items', 'journal_entries',
        'journal_lines', 'receivables', 'receivable_payments', 'payables', 'payable_payments',
        'receipts', 'mentor_notes', 'recommendations', 'mentoring_sessions', 'device_sessions'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_bump_revision BEFORE UPDATE ON kasta.%I '
            'FOR EACH ROW EXECUTE FUNCTION kasta.bump_revision_no()',
            table_name
        );
    END LOOP;
END;
$$;

-- Financial records are never physically deleted. Reversal rows are the correction mechanism.
CREATE OR REPLACE FUNCTION kasta.forbid_financial_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'hard delete is forbidden for financial table %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = '23514';
END;
$$;

DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'transactions', 'transaction_items', 'journal_entries', 'journal_lines', 'stock_movements',
        'receivables', 'receivable_payments', 'payables', 'payable_payments'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_forbid_financial_delete BEFORE DELETE ON kasta.%I '
            'FOR EACH ROW EXECUTE FUNCTION kasta.forbid_financial_delete()',
            table_name
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION kasta.forbid_all_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'update/delete is forbidden for append-only table %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = '23514';
END;
$$;

CREATE TRIGGER trg_stock_movements_append_only
BEFORE UPDATE OR DELETE ON kasta.stock_movements
FOR EACH ROW EXECUTE FUNCTION kasta.forbid_all_mutation();

CREATE TRIGGER trg_sync_logs_append_only
BEFORE UPDATE OR DELETE ON kasta.sync_logs
FOR EACH ROW EXECUTE FUNCTION kasta.forbid_all_mutation();

CREATE TRIGGER trg_audit_logs_append_only
BEFORE UPDATE OR DELETE ON kasta.audit_logs
FOR EACH ROW EXECUTE FUNCTION kasta.forbid_all_mutation();

-- Posted transactions can only move to VOIDED while their financial facts remain unchanged.
CREATE OR REPLACE FUNCTION kasta.protect_transaction_state()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    old_facts JSONB;
    new_facts JSONB;
BEGIN
    IF OLD.status = 'VOIDED' THEN
        RAISE EXCEPTION 'voided transaction % is immutable', OLD.id USING ERRCODE = '23514';
    END IF;

    IF OLD.status = 'POSTED' THEN
        old_facts := to_jsonb(OLD) - ARRAY[
            'status', 'voided_by_user_id', 'voided_at', 'void_reason', 'revision_no', 'updated_at'
        ]::text[];
        new_facts := to_jsonb(NEW) - ARRAY[
            'status', 'voided_by_user_id', 'voided_at', 'void_reason', 'revision_no', 'updated_at'
        ]::text[];

        IF NEW.status <> 'VOIDED' OR old_facts IS DISTINCT FROM new_facts THEN
            RAISE EXCEPTION 'posted transaction % may only be voided; create a reversal', OLD.id
                USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.status = 'DRAFT' AND NEW.status NOT IN ('DRAFT', 'POSTED') THEN
        RAISE EXCEPTION 'invalid transaction status transition % -> %', OLD.status, NEW.status
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_protect_transaction_state
BEFORE UPDATE ON kasta.transactions
FOR EACH ROW EXECUTE FUNCTION kasta.protect_transaction_state();

-- Posted journals can only move to REVERSED while original monetary facts remain unchanged.
CREATE OR REPLACE FUNCTION kasta.protect_journal_state()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    old_facts JSONB;
    new_facts JSONB;
BEGIN
    IF OLD.status = 'REVERSED' THEN
        RAISE EXCEPTION 'reversed journal entry % is immutable', OLD.id USING ERRCODE = '23514';
    END IF;

    IF OLD.status = 'POSTED' THEN
        old_facts := to_jsonb(OLD) - ARRAY[
            'status', 'reversed_by_user_id', 'reversed_at', 'reversal_reason', 'revision_no', 'updated_at'
        ]::text[];
        new_facts := to_jsonb(NEW) - ARRAY[
            'status', 'reversed_by_user_id', 'reversed_at', 'reversal_reason', 'revision_no', 'updated_at'
        ]::text[];

        IF NEW.status <> 'REVERSED' OR old_facts IS DISTINCT FROM new_facts THEN
            RAISE EXCEPTION 'posted journal entry % may only be reversed', OLD.id
                USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.status = 'DRAFT' AND NEW.status NOT IN ('DRAFT', 'POSTED') THEN
        RAISE EXCEPTION 'invalid journal status transition % -> %', OLD.status, NEW.status
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_protect_journal_state
BEFORE UPDATE ON kasta.journal_entries
FOR EACH ROW EXECUTE FUNCTION kasta.protect_journal_state();

-- Items and journal lines are editable only while their parent aggregate is DRAFT.
CREATE OR REPLACE FUNCTION kasta.guard_transaction_item_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_business_id UUID := COALESCE(NEW.business_id, OLD.business_id);
    target_transaction_id UUID := COALESCE(NEW.transaction_id, OLD.transaction_id);
    parent_status VARCHAR(20);
BEGIN
    SELECT status INTO parent_status
    FROM kasta.transactions
    WHERE business_id = target_business_id AND id = target_transaction_id;

    IF parent_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'transaction items are immutable unless parent transaction is DRAFT'
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_guard_transaction_item_mutation
BEFORE INSERT OR UPDATE OR DELETE ON kasta.transaction_items
FOR EACH ROW EXECUTE FUNCTION kasta.guard_transaction_item_mutation();

CREATE OR REPLACE FUNCTION kasta.guard_journal_line_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_business_id UUID := COALESCE(NEW.business_id, OLD.business_id);
    target_entry_id UUID := COALESCE(NEW.journal_entry_id, OLD.journal_entry_id);
    parent_status VARCHAR(20);
BEGIN
    SELECT status INTO parent_status
    FROM kasta.journal_entries
    WHERE business_id = target_business_id AND id = target_entry_id;

    IF parent_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'journal lines are immutable unless parent entry is DRAFT'
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_guard_journal_line_mutation
BEFORE INSERT OR UPDATE OR DELETE ON kasta.journal_lines
FOR EACH ROW EXECUTE FUNCTION kasta.guard_journal_line_mutation();

-- Deferred balance validation lets a service insert all lines and post in one SQL transaction.
CREATE OR REPLACE FUNCTION kasta.assert_journal_entry_balanced(target_entry_id UUID)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    entry_status VARCHAR(20);
    cached_debit NUMERIC(18,2);
    cached_credit NUMERIC(18,2);
    calculated_debit NUMERIC(18,2);
    calculated_credit NUMERIC(18,2);
    active_line_count BIGINT;
BEGIN
    SELECT status, total_debit, total_credit
    INTO entry_status, cached_debit, cached_credit
    FROM kasta.journal_entries
    WHERE id = target_entry_id;

    IF NOT FOUND OR entry_status = 'DRAFT' THEN
        RETURN;
    END IF;

    SELECT
        count(*),
        COALESCE(sum(debit_amount), 0)::NUMERIC(18,2),
        COALESCE(sum(credit_amount), 0)::NUMERIC(18,2)
    INTO active_line_count, calculated_debit, calculated_credit
    FROM kasta.journal_lines
    WHERE journal_entry_id = target_entry_id AND deleted_at IS NULL;

    IF active_line_count < 2
        OR calculated_debit <= 0
        OR calculated_debit <> calculated_credit
        OR cached_debit <> calculated_debit
        OR cached_credit <> calculated_credit
    THEN
        RAISE EXCEPTION 'journal entry % is not balanced', target_entry_id USING ERRCODE = '23514';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION kasta.check_journal_balance_from_line()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM kasta.assert_journal_entry_balanced(COALESCE(NEW.journal_entry_id, OLD.journal_entry_id));
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE FUNCTION kasta.check_journal_balance_from_entry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM kasta.assert_journal_entry_balanced(NEW.id);
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_journal_lines_balanced
AFTER INSERT OR UPDATE OR DELETE ON kasta.journal_lines
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION kasta.check_journal_balance_from_line();

CREATE CONSTRAINT TRIGGER trg_journal_entry_balanced
AFTER INSERT OR UPDATE ON kasta.journal_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION kasta.check_journal_balance_from_entry();

CREATE OR REPLACE FUNCTION kasta.ensure_posted_transaction_has_journal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status IN ('POSTED', 'VOIDED') AND NOT EXISTS (
        SELECT 1
        FROM kasta.journal_entries entry
        WHERE entry.business_id = NEW.business_id
          AND entry.transaction_id = NEW.id
          AND entry.status IN ('POSTED', 'REVERSED')
          AND entry.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'posted transaction % requires a posted journal entry', NEW.id
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_posted_transaction_has_journal
AFTER INSERT OR UPDATE ON kasta.transactions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION kasta.ensure_posted_transaction_has_journal();

CREATE OR REPLACE FUNCTION kasta.validate_stock_reversal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    original_product_id UUID;
    original_quantity NUMERIC(18,4);
BEGIN
    IF NEW.reversal_of_movement_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT product_id, quantity_delta
    INTO original_product_id, original_quantity
    FROM kasta.stock_movements
    WHERE business_id = NEW.business_id AND id = NEW.reversal_of_movement_id;

    IF original_product_id IS DISTINCT FROM NEW.product_id OR NEW.quantity_delta <> -original_quantity THEN
        RAISE EXCEPTION 'stock reversal % must exactly negate the original movement', NEW.id
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_validate_stock_reversal
AFTER INSERT ON kasta.stock_movements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION kasta.validate_stock_reversal();

-- Immutable audit trail written in the same database transaction as the source change.
CREATE OR REPLACE FUNCTION kasta.write_audit_log()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = kasta, pg_catalog
AS $$
DECLARE
    old_snapshot JSONB;
    new_snapshot JSONB;
    redacted_old JSONB;
    redacted_new JSONB;
    target_business_id UUID;
    target_entity_id UUID;
    target_revision INTEGER;
    actor_id UUID;
    correlation UUID;
    request UUID;
    request_ip INET;
    audit_source VARCHAR(20);
    fields TEXT[];
BEGIN
    IF TG_OP <> 'INSERT' THEN
        old_snapshot := to_jsonb(OLD);
    END IF;
    IF TG_OP <> 'DELETE' THEN
        new_snapshot := to_jsonb(NEW);
    END IF;

    SELECT COALESCE(array_agg(key ORDER BY key), ARRAY[]::text[])
    INTO fields
    FROM jsonb_object_keys(
        COALESCE(old_snapshot, '{}'::jsonb) || COALESCE(new_snapshot, '{}'::jsonb)
    ) AS keys(key)
    WHERE old_snapshot -> key IS DISTINCT FROM new_snapshot -> key;

    redacted_old := old_snapshot - ARRAY[
        'password_hash', 'refresh_token_hash', 'push_token_ciphertext', 'raw_text', 'raw_payload'
    ]::text[];
    redacted_new := new_snapshot - ARRAY[
        'password_hash', 'refresh_token_hash', 'push_token_ciphertext', 'raw_text', 'raw_payload'
    ]::text[];

    target_business_id := COALESCE(
        NULLIF(new_snapshot ->> 'business_id', '')::uuid,
        NULLIF(old_snapshot ->> 'business_id', '')::uuid
    );
    target_entity_id := COALESCE(
        NULLIF(new_snapshot ->> 'id', '')::uuid,
        NULLIF(old_snapshot ->> 'id', '')::uuid
    );
    target_revision := COALESCE(
        NULLIF(new_snapshot ->> 'revision_no', '')::integer,
        NULLIF(old_snapshot ->> 'revision_no', '')::integer
    );
    actor_id := NULLIF(current_setting('app.user_id', true), '')::uuid;
    correlation := NULLIF(current_setting('app.correlation_id', true), '')::uuid;
    request := NULLIF(current_setting('app.request_id', true), '')::uuid;
    request_ip := NULLIF(current_setting('app.ip_address', true), '')::inet;
    audit_source := upper(COALESCE(NULLIF(current_setting('app.source', true), ''), 'API'));

    INSERT INTO kasta.audit_logs (
        business_id,
        actor_user_id,
        action,
        entity_type,
        entity_id,
        entity_revision,
        before_data,
        after_data,
        changed_fields,
        correlation_id,
        request_id,
        source,
        ip_address,
        user_agent
    ) VALUES (
        target_business_id,
        actor_id,
        TG_OP,
        TG_TABLE_NAME,
        target_entity_id,
        target_revision,
        redacted_old,
        redacted_new,
        fields,
        correlation,
        request,
        audit_source,
        request_ip,
        NULLIF(current_setting('app.user_agent', true), '')
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'roles', 'permissions', 'users', 'organizations', 'businesses', 'role_permissions',
        'business_members', 'mentors', 'mentor_business_access', 'account_categories', 'accounts',
        'payment_methods', 'customers', 'suppliers', 'products', 'transactions', 'transaction_items',
        'journal_entries', 'journal_lines', 'stock_movements', 'receivables', 'receivable_payments',
        'payables', 'payable_payments', 'receipts', 'receipt_images', 'ocr_results', 'ocr_fields',
        'mentor_notes', 'recommendations', 'mentoring_sessions', 'device_sessions'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_audit_changes AFTER INSERT OR UPDATE OR DELETE ON kasta.%I '
            'FOR EACH ROW EXECUTE FUNCTION kasta.write_audit_log()',
            table_name
        );
    END LOOP;
END;
$$;

-- Transaction-local application context used by Row-Level Security.
CREATE OR REPLACE FUNCTION kasta.current_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION kasta.current_business_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.business_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION kasta.is_platform_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(NULLIF(current_setting('app.is_platform_admin', true), ''), 'false')::boolean
$$;

-- Generic tenant policy. Backend authorization must validate membership/mentor scope before setting
-- app.business_id. Runtime roles must not own these tables or have BYPASSRLS.
DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'business_members', 'mentor_business_access', 'accounts', 'payment_methods', 'customers',
        'suppliers', 'products', 'transactions', 'transaction_items', 'journal_entries',
        'journal_lines', 'stock_movements', 'receivables', 'receivable_payments', 'payables',
        'payable_payments', 'receipts', 'receipt_images', 'ocr_results', 'ocr_fields', 'mentor_notes',
        'recommendations', 'mentoring_sessions', 'sync_logs'
    ] LOOP
        EXECUTE format('ALTER TABLE kasta.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE kasta.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON kasta.%I '
            'USING (business_id = kasta.current_business_id() OR kasta.is_platform_admin()) '
            'WITH CHECK (business_id = kasta.current_business_id() OR kasta.is_platform_admin())',
            table_name
        );
    END LOOP;
END;
$$;

ALTER TABLE kasta.businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE kasta.businesses FORCE ROW LEVEL SECURITY;
CREATE POLICY business_isolation ON kasta.businesses
    USING (id = kasta.current_business_id() OR kasta.is_platform_admin())
    WITH CHECK (id = kasta.current_business_id() OR kasta.is_platform_admin());

ALTER TABLE kasta.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE kasta.users FORCE ROW LEVEL SECURITY;
CREATE POLICY user_self_or_admin ON kasta.users
    USING (id = kasta.current_user_id() OR kasta.is_platform_admin())
    WITH CHECK (id = kasta.current_user_id() OR kasta.is_platform_admin());

ALTER TABLE kasta.mentors ENABLE ROW LEVEL SECURITY;
ALTER TABLE kasta.mentors FORCE ROW LEVEL SECURITY;
CREATE POLICY mentor_self_or_admin ON kasta.mentors
    USING (user_id = kasta.current_user_id() OR kasta.is_platform_admin())
    WITH CHECK (user_id = kasta.current_user_id() OR kasta.is_platform_admin());

ALTER TABLE kasta.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE kasta.notifications FORCE ROW LEVEL SECURITY;
CREATE POLICY notification_owner ON kasta.notifications
    USING (
        user_id = kasta.current_user_id()
        AND (business_id IS NULL OR business_id = kasta.current_business_id())
        OR kasta.is_platform_admin()
    )
    WITH CHECK (
        user_id = kasta.current_user_id()
        AND (business_id IS NULL OR business_id = kasta.current_business_id())
        OR kasta.is_platform_admin()
    );

ALTER TABLE kasta.device_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE kasta.device_sessions FORCE ROW LEVEL SECURITY;
CREATE POLICY device_session_owner ON kasta.device_sessions
    USING (
        user_id = kasta.current_user_id()
        AND (business_id IS NULL OR business_id = kasta.current_business_id())
        OR kasta.is_platform_admin()
    )
    WITH CHECK (
        user_id = kasta.current_user_id()
        AND (business_id IS NULL OR business_id = kasta.current_business_id())
        OR kasta.is_platform_admin()
    );

ALTER TABLE kasta.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE kasta.audit_logs FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_scope ON kasta.audit_logs
    USING (
        business_id = kasta.current_business_id()
        OR (business_id IS NULL AND actor_user_id = kasta.current_user_id())
        OR kasta.is_platform_admin()
    )
    WITH CHECK (
        business_id = kasta.current_business_id()
        OR (business_id IS NULL AND actor_user_id = kasta.current_user_id())
        OR kasta.is_platform_admin()
    );

COMMENT ON SCHEMA kasta IS 'KASTA modular monolith database schema';
COMMENT ON TABLE kasta.transactions IS
    'User-facing business transactions; every row is tenant-scoped and posted rows are immutable';
COMMENT ON TABLE kasta.journal_entries IS
    'Double-entry journal headers; deferred triggers enforce balanced posted entries';
COMMENT ON TABLE kasta.audit_logs IS
    'Append-only change history; sensitive authentication and raw OCR values are redacted';

COMMIT;


-- A tenant-scoped row can never be moved to another business or assigned a new identifier.
CREATE OR REPLACE FUNCTION kasta.prevent_tenant_move()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id OR NEW.business_id IS DISTINCT FROM OLD.business_id THEN
        RAISE EXCEPTION 'id and business_id are immutable for %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'business_members', 'mentor_business_access', 'accounts', 'payment_methods', 'customers',
        'suppliers', 'products', 'transactions', 'transaction_items', 'journal_entries',
        'journal_lines', 'stock_movements', 'receivables', 'receivable_payments', 'payables',
        'payable_payments', 'receipts', 'receipt_images', 'ocr_results', 'ocr_fields', 'mentor_notes',
        'recommendations', 'mentoring_sessions', 'sync_logs'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_prevent_tenant_move BEFORE UPDATE ON kasta.%I '
            'FOR EACH ROW EXECUTE FUNCTION kasta.prevent_tenant_move()',
            table_name
        );
    END LOOP;
END;
$$;
