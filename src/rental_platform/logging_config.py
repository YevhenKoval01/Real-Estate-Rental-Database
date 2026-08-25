import json
import logging
from datetime import UTC, datetime

OPERATIONAL_FIELDS = (
    "event",
    "batch_id",
    "stage",
    "entity",
    "input_count",
    "accepted_count",
    "rejected_count",
    "inserted_count",
    "updated_count",
    "skipped_count",
    "duration_ms",
)


class JsonFormatter(logging.Formatter):
    """Small JSON formatter suitable for local and container logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in OPERATIONAL_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    logging.getLogger("py4j").setLevel(logging.WARNING)
