"""
Logging Configuration Module

Centralized logging setup for the TURFMAPP AI Agent application.
Provides structured logging with proper formatting and handlers.

Usage:
    from app.core.logging_config import setup_logging, get_logger
    
    # In main.py
    setup_logging()
    
    # In any module
    logger = get_logger(__name__)
    logger.info("Application started")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for other handlers
        record.levelname = levelname
        
        return result


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    enable_colors: bool = True
) -> None:
    """
    Set up application-wide logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (defaults to app_{timestamp}.log)
        log_dir: Directory for log files
        enable_colors: Enable colored console output
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Generate log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = f"app_{timestamp}.log"
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatters
    console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    if enable_colors:
        console_formatter = ColoredFormatter(console_format, datefmt=date_format)
    else:
        console_formatter = logging.Formatter(console_format, datefmt=date_format)
    
    file_formatter = logging.Formatter(file_format, datefmt=date_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    
    # File handler
    file_handler = logging.FileHandler(log_path / log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    
    # Log setup completion
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={level}, file={log_path / log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger):
    """
    Decorator to log function calls with parameters and return values.
    
    Usage:
        @log_function_call(logger)
        async def my_function(param1, param2):
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised {type(e).__name__}: {e}", exc_info=True)
                raise
        
        def sync_wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised {type(e).__name__}: {e}", exc_info=True)
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Convenience functions for common log patterns
def log_error_with_context(
    logger: logging.Logger,
    message: str,
    error: Exception,
    context: Optional[dict] = None
) -> None:
    """
    Log an error with additional context information.
    
    Args:
        logger: Logger instance
        message: Error message
        error: Exception that occurred
        context: Additional context (e.g., user_id, request_id)
    """
    context_str = f" | Context: {context}" if context else ""
    logger.error(
        f"{message}: {type(error).__name__}: {error}{context_str}",
        exc_info=True,
        extra=context or {}
    )


def log_api_call(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log API call with standardized format.
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: User ID if authenticated
    """
    parts = [f"{method} {endpoint}"]
    
    if status_code:
        parts.append(f"status={status_code}")
    
    if duration_ms is not None:
        parts.append(f"duration={duration_ms:.2f}ms")
    
    if user_id:
        parts.append(f"user_id={user_id}")
    
    message = " | ".join(parts)
    
    if status_code and status_code >= 400:
        logger.warning(message)
    else:
        logger.info(message)


# Example usage patterns
"""
# Basic usage:
from app.core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Service initialized")
logger.debug("Processing request", extra={"user_id": "123"})

# Error logging with context:
from app.core.logging_config import log_error_with_context

try:
    result = process_data()
except Exception as e:
    log_error_with_context(
        logger,
        "Failed to process data",
        e,
        {"user_id": user_id, "data_size": len(data)}
    )

# API call logging:
from app.core.logging_config import log_api_call
import time

start = time.time()
# ... handle request ...
duration = (time.time() - start) * 1000

log_api_call(
    logger,
    "POST",
    "/api/v1/chat/send",
    status_code=200,
    duration_ms=duration,
    user_id=user_id
)
"""
