"""Dual-output logging setup and redaction filter."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_FILENAME = "ohmd.log"
_LOGGER_NAME = "ohmd"

# Keep references so shutdown_logging can close them.
_file_handler: logging.FileHandler | None = None
_stream_handler: logging.StreamHandler | None = None


def setup_logging(temp_dir: Path) -> None:
    """Configure the ``ohmd`` logger with a file handler and a stderr handler.

    The file handler writes to ``ohmd.log`` inside *temp_dir*.
    The stream handler writes to stderr.

    This is the minimum viable implementation — full ``✓``/``⚠`` formatting
    and redaction are added in slice 11.
    """
    global _file_handler, _stream_handler  # noqa: PLW0603

    # Idempotency guard — close any existing handlers first to prevent
    # handler accumulation across multiple pipeline runs or tests.
    if _file_handler is not None or _stream_handler is not None:
        shutdown_logging()

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # File handler — verbose output into the temp directory.
    log_path = temp_dir / _LOG_FILENAME
    _file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    _file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    _file_handler.setFormatter(file_fmt)
    logger.addHandler(_file_handler)

    # Stream handler — INFO and above to stderr.
    _stream_handler = logging.StreamHandler(sys.stderr)
    _stream_handler.setLevel(logging.INFO)
    stream_fmt = logging.Formatter("%(message)s")
    _stream_handler.setFormatter(stream_fmt)
    logger.addHandler(_stream_handler)


def shutdown_logging() -> None:
    """Flush and close all handlers attached by :func:`setup_logging`."""
    global _file_handler, _stream_handler  # noqa: PLW0603

    logger = logging.getLogger(_LOGGER_NAME)

    if _file_handler is not None:
        _file_handler.flush()
        _file_handler.close()
        logger.removeHandler(_file_handler)
        _file_handler = None

    if _stream_handler is not None:
        _stream_handler.flush()
        _stream_handler.close()
        logger.removeHandler(_stream_handler)
        _stream_handler = None
