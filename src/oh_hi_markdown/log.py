"""Dual-output logging setup, console formatter, and redaction filter."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

_LOG_FILENAME = "ohmd.log"
_LOGGER_NAME = "ohmd"

# Keep references so shutdown_logging can close them.
_file_handler: logging.FileHandler | None = None
_stream_handler: logging.StreamHandler | None = None

# Redaction patterns: Bearer tokens and Authorization header values.
_REDACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"Authorization:\s*\S+"),
]
_REDACT_REPLACEMENT = "[REDACTED]"


def _terminal_supports_utf8() -> bool:
    """Return True if stderr's encoding can represent UTF-8 symbols."""
    encoding = getattr(sys.stderr, "encoding", None) or ""
    return encoding.lower().replace("-", "") in {"utf8", "utf_8"}


class OhmdConsoleFormatter(logging.Formatter):
    """Console formatter that prepends status symbols to log messages.

    Uses ``\\u2713`` (checkmark) for INFO and ``\\u26a0`` (warning) for WARNING
    when the terminal supports UTF-8, otherwise falls back to ``[OK]`` and
    ``[WARN]``.

    Format: ``{symbol} {message}`` — no timestamps on console.
    """

    def __init__(self) -> None:
        super().__init__()
        if _terminal_supports_utf8():
            self._info_symbol = "\u2713"
            self._warn_symbol = "\u26a0"
        else:
            self._info_symbol = "[OK]"
            self._warn_symbol = "[WARN]"

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if record.levelno == logging.INFO:
            return f"{self._info_symbol} {msg}"
        if record.levelno == logging.WARNING:
            return f"{self._warn_symbol} {msg}"
        return msg


class RedactionFilter(logging.Filter):
    """Logging filter that scrubs sensitive values from log messages.

    Replaces ``Bearer <token>`` and ``Authorization: <value>`` patterns
    with ``[REDACTED]`` to prevent API keys from leaking into ``ohmd.log``
    or console output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            # Format the message early so we can redact interpolated values.
            record.msg = record.getMessage()
            record.args = None
        record.msg = self._redact(str(record.msg))
        return True

    @staticmethod
    def _redact(text: str) -> str:
        for pattern in _REDACT_PATTERNS:
            text = pattern.sub(_REDACT_REPLACEMENT, text)
        return text


def setup_logging(temp_dir: Path) -> None:
    """Configure the ``ohmd`` logger with a file handler and a stderr handler.

    The file handler writes to ``ohmd.log`` inside *temp_dir* with full
    timestamps at DEBUG level.  The stream handler writes to stderr at INFO
    level using :class:`OhmdConsoleFormatter` for status symbols.

    Both handlers are fitted with a :class:`RedactionFilter` that scrubs
    sensitive tokens before they reach the log output.
    """
    global _file_handler, _stream_handler  # noqa: PLW0603

    # Idempotency guard — close any existing handlers first to prevent
    # handler accumulation across multiple pipeline runs or tests.
    if _file_handler is not None or _stream_handler is not None:
        shutdown_logging()

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    redaction_filter = RedactionFilter()

    # File handler — verbose output into the temp directory.
    log_path = temp_dir / _LOG_FILENAME
    _file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    _file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    _file_handler.setFormatter(file_fmt)
    _file_handler.addFilter(redaction_filter)
    logger.addHandler(_file_handler)

    # Stream handler — INFO and above to stderr with status symbols.
    _stream_handler = logging.StreamHandler(sys.stderr)
    _stream_handler.setLevel(logging.INFO)
    _stream_handler.setFormatter(OhmdConsoleFormatter())
    _stream_handler.addFilter(redaction_filter)
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
