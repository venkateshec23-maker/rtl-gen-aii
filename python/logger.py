"""
Structured Logging System for RTL-Gen AI

Usage:
    from python.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Generation started", extra={'module': 'adder_4bit'})
    logger.error("Verification failed", extra={'error_code': 'E001'})
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logger(
    name: str,
    log_file: str = 'logs/rtl_gen_ai.log',
    level: str = 'INFO',
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    json_format: bool = False
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        max_bytes: Max log file size before rotation
        backup_count: Number of backup files to keep
        json_format: Use JSON formatting
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    if json_format:
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Logger instance
    """
    from python.config import LOG_LEVEL, LOG_FILE, DEBUG_MODE
    
    level = 'DEBUG' if DEBUG_MODE else LOG_LEVEL
    
    return setup_logger(
        name=name,
        log_file=LOG_FILE,
        level=level,
        json_format=False  # Set to True for JSON logs
    )


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("Logger Self-Test\n")
    
    logger = get_logger(__name__)
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Test with extra data
    logger.info("Generation started", extra={
        'module': 'adder_4bit',
        'user': 'test_user'
    })
    
    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("Exception occurred")
    
    print("\n✓ Logger self-test complete")
    print(f"✓ Logs written to: logs/rtl_gen_ai.log")
