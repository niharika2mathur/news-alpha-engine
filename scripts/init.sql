-- scripts/init.sql – PostgreSQL initialization
-- Run automatically by Docker on first startup

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Performance settings for bulk inserts
ALTER SYSTEM SET synchronous_commit = 'off';
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

SELECT pg_reload_conf();
