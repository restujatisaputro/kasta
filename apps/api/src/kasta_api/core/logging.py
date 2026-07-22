import json
import logging
from datetime import UTC, datetime
from logging.config import dictConfig
from typing import Any

from kasta_api.core.context import request_id_context


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class JsonFormatter(logging.Formatter):
    _extra_fields = (
        "duration_ms",
        "method",
        "path",
        "status_code",
        "security_event",
        "user_id",
        "business_id",
        "session_id",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for field in self._extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str, log_format: str = "json") -> None:
    formatter: dict[str, Any]
    if log_format == "json":
        formatter = {"()": JsonFormatter}
    else:
        formatter = {
            "format": ("%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s")
        }

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_context": {"()": RequestContextFilter}},
            "formatters": {"default": formatter},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "filters": ["request_context"],
                    "formatter": "default",
                }
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )
    logging.captureWarnings(True)
