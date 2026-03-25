"""FastAPI middleware for logging and error handling."""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from logging_config import get_logger, bind_context, clear_context
from exceptions import BillingAgentException

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests/responses with request ID and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        bind_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
        )
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise
        finally:
            clear_context()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Convert exceptions to JSON responses with proper status codes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except BillingAgentException as e:
            logger.warning(
                "Business logic error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": type(e).__name__,
                    "message": str(e),
                    "detail": None,
                }
            )
        except ValueError as e:
            logger.warning(
                "Validation error",
                error=str(e),
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "ValidationError",
                    "message": str(e),
                    "detail": None,
                }
            )
        except Exception as e:
            logger.error(
                "Unhandled exception",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred. Please contact support.",
                    "detail": None,
                }
            )


class CORSHeadersMiddleware(BaseHTTPMiddleware):
    """Add CORS headers to responses for configured origins."""

    def __init__(self, app, allowed_origins: list[str] | None = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and (
            "*" in self.allowed_origins or origin in self.allowed_origins
        ):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-API-Key"
        return response


def setup_middleware(app) -> None:
    """Register all middleware on the FastAPI app."""
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Middleware configured")
