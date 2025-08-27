import logging
import os
from datetime import datetime

# ANSI escape sequences for colored output
COLORS = {
    logging.DEBUG: "\x1b[36;20m",  # Cyan
    logging.INFO: "\x1b[37;20m",  # White
    logging.WARNING: "\x1b[33;20m",  # Yellow
    logging.ERROR: "\x1b[31;20m",  # Red
    logging.CRITICAL: "\x1b[31;1m",  # Bold Red
}
RESET = "\x1b[0m"


class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors and file information to log messages."""

    def __init__(self) -> None:
        fmt = "%(asctime)s | %(levelname)-8s | " "%(filename)s:%(lineno)d | " "%(message)s"
        super().__init__(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")
        self.FORMATS = {level: f"{color}{self._fmt}{RESET}" for level, color in COLORS.items()}

    def format(self, record: logging.LogRecord) -> str:
        """Format log messages with color and file information."""
        log_fmt = self.FORMATS.get(record.levelno, self._fmt)
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


def setup_logger(debug_mode: bool = False, log_level: int | str = logging.INFO) -> logging.Logger:
    """Set up the logger with file information and colors.

    Accepts `log_level` as an int (e.g., logging.INFO) or string (e.g., "INFO").
    """
    # Normalize log level if provided as string
    if isinstance(log_level, str):
        lvl = logging._nameToLevel.get(log_level.upper())
        log_level = lvl if isinstance(lvl, int) else logging.INFO

    # Create logger
    logger = logging.getLogger("vectorsage_data")
    logger.setLevel(logging.DEBUG if debug_mode else log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else log_level)
    console_handler.setFormatter(ColorFormatter())
    logger.addHandler(console_handler)

    # Optionally add file handler for persistent logging
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"vectorsage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG if debug_mode else log_level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    # Capture warnings
    logging.captureWarnings(True)

    return logger
