BEGIN;

ALTER TABLE staging.locations
    ADD COLUMN IF NOT EXISTS batch_id text NOT NULL DEFAULT 'legacy-stage1',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz NOT NULL DEFAULT '2024-01-01 00:00:00+00',
    ADD COLUMN IF NOT EXISTS record_fingerprint char(64) NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS processed_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE staging.owners
    ADD COLUMN IF NOT EXISTS batch_id text NOT NULL DEFAULT 'legacy-stage1',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz NOT NULL DEFAULT '2024-01-01 00:00:00+00',
    ADD COLUMN IF NOT EXISTS record_fingerprint char(64) NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS processed_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE staging.tenants
    ADD COLUMN IF NOT EXISTS batch_id text NOT NULL DEFAULT 'legacy-stage1',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz NOT NULL DEFAULT '2024-01-01 00:00:00+00',
    ADD COLUMN IF NOT EXISTS record_fingerprint char(64) NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS processed_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE staging.properties
    ADD COLUMN IF NOT EXISTS batch_id text NOT NULL DEFAULT 'legacy-stage1',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz NOT NULL DEFAULT '2024-01-01 00:00:00+00',
    ADD COLUMN IF NOT EXISTS record_fingerprint char(64) NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS processed_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE staging.rental_agreements
    ADD COLUMN IF NOT EXISTS batch_id text NOT NULL DEFAULT 'legacy-stage1',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz NOT NULL DEFAULT '2024-01-01 00:00:00+00',
    ADD COLUMN IF NOT EXISTS record_fingerprint char(64) NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS processed_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE staging.payments
    ADD COLUMN IF NOT EXISTS batch_id text NOT NULL DEFAULT 'legacy-stage1',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz NOT NULL DEFAULT '2024-01-01 00:00:00+00',
    ADD COLUMN IF NOT EXISTS record_fingerprint char(64) NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS processed_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS staging.pipeline_runs (
    batch_id text PRIMARY KEY,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    input_count integer NOT NULL DEFAULT 0 CHECK (input_count >= 0),
    accepted_count integer NOT NULL DEFAULT 0 CHECK (accepted_count >= 0),
    rejected_count integer NOT NULL DEFAULT 0 CHECK (rejected_count >= 0),
    inserted_count integer NOT NULL DEFAULT 0 CHECK (inserted_count >= 0),
    updated_count integer NOT NULL DEFAULT 0 CHECK (updated_count >= 0),
    skipped_count integer NOT NULL DEFAULT 0 CHECK (skipped_count >= 0),
    final_status text NOT NULL CHECK (final_status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    failure_message text
);

CREATE TABLE IF NOT EXISTS staging.rejected_records (
    rejection_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_type text NOT NULL,
    source_identifier text NOT NULL,
    batch_id text NOT NULL REFERENCES staging.pipeline_runs (batch_id),
    reason_code text NOT NULL,
    explanation text NOT NULL,
    processed_at timestamptz NOT NULL,
    raw_record jsonb NOT NULL,
    CONSTRAINT rejected_record_once_per_batch
        UNIQUE (batch_id, record_type, source_identifier, reason_code)
);

COMMIT;
