-- ==============================================================================
-- KidSync AI - Phase 1 Initial PostgreSQL Schema
-- Tables: users, caregivers, caregiver_assignments, bookings, audit_log_entries
-- Target: PostgreSQL 15+ / 16
-- ==============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Clean up any existing objects if re-running
DROP TABLE IF EXISTS audit_log_entries CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS caregiver_assignments CASCADE;
DROP TABLE IF EXISTS caregivers CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ------------------------------------------------------------------------------
-- 1. USERS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,
    phone VARCHAR(30),
    avatar_url TEXT,
    role VARCHAR(30) NOT NULL DEFAULT 'PRIMARY_GUARDIAN', -- PRIMARY_GUARDIAN, EXTENDED_GUARDIAN, CARE_PROVIDER, OBSERVER, ADMIN
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ------------------------------------------------------------------------------
-- 2. CAREGIVERS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE caregivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    years_of_experience INTEGER NOT NULL DEFAULT 0,
    hourly_rate_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    specialties TEXT[] DEFAULT ARRAY[]::TEXT[], -- e.g., 'INFANT_CARE', 'SPECIAL_NEEDS', 'FIRST_AID', 'HOMEWORK_TUTOR'
    certifications JSONB NOT NULL DEFAULT '[]'::jsonb, -- e.g., [{"name": "CPR", "issuer": "Red Cross", "expires": "2027-01-01"}]
    background_check_status VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- PENDING, PASSED, FAILED, EXPIRED
    background_checked_at TIMESTAMPTZ,
    emergency_phone VARCHAR(30),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    rating_average NUMERIC(3, 2) NOT NULL DEFAULT 5.00,
    total_reviews_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_caregivers_user_id ON caregivers(user_id);
CREATE INDEX idx_caregivers_background_status ON caregivers(background_check_status);
CREATE INDEX idx_caregivers_is_available ON caregivers(is_available);

-- ------------------------------------------------------------------------------
-- 3. CAREGIVER ASSIGNMENTS / RBAC TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE caregiver_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caregiver_id UUID NOT NULL REFERENCES caregivers(id) ON DELETE CASCADE,
    assigned_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_type VARCHAR(30) NOT NULL DEFAULT 'CARE_PROVIDER', -- PRIMARY_GUARDIAN, EXTENDED_GUARDIAN, CARE_PROVIDER, OBSERVER
    can_view_health BOOLEAN NOT NULL DEFAULT TRUE,
    can_view_schedule BOOLEAN NOT NULL DEFAULT TRUE,
    can_view_financials BOOLEAN NOT NULL DEFAULT FALSE,
    can_administer_meds BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(caregiver_id, assigned_by_user_id)
);

CREATE INDEX idx_caregiver_assignments_caregiver_id ON caregiver_assignments(caregiver_id);
CREATE INDEX idx_caregiver_assignments_assigned_by ON caregiver_assignments(assigned_by_user_id);

-- ------------------------------------------------------------------------------
-- 4. BOOKINGS TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caregiver_id UUID NOT NULL REFERENCES caregivers(id) ON DELETE RESTRICT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- PENDING, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED, REJECTED
    total_amount_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    special_instructions TEXT,
    emergency_contact_override JSONB,
    handoff_digest_id UUID,
    cancellation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_booking_time_range CHECK (end_time > start_time)
);

CREATE INDEX idx_bookings_client_user_id ON bookings(client_user_id);
CREATE INDEX idx_bookings_caregiver_id ON bookings(caregiver_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_time_range ON bookings(start_time, end_time);

-- ------------------------------------------------------------------------------
-- 5. AUDIT LOG ENTRIES (COURT-ADMISSIBLE CRYPTOGRAPHIC LEDGER)
-- ------------------------------------------------------------------------------
CREATE TABLE audit_log_entries (
    id BIGSERIAL PRIMARY KEY,
    entity_id UUID NOT NULL,
    target_entity VARCHAR(60) NOT NULL, -- 'users', 'caregivers', 'bookings', 'medications'
    event_type VARCHAR(60) NOT NULL,    -- 'USER_CREATED', 'BOOKING_REQUESTED', 'BOOKING_CONFIRMED', etc.
    actor_id UUID NOT NULL,
    payload_snapshot JSONB NOT NULL,
    client_ip_hash VARCHAR(64) NOT NULL,
    prev_entry_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON audit_log_entries(target_entity, entity_id);
CREATE INDEX idx_audit_log_actor_id ON audit_log_entries(actor_id);
CREATE INDEX idx_audit_log_created_at ON audit_log_entries(created_at);
CREATE INDEX idx_audit_log_entry_hash ON audit_log_entries(entry_hash);

-- ------------------------------------------------------------------------------
-- AUTO-UPDATE TRIGGER FUNCTION FOR updated_at
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_users
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_caregivers
BEFORE UPDATE ON caregivers
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_caregiver_assignments
BEFORE UPDATE ON caregiver_assignments
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_bookings
BEFORE UPDATE ON bookings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
