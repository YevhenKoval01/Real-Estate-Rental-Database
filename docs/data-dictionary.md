# Data dictionary

PostgreSQL `staging` is the durable incremental boundary and dbt schemas contain analytical data. Monetary values use the record currency; generated development data uses PLN.

## Staging and operational tables

Every business table also contains `batch_id`, UTC `source_timestamp`, SHA-256 `record_fingerprint`, and UTC `processed_at` metadata.

| Table | Grain and key | Business columns |
|---|---|---|
| `staging.locations` | One location; `location_id` | `city`, `region`, `country_code` |
| `staging.owners` | One property owner; `owner_id` | `full_name`, `email` |
| `staging.tenants` | One tenant; `tenant_id` | `full_name`, `email` |
| `staging.properties` | One current property; `property_id` | location and owner IDs, type, bedrooms, size, monthly rent, currency |
| `staging.rental_agreements` | One agreement; `agreement_id` | property and tenant IDs, start/end dates, monthly rent, status |
| `staging.payments` | One scheduled payment; `payment_id` | agreement ID, due/payment dates, amount, status |
| `staging.pipeline_runs` | One attempted batch; `batch_id` | timestamps, quality/load counts, status, optional failure message |
| `staging.rejected_records` | One reason per rejected source record and batch | record type, source ID, reason code, explanation, timestamp, raw JSON |

## Gold dimensions and facts

dbt builds these tables in `analytics`. MD5 surrogate keys are deterministic hashes of stable source keys.

| Model | Grain | Important fields |
|---|---|---|
| `dim_date` | One day covered by agreement dates | date key, calendar attributes, month start, weekend flag |
| `dim_location` | One current location | location key/ID, city, region, country |
| `dim_owner` | One current owner | owner key/ID, name, email |
| `dim_tenant` | One current tenant | tenant key/ID, name, email |
| `dim_property` | One current property | property/location/owner keys, attributes, current rent |
| `fact_rental_agreement` | One agreement | agreement/property/location/owner/tenant keys, dates, rent, status, duration |
| `fact_payment` | One payment | payment/agreement/property/location/tenant keys, dates, amount, overdue fields |
| `fact_occupancy` | One occupied property day | occupancy/agreement/property/location/tenant/date keys, `occupied_day` |

`analytics_snapshots.property_history` is the SCD Type 2 history of location, ownership, property attributes, size, and monthly rent. dbt supplies `dbt_valid_from`, `dbt_valid_to`, `dbt_scd_id`, and update metadata.

## Analytical marts

| Model | Grain and purpose |
|---|---|
| `mart_occupancy` | Location and calendar month; occupied/available property-days and occupancy rate |
| `mart_monthly_rental_revenue` | Location and payment month; paid count and revenue |
| `mart_overdue_payments` | One overdue payment with property/location context |
| `mart_average_rent_per_sqm` | Location; inventory and average current rent per square metre |
| `mart_agreements_expiring_soon` | Agreement ending from today through 30 days ahead |
| `mart_rental_trends_by_location` | Location and agreement-start month; average rent and month-over-month change |
