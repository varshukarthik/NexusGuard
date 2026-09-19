from __future__ import annotations


class AppError(Exception):
    """A user-safe error. `message` is shown to users; internals never are."""

    def __init__(self, status: int, code: str, message: str, extra: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra or {}
