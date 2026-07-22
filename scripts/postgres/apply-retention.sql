\set ON_ERROR_STOP on

\if :{?security_days}
\else
\set security_days 90
\endif

BEGIN;

DELETE FROM auth_one_time_tokens
WHERE COALESCE(consumed_at, expires_at) < now() - make_interval(days => :security_days);

DELETE FROM auth_delivery_outbox
WHERE sent_at IS NOT NULL
  AND sent_at < now() - make_interval(days => :security_days);

DELETE FROM device_sessions
WHERE COALESCE(revoked_at, expires_at) < now() - make_interval(days => :security_days);

DELETE FROM login_rate_limits
WHERE COALESCE(blocked_until, window_started_at) < now() - make_interval(days => :security_days);

COMMIT;
