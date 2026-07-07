"""
Logging framework for CvC.

Replaces print/cprint with proper logging module.
Configurable via --log flag or config file.
"""
import logging
import sys
from termcolor import cprint


# Custom colored formatter for terminal output
class ColorFormatter(logging.Formatter):
    """Adds color to log messages based on level."""

    COLORS = {
        logging.DEBUG: "cyan",
        logging.INFO: "green",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
        logging.CRITICAL: "red",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "white")
        msg = super(ColorFormatter, self).format(record)
        return msg


def setup_logging(level="INFO", log_file=None):
    """Configure the logging system.

    Args:
        level: minimum log level (DEBUG, INFO, WARNING, ERROR)
        log_file: optional file path to write logs to
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger
    root = logging.getLogger("cvc")
    root.setLevel(numeric_level)

    # Clear existing handlers
    root.handlers = []

    # Console handler with colors
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    color_fmt = ColorFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    console.setFormatter(color_fmt)
    root.addHandler(console)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

    return root


def get_logger(name):
    """Get a child logger for a module."""
    return logging.getLogger("cvc." + name)


# Convenience functions that mimic the old cprint behavior
def log_info(msg, **kwargs):
    """Log an info message."""
    logging.getLogger("cvc").info(msg)


def log_debug(msg, **kwargs):
    """Log a debug message."""
    logging.getLogger("cvc").debug(msg)


def log_warning(msg, **kwargs):
    """Log a warning message."""
    logging.getLogger("cvc").warning(msg)


def log_error(msg, **kwargs):
    """Log an error message."""
    logging.getLogger("cvc").error(msg)
