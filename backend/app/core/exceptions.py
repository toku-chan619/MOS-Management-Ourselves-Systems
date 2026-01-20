"""Custom exceptions for MOS application"""


class MOSException(Exception):
    """Base exception for MOS application"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class LLMAPIError(MOSException):
    """Raised when LLM API call fails"""
    pass


class DatabaseError(MOSException):
    """Raised when database operation fails"""
    pass


class ValidationError(MOSException):
    """Raised when validation fails"""
    pass


class NotFoundError(MOSException):
    """Raised when requested resource is not found"""
    pass


class RetryableError(MOSException):
    """Raised when operation should be retried"""
    pass
