param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

docker compose config --quiet
& $Python -m ruff check .
& $Python -m ruff format --check .
& $Python -m compileall -q src
& $Python -m build
& $Python -m pytest -m "not integration"

docker compose up --detach --wait postgres
docker compose --profile pipeline run --build --rm pipeline

$env:RENTAL_TEST_POSTGRES_DSN = "postgresql://rental:rental_dev@localhost:5432/rental_analytics"
& $Python -m pytest tests/integration
docker compose ps
