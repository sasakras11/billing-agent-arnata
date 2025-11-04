"""Logging configuration with structured logging support."""
import logging
import sys
from typing import Any

import structlog
from config import get_settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    
    Uses structlog for structured logging with JSON output in production
    and colored console output in development.
    """
    settings = get_settings()
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Set third-party log levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.is_production:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Colored console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_with_context(
    logger: structlog.stdlib.BoundLogger,
    level: str,
    message: str,
    **context: Any
) -> None:
    """
    Log a message with structured context.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields
    """
    log_func = getattr(logger, level.lower())
    log_func(message, **context)


def bind_context(**context: Any) -> None:
    """
    Bind context variables to all subsequent log messages in this context.
    
    Useful for binding request IDs, user IDs, etc.
    
    Args:
        **context: Context variables to bind
    """
    structlog.contextvars.bind_contextvars(**context)


def unbind_context(*keys: str) -> None:
    """
    Unbind context variables.
    
    Args:
        *keys: Keys to unbind
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


class LoggerAdapter:
    """
    Adapter to use structlog with existing logging.getLogger() calls.
    
    This allows gradual migration from standard logging to structlog.
    """
    
    def __init__(self, name: str):
        """
        Initialize logger adapter.
        
        Args:
            name: Logger name
        """
        self.name = name
        self.logger = get_logger(name)
    
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args: Any, exc_info: bool = False, **kwargs: Any) -> None:
        """Log error message."""
        if exc_info:
            kwargs['exc_info'] = True
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        kwargs['exc_info'] = True
        self.logger.error(msg, *args, **kwargs)


# Convenience function to get adapted logger
def get_adapted_logger(name: str) -> LoggerAdapter:
    """
    Get a logger adapter that works like standard logging.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger adapter instance
    """
    return LoggerAdapter(name)

