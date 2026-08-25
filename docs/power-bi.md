# Power BI semantic model

## Delivered and verified

`bi/Rental Analytics.SemanticModel` is a source-controlled TMDL semantic-model definition. It imports six tested PostgreSQL Gold/mart queries and defines six explicit DAX measures:

| Measure | Definition intent |
|---|---|
| Occupancy Rate | occupied property-days divided by available property-days |
| Monthly Rental Revenue | sum of paid rental revenue in the current filter context |
| Average Rent per Square Metre | property-count-weighted location averages |
| Overdue Payment Rate | overdue fact rows divided by all payment fact rows |
| Agreements Expiring within 30 Days | rows in the warehouse's rolling 30-day expiration mart |
| Rental Price Trend by Location | latest visible average agreement rent minus the preceding visible month |

`rental-platform validate-bi` verifies the PBISM version, required TMDL files, V3 data-source metadata, import partitions, parameterized connection, source relations, exact measure contract, balanced DAX delimiters, and absence of embedded credentials. The automated validator passed with six tables, six measures, and six primary sources.

Power BI Desktop is not installed in the verification environment. Therefore no `.pbix`, report pages, refresh claim, or dashboard screenshot is included. The validator is structural and does not replace the Desktop DAX/M engine.

## Import and refresh in Power BI Desktop

1. Start PostgreSQL, run the pipeline, and run dbt using the root README quickstart.
2. Install a current Power BI Desktop version with PBIP/TMDL support and the PostgreSQL connector.
3. In **File → Options and settings → Options → Preview features**, enable **Store semantic model using TMDL format**, then restart Desktop if requested.
4. Create a blank report and save it as a Power BI Project named `Rental Analytics` in a temporary folder. Close Desktop.
5. Replace the generated `Rental Analytics.SemanticModel/definition` directory and `definition.pbism` file with the corresponding files from `bi/Rental Analytics.SemanticModel`.
6. Reopen the generated `Rental Analytics.pbip` file. In **Transform data → Manage parameters**, set `DatabaseServer` to `localhost` and `DatabaseName` to `rental_analytics`.
7. Refresh and supply the local PostgreSQL development account from `.env` when Desktop requests credentials. Do not store production credentials in the project.
8. Build visuals from the six measures and the city/month fields. A useful first page contains KPI cards for five headline measures, a monthly revenue line, occupancy by city, the overdue-payment detail table, and rent trend by location.
9. Save the report as PBIP. Review generated report files before adding them to source control.

If Desktop reports TMDL errors, run `rental-platform validate-bi` first, confirm the preview feature is enabled, and verify that the copied folder name exactly matches the report's `definition.pbir` `byPath` reference.
