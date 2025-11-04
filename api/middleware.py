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
    """
    Middleware to log all API requests and responses.
    
    Adds request ID to all logs and tracks request duration.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler
            
        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Bind request context for structured logging
        bind_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
        )
        
        # Track timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            
            raise
            
        finally:
            # Clean up context
            clear_context()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle exceptions and return appropriate error responses.
    
    Converts exceptions to JSON responses with proper status codes.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and handle errors.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler
            
        Returns:
            HTTP response
        """
        try:
            return await call_next(request)
            
        except BillingAgentException as e:
            # Our custom exceptions - return as 400 Bad Request
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
            # Validation errors - return as 400 Bad Request
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
            # Unexpected errors - return as 500 Internal Server Error
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
    """
    Middleware to add CORS headers to responses.
    
    Allows cross-origin requests from configured origins.
    """
    
    def __init__(self, app, allowed_origins: list[str] | None = None):
        """
        Initialize CORS middleware.
        
        Args:
            app: FastAPI application
            allowed_origins: List of allowed origins (default: all)
        """
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Add CORS headers to response.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler
            
        Returns:
            HTTP response with CORS headers
        """
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
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
    """
    Add all middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware in reverse order (last added is executed first)
    
    # Error handling (outermost - catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # CORS headers (if needed)
    # app.add_middleware(CORSHeadersMiddleware, allowed_origins=["*"])
    
    logger.info("Middleware configured")

