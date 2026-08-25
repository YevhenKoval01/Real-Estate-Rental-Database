BEGIN;

-- Supports payment drill-through by agreement and chronological due date.
CREATE INDEX IF NOT EXISTS idx_payments_agreement_due_date
    ON staging.payments (agreement_id, due_date)
    INCLUDE (payment_date, amount, status);

-- Supports location inventory joins used by occupancy and rent-per-square-metre models.
CREATE INDEX IF NOT EXISTS idx_properties_location
    ON staging.properties (location_id, property_id);

-- Supports property-to-agreement joins and agreement-expiration filtering.
CREATE INDEX IF NOT EXISTS idx_agreements_property_end_date
    ON staging.rental_agreements (property_id, end_date)
    INCLUDE (monthly_rent, status);

-- Supports operational searches for active agreements approaching expiration.
CREATE INDEX IF NOT EXISTS idx_agreements_active_end_date
    ON staging.rental_agreements (end_date)
    WHERE status = 'ACTIVE';

COMMIT;
