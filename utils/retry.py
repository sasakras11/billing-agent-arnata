"""Retry utilities for handling transient failures."""
import time
import functools
from typing import Callable, Type, Tuple, Any, Optional
import random

from logging_config import get_logger
from constants import MAX_RETRY_ATTEMPTS, RETRY_BACKOFF_FACTOR, RETRY_INITIAL_DELAY

logger = get_logger(__name__)


def exponential_backoff(
    attempt: int,
    base_delay: float = RETRY_INITIAL_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Calculate exponential backoff delay.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to prevent thundering herd
        
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
    
    if jitter:
        # Add random jitter (±25%)
        jitter_amount = delay * 0.25
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
    
    return max(0, delay)


def retry_with_backoff(
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = RETRY_INITIAL_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function
        
    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def fetch_data():
            return api.get("/data")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts", error=str(e), exc_info=True)
                        raise
                    
                    delay = exponential_backoff(attempt, base_delay=base_delay, backoff_factor=backoff_factor)
                    logger.warning(f"Function {func.__name__} failed, retrying", attempt=attempt + 1, max_attempts=max_attempts, delay_seconds=round(delay, 2), error=str(e))
                    
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error("Retry callback failed", error=str(callback_error))
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_async_with_backoff(
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = RETRY_INITIAL_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator to retry an async function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated async function
        
    Example:
        @retry_async_with_backoff(max_attempts=3)
        async def fetch_data():
            return await api.get("/data")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import asyncio
            
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Async function {func.__name__} failed after {max_attempts} attempts", error=str(e), exc_info=True)
                        raise
                    
                    delay = exponential_backoff(attempt, base_delay=base_delay, backoff_factor=backoff_factor)
                    logger.warning(f"Async function {func.__name__} failed, retrying", attempt=attempt + 1, max_attempts=max_attempts, delay_seconds=round(delay, 2), error=str(e))
                    
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error("Retry callback failed", error=str(callback_error))
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic with custom handling.
    
    Example:
        retry_ctx = RetryContext(max_attempts=3)
        
        for attempt in retry_ctx:
            try:
                result = api_call()
                retry_ctx.success()
                break
            except ConnectionError as e:
                if not retry_ctx.should_retry(e):
                    raise
    """
    
    def __init__(
        self,
        max_attempts: int = MAX_RETRY_ATTEMPTS,
        base_delay: float = RETRY_INITIAL_DELAY,
        backoff_factor: float = RETRY_BACKOFF_FACTOR,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry context.
        
        Args:
            max_attempts: Maximum number of attempts
            base_delay: Initial delay between retries
            backoff_factor: Multiplier for delay on each retry
            exceptions: Tuple of exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.current_attempt = 0
        self._success = False
    
    def __iter__(self):
        """Iterate through retry attempts."""
        self.current_attempt = 0
        return self
    
    def __next__(self):
        """Get next retry attempt."""
        if self._success or self.current_attempt >= self.max_attempts:
            raise StopIteration
        
        attempt = self.current_attempt
        self.current_attempt += 1
        return attempt
    
    def success(self):
        """Mark operation as successful."""
        self._success = True
    
    def should_retry(self, exception: Exception) -> bool:
        """
        Check if should retry after exception.
        
        Args:
            exception: Exception that occurred
            
        Returns:
            True if should retry
        """
        if self._success:
            return False
        
        if self.current_attempt >= self.max_attempts:
            return False
        
        if not isinstance(exception, self.exceptions):
            return False
        
        # Calculate and wait for backoff delay
        if self.current_attempt > 0:
            delay = exponential_backoff(
                self.current_attempt - 1,
                base_delay=self.base_delay,
                backoff_factor=self.backoff_factor
            )
            
            logger.info(
                "Retrying after delay",
                attempt=self.current_attempt,
                max_attempts=self.max_attempts,
                delay_seconds=round(delay, 2)
            )
            
            time.sleep(delay)
        
        return True

