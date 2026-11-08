import logging
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers preventing stack trace leakage."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
        errors = exc.errors()
        first_err = errors[0] if errors else {}
        loc = " -> ".join(str(l) for l in first_err.get("loc", []))
        msg = first_err.get("msg", "Invalid request body or parameters.")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Validation failed: {msg}",
                    "field": loc if loc else None,
                },
                "request_id": request_id,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            413: "PAYLOAD_TOO_LARGE",
            422: "UNPROCESSABLE_ENTITY",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        code_str = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": code_str,
                    "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                    "field": None,
                },
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
        # Log full traceback internally for operations
        logger.exception("Unhandled server exception during request %s: %s", request_id, exc)

        # Never expose stack traces or internal filesystem paths to the client
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred. Please contact support with the request ID.",
                    "field": None,
                },
                "request_id": request_id,
            },
        )
