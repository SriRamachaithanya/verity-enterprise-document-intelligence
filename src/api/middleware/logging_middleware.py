import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("verity.api")

SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting unique request correlation IDs, measuring execution latency,
    and outputting structured logs with sensitive header redaction.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Correlation ID from client or auto-generated
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        start_time = time.perf_counter()

        # Log sanitized incoming request
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            "HTTP %s %s [%s] from %s",
            request.method,
            request.url.path,
            request_id,
            client_ip,
        )

        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach correlation ID and execution time headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-MS"] = f"{elapsed_ms:.2f}"

            logger.info(
                "HTTP %s %s completed %d in %.2fms [%s]",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                request_id,
            )
            return response

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "HTTP %s %s failed with exception in %.2fms [%s]: %s",
                request.method,
                request.url.path,
                elapsed_ms,
                request_id,
                exc,
            )
            raise
