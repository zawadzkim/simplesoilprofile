"""Logging configuration for the simplesoilprofile package."""

import logging
import sys


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Set up a logger with consistent formatting.
    
    Args:
        name: Name of the logger, typically __name__ of the module
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only add handlers if the logger doesn't have any
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Set level
    logger.setLevel(getattr(logging, level.upper()))

    return logger


# Create package-level logger
logger = setup_logger("simplesoilprofile")
