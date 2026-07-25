# Real Estate Rental Database

A third-semester relational database project for a small real estate rental system. It models people and their roles, properties, houses, and rental agreements. The same logical model is provided for Microsoft SQL Server and Oracle Database.

## Project scope

The database stores:

- people who may be owners, tenants, or real estate agents;
- properties assigned to their owners;
- houses with size, floor count, garage, maintenance cost, and market value;
- rental agreements connecting a house, tenant, and optional agent;
- sample records and thirteen example analytical queries.

Optional scripts demonstrate stored procedures and triggers. They are separated from the basic schema so the main project remains easy to understand.

## Technologies

- SQL
- Microsoft SQL Server / SQL Server Management Studio
- Oracle Database / Oracle SQL Developer
- Vertabelo for the entity-relationship diagrams

## Repository structure

```text
Baza-danych-projekt-1/
|-- docs/
|   |-- diagrams/
|   |   |-- oracle-erd.png
|   |   `-- sql-server-erd.png
|   `-- requirements-pl.pdf
|-- sql/
|   |-- oracle/
|   |   |-- 01-schema-seed-and-queries.sql
|   |   `-- 02-procedures-and-triggers.sql
|   `-- sql-server/
|       |-- 01-schema-seed-and-queries.sql
|       `-- 02-procedures-and-triggers.sql
`-- README.md
```

## Data model

The central `Osoba` table stores shared personal data. Role tables (`Wlasciciel`, `Najemca`, and `Agent_nieruchomosci`) extend a person through one-to-one foreign keys. An owner may have multiple `Przestrzen` records, each space may contain houses, and every `Umowa_o_wynajem` links a house to a tenant and optionally an agent.

![SQL Server entity-relationship diagram](docs/diagrams/sql-server-erd.png)

## Running with SQL Server

1. Create or select a development database in SQL Server Management Studio.
2. Open `sql/sql-server/01-schema-seed-and-queries.sql`.
3. Execute the complete file to reset the demo tables, recreate the schema, insert sample data, and run the example queries.
4. Optionally execute `sql/sql-server/02-procedures-and-triggers.sql`.

The first SQL Server script removes only the seven demo tables before recreating them. Use a dedicated development database.

## Running with Oracle

1. Create or select an empty development schema in Oracle SQL Developer.
2. Run `sql/oracle/01-schema-seed-and-queries.sql` as a script.
3. Optionally run `sql/oracle/02-procedures-and-triggers.sql`.
4. Enable DBMS Output to see messages produced by the optional routines.

## Example topics

The query set covers joins, grouping, aggregate functions, correlated subqueries, and comparisons against averages and maximum values. The optional extensions add validation and automatic price updates with procedures and triggers.

## Project status

Complete educational project. It intentionally keeps a compact scope suitable for an introductory database course while showing the same model in two SQL dialects.
