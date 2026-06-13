-- migrations/003_credits_floor.sql
-- Prevent credits_cents from going negative at the DB level.
-- Run after 002_auth_sessions_api_keys.sql

ALTER TABLE users
    ADD CONSTRAINT users_credits_non_negative
    CHECK (credits_cents >= 0);
