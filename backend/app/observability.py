"""Dependency-free structured logging and process metrics."""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime

from fastapi import Request


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("http_method", "http_path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


request_counts: Counter[tuple[str, int]] = Counter()
request_duration_seconds = 0.0


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


async def observe_request(request: Request, call_next):
    global request_duration_seconds
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    request_counts[(request.method, response.status_code)] += 1
    request_duration_seconds += elapsed
    logging.getLogger("eduged.http").info(
        "request_completed",
        extra={
            "http_method": request.method,
            "http_path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(elapsed * 1000, 2),
        },
    )
    return response


def prometheus_metrics() -> str:
    lines = [
        "# HELP eduged_http_requests_total Total HTTP requests by method and status.",
        "# TYPE eduged_http_requests_total counter",
    ]
    for (method, status), count in sorted(request_counts.items()):
        lines.append(
            f'eduged_http_requests_total{{method="{method}",status="{status}"}} {count}'
        )
    lines.extend(
        [
            "# HELP eduged_http_request_duration_seconds_total Total request duration.",
            "# TYPE eduged_http_request_duration_seconds_total counter",
            f"eduged_http_request_duration_seconds_total {request_duration_seconds}",
        ]
    )
    return "\n".join(lines) + "\n"
