"""Custom exception taxonomy for KidSync AI following rules.md guidelines."""

from typing import Any, Dict, Optional


class KidSyncBaseError(Exception):
    """Base exception for all KidSync AI domain errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class ValidationError(KidSyncBaseError):
    """Raised when client input fails schema or semantic validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(KidSyncBaseError):
    """Raised when JWT or credentials are invalid, expired, or missing."""

    def __init__(self, message: str = "Invalid or expired authentication credentials.") -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_FAILED",
        )


class AuthorizationError(KidSyncBaseError):
    """Raised when user lacks required role or caregiver permission."""

    def __init__(self, message: str = "Insufficient permissions to perform this operation.") -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_DENIED",
        )


class ResourceNotFoundError(KidSyncBaseError):
    """Raised when requested entity is not found."""

    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"entity": entity_name, "identifier": str(identifier)},
        )


class ConflictError(KidSyncBaseError):
    """Raised when resource conflicts with existing state (e.g., double booking)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="RESOURCE_CONFLICT",
            details=details,
        )


class CryptographicIntegrityError(KidSyncBaseError):
    """Raised when court-admissible audit log hash verification fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="AUDIT_CHAIN_INTEGRITY_COMPROMISED",
            details=details,
        )


class AIServiceUnavailableError(KidSyncBaseError):
    """Raised when LLM/Gemini API is unavailable or times out."""

    def __init__(self, message: str = "AI inference service temporarily unavailable.") -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="AI_SERVICE_UNAVAILABLE",
        )
