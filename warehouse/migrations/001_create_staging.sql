BEGIN;

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.locations (
    location_id text PRIMARY KEY,
    city text NOT NULL,
    region text NOT NULL,
    country_code char(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.owners (
    owner_id text PRIMARY KEY,
    full_name text NOT NULL,
    email text NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.tenants (
    tenant_id text PRIMARY KEY,
    full_name text NOT NULL,
    email text NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.properties (
    property_id text PRIMARY KEY,
    location_id text NOT NULL REFERENCES staging.locations (location_id),
    owner_id text NOT NULL REFERENCES staging.owners (owner_id),
    property_type text NOT NULL,
    bedrooms integer NOT NULL CHECK (bedrooms >= 0),
    size_sqm numeric(10, 2) NOT NULL CHECK (size_sqm > 0),
    monthly_rent numeric(12, 2) NOT NULL CHECK (monthly_rent >= 0),
    currency char(3) NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.rental_agreements (
    agreement_id text PRIMARY KEY,
    property_id text NOT NULL REFERENCES staging.properties (property_id),
    tenant_id text NOT NULL REFERENCES staging.tenants (tenant_id),
    start_date date NOT NULL,
    end_date date NOT NULL,
    monthly_rent numeric(12, 2) NOT NULL CHECK (monthly_rent >= 0),
    status text NOT NULL,
    CONSTRAINT rental_agreement_date_order CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS staging.payments (
    payment_id text PRIMARY KEY,
    agreement_id text NOT NULL REFERENCES staging.rental_agreements (agreement_id),
    due_date date NOT NULL,
    payment_date date NOT NULL,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    status text NOT NULL
);

COMMIT;
