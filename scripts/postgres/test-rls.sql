-- PostgreSQL RLS smoke test for KASTA.
--
-- Run this file as the database owner (the `kasta` role in Compose), never as
-- the application role.  The fixture is inserted in a transaction and rolled
-- back at the end, so this script is safe to run against a non-production
-- database containing seed data.  The application role must already exist and
-- have only the privileges needed by the API (see deployment documentation).
--
-- Example:
--   docker exec -i kasta-platform-postgres-1 \
--     psql -v ON_ERROR_STOP=1 -U kasta -d kasta < scripts/postgres/test-rls.sql

\set ON_ERROR_STOP on

BEGIN;

-- A runtime role must not bypass RLS.  This also catches an accidentally
-- missing role/GRANT setup before the checks below produce misleading results.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kasta_app') THEN
        RAISE EXCEPTION 'RLS test requires role kasta_app to exist';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
         WHERE rolname = 'kasta_app' AND (rolsuper OR rolbypassrls)
    ) THEN
        RAISE EXCEPTION 'kasta_app must be NOSUPERUSER and NOBYPASSRLS';
    END IF;
    IF NOT has_table_privilege('kasta_app', 'public.accounts', 'SELECT') THEN
        RAISE EXCEPTION 'kasta_app is missing SELECT privilege on public.accounts';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM roles WHERE code = 'business_owner') THEN
        RAISE EXCEPTION 'RLS test requires seeded role business_owner';
    END IF;
END
$$;

-- Verify the policies are enabled on representative tenant tables.
DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['accounts', 'transactions', 'audit_logs'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_class c
             JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = table_name
              AND c.relrowsecurity
        ) THEN
            RAISE EXCEPTION 'RLS is not enabled on %', table_name;
        END IF;
    END LOOP;
END
$$;

-- Deterministic fixture.  UUIDs are deliberately outside normal seed values;
-- the whole transaction is rolled back, so no cleanup is required.
INSERT INTO organizations (id, name, status)
VALUES ('00000000-0000-0000-0000-0000000000a1', 'QA RLS Organization', 'ACTIVE');

INSERT INTO users (id, email, password_hash, full_name, status, email_verified_at)
VALUES
    ('00000000-0000-0000-0000-0000000000a1', 'qa-rls-owner@example.invalid', 'qa-only', 'QA RLS Owner', 'ACTIVE', now()),
    ('00000000-0000-0000-0000-0000000000a2', 'qa-rls-mentor@example.invalid', 'qa-only', 'QA RLS Mentor', 'ACTIVE', now()),
    ('00000000-0000-0000-0000-0000000000a3', 'qa-rls-support@example.invalid', 'qa-only', 'QA RLS Support', 'ACTIVE', now());

INSERT INTO businesses (id, organization_id, code, name, status)
VALUES
    ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000a1', 'QA-RLS-A', 'QA RLS Business A', 'ACTIVE'),
    ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000a1', 'QA-RLS-B', 'QA RLS Business B', 'ACTIVE');

INSERT INTO business_members (id, business_id, user_id, role_id, status, joined_at)
SELECT '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000a1', id, 'ACTIVE', now()
  FROM roles WHERE code = 'business_owner';

INSERT INTO mentors (id, user_id, status)
VALUES ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000a2', 'ACTIVE');

INSERT INTO mentor_business_access (
    id, business_id, mentor_id, role_id, requested_by_user_id, granted_by_user_id,
    scope, status, requested_at, granted_at, revision_no
)
VALUES (
    '00000000-0000-0000-0000-0000000000a1',
    '00000000-0000-0000-0000-0000000000a1',
    '00000000-0000-0000-0000-0000000000a1',
    (SELECT id FROM roles WHERE code = 'mentor'),
    '00000000-0000-0000-0000-0000000000a2',
    '00000000-0000-0000-0000-0000000000a1',
    '["REPORTS"]'::jsonb, 'ACTIVE', now(), now(), 1
);

INSERT INTO accounts (
    id, business_id, code, name, account_type, normal_balance, is_system, is_active
)
VALUES
    ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000a1', 'QA-CASH', 'QA Cash A', 'ASSET', 'DEBIT', false, true),
    ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000a2', 'QA-CASH', 'QA Cash B', 'ASSET', 'DEBIT', false, true);

INSERT INTO support_access_grants (
    id, business_id, admin_user_id, granted_by_user_id, scope, reason,
    ticket_reference, status, granted_at, expires_at
)
VALUES (
    '00000000-0000-0000-0000-0000000000a3',
    '00000000-0000-0000-0000-0000000000a1',
    '00000000-0000-0000-0000-0000000000a3',
    '00000000-0000-0000-0000-0000000000a1',
    '["REPORTS"]'::jsonb, 'RLS smoke test', 'QA-RLS-SUPPORT-001', 'ACTIVE', now(), now() + interval '1 hour'
);

INSERT INTO audit_logs (
    id, business_id, actor_user_id, action, entity_type, entity_id, created_at
)
VALUES (
    '00000000-0000-0000-0000-0000000000a3',
    '00000000-0000-0000-0000-0000000000a1',
    '00000000-0000-0000-0000-0000000000a1',
    'RLS_TEST', 'BUSINESS', '00000000-0000-0000-0000-0000000000a1', now()
);

-- `SET ROLE` makes PostgreSQL evaluate policies as the same non-privileged role
-- used by the API.  Context values are transaction-local and cannot leak.
SET ROLE kasta_app;

SELECT set_config('app.actor_type', 'BUSINESS', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000a1', true);
SELECT set_config('app.business_id', '00000000-0000-0000-0000-0000000000a1', true);
SELECT set_config('app.mentor_id', '', true);

DO $$
DECLARE
    visible_a integer;
    visible_b integer;
BEGIN
    SELECT count(*) INTO visible_a FROM accounts WHERE business_id = '00000000-0000-0000-0000-0000000000a1';
    SELECT count(*) INTO visible_b FROM accounts WHERE business_id = '00000000-0000-0000-0000-0000000000a2';
    IF visible_a <> 1 OR visible_b <> 0 THEN
        RAISE EXCEPTION 'business tenant isolation failed (A=%, B=%)', visible_a, visible_b;
    END IF;
END
$$;

DO $$
BEGIN
    BEGIN
        INSERT INTO accounts (id, business_id, code, name, account_type, normal_balance, is_system, is_active)
        VALUES ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000a2', 'QA-BLOCKED', 'Blocked', 'ASSET', 'DEBIT', false, true);
        RAISE EXCEPTION 'cross-tenant INSERT unexpectedly succeeded';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL; -- expected RLS rejection (SQLSTATE 42501)
    END;
END
$$;

DO $$
DECLARE
    updated_count integer;
BEGIN
    BEGIN
        UPDATE audit_logs SET action = 'MUTATED'
         WHERE id = '00000000-0000-0000-0000-0000000000a3';
        GET DIAGNOSTICS updated_count = ROW_COUNT;
        IF updated_count <> 0 THEN
            RAISE EXCEPTION 'audit log update unexpectedly succeeded';
        END IF;
    EXCEPTION WHEN insufficient_privilege THEN
        NULL; -- append-only policy/trigger is expected
    END;
END
$$;

SELECT set_config('app.actor_type', 'MENTOR', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000a2', true);
SELECT set_config('app.business_id', '', true);
SELECT set_config('app.mentor_id', '00000000-0000-0000-0000-0000000000a1', true);

DO $$
DECLARE
    visible_a integer;
    visible_b integer;
BEGIN
    SELECT count(*) INTO visible_a FROM accounts WHERE business_id = '00000000-0000-0000-0000-0000000000a1';
    SELECT count(*) INTO visible_b FROM accounts WHERE business_id = '00000000-0000-0000-0000-0000000000a2';
    IF visible_a <> 1 OR visible_b <> 0 THEN
        RAISE EXCEPTION 'mentor scope isolation failed (A=%, B=%)', visible_a, visible_b;
    END IF;
END
$$;

-- Expiration is evaluated by the policy at query time, not by a background job.
RESET ROLE;
UPDATE mentor_business_access
   SET status = 'EXPIRED',
       granted_at = now() - interval '2 minutes',
       expires_at = now() - interval '1 minute'
 WHERE id = '00000000-0000-0000-0000-0000000000a1';
SET ROLE kasta_app;
SELECT set_config('app.actor_type', 'MENTOR', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000a2', true);
SELECT set_config('app.business_id', '', true);
SELECT set_config('app.mentor_id', '00000000-0000-0000-0000-0000000000a1', true);

DO $$
BEGIN
    IF (SELECT count(*) FROM accounts) <> 0 THEN
        RAISE EXCEPTION 'expired mentor grant still exposes tenant data';
    END IF;
END
$$;

-- A support user is limited to an explicit, time-bound grant and scope.
RESET ROLE;
SET ROLE kasta_app;
SELECT set_config('app.actor_type', 'SUPPORT', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000a3', true);
SELECT set_config('app.business_id', '', true);
SELECT set_config('app.mentor_id', '', true);
SELECT set_config('app.support_grant_id', '00000000-0000-0000-0000-0000000000a3', true);

DO $$
BEGIN
    IF (SELECT count(*) FROM accounts) <> 1
       OR EXISTS (SELECT 1 FROM accounts WHERE business_id = '00000000-0000-0000-0000-0000000000a2') THEN
        RAISE EXCEPTION 'support grant scope/tenant isolation failed';
    END IF;
END
$$;

-- The fixture was only for this run.  ROLLBACK is intentional.
ROLLBACK;

\echo 'RLS smoke tests passed; fixture transaction rolled back.'
