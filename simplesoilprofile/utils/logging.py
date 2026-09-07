"""Logging configuration for the simplesoilprofile package.

The package logs under the ``simplesoilprofile`` hierarchy and, as a library, attaches a
handler to the package logger only — module loggers are plain children that propagate to
it, so every record is emitted once. Applications control the level through
``logging.getLogger("simplesoilprofile")``.
"""

import logging
import sys

PACKAGE_LOGGER = "simplesoilprofile"


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return the logger for ``name`` under the package hierarchy.

    Args:
        name: Name of the logger, typically __name__ of the module
        level: Logging level applied to the package logger the first time it is configured

    Returns:
        Configured logger instance
    """
    package = logging.getLogger(PACKAGE_LOGGER)
    if not package.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        package.addHandler(handler)
        package.setLevel(getattr(logging, level.upper()))

    if name == PACKAGE_LOGGER or name.startswith(PACKAGE_LOGGER + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{PACKAGE_LOGGER}.{name}")


# Create package-level logger
logger = setup_logger(PACKAGE_LOGGER)
