-- migrations/004_drop_api_key_fingerprint.sql
-- The api_key_fingerprint column on users is legacy from the original design.
-- API keys now live in the api_keys table with their own key_hash column.
-- This column being NOT NULL blocks all user registration.

ALTER TABLE users DROP COLUMN IF EXISTS api_key_fingerprint;
