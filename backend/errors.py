"""Application errors that may be safely returned as JSON."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIError(Exception):
    message: str
    status_code: int = 400
    error: str = "bad_request"
    details: Any = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.error, "message": self.message, "details": self.details}


class ValidationAPIError(APIError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, 422, "validation_error", [] if details is None else details)
