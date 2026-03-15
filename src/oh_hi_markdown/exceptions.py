"""Exception hierarchy for oh-hi-markdown."""


class ProviderError(Exception):
    """Base class for provider failures."""


class ProviderHTTPError(ProviderError):
    """Jina returned 4xx/5xx (not 429). Carries status_code."""

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(message or f"HTTP {status_code}")


class ProviderRateLimitError(ProviderError):
    """Jina returned 429. Message suggests setting JINA_API_KEY."""


class ProviderEmptyContentError(ProviderError):
    """Jina returned HTTP 200 but content is empty/whitespace."""


class ProviderUnreachableError(ProviderError):
    """Jina host is unreachable (DNS failure, connection refused, network timeout)."""


class ProviderDecodeError(ProviderError):
    """Jina returned a response that cannot be decoded as text."""


class FilesystemError(Exception):
    """Folder exists, permissions, disk full, rename failure."""
