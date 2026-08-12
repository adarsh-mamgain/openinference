"""Application-specific exceptions."""

from fastapi import HTTPException, status


class ModelUnavailableError(HTTPException):
    """Raised when a requested model file is missing on disk."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
